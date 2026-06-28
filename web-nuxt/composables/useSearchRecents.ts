const RECENT_KEY = 'vl360_recent_searches'
const MAX_RECENTS = 5
const RECENT_TTL = 14 * 24 * 60 * 60 * 1000

export function useSearchRecents() {
  const recentSearches = ref<string[]>([])

  function loadRecents() {
    try {
      const raw = localStorage.getItem(RECENT_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return
      const now = Date.now()
      if (typeof parsed[0] === 'string') {
        recentSearches.value = parsed.filter((s: unknown) => typeof s === 'string')
        return
      }
      const valid = parsed.filter((r: any) => r?.t && now - r.t < RECENT_TTL)
      recentSearches.value = valid.map((r: any) => r.q as string)
      if (valid.length < parsed.length) {
        try { localStorage.setItem(RECENT_KEY, JSON.stringify(valid)) } catch {}
      }
    } catch { recentSearches.value = [] }
  }

  function saveRecent(term: string) {
    const clean = term.trim()
    if (!clean || clean.length < 2) return
    try {
      const raw = localStorage.getItem(RECENT_KEY)
      let entries: { q: string; t: number }[] = []
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) {
          entries = typeof parsed[0] === 'string'
            ? parsed.map((q: string) => ({ q, t: Date.now() }))
            : parsed.filter((r: any) => r?.q !== clean)
        }
      }
      entries.unshift({ q: clean, t: Date.now() })
      entries = entries.slice(0, MAX_RECENTS)
      localStorage.setItem(RECENT_KEY, JSON.stringify(entries))
      recentSearches.value = entries.map(e => e.q)
    } catch {}
  }

  function removeRecent(idx: number) {
    recentSearches.value.splice(idx, 1)
    try {
      const entries = recentSearches.value.map(q => ({ q, t: Date.now() }))
      localStorage.setItem(RECENT_KEY, JSON.stringify(entries))
    } catch {}
  }

  function clearRecents() {
    recentSearches.value = []
    try { localStorage.removeItem(RECENT_KEY) } catch {}
  }

  return { recentSearches, loadRecents, saveRecent, removeRecent, clearRecents }
}
