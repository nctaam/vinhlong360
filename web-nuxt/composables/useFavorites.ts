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

export function useFavorites() {
  const favorites = useState<FavoriteItem[]>('favorites', () => [])

  function load() {
    if (loaded || import.meta.server) return
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) favorites.value = parsed
        else localStorage.removeItem(STORAGE_KEY)
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
    loaded = true
  }

  function persist() {
    if (import.meta.server) return
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites.value))
  }

  load()

  function isSaved(id: string) {
    return favorites.value.some(f => f.id === id)
  }

  function toggle(entity: Record<string, any>) {
    const idx = favorites.value.findIndex(f => f.id === entity.id)
    if (idx >= 0) {
      favorites.value.splice(idx, 1)
    } else {
      favorites.value.unshift({
        id: entity.id,
        name: entity.name,
        type: entity.type,
        place_name: entity.place_name,
        place_area: entity.place_area || entity.area,
        summary: entity.summary,
        image: Array.isArray(entity.images) ? entity.images[0] : undefined,
        savedAt: new Date().toISOString(),
      })
    }
    persist()
  }

  function remove(id: string) {
    const idx = favorites.value.findIndex(f => f.id === id)
    if (idx >= 0) {
      favorites.value.splice(idx, 1)
      persist()
    }
  }

  function clear() {
    favorites.value = []
    persist()
  }

  const count = computed(() => favorites.value.length)

  const byType = computed(() => {
    const groups: Record<string, FavoriteItem[]> = {}
    for (const f of favorites.value) {
      if (!groups[f.type]) groups[f.type] = []
      groups[f.type].push(f)
    }
    return groups
  })

  return { favorites, isSaved, toggle, remove, clear, count, byType }
}
