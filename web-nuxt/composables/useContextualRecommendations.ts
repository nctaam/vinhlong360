import { unref, type Ref } from 'vue'
import { useAdaptivePriority, type AdaptiveIntent, type AdaptiveReasonCode } from './useAdaptivePriority'
import { useAttentionBudget } from './useAttentionBudget'
import { projectAdaptivePreferenceSignals, usePersonalizationPreferences } from './usePersonalizationPreferences'
import { projectRecommendationExplanation } from '~/utils/recommendationExplanation'
import type { RecommendationCard, RecommendationResponse, RecommendationSource } from '~/types/api'
import type { ContextEnvelope } from '~/types/publicExperience'
import { normalizeSavedImageSnapshot, type SavedImageSnapshot } from '~/utils/savedImageDescriptors'

type MaybeRef<T> = T | Ref<T>

interface ContextualRecommendationOptions {
  context?: MaybeRef<string>
  entityId?: MaybeRef<string | undefined>
  query?: MaybeRef<string | undefined>
  limit?: MaybeRef<number | undefined>
  intent?: MaybeRef<AdaptiveIntent | undefined>
  contextEnvelope?: MaybeRef<Pick<ContextEnvelope, 'network'> | undefined>
  adaptiveOrder?: MaybeRef<Record<string, number> | undefined>
  adaptiveReason?: MaybeRef<AdaptiveReasonCode | undefined>
  immediate?: boolean
}

function optionValue<T>(value: MaybeRef<T> | undefined, fallback: T): T {
  const resolved = value == null ? undefined : unref(value)
  return (resolved == null ? fallback : resolved) as T
}

export type NormalizedRecommendationCard = RecommendationCard & SavedImageSnapshot

export function normalizeRecommendationItems(list: unknown): NormalizedRecommendationCard[] {
  if (!Array.isArray(list)) return []
  return list
    .filter((item): item is RecommendationCard => !!item && typeof item === 'object' && !!(item as RecommendationCard).id && !!(item as RecommendationCard).name)
    .map((item: RecommendationCard) => normalizeSavedImageSnapshot({ ...item, kind: 'entity' }) as NormalizedRecommendationCard)
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
  const { user, isLoggedIn, authHeaders, fetchCsrf } = useAuth()
  const preferences = usePersonalizationPreferences()
  const suggestionBudget = useAttentionBudget({
    storageNamespace: 'vl360:recommendations-attention:v1',
    ownerScope: () => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest',
  })
  const itemAdaptiveReasonMap = computed<Record<string, AdaptiveReasonCode | undefined>>(() => Object.fromEntries(
    items.value.map(item => [item.id, recommendationAdaptiveReason(item)]),
  ))
  const itemAdaptiveReasons = computed(() => Object.values(itemAdaptiveReasonMap.value).filter((value): value is AdaptiveReasonCode => !!value))
  const adaptiveSignals = computed<AdaptiveReasonCode[]>(() => [...new Set([
    ...projectAdaptivePreferenceSignals(preferences.snapshot.value),
    ...itemAdaptiveReasons.value,
  ])])
  const priority = computed(() => resolveContextualRecommendationPriority({
    items: items.value,
    context: optionValue<Pick<ContextEnvelope, 'network'> | undefined>(options.contextEnvelope, undefined),
    intent: optionValue<AdaptiveIntent | undefined>(options.intent, {
      confidence: source.value === 'personalized' && adaptiveSignals.value.length ? 'medium' : 'low',
      defaultCta: 'view',
      reason: adaptiveSignals.value[0],
    }),
    adaptiveOrder: optionValue<Record<string, number> | undefined>(options.adaptiveOrder, recommendationAdaptiveOrder(items.value)),
    reason: optionValue<AdaptiveReasonCode | undefined>(options.adaptiveReason, adaptiveSignals.value[0]),
    reasons: itemAdaptiveReasonMap.value,
  }))

  let requestId = 0
  let refreshTimer: ReturnType<typeof setTimeout> | null = null

  async function loadFallback(limit: number, entityId?: string) {
    if (entityId) {
      const res = await apiFetch<RecommendationResponse>(`/api/entities/${encodePathId(entityId)}/similar?limit=${limit}`)
      items.value = normalizeRecommendationItems(res.similar || res.items || res.entities)
    } else {
      const res = await apiFetch<RecommendationResponse>(`/api/entities/popular?limit=${limit}`)
      items.value = normalizeRecommendationItems(res.entities || res.items)
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
        const personalized = normalizeRecommendationItems(res.items || res.entities)
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

  function canShowSuggestion(itemId: string) {
    const id = recommendationSuggestionId(itemId)
    return !!id && suggestionBudget.canSuggest(id)
  }

  function dismissSuggestion(itemId: string) {
    const id = recommendationSuggestionId(itemId)
    return !!id && suggestionBudget.dismiss(id)
  }

  function adaptiveReasonsFor(itemId: string) {
    const reason = itemAdaptiveReasonMap.value[itemId]
    return reason && priority.value.reasonCodes.includes(reason) ? [reason] : []
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

  return {
    items,
    reasons,
    profile,
    loading,
    error,
    source,
    adaptiveSignals,
    priority,
    adaptiveReasonsFor,
    attentionOwnerScope: suggestionBudget.ownerScope,
    attentionVersion: suggestionBudget.version,
    canShowSuggestion,
    dismissSuggestion,
    resetSuggestionSession: suggestionBudget.resetSession,
    refresh,
  }
}

export function recommendationSuggestionId(value: unknown) {
  if (typeof value !== 'string') return ''
  const id = value.trim().toLowerCase()
  return /^[a-z0-9][a-z0-9:_-]{0,43}$/.test(id) ? `recommendation:${id}` : ''
}

function recommendationAdaptiveReason(item: RecommendationCard): AdaptiveReasonCode | undefined {
  const projected = projectRecommendationExplanation(item.explanation || {
    primary_reason: item.reason_vi || item.reason,
    reasons: [item.reason_vi || item.reason].filter((value): value is string => !!value),
  })
  const text = projected.reasons.join(' ').toLocaleLowerCase('vi-VN')
  if (/khu vực|gần khu vực/.test(text)) return 'selected-area'
  if (/sở thích/.test(text)) return 'explicit-interest'
  if (/vừa xem|đã lưu|gần đây/.test(text)) return 'recent-item'
  if (/mùa|thời gian/.test(text)) return 'seasonal'
  if (/chính thức|cảnh báo/.test(text)) return 'official-notice'
  if (/mới cập nhật|nguồn mới/.test(text)) return 'fresh-source'
  return undefined
}

function recommendationAdaptiveOrder(items: RecommendationCard[]) {
  return Object.fromEntries(items.map((item, index) => [item.id, recommendationAdaptiveReason(item) ? index - items.length : index]))
}

export function resolveContextualRecommendationPriority<T extends { id: string }>(input: {
  items: T[]
  context?: Pick<ContextEnvelope, 'network'>
  intent?: AdaptiveIntent
  adaptiveOrder?: Record<string, number>
  reason?: AdaptiveReasonCode
  reasons?: Record<string, AdaptiveReasonCode | undefined>
}) {
  return useAdaptivePriority().resolve({
    context: input.context,
    intent: input.intent,
    candidates: input.items.map((item, index) => ({
      ...item,
      kind: 'metadata' as const,
      defaultOrder: index,
      adaptiveRank: input.adaptiveOrder?.[item.id] ?? index,
      reason: input.reasons?.[item.id] ?? input.reason,
    })),
  })
}
