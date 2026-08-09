import type { ContextEnvelope } from '~/types/publicExperience'

export type PublicTelemetryKind = 'outcome' | 'harm' | 'performance'
export type PublicRouteFamily = 'home' | 'catalog' | 'search' | 'detail' | 'planner' | 'community' | 'settings' | 'other'
export type PublicViewport = 'mobile' | 'tablet' | 'desktop'
export type PublicTheme = 'nocturne' | 'parchment'
export type PublicPerformanceMetric = 'lcp' | 'cls' | 'inp' | 'ttfb' | 'ttfur' | 'time-to-primary-action' | 'js-bytes' | 'css-bytes' | 'ssr-bytes' | 'api-p95' | 'map-tile-cost' | 'media-decode-cost'

export interface PublicTelemetryContext {
  eventName: string
  routeFamily: PublicRouteFamily
  viewport: PublicViewport
  network: ContextEnvelope['network']
  theme: PublicTheme
  areaId?: string
}

export interface PublicOutcomeInput extends PublicTelemetryContext { outcomeClass: string }
export interface PublicHarmInput extends PublicTelemetryContext { harmClass: string }
export interface PublicPerformanceInput extends PublicTelemetryContext {
  metric: PublicPerformanceMetric
  value: number
  budget: number
}

export type PublicTelemetryEvent = Partial<PublicTelemetryContext> & {
  kind?: PublicTelemetryKind
  outcomeClass?: string
  harmClass?: string
  metric?: PublicPerformanceMetric
  value?: number
  budget?: number
  withinBudget?: boolean
}

export type PublicTelemetryTransport = (event: Readonly<PublicTelemetryEvent>) => void | Promise<void>

export interface PublicTelemetryOptions { transport?: PublicTelemetryTransport }

const ROUTE_FAMILIES = new Set<PublicRouteFamily>(['home', 'catalog', 'search', 'detail', 'planner', 'community', 'settings', 'other'])
const VIEWPORTS = new Set<PublicViewport>(['mobile', 'tablet', 'desktop'])
const NETWORKS = new Set<ContextEnvelope['network']>(['online', 'degraded', 'offline'])
const THEMES = new Set<PublicTheme>(['nocturne', 'parchment'])
const KINDS = new Set<PublicTelemetryKind>(['outcome', 'harm', 'performance'])
const METRICS = new Set<PublicPerformanceMetric>(['lcp', 'cls', 'inp', 'ttfb', 'ttfur', 'time-to-primary-action', 'js-bytes', 'css-bytes', 'ssr-bytes', 'api-p95', 'map-tile-cost', 'media-decode-cost'])
const PRIVATE_NUMBER = /(?:\d[\s().+-]*){8,}/
const SAFE_TOKEN = /^[a-z][a-z0-9-]{0,63}$/
const SAFE_AREA = /^[a-z0-9][a-z0-9-]{0,63}$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function token(value: unknown): string | undefined {
  if (typeof value !== 'string' || PRIVATE_NUMBER.test(value)) return undefined
  const normalized = value.trim().toLowerCase()
  return SAFE_TOKEN.test(normalized) ? normalized : undefined
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
  const eventName = token(input.eventName)
  const outcomeClass = token(input.outcomeClass)
  const harmClass = token(input.harmClass)
  const kind = member(input.kind, KINDS)
  const routeFamily = member(input.routeFamily, ROUTE_FAMILIES)
  const viewport = member(input.viewport, VIEWPORTS)
  const network = member(input.network, NETWORKS)
  const theme = member(input.theme, THEMES)
  const areaValue = typeof input.areaId === 'string' ? input.areaId : input.area
  const areaId = typeof areaValue === 'string' && SAFE_AREA.test(areaValue) && !PRIVATE_NUMBER.test(areaValue) ? areaValue : undefined
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

function defaultTransport(event: Readonly<PublicTelemetryEvent>): void {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return
  try {
    const config = useRuntimeConfig()
    if (config.public.publicTelemetryEnabled !== true) return
    const endpoint = typeof config.public.publicTelemetryEndpoint === 'string' ? config.public.publicTelemetryEndpoint : ''
    if (!endpoint.startsWith('/')) return
    const body = JSON.stringify(event)
    if (typeof navigator.sendBeacon === 'function' && navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }))) return
    void fetch(endpoint, { method: 'POST', body, headers: { 'content-type': 'application/json' }, keepalive: true }).catch(() => {})
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
