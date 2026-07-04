import type { Entity } from '~/types'

type UserEventType =
  | 'entity_view'
  | 'search'
  | 'save_add'
  | 'save_remove'
  | 'visit_mark'
  | 'community_view'
  | 'post_view'
  | 'map_focus'
  | 'itinerary_view'

interface UserEventPayload {
  context?: string
  entity_id?: string
  entity_type?: string
  entity_name?: string
  area?: string
  query?: string
  metadata?: Record<string, unknown>
}

interface TrackOptions {
  dedupeMs?: number
}

const DEFAULT_DEDUPE_MS = 45_000

function eventKey(eventType: UserEventType, payload: UserEventPayload) {
  return [
    eventType,
    payload.context || '',
    payload.entity_id || '',
    (payload.query || '').trim().toLocaleLowerCase('vi-VN'),
  ].join('|')
}

function entityPayload(entity: Pick<Entity, 'id' | 'type' | 'name' | 'area' | 'place_area'>, context: string): UserEventPayload {
  return {
    context,
    entity_id: entity.id,
    entity_type: entity.type,
    entity_name: entity.name,
    area: entity.place_area || entity.area,
  }
}

export function useUserEvents() {
  const { isLoggedIn, authHeaders, fetchCsrf } = useAuth()
  const lastSent = useState<Record<string, number>>('user-event-dedupe', () => ({}))

  async function send(eventType: UserEventType, payload: UserEventPayload) {
    await fetchCsrf()
    await $fetch('/api/me/events', {
      method: 'POST',
      headers: authHeaders(),
      body: {
        event_type: eventType,
        context: payload.context,
        entity_id: payload.entity_id,
        entity_type: payload.entity_type,
        entity_name: payload.entity_name,
        area: payload.area,
        query: payload.query,
        metadata: payload.metadata || {},
      },
    })
  }

  function trackEvent(eventType: UserEventType, payload: UserEventPayload = {}, options: TrackOptions = {}) {
    if (import.meta.server || !isLoggedIn.value) return
    const now = Date.now()
    const key = eventKey(eventType, payload)
    const dedupeMs = options.dedupeMs ?? DEFAULT_DEDUPE_MS
    if (lastSent.value[key] && now - lastSent.value[key]! < dedupeMs) return
    lastSent.value[key] = now
    void send(eventType, payload).catch(() => {
      // Analytics must never interrupt the user flow.
    })
  }

  function trackEntityView(entity: Pick<Entity, 'id' | 'type' | 'name' | 'area' | 'place_area'>, context = 'entity') {
    if (!entity?.id) return
    trackEvent('entity_view', entityPayload(entity, context), { dedupeMs: 60_000 })
  }

  function trackSearch(query: string, payload: Omit<UserEventPayload, 'query'> = {}) {
    const q = query.trim()
    if (q.length < 2) return
    trackEvent('search', { ...payload, context: payload.context || 'search', query: q }, { dedupeMs: 60_000 })
  }

  function trackSave(entity: Pick<Entity, 'id' | 'type' | 'name' | 'area' | 'place_area'>, saved: boolean, context = 'saved') {
    if (!entity?.id) return
    trackEvent(saved ? 'save_add' : 'save_remove', entityPayload(entity, context), { dedupeMs: 5_000 })
  }

  return { trackEvent, trackEntityView, trackSearch, trackSave }
}
