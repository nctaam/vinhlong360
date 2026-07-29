// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import OnboardingSheet from '../components/OnboardingSheet.vue'
import PersonalizeSetupSheet from '../components/PersonalizeSetupSheet.vue'
import { usePersonalizationPreferences } from '../composables/usePersonalizationPreferences'
import type { PreferenceSnapshot } from '../types/personalization'

const apiFetchMock = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({
  user: { value: { id: 'user-1' } as { id: string } | null },
  isLoggedIn: { value: true },
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

function snapshot(overrides: Partial<PreferenceSnapshot> = {}): PreferenceSnapshot {
  return { ...defaultSnapshot, ...overrides }
}

function apiResultFor(url: string, opts?: Record<string, unknown>) {
  if (url === '/api/me/preferences' && !opts?.method) return Promise.resolve(snapshot())
  return Promise.resolve(snapshot({ revision: 1 }))
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((next) => { resolve = next })
  return { promise, resolve }
}

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
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

    expect(patchResult).toEqual({ ok: true, snapshot: patched })
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

    expect(await patchPromise).toEqual({ ok: true, snapshot: patched })
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
    expect(await patchPromise).toEqual({ ok: true, snapshot: patched })
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

    expect(result).toEqual({ ok: false, snapshot: defaultSnapshot })
    expect(preferences!.error.value).toBe('Không thể lưu thiết lập cá nhân hóa.')
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
