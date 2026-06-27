from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
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


def test_main_copies_db_when_exists(tmp_path: Path, monkeypatch) -> None:
    data_json = tmp_path / "data.json"
    data_json.write_text(json.dumps({"entities": [], "relationships": [], "itineraries": []}))
    db_file = tmp_path / "test.db"
    db_file.write_bytes(b"SQLite data")

    monkeypatch.setattr(backup_data, "DATA_JSON", data_json)
    monkeypatch.setattr(backup_data, "DB_FILE", db_file)
    monkeypatch.setattr(backup_data, "BACKUP_ROOT", tmp_path / "backups")
    monkeypatch.setattr("sys.argv", ["backup_data.py"])

    rc = backup_data.main()
    assert rc == 0
    dirs = list((tmp_path / "backups").iterdir())
    manifest = json.loads((dirs[0] / "manifest.json").read_text(encoding="utf-8"))
    assert "agent/data/vinhlong360.db" in manifest["copied"]
    assert (dirs[0] / "vinhlong360.db").exists()


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
