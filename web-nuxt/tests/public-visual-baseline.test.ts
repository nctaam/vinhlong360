import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import * as visualSmoke from '../../scripts/smoke_e2e_chrome.mjs'
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

const ciWorkflow = readFileSync(resolve(process.cwd(), '../.github/workflows/ci.yml'), 'utf8')

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
    const sourceRevision = 'a'.repeat(40)
    const artifact = createVisualArtifactManifest({
      scenario,
      runId: 'run-current',
      sourceRevision,
      capturedAt: '2026-08-10T08:00:00.000Z',
      screenshotBytes: png,
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })

    expect(validateVisualArtifactForResume(scenario, artifact, png, 'run-current', sourceRevision)).toEqual([])
    expect(validateVisualArtifactForResume(scenario, artifact, Buffer.from('stale bytes'), 'run-current', sourceRevision))
      .toContain('screenshot-digest-mismatch')
    expect(validateVisualArtifactForResume(scenario, artifact, png, 'older-run', sourceRevision))
      .toContain('run-id-mismatch')
  })

  it('binds artifact resume to the source revision that produced the screenshot', () => {
    const scenario = createVisualBaselineScenarios()[0]!
    const png = Buffer.from('fresh screenshot bytes')
    const sourceRevision = 'a'.repeat(40)
    const artifact = createVisualArtifactManifest({
      scenario,
      runId: 'run-current',
      sourceRevision,
      capturedAt: '2026-08-10T08:00:00.000Z',
      screenshotBytes: png,
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })

    expect(artifact.sourceRevision).toBe(sourceRevision)
    expect(validateVisualArtifactForResume(scenario, artifact, png, 'run-current', sourceRevision)).toEqual([])
    expect(validateVisualArtifactForResume(scenario, artifact, png, 'run-current', 'b'.repeat(40)))
      .toContain('source-revision-mismatch')
  })

  it('rejects a top-level visual manifest from another source revision during resume', () => {
    type RunManifestFactory = (input: {
      runId: string
      sourceRevision: string
      comparisonMode: string
      baselineDirectory: string | null
      artifacts: unknown[]
    }) => { sourceRevision: string }
    type RunManifestValidator = (manifest: unknown, runId: string, sourceRevision: string) => string[]
    const createRunManifest = (visualSmoke as Record<string, unknown>).createVisualRunManifest as RunManifestFactory | undefined
    const validateRunManifest = (visualSmoke as Record<string, unknown>).validateVisualRunManifestForResume as RunManifestValidator | undefined

    expect(createRunManifest).toBeTypeOf('function')
    expect(validateRunManifest).toBeTypeOf('function')
    if (!createRunManifest || !validateRunManifest) return

    const manifest = createRunManifest({
      runId: 'run-current',
      sourceRevision: 'a'.repeat(40),
      comparisonMode: 'capture-for-review',
      baselineDirectory: null,
      artifacts: [],
    })

    expect(manifest.sourceRevision).toBe('a'.repeat(40))
    expect(validateRunManifest(manifest, 'run-current', 'b'.repeat(40))).toContain('source-revision-mismatch')
  })

  it('combines top-level and artifact identity before deciding whether to resume a screenshot', () => {
    type ResumeEntryValidator = (input: {
      scenario: unknown
      manifest: unknown
      artifact: unknown
      screenshotBytes: Buffer
      runId: string
      sourceRevision: string
    }) => string[]
    const validateResumeEntry = (visualSmoke as Record<string, unknown>).validateVisualResumeEntry as ResumeEntryValidator | undefined

    expect(validateResumeEntry).toBeTypeOf('function')
    if (!validateResumeEntry) return

    const scenario = createVisualBaselineScenarios()[0]!
    const screenshotBytes = Buffer.from('fresh screenshot bytes')
    const sourceRevision = 'a'.repeat(40)
    const artifact = createVisualArtifactManifest({
      scenario,
      runId: 'run-current',
      sourceRevision,
      capturedAt: '2026-08-10T08:00:00.000Z',
      screenshotBytes,
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })
    const manifest = {
      schemaRevision: visualSmoke.PUBLIC_VISUAL_SCHEMA_REVISION,
      runId: 'run-current',
      sourceRevision: 'b'.repeat(40),
      artifacts: [artifact],
    }

    expect(validateResumeEntry({
      scenario,
      manifest,
      artifact,
      screenshotBytes,
      runId: 'run-current',
      sourceRevision,
    })).toContain('source-revision-mismatch')
  })

  it('has CI capture and upload fresh source-bound visual evidence', () => {
    expect(ciWorkflow).toContain('Capture fresh public visual evidence')
    expect(ciWorkflow).toContain('SMOKE_VISUAL_DIR: ${{ github.workspace }}/artifacts/public-visual')
    expect(ciWorkflow).toContain('SMOKE_VISUAL_RUN_ID: ci-${{ github.run_id }}-${{ github.run_attempt }}')
    expect(ciWorkflow).toContain('SMOKE_SOURCE_REVISION: ${{ github.sha }}')
    expect(ciWorkflow).toContain('SMOKE_FORCE_MANAGED_APP: "1"')
    expect(ciWorkflow).toContain('SMOKE_MANAGED_APP_MODE: preview')
    expect(ciWorkflow).toContain('Upload public visual evidence')
    expect(ciWorkflow).toContain('artifacts/public-visual')
  })

  it('compares candidates against a separate authoritative baseline manifest', () => {
    const scenario = createVisualBaselineScenarios()[0]!
    const baseline = createVisualArtifactManifest({
      scenario,
      runId: 'approved-baseline',
      sourceRevision: 'a'.repeat(40),
      capturedAt: '2026-08-09T08:00:00.000Z',
      screenshotBytes: Buffer.from('approved pixels'),
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })
    const matching = createVisualArtifactManifest({
      scenario,
      runId: 'candidate',
      sourceRevision: 'b'.repeat(40),
      capturedAt: '2026-08-10T08:00:00.000Z',
      screenshotBytes: Buffer.from('approved pixels'),
      readiness: { contentIdentity: 'Gốm đỏ Mang Thít' },
    })
    const changed = { ...matching, screenshotSha256: '0'.repeat(64) }

    expect(compareVisualArtifacts(matching, baseline)).toEqual([])
    expect(compareVisualArtifacts(changed, baseline)).toContain('baseline-pixel-digest-mismatch')
  })
})
