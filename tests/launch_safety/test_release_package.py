import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

import pytest

from ai_disclosure import load_ai_disclosure
from route_manifest import load_route_manifest
from scripts import package_launch_release as release_package
from scripts.ops.compose_network_audit import CHECK_NAMES
from scripts.package_launch_release import (
    build_backend_archive,
    build_launch_release,
    build_launch_release_manifest,
    collect_launch_release_payload,
)


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


def _write_launch_fixture(root: Path) -> Path:
    """Create a small reviewed closed-release tree without building Nuxt."""
    (root / "agent" / "data" / "sitemap-bundles").mkdir(parents=True)
    (root / "agent" / "tests").mkdir(parents=True)
    (root / "agent" / "server.py").write_bytes(b"agent\n")
    (root / "agent" / "data" / "runtime.sqlite").write_bytes(b"persistent\n")
    (root / "agent" / "tests" / "test_server.py").write_bytes(b"excluded\n")
    (root / "agent" / ".env").write_bytes(b"SECRET=excluded\n")

    (root / "config").mkdir(parents=True)
    for name in ("launch-indexing-policy.json", "ai-disclosure.json"):
        source = ROOT / "config" / name
        (root / "config" / name).write_bytes(source.read_bytes())
    (root / "requirements.txt").write_bytes(b"fastapi\n")
    (root / "init.sql").write_bytes(b"-- schema\n")
    (root / "nginx.conf").write_bytes(b"events {}\n")
    (root / "nginx-ssl.conf").write_bytes(b"events {}\n")

    (root / "web-nuxt" / ".output" / "server").mkdir(parents=True)
    (root / "web-nuxt" / ".output" / "public").mkdir(parents=True)
    (root / "web-nuxt" / ".output" / "server" / "index.mjs").write_bytes(b"output\n")
    (root / "web-nuxt" / ".output" / "public" / "sw.js").write_bytes(b"worker\n")
    (root / "web-nuxt" / "package.json").write_bytes(b'{"scripts":{"build":"nuxt build"}}\n')
    (root / "web-nuxt" / "package-lock.json").write_bytes(b'{"lockfileVersion":3}\n')
    route_raw = (root / "config" / "launch-indexing-policy.json").read_bytes()
    disclosure_raw = (root / "config" / "ai-disclosure.json").read_bytes()
    route_digest = hashlib.sha256(route_raw).hexdigest()
    disclosure_digest = hashlib.sha256(disclosure_raw).hexdigest()
    fingerprint_payload = {
        "cache_isolation": "launch-cache-isolation-v1",
        "disclosure_artifact": {
            "revision": "ai-disclosure-v1",
            "sha256": hashlib.sha256(disclosure_digest.encode("ascii")).hexdigest(),
        },
        "index_policy": "index-policy-v1",
        "response_matrix": "launch-safety-matrix-v1",
        "route_artifact": {
            "revision": "launch-indexing-policy-v1",
            "sha256": hashlib.sha256(route_digest.encode("ascii")).hexdigest(),
        },
        "sitemap_protocol": "pinned-sitemap-bundle-v1",
    }
    policy_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    readiness = {
        "schema_version": 1,
        "build_revision": "reviewed-source-revision",
        "artifacts": {
            "route_manifest": {
                "revision": "launch-indexing-policy-v1",
                "sha256": route_digest,
            },
            "ai_disclosure": {
                "revision": "ai-disclosure-v1",
                "sha256": disclosure_digest,
            },
            "policy_fingerprint": policy_fingerprint,
        },
        "policy_route_classes": ["public-html", "public-api", "root-seo", "internal-readiness"],
        "compiled_cache_rules": [],
        "public_prerender_files": [],
        "service_worker": {
            "version": "vl360-launch-v1",
            "rule_digest": hashlib.sha256(b"worker\n").hexdigest(),
            "cache_purge": {
                "revision": "launch-cache-purge-v1",
                "strategy": "delete-all-except",
                "retained_cache_names": ["vl360-launch-v1-assets"],
                "forbidden_cache_classes": [
                    "navigation", "html", "root-seo", "internal", "api",
                    "selective-open", "failed-open",
                ],
                "activation_verified": True,
            },
        },
    }
    (root / "web-nuxt" / ".output" / "server" / "launch-readiness-manifest.json").write_text(
        json.dumps(readiness, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )

    (root / "ops" / "systemd").mkdir(parents=True)
    (root / "ops" / "systemd" / "vl-agent.service").write_bytes(b"[Service]\n")
    (root / "ops" / "nginx" / "maintenance").mkdir(parents=True)
    (root / "ops" / "nginx" / "maintenance" / "server-enabled.conf").write_bytes(b"if (1) { return 503; }\n")
    (root / "scripts" / "ops").mkdir(parents=True)
    (root / "scripts" / "ops" / "deploy.sh").write_bytes(b"#!/bin/sh\n")

    compose_names = (
        "docker-compose.dev.yml",
        "docker-compose.prod.yml",
        "docker-compose.systemd-deps.yml",
        "docker-compose.yml",
    )
    for name in compose_names:
        (root / name).write_bytes((name + "\n").encode("ascii"))
    audit = {
        "schema_version": 1,
        "revision": "compose-network-audit-v1",
        "check_names": sorted(CHECK_NAMES),
        "checks": {name: "passed" for name in sorted(CHECK_NAMES)},
        "published_ports": [],
        "source_digest_kind": "sha256-utf8-lf-v1",
        "sources": [
            {
                "path": name,
                "sha256": hashlib.sha256((name + "\n").encode("ascii")).hexdigest(),
            }
            for name in compose_names
        ],
    }
    audit_path = root / "build" / "compose-network-audit.json"
    audit_path.parent.mkdir()
    audit_path.write_text(json.dumps(audit, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return audit_path


def test_build_launch_release_has_closed_manifest_and_deterministic_sidecar(tmp_path: Path):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)

    first = build_launch_release(
        root,
        tmp_path / "first.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )
    second = build_launch_release(
        root,
        tmp_path / "second.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )

    assert first.archive.read_bytes() == second.archive.read_bytes()
    assert first.digest_file.read_text(encoding="ascii") == (
        f"{hashlib.sha256(first.archive.read_bytes()).hexdigest()}  first.tar.gz\n"
    )
    with tarfile.open(first.archive, "r:gz") as bundle:
        names = bundle.getnames()
        manifest = json.loads(bundle.extractfile("launch-release-manifest.json").read())
    assert "agent/data" not in names
    assert not any(name.startswith("agent/data/") for name in names)
    assert "agent/tests/test_server.py" not in names
    assert "docker-compose.dev.yml" not in names
    assert manifest["package_kind"] == "vl360-launch-release"
    assert manifest["launch_posture"] == "closed"
    assert manifest["developer_override"] == {"path": "docker-compose.dev.yml", "included": False}
    assert manifest["persistent_paths"] == ["agent/data", "agent/data/sitemap-bundles"]
    assert set(manifest) == {
        "schema_version", "package_kind", "source_revision", "launch_posture",
        "canonical_artifacts", "readiness_manifest", "network_audit",
        "developer_override", "persistent_paths", "members",
    }


def test_build_launch_release_manifest_derives_network_audit_from_payload(
    tmp_path: Path,
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    payload = collect_launch_release_payload(root, audit)

    manifest = build_launch_release_manifest(
        root, payload, "reviewed-source-revision"
    )

    assert manifest["network_audit"] == {
        "path": "compose-network-audit.json",
        "sha256": hashlib.sha256(audit.read_bytes()).hexdigest(),
    }


def test_build_launch_release_refuses_invalid_audit_without_outputs(tmp_path: Path):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    audit.write_text("{}\n", encoding="utf-8")
    destination = tmp_path / "release.tar.gz"
    with pytest.raises(ValueError):
        build_launch_release(root, destination, compose_network_audit=audit, source_revision="r")
    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()


def test_build_launch_release_normalizes_modes_and_excludes_pnpm_and_caches(tmp_path: Path):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    (root / "web-nuxt" / "pnpm-lock.yaml").write_bytes(b"excluded\n")
    (root / "web-nuxt" / ".output" / ".cache").mkdir()
    (root / "web-nuxt" / ".output" / ".cache" / "secret").write_bytes(b"excluded\n")
    result = build_launch_release(
        root,
        tmp_path / "release.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )
    with tarfile.open(result.archive, "r:gz") as bundle:
        members = {item.name: item for item in bundle.getmembers()}
    assert "web-nuxt/pnpm-lock.yaml" not in members
    assert not any(name.startswith("web-nuxt/.output/.cache") for name in members)
    assert members["scripts/ops/deploy.sh"].mode == 0o755
    assert members["agent/server.py"].mode == 0o644
    assert members["agent"].mode == 0o755
    assert members["agent/server.py"].uid == 0
    assert members["agent/server.py"].gid == 0
    assert members["agent/server.py"].mtime == 0


def test_build_launch_release_never_overwrites_existing_outputs(tmp_path: Path):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    sidecar = destination.with_name(destination.name + ".sha256")
    destination.write_bytes(b"keep archive")
    sidecar.write_text("keep digest\n", encoding="ascii")
    with pytest.raises(FileExistsError):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )
    assert destination.read_bytes() == b"keep archive"
    assert sidecar.read_text(encoding="ascii") == "keep digest\n"


def test_build_launch_release_refuses_symlink_root(tmp_path: Path):
    source = tmp_path / "source"
    _write_launch_fixture(source)
    root = tmp_path / "source-link"
    root.symlink_to(source, target_is_directory=True)
    destination = tmp_path / "release.tar.gz"

    with pytest.raises(ValueError, match="release source contains symlink"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=Path("build/compose-network-audit.json"),
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()


def test_build_launch_release_cleans_archive_temp_if_digest_temp_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    real_mkstemp = release_package.tempfile.mkstemp
    call_count = 0

    def fail_digest_temp(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("digest temp creation failed")
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(release_package.tempfile, "mkstemp", fail_digest_temp)

    with pytest.raises(OSError, match="digest temp creation failed"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.parametrize("failed_publish", [1, 2])
def test_build_launch_release_cleans_owned_outputs_if_publish_raises_after_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_publish: int,
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    real_publish = release_package._publish_without_overwrite
    call_count = 0

    def publish_then_fail(temporary: Path, output: Path) -> None:
        nonlocal call_count
        call_count += 1
        real_publish(temporary, output)
        if call_count == failed_publish:
            raise OSError("publish interrupted after link")

    monkeypatch.setattr(
        release_package, "_publish_without_overwrite", publish_then_fail
    )

    with pytest.raises(OSError, match="publish interrupted after link"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_build_launch_release_rollback_preserves_replacement_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    digest_file = destination.with_name(destination.name + ".sha256")
    real_publish = release_package._publish_without_overwrite
    call_count = 0

    def replace_outputs_before_failure(temporary: Path, output: Path) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            real_publish(temporary, output)
            output.unlink()
            output.write_bytes(b"keep replacement archive")
            return
        output.write_text("keep replacement digest\n", encoding="ascii")
        raise FileExistsError("digest output appeared concurrently")

    monkeypatch.setattr(
        release_package, "_publish_without_overwrite", replace_outputs_before_failure
    )

    with pytest.raises(FileExistsError, match="appeared concurrently"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert destination.read_bytes() == b"keep replacement archive"
    assert digest_file.read_text(encoding="ascii") == "keep replacement digest\n"
    assert list(tmp_path.glob(".*.tmp")) == []
