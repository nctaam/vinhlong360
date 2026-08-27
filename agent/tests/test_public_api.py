"""Tests for public_api source-freshness (P0-6).

Freshness must be computed from the real, human-set verification date in
``attributes.verifiedAt`` only — never from a legacy top-level field or
``updatedAt`` (an import timestamp), so a bulk re-import can't make pages look
"freshly verified".
"""
from datetime import datetime, timedelta, timezone

from public_api import _build_source_freshness


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def test_fresh_from_recent_verifiedAt():
    e = {"attributes": {"verifiedAt": _days_ago(10)}, "updatedAt": _days_ago(500)}
    assert _build_source_freshness(e)["freshness_status"] == "fresh"


def test_unknown_when_no_verifiedAt_even_if_updated_recently():
    # An import timestamp must NOT make a page look "fresh".
    e = {"updatedAt": _days_ago(1)}
    assert _build_source_freshness(e)["freshness_status"] == "unknown"


def test_status_reflects_verifiedAt_not_updatedAt():
    # Old verification + brand-new import → status reflects the OLD verification.
    e = {"attributes": {"verifiedAt": _days_ago(400)}, "updatedAt": _days_ago(1)}
    assert _build_source_freshness(e)["freshness_status"] == "stale"


def test_no_dates_is_unknown():
    assert _build_source_freshness({})["freshness_status"] == "unknown"


def test_detail_source_freshness_projects_canonical_source_tier():
    result = _build_source_freshness(
        {
            "official": True,
            "source": {"title": "Cổng thông tin tỉnh Vĩnh Long"},
            "attributes": {"verifiedAt": _days_ago(10)},
        }
    )

    assert result["source_tier"] == "official"
    assert result["freshness_status"] == "fresh"


def test_top_level_verified_at_is_never_verification_authority() -> None:
    result = _build_source_freshness(
        {"verifiedAt": _days_ago(1), "updatedAt": _days_ago(1)}
    )
    assert result["verified_at"] is None
    assert result["days_since_verified"] is None
    assert result["freshness_status"] == "unknown"


def test_attribute_wins_when_top_level_value_conflicts() -> None:
    result = _build_source_freshness(
        {
            "verifiedAt": _days_ago(1),
            "updatedAt": _days_ago(1),
            "attributes": {"verifiedAt": _days_ago(400)},
        }
    )
    assert result["freshness_status"] == "stale"


def test_public_projection_removes_legacy_verified_at() -> None:
    from public_api import _project_public_entity_media

    projected = _project_public_entity_media(
        {"id": "entity-1", "verifiedAt": "2026-07-27T00:00:00Z"}
    )
    assert "verifiedAt" not in projected


# ── The revision the projection is serving (publication verification reads it) ──

def test_the_projection_states_the_revision_it_is_serving():
    from public_api import _public_entity_revision

    assert _public_entity_revision({"revision": 8}) == 8


def test_a_missing_or_unusable_revision_reads_as_the_first_one():
    from public_api import _public_entity_revision

    # Never None and never zero: verification compares this number, and a blank
    # would compare equal to nothing and quietly pass.
    for entity in ({}, {"revision": None}, {"revision": "x"}, {"revision": 0}):
        assert _public_entity_revision(entity) == 1


# ── Xếp hạng tìm kiếm: khớp tên phải thắng khớp summary ──────────────────────
# `_rank_search_entities` trước đây có 0 test, trong khi nó là thứ quyết định
# 5 dòng gợi ý ở ô tìm của trang chủ. Ba test dưới khoá đúng hành vi đã hỏng:
# gõ "dừa sáp" mà entity tên đúng "Dừa sáp" không lên đầu.

from public_api import _rank_search_entities  # noqa: E402


def _e(eid: str, name: str, summary: str = "", confidence: float = 0.85) -> dict:
    return {"id": eid, "name": name, "summary": summary, "confidence": confidence}


def test_ten_trung_khop_thang_summary_trung_khop():
    pool = [
        _e("cho-ben-tre", "Chợ Bến Tre", "nơi bán dừa sáp và nhiều đặc sản"),
        _e("festival", "Festival Dừa Sáp Cầu Kè", "lễ hội tôn vinh dừa sáp"),
        _e("dua-sap", "Dừa sáp"),
    ]
    ranked = _rank_search_entities(pool, "dừa sáp")
    assert ranked[0]["id"] == "dua-sap", (
        "entity tên đúng phải đứng #1, không để entity chỉ nhắc trong summary chen lên"
    )


def test_confidence_khong_lat_duoc_khop_ten():
    """confidence cao KHÔNG được kéo một kết quả lệch đề lên trên khớp tên chính xác."""
    pool = [
        _e("lac-de", "Chợ Bến Tre", "có bán dừa sáp", confidence=0.99),
        _e("dua-sap", "Dừa sáp", confidence=0.60),
    ]
    assert _rank_search_entities(pool, "dừa sáp")[0]["id"] == "dua-sap"


def test_xep_hang_gan_nhan_nguon_de_truy_vet():
    ranked = _rank_search_entities([_e("a", "Dừa sáp")], "dừa sáp")
    assert ranked[0]["_search_meta"]["rank_source"] == "lexical"


# ── Canary: dữ liệu sự kiện có HẠN DÙNG ──────────────────────────────────────
# _select_upcoming_events lọc `today <= date_start <= cutoff`. Mã ĐÚNG, nhưng
# toàn bộ 67 event trong kho đều ghim năm 2026 (đo 2026-08-27: 59/59 date_start
# có năm = 2026). Từ 01/01/2027 pool rỗng VĨNH VIỄN và mục thời-vụ — trụ cột
# "trang đang sống" — im lặng biến mất, không lỗi, không log, không ai biết.
#
# Không đẩy ngày sang năm sau: nguồn chỉ nói 2026, tự suy 2027 là bịa (§1.7),
# và chỉ 2/67 event có cờ `frequency` nên không suy được cái nào thường niên.
# Thay vào đó: canary này ĐỎ khi kho sắp hết hạn, biến sự cố-2027 thành việc
# phải làm từ hôm nay. Sửa dữ liệu cần backup B1 + chỉ đạo chủ dự án (§4).

def test_canary_kho_su_kien_chua_het_han():
    import json
    from datetime import date, datetime
    from pathlib import Path

    data_path = Path(__file__).resolve().parents[2] / "web" / "data.json"
    if not data_path.exists():
        import pytest
        pytest.skip("web/data.json không có ở môi trường này")

    raw = json.loads(data_path.read_text(encoding="utf-8"))
    entities = raw.get("entities", raw) if isinstance(raw, dict) else raw
    today = date.today()
    tuong_lai = []
    for e in entities:
        if e.get("type") != "event":
            continue
        ds = (e.get("attributes") or {}).get("date_start")
        if not ds:
            continue
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if d >= today:
            tuong_lai.append((d, e.get("id")))

    assert tuong_lai, (
        "KHO SỰ KIỆN ĐÃ HẾT HẠN: không còn event nào có date_start >= hôm nay. "
        "Mục thời-vụ của trang chủ sẽ rỗng vĩnh viễn. Cần đợt cập nhật lịch sự "
        "kiện (task dữ liệu: backup B1 + chỉ đạo chủ dự án theo §4)."
    )
    xa_nhat = max(tuong_lai)[0]
    con_lai = (xa_nhat - today).days
    assert con_lai >= 60, (
        f"KHO SỰ KIỆN SẮP HẾT HẠN: sự kiện xa nhất còn {con_lai} ngày "
        f"({xa_nhat.isoformat()}). Lên lịch cập nhật trước khi mục thời-vụ im lặng."
    )
