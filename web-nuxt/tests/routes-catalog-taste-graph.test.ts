import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildRoutesCatalogSchemaGraph } from '../composables/useSeoHelpers'

describe('Milestone 143: Routes Catalog Tactile Ergonomics & Linked Trip Schema Graph', () => {
  const root = resolve(process.cwd())

  describe('buildRoutesCatalogSchemaGraph', () => {
    it('generates a rich CollectionPage with TouristTrip ItemList, spatialCoverage, and FAQPage', () => {
      const graph = buildRoutesCatalogSchemaGraph({
        routes: [
          {
            id: 'vong-trai-cay-vinh-long',
            name: 'Vòng quanh cù lao An Bình',
            description: 'Khám phá miệt vườn trái cây 4 mùa và di chuyển bằng phà sông Cổ Chiên.',
            duration: '1 ngày',
            distance: '25 km',
            area: 'vinh-long',
            stops: [
              { name: 'Bến phà An Bình' },
              { name: 'Vườn chôm chôm Bình Hòa Phước' },
              { name: 'Chùa Tiên Châu' },
            ],
          },
          {
            id: 'di-san-gom-mang-thit',
            name: 'Cung đường di sản gốm đỏ Mang Thít',
            description: 'Tuyến ĐT 902 dọc kênh Thầy Cai chiêm ngưỡng quần thể lò nung gạch nung rêu phong.',
            duration: 'Nửa ngày',
            distance: '18 km',
            area: 'vinh-long',
            stops: [
              { name: 'Cầu Mang Thít' },
              { name: 'Làng gốm Nhơn Phú' },
            ],
          },
        ],
        totalCount: 5,
        canonicalUrl: 'https://vinhlong360.vn/tuyen-duong',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Tuyến đường gợi ý Vĩnh Long')
      expect(collection.about).toBeDefined()
      expect(collection.about['@type']).toBe('TouristTrip')
      expect(collection.about.spatialCoverage.geo.box).toBe('9.8 105.8 10.4 106.7')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.catalog-hero h1')
      expect(collection.speakable.cssSelector).toContain('.route-header')
      expect(collection.speakable.cssSelector).toContain('.catalog-aeo-plaque__title')

      // ItemList with TouristTrip nodes
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(5)
      expect(itemList.itemListElement).toHaveLength(2)

      const firstTrip = itemList.itemListElement[0]
      expect(firstTrip.position).toBe(1)
      expect(firstTrip.item['@type']).toBe('TouristTrip')
      expect(firstTrip.item.name).toBe('Vòng quanh cù lao An Bình')
      expect(firstTrip.item.distance).toBe('25 km')
      expect(firstTrip.item.itinerary.itemListElement).toHaveLength(3)

      // FAQPage with route & transit questions
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
      expect(faq.mainEntity[0].name).toContain('Nên chọn phương tiện gì')
    })
  })

  describe('pages/tuyen-duong.vue Ergonomics & Design Tokens', () => {
    it('enforces purpose-based radius tokens and Stitch tactile ergonomics', () => {
      const pageSrc = readFileSync(resolve(root, 'pages/tuyen-duong.vue'), 'utf8')

      // R30.8 Radius Token Law: no --radius-full or bare --radius
      expect(pageSrc).not.toContain('var(--radius-full)')
      expect(pageSrc).not.toContain('border-radius: var(--radius);')
      expect(pageSrc).toContain('var(--radius-pill, 999px)')
      expect(pageSrc).toContain('var(--radius-sheet)')

      // Tactile physics & transition curves
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
