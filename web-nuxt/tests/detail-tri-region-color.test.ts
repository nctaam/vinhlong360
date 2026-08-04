import { clearNuxtData, clearNuxtState, useState } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ContactWidget from '../components/ContactWidget.vue'
import EntityTrustPanel from '../components/EntityTrustPanel.vue'
import { useAuthModal } from '../composables/useAuthModal'
import EntityDetailPage from '../pages/dia-diem/[id].vue'
import { aiDisclosure } from '../utils/aiDisclosure'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const triRegionCss = readFileSync(resolve(process.cwd(), 'assets/css/tri-region-color.css'), 'utf8')
const detailCss = readFileSync(resolve(process.cwd(), 'assets/css/detail.css'), 'utf8')
const variablesCss = readFileSync(resolve(process.cwd(), 'assets/css/variables.css'), 'utf8')
const shellCss = readFileSync(resolve(process.cwd(), 'assets/css/shell.css'), 'utf8')
const contactWidgetSource = readFileSync(resolve(process.cwd(), 'components/ContactWidget.vue'), 'utf8')

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

const heroDescriptor = {
  url: '/img/entities/cong-vien-an-hoi.webp',
  alt: 'Cong vien An Hoi ben song',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: aiDisclosure.entity_ai.short_label,
  full_disclosure: aiDisclosure.entity_ai.full_disclosure,
  credit: null,
  width: 800,
  height: 533,
} as const

const remoteHeroDescriptor = {
  ...heroDescriptor,
  url: 'https://cdn.example/cong-vien-an-hoi.webp',
  alt: 'Cong vien An Hoi tu CDN',
} as const

function detailEntity(id: string, name: string, images: string[] = []) {
  return {
    id,
    type: 'attraction',
    name,
    summary: `Khong gian ${name} tai Vinh Long.`,
    description: `Thong tin chi tiet ve ${name}.`,
    place_name: 'Phuong Thanh Duc',
    attributes: {},
    images,
  }
}

type DetailRouteFixture = {
  entity: ReturnType<typeof detailEntity> | Promise<ReturnType<typeof detailEntity>>
  images: readonly unknown[] | Promise<readonly unknown[]>
}

const defaultDetailFixtures: Record<string, DetailRouteFixture> = {
  'cong-vien-an-hoi': {
    entity: detailEntity('cong-vien-an-hoi', 'Cong vien An Hoi'),
    images: [heroDescriptor],
  },
}

function stubHeroImageState(initial: { complete: boolean; naturalWidth: number; naturalHeight: number }) {
  const state = { ...initial }
  vi.spyOn(HTMLImageElement.prototype, 'complete', 'get').mockImplementation(() => state.complete)
  vi.spyOn(HTMLImageElement.prototype, 'naturalWidth', 'get').mockImplementation(() => state.naturalWidth)
  vi.spyOn(HTMLImageElement.prototype, 'naturalHeight', 'get').mockImplementation(() => state.naturalHeight)
  return {
    update(next: Partial<typeof state>) {
      Object.assign(state, next)
    },
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((fulfill) => { resolve = fulfill })
  return { promise, resolve }
}

async function mountDetailHero(options: {
  route?: string
  fixtures?: Record<string, DetailRouteFixture>
} = {}) {
  const fixtures = options.fixtures || defaultDetailFixtures
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path.startsWith('/seo/jsonld/')) return Promise.resolve(null)
    const match = path.match(/^\/api\/entities\/([^/?]+)(?:\/(gallery|relationships))?/)
    if (match) {
      const fixture = fixtures[decodeURIComponent(match[1] || '')]
      if (match[2] === 'gallery') return Promise.resolve(fixture?.images || []).then(images => ({ images }))
      if (match[2] === 'relationships') return Promise.resolve({ relationships: [], total: 0 })
      if (fixture) return Promise.resolve(fixture.entity)
    }
    return Promise.resolve({})
  })

  const wrapper = await mountSuspended(EntityDetailPage, {
    route: options.route || '/dia-diem/cong-vien-an-hoi',
    global: {
      stubs: {
        NuxtImg: NuxtImgStub,
        Breadcrumb: true,
        SaveButton: true,
        ShareButton: true,
        IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
        EntityMap: true,
        EntityFeed: true,
        ReviewSection: true,
        JourneyBar: true,
        AIBestTime: true,
        ContactWidget: true,
        LazyContactWidget: true,
      },
    },
  })
  wrappers.push(wrapper)
  await flushUi()
  return wrapper
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

async function cleanupDetailTestState() {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  apiFetchMock.mockReset()
  await clearNuxtData()
  clearNuxtState('auth-user')
  const { openAuth, closeAuth } = useAuthModal()
  openAuth()
  closeAuth()
}

afterEach(cleanupDetailTestState)

describe('entity detail tri-region behavior', () => {
  it('hides a loaded hero while a reused detail navigation is still resolving', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-a': { entity: detailEntity('hero-a', 'Hero A', [heroDescriptor.url]), images: [heroDescriptor] },
        'hero-b': { entity: detailEntity('hero-b', 'Hero B'), images: [] },
      },
      route: '/dia-diem/hero-a',
    })
    const navigationGate = deferred<void>()
    let navigationReachedResolveGuard = false
    const removeGuard = wrapper.vm.$router.beforeResolve(async (to) => {
      if (to.path !== '/dia-diem/hero-b') return
      navigationReachedResolveGuard = true
      await navigationGate.promise
    })

    const navigation = wrapper.vm.$router.push('/dia-diem/hero-b')
    try {
      await vi.waitFor(() => expect(navigationReachedResolveGuard).toBe(true))
      await nextTick()

      expect(wrapper.vm.$router.currentRoute.value.path).toBe('/dia-diem/hero-a')
      expect(wrapper.get('h1').text()).toBe('Hero A')
      const pendingHero = wrapper.get<HTMLElement>('[data-entity-hero] .dc-bg')
      expect(pendingHero.classes()).not.toContain('loaded')
      expect(pendingHero.element.style.opacity).toBe('0')
      expect(pendingHero.element.style.transition).toBe('none')
    } finally {
      navigationGate.resolve()
      await navigation
      removeGuard()
    }
  })

  it('keeps a loaded hero visible through same-entity query-only and hash-only navigation', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-a': { entity: detailEntity('hero-a', 'Hero A', [heroDescriptor.url]), images: [heroDescriptor] },
      },
      route: '/dia-diem/hero-a',
    })

    for (const target of ['/dia-diem/hero-a?view=map', '/dia-diem/hero-a?view=map#entity-image-disclosure-hero-a-hero']) {
      await wrapper.vm.$router.push(target)
      await flushUi()

      const hero = wrapper.get<HTMLElement>('[data-entity-hero] .dc-bg')
      expect(hero.classes()).toContain('loaded')
      expect(hero.element.style.opacity).toBe('')
      expect(hero.element.style.transition).toBe('')
    }
  })

  it('restores the current valid hero when a later guard aborts entity navigation', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-a': { entity: detailEntity('hero-a', 'Hero A', [heroDescriptor.url]), images: [heroDescriptor] },
        'hero-b': { entity: detailEntity('hero-b', 'Hero B'), images: [] },
      },
      route: '/dia-diem/hero-a',
    })
    const removeAbortGuard = wrapper.vm.$router.beforeEach((to) => {
      if (to.path === '/dia-diem/hero-b') return false
    })

    try {
      await wrapper.vm.$router.push('/dia-diem/hero-b')
      await flushUi()

      expect(wrapper.vm.$router.currentRoute.value.path).toBe('/dia-diem/hero-a')
      expect(wrapper.get('h1').text()).toBe('Hero A')
      const hero = wrapper.get<HTMLElement>('[data-entity-hero] .dc-bg')
      expect(hero.classes()).toContain('loaded')
      expect(hero.element.style.opacity).toBe('')
      expect(hero.element.style.transition).toBe('')
    } finally {
      removeAbortGuard()
    }
  })

  it('restores the current valid hero when entity navigation redirects back to it', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-a': { entity: detailEntity('hero-a', 'Hero A', [heroDescriptor.url]), images: [heroDescriptor] },
        'hero-b': { entity: detailEntity('hero-b', 'Hero B'), images: [] },
      },
      route: '/dia-diem/hero-a',
    })
    const removeRedirectGuard = wrapper.vm.$router.beforeEach((to) => {
      if (to.path === '/dia-diem/hero-b') return '/dia-diem/hero-a?redirected=1'
    })

    try {
      await wrapper.vm.$router.push('/dia-diem/hero-b')
      await flushUi()

      expect(wrapper.vm.$router.currentRoute.value.fullPath).toBe('/dia-diem/hero-a?redirected=1')
      expect(wrapper.get('h1').text()).toBe('Hero A')
      const restoredHero = wrapper.get<HTMLElement>('[data-entity-hero] .dc-bg')
      expect(restoredHero.classes()).toContain('loaded')
      expect(restoredHero.element.style.opacity).toBe('')
      expect(restoredHero.element.style.transition).toBe('')
    } finally {
      removeRedirectGuard()
    }

    const navigationGate = deferred<void>()
    let navigationReachedResolveGuard = false
    const removeResolveGuard = wrapper.vm.$router.beforeResolve(async (to) => {
      if (to.path !== '/dia-diem/hero-b') return
      navigationReachedResolveGuard = true
      await navigationGate.promise
    })
    const nextNavigation = wrapper.vm.$router.push('/dia-diem/hero-b')

    try {
      await vi.waitFor(() => expect(navigationReachedResolveGuard).toBe(true))
      await nextTick()

      const pendingHero = wrapper.get<HTMLElement>('[data-entity-hero] .dc-bg')
      expect(pendingHero.classes()).not.toContain('loaded')
      expect(pendingHero.element.style.opacity).toBe('0')
      expect(pendingHero.element.style.transition).toBe('none')
    } finally {
      navigationGate.resolve()
      await nextNavigation
      removeResolveGuard()
    }
  })

  it('clears a loaded hero when the reused detail page switches to an incomplete failed image', async () => {
    const imageState = stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const nextEntity = deferred<ReturnType<typeof detailEntity>>()
    const nextImages = deferred<readonly unknown[]>()
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-a': { entity: detailEntity('hero-a', 'Hero A', [heroDescriptor.url]), images: [heroDescriptor] },
        'hero-b': { entity: nextEntity.promise, images: nextImages.promise },
      },
      route: '/dia-diem/hero-a',
    })
    expect(wrapper.get('[data-entity-hero] .dc-bg').classes()).toContain('loaded')

    imageState.update({ complete: false, naturalWidth: 0, naturalHeight: 0 })
    await wrapper.vm.$router.push('/dia-diem/hero-b')
    await nextTick()
    const stayedLoadedWhileNextHeroWasPending = wrapper.get('[data-entity-hero] .dc-bg').classes().includes('loaded')

    nextEntity.resolve(detailEntity('hero-b', 'Hero B', [heroDescriptor.url]))
    nextImages.resolve([heroDescriptor])
    await flushUi()
    await flushUi()

    const failedImage = wrapper.get<HTMLImageElement>('[data-entity-hero] .dc-bg')
    expect(stayedLoadedWhileNextHeroWasPending).toBe(false)
    expect(wrapper.get('h1').text()).toBe('Hero B')
    expect(failedImage.attributes('alt')).toBe(heroDescriptor.alt)
    expect(failedImage.classes()).not.toContain('loaded')
    expect(failedImage.element.style.opacity).toBe('0')
    expect(failedImage.element.style.transition).toBe('none')

    imageState.update({ complete: true })
    await failedImage.trigger('load')
    expect(failedImage.classes()).not.toContain('loaded')
    expect(failedImage.element.style.opacity).toBe('0')
    expect(failedImage.element.style.transition).toBe('none')
  })

  it('reveals a cached remote NuxtImg when it replaces a placeholder after client navigation', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-placeholder': { entity: detailEntity('hero-placeholder', 'Hero Placeholder'), images: [] },
        'hero-remote': { entity: detailEntity('hero-remote', 'Hero Remote'), images: [remoteHeroDescriptor] },
      },
      route: '/dia-diem/hero-placeholder',
    })
    expect(wrapper.find('[data-entity-hero] .dc-bg').exists()).toBe(false)

    await wrapper.vm.$router.push('/dia-diem/hero-remote')
    await flushUi()
    await flushUi()

    const remoteImage = wrapper.get<HTMLImageElement>('[data-entity-hero] .dc-bg')
    expect(wrapper.get('h1').text()).toBe('Hero Remote')
    expect(remoteImage.attributes('src')).toBe(remoteHeroDescriptor.url)
    expect(remoteImage.classes()).toContain('loaded')
    expect(remoteImage.element.style.opacity).toBe('')
    expect(remoteImage.element.style.transition).toBe('')
    expect(wrapper.get(`#${remoteImage.attributes('aria-describedby')}`).text()).toBe(remoteHeroDescriptor.full_disclosure)
  })

  it('resolves the cached remote NuxtImg component ref through its rendered image element', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    const wrapper = await mountDetailHero({
      fixtures: {
        'hero-remote': { entity: detailEntity('hero-remote', 'Hero Remote'), images: [remoteHeroDescriptor] },
      },
      route: '/dia-diem/hero-remote',
    })
    const remoteImage = wrapper.get<HTMLImageElement>('[data-entity-hero] .dc-bg')

    expect(remoteImage.attributes('src')).toBe(remoteHeroDescriptor.url)
    expect(remoteImage.classes()).toContain('loaded')
    expect(remoteImage.element.style.opacity).toBe('')
    expect(remoteImage.element.style.transition).toBe('')
  })

  it('reveals a successfully cached hero after mount without a new load event', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 800, naturalHeight: 533 })

    const wrapper = await mountDetailHero()
    const image = wrapper.get<HTMLImageElement>('[data-entity-hero] .dc-bg')
    const disclosureId = image.attributes('aria-describedby')

    expect(image.classes()).toContain('loaded')
    expect(image.element.style.opacity).toBe('')
    expect(image.element.style.transition).toBe('')
    expect(image.attributes('alt')).toBe(heroDescriptor.alt)
    expect(wrapper.get(`#${disclosureId}`).text()).toBe(heroDescriptor.full_disclosure)
  })

  it('reveals the hero when a successful load event arrives after hydration', async () => {
    const imageState = stubHeroImageState({ complete: false, naturalWidth: 0, naturalHeight: 0 })
    const wrapper = await mountDetailHero()
    const image = wrapper.get<HTMLImageElement>('[data-entity-hero] .dc-bg')

    expect(image.classes()).not.toContain('loaded')
    expect(image.element.style.opacity).toBe('0')
    expect(image.element.style.transition).toBe('none')
    imageState.update({ complete: true, naturalWidth: 800, naturalHeight: 533 })
    await image.trigger('load')

    expect(image.classes()).toContain('loaded')
    expect(image.element.style.opacity).toBe('')
    expect(image.element.style.transition).toBe('')
  })

  it('keeps hero actions labelled, ordered and independently clickable through follow state changes', async () => {
    useState('auth-user').value = { id: 'user-1', has_password: true }
    vi.stubGlobal('$fetch', vi.fn(async (input: unknown) => {
      const path = String(input)
      if (path.includes('/api/me/visits/check/')) return { status: null }
      if (path === '/api/following') return { following: [] }
      if (path === '/auth/csrf') return { csrf_token: 'test-csrf' }
      return {}
    }))

    const wrapper = await mountDetailHero()
    const actions = wrapper.findAll('.detail-cover button').filter(button =>
      button.classes().includes('trip-btn') || button.classes().includes('dc-photo-btn'))

    expect(actions.map(action => action.text())).toEqual([
      '✓ Đã đến',
      '♡ Muốn đến',
      '🔔 Theo dõi',
      '📷 Xem ảnh',
    ])

    const follow = wrapper.findAll('.trip-btn').find(button => button.text().includes('Theo dõi'))!
    expect(follow.attributes('aria-pressed')).toBe('false')
    expect(document.body.querySelector('[role="dialog"][aria-label="Xem ảnh"]')).toBeNull()

    await follow.trigger('click')
    await flushUi()

    expect(follow.attributes('aria-pressed')).toBe('true')
    expect(follow.text()).toBe('🔔 Đang theo dõi')
    expect(document.body.querySelector('[role="dialog"][aria-label="Xem ảnh"]')).toBeNull()

    await wrapper.get('.dc-photo-btn').trigger('click')
    await flushUi()

    const dialog = document.body.querySelector('[role="dialog"][aria-label="Xem ảnh"]')
    expect(dialog).not.toBeNull()
    expect(dialog?.querySelector('[data-active-media]')?.getAttribute('alt')).toBe(heroDescriptor.alt)
    expect(follow.attributes('aria-pressed')).toBe('true')
    expect(follow.text()).toBe('🔔 Đang theo dõi')
  })

  it('clears seeded auth-user and guest auth-modal state without wiping unrelated Nuxt state', async () => {
    clearNuxtState('auth-user')
    const authUser = useState('auth-user')
    const authModalOpen = useState('auth-modal-open', () => false)
    const unrelated = useState('detail-cleanup-sentinel', () => 'keep')
    authModalOpen.value = false
    unrelated.value = 'keep'

    try {
      const wrapper = await mountDetailHero()
      const follow = wrapper.findAll('.trip-btn').find(button => button.text().includes('Theo dõi'))!
      await follow.trigger('click')
      await flushUi()

      expect(authModalOpen.value).toBe(true)
      expect(follow.attributes('aria-pressed')).toBe('false')
      expect(follow.text()).toBe('🔔 Theo dõi')

      authUser.value = { id: 'cleanup-leak-user', has_password: true }
      await cleanupDetailTestState()

      expect.soft(authUser.value).toBeUndefined()
      expect.soft(unrelated.value).toBe('keep')
      expect.soft(authModalOpen.value).toBe(false)

      authModalOpen.value = false
      useAuthModal().onLoginSuccess()
      await flushUi()

      expect(authModalOpen.value).toBe(false)
    } finally {
      clearNuxtState('auth-user')
      clearNuxtState('auth-modal-open')
      clearNuxtState('detail-cleanup-sentinel')
    }
  })

  it('reserves the photo-action row continuously below the naturally clear 769px width', () => {
    const mobileInnerRule = detailCss.match(/@media \(max-width: 480px\) \{[\s\S]*?\.has-cover-img \.dc-inner\s*\{([^}]*)\}/)
    const continuousReservationRule = detailCss.match(/@media \(width < 769px\)\s*\{\s*\.has-cover-img \.dc-inner\s*\{([^}]*)\}/)
    const tripRule = detailCss.match(/\.dc-trip\s*\{([^}]*)\}/)

    expect(tripRule?.[1]).toMatch(/flex-wrap:\s*wrap/)
    expect(continuousReservationRule?.[1]).toMatch(/padding-bottom:\s*calc\(44px \+ var\(--space-6\)\)/)
    expect(mobileInnerRule?.[1]).not.toMatch(/padding-bottom:/)
  })

  it('lets the Detail main grid item shrink inside its assigned track', () => {
    const mainRule = detailCss.match(/\.detail-main\s*\{([^}]*)\}/)

    expect(mainRule?.[1]).toMatch(/(?:^|;)\s*min-width\s*:\s*(?:0|0px)\s*(?:;|$)/)
  })

  it('does not reveal a completed hero whose natural width is zero', async () => {
    stubHeroImageState({ complete: true, naturalWidth: 0, naturalHeight: 0 })
    const wrapper = await mountDetailHero()
    const image = wrapper.get<HTMLImageElement>('[data-entity-hero] .dc-bg')

    await image.trigger('load')

    expect(image.classes()).not.toContain('loaded')
    expect(image.element.style.opacity).toBe('0')
    expect(image.element.style.transition).toBe('none')
    expect(wrapper.get(`#${image.attributes('aria-describedby')}`).text()).toBe(heroDescriptor.full_disclosure)
  })

  it('separates official provenance, stale severity and report action', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'official',
        sourceTitle: 'Cổng thông tin tỉnh Vĩnh Long',
        sourceUrl: 'https://example.gov.vn/source',
        freshnessStatus: 'stale',
        updatedLabel: '12/07/2026',
        note: 'Thông tin có thể đã cũ; hãy kiểm tra trước khi đi.',
        reportTo: '/cong-dong?report=entity-1',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Có thể đã cũ')
    expect(wrapper.get('[data-source-link]').text()).toContain('Cổng thông tin tỉnh Vĩnh Long')
    expect(wrapper.get('[data-report-action]').attributes('href')).toBe('/cong-dong?report=entity-1')
  })

  it('keeps invalid source URLs as labels instead of unsafe links', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'unknown',
        sourceTitle: 'Nguồn chưa được xác minh',
        sourceUrl: 'javascript:alert(1)',
        freshnessStatus: 'unknown',
        updatedLabel: '',
        note: 'Hãy kiểm tra trước khi sử dụng thông tin.',
        reportTo: '/cong-dong?report=entity-unsafe',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.find('[data-source-link]').exists()).toBe(false)
    expect(wrapper.get('[data-source-label]').text()).toBe('Nguồn chưa được xác minh')
    expect(wrapper.get('[data-report-action]').attributes('href')).toBe('/cong-dong?report=entity-unsafe')
  })

  it('keeps the direct-contact model and semantic action order', async () => {
    const wrapper = await mountSuspended(ContactWidget, {
      props: {
        entity: {
          id: 'entity-1',
          name: 'Nhà vườn ven sông',
          attributes: { zalo: '0900000000', phone: '0900000000' },
        },
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    const actions = wrapper.findAll('.cw-btn')
    expect(actions.map(action => action.text())).toEqual(['Nhắn Zalo', 'Gọi điện'])
    expect(actions[0]!.attributes('data-color-role')).toBe('action-primary')
    expect(actions[1]!.attributes('data-color-role')).toBe('action-secondary')
    expect(wrapper.text()).not.toContain('Đặt ngay')
    expect(wrapper.text()).not.toContain('Thanh toán')
  })

  it('reserves one semantic mobile bottom-nav height beneath the contextual contact bar', () => {
    expect(variablesCss).toMatch(/--shell-public-bottom-nav-reserved-height\s*:/)
    expect(shellCss).toMatch(/\.public-bottom-nav\s*\{[\s\S]*?min-height:\s*var\(--shell-public-bottom-nav-reserved-height\)/)
    expect(shellCss).toMatch(/@media \(max-width:\s*767px\)[\s\S]*?\.public-bottom-nav\s*\{[\s\S]*?display:\s*grid/)
    expect(contactWidgetSource).toMatch(/@media \(max-width:\s*767px\)[\s\S]*?\.cw\s*\{[\s\S]*?bottom:\s*var\(--shell-public-bottom-nav-reserved-height\)/)
    expect(contactWidgetSource).not.toMatch(/@media \(max-width:\s*767px\)[\s\S]*?\.cw\s*\{[^}]*padding:[^;]*safe-area-inset-bottom/)
    expect(shellCss).toMatch(/:has\(\.detail-contact-widget\)[\s\S]*?--shell-mobile-fixed-stack-reserved-height/)
  })

  it('mounts detail data and keeps material, trust and image disclosure as separate layers', async () => {
    const entity = {
      id: 'entity-1',
      type: 'craft_village',
      name: 'Làng gốm Mang Thít',
      summary: 'Không gian nghề gốm ven sông.',
      description: 'Một làng nghề lâu đời bên dòng Cổ Chiên.',
      place_name: 'Mang Thít',
      attributes: { zalo: '0900000000', phone: '0900000000', address: 'Mang Thít, Vĩnh Long' },
      coordinates: { lat: 10.211, lng: 106.116 },
      quality: {
        source_tier: 'official',
        source_title: 'Cổng thông tin tỉnh Vĩnh Long',
        source_url: 'https://example.gov.vn/source',
      },
      source_freshness: {
        source_title: 'Cổng thông tin tỉnh Vĩnh Long',
        source_url: 'https://example.gov.vn/source',
        freshness_status: 'fresh',
        updated_at: '2026-07-30T00:00:00Z',
      },
    }
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/entities/entity-1') return Promise.resolve(entity)
      if (path === '/api/entities/entity-1/gallery') return Promise.resolve({ images: [] })
      if (path === '/seo/jsonld/entity-1') return Promise.resolve(null)
      if (path.startsWith('/api/entities/entity-1/relationships')) return Promise.resolve({ relationships: [], total: 0 })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(EntityDetailPage, {
      route: '/dia-diem/entity-1',
      global: {
        stubs: {
          NuxtImg: NuxtImgStub,
          Breadcrumb: true,
          SaveButton: true,
          ShareButton: true,
          IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
          EntityMap: true,
          EntityFeed: true,
          ReviewSection: true,
          JourneyBar: true,
          AIBestTime: true,
          ContactWidget: true,
          LazyContactWidget: true,
        },
      },
    })
    wrappers.push(wrapper)
    await flushUi()

    const root = wrapper.get('[data-page-recipe="detail"]')
    expect(root.attributes('data-material-accent')).toBe('clay')
    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Mới cập nhật')
    expect(wrapper.get('[data-image-disclosure]').text()).not.toContain('Chính thức')
    expect(wrapper.get('[data-entity-trust-panel]').text()).not.toContain('Ảnh minh họa')

    const highlightActions = wrapper.findAll('.highlights .hl-action')
    expect(highlightActions.map(action => action.text())).toEqual(['💬 Zalo', '📞 Gọi', '🗺️ Bản đồ'])
    expect(highlightActions.map(action => action.attributes('data-color-role'))).toEqual([
      'action-primary',
      'action-secondary',
      'action-secondary',
    ])

    const stickyActions = wrapper.findAll('.sticky-cta-bar a')
    expect(stickyActions.map(action => action.text())).toEqual(['💬 Zalo', '📞 Gọi', '🗺️ Bản đồ'])
    expect(stickyActions.map(action => action.attributes('data-color-role'))).toEqual([
      'action-primary',
      'action-secondary',
      'action-secondary',
    ])
  })

  it('generates the material border pseudo-element for every detail hero', () => {
    const heroRule = triRegionCss.match(/\[data-color-system="tri-region-v1"\]\[data-page-recipe="detail"\] \.detail-cover::after\s*\{([^}]*)\}/)

    expect(heroRule?.[1]).toMatch(/content:\s*""/)
    expect(heroRule?.[1]).toMatch(/position:\s*absolute/)
    expect(heroRule?.[1]).toMatch(/border-block-end:\s*3px solid var\(--tri-region-material-accent\)/)
  })

  it('keeps the required page class without inheriting the legacy constrained layout', () => {
    const rootRule = triRegionCss.match(/\[data-color-system="tri-region-v1"\]\[data-page-recipe="detail"\]\.page\.entity-detail\s*\{([^}]*)\}/)

    expect(rootRule?.[1]).toMatch(/max-width:\s*none/)
    expect(rootRule?.[1]).toMatch(/margin:\s*0/)
    expect(rootRule?.[1]).toMatch(/padding:\s*0/)
  })
})
