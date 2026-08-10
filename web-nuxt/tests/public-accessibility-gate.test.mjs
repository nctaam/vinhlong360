import { EventEmitter } from 'node:events'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import * as publicAccessibilityGate from '../scripts/check-public-accessibility.mjs'

const { evaluatePublicAccessibilitySnapshot, launchChrome } = publicAccessibilityGate

function workflowStep(workflow, name) {
  workflow = workflow.replaceAll('\r\n', '\n')
  const marker = `      - name: ${name}\n`
  const start = workflow.indexOf(marker)
  expect(start).toBeGreaterThanOrEqual(0)
  const next = workflow.indexOf('\n      - name:', start + marker.length)
  return workflow.slice(start, next === -1 ? workflow.length : next)
}

const passingSnapshot = {
  forcedColorsActive: true,
  forcedColorAdjust: 'auto',
  forcedControlBorderVisible: true,
  forcedRepresentativeControls: { total: 1, bounded: 1 },
  viewportWidth: 720,
  screenWidth: 1440,
  devicePixelRatio: 2,
  nativeBrowserZoomApplied: true,
  nativeBrowserZoomFactor: 2,
  nativeBrowserZoomLayoutFactor: 2,
  nativeBrowserZoomVisualScale: 1,
  textScale: 2,
  textScaleApplied: true,
  horizontalOverflow: 0,
  mainVisible: true,
  mainUsable: true,
  controlsBelow44: 0,
  mainVisibleMs: 1200,
  contrastAuditAvailable: true,
  contrastAuditedCount: 5,
  contrastViolations: 0,
  normalContrastAuditAvailable: true,
  normalContrastAuditedCount: 5,
  normalContrastViolations: 0,
  lcpMs: 1800,
  cls: 0.02,
  inpAvailable: true,
  inpMs: 100,
  inpEvidence: 'rendered-interaction',
  apiMaxMs: 500,
  apiObservedCount: 1,
  apiResponseSuccessful: true,
  apiFixtureFulfilled: true,
  bundleAuditAvailable: true,
  bundleViolations: 0,
}

describe('public accessibility browser gate', () => {
  it('is wired through the frontend package and blocking CI verification path', async () => {
    const packageJson = JSON.parse(await readFile(resolve(import.meta.dirname, '../package.json'), 'utf8'))
    const ci = await readFile(resolve(import.meta.dirname, '../../.github/workflows/ci.yml'), 'utf8')

    expect(packageJson.scripts['check:public-accessibility']).toBe('node scripts/check-public-accessibility.mjs')
    expect(ci).toContain('npm run check:public-accessibility')
  })

  it('runs visual and accessibility evidence independently after failures', async () => {
    const ci = await readFile(resolve(import.meta.dirname, '../../.github/workflows/ci.yml'), 'utf8')
    for (const name of [
      'Capture fresh public visual evidence',
      'Start preview server for a11y scan',
      'Accessibility scan (axe-core, 14 trang)',
      'Accessibility gate (R30.6)',
      'Stop preview server',
      'Upload axe report',
    ]) {
      expect(workflowStep(ci, name)).toContain('if: always()')
    }
    expect(workflowStep(ci, 'Start preview server for a11y scan')).toContain('a11y-unavailable')
    expect(workflowStep(ci, 'Accessibility scan (axe-core, 14 trang)')).toContain('A11Y_AVAILABLE')
  })

  it('accepts forced-colors and a native 200% browser-zoom snapshot', () => {
    expect(evaluatePublicAccessibilitySnapshot(passingSnapshot)).toEqual([])
  })

  it('rejects page-scale magnification presented as native browser zoom', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      nativeBrowserZoomApplied: false,
      nativeBrowserZoomFactor: 1,
      nativeBrowserZoomLayoutFactor: 1,
      nativeBrowserZoomVisualScale: 2,
    })).toContain('native-browser-zoom-not-200-percent')
  })

  it('blocks missing forced-colors evidence, overflow, undersized controls, and slow main content', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      forcedColorsActive: false,
      forcedControlBorderVisible: false,
      viewportWidth: 900,
      horizontalOverflow: 12,
      controlsBelow44: 1,
      mainVisibleMs: 6000,
    })).toEqual(expect.arrayContaining([
      'forced-colors-inactive',
      'forced-control-border-missing',
      'native-browser-zoom-not-200-percent',
      'horizontal-overflow',
      'undersized-controls',
      'main-visible-budget-exceeded',
    ]))
  })

  it('requires representative action controls and the application textScale=2 path', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      forcedRepresentativeControls: { total: 2, bounded: 1 },
      textScale: 1,
      textScaleApplied: false,
    })).toEqual(expect.arrayContaining([
      'forced-control-border-missing',
      'text-scale-not-200-percent',
    ]))
  })

  it('rejects a main element that has a box but is hidden or transparent', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      mainVisible: true,
      mainUsable: false,
    })).toContain('main-content-hidden')
  })

  it('enforces bounded contrast and standard performance evidence', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      contrastAuditAvailable: false,
      contrastViolations: 1,
      normalContrastAuditAvailable: false,
      normalContrastViolations: 1,
      lcpMs: 3000,
      cls: 0.2,
      inpAvailable: false,
      inpMs: 300,
      apiMaxMs: 1800,
      bundleAuditAvailable: false,
      bundleViolations: 1,
    })).toEqual(expect.arrayContaining([
      'contrast-audit-unavailable',
      'contrast-violations',
      'lcp-budget-exceeded',
      'cls-budget-exceeded',
      'inp-audit-unavailable',
      'inp-budget-exceeded',
      'api-budget-exceeded',
      'bundle-audit-unavailable',
      'bundle-budget-exceeded',
    ]))
  })

  it('requires contrast evidence to cover at least one visible action control', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      contrastAuditedCount: 0,
    })).toContain('contrast-audit-empty')
  })

  it('requires both normal and forced-colors contrast audits', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      normalContrastAuditAvailable: false,
    })).toContain('contrast-audit-unavailable')
  })

  it('rejects synthetic INP evidence and unsupported rendered interactions', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      inpEvidence: 'synthetic-probe',
    })).toContain('inp-evidence-not-rendered')
  })

  it('fails closed when no API request timing was observed', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      apiObservedCount: 0,
      apiMaxMs: 0,
    })).toContain('api-audit-empty')
  })

  it('fails closed when an observed API request has no finite duration', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      apiObservedCount: 1,
      apiMaxMs: Number.NaN,
    })).toContain('api-duration-unavailable')
  })

  it('fails closed when the API fixture response is unsuccessful', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      apiResponseSuccessful: false,
    })).toContain('api-response-unsuccessful')
  })

  it('fails closed when the self-contained API fixture was not fulfilled', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      apiFixtureFulfilled: false,
    })).toContain('api-fixture-unavailable')
  })

  it('uses only the exact fixture URL when measuring API timing', () => {
    const fixtureUrl = 'http://127.0.0.1:4173/api/places?limit=1'
    expect(publicAccessibilityGate.measureApiFixtureResources([
      { name: 'http://127.0.0.1:4173/api/other', duration: 25 },
    ], fixtureUrl)).toEqual({ apiObservedCount: 0, apiMaxMs: null })
  })

  it('fulfills the exact fixture request with a successful same-origin response', async () => {
    const calls = []
    const cdp = { send: async (method, params) => { calls.push({ method, params }) } }
    const fixtureUrl = 'http://127.0.0.1:4173/api/places?limit=1'

    await expect(publicAccessibilityGate.fulfillApiFixtureRequest(cdp, {
      requestId: 'fixture-request',
      request: { url: fixtureUrl, method: 'GET' },
    }, fixtureUrl)).resolves.toBe(true)
    expect(calls).toEqual([expect.objectContaining({
      method: 'Fetch.fulfillRequest',
      params: expect.objectContaining({ requestId: 'fixture-request', responseCode: 200 }),
    })])
  })

  it('fails closed when the INP observer capability is unsupported', () => {
    expect(evaluatePublicAccessibilitySnapshot({
      ...passingSnapshot,
      inpAvailable: false,
      inpEvidence: 'unsupported',
    })).toEqual(expect.arrayContaining([
      'inp-audit-unavailable',
      'inp-evidence-not-rendered',
    ]))
  })

  it('kills Chrome when CDP startup fails after the child is spawned', async () => {
    const stderr = new EventEmitter()
    const child = Object.assign(new EventEmitter(), {
      stderr,
      exitCode: null,
      kill() {
        this.exitCode = 0
        this.emit('exit', 0)
      },
    })
    const spawnProcess = () => {
      queueMicrotask(() => stderr.emit('data', 'DevTools listening on ws://127.0.0.1:9222/devtools/page/1'))
      return child
    }
    const fetchImpl = async () => { throw new Error('target listing failed') }

    await expect(launchChrome('fake-chrome', 'fake-profile', { spawnProcess, fetchImpl }))
      .rejects.toThrow('target listing failed')
    expect(child.exitCode).toBe(0)
  })
})
