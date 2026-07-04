import type { Entity, Post, User } from './index'

export interface ApiListResponse<T> {
  total: number
  limit?: number
  offset?: number
  entities?: T[]
  results?: T[]
}

export interface EntityListQuery {
  q?: string
  type?: string
  area?: string
  month?: number
  sort?: 'rating' | 'newest' | 'name'
  fields?: 'minimal' | 'full'
  limit?: number
  offset?: number
}

export type EntityListResponse = ApiListResponse<Entity> & {
  entities: Entity[]
}

export type SearchSuggestionKind = 'entity' | 'post' | 'user'

export interface SearchSuggestion {
  kind: SearchSuggestionKind
  id: string
  label: string
  type?: string
  to?: string
}

export interface UnifiedSearchTotals {
  entities?: number
  posts?: number
  users?: number
}

export interface UnifiedSearchPayload {
  q?: string
  total?: number
  results?: Entity[]
  entities?: Entity[]
  posts?: Post[]
  users?: User[]
  suggestions?: SearchSuggestion[]
  totals?: UnifiedSearchTotals
  filters?: {
    q?: string
    type?: string | null
    area?: string | null
    limit?: number
    [key: string]: unknown
  }
}

export interface PublicSearchQuery {
  q: string
  type?: string
  area?: string
  limit?: number
}

export type RecommendationSource = 'personalized' | 'fallback'

export interface RecommendationCard extends Entity {
  score?: number
  reason?: string
  reason_vi?: string
  place?: string
}

export interface RecommendationResponse {
  items?: RecommendationCard[]
  entities?: RecommendationCard[]
  similar?: RecommendationCard[]
  reasons?: Record<string, string[]>
  profile?: Record<string, unknown>
}
