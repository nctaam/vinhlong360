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


# ── Giờ Việt Nam ở backend + măng-sét ngày âm–dương ─────────────────────────
# `datetime.now(timezone.utc).month` cho SAI tháng trong 7 tiếng mỗi lần sang
# tháng: 31/08 23:00 UTC đã là 01/09 giờ VN, mà payload vẫn dựng mùa vụ tháng 8.

from datetime import datetime as _dt, timezone as _tz  # noqa: E402

from public_api import _TZ_VIETNAM, _build_masthead  # noqa: E402


def _vn(*args):
    return _dt(*args, tzinfo=_tz.utc).astimezone(_TZ_VIETNAM)


def test_bien_thang_utc_khong_keo_lui_thang_viet_nam():
    assert _vn(2026, 8, 31, 23, 0).month == 9, "23:00 UTC ngày 31/08 đã là 01/09 giờ VN"
    assert _vn(2026, 8, 31, 16, 0).month == 8, "16:00 UTC vẫn là 31/08 giờ VN"


def test_mang_set_khop_oracle_am_lich():
    m = _build_masthead(_vn(2026, 8, 27, 3, 0))
    assert m["solar_label"] == "Thứ Năm, 27/08/2026"
    assert m["lunar_label"] == "15 tháng 7 năm Bính Ngọ"


def test_mang_set_goi_dung_ten_thang_gieng_va_chap():
    # 17/02/2026 là mồng 1 tháng Giêng Bính Ngọ (Tết); 06/02/2027 là 30 tháng Chạp.
    assert "tháng Giêng" in _build_masthead(_vn(2026, 2, 17, 3, 0))["lunar_label"]
    assert "tháng Chạp" in _build_masthead(_vn(2027, 2, 5, 3, 0))["lunar_label"]


def test_mang_set_luon_du_hai_truong():
    m = _build_masthead(_vn(2026, 8, 27, 3, 0))
    assert set(m) == {"solar_label", "lunar_label"}
    assert all(isinstance(v, str) and v for v in m.values())


# ── «Tin chính đặc sản»: luật chọn phải TẤT ĐỊNH và sạch §1.6 ───────────────
# Mục này là điểm dừng thị giác thứ 2 của trang chủ. Nó phải đứng yên suốt
# tháng (không lật theo lượt bấm) và không bao giờ đưa lên trần một entity gọi
# tên tỉnh cũ như đang tồn tại.

from public_api import (  # noqa: E402
    _has_stale_geography,
    _lead_rank_key,
    _product_lead_eligible,
    _select_product_lead,
)


def _sp(eid, name="Sản phẩm thử", summary=None, **kw):
    """Product hợp lệ tối thiểu: có ảnh, summary trong khoảng, tên đủ ngắn."""
    e = {
        "id": eid, "type": "product", "name": name,
        "summary": summary if summary is not None else ("x" * 150),
        "images": ["/img/entities/" + eid + ".webp"],
        "attributes": {},
    }
    e.update(kw)
    return e


def test_lead_loai_entity_to_chuc_bang_id():
    """Blocklist khoá bằng ID: regex tên bắt hụt tên lai và giết oan tên hợp lệ."""
    to_chuc = _sp("cua-hang-ocop-vung-liem", name="Cửa hàng OCOP Vũng Liêm")
    assert _product_lead_eligible(to_chuc) is False
    # Ngược lại: sản phẩm có nhắc HTX trong summary vẫn hợp lệ.
    sp = _sp("ca-phi-thu", summary="Sản phẩm do HTX Thủy sản sinh thái sản xuất. " + "x" * 100)
    assert _product_lead_eligible(sp) is True


def test_lead_chan_dia_danh_cu_nhung_cho_qua_khi_ghi_ro_cu():
    assert _has_stale_geography({"name": "A", "summary": "đặc sản huyện Cầu Kè"}) is True
    assert _has_stale_geography({"name": "A", "summary": "sản xuất tại Bến Tre"}) is True
    # "(cũ)" là cách viết ĐÚNG chuẩn §1.6 — không được giết oan.
    assert _has_stale_geography({"name": "A", "summary": "tại tỉnh Trà Vinh (cũ)"}) is False


def test_lead_tat_dinh_khong_phu_thuoc_thu_tu_dau_vao():
    pool = [_sp(f"sp-{i}", name=f"Sản phẩm {i}") for i in range(6)]
    goc = [_select_product_lead(pool, m, set())["id"] for m in range(1, 13)]
    for seed in range(3):
        xao = pool[:]
        __import__("random").Random(seed).shuffle(xao)
        assert [_select_product_lead(xao, m, set())["id"] for m in range(1, 13)] == goc


def test_lead_xoay_vong_theo_thang_khong_dung_yen_mot_entity():
    pool = [_sp(f"sp-{i}", name=f"Sản phẩm {i}") for i in range(4)]
    chon = {_select_product_lead(pool, m, set())["id"] for m in range(1, 13)}
    assert len(chon) == 4, "kho 4 ứng viên thì 12 tháng phải chạm cả 4, không đứng yên một cái"


def test_lead_ton_trong_exclude_ids_va_tra_none_khi_het_ung_vien():
    pool = [_sp("chi-mot")]
    assert _select_product_lead(pool, 5, set())["id"] == "chi-mot"
    assert _select_product_lead(pool, 5, {"chi-mot"}) is None
    assert _select_product_lead([], 5, set()) is None


def test_lead_khoa_xep_hang_uu_tien_sao_ocop_roi_moi_toi_do_dai():
    cao = _sp("cao", attributes={"ocop_star": 5}, summary="x" * 130)
    thap = _sp("thap", attributes={"ocop_star": 3}, summary="x" * 390)
    assert _lead_rank_key(cao) < _lead_rank_key(thap), "5 sao phải đứng trước 3 sao dù summary ngắn hơn"


def test_lead_loai_ten_qua_dai_va_summary_ngoai_khoang():
    assert _product_lead_eligible(_sp("a", name="x" * 43)) is False
    assert _product_lead_eligible(_sp("b", summary="x" * 119)) is False
    assert _product_lead_eligible(_sp("c", summary="x" * 401)) is False
    assert _product_lead_eligible({**_sp("d"), "images": []}) is False


# ── Hợp đồng API: HomepageResponse mang được hai trường mới ─────────────────
# Import cấp module (không lồng trong hàm) — R20.7 ghép test↔module bằng AST
# import, lời gọi lúc chạy thì cây cú pháp không thấy.
import api_schemas  # noqa: E402


def test_homepage_response_mang_duoc_tin_chinh_dac_san():
    r = api_schemas.HomepageResponse(
        product_lead={"id": "x", "name": "Thử"}, products_total=218,
    )
    assert r.product_lead["id"] == "x"
    assert r.products_total == 218


def test_homepage_response_hai_truong_moi_deu_khuyet_duoc():
    """Payload cũ (không có hai trường) vẫn hợp lệ — thêm trường là ADDITIVE."""
    r = api_schemas.HomepageResponse()
    assert r.product_lead is None
    assert r.products_total is None


# ── Âm lịch của sự kiện: DERIVE từ date_start, không đọc lunar_date ─────────
# Ngày của một entity nằm ở SÁU Ô (lunar_date, date_start, date_end, summary,
# description, season). Sửa một ô làm năm ô kia nói ngược — mâu thuẫn công khai
# còn tệ hơn trạng thái lệch ban đầu (CLAUDE.md §5c). Suy từ ngày dương lúc
# dựng payload thì chỉ có MỘT nguồn sự thật, và nó là oracle Python.

from public_api import _event_lunar_label, _lunar_phrase  # noqa: E402


def test_am_lich_su_kien_suy_tu_ngay_duong():
    assert _event_lunar_label({"attributes": {"date_start": "2026-09-15"}}) == "5 tháng 8 năm Bính Ngọ"
    assert _event_lunar_label({"attributes": {"date_start": "2026-09-20"}}) == "10 tháng 8 năm Bính Ngọ"


def test_am_lich_su_kien_bo_qua_lunar_date_co_san():
    """Có sẵn lunar_date SAI trong dữ liệu cũng không được dùng — chỉ suy từ ngày dương."""
    e = {"attributes": {"date_start": "2026-09-15", "lunar_date": "mồng 9 tháng 9"}}
    assert _event_lunar_label(e) == "5 tháng 8 năm Bính Ngọ"


def test_am_lich_su_kien_khuyet_em_khi_ngay_hong():
    for attrs in ({}, {"date_start": None}, {"date_start": "xxx"}, {"date_start": "2026-13-45"}):
        assert _event_lunar_label({"attributes": attrs}) is None
    assert _event_lunar_label({}) is None


def test_am_lich_ngoai_dai_oracle_thi_tra_none_chu_khong_doan():
    """Oracle khai dải 1200–2199 (lunar_calendar.SUPPORTED_YEAR_*). Ngoài dải thì
    trả None chứ KHÔNG ngoại suy — thà khuyết còn hơn in một ngày âm bịa."""
    assert _event_lunar_label({"attributes": {"date_start": "1199-01-01"}}) is None
    assert _event_lunar_label({"attributes": {"date_start": "2200-01-01"}}) is None
    # Trong dải thì vẫn tính, kể cả năm xa — guard theo dải THẬT của oracle,
    # không theo phỏng đoán.
    assert _event_lunar_label({"attributes": {"date_start": "1500-01-01"}}) is not None


def test_lunar_phrase_goi_dung_ten_thang_dac_biet():
    assert _lunar_phrase(6, 2, 2027).startswith("1 tháng Giêng")   # mồng một Tết Đinh Mùi
    assert "năm Đinh Mùi" in _lunar_phrase(6, 2, 2027)
