"""
Tests cho tầng KB của database.py (GĐ1.1 — trước đây 0% coverage).

Bọc các hàm mà GĐ2/GĐ3 sẽ sửa nặng: upsert/get/list/count/search entity,
relationship (dedup), itinerary, migrate_from_json, replace_from_json (+ khoá GĐ0.5).
Chạy trên SQLite tạm, không đụng DB thật.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure agent/ on path (cùng pattern các test khác trong agent/tests/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import Database  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Database SQLite cô lập trong tmp_path. Ép sqlite + mở khoá replace cho test."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    d = Database(db_path=str(tmp_path / "test.db"))
    d._use_pg = False          # hằng USE_PG ở module — ép sqlite cho chắc
    d._dsn = None
    d.initialize()
    return d


def _entity(eid="e1", etype="dish", **kw):
    base = {
        "id": eid,
        "type": etype,
        "name": kw.get("name", "Bún bò"),
        "summary": kw.get("summary", "Món ngon"),
        "area": kw.get("area", "vinh-long"),
        "placeId": kw.get("placeId"),
        "attributes": kw.get("attributes", {"price": "50k"}),
        "season": kw.get("season"),
        "source": kw.get("source", {"title": "seed"}),
        "images": kw.get("images", []),
        "coordinates": kw.get("coordinates", [10.25, 105.97]),
        "confidence": kw.get("confidence", 0.8),
    }
    return base


# ── Schema ──

def test_initialize_creates_core_tables(db):
    with db._conn() as conn:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"entities", "relationships", "itineraries", "feedback", "query_log"} <= names


# ── Entity CRUD + JSON round-trip ──

def test_upsert_get_entity_roundtrip(db):
    db.upsert_entity(_entity(eid="e1", attributes={"price": "50k", "hours": "7-22"},
                             coordinates=[10.25, 105.97], season={"months": [6, 7]}))
    got = db.get_entity("e1")
    assert got is not None
    assert got["name"] == "Bún bò"
    # JSON fields phải được parse lại thành object (không phải chuỗi)
    assert got["attributes"] == {"price": "50k", "hours": "7-22"}
    assert got["coordinates"] == [10.25, 105.97]
    assert got["season"] == {"months": [6, 7]}


def test_upsert_is_update_on_same_id(db):
    db.upsert_entity(_entity(eid="e1", name="A"))
    db.upsert_entity(_entity(eid="e1", name="B"))
    assert db.get_entity("e1")["name"] == "B"
    assert db.count_entities().get("dish", 0) == 1


def test_get_missing_entity_returns_none(db):
    assert db.get_entity("khong-ton-tai") is None


def test_delete_entity_removes_entity_and_relationships(db):
    db.upsert_entity(_entity(eid="e1"))
    db.upsert_entity(_entity(eid="e2"))
    db.add_relationship("e1", "e2", "near")
    assert db.delete_entity("e1") is True
    assert db.get_entity("e1") is None
    with db._conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM relationships WHERE from_id='e1' OR to_id='e1'").fetchone()[0]
    assert n == 0


# ── List / count / search loại trừ type='place' (hợp đồng public) ──

def test_list_and_count_exclude_place(db):
    db.upsert_entity(_entity(eid="d1", etype="dish"))
    db.upsert_entity(_entity(eid="p1", etype="place", name="Xã A"))
    listed_ids = {e["id"] for e in db.list_entities()}
    assert "d1" in listed_ids and "p1" not in listed_ids
    counts = db.count_entities()
    assert "place" not in counts and counts.get("dish") == 1


def test_list_filter_by_type(db):
    db.upsert_entity(_entity(eid="d1", etype="dish"))
    db.upsert_entity(_entity(eid="a1", etype="attraction"))
    ids = {e["id"] for e in db.list_entities(entity_type="attraction")}
    assert ids == {"a1"}


def test_count_entities_filtered_by_query(db):
    db.upsert_entity(_entity(eid="d1", name="Bánh xèo", etype="dish"))
    db.upsert_entity(_entity(eid="d2", name="Hủ tiếu", etype="dish"))
    assert db.count_entities_filtered(q="Bánh") == 1
    assert db.count_entities_filtered(entity_type="dish") == 2


# ── Relationships ──

def test_add_relationship_dedup(db):
    """INSERT OR IGNORE: thêm cạnh trùng (from,to,type) chỉ lưu 1 lần.

    Ghi lại hành vi mất-mát mà GĐ3.2 sẽ giám sát khi migrate.
    """
    db.upsert_entity(_entity(eid="e1"))
    db.upsert_entity(_entity(eid="e2"))
    db.add_relationship("e1", "e2", "near")
    db.add_relationship("e1", "e2", "near")  # trùng
    with db._conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    assert n == 1


# ── Itineraries ──

def test_itinerary_roundtrip(db):
    it = {"id": "it1", "title": "1 ngày Vĩnh Long", "area": "vinh-long",
          "duration": "1 ngày", "summary": "x", "stops": [{"name": "A"}, {"name": "B"}]}
    db.upsert_itinerary(it)
    got = db.get_itinerary("it1")
    assert got["title"] == "1 ngày Vĩnh Long"
    assert isinstance(got["stops"], list) and len(got["stops"]) == 2
    assert {i["id"] for i in db.list_itineraries()} == {"it1"}


# ── migrate_from_json ──

def test_migrate_from_json_roundtrip(db, tmp_path):
    data = {
        "entities": [_entity(eid="d1", etype="dish"), _entity(eid="p1", etype="place", name="Xã A")],
        "relationships": [
            {"from": "d1", "to": "p1", "type": "located_in"},
            {"from": "d1", "to": "p1", "type": "located_in"},  # trùng -> dedup khi lưu
        ],
        "itineraries": [{"id": "it1", "title": "T", "stops": []}],
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    res = db.migrate_from_json(str(p))
    assert res["entities"] == 2
    assert res["itineraries"] == 1
    # report đếm số cạnh hợp lệ (2) nhưng lưu chỉ 1 do dedup -> bằng chứng mất-mát
    assert res["relationships"] == 2
    with db._conn() as conn:
        stored = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    assert stored == 1
    assert db.get_entity("d1") is not None and db.get_entity("p1") is not None


# ── replace_from_json + khoá GĐ0.5 ──

def test_replace_from_json_locked_by_default(db, tmp_path, monkeypatch):
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_DB_REPLACE", raising=False)
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"entities": [], "relationships": [], "itineraries": []}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="khoá|locked|DESTRUCTIVE"):
        db.replace_from_json(str(p))


def test_replace_from_json_with_override_roundtrip(db, tmp_path, monkeypatch):
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    db.upsert_entity(_entity(eid="old", etype="dish"))  # sẽ bị thay
    data = {
        "entities": [_entity(eid="new1", etype="attraction", name="Mới")],
        "relationships": [],
        "itineraries": [],
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    db.replace_from_json(str(p))
    assert db.get_entity("old") is None
    assert db.get_entity("new1")["name"] == "Mới"


# ── Gap GĐ3.1: SQLite chưa có bảng users (UGC/login crash ở local dev) ──

@pytest.mark.xfail(reason="GĐ3.1 sẽ thêm bảng users/posts/... cho SQLite", strict=False)
def test_users_table_exists_after_gd31(db):
    db.create_user("0900000000", "Test")
    assert db.get_user_by_phone("0900000000") is not None
