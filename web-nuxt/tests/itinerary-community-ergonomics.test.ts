import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Itinerary, Community Ergonomics & Hall of Honor (Moc 130)', () => {
  describe('Community Hall of Honor (pages/bang-xep-hang.vue)', () => {
    it('integrates CatalogAeoPlaque with ambassador vinh danh highlights', () => {
      const src = readPage('pages/bang-xep-hang.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Sổ Vàng Đóng Góp &amp; Danh Hiệu Đại Sứ Bản Địa')
      expect(src).toContain('Hệ thống Cấp bậc &amp; Điểm Danh tiếng Minh bạch')
      expect(src).toContain('Top 3 Đại sứ Bản xứ Vinh danh Trang trọng')
      expect(src).toContain('Đặc quyền Đóng góp &amp; Huy hiệu Xác thực')
    })

    it('injects speakable AEO selectors into buildLeaderboardSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildLeaderboardSchemaGraph')
      expect(helperSrc).toContain("'.catalog-aeo-plaque__title'")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Itinerary Detail Hub (pages/lich-trinh/[id].vue)', () => {
    it('integrates CatalogAeoPlaque for field trip guidance & terroir insights', () => {
      const src = readPage('pages/lich-trinh/[id].vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Cẩm Nang Trải Nghiệm Thực Địa &amp; Điểm Nhấn Bản Địa')
      expect(src).toContain('Tối ưu Di chuyển &amp; Nhịp Điệu Hành Trình')
      expect(src).toContain('Trải Nghiệm Đậm Chất Sông Nước Nam Bộ')
      expect(src).toContain('Mẹo Bỏ Túi Cho Chuyến Đi Trọn Vẹn')
    })

    it('injects speakable AEO selectors into buildItineraryDetailSchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain('buildItineraryDetailSchemaGraph')
      expect(helperSrc).toContain("'.catalog-aeo-plaque__title'")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__dek'")
    })

    it('respects clean code line ceiling', () => {
      const src = readPage('pages/lich-trinh/[id].vue')
      const lineCount = src.split('\n').length
      expect(lineCount).toBeLessThan(1500)
    })
  })

  describe('Shared Itinerary Hub (pages/lich-trinh-chia-se/[id].vue)', () => {
    it('focuses immediately on shared stops and actions without generic plaques', () => {
      const src = readPage('pages/lich-trinh-chia-se/[id].vue')
      expect(src).not.toContain('<CatalogAeoPlaque')
      expect(src).toContain('class="sp-header"')
      expect(src).toContain('class="sp-stops"')
      expect(src).toContain('class="sp-actions"')
    })

    it('includes direct itinerary speakable selectors in planSchema', () => {
      const src = readPage('pages/lich-trinh-chia-se/[id].vue')
      expect(src).toContain("'.sp-title'")
      expect(src).toContain("'.sp-meta'")
      expect(src).toContain("'.sp-stops'")
      expect(src).not.toMatch(/planSchema[\s\S]*?'.catalog-aeo-plaque__title'/)
    })
  })

  describe('Itinerary Catalog Hub (pages/lich-trinh/index.vue)', () => {
    it('integrates CatalogAeoPlaque with itinerary design rhythms', () => {
      const src = readPage('pages/lich-trinh/index.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Sổ Tay Thiết Kế Lịch Trình &amp; Cung Đường Khám Phá')
      expect(src).toContain('Nhịp Điệu Nửa Ngày (Sáng sớm hoặc Chiều tà)')
      expect(src).toContain('Nhịp Điệu Trọn Ngày (Khám phá Sâu sắc)')
      expect(src).toContain('Nhịp Điệu Nhiều Ngày (Hành trình Liên vùng)')
    })

    it('includes speakable selectors in itineraryCollectionSchema', () => {
      const src = readPage('pages/lich-trinh/index.vue')
      expect(src).toContain("'.catalog-aeo-plaque__title'")
      expect(src).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Design Token & Color Compliance', () => {
    it('has zero raw hex colors across all modified pages', () => {
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
      const files = [
        'pages/bang-xep-hang.vue',
        'pages/lich-trinh/[id].vue',
        'pages/lich-trinh-chia-se/[id].vue',
        'pages/lich-trinh/index.vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const hexes = m[1].match(rawHexPattern) || []
          expect(hexes, `Found raw hex in ${f}`).toEqual([])
        }
      }
    })

    it('complies with R30.8 purpose-based radius tokens', () => {
      const legacyRadiusPattern = /var\(--radius-(xs|sm|md|lg|xl)\)/g
      const files = [
        'pages/bang-xep-hang.vue',
        'pages/lich-trinh/[id].vue',
        'pages/lich-trinh-chia-se/[id].vue',
        'pages/lich-trinh/index.vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const legacyRadii = m[1].match(legacyRadiusPattern) || []
          expect(legacyRadii, `Found legacy radius token in ${f}`).toEqual([])
        }
      }
    })
  })
})
