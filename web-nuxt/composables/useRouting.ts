export type TransportMode = 'driving' | 'cycling' | 'foot'

export interface RouteLeg {
  distance: number // meters
  duration: number // seconds
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

export async function fetchRoute(
  coords: [number, number][], // [lat, lng] pairs
  mode: TransportMode = 'driving'
): Promise<RouteResult | null> {
  if (import.meta.server) return null
  if (coords.length < 2) return null

  const coordStr = coords.map(([lat, lng]) => `${lng},${lat}`).join(';')
  const url = `${OSRM_BASE}/car/${coordStr}?overview=full&geometries=geojson&steps=false`

  try {
    const res = await $fetch<any>(url)
    if (res.code !== 'Ok' || !res.routes?.length) return null

    const route = res.routes[0]
    const speed = AVG_SPEED[mode]

    const legs: RouteLeg[] = route.legs.map((leg: { distance: number }) => ({
      distance: leg.distance,
      duration: (leg.distance / 1000 / speed) * 3600,
    }))

    const geometry: [number, number][] = route.geometry.coordinates.map(
      ([lng, lat]: [number, number]) => [lat, lng]
    )

    const totalDistance = route.distance
    return {
      legs,
      totalDistance,
      totalDuration: (totalDistance / 1000 / speed) * 3600,
      geometry,
    }
  } catch {
    return null
  }
}

export function useRouting() {
  return { fetchRoute, formatDistance, formatDuration }
}
