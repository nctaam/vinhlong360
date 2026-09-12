import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Interactive Heritage Map Ergonomics & Terroir Utility', () => {
  const mapVue = readFileSync(resolve(__dirname, '../pages/ban-do.vue'), 'utf8')

  it('includes outdoor contrast toggle button with accessible aria-pressed state', () => {
    expect(mapVue).toContain('map-contrast-toggle')
    expect(mapVue).toContain(':aria-pressed="outdoorContrast"')
    expect(mapVue).toContain('Tương phản ngoài trời')
  })

  it('contains quick water presets with vector icons and terracotta active styling', () => {
    expect(mapVue).toContain('map-quick-presets')
    expect(mapVue).toContain('activeWaterPreset')
    expect(mapVue).toContain('.map-quick-preset-btn')
    expect(mapVue).toContain('.map-contrast-toggle')
  })

  it('enforces min 44px touch target on map controls for mobile ergonomics', () => {
    expect(mapVue).toMatch(/\.map-quick-preset-btn\s*\{[\s\S]*?min-height:\s*44px/)
    expect(mapVue).toMatch(/\.map-contrast-toggle\s*\{[\s\S]*?min-height:\s*44px/)
  })
})
