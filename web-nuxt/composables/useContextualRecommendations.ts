import { unref, type Ref } from 'vue'
import type { RecommendationCard, RecommendationResponse, RecommendationSource } from '~/types/api'

type MaybeRef<T> = T | Ref<T>

interface ContextualRecommendationOptions {
  context?: MaybeRef<string>
  entityId?: MaybeRef<string | undefined>
  query?: MaybeRef<string | undefined>
  limit?: MaybeRef<number | undefined>
  immediate?: boolean
}

function optionValue<T>(value: MaybeRef<T> | undefined, fallback: T): T {
  const resolved = value == null ? undefined : unref(value)
  return (resolved == null ? fallback : resolved) as T
}

function normalizeItems(list: unknown): RecommendationCard[] {
  if (!Array.isArray(list)) return []
  return list
    .filter((item): item is RecommendationCard => !!item && typeof item === 'object' && !!(item as RecommendationCard).id && !!(item as RecommendationCard).name)
    .map((item: RecommendationCard) => ({
      ...item,
      images: Array.isArray(item.images) ? item.images : item.image ? [item.image] : [],
    }))
}

function reasonMapFromItems(list: RecommendationCard[], explicit: Record<string, string[]> = {}) {
  const next: Record<string, string[]> = { ...explicit }
  for (const item of list) {
    const reason = item.reason_vi || item.reason
    if (item.id && reason && !next[item.id]?.length) next[item.id] = [reason]
  }
  return next
}

export function useContextualRecommendations(options: ContextualRecommendationOptions = {}) {
  const items = ref<RecommendationCard[]>([])
  const reasons = ref<Record<string, string[]>>({})
  const profile = ref<Record<string, unknown> | null>(null)
  const loading = ref(false)
  const error = ref(false)
  const source = ref<RecommendationSource>('fallback')
  const { isLoggedIn, authHeaders, fetchCsrf } = useAuth()

  let requestId = 0
  let refreshTimer: ReturnType<typeof setTimeout> | null = null

  async function loadFallback(limit: number, entityId?: string) {
    if (entityId) {
      const res = await apiFetch<RecommendationResponse>(`/api/entities/${encodePathId(entityId)}/similar?limit=${limit}`)
      items.value = normalizeItems(res.similar || res.items || res.entities)
    } else {
      const res = await apiFetch<RecommendationResponse>(`/api/entities/popular?limit=${limit}`)
      items.value = normalizeItems(res.entities || res.items)
    }
    reasons.value = reasonMapFromItems(items.value)
    profile.value = null
    source.value = 'fallback'
  }

  async function refresh() {
    if (import.meta.server) return
    const currentRequest = ++requestId
    const context = optionValue(options.context, 'home')
    const entityId = optionValue<string | undefined>(options.entityId, undefined)
    const query = optionValue<string | undefined>(options.query, undefined)
    const limit = Math.min(Math.max(optionValue(options.limit, 6) || 6, 1), 20)
    loading.value = true
    error.value = false

    try {
      if (isLoggedIn.value) {
        await fetchCsrf()
        const params = new URLSearchParams({ context, limit: String(limit) })
        if (entityId) params.set('entity_id', entityId)
        if (query?.trim()) params.set('q', query.trim())
        const res = await apiFetch<RecommendationResponse>(`/api/me/recommendations/contextual?${params}`, {
          headers: authHeaders(),
        })
        if (currentRequest !== requestId) return
        const personalized = normalizeItems(res.items || res.entities)
        if (personalized.length) {
          items.value = personalized
          reasons.value = reasonMapFromItems(personalized, res.reasons || {})
          profile.value = res.profile || null
          source.value = 'personalized'
          return
        }
      }
      await loadFallback(limit, entityId)
    } catch {
      if (currentRequest !== requestId) return
      error.value = true
      try {
        await loadFallback(limit, entityId)
      } catch {
        items.value = []
      }
    } finally {
      if (currentRequest === requestId) loading.value = false
    }
  }

  function queueRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => { void refresh() }, 120)
  }

  if (import.meta.client && options.immediate !== false) {
    onMounted(refresh)
    watch(
      () => [
        optionValue(options.context, 'home'),
        optionValue<string | undefined>(options.entityId, undefined),
        optionValue<string | undefined>(options.query, undefined),
        optionValue(options.limit, 6),
        isLoggedIn.value,
      ],
      queueRefresh,
    )
    onBeforeUnmount(() => {
      if (refreshTimer) clearTimeout(refreshTimer)
    })
  }

  return { items, reasons, profile, loading, error, source, refresh }
}
