import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { useAccessibilityProfile } from '~/composables/useAccessibilityProfile'
import { usePublicContextEnvelope } from '~/composables/usePublicContextEnvelope'
import type { RegionSlug } from '~/composables/useRegionPref'
import type { ContextEnvelope } from '~/types/publicExperience'
import type { PreferenceSnapshot } from '~/types/personalization'

const snapshot = (overrides: Partial<PreferenceSnapshot> = {}): PreferenceSnapshot => ({
  region_id: null, region_label: null, region_scope: 'unknown', location_source: 'default', location_accuracy: 'unknown',
  location_consent_state: 'unknown', location_enabled: false, personalization_enabled: false, explicit_interests: [],
  recommendation_reset_at: null, consent_version: null, location_reconfirm_required: false, revision: 0, ...overrides,
})

async function envelopeFor(region: RegionSlug | null, preferences: PreferenceSnapshot): Promise<ContextEnvelope> {
  useState('auth-user').value = null
  useState<RegionSlug | null>('regionPref', () => null).value = region
  useState<PreferenceSnapshot>('personalization-preferences-snapshot', snapshot).value = preferences
  let context: ReturnType<typeof usePublicContextEnvelope> | undefined
  const Harness = defineComponent({
    setup() {
      context = usePublicContextEnvelope()
      return () => h('div')
    },
  })
  const wrapper = await mountSuspended(Harness)
  const envelope = context!.envelope.value
  wrapper.unmount()
  return envelope
}

async function mountedEnvelope() {
  let context: ReturnType<typeof usePublicContextEnvelope> | undefined
  let accessibility: ReturnType<typeof useAccessibilityProfile> | undefined
  const Harness = defineComponent({
    setup() {
      context = usePublicContextEnvelope()
      accessibility = useAccessibilityProfile({ autoHydrate: false })
      return () => h('div')
    },
  })
  const wrapper = await mountSuspended(Harness)
  return { context: context!, accessibility: accessibility!, wrapper }
}

describe('public context envelope', () => {
  it('defaults location to unavailable and does not expose coordinates', () => {
    const { envelope } = usePublicContextEnvelope()
    expect(['unavailable', 'selected']).toContain(envelope.value.location.mode)
    expect(JSON.stringify(envelope.value)).not.toMatch(/latitude|longitude|coords|gps/i)
  })
  it('uses Bangkok local time fields rather than UTC serialization', () => {
    const { envelope } = usePublicContextEnvelope()
    expect(envelope.value.time.localDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(envelope.value.time.localTime).toMatch(/^\d{2}:\d{2}$/)
  })
  it('refreshes time-derived context after the declared TTL', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-10T00:00:00.000Z'))
    try {
      const { context, wrapper } = await mountedEnvelope()

      expect(context.envelope.value.time.localTime).toBe('07:00')
      vi.advanceTimersByTime(context.envelope.value.ttlSeconds * 1000)
      await nextTick()
      expect(context.envelope.value.time.localTime).toBe('07:05')

      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })
  it('projects shared accessibility preferences and live connectivity changes', async () => {
    const { context, accessibility, wrapper } = await mountedEnvelope()
    try {
      accessibility.setProfile({ reducedMotion: true, highContrast: true, textScale: 1.5 })
      await nextTick()
      expect(context.envelope.value.accessibility).toEqual({ reducedMotion: true, highContrast: true, textScale: 1.5 })

      window.dispatchEvent(new Event('offline'))
      await nextTick()
      expect(context.envelope.value.network).toBe('offline')

      window.dispatchEvent(new Event('online'))
      await nextTick()
      expect(context.envelope.value.network).toBe('online')
    } finally {
      wrapper.unmount()
    }
  })
  it.each([
    {
      name: 'manual selection while location is disabled',
      region: 'vinh-long' as const,
      preferences: snapshot({ location_source: 'manual', location_accuracy: 'province', location_enabled: false }),
      location: { mode: 'selected', confidence: 'medium', source: 'manual', accuracy: 'province' },
      signals: ['selected-region'],
      area: { id: 'vinh-long' },
    },
    {
      name: 'GPS-derived region',
      region: 'vinh-long' as const,
      preferences: snapshot({ location_source: 'gps', location_accuracy: 'province', location_enabled: true }),
      location: { mode: 'approximate', confidence: 'low', source: 'gps', accuracy: 'province' },
      signals: ['location-signal'],
      area: { id: 'vinh-long' },
    },
    {
      name: 'IP-derived region',
      region: 'vinh-long' as const,
      preferences: snapshot({ location_source: 'ip', location_accuracy: 'ward', location_enabled: true }),
      location: { mode: 'exact', confidence: 'high', source: 'ip', accuracy: 'ward' },
      signals: ['location-signal'],
      area: { id: 'vinh-long' },
    },
    {
      name: 'unavailable location',
      region: null,
      preferences: snapshot(),
      location: { mode: 'unavailable', confidence: 'low', source: 'default', accuracy: 'unknown' },
      signals: [],
      area: undefined,
    },
  ])('emits the complete $name envelope projection', async ({ region, preferences, location, signals, area }) => {
    const envelope = await envelopeFor(region, preferences)

    expect(envelope.location).toEqual(location)
    expect(envelope.ttlSeconds).toBe(300)
    expect(envelope.explainableSignals).toEqual(signals)
    expect(envelope.area).toEqual(area)
    expect(JSON.stringify(envelope)).not.toMatch(/latitude|longitude|coords/i)
  })
})
