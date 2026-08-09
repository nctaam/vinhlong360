import type { Entity } from '~/types'
import type { UnifiedSearchPayload } from '~/types/api'
import type { FilterSet, SearchViewState } from '~/types/publicExperience'
import { usePublicApi } from '~/composables/usePublicApi'

export type ZeroResultRecoveryId = 'remove-filter' | 'widen-area' | 'correct-query' | 'intent-all' | 'recent-saved'
export interface ZeroResultRecoveryAction {
  id: ZeroResultRecoveryId
  label: string
  patch?: Partial<SearchViewState>
  to?: string
}

const FILTER_REMOVAL_ORDER = ['sort', 'distance', 'price', 'season', 'month', 'type', 'category']

function filterWithoutLeastImportant(filters: FilterSet) {
  const keys = Object.keys(filters)
  if (!keys.length) return null
  const key = FILTER_REMOVAL_ORDER.find(candidate => keys.includes(candidate)) || [...keys].sort().at(-1)!
  const next = { ...filters }
  delete next[key]
  return next
}

export function buildZeroResultRecoveryActions(
  active: SearchViewState,
  options: { suggestedQuery?: string; hasRecentOrSaved?: boolean } = {},
): ZeroResultRecoveryAction[] {
  const actions: ZeroResultRecoveryAction[] = []
  const reducedFilters = filterWithoutLeastImportant(active.filters)
  if (reducedFilters) actions.push({ id: 'remove-filter', label: 'Bỏ bộ lọc ít quan trọng nhất', patch: { filters: reducedFilters } })
  if (active.area?.id) actions.push({ id: 'widen-area', label: 'Mở rộng khu vực tìm kiếm', patch: { area: undefined } })
  const suggestedQuery = String(options.suggestedQuery || '').trim()
  if (suggestedQuery && suggestedQuery !== active.query.trim()) {
    actions.push({ id: 'correct-query', label: `Thử “${suggestedQuery}”`, patch: { query: suggestedQuery } })
  }
  if (active.intent !== 'all') actions.push({ id: 'intent-all', label: 'Tìm trong tất cả nội dung', patch: { intent: 'all' } })
  actions.push({
    id: 'recent-saved',
    label: options.hasRecentOrSaved === false ? 'Khám phá nội dung đã lưu' : 'Xem mục gần đây và đã lưu',
    to: '/da-luu',
  })
  return actions
}

function normalizedEntities(payload: UnifiedSearchPayload | null | undefined): Entity[] {
  const list = payload?.entities || payload?.results || []
  return Array.isArray(list) ? list : []
}

export function useUnifiedSearch() {
  const publicApi = usePublicApi()

  async function searchAll(term: string, limit = 20, opts: Record<string, unknown> = {}) {
    return publicApi.search({ q: term, limit }, opts)
  }

  async function fetchEntitySuggestions(term: string, limit = 5, opts: Record<string, unknown> = {}) {
    if (!term.trim() || term.trim().length < 2) return []
    const payload = await searchAll(term.trim(), limit, opts)
    return normalizedEntities(payload).slice(0, limit)
  }

  return {
    searchAll,
    fetchEntitySuggestions,
    normalizedEntities,
    zeroResultRecoveryActions: buildZeroResultRecoveryActions,
  }
}
