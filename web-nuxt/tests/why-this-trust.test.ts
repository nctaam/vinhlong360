// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import WhyThisDrawer from '../components/WhyThisDrawer.vue'
import SourceTrustDrawer from '../components/SourceTrustDrawer.vue'
import SmartRecommendations from '../components/SmartRecommendations.vue'
import DetailPage from '../pages/dia-diem/[id].vue'
import { useAuth } from '../composables/useAuth'
import type { Entity } from '../types'
import type { RecommendationCard, RecommendationSource } from '../types/api'
import type { PreferenceSnapshot } from '../types/personalization'

const apiFetchMock = vi.hoisted(() => vi.fn())
const pageFetchMock = vi.hoisted(() => vi.fn())
const navigateToMock = vi.hoisted(() => vi.fn(() => Promise.resolve()))

vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))
mockNuxtImport('navigateTo', () => navigateToMock)
mockNuxtImport('useSiteSettings', () => () => ({
  get: (key: string, fallback?: unknown) => key === 'features.flags'
    ? { recommendation_explanations_v1: true, trust_drawer_v1: true }
    : fallback,
}))

const wrappers: Array<{ unmount: () => void }> = []
let userSequence = 0

const preferenceSnapshot = (overrides: Partial<PreferenceSnapshot> = {}): PreferenceSnapshot => ({
  region_id: 'province-vl',
  region_label: 'Vĩnh Long',
  region_scope: 'province',
  location_source: 'manual',
  location_accuracy: 'province',
  location_consent_state: 'off',
  location_enabled: false,
  personalization_enabled: true,
  explicit_interests: ['food'],
  recommendation_reset_at: null,
  consent_version: 'identity-location-trust-v1',
  revision: 2,
  ...overrides,
})

const recommendationFixture = (overrides: Partial<RecommendationCard> = {}): RecommendationCard => ({
  id: 'entity-rec-1',
  type: 'place',
  name: 'Vườn trái cây ven sông',
  summary: 'Một điểm ghé chậm rãi trong ngày.',
  attributes: {},
  relationships: [],
  relationship_total: 0,
  explanation: {
    primary_reason: 'Cùng khu vực bạn quan tâm',
    reasons: ['Cùng khu vực bạn quan tâm', 'Phù hợp với sở thích bạn đã chọn'],
    region_label: 'Vĩnh Long',
    explicit_interests: ['Ẩm thực'],
  },
  source_tier: 'official',
  freshness_status: 'fresh',
  reason_vi: 'Cùng khu vực bạn quan tâm',
  ...overrides,
})

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

async function mountSmart(loggedIn: boolean) {
  const Harness = defineComponent({
    setup() {
      const { user } = useAuth()
      user.value = loggedIn ? { id: `recommendation-user-${userSequence}` } : null
      return () => h(SmartRecommendations, { context: 'home', limit: 1 })
    },
  })
  return await mountSuspended(Harness, { attachTo: document.body })
}

async function mountSmartRecommendations(state: {
  source: RecommendationSource
  items: RecommendationCard[]
  reasons?: Record<string, string[]>
  profile?: Record<string, unknown>
}) {
  apiFetchMock.mockImplementation((url: string) => {
    if (url.startsWith('/api/me/recommendations/contextual?')) {
      return Promise.resolve({
        items: state.source === 'personalized' ? state.items : [],
        reasons: state.reasons || {},
        profile: state.profile || { signal_count: 1 },
      })
    }
    if (url.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: state.items })
    return Promise.resolve({ entities: [] })
  })
  return await mountSmart(state.source === 'personalized')
}

async function mountDetail(route: string) {
  const AuthReset = defineComponent({
    setup() {
      useAuth().user.value = null
      return () => h('div')
    },
  })
  const resetWrapper = await mountSuspended(AuthReset)
  resetWrapper.unmount()
  return await mountSuspended(DetailPage, { route, attachTo: document.body })
}

async function mountPlaceDetail(entity: Entity) {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === `/api/entities/${entity.id}`) return Promise.resolve(entity)
    if (url === `/api/entities/${entity.id}/gallery`) return Promise.resolve({ images: [] })
    if (url === `/seo/jsonld/${entity.id}`) return Promise.resolve(null)
    return Promise.resolve({})
  })
  return await mountDetail(`/dia-diem/${entity.id}`)
}

beforeEach(() => {
  userSequence += 1
  apiFetchMock.mockReset()
  apiFetchMock.mockResolvedValue({})
  pageFetchMock.mockReset()
  navigateToMock.mockClear()
  pageFetchMock.mockImplementation((url: string) => {
    if (url === '/auth/me') return Promise.resolve({ user: null })
    if (url === '/auth/csrf') return Promise.resolve({ csrf_token: 'csrf-token' })
    return Promise.resolve({})
  })
  vi.stubGlobal('$fetch', pageFetchMock)
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  while (wrappers.length) wrappers.pop()?.unmount()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
  document.body.style.overflow = ''
})

describe('SourceTrustDrawer contract', () => {
  it('refuses to assert a verified source without a valid verification date', async () => {
    const wrapper = await mountSuspended(SourceTrustDrawer, {
      props: {
        open: true,
        sourceTier: 'verified',
        sourceTitle: 'Đối tác dữ liệu',
        verifiedAt: '',
        freshnessStatus: 'fresh',
      },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.textContent).toContain('Chưa đủ bằng chứng xác minh')
    expect(dialog.textContent).not.toContain('Đã xác minh')
    expect(dialog.querySelector('[data-verification-date]')).toBeNull()
  })

  it('rejects a calendar-impossible verification timestamp', async () => {
    const wrapper = await mountSuspended(SourceTrustDrawer, {
      props: {
        open: true,
        sourceTier: 'verified',
        sourceTitle: 'Đối tác dữ liệu',
        verifiedAt: '2026-02-30T00:00:00Z',
        freshnessStatus: 'fresh',
      },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.dataset.sourceTier).toBe('unsupported-verified')
    expect(dialog.textContent).toContain('Chưa đủ bằng chứng xác minh')
    expect(dialog.querySelector('[data-verification-date]')).toBeNull()
  })

  it('asserts a verified partner only with a valid date and exposes that evidence', async () => {
    const wrapper = await mountSuspended(SourceTrustDrawer, {
      props: {
        open: true,
        sourceTier: 'verified',
        sourceTitle: 'Đối tác dữ liệu địa phương',
        sourceUrl: 'https://partner.example.vn/entity-1',
        verifiedAt: '2026-07-18T00:00:00Z',
        freshnessStatus: 'aging',
      },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.dataset.sourceTier).toBe('verified')
    expect(dialog.textContent).toContain('Đối tác xác minh kèm ngày')
    expect(dialog.querySelector('[data-verification-date] time[datetime="2026-07-18T00:00:00Z"]')).toBeTruthy()

    ;(dialog.querySelector('[aria-label="Đóng thông tin nguồn"]') as HTMLButtonElement).click()
    await flushUi()
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('degrades a dated verified tier when public source evidence is missing', async () => {
    const wrapper = await mountSuspended(SourceTrustDrawer, {
      props: {
        open: true,
        sourceTier: 'verified',
        sourceTitle: 'Đối tác dữ liệu địa phương',
        sourceUrl: '',
        verifiedAt: '2026-07-18T00:00:00Z',
        freshnessStatus: 'fresh',
      },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.dataset.sourceTier).toBe('unsupported-verified')
    expect(dialog.textContent).toContain('Chưa đủ bằng chứng xác minh')
    expect(dialog.textContent).not.toContain('Đối tác xác minh kèm ngày')
    expect(dialog.querySelector('[data-verification-date]')).toBeNull()
  })

  it('keeps official and community identity separate and reports freshness evidence', async () => {
    const official = await mountSuspended(SourceTrustDrawer, {
      props: {
        open: true,
        sourceTier: 'official',
        sourceTitle: 'Cổng thông tin tỉnh',
        sourceUrl: 'https://example.gov.vn/entity-1',
        updatedAt: '2026-07-12T00:00:00Z',
        freshnessStatus: 'fresh',
      },
      attachTo: document.body,
    })
    wrappers.push(official)

    let dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.dataset.sourceTier).toBe('official')
    expect(dialog.textContent).toContain('Nguồn chính thức')
    expect(dialog.textContent).toContain('Mới cập nhật')
    expect(dialog.textContent).not.toContain('Nguồn cộng đồng')
    expect(dialog.querySelector('a[href="https://example.gov.vn/entity-1"]')).toBeTruthy()
    expect(dialog.querySelector('time[datetime="2026-07-12T00:00:00Z"]')).toBeTruthy()

    official.unmount()
    wrappers.pop()
    const community = await mountSuspended(SourceTrustDrawer, {
      props: {
        open: true,
        sourceTier: 'community',
        sourceTitle: 'Chia sẻ từ người dân địa phương',
        freshnessStatus: 'aging',
        communityContext: 'Nội dung cộng đồng được kiểm duyệt trước khi hiển thị.',
      },
      attachTo: document.body,
    })
    wrappers.push(community)

    dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.dataset.sourceTier).toBe('community')
    expect(dialog.textContent).toContain('Nguồn cộng đồng')
    expect(dialog.textContent).toContain('kiểm duyệt')
    expect(dialog.textContent).not.toContain('Nguồn chính thức')

    ;(dialog.querySelector('[data-action="report"]') as HTMLButtonElement).click()
    await flushUi()
    expect(community.emitted('report')).toHaveLength(1)
  })
})

describe('WhyThisDrawer contract', () => {
  it('shows only allowlisted broad explanation signals and emits preference controls', async () => {
    const wrapper = await mountSuspended(WhyThisDrawer, {
      props: {
        open: true,
        preferenceHref: '/cai-dat#khu-vuc-de-xuat',
        explanation: {
          primary_reason: 'Cùng khu vực bạn quan tâm',
          reasons: ['Cùng khu vực bạn quan tâm', 'Phù hợp với sở thích bạn đã chọn'],
          region_label: 'Vĩnh Long',
          explicit_interests: ['Ẩm thực'],
          derived_age_band: '25_34',
          score: 0.998,
          exact_age: 31,
          query: 'quán ăn bí mật',
          gps: '10.25,105.97',
          ip: '203.0.113.10',
          metadata: { private_note: 'uncommon-provider-field' },
        } as never,
      },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const dialog = document.body.querySelector('[role="dialog"][data-why-this]') as HTMLElement
    expect(dialog.textContent).toContain('Vì sao bạn thấy nội dung này?')
    expect(dialog.textContent).toContain('Cùng khu vực bạn quan tâm')
    expect(dialog.textContent).toContain('Vĩnh Long')
    expect(dialog.textContent).toContain('Ẩm thực')
    expect(dialog.textContent).not.toContain('0.998')
    expect(dialog.textContent).not.toContain('31')
    expect(dialog.textContent).not.toContain('quán ăn bí mật')
    expect(dialog.textContent).not.toContain('10.25,105.97')
    expect(dialog.textContent).not.toContain('203.0.113.10')
    expect(dialog.textContent).not.toContain('uncommon-provider-field')

    for (const action of ['open-preferences', 'reset', 'disable-personalization'] as const) {
      ;(dialog.querySelector(`[data-action="${action}"]`) as HTMLElement).click()
      await flushUi()
      expect(wrapper.emitted(action)).toHaveLength(1)
    }
  })

  it('redacts sensitive values embedded inside explanation strings and keeps a useful fallback', async () => {
    const wrapper = await mountSuspended(WhyThisDrawer, {
      props: {
        open: true,
        explanation: {
          primary_reason: 'Bạn thấy mục này vì đã tìm "quán ăn bí mật" gần GPS 10.25,105.97',
          reasons: [
            'Tuổi chính xác 31, IP 203.0.113.10 và điểm nội bộ 0.998',
            'Metadata uncommon-provider-field từ truy vấn thô',
          ],
          region_label: 'GPS 10.25,105.97',
          explicit_interests: ['quán ăn bí mật'],
        },
      },
      attachTo: document.body,
    })
    wrappers.push(wrapper)

    const dialog = document.body.querySelector('[role="dialog"][data-why-this]') as HTMLElement
    expect(dialog.textContent).toContain('Được cộng đồng quan tâm')
    expect(dialog.textContent).not.toContain('quán ăn bí mật')
    expect(dialog.textContent).not.toContain('10.25,105.97')
    expect(dialog.textContent).not.toContain('203.0.113.10')
    expect(dialog.textContent).not.toContain('0.998')
    expect(dialog.textContent).not.toContain('uncommon-provider-field')
    expect(dialog.textContent).not.toContain('31')
  })

  it('closes on Escape and restores focus to the disclosure trigger', async () => {
    const originalOffsetParent = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetParent')
    Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
      configurable: true,
      get: () => document.body,
    })

    try {
      const Harness = defineComponent({
        setup() {
          const open = ref(false)
          return () => h('div', [
            h('button', { 'data-trigger': 'why-this', onClick: () => { open.value = true } }, 'Mở giải thích'),
            h(WhyThisDrawer, {
              open: open.value,
              explanation: { primary_reason: 'Được cộng đồng quan tâm', reasons: ['Được cộng đồng quan tâm'] },
              onClose: () => { open.value = false },
            }),
          ])
        },
      })
      const wrapper = await mountSuspended(Harness, { attachTo: document.body })
      wrappers.push(wrapper)
      const trigger = wrapper.get('[data-trigger="why-this"]')
      ;(trigger.element as HTMLElement).focus()
      await trigger.trigger('click')
      await flushUi()

      const dialog = document.body.querySelector('[role="dialog"][data-why-this]') as HTMLElement
      expect(dialog.contains(document.activeElement)).toBe(true)
      expect(document.body.style.overflow).toBe('hidden')

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await flushUi()

      expect(document.body.querySelector('[role="dialog"][data-why-this]')).toBeNull()
      expect(document.body.style.overflow).toBe('')
      expect(document.activeElement).toBe(trigger.element)
    } finally {
      if (originalOffsetParent) Object.defineProperty(HTMLElement.prototype, 'offsetParent', originalOffsetParent)
      else Reflect.deleteProperty(HTMLElement.prototype, 'offsetParent')
    }
  })
})

describe('recommendation and detail integration', () => {
  it('opens WhyThis from a reason_vi-only personalized recommendation', async () => {
    const wrapper = await mountSmartRecommendations({
      source: 'personalized',
      items: [recommendationFixture({
        explanation: undefined,
        reason: undefined,
        reason_vi: 'Cùng khu vực bạn chọn',
      })],
    })
    wrappers.push(wrapper)

    await vi.waitFor(() => expect(wrapper.find('[data-action="why-this"]').exists()).toBe(true))
    await wrapper.get('[data-action="why-this"]').trigger('click')
    await flushUi()

    const dialog = document.body.querySelector('[role="dialog"][data-why-this]') as HTMLElement
    expect(dialog.textContent).toContain('Cùng khu vực bạn quan tâm')
    expect(dialog.textContent).not.toContain('Được cộng đồng quan tâm')
  })

  it('opens the real explanation drawer and applies reset and disable through preference APIs', async () => {
    const cards = [recommendationFixture()]
    apiFetchMock.mockImplementation((url: string, request?: Record<string, unknown>) => {
      if (url.startsWith('/api/me/recommendations/contextual?')) {
        return Promise.resolve({ items: cards, reasons: {}, profile: { signal_count: 3 } })
      }
      if (url === '/api/me/recommendations/reset') {
        return Promise.resolve(preferenceSnapshot({ recommendation_reset_at: '2026-07-29T09:00:00Z', revision: 3 }))
      }
      if (url === '/api/me/preferences' && request?.method === 'PATCH') {
        return Promise.resolve(preferenceSnapshot({ personalization_enabled: false, revision: 4 }))
      }
      return Promise.resolve({ entities: [] })
    })

    const wrapper = await mountSmart(true)
    wrappers.push(wrapper)

    await vi.waitFor(() => expect(wrapper.find('[data-action="why-this"]').exists()).toBe(true))
    expect(wrapper.get('.card').text()).toContain('Vườn trái cây ven sông')
    await wrapper.get('[data-action="why-this"]').trigger('click')
    await flushUi()

    let dialog = document.body.querySelector('[role="dialog"][data-why-this]') as HTMLElement
    expect(dialog.textContent).toContain('Cùng khu vực bạn quan tâm')
    ;(dialog.querySelector('[data-action="reset"]') as HTMLButtonElement).click()
    await vi.waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith('/api/me/recommendations/reset', expect.objectContaining({ method: 'POST' })))
    expect(wrapper.get('[role="status"]').text()).toContain('Đã làm mới đề xuất')

    dialog = document.body.querySelector('[role="dialog"][data-why-this]') as HTMLElement
    ;(dialog.querySelector('[data-action="disable-personalization"]') as HTMLButtonElement).click()
    await vi.waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith('/api/me/preferences', expect.objectContaining({
      method: 'PATCH',
      body: expect.objectContaining({ personalization_enabled: false }),
    })))
  })

  it('keeps the real recommendation card functional when disclosure data is absent', async () => {
    apiFetchMock.mockResolvedValue({ entities: [recommendationFixture({ explanation: undefined, reason_vi: undefined })] })

    const wrapper = await mountSmart(false)
    wrappers.push(wrapper)

    await vi.waitFor(() => expect(wrapper.find('.card').exists()).toBe(true))
    expect(wrapper.get('.card').text()).toContain('Vườn trái cây ven sông')
    expect(wrapper.find('[data-action="why-this"]').exists()).toBe(false)
    expect(document.body.querySelector('[role="dialog"][data-why-this]')).toBeNull()
  })

  it('opens the shared trust drawer from detail and preserves report navigation', async () => {
    const wrapper = await mountPlaceDetail({
      id: 'detail-official',
      type: 'place',
      name: 'Nhà cổ ven sông',
      summary: 'Không gian di sản được biên tập từ nguồn công khai.',
      attributes: {},
      relationships: [],
      relationship_total: 0,
      quality: {
        source_title: 'Cổng thông tin tỉnh Vĩnh Long',
        source_url: 'https://example.gov.vn/detail-official',
      },
      source_freshness: {
        source_title: 'Cổng thông tin tỉnh Vĩnh Long',
        source_url: 'https://example.gov.vn/detail-official',
        source_tier: 'official',
        updated_at: '2026-07-20T00:00:00Z',
        freshness_status: 'fresh',
      },
    })
    wrappers.push(wrapper)

    await vi.waitFor(() => expect(wrapper.find('[data-action="open-source-trust"]').exists()).toBe(true))
    await wrapper.get('[data-action="open-source-trust"]').trigger('click')
    await flushUi()

    const dialog = document.body.querySelector('[role="dialog"][data-source-trust]') as HTMLElement
    expect(dialog.textContent).toContain('Nguồn chính thức')
    expect(dialog.textContent).toContain('Cổng thông tin tỉnh Vĩnh Long')
    ;(dialog.querySelector('[data-action="report"]') as HTMLButtonElement).click()
    await vi.waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('/cong-dong?report=detail-official'))
    expect(document.body.querySelector('[role="dialog"][data-source-trust]')).toBeNull()
  })

  it('keeps the detail report fallback when no public source can open the enhancement', async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/entities/detail-fallback') {
        return Promise.resolve({
          id: 'detail-fallback',
          type: 'place',
          name: 'Điểm ghé chưa có nguồn',
          summary: 'Bố cục chi tiết vẫn hoạt động khi chưa có lớp nguồn mở rộng.',
          attributes: {},
          relationships: [],
          relationship_total: 0,
        })
      }
      if (url === '/api/entities/detail-fallback/gallery') return Promise.resolve({ images: [] })
      if (url === '/seo/jsonld/detail-fallback') return Promise.resolve(null)
      return Promise.resolve({})
    })

    const wrapper = await mountDetail('/dia-diem/detail-fallback')
    wrappers.push(wrapper)

    await vi.waitFor(() => expect(wrapper.find('.quality-report').exists()).toBe(true))
    expect(wrapper.find('[data-action="open-source-trust"]').exists()).toBe(false)
    expect(wrapper.get('.quality-report').attributes('href')).toBe('/cong-dong?report=detail-fallback')
    expect(document.body.querySelector('[role="dialog"][data-source-trust]')).toBeNull()
  })
})
