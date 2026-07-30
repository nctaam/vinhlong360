// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref, type Ref } from 'vue'

import PersonalizeSetupSheet from '../components/PersonalizeSetupSheet.vue'
import { usePersonalizationPreferences } from '../composables/usePersonalizationPreferences'
import { useRegionPref } from '../composables/useRegionPref'
import type { PreferenceSnapshot } from '../types/personalization'

const apiFetchMock = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({
  user: null as unknown as Ref<{ id: string } | null>,
  isLoggedIn: null as unknown as Ref<boolean>,
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer test-token' })),
  fetchCsrf: vi.fn(() => Promise.resolve('csrf-token')),
  fetchMe: vi.fn(() => Promise.resolve()),
}))

vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))
mockNuxtImport('useAuth', () => () => {
  if (!authState.user) authState.user = ref(null)
  if (!authState.isLoggedIn) authState.isLoggedIn = ref(false)
  return authState
})

const baseSnapshot: PreferenceSnapshot & { location_reconfirm_required: boolean } = {
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
  location_reconfirm_required: false,
  revision: 0,
}

function snapshot(overrides: Partial<PreferenceSnapshot> & { location_reconfirm_required?: boolean } = {}): PreferenceSnapshot {
  return { ...baseSnapshot, ...overrides }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((next, fail) => {
    resolve = next
    reject = fail
  })
  return { promise, resolve, reject }
}

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

function mockPreferenceApi(initial: PreferenceSnapshot = snapshot()) {
  let current = initial
  apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
    if (url === '/api/me/preferences' && !opts?.method) return Promise.resolve(current)
    if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
      const { revision: _revision, ...patch } = opts.body as Record<string, unknown>
      const { location_confirmation_token: confirmationToken, ...publicPatch } = patch
      const confirmedPatch = confirmationToken && current.location_source !== 'manual'
        ? {
            region_id: 'province-vl',
            region_label: 'Vĩnh Long',
            region_scope: 'province' as const,
            location_source: 'gps' as const,
            location_accuracy: 'province' as const,
          }
        : {}
      current = snapshot({
        ...current,
        ...publicPatch,
        ...confirmedPatch,
        revision: current.revision + 1,
      })
      return Promise.resolve(current)
    }
    if (url === '/api/me/location/resolve') {
      return Promise.resolve({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'gps',
        location_accuracy: 'province',
        confirmation_token: 'fixture-location-confirmation',
      })
    }
    return Promise.resolve(current)
  })
}

function mockPendingLocationConfirmation(pending: Promise<PreferenceSnapshot>) {
  let current = snapshot()
  apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
    if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
      const { revision: _revision, ...patch } = opts.body as Record<string, unknown>
      if (patch.location_confirmation_token) return pending
      current = snapshot({ ...current, ...patch, revision: current.revision + 1 })
      return Promise.resolve(current)
    }
    if (url === '/api/me/location/resolve') {
      return Promise.resolve({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'gps',
        location_accuracy: 'province',
        confirmation_token: 'fixture-location-confirmation',
      })
    }
    return Promise.resolve(current)
  })
}

async function hydratePreferences(initial: PreferenceSnapshot) {
  mockPreferenceApi(initial)
  let preferences: ReturnType<typeof usePersonalizationPreferences> | undefined
  const Harness = defineComponent({
    setup() {
      preferences = usePersonalizationPreferences()
      return () => h('div')
    },
  })
  const wrapper = await mountSuspended(Harness)
  await preferences!.refresh()
  await flushUi()
  wrapper.unmount()
  return preferences!
}

function mountSetupHarness(initiallyOpen = true) {
  const Harness = defineComponent({
    setup() {
      const open = ref(initiallyOpen)
      return () => h('div', [
        h('button', {
          type: 'button',
          'data-trigger': 'personalize',
          onClick: () => { open.value = true },
        }, 'Mở thiết lập'),
        h(PersonalizeSetupSheet, {
          modelValue: open.value,
          'onUpdate:modelValue': (value: boolean) => { open.value = value },
        }),
      ])
    },
  })
  return mountSuspended(Harness, {
    attachTo: document.body,
    global: { stubs: { IconLine: true } },
  })
}

async function advanceToLocationStep() {
  const dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
  ;(dialog.querySelector('[data-region="province-vl"]') as HTMLButtonElement).click()
  ;(dialog.querySelector('[data-action="continue"]') as HTMLButtonElement).click()
  await flushUi()
  ;((document.body.querySelector('[role="dialog"]') as HTMLElement)
    .querySelector('[data-action="continue"]') as HTMLButtonElement).click()
  await flushUi()
}

beforeEach(() => {
  if (!authState.user) authState.user = ref(null)
  if (!authState.isLoggedIn) authState.isLoggedIn = ref(false)
  localStorage.clear()
  authState.user.value = null
  authState.isLoggedIn.value = false
  authState.authHeaders.mockClear()
  authState.fetchCsrf.mockClear()
  authState.fetchMe.mockClear()
  apiFetchMock.mockReset()
  mockPreferenceApi()
})

afterEach(() => {
  localStorage.clear()
  document.body.innerHTML = ''
  document.body.style.overflow = ''
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('region preference ownership', () => {
  it('hydrates and persists the anonymous region only through local storage', async () => {
    localStorage.setItem('vl360-region-pref', 'ben-tre')
    let regionPref: ReturnType<typeof useRegionPref> | undefined
    const Harness = defineComponent({
      setup() {
        regionPref = useRegionPref()
        return () => h('div')
      },
    })
    const wrapper = await mountSuspended(Harness)
    await flushUi()

    expect(regionPref!.region.value).toBe('ben-tre')
    await regionPref!.setRegion('tra-vinh')
    expect(localStorage.getItem('vl360-region-pref')).toBe('tra-vinh')
    expect(apiFetchMock).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('ignores anonymous cache and derives authenticated region from the API snapshot', async () => {
    localStorage.setItem('vl360-region-pref', 'vinh-long')
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    mockPreferenceApi(snapshot({
      region_id: 'province-bt',
      region_label: 'Bến Tre',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      revision: 3,
    }))
    let regionPref: ReturnType<typeof useRegionPref> | undefined
    const Harness = defineComponent({
      setup() {
        regionPref = useRegionPref()
        return () => h('div')
      },
    })
    const wrapper = await mountSuspended(Harness)
    await flushUi()

    expect(regionPref!.region.value).toBe('ben-tre')
    await regionPref!.setRegion('tra-vinh')
    expect(apiFetchMock).toHaveBeenLastCalledWith('/api/me/preferences', expect.objectContaining({
      method: 'PATCH',
      body: expect.objectContaining({
        revision: 3,
        region_id: 'province-tv',
        location_source: 'manual',
      }),
    }))
    expect(localStorage.getItem('vl360-region-pref')).toBe('vinh-long')
    wrapper.unmount()
  })

  it('falls back to all regions without crashing on a malformed authenticated snapshot', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    apiFetchMock.mockResolvedValue({ region_id: 42, revision: 'bad' })
    let regionPref: ReturnType<typeof useRegionPref> | undefined
    const Harness = defineComponent({
      setup() {
        regionPref = useRegionPref()
        return () => h('div')
      },
    })
    const wrapper = await mountSuspended(Harness)
    await flushUi()

    expect(regionPref!.region.value).toBe('all')
    wrapper.unmount()
  })

  it('ignores a disabled GPS region while keeping a disabled manual region active', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    mockPreferenceApi(snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'gps',
      location_accuracy: 'province',
      location_enabled: false,
      revision: 2,
    }))
    let gpsPref: ReturnType<typeof useRegionPref> | undefined
    const GpsHarness = defineComponent({
      setup() {
        gpsPref = useRegionPref()
        return () => h('div')
      },
    })
    const gpsWrapper = await mountSuspended(GpsHarness)
    await flushUi()

    expect(gpsPref!.region.value).toBe('all')
    gpsWrapper.unmount()

    mockPreferenceApi(snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      location_enabled: false,
      revision: 3,
    }))
    let manualPref: ReturnType<typeof useRegionPref> | undefined
    const ManualHarness = defineComponent({
      setup() {
        manualPref = useRegionPref()
        return () => h('div')
      },
    })
    const manualWrapper = await mountSuspended(ManualHarness)
    await flushUi()

    expect(manualPref!.region.value).toBe('vinh-long')
    manualWrapper.unmount()
  })

  it.each([
    ['manual', true, 'vinh-long'],
    ['gps', true, 'vinh-long'],
    ['ip', true, 'vinh-long'],
    ['default', false, 'all'],
  ] as const)('applies the %s source at the region consumer boundary', async (locationSource, locationEnabled, expectedRegion) => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    mockPreferenceApi(snapshot({
      region_id: locationSource === 'default' ? null : 'province-vl',
      region_label: locationSource === 'default' ? null : 'Vĩnh Long',
      region_scope: locationSource === 'default' ? 'unknown' : 'province',
      location_source: locationSource,
      location_accuracy: locationSource === 'default' ? 'unknown' : 'province',
      location_consent_state: locationSource === 'default' ? 'unknown' : 'granted',
      location_enabled: locationEnabled,
      revision: 4,
    }))
    let regionPref: ReturnType<typeof useRegionPref> | undefined
    const Harness = defineComponent({
      setup() {
        regionPref = useRegionPref()
        return () => h('div', { 'data-region-result': regionPref!.region.value })
      },
    })
    const wrapper = await mountSuspended(Harness)
    await flushUi()

    expect(wrapper.attributes('data-region-result')).toBe(expectedRegion)
    wrapper.unmount()
  })
})

describe('optional location consent flow', () => {
  it('applies manual over GPS over IP when the real setup receives competing signals', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    await hydratePreferences(snapshot({
      region_id: 'province-bt',
      region_label: 'Bến Tre',
      region_scope: 'province',
      location_source: 'ip',
      location_accuracy: 'province',
      location_consent_state: 'granted',
      location_enabled: true,
      revision: 4,
    }))
    const getCurrentPosition = vi.fn((success: PositionCallback) => {
      success({ coords: { latitude: 10.24, longitude: 105.97 } } as GeolocationPosition)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })

    const gpsWrapper = await mountSetupHarness()
    let dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement).click()
    await flushUi()
    gpsWrapper.unmount()

    const manualWrapper = await mountSetupHarness()
    dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog().querySelector('[data-region="province-tv"]') as HTMLButtonElement).click()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement).click()
    await flushUi()

    const grantedPatches = apiFetchMock.mock.calls
      .filter(([url, request]) => url === '/api/me/preferences' && request?.method === 'PATCH')
      .map(([, request]) => request.body as Record<string, unknown>)
      .filter(body => body.location_consent_state === 'granted')
    expect(grantedPatches).toHaveLength(2)
    expect(grantedPatches[0]).toMatchObject({
      location_confirmation_token: 'fixture-location-confirmation',
      location_enabled: true,
    })
    expect(grantedPatches[0]).not.toHaveProperty('region_id')
    expect(grantedPatches[0]).not.toHaveProperty('region_label')
    expect(grantedPatches[0]).not.toHaveProperty('location_source')
    expect(grantedPatches[1]).toMatchObject({ location_enabled: true })
    expect(grantedPatches[1]).not.toHaveProperty('region_id')
    expect(grantedPatches[1]).not.toHaveProperty('location_source')
    expect(getCurrentPosition).toHaveBeenCalledTimes(2)

    let regionPref: ReturnType<typeof useRegionPref> | undefined
    const RegionConsumer = defineComponent({
      setup() {
        regionPref = useRegionPref()
        return () => h('output', { 'data-final-region': regionPref!.region.value })
      },
    })
    const regionWrapper = await mountSuspended(RegionConsumer)
    await flushUi()
    expect(regionWrapper.get('output').attributes('data-final-region')).toBe('tra-vinh')
    regionWrapper.unmount()
    manualWrapper.unmount()
  })

  it('blocks explicit GPS and IP resolution attempts after location is off', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const preferences = await hydratePreferences(snapshot({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'manual',
      location_accuracy: 'province',
      location_consent_state: 'off',
      location_enabled: false,
      revision: 5,
    }))
    apiFetchMock.mockClear()

    const gps = await preferences.resolveLocation('gps', { latitude: 10.24, longitude: 105.97 })
    const ip = await preferences.resolveLocation('ip')

    expect(gps).toMatchObject({ region_id: null, location_source: 'gps', location_accuracy: 'unknown' })
    expect(ip).toMatchObject({ region_id: null, location_source: 'ip', location_accuracy: 'unknown' })
    expect(apiFetchMock.mock.calls.filter(([url]) => url === '/api/me/location/resolve')).toHaveLength(0)
  })

  it('uses toggle-button semantics for manual region choices', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const wrapper = await mountSetupHarness()
    await flushUi()

    const dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
    const regionGroup = dialog.querySelector('[data-panel="region"] .setup-option-grid') as HTMLElement
    const vinhLong = dialog.querySelector('[data-region="province-vl"]') as HTMLButtonElement

    expect(regionGroup.getAttribute('role')).toBe('group')
    expect(dialog.querySelector('[role="listbox"]')).toBeNull()
    expect(dialog.querySelector('[role="option"]')).toBeNull()
    expect(vinhLong.getAttribute('aria-pressed')).toBe('false')

    vinhLong.click()
    await nextTick()
    expect(vinhLong.getAttribute('aria-pressed')).toBe('true')
    wrapper.unmount()
  })

  it('offers the same skip route at every setup step', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true

    for (const targetStep of [0, 1, 2]) {
      const wrapper = await mountSetupHarness()
      await flushUi()
      const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement

      if (targetStep >= 1) {
        ;(dialog().querySelector('[data-region="province-vl"]') as HTMLButtonElement).click()
        ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
        await flushUi()
      }
      if (targetStep >= 2) {
        ;(dialog().querySelector('[data-interest="food"]') as HTMLButtonElement).click()
        ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
        await flushUi()
      }

      const activeDialog = document.body.querySelector('[role="dialog"]') as HTMLElement
      expect(activeDialog?.getAttribute('data-step')).toBe(String(targetStep + 1))
      const skip = activeDialog?.querySelector('[data-action="skip"]') as HTMLButtonElement
      expect(skip?.textContent).toBe('Bỏ qua, thiết lập sau')
      skip.click()
      await flushUi()
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
      wrapper.unmount()
    }
  })

  it('does not loop the browser prompt after permission is denied', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const getCurrentPosition = vi.fn((_success: PositionCallback, error: PositionErrorCallback) => {
      error({ code: 1, message: 'denied', PERMISSION_DENIED: 1 } as GeolocationPositionError)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog().querySelector('[data-region="province-vl"]') as HTMLButtonElement).click()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()

    ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    await flushUi()

    expect(getCurrentPosition).toHaveBeenCalledTimes(1)
    expect(dialog().querySelector('[role="status"]')?.textContent).toContain('bị từ chối')
    await flushUi()
    expect(getCurrentPosition).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('does not offer completion while denied-consent persistence is pending', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const deniedSave = deferred<PreferenceSnapshot>()
    let current = snapshot()
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
        const { revision: _revision, ...patch } = opts.body as Record<string, unknown>
        if (patch.location_consent_state === 'denied') return deniedSave.promise
        current = snapshot({ ...current, ...patch, revision: current.revision + 1 })
        return Promise.resolve(current)
      }
      return Promise.resolve(current)
    })
    const getCurrentPosition = vi.fn((_success: PositionCallback, error: PositionErrorCallback) => {
      error({ code: 1, message: 'denied', PERMISSION_DENIED: 1 } as GeolocationPositionError)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()

    try {
      await flushUi()
      await advanceToLocationStep()
      const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement

      ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
      await flushUi()
      const finishWhilePending = dialog().querySelector('[data-action="finish"]')

      deniedSave.resolve(snapshot({
        region_id: 'province-vl',
        region_label: 'Vĩnh Long',
        region_scope: 'province',
        location_source: 'manual',
        location_accuracy: 'province',
        location_consent_state: 'denied',
        location_enabled: false,
        revision: 3,
      }))
      await flushUi()

      expect(finishWhilePending).toBeNull()
      expect(dialog().querySelector('[data-action="finish"]')).toBeTruthy()
      expect(getCurrentPosition).toHaveBeenCalledTimes(1)
    } finally {
      deniedSave.resolve(snapshot())
      wrapper.unmount()
    }
  })

  it('offers retry or skip instead of completion when denied-consent persistence fails', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    let current = snapshot()
    let deniedAttempts = 0
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
        const { revision: _revision, ...patch } = opts.body as Record<string, unknown>
        if (patch.location_consent_state === 'denied') {
          deniedAttempts += 1
          if (deniedAttempts === 1) return Promise.reject(new Error('save failed'))
        }
        current = snapshot({ ...current, ...patch, revision: current.revision + 1 })
        return Promise.resolve(current)
      }
      return Promise.resolve(current)
    })
    const getCurrentPosition = vi.fn((_success: PositionCallback, error: PositionErrorCallback) => {
      error({ code: 1, message: 'denied', PERMISSION_DENIED: 1 } as GeolocationPositionError)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()

    try {
      await flushUi()
      await advanceToLocationStep()
      const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement

      ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
      await flushUi()

      expect(dialog().querySelector('[data-action="finish"]')).toBeNull()
      expect(dialog().querySelector('[data-action="retry-denial"]')).toBeTruthy()
      expect(dialog().querySelector('[data-action="skip"]')).toBeTruthy()

      ;(dialog().querySelector('[data-action="retry-denial"]') as HTMLButtonElement).click()
      await flushUi()

      expect(dialog().querySelector('[data-action="finish"]')).toBeTruthy()
      expect(getCurrentPosition).toHaveBeenCalledTimes(1)
      expect(deniedAttempts).toBe(2)
    } finally {
      wrapper.unmount()
    }
  })

  it('keeps a manually selected all-region scope when GPS is confirmed', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const getCurrentPosition = vi.fn((success: PositionCallback) => {
      success({ coords: { latitude: 10.24, longitude: 105.97 } } as GeolocationPosition)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement

    ;(dialog().querySelector('[data-region="all"]') as HTMLButtonElement).click()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement).click()
    await flushUi()

    const confirmationPatch = apiFetchMock.mock.calls.at(-1)?.[1]?.body as Record<string, unknown>
    expect(confirmationPatch).toMatchObject({
      location_consent_state: 'granted',
      location_enabled: true,
    })
    expect(confirmationPatch).not.toHaveProperty('region_id')
    expect(confirmationPatch).not.toHaveProperty('location_source')
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    wrapper.unmount()
  })

  it('discards a stale location token and requires an explicit resolve again', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) => success({
          coords: { latitude: 10.24, longitude: 105.97 },
        } as GeolocationPosition),
      },
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    await flushUi()
    apiFetchMock.mockRejectedValueOnce({
      response: { status: 409, _data: snapshot({ revision: 2, location_reconfirm_required: true }) },
    })

    const confirm = dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement
    confirm.focus()
    confirm.click()
    await flushUi()
    await nextTick()

    expect(dialog().textContent).toContain('xác định lại khu vực')
    expect(dialog().querySelector('[data-action="confirm-location"]')).toBeNull()
    const retry = dialog().querySelector('[data-action="retry-location"]') as HTMLButtonElement
    expect(retry).toBeTruthy()
    expect(document.activeElement).toBe(retry)
    wrapper.unmount()
  })

  it('ignores a stale confirmation after the sheet closes and reopens', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const pendingConfirmation = deferred<PreferenceSnapshot>()
    mockPendingLocationConfirmation(pendingConfirmation.promise)
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) => success({
          coords: { latitude: 10.24, longitude: 105.97 },
        } as GeolocationPosition),
      },
    })
    const wrapper = await mountSetupHarness()

    try {
      await flushUi()
      const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement).click()
      await flushUi()

      ;(dialog().querySelector('[data-action="skip"]') as HTMLButtonElement).click()
      await flushUi()
      await wrapper.get('[data-trigger="personalize"]').trigger('click')
      await flushUi()

      pendingConfirmation.reject({
        response: { status: 409, _data: snapshot({ revision: 2, location_reconfirm_required: true }) },
      })
      await flushUi()
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()

      expect(dialog().querySelector('[data-action="use-location"]')).toBeTruthy()
      expect(dialog().querySelector('[data-action="retry-location"]')).toBeNull()
    } finally {
      pendingConfirmation.resolve(snapshot())
      wrapper.unmount()
    }
  })

  it('ignores a confirmation completion after the authenticated account changes', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const pendingConfirmation = deferred<PreferenceSnapshot>()
    mockPendingLocationConfirmation(pendingConfirmation.promise)
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) => success({
          coords: { latitude: 10.24, longitude: 105.97 },
        } as GeolocationPosition),
      },
    })
    const wrapper = await mountSetupHarness()

    try {
      await flushUi()
      const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="confirm-location"]') as HTMLButtonElement).click()
      await flushUi()

      authState.user.value = { id: 'user-2' }
      await flushUi()
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()

      pendingConfirmation.reject({
        response: { status: 409, _data: snapshot({ revision: 2, location_reconfirm_required: true }) },
      })
      await flushUi()
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()

      await wrapper.get('[data-trigger="personalize"]').trigger('click')
      await flushUi()
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()
      ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
      await flushUi()

      expect(dialog().querySelector('[data-action="use-location"]')).toBeTruthy()
      expect(dialog().querySelector('[data-action="retry-location"]')).toBeNull()
    } finally {
      pendingConfirmation.resolve(snapshot())
      wrapper.unmount()
    }
  })

  it('stays on the current step when saving a region fails', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') return Promise.reject(new Error('save failed'))
      return Promise.resolve(snapshot())
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement

    ;(dialog().querySelector('[data-region="province-vl"]') as HTMLButtonElement).click()
    ;(dialog().querySelector('[data-action="continue"]') as HTMLButtonElement).click()
    await flushUi()

    expect(dialog().getAttribute('data-step')).toBe('1')
    expect(dialog().querySelector('[role="alert"]')?.textContent).toContain('Không thể lưu')
    wrapper.unmount()
  })

  it('ignores a geolocation callback from a previous sheet attempt after close and reopen', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    let lateSuccess!: PositionCallback
    const getCurrentPosition = vi.fn((success: PositionCallback) => { lateSuccess = success })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    await advanceToLocationStep()

    let dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog.querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    ;(dialog.querySelector('[data-action="skip"]') as HTMLButtonElement).click()
    await flushUi()
    await wrapper.get('[data-trigger="personalize"]').trigger('click')
    await flushUi()
    await advanceToLocationStep()

    lateSuccess({ coords: { latitude: 10.24, longitude: 105.97 } } as GeolocationPosition)
    await flushUi()

    dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
    expect(apiFetchMock.mock.calls.some(([url]) => url === '/api/me/location/resolve')).toBe(false)
    expect(dialog.querySelector('[data-action="use-location"]')).toBeTruthy()
    wrapper.unmount()
  })

  it('ignores a geolocation callback after the authenticated account changes', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    let lateSuccess!: PositionCallback
    const getCurrentPosition = vi.fn((success: PositionCallback) => { lateSuccess = success })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    await advanceToLocationStep()

    const dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog.querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    authState.user.value = { id: 'user-2' }
    lateSuccess({ coords: { latitude: 10.24, longitude: 105.97 } } as GeolocationPosition)
    await flushUi()

    expect(apiFetchMock.mock.calls.some(([url]) => url === '/api/me/location/resolve')).toBe(false)
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    wrapper.unmount()
  })

  it('closes an open setup before another account can save the previous account selection', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    const wrapper = await mountSetupHarness()

    try {
      await flushUi()
      const dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
      ;(dialog.querySelector('[data-region="province-vl"]') as HTMLButtonElement).click()

      authState.user.value = { id: 'user-2' }
      await flushUi()

      const preferencePatches = apiFetchMock.mock.calls.filter(([url, opts]) => (
        url === '/api/me/preferences' && (opts as Record<string, unknown> | undefined)?.method === 'PATCH'
      ))
      expect(preferencePatches).toHaveLength(0)
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    } finally {
      wrapper.unmount()
    }
  })

  it('does not apply a location resolution that completes after the sheet closes', async () => {
    authState.user.value = { id: 'user-1' }
    authState.isLoggedIn.value = true
    let resolveLocation!: (value: Record<string, unknown>) => void
    const resolutionPromise = new Promise<Record<string, unknown>>((resolve) => { resolveLocation = resolve })
    apiFetchMock.mockImplementation((url: string, opts?: Record<string, unknown>) => {
      if (url === '/api/me/location/resolve') return resolutionPromise
      if (url === '/api/me/preferences' && opts?.method === 'PATCH') {
        const { revision: _revision, ...patch } = opts.body as Record<string, unknown>
        return Promise.resolve(snapshot({ ...patch, revision: 1 }))
      }
      return Promise.resolve(snapshot())
    })
    const getCurrentPosition = vi.fn((success: PositionCallback) => {
      success({ coords: { latitude: 10.24, longitude: 105.97 } } as GeolocationPosition)
    })
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: { getCurrentPosition },
    })
    const wrapper = await mountSetupHarness()
    await flushUi()
    await advanceToLocationStep()

    const dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
    ;(dialog.querySelector('[data-action="use-location"]') as HTMLButtonElement).click()
    await flushUi()
    ;(dialog.querySelector('[data-action="skip"]') as HTMLButtonElement).click()
    await flushUi()

    resolveLocation({
      region_id: 'province-vl',
      region_label: 'Vĩnh Long',
      region_scope: 'province',
      location_source: 'gps',
      location_accuracy: 'province',
    })
    await flushUi()
    await wrapper.get('[data-trigger="personalize"]').trigger('click')
    await flushUi()
    await advanceToLocationStep()

    expect((document.body.querySelector('[role="dialog"]') as HTMLElement)
      .querySelector('[data-action="use-location"]')).toBeTruthy()
    wrapper.unmount()
  })

  it('closes on Escape and restores focus to the trigger', async () => {
    const originalOffsetParent = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetParent')
    Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
      configurable: true,
      get: () => document.body,
    })

    try {
      const wrapper = await mountSetupHarness(false)
      const trigger = wrapper.get('[data-trigger="personalize"]')
      ;(trigger.element as HTMLElement).focus()
      await trigger.trigger('click')
      await flushUi()

      const dialog = document.body.querySelector('[role="dialog"]') as HTMLElement
      expect(dialog.contains(document.activeElement)).toBe(true)
      expect(document.body.style.overflow).toBe('hidden')

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await flushUi()

      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
      expect(document.body.style.overflow).toBe('')
      expect(document.activeElement).toBe(trigger.element)
      wrapper.unmount()
    } finally {
      if (originalOffsetParent) Object.defineProperty(HTMLElement.prototype, 'offsetParent', originalOffsetParent)
      else Reflect.deleteProperty(HTMLElement.prototype, 'offsetParent')
    }
  })
})
