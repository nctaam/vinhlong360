import { EventEmitter } from 'node:events'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { evaluatePublicAccessibilitySnapshot, launchChrome } from '../scripts/check-public-accessibility.mjs'

const passingSnapshot = {
  forcedColorsActive: true,
  forcedColorAdjust: 'auto',
  forcedControlBorderVisible: true,
  forcedRepresentativeControls: { total: 1, bounded: 1 },
  viewportWidth: 720,
  screenWidth: 1440,
  devicePixelRatio: 2,
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
  lcpMs: 1800,
  cls: 0.02,
  inpAvailable: true,
  inpMs: 100,
  apiMaxMs: 500,
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

  it('accepts forced-colors and a bounded 200%-layout equivalent snapshot', () => {
    expect(evaluatePublicAccessibilitySnapshot(passingSnapshot)).toEqual([])
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
      'zoom-layout-not-2x',
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
