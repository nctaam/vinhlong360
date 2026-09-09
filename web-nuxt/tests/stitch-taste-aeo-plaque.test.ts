import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readComp(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Stitch Design Taste & AEO Plaque Refinements (Moc 136)', () => {
  describe('Shared Catalog AEO Plaque (components/CatalogAeoPlaque.vue)', () => {
    it('integrates local field verification stamp with icon and localized text', () => {
      const src = readComp('components/CatalogAeoPlaque.vue')
      expect(src).toContain('catalog-aeo-plaque__stamp')
      expect(src).toContain('name="shield-check"')
      expect(src).toContain('Xác thực thực địa')
    })

    it('enforces purpose-based radius scale and eliminates legacy radius-full', () => {
      const src = readComp('components/CatalogAeoPlaque.vue')
      const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
      expect(style).toContain('--radius-pill')
      expect(style).toContain('--radius-sheet')
      expect(style).toContain('--radius-surface')
      expect(style).not.toMatch(/--radius-full\b/)
      expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)
    })

    it('enforces zero raw hex color debt in style tag', () => {
      const src = readComp('components/CatalogAeoPlaque.vue')
      const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
      expect(style).not.toMatch(/:\s*#[0-9a-fA-F]{3,8}\b/)
    })

    it('provides tactile spring physics and accessibility motion reduction', () => {
      const src = readComp('components/CatalogAeoPlaque.vue')
      expect(src).toContain('cubic-bezier(0.16, 1, 0.3, 1)')
      expect(src).toContain('prefers-reduced-motion: reduce')
    })
  })

  describe('Home AEO Plaque Integration (pages/index.vue)', () => {
    it('integrates configurable CatalogAeoPlaque with seasonal entries on home page', () => {
      const src = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('data-home-section="aeo-plaque"')
      expect(src).toContain('data-home-aeo-plaque')
      expect(src).toContain('Cẩm nang du lịch theo mùa')
      expect(src).toContain('Mùa nước nổi & Miệt vườn')
      expect(src).toContain('Mùa di sản gốm & Hoa xuân')
    })
  })

  describe('Tone of Voice & Anti-Slop Enforcement', () => {
    const FILLERS = [
      'miền Tây',
      'sông nước hữu tình',
      'thiên đường',
      'hidden gem',
      'must-see',
      'không thể bỏ lỡ',
      'đắm chìm',
      'hòa mình vào',
      'điểm đến lý tưởng',
    ]

    const files = [
      'components/CatalogAeoPlaque.vue',
      'pages/index.vue',
    ]

    for (const f of files) {
      it(`${f} is free from banned promotional fillers`, () => {
        const src = readFileSync(resolve(__dirname, '..', f), 'utf8')
        for (const filler of FILLERS) {
          expect(src.toLowerCase()).not.toContain(filler.toLowerCase())
        }
      })
    }
  })
})
