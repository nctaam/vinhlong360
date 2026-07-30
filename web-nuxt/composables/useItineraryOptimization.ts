import type {
  RouteLeg,
  RouteResult,
  RouteTableResult,
  TransportMode,
} from './useRouting'

export type Coordinates = [number, number]
export type BlockedEdge = [string, string]

export interface StopWithCoords {
  id: string
  coords: Coordinates | null
}

export interface RoutableStop<T extends StopWithCoords> {
  key: string
  originalIndex: number
  stop: T
  coordinates: Coordinates
}

export interface OptimizeOrderResponse {
  ordered_ids: string[]
  distance_before_km: number
  distance_after_km: number
  saved_distance_km: number
  backtrack_ratio: number
  solver: 'exact-dp' | 'beam-search' | 'schedule-exact' | 'schedule-beam'
  warnings: string[]
  schedule?: OptimizeScheduleResponse
}

export interface OptimizeScheduleStopRequest {
  id: string
  visit_minutes?: number
  opening_hours?: string | null
  requested_time?: string | null
  required?: boolean
}

export interface OptimizeScheduleRequest {
  day_start_minute: number
  day_end_minute: number
  mode: TransportMode
  stops: OptimizeScheduleStopRequest[]
  duration_matrix_minutes?: Array<Array<number | null>> | null
}

export interface OptimizeSchedulePlacement {
  stop_id: string
  arrival_minute: number
  start_visit_minute: number
  end_visit_minute: number
}

export interface OptimizeScheduleResponse {
  placements: OptimizeSchedulePlacement[]
  skipped: Array<{ stop_id: string; reason: string }>
  matrix_source: 'request' | 'haversine-fallback'
  total_travel_minutes: number
  waiting_minutes: number
  overtime_minutes: number
  minimum_slack_minutes: number
}

export type PlannerScheduleWarning =
  | 'opening-hours-unknown'
  | 'opening-hours-invalid'

export interface PlannerScheduleMetadata {
  visitMinutes: number
  openingHours: string | null
  warnings: PlannerScheduleWarning[]
  placement?: OptimizeSchedulePlacement
}

export interface PlannerInputState {
  version: number
}

export interface PlannerStopDetailEnrichmentOptions<
  T extends StopWithCoords,
  TDetail,
> {
  stop: T
  fetchDetail: () => Promise<TDetail>
  isCurrentStop: (stop: T) => boolean
  coordinatesFromDetail: (detail: TDetail) => Coordinates | null
  metadataFromDetail: (detail: TDetail) => PlannerScheduleMetadata
  metadataByStop: WeakMap<object, PlannerScheduleMetadata>
  invalidate: () => void
}

export type PlannerStopDetailEnrichmentResult =
  | 'updated'
  | 'unchanged'
  | 'removed'

export interface SavedPlanStopShape {
  id: string
  name: string
  type: string
  place_name?: string
  coords: Coordinates | null
  time: string
  notes: string
}

export interface BoundedOptimizationResult<T extends StopWithCoords> {
  ordered: RoutableStop<T>[]
  route: RouteResult | null
  optimization: OptimizeOrderResponse
  attempts: 1 | 2
  unresolvedUturn: boolean
  warnings: string[]
}

interface OptimizeRequestOptions {
  method: 'POST'
  body: OptimizeRequestBody
}

interface OptimizeRequestBody {
  stops: Array<{ id: string; coordinates: Coordinates }>
  strict_direction: true
  blocked_edges: BlockedEdge[]
  schedule?: OptimizeScheduleRequest
}

type OptimizeFetcher = (
  url: string,
  options: OptimizeRequestOptions,
) => Promise<OptimizeOrderResponse>

type OptimizeFunction<T extends StopWithCoords> = (
  routed: RoutableStop<T>[],
  blockedEdges: BlockedEdge[],
) => Promise<OptimizeOrderResponse>

type RouteFunction = (coordinates: Coordinates[]) => Promise<RouteResult | null>

type PlannerTableFunction = (
  coordinates: Coordinates[],
  mode: TransportMode,
) => Promise<RouteTableResult | null>

type PlannerRequestFunction<T extends StopWithCoords> = (
  routed: RoutableStop<T>[],
  blockedEdges: BlockedEdge[],
  schedule?: OptimizeScheduleRequest,
) => Promise<OptimizeOrderResponse>

export interface PlannerOptimizationOptions<T extends StopWithCoords> {
  scheduleEnabled: boolean
  routed: RoutableStop<T>[]
  metadataByStop: WeakMap<object, PlannerScheduleMetadata>
  inputState: PlannerInputState
  mode: TransportMode
  fetchTable: PlannerTableFunction
  requestOptimization: PlannerRequestFunction<T>
  route: RouteFunction
}

export interface CurrentPlannerOptimizationResult<T extends StopWithCoords> {
  status: 'current'
  outcome: BoundedOptimizationResult<T>
  scheduleEnvelope?: OptimizeScheduleRequest
  scheduleWarnings: string[]
}

export interface StalePlannerOptimizationResult {
  status: 'stale'
}

export type PlannerOptimizationResult<T extends StopWithCoords> =
  | CurrentPlannerOptimizationResult<T>
  | StalePlannerOptimizationResult

export interface PlannerOptimizationCommitCallbacks<T extends StopWithCoords> {
  isActive?: () => boolean
  applyPlacements: (result: CurrentPlannerOptimizationResult<T>) => void
  reorderStops: (orderedKeys: string[]) => void
  applyRoute: (route: RouteResult | null) => void
  updateMap: (route: RouteResult | null) => Promise<void> | void
}

export interface RouteRefreshTimer {
  schedule: (callback: () => void, delayMs: number) => unknown
  cancel: (handle: unknown) => void
}

export interface SuspendedRouteScheduler {
  request: () => number | null
  resume: () => void
  cancelScheduled: () => void
  discardPending: (requestId: number | null) => void
  dispose: () => void
}

type RouteTableCacheEntry = {
  expiresAt: number | null
  promise: Promise<RouteTableResult | null>
}

const ROUTE_TABLE_CACHE_TTL_MS = 15 * 60 * 1000
const ROUTE_TABLE_CACHE_MAX_KEYS = 16
const routeTableCache = new Map<string, RouteTableCacheEntry>()

const defaultRouteRefreshTimer: RouteRefreshTimer = {
  schedule: (callback, delayMs) => setTimeout(callback, delayMs),
  cancel: handle => clearTimeout(handle as ReturnType<typeof setTimeout>),
}

const DEFAULT_VISIT_MINUTES: Record<string, number> = {
  accommodation: 0,
  attraction: 90,
  craft_village: 60,
  dish: 45,
  economy: 30,
  event: 120,
  experience: 120,
  history: 60,
  nature: 90,
  person: 30,
  product: 30,
}

const TIME_RANGE_SOURCE = String.raw`(\d{1,2})(?:(?::(\d{2}))|(?:[hH](\d{2})?))\s*-\s*(\d{1,2})(?:(?::(\d{2}))|(?:[hH](\d{2})?))`
const REQUESTED_TIME_PATTERN = new RegExp(`^\\s*${TIME_RANGE_SOURCE}\\s*$`)
const OPENING_HOURS_PATTERN = new RegExp(TIME_RANGE_SOURCE, 'g')
const HOURS_DURATION_PATTERN = /(\d+(?:[.,]\d+)?)\s*(?:giờ|gio|hours?|hrs?|h)\b/i
const MINUTES_DURATION_PATTERN = /(\d+(?:[.,]\d+)?)\s*(?:phút|phut|minutes?|mins?)\b/i

export function createSuspendedRouteScheduler(
  refresh: () => Promise<void> | void,
  isSuspended: () => boolean,
  delayMs = 400,
  timer: RouteRefreshTimer = defaultRouteRefreshTimer,
): SuspendedRouteScheduler {
  let scheduledHandle: unknown
  let hasScheduledHandle = false
  let scheduledToken: object | null = null
  let nextRequestId = 0
  let pendingRequestId: number | null = null
  let disposed = false

  const cancelScheduled = () => {
    if (!hasScheduledHandle) return
    timer.cancel(scheduledHandle)
    scheduledHandle = undefined
    hasScheduledHandle = false
    scheduledToken = null
  }

  const scheduleRefresh = () => {
    if (disposed) return
    cancelScheduled()
    const token = {}
    scheduledToken = token
    scheduledHandle = timer.schedule(() => {
      if (disposed || scheduledToken !== token) return
      scheduledHandle = undefined
      hasScheduledHandle = false
      scheduledToken = null
      void refresh()
    }, delayMs)
    hasScheduledHandle = true
  }

  return {
    request: () => {
      if (disposed) return null
      const requestId = ++nextRequestId
      if (isSuspended()) {
        pendingRequestId = requestId
        return requestId
      }
      pendingRequestId = null
      scheduleRefresh()
      return requestId
    },
    resume: () => {
      if (disposed || pendingRequestId === null || isSuspended()) return
      pendingRequestId = null
      scheduleRefresh()
    },
    cancelScheduled,
    discardPending: (requestId) => {
      if (disposed || requestId === null) return
      if (pendingRequestId === requestId) pendingRequestId = null
    },
    dispose: () => {
      if (disposed) return
      disposed = true
      pendingRequestId = null
      cancelScheduled()
    },
  }
}

function minuteOfDay(hourText: string, minuteText?: string): number | null {
  const hour = Number(hourText)
  const minute = Number(minuteText || 0)
  if (
    !Number.isInteger(hour)
    || !Number.isInteger(minute)
    || hour > 24
    || minute > 59
    || (hour === 24 && minute !== 0)
  ) {
    return null
  }
  return hour * 60 + minute
}

function validTimeRangeMatch(match: RegExpMatchArray | RegExpExecArray): boolean {
  const start = minuteOfDay(match[1] ?? '', match[2] ?? match[3])
  const end = minuteOfDay(match[4] ?? '', match[5] ?? match[6])
  return start !== null && end !== null && start <= end
}

function isSupportedRequestedTime(value: string): boolean {
  const match = value.match(REQUESTED_TIME_PATTERN)
  return match !== null && validTimeRangeMatch(match)
}

function hasSupportedOpeningHours(value: string): boolean {
  OPENING_HOURS_PATTERN.lastIndex = 0
  let match = OPENING_HOURS_PATTERN.exec(value)
  while (match) {
    if (validTimeRangeMatch(match)) return true
    match = OPENING_HOURS_PATTERN.exec(value)
  }
  return false
}

function defaultVisitMinutes(type: string): number {
  return DEFAULT_VISIT_MINUTES[type.trim().toLowerCase()] ?? 60
}

function inferredVisitMinutes(type: string, suggestedDuration: unknown): number {
  if (typeof suggestedDuration !== 'string') return defaultVisitMinutes(type)
  const hours = suggestedDuration.match(HOURS_DURATION_PATTERN)
  const minutes = suggestedDuration.match(MINUTES_DURATION_PATTERN)
  if (!hours && !minutes) return defaultVisitMinutes(type)
  const hourValue = Number((hours?.[1] ?? '0').replace(',', '.'))
  const minuteValue = Number((minutes?.[1] ?? '0').replace(',', '.'))
  return Math.round(hourValue * 60 + minuteValue)
}

export function plannerMetadataForEntity(
  type: string,
  attributes?: { suggested_duration?: unknown; hours?: unknown } | null,
): PlannerScheduleMetadata {
  const rawHours = typeof attributes?.hours === 'string' && attributes.hours.trim().length
    ? attributes.hours
    : null
  const warnings: PlannerScheduleWarning[] = rawHours === null
    ? ['opening-hours-unknown']
    : hasSupportedOpeningHours(rawHours)
      ? []
      : ['opening-hours-invalid']
  return {
    visitMinutes: inferredVisitMinutes(type, attributes?.suggested_duration),
    openingHours: rawHours,
    warnings,
  }
}

export function plannerMetadataForLoadedStop(type: string): PlannerScheduleMetadata {
  return {
    visitMinutes: defaultVisitMinutes(type),
    openingHours: null,
    warnings: ['opening-hours-unknown'],
  }
}

function formatMinuteOfDay(value: number): string {
  const minute = Math.max(0, Math.round(value))
  const hours = Math.floor(minute / 60)
  const minutes = minute % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

export function formatScheduledInterval(
  placement?: Pick<OptimizeSchedulePlacement, 'start_visit_minute' | 'end_visit_minute'> | null,
): string {
  if (!placement) return ''
  return `${formatMinuteOfDay(placement.start_visit_minute)}-${formatMinuteOfDay(placement.end_visit_minute)}`
}

export function applySchedulePlacement<T extends object>(
  stop: T,
  placement: OptimizeSchedulePlacement,
): { stop: T; scheduledTime: string } {
  return {
    stop,
    scheduledTime: formatScheduledInterval(placement),
  }
}

function clearSchedulePlacements<T extends object>(
  stops: T[],
  metadataByStop: WeakMap<object, PlannerScheduleMetadata>,
): void {
  stops.forEach((stop) => {
    const metadata = metadataByStop.get(stop)
    if (!metadata?.placement) return
    const { placement: _placement, ...withoutPlacement } = metadata
    metadataByStop.set(stop, withoutPlacement)
  })
}

export function invalidatePlannerInputs<T extends object>(
  inputState: PlannerInputState,
  stops: T[],
  metadataByStop: WeakMap<object, PlannerScheduleMetadata>,
): void {
  clearSchedulePlacements(stops, metadataByStop)
  inputState.version += 1
}

function samePlannerMetadata(
  current: PlannerScheduleMetadata | undefined,
  next: PlannerScheduleMetadata,
): boolean {
  return current?.visitMinutes === next.visitMinutes
    && current.openingHours === next.openingHours
    && current.warnings.join('|') === next.warnings.join('|')
}

export async function enrichPlannerStopFromDetail<
  T extends StopWithCoords,
  TDetail,
>(
  options: PlannerStopDetailEnrichmentOptions<T, TDetail>,
): Promise<PlannerStopDetailEnrichmentResult> {
  const detail = await options.fetchDetail()
  if (!options.isCurrentStop(options.stop)) return 'removed'

  const coordinates = options.coordinatesFromDetail(detail)
  const nextMetadata = options.metadataFromDetail(detail)
  const currentMetadata = options.metadataByStop.get(options.stop)
  const coordinatesChanged = Boolean(coordinates) && (
    !options.stop.coords
    || options.stop.coords[0] !== coordinates?.[0]
    || options.stop.coords[1] !== coordinates?.[1]
  )
  const metadataChanged = !samePlannerMetadata(currentMetadata, nextMetadata)
  if (!coordinatesChanged && !metadataChanged) return 'unchanged'

  options.invalidate()
  if (coordinates) options.stop.coords = coordinates
  options.metadataByStop.set(options.stop, nextMetadata)
  return 'updated'
}

export function applySchedulePlacements<T extends StopWithCoords>(
  routed: RoutableStop<T>[],
  placements: OptimizeSchedulePlacement[],
  metadataByStop: WeakMap<object, PlannerScheduleMetadata>,
  inputState?: PlannerInputState,
): number {
  clearSchedulePlacements(routed.map(item => item.stop), metadataByStop)
  const byKey = new Map(routed.map(item => [item.key, item.stop]))
  let applied = 0
  placements.forEach((placement) => {
    const stop = byKey.get(placement.stop_id)
    if (!stop) return
    const appliedPlacement = applySchedulePlacement(stop, placement)
    const metadata = metadataByStop.get(stop) ?? plannerMetadataForLoadedStop('')
    metadataByStop.set(appliedPlacement.stop, { ...metadata, placement })
    applied += 1
  })
  if (inputState) inputState.version += 1
  return applied
}

export function serializePlanStops<T extends SavedPlanStopShape>(
  stops: T[],
): SavedPlanStopShape[] {
  return stops.map((stop) => {
    const serialized: SavedPlanStopShape = {
      id: stop.id,
      name: stop.name,
      type: stop.type,
      coords: stop.coords ? [stop.coords[0], stop.coords[1]] : null,
      time: stop.time,
      notes: stop.notes,
    }
    if (stop.place_name !== undefined) serialized.place_name = stop.place_name
    return serialized
  })
}

export function buildPlannerScheduleEnvelope<
  T extends StopWithCoords & { time?: string },
>(
  routed: RoutableStop<T>[],
  metadataByStop: WeakMap<object, PlannerScheduleMetadata>,
  mode: TransportMode,
  table: RouteTableResult | null,
): { envelope: OptimizeScheduleRequest; warnings: string[] } {
  const warnings: string[] = []
  const envelope: OptimizeScheduleRequest = {
    day_start_minute: 480,
    day_end_minute: 1080,
    mode,
    stops: routed.map((item) => {
      const metadata = metadataByStop.get(item.stop)
        ?? plannerMetadataForLoadedStop('')
      metadata.warnings.forEach(warning => warnings.push(`${warning}:${item.key}`))
      const scheduledStop: OptimizeScheduleStopRequest = {
        id: item.key,
        visit_minutes: metadata.visitMinutes,
        required: true,
      }
      if (metadata.openingHours !== null) {
        scheduledStop.opening_hours = metadata.openingHours
      }
      const requestedTime = item.stop.time?.trim()
      if (requestedTime) {
        if (isSupportedRequestedTime(requestedTime)) {
          scheduledStop.requested_time = requestedTime
        }
        else {
          warnings.push(`requested-time-invalid:${item.key}`)
        }
      }
      return scheduledStop
    }),
  }
  if (table) envelope.duration_matrix_minutes = table.durationMinutes
  return { envelope, warnings }
}

export async function runPlannerOptimization<
  T extends StopWithCoords & { time?: string },
>(
  options: PlannerOptimizationOptions<T>,
): Promise<PlannerOptimizationResult<T>> {
  const inputVersion = options.inputState.version
  try {
    let scheduleEnvelope: OptimizeScheduleRequest | undefined
    let scheduleWarnings: string[] = []
    if (options.scheduleEnabled) {
      const coordinates = options.routed.map(item => item.coordinates)
      const table = await getCachedRouteTable(
        routeTableCacheKey(coordinates, options.mode),
        () => options.fetchTable(coordinates, options.mode),
      )
      const prepared = buildPlannerScheduleEnvelope(
        options.routed,
        options.metadataByStop,
        options.mode,
        table,
      )
      scheduleEnvelope = prepared.envelope
      scheduleWarnings = prepared.warnings
      if (!table) scheduleWarnings.push('route-table-unavailable')
    }

    const outcome = await runBoundedOptimization(
      options.routed,
      (routed, blockedEdges) => options.requestOptimization(
        routed,
        blockedEdges,
        scheduleEnvelope,
      ),
      options.route,
    )
    if (options.inputState.version !== inputVersion) return { status: 'stale' }
    return { status: 'current', outcome, scheduleEnvelope, scheduleWarnings }
  }
  catch (error) {
    if (options.inputState.version !== inputVersion) return { status: 'stale' }
    throw error
  }
}

export async function commitPlannerOptimizationResult<
  T extends StopWithCoords,
>(
  result: PlannerOptimizationResult<T>,
  callbacks: PlannerOptimizationCommitCallbacks<T>,
): Promise<CurrentPlannerOptimizationResult<T> | null> {
  if (result.status === 'stale') return null
  if (callbacks.isActive && !callbacks.isActive()) return null
  callbacks.applyPlacements(result)
  if (callbacks.isActive && !callbacks.isActive()) return null
  callbacks.reorderStops(result.outcome.ordered.map(item => item.key))
  if (callbacks.isActive && !callbacks.isActive()) return null
  callbacks.applyRoute(result.outcome.route)
  if (callbacks.isActive && !callbacks.isActive()) return null
  await callbacks.updateMap(result.outcome.route)
  if (callbacks.isActive && !callbacks.isActive()) return null
  return result
}

function isCoordinates(value: StopWithCoords['coords']): value is Coordinates {
  return Array.isArray(value)
    && value.length >= 2
    && Number.isFinite(value[0])
    && Number.isFinite(value[1])
}

export function collectRoutableStops<T extends StopWithCoords>(
  stops: T[],
): RoutableStop<T>[] {
  const routed: RoutableStop<T>[] = []
  stops.forEach((stop, originalIndex) => {
    if (!isCoordinates(stop.coords)) return
    routed.push({
      key: `planner-stop-${originalIndex}`,
      originalIndex,
      stop,
      coordinates: stop.coords,
    })
  })
  return routed
}

export function routeTableCacheKey(
  coordinates: Coordinates[],
  mode: TransportMode,
): string {
  const rounded = coordinates
    .map(([lat, lng]) => `${lat.toFixed(5)},${lng.toFixed(5)}`)
    .join(';')
  return `${mode}:${rounded}`
}

export function getCachedRouteTable(
  key: string,
  fetcher: () => Promise<RouteTableResult | null>,
): Promise<RouteTableResult | null> {
  const now = Date.now()
  for (const [cachedKey, entry] of routeTableCache) {
    if (entry.expiresAt !== null && entry.expiresAt <= now) {
      routeTableCache.delete(cachedKey)
    }
  }

  const cached = routeTableCache.get(key)
  if (cached) return cached.promise

  let request: Promise<RouteTableResult | null>
  try {
    request = fetcher()
  } catch (error) {
    return Promise.reject(error)
  }

  const entry: RouteTableCacheEntry = {
    expiresAt: null,
    promise: request,
  }
  entry.promise = Promise.resolve(request).then(
    (result) => {
      entry.expiresAt = Date.now() + ROUTE_TABLE_CACHE_TTL_MS
      return result
    },
    (error) => {
      if (routeTableCache.get(key) === entry) routeTableCache.delete(key)
      throw error
    },
  )
  routeTableCache.set(key, entry)

  while (routeTableCache.size > ROUTE_TABLE_CACHE_MAX_KEYS) {
    const oldestKey = routeTableCache.keys().next().value
    if (oldestKey === undefined) break
    routeTableCache.delete(oldestKey)
  }
  return entry.promise
}

function reorderRoutableStops<T extends StopWithCoords>(
  routed: RoutableStop<T>[],
  orderedIds: string[],
): RoutableStop<T>[] {
  const byKey = new Map(routed.map(item => [item.key, item]))
  const uniqueIds = new Set(orderedIds)
  if (
    orderedIds.length !== routed.length
    || uniqueIds.size !== routed.length
    || orderedIds.some(key => !byKey.has(key))
  ) {
    throw new Error('Thứ tự tối ưu không khớp danh sách điểm được gửi')
  }
  return orderedIds.map(key => byKey.get(key) as RoutableStop<T>)
}

export function mergeOptimizedStops<T extends StopWithCoords>(
  stops: T[],
  routed: RoutableStop<T>[],
  orderedIds: string[],
): T[] {
  const ordered = reorderRoutableStops(routed, orderedIds)
  const merged = stops.slice()
  routed.forEach((slot, index) => {
    const orderedStop = ordered[index]
    if (orderedStop) merged[slot.originalIndex] = orderedStop.stop
  })
  return merged
}

export function routeLegForStopIndex(
  stopIndex: number,
  routed: Array<RoutableStop<StopWithCoords>>,
  legs: RouteLeg[],
): RouteLeg | null {
  const routedIndex = routed.findIndex(item => item.originalIndex === stopIndex)
  if (routedIndex < 0 || routedIndex >= legs.length) return null
  return legs[routedIndex] ?? null
}

export function blockedEdgesForUturns<T extends StopWithCoords>(
  routed: RoutableStop<T>[],
  route: RouteResult,
): BlockedEdge[] {
  const blocked: BlockedEdge[] = []
  route.legs.forEach((leg, index) => {
    const source = routed[index]
    const target = routed[index + 1]
    if (leg.hasUturn && source && target) {
      blocked.push([source.key, target.key])
    }
  })
  return blocked
}

export function requestOptimizedOrder<T extends StopWithCoords>(
  routed: RoutableStop<T>[],
  blockedEdges?: BlockedEdge[],
  fetcher?: OptimizeFetcher,
): Promise<OptimizeOrderResponse>
export function requestOptimizedOrder<T extends StopWithCoords>(
  routed: RoutableStop<T>[],
  blockedEdges: BlockedEdge[],
  schedule: OptimizeScheduleRequest,
  fetcher?: OptimizeFetcher,
): Promise<OptimizeOrderResponse>
export async function requestOptimizedOrder<T extends StopWithCoords>(
  routed: RoutableStop<T>[],
  blockedEdges: BlockedEdge[] = [],
  scheduleOrFetcher?: OptimizeScheduleRequest | OptimizeFetcher,
  injectedFetcher?: OptimizeFetcher,
): Promise<OptimizeOrderResponse> {
  const schedule = typeof scheduleOrFetcher === 'function'
    ? undefined
    : scheduleOrFetcher
  const fetcher = (
    typeof scheduleOrFetcher === 'function'
      ? scheduleOrFetcher
      : injectedFetcher
  ) ?? ((url, options) => $fetch<OptimizeOrderResponse>(url, options))
  const body: OptimizeRequestBody = {
    stops: routed.map(item => ({
      id: item.key,
      coordinates: item.coordinates,
    })),
    strict_direction: true,
    blocked_edges: blockedEdges,
  }
  if (schedule) body.schedule = schedule

  return fetcher('/api/itineraries/optimize-order', {
    method: 'POST',
    body,
  })
}

function validationWarning(): string {
  return 'Không thể kiểm tra U-turn trên tuyến đường thực tế'
}

export async function runBoundedOptimization<T extends StopWithCoords>(
  initialRouted: RoutableStop<T>[],
  optimize: OptimizeFunction<T>,
  route: RouteFunction,
): Promise<BoundedOptimizationResult<T>> {
  const firstOptimization = await optimize(initialRouted, [])
  const firstOrdered = reorderRoutableStops(
    initialRouted,
    firstOptimization.ordered_ids,
  )
  const firstRoute = await route(firstOrdered.map(item => item.coordinates))
  const firstWarnings = [...firstOptimization.warnings]
  if (!firstRoute) {
    firstWarnings.push(validationWarning())
    return {
      ordered: firstOrdered,
      route: null,
      optimization: firstOptimization,
      attempts: 1,
      unresolvedUturn: false,
      warnings: firstWarnings,
    }
  }

  const blockedEdges = blockedEdgesForUturns(firstOrdered, firstRoute)
  if (!blockedEdges.length) {
    return {
      ordered: firstOrdered,
      route: firstRoute,
      optimization: firstOptimization,
      attempts: 1,
      unresolvedUturn: false,
      warnings: firstWarnings,
    }
  }

  try {
    const secondOptimization = await optimize(firstOrdered, blockedEdges)
    const secondOrdered = reorderRoutableStops(
      firstOrdered,
      secondOptimization.ordered_ids,
    )
    const secondRoute = await route(secondOrdered.map(item => item.coordinates))
    const combinedOptimization: OptimizeOrderResponse = {
      ...secondOptimization,
      distance_before_km: firstOptimization.distance_before_km,
      saved_distance_km: Math.max(
        0,
        firstOptimization.distance_before_km - secondOptimization.distance_after_km,
      ),
      warnings: [...new Set([
        ...firstOptimization.warnings,
        ...secondOptimization.warnings,
      ])],
    }
    const unresolvedUturn = !secondRoute
      || blockedEdgesForUturns(secondOrdered, secondRoute).length > 0
    const warnings = [...combinedOptimization.warnings]
    if (!secondRoute) warnings.push(validationWarning())
    if (unresolvedUturn) warnings.push('Tuyến vẫn có thao tác quay đầu theo dữ liệu OSRM')
    return {
      ordered: secondOrdered,
      route: secondRoute,
      optimization: combinedOptimization,
      attempts: 2,
      unresolvedUturn,
      warnings,
    }
  } catch {
    return {
      ordered: firstOrdered,
      route: firstRoute,
      optimization: firstOptimization,
      attempts: 2,
      unresolvedUturn: true,
      warnings: [
        ...firstWarnings,
        'Không tìm được thứ tự thay thế cho cạnh có thao tác quay đầu',
      ],
    }
  }
}
