import os
from pathlib import Path
import shutil
import subprocess
import tarfile


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
        if line.startswith("ls -t backups/pre-deploy-")
    )
    return "\n".join(deploy_lines[dump_index + 1 : rotation_index])


def _git_bash() -> str:
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if git_bash.exists():
        return str(git_bash)
    bash = shutil.which("bash")
    assert bash is not None
    return bash


def _run_pre_deploy_snapshot(root: Path) -> subprocess.CompletedProcess[str]:
    for directory in ("agent", "web/media", "web-nuxt/.output", "backups"):
        (root / directory).mkdir(parents=True)
    (root / "agent" / "server.py").write_bytes(b"agent\n")
    (root / "web" / "data.json").write_bytes(b"{}\n")
    (root / "web" / "media" / "photo.txt").write_bytes(b"media\n")
    (root / "web-nuxt" / ".output" / "server.mjs").write_bytes(b"nuxt\n")
    env = {**os.environ, "TS": "snapshot-test"}
    # The production block is inside an unquoted SSH heredoc, so escaped remote
    # expansions arrive at the remote Bash process without the backslash.
    snapshot_block = _pre_deploy_snapshot_block().replace(r"\$", "$")
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
    assert "context: ./web-nuxt" not in nuxt_service


def test_nuxt_image_builds_from_web_project_and_root_config():
    dockerfile = (ROOT / "web-nuxt" / "Dockerfile").read_text(encoding="utf-8")

    assert "WORKDIR /app/web-nuxt" in dockerfile
    assert "COPY web-nuxt/package*.json ./" in dockerfile
    assert "COPY web-nuxt/ ./" in dockerfile
    assert "COPY config/ /app/config/" in dockerfile
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
