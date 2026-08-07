"""
Lịch âm Việt Nam — chuyển đổi dương ⇄ âm, can chi, tiết khí.

THUẦN PYTHON, KHÔNG dependency mới, KHÔNG gọi API ngoài (§B8). Toàn bộ tính toán
là thiên văn học rời rạc chạy offline.

## Nguồn thuật toán

Thuật toán của **Hồ Ngọc Đức** ("Âm lịch Việt Nam", https://www.informatik.uni-leipzig.de/~duc/amlich/),
bản thân dựa trên *Astronomical Algorithms* (Jean Meeus, 1998) — công thức sóc (new moon)
chương 49 và kinh độ mặt trời chương 25 (độ chính xác thấp, sai số ~0.01°).

## BẪY MÚI GIỜ — đọc trước khi dùng

Âm lịch **Việt Nam** quy ước theo **UTC+7**; âm lịch **Trung Quốc** theo **UTC+8**.
Điểm sóc (và do đó ngày mùng 1) rơi vào múi giờ nào quyết định ngày âm. Khi sóc rơi
vào khoảng 23:00–24:00 giờ VN, hai lịch lệch nhau **1 ngày**; nếu cú lệch đó rơi trúng
mốc quyết định tháng 11 / tháng nhuận thì hai lịch lệch nhau cả **1 tháng**.

⇒ Mọi hàm ở đây nhận tham số ``timezone`` (giờ, số thực) với **mặc định 7.0**.
KHÔNG hardcode 8.0. Hằng số sẵn có: :data:`TZ_VIETNAM` (7.0), :data:`TZ_CHINA` (8.0)
— hằng số TQ chỉ để **so sánh / kiểm thử**, không phải để tính lịch cho site.

## PHẠM VI NĂM TIN ĐƯỢC

- **1968–2199**: dùng trực tiếp, mặc định ``timezone=7.0``. Đây là phạm vi khuyến nghị.
- **Trước 1968**: múi giờ dùng cho lịch VN **không phải** 7.0 (xem :func:`vietnam_timezone_for_year`).
  Đặc biệt Tết Mậu Thân 1968: miền Bắc theo UTC+7 (29/01/1968), miền Nam còn theo UTC+8
  (30/01/1968) — **hai miền ăn Tết lệch nhau 1 ngày**. Module KHÔNG tự đoán hộ: muốn tính
  năm cũ thì phải truyền ``timezone`` tường minh.
- **Ngoài 1200–2199**: công thức Meeus độ-chính-xác-thấp bắt đầu trôi; KHÔNG dùng.

:data:`SUPPORTED_YEAR_MIN` / :data:`SUPPORTED_YEAR_MAX` là ranh giới kiểm tra được bằng code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

__all__ = [
    "TZ_VIETNAM",
    "TZ_CHINA",
    "SUPPORTED_YEAR_MIN",
    "SUPPORTED_YEAR_MAX",
    "RECOMMENDED_YEAR_MIN",
    "CAN",
    "CHI",
    "TIET_KHI",
    "LunarDate",
    "jd_from_date",
    "jd_to_date",
    "solar_to_lunar",
    "lunar_to_solar",
    "can_chi_year",
    "can_chi_month",
    "can_chi_day",
    "can_chi_hour",
    "sun_longitude_degrees",
    "tiet_khi_index",
    "tiet_khi_name",
    "tiet_khi_start_date",
    "vietnam_timezone_for_year",
    "is_mung_mot",
    "is_ngay_ram",
]

# --- Múi giờ ---------------------------------------------------------------
TZ_VIETNAM = 7.0
"""Múi giờ quy ước của âm lịch Việt Nam (UTC+7). MẶC ĐỊNH của mọi hàm."""

TZ_CHINA = 8.0
"""Múi giờ của âm lịch Trung Quốc (UTC+8). CHỈ dùng để so sánh/kiểm thử."""

SUPPORTED_YEAR_MIN = 1200
SUPPORTED_YEAR_MAX = 2199
RECOMMENDED_YEAR_MIN = 1968
"""Từ 1968 trở đi lịch VN dùng UTC+7 thống nhất → mặc định 7.0 là đúng."""

# --- Can chi ---------------------------------------------------------------
CAN = ("Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý")
CHI = ("Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi")

# --- Tiết khí --------------------------------------------------------------
# 24 tiết khí = 24 cung 15° kinh độ mặt trời. Chỉ số i ⇔ kinh độ [15i, 15i+15).
# Bắt đầu từ 0° = Xuân phân (không phải từ Lập xuân) để index = floor(deg/15).
TIET_KHI = (
    "Xuân phân",    # 0°
    "Thanh minh",   # 15°
    "Cốc vũ",       # 30°
    "Lập hạ",       # 45°
    "Tiểu mãn",     # 60°
    "Mang chủng",   # 75°
    "Hạ chí",       # 90°
    "Tiểu thử",     # 105°
    "Đại thử",      # 120°
    "Lập thu",      # 135°
    "Xử thử",       # 150°
    "Bạch lộ",      # 165°
    "Thu phân",     # 180°
    "Hàn lộ",       # 195°
    "Sương giáng",  # 210°
    "Lập đông",     # 225°
    "Tiểu tuyết",   # 240°
    "Đại tuyết",    # 255°
    "Đông chí",     # 270°
    "Tiểu hàn",     # 285°
    "Đại hàn",      # 300°
    "Lập xuân",     # 315°
    "Vũ thủy",      # 330°
    "Kinh trập",    # 345°
)

_SYNODIC = 29.530588853  # độ dài trung bình tuần trăng (ngày)
_NM_EPOCH = 2415021.076998695  # JD của sóc k=0 (1900-01-01 quanh đó)


# ---------------------------------------------------------------------------
# Julian Day
# ---------------------------------------------------------------------------
def jd_from_date(dd: int, mm: int, yy: int) -> int:
    """Số ngày Julian (JDN) của ngày dương lịch dd/mm/yy.

    Tự chuyển sang lịch Julius cho ngày trước 15/10/1582 (như bản gốc HND).
    """
    a = (14 - mm) // 12
    y = yy + 4800 - a
    m = mm + 12 * a - 3
    jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    if jd < 2299161:
        jd = dd + (153 * m + 2) // 5 + 365 * y + y // 4 - 32083
    return jd


def jd_to_date(jd: int) -> tuple[int, int, int]:
    """Ngược của :func:`jd_from_date`. Trả (dd, mm, yy)."""
    if jd > 2299160:  # sau 05/10/1582 → Gregorian
        a = jd + 32044
        b = (4 * a + 3) // 146097
        c = a - (b * 146097) // 4
    else:
        b = 0
        c = jd + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = b * 100 + d - 4800 + m // 10
    return day, month, year


# ---------------------------------------------------------------------------
# Thiên văn: sóc & kinh độ mặt trời
# ---------------------------------------------------------------------------
def _new_moon(k: int) -> float:
    """JD (giờ UTC, số thực) của điểm sóc thứ k tính từ 1900-01-01.

    Meeus ch.49 rút gọn — sai số vài phút, thừa cho phân giải ngày.
    """
    t = k / 1236.85
    t2 = t * t
    t3 = t2 * t
    dr = math.pi / 180
    jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * t2 - 0.000000155 * t3
    jd1 += 0.00033 * math.sin((166.56 + 132.87 * t - 0.009173 * t2) * dr)
    m = 359.2242 + 29.10535608 * k - 0.0000333 * t2 - 0.00000347 * t3
    mpr = 306.0253 + 385.81691806 * k + 0.0107306 * t2 + 0.00001236 * t3
    f = 21.2964 + 390.67050646 * k - 0.0016528 * t2 - 0.00000239 * t3
    c1 = (0.1734 - 0.000393 * t) * math.sin(m * dr) + 0.0021 * math.sin(2 * dr * m)
    c1 = c1 - 0.4068 * math.sin(mpr * dr) + 0.0161 * math.sin(dr * 2 * mpr)
    c1 = c1 - 0.0004 * math.sin(dr * 3 * mpr)
    c1 = c1 + 0.0104 * math.sin(dr * 2 * f) - 0.0051 * math.sin(dr * (m + mpr))
    c1 = c1 - 0.0074 * math.sin(dr * (m - mpr)) + 0.0004 * math.sin(dr * (2 * f + m))
    c1 = c1 - 0.0004 * math.sin(dr * (2 * f - m)) - 0.0006 * math.sin(dr * (2 * f + mpr))
    c1 = c1 + 0.0010 * math.sin(dr * (2 * f - mpr)) + 0.0005 * math.sin(dr * (2 * mpr + m))
    if t < -11:
        deltat = 0.001 + 0.000839 * t + 0.0002261 * t2 - 0.00000845 * t3 - 0.000000081 * t * t3
    else:
        deltat = -0.000278 + 0.000265 * t + 0.000262 * t2
    return jd1 + c1 - deltat


def sun_longitude_degrees(jd: float) -> float:
    """Kinh độ hoàng đạo biểu kiến của mặt trời tại thời điểm JD (độ, [0, 360))."""
    t = (jd - 2451545.0) / 36525
    t2 = t * t
    dr = math.pi / 180
    m = 357.52910 + 35999.05030 * t - 0.0001559 * t2 - 0.00000048 * t * t2
    l0 = 280.46645 + 36000.76983 * t + 0.0003032 * t2
    dl = (1.914600 - 0.004817 * t - 0.000014 * t2) * math.sin(dr * m)
    dl += (0.019993 - 0.000101 * t) * math.sin(dr * 2 * m)
    dl += 0.000290 * math.sin(dr * 3 * m)
    lon = (l0 + dl) % 360.0
    return lon


def _new_moon_day(k: int, timezone: float) -> int:
    """JDN của NGÀY chứa điểm sóc thứ k, theo giờ địa phương ``timezone``.

    Đây là chỗ múi giờ tạo ra khác biệt VN (7.0) ⇄ TQ (8.0).
    """
    return math.floor(_new_moon(k) + 0.5 + timezone / 24.0)


def _sun_longitude_sector(jdn: int, timezone: float) -> int:
    """Cung 30° (0..11) chứa mặt trời lúc 00:00 giờ địa phương của ngày ``jdn``.

    Bản gốc HND: ``SunLongitude(dayNumber - 0.5 - timeZone/24)``. Phần ``-0.5``
    là bắt buộc (JDN bắt đầu lúc 12:00 UTC) — bỏ nó đi thì mẫu lệch nửa ngày
    (~0.5° mặt trời) và có năm tính sai tháng nhuận.
    """
    return int(sun_longitude_degrees(jdn - 0.5 - timezone / 24.0) // 30.0)


def _lunar_month_11(yy: int, timezone: float) -> int:
    """JDN ngày mùng 1 tháng 11 âm của năm dương ``yy`` (tháng chứa Đông chí)."""
    off = jd_from_date(31, 12, yy) - 2415021
    k = math.floor(off / _SYNODIC)
    nm = _new_moon_day(k, timezone)
    if _sun_longitude_sector(nm, timezone) >= 9:
        nm = _new_moon_day(k - 1, timezone)
    return nm


def _leap_month_offset(a11: int, timezone: float) -> int:
    """Vị trí (offset từ tháng 11) của tháng nhuận trong năm âm bắt đầu tại a11."""
    k = math.floor((a11 - _NM_EPOCH) / _SYNODIC + 0.5)
    i = 1  # bắt đầu từ tháng ngay sau tháng 11
    arc = _sun_longitude_sector(_new_moon_day(k + i, timezone), timezone)
    while True:
        last = arc
        i += 1
        arc = _sun_longitude_sector(_new_moon_day(k + i, timezone), timezone)
        if arc == last or i >= 14:
            break
    return i - 1


# ---------------------------------------------------------------------------
# Kiểu dữ liệu
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LunarDate:
    """Một ngày âm lịch."""

    day: int
    month: int
    year: int
    leap: bool = False

    def __str__(self) -> str:
        return f"{self.day:02d}/{self.month:02d}{'N' if self.leap else ''}/{self.year}"

    @property
    def is_mung_mot(self) -> bool:
        return self.day == 1

    @property
    def is_ngay_ram(self) -> bool:
        return self.day == 15


# ---------------------------------------------------------------------------
# Chuyển đổi dương ⇄ âm
# ---------------------------------------------------------------------------
def solar_to_lunar(dd: int, mm: int, yy: int, timezone: float = TZ_VIETNAM) -> LunarDate:
    """Dương lịch → âm lịch.

    >>> solar_to_lunar(29, 1, 2025)          # Tết Ất Tỵ
    LunarDate(day=1, month=1, year=2025, leap=False)
    """
    day_number = jd_from_date(dd, mm, yy)
    # k ước lượng bằng tuần trăng TRUNG BÌNH nên có thể lệch ±1 so với sóc thật
    # (sóc thật trễ/sớm tới ~0.7 ngày). Bản gốc HND chỉ lùi ĐÚNG 1 bước
    # (`k+1` rồi `k`) — chưa đủ: 07/05/2054 và 09/04/2062 rơi vào kẽ đó và cho
    # ngày âm = 0. Ở đây lùi bằng VÒNG LẶP tới khi mùng 1 thật sự ≤ ngày cần tra.
    # Hồi quy: test_ngay_am_luon_trong_1_30_suot_1900_2199.
    k = math.floor((day_number - _NM_EPOCH) / _SYNODIC) + 1
    month_start = _new_moon_day(k, timezone)
    while month_start > day_number:
        k -= 1
        month_start = _new_moon_day(k, timezone)
    a11 = _lunar_month_11(yy, timezone)
    b11 = a11
    if a11 >= month_start:
        lunar_year = yy
        a11 = _lunar_month_11(yy - 1, timezone)
    else:
        lunar_year = yy + 1
        b11 = _lunar_month_11(yy + 1, timezone)
    lunar_day = day_number - month_start + 1
    diff = (month_start - a11) // 29
    lunar_leap = False
    lunar_month = diff + 11
    if b11 - a11 > 365:
        leap_month_diff = _leap_month_offset(a11, timezone)
        if diff >= leap_month_diff:
            lunar_month = diff + 10
            if diff == leap_month_diff:
                lunar_leap = True
    if lunar_month > 12:
        lunar_month -= 12
    if lunar_month >= 11 and diff < 4:
        lunar_year -= 1
    return LunarDate(day=lunar_day, month=lunar_month, year=lunar_year, leap=lunar_leap)


def solar_date_to_lunar(d: date, timezone: float = TZ_VIETNAM) -> LunarDate:
    """Bọc :func:`solar_to_lunar` cho ``datetime.date``."""
    return solar_to_lunar(d.day, d.month, d.year, timezone)


def _apply_leap_offset(
    off: int, a11: int, b11: int, mm: int, yy: int, leap: bool, timezone: float
) -> int:
    """Dịch offset tháng khi năm âm có tháng nhuận.

    Tách khỏi ``lunar_to_solar`` để hàm đó không gánh cả hai việc — tra tháng và
    xử nhuận (cổng R20.8 complexity). Raise ``ValueError`` khi người gọi đòi một
    tháng nhuận mà năm âm đó không có.
    """
    if b11 - a11 <= 365:
        if leap:
            raise ValueError(f"năm âm {yy} không có tháng nhuận")
        return off

    leap_off = _leap_month_offset(a11, timezone)
    leap_month = leap_off - 2
    if leap_month < 0:
        leap_month += 12
    if leap and mm != leap_month:
        raise ValueError(f"năm âm {yy} không có tháng {mm} nhuận")
    if leap or off >= leap_off:
        return off + 1
    return off


def lunar_to_solar(
    dd: int, mm: int, yy: int, leap: bool = False, timezone: float = TZ_VIETNAM
) -> date:
    """Âm lịch → dương lịch. Raise ``ValueError`` nếu ngày âm không tồn tại.

    >>> lunar_to_solar(1, 1, 2025)
    datetime.date(2025, 1, 29)
    """
    if not 1 <= mm <= 12:
        raise ValueError(f"tháng âm không hợp lệ: {mm}")
    if not 1 <= dd <= 30:
        raise ValueError(f"ngày âm không hợp lệ: {dd}")
    if mm < 11:
        a11 = _lunar_month_11(yy - 1, timezone)
        b11 = _lunar_month_11(yy, timezone)
    else:
        a11 = _lunar_month_11(yy, timezone)
        b11 = _lunar_month_11(yy + 1, timezone)
    off = mm - 11
    if off < 0:
        off += 12
    off = _apply_leap_offset(off, a11, b11, mm, yy, leap, timezone)
    k = math.floor(0.5 + (a11 - _NM_EPOCH) / _SYNODIC)
    month_start = _new_moon_day(k + off, timezone)
    jdn = month_start + dd - 1
    # Ngày 30 của tháng thiếu (29 ngày) không tồn tại → phát hiện bằng vòng ngược.
    d, m, y = jd_to_date(jdn)
    back = solar_to_lunar(d, m, y, timezone)
    if (back.day, back.month, back.leap) != (dd, mm, leap):
        raise ValueError(
            f"ngày âm {dd}/{mm}{'N' if leap else ''}/{yy} không tồn tại "
            f"(tháng thiếu); JDN {jdn} ứng với {back}"
        )
    return date(y, m, d)


def is_mung_mot(dd: int, mm: int, yy: int, timezone: float = TZ_VIETNAM) -> bool:
    return solar_to_lunar(dd, mm, yy, timezone).day == 1


def is_ngay_ram(dd: int, mm: int, yy: int, timezone: float = TZ_VIETNAM) -> bool:
    return solar_to_lunar(dd, mm, yy, timezone).day == 15


# ---------------------------------------------------------------------------
# Can chi
# ---------------------------------------------------------------------------
def can_chi_year(lunar_year: int) -> str:
    """Can chi của NĂM âm. ``can_chi_year(2024) == "Giáp Thìn"``."""
    return f"{CAN[(lunar_year + 6) % 10]} {CHI[(lunar_year + 8) % 12]}"


def can_chi_month(lunar_month: int, lunar_year: int) -> str:
    """Can chi của THÁNG âm (tháng Giêng luôn mang chi Dần).

    Tháng nhuận theo quy ước dùng can chi của tháng chính cùng số.
    """
    if not 1 <= lunar_month <= 12:
        raise ValueError(f"tháng âm không hợp lệ: {lunar_month}")
    return f"{CAN[(lunar_year * 12 + lunar_month + 3) % 10]} {CHI[(lunar_month + 1) % 12]}"


def can_chi_day(dd: int, mm: int, yy: int) -> str:
    """Can chi của NGÀY (chu kỳ 60 liên tục, không phụ thuộc múi giờ)."""
    jd = jd_from_date(dd, mm, yy)
    return f"{CAN[(jd + 9) % 10]} {CHI[(jd + 1) % 12]}"


def can_chi_hour(dd: int, mm: int, yy: int, chi_index: int) -> str:
    """Can chi của một CANH GIỜ (``chi_index`` 0 = giờ Tý 23–01, …, 11 = giờ Hợi).

    Quy tắc "Giáp Kỷ dạ sinh Giáp": can giờ Tý = (can ngày × 2) mod 10.
    """
    if not 0 <= chi_index <= 11:
        raise ValueError(f"chi giờ không hợp lệ: {chi_index}")
    jd = jd_from_date(dd, mm, yy)
    can_day = (jd + 9) % 10
    return f"{CAN[(can_day * 2 + chi_index) % 10]} {CHI[chi_index]}"


# ---------------------------------------------------------------------------
# Tiết khí
# ---------------------------------------------------------------------------
def _tiet_khi_index_jdn(jdn: int, timezone: float) -> int:
    """Tiết khí của ngày ``jdn``, lấy mẫu ở CUỐI ngày địa phương.

    Quy ước dân dụng: ngày nào CHỨA thời điểm mặt trời cắt mốc 15° thì ngày đó
    mang tên tiết khí mới (vd Đông chí 2024 rơi 16:20 ngày 21/12 ⇒ 21/12 là
    Đông chí, không phải 22/12). Lấy mẫu ở 00:00 đầu ngày như bản gốc HND sẽ
    trễ đúng 1 ngày mỗi khi thời điểm cắt rơi sau nửa đêm — nên ở đây lấy mẫu
    ở cuối ngày (= đầu ngày kế, lùi 1 giây).

    (Logic tháng nhuận vẫn dùng :func:`_sun_longitude_sector` lấy mẫu đầu ngày,
    đúng nguyên bản HND — hai chỗ hỏi hai câu khác nhau, đừng gộp.)
    """
    end_of_day = jdn + 0.5 - timezone / 24.0 - 1.0 / 86400.0
    return int(sun_longitude_degrees(end_of_day) // 15.0)


def tiet_khi_index(dd: int, mm: int, yy: int, timezone: float = TZ_VIETNAM) -> int:
    """Chỉ số tiết khí (0..23) mà ngày dương dd/mm/yy mang."""
    return _tiet_khi_index_jdn(jd_from_date(dd, mm, yy), timezone)


def tiet_khi_name(dd: int, mm: int, yy: int, timezone: float = TZ_VIETNAM) -> str:
    """Tên tiết khí của ngày dương dd/mm/yy."""
    return TIET_KHI[tiet_khi_index(dd, mm, yy, timezone)]


def tiet_khi_start_date(
    term: int | str, solar_year: int, timezone: float = TZ_VIETNAM
) -> date:
    """Ngày dương BẮT ĐẦU của một tiết khí trong năm dương ``solar_year``.

    ``term`` là chỉ số 0..23 hoặc tên trong :data:`TIET_KHI`.
    Raise ``ValueError`` nếu tiết khí đó không bắt đầu trong năm ``solar_year``.
    """
    if isinstance(term, str):
        try:
            term = TIET_KHI.index(term)
        except ValueError:
            raise ValueError(f"tiết khí không có trong danh sách: {term!r}") from None
    if not 0 <= term <= 23:
        raise ValueError(f"chỉ số tiết khí không hợp lệ: {term}")
    jd_start = jd_from_date(1, 1, solar_year)
    jd_end = jd_from_date(31, 12, solar_year)
    # Mồi bằng ngày 31/12 năm trước, nếu không ngày 1/1 luôn bị coi là "mới bắt đầu".
    prev = _tiet_khi_index_jdn(jd_start - 1, timezone)
    for jdn in range(jd_start, jd_end + 1):
        idx = _tiet_khi_index_jdn(jdn, timezone)
        if idx == term and prev != term:
            d, m, y = jd_to_date(jdn)
            return date(y, m, d)
        prev = idx
    raise ValueError(f"tiết khí {TIET_KHI[term]} không bắt đầu trong năm {solar_year}")


# ---------------------------------------------------------------------------
# Múi giờ lịch sử
# ---------------------------------------------------------------------------
def vietnam_timezone_for_year(solar_year: int) -> float:
    """Múi giờ mà lịch VN dùng cho năm dương ``solar_year`` — CHỈ dùng cho năm cũ.

    Sự thật đắt giá: **từ 1968 lịch miền Bắc chuyển sang UTC+7, miền Nam giữ UTC+8
    tới 1975** ⇒ Tết Mậu Thân 1968 hai miền lệch nhau 1 ngày (29/01 vs 30/01/1968).
    Hàm này trả múi giờ của **miền Bắc / lịch nhà nước hiện hành**; muốn tra lịch
    miền Nam giai đoạn 1968–1975 phải truyền ``TZ_CHINA`` (8.0) tường minh.

    Trước 1968 module KHÔNG được coi là đã kiểm chứng — trả 8.0 chỉ là xấp xỉ
    tốt nhất, hãy tự đối chiếu bảng lịch của Hồ Ngọc Đức trước khi công bố.
    """
    return TZ_VIETNAM if solar_year >= 1968 else TZ_CHINA
