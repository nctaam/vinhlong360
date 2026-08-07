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

function jdFromDate(dd: number, mm: number, yy: number): number {
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
