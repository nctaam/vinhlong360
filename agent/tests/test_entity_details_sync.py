"""Tests GĐ-C (C1): dual-write typed attributes ↔ cột phổ quát + bảng CTI.

Chạy trên SQLite dev (ensure_schema_sqlite tạo bảng/cột khi initialize).
Bất biến kiểm chứng: sau MỖI upsert, cột == nội dung typed coerce-được trong
attributes JSONB (mirror, không COALESCE); xoá entity dọn sạch detail row.
Dùng entity id test riêng + dọn sạch sau mỗi test — không đụng dữ liệu dev.
"""
import os
import sys
import pathlib

os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from database import db  # noqa: E402

TEST_ID = "zz-test-entity-details-sync"


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    db.delete_entity(TEST_ID)


def _fetch_detail(table: str) -> dict | None:
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT * FROM {table} WHERE entity_id = {db._ph}", (TEST_ID,))
        return db._row_to_dict(row) if row else None


def _fetch_universal() -> dict:
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT address, phone, price_range, best_time FROM entities WHERE id = {db._ph}", (TEST_ID,))
        return db._row_to_dict(row) or {}


def test_upsert_mirrors_product_typed_fields():
    db.upsert_entity({
        "id": TEST_ID, "type": "product", "name": "Test OCOP sync",
        "attributes": {"ocop_star": "4", "producer": "HTX Test", "address": "Ấp 9, xã Test",
                       "sac_phong": "tail giữ nguyên"},
    })
    d = _fetch_detail("entity_product_details")
    assert d and d["ocop_star"] == 4 and d["producer"] == "HTX Test"
    assert _fetch_universal()["address"] == "Ấp 9, xã Test"
    # bespoke tail không sinh cột
    assert "sac_phong" not in (d or {})


def test_reupsert_clears_removed_values_mirror_not_coalesce():
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "T",
                      "attributes": {"ocop_star": "5", "address": "A"}})
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "T",
                      "attributes": {"producer": "Chỉ còn producer"}})
    d = _fetch_detail("entity_product_details")
    assert d["producer"] == "Chỉ còn producer"
    assert d["ocop_star"] is None, "mirror: giá trị bị xoá khỏi JSONB phải NULL ở cột"
    assert _fetch_universal()["address"] is None


def test_bool_and_tags_on_sqlite():
    db.upsert_entity({"id": TEST_ID, "type": "cafe", "name": "Cafe test",
                      "attributes": {"wifi": "true", "rating": "4.5",
                                     "price_range": "20-40k"}})
    d = _fetch_detail("entity_food_details")
    assert d["wifi"] == 1 and abs(d["rating"] - 4.5) < 1e-9
    db.upsert_entity({"id": TEST_ID, "type": "dish", "name": "Món test",
                      "attributes": {"ingredients": "dừa, mè"}})
    d2 = _fetch_detail("entity_food_details")
    import json
    assert json.loads(d2["ingredients"]) == ["dừa", "mè"]


def test_no_typed_values_no_row_and_itinerary_kind_skipped():
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "T",
                      "attributes": {"schema_type": "Product"}})  # chỉ tail
    assert _fetch_detail("entity_product_details") is None
    db.upsert_entity({"id": TEST_ID, "type": "itinerary", "name": "LT test",
                      "attributes": {"duration": "2 ngày"}})  # kind không bảng CTI
    # không crash, không bảng nào có row
    for t in ("entity_place_details", "entity_food_details"):
        assert _fetch_detail(t) is None


def test_delete_entity_cleans_detail_rows():
    db.upsert_entity({"id": TEST_ID, "type": "person", "name": "Nhân vật test",
                      "attributes": {"role": "Danh nhân", "birth_year": "1900"}})
    assert _fetch_detail("entity_person_details")["role"] == "Danh nhân"
    db.delete_entity(TEST_ID)
    assert _fetch_detail("entity_person_details") is None
