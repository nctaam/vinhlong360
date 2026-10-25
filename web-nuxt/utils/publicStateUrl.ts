import type { FilterSet, Intent, MapViewport, SearchViewState } from '~/types/publicExperience'

const MAX_QUERY = 120
const INTENTS = new Set<Intent>(['place', 'service', 'event', 'story', 'all'])
const AREA_ID = /^[a-z0-9][a-z0-9-]{0,63}$/i
const SORTED_FILTER_KEYS = ['category', 'distance', 'month', 'price', 'season', 'sort', 'type'] as const
const FILTER_KEYS = new Set<string>(SORTED_FILTER_KEYS)
const RE_VIEWPORT_TILE = /^([0-9]{1,2})\/([0-9]+)\/([0-9]+)$/
const MAX_FILTERS = 20
const MAX_MERCATOR_LAT = 85.05112878
const DEG_TO_RAD = Math.PI / 180
const RAD_TO_DEG = 180 / Math.PI
function bounded(value: unknown, max: number) { return typeof value === 'string' ? value.trim().slice(0, max) : '' }

type ViewportTile = { z: number; x: number; y: number }
export type SearchViewStateParseResult = { state: SearchViewState; malformed: boolean }
export type ViewportTileBounds = { west: number; east: number; south: number; north: number }

function viewportTile(viewport?: MapViewport): ViewportTile | undefined {
  if (!viewport || !Number.isFinite(viewport.zoom)) return undefined
  const [lng, rawLat] = viewport.center
  if (!Number.isFinite(lng) || !Number.isFinite(rawLat)) return undefined
  const z = Math.max(0, Math.min(22, Math.round(viewport.zoom)))
  const n = 2 ** z
  const lat = Math.max(-MAX_MERCATOR_LAT, Math.min(MAX_MERCATOR_LAT, rawLat))
  const x = Math.floor(((lng + 180) / 360) * n)
  const y = Math.floor((1 - Math.asinh(Math.tan(lat * DEG_TO_RAD)) / Math.PI) / 2 * n)
  return {
    z,
    x: Math.max(0, Math.min(n - 1, x)),
    y: Math.max(0, Math.min(n - 1, y)),
  }
}

function tileCenter(tile: ViewportTile): MapViewport {
  const n = 2 ** tile.z
  const lng = (tile.x + 0.5) / n * 360 - 180
  const lat = RAD_TO_DEG * Math.atan(Math.sinh(Math.PI * (1 - 2 * (tile.y + 0.5) / n)))
  return { center: [lng, lat], zoom: tile.z }
}

function sanitizeFilterValue(value: unknown): { value?: FilterSet[string]; malformed: boolean } {
  if (typeof value === 'string') {
    const sanitized = bounded(value, 80)
    return sanitized ? { value: sanitized, malformed: sanitized !== value } : { malformed: sanitized !== value }
  }
  if (typeof value === 'boolean') return { value, malformed: false }
  if (typeof value === 'number') return Number.isFinite(value) ? { value, malformed: false } : { malformed: true }
  if (Array.isArray(value)) {
    const sanitized: string[] = []
    let malformed = false
    for (let i = 0; i < value.length; i++) {
      const item = value[i]
      if (typeof item !== 'string') {
        malformed = true
        continue
      }
      const b = bounded(item, 40)
      if (!b) {
        malformed = true
        continue
      }
      if (sanitized.length < 20) {
        if (b !== value[sanitized.length]) malformed = true
        sanitized.push(b)
      } else {
        malformed = true
        break
      }
    }
    if (sanitized.length !== value.length) malformed = true
    return sanitized.length ? { value: sanitized, malformed } : { malformed }
  }
  return { malformed: true }
}

function sanitizeFilters(input: unknown): { filters: FilterSet; malformed: boolean } {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { filters: {}, malformed: true }
  const entries = Object.entries(input)
  const filters: FilterSet = {}
  let malformed = entries.length > MAX_FILTERS
  const limit = Math.min(entries.length, MAX_FILTERS)
  for (let i = 0; i < limit; i++) {
    const [key, value] = entries[i]!
    if (!FILTER_KEYS.has(key)) {
      malformed = true
      continue
    }
    const sanitized = sanitizeFilterValue(value)
    if (sanitized.value !== undefined) filters[key] = sanitized.value
    if (sanitized.malformed) malformed = true
  }
  return { filters, malformed }
}

export function serializeSearchViewState(state: Partial<SearchViewState>): string {
  const params = new URLSearchParams()
  const query = bounded(state.query, MAX_QUERY)
  if (query) params.set('query', query)
  if (state.intent && state.intent !== 'all' && INTENTS.has(state.intent)) params.set('intent', state.intent)
  if (state.area?.id && AREA_ID.test(state.area.id)) params.set('area', state.area.id)
  const rawFilters = state.filters
  if (rawFilters) {
    const filters: FilterSet = {}
    let hasValidFilter = false
    for (let i = 0; i < SORTED_FILTER_KEYS.length; i++) {
      const key = SORTED_FILTER_KEYS[i]!
      if (!Object.prototype.hasOwnProperty.call(rawFilters, key)) continue
      const sanitized = sanitizeFilterValue(rawFilters[key])
      if (sanitized.value !== undefined) {
        filters[key] = sanitized.value
        hasValidFilter = true
      }
    }
    if (hasValidFilter) params.set('filters', JSON.stringify(filters))
  }
  // Deliberately omit raw center coordinates; area is the privacy-safe fallback.
  const tile = viewportTile(state.viewport)
  if (tile) params.set('viewport', `${tile.z}/${tile.x}/${tile.y}`)
  return params.toString()
}

function toSearchParams(input: string | URLSearchParams | Record<string, unknown>): URLSearchParams {
  if (input instanceof URLSearchParams) return input
  if (typeof input === 'string') return new URLSearchParams(input.startsWith('?') ? input.slice(1) : input)
  const params = new URLSearchParams()
  for (const key in input) {
    if (Object.prototype.hasOwnProperty.call(input, key)) {
      params.append(key, String(input[key]))
    }
  }
  return params
}

export function parseSearchViewStateWithMeta(input: string | URLSearchParams | Record<string, unknown>): SearchViewStateParseResult {
  const p = toSearchParams(input)
  const rawIntent = p.get('intent')
  const intent = rawIntent && INTENTS.has(rawIntent as Intent) ? (rawIntent as Intent) : 'all'
  let malformed = Boolean(rawIntent && intent === 'all' && rawIntent !== 'all')
  let filters: FilterSet = {}
  const rawFilters = p.get('filters')
  if (rawFilters !== null) {
    try {
      const sanitized = sanitizeFilters(JSON.parse(rawFilters || '{}'))
      filters = sanitized.filters
      malformed ||= sanitized.malformed
    } catch {
      malformed = true
    }
  }
  const rawArea = p.get('area')
  const areaId = bounded(rawArea, 64)
  const validArea = AREA_ID.test(areaId) ? areaId : ''
  if (rawArea !== null && !validArea) malformed = true
  let viewport: SearchViewState['viewport']
  const viewportParam = p.get('viewport') || ''
  const tile = RE_VIEWPORT_TILE.exec(viewportParam)
  if (tile) {
    const z = Number(tile[1]); const n = 2 ** z; const x = Number(tile[2]); const y = Number(tile[3])
    if (z <= 22 && x < n && y < n) {
      viewport = tileCenter({ z, x, y })
    } else {
      malformed = true
    }
  } else if (viewportParam) {
    malformed = true
  }
  return {
    state: { query: bounded(p.get('query'), MAX_QUERY), intent, filters, ...(validArea ? { area: { id: validArea } } : {}), ...(viewport ? { viewport } : {}), panel: 'list' },
    malformed,
  }
}

export function parseSearchViewState(input: string | URLSearchParams | Record<string, unknown>): SearchViewState {
  return parseSearchViewStateWithMeta(input).state
}

export function viewportTileBounds(viewport: MapViewport): ViewportTileBounds {
  const tile = viewportTile(viewport)
  if (!tile) return { west: -180, east: 180, south: -MAX_MERCATOR_LAT, north: MAX_MERCATOR_LAT }
  const n = 2 ** tile.z
  const west = tile.x / n * 360 - 180
  const east = (tile.x + 1) / n * 360 - 180
  const north = RAD_TO_DEG * Math.atan(Math.sinh(Math.PI * (1 - 2 * tile.y / n)))
  const south = RAD_TO_DEG * Math.atan(Math.sinh(Math.PI * (1 - 2 * (tile.y + 1) / n)))
  return { west, east, south, north }
}
