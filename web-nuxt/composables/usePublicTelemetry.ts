import type { ContextEnvelope } from '~/types/publicExperience'

export type PublicTelemetryKind = 'outcome' | 'harm' | 'performance'
export type PublicRouteFamily = 'home' | 'catalog' | 'search' | 'detail' | 'planner' | 'community' | 'settings' | 'other'
export type PublicViewport = 'mobile' | 'tablet' | 'desktop'
export type PublicTheme = 'nocturne' | 'parchment'
export type PublicTelemetryEventName = 'search-submitted' | 'search-result-opened' | 'search-recovered' | 'detail-recovery-shown' | 'planner-completed' | 'first-useful-result'
export type PublicOutcomeClass = 'result-shown' | 'detail-opened' | 'task-completed' | 'task-recovered'
export type PublicHarmClass = 'false-not-found-risk' | 'stale-data-risk' | 'blocked-core-task' | 'privacy-boundary-rejected'
export type PublicAreaId = 'vinh-long' | 'ben-tre' | 'tra-vinh' | 'tri-region' | 'unknown'
export type PublicPerformanceMetric = 'lcp' | 'cls' | 'inp' | 'ttfb' | 'ttfur' | 'time-to-primary-action' | 'js-bytes' | 'css-bytes' | 'ssr-bytes' | 'api-p95' | 'map-tile-cost' | 'media-decode-cost'

export interface PublicTelemetryContext {
  eventName: PublicTelemetryEventName
  routeFamily: PublicRouteFamily
  viewport: PublicViewport
  network: ContextEnvelope['network']
  theme: PublicTheme
  areaId?: PublicAreaId
}

export interface PublicOutcomeInput extends PublicTelemetryContext { outcomeClass: PublicOutcomeClass }
export interface PublicHarmInput extends PublicTelemetryContext { harmClass: PublicHarmClass }
export interface PublicPerformanceInput extends PublicTelemetryContext {
  metric: PublicPerformanceMetric
  value: number
  budget: number
}

export type PublicTelemetryEvent = Partial<PublicTelemetryContext> & {
  kind?: PublicTelemetryKind
  outcomeClass?: PublicOutcomeClass
  harmClass?: PublicHarmClass
  metric?: PublicPerformanceMetric
  value?: number
  budget?: number
  withinBudget?: boolean
}

export type PublicTelemetryTransport = (event: Readonly<PublicTelemetryEvent>) => void | Promise<void>

export interface PublicTelemetryOptions { transport?: PublicTelemetryTransport }
type PublicTelemetryRuntimeConfig = {
  public?: {
    publicTelemetryEnabled?: unknown
    publicTelemetryEndpoint?: unknown
  }
}
type TelemetryBeacon = (url: string, data: BodyInit | null) => boolean
type TelemetryFetch = (url: string, init: RequestInit) => unknown

export interface DefaultPublicTelemetryTransportOptions {
  config: PublicTelemetryRuntimeConfig
  origin: string
  sendBeacon?: TelemetryBeacon
  fetch?: TelemetryFetch
  Blob?: typeof Blob
}

const ROUTE_FAMILIES = new Set<PublicRouteFamily>(['home', 'catalog', 'search', 'detail', 'planner', 'community', 'settings', 'other'])
const VIEWPORTS = new Set<PublicViewport>(['mobile', 'tablet', 'desktop'])
const NETWORKS = new Set<ContextEnvelope['network']>(['online', 'degraded', 'offline'])
const THEMES = new Set<PublicTheme>(['nocturne', 'parchment'])
const KINDS = new Set<PublicTelemetryKind>(['outcome', 'harm', 'performance'])
const METRICS = new Set<PublicPerformanceMetric>(['lcp', 'cls', 'inp', 'ttfb', 'ttfur', 'time-to-primary-action', 'js-bytes', 'css-bytes', 'ssr-bytes', 'api-p95', 'map-tile-cost', 'media-decode-cost'])
const EVENT_NAMES = new Set<PublicTelemetryEventName>(['search-submitted', 'search-result-opened', 'search-recovered', 'detail-recovery-shown', 'planner-completed', 'first-useful-result'])
const OUTCOME_CLASSES = new Set<PublicOutcomeClass>(['result-shown', 'detail-opened', 'task-completed', 'task-recovered'])
const HARM_CLASSES = new Set<PublicHarmClass>(['false-not-found-risk', 'stale-data-risk', 'blocked-core-task', 'privacy-boundary-rejected'])
const AREA_IDS = new Set<PublicAreaId>(['vinh-long', 'ben-tre', 'tra-vinh', 'tri-region', 'unknown'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function member<T extends string>(value: unknown, allowed: Set<T>): T | undefined {
  return typeof value === 'string' && allowed.has(value as T) ? value as T : undefined
}

function finiteNonNegative(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : undefined
}

export function sanitizePublicTelemetry(input: unknown): PublicTelemetryEvent {
  if (!isRecord(input)) return {}
  const event: PublicTelemetryEvent = {}
  const eventName = member(input.eventName, EVENT_NAMES)
  const outcomeClass = member(input.outcomeClass, OUTCOME_CLASSES)
  const harmClass = member(input.harmClass, HARM_CLASSES)
  const kind = member(input.kind, KINDS)
  const routeFamily = member(input.routeFamily, ROUTE_FAMILIES)
  const viewport = member(input.viewport, VIEWPORTS)
  const network = member(input.network, NETWORKS)
  const theme = member(input.theme, THEMES)
  const areaValue = typeof input.areaId === 'string' ? input.areaId : input.area
  const areaId = member(areaValue, AREA_IDS)
  const metric = member(input.metric, METRICS)
  const value = finiteNonNegative(input.value)
  const budget = finiteNonNegative(input.budget)

  if (kind) event.kind = kind
  if (eventName) event.eventName = eventName
  if (outcomeClass) event.outcomeClass = outcomeClass
  if (harmClass) event.harmClass = harmClass
  if (routeFamily) event.routeFamily = routeFamily
  if (viewport) event.viewport = viewport
  if (network) event.network = network
  if (theme) event.theme = theme
  if (areaId) event.areaId = areaId
  if (metric) event.metric = metric
  if (value !== undefined) event.value = value
  if (budget !== undefined) event.budget = budget
  if (value !== undefined && budget !== undefined) event.withinBudget = value <= budget
  return event
}

export function resolvePublicTelemetryEndpoint(input: unknown, origin: string): string | undefined {
  if (typeof input !== 'string' || !input.trim()) return undefined
  try {
    const base = new URL(origin)
    const endpoint = new URL(input, base)
    if ((endpoint.protocol !== 'http:' && endpoint.protocol !== 'https:')
      || endpoint.origin !== base.origin
      || endpoint.username
      || endpoint.password) return undefined
    return endpoint.href
  } catch {
    return undefined
  }
}

export function createDefaultPublicTelemetryTransport(options: DefaultPublicTelemetryTransportOptions): PublicTelemetryTransport {
  return (event) => {
    if (options.config.public?.publicTelemetryEnabled !== true) return
    const endpoint = resolvePublicTelemetryEndpoint(options.config.public?.publicTelemetryEndpoint, options.origin)
    if (!endpoint) return
    try {
      const body = JSON.stringify(event)
      const beaconBody = options.Blob ? new options.Blob([body], { type: 'application/json' }) : body
      if (options.sendBeacon?.(endpoint, beaconBody)) return
      const pending = options.fetch?.(endpoint, { method: 'POST', body, headers: { 'content-type': 'application/json' }, keepalive: true })
      if (pending && typeof (pending as Promise<unknown>).catch === 'function') {
        void (pending as Promise<unknown>).catch(() => {})
      }
    } catch {
      // Observability is best-effort and must never block search, detail or planner.
    }
  }
}

function defaultTransport(event: Readonly<PublicTelemetryEvent>): void {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return
  try {
    const config = useRuntimeConfig() as PublicTelemetryRuntimeConfig
    const transport = createDefaultPublicTelemetryTransport({
      config,
      origin: window.location.origin,
      sendBeacon: typeof navigator.sendBeacon === 'function' ? navigator.sendBeacon.bind(navigator) : undefined,
      fetch: typeof fetch === 'function' ? fetch : undefined,
      Blob: typeof Blob === 'undefined' ? undefined : Blob,
    })
    transport(event)
  } catch {
    // Observability is best-effort and must never block search, detail or planner.
  }
}

function createTracker(transport: PublicTelemetryTransport) {
  return (input: Record<string, unknown>, kind: PublicTelemetryKind): PublicTelemetryEvent | null => {
    const event = sanitizePublicTelemetry({ ...input, kind })
    const valid = !!event.eventName && !!event.routeFamily && !!event.viewport && !!event.network && !!event.theme
      && (kind === 'outcome' ? !!event.outcomeClass : kind === 'harm' ? !!event.harmClass : !!event.metric && event.value !== undefined && event.budget !== undefined)
    if (!valid) return null
    try {
      const pending = transport(Object.freeze(event))
      if (pending && typeof pending.then === 'function') void pending.catch(() => {})
    } catch {
      // A failed transport is intentionally invisible to the public task.
    }
    return event
  }
}

export function usePublicTelemetry(options: PublicTelemetryOptions = {}) {
  const track = createTracker(options.transport || defaultTransport)
  return {
    trackPublicOutcome: (input: PublicOutcomeInput) => track(input as unknown as Record<string, unknown>, 'outcome'),
    trackPublicHarm: (input: PublicHarmInput) => track(input as unknown as Record<string, unknown>, 'harm'),
    trackPerformanceBudget: (input: PublicPerformanceInput) => track(input as unknown as Record<string, unknown>, 'performance'),
  }
}
