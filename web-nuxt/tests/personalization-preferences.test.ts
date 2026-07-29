// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import OnboardingSheet from '../components/OnboardingSheet.vue'
import PersonalizeSetupSheet from '../components/PersonalizeSetupSheet.vue'
import ToastContainer from '../components/ToastContainer.vue'
import { usePersonalizationPreferences } from '../composables/usePersonalizationPreferences'
import SettingsPage from '../pages/cai-dat.vue'
import type { PreferenceSnapshot } from '../types/personalization'

const apiFetchMock = vi.hoisted(() => vi.fn())
const pageFetchMock = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({
  user: { __v_isRef: true, value: { id: 'user-1' } as { id: string } | null },
  isLoggedIn: { __v_isRef: true, value: true },
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer test-token' })),
  fetchCsrf: vi.fn(() => Promise.resolve('csrf-token')),
  fetchMe: vi.fn(() => Promise.resolve()),
}))

vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))
mockNuxtImport('useAuth', () => () => authState)
mockNuxtImport('useFeature', () => () => ({ enabled: () => true }))
mockNuxtImport('useSiteSettings', () => () => ({ get: () => ({}) }))

const defaultSnapshot: PreferenceSnapshot = {
  region_id: null,
  region_label: null,
  region_scope: 'unknown',
  location_source: 'default',
  location_accuracy: 'unknown',
  location_consent_state: 'unknown',
  location_enabled: false,
  personalization_enabled: false,
  explicit_interests: [],
  recommendation_reset_at: null,
  consent_version: null,
  revision: 0,
}

function preferenceFixture(overrides: Partial<PreferenceSnapshot> = {}): PreferenceSnapshot {
  return { ...defaultSnapshot, ...overrides }
}

const snapshot = preferenceFixture

function apiResultFor(url: string, opts?: Record<string, unknown>) {
  if (url === '/api/me/preferences' && !opts?.method) return Promise.resolve(snapshot())
  return Promise.resolve(snapshot({ revision: 1 }))
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((next, fail) => { resolve = next; reject = fail })
  return { promise, resolve, reject }
}

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

type ConsentFixture = { id: string; version: string | null; created_at: string }
type DeleteResponse = { status: string; message: string; grace_days: number }

async function mountSettingsPage(options: {
  preferences?: PreferenceSnapshot
  consents?: ConsentFixture[]
  deleteResponse?: DeleteResponse
  initialHash?: 'khu-vuc-de-xuat' | 'du-lieu' | 'nguy-hiem'
  openViaHash?: boolean
  preferenceMutations?: Array<PreferenceSnapshot | Promise<PreferenceSnapshot> | { reject: unknown }>
} = {}) {
  let current = options.preferences || preferenceFixture()
  const mutationQueue = [...(options.preferenceMutations || [])]
  const deleteResponse = options.deleteResponse || {
    status: 'scheduled',
    message: 'Tài khoản sẽ bị xóa sau 30 ngày',
    grace_days: 30,
  }

  apiFetchMock.mockImplementation((url: string, request?: Record<string, unknown>) => {
    if (url === '/api/me/preferences' && !request?.method) return Promise.resolve(current)
    if (url === '/api/me/preferences' && request?.method === 'PATCH') {
      const queued = mutationQueue.shift()
      if (queued && typeof queued === 'object' && 'reject' in queued) return Promise.reject(queued.reject)
      if (queued) return Promise.resolve(queued).then((next) => {
        current = next
        return next
      })
      const body = request.body as Partial<PreferenceSnapshot> | undefined
      current = preferenceFixture({ ...current, ...body, revision: current.revision + 1 })
      return Promise.resolve(current)
    }
    if (url === '/api/me/recommendations/reset') {
      current = preferenceFixture({
        ...current,
        recommendation_reset_at: '2026-07-29T08:00:00Z',
        revision: current.revision + 1,
      })
      return Promise.resolve(current)
    }
    return Promise.resolve(current)
  })
  pageFetchMock.mockImplementation((url: string) => {
    if (url === '/auth/consent-history') return Promise.resolve({ history: options.consents || [] })
    if (url === '/auth/account') return Promise.resolve(deleteResponse)
    if (url === '/auth/privacy') return Promise.resolve({ profile_visibility: 'public', show_activity: true, show_saved: true })
    if (url === '/api/notification-preferences') return Promise.resolve({})
    if (url.startsWith('/api/users/')) return Promise.resolve({ user: { id: 'user-1', display_name: 'Lan' } })
    return Promise.resolve({})
  })
  vi.stubGlobal('$fetch', pageFetchMock)
  Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
  const initialHash = options.initialHash || 'khu-vuc-de-xuat'
  const initialRoute = options.openViaHash ? `/cai-dat#${initialHash}` : '/cai-dat'
  window.history.replaceState(null, '', initialRoute)

  const SettingsHarness = defineComponent({
    setup() {
      return () => h('div', [h(SettingsPage), h(ToastContainer)])
    },
  })
  const wrapper = await mountSuspended(options.openViaHash ? SettingsPage : SettingsHarness, {
    route: initialRoute,
    global: {
      stubs: {
        Breadcrumb: true,
        AvatarPlaceholder: true,
      },
    },
  })
  await flushUi()
  const initialTab = wrapper.find(`#tab-${initialHash}`)
  if (!options.openViaHash && initialTab.exists()) {
    await initialTab.trigger('click')
    await flushUi()
  }
  return wrapper
}

beforeEach(() => {
  authState.isLoggedIn.value = true
  authState.user.value = { id: 'user-1' }
  authState.authHeaders.mockClear()
  authState.fetchCsrf.mockClear()
  authState.fetchMe.mockClear()
  apiFetchMock.mockReset()
  apiFetchMock.mockImplementation(apiResultFor)
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
  document.body.style.overflow = ''
})

describe('usePersonalizationPreferences contract', () => {
  it('loads an API snapshot as the authenticated source of truth', async () => {
    const fixture = snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      explicit_interests: ['food', 'culture'],
      revision: 4,
    })
    apiFetchMock.mockResolvedValueOnce(fixture)

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    await preferences!.refresh()

    expect(preferences!.snapshot.value).toEqual(fixture)
    expect(apiFetchMock).toHaveBeenCalledWith('/api/me/preferences', expect.objectContaining({
      credentials: 'include',
      headers: { Authorization: 'Bearer test-token' },
    }))
  })

  it('falls back to a safe all-region snapshot when the API payload is malformed', async () => {
    apiFetchMock.mockResolvedValueOnce({ region_id: ['not-text'], explicit_interests: 'food' })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    await expect(preferences!.refresh()).resolves.toBe(true)

    expect(preferences!.snapshot.value.region_id).toBeNull()
    expect(preferences!.snapshot.value.region_scope).toBe('unknown')
    expect(preferences!.snapshot.value.explicit_interests).toEqual([])
  })

  it('keeps a manual region after location is revoked', async () => {
    const calls: Array<{ url: string; opts?: Record<string, unknown> }> = []
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      calls.push({ url, opts })
      if (!opts?.method) return Promise.resolve(snapshot())
      const body = opts.body as Record<string, unknown>
      if (body.location_enabled === false) {
        return Promise.resolve(snapshot({
          region_id: 'province-vl',
          region_label: 'Vĩnh Long',
          region_scope: 'province',
          location_source: 'manual',
          location_accuracy: 'province',
          location_consent_state: 'off',
          location_enabled: false,
          revision: 2,
        }))
      }
      return Promise.resolve(snapshot({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'manual',
        location_accuracy: 'province',
        revision: 1,
      }))
    })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    await preferences!.setRegion({ id: 'province-vl', label: 'Vĩnh Long', scope: 'province' })
    await preferences!.revokeLocation()

    expect(preferences!.snapshot.value.region_id).toBe('province-vl')
    expect(preferences!.snapshot.value.location_enabled).toBe(false)
    expect(calls.at(-1)?.opts?.body).toMatchObject({ location_enabled: false })
  })

  it('never stores GPS coordinates and returns only normalized region data', async () => {
    const resolution = {
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'gps',
      location_accuracy: 'province',
    }
    apiFetchMock.mockResolvedValueOnce(resolution)

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    const result = await preferences!.resolveLocation('gps', { latitude: 10.24, longitude: 105.97 })

    expect(result).toEqual(resolution)
    expect(result).not.toHaveProperty('latitude')
    expect(result).not.toHaveProperty('longitude')
    expect(preferences!.snapshot.value).not.toHaveProperty('latitude')
    expect(preferences!.snapshot.value).not.toHaveProperty('longitude')
    expect(apiFetchMock).toHaveBeenCalledWith('/api/me/location/resolve', expect.objectContaining({
      method: 'POST',
      body: { mode: 'gps', latitude: 10.24, longitude: 105.97 },
    }))
  })

  it('bounds setup interests to three unique keys before patching', async () => {
    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    await preferences!.setInterests(['food', 'food', 'culture', 'garden', 'stay'])

    const patch = apiFetchMock.mock.calls.at(-1)?.[1]?.body
    expect(patch).toMatchObject({ explicit_interests: ['food', 'culture', 'garden'] })
  })

  it('keeps a newer patch when an older refresh resolves last', async () => {
    const staleRefresh = deferred<PreferenceSnapshot>()
    const patched = snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 3,
    })
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && !opts?.method) return staleRefresh.promise
      return Promise.resolve(patched)
    })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    const refreshPromise = preferences!.refresh()
    const patchResult = await preferences!.setRegion({ id: 'province-vl', label: 'Vĩnh Long', scope: 'province' })
    staleRefresh.resolve(snapshot({ revision: 1 }))
    await refreshPromise

    expect(patchResult).toEqual({ ok: true, snapshot: patched, status: null })
    expect(preferences!.snapshot.value).toEqual(patched)
  })

  it('keeps an earlier patch when a later refresh resolves first with stale state', async () => {
    const patchStarted = deferred<void>()
    const pendingPatch = deferred<PreferenceSnapshot>()
    const pendingRefresh = deferred<PreferenceSnapshot>()
    const patched = snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 6,
    })
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
        patchStarted.resolve()
        return pendingPatch.promise
      }
      if (url === '/api/me/preferences') return pendingRefresh.promise
      return Promise.resolve(snapshot())
    })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    const patchPromise = preferences!.setRegion({ id: 'province-vl', label: 'Vĩnh Long', scope: 'province' })
    await patchStarted.promise
    const refreshPromise = preferences!.refresh()
    pendingRefresh.resolve(snapshot({ revision: 5 }))
    expect(await refreshPromise).toBe(false)
    pendingPatch.resolve(patched)

    expect(await patchPromise).toEqual({ ok: true, snapshot: patched, status: null })
    expect(preferences!.snapshot.value).toEqual(patched)
  })

  it('keeps an earlier patch when a later stale refresh resolves after the patch', async () => {
    const patchStarted = deferred<void>()
    const pendingPatch = deferred<PreferenceSnapshot>()
    const pendingRefresh = deferred<PreferenceSnapshot>()
    const patched = snapshot({
      region_id: 'province-bt',
      region_label: 'Bến Tre',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 10,
    })
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
        patchStarted.resolve()
        return pendingPatch.promise
      }
      if (url === '/api/me/preferences') return pendingRefresh.promise
      return Promise.resolve(snapshot())
    })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    const patchPromise = preferences!.setRegion({ id: 'province-bt', label: 'Bến Tre', scope: 'province' })
    await patchStarted.promise
    const refreshPromise = preferences!.refresh()
    pendingPatch.resolve(patched)
    expect(await patchPromise).toEqual({ ok: true, snapshot: patched, status: null })
    pendingRefresh.resolve(snapshot({ revision: 9 }))

    expect(await refreshPromise).toBe(false)
    expect(preferences!.snapshot.value).toEqual(patched)
  })

  it('resets owner state and ignores a previous account response after an account switch', async () => {
    const previousOwner = deferred<PreferenceSnapshot>()
    const nextOwner = deferred<PreferenceSnapshot>()
    apiFetchMock
      .mockImplementationOnce(() => previousOwner.promise)
      .mockImplementationOnce(() => nextOwner.promise)

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    const previousRefresh = preferences!.refresh()
    authState.user.value = { id: 'user-2' }
    const nextRefresh = preferences!.refresh()

    expect(preferences!.snapshot.value).toEqual(defaultSnapshot)

    const userTwoSnapshot = snapshot({
      region_id: 'province-bt',
      region_label: 'Bến Tre',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 8,
    })
    nextOwner.resolve(userTwoSnapshot)
    await nextRefresh
    previousOwner.resolve(snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    }))
    await previousRefresh

    expect(preferences!.snapshot.value).toEqual(userTwoSnapshot)

    authState.isLoggedIn.value = false
    authState.user.value = null
    await expect(preferences!.refresh()).resolves.toBe(false)
    expect(preferences!.snapshot.value).toEqual(defaultSnapshot)
  })

  it('returns an explicit failed mutation result when a preference patch is rejected', async () => {
    apiFetchMock
      .mockResolvedValueOnce(defaultSnapshot)
      .mockRejectedValueOnce(new Error('save failed'))

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)

    await preferences!.refresh()
    const result = await preferences!.setRegion({ id: 'province-vl', label: 'Vĩnh Long', scope: 'province' })

    expect(result).toEqual({ ok: false, snapshot: defaultSnapshot, status: null })
    expect(preferences!.error.value).toBe('Không thể lưu thiết lập cá nhân hóa.')
  })

  it('reports an actual 409 even when the server snapshot has the same revision', async () => {
    const previous = snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    })
    const server = snapshot({
      region_id: 'province-tv',
      region_label: 'Trà Vinh',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    })
    apiFetchMock
      .mockResolvedValueOnce(previous)
      .mockRejectedValueOnce({ response: { status: 409, _data: server } })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    await preferences!.refresh()

    const result = await preferences!.setRegion({ id: 'province-bt', label: 'Bến Tre', scope: 'province' })

    expect(result).toEqual({ ok: false, snapshot: server, status: 409 })
    expect(preferences!.snapshot.value).toEqual(server)
  })

  it('ignores a snapshot-shaped payload from a non-409 failure and rolls back', async () => {
    const previous = snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    })
    const unrelatedPayload = snapshot({
      region_id: 'province-tv',
      region_label: 'Trà Vinh',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 9,
    })
    apiFetchMock
      .mockResolvedValueOnce(previous)
      .mockRejectedValueOnce({ response: { status: 503, _data: unrelatedPayload } })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    await preferences!.refresh()

    const result = await preferences!.setRegion({ id: 'province-bt', label: 'Bến Tre', scope: 'province' })

    expect(result).toEqual({ ok: false, snapshot: previous, status: 503 })
    expect(preferences!.snapshot.value).toEqual(previous)
  })

  it('does not leak a stale patch 409 into the result of an obsolete write', async () => {
    const stalePatchStarted = deferred<void>()
    const stalePatch = deferred<PreferenceSnapshot>()
    const previous = snapshot({ revision: 4 })
    const current = snapshot({
      region_id: 'province-bt',
      region_label: 'Bến Tre',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 5,
    })
    const staleServer = snapshot({
      region_id: 'province-tv',
      region_label: 'Trà Vinh',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    })
    let patchCalls = 0
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && !opts?.method) return Promise.resolve(previous)
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
        patchCalls += 1
        if (patchCalls === 1) {
          stalePatchStarted.resolve()
          return stalePatch.promise
        }
        return Promise.resolve(current)
      }
      return Promise.resolve(previous)
    })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    await preferences!.refresh()

    const staleResult = preferences!.setRegion({ id: 'province-vl', label: 'Vĩnh Long', scope: 'province' })
    await stalePatchStarted.promise
    const currentResult = await preferences!.setRegion({ id: 'province-bt', label: 'Bến Tre', scope: 'province' })
    stalePatch.reject({ response: { status: 409, _data: staleServer } })

    expect(currentResult).toEqual({ ok: true, snapshot: current, status: null })
    expect(await staleResult).toEqual({ ok: false, snapshot: current, status: null })
    expect(preferences!.snapshot.value).toEqual(current)
    expect(preferences!.error.value).toBeNull()
  })

  it('does not leak a stale reset 409 into the result of an obsolete write', async () => {
    const staleResetStarted = deferred<void>()
    const staleReset = deferred<PreferenceSnapshot>()
    const previous = snapshot({ revision: 4 })
    const current = snapshot({ recommendation_reset_at: '2026-07-29T08:00:00Z', revision: 5 })
    const staleServer = snapshot({ recommendation_reset_at: '2026-07-28T08:00:00Z', revision: 4 })
    let resetCalls = 0
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && !opts?.method) return Promise.resolve(previous)
      if (url === '/api/me/recommendations/reset') {
        resetCalls += 1
        if (resetCalls === 1) {
          staleResetStarted.resolve()
          return staleReset.promise
        }
        return Promise.resolve(current)
      }
      return Promise.resolve(previous)
    })

    let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
    const Harness = defineComponent({
      setup() {
        preferences = usePersonalizationPreferences()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    await preferences!.refresh()

    const staleResult = preferences!.resetRecommendations()
    await staleResetStarted.promise
    const currentResult = await preferences!.resetRecommendations()
    staleReset.reject({ response: { status: 409, _data: staleServer } })

    expect(currentResult).toEqual({ ok: true, snapshot: current, status: null })
    expect(await staleResult).toEqual({ ok: false, snapshot: current, status: null })
    expect(preferences!.snapshot.value).toEqual(current)
    expect(preferences!.error.value).toBeNull()
  })

  it('does not open personalization for a different user after refresh completes', async () => {
    const pendingRefresh = deferred<PreferenceSnapshot>()
    apiFetchMock.mockReturnValueOnce(pendingRefresh.promise)

    const wrapper = await mountSuspended(OnboardingSheet, {
      attachTo: document.body,
      global: { stubs: { IconLine: true } },
    })
    await flushUi()

    authState.user.value = { id: 'user-2' }
    pendingRefresh.resolve(snapshot())
    await flushUi()

    expect(document.body.querySelector('[aria-label="Thiết lập khu vực và sở thích"]')).toBeNull()
    wrapper.unmount()
  })

  it('does not request geolocation until the location action is clicked', async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) => {
      success({ coords: { latitude: 10.24, longitude: 105.97 } } as GeolocationPosition)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })

    const wrapper = await mountSuspended(PersonalizeSetupSheet, {
      props: { modelValue: true },
      global: { stubs: { IconLine: true } },
    })
    await flushUi()
    const body = () => document.body
    ;(body().querySelector('[data-region="province-vl"]') as HTMLButtonElement).click()
    ;(body().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(body().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()

    expect(getCurrentPosition).not.toHaveBeenCalled()
    const useLocation = document.body.querySelector('[data-action="use-location"]') as HTMLButtonElement
    expect(useLocation).toBeTruthy()
    useLocation.click()
    await nextTick()

    expect(getCurrentPosition).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
})

describe('settings preference and account contracts', () => {
  it('opens the preference panel from the real hash and follows later hash changes', async () => {
    const wrapper = await mountSettingsPage({
      openViaHash: true,
      initialHash: 'khu-vuc-de-xuat',
      preferences: preferenceFixture({ region_label: 'Vĩnh Long', revision: 2 }),
    })

    expect(window.location.hash).toBe('#khu-vuc-de-xuat')
    expect(wrapper.get('#tab-khu-vuc-de-xuat').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('#khu-vuc-de-xuat').attributes()).not.toHaveProperty('hidden')

    window.history.replaceState(null, '', '/cai-dat#du-lieu')
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    await flushUi()

    expect(wrapper.get('#tab-du-lieu').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('#panel-du-lieu').attributes()).not.toHaveProperty('hidden')
    wrapper.unmount()
  })

  it('renders preference and consent data from the API contract', async () => {
    const wrapper = await mountSettingsPage({
      preferences: preferenceFixture({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'manual',
        location_accuracy: 'province',
        explicit_interests: ['food'],
        derived_age_band: '25_34',
        revision: 4,
      }),
      consents: [{ id: 'consent-1', version: 'location-v1', created_at: '2026-07-28T08:00:00Z' }],
    })

    expect(wrapper.get('#khu-vuc-de-xuat').text()).toContain('Vĩnh Long')
    await wrapper.get('#tab-du-lieu').trigger('click')
    await flushUi()
    await wrapper.get('[data-action="load-consent-history"]').trigger('click')
    await flushUi()
    expect(wrapper.get('[data-consent-id="consent-1"]').text()).toContain('location-v1')
    expect(wrapper.get('[data-consent-id="consent-1"] time').attributes('datetime')).toBe('2026-07-28T08:00:00Z')
    expect(wrapper.text()).not.toContain('203.0.113.')
    await wrapper.get('#tab-khu-vuc-de-xuat').trigger('click')
    await flushUi()
    expect(window.location.hash).toBe('#khu-vuc-de-xuat')
    wrapper.unmount()
  })

  it('renders an honest label when consent history has no version', async () => {
    const wrapper = await mountSettingsPage({
      initialHash: 'du-lieu',
      consents: [{ id: 'consent-unknown', version: null, created_at: '2026-07-28T08:00:00Z' }],
    })

    await wrapper.get('[data-action="load-consent-history"]').trigger('click')
    await flushUi()

    const row = wrapper.get('[data-consent-id="consent-unknown"]')
    expect(row.text()).toContain('Không rõ phiên bản')
    expect(row.text()).not.toContain('1.0')
    wrapper.unmount()
  })

  it('uses the scheduled-deletion response instead of claiming immediate deletion', async () => {
    const wrapper = await mountSettingsPage({
      initialHash: 'nguy-hiem',
      deleteResponse: { status: 'scheduled', message: 'Tài khoản sẽ bị xóa sau 30 ngày', grace_days: 30 },
    })

    await wrapper.get('[data-action="delete-account"]').trigger('click')
    await wrapper.get('[data-action="confirm-delete-account"]').trigger('click')
    await flushUi()

    const status = wrapper.get('.account-status').text()
    expect(status).toContain('Tài khoản sẽ bị xóa sau 30 ngày')
    expect(status.match(/30 ngày/g)).toHaveLength(1)
    expect(document.body.querySelector('.toast')?.textContent).toContain('Tài khoản sẽ bị xóa sau 30 ngày')
    expect(wrapper.text()).not.toContain('Đã xóa tài khoản')
    wrapper.unmount()
  })

  it('adds the grace period once when the scheduled-deletion message omits it', async () => {
    const wrapper = await mountSettingsPage({
      initialHash: 'nguy-hiem',
      deleteResponse: { status: 'scheduled', message: 'Yêu cầu xóa đã được lên lịch', grace_days: 30 },
    })

    await wrapper.get('[data-action="delete-account"]').trigger('click')
    await wrapper.get('[data-action="confirm-delete-account"]').trigger('click')
    await flushUi()

    const status = wrapper.get('.account-status').text()
    expect(status).toContain('Yêu cầu xóa đã được lên lịch')
    expect(status.match(/30 ngày/g)).toHaveLength(1)
    wrapper.unmount()
  })

  it.each([
    ['unknown', preferenceFixture(), ['Chưa có quyết định về vị trí', 'Chưa xác định']],
    ['manual', preferenceFixture({ region_id: 'province-vl', region_label: 'Vĩnh Long', region_scope: 'province', location_source: 'manual', location_accuracy: 'province' }), ['Bạn chọn thủ công', 'Cấp tỉnh']],
    ['gps', preferenceFixture({ region_id: 'province-vl', region_label: 'Vĩnh Long', region_scope: 'province', location_source: 'gps', location_accuracy: 'province', location_consent_state: 'granted', location_enabled: true }), ['GPS gần đúng', 'Cấp tỉnh']],
    ['ip', preferenceFixture({ region_id: 'province-vl', region_label: 'Vĩnh Long', region_scope: 'province', location_source: 'ip', location_accuracy: 'province', location_consent_state: 'granted', location_enabled: true }), ['IP gần đúng', 'Cấp tỉnh']],
    ['off', preferenceFixture({ region_id: 'province-vl', region_label: 'Vĩnh Long', region_scope: 'province', location_source: 'manual', location_accuracy: 'province', location_consent_state: 'off', location_enabled: false }), ['Vị trí đang tắt', 'khu vực thủ công vẫn được dùng']],
    ['denied', preferenceFixture({ location_consent_state: 'denied' }), ['Quyền vị trí đã bị từ chối', 'chọn khu vực thủ công']],
    ['expired', preferenceFixture({ location_consent_state: 'expired' }), ['Quyền vị trí đã hết hạn', 'xác nhận lại']],
  ])('distinguishes the %s preference state without exposing exact age or location', async (_state, preferences, labels) => {
    const wrapper = await mountSettingsPage({ preferences })
    const panel = wrapper.get('#khu-vuc-de-xuat')

    for (const label of labels) expect(panel.text()).toContain(label)
    expect(panel.text()).not.toMatch(/Tuổi chính xác|Tọa độ|Địa chỉ IP|Điểm nội bộ/)
    expect(panel.get('[data-action="toggle-location"]').attributes('aria-label')).toBeTruthy()
    expect(panel.get('[data-action="toggle-personalization"]').attributes('aria-label')).toBeTruthy()
    expect(panel.get('[data-action="reset-recommendations"]').attributes('type')).toBe('button')
    wrapper.unmount()
  })

  it('keeps the cached snapshot readable offline, disables mutations, and retries explicitly', async () => {
    const wrapper = await mountSettingsPage({
      preferences: preferenceFixture({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'manual',
        location_accuracy: 'province',
        revision: 3,
      }),
    })
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
    window.dispatchEvent(new Event('offline'))
    await flushUi()

    const panel = wrapper.get('#khu-vuc-de-xuat')
    expect(panel.text()).toContain('Vĩnh Long')
    expect(panel.text()).toContain('Đang ngoại tuyến')
    expect(panel.get('[data-action="toggle-location"]').attributes()).toHaveProperty('disabled')
    expect(panel.get('[data-action="toggle-personalization"]').attributes()).toHaveProperty('disabled')
    expect(panel.get('[data-action="reset-recommendations"]').attributes()).toHaveProperty('disabled')
    expect(panel.get('[data-action="retry-preferences"]').attributes()).not.toHaveProperty('disabled')

    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
    await panel.get('[data-action="retry-preferences"]').trigger('click')
    await flushUi()
    expect(panel.text()).not.toContain('Đang ngoại tuyến')
    wrapper.unmount()
  })

  it('shows a same-revision 409 server snapshot and waits for an explicit retry', async () => {
    const serverSnapshot = preferenceFixture({
      region_id: 'province-tv',
      region_label: 'Trà Vinh',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    })
    const retriedSnapshot = preferenceFixture({
      region_id: 'province-bt',
      region_label: 'Bến Tre',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 6,
    })
    const wrapper = await mountSettingsPage({
      preferences: preferenceFixture({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'manual',
        location_accuracy: 'province',
        revision: 4,
      }),
      preferenceMutations: [
        { reject: { response: { status: 409, _data: serverSnapshot } } },
        retriedSnapshot,
      ],
    })

    await wrapper.get('[data-region="province-bt"]').trigger('click')
    await flushUi()

    const panel = wrapper.get('#khu-vuc-de-xuat')
    expect(panel.text()).toContain('Dữ liệu trên máy chủ đã thay đổi')
    expect(panel.text()).toContain('Trà Vinh')
    expect(panel.get('[data-action="retry-conflict"]').text()).toContain('Thử lưu lại')

    await panel.get('[data-action="retry-conflict"]').trigger('click')
    await flushUi()
    expect(panel.text()).toContain('Bến Tre')
    expect(panel.find('[data-action="retry-conflict"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('treats a non-409 snapshot payload as an ordinary failure and rolls back', async () => {
    const previous = preferenceFixture({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 4,
    })
    const unrelatedPayload = preferenceFixture({
      region_id: 'province-tv',
      region_label: 'Trà Vinh',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 9,
    })
    const wrapper = await mountSettingsPage({
      preferences: previous,
      preferenceMutations: [{ reject: { response: { status: 503, _data: unrelatedPayload } } }],
    })

    await wrapper.get('[data-region="province-bt"]').trigger('click')
    await flushUi()

    const panel = wrapper.get('#khu-vuc-de-xuat')
    expect(panel.text()).toContain('Vĩnh Long')
    expect(panel.text()).toContain('Không thể lưu thiết lập cá nhân hóa')
    expect(panel.find('[data-action="retry-conflict"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('rolls an optimistic toggle back when the preference mutation fails', async () => {
    const pending = deferred<PreferenceSnapshot>()
    const previous = preferenceFixture({ personalization_enabled: false, revision: 2 })
    const wrapper = await mountSettingsPage({ preferences: previous, preferenceMutations: [pending.promise] })
    const toggle = wrapper.get<HTMLInputElement>('[data-action="toggle-personalization"]')

    await toggle.setValue(true)
    expect(toggle.element.checked).toBe(true)
    pending.reject(new Error('save failed'))
    await flushUi()

    expect(toggle.element.checked).toBe(false)
    wrapper.unmount()
  })
})
