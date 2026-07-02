"""Contract tests GĐ-C (C2): flip ĐỌC sau flag ENTITY_DETAILS_TABLES.

Hợp đồng khi flag ON, so với flag OFF:
  1. Tail (bespoke + KBYG) byte-identical, đúng thứ tự key gốc.
  2. Typed keys: cột thắng khi có giá trị — với dữ liệu đã đúng kiểu (int/bool/
     list) kết quả BYTE-IDENTICAL; với legacy string-số ("4") giá trị được
     CHUẨN HOÁ KIỂU (→ 4) — thay đổi chủ đích, ghi trong spec.
  3. Giá trị uncoercible ("Thế kỷ 19" trong trường số) KHÔNG mất — fallback JSONB.
  4. Kind không bảng CTI (itinerary) → attributes nguyên vẹn tuyệt đối.
  5. Mọi đường đọc (get_entity / get_entities_batch / list_entities) cùng hành vi.
"""
import os
import sys
import pathlib

os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.pop("ENTITY_DETAILS_TABLES", None)  # baseline: flag OFF
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import entity_details  # noqa: E402
from database import db  # noqa: E402

IDS = {
    "product": "zz-test-readflip-product",
    "attraction": "zz-test-readflip-attraction",
    "cafe": "zz-test-readflip-cafe",
    "legacy": "zz-test-readflip-legacy",
    "itinerary": "zz-test-readflip-itin",
}


@pytest.fixture()
def flip(monkeypatch):
    """Bật flag + nạp cache; tự tắt và reset sau test."""
    def _on():
        monkeypatch.setenv("ENTITY_DETAILS_TABLES", "true")
        db.reload_entity_details_cache()
    yield _on
    monkeypatch.delenv("ENTITY_DETAILS_TABLES", raising=False)
    entity_details.reset_detail_cache()


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    os.environ.pop("ENTITY_DETAILS_TABLES", None)
    entity_details.reset_detail_cache()
    for eid in IDS.values():
        db.delete_entity(eid)


def _attrs(eid: str) -> dict:
    e = db.get_entity(eid)
    assert e is not None
    return e["attributes"]


def test_typed_clean_data_byte_identical(flip):
    original = {
        "sac_phong": "Tự Đức 1852",           # bespoke tail
        "ocop_star": 4,                        # đã đúng kiểu int
        "producer": "HTX Contract",
        "address": "Ấp Test, xã Contract",     # universal
        "kbyg_tips": ["đi sáng sớm", "mang nón"],  # KBYG tail (list)
    }
    db.upsert_entity({"id": IDS["product"], "type": "product", "name": "SP contract",
                      "attributes": dict(original)})
    off = _attrs(IDS["product"])
    flip()
    on = _attrs(IDS["product"])
    assert on == off == original
    assert list(on.keys()) == list(original.keys()), "thứ tự key phải giữ nguyên"


def test_uncoercible_value_not_lost(flip):
    db.upsert_entity({"id": IDS["attraction"], "type": "attraction", "name": "Đình contract",
                      "attributes": {"founding_year": "Thế kỷ 19", "religion": "Tín ngưỡng dân gian"}})
    off = _attrs(IDS["attraction"])
    flip()
    on = _attrs(IDS["attraction"])
    assert on["founding_year"] == "Thế kỷ 19", "giá trị uncoercible phải fallback JSONB, không mất"
    assert on == off


def test_bool_and_typed_values_identical(flip):
    db.upsert_entity({"id": IDS["cafe"], "type": "cafe", "name": "Cafe contract",
                      "attributes": {"wifi": True, "rating": 4.5, "price_range": "25-45k"}})
    off = _attrs(IDS["cafe"])
    flip()
    on = _attrs(IDS["cafe"])
    assert on == off
    assert on["wifi"] is True and abs(on["rating"] - 4.5) < 1e-9


def test_legacy_string_number_normalized_by_design(flip):
    db.upsert_entity({"id": IDS["legacy"], "type": "product", "name": "SP legacy",
                      "attributes": {"ocop_star": "4"}})   # legacy string-số trong JSONB
    off = _attrs(IDS["legacy"])
    assert off["ocop_star"] == "4"
    flip()
    on = _attrs(IDS["legacy"])
    assert on["ocop_star"] == 4, "flag ON chuẩn hoá kiểu theo cột (chủ đích, ghi trong spec)"


def test_itinerary_kind_untouched(flip):
    original = {"duration": "2 ngày", "provinces": ["Vĩnh Long"], "traveler_type": "gia đình"}
    db.upsert_entity({"id": IDS["itinerary"], "type": "itinerary", "name": "LT contract",
                      "attributes": dict(original)})
    flip()
    assert _attrs(IDS["itinerary"]) == original


def test_all_read_paths_agree(flip):
    db.upsert_entity({"id": IDS["product"], "type": "product", "name": "SP contract",
                      "attributes": {"ocop_star": 5, "producer": "HTX Đồng Bộ"}})
    flip()
    via_get = _attrs(IDS["product"])
    via_batch = db.get_entities_batch([IDS["product"]])[IDS["product"]]["attributes"]
    via_list = next(e for e in db.list_entities(entity_type="product", limit=2000, offset=0)
                    if e["id"] == IDS["product"])["attributes"]
    assert via_get == via_batch == via_list


def test_cache_follows_writes_while_flag_on(flip):
    db.upsert_entity({"id": IDS["product"], "type": "product", "name": "SP contract",
                      "attributes": {"ocop_star": 3}})
    flip()
    assert _attrs(IDS["product"])["ocop_star"] == 3
    # Ghi tiếp KHI flag đang ON — cache phải theo (sync cập nhật cache)
    db.upsert_entity({"id": IDS["product"], "type": "product", "name": "SP contract",
                      "attributes": {"ocop_star": 5, "producer": "HTX Mới"}})
    on = _attrs(IDS["product"])
    assert on["ocop_star"] == 5 and on["producer"] == "HTX Mới"