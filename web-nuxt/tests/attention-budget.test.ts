// @vitest-environment node

import { describe, expect, it } from 'vitest'
import { useAttentionBudget } from '../composables/useAttentionBudget'

function memoryStorage() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value) },
    removeItem: (key: string) => { values.delete(key) },
  }
}

describe('useAttentionBudget', () => {
  it('caps unique suggestions within a session without charging repeated renders', () => {
    const session = memoryStorage()
    const local = memoryStorage()
    const budget = useAttentionBudget({ sessionStorage: session, persistentStorage: local, maxSuggestions: 2, now: () => 1_000 })

    expect(budget.canSuggest('nearby')).toBe(true)
    expect(budget.canSuggest('nearby')).toBe(true)
    expect(budget.canSuggest('seasonal')).toBe(true)
    expect(budget.canSuggest('community')).toBe(false)
  })

  it('persists bounded dismissals across reload and keeps them after a session reset', () => {
    const session = memoryStorage()
    const local = memoryStorage()
    const first = useAttentionBudget({ sessionStorage: session, persistentStorage: local, now: () => 2_000 })
    first.dismiss('nearby')

    const reloaded = useAttentionBudget({ sessionStorage: memoryStorage(), persistentStorage: local, now: () => 2_100 })
    expect(reloaded.canSuggest('nearby')).toBe(false)
    reloaded.resetSession()
    expect(reloaded.canSuggest('nearby')).toBe(false)
    expect(reloaded.canSuggest('seasonal')).toBe(true)
  })

  it('expires old dismissals and stores no context payload', () => {
    const session = memoryStorage()
    const local = memoryStorage()
    let now = 3_000
    const first = useAttentionBudget({ sessionStorage: session, persistentStorage: local, dismissalTtlMs: 500, now: () => now })
    first.dismiss('nearby')

    now = 3_501
    const reloaded = useAttentionBudget({ sessionStorage: memoryStorage(), persistentStorage: local, dismissalTtlMs: 500, now: () => now })
    expect(reloaded.canSuggest('nearby')).toBe(true)
    expect(reloaded.dismiss('query=secret&gps=10.25,105.97')).toBe(false)
  })
})
