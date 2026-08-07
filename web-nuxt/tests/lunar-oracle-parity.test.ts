// @vitest-environment node
//
// Parity giữa composables/useLunar.ts (chạy thật trên le-hoi/su-kien/useEventCalendar)
// và ORACLE agent/lunar_calendar.py (108 test, Hồ Ngọc Đức + Meeus, timezone 7.0).
//
// Fixture tests/fixtures/lunar-oracle.json được SINH TỪ oracle Python — không gõ tay.
// Nếu oracle đổi, sinh lại fixture rồi chạy lại; KHÔNG nới assertion cho xanh.

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  solarToLunar,
  lunarLabel,
  isLunarFirstDay,
  isLunarFull,
  jdFromDate,
  jdToDate,
  lunarToSolar,
  tryLunarToSolar,
  canChiYear,
  canChiMonth,
  canChiDay,
  canChiHour,
  hourToChiIndex,
  tietKhiIndex,
  tietKhiName,
  tietKhiStartDate,
  tietKhiStartDatesOfYear,
  isSupportedLunarYear,
  LUNAR_CAN,
  LUNAR_CHI,
  LUNAR_YEAR_MIN,
  LUNAR_YEAR_MAX,
  TIET_KHI,
  type SolarDate,
} from '../composables/useLunar'

type DailyRow = [iso: string, day: number, month: number, year: number, leap: boolean]
type TetRow = [lunarYear: number, isoSolar: string]
type LeapRow = [solarYear: number, leaps: Array<[lunarYear: number, leapMonth: number]>]
type JdRow = [iso: string, jdn: number]
type CanChiDailyRow = [iso: string, canChi: string]
type CanChiYearRow = [lunarYear: number, canChi: string]
type CanChiMonthRow = [lunarMonth: number, lunarYear: number, canChi: string]
type CanChiHourRow = [iso: string, chiIndex: number, canChi: string]
type TietKhiDailyRow = [iso: string, index: number]
type TietKhiStartRow = [solarYear: number, starts: Array<[term: number, iso: string]>]
type LunarToSolarRow = [
  lunarDay: number, lunarMonth: number, lunarYear: number, leap: boolean, iso: string | null,
]

interface Fixture {
  meta: {
    source: string
    timezone: number
    denseYears: number[]
    tetYears: number[]
    canChiDailyYears: number[]
    tietKhiYears: number[]
    lunarToSolarYears: number[]
    tietKhiNames: string[]
    can: string[]
    chi: string[]
  }
  daily: DailyRow[]
  tet: TetRow[]
  leapMonths: LeapRow[]
  jd: JdRow[]
  canChiDaily: CanChiDailyRow[]
  canChiYear: CanChiYearRow[]
  canChiMonth: CanChiMonthRow[]
  canChiHour: CanChiHourRow[]
  tietKhiDaily: TietKhiDailyRow[]
  tietKhiStarts: TietKhiStartRow[]
  lunarToSolar: LunarToSolarRow[]
}

const fixture: Fixture = JSON.parse(
  readFileSync(fileURLToPath(new URL('./fixtures/lunar-oracle.json', import.meta.url)), 'utf-8'),
)

function parseIso(iso: string): [number, number, number] {
  const [y, m, d] = iso.split('-').map(Number)
  return [d as number, m as number, y as number]
}

/** "d/m[N]/y" — dạng gọn để so sánh và để thông báo lỗi đọc được. */
function fmt(day: number, month: number, year: number, leap: boolean): string {
  return `${day}/${month}${leap ? 'N' : ''}/${year}`
}

const dailyByYear = new Map<number, DailyRow[]>()
for (const row of fixture.daily) {
  const y = Number(row[0].slice(0, 4))
  const bucket = dailyByYear.get(y)
  if (bucket) bucket.push(row)
  else dailyByYear.set(y, [row])
}

describe('useLunar ⇄ oracle Python: parity từng ngày', () => {
  it.each(fixture.meta.denseYears)('mọi ngày dương của năm %i khớp oracle', (year) => {
    const rows = dailyByYear.get(year)
    expect(rows, `fixture thiếu năm ${year}`).toBeDefined()
    const mismatches: string[] = []
    for (const [iso, oDay, oMonth, oYear, oLeap] of rows as DailyRow[]) {
      const [dd, mm, yy] = parseIso(iso)
      const got = solarToLunar(dd, mm, yy)
      const want = fmt(oDay, oMonth, oYear, oLeap)
      const have = fmt(got.day, got.month, got.year, got.leap)
      if (have !== want) mismatches.push(`${iso}: TS=${have} ≠ oracle=${want}`)
    }
    expect(
      mismatches.length,
      `${mismatches.length}/${(rows as DailyRow[]).length} ngày sai trong ${year}. ` +
        `Ví dụ:\n${mismatches.slice(0, 8).join('\n')}`,
    ).toBe(0)
  })
})

describe('useLunar ⇄ oracle Python: ngày Tết 2015–2030', () => {
  it.each(fixture.tet)('mùng 1 Tết năm âm %i rơi đúng ngày dương %s', (lunarYear, iso) => {
    const [dd, mm, yy] = parseIso(iso)
    const got = solarToLunar(dd, mm, yy)
    expect(fmt(got.day, got.month, got.year, got.leap)).toBe(fmt(1, 1, lunarYear as number, false))
    expect(isLunarFirstDay(dd, mm, yy)).toBe(true)
  })
})

describe('useLunar ⇄ oracle Python: tháng nhuận', () => {
  it.each(fixture.leapMonths)(
    'năm dương %i có đúng bộ tháng nhuận oracle chỉ ra',
    (solarYear, wantLeaps) => {
      const rows = dailyByYear.get(solarYear as number) as DailyRow[]
      const seen: string[] = []
      for (const [iso] of rows) {
        const [dd, mm, yy] = parseIso(iso)
        const got = solarToLunar(dd, mm, yy)
        const key = `${got.year}-${got.month}`
        if (got.leap && !seen.includes(key)) seen.push(key)
      }
      const want = (wantLeaps as LeapRow[1]).map(([ly, lm]) => `${ly}-${lm}`)
      expect(seen).toEqual(want)
    },
  )

  it('nhuận tháng 6/2025: 25/07–22/08/2025 là tháng 6 NHUẬN, không phải tháng 7', () => {
    const first = solarToLunar(25, 7, 2025)
    expect(fmt(first.day, first.month, first.year, first.leap)).toBe('1/6N/2025')
    const mid = solarToLunar(8, 8, 2025)
    expect([mid.month, mid.leap]).toEqual([6, true])
    const last = solarToLunar(22, 8, 2025)
    expect([last.day, last.month, last.leap]).toEqual([29, 6, true])
    // ngày sau đó mới là mùng 1 tháng 7 (không nhuận)
    const next = solarToLunar(23, 8, 2025)
    expect([next.day, next.month, next.leap]).toEqual([1, 7, false])
  })
})

describe('useLunar: bất biến cấu trúc 1900–2100', () => {
  it('KHÔNG BAO GIỜ có ngày âm 0 hoặc 31 (và tháng luôn 1–12)', () => {
    const bad: string[] = []
    let cursor = Date.UTC(1900, 0, 1)
    const end = Date.UTC(2100, 11, 31)
    while (cursor <= end) {
      const d = new Date(cursor)
      const dd = d.getUTCDate()
      const mm = d.getUTCMonth() + 1
      const yy = d.getUTCFullYear()
      const l = solarToLunar(dd, mm, yy)
      if (l.day < 1 || l.day > 30 || l.month < 1 || l.month > 12) {
        bad.push(`${yy}-${String(mm).padStart(2, '0')}-${String(dd).padStart(2, '0')} → ${fmt(l.day, l.month, l.year, l.leap)}`)
      }
      cursor += 86400000
    }
    expect(bad.length, `${bad.length} ngày ngoài biên. Ví dụ:\n${bad.slice(0, 12).join('\n')}`).toBe(0)
  })

  it('mỗi tháng âm dài 29 hoặc 30 ngày, đánh số liên tục từ 1 (mẫu 2020–2030)', () => {
    const lengths = new Set<number>()
    const breaks: string[] = []
    let prev = solarToLunar(1, 1, 2020)
    let run = prev.day
    let cursor = Date.UTC(2020, 0, 2)
    const end = Date.UTC(2030, 11, 31)
    while (cursor <= end) {
      const d = new Date(cursor)
      const l = solarToLunar(d.getUTCDate(), d.getUTCMonth() + 1, d.getUTCFullYear())
      if (l.day === 1) {
        lengths.add(run)
        run = 1
      } else if (l.day !== prev.day + 1) {
        breaks.push(`${d.toISOString().slice(0, 10)}: ${prev.day} → ${l.day}`)
        run = l.day
      } else {
        run = l.day
      }
      prev = l
      cursor += 86400000
    }
    expect(breaks, `ngày âm nhảy cóc:\n${breaks.slice(0, 10).join('\n')}`).toEqual([])
    expect([...lengths].sort((a, b) => a - b)).toEqual([29, 30])
  })
})

describe('useLunar: mốc THẬT (không phải parity — đối chiếu lịch dân dụng)', () => {
  it('rằm tháng Bảy 2025 = 06/09/2025 (không phải 08/08)', () => {
    const l = solarToLunar(6, 9, 2025)
    expect([l.day, l.month, l.leap]).toEqual([15, 7, false])
    expect(isLunarFull(6, 9, 2025)).toBe(true)
    // 08/08/2025 IS a rằm — but of the LEAP 6th month. The old bug labelled it 15/7,
    // which is what moved Vu Lan a month early. Assert the month, not the fullness.
    const old = solarToLunar(8, 8, 2025)
    expect([old.day, old.month, old.leap]).toEqual([15, 6, true])
  })

  it('Đoan Ngọ 2025 (mùng 5 tháng 5) = 31/05/2025 (không phải 01/06)', () => {
    const l = solarToLunar(31, 5, 2025)
    expect([l.day, l.month, l.leap]).toEqual([5, 5, false])
    expect(solarToLunar(27, 5, 2025)).toMatchObject({ day: 1, month: 5, leap: false })
  })

  it('Tết Bính Ngọ 2026 = 17/02/2026', () => {
    const l = solarToLunar(17, 2, 2026)
    expect([l.day, l.month, l.year, l.leap]).toEqual([1, 1, 2026, false])
    expect(lunarLabel(17, 2, 2026)).toBe('1/1')
  })
})

// ---------------------------------------------------------------------------
// Khối mở rộng: các hàm vừa port từ oracle (jd, âm→dương, can chi, tiết khí).
// Cùng một luật: fixture sinh từ Python, KHÔNG gõ số tay, KHÔNG nới assertion.
// ---------------------------------------------------------------------------

function isoOf(d: SolarDate): string {
  return `${String(d.year).padStart(4, '0')}-${String(d.month).padStart(2, '0')}-${String(d.day).padStart(2, '0')}`
}

describe('useLunar ⇄ oracle: Julian Day hai chiều', () => {
  it('jdFromDate khớp oracle (mọi ngày 2025 + mốc chuyển lịch Julius 1582)', () => {
    const bad: string[] = []
    for (const [iso, jdn] of fixture.jd) {
      const [dd, mm, yy] = parseIso(iso)
      const got = jdFromDate(dd, mm, yy)
      if (got !== jdn) bad.push(`${iso}: TS=${got} ≠ oracle=${jdn}`)
    }
    expect(bad, bad.slice(0, 8).join('\n')).toEqual([])
  })

  it('jdToDate là nghịch đảo đúng của jdFromDate trên cùng bộ mốc', () => {
    const bad: string[] = []
    for (const [iso, jdn] of fixture.jd) {
      const back = isoOf(jdToDate(jdn))
      if (back !== iso) bad.push(`JDN ${jdn}: TS=${back} ≠ oracle=${iso}`)
    }
    expect(bad, bad.slice(0, 8).join('\n')).toEqual([])
  })
})

describe('useLunar ⇄ oracle: âm → dương (lunarToSolar)', () => {
  it('khớp oracle trên MỌI (ngày, tháng, nhuận) của năm âm 2020–2030 — kể cả ca không tồn tại', () => {
    const bad: string[] = []
    for (const [dd, mm, yy, leap, iso] of fixture.lunarToSolar) {
      const got = tryLunarToSolar(dd, mm, yy, leap)
      const have = got ? isoOf(got) : null
      if (have !== iso) bad.push(`${dd}/${mm}${leap ? 'N' : ''}/${yy}: TS=${have} ≠ oracle=${iso}`)
    }
    expect(
      bad.length,
      `${bad.length}/${fixture.lunarToSolar.length} ca sai. Ví dụ:\n${bad.slice(0, 10).join('\n')}`,
    ).toBe(0)
  })

  it('fixture thật sự có cả ca hợp lệ lẫn ca KHÔNG tồn tại (test không rỗng nghĩa)', () => {
    const nulls = fixture.lunarToSolar.filter(r => r[4] === null).length
    expect(nulls).toBeGreaterThan(0)
    expect(fixture.lunarToSolar.length - nulls).toBeGreaterThan(3000)
  })

  it('ngày 30 của tháng thiếu ném lỗi, không trả bừa một ngày dương', () => {
    // Tháng 6 nhuận 2025 kết thúc ngày 29 (22/08/2025) — đã khẳng định ở khối trên.
    expect(() => lunarToSolar(30, 6, 2025, true)).toThrow(/không tồn tại/)
    expect(tryLunarToSolar(30, 6, 2025, true)).toBeNull()
  })

  it('xin tháng nhuận mà năm âm đó không có → lỗi', () => {
    expect(() => lunarToSolar(1, 3, 2026, true)).toThrow(/không có tháng/)
    expect(() => lunarToSolar(1, 7, 2025, true)).toThrow(/không có tháng 7 nhuận/)
  })

  it('tham số ngoài miền → lỗi (không âm thầm kẹp giá trị)', () => {
    expect(() => lunarToSolar(1, 13, 2025)).toThrow(/tháng âm không hợp lệ/)
    expect(() => lunarToSolar(0, 1, 2025)).toThrow(/ngày âm không hợp lệ/)
    expect(() => lunarToSolar(31, 1, 2025)).toThrow(/ngày âm không hợp lệ/)
  })

  it('Tết mọi năm 2015–2030: lunarToSolar(1,1,y) khớp bảng Tết của oracle', () => {
    for (const [lunarYear, iso] of fixture.tet) {
      expect(isoOf(lunarToSolar(1, 1, lunarYear)), `Tết ${lunarYear}`).toBe(iso)
    }
  })

  it('vòng tròn dương→âm→dương đóng lại trên mọi ngày 2024–2027', () => {
    const bad: string[] = []
    let cursor = Date.UTC(2024, 0, 1)
    const end = Date.UTC(2027, 11, 31)
    while (cursor <= end) {
      const d = new Date(cursor)
      const dd = d.getUTCDate()
      const mm = d.getUTCMonth() + 1
      const yy = d.getUTCFullYear()
      const l = solarToLunar(dd, mm, yy)
      const back = tryLunarToSolar(l.day, l.month, l.year, l.leap)
      const iso = d.toISOString().slice(0, 10)
      if (!back || isoOf(back) !== iso) bad.push(`${iso} → ${l.day}/${l.month}${l.leap ? 'N' : ''}/${l.year} → ${back ? isoOf(back) : 'null'}`)
      cursor += 86400000
    }
    expect(bad, bad.slice(0, 8).join('\n')).toEqual([])
  })
})

describe('useLunar ⇄ oracle: can chi', () => {
  it('bảng CAN/CHI đúng bằng bảng của oracle', () => {
    expect([...LUNAR_CAN]).toEqual(fixture.meta.can)
    expect([...LUNAR_CHI]).toEqual(fixture.meta.chi)
  })

  it('can chi NGÀY khớp oracle từng ngày (2025–2026)', () => {
    const bad: string[] = []
    for (const [iso, want] of fixture.canChiDaily) {
      const [dd, mm, yy] = parseIso(iso)
      const got = canChiDay(dd, mm, yy)
      if (got !== want) bad.push(`${iso}: TS=${got} ≠ oracle=${want}`)
    }
    expect(bad.length, `${bad.length} ngày sai:\n${bad.slice(0, 8).join('\n')}`).toBe(0)
  })

  it('can chi NĂM khớp oracle suốt dải năm được hỗ trợ 1968–2199', () => {
    const bad: string[] = []
    for (const [lunarYear, want] of fixture.canChiYear) {
      const got = canChiYear(lunarYear)
      if (got !== want) bad.push(`${lunarYear}: TS=${got} ≠ oracle=${want}`)
    }
    expect(bad.length, `${bad.length} năm sai:\n${bad.slice(0, 8).join('\n')}`).toBe(0)
    expect(fixture.canChiYear.length).toBe(LUNAR_YEAR_MAX - LUNAR_YEAR_MIN + 1)
  })

  it('can chi THÁNG khớp oracle (12 tháng × năm âm 2020–2030)', () => {
    const bad: string[] = []
    for (const [lunarMonth, lunarYear, want] of fixture.canChiMonth) {
      const got = canChiMonth(lunarMonth, lunarYear)
      if (got !== want) bad.push(`${lunarMonth}/${lunarYear}: TS=${got} ≠ oracle=${want}`)
    }
    expect(bad.length, `${bad.length} tháng sai:\n${bad.slice(0, 8).join('\n')}`).toBe(0)
    // Tháng Giêng luôn mang chi Dần — nếu ai đảo thứ tự tham số, dòng này đỏ.
    expect(canChiMonth(1, 2025).endsWith('Dần')).toBe(true)
  })

  it('can chi 12 CANH GIỜ khớp oracle', () => {
    const bad: string[] = []
    for (const [iso, chiIndex, want] of fixture.canChiHour) {
      const [dd, mm, yy] = parseIso(iso)
      const got = canChiHour(dd, mm, yy, chiIndex)
      if (got !== want) bad.push(`${iso} canh ${chiIndex}: TS=${got} ≠ oracle=${want}`)
    }
    expect(bad, bad.join('\n')).toEqual([])
    expect(fixture.canChiHour.length).toBe(4 * 12)
  })

  it('canChiMonth/canChiHour ném lỗi khi tham số ngoài miền', () => {
    expect(() => canChiMonth(0, 2025)).toThrow(/tháng âm không hợp lệ/)
    expect(() => canChiMonth(13, 2025)).toThrow(/tháng âm không hợp lệ/)
    expect(() => canChiHour(1, 1, 2025, -1)).toThrow(/chi giờ không hợp lệ/)
    expect(() => canChiHour(1, 1, 2025, 12)).toThrow(/chi giờ không hợp lệ/)
  })

  it('hourToChiIndex: 23h và 0h cùng là giờ Tý, mỗi canh dài đúng 2 giờ đồng hồ', () => {
    expect(hourToChiIndex(23)).toBe(0)
    expect(hourToChiIndex(0)).toBe(0)
    expect(hourToChiIndex(1)).toBe(1)
    expect(hourToChiIndex(2)).toBe(1)
    expect(hourToChiIndex(11)).toBe(6) // 11:00 → giờ Ngọ
    const counts = new Map<number, number>()
    for (let h = 0; h < 24; h++) counts.set(hourToChiIndex(h), (counts.get(hourToChiIndex(h)) || 0) + 1)
    expect([...counts.keys()].sort((a, b) => a - b)).toEqual([...Array(12).keys()])
    expect([...new Set(counts.values())]).toEqual([2])
  })
})

describe('useLunar ⇄ oracle: tiết khí', () => {
  it('bảng 24 tên tiết khí đúng bằng bảng của oracle (index 0 = Xuân phân)', () => {
    expect([...TIET_KHI]).toEqual(fixture.meta.tietKhiNames)
    expect(TIET_KHI[0]).toBe('Xuân phân')
    expect(TIET_KHI[18]).toBe('Đông chí')
    expect(TIET_KHI[21]).toBe('Lập xuân')
  })

  it('chỉ số tiết khí khớp oracle từng ngày (2024–2027)', () => {
    const bad: string[] = []
    for (const [iso, want] of fixture.tietKhiDaily) {
      const [dd, mm, yy] = parseIso(iso)
      const got = tietKhiIndex(dd, mm, yy)
      if (got !== want) bad.push(`${iso}: TS=${got}(${TIET_KHI[got]}) ≠ oracle=${want}(${TIET_KHI[want]})`)
    }
    expect(
      bad.length,
      `${bad.length}/${fixture.tietKhiDaily.length} ngày sai:\n${bad.slice(0, 10).join('\n')}`,
    ).toBe(0)
  })

  it('tietKhiName đọc đúng tên từ chỉ số', () => {
    for (const [iso, want] of fixture.tietKhiDaily.slice(0, 400)) {
      const [dd, mm, yy] = parseIso(iso)
      expect(tietKhiName(dd, mm, yy)).toBe(TIET_KHI[want])
    }
  })

  it('mốc bắt đầu của cả 24 tiết khí khớp oracle (2024–2027)', () => {
    const bad: string[] = []
    for (const [solarYear, starts] of fixture.tietKhiStarts) {
      expect(starts.length, `oracle phải cho 24 mốc trong ${solarYear}`).toBe(24)
      for (const [term, iso] of starts) {
        const got = isoOf(tietKhiStartDate(term, solarYear))
        if (got !== iso) bad.push(`${TIET_KHI[term]} ${solarYear}: TS=${got} ≠ oracle=${iso}`)
      }
    }
    expect(bad, bad.slice(0, 10).join('\n')).toEqual([])
  })

  it('tra theo TÊN cho cùng kết quả với tra theo chỉ số', () => {
    for (const [solarYear, starts] of fixture.tietKhiStarts) {
      for (const [term, iso] of starts) {
        expect(isoOf(tietKhiStartDate(TIET_KHI[term] as string, solarYear))).toBe(iso)
      }
    }
  })

  it('tietKhiStartDatesOfYear (một lượt quét) cho đúng bộ mốc như oracle', () => {
    for (const [solarYear, starts] of fixture.tietKhiStarts) {
      const map = tietKhiStartDatesOfYear(solarYear)
      expect(map.size, `năm ${solarYear}`).toBe(starts.length)
      for (const [term, iso] of starts) {
        expect(isoOf(map.get(term) as SolarDate), `${TIET_KHI[term]} ${solarYear}`).toBe(iso)
      }
    }
  })

  it('tiết khí sai tên / sai chỉ số → lỗi', () => {
    expect(() => tietKhiStartDate('Lập thân', 2025)).toThrow(/không có trong danh sách/)
    expect(() => tietKhiStartDate(24, 2025)).toThrow(/không hợp lệ/)
    expect(() => tietKhiStartDate(-1, 2025)).toThrow(/không hợp lệ/)
  })
})

describe('useLunar: dải năm bản TS dám nhận', () => {
  it('chặn dưới là 1968 vì TZ ghim cứng 7.0 — trước đó lịch VN không dùng UTC+7', () => {
    expect(LUNAR_YEAR_MIN).toBe(1968)
    expect(LUNAR_YEAR_MAX).toBe(2199)
    expect(isSupportedLunarYear(1967)).toBe(false)
    expect(isSupportedLunarYear(1968)).toBe(true)
    expect(isSupportedLunarYear(2199)).toBe(true)
    expect(isSupportedLunarYear(2200)).toBe(false)
    expect(isSupportedLunarYear(2025.5)).toBe(false)
    expect(isSupportedLunarYear(Number.NaN)).toBe(false)
  })
})
