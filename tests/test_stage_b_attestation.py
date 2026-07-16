from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import migrate_entity_status as migration
from scripts import postgres_target
from scripts import stage_b_attestation


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = {
    "identity_revision": "postgres-cluster-v2",
    "database": "vl360",
    "database_oid": 16384,
    "system_identifier": "7463376938976342231",
    "server_addr": "127.0.0.1/32",
    "server_port": 5432,
    "server_version_num": 160004,
}
REVISION = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT,
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
NOW = datetime.now(UTC).replace(microsecond=0)
REAL_ACL_HELPER = stage_b_attestation.run_acl_helper
ACL_SUMMARY_BY_ROOT: dict[Path, dict[str, object]] = {}


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _dotnet_utc_text(value: datetime) -> str:
    utc = value.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond:06d}7Z"


def _restore_listing() -> bytes:
    return (
        b"1; 2615 2200 TABLE public entities postgres\n"
        b"2; 2615 2201 TABLE public entity_changes postgres\n"
    )


def _populate_artifacts(root: Path) -> str:
    run = root / "backup" / "20260715-230716"
    run.mkdir(parents=True)
    dump = b"synthetic postgres dump bytes\n"
    listing = _restore_listing()
    listing_sha = hashlib.sha256(listing).hexdigest()
    plan = _plan(IDENTITY, listing_sha)
    plan.pop("_listing_sha256_unused")
    manifest = _manifest(IDENTITY, dump, listing_sha)
    (root / "published-v1-plan.json").write_bytes(
        postgres_target.canonical_json_bytes(plan)
    )
    (root / "pg-restore-list.txt").write_bytes(listing)
    (run / "postgres.dump").write_bytes(dump)
    (run / "manifest.json").write_bytes(postgres_target.canonical_json_bytes(manifest))
    return listing_sha


def _plan(identity: dict[str, object], listing_sha256: str) -> dict[str, object]:
    target = postgres_target.target_fingerprint(identity)
    columns = [
        {"name": "attributes", "type": "jsonb", "nullable": "YES"},
        {"name": "id", "type": "text", "nullable": "NO"},
        {"name": "source", "type": "text", "nullable": "YES"},
        {"name": "status", "type": "text", "nullable": "YES"},
        {"name": "type", "type": "text", "nullable": "NO"},
        {"name": "verified", "type": "boolean", "nullable": "NO"},
    ]
    return {
        "schema": migration.PLAN_SCHEMA,
        "policy_revision": "published-v1",
        "created_at": _utc_text(NOW),
        "max_age_seconds": migration.MAX_PLAN_AGE_SECONDS,
        "tool_source_revision": REVISION,
        "target_fingerprint": target,
        "database_identity": dict(identity),
        "schema_fingerprint": postgres_target.sha256_bytes(
            postgres_target.canonical_json_bytes(columns)
        ),
        "schema_columns": columns,
        "candidate_ids": ["entity-1"],
        "candidate_count": 1,
        "candidate_sha256": postgres_target.sha256_bytes(
            postgres_target.canonical_json_bytes(["entity-1"])
        ),
        "reviewed_exclusions": sorted(migration.PUBLISHED_V1_EXCLUSIONS),
        "exclusion_counts": {},
        "status_groups": {"<null>": 1},
        "expected_before": {"published": 0, "null": 1},
        "expected_after": {"published": 1, "null": 0},
        "_listing_sha256_unused": listing_sha256,
    }


def _manifest(
    identity: dict[str, object], dump: bytes, listing_sha256: str
) -> dict[str, object]:
    target = postgres_target.target_fingerprint(identity)
    return {
        "schema": "vinhlong360-pg-backup-v1",
        "target": "pg",
        "target_fingerprint": target,
        "database_identity": dict(identity),
        "started_at": _utc_text(NOW),
        "completed_at": _utc_text(NOW),
        "max_age_seconds": migration.MAX_BACKUP_AGE_SECONDS,
        "tools": {
            "pg_dump": "pg_dump (PostgreSQL) 16",
            "pg_restore": "pg_restore (PostgreSQL) 16",
        },
        "artifact": {
            "path": "postgres.dump",
            "size": len(dump),
            "sha256": hashlib.sha256(dump).hexdigest(),
        },
        "validation": {
            "pg_restore_list": True,
            "required_tables": ["entities", "entity_changes"],
            "listing_sha256": listing_sha256,
        },
        "policy_revision": "published-v1",
    }


@pytest.fixture()
def stage_b_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "stage-b"
    root.mkdir()
    listing_sha = _populate_artifacts(root)
    monkeypatch.setattr(
        stage_b_attestation,
        "validate_restore_artifact",
        lambda _path: listing_sha,
    )
    acl_checked_at = _dotnet_utc_text(datetime.now(UTC))

    def fake_acl(mode: str, checked_root: Path) -> dict[str, object]:
        object_count = (
            8 if os.path.lexists(checked_root / "stage-b-attestation.json") else 6
        )
        summary = {
            "checked_at": acl_checked_at,
            "allowed_principals": [
                "DESKTOP\\Administrator",
                "NT AUTHORITY\\SYSTEM",
                "BUILTIN\\Administrators",
            ],
            "object_count": object_count,
            "protected_object_count": object_count,
            "unexpected_principals": [],
            "inherited_rule_count": 0,
            "reparse_point_count": 0,
            "alternate_data_stream_count": 0,
        }
        if mode == "NormalizeAndVerify":
            ACL_SUMMARY_BY_ROOT[checked_root] = dict(summary)
        return summary

    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", fake_acl)
    monkeypatch.setattr(
        stage_b_attestation,
        "git_state",
        lambda _root: {"head": REVISION, "worktree_clean": True},
    )
    return root


@pytest.fixture()
def secure_stage_b_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    if os.name != "nt":
        pytest.skip("Windows ACL contract")
    root = tmp_path / "secure-stage-b"
    completed = subprocess.run(
        [
            "pwsh",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(ROOT / "scripts" / "secure_stage_b_artifacts.ps1"),
            "-Mode",
            "CreateRoot",
            "-Root",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(f"Windows ACL helper unavailable: {completed.stderr}")
    listing_sha = _populate_artifacts(root)
    normalized = subprocess.run(
        [
            "pwsh",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(ROOT / "scripts" / "secure_stage_b_artifacts.ps1"),
            "-Mode",
            "NormalizeAndVerify",
            "-Root",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if normalized.returncode != 0:
        pytest.skip(f"Windows ACL normalization unavailable: {normalized.stderr}")
    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", REAL_ACL_HELPER)
    monkeypatch.setattr(
        stage_b_attestation, "validate_restore_artifact", lambda _path: listing_sha
    )
    monkeypatch.setattr(
        stage_b_attestation,
        "git_state",
        lambda _root: {"head": REVISION, "worktree_clean": True},
    )
    return root


@pytest.fixture()
def evidence() -> dict[str, object]:
    return {
        "source": {"head": REVISION, "worktree_clean": True},
        "noindex": {
            "url": "https://vinhlong360.vn/",
            "checked_at": _utc_text(NOW),
            "status": 200,
            "x_robots_tag": "noindex, follow",
            "robots_meta_count": 1,
            "robots_meta_value": "noindex, follow",
            "body_sha256": "a" * 64,
        },
        "temporary_role": {
            "name": "vl360_stage_b_0123456789abcdef0123456789abcdef",
            "expires_at": _utc_text(NOW + timedelta(hours=2)),
            "role_absent": True,
            "absent_checked_at": _utc_text(NOW),
        },
        "tunnel": {
            "endpoint": "127.0.0.1:15432",
            "pid": 7712,
            "process_absent": True,
            "listener_absent": True,
            "absent_checked_at": _utc_text(NOW),
        },
        "operations": {
            "apply_run": False,
            "rollback_run": False,
            "export_run": False,
            "deploy_run": False,
        },
    }


def _run_attestation(
    root: Path,
    output: Path,
    evidence: dict[str, object],
) -> subprocess.CompletedProcess[str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        returncode = stage_b_attestation.main(
            ["--artifact-root", str(root), "--out", str(output)],
            stdin=io.StringIO(json.dumps(evidence)),
        )
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def _run_raw_attestation(
    root: Path,
    output: Path,
    raw: str,
) -> subprocess.CompletedProcess[str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        returncode = stage_b_attestation.main(
            ["--artifact-root", str(root), "--out", str(output)],
            stdin=io.StringIO(raw),
        )
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def test_attestation_writer_validates_and_writes_canonical_secret_free_evidence(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert set(document) == {
        "schema",
        "attestation_revision",
        "generated_at",
        "source",
        "artifacts",
        "target",
        "noindex",
        "temporary_role",
        "tunnel",
        "acl",
        "operations",
    }
    assert document["schema"] == "vinhlong360-stage-b-attestation-v1"
    assert document["attestation_revision"] == "postgres-identity-v2"
    assert document["target"]["database_identity"] == IDENTITY
    assert document["target"][
        "target_fingerprint"
    ] == postgres_target.target_fingerprint(IDENTITY)
    assert document["temporary_role"]["role_absent"] is True
    assert document["tunnel"]["process_absent"] is True
    assert document["tunnel"]["listener_absent"] is True
    assert document["operations"] == {
        "apply_run": False,
        "rollback_run": False,
        "export_run": False,
        "deploy_run": False,
    }
    assert document["acl"] == ACL_SUMMARY_BY_ROOT[stage_b_root]
    assert document["acl"]["checked_at"].endswith("7Z")
    assert output.read_bytes() == postgres_target.canonical_json_bytes(document)
    assert "entity-1" not in output.read_text(encoding="utf-8")
    pending = list(stage_b_root.glob(".pending-write-*"))
    assert len(pending) == 1
    assert os.stat(pending[0]).st_ino == os.stat(output).st_ino
    assert json.loads(result.stdout) == {
        "attestation_path": str(output),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda e: e["noindex"].update(x_robots_tag="index, follow"), "noindex"),
        (lambda e: e["noindex"].update(status=503), "noindex"),
        (lambda e: e["noindex"].update(robots_meta_count=0), "robots meta"),
        (
            lambda e: e["noindex"].update(robots_meta_value="index, follow"),
            "robots meta",
        ),
        (lambda e: e["temporary_role"].update(role_absent=False), "role cleanup"),
        (lambda e: e["tunnel"].update(process_absent=False), "tunnel cleanup"),
        (lambda e: e["tunnel"].update(listener_absent=False), "tunnel cleanup"),
        (lambda e: e["operations"].update(apply_run=True), "operation flags"),
        (lambda e: e["operations"].update(rollback_run=True), "operation flags"),
        (lambda e: e["operations"].update(export_run=True), "operation flags"),
        (lambda e: e["operations"].update(deploy_run=True), "operation flags"),
        (lambda e: e.update(database_url="postgresql://secret"), "secret field"),
    ],
)
def test_attestation_refuses_failed_gate_without_output(
    stage_b_root: Path,
    evidence: dict[str, object],
    mutation,
    message: str,
) -> None:
    mutation(evidence)
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert message.lower() in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda root: _mutate_json(
            root / "published-v1-plan.json",
            {"database_identity": {**IDENTITY, "database_oid": 16385}},
        ),
        lambda root: _mutate_json(
            root / "backup" / "20260715-230716" / "manifest.json",
            {"database_identity": {**IDENTITY, "database_oid": 16385}},
        ),
        lambda root: (
            root / "backup" / "20260715-230716" / "postgres.dump"
        ).write_bytes(b"drift"),
        lambda root: (root / "pg-restore-list.txt").write_bytes(b"drift\n"),
    ],
)
def test_attestation_refuses_artifact_drift_without_output(
    stage_b_root: Path, evidence: dict[str, object], mutate
) -> None:
    mutate(stage_b_root)
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_manifest_bound_to_identical_sibling_dump(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    run = stage_b_root / "backup" / "20260715-230716"
    dump = run / "postgres.dump"
    (run / "other.dump").write_bytes(dump.read_bytes())
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact"]["path"] = "other.dump"
    manifest_path.write_bytes(postgres_target.canonical_json_bytes(manifest))

    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "artifact path" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_nonempty_hardlinks_before_acl_normalization(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acl_modes: list[str] = []
    original_acl = stage_b_attestation.run_acl_helper
    original_link = stage_b_attestation.os.link

    def record_acl(mode: str, root: Path) -> dict[str, object]:
        acl_modes.append(mode)
        return original_acl(mode, root)

    def link_then_write(
        source: os.PathLike[str] | str,
        destination: os.PathLike[str] | str,
        *,
        follow_symlinks: bool = True,
    ) -> None:
        original_link(source, destination, follow_symlinks=follow_symlinks)
        Path(source).write_bytes(b"x")

    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", record_acl)
    monkeypatch.setattr(stage_b_attestation.os, "link", link_then_write)
    output = stage_b_root / "stage-b-attestation.json"

    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "empty" in result.stderr.lower()
    assert acl_modes == ["Verify"]
    pending = list(stage_b_root.glob(".pending-write-*"))
    assert len(pending) == 1
    assert pending[0].read_bytes() == b"x"
    assert output.read_bytes() == b"x"


def test_attestation_refuses_extra_acl_summary_key_before_allocation(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_acl = stage_b_attestation.run_acl_helper

    def acl_with_extra(mode: str, root: Path) -> dict[str, object]:
        summary = original_acl(mode, root)
        summary["unexpected_extra"] = True
        return summary

    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", acl_with_extra)
    output = stage_b_root / "stage-b-attestation.json"

    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "acl evidence fields" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_final_output_mutation_after_acl_verify(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_acl = stage_b_attestation.run_acl_helper
    output = stage_b_root / "stage-b-attestation.json"

    def mutate_final(mode: str, root: Path) -> dict[str, object]:
        summary = original_acl(mode, root)
        if mode == "Verify" and output.exists():
            output.write_bytes(b"X")
        return summary

    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", mutate_final)
    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "hash" in result.stderr.lower() or "canonical" in result.stderr.lower()
    assert output.read_bytes() == b"X"
    pending = list(stage_b_root.glob(".pending-write-*"))
    assert len(pending) == 1
    assert pending[0].read_bytes() == b"X"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda root: _mutate_json(
            root / "published-v1-plan.json", {"candidate_count": 2}
        ),
        lambda root: _mutate_json(
            root / "backup" / "20260715-230716" / "manifest.json",
            {"completed_at": "2026-07-16T05:00:00Z"},
        ),
        lambda root: (
            root / "backup" / "20260715-230716" / "postgres.dump"
        ).write_bytes(b"drift"),
        lambda root: (root / "pg-restore-list.txt").write_bytes(b"drift\n"),
    ],
)
def test_attestation_refuses_artifact_drift_after_normalization(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    mutate,
) -> None:
    original_acl = stage_b_attestation.run_acl_helper

    def mutate_on_normalize(mode: str, root: Path) -> dict[str, object]:
        summary = original_acl(mode, root)
        if mode == "NormalizeAndVerify":
            mutate(root)
        return summary

    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", mutate_on_normalize)
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "artifact" in result.stderr.lower() or "canonical" in result.stderr.lower()


def test_attestation_refuses_acl_evidence_for_wrong_root(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original_acl = stage_b_attestation.run_acl_helper
    wrong_root = tmp_path / "wrong-root"

    def wrong_root_acl(mode: str, root: Path) -> dict[str, object]:
        summary = original_acl(mode, root)
        summary["root"] = str(wrong_root.absolute())
        return summary

    monkeypatch.setattr(stage_b_attestation, "run_acl_helper", wrong_root_acl)
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "root" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_freshness_expiring_during_validation(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = datetime.now(UTC)
    clock_values = iter(
        [
            base + timedelta(seconds=1),
            base + timedelta(seconds=1),
            base + timedelta(seconds=302),
        ]
    )
    monkeypatch.setattr(stage_b_attestation, "_utc_now", lambda: next(clock_values))
    output = stage_b_root / "stage-b-attestation.json"

    result = _run_attestation(stage_b_root, output, evidence)

    assert result.returncode != 0
    assert "stale" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def _mutate_json(path: Path, updates: dict[str, object]) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    value.update(updates)
    path.write_bytes(postgres_target.canonical_json_bytes(value))


def test_attestation_refuses_evidenced_source_head_drift(
    stage_b_root: Path,
    evidence: dict[str, object],
) -> None:
    evidence["source"]["head"] = "0" * 40
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "source" in result.stderr.lower() or "worktree" in result.stderr.lower()
    assert not output.exists()


def test_attestation_refuses_real_dirty_worktree(
    stage_b_root: Path,
    evidence: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stage_b_attestation,
        "git_state",
        lambda _root: {"head": REVISION, "worktree_clean": False},
    )
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "worktree" in result.stderr.lower()
    assert not output.exists()


def test_attestation_refuses_plan_source_revision_drift(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    _mutate_json(
        stage_b_root / "published-v1-plan.json",
        {"tool_source_revision": "0" * 40},
    )
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "source revision" in result.stderr.lower()
    assert not output.exists()


def test_attestation_refuses_stale_timestamp_without_output(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    evidence["noindex"]["checked_at"] = _utc_text(NOW - timedelta(seconds=301))
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "stale" in result.stderr.lower() or "fresh" in result.stderr.lower()
    assert not output.exists()


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("temporary_role", "absent_checked_at"),
        ("tunnel", "absent_checked_at"),
    ],
)
def test_attestation_refuses_stale_cleanup_timestamp_without_output(
    stage_b_root: Path,
    evidence: dict[str, object],
    section: str,
    field: str,
) -> None:
    evidence[section][field] = _utc_text(NOW - timedelta(seconds=301))
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "stale" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


@pytest.mark.parametrize(
    "raw",
    ["{", json.dumps("not-an-object"), "{} {}"],
)
def test_attestation_refuses_malformed_stdin_without_output(
    stage_b_root: Path, raw: str
) -> None:
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_raw_attestation(stage_b_root, output, raw)
    assert result.returncode != 0
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_oversize_stdin_without_output(
    stage_b_root: Path,
) -> None:
    output = stage_b_root / "stage-b-attestation.json"
    raw = '{"source":"' + ("x" * (1024 * 1024)) + '"}'
    result = _run_raw_attestation(stage_b_root, output, raw)
    assert result.returncode != 0
    assert "1 mib" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_noncanonical_root_json_before_output(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    plan = stage_b_root / "published-v1-plan.json"
    plan.write_text(
        json.dumps(json.loads(plan.read_text()), indent=2), encoding="utf-8"
    )
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "canonical" in result.stderr.lower()
    assert not output.exists()


def test_secret_value_marker_is_rejected_without_echoing_secret(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    secret = "postgresql://user:super-secret@db/vl360"
    evidence["noindex"]["body_sha256"] = secret
    output = stage_b_root / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "secret" in result.stderr.lower()
    assert secret not in result.stderr
    assert not output.exists()


def test_attestation_refuses_output_outside_root_before_allocation(
    stage_b_root: Path, evidence: dict[str, object], tmp_path: Path
) -> None:
    output = tmp_path / "outside-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "escapes" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def test_attestation_refuses_nested_output_before_allocation(
    stage_b_root: Path, evidence: dict[str, object]
) -> None:
    nested = stage_b_root / "nested"
    nested.mkdir()
    output = nested / "stage-b-attestation.json"
    result = _run_attestation(stage_b_root, output, evidence)
    assert result.returncode != 0
    assert "directly under" in result.stderr.lower()
    assert not output.exists()
    assert not list(stage_b_root.glob(".pending-write-*"))


def _grant_read_rule(path: Path, principal: str) -> None:
    command = r"""
$ErrorActionPreference = 'Stop'
$acl = Get-Acl -LiteralPath $env:ACL_TEST_PATH
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    $env:ACL_TEST_PRINCIPAL,
    [System.Security.AccessControl.FileSystemRights]::Read,
    [System.Security.AccessControl.AccessControlType]::Allow
)
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $env:ACL_TEST_PATH -AclObject $acl
"""
    env = os.environ.copy()
    env["ACL_TEST_PATH"] = str(path)
    env["ACL_TEST_PRINCIPAL"] = principal
    completed = subprocess.run(
        ["pwsh", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr


def _assert_real_acl_refusal_without_attestation(
    root: Path, evidence: dict[str, object]
) -> None:
    output = root / "stage-b-attestation.json"
    result = _run_attestation(root, output, evidence)
    assert result.returncode != 0
    assert "acl" in result.stderr.lower()
    assert not output.exists()
    assert not list(root.glob(".pending-write-*"))


def test_attestation_real_acl_verify_rejects_unexpected_principal_before_allocation(
    secure_stage_b_root: Path, evidence: dict[str, object]
) -> None:
    _grant_read_rule(secure_stage_b_root / "published-v1-plan.json", r"BUILTIN\Users")

    _assert_real_acl_refusal_without_attestation(secure_stage_b_root, evidence)


def test_attestation_real_acl_verify_rejects_reparse_point_before_allocation(
    secure_stage_b_root: Path, evidence: dict[str, object], tmp_path: Path
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = secure_stage_b_root / "hostile-link.txt"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Windows symlink creation unavailable: {exc}")

    _assert_real_acl_refusal_without_attestation(secure_stage_b_root, evidence)


def test_attestation_real_acl_verify_rejects_ads_before_allocation(
    secure_stage_b_root: Path, evidence: dict[str, object]
) -> None:
    plan = secure_stage_b_root / "published-v1-plan.json"
    try:
        with open(f"{plan}:hostile", "w", encoding="utf-8") as stream:
            stream.write("hidden")
    except OSError as exc:
        pytest.skip(f"Named alternate streams unavailable: {exc}")

    _assert_real_acl_refusal_without_attestation(secure_stage_b_root, evidence)
