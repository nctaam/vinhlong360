import { computed, getCurrentScope, onScopeDispose, ref, watch, type Ref } from 'vue'
import type { AreaRef, FilterSet, Intent, MapViewport, SearchViewState } from '~/types/publicExperience'
import { parseSearchViewState, parseSearchViewStateWithMeta, serializeSearchViewState } from '~/utils/publicStateUrl'

const SESSION_KEY = 'vinhlong360:public-search-view:v1'
const URL_WRITE_DELAY = 200
const INTENTS = new Set<Intent>(['place', 'service', 'event', 'story', 'all'])

export type SearchViewPanel = SearchViewState['panel']
export type SearchViewRuntimeState = SearchViewState & { scrollKey?: string }

type PrivateSearchState = Pick<SearchViewRuntimeState, 'selectedId' | 'panel' | 'scrollKey'>
type HistoryMode = 'push' | 'replace'
type PublicSearchHistoryState = Record<string, unknown> & {
  publicSearchPrivate?: Partial<PrivateSearchState>
  publicSearchCommittedViewport?: MapViewport | null
  publicSearchUrl?: string
}

function firstValue(value: string | null) {
  return typeof value === 'string' ? value : ''
}

function safeUrl(input: string) {
  try {
    return new URL(input, 'https://vinhlong360.local')
  } catch {
    return new URL('/tim-kiem', 'https://vinhlong360.local')
  }
}

function legacyCompatibleParams(url: URL) {
  const params = new URLSearchParams(url.search)
  if (!params.has('query') && params.has('q')) params.set('query', firstValue(params.get('q')))
  if (!params.has('area') && params.has('vung')) params.set('area', firstValue(params.get('vung')))
  if (!params.has('filters') && params.has('type')) {
    const types = firstValue(params.get('type')).split(',').map(value => value.trim()).filter(Boolean)
    if (types.length) params.set('filters', JSON.stringify({ type: types }))
  }
  return params
}

function normalizePrivateState(value: unknown): PrivateSearchState | undefined {
  if (!value || typeof value !== 'object') return undefined
  const parsed = value as Partial<PrivateSearchState>
  return {
    ...(typeof parsed.selectedId === 'string' && parsed.selectedId ? { selectedId: parsed.selectedId } : {}),
    panel: parsed.panel === 'map' ? 'map' : 'list',
    ...(typeof parsed.scrollKey === 'string' && parsed.scrollKey ? { scrollKey: parsed.scrollKey } : {}),
  }
}

function readPrivateState(): PrivateSearchState {
  if (!import.meta.client) return { panel: 'list' }
  try {
    return normalizePrivateState(JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}')) || { panel: 'list' }
  } catch {
    return { panel: 'list' }
  }
}

function privateStateFromHistory(value: unknown) {
  if (!value || typeof value !== 'object') return undefined
  return normalizePrivateState((value as PublicSearchHistoryState).publicSearchPrivate)
}

function sameViewport(left?: MapViewport, right?: MapViewport) {
  if (!left || !right) return left === right
  return left.zoom === right.zoom && left.center[0] === right.center[0] && left.center[1] === right.center[1]
}

function sanitizedViewport(viewport?: MapViewport) {
  if (!viewport) return undefined
  return parseSearchViewState(serializeSearchViewState({ viewport })).viewport
}

function committedViewportFromHistory(value: unknown, fallback?: MapViewport) {
  if (!value || typeof value !== 'object') return fallback
  const historyState = value as PublicSearchHistoryState
  if (!Object.prototype.hasOwnProperty.call(historyState, 'publicSearchCommittedViewport')) return fallback
  return historyState.publicSearchCommittedViewport ? sanitizedViewport(historyState.publicSearchCommittedViewport) : undefined
}

function publicStateFromUrl(input: string) {
  const url = safeUrl(input)
  const params = legacyCompatibleParams(url)
  const inspected = parseSearchViewStateWithMeta(params)
  return { url, params, parsed: inspected.state, malformed: inspected.malformed }
}

function publicUrl(pathname: string, state: SearchViewRuntimeState, source?: string) {
  const params = new URLSearchParams(serializeSearchViewState(state))
  const query = params.get('query')
  params.delete('query')
  if (query) params.set('q', query)
  if (source === 'saved') params.set('source', 'saved')
  const search = params.toString()
  return `${pathname}${search ? `?${search}` : ''}`
}

export function useSearchViewState(input?: string) {
  const route = input === undefined ? useRoute() : null
  const initialInput = input ?? route?.fullPath ?? '/tim-kiem'
  const initial = publicStateFromUrl(initialInput)
  const browserUrl = import.meta.client ? safeUrl(window.location.pathname + window.location.search) : undefined
  const initialUsesBrowserEntry = input === undefined
    && browserUrl?.pathname === initial.url.pathname
    && browserUrl.search === initial.url.search
  const historyCandidate = initialUsesBrowserEntry ? window.history.state as PublicSearchHistoryState | null : null
  const initialEntryUrl = `${initial.url.pathname}${initial.url.search}`
  const initialHistoryState = historyCandidate?.publicSearchUrl === initialEntryUrl ? historyCandidate : undefined
  const privateState = privateStateFromHistory(initialHistoryState) || readPrivateState()
  const state = ref<SearchViewRuntimeState>({
    ...initial.parsed,
    ...privateState,
    panel: privateState.panel,
  }) as Ref<SearchViewRuntimeState>
  const committedViewport = ref<MapViewport | undefined>(committedViewportFromHistory(initialHistoryState, initial.parsed.viewport))
  const url = ref(publicUrl(initial.url.pathname, state.value, initial.url.searchParams.get('source') || undefined))
  const hasMalformedUrl = ref(initial.malformed)
  const viewportPending = ref(!sameViewport(state.value.viewport, committedViewport.value))
  const currentPath = ref(initial.url.pathname)
  const sourceMode = ref(initial.url.searchParams.get('source') === 'saved' ? 'saved' : '')
  let viewportTimer: ReturnType<typeof setTimeout> | null = null

  function currentPrivateState(): PrivateSearchState {
    return {
      ...(state.value.selectedId ? { selectedId: state.value.selectedId } : {}),
      panel: state.value.panel,
      ...(state.value.scrollKey ? { scrollKey: state.value.scrollKey } : {}),
    }
  }

  function historyStateWithSearchState(base: unknown, privateValue = currentPrivateState(), entryUrl = url.value): PublicSearchHistoryState {
    const historyState = base && typeof base === 'object' ? base as Record<string, unknown> : {}
    return {
      ...historyState,
      publicSearchPrivate: privateValue,
      publicSearchCommittedViewport: sanitizedViewport(committedViewport.value) || null,
      publicSearchUrl: entryUrl,
    }
  }

  function persistPrivateSession(privateValue: PrivateSearchState) {
    if (!import.meta.client) return
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(privateValue))
  }

  function persistPrivate() {
    if (!import.meta.client) return
    const privateValue = currentPrivateState()
    persistPrivateSession(privateValue)
    const entryUrl = window.location.pathname + window.location.search
    window.history.replaceState(historyStateWithSearchState(window.history.state, privateValue, entryUrl), '', window.location.href)
  }

  function writeUrl(mode: HistoryMode) {
    url.value = publicUrl(currentPath.value, state.value, sourceMode.value || undefined)
    if (!import.meta.client) return
    const privateValue = currentPrivateState()
    persistPrivateSession(privateValue)
    const nextState = historyStateWithSearchState(window.history.state, privateValue)
    if (mode === 'push') window.history.pushState(nextState, '', url.value)
    else window.history.replaceState(nextState, '', url.value)
  }

  function restorePublic(inputValue: string, historyState?: unknown) {
    const next = publicStateFromUrl(inputValue)
    currentPath.value = next.url.pathname
    sourceMode.value = next.url.searchParams.get('source') === 'saved' ? 'saved' : ''
    state.value = { ...next.parsed, panel: 'list' }
    committedViewport.value = committedViewportFromHistory(historyState, next.parsed.viewport)
    url.value = publicUrl(currentPath.value, state.value, sourceMode.value || undefined)
    hasMalformedUrl.value = next.malformed
    viewportPending.value = !sameViewport(state.value.viewport, committedViewport.value)
    restoreBackStack(historyState)
  }

  function setQuery(query: string) {
    state.value = { ...state.value, query: query.trim().slice(0, 120) }
    writeUrl('push')
  }

  function setIntent(intent: Intent) {
    state.value = { ...state.value, intent: INTENTS.has(intent) ? intent : 'all' }
    writeUrl('push')
  }

  function setFilter(key: string, value: FilterSet[string] | undefined) {
    const filters = { ...state.value.filters }
    if (value === undefined || value === '' || value === 'all' || (Array.isArray(value) && value.length === 0)) delete filters[key]
    else filters[key] = value
    state.value = { ...state.value, filters }
    writeUrl('push')
  }

  function setArea(area?: AreaRef | string) {
    const normalized = typeof area === 'string' ? { id: area } : area
    state.value = { ...state.value, ...(normalized?.id ? { area: normalized } : {} ) }
    if (!normalized?.id) delete state.value.area
    writeUrl('push')
  }

  function setViewport(viewport: MapViewport) {
    const normalized: MapViewport = {
      center: [Number(viewport.center[0]), Number(viewport.center[1])],
      zoom: Number(viewport.zoom),
    }
    if (sameViewport(state.value.viewport, normalized) && viewportPending.value) return
    state.value = { ...state.value, viewport: normalized }
    viewportPending.value = true
    if (viewportTimer) clearTimeout(viewportTimer)
    viewportTimer = setTimeout(() => {
      viewportTimer = null
      writeUrl('replace')
    }, URL_WRITE_DELAY)
  }

  function commitViewport(viewport?: MapViewport) {
    if (viewport) {
      state.value = {
        ...state.value,
        viewport: { center: [Number(viewport.center[0]), Number(viewport.center[1])], zoom: Number(viewport.zoom) },
      }
    }
    committedViewport.value = state.value.viewport
    viewportPending.value = false
    if (viewportTimer) {
      clearTimeout(viewportTimer)
      viewportTimer = null
    }
    writeUrl('push')
  }

  function selectResult(selectedId?: string) {
    state.value = { ...state.value, ...(selectedId ? { selectedId } : {}) }
    if (!selectedId) delete state.value.selectedId
    persistPrivate()
  }

  function openPanel(panel: SearchViewPanel) {
    state.value = { ...state.value, panel }
    persistPrivate()
  }

  function setScrollKey(scrollKey?: string) {
    state.value = { ...state.value, ...(scrollKey ? { scrollKey } : {}) }
    if (!scrollKey) delete state.value.scrollKey
    persistPrivate()
  }

  function restoreBackStack(historyState?: unknown) {
    const currentHistoryState = historyState === undefined && import.meta.client ? window.history.state : historyState
    const restored = privateStateFromHistory(currentHistoryState) || readPrivateState()
    const { selectedId: _selectedId, scrollKey: _scrollKey, ...publicState } = state.value
    state.value = {
      ...publicState,
      ...restored,
      panel: restored.panel,
    }
    persistPrivateSession(restored)
    return state.value
  }

  function urlForQuery(query: string) {
    return publicUrl(currentPath.value, { ...state.value, query: query.trim().slice(0, 120) }, sourceMode.value || undefined)
  }

  if (route) {
    watch(() => route.fullPath, fullPath => restorePublic(fullPath, import.meta.client ? window.history.state : undefined))
  }

  if (import.meta.client) {
    if (initialUsesBrowserEntry) {
      const entryUrl = window.location.pathname + window.location.search
      window.history.replaceState(historyStateWithSearchState(window.history.state, privateState, entryUrl), '', window.location.href)
    }
    const onPopState = (event: PopStateEvent) => restorePublic(window.location.pathname + window.location.search, event.state)
    window.addEventListener('popstate', onPopState)
    if (getCurrentScope()) onScopeDispose(() => window.removeEventListener('popstate', onPopState))
  }

  if (getCurrentScope()) {
    onScopeDispose(() => {
      if (viewportTimer) clearTimeout(viewportTimer)
    })
  }

  return {
    state,
    url,
    hasMalformedUrl,
    malformedNotice: computed(() => hasMalformedUrl.value ? 'Một phần trạng thái tìm kiếm không hợp lệ đã được đưa về mặc định an toàn.' : ''),
    viewportPending,
    committedViewport,
    setQuery,
    setIntent,
    setFilter,
    setArea,
    setViewport,
    commitViewport,
    selectResult,
    openPanel,
    setScrollKey,
    restoreBackStack,
    urlForQuery,
  }
}
