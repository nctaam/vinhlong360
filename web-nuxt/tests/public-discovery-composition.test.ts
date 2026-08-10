import { clearNuxtData } from '#app'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../pages/index.vue'
import TourismPage from '../pages/du-lich.vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
mockNuxtImport('apiFetch', () => apiFetchMock)

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

const commonStubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  CountUp: { props: ['value'], template: '<span data-count-up>{{ value }}</span>' },
  EmptyState: { props: ['title', 'message'], template: '<div data-empty-state>{{ title }} {{ message }}<slot name="actions" /></div>' },
  FilterChips: true,
  SkeletonGrid: true,
  SaveButton: true,
  JourneyBar: true,
  JourneyActionRail: { template: '<nav data-journey-action-rail />' },
  SearchAutocomplete: { template: '<div data-home-search />' },
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

const homeStubs = {
  ...commonStubs,
  HeroIllustration: { template: '<div data-legacy-media-feature="hero-background" />' },
  EntityFeature: { template: '<div data-legacy-media-feature="entity-feature" />' },
  StorySpread: { template: '<div data-legacy-media-feature="story-spread" />' },
  EntityCard: { props: ['entity'], template: '<article data-legacy-entity-card>{{ entity.name }}</article>' },
}

const catalogStubs = {
  ...commonStubs,
  CatalogSpotlight: { template: '<section data-legacy-media-feature="catalog-spotlight" />' },
  CatalogInterstitial: { template: '<section data-catalog-interstitial />' },
  EntityCard: { props: ['entity'], template: '<article data-legacy-entity-card>{{ entity.name }}</article>' },
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => {
  apiFetchMock.mockReset()
  localStorage.clear()
})

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})

function homeFixture() {
  return {
    month: 8,
    seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
    experiences: [
      {
        id: 'experience-1',
        name: 'Vườn ven sông',
        type: 'experience',
        summary: 'Đi giữa vườn cây.',
        images: ['/img/entities/experience-1.webp'],
        quality: { source_tier: 'official' },
      },
    ],
    products: [],
    upcoming_events: [
      {
        id: 'event-1',
        name: 'Lễ hội sông nước',
        type: 'event',
        days_until: 1,
        attributes: { date_start: '2026-08-10' },
        source_freshness: {
          source_tier: 'official',
          source_title: 'Cổng thông tin Vĩnh Long',
          source_url: 'https://vinhlong.gov.vn',
          updated_at: '2026-08-09T07:00:00+07:00',
          freshness_status: 'fresh',
        },
      },
      {
        id: 'event-2',
        name: 'Đêm đờn ca',
        type: 'event',
        days_until: 4,
        attributes: { date_start: '2026-08-13' },
        source_freshness: {
          source_tier: 'official',
          source_title: 'Cổng thông tin Vĩnh Long',
          source_url: 'https://vinhlong.gov.vn',
          updated_at: '2026-08-09T07:00:00+07:00',
          freshness_status: 'fresh',
        },
      },
    ],
    seasonal: [
      { id: 'season-1', name: 'Chôm chôm Bình Hòa Phước', type: 'product' },
      { id: 'season-2', name: 'Bưởi Năm Roi', type: 'product' },
    ],
    top_dishes: [],
    itineraries: [],
    area_counts: { 'long-ho': 1 },
  }
}

function catalogFixture() {
  return {
    entities: [
      {
        id: 'craft-1',
        type: 'craft_village',
        name: 'Làng gốm Mang Thít',
        summary: 'Theo dấu đất và lửa dọc sông Cổ Chiên.',
        area: 'Mang Thít',
        quality: { source_tier: 'official', source_title: 'Cổng thông tin Vĩnh Long', source_url: 'https://vinhlong.gov.vn' },
        source_freshness: { source_tier: 'official', source_title: 'Cổng thông tin Vĩnh Long', source_url: 'https://vinhlong.gov.vn', updated_at: '2026-08-09T07:00:00+07:00', freshness_status: 'fresh' },
      },
      {
        id: 'stay-1',
        type: 'accommodation',
        name: 'Nhà vườn Cù Lao An Bình',
        summary: 'Một điểm nghỉ giữa vườn cây.',
        area: 'Long Hồ',
        images: ['/img/entities/stay-1.webp'],
        quality: { source_tier: 'community' },
        source_freshness: { source_tier: 'community', updated_at: '2026-07-20T07:00:00+07:00', freshness_status: 'aging' },
      },
    ],
    total: 2,
  }
}

describe('Adaptive Nocturne public discovery composition', () => {
  it('orders homepage context, editorial lead, decisions, signals, and continuation with one media lead', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(homeFixture())
      if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
      if (path === '/api/community/stats') return Promise.resolve(null)
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: homeStubs } })
    wrappers.push(wrapper)
    await flushUi()

    const anatomy = wrapper
      .findAll('[data-home-section]')
      .map(node => node.attributes('data-home-section'))
      .filter(section => ['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation'].includes(section || ''))

    expect(anatomy).toEqual(['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation'])
    expect(wrapper.findAll('[data-media-led-feature], [data-legacy-media-feature]')).toHaveLength(1)
    expect(wrapper.find('.spot-visual').exists()).toBe(false)

    const decisionLinks = wrapper.get('[data-home-section="quick-decisions"]').findAll('a')
    expect(decisionLinks.length).toBeGreaterThan(0)
    expect(decisionLinks.every(link => /^\/(?!\/)/.test(link.attributes('href') || ''))).toBe(true)

    const signals = wrapper.get('[data-home-section="signals"]').findAll('[data-home-signal]')
    expect(signals.length).toBeGreaterThan(0)
    expect(signals.every(signal => signal.find('[data-signal-source]').exists() && signal.find('[data-freshness-line]').exists())).toBe(true)
  })

  it('keeps degraded homepage data free of fabricated metrics', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.reject(new Error('homepage unavailable'))
      if (path.startsWith('/api/community/') || path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: homeStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.find('[data-home-metric]').exists()).toBe(false)
    expect(wrapper.find('[data-count-up]').exists()).toBe(false)
    expect(wrapper.text()).not.toMatch(/\b5[,.]0\b|\b\d+\s+(lượt xem|đánh giá|thành viên)\b/i)
  })

  it('renders honest evidence for seasonal signals even when source metadata is absent', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(homeFixture())
      if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
      if (path.startsWith('/api/community/')) return Promise.resolve(null)
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: homeStubs } })
    wrappers.push(wrapper)
    await flushUi()

    const seasonal = wrapper.get('[data-home-seasonal-signal]')
    expect(seasonal.text()).toContain('Bưởi Năm Roi')
    expect(seasonal.get('[data-signal-source]').text()).toContain('Chưa rõ nguồn')
    expect(seasonal.get('[data-freshness-line]').text()).toContain('Chưa rõ thời điểm cập nhật')
  })

  it('orders catalog orientation, decisions, results, evidence, and continuation using row/tile contracts', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())

    const wrapper = await mountSuspended(TourismPage, { global: { stubs: catalogStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.findAll('[data-catalog-section]').map(node => node.attributes('data-catalog-section'))).toEqual([
      'orientation',
      'filters',
      'results',
      'evidence',
      'continuation',
    ])

    const contracts = wrapper.get('[data-catalog-section="results"]').findAll('[data-entity-contract]')
    expect(contracts).toHaveLength(2)
    expect(contracts.map(item => item.attributes('data-entity-contract')).sort()).toEqual(['entity-row', 'entity-tile'])
    expect(wrapper.find('[data-catalog-interstitial]').exists()).toBe(false)
    expect(wrapper.find('.atlas-hero-stats').exists()).toBe(false)

    const evidence = wrapper.get('[data-catalog-section="evidence"]')
    expect(evidence.findAll('[data-source-mark]').length).toBeGreaterThan(0)
    expect(evidence.findAll('[data-freshness-line]').length).toBeGreaterThan(0)

    const continuationLinks = wrapper.get('[data-catalog-section="continuation"]').findAll('a')
    expect(continuationLinks.map(link => link.attributes('href'))).toEqual(['/ban-do', '/lich-trinh'])
  })

  it('hydrates catalog orientation from the effective deep-linked type filter', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())

    const wrapper = await mountSuspended(TourismPage, {
      route: '/du-lich?type=accommodation',
      global: { stubs: catalogStubs },
    })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-route-node-active]').text()).toContain('Lưu trú')
    expect(wrapper.get('.mode-pill[aria-pressed="true"]').text()).toContain('Lưu trú')
    expect(wrapper.get('[data-catalog-section="results"]').text()).toContain('Nhà vườn Cù Lao An Bình')
    expect(wrapper.get('[data-catalog-section="results"]').text()).not.toContain('Làng gốm Mang Thít')
  })

  it('uses text and line icons for catalog decisions instead of structural emoji or glyph buttons', async () => {
    apiFetchMock.mockResolvedValue(catalogFixture())

    const wrapper = await mountSuspended(TourismPage, { global: { stubs: catalogStubs } })
    wrappers.push(wrapper)
    await flushUi()

    for (const button of wrapper.findAll('.mode-pill')) {
      expect(button.text()).not.toMatch(/\p{Extended_Pictographic}/u)
      expect(button.find('[data-icon]').exists()).toBe(true)
    }
    for (const button of wrapper.findAll('.vt-btn')) {
      expect(button.text().trim()).toBe('')
      expect(button.find('[data-icon]').exists()).toBe(true)
    }
  })
})
