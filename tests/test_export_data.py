# -*- coding: utf-8 -*-
"""Test scripts/export_data.py — tái lập cơ chế export DB→data.json (campaign tỉnh-mới T1).

B3/B4: script ETL mới phải có test trước khi dùng. Chạy trên SQLite temp — không đụng DB thật.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))

MINI = {
    "entities": [
        {
            "id": "test-entity-a",
            "type": "dish",
            "name": "Bún test A",
            "summary": "Tóm tắt A",
            "description": "Mô tả A dài hơn một chút.",
            "area": "vinh-long",
            "attributes": {"address": "Xã Test, tỉnh Vĩnh Long"},
        },
        {
            "id": "test-entity-b",
            "type": "place",
            "name": "Xã Test B",
            "summary": "Tóm tắt B",
            "description": "Mô tả B.",
            "area": "ben-tre",
            "attributes": {},
        },
    ],
    "relationships": [
        {"type": "located_in", "from": "test-entity-a", "to": "test-entity-b"},
    ],
    "itineraries": [
        {"id": "it-test", "title": "Hành trình test", "days": []},
    ],
}


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """SQLite temp đã nạp MINI qua replace_from_json (mở khoá chỉ trong test)."""
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "0")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    src = tmp_path / "mini.json"
    src.write_text(json.dumps(MINI, ensure_ascii=False), encoding="utf-8")
    import database

    d = database.Database(db_path=str(tmp_path / "t.db"))
    d.replace_from_json(str(src))
    return d


def test_export_writes_data_json_shape(tmp_db, tmp_path):
    from export_data import export

    out = tmp_path / "out.json"
    result = export(tmp_db, str(out), dry_run=False)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"entities", "relationships", "itineraries"}
    assert {e["id"] for e in data["entities"]} == {"test-entity-a", "test-entity-b"}
    assert len(data["relationships"]) == 1
    assert len(data["itineraries"]) == 1
    assert result["written"] is True
    # atomic: không để lại file tạm
    assert not list(tmp_path.glob("out.json.*tmp*"))


def test_export_dry_run_does_not_write(tmp_db, tmp_path):
    from export_data import export

    out = tmp_path / "out.json"
    result = export(tmp_db, str(out), dry_run=True)
    assert not out.exists()
    assert result["written"] is False
    assert result["counts"]["entities"] == 2


def test_export_dry_run_diffs_against_existing(tmp_db, tmp_path):
    from export_data import export

    out = tmp_path / "out.json"
    # file hiện có: thiếu 1 entity + text khác
    old = {
        "entities": [dict(MINI["entities"][0], summary="Tóm tắt CŨ")],
        "relationships": [],
        "itineraries": [],
    }
    out.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    result = export(tmp_db, str(out), dry_run=True)
    assert result["written"] is False
    d = result["diff"]
    assert d["entities_added"] == 1      # test-entity-b mới
    assert d["entities_removed"] == 0
    assert d["entities_changed"] >= 1    # summary A đổi
    # dry-run không được đụng file
    assert json.loads(out.read_text(encoding="utf-8")) == old


def test_export_normalizes_shape_no_flat_cols_and_createdAt(tmp_db, tmp_path, monkeypatch):
    """SP2 T2: export không mang 8 cột phẳng; createdAt hiện diện khi có created_at."""
    from export_data import export

    ents = tmp_db.all_entities()
    ents[0]["address"] = "flat"
    ents[0]["phone"] = "123"
    ents[0]["created_at"] = "2026-07-07"
    ents[0].pop("createdAt", None)
    monkeypatch.setattr(tmp_db, "all_entities", lambda: ents)
    out = tmp_path / "out.json"
    export(tmp_db, str(out), dry_run=False)
    e = json.loads(out.read_text(encoding="utf-8"))["entities"][0]
    assert "address" not in e and "phone" not in e
    assert e["createdAt"] == "2026-07-07"


def test_export_roundtrip_stable(tmp_db, tmp_path, monkeypatch):
    """Round-trip: replace_from_json(export) → export lại ≡ lần 1 (entities theo id)."""
    import database
    from export_data import export

    out1 = tmp_path / "r1.json"
    export(tmp_db, str(out1), dry_run=False)
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "0")
    db2 = database.Database(db_path=str(tmp_path / "t2.db"))
    db2.replace_from_json(str(out1))
    out2 = tmp_path / "r2.json"
    export(db2, str(out2), dry_run=False)
    d1 = json.loads(out1.read_text(encoding="utf-8"))
    d2 = json.loads(out2.read_text(encoding="utf-8"))
    e1 = {e["id"]: e for e in d1["entities"]}
    e2 = {e["id"]: e for e in d2["entities"]}
    assert set(e1) == set(e2)
    for i in e1:
        for f in ("name", "summary", "description", "type", "attributes"):
            assert e1[i].get(f) == e2[i].get(f), (i, f)


def test_export_serializes_datetime_from_pg_backend(tmp_db, tmp_path, monkeypatch):
    """PG trả datetime cho timestamp — export không được nổ TypeError."""
    from datetime import datetime

    from export_data import export

    ents = tmp_db.all_entities()
    ents[0]["createdAt"] = datetime(2026, 7, 7, 10, 30)
    monkeypatch.setattr(tmp_db, "all_entities", lambda: ents)
    out = tmp_path / "out.json"
    export(tmp_db, str(out), dry_run=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["entities"][0]["createdAt"] == "2026-07-07T10:30:00"


def test_export_overwrite_preserves_valid_json_on_success(tmp_db, tmp_path):
    from export_data import export

    out = tmp_path / "out.json"
    out.write_text("{\"entities\": []}", encoding="utf-8")
    export(tmp_db, str(out), dry_run=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["entities"]) == 2
