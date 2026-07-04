import type { Entity } from '~/types'
import type { UnifiedSearchPayload } from '~/types/api'
import { usePublicApi } from '~/composables/usePublicApi'

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

  return { searchAll, fetchEntitySuggestions, normalizedEntities }
}
