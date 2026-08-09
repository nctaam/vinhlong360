import { describe, expect, it } from 'vitest'

import { evaluatePublicAccessibilitySnapshot } from '../scripts/check-public-accessibility.mjs'

const passingSnapshot = {
  forcedColorsActive: true,
  forcedColorAdjust: 'auto',
  forcedControlBorderVisible: true,
  viewportWidth: 720,
  screenWidth: 1440,
  devicePixelRatio: 2,
  horizontalOverflow: 0,
  mainVisible: true,
  controlsBelow44: 0,
  mainVisibleMs: 1200,
}

describe('public accessibility browser gate', () => {
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
})
