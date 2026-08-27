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
    """CHỈ chốt tiền đề của các test đồng hồ phía dưới — KHÔNG phải rào chống
    hồi quy.

    Bản đầu của test này được viết như thể nó canh lỗi múi giờ, nhưng nó chỉ
    khẳng định số học `datetime.astimezone` của stdlib: hoàn nguyên mã sản phẩm
    về UTC thì nó vẫn xanh. Rào THẬT nằm ở
    `test_mang_set_va_dem_nguoc_dung_CHUNG_mot_dong_ho` và
    `test_su_kien_da_qua_theo_gio_VN_thi_bi_loai` — hai test đó chạy thẳng
    `_build_homepage_payload` với đồng hồ đóng băng và đã được kiểm là ĐỎ trên
    mã cũ."""
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


# ── Ngày âm của SỰ KIỆN: cố ý KHÔNG có trên payload trang chủ ───────────────
# C1 từng suy nhãn đó từ attributes.date_start, lập luận "không đọc lunar_date
# thì né được bẫy sáu-ô §5c". Lập luận sai vế: không ĐỌC thì tránh được việc
# SỬA nó, nhưng không tránh được việc NÓI NGƯỢC nó — /le-hoi vẫn in ô lunar_date
# cho cùng lễ hội, và đo lại thấy 24/36 sự kiện lệch, có ca lệch cả tháng âm.
#
# Bảng quyết định của dự án (docs/2026-08-07-bang-quyet-dinh-ngay-le-hoi-am-duong.md)
# phân loại 67 event: 12 ca KHỚP mọi trường · 3 ca date_start CHÍNH LÀ ô sai ·
# 14 ca tự mâu thuẫn, ghi rõ "KHÔNG giải được từ dữ liệu — phải có người chốt".
# Suy từ date_start là khuếch đại đúng ô hỏng. Mở lại được khi chủ dự án chốt
# bảng đó — không phải bằng cách viết lại luật suy.

from public_api import _finalize_homepage_sections, _lunar_phrase  # noqa: E402


def test_payload_KHONG_gan_nhan_am_lich_cho_tung_su_kien():
    """Rào chặn C1 quay lại bằng cửa sau.

    Ghim ở tầng payload chứ không ở tầng hàm: hàm nào biến mất thì test kiểu
    "hàm trả None" tự bốc hơi cùng nó, còn rào này vẫn đứng."""
    events = [
        {"id": "a", "_days_until": 3, "attributes": {"date_start": "2026-09-15"}},
        {"id": "b", "_days_until": 0,
         "attributes": {"date_start": "2026-11-22", "lunar_date": "Rằm tháng 10"}},
    ]
    _finalize_homepage_sections([], events)
    for e in events:
        assert "lunar_label" not in e, (
            "sự kiện không được mang nhãn âm lịch riêng khi /le-hoi vẫn in "
            "attributes.lunar_date — hai bề mặt sẽ nói hai ngày khác nhau"
        )
    assert [e["days_until"] for e in events] == [3, 0]


def test_mang_set_VAN_in_ngay_am_cua_hom_nay():
    """Rút lui đúng phạm vi: măng-sét không dính bẫy sáu-ô vì ngày âm của HÔM NAY
    là ngày lịch, không phải dữ liệu entity — không có ô nào để nói ngược."""
    assert _build_masthead(_vn(2026, 8, 27, 9, 0))["lunar_label"]


def test_lunar_phrase_goi_dung_ten_thang_dac_biet():
    assert _lunar_phrase(6, 2, 2027).startswith("1 tháng Giêng")   # mồng một Tết Đinh Mùi
    assert "năm Đinh Mùi" in _lunar_phrase(6, 2, 2027)


# ─────────────────────────────────────────────────────────────────────────
# C2 — tin dẫn tín hiệu: backend chấm ĐIỀU KIỆN, không chọn người
# ─────────────────────────────────────────────────────────────────────────
from public_api import _mark_signal_lead  # noqa: E402


def _sig(eid, name, url=None, summary=""):
    e = {"id": eid, "name": name, "summary": summary}
    if url:
        e["image_descriptors"] = [{"url": url, "alt": name}]
    return e


def _ok(section):
    return [e["id"] for e in section if e.get("signal_lead_ok")]


def test_tin_dan_bo_qua_hang_khong_co_anh():
    """Không ảnh thì không đủ điều kiện — bìa sinh không được làm bậc 3."""
    events = [_sig("khong-anh", "Ngày hội Thanh Trà")]
    seasonal = [_sig("co-anh", "Mật ong rừng", "/img/mua.webp")]
    _mark_signal_lead(events, seasonal)
    assert _ok(events) == []
    assert _ok(seasonal) == ["co-anh"]


def test_tin_dan_cham_MOI_ung_vien_chu_khong_chon_mot():
    """Backend KHÔNG chọn: nó không biết frontend sẽ loại ai.

    `homeNocturnePresentation.remaining()` bỏ các entity đã bị hero/spotlight/
    quick-decision tiêu thụ. Chấm đúng một người thì người đó có thể bị ăn mất
    và trang ra 0 tin dẫn — đã đo thấy đúng như vậy trước khi tách vai.
    """
    seasonal = [_sig(f"s{i}", f"Đặc sản {i}", f"/img/{i}.webp") for i in range(4)]
    _mark_signal_lead([], seasonal)
    assert _ok(seasonal) == ["s0", "s1", "s2", "s3"]


def test_tin_dan_chan_dia_danh_cu_tran():
    """§1.6: dựng lớn một cái tên còn mang địa danh cũ trần là khuếch đại
    đúng thứ đang phải sửa."""
    seasonal = [
        _sig("cu", "Vườn dừa sinh thái Cầu Kè Trà Vinh", "/img/a.webp"),
        _sig("huyen", "Hội thi đờn ca tài tử huyện Long Hồ", "/img/b.webp"),
        _sig("sach", "Mật ong rừng Bản Mỹ Long Nam", "/img/c.webp"),
    ]
    _mark_signal_lead([], seasonal)
    assert _ok(seasonal) == ["sach"]


def test_tin_dan_van_nhan_cach_viet_lich_su_dung_chuan():
    """'Trà Vinh (cũ)' là cách viết ĐÚNG §1.6 — không được giết oan."""
    seasonal = [_sig("ok", "Bánh tét Trà Cuôn", "/img/a.webp",
                     summary="Đặc sản vùng Trà Vinh (cũ), nay thuộc tỉnh Vĩnh Long.")]
    _mark_signal_lead([], seasonal)
    assert _ok(seasonal) == ["ok"]


def test_tin_dan_khuyet_em_khi_khong_ai_du_dieu_kien():
    events = [_sig("a", "Ngày hội Thanh Trà")]
    seasonal = [_sig("b", "Ốc lác hấp lá gừng")]
    _mark_signal_lead(events, seasonal)
    assert _ok(events) + _ok(seasonal) == []


# ─────────────────────────────────────────────────────────────────────────
# MỘT đồng hồ cho cả payload — giờ Việt Nam, không phải UTC
# ─────────────────────────────────────────────────────────────────────────
# Test cũ (`test_bien_thang_utc_khong_keo_lui_thang_viet_nam`) là test RỖNG: nó
# khẳng định `datetime(...,utc).astimezone(_TZ_VIETNAM).month`, tức số học của
# stdlib. Hoàn nguyên mã sản phẩm về UTC thì nó vẫn xanh. Vòng thẩm tra đối
# kháng bắt được đúng chỗ đó, và đúng: B1a tuyên bố đóng lỗi 7 tiếng nhưng chỉ
# đổi `month`, còn `today` của cửa sổ sự kiện và `_event_is_past` vẫn đọc UTC.
#
# Test dưới đây CHẠY THẲNG `_build_homepage_payload` với đồng hồ bị đóng băng,
# nên nó đỏ nếu ai đó trả một dòng nào về UTC.
import asyncio  # noqa: E402

import public_api as _pa  # noqa: E402


def _dung_dong_ho(monkeypatch, ngay_gio_vn):
    monkeypatch.setattr(_pa, "_today_vietnam", lambda: ngay_gio_vn)


def _kho_su_kien():
    def ent(eid, **kw):
        base = {"id": eid, "name": eid, "type": "event", "summary": "x" * 130,
                "attributes": {}, "area": "vinh-long"}
        base["attributes"].update(kw)
        return base
    return [
        ent("hom-nay", date_start="2026-09-15", date_end="2026-09-15", month=9),
        ent("hom-qua", date_start="2026-09-14", date_end="2026-09-14", month=9),
        ent("tuan-sau", date_start="2026-09-22", date_end="2026-09-22", month=9),
    ]


def _chay_payload(monkeypatch, ngay_gio_vn, entities):
    _dung_dong_ho(monkeypatch, ngay_gio_vn)
    monkeypatch.setattr(_pa.db, "list_entities", lambda **kw: [dict(e) for e in entities])
    monkeypatch.setattr(_pa.db, "list_itineraries", lambda *a, **kw: [])
    monkeypatch.setattr(_pa.db, "stats", lambda *a, **kw: {})
    monkeypatch.setattr(_pa, "_enrich_place", lambda *a, **kw: None)
    return asyncio.run(_pa._build_homepage_payload(ngay_gio_vn.month))


def test_mang_set_va_dem_nguoc_dung_CHUNG_mot_dong_ho(monkeypatch):
    """01:00 sáng 15/09 giờ VN = 18:00Z ngày 14/09.

    Trước khi vá: măng-sét in "Thứ Ba, 15/09/2026" (giờ VN) trong khi sự kiện
    ngày 15/09 nhận days_until=1 → index.vue render "Ngày mai". Người dân mở
    trang vào sáng ngày khai hội bị site bảo mai mới diễn ra. Khung hỏng lặp
    lại 7 tiếng MỖI NGÀY (17:00–23:59Z).
    """
    payload = _chay_payload(monkeypatch, _vn(2026, 9, 15, 1, 0), _kho_su_kien())

    assert payload["masthead"]["solar_label"] == "Thứ Ba, 15/09/2026"
    hom_nay = [e for e in payload["upcoming_events"] if e["id"] == "hom-nay"]
    assert hom_nay, "sự kiện của HÔM NAY (giờ VN) phải nằm trong cửa sổ sắp diễn ra"
    assert hom_nay[0]["days_until"] == 0, (
        "days_until phải tính theo cùng đồng hồ với măng-sét; =1 nghĩa là "
        "cửa sổ sự kiện đã tụt về UTC"
    )


def test_su_kien_da_qua_theo_gio_VN_thi_bi_loai(monkeypatch):
    """`_event_is_past` cũng phải dùng giờ VN.

    Lúc 18:00Z 14/09 (= 01:00 15/09 VN) một lễ hội kết thúc 14/09 ĐÃ QUA theo
    giờ Việt Nam, nhưng theo UTC thì vẫn là "hôm nay" nên không bị loại.
    """
    payload = _chay_payload(monkeypatch, _vn(2026, 9, 15, 1, 0), _kho_su_kien())
    ids = {e["id"] for e in payload["upcoming_events"]}
    assert "hom-qua" not in ids
    assert "tuan-sau" in ids


def test_dong_ho_UTC_va_VN_that_su_khac_ngay_o_khung_gio_nay():
    """Chốt tiền đề của hai test trên — nếu không thì chúng vô nghĩa."""
    utc = _dt(2026, 9, 14, 18, 0, tzinfo=_tz.utc)
    assert utc.date() != utc.astimezone(_TZ_VIETNAM).date()


# ─────────────────────────────────────────────────────────────────────────
# Cổng §1.6 phải fail-CLOSED — mọi ca dưới đây là chuỗi THẬT trong dữ liệu
# ─────────────────────────────────────────────────────────────────────────
# Bản đầu dò dấu lịch sử bằng r"\b(cu|truoc)\b" SAU khi bỏ dấu, nên "cù", "Cứ",
# "Trà Cú" đều cấp token "cu" và được tính là đã ghi "cũ". Vòng thẩm tra đối
# kháng quét web/data.json bằng chính hàm này: 8 entity gọi tỉnh cũ trần vẫn qua
# cổng. Đây là cổng §1.6 DUY NHẤT của cả _product_lead_eligible lẫn
# _mark_signal_lead, nên nó fail-open là mở toang cả hai.

from public_api import _fold_ascii  # noqa: E402  (_has_stale_geography đã import ở trên)


def test_co_16_khong_nham_cu_lao_tra_cu_cu_lam_dau_chu_cu():
    """Ba ca CỨU OAN thật — không ca nào có chữ «cũ» ở đâu cả."""
    assert _has_stale_geography({
        "name": "Nhãn xuồng cơm vàng",
        "summary": "Trái ngọt, trồng nhiều ở Bến Tre và cù lao An Bình."}) is True
    assert _has_stale_geography({
        "name": "Mắm Còng Bến Tre",
        "summary": "Cứ mười con còng thì làm được một hũ mắm."}) is True
    assert _has_stale_geography({
        "name": "Bánh tét",
        "summary": "Món đặc sản của vùng Trà Cú - Trà Vinh, gói bằng lá chuối."}) is True


def test_co_16_van_nhan_cach_viet_dung_chuan():
    """Fail-closed KHÔNG được biến thành giết-oan."""
    assert _has_stale_geography({
        "name": "Kẹo dừa",
        "summary": "Đặc sản vùng Bến Tre (cũ), nay thuộc tỉnh Vĩnh Long."}) is False
    assert _has_stale_geography({
        "name": "Vicosap",
        "summary": "chiếm 4 trong 6 sản phẩm OCOP 5 sao của tỉnh Trà Vinh (cũ)."}) is False
    assert _has_stale_geography({
        "name": "Bánh tét",
        "summary": "Vùng này TRƯỚC 7-2025 thuộc tỉnh Trà Vinh."}) is False


def test_co_16_bat_ten_hien_thi_goi_tinh_cu_tran():
    """Tên hiển thị cũng bị soi, không riêng summary — đây là ca đang SỐNG
    trong dữ liệu và từng được `_mark_signal_lead` chấm đủ điều kiện."""
    assert _has_stale_geography({
        "name": "Mật hoa dừa và đường hoa dừa Trà Vinh (OCOP 5 sao)",
        "summary": "Sản phẩm OCOP đạt 5 sao cấp quốc gia."}) is True


def test_co_16_van_bat_cap_huyen():
    assert _has_stale_geography({"name": "Hội thi đờn ca huyện Long Hồ", "summary": ""}) is True
    assert _has_stale_geography({
        "name": "Bưởi Năm Roi", "summary": "Trồng ở xã Mỹ Hoà, tỉnh Vĩnh Long."}) is False


def test_fold_ascii_bao_toan_do_dai():
    """Cửa sổ ±40 tìm chỉ số trên chuỗi bỏ dấu rồi cắt trên chuỗi GỐC. Lệch một
    ký tự là cắt trượt cửa sổ, và cổng lại hỏng theo kiểu khác."""
    for t in ("Đường hoa dừa Trà Vinh", "cù lao An Bình", "Bến Tre (cũ)",
              "Nguyễn Đình Chiểu", "Ốc lác hấp lá gừng"):
        assert len(_fold_ascii(t)) == len(t), t
    assert _fold_ascii("Đường") == "Duong"


def test_co_16_dau_lich_su_phai_THUOC_VE_ten_tinh():
    """Ba ca THẬT nơi dấu "cũ"/"trước" thuộc về một danh từ KHÁC.

    Bản vá đầu (dò dấu trên chuỗi còn dấu) đã bịt lỗ "cù/Cứ/Trà Cú", nhưng cửa
    sổ ±40 vẫn nhận dấu của bất kỳ danh từ nào lọt vào đó. Đo trên web/data.json:
    3 entity gọi tỉnh cũ TRẦN mà vẫn qua cổng nhờ dấu của thứ khác.

    Nay: chữ "cũ" trần chỉ tính khi BÁM NGAY SAU tên tỉnh; còn cụm chỉ đích danh
    việc sáp nhập ("trước 7-2025", "trước khi sáp nhập") thì tính ở bất kỳ đâu
    trong cửa sổ, vì chúng không mang nghĩa nào khác.
    """
    def ban(txt):
        return _has_stale_geography({"name": "x", "summary": txt})

    # Dấu thuộc về danh từ khác → vẫn là BẨN.
    assert ban("Khu vực gần bến phà Hàm Luông (cũ), TP. Bến Tre.") is True
    assert ban("Siêu thị thuộc chuỗi GO! (trước đây là Big C) Bến Tre.") is True
    assert ban("Ranh giới giữa Vĩnh Long, Bến Tre và Trà Vinh trước khi đổ ra biển.") is True

    # Dấu thuộc về TÊN TỈNH → sạch.
    assert ban("Đạt OCOP 4 sao cấp tỉnh Trà Vinh (cũ), sản phẩm tiêu biểu.") is False
    assert ban("Vùng biển Ba Động ở khu vực Trà Vinh cũ (nay thuộc Vĩnh Long).") is False
    # Mốc sáp nhập đặt TRƯỚC tên tỉnh cũng là lối viết hợp lệ.
    assert ban("Trước 7-2025 nơi này thuộc tỉnh Trà Vinh.") is False


# ─────────────────────────────────────────────────────────────────────────
# Trần quét-toàn-kho: chạm trần phải NÓI RA
# ─────────────────────────────────────────────────────────────────────────
# Ba truy vấn (trang chủ, ghim bản đồ, lịch sự kiện) lấy một lát rồi tự xếp
# hạng/lọc — không phân trang. Khi kho vượt trần, phần dôi biến mất LẶNG LẼ:
# không lỗi, không log, chỉ là vài entity không bao giờ lên trang và không ai
# biết để đi tìm. Backlog §31.5 gọi đây là "mìn hẹn giờ"; cái nguy hiểm không
# phải con số trần mà là sự im lặng.

import pathlib  # noqa: E402

from public_api import (  # noqa: E402
    _EVENT_SCAN_LIMIT,
    _FULL_SCAN_LIMIT,
    _warn_if_scan_truncated,
)


def test_tran_quet_chua_cham_thi_im_lang(caplog):
    with caplog.at_level("WARNING"):
        assert _warn_if_scan_truncated([1] * 10, 5000, "trang chủ") is False
    assert caplog.records == []


def test_tran_quet_cham_thi_canh_bao(caplog):
    with caplog.at_level("WARNING"):
        assert _warn_if_scan_truncated([1] * 5000, 5000, "trang chủ") is True
    # KHÔNG chốt số bản ghi: log đi qua cả handler middleware của dự án nên
    # cùng một cảnh báo xuất hiện hai lần. Cái cần khoá là NỘI DUNG.
    msgs = [r.getMessage() for r in caplog.records]
    assert any("trang chủ" in m and "5000" in m for m in msgs), msgs


def test_tran_quet_dung_dau_bang_chu_khong_phai_lon_hon():
    """Trả về ĐÚNG `limit` hàng thì không phân biệt được "vừa đủ" với "đã bị
    cắt" — ở ranh giới đó phải coi như đã cắt, nếu không mìn nổ im lặng ở đúng
    hàng đầu tiên vượt trần."""
    assert _warn_if_scan_truncated([1] * 4999, 5000, "x") is False
    assert _warn_if_scan_truncated([1] * 5000, 5000, "x") is True
    assert _warn_if_scan_truncated([1] * 5001, 5000, "x") is True


def test_tran_quet_la_hang_co_ten_khong_phai_so_roi_trong_ma():
    """Số rời rạc trong thân hàm thì không ai sửa được đồng bộ, và không test
    nào tham chiếu được tới nó."""
    assert _FULL_SCAN_LIMIT == 5000
    assert _EVENT_SCAN_LIMIT == 2000
    src = pathlib.Path(_pa.__file__).read_text(encoding="utf-8")
    assert "limit=5000" not in src, "còn số 5000 rời trong mã — dùng _FULL_SCAN_LIMIT"
    assert "limit=2000" not in src, "còn số 2000 rời trong mã — dùng _EVENT_SCAN_LIMIT"


def test_lead_ocop_star_khong_bat_chu_so_lac():
    """`_lead_ocop_star` từng là bản sao THỨ BA của luật rút hạng, rút bằng chữ
    số đầu tiên gặp ở bất kỳ đâu trong chuỗi."""
    from public_api import _lead_ocop_star

    # Danh mục của công ty khác — không được đọc thành hạng 4.
    assert _lead_ocop_star({
        "id": "dua-sap-cau-ke",
        "attributes": {"ocop": "VICOSAP: 4 SP OCOP 5 sao quoc gia + 7 SP OCOP 4 sao"},
    }) == 1
    # Năm ban hành không phải hạng.
    assert _lead_ocop_star({"id": "x", "attributes": {"ocop": "Dat chuan nam 2020"}}) == 1
    # Hạng thật vẫn ra đúng.
    assert _lead_ocop_star({"id": "y", "attributes": {"ocop_star": 4}}) == 4
    # Không có dấu hiệu OCOP nào.
    assert _lead_ocop_star({"id": "z", "attributes": {"rating": 4.5}}) == 0
