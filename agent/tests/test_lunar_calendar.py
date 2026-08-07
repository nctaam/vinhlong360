"""
Test cho agent/lunar_calendar.py — đối chiếu MỐC ĐÃ BIẾT, không tự chứng minh vòng tròn.

Nguyên tắc: mọi hằng số kỳ vọng ở đây phải tra được từ nguồn NGOÀI code này.
Nguồn dùng cho từng nhóm được ghi ngay trên nhóm đó. KHÔNG sửa số kỳ vọng cho
test xanh — nếu lệch thì báo người (CLAUDE.md §3.3).
"""
import math
from datetime import date

import pytest

import lunar_calendar as lc


# ---------------------------------------------------------------------------
# 1. Tết Nguyên đán — mốc phổ thông nhất, ai cũng kiểm chứng được
#
# Nguồn: lịch dân dụng VN đã phát hành (mọi cuốn lịch block / lịch vạn niên).
# Đối chiếu thêm: thanhnien.vn "Vì sao năm nay Việt Nam ăn Tết trước Trung Quốc
# một ngày?" và tuoitre.vn "Vì sao lịch VN và Trung Quốc lệch nhau?" (bài 2007).
# ---------------------------------------------------------------------------
TET_VN = {
    2015: date(2015, 2, 19),
    2016: date(2016, 2, 8),
    2017: date(2017, 1, 28),
    2018: date(2018, 2, 16),
    2019: date(2019, 2, 5),
    2020: date(2020, 1, 25),
    2021: date(2021, 2, 12),
    2022: date(2022, 2, 1),
    2023: date(2023, 1, 22),
    2024: date(2024, 2, 10),
    2025: date(2025, 1, 29),
    2026: date(2026, 2, 17),
    2027: date(2027, 2, 6),
    2028: date(2028, 1, 26),
    2029: date(2029, 2, 13),
    2030: date(2030, 2, 2),
}


@pytest.mark.parametrize("year,expected", sorted(TET_VN.items()))
def test_tet_lunar_to_solar(year, expected):
    """Mùng 1 tháng Giêng âm → đúng ngày dương lịch đã công bố."""
    assert lc.lunar_to_solar(1, 1, year) == expected


@pytest.mark.parametrize("year,expected", sorted(TET_VN.items()))
def test_tet_solar_to_lunar(year, expected):
    """Chiều ngược lại: ngày Tết dương → mùng 1 tháng Giêng, không nhuận."""
    got = lc.solar_to_lunar(expected.day, expected.month, expected.year)
    assert (got.day, got.month, got.leap) == (1, 1, False)
    assert got.year == year


# ---------------------------------------------------------------------------
# 2. Rằm & các tiết lễ âm lịch
#
# Nguồn: baovanhoa.vn / vtcnews.vn — "Rằm tháng 7 năm 2025 rơi vào ngày nào
# Dương lịch?" → 15/7 ÂL 2025 = thứ Bảy 06/09/2025.
# thuvienphapluat.vn / vietnamnet.vn — Tết Đoan Ngọ (5/5 ÂL) 2025 = 31/05/2025.
# Các mốc còn lại tra lịch vạn niên VN đã phát hành.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "lunar_day,lunar_month,lunar_year,expected",
    [
        # Rằm tháng Giêng (Tết Nguyên tiêu)
        (15, 1, 2024, date(2024, 2, 24)),
        (15, 1, 2025, date(2025, 2, 12)),
        (15, 1, 2026, date(2026, 3, 3)),
        # Rằm tháng Bảy (Vu Lan / xá tội vong nhân)
        (15, 7, 2024, date(2024, 8, 18)),
        (15, 7, 2025, date(2025, 9, 6)),  # nguồn: baovanhoa.vn, vtcnews.vn
        (15, 7, 2026, date(2026, 8, 27)),
        # Rằm tháng Tám (Trung thu)
        (15, 8, 2024, date(2024, 9, 17)),
        (15, 8, 2025, date(2025, 10, 6)),
        (15, 8, 2026, date(2026, 9, 25)),
        # Tết Đoan Ngọ
        (5, 5, 2025, date(2025, 5, 31)),  # nguồn: thuvienphapluat.vn, vietnamnet.vn
    ],
)
def test_lunar_festivals(lunar_day, lunar_month, lunar_year, expected):
    assert lc.lunar_to_solar(lunar_day, lunar_month, lunar_year) == expected
    back = lc.solar_to_lunar(expected.day, expected.month, expected.year)
    assert (back.day, back.month, back.year, back.leap) == (
        lunar_day,
        lunar_month,
        lunar_year,
        False,
    )


def test_ram_va_mung_mot_flags():
    assert lc.is_mung_mot(29, 1, 2025) is True  # Tết Ất Tỵ
    assert lc.is_ngay_ram(29, 1, 2025) is False
    assert lc.is_ngay_ram(6, 9, 2025) is True  # rằm tháng Bảy 2025
    assert lc.solar_to_lunar(6, 9, 2025).is_ngay_ram is True
    assert lc.solar_to_lunar(29, 1, 2025).is_mung_mot is True


# ---------------------------------------------------------------------------
# 3. ★ LỆCH VIỆT NAM ⇄ TRUNG QUỐC — nhóm test CHỊU LỰC ★
#
# Đây là nhóm DUY NHẤT chứng minh module cài cho VN (UTC+7) chứ không phải chép
# lịch TQ (UTC+8). Nếu ai đó "tối ưu" bằng cách hardcode 8.0, chỉ nhóm này đỏ.
#
# Nguồn:
#  - tuoitre.vn "Vì sao lịch VN và Trung Quốc lệch nhau?" + rfa.org (07/02/2007):
#    Tết Đinh Hợi — VN 17/02/2007 (thứ Bảy), TQ 18/02/2007 (Chủ nhật).
#    Giờ sóc tháng Giêng 2007 = 16g15 giờ quốc tế ngày 17/2 → +7h = 23g15 ngày
#    17/2 (VN vẫn 17/2) nhưng +8h = 0g15 ngày 18/2 (TQ sang 18/2).
#  - tuoitre.vn (cùng bài): trong thế kỷ 21 CHỈ có 2007, 2030, 2053 là VN ăn Tết
#    trước TQ một ngày. Test dưới kiểm đúng tập 3 năm này, không thừa không thiếu.
#  - suckhoedoisong.vn "Vì sao Tết Nguyên Đán giữa các nước có thể chênh nhau đến
#    1 tháng": Tết Ất Sửu — VN 21/01/1985, TQ 20/02/1985 (lệch trọn 1 tháng, do
#    lịch TQ nhuận tháng 10 năm 1984 còn lịch VN nhuận tháng 2 năm 1985).
# ---------------------------------------------------------------------------
def test_tet_2007_vn_som_hon_tq_mot_ngay():
    """Mốc kinh điển: Tết Đinh Hợi 2007, VN 17/2 — TQ 18/2."""
    assert lc.lunar_to_solar(1, 1, 2007, timezone=lc.TZ_VIETNAM) == date(2007, 2, 17)
    assert lc.lunar_to_solar(1, 1, 2007, timezone=lc.TZ_CHINA) == date(2007, 2, 18)
    # Theo lịch TQ, ngày 17/2/2007 vẫn là 30 tháng Chạp năm Bính Tuất.
    tq = lc.solar_to_lunar(17, 2, 2007, timezone=lc.TZ_CHINA)
    assert (tq.day, tq.month) == (30, 12)


def test_gio_soc_thang_gieng_2007_dung_1615_uct():
    """Kiểm chính con số Tuổi Trẻ công bố: sóc lúc 16g15 giờ quốc tế 17/02/2007.

    Đây là test đo THẲNG hàm thiên văn, không qua tầng lịch — nếu _new_moon()
    sai thì mọi thứ phía trên sai theo mà không ai biết.
    """
    jd_ref = lc.jd_from_date(17, 2, 2007)
    k = math.floor((jd_ref - lc._NM_EPOCH) / lc._SYNODIC) + 1
    jd_nm = lc._new_moon(k)
    dd, mm, yy = lc.jd_to_date(math.floor(jd_nm + 0.5))
    assert (dd, mm, yy) == (17, 2, 2007)
    hours_utc = (jd_nm + 0.5 - math.floor(jd_nm + 0.5)) * 24
    assert hours_utc == pytest.approx(16 + 15 / 60, abs=2 / 60)  # 16:15 UTC ±2 phút
    # +7h ⇒ vẫn 17/2 giờ VN; +8h ⇒ đã sang 18/2 giờ TQ. Chính là gốc của cú lệch.
    assert hours_utc + 7 < 24
    assert hours_utc + 8 >= 24


def test_tet_1985_lech_tron_mot_thang():
    """Ca phức tạp nhất: VN 21/01/1985 vs TQ 20/02/1985 — lệch 1 THÁNG."""
    assert lc.lunar_to_solar(1, 1, 1985, timezone=lc.TZ_VIETNAM) == date(1985, 1, 21)
    assert lc.lunar_to_solar(1, 1, 1985, timezone=lc.TZ_CHINA) == date(1985, 2, 20)


def test_thang_nhuan_1984_1985_khac_nhau_giua_vn_va_tq():
    """Gốc rễ cú lệch 1985: TQ nhuận tháng 10/1984, VN nhuận tháng 2/1985."""
    assert _leap_months_in_solar_year(1984, lc.TZ_CHINA) == {(1984, 10)}
    assert _leap_months_in_solar_year(1984, lc.TZ_VIETNAM) == set()
    assert _leap_months_in_solar_year(1985, lc.TZ_VIETNAM) == {(1985, 2)}
    assert _leap_months_in_solar_year(1985, lc.TZ_CHINA) == set()


def test_the_ky_21_chi_co_2007_2030_2053_lech_tet():
    """Tuổi Trẻ: thế kỷ 21 chỉ 3 năm VN ăn Tết trước TQ. Kiểm ĐÚNG tập đó."""
    lech = {
        y
        for y in range(2001, 2101)
        if lc.lunar_to_solar(1, 1, y, timezone=lc.TZ_VIETNAM)
        != lc.lunar_to_solar(1, 1, y, timezone=lc.TZ_CHINA)
    }
    assert lech == {2007, 2030, 2053}
    for y in sorted(lech):
        vn = lc.lunar_to_solar(1, 1, y, timezone=lc.TZ_VIETNAM)
        tq = lc.lunar_to_solar(1, 1, y, timezone=lc.TZ_CHINA)
        assert (tq - vn).days == 1, f"{y}: VN phải SỚM hơn TQ đúng 1 ngày"


def test_tet_mau_than_1968_hai_mien_lech_mot_ngay():
    """Sự thật lịch sử: 1968 miền Bắc theo UTC+7 (29/01), miền Nam UTC+8 (30/01)."""
    assert lc.lunar_to_solar(1, 1, 1968, timezone=7.0) == date(1968, 1, 29)
    assert lc.lunar_to_solar(1, 1, 1968, timezone=8.0) == date(1968, 1, 30)
    assert lc.vietnam_timezone_for_year(1968) == 7.0
    assert lc.vietnam_timezone_for_year(1967) == 8.0


def test_mac_dinh_la_mui_gio_viet_nam_khong_phai_trung_quoc():
    """Chốt chặn hồi quy: mặc định PHẢI là 7.0. Đổi thành 8.0 là test này đỏ."""
    assert lc.TZ_VIETNAM == 7.0
    assert lc.TZ_CHINA == 8.0
    for fn_args in [(1, 1, 2007), (1, 1, 1985), (1, 1, 2030)]:
        assert lc.lunar_to_solar(*fn_args) == lc.lunar_to_solar(
            *fn_args, timezone=lc.TZ_VIETNAM
        )
        assert lc.lunar_to_solar(*fn_args) != lc.lunar_to_solar(
            *fn_args, timezone=lc.TZ_CHINA
        )
    assert lc.solar_to_lunar(17, 2, 2007) == lc.solar_to_lunar(
        17, 2, 2007, timezone=lc.TZ_VIETNAM
    )
    assert lc.solar_to_lunar(17, 2, 2007) != lc.solar_to_lunar(
        17, 2, 2007, timezone=lc.TZ_CHINA
    )


# ---------------------------------------------------------------------------
# 4. Tháng nhuận
#
# Nguồn: lịch vạn niên VN đã phát hành. Các năm nhuận gần đây ai cũng nhớ:
# 2020 nhuận tháng 4, 2023 nhuận tháng 2, 2025 nhuận tháng 6 (tháng 6 nhuận
# 2025 bắt đầu 25/07/2025 — chính là lý do rằm tháng Bảy 2025 rơi tận 06/09).
# ---------------------------------------------------------------------------
def _leap_months_in_solar_year(solar_year: int, timezone: float = lc.TZ_VIETNAM):
    """Tập (năm âm, tháng) nhuận xuất hiện trong năm dương ``solar_year``."""
    out = set()
    jd = lc.jd_from_date(1, 1, solar_year)
    jd_end = lc.jd_from_date(31, 12, solar_year)
    while jd <= jd_end:
        d, m, y = lc.jd_to_date(jd)
        got = lc.solar_to_lunar(d, m, y, timezone)
        if got.leap:
            out.add((got.year, got.month))
        jd += 1
    return out


@pytest.mark.parametrize(
    "solar_year,expected",
    [
        (2012, {(2012, 4)}),
        (2014, {(2014, 9)}),
        (2017, {(2017, 6)}),
        (2020, {(2020, 4)}),
        (2023, {(2023, 2)}),
        (2025, {(2025, 6)}),
        (2028, {(2028, 5)}),
        (2031, {(2031, 3)}),
        (2024, set()),  # năm thường — không được bịa ra tháng nhuận
        (2026, set()),
    ],
)
def test_thang_nhuan_viet_nam(solar_year, expected):
    assert _leap_months_in_solar_year(solar_year) == expected


def test_thang_6_nhuan_2025_bat_dau_dung_ngay():
    """Mùng 1 tháng 6 nhuận Ất Tỵ = 25/07/2025; tháng 6 chính = 25/06/2025."""
    assert lc.lunar_to_solar(1, 6, 2025, leap=False) == date(2025, 6, 25)
    assert lc.lunar_to_solar(1, 6, 2025, leap=True) == date(2025, 7, 25)
    got = lc.solar_to_lunar(25, 7, 2025)
    assert (got.day, got.month, got.leap) == (1, 6, True)
    assert str(got) == "01/06N/2025"


def test_thang_11_nhuan_2033_ca_kho():
    """2033 nhuận tháng 11 — ca hiếm, từng gây tranh cãi lịch pháp ("vấn đề 2033").

    VN và TQ trùng nhau ở ca này; test giữ để refactor không âm thầm làm trôi.
    """
    assert _leap_months_in_solar_year(2033) == {(2033, 11)}
    assert _leap_months_in_solar_year(2033, lc.TZ_CHINA) == {(2033, 11)}
    assert lc.lunar_to_solar(1, 11, 2033, leap=True) == date(2033, 12, 22)


def test_thang_nhuan_khong_ton_tai_thi_bao_loi():
    with pytest.raises(ValueError, match="không có tháng nhuận"):
        lc.lunar_to_solar(1, 3, 2024, leap=True)  # 2024 không nhuận
    with pytest.raises(ValueError, match="không có tháng 3 nhuận"):
        lc.lunar_to_solar(1, 3, 2025, leap=True)  # 2025 nhuận tháng 6, không phải 3


# ---------------------------------------------------------------------------
# 5. Vòng tròn dương → âm → dương trên dải dài
# ---------------------------------------------------------------------------
def test_round_trip_moi_ngay_1990_2060():
    """Mọi ngày dương 1990–2060: solar→lunar→solar phải về đúng chỗ cũ."""
    jd = lc.jd_from_date(1, 1, 1990)
    jd_end = lc.jd_from_date(31, 12, 2060)
    checked = 0
    while jd <= jd_end:
        d, m, y = lc.jd_to_date(jd)
        lunar = lc.solar_to_lunar(d, m, y)
        assert lc.lunar_to_solar(
            lunar.day, lunar.month, lunar.year, lunar.leap
        ) == date(y, m, d), f"round-trip hỏng ở {d:02d}/{m:02d}/{y} → {lunar}"
        checked += 1
        jd += 1
    assert checked > 25_000


def test_jd_round_trip():
    for y in (1200, 1582, 1900, 2026, 2199):
        for m, d in ((1, 1), (2, 28), (7, 15), (12, 31)):
            assert lc.jd_to_date(lc.jd_from_date(d, m, y)) == (d, m, y)


@pytest.mark.parametrize("timezone", [lc.TZ_VIETNAM, lc.TZ_CHINA])
def test_ngay_am_luon_trong_1_30_suot_1900_2199(timezone):
    """Hồi quy BUG THẬT: ước lượng k bằng tuần trăng trung bình lệch 1 bước.

    Bản gốc Hồ Ngọc Đức chỉ lùi đúng 1 bước (`k+1` → `k`) nên 07/05/2054 và
    09/04/2062 cho ngày âm = 0 (múi giờ 7); múi giờ 8 cũng dính (vd 09/04/2062).
    Bản này lùi bằng vòng lặp. Quét TOÀN BỘ dải hỗ trợ, không lấy mẫu.
    """
    jd = lc.jd_from_date(1, 1, 1900)
    jd_end = lc.jd_from_date(31, 12, 2199)
    while jd <= jd_end:
        d, m, y = lc.jd_to_date(jd)
        got = lc.solar_to_lunar(d, m, y, timezone)
        assert 1 <= got.day <= 30, f"ngày âm {got.day} tại {d:02d}/{m:02d}/{y}"
        jd += 1


@pytest.mark.parametrize("d,m,y", [(7, 5, 2054), (9, 4, 2062)])
def test_hai_ngay_tung_vo_o_ban_goc(d, m, y):
    """Hai ngày cụ thể từng cho ngày âm = 0 — chốt lại bằng giá trị đúng."""
    got = lc.solar_to_lunar(d, m, y)
    assert got.day == 30, f"{d:02d}/{m:02d}/{y} phải là ngày 30 (cuối tháng đủ)"
    assert lc.lunar_to_solar(got.day, got.month, got.year, got.leap) == date(y, m, d)


def test_ngay_am_lien_tuc_khong_nhay_coc():
    """Ngày âm phải chạy 1..29/30 rồi về 1 — không có ngày 0, 31, hay đứt đoạn."""
    jd = lc.jd_from_date(1, 1, 2020)
    jd_end = lc.jd_from_date(31, 12, 2035)
    prev = None
    while jd <= jd_end:
        d, m, y = lc.jd_to_date(jd)
        cur = lc.solar_to_lunar(d, m, y)
        assert 1 <= cur.day <= 30, f"ngày âm phi lý {cur.day} tại {d:02d}/{m:02d}/{y}"
        assert 1 <= cur.month <= 12
        if prev is not None:
            assert cur.day == prev + 1 or cur.day == 1, (
                f"đứt đoạn ngày âm tại {d:02d}/{m:02d}/{y}: {prev} → {cur.day}"
            )
        prev = cur.day
        jd += 1


def test_thang_am_dai_29_hoac_30_ngay():
    """Tháng âm chỉ có thể 29 (thiếu) hoặc 30 (đủ) ngày."""
    jd = lc.jd_from_date(1, 1, 2000)
    jd_end = lc.jd_from_date(31, 12, 2050)
    lengths = set()
    run = 0
    started = False  # 01/01/2000 rơi vào GIỮA tháng âm (ngày 25) → đoạn đầu là
    # mảnh 6 ngày, không phải một tháng. Chỉ đo từ mùng 1 đầu tiên trở đi.
    while jd <= jd_end:
        d, m, y = lc.jd_to_date(jd)
        cur = lc.solar_to_lunar(d, m, y)
        if cur.day == 1:
            if started:
                lengths.add(run)
            started = True
            run = 0
        if started:
            run += 1
        jd += 1
    assert lengths <= {29, 30}, f"độ dài tháng âm phi lý: {sorted(lengths)}"
    assert lengths == {29, 30}


def test_ngay_30_cua_thang_thieu_bao_loi():
    """Tháng thiếu không có ngày 30 → phải raise, KHÔNG trả ngày trôi sang tháng sau."""
    jd = lc.jd_from_date(1, 1, 2025)
    jd_end = lc.jd_from_date(31, 12, 2025)
    thang_thieu = []
    while jd <= jd_end:
        d, m, y = lc.jd_to_date(jd)
        cur = lc.solar_to_lunar(d, m, y)
        if cur.day == 29:
            nxt = lc.solar_to_lunar(*lc.jd_to_date(jd + 1))
            if nxt.day == 1:
                thang_thieu.append((cur.month, cur.year, cur.leap))
        jd += 1
    assert thang_thieu, "2025 phải có ít nhất một tháng thiếu"
    m, y, leap = thang_thieu[0]
    with pytest.raises(ValueError, match="không tồn tại"):
        lc.lunar_to_solar(30, m, y, leap)


# ---------------------------------------------------------------------------
# 6. Can chi
#
# Nguồn: quy tắc lịch pháp phổ thông + tên năm ai cũng biết (2024 Giáp Thìn,
# 2025 Ất Tỵ). Tháng: "năm Giáp/Kỷ thì tháng Giêng là Bính Dần" (ngũ hổ độn).
# Giờ: "Giáp Kỷ dạ sinh Giáp" (ngũ thử độn).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "lunar_year,expected",
    [
        (1984, "Giáp Tý"),  # khởi đầu một hoa giáp
        (2020, "Canh Tý"),
        (2023, "Quý Mão"),
        (2024, "Giáp Thìn"),
        (2025, "Ất Tỵ"),
        (2026, "Bính Ngọ"),
        (2044, "Giáp Tý"),  # 60 năm sau 1984
    ],
)
def test_can_chi_nam(lunar_year, expected):
    assert lc.can_chi_year(lunar_year) == expected


def test_can_chi_nam_lap_lai_moi_60_nam():
    for y in range(1900, 2100):
        assert lc.can_chi_year(y) == lc.can_chi_year(y + 60)


def test_can_chi_thang_theo_ngu_ho_don():
    """Tháng Giêng luôn mang chi Dần; can theo năm (Giáp/Kỷ → Bính Dần)."""
    assert lc.can_chi_month(1, 2024) == "Bính Dần"  # Giáp Thìn → Bính Dần
    assert lc.can_chi_month(1, 2029) == "Bính Dần"  # Kỷ Dậu → Bính Dần
    assert lc.can_chi_month(1, 2025) == "Mậu Dần"  # Ất Tỵ → Mậu Dần
    assert lc.can_chi_month(1, 2026) == "Canh Dần"  # Bính Ngọ → Canh Dần
    # Chi tháng cố định theo số tháng, không phụ thuộc năm
    for y in (2024, 2025, 2026):
        assert lc.can_chi_month(1, y).endswith("Dần")
        assert lc.can_chi_month(11, y).endswith("Tý")
        assert lc.can_chi_month(12, y).endswith("Sửu")


def test_can_chi_ngay_chay_lien_tuc_60():
    """Can chi ngày là chu kỳ 60 không đứt — kiểm bằng tính liên tục."""
    assert lc.can_chi_day(29, 1, 2025) == "Mậu Tuất"  # Tết Ất Tỵ
    seen = []
    jd0 = lc.jd_from_date(1, 1, 2026)
    for i in range(60):
        d, m, y = lc.jd_to_date(jd0 + i)
        seen.append(lc.can_chi_day(d, m, y))
    assert len(set(seen)) == 60, "60 ngày liên tiếp phải cho 60 can chi khác nhau"
    d, m, y = lc.jd_to_date(jd0 + 60)
    assert lc.can_chi_day(d, m, y) == seen[0]


def test_can_chi_ngay_moc_tra_duoc():
    """Mốc tra từ lịch vạn niên đã phát hành, KHÔNG suy ra từ chính công thức.

    Nguồn: xemlicham.com / home.vn — trang lịch vạn niên ngày 29/01/2025 ghi
    "Ngày Mậu Tuất, Tháng Mậu Dần, Năm Ất Tỵ. Tiết khí: Đại Hàn".
    01/01/2000 = ngày Mậu Ngọ (mốc quy chiếu quen dùng của lịch pháp).
    """
    assert lc.can_chi_day(29, 1, 2025) == "Mậu Tuất"
    assert lc.can_chi_day(1, 1, 2000) == "Mậu Ngọ"


def test_bo_moc_29_01_2025_khop_tron_bo():
    """Một ngày, bốn chiều — ngày/tháng/năm/tiết khí đều khớp lịch đã phát hành.

    Đây là test "chụp ảnh" mạnh nhất: nguồn ngoài cho cả 4 trường cùng lúc nên
    một sai lệch ở bất kỳ tầng nào cũng lộ.
    """
    lunar = lc.solar_to_lunar(29, 1, 2025)
    assert (lunar.day, lunar.month, lunar.year, lunar.leap) == (1, 1, 2025, False)
    assert lc.can_chi_day(29, 1, 2025) == "Mậu Tuất"
    assert lc.can_chi_month(lunar.month, lunar.year) == "Mậu Dần"
    assert lc.can_chi_year(lunar.year) == "Ất Tỵ"
    assert lc.tiet_khi_name(29, 1, 2025) == "Đại hàn"


def test_can_chi_gio_ngu_thu_don():
    """Ngũ thử độn: ngày can Mậu/Quý → giờ Tý là Nhâm Tý.

    29/01/2025 là ngày Mậu Tuất (nguồn ở test trên) ⇒ giờ Tý = Nhâm Tý.
    """
    assert lc.can_chi_hour(29, 1, 2025, 0) == "Nhâm Tý"
    assert lc.can_chi_hour(29, 1, 2025, 1) == "Quý Sửu"
    # Ngày Mậu Ngọ (01/01/2000) cũng can Mậu ⇒ cũng khởi Nhâm Tý
    assert lc.can_chi_hour(1, 1, 2000, 0) == "Nhâm Tý"
    # 12 canh giờ trong ngày phải đủ 12 chi, đúng thứ tự, không trùng
    chis = [lc.can_chi_hour(29, 1, 2025, i).split()[1] for i in range(12)]
    assert chis == list(lc.CHI)
    with pytest.raises(ValueError):
        lc.can_chi_hour(29, 1, 2025, 12)


# ---------------------------------------------------------------------------
# 7. Tiết khí
#
# Nguồn: mốc thiên văn công bố (phân/chí) quy về giờ VN (UTC+7):
#   Xuân phân 2025: 20/03 09:01 UTC = 16:01 VN → ngày 20/03
#   Hạ chí   2025: 21/06 02:42 UTC = 09:42 VN → ngày 21/06
#   Thu phân 2025: 22/09 18:19 UTC = 23/09 01:19 VN → ngày 23/09
#   Đông chí 2025: 21/12 15:03 UTC = 22:03 VN → ngày 21/12
# Lập xuân / Thanh minh đối chiếu lịch vạn niên VN.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "term,solar_year,expected",
    [
        ("Xuân phân", 2024, date(2024, 3, 20)),
        ("Hạ chí", 2024, date(2024, 6, 21)),
        ("Thu phân", 2024, date(2024, 9, 22)),
        ("Đông chí", 2024, date(2024, 12, 21)),
        ("Xuân phân", 2025, date(2025, 3, 20)),
        ("Hạ chí", 2025, date(2025, 6, 21)),
        ("Thu phân", 2025, date(2025, 9, 23)),
        ("Đông chí", 2025, date(2025, 12, 21)),
        ("Lập xuân", 2025, date(2025, 2, 3)),
        ("Lập xuân", 2024, date(2024, 2, 4)),
        ("Thanh minh", 2024, date(2024, 4, 4)),
        ("Thanh minh", 2025, date(2025, 4, 4)),
        ("Thanh minh", 2026, date(2026, 4, 5)),
    ],
)
def test_tiet_khi_start_date(term, solar_year, expected):
    assert lc.tiet_khi_start_date(term, solar_year) == expected


def test_tiet_khi_du_24_va_bat_dau_dung_thu_tu():
    assert len(lc.TIET_KHI) == 24
    assert len(set(lc.TIET_KHI)) == 24
    assert lc.TIET_KHI[0] == "Xuân phân"  # 0° kinh độ mặt trời
    assert lc.TIET_KHI[18] == "Đông chí"  # 270°
    assert lc.TIET_KHI[21] == "Lập xuân"  # 315°
    starts = [lc.tiet_khi_start_date(i, 2025) for i in range(24)]
    assert len(set(starts)) == 24, "24 tiết khí phải bắt đầu ở 24 ngày khác nhau"


def test_tiet_khi_name_cua_ngay():
    assert lc.tiet_khi_name(3, 2, 2025) == "Lập xuân"
    assert lc.tiet_khi_name(21, 12, 2025) == "Đông chí"
    # Ngày trước Đông chí 2025 phải còn là tiết trước (Đại tuyết)
    assert lc.tiet_khi_name(20, 12, 2025) == "Đại tuyết"


def test_tiet_khi_moi_ngay_deu_co_ten_hop_le():
    jd = lc.jd_from_date(1, 1, 2025)
    for i in range(365):
        d, m, y = lc.jd_to_date(jd + i)
        assert lc.tiet_khi_name(d, m, y) in lc.TIET_KHI


def test_tiet_khi_ten_sai_bao_loi():
    with pytest.raises(ValueError, match="không có trong danh sách"):
        lc.tiet_khi_start_date("Không Tồn Tại", 2025)
    with pytest.raises(ValueError, match="không hợp lệ"):
        lc.tiet_khi_start_date(24, 2025)


# ---------------------------------------------------------------------------
# 8. Đầu vào sai phải nổ rõ ràng
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "args", [(1, 13, 2025), (1, 0, 2025), (0, 1, 2025), (31, 1, 2025)]
)
def test_lunar_to_solar_dau_vao_sai(args):
    with pytest.raises(ValueError):
        lc.lunar_to_solar(*args)


def test_can_chi_month_dau_vao_sai():
    with pytest.raises(ValueError):
        lc.can_chi_month(13, 2025)


def test_pham_vi_nam_duoc_cong_bo():
    """Module phải nói rõ phạm vi tin được — đừng để người dùng tự đoán."""
    assert lc.SUPPORTED_YEAR_MIN == 1200
    assert lc.SUPPORTED_YEAR_MAX == 2199
    assert lc.RECOMMENDED_YEAR_MIN == 1968
    assert "1968" in lc.__doc__ and "2199" in lc.__doc__
