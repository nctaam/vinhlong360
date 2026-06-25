interface RecentItem {
  id: string
  name: string
  type: string
  image?: string
  viewedAt: number
}

const STORAGE_KEY = 'vl360_recent'
const MAX_ITEMS = 12

const items = ref<RecentItem[]>([])
let loaded = false

function load() {
  if (loaded || !import.meta.client) return
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) items.value = JSON.parse(raw)
  } catch { /* corrupt data */ }
  loaded = true
}

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items.value)) } catch {}
}

export function useRecentlyViewed() {
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
