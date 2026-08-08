// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import OnboardingSheet from '../components/OnboardingSheet.vue'
import SmartRecommendations from '../components/SmartRecommendations.vue'
import SettingsPage from '../pages/cai-dat.vue'
import DetailPage from '../pages/dia-diem/[id].vue'
import { featureFlagDefault } from '../utils/featureFlags'

const apiFetchMock = vi.hoisted(() => vi.fn())
const pageFetchMock = vi.hoisted(() => vi.fn())
const navigateToMock = vi.hoisted(() => vi.fn(() => Promise.resolve()))
const publicFlags = vi.hoisted(() => ({
  preference_ui_v1: false,
  recommendation_explanations_v1: false,
  trust_drawer_v1: false,
}))
const authState = vi.hoisted(() => ({
  user: { __v_isRef: true, value: { id: 'flag-user' } as { id: string } | null },
  isLoggedIn: { __v_isRef: true, value: true },
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer flag-test' })),
  fetchCsrf: vi.fn(() => Promise.resolve('csrf-token')),
  fetchMe: vi.fn(() => Promise.resolve()),
  handleSessionExpired: vi.fn(),
}))

vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))
mockNuxtImport('navigateTo', () => navigateToMock)
mockNuxtImport('useAuth', () => () => authState)
mockNuxtImport('useSiteSettings', () => () => ({
  get: (key: string, fallback?: unknown) => key === 'features.flags' ? publicFlags : fallback,
}))

const preferenceSnapshot = {
  region_id: null,
  region_label: null,
  region_scope: 'unknown',
  location_source: 'default',
  location_accuracy: 'unknown',
  location_consent_state: 'unknown',
  location_enabled: false,
  personalization_enabled: true,
  explicit_interests: [],
  recommendation_reset_at: null,
  consent_version: null,
  revision: 0,
}

const recommendation = {
  id: 'flag-rec-1',
  type: 'place',
  name: 'Vườn ven sông',
  summary: 'Một gợi ý công khai vẫn dùng được khi tắt lớp giải thích.',
  attributes: {},
  relationships: [],
  relationship_total: 0,
  explanation: {
    primary_reason: 'Cùng khu vực bạn quan tâm',
    reasons: ['Cùng khu vực bạn quan tâm'],
  },
}

const sourcedEntity = {
  id: 'flag-detail-1',
  type: 'place',
  name: 'Nhà cổ ven sông',
  summary: 'Thông tin công khai vẫn hiển thị khi tắt ngăn nguồn mở rộng.',
  attributes: {},
  relationships: [],
  relationship_total: 0,
  quality: {
    source_title: 'Cổng thông tin tỉnh',
    source_url: 'https://example.gov.vn/flag-detail-1',
  },
  source_freshness: {
    source_title: 'Cổng thông tin tỉnh',
    source_url: 'https://example.gov.vn/flag-detail-1',
    source_tier: 'official',
    updated_at: '2026-07-20T00:00:00Z',
    freshness_status: 'fresh',
  },
}

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

beforeEach(() => {
  publicFlags.preference_ui_v1 = false
  publicFlags.recommendation_explanations_v1 = false
  publicFlags.trust_drawer_v1 = false
  authState.user.value = { id: 'flag-user' }
  authState.isLoggedIn.value = true
  apiFetchMock.mockReset()
  pageFetchMock.mockReset()
  navigateToMock.mockClear()
  apiFetchMock.mockImplementation((url: string) => {
    if (url === '/api/me/preferences') return Promise.resolve(preferenceSnapshot)
    if (url.startsWith('/api/me/recommendations/contextual?')) {
      return Promise.resolve({ items: [recommendation], reasons: {}, profile: { signal_count: 1 } })
    }
    if (url === `/api/entities/${sourcedEntity.id}`) return Promise.resolve(sourcedEntity)
    if (url === `/api/entities/${sourcedEntity.id}/gallery`) return Promise.resolve({ images: [] })
    if (url === `/seo/jsonld/${sourcedEntity.id}`) return Promise.resolve(null)
    return Promise.resolve({})
  })
  pageFetchMock.mockImplementation((url: string) => {
    if (url === '/auth/me') return Promise.resolve({ user: authState.user.value })
    if (url === '/auth/csrf') return Promise.resolve({ csrf_token: 'csrf-token' })
    if (url === '/auth/privacy') return Promise.resolve({ profile_visibility: 'public', show_activity: true, show_saved: true })
    if (url === '/api/notification-preferences') return Promise.resolve({})
    if (url.startsWith('/api/users/')) return Promise.resolve({ user: { id: 'flag-user', display_name: 'Lan' } })
    return Promise.resolve({})
  })
  vi.stubGlobal('$fetch', pageFetchMock)
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
  document.body.style.overflow = ''
})

describe('NP-1 public feature flag defaults', () => {
  it('defaults every rollout enhancement to off', () => {
    expect(featureFlagDefault('preference_ui_v1')).toBe(false)
    expect(featureFlagDefault('recommendation_explanations_v1')).toBe(false)
    expect(featureFlagDefault('trust_drawer_v1')).toBe(false)
  })
})

describe('preference_ui_v1 behavior', () => {
  it('keeps ordinary onboarding for guests while hiding personalized setup', async () => {
    vi.useFakeTimers()
    authState.user.value = null
    authState.isLoggedIn.value = false

    const wrapper = await mountSuspended(OnboardingSheet, { attachTo: document.body })
    await vi.advanceTimersByTimeAsync(5000)
    await flushUi()

    expect(document.body.querySelector('[aria-label="Chào mừng đến vinhlong360"]')).toBeTruthy()
    expect(document.body.querySelector('[aria-label="Thiết lập khu vực và sở thích"]')).toBeNull()
    wrapper.unmount()
  })

  it('exposes real setup and settings panels only when enabled', async () => {
    let onboarding = await mountSuspended(OnboardingSheet, { attachTo: document.body })
    await flushUi()
    expect(document.body.querySelector('[aria-label="Thiết lập khu vực và sở thích"]')).toBeNull()
    onboarding.unmount()

    let settings = await mountSuspended(SettingsPage, {
      route: '/cai-dat',
      global: { stubs: { Breadcrumb: true, AvatarPlaceholder: true } },
    })
    expect(settings.find('#tab-khu-vuc-de-xuat').exists()).toBe(false)
    expect(settings.find('.settings-title').text()).toContain('Cài đặt')
    settings.unmount()

    publicFlags.preference_ui_v1 = true
    onboarding = await mountSuspended(OnboardingSheet, { attachTo: document.body })
    await vi.waitFor(() => expect(document.body.querySelector('[aria-label="Thiết lập khu vực và sở thích"]')).toBeTruthy())
    onboarding.unmount()

    settings = await mountSuspended(SettingsPage, {
      route: '/cai-dat',
      global: { stubs: { Breadcrumb: true, AvatarPlaceholder: true } },
    })
    await settings.get('#tab-khu-vuc-de-xuat').trigger('click')
    await flushUi()
    expect(settings.get('#khu-vuc-de-xuat').text()).toContain('Khu vực & đề xuất')
    settings.unmount()
  })
})

describe('recommendation_explanations_v1 behavior', () => {
  it('keeps recommendation cards while gating the explanation trigger', async () => {
    let wrapper = await mountSuspended(SmartRecommendations, {
      props: { context: 'home', limit: 1 },
      attachTo: document.body,
    })
    await vi.waitFor(() => expect(wrapper.find('.card').exists()).toBe(true))
    expect(wrapper.get('.card').text()).toContain('Vườn ven sông')
    expect(wrapper.find('[data-action="why-this"]').exists()).toBe(false)
    wrapper.unmount()

    publicFlags.recommendation_explanations_v1 = true
    wrapper = await mountSuspended(SmartRecommendations, {
      props: { context: 'home', limit: 1 },
      attachTo: document.body,
    })
    await vi.waitFor(() => expect(wrapper.find('[data-action="why-this"]').exists()).toBe(true))
    await wrapper.get('[data-action="why-this"]').trigger('click')
    await flushUi()
    expect(document.body.querySelector('[role="dialog"][data-why-this]')).toBeTruthy()
    wrapper.unmount()
  })
})

describe('trust_drawer_v1 behavior', () => {
  it('keeps public detail and report fallback while gating trust disclosure', async () => {
    let wrapper = await mountSuspended(DetailPage, {
      route: `/dia-diem/${sourcedEntity.id}`,
      attachTo: document.body,
    })
    await vi.waitFor(() => expect(wrapper.find('h1').text()).toContain('Nhà cổ ven sông'))
    expect(wrapper.find('[data-action="open-source-trust"]').exists()).toBe(false)
    expect(wrapper.get('.quality-report').attributes('href')).toBe(`/cong-dong?report=${sourcedEntity.id}`)
    wrapper.unmount()

    publicFlags.trust_drawer_v1 = true
    wrapper = await mountSuspended(DetailPage, {
      route: `/dia-diem/${sourcedEntity.id}`,
      attachTo: document.body,
    })
    await vi.waitFor(() => expect(wrapper.find('[data-action="open-source-trust"]').exists()).toBe(true))
    await wrapper.get('[data-action="open-source-trust"]').trigger('click')
    await flushUi()
    expect(document.body.querySelector('[role="dialog"][data-source-trust]')).toBeTruthy()
    wrapper.unmount()
  })
})
