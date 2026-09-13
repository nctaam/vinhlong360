import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

describe('R1: Catalog Magazine Layout & Asymmetric Editorial Architecture', () => {
  const catalogCss = readFileSync(resolve(__dirname, '../assets/css/catalog.css'), 'utf8')
  const cardsCss = readFileSync(resolve(__dirname, '../assets/css/cards.css'), 'utf8')
  const duLichVue = readFileSync(resolve(__dirname, '../pages/du-lich.vue'), 'utf8')
  const luuTruVue = readFileSync(resolve(__dirname, '../pages/luu-tru.vue'), 'utf8')
  const sanPhamVue = readFileSync(resolve(__dirname, '../pages/san-pham.vue'), 'utf8')
  const diaDiemIndexVue = readFileSync(resolve(__dirname, '../pages/dia-diem/index.vue'), 'utf8')
  const filterChipsVue = readFileSync(resolve(__dirname, '../components/FilterChips.vue'), 'utf8')
  const amThucPath = resolve(__dirname, '../pages/am-thuc.vue')

  describe('Tier 1: Feature Coverage — Lead Hero Card span-2 & Asymmetry', () => {
    it('enforces Lead Hero span-2 with 21:9 aspect ratio in catalog stylesheet container queries', () => {
      expect(catalogCss).toContain('catalog-result-surface')
      expect(catalogCss).toMatch(
        /\.catalog-result-surface:not\(\.list-view\)\s*>\s*\.catalog-result-item:first-child[\s\S]*?grid-column:\s*span\s*2/
      )
      expect(catalogCss).toMatch(
        /\.catalog-result-surface:not\(\.list-view\)\s*>\s*\.catalog-result-item:first-child[\s\S]*?aspect-ratio:\s*21\s*\/\s*9/
      )
    })

    it('enforces Lead Hero span-2 rule in shared cards stylesheet for asymmetric grids', () => {
      expect(cardsCss).toMatch(
        /\.grid--asymmetric\s*>\s*\.card:first-child[\s\S]*?grid-column:\s*span\s*2/
      )
      expect(cardsCss).toMatch(
        /\.grid--asymmetric\s*>\s*\.card:first-child[\s\S]*?aspect-ratio:\s*21\s*\/\s*9/
      )
    })

    it('implements asymmetric grid layout across accommodation (luu-tru) and products (san-pham)', () => {
      expect(luuTruVue).toContain('grid--asymmetric')
      expect(luuTruVue).toContain('stay-grid')

      expect(sanPhamVue).toContain('grid--asymmetric')
      expect(sanPhamVue).toContain('product-grid')
    })

    it('implements asymmetric grid layout in destinations directory (dia-diem/index)', () => {
      expect(diaDiemIndexVue).toContain('grid--asymmetric')
      expect(diaDiemIndexVue).toContain('dd-grid')
    })
  })

  describe('Tier 1 & Tier 2: Editorial Flow & Interruption Dividers (Anti-AI-Slop)', () => {
    it('integrates rhythmic editorial interruption dividers breaking monotony every 8-9 cards', () => {
      expect(diaDiemIndexVue).toMatch(/i\s*%\s*9\s*===\s*0/)
      expect(diaDiemIndexVue).toContain('grid-divider')
    })

    it('eliminates unmodulated equal-column slop grids across catalog pages', () => {
      // Must not use raw unmodulated grid-cols-3 or grid-cols-4 utility slop
      expect(duLichVue).not.toMatch(/\bgrid-cols-[34]\b/)
      expect(luuTruVue).not.toMatch(/\bgrid-cols-[34]\b/)
      expect(sanPhamVue).not.toMatch(/\bgrid-cols-[34]\b/)
      expect(diaDiemIndexVue).not.toMatch(/\bgrid-cols-[34]\b/)
    })
  })

  describe('Tier 1 & Tier 2: Tactile Filter Pills & Touch Target Ergonomics (>= 44px)', () => {
    it('enforces minimum 44px touch targets on FilterChips pills', () => {
      expect(filterChipsVue).toMatch(/\.fc-chip[\s\S]*?min-height:\s*44px/)
    })

    it('enforces minimum 44px touch target on catalog mode pills', () => {
      expect(catalogCss).toMatch(/\.mode-pill[\s\S]*?min-height:\s*(?:var\(--touch-min\)|44px)/)
    })

    it('enforces >= 44x44px touch target with ::before hitbox expansion on dia-diem active filter chips', () => {
      expect(diaDiemIndexVue).toMatch(/\.dd-af-chip\s*\{[\s\S]*?min-height:\s*44px/)
      expect(diaDiemIndexVue).toMatch(/\.dd-af-chip\s*\{[\s\S]*?min-width:\s*44px/)
      expect(diaDiemIndexVue).toMatch(/\.dd-af-chip::before\s*\{[\s\S]*?min-width:\s*44px[\s\S]*?min-height:\s*44px/)
    })

    it('enforces >= 44x44px touch target with ::before hitbox expansion on dia-diem clear button', () => {
      expect(diaDiemIndexVue).toMatch(/\.dd-af-clear\s*\{[\s\S]*?min-height:\s*44px/)
      expect(diaDiemIndexVue).toMatch(/\.dd-af-clear\s*\{[\s\S]*?min-width:\s*44px/)
      expect(diaDiemIndexVue).toMatch(/\.dd-af-clear::before\s*\{[\s\S]*?min-width:\s*44px[\s\S]*?min-height:\s*44px/)
    })

    it('enforces >= 44px touch target on season reset chip in san-pham', () => {
      expect(sanPhamVue).toMatch(/\.season-reset-chip\s*\{[\s\S]*?min-height:\s*44px/)
    })
  })

  describe('Tier 1 & Tier 4: Dedicated Gastronomy Portal (am-thuc.vue)', () => {
    it('provides a dedicated, first-class culinary experience route (am-thuc.vue)', () => {
      expect(existsSync(amThucPath), 'am-thuc.vue must exist to satisfy R1').toBe(true)
      const amThucVue = readFileSync(amThucPath, 'utf8')

      // Verifies Mekong culinary identity
      expect(amThucVue).toContain('Ẩm thực sông nước Cửu Long')
      expect(amThucVue).toMatch(/bún nước lèo|bánh xèo|cá linh|bông điên điển/i)

      // Verifies AEO Plaque guidance
      expect(amThucVue).toContain('CatalogAeoPlaque')
      expect(amThucVue).toContain('Chỉ dẫn Ẩm thực Bản địa Vĩnh Long')

      // Verifies asymmetric layout and flow dividers
      expect(amThucVue).toContain('grid--asymmetric')
      expect(amThucVue).toContain('cuisine-grid')
      expect(amThucVue).toMatch(/cuisine-divider/)

      // Verifies tactile filter pills >= 44px
      expect(amThucVue).toContain('tactile-pill')
      expect(amThucVue).toMatch(/\.tactile-pill[\s\S]*?min-height:\s*44px/)
    })
  })

  describe('Tier 3: Anti-Slop Discipline & Clean Token Integrity', () => {
    it('eliminates false verification claims in catalog interstitials (CLAUDE.md §1.7 & R40.3)', () => {
      // CẤM: Banned claim check without verifiedAt audit
      const bannedAuditPattern = new RegExp('tất cả ' + 'được ' + 'xác minh', 'i')
      expect(diaDiemIndexVue).not.toMatch(bannedAuditPattern)
      expect(diaDiemIndexVue).toMatch(/được ban biên tập tổng hợp|được cập nhật/i)
    })

    it('rejects AI SaaS neon purple and cyan hues in catalog styling', () => {
      expect(catalogCss).not.toMatch(/#5b6cc4|#a855f7|#8b5cf6|#00f0ff/i)
    })
  })
})
