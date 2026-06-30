interface FavoriteItem {
  id: string
  name: string
  type: string
  place_name?: string
  place_area?: string
  summary?: string
  image?: string
  savedAt: string
}

const STORAGE_KEY = 'vl360_favorites'
let loaded = false
let syncSetup = false

function isValidFavorite(v: unknown): v is FavoriteItem {
  if (!v || typeof v !== 'object') return false
  const o = v as Record<string, unknown>
  return typeof o.id === 'string' && typeof o.name === 'string' && typeof o.type === 'string'
}

export function useFavorites() {
  const favorites = useState<FavoriteItem[]>('favorites', () => [])
  const { isLoggedIn, authHeaders } = useAuth()

  function load() {
    if (loaded || import.meta.server) return
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) favorites.value = parsed.filter(isValidFavorite)
        else localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
    loaded = true
  }

  function persist() {
    if (import.meta.server) return
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites.value)) } catch {}
  }

  if (import.meta.client) onNuxtReady(load)

  // ── Account sync (P1) ──────────────────────────────────────────────
  // localStorage is the offline cache + UI source of truth; the server is the
  // cross-device store. On login we merge local→account (union, nothing lost)
  // and adopt the merged list; toggles write through fire-and-forget.
  async function mergeToServer() {
    if (!isLoggedIn.value || import.meta.server) return
    try {
      const hasLocalItems = favorites.value.length > 0
      const res = hasLocalItems
        ? await $fetch<{ items?: FavoriteItem[] }>('/api/saved/merge', {
            method: 'POST', headers: authHeaders(), body: { items: favorites.value },
          })
        : await $fetch<{ items?: FavoriteItem[] }>('/api/saved', { headers: authHeaders() })
      if (Array.isArray(res?.items)) { favorites.value = res.items; persist() }
    } catch { /* offline / not available — keep local */ }
  }
  async function pushAdd(item: FavoriteItem) {
    if (!isLoggedIn.value || import.meta.server) return
    try { await $fetch('/api/saved', { method: 'POST', headers: authHeaders(), body: item }) } catch { /* keep local */ }
  }
  async function pushRemove(id: string) {
    if (!isLoggedIn.value || import.meta.server) return
    try { await $fetch(`/api/saved/${encodeURIComponent(id)}`, { method: 'DELETE', headers: authHeaders() }) } catch { /* keep local */ }
  }

  if (!syncSetup && import.meta.client) {
    syncSetup = true
    if (isLoggedIn.value) mergeToServer()
    watch(isLoggedIn, (v, old) => { if (v && !old) mergeToServer() })
  }

  function isSaved(id: string) {
    return favorites.value.some(f => f.id === id)
  }

  function toggle(entity: Record<string, any>) {
    const idx = favorites.value.findIndex(f => f.id === entity.id)
    if (idx >= 0) {
      favorites.value.splice(idx, 1)
      persist()
      pushRemove(entity.id)
    } else {
      const item: FavoriteItem = {
        id: entity.id,
        name: entity.name,
        type: entity.type,
        place_name: entity.place_name,
        place_area: entity.place_area || entity.area,
        summary: entity.summary,
        image: Array.isArray(entity.images) ? entity.images[0] : undefined,
        savedAt: new Date().toISOString(),
      }
      favorites.value.unshift(item)
      persist()
      pushAdd(item)
    }
  }

  function remove(id: string) {
    const idx = favorites.value.findIndex(f => f.id === id)
    if (idx >= 0) {
      favorites.value.splice(idx, 1)
      persist()
      pushRemove(id)
    }
  }

  function clear() {
    const ids = favorites.value.map(f => f.id)
    favorites.value = []
    persist()
    if (isLoggedIn.value) ids.forEach(pushRemove)
  }

  const count = computed(() => favorites.value.length)

  const byType = computed(() => {
    const groups: Record<string, FavoriteItem[]> = {}
    for (const f of favorites.value) {
      const key = f.type
      if (!groups[key]) groups[key] = []
      groups[key]!.push(f)
    }
    return groups
  })

  return { favorites, isSaved, toggle, remove, clear, count, byType }
}
