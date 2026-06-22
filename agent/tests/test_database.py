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


def test_replace_from_json_roundtrip_with_rels_itins(db, tmp_path, monkeypatch):
    """Replace nạp đủ entity + relationship + itinerary; xoá row cũ (stale)."""
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    db.upsert_entity(_entity(eid="stale"))  # phải biến mất sau replace
    data = {
        "entities": [_entity(eid="a"), _entity(eid="b")],
        "relationships": [{"from": "a", "to": "b", "type": "near"}],
        "itineraries": [{"id": "it1", "title": "T", "area": "vinh-long", "stops": [{"name": "A"}]}],
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    db.replace_from_json(str(p))
    assert db.get_entity("stale") is None
    assert db.get_entity("a") and db.get_entity("b")
    assert db.all_relationships() == [{"from": "a", "to": "b", "type": "near"}]
    its = db.all_itineraries()
    assert len(its) == 1 and its[0]["id"] == "it1"


def test_replace_from_json_atomic_rollback(db, tmp_path, monkeypatch):
    """ATOMIC (F1): insert lỗi giữa chừng → DELETE rollback → data CŨ còn nguyên,
    KHÔNG để DB rỗng. (Hợp-nhất path: SQLite+PG cùng 1 transaction qua _bulk_load.)"""
    monkeypatch.setenv("DESTRUCTIVE_OPS_LOCKED", "1")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DB_REPLACE", "1")
    db.upsert_entity(_entity(eid="old", name="Cũ"))
    data = {"entities": [_entity(eid="new1")], "relationships": [], "itineraries": []}
    p = tmp_path / "data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def boom(conn, d):
        conn.execute("INSERT OR REPLACE INTO entities (id, type, name) VALUES ('partial','dish','X')")
        raise RuntimeError("simulated crash mid-insert")
    monkeypatch.setattr(db, "_bulk_load", boom)

    with pytest.raises(RuntimeError):
        db.replace_from_json(str(p))
    # DELETE + partial-INSERT đều rollback trong 1 transaction
    assert db.get_entity("old") is not None, "data cũ phải còn (transaction rollback)"
    assert db.get_entity("new1") is None
    assert db.get_entity("partial") is None


# ── Bulk getters (GĐ3.4: nguồn nạp knowledge in-memory) ──

def test_all_entities_includes_place(db):
    db.upsert_entity(_entity(eid="d1", etype="dish"))
    db.upsert_entity(_entity(eid="p1", etype="place", name="Xã A"))
    ids = {e["id"] for e in db.all_entities()}
    assert ids == {"d1", "p1"}  # KHÁC list_entities: gồm cả place


def test_all_relationships_shape(db):
    db.upsert_entity(_entity(eid="e1"))
    db.upsert_entity(_entity(eid="e2"))
    db.add_relationship("e1", "e2", "near")
    rels = db.all_relationships()
    assert rels == [{"from": "e1", "to": "e2", "type": "near"}]


def test_all_itineraries(db):
    db.upsert_itinerary({"id": "it1", "title": "T", "stops": [{"name": "A"}]})
    its = db.all_itineraries()
    assert len(its) == 1 and its[0]["id"] == "it1" and isinstance(its[0]["stops"], list)


# ── D02: PG connection pool — kill-switch + fallback (an-toàn, không cần PG thật) ──

def test_pg_pool_kill_switch(tmp_path, monkeypatch):
    """PG_USE_POOL=false → _get_pg_pool trả None (dùng connect-trực-tiếp)."""
    d = Database(db_path=str(tmp_path / "t.db"))
    d._use_pg = True
    d._dsn = "postgresql://x@127.0.0.1:5432/x"
    monkeypatch.setenv("PG_USE_POOL", "false")
    assert d._get_pg_pool() is None


def test_pg_pool_fallback_on_bad_dsn(tmp_path, monkeypatch):
    """DSN lỗi → tạo pool raise → fallback None + đánh dấu failed (không crash)."""
    d = Database(db_path=str(tmp_path / "t.db"))
    d._use_pg = True
    d._dsn = "not-a-valid-dsn"
    monkeypatch.setenv("PG_USE_POOL", "true")
    assert d._get_pg_pool() is None
    assert d._pg_pool_failed is True


def test_pg_pool_default_off(tmp_path, monkeypatch):
    """OPT-IN: KHÔNG set PG_USE_POOL → pool OFF (connect-trực-tiếp). Khoá incident-fix
    2026-06-22 (pool treo agent startup prod). Pool chỉ bật khi PG_USE_POOL=true tường minh."""
    d = Database(db_path=str(tmp_path / "t.db"))
    d._use_pg = True
    d._dsn = "postgresql://x@127.0.0.1:5432/x"
    monkeypatch.delenv("PG_USE_POOL", raising=False)
    assert d._get_pg_pool() is None


# ── GĐ13.3: danh bạ hành chính (facility theo placeId) ──

def test_facilities_by_place(db):
    db.upsert_entity({"id": "ubnd-xa-a", "type": "facility", "name": "UBND xã A",
                      "placeId": "xa-a",
                      "attributes": {"office_kind": "ubnd", "address": "Số 1", "phone": "0270..."}})
    db.upsert_entity({"id": "ca-xa-a", "type": "facility", "name": "Công an xã A",
                      "placeId": "xa-a", "attributes": {"office_kind": "cong_an"}})
    db.upsert_entity({"id": "ubnd-xa-b", "type": "facility", "name": "UBND xã B", "placeId": "xa-b"})

    a = db.facilities_by_place("xa-a")
    assert {f["id"] for f in a} == {"ubnd-xa-a", "ca-xa-a"}
    assert a[0]["attributes"].get("office_kind") in ("ubnd", "cong_an")  # JSON attrs parse lại
    assert {f["id"] for f in db.facilities_by_place("xa-b")} == {"ubnd-xa-b"}
    assert db.facilities_by_place("khong-co") == []
    assert len(db.facilities_by_place()) == 3  # tất cả facility


def test_upsert_accepts_coords_alias(db):
    # GĐ-audit: ETL/auto_learn ghi entity["coords"] (legacy) — upsert phải map sang coordinates
    # để không mất toạ độ đã geocode.
    db.upsert_entity({"id": "e-coords", "type": "attraction", "name": "Điểm có coords",
                      "coords": [10.25, 105.97]})
    e = db.get_entity("e-coords")
    assert e.get("coordinates") == [10.25, 105.97]
    # "coordinates" vẫn được ưu tiên nếu có cả hai
    db.upsert_entity({"id": "e-both", "type": "attraction", "name": "X",
                      "coordinates": [10.25, 105.97], "coords": [10.30, 106.00]})
    assert db.get_entity("e-both").get("coordinates") == [10.25, 105.97]


def test_entities_by_place(db):
    # Trang hub xã/phường: gom mọi entity nội dung theo placeId, trừ chính các place.
    db.upsert_entity({"id": "xa-h", "type": "place", "name": "Xã H", "placeId": None})
    db.upsert_entity({"id": "diem-1", "type": "attraction", "name": "Điểm 1", "placeId": "xa-h"})
    db.upsert_entity({"id": "ks-1", "type": "accommodation", "name": "KS 1", "placeId": "xa-h"})
    db.upsert_entity({"id": "sp-1", "type": "product", "name": "SP 1", "placeId": "xa-h"})
    db.upsert_entity({"id": "diem-x", "type": "attraction", "name": "Điểm X", "placeId": "xa-khac"})

    got = db.entities_by_place("xa-h")
    ids = {e["id"] for e in got}
    assert ids == {"diem-1", "ks-1", "sp-1"}          # đúng ward, gồm nhiều type
    assert "xa-h" not in ids                          # KHÔNG gồm chính đơn vị place
    assert "diem-x" not in ids                        # KHÔNG gồm ward khác
    assert db.entities_by_place("khong-co") == []


# ── GĐ3.8: data-quality apply/rollback DB-native (không DELETE-reload-json) ──

def test_data_quality_apply_and_rollback_db_native(db, tmp_path, monkeypatch):
    import data_quality

    db.upsert_entity(_entity(eid="e1", etype="dish",
                             source={"title": "old", "url": "https://old.example/"}))
    monkeypatch.setattr(data_quality, "db", db)          # apply/rollback dùng temp DB
    monkeypatch.setattr(data_quality, "BURST_DIR", tmp_path)  # cô lập apply_history

    cand = {
        "candidate_id": "c1", "entity_id": "e1", "field": "source",
        "apply_policy": "auto_apply", "url_verified": True,
        "suggested_value": {"title": "New", "url": "https://new.example/page"},
        "evidence_urls": ["https://new.example/page"], "confidence": 0.9,
    }
    monkeypatch.setattr(data_quality, "load_candidate_queue", lambda **k: {"auto_apply": [cand]})

    res = data_quality.apply_candidates(["c1"], dry_run=False)
    assert res["applied_count"] == 1
    # ghi THẲNG vào DB (không qua data.json)
    src = db.get_entity("e1")["source"]
    assert (src[0]["url"] if isinstance(src, list) else src["url"]) == "https://new.example/page"

    rb = data_quality.rollback_apply(res["batch_id"])
    assert rb["restored_changes"] == 1
    src_after = db.get_entity("e1")["source"]
    assert (src_after[0] if isinstance(src_after, list) else src_after) == {"title": "old", "url": "https://old.example/"}


# ── GĐ3.1 (QUYẾT ĐỊNH): UGC/auth Postgres-only; SQLite KHÔNG có bảng users (by design) ──
# Dev/prod parity. SQLite chỉ phục vụ tầng tri thức (entity/rel/itinerary).

@pytest.mark.xfail(reason="QUYẾT ĐỊNH: UGC Postgres-only — SQLite không có users (by design)", strict=False)
def test_create_user_unavailable_on_sqlite_by_design(db):
    db.create_user("0900000000", "Test")
    assert db.get_user_by_phone("0900000000") is not None
