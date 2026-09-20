import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mount } from '@vue/test-utils'
import MekongWaterBadge from '../components/MekongWaterBadge.vue'
import { solarToLunar } from '../composables/useLunar'

describe('Adversarial Verification: Editorial Design, Ergonomics & Terroir Architecture', () => {
  const catalogCss = readFileSync(resolve(__dirname, '../assets/css/catalog.css'), 'utf8')
  const cardsCss = readFileSync(resolve(__dirname, '../assets/css/cards.css'), 'utf8')
  const banDoVue = readFileSync(resolve(__dirname, '../pages/ban-do.vue'), 'utf8')
  const tuyenDuongVue = readFileSync(resolve(__dirname, '../pages/tuyen-duong.vue'), 'utf8')
  const duLichVue = readFileSync(resolve(__dirname, '../pages/du-lich.vue'), 'utf8')
  const amThucVue = readFileSync(resolve(__dirname, '../pages/am-thuc.vue'), 'utf8')
  const luuTruVue = readFileSync(resolve(__dirname, '../pages/luu-tru.vue'), 'utf8')
  const sanPhamVue = readFileSync(resolve(__dirname, '../pages/san-pham.vue'), 'utf8')
  const diaDiemIndexVue = readFileSync(resolve(__dirname, '../pages/dia-diem/index.vue'), 'utf8')

  // ──────────────────────────────────────────────────────────────────────────
  // TASK 1: Responsive Layout Breakpoint Stress-Testing
  // ──────────────────────────────────────────────────────────────────────────
  describe('Task 1: Responsive Layout Breakpoint Stress-Testing', () => {
    it('verifies Lead Hero Card span-2 is strictly guarded by @container (min-width: 48rem)', () => {
      const cardsMatch = cardsCss.match(/@container\s*\((?:min-width:\s*48rem)\)\s*\{[\s\S]*?\.grid--asymmetric\s*>\s*\.card:first-child[\s\S]*?grid-column:\s*span\s*2[\s\S]*?\}/)
      expect(cardsMatch, 'cards.css must wrap grid--asymmetric span 2 in min-width: 48rem container query').not.toBeNull()

      const catalogMatch = catalogCss.match(/@container\s*(?:catalog-results\s*)?\((?:min-width:\s*48rem)\)\s*\{[\s\S]*?\.catalog-result-surface:not\(\.list-view\)\s*>\s*\.catalog-result-item:first-child[\s\S]*?grid-column:\s*span\s*2[\s\S]*?\}/)
      expect(catalogMatch, 'catalog.css must wrap catalog-result-surface span 2 in min-width: 48rem container query').not.toBeNull()
    })

    it('verifies mobile viewports (< 48rem) collapse to single column without overflow or span-2 blowouts', () => {
      expect(cardsCss).toMatch(/@container\s*\(max-width:\s*480px\)\s*\{\s*\.grid\s*\{\s*grid-template-columns:\s*1fr;\s*\}\s*\}/)
      expect(catalogCss).toMatch(/@container\s*catalog-results\s*\(max-width:\s*40rem\)\s*\{[\s\S]*?grid-template-columns:\s*1fr;[\s\S]*?grid-column:\s*1;\s*\}/)

      const strippedCards = cardsCss.replace(/@container\s*\([^{]+\)\s*\{[\s\S]*?\}/g, '')
      expect(strippedCards).not.toMatch(/grid-column:\s*span\s*2/)
    })

    it('verifies all 5 core catalog pages employ .grid--asymmetric for asymmetric magazine flow', () => {
      const catalogPages = [
        { name: 'du-lich.vue', content: duLichVue },
        { name: 'am-thuc.vue', content: amThucVue },
        { name: 'luu-tru.vue', content: luuTruVue },
        { name: 'san-pham.vue', content: sanPhamVue },
        { name: 'dia-diem/index.vue', content: diaDiemIndexVue },
      ]

      for (const page of catalogPages) {
        expect(page.content, `${page.name} must declare grid--asymmetric`).toContain('grid--asymmetric')
      }
    })

    it('verifies tablet viewports (48rem - 64rem) format grid into tidy 2-column layout', () => {
      expect(cardsCss).toMatch(/@media\s*\(min-width:\s*769px\)\s*and\s*\(max-width:\s*1024px\)\s*\{[\s\S]*?\.grid\s*\{\s*grid-template-columns:\s*repeat\(2,\s*1fr\);[\s\S]*?\}/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // TASK 2: Cartography Full-Bleed & Floating Thumb Dock Ergonomics
  // ──────────────────────────────────────────────────────────────────────────
  describe('Task 2: Cartography Full-Bleed & Floating Thumb Dock Ergonomics', () => {
    it('verifies floating thumb dock position and safe-area inset anchoring', () => {
      expect(banDoVue).toMatch(/@media\s*\(max-width:\s*768px\)\s*\{[\s\S]*?\.map-floating-thumb-dock\s*\{[\s\S]*?position:\s*fixed;/)
      expect(banDoVue).toMatch(/bottom:\s*calc\(env\(safe-area-inset-bottom\)\s*\+\s*72px\);/)
      expect(banDoVue).toMatch(/right:\s*16px;/)
      expect(banDoVue).toMatch(/z-index:\s*var\(--z-overlay-raised\);/)
    })

    it('empirically identifies mobile sheet z-index collision (Challenge Point)', () => {
      expect(catalogCss).toMatch(/\.map-list-surface\[data-panel='map'\]\s+\.map-list-surface__map-pane\s*\{[\s\S]*?z-index:\s*var\(--z-overlay\);/)

      expect(banDoVue).toMatch(/\.map-floating-thumb-dock\s*\{[\s\S]*?z-index:\s*var\(--z-overlay-raised\);/)
    })

    it('verifies full-bleed toggle button state synchronization in ban-do.vue', () => {
      expect(banDoVue).toContain('isFullBleed = !isFullBleed')
      expect(banDoVue).toContain(':aria-pressed="isFullBleed"')
      expect(banDoVue).toContain(':class="{ \'is-active\': isFullBleed }"')
    })

    it('verifies ban-do.vue contains ergonomic bottom floating dock on mobile', () => {
      const banDo = readFileSync(resolve(__dirname, '../pages/ban-do.vue'), 'utf8')
      expect(banDo).toContain('map-floating-dock')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // TASK 3: Tidal Cycle & Water Flow Edge Cases (MekongWaterBadge)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Task 3: Tidal Cycle & Water Flow Edge Cases', () => {
    it('correctly infers Con nước rong on lunar month boundaries (Mùng 1 and Rằm)', () => {
      const wrapper1 = mount(MekongWaterBadge, {
        props: { lunarDay: 1, lunarMonth: 1 },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapper1.attributes('data-tide-state')).toBe('rong')
      expect(wrapper1.text()).toContain('Con nước rong')
      expect(wrapper1.text()).toContain('Mùng 1 th.1 ÂL')

      const wrapper15 = mount(MekongWaterBadge, {
        props: { lunarDay: 15, lunarMonth: 8 },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapper15.attributes('data-tide-state')).toBe('rong')
      expect(wrapper15.text()).toContain('Con nước rong')
      expect(wrapper15.text()).toContain('Rằm (15) th.8 ÂL')
    })

    it('correctly infers Con nước kém during neap tide quarters (7-10 and 22-25)', () => {
      for (const day of [7, 8, 9, 10, 22, 23, 24, 25]) {
        const wrapper = mount(MekongWaterBadge, {
          props: { lunarDay: day, lunarMonth: 3 },
          global: { stubs: { IconLine: true } },
        })
        expect(wrapper.attributes('data-tide-state'), `Day ${day} must be Con nước kém`).toBe('kem')
        expect(wrapper.text()).toContain('Con nước kém')
      }
    })

    it('handles Solar New Year vs Lunar New Year transition (Jan 1, 2026 vs Feb 17, 2026)', () => {
      const l1 = solarToLunar(1, 1, 2026)
      expect(l1.year).toBe(2025)
      expect(l1.month).toBe(11)
      expect(l1.day).toBe(13)

      const wrapperJan1 = mount(MekongWaterBadge, {
        props: { date: '2026-01-01' },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapperJan1.attributes('data-tide-state')).toBe('chuyen')
      expect(wrapperJan1.text()).toContain('Con nước thường')

      const lTet = solarToLunar(17, 2, 2026)
      expect(lTet.year).toBe(2026)
      expect(lTet.month).toBe(1)
      expect(lTet.day).toBe(1)

      const wrapperTet = mount(MekongWaterBadge, {
        props: { date: '2026-02-17' },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapperTet.attributes('data-tide-state')).toBe('rong')
      expect(wrapperTet.text()).toContain('Con nước rong')
      expect(wrapperTet.text()).toContain('Mùng 1 th.1 ÂL')
    })

    it('handles Leap Month edge cases (Year 2025 has leap 6th month - tháng 6 nhuận)', () => {
      const lLeap = solarToLunar(25, 7, 2025)
      expect(lLeap.leap).toBe(true)
      expect(lLeap.month).toBe(6)

      const wrapperLeap = mount(MekongWaterBadge, {
        props: { date: '2025-07-25' },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapperLeap.exists()).toBe(true)
      expect(wrapperLeap.attributes('data-tide-state')).toBe('rong')
    })

    it('gracefully handles extreme/invalid inputs without throwing exceptions', () => {
      const wrapperInvalidDate = mount(MekongWaterBadge, {
        props: { date: 'not-a-real-date' },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapperInvalidDate.attributes('data-tide-state')).toBe('rong')

      const wrapperOOB = mount(MekongWaterBadge, {
        props: { lunarDay: 99 },
        global: { stubs: { IconLine: true } },
      })
      expect(wrapperOOB.attributes('data-tide-state')).toBe('chuyen')

      const wrapperNull = mount(MekongWaterBadge, {
        props: {},
        global: { stubs: { IconLine: true } },
      })
      expect(wrapperNull.attributes('data-tide-state')).toBe('rong')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // TASK 4: Route Waypoint Navigation in tuyen-duong.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Task 4: Route Waypoint Navigation in tuyen-duong.vue', () => {
    it('verifies Keyboard Escape handling on route preview modal', () => {
      expect(tuyenDuongVue).toContain('function onModalKeydown(event: KeyboardEvent)')
      expect(tuyenDuongVue).toMatch(/if\s*\(event\.key\s*===\s*['"]Escape['"]\s*&&\s*previewRoute\.value\)\s*\{\s*closeRoutePreview\(\)\s*\}/)
      expect(tuyenDuongVue).toContain("window.addEventListener('keydown', onModalKeydown)")
      expect(tuyenDuongVue).toContain("window.removeEventListener('keydown', onModalKeydown)")
    })

    it('verifies stop selection bounds prevent index underflow and overflow', () => {
      expect(tuyenDuongVue).toMatch(/:disabled="selectedStopIndex\s*===\s*0"/)
      expect(tuyenDuongVue).toMatch(/@click="selectedStopIndex\s*=\s*Math\.max\(0,\s*selectedStopIndex\s*-\s*1\)"/)

      expect(tuyenDuongVue).toMatch(/:disabled="selectedStopIndex\s*>=\s*previewRoute\.stops\.length\s*-\s*1"/)
      expect(tuyenDuongVue).toMatch(/@click="selectedStopIndex\s*=\s*Math\.min\(previewRoute\.stops\.length\s*-\s*1,\s*selectedStopIndex\s*\+\s*1\)"/)
    })

    it('verifies strict null safety across route waypoints and stop SVG generation', () => {
      expect(tuyenDuongVue).toMatch(/if\s*\(!previewRoute\.value\s*\|\|\s*!previewRoute\.value\.stops\)\s*return\s*null/)
      expect(tuyenDuongVue).toMatch(/if\s*\(!stops\s*\|\|\s*!stops\.length\)\s*return\s*['"]['"]/)
      expect(tuyenDuongVue).toMatch(/if\s*\(total\s*<=\s*1\)\s*return\s*\[300,\s*160\]/)
    })
  })
})
