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
        backup_data,
        "resolve_database_url",
        lambda *_args, **_kwargs: pytest.fail("local backup resolved PostgreSQL URL"),
    )
    monkeypatch.setattr(
        backup_data,
        "_read_postgres_identity",
        lambda *_args, **_kwargs: pytest.fail("local backup read PostgreSQL identity"),
    )
    monkeypatch.setattr(
        backup_data,
        "create_postgres_backup",
        lambda *_args, **_kwargs: pytest.fail("local backup invoked PostgreSQL backup"),
    )
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


def _write_owned_local_backup(root: Path, name: str, modified_at: float) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "timestamp": name[:15],
                "copied": ["web/data.json"],
                "counts": {},
                "sizes": {},
            }
        ),
        encoding="utf-8",
    )
    os.utime(directory, (modified_at, modified_at))
    return directory


def test_main_custom_out_dir_preserves_unrelated_old_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_root = tmp_path / "user-output"
    custom_root.mkdir()
    old_time = time.time() - 40 * 86400
    markers = []
    for index in range(6):
        unrelated = custom_root / f"unrelated-{index}"
        unrelated.mkdir()
        marker = unrelated / "keep-me.txt"
        marker.write_text(f"marker-{index}", encoding="utf-8")
        os.utime(unrelated, (old_time - index, old_time - index))
        markers.append(marker)

    data_json = tmp_path / "data.json"
    data_json.write_text(
        json.dumps({"entities": [], "relationships": [], "itineraries": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(backup_data, "DATA_JSON", data_json)
    monkeypatch.setattr(backup_data, "DB_FILE", tmp_path / "missing.db")
    monkeypatch.setattr(
        "sys.argv",
        [
            "backup_data.py",
            "--target",
            "local",
            "--out-dir",
            str(custom_root),
            "--keep",
            "5",
            "--max-age-days",
            "30",
        ],
    )

    assert backup_data.main() == 0
    assert all(marker.read_text(encoding="utf-8").startswith("marker-") for marker in markers)


def test_cleanup_managed_root_preserves_unowned_old_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_root = tmp_path / "backups"
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", backup_root)
    backup_root.mkdir()
    now = time.time()
    for index in range(5):
        _write_owned_local_backup(
            backup_root,
            f"2026071{index + 1}-120000",
            now - index,
        )
    unrelated = backup_root / "unrelated-user-data"
    unrelated.mkdir()
    marker = unrelated / "keep-me.txt"
    marker.write_text("important", encoding="utf-8")
    old_time = now - 40 * 86400
    os.utime(unrelated, (old_time, old_time))

    backup_data._cleanup_old_backups(keep=5, max_age_days=30)

    assert marker.read_text(encoding="utf-8") == "important"


def test_cleanup_managed_root_removes_expired_owned_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_root = tmp_path / "backups"
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", backup_root)
    backup_root.mkdir()
    now = time.time()
    old_backup = _write_owned_local_backup(
        backup_root,
        "20260101-000000-old",
        now - 40 * 86400,
    )
    new_backup = _write_owned_local_backup(
        backup_root,
        "20260714-120000-new",
        now,
    )

    backup_data._cleanup_old_backups(keep=1, max_age_days=30)

    assert not old_backup.exists()
    assert new_backup.exists()


def test_cleanup_keeps_minimum(tmp_path: Path, monkeypatch) -> None:
    backup_root = tmp_path / "backups"
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", backup_root)

    for i in range(3):
        d = backup_root / f"backup-{i}"
        d.mkdir(parents=True)

    backup_data._cleanup_old_backups(keep=5, max_age_days=1)
    assert len(list(backup_root.iterdir())) == 3


class FakeRunner:
    def __init__(
        self,
        *,
        listing: str | None = None,
        dump_returncode: int = 0,
        restore_returncode: int = 0,
        unavailable_tool: str | None = None,
        version_tool: str | None = None,
        version_returncode: int = 0,
        version_stdout: str = "16.4\n",
    ) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.listing = (
            listing
            if listing is not None
            else (
                "1; 0 0 TABLE public entities postgres\n"
                "2; 0 0 TABLE public entity_changes postgres\n"
            )
        )
        self.dump_returncode = dump_returncode
        self.restore_returncode = restore_returncode
        self.unavailable_tool = unavailable_tool
        self.version_tool = version_tool
        self.version_returncode = version_returncode
        self.version_stdout = version_stdout

    def __call__(self, args, **kwargs):
        command = [str(value) for value in args]
        self.calls.append((command, kwargs))
        if command[0] == self.unavailable_tool:
            raise FileNotFoundError(command[0])
        if command[1:] == ["--version"]:
            use_invalid_version = command[0] == self.version_tool
            return subprocess.CompletedProcess(
                command,
                self.version_returncode if use_invalid_version else 0,
                self.version_stdout if use_invalid_version else "16.4\n",
                "version failed",
            )
        if command[0] == "pg_dump":
            if self.dump_returncode == 0:
                artifact = Path(command[command.index("--file") + 1])
                artifact.write_bytes(b"PGDMP-test")
            return subprocess.CompletedProcess(command, self.dump_returncode, "", "dump failed")
        if command[:2] == ["pg_restore", "--list"]:
            return subprocess.CompletedProcess(
                command,
                self.restore_returncode,
                self.listing,
                "restore failed",
            )
        raise AssertionError(f"unexpected command: {command}")


def _identity() -> dict[str, object]:
    return {
        "database": "vl360",
        "server_addr": "10.0.0.8",
        "server_port": 5432,
        "server_version_num": 160004,
    }


def _clock():
    return lambda: "2026-07-14T12:00:00Z"


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

    assert result == destination / "manifest.json"
    manifest_text = result.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["schema"] == "vinhlong360-pg-backup-v1"
    assert manifest["target"] == "pg"
    assert manifest["database_identity"] == _identity()
    assert len(manifest["target_fingerprint"]) == 64
    assert manifest["started_at"] == "2026-07-14T12:00:00Z"
    assert manifest["completed_at"] == "2026-07-14T12:00:00Z"
    assert manifest["max_age_seconds"] == 3600
    assert manifest["tools"] == {"pg_dump": "16.4", "pg_restore": "16.4"}
    assert manifest["artifact"] == {
        "path": "postgres.dump",
        "size": len(b"PGDMP-test"),
        "sha256": hashlib.sha256(b"PGDMP-test").hexdigest(),
    }
    assert (result.parent / manifest["artifact"]["path"]).read_bytes() == b"PGDMP-test"
    listing = runner.listing.encode()
    assert manifest["validation"] == {
        "pg_restore_list": True,
        "required_tables": ["entities", "entity_changes"],
        "listing_sha256": hashlib.sha256(listing).hexdigest(),
    }
    assert manifest["policy_revision"] == "published-v1"
    assert secret not in manifest_text
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


def test_create_postgres_backup_rejects_required_names_on_wrong_toc_objects(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "pg-backup"
    listing = (
        "1; 0 0 FUNCTION public entities() postgres\n"
        "2; 0 0 ACL public entity_changes postgres\n"
        "3; 0 0 COMMENT - TABLE public entities postgres\n"
        "4; 0 0 TABLE DATA public entities postgres\n"
        "5; 0 0 TABLE DATA public entity_changes postgres\n"
        "6; 0 0 TABLE public entities_archive postgres\n"
    )

    with pytest.raises(RuntimeError, match="entities"):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=_identity(),
            runner=FakeRunner(listing=listing),
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


@pytest.mark.parametrize("tool", ["pg_dump", "pg_restore"])
def test_create_postgres_backup_rejects_unavailable_tool_without_manifest(
    tmp_path: Path,
    tool: str,
) -> None:
    destination = tmp_path / "pg-backup"

    with pytest.raises(RuntimeError, match=tool):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=_identity(),
            runner=FakeRunner(unavailable_tool=tool),
            now=_clock(),
        )

    assert not (destination / "manifest.json").exists()


@pytest.mark.parametrize(
    ("tool", "version_stdout", "version_returncode"),
    [
        ("pg_dump", "", 0),
        ("pg_dump", "16.4\n", 1),
        ("pg_restore", "", 0),
        ("pg_restore", "16.4\n", 1),
    ],
)
def test_create_postgres_backup_rejects_invalid_tool_version_without_manifest(
    tmp_path: Path,
    tool: str,
    version_stdout: str,
    version_returncode: int,
) -> None:
    destination = tmp_path / "pg-backup"

    with pytest.raises(RuntimeError, match=tool):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=_identity(),
            runner=FakeRunner(
                version_tool=tool,
                version_stdout=version_stdout,
                version_returncode=version_returncode,
            ),
            now=_clock(),
        )

    assert not (destination / "manifest.json").exists()


def test_create_postgres_backup_rejects_failed_restore_listing_without_manifest(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "pg-backup"

    with pytest.raises(RuntimeError, match="pg_restore --list"):
        backup_data.create_postgres_backup(
            database_url="postgresql://backup:secret@db.example/vl360",
            destination=destination,
            identity=_identity(),
            runner=FakeRunner(restore_returncode=1),
            now=_clock(),
        )

    assert not (destination / "manifest.json").exists()


def test_main_pg_missing_named_env_stops_before_identity_or_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    environment_name = "TASK5_MISSING_DATABASE_URL"
    fallback_secret = "fallback-secret"
    monkeypatch.delenv(environment_name, raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql://fallback:{fallback_secret}@db.example/vl360",
    )
    monkeypatch.setattr(
        backup_data,
        "_read_postgres_identity",
        lambda *_args, **_kwargs: pytest.fail("identity ran before env validation"),
    )
    monkeypatch.setattr(
        backup_data,
        "create_postgres_backup",
        lambda *_args, **_kwargs: pytest.fail("backup ran before env validation"),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "backup_data.py",
            "--target",
            "pg",
            "--database-url-env",
            environment_name,
            "--out-dir",
            str(tmp_path),
        ],
    )

    assert backup_data.main() == 1
    stderr = capsys.readouterr().err
    assert environment_name in stderr
    assert fallback_secret not in stderr
    assert not list(tmp_path.rglob("manifest.json"))


def test_main_pg_missing_psycopg2_is_credential_safe_and_has_no_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    environment_name = "TASK5_DATABASE_URL"
    secret = "identity-secret"
    monkeypatch.setenv(
        environment_name,
        f"postgresql://backup:{secret}@db.example/vl360",
    )
    monkeypatch.setitem(sys.modules, "psycopg2", None)
    monkeypatch.setattr(
        backup_data,
        "create_postgres_backup",
        lambda *_args, **_kwargs: pytest.fail("backup ran without PostgreSQL identity"),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "backup_data.py",
            "--target",
            "pg",
            "--database-url-env",
            environment_name,
            "--out-dir",
            str(tmp_path),
        ],
    )

    assert backup_data.main() == 1
    stderr = capsys.readouterr().err
    assert "psycopg2" in stderr
    assert secret not in stderr
    assert not list(tmp_path.rglob("manifest.json"))


def test_main_pg_validation_failure_returns_1_without_success_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    environment_name = "TASK5_DATABASE_URL"
    secret = "validation-secret"
    monkeypatch.setenv(
        environment_name,
        f"postgresql://backup:{secret}@db.example/vl360",
    )
    monkeypatch.setattr(backup_data, "_read_postgres_identity", lambda _url: _identity())
    create_postgres_backup = backup_data.create_postgres_backup

    def fail_validation(**kwargs):
        return create_postgres_backup(
            **kwargs,
            runner=FakeRunner(listing="1; 0 0 TABLE public entities postgres\n"),
            now=_clock(),
        )

    monkeypatch.setattr(backup_data, "create_postgres_backup", fail_validation)
    monkeypatch.setattr(
        "sys.argv",
        [
            "backup_data.py",
            "--target",
            "pg",
            "--database-url-env",
            environment_name,
            "--out-dir",
            str(tmp_path),
        ],
    )

    assert backup_data.main() == 1
    stderr = capsys.readouterr().err
    assert "entity_changes" in stderr
    assert secret not in stderr
    assert not list(tmp_path.rglob("manifest.json"))
