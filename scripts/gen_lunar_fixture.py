"""Sinh fixture parity cho `web-nuxt/composables/useLunar.ts` TỪ oracle `agent/lunar_calendar.py`.

Bản TS là bản port của lõi Python; ORACLE là Python (108 test, Hồ Ngọc Đức + Meeus, tz=7.0).
Fixture sinh ra: `web-nuxt/tests/fixtures/lunar-oracle.json`, tiêu thụ bởi
`web-nuxt/tests/lunar-oracle-parity.test.ts`.

Chạy lại MỖI KHI `agent/lunar_calendar.py` đổi:

    python scripts/gen_lunar_fixture.py
    cd web-nuxt && npx vitest run tests/lunar-oracle-parity.test.ts

KHÔNG sửa fixture bằng tay, và KHÔNG nới assertion trong test để cho xanh — nếu TS lệch
oracle thì sửa TS.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "agent"))

import lunar_calendar as L  # noqa: E402

TZ = L.TZ_VIETNAM

# Mỗi ngày của 2024–2027 (đủ bắt nhuận tháng 6/2025) + vài năm nhuận rải rác.
DENSE_YEARS = [2012, 2017, 2020, 2023, 2024, 2025, 2026, 2027, 2028]
TET_YEARS = list(range(2015, 2031))

# Khối mở rộng (JD / can chi / tiết khí / âm→dương). Các khối cũ ở trên KHÔNG đổi.
CANCHI_DAILY_YEARS = [2025, 2026]
TIETKHI_YEARS = [2024, 2025, 2026, 2027]
CANCHI_YEAR_RANGE = range(1968, 2200)  # đúng dải năm bản TS tự nhận hỗ trợ
LUNAR_TO_SOLAR_YEARS = list(range(2020, 2031))
CANCHI_HOUR_DATES = [(29, 1, 2025), (1, 1, 2000), (31, 5, 2025), (17, 2, 2026)]


def _days(yy: int):
    d, end = date(yy, 1, 1), date(yy, 12, 31)
    while d <= end:
        yield d
        d += timedelta(days=1)


def daily_rows() -> list[list]:
    rows: list[list] = []
    for yy in DENSE_YEARS:
        for d in _days(yy):
            lu = L.solar_to_lunar(d.day, d.month, d.year, TZ)
            rows.append([d.isoformat(), lu.day, lu.month, lu.year, lu.leap])
    return rows


def tet_rows() -> list[list]:
    return [[yy, L.lunar_to_solar(1, 1, yy, False, TZ).isoformat()] for yy in TET_YEARS]


def leap_month_rows() -> list[list]:
    """Với mỗi năm dense: tháng nhuận (nếu có) suy ra từ chính bảng ngày của oracle."""
    rows: list[list] = []
    for yy in DENSE_YEARS:
        found: list[list] = []
        seen: set[tuple[int, int]] = set()
        for d in _days(yy):
            lu = L.solar_to_lunar(d.day, d.month, d.year, TZ)
            if lu.leap and (lu.year, lu.month) not in seen:
                seen.add((lu.year, lu.month))
                found.append([lu.year, lu.month])
        rows.append([yy, found])
    return rows


def jd_rows() -> list[list]:
    """JDN của mốc dương lịch — khoá cả hai chiều jd_from_date ⇄ jd_to_date.

    Có cả 04/10/1582 và 15/10/1582 để chạm nhánh lịch Julius (jd < 2299161).
    """
    rows: list[list] = [
        [f"{y:04d}-{m:02d}-{d:02d}", L.jd_from_date(d, m, y)]
        for (d, m, y) in [
            (4, 10, 1582), (15, 10, 1582), (1, 1, 1900),
            (1, 1, 1968), (1, 1, 2000), (31, 12, 2199),
        ]
    ]
    rows += [[d.isoformat(), L.jd_from_date(d.day, d.month, d.year)] for d in _days(2025)]
    return rows


def can_chi_daily_rows() -> list[list]:
    return [
        [d.isoformat(), L.can_chi_day(d.day, d.month, d.year)]
        for yy in CANCHI_DAILY_YEARS
        for d in _days(yy)
    ]


def can_chi_year_rows() -> list[list]:
    return [[yy, L.can_chi_year(yy)] for yy in CANCHI_YEAR_RANGE]


def can_chi_month_rows() -> list[list]:
    return [
        [mm, yy, L.can_chi_month(mm, yy)]
        for yy in LUNAR_TO_SOLAR_YEARS
        for mm in range(1, 13)
    ]


def can_chi_hour_rows() -> list[list]:
    return [
        [f"{yy:04d}-{mm:02d}-{dd:02d}", ci, L.can_chi_hour(dd, mm, yy, ci)]
        for (dd, mm, yy) in CANCHI_HOUR_DATES
        for ci in range(12)
    ]


def tiet_khi_daily_rows() -> list[list]:
    return [
        [d.isoformat(), L.tiet_khi_index(d.day, d.month, d.year, TZ)]
        for yy in TIETKHI_YEARS
        for d in _days(yy)
    ]


def tiet_khi_start_rows() -> list[list]:
    """Mốc bắt đầu của cả 24 tiết khí trong mỗi năm mẫu."""
    rows: list[list] = []
    for yy in TIETKHI_YEARS:
        starts = []
        for term in range(24):
            try:
                starts.append([term, L.tiet_khi_start_date(term, yy, TZ).isoformat()])
            except ValueError:
                pass  # tiết khí không bắt đầu trong năm này — TS cũng phải không có
        rows.append([yy, starts])
    return rows


def lunar_to_solar_rows() -> list[list]:
    """Mọi (ngày, tháng, nhuận?) của các năm âm mẫu — kể cả ca KHÔNG tồn tại (null).

    Ngày 30 của tháng thiếu và tháng-nhuận-không-có-thật phải cùng lỗi ở hai bản.
    """
    rows: list[list] = []
    for yy in LUNAR_TO_SOLAR_YEARS:
        for mm in range(1, 13):
            for leap in (False, True):
                for dd in range(1, 31):
                    try:
                        iso = L.lunar_to_solar(dd, mm, yy, leap, TZ).isoformat()
                    except ValueError:
                        iso = None
                    rows.append([dd, mm, yy, leap, iso])
    return rows


def main() -> None:
    out = {
        "meta": {
            "source": "agent/lunar_calendar.py",
            "generator": "scripts/gen_lunar_fixture.py",
            "timezone": TZ,
            "note": "SINH TỰ ĐỘNG — KHÔNG sửa tay. Chạy lại generator khi oracle đổi.",
            "denseYears": DENSE_YEARS,
            "tetYears": TET_YEARS,
            "canChiDailyYears": CANCHI_DAILY_YEARS,
            "tietKhiYears": TIETKHI_YEARS,
            "lunarToSolarYears": LUNAR_TO_SOLAR_YEARS,
            "tietKhiNames": list(L.TIET_KHI),
            "can": list(L.CAN),
            "chi": list(L.CHI),
            "format": {
                "daily": "[isoSolarDate, lunarDay, lunarMonth, lunarYear, isLeapMonth]",
                "tet": "[lunarYear, isoSolarDateOfLunar_1_1]",
                "leapMonths": "[solarYear, [[lunarYear, leapLunarMonth], ...]]",
                "jd": "[isoSolarDate, julianDayNumber]",
                "canChiDaily": "[isoSolarDate, canChiOfDay]",
                "canChiYear": "[lunarYear, canChi]",
                "canChiMonth": "[lunarMonth, lunarYear, canChi]",
                "canChiHour": "[isoSolarDate, chiIndex, canChi]",
                "tietKhiDaily": "[isoSolarDate, tietKhiIndex]",
                "tietKhiStarts": "[solarYear, [[termIndex, isoStartDate], ...]]",
                "lunarToSolar": "[lunarDay, lunarMonth, lunarYear, leap, isoSolarDate|null]",
            },
        },
        "daily": daily_rows(),
        "tet": tet_rows(),
        "leapMonths": leap_month_rows(),
        "jd": jd_rows(),
        "canChiDaily": can_chi_daily_rows(),
        "canChiYear": can_chi_year_rows(),
        "canChiMonth": can_chi_month_rows(),
        "canChiHour": can_chi_hour_rows(),
        "tietKhiDaily": tiet_khi_daily_rows(),
        "tietKhiStarts": tiet_khi_start_rows(),
        "lunarToSolar": lunar_to_solar_rows(),
    }
    dest = REPO / "web-nuxt" / "tests" / "fixtures" / "lunar-oracle.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(
        f"wrote {dest} - daily={len(out['daily'])} tet={len(out['tet'])} "
        f"canChiDaily={len(out['canChiDaily'])} tietKhiDaily={len(out['tietKhiDaily'])} "
        f"lunarToSolar={len(out['lunarToSolar'])}"
    )


if __name__ == "__main__":
    main()
