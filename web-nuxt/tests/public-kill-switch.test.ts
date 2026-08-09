import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useFeature } from '../composables/useFeature'
import { PUBLIC_CAPABILITY_FLAGS, featureFlagDefault } from '../utils/featureFlags'

const settings = vi.hoisted(() => ({
  unavailable: false,
  flags: {} as Record<string, unknown>,
}))

mockNuxtImport('useSiteSettings', () => () => ({
  get: (key: string, fallback?: unknown) => {
    if (settings.unavailable) throw new Error('settings unavailable')
    return key === 'features.flags' ? settings.flags : fallback
  },
}))

describe('public feature kill switches', () => {
  beforeEach(() => {
    settings.unavailable = false
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

  it('switches capabilities independently without affecting core task families', () => {
    settings.flags = {
      [PUBLIC_CAPABILITY_FLAGS.recommendation]: true,
      [PUBLIC_CAPABILITY_FLAGS.optimizer]: false,
    }
    const feature = useFeature()

    expect(feature.capabilityMode('recommendation')).toBe('enhanced')
    expect(feature.capabilityMode('optimizer')).toBe('deterministic')
    expect(feature.capabilityMode('searchExpansion')).toBe('deterministic')
    expect(Object.values(feature.capabilityModes.value)).not.toContain('blocked')
  })

  it('fails closed when settings are unavailable, malformed or unknown', () => {
    settings.unavailable = true
    let feature = useFeature()
    expect(feature.capabilityMode('personalization')).toBe('deterministic')
    expect(feature.enabled('ai_recommendations')).toBe(false)

    settings.unavailable = false
    settings.flags = {
      [PUBLIC_CAPABILITY_FLAGS.personalization]: 'yes',
      ai_recommendations: 'yes',
    }
    feature = useFeature()
    expect(feature.capabilityMode('personalization')).toBe('deterministic')
    expect(feature.enabled('ai_recommendations')).toBe(false)
    expect(feature.enabled('unknown-public-enhancement')).toBe(false)
  })
})
