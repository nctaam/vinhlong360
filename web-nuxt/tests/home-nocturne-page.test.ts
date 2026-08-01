import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../pages/index.vue'
import { installActualHomepageStyles } from './helpers/installHomepageStyles'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const wrappers: Array<{ unmount: () => void }> = []
const stylesheets: HTMLStyleElement[] = []
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

beforeEach(() => {
  apiFetchMock.mockReset()
  localStorage.clear()
})
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  for (const stylesheet of stylesheets.splice(0)) stylesheet.remove()
  await clearNuxtData()
  document.documentElement.classList.remove('dark', 'light')
})

function homeFixture() {
  return {
    month: 8,
    seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
    experiences: [
      { id: 'experience-1', name: 'Vườn ven sông', type: 'experience', summary: 'Đi giữa vườn cây.', images: ['/img/entities/experience-1.webp'], quality: undefined as { source_tier?: string } | undefined },
      { id: 'experience-2', name: 'Làng nghề gốm', type: 'experience', summary: 'Nghe chuyện người thợ.', images: ['/img/entities/experience-2.webp'], quality: undefined as { source_tier?: string } | undefined },
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

type Rgba = [number, number, number, number]

function rgba(value: string): Rgba {
  if (value === 'transparent') return [0, 0, 0, 0]
  const hex = /^#([0-9a-f]{6})$/i.exec(value)
  if (hex) {
    const number = Number.parseInt(hex[1]!, 16)
    return [(number >> 16) & 255, (number >> 8) & 255, number & 255, 1]
  }
  const match = /rgba?\(\s*([0-9.]+)[, ]+([0-9.]+)[, ]+([0-9.]+)(?:\s*[,/]\s*([0-9.]+))?/.exec(value)
  if (!match) throw new Error(`Expected computed RGB(A) color, received: ${value}`)
  return [Number(match[1]), Number(match[2]), Number(match[3]), match[4] === undefined ? 1 : Number(match[4])]
}

function composite(foreground: Rgba, background: Rgba): Rgba {
  const alpha = foreground[3] + background[3] * (1 - foreground[3])
  if (alpha === 0) return [0, 0, 0, 0]
  return [
    (foreground[0] * foreground[3] + background[0] * background[3] * (1 - foreground[3])) / alpha,
    (foreground[1] * foreground[3] + background[1] * background[3] * (1 - foreground[3])) / alpha,
    (foreground[2] * foreground[3] + background[2] * background[3] * (1 - foreground[3])) / alpha,
    alpha,
  ]
}

function luminance(color: Rgba) {
  const channels = color.slice(0, 3).map((channel) => {
    const normalized = channel / 255
    return normalized <= .04045 ? normalized / 12.92 : ((normalized + .055) / 1.055) ** 2.4
  })
  return .2126 * channels[0]! + .7152 * channels[1]! + .0722 * channels[2]!
}

function contrast(foreground: Rgba, background: Rgba) {
  const a = luminance(foreground)
  const b = luminance(background)
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05)
}

describe('homepage Existing Screen Evolution B1', () => {
  it.each([
    { theme: 'light', canvas: [249, 247, 241, 1] as Rgba },
    { theme: 'dark', canvas: [7, 18, 16, 1] as Rgba },
  ])('renders the real hero subtitle with an accessible on-media plate in $theme', async ({ theme, canvas }) => {
    document.documentElement.classList.add(theme)
    stylesheets.push(await installActualHomepageStyles({ srgbFallback: true }))
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

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs }, attachTo: document.body })
    wrappers.push(wrapper)
    await flushUi()

    const root = wrapper.get<HTMLElement>('[data-home-pilot="nocturne-b1"]')
    const subtitle = wrapper.get<HTMLElement>('.hero-sub')
    const rootBackground = rgba(getComputedStyle(root.element).backgroundColor)
    const subtitleStyle = getComputedStyle(subtitle.element)
    const subtitleText = rgba(subtitleStyle.color)
    const subtitlePlate = rgba(subtitleStyle.backgroundColor)
    const renderedPlate = composite(subtitlePlate, rootBackground)

    expect(subtitle.text()).toContain('Tìm điểm đến')
    expect(rootBackground).toEqual(canvas)
    expect(subtitleText).toEqual([253, 252, 249, 1])
    expect(subtitlePlate.slice(0, 3)).toEqual([0, 0, 0])
    expect(subtitlePlate[3]).toBeGreaterThanOrEqual(.72)
    expect(contrast(subtitleText, renderedPlate)).toBeGreaterThanOrEqual(4.5)
  })

  it.each([
    { theme: 'light', text: [8, 26, 22, 1] as Rgba, canvas: [249, 247, 241, 1] as Rgba, error: '#BD413F' },
    { theme: 'dark', text: [237, 235, 229, 1] as Rgba, canvas: [7, 18, 16, 1] as Rgba, error: '#DF7F78' },
  ])('renders the real today event with semantic foreground on its transparent canvas path in $theme', async ({ theme, text, canvas, error }) => {
    document.documentElement.classList.add(theme)
    // Happy DOM cannot resolve OKLCH through var(); the executable audit covers the color-mix composite.
    stylesheets.push(await installActualHomepageStyles({ srgbFallback: true }))
    const fixture = homeFixture()
    fixture.upcoming_events[0]!.days_until = 0
    fixture.upcoming_events[1]!.days_until = 0
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(fixture)
      if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
      if (path === '/api/community/stats') return Promise.resolve(null)
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs }, attachTo: document.body })
    wrappers.push(wrapper)
    await flushUi()

    const root = wrapper.get<HTMLElement>('[data-home-pilot="nocturne-b1"]')
    const event = wrapper.get<HTMLElement>('.event-mini:has(.ec-today)')
    const today = event.get<HTMLElement>('.ec-today')
    const rootStyle = getComputedStyle(root.element)
    const rootBackground = rgba(rootStyle.backgroundColor)
    const eventBackground = rgba(getComputedStyle(event.element).backgroundColor)
    const todayStyle = getComputedStyle(today.element)

    expect(today.text()).toBe('Hôm nay!')
    expect(today.classes()).toContain('ec-today')
    expect(today.attributes('data-material-accent')).toBe('amber')
    expect(rootBackground).toEqual(canvas)
    expect(eventBackground[3]).toBe(0)
    expect(rgba(todayStyle.color)).toEqual(text)
    expect(todayStyle.boxShadow).toContain(error)
  })

  it('renders the homepage recipe with River action, Clay context and visible source tier', async () => {
    const fixture = homeFixture()
    fixture.experiences[0]!.quality = { source_tier: 'official' }
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(fixture)
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

    const root = wrapper.get('[data-color-system="tri-region-v1"]')
    expect(root.attributes('data-page-recipe')).toBe('homepage')
    expect(root.attributes('data-material-accent')).toBe('clay')
    expect(wrapper.get('[data-home-search]').attributes('data-color-role')).toBe('action-primary')
    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-source-mark]').attributes('data-source-tier')).toBe('official')
    expect(wrapper.get('[data-home-section="events-seasonal"]').attributes('data-material-accent')).toBe('amber')
    expect(wrapper.get('.ec-countdown').attributes('data-material-accent')).toBe('amber')
    expect(wrapper.get('[data-home-section="community"]').attributes('data-material-accent')).toBe('neutral')
  })

  it('shows an honest unknown source label instead of inventing verification', async () => {
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

    expect(wrapper.get('[data-source-mark]').text()).toContain('Chưa rõ nguồn')
    expect(wrapper.text()).not.toContain('Đã xác minh')
  })

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
    expect(wrapper.find('.dx-num').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Đã xác minh')
    expect(wrapper.text()).not.toContain('Nguồn:')
    const temporal = wrapper.get('[data-home-section="events-seasonal"]')
    expect(temporal.text()).toContain('Đêm đờn ca')
    expect(temporal.text()).not.toContain('Lễ hội sông nước')
    expect(wrapper.findAll('[data-entity-card]').map(card => card.text())).toEqual(['Bưởi Năm Roi'])
    expect(wrapper.text()).toContain('Bánh xèo hến')
  })

  it('keeps navigation and retry available when the homepage request fails', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.reject(new Error('homepage unavailable'))
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

    expect(wrapper.get('[data-home-search]')).toBeTruthy()
    expect(wrapper.get('[data-empty-state]').text()).toContain('Đang cập nhật nội dung')
    expect(wrapper.get('[data-empty-state] button').text()).toBe('Tải lại')
    expect(wrapper.get('[data-home-category-index]').findAll('a').map(link => link.attributes('href'))).toEqual([
      '/du-lich',
      '/kham-pha/am-thuc',
      '/ocop',
      '/le-hoi',
      '/luu-tru',
      '/lich-trinh',
      '/ban-do',
    ])
  })

  it('shows homepage loading feedback during retry even when community content is available', async () => {
    let homepageState: 'failure' | 'pending' = 'failure'
    let resolveHomepage: ((value: ReturnType<typeof homeFixture>) => void) | undefined
    const pendingHomepage = new Promise<ReturnType<typeof homeFixture>>((resolve) => {
      resolveHomepage = resolve
    })

    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') {
        return homepageState === 'failure'
          ? Promise.reject(new Error('homepage unavailable'))
          : pendingHomepage
      }
      if (path === '/api/feed?limit=10') {
        return Promise.resolve({ posts: [{ id: 'post-1', content: 'Chuyen ben song', display_name: 'An' }] })
      }
      if (path === '/api/community/stats') return Promise.resolve({ posts: 1, reviews: 0, members: 1 })
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-home-section="community"]')).toBeTruthy()
    homepageState = 'pending'
    await wrapper.get('[data-empty-state] button').trigger('click')
    await nextTick()

    const loading = wrapper.get('[data-home-section="recovery"]')
    expect(loading.find('.sk-heading').exists()).toBe(true)
    expect(wrapper.find('[data-empty-state]').exists()).toBe(false)

    resolveHomepage?.(homeFixture())
    await flushUi()
  })

  it('shows the homepage empty state even when community content is available', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') {
        return Promise.resolve({
          month: 8,
          seasonal: [],
          experiences: [],
          products: [],
          top_dishes: [],
          itineraries: [],
          upcoming_events: [],
          area_counts: {},
        })
      }
      if (path === '/api/feed?limit=10') {
        return Promise.resolve({ posts: [{ id: 'post-1', content: 'Chuyen ben song', display_name: 'An' }] })
      }
      if (path === '/api/community/stats') return Promise.resolve({ posts: 1, reviews: 0, members: 1 })
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-home-section="community"]')).toBeTruthy()
    expect(wrapper.get('[data-empty-state]').text()).toContain('Đang cập nhật nội dung')
    expect(wrapper.get('[data-empty-state]').text()).toContain('Tụi mình đang bổ sung điểm đến')
  })

  it('isolates community failure and omits personalization without a real signal', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(homeFixture())
      if (path.startsWith('/api/community/') || path === '/api/feed?limit=10') {
        return Promise.reject(new Error('community unavailable'))
      }
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-existing-entity-feature]')).toBeTruthy()
    expect(wrapper.get('[data-existing-story-spread]')).toBeTruthy()
    expect(wrapper.get('[data-home-section="spotlight-food"]')).toBeTruthy()
    expect(wrapper.get('[data-home-section="community"] a[href="/cong-dong"]')).toBeTruthy()
    expect(wrapper.find('[data-home-section="for-you"]').exists()).toBe(false)
  })

  it('preserves the stable section order across Nocturne and Daylight Parchment', async () => {
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

    document.documentElement.classList.add('dark')
    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    const stableSections = new Set([
      'hero',
      'decisions',
      'categories',
      'events-seasonal',
      'editorial-feature',
      'spotlight-food',
      'story-spread',
    ])
    const sectionOrder = () => wrapper
      .findAll('[data-home-section]')
      .map(node => node.attributes('data-home-section'))
      .filter((name): name is string => typeof name === 'string' && stableSections.has(name))

    const nocturneOrder = sectionOrder()
    document.documentElement.classList.replace('dark', 'light')
    await nextTick()
    expect(sectionOrder()).toEqual(nocturneOrder)
    expect(nocturneOrder).toEqual([
      'hero',
      'decisions',
      'categories',
      'events-seasonal',
      'editorial-feature',
      'spotlight-food',
      'story-spread',
    ])
  })

  it('does not invent rating or review status when dish signals are absent', async () => {
    const fixture = homeFixture()
    fixture.top_dishes = [
      { id: 'dish-1', name: 'Cá tai tượng chiên xù', attributes: { rating: 4.8, review_count: 12 } },
      { id: 'dish-2', name: 'Bánh xèo hến', attributes: { rating: 0, review_count: 0 } },
    ]
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(fixture)
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

    const foodLedger = wrapper.get('[data-home-section="spotlight-food"]')
    expect(foodLedger.text()).toContain('Bánh xèo hến')
    expect(foodLedger.find('.dish-rating-badge').exists()).toBe(false)
    expect(foodLedger.text()).not.toContain('Mới')
    expect(foodLedger.text()).not.toContain('0 đánh giá')
  })

  it('uses Vietnamese language for community trend context', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(homeFixture())
      if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [{ id: 'post-1', content: 'Một vòng làng gốm', display_name: 'An' }] })
      if (path === '/api/community/stats') return Promise.resolve(null)
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [{ tag: 'gốm đỏ' }] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    const community = wrapper.get('[data-home-section="community"]')
    expect(community.text()).toContain('Đang được nhắc:')
    expect(community.text()).not.toContain('Trending:')
  })
})
