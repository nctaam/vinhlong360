import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useFeature } from '../composables/useFeature'
import { PUBLIC_CAPABILITY_FLAGS, featureFlagDefault } from '../utils/featureFlags'

const settings = vi.hoisted(() => ({
  status: 'success' as 'success' | 'error',
  present: true,
  flags: {} as unknown,
}))

mockNuxtImport('useSiteSettings', () => () => ({
  settings: {
    get value() {
      return settings.present ? { 'features.flags': settings.flags } : {}
    },
  },
  available: {
    get value() {
      return settings.status === 'success'
    },
  },
  get: (key: string, fallback?: unknown) => {
    if (settings.status === 'error' || !settings.present) return fallback
    return key === 'features.flags' ? settings.flags : fallback
  },
}))

describe('public feature kill switches', () => {
  beforeEach(() => {
    settings.status = 'success'
    settings.present = true
    settings.flags = {}
  })

  it('defaults every adaptive capability to deterministic mode', () => {
    const feature = useFeature()

    for (const key of Object.values(PUBLIC_CAPABILITY_FLAGS)) {
      expect(featureFlagDefault(key)).toBe(false)
    }
    expect(feature.capabilityModes.value).toEqual({
      personalization: 'deterministic',
      recommendation: 'deterministic',
      searchExpansion: 'deterministic',
      optimizer: 'deterministic',
      proactiveNotices: 'deterministic',
    })
  })

  it('bridges real legacy consumers to independent public capability switches', () => {
    settings.flags = {
      ai_recommendations: true,
      preference_ui_v1: true,
      ai_tips: true,
      [PUBLIC_CAPABILITY_FLAGS.recommendation]: true,
      [PUBLIC_CAPABILITY_FLAGS.personalization]: false,
      [PUBLIC_CAPABILITY_FLAGS.proactiveNotices]: false,
    }
    const feature = useFeature()

    expect(feature.capabilityMode('recommendation')).toBe('enhanced')
    expect(feature.enabled('ai_recommendations')).toBe(true)
    expect(feature.enabled('preference_ui_v1')).toBe(false)
    expect(feature.enabled('ai_tips')).toBe(false)
  })

  it.each([
    ['missing settings', 'success', false, {}],
    ['failed settings request', 'error', true, { ai_recommendations: true }],
    ['malformed settings flags', 'success', true, 'not-a-feature-flag-object'],
  ] as const)('keeps legacy defaults but fails every public capability closed for %s', (_name, status, present, flags) => {
    settings.status = status
    settings.present = present
    settings.flags = flags

    const feature = useFeature()

    expect(feature.enabled('chat_widget')).toBe(true)
    expect(feature.enabled('reviews')).toBe(true)
    expect(feature.enabled('unknown-public-enhancement')).toBe(false)
    for (const capability of Object.keys(PUBLIC_CAPABILITY_FLAGS) as Array<keyof typeof PUBLIC_CAPABILITY_FLAGS>) {
      expect(feature.enabled(PUBLIC_CAPABILITY_FLAGS[capability])).toBe(false)
      expect(feature.capabilityMode(capability)).toBe('deterministic')
    }
  })
})
