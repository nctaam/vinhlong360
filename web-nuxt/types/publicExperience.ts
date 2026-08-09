export type SurfaceKind = 'loading' | 'ready' | 'partial' | 'stale' | 'empty' | 'error' | 'offline'

export interface FreshnessMeta { updatedAt?: string; source?: string; ttlSeconds?: number }
export interface RecoveryAction { id: string; label: string }
export interface RetryAction { label?: string; attempts?: number; nextRetryAt?: string }

export type SurfaceState<T> =
  | { kind: 'loading' }
  | { kind: 'ready'; data: T; freshness?: FreshnessMeta }
  | { kind: 'partial'; data: T; failedPanels: string[] }
  | { kind: 'stale'; data: T; updatedAt: string }
  | { kind: 'empty'; recovery: RecoveryAction }
  | { kind: 'error'; retry: RetryAction; fallback?: T }
  | { kind: 'offline'; cached?: T; cachedAt?: string }

export interface AreaRef { id: string; name?: string; scope?: string }
export type Intent = 'place' | 'service' | 'event' | 'story' | 'all'
export interface IntentState { value: Intent; source?: string }
export interface MapViewport { center: [number, number]; zoom: number }
export type FilterSet = Record<string, string | number | boolean | string[]>
export interface SearchViewState {
  query: string
  intent: Intent
  filters: FilterSet
  area?: AreaRef
  viewport?: MapViewport
  selectedId?: string
  panel: 'list' | 'map'
}
export interface ContextEnvelope {
  version: number
  source: string
  ttlSeconds: number
  area?: AreaRef
  location: { mode: 'exact' | 'approximate' | 'selected' | 'unavailable'; confidence: 'high' | 'medium' | 'low' }
  intent?: IntentState
  time: { localDate: string; localTime: string; season?: string }
  freshness: { updatedAt?: string; source?: string }
  accessibility: { reducedMotion: boolean; highContrast: boolean; textScale: number }
  network: 'online' | 'degraded' | 'offline'
  explainableSignals: string[]
}
