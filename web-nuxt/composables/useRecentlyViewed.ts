interface RecentItem {
  id: string
  name: string
  type: string
  image?: string
  viewedAt: number
}

const STORAGE_KEY = 'vl360_recent'
const MAX_ITEMS = 12

let loaded = false

function isValidItem(v: unknown): v is RecentItem {
  if (!v || typeof v !== 'object') return false
  const o = v as Record<string, unknown>
  return typeof o.id === 'string' && typeof o.name === 'string' && typeof o.type === 'string'
}

export function useRecentlyViewed() {
  const items = useState<RecentItem[]>('recentlyViewed', () => [])

  function load() {
    if (loaded || !import.meta.client) return
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) items.value = parsed.filter(isValidItem)
      }
    } catch { /* corrupt data */ }
    loaded = true
  }

  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items.value)) } catch {}
  }

  load()

  function track(entity: { id: string; name: string; type: string; images?: string[] }) {
    if (!import.meta.client) return
    load()
    const existing = items.value.findIndex(i => i.id === entity.id)
    if (existing >= 0) items.value.splice(existing, 1)
    items.value.unshift({
      id: entity.id,
      name: entity.name,
      type: entity.type,
      image: entity.images?.[0],
      viewedAt: Date.now(),
    })
    if (items.value.length > MAX_ITEMS) items.value.length = MAX_ITEMS
    save()
  }

  return { recentItems: items, track }
}
