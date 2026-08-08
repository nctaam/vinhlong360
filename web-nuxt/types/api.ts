import type { Entity, Post, User } from './index'
import type { ImageDescriptor } from './image'

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

export interface GalleryResponse {
  images: ImageDescriptor[]
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
export type RecommendationSourceTier = 'official' | 'verified' | 'community' | 'unknown'
export type RecommendationFreshnessStatus = 'fresh' | 'aging' | 'stale' | 'unknown'
export type RecommendationAgeBand = 'under_18' | '18_24' | '25_34' | '35_49' | '50_plus' | 'unknown'

export interface RecommendationExplanation {
  primary_reason: string
  reasons: string[]
  region_label?: string
  explicit_interests?: string[]
  derived_age_band?: RecommendationAgeBand
}

export interface RecommendationCard extends Entity {
  score?: number
  reason?: string
  reason_vi?: string
  place?: string
  explanation?: RecommendationExplanation
  source_tier?: RecommendationSourceTier
  freshness_status?: RecommendationFreshnessStatus
}

export interface RecommendationResponse {
  items?: RecommendationCard[]
  entities?: RecommendationCard[]
  similar?: RecommendationCard[]
  reasons?: Record<string, string[]>
  profile?: Record<string, unknown>
  explanation?: RecommendationExplanation
  source_tier?: RecommendationSourceTier
  freshness_status?: RecommendationFreshnessStatus
}
