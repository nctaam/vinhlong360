"""
Characterization test cho data_quality._apply_reviewed_records — áp bản ghi
ĐÃ DUYỆT vào DB (nguồn sự thật), ghi apply-history nguồn "review_decision".

Harness học từ agent/tests/test_data_quality.py: DB là SQLite tạm trong
tmp_path (fixture isolated_sqlite_db), monkeypatch data_quality.db +
data_quality.BURST_DIR — KHÔNG chạm DB thật, không chạm thư mục burst thật.

Khoá cả các nhánh từ-chối: entity không tồn tại, gợi ý không hợp lệ, giá trị
đã hiện hành, toạ độ trùng entity khác (kể cả trùng NGAY TRONG cùng một đợt).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data_quality


@pytest.fixture
def dq_env(tmp_path, monkeypatch, isolated_sqlite_db):
    """(db tạm, burst dir tạm) đã nối vào data_quality."""
    burst = tmp_path / "burst"
    monkeypatch.setattr(data_quality, "db", isolated_sqlite_db)
    monkeypatch.setattr(data_quality, "BURST_DIR", burst)
    return isolated_sqlite_db, burst


def _source_record(entity_id="e1", url="https://example.com/bao"):
    return {
        "entity_id": entity_id,
        "field": "source",
        "suggested_value": {"title": "Báo Vĩnh Long", "url": url},
        "stream": "source",
        "bucket": "needs_review",
        "evidence_urls": [url],
        "reason": "nguồn báo chính thức",
    }


def _coord_record(entity_id, coords):
    return {
        "entity_id": entity_id,
        "field": "coordinates",
        "suggested_value": coords,
        "stream": "location",
    }


def test_ap_dung_source_ghi_thang_db_va_history(dq_env):
    tdb, burst = dq_env
    tdb.upsert_entity({"id": "e1", "name": "Entity 1", "type": "product"})
    record = _source_record()

    result = data_quality._apply_reviewed_records([record], reviewer="tam", dry_run=False)

    assert result["dry_run"] is False
    assert result["batch_id"].startswith("dq_review_")
    assert result["applied_count"] == 1
    assert result["skipped"] == []
    expected_cid = data_quality.candidate_id(record)
    assert result["applied"] == [
        {"candidate_id": expected_cid, "entity_id": "e1", "field": "source"}
    ]

    change = result["changes"][0]
    # entity chưa có source: DB chuẩn hoá thành list rỗng khi lưu → before là []
    assert change["before"] == []
    assert change["after"] == {"title": "Báo Vĩnh Long", "url": "https://example.com/bao"}
    assert change["reviewer"] == "tam"
    assert change["review_bucket"] == "needs_review"
    assert change["evidence_urls"] == ["https://example.com/bao"]
    assert change["entity_name"] == "Entity 1"

    # ghi THẲNG vào DB (source được chuẩn hoá thành list[dict] khi lưu)
    src = tdb.get_entity("e1")["source"]
    assert (src[0]["url"] if isinstance(src, list) else src["url"]) == "https://example.com/bao"

    history = data_quality.load_apply_history(output_dir=burst)
    assert history["total"] == 1
    entry = history["history"][0]
    assert entry["record_type"] == "apply"
    assert entry["source"] == "review_decision"
    assert entry["reviewer"] == "tam"
    assert entry["batch_id"] == result["batch_id"]
    assert entry["applied_count"] == 1
    assert entry["skipped_count"] == 0


def test_dry_run_tinh_thay_doi_nhung_khong_ghi_gi(dq_env):
    tdb, burst = dq_env
    tdb.upsert_entity({"id": "e1", "name": "Entity 1", "type": "product"})

    result = data_quality._apply_reviewed_records([_source_record()], dry_run=True)

    assert result["dry_run"] is True
    assert result["applied_count"] == 1
    assert result["changes"][0]["after"]["url"] == "https://example.com/bao"
    # DB không đổi, history không sinh ra
    assert tdb.get_entity("e1").get("source") in (None, {}, [])
    assert data_quality.load_apply_history(output_dir=burst)["total"] == 0


def test_entity_khong_ton_tai_bi_skip_va_khong_co_history(dq_env):
    _tdb, burst = dq_env
    record = _source_record(entity_id="ghost")

    result = data_quality._apply_reviewed_records([record], dry_run=False)

    assert result["applied_count"] == 0
    assert result["changes"] == []
    assert result["skipped"] == [
        {"candidate_id": data_quality.candidate_id(record), "reason": "entity not found"}
    ]
    # không có gì được áp → không ghi history
    assert data_quality.load_apply_history(output_dir=burst)["total"] == 0


def test_goi_y_khong_hop_le_skip_kem_entity_id_va_field(dq_env):
    tdb, _burst = dq_env
    tdb.upsert_entity({"id": "e1", "name": "Entity 1", "type": "product"})
    record = _source_record(url="khong-phai-url")  # url hỏng → after=None

    result = data_quality._apply_reviewed_records([record], dry_run=False)

    # đường review gắn thêm entity_id + field vào skip (khác đường auto-apply)
    assert result["skipped"] == [{
        "candidate_id": data_quality.candidate_id(record),
        "entity_id": "e1",
        "field": "source",
        "reason": "invalid suggestion",
    }]


def test_field_ngoai_source_coordinates_luon_la_invalid(dq_env):
    tdb, _burst = dq_env
    tdb.upsert_entity({"id": "e1", "name": "Entity 1", "type": "product"})
    record = {"entity_id": "e1", "field": "placeId",
              "suggested_value": "xa-nao-do", "stream": "placeid"}

    result = data_quality._apply_reviewed_records([record], dry_run=False)

    assert result["applied_count"] == 0
    assert result["skipped"][0]["reason"] == "invalid suggestion"


def test_gia_tri_da_hien_hanh_thi_skip(dq_env):
    tdb, _burst = dq_env
    tdb.upsert_entity({"id": "e1", "name": "Entity 1", "type": "product",
                       "coordinates": [10.1, 106.3]})
    record = _coord_record("e1", [10.1, 106.3])

    result = data_quality._apply_reviewed_records([record], dry_run=False)

    assert result["applied_count"] == 0
    assert result["skipped"] == [{
        "candidate_id": data_quality.candidate_id(record),
        "entity_id": "e1",
        "field": "coordinates",
        "reason": "value already current",
    }]


def test_toa_do_trung_entity_khac_bi_chan(dq_env):
    tdb, _burst = dq_env
    tdb.upsert_entity({"id": "own-a", "name": "Chủ toạ độ", "type": "attraction",
                       "coordinates": [10.2, 106.4]})
    tdb.upsert_entity({"id": "e-b", "name": "Entity B", "type": "product"})
    record = _coord_record("e-b", [10.2, 106.4])

    result = data_quality._apply_reviewed_records([record], dry_run=False)

    assert result["applied_count"] == 0
    skip = result["skipped"][0]
    assert skip["reason"] == "duplicate coordinates"
    assert skip["duplicate_of"] == "own-a"
    assert skip["entity_id"] == "e-b"
    assert skip["coordinates"] == [10.2, 106.4]
    # DB của e-b không bị gán toạ độ trùng
    assert tdb.get_entity("e-b").get("coordinates") in (None, [])


def test_hai_ban_ghi_cung_toa_do_trong_mot_dot_chi_ap_ban_dau(dq_env):
    tdb, burst = dq_env
    tdb.upsert_entity({"id": "b1", "name": "B1", "type": "attraction"})
    tdb.upsert_entity({"id": "b2", "name": "B2", "type": "attraction"})
    records = [_coord_record("b1", [10.15, 106.25]),
               _coord_record("b2", [10.15, 106.25])]

    result = data_quality._apply_reviewed_records(records, reviewer="tam", dry_run=False)

    assert result["applied_count"] == 1
    assert result["skipped_count"] == 1
    assert result["applied"][0]["entity_id"] == "b1"
    assert result["changes"][0]["before"] is None
    assert result["changes"][0]["after"] == [10.15, 106.25]
    # bản ghi thứ hai vấp chủ toạ độ vừa được nhận NGAY trong đợt
    assert result["skipped"][0]["reason"] == "duplicate coordinates"
    assert result["skipped"][0]["duplicate_of"] == "b1"

    assert tdb.get_entity("b1")["coordinates"] == [10.15, 106.25]
    assert tdb.get_entity("b2").get("coordinates") in (None, [])

    history = data_quality.load_apply_history(output_dir=burst)
    assert history["total"] == 1
    assert history["history"][0]["applied_count"] == 1
    assert history["history"][0]["skipped_count"] == 1
