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


def main() -> None:
    out = {
        "meta": {
            "source": "agent/lunar_calendar.py",
            "generator": "scripts/gen_lunar_fixture.py",
            "timezone": TZ,
            "note": "SINH TỰ ĐỘNG — KHÔNG sửa tay. Chạy lại generator khi oracle đổi.",
            "denseYears": DENSE_YEARS,
            "tetYears": TET_YEARS,
            "format": {
                "daily": "[isoSolarDate, lunarDay, lunarMonth, lunarYear, isLeapMonth]",
                "tet": "[lunarYear, isoSolarDateOfLunar_1_1]",
                "leapMonths": "[solarYear, [[lunarYear, leapLunarMonth], ...]]",
            },
        },
        "daily": daily_rows(),
        "tet": tet_rows(),
        "leapMonths": leap_month_rows(),
    }
    dest = REPO / "web-nuxt" / "tests" / "fixtures" / "lunar-oracle.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"wrote {dest} - daily={len(out['daily'])} tet={len(out['tet'])}")


if __name__ == "__main__":
    main()
