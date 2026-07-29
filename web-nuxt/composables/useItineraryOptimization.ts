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

type RouteTableCacheEntry = {
  expiresAt: number | null
  promise: Promise<RouteTableResult | null>
}

const ROUTE_TABLE_CACHE_TTL_MS = 15 * 60 * 1000
const ROUTE_TABLE_CACHE_MAX_KEYS = 16
const routeTableCache = new Map<string, RouteTableCacheEntry>()

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
