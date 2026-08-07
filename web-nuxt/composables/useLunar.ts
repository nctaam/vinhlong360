// Lunar calendar conversion — based on Hồ Ngọc Đức's algorithm (Meeus ch.25 + ch.49).
// Covers years 1900–2100, timezone UTC+7 (Vietnam — NOT UTC+8 like the Chinese calendar).
//
// ORACLE: agent/lunar_calendar.py. This file must stay bit-for-bit in agreement with it —
// tests/lunar-oracle-parity.test.ts compares against a fixture generated from that module.
// Do not "improve" the astronomy here without regenerating the fixture and re-reading the
// oracle's own comments; two subtle traps live below (sampling offset, and the k step-back).

const PI = Math.PI
const TZ = 7.0 / 24 // fraction of a day
const SYNODIC = 29.530588853 // mean synodic month (days)
const NM_EPOCH = 2415021.076998695 // JD of new moon k=0

export function jdFromDate(dd: number, mm: number, yy: number): number {
  const a = Math.floor((14 - mm) / 12)
  const y = yy + 4800 - a
  const m = mm + 12 * a - 3
  let jd = dd + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045
  if (jd < 2299161) {
    jd = dd + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - 32083
  }
  return jd
}

function newMoon(k: number): number {
  const T = k / 1236.85
  const T2 = T * T
  const T3 = T2 * T
  const dr = PI / 180
  let Jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
  Jd1 += 0.00033 * Math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
  const M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
  const Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
  const F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
  let C1 = (0.1734 - 0.000393 * T) * Math.sin(M * dr) + 0.0021 * Math.sin(2 * dr * M)
  C1 = C1 - 0.4068 * Math.sin(Mpr * dr) + 0.0161 * Math.sin(dr * 2 * Mpr)
  C1 = C1 - 0.0004 * Math.sin(dr * 3 * Mpr)
  C1 = C1 + 0.0104 * Math.sin(dr * 2 * F) - 0.0051 * Math.sin(dr * (M + Mpr))
  C1 = C1 - 0.0074 * Math.sin(dr * (M - Mpr)) + 0.0004 * Math.sin(dr * (2 * F + M))
  C1 = C1 - 0.0004 * Math.sin(dr * (2 * F - M)) - 0.0006 * Math.sin(dr * (2 * F + Mpr))
  C1 = C1 + 0.001 * Math.sin(dr * (2 * F - Mpr)) + 0.0005 * Math.sin(dr * (2 * Mpr + M))
  let deltat: number
  if (T < -11) {
    deltat = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
  } else {
    deltat = -0.000278 + 0.000265 * T + 0.000262 * T2
  }
  return Jd1 + C1 - deltat
}

/** Apparent ecliptic longitude of the sun at instant `jd`, in degrees [0, 360). */
function sunLongitudeDegrees(jd: number): number {
  const T = (jd - 2451545.0) / 36525
  const T2 = T * T
  const dr = PI / 180
  const M = 357.5291 + 35999.0503 * T - 0.0001559 * T2 - 0.00000048 * T * T2
  const L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
  let DL = (1.9146 - 0.004817 * T - 0.000014 * T2) * Math.sin(dr * M)
  DL = DL + (0.019993 - 0.000101 * T) * Math.sin(dr * 2 * M) + 0.00029 * Math.sin(dr * 3 * M)
  let lon = (L0 + DL) % 360
  if (lon < 0) lon += 360
  return lon
}

/**
 * 30° sector (0..11) holding the sun at 00:00 local time on day `jdn`.
 *
 * The `- 0.5` is mandatory: a JDN starts at 12:00 UTC, so sampling at `jdn` alone is
 * half a day (~0.5° of sun) late. Dropping it misplaces the leap month in 22 windows
 * between 1900 and 2100 — e.g. it hid the leap 6th month of 2025 and pushed rằm tháng
 * Bảy from 06/09/2025 to 08/08/2025.
 */
function sunLongitudeSector(jdn: number): number {
  return Math.floor(sunLongitudeDegrees(jdn - 0.5 - TZ) / 30)
}

function getNewMoonDay(k: number): number {
  return Math.floor(newMoon(k) + 0.5 + TZ)
}

function getLunarMonth11(yy: number): number {
  const off = jdFromDate(31, 12, yy) - 2415021
  const k = Math.floor(off / SYNODIC)
  let nm = getNewMoonDay(k)
  if (sunLongitudeSector(nm) >= 9) {
    nm = getNewMoonDay(k - 1)
  }
  return nm
}

function getLeapMonthOffset(a11: number): number {
  const k = Math.floor((a11 - NM_EPOCH) / SYNODIC + 0.5)
  let last = 0
  let i = 1
  let arc = sunLongitudeSector(getNewMoonDay(k + i))
  do {
    last = arc
    i++
    arc = sunLongitudeSector(getNewMoonDay(k + i))
  } while (arc !== last && i < 14)
  return i - 1
}

export interface LunarDate {
  day: number
  month: number
  year: number
  leap: boolean
}

export function solarToLunar(dd: number, mm: number, yy: number): LunarDate {
  const dayNumber = jdFromDate(dd, mm, yy)
  // `k` is estimated from the MEAN synodic month, so it can be off by ±1 against the true
  // new moon (which runs up to ~0.7 days early/late). Hồ Ngọc Đức's original steps back
  // exactly once (`k+1` then `k`) — not enough: 07/05/2054 and 09/04/2062 fall in that gap
  // and yield lunar day 0. Step back in a LOOP until the 1st really is ≤ the queried day.
  // (Same fix as agent/lunar_calendar.py; guarded by the 1900–2100 range invariant test.)
  let k = Math.floor((dayNumber - NM_EPOCH) / SYNODIC) + 1
  let monthStart = getNewMoonDay(k)
  while (monthStart > dayNumber) {
    k--
    monthStart = getNewMoonDay(k)
  }
  let a11 = getLunarMonth11(yy)
  let b11 = a11
  let lunarYear: number
  if (a11 >= monthStart) {
    lunarYear = yy
    a11 = getLunarMonth11(yy - 1)
  } else {
    lunarYear = yy + 1
    b11 = getLunarMonth11(yy + 1)
  }
  const lunarDay = dayNumber - monthStart + 1
  const diff = Math.floor((monthStart - a11) / 29)
  let lunarLeap = false
  let lunarMonth = diff + 11
  if (b11 - a11 > 365) {
    const leapMonthDiff = getLeapMonthOffset(a11)
    if (diff >= leapMonthDiff) {
      lunarMonth = diff + 10
      if (diff === leapMonthDiff) {
        lunarLeap = true
      }
    }
  }
  if (lunarMonth > 12) {
    lunarMonth = lunarMonth - 12
  }
  if (lunarMonth >= 11 && diff < 4) {
    lunarYear -= 1
  }
  return { day: lunarDay, month: lunarMonth, year: lunarYear, leap: lunarLeap }
}

export function lunarLabel(dd: number, mm: number, yy: number): string {
  const l = solarToLunar(dd, mm, yy)
  if (l.day === 1) return `${l.day}/${l.month}${l.leap ? 'n' : ''}`
  return String(l.day)
}

export function isLunarFirstDay(dd: number, mm: number, yy: number): boolean {
  return solarToLunar(dd, mm, yy).day === 1
}

export function isLunarFull(dd: number, mm: number, yy: number): boolean {
  return solarToLunar(dd, mm, yy).day === 15
}

// ---------------------------------------------------------------------------
// Ported from the oracle (agent/lunar_calendar.py) — everything below has a
// one-to-one Python counterpart and is locked by tests/lunar-oracle-parity.test.ts.
//
// NO Nuxt auto-imports in this file. The parity suite runs under
// `@vitest-environment node`; a bare `ref()`/`computed()` here would throw
// ReferenceError at import time and take all of it down with it.
// ---------------------------------------------------------------------------

/**
 * Years this FILE can be trusted for.
 *
 * The lower bound is 1968, not the oracle's 1200: `TZ` above is hardcoded to
 * UTC+7, and Vietnam's calendar only settled on UTC+7 in 1968 (the South kept
 * UTC+8 until 1975 — Tết Mậu Thân fell on two different days). Before that this
 * port silently returns the wrong day. The oracle takes an explicit `timezone`
 * argument and can go back to 1200; this port cannot, so it must not pretend to.
 * Above 2199 the low-precision Meeus series drifts.
 */
export const LUNAR_YEAR_MIN = 1968
export const LUNAR_YEAR_MAX = 2199

export function isSupportedLunarYear(year: number): boolean {
  return Number.isInteger(year) && year >= LUNAR_YEAR_MIN && year <= LUNAR_YEAR_MAX
}

/** Python's `%` is always non-negative; JS's is not. Every index below goes through this. */
function mod(n: number, m: number): number {
  return ((n % m) + m) % m
}

export const LUNAR_CAN = ['Giáp', 'Ất', 'Bính', 'Đinh', 'Mậu', 'Kỷ', 'Canh', 'Tân', 'Nhâm', 'Quý'] as const
export const LUNAR_CHI = ['Tý', 'Sửu', 'Dần', 'Mão', 'Thìn', 'Tỵ', 'Ngọ', 'Mùi', 'Thân', 'Dậu', 'Tuất', 'Hợi'] as const

/**
 * 24 tiết khí = 24 sectors of 15° of solar longitude. Index 0 is Xuân phân (0°),
 * NOT Lập xuân — that way `index === floor(degrees / 15)`. Đông chí is 18.
 */
export const TIET_KHI = [
  'Xuân phân', 'Thanh minh', 'Cốc vũ', 'Lập hạ', 'Tiểu mãn', 'Mang chủng',
  'Hạ chí', 'Tiểu thử', 'Đại thử', 'Lập thu', 'Xử thử', 'Bạch lộ',
  'Thu phân', 'Hàn lộ', 'Sương giáng', 'Lập đông', 'Tiểu tuyết', 'Đại tuyết',
  'Đông chí', 'Tiểu hàn', 'Đại hàn', 'Lập xuân', 'Vũ thủy', 'Kinh trập',
] as const

export interface SolarDate {
  day: number
  month: number
  year: number
}

/** Inverse of `jdFromDate`. Mirrors the oracle's `jd_to_date`. */
export function jdToDate(jd: number): SolarDate {
  let b: number
  let c: number
  if (jd > 2299160) {
    const a = jd + 32044
    b = Math.floor((4 * a + 3) / 146097)
    c = a - Math.floor((b * 146097) / 4)
  } else {
    b = 0
    c = jd + 32082
  }
  const d = Math.floor((4 * c + 3) / 1461)
  const e = c - Math.floor((1461 * d) / 4)
  const m = Math.floor((5 * e + 2) / 153)
  return {
    day: e - Math.floor((153 * m + 2) / 5) + 1,
    month: m + 3 - 12 * Math.floor(m / 10),
    year: b * 100 + d - 4800 + Math.floor(m / 10),
  }
}

/**
 * Lunar → solar. Throws when the lunar date does not exist (day 30 of a 29-day
 * month, or a leap month the year does not have) — same contract as the oracle's
 * `lunar_to_solar`, which raises ValueError.
 */
export function lunarToSolar(dd: number, mm: number, yy: number, leap = false): SolarDate {
  if (!(mm >= 1 && mm <= 12)) throw new Error(`tháng âm không hợp lệ: ${mm}`)
  if (!(dd >= 1 && dd <= 30)) throw new Error(`ngày âm không hợp lệ: ${dd}`)
  let a11: number
  let b11: number
  if (mm < 11) {
    a11 = getLunarMonth11(yy - 1)
    b11 = getLunarMonth11(yy)
  } else {
    a11 = getLunarMonth11(yy)
    b11 = getLunarMonth11(yy + 1)
  }
  let off = mm - 11
  if (off < 0) off += 12
  if (b11 - a11 > 365) {
    const leapOff = getLeapMonthOffset(a11)
    let leapMonth = leapOff - 2
    if (leapMonth < 0) leapMonth += 12
    if (leap && mm !== leapMonth) throw new Error(`năm âm ${yy} không có tháng ${mm} nhuận`)
    if (leap || off >= leapOff) off += 1
  } else if (leap) {
    throw new Error(`năm âm ${yy} không có tháng nhuận`)
  }
  const k = Math.floor(0.5 + (a11 - NM_EPOCH) / SYNODIC)
  const monthStart = getNewMoonDay(k + off)
  const jdn = monthStart + dd - 1
  // A 29-day month has no 30th. Detect it by converting back, exactly like the oracle.
  const solar = jdToDate(jdn)
  const back = solarToLunar(solar.day, solar.month, solar.year)
  if (back.day !== dd || back.month !== mm || back.leap !== leap) {
    throw new Error(
      `ngày âm ${dd}/${mm}${leap ? 'N' : ''}/${yy} không tồn tại (tháng thiếu); ` +
      `JDN ${jdn} ứng với ${back.day}/${back.month}${back.leap ? 'N' : ''}/${back.year}`,
    )
  }
  return solar
}

/** Non-throwing wrapper — returns null instead of throwing for a nonexistent date. */
export function tryLunarToSolar(dd: number, mm: number, yy: number, leap = false): SolarDate | null {
  try {
    return lunarToSolar(dd, mm, yy, leap)
  } catch {
    return null
  }
}

// --- Can chi ---------------------------------------------------------------

/** Can chi of a LUNAR year. `canChiYear(2025) === 'Ất Tỵ'`. */
export function canChiYear(lunarYear: number): string {
  return `${LUNAR_CAN[mod(lunarYear + 6, 10)]} ${LUNAR_CHI[mod(lunarYear + 8, 12)]}`
}

/** Can chi of a LUNAR month — note the argument order: month first, year second. */
export function canChiMonth(lunarMonth: number, lunarYear: number): string {
  if (!(lunarMonth >= 1 && lunarMonth <= 12)) throw new Error(`tháng âm không hợp lệ: ${lunarMonth}`)
  return `${LUNAR_CAN[mod(lunarYear * 12 + lunarMonth + 3, 10)]} ${LUNAR_CHI[mod(lunarMonth + 1, 12)]}`
}

/** Can chi of a day — an unbroken 60-day cycle, independent of timezone. Takes a SOLAR date. */
export function canChiDay(dd: number, mm: number, yy: number): string {
  const jd = jdFromDate(dd, mm, yy)
  return `${LUNAR_CAN[mod(jd + 9, 10)]} ${LUNAR_CHI[mod(jd + 1, 12)]}`
}

/**
 * Can chi of one of the 12 double-hours. `chiIndex` is NOT a clock hour:
 * 0 = giờ Tý (23:00–01:00), 1 = Sửu, … 11 = Hợi. Use `hourToChiIndex` to convert.
 */
export function canChiHour(dd: number, mm: number, yy: number, chiIndex: number): string {
  if (!(chiIndex >= 0 && chiIndex <= 11)) throw new Error(`chi giờ không hợp lệ: ${chiIndex}`)
  const canDay = mod(jdFromDate(dd, mm, yy) + 9, 10)
  return `${LUNAR_CAN[mod(canDay * 2 + chiIndex, 10)]} ${LUNAR_CHI[chiIndex]}`
}

/** Clock hour (0–23) → chi index (0–11). 23:00 and 00:00 both fall in giờ Tý. */
export function hourToChiIndex(hour24: number): number {
  return Math.floor(mod(hour24 + 1, 24) / 2)
}

// --- Tiết khí --------------------------------------------------------------

/**
 * Tiết khí of a day, sampled at the END of the local day.
 *
 * Civil convention: the day that CONTAINS the moment the sun crosses a 15° mark
 * carries the new term's name. The leap-month logic above deliberately samples
 * the START of the day instead (`sunLongitudeSector`) — two different questions,
 * do not merge them, or you break either tiết khí or the leap month.
 */
function tietKhiIndexForJdn(jdn: number): number {
  return Math.floor(sunLongitudeDegrees(jdn + 0.5 - TZ - 1 / 86400) / 15)
}

export function tietKhiIndex(dd: number, mm: number, yy: number): number {
  return tietKhiIndexForJdn(jdFromDate(dd, mm, yy))
}

export function tietKhiName(dd: number, mm: number, yy: number): string {
  return TIET_KHI[tietKhiIndex(dd, mm, yy)] as string
}

/**
 * Start date of every tiết khí that begins in `solarYear`, keyed by term index.
 * One linear scan for all 24 — the oracle's `tiet_khi_start_date` rescans the
 * whole year per term, which would be 24 × 365 samples for a year overview.
 */
export function tietKhiStartDatesOfYear(solarYear: number): Map<number, SolarDate> {
  const jdStart = jdFromDate(1, 1, solarYear)
  const jdEnd = jdFromDate(31, 12, solarYear)
  const found = new Map<number, SolarDate>()
  // Prime with 31/12 of the previous year, else 1 Jan always looks like a fresh start.
  let prev = tietKhiIndexForJdn(jdStart - 1)
  for (let jdn = jdStart; jdn <= jdEnd; jdn++) {
    const idx = tietKhiIndexForJdn(jdn)
    if (idx !== prev && !found.has(idx)) found.set(idx, jdToDate(jdn))
    prev = idx
  }
  return found
}

/** Solar date on which `term` (index 0–23, or a name from `TIET_KHI`) starts in `solarYear`. */
export function tietKhiStartDate(term: number | string, solarYear: number): SolarDate {
  let index: number
  if (typeof term === 'string') {
    index = (TIET_KHI as readonly string[]).indexOf(term)
    if (index < 0) throw new Error(`tiết khí không có trong danh sách: ${term}`)
  } else {
    index = term
  }
  if (!(index >= 0 && index <= 23)) throw new Error(`chỉ số tiết khí không hợp lệ: ${term}`)
  const hit = tietKhiStartDatesOfYear(solarYear).get(index)
  if (!hit) throw new Error(`tiết khí ${TIET_KHI[index]} không bắt đầu trong năm ${solarYear}`)
  return hit
}
