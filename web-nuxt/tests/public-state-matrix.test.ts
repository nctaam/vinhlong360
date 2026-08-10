import { clearNuxtData, refreshNuxtData } from '#app'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import HomePage from '../pages/index.vue'
import TourismPage from '../pages/du-lich.vue'
import SearchPage from '../pages/tim-kiem.vue'
import MapPage from '../pages/ban-do.vue'
import DetailPage from '../pages/dia-diem/[id].vue'
import PlannerPage from '../pages/tao-lich-trinh.vue'
import {
  PUBLIC_ROUTE_SPECS,
  PUBLIC_STATE_KINDS,
  buildPublicStateMatrix,
  evaluatePublicStateEvidence,
} from '../../scripts/smoke_e2e_chrome.mjs'

const apiFetchMock = vi.hoisted(() => vi.fn())
const navigateToMock = vi.hoisted(() => vi.fn(() => Promise.resolve()))
const plannerGetEntityMock = vi.hoisted(() => vi.fn())
const plannerListEntitiesMock = vi.hoisted(() => vi.fn())
const searchAllMock = vi.hoisted(() => vi.fn())

mockNuxtImport('apiFetch', () => apiFetchMock)
mockNuxtImport('navigateTo', () => navigateToMock)
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))
vi.mock('../composables/useUnifiedSearch', () => ({
  useUnifiedSearch: () => ({
    searchAll: searchAllMock,
    fetchEntitySuggestions: vi.fn().mockResolvedValue([]),
    zeroResultRecoveryActions: () => [{ id: 'browse', label: 'Khám phá du lịch', to: '/du-lich' }],
  }),
}))
vi.mock('~/composables/usePublicApi', () => ({
  usePublicApi: () => ({
    getEntity: plannerGetEntityMock,
    listEntities: plannerListEntitiesMock,
  }),
}))

type RouteKey = typeof PUBLIC_ROUTE_SPECS[number]['key']
type StateKind = typeof PUBLIC_STATE_KINDS[number]

// Generic matrix rows intentionally collapse onto the closest boundary each route owns.
// The route tests below execute every distinct boundary named here through the real page component.
const ROUTE_STATE_BOUNDARIES: Record<RouteKey, Record<StateKind, string>> = {
  home: {
    loading: 'homepage refresh skeleton',
    ready: 'homepage editorial content',
    partial: 'preserved homepage editorial content',
    stale: 'preserved homepage editorial content',
    empty: 'homepage empty recovery',
    error: 'homepage retry recovery',
    offline: 'preserved homepage editorial content',
    '404-confirmed': 'homepage retry recovery; never a route-level 404',
    'retryable-5xx': 'homepage retry recovery',
  },
  tourism: {
    loading: 'catalog retry recovery; route exposes no distinct pending branch after first load',
    ready: 'catalog result surface',
    partial: 'preserved catalog result surface',
    stale: 'preserved catalog result surface',
    empty: 'catalog filter recovery',
    error: 'catalog retry recovery',
    offline: 'preserved catalog result surface',
    '404-confirmed': 'catalog retry recovery; never a route-level 404',
    'retryable-5xx': 'catalog retry recovery',
  },
  search: {
    loading: 'search retry skeleton',
    ready: 'search map-list result surface',
    partial: 'preserved search result surface',
    stale: 'preserved search result surface',
    empty: 'zero-result query recovery',
    error: 'search retry recovery',
    offline: 'preserved search result surface',
    '404-confirmed': 'search retry recovery; never a route-level 404',
    'retryable-5xx': 'search retry recovery',
  },
  map: {
    loading: 'map retry loading state',
    ready: 'map-list result surface',
    partial: 'map error with preserved list fallback',
    stale: 'preserved map-list result surface',
    empty: 'empty map-list surface',
    error: 'map retry recovery',
    offline: 'preserved map-list result surface',
    '404-confirmed': 'map retry recovery; never a route-level 404',
    'retryable-5xx': 'map retry recovery',
  },
  detail: {
    loading: 'detail retry loading state',
    ready: 'detail dossier',
    partial: 'detail dossier with gallery recovery',
    stale: 'detail dossier with supplied source evidence',
    empty: 'hidden-content recovery',
    error: 'detail retry recovery',
    offline: 'preserved detail dossier',
    '404-confirmed': 'confirmed not-found recovery',
    'retryable-5xx': 'detail retry recovery',
  },
  planner: {
    loading: 'editable planner while picker refreshes',
    ready: 'planner picker results',
    partial: 'preserved editable planner and picker results',
    stale: 'preserved editable planner and picker results',
    empty: 'empty picker recovery',
    error: 'picker retry recovery',
    offline: 'preserved editable planner and picker results',
    '404-confirmed': 'picker retry recovery; never a route-level 404',
    'retryable-5xx': 'picker retry recovery',
  },
}

const wrappers: Array<{ unmount: () => void }> = []
const routeOwnedPageExecutions = new Set<string>()

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

const sharedStubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  CountUp: true,
  FilterChips: true,
  ImageDisclosure: true,
  JourneyActionRail: true,
  JourneyBar: true,
  LazyJourneyBar: true,
  SaveButton: true,
  SearchAutocomplete: true,
  SkeletonGrid: { props: ['count'], template: '<div data-skeleton-grid />' },
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

const homeStubs = {
  ...sharedStubs,
  EntityCard: { props: ['entity'], template: '<article data-home-entity>{{ entity.name }}</article>' },
  HomeFeatureDossier: { props: ['title'], template: '<article data-home-feature>{{ title }}</article>' },
}

const tourismStubs = {
  ...sharedStubs,
  CatalogSpotlight: true,
  EntityCard: { props: ['entity'], template: '<article data-tourism-entity>{{ entity.name }}</article>' },
}

const mapListStub = {
  props: ['results', 'mapState'],
  template: '<section data-map-list-surface :data-map-state="mapState"><span v-for="item in results" :key="item.id" data-route-result>{{ item.name }}</span></section>',
}

const searchStubs = {
  ...sharedStubs,
  AISearchAssist: true,
  LazyAISearchAssist: true,
  LazySmartRecommendations: true,
  MapListSurface: mapListStub,
}

const mapStubs = {
  ...sharedStubs,
  ClientOnly: { template: '<slot />' },
  MapListSurface: mapListStub,
}

const detailStubs = {
  ...sharedStubs,
  AIBestTime: true,
  ContactWidget: true,
  EntityFeed: true,
  EntityMap: true,
  LazyContactWidget: true,
  ReviewSection: true,
  ShareButton: true,
}

const plannerStubs = {
  Breadcrumb: true,
  ClientOnly: true,
  FilterChips: true,
}

function cover(route: RouteKey, states: StateKind[]) {
  for (const state of states) routeOwnedPageExecutions.add(`${route}:${state}`)
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

async function resetMountedRoutes() {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((fulfill) => { resolve = fulfill })
  return { promise, resolve }
}

function homeFixture() {
  return {
    month: 8,
    seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
    experiences: [{ id: 'experience-1', name: 'Vườn ven sông', type: 'experience', summary: 'Đi giữa vườn cây.', images: [] }],
    products: [],
    upcoming_events: [],
    seasonal: [],
    top_dishes: [],
    itineraries: [],
    area_counts: {},
  }
}

function catalogFixture() {
  return {
    entities: [{ id: 'craft-1', name: 'Làng gốm Mang Thít', type: 'craft_village', summary: 'Theo dấu đất và lửa.', quality: { source_tier: 'official' } }],
    total: 1,
  }
}

function searchFixture() {
  return {
    entities: [{ id: 'craft-1', name: 'Gốm đỏ Mang Thít', type: 'craft_village', coordinates: { lat: 10.24, lng: 106.01 } }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  }
}

function mapFixture() {
  return [{ id: 'craft-1', name: 'Gốm đỏ Mang Thít', type: 'craft_village', lat: 10.24, lng: 106.01 }]
}

function plannerFixture() {
  return {
    total: 1,
    entities: [{ id: 'craft-1', name: 'Gốm đỏ Mang Thít', type: 'craft_village', coordinates: [10.24, 106.01] }],
  }
}

function detailEntity() {
  return {
    id: 'gom-do-mang-thit',
    name: 'Gốm đỏ Mang Thít',
    type: 'craft_village',
    summary: 'Theo dấu đất và lửa dọc sông Cổ Chiên.',
    description: 'Thông tin chi tiết về làng gốm.',
    attributes: {},
    images: [],
    source_freshness: { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' },
  }
}

function detailFailure(statusCode: number, detail: string) {
  return Object.assign(new Error(detail), { statusCode, data: { detail } })
}

function mockBackgroundApi(path: string) {
  if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
  if (path.startsWith('/api/community/')) return Promise.resolve(null)
  if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
  return Promise.resolve({})
}

function mockDetailApi(baseResult: () => Promise<unknown>, galleryResult: () => Promise<unknown> = () => Promise.resolve({ images: [] })) {
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/entities/gom-do-mang-thit') return baseResult()
    if (path === '/api/entities/gom-do-mang-thit/gallery') return galleryResult()
    if (path === '/api/entities/gom-do-mang-thit/relationships') return Promise.resolve({ relationships: [], total: 0 })
    if (path === '/seo/jsonld/gom-do-mang-thit') return Promise.resolve(null)
    return Promise.resolve({})
  })
}

async function mountPage(component: Parameters<typeof mountSuspended>[0], options: Parameters<typeof mountSuspended>[1] = {}) {
  const wrapper = await mountSuspended(component, options)
  wrappers.push(wrapper)
  await flushUi()
  return wrapper
}

beforeEach(() => {
  apiFetchMock.mockReset()
  navigateToMock.mockReset()
  plannerGetEntityMock.mockReset()
  plannerListEntitiesMock.mockReset()
  searchAllMock.mockReset()
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(resetMountedRoutes)

describe.sequential('public vertical-slice state matrix', () => {
  it('covers every required route and state without collapsing retryable 5xx into 404', () => {
    const matrix = buildPublicStateMatrix()

    expect(matrix).toHaveLength(PUBLIC_ROUTE_SPECS.length * PUBLIC_STATE_KINDS.length)
    expect(new Set(matrix.map(scenario => `${scenario.route.key}:${scenario.state}`)).size).toBe(matrix.length)

    for (const route of PUBLIC_ROUTE_SPECS) {
      expect(matrix.filter(scenario => scenario.route.key === route.key).map(scenario => scenario.state))
        .toEqual(PUBLIC_STATE_KINDS)
      expect(Object.keys(ROUTE_STATE_BOUNDARIES[route.key])).toEqual(PUBLIC_STATE_KINDS)
      expect(Object.values(ROUTE_STATE_BOUNDARIES[route.key]).every(Boolean)).toBe(true)
    }

    const retryableDetail = matrix.find(scenario => scenario.route.key === 'detail' && scenario.state === 'retryable-5xx')!
    expect(retryableDetail.expected.confirmed404).toBe(false)
    expect(retryableDetail.expected.actions).toContain('retry')
  })

  it('requires preserved content and local recovery for partial, stale and offline states', () => {
    for (const state of ['partial', 'stale', 'offline'] as const) {
      const scenario = buildPublicStateMatrix().find(item => item.route.key === 'search' && item.state === state)!
      const reasons = evaluatePublicStateEvidence(scenario, {
        shellVisible: true,
        mainVisible: true,
        contentVisible: false,
        actions: state === 'partial' ? ['retry-panel'] : [],
        confirmed404: false,
        actionDockOverlap: 0,
      })

      expect(reasons).toContain('content-not-preserved')
    }
  })

  it('accepts confirmed 404 only on detail and requires a way back to prior results', () => {
    const detail404 = buildPublicStateMatrix().find(item => item.route.key === 'detail' && item.state === '404-confirmed')!
    const validEvidence = {
      shellVisible: true,
      mainVisible: true,
      contentVisible: false,
      actions: ['back-to-results'],
      confirmed404: true,
      actionDockOverlap: 0,
    }

    expect(evaluatePublicStateEvidence(detail404, validEvidence)).toEqual([])

    const search404 = buildPublicStateMatrix().find(item => item.route.key === 'search' && item.state === '404-confirmed')!
    expect(evaluatePublicStateEvidence(search404, validEvidence)).toContain('false-404')
  })

  it('executes homepage content, empty, retry, and pending-refresh boundaries', async () => {
    apiFetchMock.mockImplementation((url: unknown) => String(url) === '/api/homepage'
      ? Promise.resolve(homeFixture())
      : mockBackgroundApi(String(url)))
    let wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-page-recipe="homepage"]').text()).toContain('Theo dòng sông, gặp mùa trái chín')
    cover('home', ['ready', 'partial', 'stale', 'offline'])

    await resetMountedRoutes()
    apiFetchMock.mockImplementation((url: unknown) => String(url) === '/api/homepage'
      ? Promise.resolve({ month: 8, experiences: [], products: [], upcoming_events: [], seasonal: [], top_dishes: [], itineraries: [], area_counts: {} })
      : mockBackgroundApi(String(url)))
    wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"]').text()).toContain('Đang cập nhật nội dung')
    cover('home', ['empty'])

    await resetMountedRoutes()
    apiFetchMock.mockImplementation((url: unknown) => String(url) === '/api/homepage'
      ? Promise.reject(new Error('homepage unavailable'))
      : mockBackgroundApi(String(url)))
    wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"] button').text()).toContain('Tải lại')
    cover('home', ['error', '404-confirmed', 'retryable-5xx'])

    await resetMountedRoutes()
    const pending = deferred<ReturnType<typeof homeFixture>>()
    let homepageAttempts = 0
    apiFetchMock.mockImplementation((url: unknown) => {
      if (String(url) !== '/api/homepage') return mockBackgroundApi(String(url))
      homepageAttempts += 1
      return homepageAttempts === 1 ? Promise.reject(new Error('retry')) : pending.promise
    })
    wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.find('[data-skeleton-grid]').exists()).toBe(true)
    cover('home', ['loading'])
    pending.resolve(homeFixture())
  })

  it('executes tourism results, empty recovery, retry, and retry loading', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())
    let wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.get('[data-catalog-result]').text()).toContain('Làng gốm Mang Thít')
    cover('tourism', ['ready', 'partial', 'stale', 'offline'])

    await resetMountedRoutes()
    apiFetchMock.mockResolvedValue({ entities: [], total: 0 })
    wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.get('[data-catalog-section="results"]').text()).toContain('Không tìm thấy kết quả')
    cover('tourism', ['empty'])

    await resetMountedRoutes()
    apiFetchMock.mockRejectedValue(new Error('catalog unavailable'))
    wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    const retry = wrapper.get('[data-catalog-section="results"]').findAll('button')
      .find(button => button.text().includes('Thử lại'))!
    expect(retry.text()).toContain('Thử lại')
    cover('tourism', ['loading', 'error', '404-confirmed', 'retryable-5xx'])
    apiFetchMock.mockResolvedValue(catalogFixture())
    await retry.trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-catalog-result]').exists()).toBe(true))
  })

  it('executes search results, zero results, retry, and retry loading', async () => {
    searchAllMock.mockResolvedValue(searchFixture())
    let wrapper = await mountPage(SearchPage, { route: '/tim-kiem?q=g%E1%BB%91m', global: { stubs: searchStubs } })
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
    cover('search', ['ready', 'partial', 'stale', 'offline'])

    await resetMountedRoutes()
    searchAllMock.mockResolvedValue({ entities: [], posts: [], users: [], totals: { entities: 0, posts: 0, users: 0 } })
    wrapper = await mountPage(SearchPage, { route: '/tim-kiem?q=g%E1%BB%91m', global: { stubs: searchStubs } })
    expect(wrapper.text()).toContain('Chưa thấy đúng ý bạn')
    cover('search', ['empty'])

    await resetMountedRoutes()
    const pending = deferred<ReturnType<typeof searchFixture>>()
    searchAllMock.mockRejectedValueOnce(new Error('search unavailable')).mockImplementationOnce(() => pending.promise)
    wrapper = await mountPage(SearchPage, { route: '/tim-kiem?q=g%E1%BB%91m', global: { stubs: searchStubs } })
    const retry = wrapper.get('[role="alert"] button')
    expect(retry.text()).toContain('Thử lại')
    cover('search', ['error', '404-confirmed', 'retryable-5xx'])
    await retry.trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-skeleton-grid]').exists()).toBe(true))
    cover('search', ['loading'])
    pending.resolve(searchFixture())
  })

  it('executes map results, empty, preserved fallback, retry, and retry loading', async () => {
    apiFetchMock.mockResolvedValue(mapFixture())
    let wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
    cover('map', ['ready', 'stale', 'offline'])

    apiFetchMock.mockRejectedValue(new Error('map refresh unavailable'))
    await refreshNuxtData('map-pins-all-all')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="error"]').exists()).toBe(true))
    expect(wrapper.get('[data-page-state="error"] [data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
    cover('map', ['partial'])

    await resetMountedRoutes()
    apiFetchMock.mockResolvedValue([])
    wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-map-list-surface]').findAll('[data-route-result]')).toHaveLength(0)
    cover('map', ['empty'])

    await resetMountedRoutes()
    const pending = deferred<ReturnType<typeof mapFixture>>()
    apiFetchMock.mockRejectedValueOnce(new Error('map unavailable')).mockImplementationOnce(() => pending.promise)
    wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    const retry = wrapper.get('[data-page-state-retry]')
    expect(wrapper.get('[data-page-state="error"]')).toBeTruthy()
    cover('map', ['error', '404-confirmed', 'retryable-5xx'])
    await retry.trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="loading"]').exists()).toBe(true))
    cover('map', ['loading'])
    pending.resolve(mapFixture())
  })

  it('executes detail dossier, partial media, hidden, confirmed 404, and retryable failure boundaries', async () => {
    mockDetailApi(() => Promise.resolve(detailEntity()))
    let wrapper = await mountPage(DetailPage, { route: '/dia-diem/gom-do-mang-thit', global: { stubs: detailStubs } })
    expect(wrapper.get('[data-page-recipe="detail"]').text()).toContain('Gốm đỏ Mang Thít')
    cover('detail', ['ready', 'stale', 'offline'])

    await resetMountedRoutes()
    mockDetailApi(() => Promise.resolve(detailEntity()), () => Promise.reject(new Error('gallery unavailable')))
    wrapper = await mountPage(DetailPage, { route: '/dia-diem/gom-do-mang-thit', global: { stubs: detailStubs } })
    expect(wrapper.get('[data-page-state="partial"]')).toBeTruthy()
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')
    cover('detail', ['partial'])

    await resetMountedRoutes()
    mockDetailApi(() => Promise.reject(detailFailure(403, 'hidden')))
    wrapper = await mountPage(DetailPage, { route: '/dia-diem/gom-do-mang-thit', global: { stubs: detailStubs } })
    expect(wrapper.text()).toContain('Nội dung chưa công khai')
    expect(wrapper.text()).toContain('Quay lại')
    cover('detail', ['empty'])

    await resetMountedRoutes()
    mockDetailApi(() => Promise.reject(detailFailure(404, 'not_found')))
    wrapper = await mountPage(DetailPage, { route: '/dia-diem/gom-do-mang-thit', global: { stubs: detailStubs } })
    expect(wrapper.text()).toContain('Không tìm thấy địa điểm này')
    expect(wrapper.text()).toContain('Khám phá điểm đến')
    expect(wrapper.get('button').text()).toContain('Quay lại')
    cover('detail', ['404-confirmed'])

    await resetMountedRoutes()
    const pending = deferred<ReturnType<typeof detailEntity>>()
    let detailAttempts = 0
    mockDetailApi(() => {
      detailAttempts += 1
      return detailAttempts === 1
        ? Promise.reject(detailFailure(503, 'temporarily_unavailable'))
        : pending.promise
    })
    wrapper = await mountPage(DetailPage, { route: '/dia-diem/gom-do-mang-thit', global: { stubs: detailStubs } })
    expect(wrapper.get('.detail-recovery-page').text()).toContain('Quay lại kết quả trước')
    expect(wrapper.get('.detail-recovery-page').text()).toContain('Khám phá điểm đến')
    const retry = wrapper.get('[data-page-state-retry]')
    cover('detail', ['error', 'retryable-5xx'])
    await retry.trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="loading"]').exists()).toBe(true))
    cover('detail', ['loading'])
    pending.resolve(detailEntity())
  })

  it('executes planner picker results, empty, retry, and editable pending-refresh boundaries', async () => {
    plannerListEntitiesMock.mockResolvedValue(plannerFixture())
    let wrapper = await mountPage(PlannerPage, { route: '/tao-lich-trinh', global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-list').text()).toContain('Gốm đỏ Mang Thít')
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
    cover('planner', ['ready', 'partial', 'stale', 'offline'])

    await resetMountedRoutes()
    plannerListEntitiesMock.mockResolvedValue({ total: 0, entities: [] })
    wrapper = await mountPage(PlannerPage, { route: '/tao-lich-trinh', global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-list').text()).toContain('Không tìm thấy')
    cover('planner', ['empty'])

    await resetMountedRoutes()
    const pending = deferred<ReturnType<typeof plannerFixture>>()
    plannerListEntitiesMock.mockRejectedValueOnce(new Error('picker unavailable')).mockImplementationOnce(() => pending.promise)
    wrapper = await mountPage(PlannerPage, { route: '/tao-lich-trinh', global: { stubs: plannerStubs } })
    const retry = wrapper.get('.picker-empty button')
    expect(retry.text()).toContain('Thử lại')
    cover('planner', ['error', '404-confirmed', 'retryable-5xx'])
    await retry.trigger('click')
    await nextTick()
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
    expect(wrapper.find('.builder-empty').exists()).toBe(true)
    cover('planner', ['loading'])
    pending.resolve(plannerFixture())
  })

  it('binds every matrix row to an executed route-owned page boundary', () => {
    expect([...routeOwnedPageExecutions].sort()).toEqual(
      buildPublicStateMatrix().map(scenario => `${scenario.route.key}:${scenario.state}`).sort(),
    )
  })
})
