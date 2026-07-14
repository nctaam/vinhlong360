from __future__ import annotations

import importlib.util
import builtins
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("backup_data", ROOT / "scripts" / "backup_data.py")
backup_data = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = backup_data
SPEC.loader.exec_module(backup_data)


def test_count_data_json_valid(tmp_path: Path) -> None:
    data = {"entities": [1, 2], "relationships": [3], "itineraries": []}
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    result = backup_data._count_data_json(p)
    assert result == {"entities": 2, "relationships": 1, "itineraries": 0}


def test_count_data_json_missing_keys(tmp_path: Path) -> None:
    p = tmp_path / "data.json"
    p.write_text("{}", encoding="utf-8")
    result = backup_data._count_data_json(p)
    assert result == {"entities": 0, "relationships": 0, "itineraries": 0}


def test_count_data_json_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    result = backup_data._count_data_json(p)
    assert "error" in result


def test_file_size_human() -> None:
    assert "B" in backup_data._file_size_human(Path(__file__))


def test_main_creates_backup(tmp_path: Path, monkeypatch) -> None:
    data_json = tmp_path / "web" / "data.json"
    data_json.parent.mkdir(parents=True)
    data_json.write_text(json.dumps({"entities": [{"id": "x"}], "relationships": [], "itineraries": []}))

    backup_root = tmp_path / "backups"

    monkeypatch.setattr(backup_data, "DATA_JSON", data_json)
    monkeypatch.setattr(backup_data, "DB_FILE", tmp_path / "nonexistent.db")
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr("sys.argv", ["backup_data.py"])

    rc = backup_data.main()
    assert rc == 0
    assert backup_root.exists()

    dirs = list(backup_root.iterdir())
    assert len(dirs) == 1

    manifest = json.loads((dirs[0] / "manifest.json").read_text(encoding="utf-8"))
    assert "web/data.json" in manifest["copied"]
    assert manifest["counts"]["entities"] == 1
    assert "data.json" in manifest["sizes"]
    assert (dirs[0] / "data.json").exists()


def test_main_uses_sqlite_backup_api_for_consistent_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_file = tmp_path / "test.db"
    source = sqlite3.connect(db_file)
    source.execute("PRAGMA journal_mode=WAL")
    source.execute("CREATE TABLE entities (id TEXT PRIMARY KEY, published INTEGER)")
    source.execute("INSERT INTO entities VALUES ('entity-1', 1)")
    source.commit()

    real_copy2 = backup_data.shutil.copy2

    def guarded_copy2(source_path, destination_path):
        assert Path(source_path) != db_file, "live SQLite files must use Connection.backup()"
        return real_copy2(source_path, destination_path)

    monkeypatch.setattr(backup_data, "DATA_JSON", tmp_path / "missing.json")
    monkeypatch.setattr(backup_data, "DB_FILE", db_file)
    monkeypatch.setattr(backup_data.shutil, "copy2", guarded_copy2)
    monkeypatch.setattr(
        "sys.argv",
        ["backup_data.py", "--target", "local", "--out-dir", str(tmp_path / "backups")],
    )

    try:
        rc = backup_data.main()
    finally:
        source.close()

    assert rc == 0
    dirs = list((tmp_path / "backups").iterdir())
    manifest = json.loads((dirs[0] / "manifest.json").read_text(encoding="utf-8"))
    assert "agent/data/vinhlong360.db" in manifest["copied"]
    artifact = dirs[0] / "vinhlong360.db"
    with sqlite3.connect(artifact) as connection:
        assert connection.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert connection.execute("SELECT id, published FROM entities").fetchall() == [
            ("entity-1", 1)
        ]


def test_local_target_does_not_import_or_call_postgresql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_json = tmp_path / "data.json"
    data_json.write_text(json.dumps({"entities": [], "relationships": [], "itineraries": []}))
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "psycopg2":
            raise AssertionError("local backups must not import psycopg2")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(backup_data, "DATA_JSON", data_json)
    monkeypatch.setattr(backup_data, "DB_FILE", tmp_path / "missing.db")
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(
        "sys.argv",
        ["backup_data.py", "--target", "local", "--out-dir", str(tmp_path / "backups")],
    )

    assert backup_data.main() == 0


def test_local_backup_removes_only_empty_sidecars_it_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_file = tmp_path / "wal-source.db"
    connection = sqlite3.connect(db_file)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE entities (id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO entities VALUES ('entity-1')")
        connection.commit()
    finally:
        connection.close()
    wal_path = Path(f"{db_file}-wal")
    shm_path = Path(f"{db_file}-shm")
    assert not wal_path.exists()
    assert not shm_path.exists()

    monkeypatch.setattr(backup_data, "DATA_JSON", tmp_path / "missing.json")
    monkeypatch.setattr(backup_data, "DB_FILE", db_file)
    monkeypatch.setattr(
        "sys.argv",
        ["backup_data.py", "--target", "local", "--out-dir", str(tmp_path / "backups")],
    )

    assert backup_data.main() == 0
    assert not wal_path.exists()
    assert not shm_path.exists()


def test_main_returns_1_when_nothing_to_backup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(backup_data, "DATA_JSON", tmp_path / "nope.json")
    monkeypatch.setattr(backup_data, "DB_FILE", tmp_path / "nope.db")
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", tmp_path / "backups")
    monkeypatch.setattr("sys.argv", ["backup_data.py"])

    rc = backup_data.main()
    assert rc == 1


def test_cleanup_removes_old_backups(tmp_path: Path, monkeypatch) -> None:
    backup_root = tmp_path / "backups"
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", backup_root)

    for i in range(8):
        d = backup_root / f"backup-{i:02d}"
        d.mkdir(parents=True)
        old_time = time.time() - (40 + i) * 86400
        os.utime(d, (old_time, old_time))

    newest = backup_root / "backup-newest"
    newest.mkdir(parents=True)

    backup_data._cleanup_old_backups(keep=3, max_age_days=30)

    remaining = list(backup_root.iterdir())
    assert len(remaining) <= 3 + 1


def test_cleanup_keeps_minimum(tmp_path: Path, monkeypatch) -> None:
    backup_root = tmp_path / "backups"
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", backup_root)

    for i in range(3):
        d = backup_root / f"backup-{i}"
        d.mkdir(parents=True)

    backup_data._cleanup_old_backups(keep=5, max_age_days=1)
    assert len(list(backup_root.iterdir())) == 3


class FakeRunner:
    def __init__(self, *, listing: str | None = None, dump_returncode: int = 0) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.listing = listing or (
            "1; 0 0 TABLE public entities postgres\n"
            "2; 0 0 TABLE public entity_changes postgres\n"
        )
        self.dump_returncode = dump_returncode

    def __call__(self, args, **kwargs):
        command = [str(value) for value in args]
        self.calls.append((command, kwargs))
        if command[:2] == ["pg_dump", "--version"]:
            return subprocess.CompletedProcess(command, 0, "16.4\n", "")
        if command[:2] == ["pg_restore", "--version"]:
            return subprocess.CompletedProcess(command, 0, "16.4\n", "")
        if command[0] == "pg_dump":
            if self.dump_returncode == 0:
                artifact = Path(command[command.index("--file") + 1])
                artifact.write_bytes(b"PGDMP-test")
            return subprocess.CompletedProcess(command, self.dump_returncode, "", "dump failed")
        if command[:2] == ["pg_restore", "--list"]:
            return subprocess.CompletedProcess(command, 0, self.listing, "")
        raise AssertionError(f"unexpected command: {command}")


def _identity() -> dict[str, object]:
    return {
        "database": "vl360",
        "server_addr": "10.0.0.8",
        "server_port": 5432,
        "server_version_num": 160004,
    }


def _clock():
    values = iter(
        [
            datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
            datetime(2026, 7, 14, 12, 1, tzinfo=UTC),
        ]
    )
    return lambda: next(values)


def test_create_postgres_backup_writes_validated_secret_free_manifest(
    tmp_path: Path,
) -> None:
    secret = "backup-secret"
    database_url = f"postgresql://backup:{secret}@db.example:5433/vl360?sslmode=require"
    destination = tmp_path / "pg-backup"
    runner = FakeRunner()

    result = backup_data.create_postgres_backup(
        database_url=database_url,
        destination=destination,
        identity=_identity(),
        runner=runner,
        now=_clock(),
    )

    assert result == destination
    manifest_bytes = (destination / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest["schema"] == "vinhlong360-pg-backup-v1"
    assert manifest["target"] == "pg"
    assert manifest["database_identity"] == _identity()
    assert len(manifest["target_fingerprint"]) == 64
    assert manifest["started_at"] == "2026-07-14T12:00:00Z"
    assert manifest["completed_at"] == "2026-07-14T12:01:00Z"
    assert manifest["max_age_seconds"] == 3600
    assert manifest["tools"] == {"pg_dump": "16.4", "pg_restore": "16.4"}
    assert manifest["artifact"] == {
        "path": "postgres.dump",
        "size": len(b"PGDMP-test"),
        "sha256": hashlib.sha256(b"PGDMP-test").hexdigest(),
    }
    listing = runner.listing.encode()
    assert manifest["validation"] == {
        "pg_restore_list": True,
        "required_tables": ["entities", "entity_changes"],
        "listing_sha256": hashlib.sha256(listing).hexdigest(),
    }
    assert manifest["policy_revision"] == "published-v1"
    assert secret.encode() not in manifest_bytes
    assert all(secret not in " ".join(command) for command, _ in runner.calls)
    dump_call = next(call for call in runner.calls if call[0][0] == "pg_dump" and "--file" in call[0])
    assert dump_call[1]["env"]["PGPASSWORD"] == secret
    assert dump_call[1]["env"]["PGSSLMODE"] == "require"


def test_create_postgres_backup_rejects_missing_required_table_without_manifest(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "pg-backup"
    runner = FakeRunner(listing="1; 0 0 TABLE public entities postgres\n")

    with pytest.raises(RuntimeError, match="entity_changes"):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=_identity(),
            runner=runner,
            now=_clock(),
        )

    assert not (destination / "manifest.json").exists()


def test_create_postgres_backup_does_not_claim_success_when_pg_dump_fails(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "pg-backup"

    with pytest.raises(RuntimeError, match="pg_dump"):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=_identity(),
            runner=FakeRunner(dump_returncode=1),
            now=_clock(),
        )

    assert not (destination / "manifest.json").exists()
