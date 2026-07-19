import type { ImageDescriptor } from '~/types/image'
import { isKnownEntityType, normalizeSavedImageSnapshot } from '~/utils/savedImageDescriptors'

export interface FavoriteItem {
  id: string
  name: string
  type: string
  kind?: 'entity' | 'post' | 'itinerary' | 'unknown'
  place_name?: string
  place_area?: string
  summary?: string
  image_descriptor: ImageDescriptor
  descriptor_revision: 'ai-disclosure-v1'
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

export function readFavoriteStorage(storage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>): FavoriteItem[] {
  const raw = storage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      storage.removeItem(STORAGE_KEY)
      return []
    }
    const normalized = parsed.filter(isValidFavorite).map(normalizeFavoriteItem)
    // Rewrite legacy URL snapshots immediately so later syncs cannot reintroduce raw media.
    storage.setItem(STORAGE_KEY, JSON.stringify(normalized))
    return normalized
  } catch {
    storage.removeItem(STORAGE_KEY)
    return []
  }
}

export async function runFavoriteBootstrap(
  load: () => void | Promise<void>,
  isLoggedIn: () => boolean,
  merge: () => void | Promise<void>,
): Promise<void> {
  await load()
  if (isLoggedIn()) await merge()
}

export function createFavoriteItem(entity: Record<string, any>, savedAt = new Date().toISOString()): FavoriteItem {
  return normalizeSavedImageSnapshot({
    id: entity.id,
    name: entity.name,
    type: entity.type,
    kind: entity.kind || (entity.type === 'itinerary' ? 'itinerary' : isKnownEntityType(entity.type) ? 'entity' : 'unknown'),
    place_name: entity.place_name,
    place_area: entity.place_area || entity.area,
    summary: entity.summary,
    images: entity.images,
    image: entity.image,
    ...(Object.prototype.hasOwnProperty.call(entity, 'image_descriptor') ? { image_descriptor: entity.image_descriptor } : {}),
    ...(Object.prototype.hasOwnProperty.call(entity, 'image_descriptors') ? { image_descriptors: entity.image_descriptors } : {}),
    savedAt,
  }) as FavoriteItem
}

function normalizeFavoriteItem(item: FavoriteItem): FavoriteItem {
  return normalizeSavedImageSnapshot(item) as FavoriteItem
}

export function useFavorites() {
  const favorites = useState<FavoriteItem[]>('favorites', () => [])
  const { isLoggedIn, authHeaders } = useAuth()
  const { trackSave } = useUserEvents()

  function load() {
    if (loaded || import.meta.server) return
    favorites.value = readFavoriteStorage(localStorage)
    loaded = true
  }

  function persist() {
    if (import.meta.server) return
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites.value)) } catch {}
  }

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
      if (Array.isArray(res?.items)) { favorites.value = res.items.filter(isValidFavorite).map(normalizeFavoriteItem); persist() }
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

  function bootstrapSync() {
    return runFavoriteBootstrap(load, () => isLoggedIn.value, mergeToServer)
  }

  if (!syncSetup && import.meta.client) {
    syncSetup = true
    onNuxtReady(() => { void bootstrapSync() })
    watch(isLoggedIn, (v, old) => { if (v && !old) void bootstrapSync() })
  }

  function isSaved(id: string) {
    return favorites.value.some(f => f.id === id)
  }

  function toggle(entity: Record<string, any>) {
    const idx = favorites.value.findIndex(f => f.id === entity.id)
    if (idx >= 0) {
      const removed = favorites.value[idx]
      favorites.value.splice(idx, 1)
      persist()
      pushRemove(entity.id)
      if (removed) trackSave(removed, false)
    } else {
      const item = createFavoriteItem(entity)
      favorites.value.unshift(item)
      persist()
      pushAdd(item)
      trackSave(item, true)
    }
  }

  function remove(id: string) {
    const idx = favorites.value.findIndex(f => f.id === id)
    if (idx >= 0) {
      const removed = favorites.value[idx]
      favorites.value.splice(idx, 1)
      persist()
      pushRemove(id)
      if (removed) trackSave(removed, false)
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
