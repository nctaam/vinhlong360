import { describe, expect, it } from 'vitest'
import {
  PUBLIC_ROUTE_SPECS,
  PUBLIC_VISUAL_THEMES,
  PUBLIC_VISUAL_VIEWPORTS,
  createVisualBaselineScenarios,
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
})
