"""Tests GĐ-C3: strip-on-write + cleanup so-sánh-trước-khi-xoá.

Bất biến: (1) flag ON → JSONB lưu tail-only nhưng ĐỌC vẫn đủ; (2) cleanup chỉ
xoá key có cột khớp thật — cột trống (dev chưa backfill) = no-op; uncoercible
ở lại; (3) đầu ra đọc TRƯỚC == SAU cleanup.
"""
import json
import os
import sys
import pathlib

os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.pop("ENTITY_DETAILS_TABLES", None)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import pytest  # noqa: E402
import entity_details  # noqa: E402
from database import db  # noqa: E402
from cleanup_entity_jsonb import run as cleanup_run, strippable_keys  # noqa: E402

TEST_ID = "zz-test-c3-cleanup"


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    os.environ.pop("ENTITY_DETAILS_TABLES", None)
    entity_details.reset_detail_cache()
    db.delete_entity(TEST_ID)


def _raw_attrs() -> dict:
    with db._conn() as conn:
        row = db._fetchone(conn, f"SELECT attributes FROM entities WHERE id = {db._ph}", (TEST_ID,))
        d = db._row_to_dict(row) or {}
    a = d.get("attributes")
    return json.loads(a) if isinstance(a, str) else (a or {})


def test_strip_on_write_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENTITY_DETAILS_TABLES", "true")
    db.reload_entity_details_cache()
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "C3 test",
                      "attributes": {"ocop_star": 4, "producer": "HTX C3",
                                     "address": "Ấp C3", "sac_phong": "tail",
                                     "founding_year": "Thế kỷ 19"}})
    raw = _raw_attrs()
    assert "ocop_star" not in raw and "producer" not in raw and "address" not in raw, \
        "typed keys đã sync phải bị strip khỏi JSONB khi flag ON"
    assert raw.get("sac_phong") == "tail", "tail phải ở lại"
    assert raw.get("founding_year") == "Thế kỷ 19", "uncoercible phải ở lại JSONB"
    on = db.get_entity(TEST_ID)["attributes"]
    assert on["ocop_star"] == 4 and on["producer"] == "HTX C3"
    assert on["address"] == "Ấp C3" and on["sac_phong"] == "tail"
    assert on["founding_year"] == "Thế kỷ 19"


def test_flag_off_write_keeps_full_jsonb():
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "C3 test",
                      "attributes": {"ocop_star": 3, "sac_phong": "tail"}})
    raw = _raw_attrs()
    assert raw.get("ocop_star") == 3 and raw.get("sac_phong") == "tail"


def test_cleanup_strips_only_when_column_matches(monkeypatch):
    # Ghi flag OFF: JSONB đầy đủ + cột đầy đủ (dual-write)
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "C3 test",
                      "attributes": {"ocop_star": 5, "producer": "HTX Khớp",
                                     "sac_phong": "tail", "founding_year": "Thế kỷ 19"}})
    before_read = db.get_entity(TEST_ID)["attributes"]
    stats = cleanup_run(apply=True)
    assert stats["keys_removed"] >= 2
    raw = _raw_attrs()
    assert "ocop_star" not in raw and "producer" not in raw
    assert raw.get("sac_phong") == "tail" and raw.get("founding_year") == "Thế kỷ 19"
    # Đọc flag ON sau dọn phải bằng đọc trước dọn
    monkeypatch.setenv("ENTITY_DETAILS_TABLES", "true")
    db.reload_entity_details_cache()
    after_read = db.get_entity(TEST_ID)["attributes"]
    assert after_read == before_read


def test_cleanup_noop_when_columns_empty():
    db.upsert_entity({"id": TEST_ID, "type": "product", "name": "C3 test",
                      "attributes": {"ocop_star": 4, "sac_phong": "tail"}})
    # Giả lập môi trường chưa backfill: xoá detail row (cột trống)
    with db._conn() as conn:
        db._execute(conn, f"DELETE FROM entity_product_details WHERE entity_id = {db._ph}", (TEST_ID,))
    with db._conn() as conn:
        row = db._row_to_dict(db._fetchone(conn, f"SELECT * FROM entities WHERE id = {db._ph}", (TEST_ID,)))
    keys = strippable_keys("product", {"ocop_star": 4, "sac_phong": "tail"}, row, {})
    assert keys == [], "cột trống → không được xoá gì (an toàn dev chưa backfill)"