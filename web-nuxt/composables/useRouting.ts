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

const OSRM_BASE = 'https://router.project-osrm.org/route/v1'

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
  return { fetchRoute, formatDistance, formatDuration }
}
