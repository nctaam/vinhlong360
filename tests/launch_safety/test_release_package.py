import hashlib
import json
import os
from pathlib import Path
import tarfile

import pytest

from agent.launch_evidence import build_policy_fingerprint
from ai_disclosure import load_ai_disclosure
from route_manifest import load_route_manifest
from scripts import package_launch_release as release_package
from scripts.ops import verify_closed_release as closed_release_verifier
from scripts.ops.compose_network_audit import CHECK_NAMES
from scripts.package_launch_release import (
    build_backend_archive,
    build_launch_release,
    build_launch_release_manifest,
    collect_launch_release_payload,
)


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy.sh"


def test_release_policy_fingerprint_matches_backend_contract():
    artifacts = {
        "route_manifest": {
            "revision": "launch-indexing-policy-v1",
            "sha256": "a" * 64,
        },
        "ai_disclosure": {
            "revision": "ai-disclosure-v1",
            "sha256": "b" * 64,
        },
    }
    expected = build_policy_fingerprint(
        route_revision="launch-indexing-policy-v1",
        route_digest="a" * 64,
        disclosure_revision="ai-disclosure-v1",
        disclosure_digest="b" * 64,
    )

    assert {
        "packager": release_package._policy_fingerprint(artifacts),
        "verifier": closed_release_verifier._expected_policy_fingerprint(artifacts),
    } == {"packager": expected, "verifier": expected}


def _network_audit_header(revision: str) -> dict[str, object]:
    check_names = sorted(CHECK_NAMES)
    return {
        "schema_version": 1,
        "revision": revision,
        "check_names": check_names,
        "checks": {name: "passed" for name in check_names},
        "published_ports": [],
        "source_digest_kind": "sha256-utf8-lf-v1",
        "sources": [],
    }


def _network_audit_verifier_bytes(revision: str) -> bytes:
    audit = _network_audit_header(revision)
    audit["published_ports"] = [
        {
            "service": "nginx",
            "host_ip": "0.0.0.0",
            "published": port,
            "target": port,
            "protocol": "tcp",
        }
        for port in (80, 443)
    ]
    return (json.dumps(audit, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def test_network_audit_v2_is_the_canonical_package_and_verifier_identity():
    release_package._validate_network_audit_header(
        _network_audit_header("compose-network-audit-v2")
    )
    closed_release_verifier._validate_network_audit(
        _network_audit_verifier_bytes("compose-network-audit-v2")
    )


def test_stale_network_audit_v1_is_rejected_by_package_and_verifier():
    with pytest.raises(ValueError, match="revision mismatch"):
        release_package._validate_network_audit_header(
            _network_audit_header("compose-network-audit-v1")
        )
    with pytest.raises(ValueError, match="revision mismatch"):
        closed_release_verifier._validate_network_audit(
            _network_audit_verifier_bytes("compose-network-audit-v1")
        )


def test_network_audit_v2_rejects_stale_check_inventory_end_to_end():
    audit = _network_audit_header("compose-network-audit-v2")
    audit["check_names"].remove("maintenance_initializer_exact")
    del audit["checks"]["maintenance_initializer_exact"]

    with pytest.raises(ValueError, match="check inventory mismatch"):
        release_package._validate_network_audit_header(audit)
    audit["published_ports"] = json.loads(
        _network_audit_verifier_bytes("compose-network-audit-v2")
    )["published_ports"]
    with pytest.raises(ValueError, match="check inventory mismatch"):
        closed_release_verifier._validate_network_audit(
            (json.dumps(audit, sort_keys=True, separators=(",", ":")) + "\n").encode(
                "utf-8"
            )
        )


def test_deploy_builds_and_uploads_only_the_combined_launch_release():
    script = DEPLOY.read_text(encoding="utf-8")

    assert "scripts/ops/compose_network_audit.py" in script
    assert "scripts/package_launch_release.py launch-release" in script
    assert '--destination "$RELEASE_ARCHIVE"' in script
    assert 'RELEASE_ARCHIVE="$TMP/vl360-launch-release.tar.gz"' in script
    assert '"$RELEASE_ARCHIVE.sha256"' in script
    assert "vl-deploy.tar.gz" not in script
    assert "vl-nuxt-output.tar.gz" not in script
    assert "tar -xzf" not in script


def test_nuxt_compose_build_uses_repository_root_context():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nuxt_service = compose.split("\n  nuxt:\n", 1)[1].split("\n  nginx:\n", 1)[0]

    assert "context: ." in nuxt_service
    assert "dockerfile: web-nuxt/Dockerfile" in nuxt_service
    assert "BUILD_REVISION: ${BUILD_REVISION:-}" in nuxt_service
    assert "API_BASE: http://agent:8360" in nuxt_service
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
    assert "ARG API_BASE" in dockerfile
    assert "ENV API_BASE=${API_BASE}" in dockerfile
    assert 'RUN test -n "$BUILD_REVISION"' in dockerfile
    assert "COPY --from=build /app/web-nuxt/.output ./.output" in dockerfile


def test_backend_image_contains_root_config():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY config/ ./config/" in dockerfile


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
    (root / "agent" / "migrations").mkdir(parents=True)
    (root / "agent" / "tests").mkdir(parents=True)
    (root / "agent" / "server.py").write_bytes(b"agent\n")
    (root / "agent" / "data" / "runtime.sqlite").write_bytes(b"persistent\n")
    (root / "agent" / "tests" / "test_server.py").write_bytes(b"excluded\n")
    (root / "agent" / ".env").write_bytes(b"SECRET=excluded\n")
    for migration in sorted((ROOT / "agent" / "migrations").glob("*.sql")):
        (root / "agent" / "migrations" / migration.name).write_bytes(
            migration.read_bytes()
        )

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
    policy_fingerprint = build_policy_fingerprint(
        route_revision="launch-indexing-policy-v1",
        route_digest=route_digest,
        disclosure_revision="ai-disclosure-v1",
        disclosure_digest=disclosure_digest,
    )
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
    (root / "scripts" / "check_migration_gate.py").write_bytes(
        (ROOT / "scripts" / "check_migration_gate.py").read_bytes()
    )
    (root / "scripts" / "ops" / "deploy.sh").write_bytes(b"#!/bin/sh\n")
    (root / "scripts" / "ops" / "verify_closed_release.py").write_bytes(
        (ROOT / "scripts" / "ops" / "verify_closed_release.py").read_bytes()
    )

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
        "revision": "compose-network-audit-v2",
        "check_names": sorted(CHECK_NAMES),
        "checks": {name: "passed" for name in sorted(CHECK_NAMES)},
        "published_ports": [
            {
                "service": "nginx",
                "host_ip": "192.0.2.1",
                "published": 80,
                "target": 80,
                "protocol": "tcp",
            },
            {
                "service": "nginx",
                "host_ip": "192.0.2.1",
                "published": 443,
                "target": 443,
                "protocol": "tcp",
            },
        ],
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


def _assert_manifest_matches_archive_members(archive: Path) -> dict[str, object]:
    with tarfile.open(archive, "r:gz") as bundle:
        manifest = json.loads(
            bundle.extractfile("launch-release-manifest.json").read()
        )
        completed_members = {}
        for member in bundle.getmembers():
            if not member.isfile() or member.name == "launch-release-manifest.json":
                continue
            raw = bundle.extractfile(member).read()
            completed_members[member.name] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
    assert manifest["members"] == completed_members
    return manifest


def test_launch_release_ignores_ambient_non_member_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    ambient = root / "docs" / "launch-indexing-policy.json"
    ambient.parent.mkdir()
    ambient.write_bytes(b"not packaged")

    package = build_launch_release(
        root,
        tmp_path / "release.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )

    with tarfile.open(package.archive, "r:gz") as bundle:
        assert "docs/launch-indexing-policy.json" not in bundle.getnames()


def test_launch_release_rejects_duplicate_snapshot_member_without_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    real_snapshot = release_package._snapshot_launch_release

    def duplicate_snapshot(root_path, payload):
        snapshot = real_snapshot(root_path, payload)
        canonical = next(
            member
            for member in snapshot.members
            if member.arcname == "config/launch-indexing-policy.json"
        )
        duplicate = release_package._SnapshotMember(
            canonical.source,
            "web-nuxt/launch-indexing-policy.json",
        )
        return release_package._LaunchReleaseSnapshot(
            snapshot.root,
            snapshot.members + (duplicate,),
            snapshot.sources,
        )

    monkeypatch.setattr(
        release_package,
        "_snapshot_launch_release",
        duplicate_snapshot,
    )

    with pytest.raises(ValueError, match="duplicate canonical"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


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
    _assert_manifest_matches_archive_members(first.archive)
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


def test_build_launch_release_includes_migration_prerequisites_with_manifest_digests(
    tmp_path: Path,
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    package = build_launch_release(
        root,
        tmp_path / "release.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )
    expected = {
        "scripts/check_migration_gate.py": root
        / "scripts"
        / "check_migration_gate.py",
        "scripts/ops/verify_closed_release.py": root
        / "scripts"
        / "ops"
        / "verify_closed_release.py",
        **{
            f"agent/migrations/{source.name}": source
            for source in sorted((root / "agent" / "migrations").glob("*.sql"))
        },
    }

    with tarfile.open(package.archive, "r:gz") as bundle:
        manifest = json.loads(
            bundle.extractfile("launch-release-manifest.json").read()
        )
        archived = {
            member.name: bundle.extractfile(member).read()
            for member in bundle.getmembers()
            if member.isfile() and member.name in expected
        }

    missing = set(expected) - set(archived)
    unexpected = set(archived) - set(expected)
    assert not missing, f"missing migration prerequisite archive members: {sorted(missing)}"
    assert not unexpected, (
        f"unexpected migration prerequisite archive members: {sorted(unexpected)}"
    )
    for name, source in expected.items():
        raw = source.read_bytes()
        assert archived[name] == raw
        assert manifest["members"][name] == {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }


@pytest.mark.parametrize(
    "source_revision",
    [
        pytest.param(" invalid-revision ", id="surrounding-whitespace"),
        pytest.param("invalid\0revision", id="nul"),
        pytest.param("invalid\rrevision", id="carriage-return"),
        pytest.param("invalid\nrevision", id="newline"),
    ],
)
def test_build_launch_release_refuses_noncanonical_source_revision_without_outputs(
    tmp_path: Path, source_revision: str
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    readiness_path = (
        root / "web-nuxt" / ".output" / "server" / "launch-readiness-manifest.json"
    )
    readiness = json.loads(readiness_path.read_bytes())
    readiness["build_revision"] = source_revision
    readiness_path.write_text(
        json.dumps(readiness, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "release.tar.gz"

    with pytest.raises(
        ValueError, match="source revision must be a non-empty canonical string"
    ):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision=source_revision,
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_build_launch_release_uses_one_snapshot_if_source_mutates_before_tar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    source = root / "agent" / "server.py"
    destination = tmp_path / "release.tar.gz"
    real_write = release_package.write_deterministic_tar_gz

    def mutate_then_write(*args, **kwargs):
        source.write_bytes(b"mutated after manifest\n")
        return real_write(*args, **kwargs)

    monkeypatch.setattr(
        release_package, "write_deterministic_tar_gz", mutate_then_write
    )

    result = build_launch_release(
        root,
        destination,
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )

    with tarfile.open(result.archive, "r:gz") as bundle:
        assert bundle.extractfile("agent/server.py").read() == b"agent\n"
    _assert_manifest_matches_archive_members(result.archive)


def test_build_launch_release_refuses_symlink_swap_before_tar_without_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    source = root / "agent" / "server.py"
    outside_secret = tmp_path / "OUTSIDE_SECRET"
    outside_secret.write_bytes(b"must never be packaged\n")
    destination = tmp_path / "release.tar.gz"
    real_write = release_package.write_deterministic_tar_gz

    def swap_then_write(*args, **kwargs):
        source.unlink()
        try:
            source.symlink_to(outside_secret)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")
        return real_write(*args, **kwargs)

    monkeypatch.setattr(release_package, "write_deterministic_tar_gz", swap_then_write)

    with pytest.raises(ValueError, match="release source (contains symlink|changed)"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


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


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "host_ip": "127.0.0.1"}),
            id="loopback-host-ip",
        ),
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "host_ip": "not-an-ip"}),
            id="invalid-host-ip",
        ),
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "published": "80"}),
            id="string-published-port",
        ),
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "published": True}),
            id="boolean-published-port",
        ),
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "host_ip": 2130706433}),
            id="non-string-host-ip",
        ),
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "target": 443}),
            id="wrong-target-port",
        ),
        pytest.param(
            lambda ports: ports.__setitem__(0, {**ports[0], "protocol": "udp"}),
            id="wrong-protocol",
        ),
        pytest.param(
            lambda ports: ports.append(dict(ports[0])),
            id="duplicate-endpoint",
        ),
        pytest.param(
            lambda ports: ports.pop(1),
            id="missing-endpoint",
        ),
        pytest.param(
            lambda ports: ports.reverse(),
            id="noncanonical-order",
        ),
    ],
)
def test_build_launch_release_rejects_noncanonical_published_endpoints_without_outputs(
    tmp_path: Path, mutate
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    value = json.loads(audit.read_text(encoding="utf-8"))
    mutate(value["published_ports"])
    audit.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "release.tar.gz"

    with pytest.raises(ValueError):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.skipif(os.name == "nt", reason="Windows denies unlinking an open temp file")
def test_build_launch_release_rejects_temp_symlink_swap_without_touching_external_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    sentinel = tmp_path / "external-sentinel"
    sentinel.write_bytes(b"must remain untouched\n")
    real_mkstemp = release_package.tempfile.mkstemp
    call_count = 0

    def swap_archive_temp(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        descriptor, name = real_mkstemp(*args, **kwargs)
        if call_count == 1:
            temporary = Path(name)
            temporary.unlink()
            temporary.symlink_to(sentinel)
        return descriptor, name

    monkeypatch.setattr(release_package.tempfile, "mkstemp", swap_archive_temp)

    with pytest.raises(ValueError, match="temporary archive"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert sentinel.read_bytes() == b"must remain untouched\n"
    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_build_launch_release_never_reopens_owned_temporary_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    real_open = Path.open

    def reject_temporary_reopen(path: Path, *args, **kwargs):
        if path.name.endswith(".tmp"):
            raise AssertionError(f"temporary path was reopened: {path}")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_temporary_reopen)

    result = build_launch_release(
        root,
        destination,
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )

    assert result.archive == destination
    assert result.digest_file == destination.with_name(destination.name + ".sha256")


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
    try:
        root.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
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


def test_build_launch_release_rolls_back_owned_outputs_if_temp_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    digest_file = destination.with_name(destination.name + ".sha256")
    real_cleanup = release_package._cleanup_temporary_outputs

    def cleanup_then_fail(descriptors, paths):
        assert real_cleanup(descriptors, paths) is None
        return OSError("post-publication temp cleanup failed")

    monkeypatch.setattr(
        release_package, "_cleanup_temporary_outputs", cleanup_then_fail
    )

    with pytest.raises(OSError, match="post-publication temp cleanup failed"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not digest_file.exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_temp_cleanup_failure_rollback_preserves_foreign_replacement_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    digest_file = destination.with_name(destination.name + ".sha256")
    real_cleanup = release_package._cleanup_temporary_outputs

    def cleanup_replace_then_fail(descriptors, paths):
        assert real_cleanup(descriptors, paths) is None
        destination.unlink()
        destination.write_bytes(b"keep foreign archive")
        digest_file.unlink()
        digest_file.write_text("keep foreign digest\n", encoding="ascii")
        return OSError("post-publication temp cleanup failed")

    monkeypatch.setattr(
        release_package, "_cleanup_temporary_outputs", cleanup_replace_then_fail
    )

    with pytest.raises(OSError, match="post-publication temp cleanup failed"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert destination.read_bytes() == b"keep foreign archive"
    assert digest_file.read_text(encoding="ascii") == "keep foreign digest\n"
    assert list(tmp_path.glob(".*.tmp")) == []
