import type { ImageDescriptor } from '~/types/image'
import { isKnownEntityType, normalizeSavedImageSnapshot } from '~/utils/savedImageDescriptors'

export interface RecentItem {
  id: string
  name: string
  type: string
  image_descriptor: ImageDescriptor
  descriptor_revision: 'ai-disclosure-v1'
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

export function readRecentStorage(storage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>): RecentItem[] {
  const raw = storage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      storage.removeItem(STORAGE_KEY)
      return []
    }
    const normalized = parsed.filter(isValidItem).map(item => normalizeSavedImageSnapshot(item) as RecentItem)
    // Rewrite legacy URL snapshots while preserving their original order and timestamps.
    storage.setItem(STORAGE_KEY, JSON.stringify(normalized))
    return normalized
  } catch {
    storage.removeItem(STORAGE_KEY)
    return []
  }
}

export function createRecentItem(entity: Record<string, any>, viewedAt = Date.now()): RecentItem {
  return normalizeSavedImageSnapshot({
    id: entity.id,
    name: entity.name,
    type: entity.type,
    kind: entity.kind || (entity.type === 'itinerary' ? 'itinerary' : isKnownEntityType(entity.type) ? 'entity' : 'unknown'),
    images: entity.images,
    image: entity.image,
    ...(Object.prototype.hasOwnProperty.call(entity, 'image_descriptor') ? { image_descriptor: entity.image_descriptor } : {}),
    ...(Object.prototype.hasOwnProperty.call(entity, 'image_descriptors') ? { image_descriptors: entity.image_descriptors } : {}),
    viewedAt,
  }) as RecentItem
}

export function useRecentlyViewed() {
  const items = useState<RecentItem[]>('recentlyViewed', () => [])

  function load() {
    if (loaded || !import.meta.client) return
    items.value = readRecentStorage(localStorage)
    loaded = true
  }

  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items.value)) } catch {}
  }

  load()

  function track(entity: Record<string, any>) {
    if (!import.meta.client) return
    load()
    const existing = items.value.findIndex(i => i.id === entity.id)
    if (existing >= 0) items.value.splice(existing, 1)
    items.value.unshift(createRecentItem(entity))
    if (items.value.length > MAX_ITEMS) items.value.length = MAX_ITEMS
    save()
  }

  return { recentItems: items, track }
}
