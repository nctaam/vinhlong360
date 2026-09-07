import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  buildContemporaryEventSchemaGraph,
  buildTourismCatalogSchemaGraph,
} from '../composables/useSeoHelpers'

describe('Milestone 144: Contemporary Events & 3-Region Tourism Catalog Schema Graphs', () => {
  const root = resolve(process.cwd())

  describe('buildContemporaryEventSchemaGraph', () => {
    it('generates a rich CollectionPage with Event ItemList, speakable selectors, and FAQPage', () => {
      const graph = buildContemporaryEventSchemaGraph({
        events: [
          {
            id: 'festival-gom-mang-thit',
            name: 'Festival Gạch Gốm Đỏ Mang Thít',
            summary: 'Tôn vinh làng nghề gốm đỏ truyền thống trăm năm dọc dòng kênh Thầy Cai.',
            place_name: 'Huyện Mang Thít, Tỉnh Vĩnh Long',
            date_start: '2026-10-15',
            date_end: '2026-10-18',
          },
        ],
        totalCount: 8,
        todayGregorianLabel: '08/09/2026',
        todayLunarLabel: '28/07 Bính Ngọ',
        canonicalUrl: 'https://vinhlong360.vn/su-kien',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Sự kiện & Hội chợ Vĩnh Long')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.catalog-hero h1')
      expect(collection.speakable.cssSelector).toContain('.now-banner')
      expect(collection.speakable.cssSelector).toContain('.register-toggle')

      // ItemList with Event nodes
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(8)
      expect(itemList.itemListElement).toHaveLength(1)

      const firstEvent = itemList.itemListElement[0]
      expect(firstEvent.position).toBe(1)
      expect(firstEvent.item['@type']).toBe('Event')
      expect(firstEvent.item.name).toBe('Festival Gạch Gốm Đỏ Mang Thít')
      expect(firstEvent.item.startDate).toBe('2026-10-15')
      expect(firstEvent.item.location.name).toBe('Huyện Mang Thít, Tỉnh Vĩnh Long')

      // FAQPage with event questions
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
      expect(faq.mainEntity[0].name).toContain('Vĩnh Long thường tổ chức những sự kiện hoặc hội chợ lớn nào')
    })
  })

  describe('buildTourismCatalogSchemaGraph', () => {
    it('generates a rich CollectionPage with TouristAttraction ItemList and geo coverage', () => {
      const graph = buildTourismCatalogSchemaGraph({
        items: [
          {
            id: 'lo-gach-mang-thit',
            name: 'Quần thể lò gạch gốm Mang Thít',
            summary: 'Di sản đương đại độc nhất vô nhị vùng đồng bằng sông Cửu Long.',
            type: 'attraction',
          },
        ],
        totalCount: 45,
        currentMonth: 9,
        canonicalUrl: 'https://vinhlong360.vn/du-lich',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Du lịch Vĩnh Long')
      expect(collection.about).toBeDefined()
      expect(collection.about['@type']).toBe('TouristDestination')
      expect(collection.about.geo.box).toBe('9.8 105.8 10.4 106.7')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.atlas-hero-title')
      expect(collection.speakable.cssSelector).toContain('.catalog-route-trace')

      // ItemList with TouristAttraction nodes
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(45)
      expect(itemList.itemListElement).toHaveLength(1)

      const firstItem = itemList.itemListElement[0]
      expect(firstItem.position).toBe(1)
      expect(firstItem.item['@type']).toBe('TouristAttraction')
      expect(firstItem.item.name).toBe('Quần thể lò gạch gốm Mang Thít')

      // FAQPage with tourism questions
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
      expect(faq.mainEntity[0].name).toContain('Đi du lịch Vĩnh Long mùa nào')
    })
  })

  describe('Clean Code & Protected Core Files', () => {
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
