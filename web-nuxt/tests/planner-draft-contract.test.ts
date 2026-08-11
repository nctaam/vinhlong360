import { describe, expect, it } from 'vitest'
import {
  createPlannerDraftSnapshot,
  parsePlannerDraftSnapshot,
} from '../composables/useItineraryOptimization'

const stop = {
  id: 'start',
  name: 'Start',
  type: 'attraction',
  coords: [10.01, 106.01] as [number, number],
  time: '',
  notes: 'Local note',
}

const legacyDraft = {
  title: 'Local title',
  stops: [stop],
  revision: 7,
  savedAt: '2026-08-11T12:00:00Z',
  source: 'server' as const,
  travelBudgetMinutes: 90,
}

describe('planner draft server identity contract', () => {
  it('round-trips a valid server plan id and positive comparison revision', () => {
    const snapshot = createPlannerDraftSnapshot({
      ...legacyDraft,
      serverPlanId: ' server-plan ',
      serverRevision: 5,
    })

    expect(snapshot).toEqual({
      ...legacyDraft,
      stops: [{ ...stop }],
      serverPlanId: 'server-plan',
      serverRevision: 5,
    })
    expect(parsePlannerDraftSnapshot(snapshot)).toEqual(snapshot)
  })

  it('omits server identity from local-source drafts even when supplied', () => {
    const snapshot = createPlannerDraftSnapshot({
      ...legacyDraft,
      source: 'local',
      serverPlanId: 'server-plan',
      serverRevision: 5,
    })

    expect(snapshot).toEqual({
      ...legacyDraft,
      source: 'local',
      stops: [{ ...stop }],
    })
  })

  it.each([
    { serverPlanId: 'server-plan' },
    { serverRevision: 5 },
    { serverPlanId: '   ', serverRevision: 5 },
    { serverPlanId: 'server-plan', serverRevision: 0 },
    { serverPlanId: 'server-plan', serverRevision: '5' },
    { serverPlanId: 'server-plan', serverRevision: true },
  ])('drops a malformed or partial server identity pair: %o', identity => {
    const parsed = parsePlannerDraftSnapshot({ ...legacyDraft, ...identity })

    expect(parsed).toEqual({
      ...legacyDraft,
      stops: [{ ...stop }],
    })
  })

  it('keeps legacy server drafts without identity backward compatible', () => {
    expect(parsePlannerDraftSnapshot(legacyDraft)).toEqual({
      ...legacyDraft,
      stops: [{ ...stop }],
    })
  })
})
