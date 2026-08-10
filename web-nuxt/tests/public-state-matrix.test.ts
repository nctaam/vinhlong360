import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PageState from '../components/public/PageState.vue'
import { resolveDetailFetchError } from '../utils/detailExperience'
import {
  PUBLIC_ROUTE_SPECS,
  PUBLIC_STATE_KINDS,
  buildPublicStateFixture,
  buildPublicStateMatrix,
  evaluatePublicStateEvidence,
} from '../../scripts/smoke_e2e_chrome.mjs'

const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

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

  it('executes every matrix row through the real page-state and detail resolution behavior', async () => {
    for (const scenario of buildPublicStateMatrix()) {
      const fixture = buildPublicStateFixture(scenario)
      const routePath = scenario.route.path.replace('{id}', 'gom-do-mang-thit')
      await navigateTo(routePath)

      if (fixture.detailFailure) {
        const resolution = resolveDetailFetchError(fixture.detailFailure)
        expect(resolution.kind, `${scenario.route.key}:${scenario.state}`).toBe(fixture.detailResolution)
        if (resolution.kind === 'not_found') {
          expect(scenario.expected.actions).toContain('back-to-results')
          continue
        }
      }

      const retry = vi.fn(() => Promise.resolve())
      const recovery = vi.fn()
      const wrapper = await mountSuspended(PageState, {
        route: routePath,
        props: { state: fixture.surfaceState!, retry, recovery },
        slots: { default: '<p data-matrix-content>Nội dung tuyến công khai</p>' },
      })
      wrappers.push(wrapper)

      expect(wrapper.vm.$route.path, `${scenario.route.key}:${scenario.state}`).toBe(routePath)
      expect(wrapper.get(`[data-page-state="${fixture.surfaceState!.kind}"]`)).toBeTruthy()

      if (scenario.expected.preserveContent || scenario.expected.contentVisible) {
        expect(wrapper.get('[data-matrix-content]').text()).toContain('Nội dung tuyến công khai')
      }
      if (scenario.expected.actions.includes('retry') || scenario.expected.actions.includes('retry-panel')) {
        await wrapper.get('[data-page-state-retry]').trigger('click')
        expect(retry).toHaveBeenCalledOnce()
      }
      if (scenario.expected.actions.includes('recover')) {
        await wrapper.get('[data-page-state-recovery]').trigger('click')
        expect(recovery).toHaveBeenCalledOnce()
      }
    }
  })
})
