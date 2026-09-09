import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildOcopLedgerSchemaGraph } from '../composables/useSeoHelpers'

describe('Milestone 141: OCOP Honor Ledger Taste, Tactile Ergonomics & Schema Graph', () => {
  const root = resolve(process.cwd())

  describe('buildOcopLedgerSchemaGraph', () => {
    it('generates a rich CollectionPage with speakable selectors, Product ItemList with awards, and FAQPage', () => {
      const graph = buildOcopLedgerSchemaGraph({
        items: [
          {
            id: 'buoi-nam-roi-binh-minh',
            name: 'Bưởi Năm Roi Bình Minh',
            summary: 'Đặc sản quốc gia đạt chứng nhận OCOP 5 sao với vị ngọt thanh ráo múi.',
            stars: 5,
            category: 'Nông sản',
          },
          {
            id: 'banh-trang-nem-cu-lao-may',
            name: 'Bánh tráng nem Cù lao Mây',
            summary: 'Làng nghề truyền thống trăm năm đạt chứng nhận OCOP 4 sao.',
            stars: 4,
            category: 'Thực phẩm chế biến',
          },
        ],
        totalCount: 42,
        topStarTier: 5,
        canonicalUrl: 'https://vinhlong360.vn/ocop',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Sản phẩm OCOP Vĩnh Long')
      expect(collection.about).toBeDefined()
      expect(collection.about.name).toContain('OCOP')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.catalog-hero h1')
      expect(collection.speakable.cssSelector).toContain('.ledger-kicker')
      expect(collection.speakable.cssSelector).toContain('.catalog-aeo-plaque__title')

      // ItemList with Product nodes
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(42)
      expect(itemList.itemListElement).toHaveLength(2)

      const firstProductItem = itemList.itemListElement[0]
      expect(firstProductItem.position).toBe(1)
      expect(firstProductItem.item['@type']).toBe('Product')
      expect(firstProductItem.item.name).toBe('Bưởi Năm Roi Bình Minh')
      expect(firstProductItem.item.award).toBe('Chứng nhận OCOP 5 sao Tỉnh Vĩnh Long')
      expect(firstProductItem.item.category).toBe('OCOP Certified Products')

      // FAQPage with OCOP questions
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
      expect(faq.mainEntity[0].name).toContain('Sản phẩm OCOP Vĩnh Long là gì')
    })
  })

  describe('pages/ocop.vue Ergonomics & Design Tokens', () => {
    it('enforces purpose-based radius tokens and Stitch tactile ergonomics', () => {
      const pageSrc = readFileSync(resolve(root, 'pages/ocop.vue'), 'utf8')

      // R30.8 Radius Token Law: no --radius-full
      expect(pageSrc).not.toContain('var(--radius-full)')
      expect(pageSrc).toContain('var(--radius-pill, 999px)')

      // Tactile physics & mobile ergonomics on star jump buttons
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
