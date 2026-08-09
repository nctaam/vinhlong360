// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AISearchAssist from '../components/AISearchAssist.vue'

const capabilityModeState = vi.hoisted(() => ({ mode: 'deterministic' as 'deterministic' | 'enhanced' }))
const aiChat = vi.hoisted(() => vi.fn())

vi.mock('../composables/useAI', () => ({
  useAI: () => ({ aiChat }),
}))

mockNuxtImport('useFeature', () => () => ({
  capabilityMode: (capability: string) => capability === 'searchExpansion' ? capabilityModeState.mode : 'deterministic',
}))

mockNuxtImport('useSiteSettings', () => () => ({
  get: (_key: string, fallback: unknown) => fallback,
}))

describe('public capability consumers', () => {
  beforeEach(() => {
    capabilityModeState.mode = 'deterministic'
    aiChat.mockReset()
  })

  it('hides AI search expansion while keeping the component mountable when disabled', async () => {
    const wrapper = await mountSuspended(AISearchAssist, { props: { query: 'gốm' } })
    await nextTick()

    expect(wrapper.find('.ai-toggle-btn').exists()).toBe(false)
    expect(aiChat).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('exposes AI search expansion only when its public capability is enabled', async () => {
    capabilityModeState.mode = 'enhanced'
    const wrapper = await mountSuspended(AISearchAssist, { props: { query: 'gốm' } })
    await nextTick()

    expect(wrapper.find('.ai-toggle-btn').exists()).toBe(true)
    wrapper.unmount()
  })
})
