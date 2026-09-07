import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildProductCatalogSchemaGraph } from '../composables/useSeoHelpers'

describe('Milestone 142: Product Catalog Market Shelf, Tactile Ergonomics & Schema Graph', () => {
  const root = resolve(process.cwd())

  describe('buildProductCatalogSchemaGraph', () => {
    it('generates a rich CollectionPage with speakable selectors, Product ItemList with awards, and FAQPage', () => {
      const graph = buildProductCatalogSchemaGraph({
        items: [
          {
            id: 'sau-rieng-ri6-long-ho',
            name: 'Sầu riêng Ri6 Long Hồ',
            summary: 'Đặc sản nức tiếng cù lao An Bình với cơm vàng hạt lép, béo ngậy.',
            category: 'Trái cây đặc sản',
            ocop_stars: 4,
          },
          {
            id: 'khoai-lang-binh-tan',
            name: 'Khoai lang tím Nhật Bình Tân',
            summary: 'Vùng chuyên canh khoai lang xuất khẩu lớn nhất Đồng bằng sông Cửu Long.',
            category: 'Nông sản',
            ocop_stars: 4,
          },
        ],
        totalCount: 56,
        inSeasonCount: 12,
        currentMonth: 6,
        canonicalUrl: 'https://vinhlong360.vn/san-pham',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Đặc sản & Sản phẩm Vĩnh Long')
      expect(collection.about).toBeDefined()
      expect(collection.about.name).toContain('Đặc sản')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.catalog-hero h1')
      expect(collection.speakable.cssSelector).toContain('.market-kicker')
      expect(collection.speakable.cssSelector).toContain('.seasonal-banner-title')
      expect(collection.speakable.cssSelector).toContain('.catalog-aeo-plaque__title')

      // ItemList with Product nodes
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(56)
      expect(itemList.itemListElement).toHaveLength(2)

      const firstProductItem = itemList.itemListElement[0]
      expect(firstProductItem.position).toBe(1)
      expect(firstProductItem.item['@type']).toBe('Product')
      expect(firstProductItem.item.name).toBe('Sầu riêng Ri6 Long Hồ')
      expect(firstProductItem.item.award).toBe('Chứng nhận OCOP 4 sao')
      expect(firstProductItem.item.category).toBe('Trái cây đặc sản')

      // FAQPage with product questions
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
      expect(faq.mainEntity[0].name).toContain('Vĩnh Long có những loại đặc sản nào nổi tiếng nhất')
    })
  })

  describe('pages/san-pham.vue Ergonomics & Design Tokens', () => {
    it('enforces purpose-based radius tokens and Stitch tactile ergonomics', () => {
      const pageSrc = readFileSync(resolve(root, 'pages/san-pham.vue'), 'utf8')

      // R30.8 Radius Token Law: no --radius-full
      expect(pageSrc).not.toContain('var(--radius-full)')
      expect(pageSrc).toContain('var(--radius-pill, 999px)')

      // Tactile physics & touch target ergonomics on reset chip
      expect(pageSrc).toContain('min-height: 44px')
      expect(pageSrc).toContain('cubic-bezier(0.16, 1, 0.3, 1)')

      // Zero raw hex in stylesheet
      const styleMatches = pageSrc.match(/<style[^>]*>([\s\S]*?)<\/style>/g) || []
      const styleContent = styleMatches.join('\n')
      const cleanCss = styleContent.replace(/url\("data:[^"]+"\)/g, '')
      const rawHexPattern = /(?<![\w-])#[0-9a-fA-F]{3,8}\b/g
      expect(cleanCss.match(rawHexPattern) || []).toEqual([])
    })

    it('preserves Clean Code line ceilings on protected core files', () => {
      const checkMax = (file: string, max: number) => {
        const text = readFileSync(resolve(root, file), 'utf8')
        expect(text.split('\n').length).toBeLessThan(max)
      }
      checkMax('pages/dia-diem/[id].vue', 1200)
      checkMax('pages/tao-lich-trinh.vue', 1500)
      checkMax('pages/tim-kiem.vue', 1100)
      checkMax('pages/xa-phuong/[id].vue', 1050)
    })
  })
})
