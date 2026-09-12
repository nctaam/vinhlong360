import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Phase 2 Experience Elevation & Editorial Benchmark Tests', () => {
  const root = resolve(__dirname, '..')
  const localBriefingVue = readFileSync(resolve(root, 'components/home/HomeLocalBriefing.vue'), 'utf8')
  const featureDossierVue = readFileSync(resolve(root, 'components/home/HomeFeatureDossier.vue'), 'utf8')
  const indexVue = readFileSync(resolve(root, 'pages/index.vue'), 'utf8')
  const cardsCss = readFileSync(resolve(root, 'assets/css/cards.css'), 'utf8')
  const componentsCss = readFileSync(resolve(root, 'assets/css/components.css'), 'utf8')
  const homeNocturneCss = readFileSync(resolve(root, 'assets/css/home-nocturne.css'), 'utf8')
  const khamPhaVue = readFileSync(resolve(root, 'pages/kham-pha/[interest].vue'), 'utf8')
  const diaDiemVue = readFileSync(resolve(root, 'pages/dia-diem/index.vue'), 'utf8')

  describe('DEF-UX-06: Dynamic Mekong Tide Cycle Handbook', () => {
    it('integrates solarToLunar algorithm and dynamic tide phase computation in HomeLocalBriefing', () => {
      expect(localBriefingVue).toContain("import { solarToLunar } from '~/composables/useLunar'")
      expect(localBriefingVue).toMatch(/const\s+tidePhase\s*=\s*computed/)
      expect(localBriefingVue).toContain('Kỳ Nước rong')
      expect(localBriefingVue).toContain('Kỳ Nước kém')
      expect(localBriefingVue).toContain('Kỳ Nước chuyển')
    })

    it('renders dynamic tide badge with data-tide-phase attribute and authentic folk rule', () => {
      expect(localBriefingVue).toMatch(/:data-tide-phase="tidePhase\.phase"/)
      expect(localBriefingVue).toMatch(/:data-lunar-day="tidePhase\.lunarDay"/)
      expect(localBriefingVue).toContain('home-local-briefing__tide-badge')
      expect(localBriefingVue).toMatch(/Nước rong rằm (&|&amp;) mùng một, nước kém mùng bảy (&|&amp;) hăm ba/)
    })

    it('styles tide badge with semantic tokens for all 3 phases', () => {
      expect(localBriefingVue).toMatch(/\.home-local-briefing__tide-badge\[data-tide-phase="rong"\]/)
      expect(localBriefingVue).toMatch(/\.home-local-briefing__tide-badge\[data-tide-phase="kem"\]/)
      expect(localBriefingVue).toMatch(/\.home-local-briefing__tide-badge\[data-tide-phase="chuyen"\]/)
    })
  })

  describe('DEF-UX-03: Dynamic Field GPS Coordinates & Interactive Map Anchor', () => {
    it('equips HomeFeatureDossier with coordinates and mapTo props', () => {
      expect(featureDossierVue).toMatch(/coordinates\?:\s*string\s*\|\s*null/)
      expect(featureDossierVue).toMatch(/mapTo\?:\s*string\s*\|\s*null/)
      expect(featureDossierVue).toContain("coordinates: '10.254° N, 105.972° E'")
    })

    it('renders NuxtLink for coordinates when mapTo is supplied', () => {
      expect(featureDossierVue).toMatch(/<NuxtLink[^>]*v-if="mapTo"[^>]*:to="mapTo"[^>]*class="[^"]*home-feature-dossier__coords--link[^"]*"/)
      expect(featureDossierVue).toMatch(/v-else[^>]*class="[^"]*home-feature-dossier__coords[^"]*"/)
    })

    it('styles home-feature-dossier__coords--link with hover & focus-visible states', () => {
      expect(homeNocturneCss).toMatch(/\.home-feature-dossier__coords--link:hover/)
      expect(homeNocturneCss).toMatch(/\.home-feature-dossier__coords--link:focus-visible/)
    })

    it('computes and forwards hfCoordinates and hfMapTo from pages/index.vue', () => {
      expect(indexVue).toMatch(/const\s+hfCoordinates\s*=\s*computed/)
      expect(indexVue).toMatch(/const\s+hfMapTo\s*=\s*computed/)
      expect(indexVue).toMatch(/:coordinates="hfCoordinates"/)
      expect(indexVue).toMatch(/:map-to="hfMapTo"/)
    })
  })

  describe('DEF-ART-03: Asymmetric Editorial Grid (Anti Equal-Column Slop)', () => {
    it('defines grid--asymmetric with lead card span 2 and cinematic ratio in cards.css', () => {
      expect(cardsCss).toMatch(/\.grid--asymmetric\s*>\s*\.card:first-child\s*\{[^}]*grid-column:\s*span\s*2/s)
      expect(cardsCss).toMatch(/\.grid--asymmetric\s*>\s*\.card:first-child\s*\.cover-img\s*\{[^}]*aspect-ratio:\s*21\s*\/\s*9/s)
    })

    it('applies grid--asymmetric to discovery and destination catalog pages', () => {
      expect(khamPhaVue).toMatch(/class="[^"]*grid\s+grid--asymmetric\s+int-grid[^"]*"/)
      expect(diaDiemVue).toMatch(/class="[^"]*grid\s+grid--asymmetric\s+dd-grid[^"]*"/)
    })
  })

  describe('DEF-ART-05: Mechanical Tactile Haptic Physics', () => {
    it('calibrates card:active to natural mechanical depression (translateY 1px scale 0.98)', () => {
      expect(cardsCss).toMatch(/\.card:active\s*\{[^}]*transform:\s*translateY\(1px\)\s*scale\(0\.98\)/)
      expect(cardsCss).not.toMatch(/\.card:active\s*\{[^}]*transform:\s*translateY\(-1px\)/)
    })
  })

  describe('DEF-A11Y-02: WCAG 2.2 AAA Touch Target Expansion (≥44px)', () => {
    it('expands touch targets for search clear buttons via pseudo-elements', () => {
      expect(componentsCss).toMatch(/\.ac-clear::before,\s*\.ac-remove-recent::before\s*\{[^}]*min-width:\s*44px;\s*min-height:\s*44px;/s)
    })

    it('enforces 44px touch targets on touch devices without hover', () => {
      expect(componentsCss).toMatch(/@media\s*\(hover:\s*none\)\s*\{[\s\S]*?\.ac-clear\s*\{[^}]*min-width:\s*44px;\s*min-height:\s*44px;/)
      expect(componentsCss).toMatch(/@media\s*\(hover:\s*none\)\s*\{[\s\S]*?\.ac-remove-recent\s*\{[^}]*min-width:\s*44px;\s*min-height:\s*44px;/)
    })
  })
})
