import { describe, expect, it } from 'vitest'
import { projectLocation, usePublicContextEnvelope } from '~/composables/usePublicContextEnvelope'
import type { PreferenceSnapshot } from '~/types/personalization'

const snapshot = (overrides: Partial<PreferenceSnapshot> = {}): PreferenceSnapshot => ({
  region_id: null, region_label: null, region_scope: 'unknown', location_source: 'default', location_accuracy: 'unknown',
  location_consent_state: 'unknown', location_enabled: false, personalization_enabled: false, explicit_interests: [],
  recommendation_reset_at: null, consent_version: null, location_reconfirm_required: false, revision: 0, ...overrides,
})

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
  it.each([
    ['manual-off', 'vinh-long', snapshot({ location_source: 'manual', location_accuracy: 'province', location_enabled: false }), 'selected', 'manual', 'province'],
    ['gps', 'vinh-long', snapshot({ location_source: 'gps', location_accuracy: 'province', location_enabled: true }), 'approximate', 'gps', 'province'],
    ['ip', 'vinh-long', snapshot({ location_source: 'ip', location_accuracy: 'ward', location_enabled: true }), 'exact', 'ip', 'ward'],
    ['unavailable', null, snapshot(), 'unavailable', 'default', 'unknown'],
  ])('projects %s provenance without raw location', (_name, region, prefs, mode, source, accuracy) => {
    const result = projectLocation(region, prefs)
    expect(result.mode).toBe(mode)
    expect(result.source).toBe(source)
    expect(result.accuracy).toBe(accuracy)
    expect(JSON.stringify(result)).not.toMatch(/latitude|longitude|coords/i)
  })
  it('keeps the envelope TTL explicit', () => {
    expect(usePublicContextEnvelope().envelope.value.ttlSeconds).toBe(300)
  })
})
