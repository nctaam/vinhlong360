const DIACRITICS_RE = /[\u0300-\u036f]/g
const FOLD_CACHE = new Map<string, string>()
const MAX_FOLD_CACHE = 512

export interface WeightedSearchField {
  text: string
  weight: number
}

/**
 * Normalize Vietnamese text by removing diacritics, converting đ/Đ → d,
 * lowercasing, and collapsing whitespace. Memoized with a bounded LRU cache.
 */
export function foldVietnamese(text: string): string {
  if (!text) return ''
  const cached = FOLD_CACHE.get(text)
  if (cached !== undefined) {
    FOLD_CACHE.delete(text)
    FOLD_CACHE.set(text, cached)
    return cached
  }
  const folded = text
    .normalize('NFD')
    .replace(DIACRITICS_RE, '')
    .replace(/[đĐ]/g, 'd')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
  if (FOLD_CACHE.size >= MAX_FOLD_CACHE) {
    const oldest = FOLD_CACHE.keys().next().value
    if (oldest !== undefined) FOLD_CACHE.delete(oldest)
  }
  FOLD_CACHE.set(text, folded)
  return folded
}

/**
 * Optimal String Alignment (Restricted Damerau-Levenshtein) edit distance.
 * Adjacent transpositions count as 1 edit; aborts early when min row > maxDist.
 */
export function damerauLevenshtein(a: string, b: string, maxDist = 2): number {
  if (a === b) return 0
  if (a.length > b.length) [a, b] = [b, a]
  const m = a.length
  const n = b.length
  if (n - m > maxDist) return maxDist + 1
  if (m === 0) return n

  let prevPrev: number[] | null = null
  let prev = Array.from({ length: m + 1 }, (_, i) => i)
  for (let j = 1; j <= n; j++) {
    const curr = new Array<number>(m + 1)
    curr[0] = j
    let rowMin = j
    const bj = b[j - 1]!
    for (let i = 1; i <= m; i++) {
      const ai = a[i - 1]!
      const cost = ai === bj ? 0 : 1
      let d = Math.min(curr[i - 1]! + 1, prev[i]! + 1, prev[i - 1]! + cost)
      if (prevPrev && i > 1 && j > 1 && ai === b[j - 2] && a[i - 2] === bj) {
        d = Math.min(d, prevPrev[i - 2]! + 1)
      }
      curr[i] = d
      if (d < rowMin) rowMin = d
    }
    if (rowMin > maxDist) return maxDist + 1
    prevPrev = prev
    prev = curr
  }
  return prev[m]!
}

function tokenFieldScore(qTok: string, fieldFold: string, fieldTokens: string[]): number {
  if (fieldTokens.includes(qTok)) return 24
  if (fieldTokens.some(ft => ft.startsWith(qTok))) return 18
  if (fieldFold.includes(qTok)) return 12
  if (qTok.length >= 4) {
    for (const ft of fieldTokens) {
      if (Math.abs(ft.length - qTok.length) <= 1 && damerauLevenshtein(qTok, ft, 1) <= 1) {
        return 9
      }
    }
  }
  return 0
}

/**
 * Score weighted fields against a Vietnamese query using diacritic folding,
 * prefix/word boosts, and distance-1 Damerau-Levenshtein typo tolerance.
 * Returns 0 when any query token fails to match across all fields.
 */
export function scoreVietnameseQuery(
  query: string,
  fields: ReadonlyArray<WeightedSearchField>,
): number {
  const qFold = foldVietnamese(query)
  if (!qFold) return 1
  const qTokens = qFold.split(' ').filter(Boolean)
  if (!qTokens.length) return 1

  const prepared = fields
    .map(f => {
      const fold = foldVietnamese(f.text)
      return {
        fold,
        tokens: fold ? fold.split(' ').filter(Boolean) : [],
        weight: f.weight,
      }
    })
    .filter(f => f.fold.length > 0 && f.weight > 0)

  if (!prepared.length) return 0

  let totalScore = 0
  for (const field of prepared) {
    if (field.fold === qFold) totalScore += 140 * field.weight
    else if (field.fold.startsWith(qFold)) totalScore += 100 * field.weight
    else if (field.fold.includes(qFold)) totalScore += 65 * field.weight
  }

  for (const qTok of qTokens) {
    let bestTokenScore = 0
    for (const field of prepared) {
      const s = tokenFieldScore(qTok, field.fold, field.tokens)
      if (s > 0) {
        totalScore += s * field.weight
        if (s > bestTokenScore) bestTokenScore = s
      }
    }
    if (bestTokenScore === 0) return 0
  }
  return totalScore
}
