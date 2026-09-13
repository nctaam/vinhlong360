import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('R3: Cartography Field Ergonomics & Interactive Terroir Map', () => {
  const banDoVue = readFileSync(resolve(__dirname, '../pages/ban-do.vue'), 'utf8')
  const tuyenDuongVue = readFileSync(resolve(__dirname, '../pages/tuyen-duong.vue'), 'utf8')
  const baseCss = readFileSync(resolve(__dirname, '../assets/css/base.css'), 'utf8')
  const mapListSurfaceVue = readFileSync(resolve(__dirname, '../components/public/MapListSurface.vue'), 'utf8')

  describe('Tier 1 & Tier 4: Full-Bleed Cartography & Spatial Waypoints', () => {
    it('supports full-bleed map canvas mode with dynamic state toggle', () => {
      expect(banDoVue).toContain('isFullBleed')
      expect(banDoVue).toContain(':class="{ \'is-fullbleed\': isFullBleed }"')
      expect(banDoVue).toContain('map-fullbleed-toggle')
      expect(banDoVue).toContain(':aria-pressed="isFullBleed"')
      expect(banDoVue).toMatch(/Tràn viền|Bản đồ tràn viền/)
    })

    it('provides an interactive spatial route preview with waypoint map on tuyen-duong', () => {
      expect(tuyenDuongVue).toContain('openRoutePreview')
      expect(tuyenDuongVue).toContain('route-preview-dialog')
      expect(tuyenDuongVue).toContain('route-preview-map-canvas')
      expect(tuyenDuongVue).toContain('route-waypoint-pin')
      expect(tuyenDuongVue).toContain('route-preview-sidebar')
    })
  })

  describe('Tier 1 & Tier 2: 1-Hand Thumb Zone Ergonomics (>= 44px Controls)', () => {
    it('anchors essential field controls in floating thumb dock (.map-floating-thumb-dock)', () => {
      expect(banDoVue).toContain('map-floating-thumb-dock')
      expect(banDoVue).toContain('map-quick-presets')
      expect(banDoVue).toContain('map-zoom-btn')
      expect(banDoVue).toContain('map-terroir-gps-btn')
      expect(banDoVue).toContain('map-contrast-toggle')
    })

    it('enforces minimum 44px touch target on all dock buttons for one-handed thumb interaction', () => {
      expect(banDoVue).toMatch(/\.map-quick-preset-btn\s*\{[\s\S]*?min-height:\s*44px/)
      expect(banDoVue).toMatch(/\.map-contrast-toggle\s*\{[\s\S]*?min-height:\s*44px/)
      expect(banDoVue).toMatch(/\.map-fullbleed-toggle\s*\{[\s\S]*?min-height:\s*44px/)
    })
  })

  describe('Tier 1 & Tier 2: Map Marker Touch Targets (Hitbox Expansion)', () => {
    it('enforces >= 44x44px touch target on .map-locator-marker via ::before pseudo-element', () => {
      expect(baseCss).toMatch(/\.map-locator-marker::before\s*\{[\s\S]*?min-width:\s*44px/)
      expect(baseCss).toMatch(/\.map-locator-marker::before\s*\{[\s\S]*?min-height:\s*44px/)
      expect(baseCss).toMatch(/\.map-locator-marker::before\s*\{[\s\S]*?inset:\s*-6px/)
    })
  })

  describe('Tier 1 & Tier 4: Outdoor High-Contrast Mode (Sunlight Resistance)', () => {
    it('supports outdoor contrast mode with accessible aria-pressed toggle', () => {
      expect(banDoVue).toContain(':data-outdoor-contrast="outdoorContrast ? \'high\' : \'normal\'"')
      expect(banDoVue).toContain(':aria-pressed="outdoorContrast"')
      expect(banDoVue).toContain(':outdoor-contrast="outdoorContrast"')
    })

    it('propagates outdoor contrast state into MapListSurface component', () => {
      expect(mapListSurfaceVue).toContain('outdoorContrast')
      expect(mapListSurfaceVue).toContain(':data-outdoor-contrast="outdoorContrast ? \'high\' : undefined"')
    })

    it('applies hardware-accelerated contrast and saturation filters to map canvas under sunlight', () => {
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.maplibregl-canvas\s*\{[\s\S]*?filter:\s*contrast\(/)
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.maplibregl-canvas\s*\{[\s\S]*?saturate\(/)
    })

    it('enhances marker visibility and popup contrast in outdoor high-contrast mode', () => {
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.map-locator-marker\s*\{[\s\S]*?border-width:\s*4px/)
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.maplibregl-popup-content\s*\{[\s\S]*?border:\s*2px solid/)
    })
  })

  describe('Tier 1 & Tier 3: Route Header Contrast AAA Remediation', () => {
    it('ensures Bến Tre route header achieves high contrast on amber product gradient', () => {
      expect(tuyenDuongVue).toContain('area-ben-tre')
      // Contrast rule ensures text is legible against light gold/orange background
      const benTreHeaderRegex = /\.route-header\.area-ben-tre\s*\{[\s\S]*?(?:color:\s*var\(--(?:mekong-ink|ink)\)|color:\s*#181e28)/
      expect(tuyenDuongVue).toMatch(benTreHeaderRegex)
    })
  })
})
