import type { FilterSet, Intent, SearchViewState } from '~/types/publicExperience'

const MAX_QUERY = 120
const INTENTS = new Set<Intent>(['place', 'service', 'event', 'story', 'all'])
const AREA_ID = /^[a-z0-9][a-z0-9-]{0,63}$/i
function bounded(value: unknown, max: number) { return typeof value === 'string' ? value.trim().slice(0, max) : '' }

export function serializeSearchViewState(state: Partial<SearchViewState>): string {
  const params = new URLSearchParams()
  const query = bounded(state.query, MAX_QUERY); if (query) params.set('query', query)
  if (state.intent && INTENTS.has(state.intent)) params.set('intent', state.intent)
  if (state.area?.id && AREA_ID.test(state.area.id)) params.set('area', state.area.id)
  if (state.filters && Object.keys(state.filters).length) {
    const filters: FilterSet = {}
    for (const key of Object.keys(state.filters).sort().slice(0, 20)) {
      const value = state.filters[key]
      if (typeof value === 'string') filters[key] = bounded(value, 80)
      else if (typeof value === 'boolean' || typeof value === 'number') filters[key] = value
      else if (Array.isArray(value)) filters[key] = value.filter(v => typeof v === 'string').map(v => bounded(v, 40)).filter(Boolean).slice(0, 20)
    }
    if (Object.keys(filters).length) params.set('filters', JSON.stringify(filters))
  }
  // Deliberately omit raw center coordinates; area is the privacy-safe fallback.
  if (state.viewport && Number.isFinite(state.viewport.zoom)) {
    const z = Math.max(0, Math.min(22, Math.round(state.viewport.zoom)))
    const [lng, lat] = state.viewport.center
    if (Number.isFinite(lng) && Number.isFinite(lat)) {
      const n = 2 ** z
      const x = Math.floor(((lng + 180) / 360) * n)
      const y = Math.floor((1 - Math.asinh(Math.tan((lat * Math.PI) / 180)) / Math.PI) / 2 * n)
      params.set('viewport', `${z}/${Math.max(0, Math.min(n - 1, x))}/${Math.max(0, Math.min(n - 1, y))}`)
    }
  }
  return params.toString()
}

export function parseSearchViewState(input: string | URLSearchParams | Record<string, unknown>): SearchViewState {
  const p = input instanceof URLSearchParams ? input : typeof input === 'string' ? new URLSearchParams(input.replace(/^\?/, '')) : new URLSearchParams(Object.entries(input).flatMap(([k, v]) => [[k, String(v)]]))
  const intent = INTENTS.has(p.get('intent') as Intent) ? p.get('intent') as Intent : 'all'
  let filters: FilterSet = {}
  try {
    const parsed = JSON.parse(p.get('filters') || '{}')
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      for (const [key, value] of Object.entries(parsed).slice(0, 20)) {
        if (!/^[a-z][a-z0-9_-]{0,31}$/i.test(key)) continue
        if (typeof value === 'string') filters[key] = bounded(value, 80)
        else if (typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value))) filters[key] = value
        else if (Array.isArray(value)) filters[key] = value.filter(v => typeof v === 'string').map(v => bounded(v, 40)).filter(Boolean).slice(0, 20)
      }
    }
  } catch { /* malformed URL state is ignored */ }
  const areaId = bounded(p.get('area'), 64)
  const validArea = AREA_ID.test(areaId) ? areaId : ''
  let viewport: SearchViewState['viewport']
  const tile = /^([0-9]{1,2})\/([0-9]+)\/([0-9]+)$/.exec(p.get('viewport') || '')
  if (tile) {
    const z = Number(tile[1]); const n = 2 ** z; const x = Number(tile[2]); const y = Number(tile[3])
    if (z <= 22 && x < n && y < n) {
      const lng = (x + 0.5) / n * 360 - 180
      const lat = 180 / Math.PI * Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 0.5) / n)))
      viewport = { center: [lng, lat], zoom: z }
    }
  }
  return { query: bounded(p.get('query'), MAX_QUERY), intent, filters, ...(validArea ? { area: { id: validArea } } : {}), ...(viewport ? { viewport } : {}), panel: 'list' }
}
