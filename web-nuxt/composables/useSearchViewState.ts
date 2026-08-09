import { computed, getCurrentScope, onScopeDispose, ref, watch, type Ref } from 'vue'
import type { AreaRef, FilterSet, Intent, MapViewport, SearchViewState } from '~/types/publicExperience'
import { parseSearchViewState, parseSearchViewStateWithMeta, serializeSearchViewState } from '~/utils/publicStateUrl'

const SESSION_KEY = 'vinhlong360:public-search-entries:v2'
const URL_WRITE_DELAY = 200
const INTENTS = new Set<Intent>(['place', 'service', 'event', 'story', 'all'])

export type SearchViewPanel = SearchViewState['panel']
export type SearchViewRuntimeState = SearchViewState & { scrollKey?: string }

type PrivateSearchState = Pick<SearchViewRuntimeState, 'selectedId' | 'panel' | 'scrollKey'>
type HistoryMode = 'push' | 'replace'
type PublicSearchHistoryState = Record<string, unknown> & {
  publicSearchPrivate?: Partial<PrivateSearchState>
  publicSearchCommittedViewport?: MapViewport | null
  publicSearchViewportPending?: boolean
  publicSearchUrl?: string
}
type SearchEntrySnapshot = {
  url: string
  privateState: PrivateSearchState
  committedViewport: MapViewport | undefined
  viewportPending: boolean
}
type StoredSearchEntrySnapshot = Omit<SearchEntrySnapshot, 'committedViewport'> & { committedViewport: MapViewport | null }

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

function entryUrl(input: string) {
  const parsed = safeUrl(input)
  return `${parsed.pathname}${parsed.search}`
}

function entrySnapshotFromHistory(value: unknown, input: string, fallbackViewport?: MapViewport): SearchEntrySnapshot | undefined {
  if (!value || typeof value !== 'object') return undefined
  const historyState = value as PublicSearchHistoryState
  const targetUrl = entryUrl(input)
  if (historyState.publicSearchUrl !== targetUrl) return undefined
  const committedViewport = committedViewportFromHistory(historyState, fallbackViewport)
  const viewportPending = Object.prototype.hasOwnProperty.call(historyState, 'publicSearchViewportPending')
    ? historyState.publicSearchViewportPending === true
    : !sameViewport(fallbackViewport, committedViewport)
  return {
    url: targetUrl,
    privateState: privateStateFromHistory(historyState) || { panel: 'list' },
    committedViewport,
    viewportPending,
  }
}

function sessionEntryKey(value: unknown, input: string) {
  if (value && typeof value === 'object') {
    const position = (value as Record<string, unknown>).position
    if (typeof position === 'number' || typeof position === 'string') return `position:${position}`
  }
  return `url:${entryUrl(input)}`
}

function readSessionSnapshot(value: unknown, input: string): SearchEntrySnapshot | undefined {
  if (!import.meta.client) return undefined
  try {
    const stored = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}') as Record<string, StoredSearchEntrySnapshot>
    const snapshot = stored[sessionEntryKey(value, input)]
    if (!snapshot || snapshot.url !== entryUrl(input)) return undefined
    return {
      url: snapshot.url,
      privateState: normalizePrivateState(snapshot.privateState) || { panel: 'list' },
      committedViewport: snapshot.committedViewport ? sanitizedViewport(snapshot.committedViewport) : undefined,
      viewportPending: snapshot.viewportPending === true,
    }
  } catch {
    return undefined
  }
}

function persistSessionSnapshot(value: unknown, snapshot: SearchEntrySnapshot) {
  if (!import.meta.client) return
  try {
    const stored = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}') as Record<string, StoredSearchEntrySnapshot>
    stored[sessionEntryKey(value, snapshot.url)] = {
      ...snapshot,
      committedViewport: sanitizedViewport(snapshot.committedViewport) || null,
    }
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(stored))
  } catch {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({
      [sessionEntryKey(value, snapshot.url)]: {
        ...snapshot,
        committedViewport: sanitizedViewport(snapshot.committedViewport) || null,
      },
    }))
  }
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
  const initialSnapshot = entrySnapshotFromHistory(historyCandidate, initialInput, initial.parsed.viewport)
    || readSessionSnapshot(historyCandidate, initialInput)
  const privateState = initialSnapshot?.privateState || { panel: 'list' }
  const state = ref<SearchViewRuntimeState>({
    ...initial.parsed,
    ...privateState,
    panel: privateState.panel,
  }) as Ref<SearchViewRuntimeState>
  const committedViewport = ref<MapViewport | undefined>(initialSnapshot ? initialSnapshot.committedViewport : initial.parsed.viewport)
  const url = ref(publicUrl(initial.url.pathname, state.value, initial.url.searchParams.get('source') || undefined))
  const hasMalformedUrl = ref(initial.malformed)
  const viewportPending = ref(initialSnapshot?.viewportPending || false)
  const currentPath = ref(initial.url.pathname)
  const sourceMode = ref(initial.url.searchParams.get('source') === 'saved' ? 'saved' : '')
  let viewportTimer: ReturnType<typeof setTimeout> | null = null
  let plannedNavigation: SearchEntrySnapshot | undefined

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
      // Vue Router consults this field before its next push; keep pending replacements from being reverted.
      ...(Object.prototype.hasOwnProperty.call(historyState, 'current') ? { current: entryUrl } : {}),
      publicSearchPrivate: privateValue,
      publicSearchCommittedViewport: sanitizedViewport(committedViewport.value) || null,
      publicSearchViewportPending: viewportPending.value,
      publicSearchUrl: entryUrl,
    }
  }

  function currentEntrySnapshot(entryUrlValue = url.value): SearchEntrySnapshot {
    return {
      url: entryUrl(entryUrlValue),
      privateState: currentPrivateState(),
      committedViewport: sanitizedViewport(committedViewport.value),
      viewportPending: viewportPending.value,
    }
  }

  function persistPrivate() {
    if (!import.meta.client) return
    const privateValue = currentPrivateState()
    const currentUrl = window.location.pathname + window.location.search
    window.history.replaceState(historyStateWithSearchState(window.history.state, privateValue, currentUrl), '', window.location.href)
    persistSessionSnapshot(window.history.state, currentEntrySnapshot(currentUrl))
  }

  function stampCurrentEntry(entryUrlValue?: string) {
    if (!import.meta.client) return
    const targetUrl = entryUrlValue || window.location.pathname + window.location.search
    if (entryUrl(window.location.pathname + window.location.search) !== entryUrl(targetUrl)) return
    const privateValue = currentPrivateState()
    window.history.replaceState(historyStateWithSearchState(window.history.state, privateValue, entryUrl(targetUrl)), '', window.location.href)
    persistSessionSnapshot(window.history.state, currentEntrySnapshot(targetUrl))
  }

  function writeUrl(mode: HistoryMode) {
    url.value = publicUrl(currentPath.value, state.value, sourceMode.value || undefined)
    if (!import.meta.client) return
    const privateValue = currentPrivateState()
    const nextState = historyStateWithSearchState(window.history.state, privateValue)
    if (mode === 'push') window.history.pushState(nextState, '', url.value)
    else window.history.replaceState(nextState, '', url.value)
    persistSessionSnapshot(window.history.state, currentEntrySnapshot(url.value))
  }

  function restorePublic(inputValue: string, historyState?: unknown, plannedSnapshot?: SearchEntrySnapshot) {
    const next = publicStateFromUrl(inputValue)
    const restoredSnapshot = plannedSnapshot?.url === entryUrl(inputValue)
      ? plannedSnapshot
      : entrySnapshotFromHistory(historyState, inputValue, next.parsed.viewport)
        || readSessionSnapshot(historyState, inputValue)
    const restoredPrivate = restoredSnapshot?.privateState || { panel: 'list' }
    currentPath.value = next.url.pathname
    sourceMode.value = next.url.searchParams.get('source') === 'saved' ? 'saved' : ''
    state.value = { ...next.parsed, ...restoredPrivate, panel: restoredPrivate.panel }
    committedViewport.value = restoredSnapshot ? restoredSnapshot.committedViewport : next.parsed.viewport
    url.value = publicUrl(currentPath.value, state.value, sourceMode.value || undefined)
    hasMalformedUrl.value = next.malformed
    viewportPending.value = restoredSnapshot?.viewportPending || false
    stampCurrentEntry(inputValue)
  }

  function flushPendingEntry() {
    if (!viewportPending.value) return
    if (viewportTimer) {
      clearTimeout(viewportTimer)
      viewportTimer = null
    }
    writeUrl('replace')
  }

  function pushPublicState(nextState: SearchViewRuntimeState) {
    flushPendingEntry()
    state.value = nextState
    if (committedViewport.value) state.value.viewport = committedViewport.value
    else delete state.value.viewport
    viewportPending.value = false
    writeUrl('push')
  }

  function setQuery(query: string) {
    pushPublicState({ ...state.value, query: query.trim().slice(0, 120) })
  }

  function setIntent(intent: Intent) {
    pushPublicState({ ...state.value, intent: INTENTS.has(intent) ? intent : 'all' })
  }

  function setFilter(key: string, value: FilterSet[string] | undefined) {
    const filters = { ...state.value.filters }
    if (value === undefined || value === '' || value === 'all' || (Array.isArray(value) && value.length === 0)) delete filters[key]
    else filters[key] = value
    pushPublicState({ ...state.value, filters })
  }

  function setArea(area?: AreaRef | string) {
    const normalized = typeof area === 'string' ? { id: area } : area
    const nextState = { ...state.value, ...(normalized?.id ? { area: normalized } : {} ) }
    if (!normalized?.id) delete nextState.area
    pushPublicState(nextState)
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
    if (!import.meta.client) return state.value
    const inputValue = window.location.pathname + window.location.search
    restorePublic(inputValue, historyState === undefined ? window.history.state : historyState)
    return state.value
  }

  function urlForQuery(query: string) {
    flushPendingEntry()
    const nextState: SearchViewRuntimeState = { ...state.value, query: query.trim().slice(0, 120) }
    if (committedViewport.value) nextState.viewport = committedViewport.value
    else delete nextState.viewport
    const target = publicUrl(currentPath.value, nextState, sourceMode.value || undefined)
    plannedNavigation = {
      url: entryUrl(target),
      privateState: currentPrivateState(),
      committedViewport: sanitizedViewport(committedViewport.value),
      viewportPending: false,
    }
    return target
  }

  if (route) {
    watch(() => route.fullPath, (fullPath) => {
      const plannedSnapshot = plannedNavigation?.url === entryUrl(fullPath) ? plannedNavigation : undefined
      restorePublic(fullPath, import.meta.client ? window.history.state : undefined, plannedSnapshot)
      if (plannedSnapshot) plannedNavigation = undefined
    })
  }

  if (import.meta.client) {
    if (initialUsesBrowserEntry) {
      stampCurrentEntry(initialInput)
    }
    const onPopState = (event: PopStateEvent) => {
      plannedNavigation = undefined
      restorePublic(window.location.pathname + window.location.search, event.state)
    }
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
