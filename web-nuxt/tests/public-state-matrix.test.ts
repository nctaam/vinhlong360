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

const wrappers: Array<{ unmount: () => void }> = []
const executedStateRows = new Map<string, number>()

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

const searchStubs = {
  ...sharedStubs,
  AISearchAssist: true,
  EntityCard: { props: ['entity'], template: '<article data-search-entity>{{ entity.name }}</article>' },
  LazyAISearchAssist: true,
  LazySmartRecommendations: true,
}

const mapStubs = {
  ...sharedStubs,
  ClientOnly: { template: '<slot />' },
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

interface RouteStateEvidence {
  readonly shellVisible: boolean
  readonly mainVisible: boolean
  readonly contentVisible: boolean
  readonly actions: string[]
  readonly confirmed404: boolean
}

function captureRouteStateEvidence(route: RouteKey, state: StateKind, wrapper: any): RouteStateEvidence {
  const contentSelectors: Record<RouteKey, string> = {
    home: '[data-home-entity], [data-home-feature]',
    tourism: '[data-catalog-result]',
    search: '[data-map-list-surface], .search-section-secondary',
    map: '[data-map-list-surface]',
    detail: '[data-page-recipe="detail"]',
    planner: '.picker-item',
  }
  const controls = wrapper.findAll('button, a')
  const controlText = controls.map((control: { text: () => string }) => control.text().trim()).join('\n')
  const retryVisible = wrapper.find('[data-page-state-retry]').exists()
    || /(?:Thử lại|Tải lại(?: dữ liệu)?)/i.test(controlText)
  const recoverVisible = wrapper.find('[data-page-state-recovery], [data-recovery-action]').exists()
    || /(?:Xóa bộ lọc|Quay lại)/i.test(controlText)
    || wrapper.find('a[href="/du-lich"]').exists()
    || wrapper.find('[data-home-section="community"] a').exists()
    || wrapper.find('[aria-label="Lọc theo loại địa điểm"]').exists()
    || wrapper.find('input[aria-label="Tìm điểm đến"]').exists()
  const actions: string[] = []
  if (state === 'partial' && route === 'home' && recoverVisible) actions.push('recover')
  if (state === 'partial' && route !== 'home' && retryVisible) actions.push('retry-panel')
  if ((state === 'error' || state === 'retryable-5xx' || (state === '404-confirmed' && route !== 'detail')) && retryVisible) actions.push('retry')
  if (state === 'offline' && route === 'home' && retryVisible) actions.push('retry')
  if (state === 'empty' && recoverVisible) actions.push('recover')
  if (state === '404-confirmed' && route === 'detail' && recoverVisible) actions.push('back-to-results')

  return {
    shellVisible: wrapper.exists(),
    mainVisible: wrapper.find('.page, [data-page-recipe]').exists(),
    contentVisible: wrapper.find(contentSelectors[route]).exists(),
    actions,
    confirmed404: wrapper.text().includes('Không tìm thấy địa điểm này'),
  }
}

function stateIt(route: RouteKey, state: StateKind, run: () => Promise<RouteStateEvidence | void>) {
  it(`${route}:${state} executes its own route-owned boundary`, async () => {
    const captured = await run()
    const wrapper = wrappers.at(-1)
    const evidence = captured || (wrapper ? captureRouteStateEvidence(route, state, wrapper) : null)
    expect(evidence, `${route}:${state} must capture route-owned DOM evidence`).not.toBeNull()
    const scenario = buildPublicStateMatrix().find(item => item.route.key === route && item.state === state)!
    expect(evaluatePublicStateEvidence(scenario, evidence)).toEqual([])
    const row = `${route}:${state}`
    executedStateRows.set(row, (executedStateRows.get(row) || 0) + 1)
  })
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

async function mountPage(component: Parameters<typeof mountSuspended>[0], options: Parameters<typeof mountSuspended>[1] = {}) {
  const wrapper = await mountSuspended(component, options)
  wrappers.push(wrapper)
  await flushUi()
  return wrapper
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((fulfill) => { resolve = fulfill })
  return { promise, resolve }
}

function setOnline(value: boolean) {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value })
}

function requestFailure(statusCode: number, detail: string) {
  return Object.assign(new Error(detail), { statusCode, data: { detail } })
}

function homeFixture(options: { staleEvent?: boolean } = {}) {
  return {
    month: 8,
    seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
    experiences: [{ id: 'experience-1', name: 'Vườn ven sông', type: 'experience', summary: 'Đi giữa vườn cây.', images: [] }],
    products: [],
    upcoming_events: options.staleEvent ? [
      {
        id: 'event-1',
        name: 'Ngày hội ven sông',
        type: 'event',
        attributes: { date_start: '2026-08-20' },
        source_freshness: { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' },
      },
      {
        id: 'event-2',
        name: 'Đêm hội gốm đỏ',
        type: 'event',
        attributes: { date_start: '2026-08-21' },
        source_freshness: { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' },
      },
    ] : [],
    seasonal: [],
    top_dishes: [],
    itineraries: [],
    area_counts: {},
  }
}

function emptyHomeFixture() {
  return { month: 8, experiences: [], products: [], upcoming_events: [], seasonal: [], top_dishes: [], itineraries: [], area_counts: {} }
}

function catalogFixture(options: { stale?: boolean } = {}) {
  return {
    entities: [{
      id: 'craft-1',
      name: 'Làng gốm Mang Thít',
      type: 'craft_village',
      summary: 'Theo dấu đất và lửa.',
      quality: { source_tier: 'official' },
      source_freshness: options.stale
        ? { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' }
        : { freshness_status: 'fresh', updated_at: '2026-08-01T00:00:00Z' },
    }],
    total: 1,
  }
}

function searchFixture(options: { stale?: boolean } = {}) {
  return {
    entities: [{
      id: 'craft-1',
      name: 'Gốm đỏ Mang Thít',
      type: 'craft_village',
      source_freshness: options.stale
        ? { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' }
        : { freshness_status: 'fresh', updated_at: '2026-08-01T00:00:00Z' },
    }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  }
}

function searchCommunityFixture() {
  return {
    entities: [],
    posts: [{ id: 'post-1', display_name: 'Lan', content: 'Chia sẻ đường về làng gốm.' }],
    users: [{ id: 'user-1', username: 'lan', display_name: 'Lan', post_count: 3 }],
    totals: { entities: 0, posts: 1, users: 1 },
  }
}

function mapFixture(options: { stale?: boolean } = {}) {
  return [{
    id: 'craft-1',
    name: 'Gốm đỏ Mang Thít',
    type: 'craft_village',
    source_freshness: options.stale
      ? { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' }
      : { freshness_status: 'fresh', updated_at: '2026-08-01T00:00:00Z' },
  }]
}

function plannerFixture(options: { stale?: boolean } = {}) {
  return {
    total: 1,
    entities: [{
      id: 'craft-1',
      name: 'Gốm đỏ Mang Thít',
      type: 'craft_village',
      coordinates: [10.24, 106.01],
      source_freshness: options.stale
        ? { freshness_status: 'stale', updated_at: '2026-06-01T00:00:00Z' }
        : { freshness_status: 'fresh', updated_at: '2026-08-01T00:00:00Z' },
    }],
  }
}

function detailEntity(freshness: 'fresh' | 'stale' = 'fresh') {
  return {
    id: 'gom-do-mang-thit',
    name: 'Gốm đỏ Mang Thít',
    type: 'craft_village',
    summary: 'Theo dấu đất và lửa dọc sông Cổ Chiên.',
    description: 'Thông tin chi tiết về làng gốm.',
    attributes: {},
    images: [],
    source_freshness: {
      freshness_status: freshness,
      updated_at: freshness === 'stale' ? '2026-06-01T00:00:00Z' : '2026-08-01T00:00:00Z',
    },
  }
}

function mockBackgroundApi(path: string, fail = false) {
  if (fail && (path.startsWith('/api/feed?') || path.startsWith('/api/community/'))) return Promise.reject(new Error('community unavailable'))
  if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
  if (path.startsWith('/api/community/')) return Promise.resolve(null)
  if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
  return Promise.resolve({})
}

function mockHome(result: () => Promise<unknown>, failBackground = false) {
  apiFetchMock.mockImplementation((url: unknown) => String(url) === '/api/homepage'
    ? result()
    : mockBackgroundApi(String(url), failBackground))
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

beforeEach(() => {
  apiFetchMock.mockReset()
  navigateToMock.mockReset()
  plannerGetEntityMock.mockReset()
  plannerListEntitiesMock.mockReset()
  searchAllMock.mockReset()
  localStorage.clear()
  sessionStorage.clear()
  setOnline(true)
})

afterEach(resetMountedRoutes)

describe.sequential('public vertical-slice state matrix contracts', () => {
  it('requires every route and state without collapsing retryable 5xx into 404', () => {
    const matrix = buildPublicStateMatrix()

    expect(matrix).toHaveLength(PUBLIC_ROUTE_SPECS.length * PUBLIC_STATE_KINDS.length)
    expect(new Set(matrix.map(scenario => `${scenario.route.key}:${scenario.state}`)).size).toBe(matrix.length)
    for (const route of PUBLIC_ROUTE_SPECS) {
      expect(matrix.filter(scenario => scenario.route.key === route.key).map(scenario => scenario.state)).toEqual(PUBLIC_STATE_KINDS)
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
      })
      expect(reasons).toContain('content-not-preserved')
    }

    const homePartial = buildPublicStateMatrix().find(item => item.route.key === 'home' && item.state === 'partial')!
    expect(homePartial.expected).toMatchObject({ preserveContent: true, actions: ['recover'] })
    const homeOffline = buildPublicStateMatrix().find(item => item.route.key === 'home' && item.state === 'offline')!
    expect(homeOffline.expected).toMatchObject({ preserveContent: false, actions: ['retry'] })
  })

  it('accepts confirmed 404 only on detail and requires a way back to prior results', () => {
    const detail404 = buildPublicStateMatrix().find(item => item.route.key === 'detail' && item.state === '404-confirmed')!
    const validEvidence = {
      shellVisible: true,
      mainVisible: true,
      contentVisible: false,
      actions: ['back-to-results'],
      confirmed404: true,
    }
    expect(evaluatePublicStateEvidence(detail404, validEvidence)).toEqual([])

    const search404 = buildPublicStateMatrix().find(item => item.route.key === 'search' && item.state === '404-confirmed')!
    expect(evaluatePublicStateEvidence(search404, validEvidence)).toContain('false-404')
  })
})

describe.sequential('home route state evidence', () => {
  stateIt('home', 'loading', async () => {
    const pending = deferred<ReturnType<typeof homeFixture>>()
    let attempts = 0
    mockHome(() => ++attempts === 1 ? Promise.reject(new Error('retry')) : pending.promise)
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.find('[data-skeleton-grid]').exists()).toBe(true)
    const evidence = captureRouteStateEvidence('home', 'loading', wrapper)
    pending.resolve(homeFixture())
    await flushUi()
    return evidence
  })

  stateIt('home', 'ready', async () => {
    mockHome(() => Promise.resolve(homeFixture()))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-page-recipe="homepage"]').text()).toContain('Theo dòng sông, gặp mùa trái chín')
  })

  stateIt('home', 'partial', async () => {
    mockHome(() => Promise.resolve(homeFixture()), true)
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-page-recipe="homepage"]').text()).toContain('Vườn ven sông')
    expect(wrapper.get('[data-home-section="community"]').text()).toContain('Cộng đồng đang khởi động')
    expect(wrapper.get('[data-home-section="community"] a').text()).toContain('Tham gia cộng đồng')
  })

  stateIt('home', 'stale', async () => {
    mockHome(() => Promise.resolve(homeFixture({ staleEvent: true })))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-freshness-status="stale"]').text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('Đêm hội gốm đỏ')
  })

  stateIt('home', 'empty', async () => {
    mockHome(() => Promise.resolve(emptyHomeFixture()))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"]').text()).toContain('Đang cập nhật nội dung')
  })

  stateIt('home', 'error', async () => {
    mockHome(() => Promise.reject(new Error('homepage unavailable')))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"] button').text()).toContain('Tải lại')
  })

  stateIt('home', 'offline', async () => {
    setOnline(false)
    mockHome(() => Promise.reject(new TypeError('Failed to fetch')))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"]').text()).toContain('Mạng chậm')
    expect(wrapper.get('[data-home-section="recovery"] button').text()).toContain('Tải lại')
  })

  stateIt('home', '404-confirmed', async () => {
    mockHome(() => Promise.reject(requestFailure(404, 'not_found')))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"] button').text()).toContain('Tải lại')
    expect(wrapper.text()).not.toContain('Không tìm thấy địa điểm này')
  })

  stateIt('home', 'retryable-5xx', async () => {
    mockHome(() => Promise.reject(requestFailure(503, 'temporarily_unavailable')))
    const wrapper = await mountPage(HomePage, { global: { stubs: homeStubs } })
    expect(wrapper.get('[data-home-section="recovery"] button').text()).toContain('Tải lại')
  })
})

describe.sequential('tourism route state evidence', () => {
  stateIt('tourism', 'loading', async () => {
    const pending = deferred<ReturnType<typeof catalogFixture>>()
    let retrying = false
    apiFetchMock.mockImplementation(() => retrying ? pending.promise : Promise.reject(new Error('catalog unavailable')))
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    const retry = wrapper.findAll('[data-catalog-section="results"] button').find(button => button.text().includes('Thử lại'))!
    expect(retry).toBeTruthy()
    retrying = true
    await retry.trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-skeleton-grid]').exists()).toBe(true))
    const evidence = captureRouteStateEvidence('tourism', 'loading', wrapper)
    pending.resolve(catalogFixture())
    await flushUi()
    return evidence
  })

  stateIt('tourism', 'ready', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.get('[data-catalog-result]').text()).toContain('Làng gốm Mang Thít')
  })

  stateIt('tourism', 'partial', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    apiFetchMock.mockRejectedValue(new Error('catalog refresh unavailable'))
    await refreshNuxtData('catalog-tourism')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="partial"]').exists()).toBe(true))
    expect(wrapper.get('[data-page-state="partial"]').text()).toContain('Làng gốm Mang Thít')
    expect(wrapper.find('[data-page-state="partial"] [data-page-state-retry]').exists()).toBe(true)
  })

  stateIt('tourism', 'stale', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture({ stale: true }))
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.get('[data-freshness-status="stale"]').text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('Làng gốm Mang Thít')
  })

  stateIt('tourism', 'empty', async () => {
    apiFetchMock.mockResolvedValue({ entities: [], total: 0 })
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.get('[data-catalog-section="results"]').text()).toContain('Không tìm thấy kết quả')
    expect(wrapper.findAll('[data-catalog-section="results"] button').some(button => button.text().includes('Xóa bộ lọc'))).toBe(true)
  })

  stateIt('tourism', 'error', async () => {
    apiFetchMock.mockRejectedValue(new Error('catalog unavailable'))
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.findAll('[data-catalog-section="results"] button').some(button => button.text().includes('Thử lại'))).toBe(true)
  })

  stateIt('tourism', 'offline', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    setOnline(false)
    window.dispatchEvent(new Event('offline'))
    await flushUi()
    expect(wrapper.get('[data-page-state="offline"]').text()).toContain('Bạn đang ngoại tuyến')
    expect(wrapper.get('[data-page-state="offline"]').text()).toContain('Làng gốm Mang Thít')
  })

  stateIt('tourism', '404-confirmed', async () => {
    apiFetchMock.mockRejectedValue(requestFailure(404, 'not_found'))
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.findAll('[data-catalog-section="results"] button').some(button => button.text().includes('Thử lại'))).toBe(true)
    expect(wrapper.text()).not.toContain('Không tìm thấy địa điểm này')
  })

  stateIt('tourism', 'retryable-5xx', async () => {
    apiFetchMock.mockRejectedValue(requestFailure(503, 'temporarily_unavailable'))
    const wrapper = await mountPage(TourismPage, { global: { stubs: tourismStubs } })
    expect(wrapper.findAll('[data-catalog-section="results"] button').some(button => button.text().includes('Thử lại'))).toBe(true)
  })
})

describe.sequential('search route state evidence', () => {
  const route = '/tim-kiem?q=g%E1%BB%91m'

  stateIt('search', 'loading', async () => {
    const pending = deferred<ReturnType<typeof searchFixture>>()
    searchAllMock.mockRejectedValueOnce(new Error('search unavailable')).mockImplementationOnce(() => pending.promise)
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    await wrapper.get('[role="alert"] button').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-skeleton-grid]').exists()).toBe(true))
    const evidence = captureRouteStateEvidence('search', 'loading', wrapper)
    pending.resolve(searchFixture())
    await flushUi()
    return evidence
  })

  stateIt('search', 'ready', async () => {
    searchAllMock.mockResolvedValue(searchFixture())
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('search', 'partial', async () => {
    searchAllMock.mockResolvedValue(searchFixture())
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    searchAllMock.mockRejectedValue(new Error('search refresh unavailable'))
    await refreshNuxtData('search-results')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="partial"]').exists()).toBe(true))
    expect(wrapper.get('[data-page-state="partial"]').text()).toContain('Gốm đỏ Mang Thít')
    expect(wrapper.find('[data-page-state="partial"] [data-page-state-retry]').exists()).toBe(true)
  })

  it('does not reuse results from a different query after the new query fails', async () => {
    searchAllMock.mockImplementation((query: string) => query === 'gốm'
      ? Promise.resolve(searchFixture())
      : Promise.reject(new Error('new query unavailable')))
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')

    await wrapper.vm.$router.push('/tim-kiem?q=sen')
    await flushUi()

    expect(wrapper.get('[role="alert"]').text()).toContain('Lỗi tìm kiếm')
    expect(wrapper.text()).not.toContain('Gốm đỏ Mang Thít')
  })

  it('preserves post and user results with offline precedence after refresh failure', async () => {
    searchAllMock.mockResolvedValue(searchCommunityFixture())
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.text()).toContain('Chia sẻ đường về làng gốm.')
    expect(wrapper.text()).toContain('Lan')

    setOnline(false)
    window.dispatchEvent(new Event('offline'))
    searchAllMock.mockRejectedValue(new Error('offline refresh unavailable'))
    await refreshNuxtData('search-results')
    await flushUi()

    expect(wrapper.get('[data-page-state="offline"]').text()).toContain('Bạn đang ngoại tuyến')
    expect(wrapper.get('[data-page-state="offline"]').text()).toContain('Chia sẻ đường về làng gốm.')
    expect(wrapper.get('[data-page-state="offline"]').text()).toContain('Lan')
  })

  stateIt('search', 'stale', async () => {
    searchAllMock.mockResolvedValue(searchFixture({ stale: true }))
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.get('[data-freshness-status="stale"]').text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('search', 'empty', async () => {
    searchAllMock.mockResolvedValue({ entities: [], posts: [], users: [], totals: { entities: 0, posts: 0, users: 0 } })
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.text()).toContain('Chưa thấy đúng ý bạn')
    expect(wrapper.get('[data-recovery-action="browse"]').text()).toContain('Khám phá du lịch')
  })

  stateIt('search', 'error', async () => {
    searchAllMock.mockRejectedValue(new Error('search unavailable'))
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.get('[role="alert"] button').text()).toContain('Thử lại')
  })

  stateIt('search', 'offline', async () => {
    searchAllMock.mockResolvedValue(searchFixture())
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    setOnline(false)
    window.dispatchEvent(new Event('offline'))
    await flushUi()
    expect(wrapper.get('[data-map-list-surface]').attributes('data-map-state')).toBe('offline')
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('search', '404-confirmed', async () => {
    searchAllMock.mockRejectedValue(requestFailure(404, 'not_found'))
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.get('[role="alert"] button').text()).toContain('Thử lại')
    expect(wrapper.text()).not.toContain('Không tìm thấy địa điểm này')
  })

  stateIt('search', 'retryable-5xx', async () => {
    searchAllMock.mockRejectedValue(requestFailure(503, 'temporarily_unavailable'))
    const wrapper = await mountPage(SearchPage, { route, global: { stubs: searchStubs } })
    expect(wrapper.get('[role="alert"] button').text()).toContain('Thử lại')
  })
})

describe.sequential('map route state evidence', () => {
  stateIt('map', 'loading', async () => {
    const pending = deferred<ReturnType<typeof mapFixture>>()
    apiFetchMock.mockRejectedValueOnce(new Error('map unavailable')).mockImplementationOnce(() => pending.promise)
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    await wrapper.get('[data-page-state-retry]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="loading"]').exists()).toBe(true))
    const evidence = captureRouteStateEvidence('map', 'loading', wrapper)
    pending.resolve(mapFixture())
    await flushUi()
    return evidence
  })

  stateIt('map', 'ready', async () => {
    apiFetchMock.mockResolvedValue(mapFixture())
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('map', 'partial', async () => {
    apiFetchMock.mockResolvedValue(mapFixture())
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    apiFetchMock.mockRejectedValue(new Error('map refresh unavailable'))
    await refreshNuxtData('map-pins-all-all')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="error"]').exists()).toBe(true))
    expect(wrapper.get('[data-page-state="error"]').text()).toContain('Gốm đỏ Mang Thít')
    expect(wrapper.find('[data-page-state="error"] [data-page-state-retry]').exists()).toBe(true)
  })

  stateIt('map', 'stale', async () => {
    apiFetchMock.mockResolvedValue(mapFixture({ stale: true }))
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-freshness-status="stale"]').text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('map', 'empty', async () => {
    apiFetchMock.mockResolvedValue([])
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('0 kết quả')
    expect(wrapper.get('[data-map-fallback]').text()).toContain('Chưa có vị trí để đặt trên bản đồ')
  })

  stateIt('map', 'error', async () => {
    apiFetchMock.mockRejectedValue(new Error('map unavailable'))
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-page-state="error"] [data-page-state-retry]').text()).toContain('Tải lại dữ liệu')
  })

  stateIt('map', 'offline', async () => {
    apiFetchMock.mockResolvedValue(mapFixture())
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    setOnline(false)
    window.dispatchEvent(new Event('offline'))
    await flushUi()
    expect(wrapper.get('[data-map-list-surface]').attributes('data-map-state')).toBe('offline')
    expect(wrapper.get('[data-map-list-surface]').text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('map', '404-confirmed', async () => {
    apiFetchMock.mockRejectedValue(requestFailure(404, 'not_found'))
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-page-state="error"] [data-page-state-retry]').text()).toContain('Tải lại dữ liệu')
    expect(wrapper.text()).not.toContain('Không tìm thấy địa điểm này')
  })

  stateIt('map', 'retryable-5xx', async () => {
    apiFetchMock.mockRejectedValue(requestFailure(503, 'temporarily_unavailable'))
    const wrapper = await mountPage(MapPage, { route: '/ban-do', global: { stubs: mapStubs } })
    expect(wrapper.get('[data-page-state="error"] [data-page-state-retry]').text()).toContain('Tải lại dữ liệu')
  })
})

describe.sequential('detail route state evidence', () => {
  const route = '/dia-diem/gom-do-mang-thit'

  stateIt('detail', 'loading', async () => {
    const pending = deferred<ReturnType<typeof detailEntity>>()
    let attempts = 0
    mockDetailApi(() => ++attempts === 1 ? Promise.reject(new Error('detail unavailable')) : pending.promise)
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    await wrapper.get('[data-page-state-retry]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-page-state="loading"]').exists()).toBe(true))
    const evidence = captureRouteStateEvidence('detail', 'loading', wrapper)
    pending.resolve(detailEntity())
    await flushUi()
    return evidence
  })

  stateIt('detail', 'ready', async () => {
    mockDetailApi(() => Promise.resolve(detailEntity()))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.get('[data-page-recipe="detail"]').text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('detail', 'partial', async () => {
    mockDetailApi(() => Promise.resolve(detailEntity()), () => Promise.reject(new Error('gallery unavailable')))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.get('[data-page-state="partial"]').text()).toContain('Thông tin địa điểm vẫn dùng được')
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')
    expect(wrapper.find('[data-page-state="partial"] [data-page-state-retry]').exists()).toBe(true)
  })

  stateIt('detail', 'stale', async () => {
    mockDetailApi(() => Promise.resolve(detailEntity('stale')))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.get('[data-freshness-status="stale"]').text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('detail', 'empty', async () => {
    mockDetailApi(() => Promise.reject(requestFailure(403, 'hidden')))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.text()).toContain('Nội dung chưa công khai')
    expect(wrapper.get('button').text()).toContain('Quay lại')
  })

  stateIt('detail', 'error', async () => {
    mockDetailApi(() => Promise.reject(new Error('detail unavailable')))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.get('[data-page-state="error"] [data-page-state-retry]').text()).toContain('Thử lại')
    expect(wrapper.text()).toContain('Quay lại kết quả trước')
  })

  stateIt('detail', 'offline', async () => {
    mockDetailApi(() => Promise.resolve(detailEntity()))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    setOnline(false)
    window.dispatchEvent(new Event('offline'))
    await flushUi()
    expect(wrapper.get('[data-page-state="offline"]').text()).toContain('Bạn đang ngoại tuyến')
    expect(wrapper.get('[data-page-recipe="detail"]').text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('detail', '404-confirmed', async () => {
    mockDetailApi(() => Promise.reject(requestFailure(404, 'not_found')))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.text()).toContain('Không tìm thấy địa điểm này')
    expect(wrapper.text()).toContain('Khám phá điểm đến')
    expect(wrapper.get('button').text()).toContain('Quay lại')
  })

  stateIt('detail', 'retryable-5xx', async () => {
    mockDetailApi(() => Promise.reject(requestFailure(503, 'temporarily_unavailable')))
    const wrapper = await mountPage(DetailPage, { route, global: { stubs: detailStubs } })
    expect(wrapper.get('[data-page-state="error"] [data-page-state-retry]').text()).toContain('Thử lại')
    expect(wrapper.text()).not.toContain('Không tìm thấy địa điểm này')
  })
})

describe.sequential('planner route state evidence', () => {
  const route = '/tao-lich-trinh'

  stateIt('planner', 'loading', async () => {
    const pending = deferred<ReturnType<typeof plannerFixture>>()
    plannerListEntitiesMock.mockRejectedValueOnce(new Error('picker unavailable')).mockImplementationOnce(() => pending.promise)
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    await wrapper.get('.picker-empty button').trigger('click')
    await flushUi()
    expect(wrapper.get('[data-picker-state="loading"]').text()).toContain('Đang tải danh sách')
    expect(wrapper.find('.builder-empty').exists()).toBe(true)
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
    const evidence = captureRouteStateEvidence('planner', 'loading', wrapper)
    pending.resolve(plannerFixture())
    await flushUi()
    return evidence
  })

  stateIt('planner', 'ready', async () => {
    plannerListEntitiesMock.mockResolvedValue(plannerFixture())
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-list').text()).toContain('Gốm đỏ Mang Thít')
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
  })

  stateIt('planner', 'partial', async () => {
    plannerListEntitiesMock.mockResolvedValue(plannerFixture())
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    plannerListEntitiesMock.mockRejectedValue(new Error('picker refresh unavailable'))
    await refreshNuxtData('planner-entities')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Không thể tải danh sách'))
    expect(wrapper.get('.picker-list').text()).toContain('Gốm đỏ Mang Thít')
    expect(wrapper.get('.picker-empty button').text()).toContain('Thử lại')
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
  })

  it('does not reuse picker results from a different query after the new query fails', async () => {
    plannerListEntitiesMock.mockImplementation((options: { q?: string }) => options.q === 'sen'
      ? Promise.reject(new Error('new picker query unavailable'))
      : Promise.resolve(plannerFixture()))
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-list').text()).toContain('Gốm đỏ Mang Thít')

    await wrapper.get('input[aria-label="Tìm điểm đến"]').setValue('sen')
    await flushUi()

    expect(wrapper.get('.picker-empty button').text()).toContain('Thử lại')
    expect(wrapper.get('.picker-list').text()).not.toContain('Gốm đỏ Mang Thít')
  })

  stateIt('planner', 'stale', async () => {
    plannerListEntitiesMock.mockResolvedValue(plannerFixture({ stale: true }))
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    await wrapper.get('.picker-item').trigger('click')
    await flushUi()
    expect(wrapper.get('[data-friction-code="stale-stop-facts"]').text()).toContain('Dữ kiện có thể đã cũ')
    expect(wrapper.text()).toContain('Gốm đỏ Mang Thít')
  })

  stateIt('planner', 'empty', async () => {
    plannerListEntitiesMock.mockResolvedValue({ total: 0, entities: [] })
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-list').text()).toContain('Không tìm thấy')
    expect(wrapper.find('.builder-empty').exists()).toBe(true)
  })

  stateIt('planner', 'error', async () => {
    plannerListEntitiesMock.mockRejectedValue(new Error('picker unavailable'))
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-empty button').text()).toContain('Thử lại')
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
  })

  stateIt('planner', 'offline', async () => {
    plannerListEntitiesMock.mockResolvedValue(plannerFixture())
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    setOnline(false)
    window.dispatchEvent(new Event('offline'))
    await flushUi()
    expect(wrapper.get('[data-friction-code="offline-draft"]').text()).toContain('Bản nháp ngoại tuyến')
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
  })

  stateIt('planner', '404-confirmed', async () => {
    plannerListEntitiesMock.mockRejectedValue(requestFailure(404, 'not_found'))
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-empty button').text()).toContain('Thử lại')
    expect(wrapper.text()).not.toContain('Không tìm thấy địa điểm này')
  })

  stateIt('planner', 'retryable-5xx', async () => {
    plannerListEntitiesMock.mockRejectedValue(requestFailure(503, 'temporarily_unavailable'))
    const wrapper = await mountPage(PlannerPage, { route, global: { stubs: plannerStubs } })
    expect(wrapper.get('.picker-empty button').text()).toContain('Thử lại')
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
  })
})

describe.sequential('route-owned state evidence coverage', () => {
  it('executes and validates every matrix row exactly once', () => {
    const expectedRows = buildPublicStateMatrix().map(scenario => `${scenario.route.key}:${scenario.state}`).sort()
    expect([...executedStateRows.entries()].sort(([left], [right]) => left.localeCompare(right))).toEqual(
      expectedRows.map(row => [row, 1]),
    )
  })
})
