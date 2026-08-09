// @vitest-environment node

import { describe, it, expect } from 'vitest'
import { useJourneyActions } from '../composables/useJourneyActions'

const actions = useJourneyActions()
const { homepageDecisionActions } = actions

describe('homepageDecisionActions — personal-only', () => {
  it('returns nothing for an anonymous first-time visitor', () => {
    expect(homepageDecisionActions({ isLoggedIn: false, savedCount: 0, recentCount: 0, currentMonth: 7 })).toEqual([])
  })

  it('never emits editorial/generic echoes (event, heroFeature, map, community)', () => {
    const ids = homepageDecisionActions({
      isLoggedIn: true, savedCount: 5, recentCount: 3, currentMonth: 7,
      heroFeatureName: 'X', heroFeaturePlannerPath: '/tao-lich-trinh?add=x',
      upcomingEventName: 'Lễ', upcomingEventPath: '/dia-diem/le', communityPostCount: 9,
    }).map(a => a.id)
    expect(ids).not.toContain('home-start-planner')
    expect(ids).not.toContain('home-event')
    expect(ids).not.toContain('home-map')
    expect(ids).not.toContain('home-community')
  })

  it('emits the saved→plan action for a logged-in user with saves', () => {
    const ids = homepageDecisionActions({ isLoggedIn: true, savedCount: 5, recentCount: 0, currentMonth: 7 }).map(a => a.id)
    expect(ids).toContain('home-continue-saved')
  })

  it('emits the continue-recent action when there is recent history', () => {
    const ids = homepageDecisionActions({ isLoggedIn: false, savedCount: 0, recentCount: 4, currentMonth: 7 }).map(a => a.id)
    expect(ids).toContain('home-recent')
  })

  it('emits at most the two personal actions', () => {
    const actions = homepageDecisionActions({ isLoggedIn: true, savedCount: 5, recentCount: 4, currentMonth: 7 })
    expect(actions.length).toBeLessThanOrEqual(2)
  })

  it('uses semantic line-icon tokens and assigns at most one primary role', () => {
    const rails = [
      actions.searchRecoveryActions('chợ nổi'),
      actions.searchSuccessActions('chợ nổi', 5),
      actions.savedWorkspaceActions({ entityCount: 3, itineraryCount: 0 }),
      actions.homepageDecisionActions({ isLoggedIn: true, savedCount: 3, recentCount: 2, currentMonth: 8 }),
      actions.adminOpsActions({ healthStatus: 'ok', releaseGateOk: true, deployHealthBlocking: true, deployHostConfigured: true, rollbackReady: true }),
      actions.dataQualityQueueActions({ autoApply: 1, needsReview: 1, reject: 1, missingSource: 1, missingLocation: 0, missingPlaceId: 0, selectedAuto: 0 }),
    ]

    for (const rail of rails) {
      expect(rail.every(action => /^[a-z][a-z0-9-]*$/.test(action.icon))).toBe(true)
    }
    for (const rail of rails.slice(0, 4)) {
      expect(rail.filter(action => action.role === 'primary')).toHaveLength(1)
      expect(rail.filter(action => action.role === 'secondary').length).toBeLessThanOrEqual(2)
    }
  })
})
