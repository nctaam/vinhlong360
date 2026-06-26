import { FLOOD_MONTHS } from './useConstants'

export interface Season {
  months?: number[]
  peak?: number[]
}

export function isYearRound(season?: Season | null): boolean {
  return !!season?.months && season.months.length >= 11
}

export function monthRanges(months: number[]): string {
  const sorted = [...new Set(months)].sort((a, b) => a - b)
  if (!sorted.length) return ''
  const ranges: string[] = []
  let start = sorted[0]!, prev = sorted[0]!
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === prev + 1) {
      prev = sorted[i]!
    } else {
      ranges.push(start === prev ? `T${start}` : `T${start}–${prev}`)
      start = sorted[i]!
      prev = sorted[i]!
    }
  }
  ranges.push(start === prev ? `T${start}` : `T${start}–${prev}`)
  return ranges.join(', ')
}

export function seasonText(season?: Season | null): string {
  if (!season?.months) return 'Quanh năm'
  if (isYearRound(season)) return 'Quanh năm'
  return monthRanges(season.months)
}

function expandSeason(sel: string | null): number[] | null {
  if (!sel || sel === 'all') return null
  if (sel === 'flood') return FLOOD_MONTHS
  const month = parseInt(sel, 10)
  if (Number.isNaN(month) || month < 1 || month > 12) return null
  return [month]
}

export function inSeason(entity: { season?: Season | null }, sel: string | null): boolean {
  const m = expandSeason(sel)
  if (!m) return true
  if (!entity.season?.months) return true
  return entity.season.months.some(x => m.includes(x))
}

export function relevanceScore(entity: { season?: Season | null; confidence?: number }, sel: string | null): number {
  const m = expandSeason(sel)
  if (!m) return entity.confidence || 0
  if (!entity.season?.months) return 1
  if (!entity.season.months.some(x => m.includes(x))) return -1
  if (isYearRound(entity.season)) return 2
  return (entity.season.peak || []).some(x => m.includes(x)) ? 4 : 3
}

export function useSeason() {
  return { isYearRound, monthRanges, seasonText, inSeason, relevanceScore }
}
