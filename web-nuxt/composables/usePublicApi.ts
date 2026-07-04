import type { Entity } from '~/types'
import type { EntityListQuery, EntityListResponse, PublicSearchQuery, UnifiedSearchPayload } from '~/types/api'

function cleanQueryValue(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null
  const text = String(value).trim()
  return text ? text : null
}

function toQueryString(query: object): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query as Record<string, unknown>)) {
    const text = cleanQueryValue(value)
    if (text !== null) params.set(key, text)
  }
  return params.toString()
}

export function usePublicApi() {
  function listEntities(query: EntityListQuery = {}, opts: Record<string, unknown> = {}) {
    const qs = toQueryString(query)
    return apiFetch<EntityListResponse>(`/api/entities${qs ? `?${qs}` : ''}`, opts)
  }

  function getEntity(id: string, opts: Record<string, unknown> = {}) {
    return apiFetch<Entity>(`/api/entities/${encodePathId(id)}`, opts)
  }

  function search(query: PublicSearchQuery, opts: Record<string, unknown> = {}) {
    const qs = toQueryString({ ...query, limit: query.limit ?? 20 })
    return apiFetch<UnifiedSearchPayload>(`/api/search?${qs}`, opts)
  }

  return { listEntities, getEntity, search }
}
