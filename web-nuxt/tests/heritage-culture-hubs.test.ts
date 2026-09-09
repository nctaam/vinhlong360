import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('Heritage, Culture Hubs & Lunar Terroir Calendar (Moc 128)', () => {
  describe('Discovery Interest Hub (pages/kham-pha/[interest].vue)', () => {
    it('integrates CatalogAeoPlaque with reactive dynamic content', () => {
      const src = readPage('pages/kham-pha/[interest].vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain(':title="aeoContent.title"')
      expect(src).toContain(':kicker="aeoContent.kicker"')
      expect(src).toContain(':entries="aeoContent.entries"')
    })

    it('defines authoritative AEO digests for all 5 core themes', () => {
      const src = readPage('pages/kham-pha/[interest].vue')
      // am-thuc
      expect(src).toContain('Tinh hoa Ẩm thực Bản địa Vĩnh Long')
      expect(src).toContain('Khoai lang tím mắm sống & Cá tai tượng')
      // lang-nghe
      expect(src).toContain('Di sản Làng nghề & Vương quốc Gốm Đỏ')
      expect(src).toContain('Lò gạch gốm đỏ Mang Thít')
      // van-hoa
      expect(src).toContain('Đất Địa Linh Nhân Kiệt & Di Tích Lịch Sử')
      expect(src).toContain('Văn Thánh Miếu 1864')
      // thien-nhien
      expect(src).toContain('Nhịp Sống Cù Lao & Vườn Cây Trái Xanh Mát')
      expect(src).toContain('Cù lao An Bình sông Cổ Chiên')
      // mua-sam (fallback)
      expect(src).toContain('Đặc Sản OCOP & Quà Quê Phù Sa')
      expect(src).toContain('Bưởi Năm Roi & Sầu riêng Ri6')
    })

    it('injects speakable AEO selectors into interest schema helper', () => {
      const helperSrc = readPage('composables/useSeoHelpers.ts')
      expect(helperSrc).toContain("'.catalog-aeo-plaque__title'")
      expect(helperSrc).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Events & Festivals Hub (pages/su-kien.vue)', () => {
    it('integrates CatalogAeoPlaque with contemporary event highlights', () => {
      const src = readPage('pages/su-kien.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Nhịp Điệu Sự Kiện &amp; Hội Chợ Vĩnh Long')
      expect(src).toContain('Festival Gạch Gốm Đỏ Mang Thít')
      expect(src).toContain('Ngày hội Du lịch Sông nước Cù lao')
      expect(src).toContain('Hội chợ Nông nghiệp &amp; Triển lãm OCOP')
    })

    it('includes speakable selectors in Schema.org LD+JSON graph', () => {
      const helper = readPage('composables/useSeoHelpers.ts')
      expect(helper).toMatch(/buildContemporaryEventSchemaGraph[\s\S]*?\.catalog-aeo-plaque__title/)
      expect(helper).toMatch(/buildContemporaryEventSchemaGraph[\s\S]*?\.catalog-aeo-plaque__dek/)
    })
  })

  describe('Lunar Terroir Calendar (pages/lich-van-nien.vue)', () => {
    it('integrates CatalogAeoPlaque for Mekong tidal rhythm & solar terms', () => {
      const src = readPage('pages/lich-van-nien.vue')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('Nhịp Con Nước &amp; Tiết Khí Sông Nước Vĩnh Long')
      expect(src).toContain('Con nước rong (Rằm &amp; Mùng 1 âm lịch)')
      expect(src).toContain('Con nước kém (Mùng 7–8 &amp; 22–23 âm lịch)')
      expect(src).toContain('24 Tiết khí &amp; Vụ mùa cây trái')
    })

    it('includes speakable selectors in WebApplication Schema', () => {
      const src = readPage('pages/lich-van-nien.vue')
      expect(src).toContain("'.catalog-aeo-plaque__title'")
      expect(src).toContain("'.catalog-aeo-plaque__dek'")
    })
  })

  describe('Design Token & Color Compliance', () => {
    it('has zero raw hex colors across all modified pages', () => {
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
      const files = [
        'pages/kham-pha/[interest].vue',
        'pages/su-kien.vue',
        'pages/lich-van-nien.vue',
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
        'pages/kham-pha/[interest].vue',
        'pages/su-kien.vue',
        'pages/lich-van-nien.vue',
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
