import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from ai_disclosure import load_ai_disclosure
from route_manifest import load_route_manifest
from scripts.package_launch_release import build_backend_archive


ROOT = Path(__file__).resolve().parents[2]


def _pre_deploy_snapshot_block() -> str:
    deploy_lines = (ROOT / "scripts" / "deploy.sh").read_text(
        encoding="utf-8"
    ).splitlines()
    dump_index = next(
        index for index, line in enumerate(deploy_lines) if line.startswith("pg_dump -Fc")
    )
    rotation_index = next(
        index
        for index, line in enumerate(deploy_lines[dump_index + 1 :], dump_index + 1)
        if line == 'echo "  rotated auto-backups (kept newest 6)"'
    )
    return "\n".join(deploy_lines[dump_index + 1 : rotation_index + 1])


def _git_bash() -> str:
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if git_bash.exists():
        return str(git_bash)
    bash = shutil.which("bash")
    assert bash is not None
    return bash


def _run_pre_deploy_snapshot(
    root: Path, *, include_nuxt_output: bool = True
) -> subprocess.CompletedProcess[str]:
    for directory in ("agent", "web/media", "backups"):
        (root / directory).mkdir(parents=True)
    (root / "agent" / "server.py").write_bytes(b"agent\n")
    (root / "web" / "data.json").write_bytes(b"{}\n")
    (root / "web" / "media" / "photo.txt").write_bytes(b"media\n")
    if include_nuxt_output:
        (root / "web-nuxt" / ".output").mkdir(parents=True)
        (root / "web-nuxt" / ".output" / "server.mjs").write_bytes(b"nuxt\n")
    env = {**os.environ, "TS": "snapshot-test"}
    # The production block is inside an unquoted SSH heredoc, so escaped remote
    # expansions arrive at the remote Bash process without the backslash.
    snapshot_block = "set -e\n" + _pre_deploy_snapshot_block().replace(r"\$", "$")
    return subprocess.run(
        [_git_bash(), "-c", snapshot_block],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_nuxt_compose_build_uses_repository_root_context():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nuxt_service = compose.split("\n  nuxt:\n", 1)[1].split("\n  nginx:\n", 1)[0]

    assert "context: ." in nuxt_service
    assert "dockerfile: web-nuxt/Dockerfile" in nuxt_service
    assert "BUILD_REVISION: ${BUILD_REVISION:-}" in nuxt_service
    assert "context: ./web-nuxt" not in nuxt_service


def test_production_nuxt_build_entrypoints_supply_the_source_revision():
    deploy = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    prerender = (ROOT / "scripts" / "build-prerender.sh").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )

    revision_export = 'export BUILD_REVISION="$(git rev-parse --verify HEAD)"'
    assert revision_export in deploy
    assert deploy.index(revision_export) < deploy.index(
        'NODE_OPTIONS="--max-old-space-size=4096" npm run build'
    )
    assert revision_export in prerender
    assert prerender.index(revision_export) < prerender.index("npm run build")
    assert (
        "env:\n          BUILD_REVISION: ${{ github.sha }}\n        run: npm run build"
        in ci
    )
    assert (
        'BUILD_REVISION="$(git rev-parse --verify HEAD)" docker compose up -d --build'
        in release
    )


def test_nuxt_image_builds_from_web_project_and_root_config():
    dockerfile = (ROOT / "web-nuxt" / "Dockerfile").read_text(encoding="utf-8")

    assert "WORKDIR /app/web-nuxt" in dockerfile
    assert "COPY web-nuxt/package*.json ./" in dockerfile
    assert "COPY web-nuxt/ ./" in dockerfile
    assert "COPY config/ /app/config/" in dockerfile
    assert "ARG BUILD_REVISION" in dockerfile
    assert "ENV BUILD_REVISION=${BUILD_REVISION}" in dockerfile
    assert 'RUN test -n "$BUILD_REVISION"' in dockerfile
    assert "COPY --from=build /app/web-nuxt/.output ./.output" in dockerfile


def test_backend_image_contains_root_config():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY config/ ./config/" in dockerfile


def test_deploy_packages_root_config():
    deploy = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'init.sql config web/data.json' in deploy


def test_pre_deploy_snapshot_succeeds_without_config_for_first_migration(tmp_path: Path):
    result = _run_pre_deploy_snapshot(tmp_path)

    assert result.returncode == 0, result.stderr
    with tarfile.open(tmp_path / "backups/pre-deploy-snapshot-test.tar.gz", "r:gz") as bundle:
        assert not any(
            name == "config" or name.startswith("config/") for name in bundle.getnames()
        )


def test_pre_deploy_snapshot_includes_config_bytes_when_present(tmp_path: Path):
    config_bytes = b'{"revision":"launch-indexing-policy-v1"}\n'
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "launch-indexing-policy.json").write_bytes(config_bytes)

    result = _run_pre_deploy_snapshot(tmp_path)

    assert result.returncode == 0, result.stderr
    with tarfile.open(tmp_path / "backups/pre-deploy-snapshot-test.tar.gz", "r:gz") as bundle:
        assert bundle.extractfile("config/launch-indexing-policy.json").read() == config_bytes


def test_pre_deploy_snapshot_failure_is_nonzero_and_leaves_no_partial_archive(
    tmp_path: Path,
):
    result = _run_pre_deploy_snapshot(tmp_path, include_nuxt_output=False)

    assert result.returncode != 0
    assert not (tmp_path / "backups/pre-deploy-snapshot-test.tar.gz").exists()
    assert list((tmp_path / "backups").glob("*.tmp*")) == []


def test_docker_context_excludes_secrets_and_local_build_caches():
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {
        ".env",
        "**/.env",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "**/node_modules",
        "web-nuxt/.nuxt",
        "web-nuxt/.output",
    } <= ignored
    assert "config" not in ignored
    assert "config/" not in ignored


def test_unpacked_release_loaders_read_exact_packaged_bytes(tmp_path: Path):
    archive = build_backend_archive(ROOT, tmp_path / "backend.tar.gz")
    release_root = tmp_path / "release"
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(release_root, filter="data")

    route = load_route_manifest(release_root=release_root)
    disclosure = load_ai_disclosure(release_root=release_root)

    route_path = ROOT / "config" / "launch-indexing-policy.json"
    disclosure_path = ROOT / "config" / "ai-disclosure.json"
    assert route.artifact.path == release_root / "config" / route_path.name
    assert disclosure.artifact.path == release_root / "config" / disclosure_path.name
    assert route.artifact.raw == route_path.read_bytes()
    assert disclosure.artifact.raw == disclosure_path.read_bytes()
