import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useUnifiedSearch } from '../composables/useUnifiedSearch'

vi.mock('../composables/usePublicApi', () => ({
  usePublicApi: () => ({ search: vi.fn() }),
}))

describe('zero-result recovery', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('offers deterministic recovery steps without mutating the active search', () => {
    const { zeroResultRecoveryActions } = useUnifiedSearch()
    const active = {
      query: 'gom do',
      intent: 'place' as const,
      filters: { type: 'craft_village', sort: 'nearby' },
      area: { id: 'vinh-long' },
      panel: 'list' as const,
    }

    const actions = zeroResultRecoveryActions(active, {
      suggestedQuery: 'gốm đỏ',
      hasRecentOrSaved: true,
    })

    expect(actions.map(action => action.id)).toEqual([
      'remove-filter',
      'widen-area',
      'correct-query',
      'intent-all',
      'recent-saved',
    ])
    expect(actions[0]?.patch).toEqual({ filters: { type: 'craft_village' } })
    expect(actions[2]?.patch).toEqual({ query: 'gốm đỏ' })
    expect(active).toEqual({
      query: 'gom do',
      intent: 'place',
      filters: { type: 'craft_village', sort: 'nearby' },
      area: { id: 'vinh-long' },
      panel: 'list',
    })
  })

  it('omits unavailable steps while preserving the recovery order', () => {
    const { zeroResultRecoveryActions } = useUnifiedSearch()
    const actions = zeroResultRecoveryActions({
      query: 'gốm đỏ',
      intent: 'all',
      filters: {},
      panel: 'list',
    })

    expect(actions.map(action => action.id)).toEqual(['recent-saved'])
  })
})
