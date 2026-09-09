import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('District Terroirs, River Ecology Routes & Directory Hub (Moc 129)', () => {
  describe('Main Directory Hub (pages/dia-diem/index.vue)', () => {
    it('integrates CatalogAeoPlaque with tri-region directory highlights', () => {
      const src = readPage('pages/dia-diem/index.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Cẩm Nang Tra Cứu Toàn Bộ 1.500+ Điểm Đến Vĩnh Long')
      expect(src).toContain('Vùng Đất Gốm Đỏ &amp; Miệt Vườn Cù Lao (Vĩnh Long)')
      expect(src).toContain('Vùng Xứ Dừa &amp; Rạch Sông Nước (Bến Tre trước 7-2025)')
      expect(src).toContain('Vùng Văn Hóa Khmer &amp; Biển Phù Sa (Trà Vinh trước 7-2025)')
    })

    it('injects speakable AEO selectors into buildCatalogDirectorySchemaGraph', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain("buildCatalogDirectorySchemaGraph")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__title'")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Regional & District Terroir Hub (pages/khu-vuc/[area].vue)', () => {
    it('integrates dynamic CatalogAeoPlaque for regional terroir portfolios', () => {
      const src = readPage('pages/khu-vuc/[area].vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain(':title="areaAeoDigest.title"')
      expect(src).toContain(':kicker="areaAeoDigest.kicker"')
      expect(src).toContain(':entries="areaAeoDigest.entries"')
    })

    it('defines authoritative terroir digests for all 3 historical regions', () => {
      const src = readPage('pages/khu-vuc/[area].vue')
      // ben-tre
      expect(src).toContain('Đặc Trưng Thổ Nhưỡng & Văn Hóa Địa Hạt Bến Tre (Cũ)')
      expect(src).toContain('Chợ Lách — Thủ phủ Hoa kiểng Cái Mơn')
      // tra-vinh
      expect(src).toContain('Đặc Trưng Thổ Nhưỡng & Văn Hóa Địa Hạt Trà Vinh (Cũ)')
      expect(src).toContain('Quần thể 140+ Chùa Khmer Cổ kính')
      expect(src).toContain('Dừa sáp Cầu Kè & Biển Ba Động')
      // vinh-long
      expect(src).toContain('Đặc Trưng Thổ Nhưỡng & Văn Hóa Địa Hạt Vĩnh Long')
      expect(src).toContain('Cù lao An Bình & Bình Hòa Phước')
      expect(src).toContain('Di sản Đương đại Mang Thít')
    })

    it('includes speakable selectors in Schema.org LD+JSON graph', () => {
      const src = readPage('pages/khu-vuc/[area].vue')
      expect(src).toContain("'.catalog-aeo-plaque__title'")
      expect(src).toContain("'.catalog-aeo-plaque__dek'")
    })

    it('respects clean code line ceiling', () => {
      const src = readPage('pages/khu-vuc/[area].vue')
      const lineCount = src.split('\n').length
      expect(lineCount).toBeLessThan(1050)
    })
  })

  describe('River Routes & Transit Hub (pages/tuyen-duong.vue)', () => {
    it('integrates CatalogAeoPlaque with river ecology & road routes', () => {
      const src = readPage('pages/tuyen-duong.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Cẩm Nang Tuyến Đường Khám Phá &amp; Hành Trình Sông Nước')
      expect(src).toContain('Cung đường Cù lao An Bình &amp; Đò ngang sông Cổ Chiên')
      expect(src).toContain('Cung đường Di sản Gốm đỏ Mang Thít (ĐT 902)')
      expect(src).toContain('Hành trình Liên Vùng Ba Con Sông (Tiền – Cổ Chiên – Hậu)')
    })

    it('includes speakable selectors in WebPage schema', () => {
      const src = readPage('pages/tuyen-duong.vue')
      expect(src).toContain('buildRoutesCatalogSchemaGraph')
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain("'.catalog-aeo-plaque__title'")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Design Token & Color Compliance', () => {
    it('has zero raw hex colors across all modified pages', () => {
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
      const files = [
        'pages/dia-diem/index.vue',
        'pages/khu-vuc/[area].vue',
        'pages/tuyen-duong.vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const hexes = m[1]!.match(rawHexPattern) || []
          expect(hexes, `Found raw hex in ${f}`).toEqual([])
        }
      }
    })

    it('complies with R30.8 purpose-based radius tokens', () => {
      const legacyRadiusPattern = /var\(--radius-(xs|sm|md|lg|xl)\)/g
      const files = [
        'pages/dia-diem/index.vue',
        'pages/khu-vuc/[area].vue',
        'pages/tuyen-duong.vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const legacyRadii = m[1]!.match(legacyRadiusPattern) || []
          expect(legacyRadii, `Found legacy radius token in ${f}`).toEqual([])
        }
      }
    })
  })
})
