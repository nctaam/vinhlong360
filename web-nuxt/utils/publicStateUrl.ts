import type { FilterSet, Intent, MapViewport, SearchViewState } from '~/types/publicExperience'

const MAX_QUERY = 120
const INTENTS = new Set<Intent>(['place', 'service', 'event', 'story', 'all'])
const AREA_ID = /^[a-z0-9][a-z0-9-]{0,63}$/i
const FILTER_KEYS = new Set(['type', 'category', 'sort', 'distance', 'price', 'season', 'month'])
const MAX_FILTERS = 20
const MAX_MERCATOR_LAT = 85.05112878
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
  const y = Math.floor((1 - Math.asinh(Math.tan((lat * Math.PI) / 180)) / Math.PI) / 2 * n)
  return {
    z,
    x: Math.max(0, Math.min(n - 1, x)),
    y: Math.max(0, Math.min(n - 1, y)),
  }
}

function tileCenter(tile: ViewportTile): MapViewport {
  const n = 2 ** tile.z
  const lng = (tile.x + 0.5) / n * 360 - 180
  const lat = 180 / Math.PI * Math.atan(Math.sinh(Math.PI * (1 - 2 * (tile.y + 0.5) / n)))
  return { center: [lng, lat], zoom: tile.z }
}

function sanitizeFilterValue(value: unknown): { value?: FilterSet[string]; malformed: boolean } {
  if (typeof value === 'string') {
    const sanitized = bounded(value, 80)
    return { ...(sanitized ? { value: sanitized } : {}), malformed: sanitized !== value }
  }
  if (typeof value === 'boolean') return { value, malformed: false }
  if (typeof value === 'number') return Number.isFinite(value) ? { value, malformed: false } : { malformed: true }
  if (Array.isArray(value)) {
    const sanitized = value
      .filter(item => typeof item === 'string')
      .map(item => bounded(item, 40))
      .filter(Boolean)
      .slice(0, 20)
    const malformed = sanitized.length !== value.length
      || sanitized.some((item, index) => item !== value[index])
    return { ...(sanitized.length ? { value: sanitized } : {}), malformed }
  }
  return { malformed: true }
}

function sanitizeFilters(input: unknown): { filters: FilterSet; malformed: boolean } {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { filters: {}, malformed: true }
  const entries = Object.entries(input)
  const filters: FilterSet = {}
  let malformed = entries.length > MAX_FILTERS
  for (const [key, value] of entries.slice(0, MAX_FILTERS)) {
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
  const query = bounded(state.query, MAX_QUERY); if (query) params.set('query', query)
  if (state.intent && state.intent !== 'all' && INTENTS.has(state.intent)) params.set('intent', state.intent)
  if (state.area?.id && AREA_ID.test(state.area.id)) params.set('area', state.area.id)
  if (state.filters && Object.keys(state.filters).length) {
    const filters: FilterSet = {}
    for (const key of Object.keys(state.filters).sort().filter(key => FILTER_KEYS.has(key)).slice(0, MAX_FILTERS)) {
      const sanitized = sanitizeFilterValue(state.filters[key])
      if (sanitized.value !== undefined) filters[key] = sanitized.value
    }
    if (Object.keys(filters).length) params.set('filters', JSON.stringify(filters))
  }
  // Deliberately omit raw center coordinates; area is the privacy-safe fallback.
  const tile = viewportTile(state.viewport)
  if (tile) params.set('viewport', `${tile.z}/${tile.x}/${tile.y}`)
  return params.toString()
}

export function parseSearchViewStateWithMeta(input: string | URLSearchParams | Record<string, unknown>): SearchViewStateParseResult {
  const p = input instanceof URLSearchParams ? input : typeof input === 'string' ? new URLSearchParams(input.replace(/^\?/, '')) : new URLSearchParams(Object.entries(input).flatMap(([k, v]) => [[k, String(v)]]))
  const intent = INTENTS.has(p.get('intent') as Intent) ? p.get('intent') as Intent : 'all'
  let malformed = Boolean(p.get('intent') && intent === 'all' && p.get('intent') !== 'all')
  let filters: FilterSet = {}
  if (p.has('filters')) {
    try {
      const sanitized = sanitizeFilters(JSON.parse(p.get('filters') || '{}'))
      filters = sanitized.filters
      malformed ||= sanitized.malformed
    } catch {
      malformed = true
    }
  }
  const areaId = bounded(p.get('area'), 64)
  const validArea = AREA_ID.test(areaId) ? areaId : ''
  if (p.has('area') && !validArea) malformed = true
  let viewport: SearchViewState['viewport']
  const viewportParam = p.get('viewport') || ''
  const tile = /^([0-9]{1,2})\/([0-9]+)\/([0-9]+)$/.exec(viewportParam)
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
  const north = 180 / Math.PI * Math.atan(Math.sinh(Math.PI * (1 - 2 * tile.y / n)))
  const south = 180 / Math.PI * Math.atan(Math.sinh(Math.PI * (1 - 2 * (tile.y + 1) / n)))
  return { west, east, south, north }
}
