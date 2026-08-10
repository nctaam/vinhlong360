import { describe, expect, it } from 'vitest'
import {
  PUBLIC_ROUTE_SPECS,
  PUBLIC_VISUAL_THEMES,
  PUBLIC_VISUAL_VIEWPORTS,
  compareVisualArtifacts,
  createVisualArtifactManifest,
  createVisualBaselineScenarios,
  evaluateVisualReadiness,
  validateVisualArtifactForResume,
  visualScreenshotName,
} from '../../scripts/smoke_e2e_chrome.mjs'

describe('public visual baseline scenarios', () => {
  it('covers Nocturne and Parchment at every required viewport for every route', () => {
    const scenarios = createVisualBaselineScenarios()
    const expectedCount = PUBLIC_ROUTE_SPECS.length * PUBLIC_VISUAL_THEMES.length * PUBLIC_VISUAL_VIEWPORTS.length

    expect(scenarios).toHaveLength(expectedCount)
    expect(new Set(scenarios.map(scenario => scenario.fileName)).size).toBe(expectedCount)

    for (const route of PUBLIC_ROUTE_SPECS) {
      for (const theme of PUBLIC_VISUAL_THEMES) {
        expect(scenarios
          .filter(scenario => scenario.route.key === route.key && scenario.theme === theme)
          .map(scenario => scenario.viewport.width))
          .toEqual([375, 390, 768, 1024, 1440])
      }
    }
  })

  it('names screenshots by route, theme, viewport and state', () => {
    expect(visualScreenshotName({
      routeKey: 'detail',
      theme: 'parchment',
      viewport: { width: 390, height: 844 },
      state: 'retryable-5xx',
    })).toBe('detail__parchment__390px__retryable-5xx.png')
  })

  it('requires route identity, hydration, selected theme and ready content before capture', () => {
    const scenario = createVisualBaselineScenarios().find(item => item.route.key === 'search')!
    const readyEvidence = {
      pathname: '/tim-kiem',
      recipe: 'search',
      hydrated: true,
      theme: scenario.theme,
      mainHeight: 900,
      readySelectorVisible: true,
      contentIdentity: 'Gốm đỏ Mang Thít',
      blockingStates: [],
    }

    expect(evaluateVisualReadiness(scenario, readyEvidence)).toEqual([])
    expect(evaluateVisualReadiness(scenario, {
      ...readyEvidence,
      hydrated: false,
      theme: 'parchment',
      readySelectorVisible: false,
      blockingStates: ['loading', 'nuxt-error-overlay'],
    })).toEqual(expect.arrayContaining([
      'not-hydrated',
      'theme-mismatch',
      'ready-content-missing',
      'blocking-state:loading',
      'blocking-state:nuxt-error-overlay',
    ]))
  })

  it('resumes only artifacts from the current run whose manifest identity and PNG digest still match', () => {
    const scenario = createVisualBaselineScenarios()[0]!
    const png = Buffer.from('fresh screenshot bytes')
    const artifact = createVisualArtifactManifest({
      scenario,
      runId: 'run-current',
      capturedAt: '2026-08-10T08:00:00.000Z',
      screenshotBytes: png,
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })

    expect(validateVisualArtifactForResume(scenario, artifact, png, 'run-current')).toEqual([])
    expect(validateVisualArtifactForResume(scenario, artifact, Buffer.from('stale bytes'), 'run-current'))
      .toContain('screenshot-digest-mismatch')
    expect(validateVisualArtifactForResume(scenario, artifact, png, 'older-run'))
      .toContain('run-id-mismatch')
  })

  it('compares candidates against a separate authoritative baseline manifest', () => {
    const scenario = createVisualBaselineScenarios()[0]!
    const baseline = createVisualArtifactManifest({
      scenario,
      runId: 'approved-baseline',
      capturedAt: '2026-08-09T08:00:00.000Z',
      screenshotBytes: Buffer.from('approved pixels'),
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })
    const matching = createVisualArtifactManifest({
      scenario,
      runId: 'candidate',
      capturedAt: '2026-08-10T08:00:00.000Z',
      screenshotBytes: Buffer.from('approved pixels'),
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })
    const changed = { ...matching, screenshotSha256: '0'.repeat(64) }

    expect(compareVisualArtifacts(matching, baseline)).toEqual([])
    expect(compareVisualArtifacts(changed, baseline)).toContain('baseline-pixel-digest-mismatch')
  })
})
