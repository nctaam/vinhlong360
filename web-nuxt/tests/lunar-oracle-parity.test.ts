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
import { solarToLunar, lunarLabel, isLunarFirstDay, isLunarFull } from '../composables/useLunar'

type DailyRow = [iso: string, day: number, month: number, year: number, leap: boolean]
type TetRow = [lunarYear: number, isoSolar: string]
type LeapRow = [solarYear: number, leaps: Array<[lunarYear: number, leapMonth: number]>]

interface Fixture {
  meta: { source: string; timezone: number; denseYears: number[]; tetYears: number[] }
  daily: DailyRow[]
  tet: TetRow[]
  leapMonths: LeapRow[]
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
