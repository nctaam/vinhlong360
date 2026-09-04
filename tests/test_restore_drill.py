from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.backup_manifest import BackupManifest, RestoreReport, find_latest_manifest, validate_manifest_artifact
from scripts.restore_drill import restore_backup, _find_latest_dump, _run_restore


def test_backup_manifest_round_trips_required_integrity_fields() -> None:
    manifest = BackupManifest(
        artifact_id="pg-20260902-120000",
        format="postgres.custom",
        source_identity={"database": "vinhlong360", "system_identifier": "42"},
        row_counts={"entities": 3, "relationships": 2},
        checksum="a" * 64,
        created_at="2026-09-02T12:00:00Z",
    )

    restored = BackupManifest.from_dict(manifest.to_dict())

    assert restored == manifest


def test_validate_manifest_artifact_rejects_checksum_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "backup.dump"
    artifact.write_bytes(b"known-good")
    manifest = BackupManifest(
        artifact_id="a1",
        format="postgres.custom",
        source_identity={"database": "vinhlong360"},
        row_counts={"entities": 1},
        checksum="b" * 64,
        created_at="2026-09-02T12:00:00Z",
    )

    with pytest.raises(ValueError, match="checksum"):
        validate_manifest_artifact(manifest, artifact)


def test_restore_backup_validates_identity_and_row_counts_before_restore(tmp_path: Path) -> None:
    artifact = tmp_path / "backup.dump"
    artifact.write_bytes(b"known-good")
    from scripts.backup_manifest import sha256_file

    manifest = BackupManifest(
        artifact_id="a1",
        format="postgres.custom",
        source_identity={"database": "vinhlong360"},
        row_counts={"entities": 2},
        checksum=sha256_file(artifact),
        created_at="2026-09-02T12:00:00Z",
    )

    calls: list[str] = []

    class Target:
        def preflight(self, **kwargs):
            return {"entities": 1}

        def __call__(self, **kwargs):
            calls.append("restore")
            return {"entities": 1}

    with pytest.raises(ValueError, match="row count"):
        restore_backup(manifest, Target(), artifact=artifact)
    assert calls == []


def test_restore_backup_returns_evidence_report(tmp_path: Path) -> None:
    artifact = tmp_path / "backup.dump"
    artifact.write_bytes(b"known-good")
    from scripts.backup_manifest import sha256_file

    manifest = BackupManifest(
        artifact_id="a1",
        format="postgres.custom",
        source_identity={"database": "vinhlong360"},
        row_counts={"entities": 2},
        checksum=sha256_file(artifact),
        created_at="2026-09-02T12:00:00Z",
    )

    report = restore_backup(
        manifest,
        lambda **kwargs: {"entities": 2},
        artifact=artifact,
    )

    assert isinstance(report, RestoreReport)
    assert report.success is True
    assert report.artifact_id == "a1"
    assert report.row_counts == {"entities": 2}


def test_sidecar_manifest_discovers_sql_gzip_and_rejects_tamper(tmp_path: Path) -> None:
    artifact = tmp_path / "db-daily-20260902.sql.gz"
    artifact.write_bytes(b"sql dump")
    from scripts.backup_manifest import sha256_file

    payload = {
        "schema": "vinhlong360-backup-manifest-v2",
        "artifact_id": artifact.name,
        "format": "postgres.sql.gz",
        "source_identity": {"target": "pg"},
        "row_counts": {},
        "checksum": sha256_file(artifact),
        "created_at": "2026-09-02T12:00:00Z",
        "artifact": {"path": artifact.name},
    }
    sidecar = artifact.with_name(artifact.name + ".manifest.json")
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    assert find_latest_manifest(tmp_path) is not None
    artifact.write_bytes(b"tampered")
    assert find_latest_manifest(tmp_path) is None


def test_manifest_requires_declared_artifact_and_rejects_path_traversal(tmp_path: Path) -> None:
    artifact = tmp_path / "backup.dump"
    artifact.write_bytes(b"known-good")
    from scripts.backup_manifest import sha256_file

    base = {
        "schema": "vinhlong360-backup-manifest-v2",
        "artifact_id": "a1", "format": "postgres.custom",
        "source_identity": {}, "row_counts": {}, "checksum": sha256_file(artifact),
        "created_at": "2026-09-02T12:00:00Z",
    }
    (tmp_path / "manifest.json").write_text(json.dumps(base), encoding="utf-8")
    assert find_latest_manifest(tmp_path) is None
    base["artifact"] = {"path": "../backup.dump"}
    (tmp_path / "manifest.json").write_text(json.dumps(base), encoding="utf-8")
    assert find_latest_manifest(tmp_path) is None


def test_sql_gzip_restore_uses_psql_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "backup.sql.gz"
    import gzip
    with gzip.open(artifact, "wb") as stream:
        stream.write(b"CREATE TABLE entities(id text);")
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("scripts.restore_drill.shutil.which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr("scripts.restore_drill.subprocess.run", lambda args, **kwargs: calls.append(list(args)) or Result())
    _run_restore("postgresql://u:p@localhost/db", "restore_db", artifact)
    assert calls and calls[0][0].endswith("psql")
    assert "--dbname" in calls[0]


def test_find_latest_dump_returns_none_for_missing_directory(tmp_path: Path) -> None:
    assert _find_latest_dump(tmp_path / "missing") is None


def test_find_latest_dump_ignores_valid_non_postgres_manifest(tmp_path: Path) -> None:
    artifact = tmp_path / "local.json"
    artifact.write_bytes(b"local snapshot")
    from scripts.backup_manifest import sha256_file

    payload = {
        "schema": "vinhlong360-local-backup-v1",
        "artifact_id": "local-1",
        "format": "json+sqlite",
        "source_identity": {"target": "local"},
        "row_counts": {},
        "checksum": sha256_file(artifact),
        "created_at": "2026-09-02T12:00:00Z",
        "artifact": {"path": artifact.name},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    assert _find_latest_dump(tmp_path) is None


def test_find_latest_dump_prefers_declared_postgres_manifest_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "postgres.dump"
    artifact.write_bytes(b"postgres dump")
    from scripts.backup_manifest import sha256_file

    payload = {
        "schema": "vinhlong360-backup-manifest-v2",
        "artifact_id": "pg-1",
        "format": "postgres.custom",
        "source_identity": {"target": "pg"},
        "row_counts": {},
        "checksum": sha256_file(artifact),
        "created_at": "2026-09-02T12:00:00Z",
        "artifact": {"path": artifact.name},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

    assert _find_latest_dump(tmp_path) == artifact


def test_find_latest_dump_uses_newest_legacy_dump(tmp_path: Path) -> None:
    older = tmp_path / "db-pre-deploy-20260901.dump"
    newer = tmp_path / "db-pre-deploy-20260902.dump"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    os.utime(newer, (older.stat().st_atime, older.stat().st_mtime + 2))

    assert _find_latest_dump(tmp_path) == newer
