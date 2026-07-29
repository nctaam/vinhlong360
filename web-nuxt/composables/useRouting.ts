export type TransportMode = 'driving' | 'cycling' | 'foot'

export interface RouteLeg {
  distance: number // meters
  duration: number // seconds
  hasUturn: boolean
}

export interface RouteResult {
  legs: RouteLeg[]
  totalDistance: number
  totalDuration: number
  geometry: [number, number][] // [lat, lng] pairs for polyline
}

export interface RouteTableResult {
  distanceKm: number[][]
  durationMinutes: number[][]
  source: 'osrm-table'
}

const OSRM_HOST = 'https://router.project-osrm.org'
const OSRM_BASE = `${OSRM_HOST}/route/v1`
const OSRM_TABLE_BASE = `${OSRM_HOST}/table/v1`

// OSRM demo only has driving profile — recalculate duration by mode
const AVG_SPEED: Record<TransportMode, number> = {
  driving: 40,  // km/h — rural Vietnamese roads
  cycling: 15,
  foot: 5,
}

interface OsrmStep {
  maneuver?: { type?: string }
}

interface OsrmLeg {
  distance?: number
  steps?: OsrmStep[]
}

interface OsrmRoute {
  distance?: number
  legs?: OsrmLeg[]
  geometry?: { coordinates?: [number, number][] }
}

interface OsrmResponse {
  code?: string
  routes?: OsrmRoute[]
}

interface OsrmTableResponse {
  code?: string
  distances?: unknown
  durations?: unknown
}

type TableFetcher = (url: string) => Promise<OsrmTableResponse>

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1)} km`
}

export function formatDuration(seconds: number): string {
  const mins = Math.round(seconds / 60)
  if (mins <= 0) return '< 1 phút'
  if (mins < 60) return `${mins} phút`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m > 0 ? `${h} giờ ${m} phút` : `${h} giờ`
}

export function buildRouteUrl(coords: [number, number][]): string {
  const coordStr = coords.map(([lat, lng]) => `${lng},${lat}`).join(';')
  return `${OSRM_BASE}/car/${coordStr}?overview=full&geometries=geojson&steps=true&continue_straight=true`
}

export function buildTableUrl(
  coords: [number, number][],
  _mode: TransportMode = 'driving',
): string {
  const coordStr = coords.map(([lat, lng]) => `${lng},${lat}`).join(';')
  return `${OSRM_TABLE_BASE}/car/${coordStr}?annotations=distance,duration`
}

export function parseRouteResponse(
  response: OsrmResponse,
  mode: TransportMode = 'driving',
): RouteResult | null {
  if (response?.code !== 'Ok' || !Array.isArray(response.routes) || !response.routes.length) return null

  const route = response.routes[0]
  if (!route || !Array.isArray(route.legs) || !Array.isArray(route.geometry?.coordinates)) return null

  const speed = AVG_SPEED[mode]
  const legs: RouteLeg[] = []
  for (const leg of route.legs) {
    const distance = Number(leg.distance)
    if (!Number.isFinite(distance) || distance < 0) return null
    const steps = Array.isArray(leg.steps) ? leg.steps : []
    legs.push({
      distance,
      duration: (distance / 1000 / speed) * 3600,
      hasUturn: steps.some(step => step?.maneuver?.type === 'uturn'),
    })
  }

  const geometry: [number, number][] = []
  for (const coordinate of route.geometry.coordinates) {
    if (!Array.isArray(coordinate) || coordinate.length < 2) return null
    const [lng, lat] = coordinate
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
    geometry.push([lat, lng])
  }

  const totalDistance = Number(route.distance)
  if (!Number.isFinite(totalDistance) || totalDistance < 0) return null
  return {
    legs,
    totalDistance,
    totalDuration: (totalDistance / 1000 / speed) * 3600,
    geometry,
  }
}

export function parseTableResponse(
  response: OsrmTableResponse,
  mode: TransportMode = 'driving',
): RouteTableResult | null {
  if (
    response?.code !== 'Ok'
    || !Array.isArray(response.distances)
    || !Array.isArray(response.durations)
    || response.distances.length === 0
    || response.durations.length !== response.distances.length
  ) {
    return null
  }

  const size = response.distances.length
  const distanceKm: number[][] = []
  const durationMinutes: number[][] = []
  for (let rowIndex = 0; rowIndex < size; rowIndex += 1) {
    const distanceRow = response.distances[rowIndex]
    const durationRow = response.durations[rowIndex]
    if (
      !Array.isArray(distanceRow)
      || !Array.isArray(durationRow)
      || distanceRow.length !== size
      || durationRow.length !== size
    ) {
      return null
    }

    const parsedDistances: number[] = []
    const parsedDurations: number[] = []
    for (let columnIndex = 0; columnIndex < size; columnIndex += 1) {
      const distance = distanceRow[columnIndex]
      const duration = durationRow[columnIndex]
      if (
        typeof distance !== 'number'
        || !Number.isFinite(distance)
        || distance < 0
        || (
          duration !== null
          && (
            typeof duration !== 'number'
            || !Number.isFinite(duration)
            || duration < 0
          )
        )
      ) {
        return null
      }

      const kilometers = distance / 1000
      parsedDistances.push(kilometers)
      parsedDurations.push(
        mode === 'driving' && duration !== null
          ? duration / 60
          : (kilometers / AVG_SPEED[mode]) * 60,
      )
    }
    distanceKm.push(parsedDistances)
    durationMinutes.push(parsedDurations)
  }

  return { distanceKm, durationMinutes, source: 'osrm-table' }
}

export async function fetchRouteTable(
  coords: [number, number][],
  mode: TransportMode = 'driving',
  fetcher?: TableFetcher,
): Promise<RouteTableResult | null> {
  if (coords.length < 2) return null
  if (import.meta.server && !fetcher) return null

  const request = fetcher
    ?? ((url: string) => $fetch<OsrmTableResponse>(url))
  try {
    const response = await request(buildTableUrl(coords, mode))
    return parseTableResponse(response, mode)
  } catch {
    return null
  }
}

export async function fetchRoute(
  coords: [number, number][], // [lat, lng] pairs
  mode: TransportMode = 'driving'
): Promise<RouteResult | null> {
  if (import.meta.server) return null
  if (coords.length < 2) return null

  try {
    const response = await $fetch<OsrmResponse>(buildRouteUrl(coords))
    return parseRouteResponse(response, mode)
  } catch {
    return null
  }
}

export function useRouting() {
  return { fetchRoute, fetchRouteTable, formatDistance, formatDuration }
}
