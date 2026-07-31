import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../pages/index.vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const EmptyStateStub = defineComponent({
  props: { title: String, message: String },
  template: '<div data-empty-state><strong>{{ title }}</strong><span>{{ message }}</span><slot name="actions" /></div>',
})
const pageStubs = {
  NuxtImg: NuxtImgStub,
  EmptyState: EmptyStateStub,
  EntityCard: { props: ['entity'], template: '<article data-entity-card>{{ entity.name }}</article>' },
  EntityFeature: { template: '<section data-existing-entity-feature />' },
  StorySpread: { template: '<section data-existing-story-spread />' },
  HeroIllustration: true,
  IconLine: true,
  JourneyActionRail: true,
  SearchAutocomplete: { template: '<div data-home-search />' },
  SkeletonGrid: true,
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => apiFetchMock.mockReset())
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
  document.documentElement.classList.remove('dark', 'light')
})

function homeFixture() {
  return {
    month: 8,
    seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
    experiences: [
      { id: 'experience-1', name: 'Vườn ven sông', type: 'experience', summary: 'Đi giữa vườn cây.', images: ['/img/entities/experience-1.webp'] },
      { id: 'experience-2', name: 'Làng nghề gốm', type: 'experience', summary: 'Nghe chuyện người thợ.', images: ['/img/entities/experience-2.webp'] },
    ],
    products: [{ id: 'product-1', name: 'Gốm đỏ Mang Thít', type: 'product', summary: 'Một câu chuyện vật liệu.' }],
    upcoming_events: [
      { id: 'event-1', name: 'Lễ hội sông nước', days_until: 1, attributes: { date_start: '2026-08-01' } },
      { id: 'event-2', name: 'Đêm đờn ca', days_until: 4, attributes: { date_start: '2026-08-04' } },
    ],
    seasonal: [
      { id: 'season-1', name: 'Chôm chôm Bình Hòa Phước', type: 'product' },
      { id: 'season-2', name: 'Bưởi Năm Roi', type: 'product' },
    ],
    top_dishes: [
      { id: 'dish-1', name: 'Cá tai tượng chiên xù', attributes: { rating: 4.8, review_count: 12 } },
      { id: 'dish-2', name: 'Bánh xèo hến', attributes: { rating: 4.6, review_count: 8 } },
    ],
    itineraries: [{ id: 'plan-1', title: 'Một ngày ven sông' }],
    area_counts: { 'long-ho': 2, 'mang-thit': 1 },
  }
}

describe('homepage Existing Screen Evolution B1', () => {
  it('renders the controlled top zone and removes decision items from following collections', async () => {
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

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-home-pilot="nocturne-b1"]')).toBeTruthy()
    expect(wrapper.get('[data-home-feature-dossier]').text()).toContain('Vườn ven sông')
    expect(wrapper.find('.hero-kenburns').exists()).toBe(false)
    const decisions = wrapper.findAll('[data-home-decision-entry]')
    expect(decisions.map(row => row.get('.home-decision-ledger__title').text())).toEqual([
      'Có lịch gần nhất',
      'Đang vào mùa',
      'Ăn gì hôm nay',
      'Đi theo lộ trình có sẵn',
    ])
    expect(decisions.map(row => row.get('.home-decision-ledger__text').text())).toEqual([
      'Lễ hội sông nước',
      'Chôm chôm Bình Hòa Phước',
      'Cá tai tượng chiên xù',
      'Một ngày ven sông',
    ])
    const temporal = wrapper.get('[data-home-section="events-seasonal"]')
    expect(temporal.text()).toContain('Đêm đờn ca')
    expect(temporal.text()).not.toContain('Lễ hội sông nước')
    expect(wrapper.findAll('[data-entity-card]').map(card => card.text())).toEqual(['Bưởi Năm Roi'])
    expect(wrapper.text()).toContain('Bánh xèo hến')
  })
})
