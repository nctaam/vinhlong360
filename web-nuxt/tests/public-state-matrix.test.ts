import { describe, expect, it } from 'vitest'
import {
  PUBLIC_ROUTE_SPECS,
  PUBLIC_STATE_KINDS,
  buildPublicStateMatrix,
  evaluatePublicStateEvidence,
} from '../../scripts/smoke_e2e_chrome.mjs'

describe('public vertical-slice state matrix', () => {
  it('covers every required route and state without collapsing retryable 5xx into 404', () => {
    const matrix = buildPublicStateMatrix()

    expect(matrix).toHaveLength(PUBLIC_ROUTE_SPECS.length * PUBLIC_STATE_KINDS.length)
    expect(new Set(matrix.map(scenario => `${scenario.route.key}:${scenario.state}`)).size).toBe(matrix.length)

    for (const route of PUBLIC_ROUTE_SPECS) {
      expect(matrix.filter(scenario => scenario.route.key === route.key).map(scenario => scenario.state))
        .toEqual(PUBLIC_STATE_KINDS)
    }

    const retryableDetail = matrix.find(scenario => scenario.route.key === 'detail' && scenario.state === 'retryable-5xx')!
    expect(retryableDetail.expected.confirmed404).toBe(false)
    expect(retryableDetail.expected.actions).toContain('retry')
  })

  it('requires preserved content and local recovery for partial, stale and offline states', () => {
    for (const state of ['partial', 'stale', 'offline'] as const) {
      const scenario = buildPublicStateMatrix().find(item => item.route.key === 'search' && item.state === state)!
      const reasons = evaluatePublicStateEvidence(scenario, {
        shellVisible: true,
        mainVisible: true,
        contentVisible: false,
        actions: state === 'partial' ? ['retry-panel'] : [],
        confirmed404: false,
        actionDockOverlap: 0,
      })

      expect(reasons).toContain('content-not-preserved')
    }
  })

  it('accepts confirmed 404 only on detail and requires a way back to prior results', () => {
    const detail404 = buildPublicStateMatrix().find(item => item.route.key === 'detail' && item.state === '404-confirmed')!
    const validEvidence = {
      shellVisible: true,
      mainVisible: true,
      contentVisible: false,
      actions: ['back-to-results'],
      confirmed404: true,
      actionDockOverlap: 0,
    }

    expect(evaluatePublicStateEvidence(detail404, validEvidence)).toEqual([])

    const search404 = buildPublicStateMatrix().find(item => item.route.key === 'search' && item.state === '404-confirmed')!
    expect(evaluatePublicStateEvidence(search404, validEvidence)).toContain('false-404')
  })
})
