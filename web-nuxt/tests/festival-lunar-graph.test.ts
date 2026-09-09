import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildFestivalEventSchemaGraph } from '../composables/useSeoHelpers'

describe('Milestone 140: Festival Lunar Ribbon Liquid Glass & Event Schema Graph', () => {
  const root = resolve(process.cwd())

  describe('buildFestivalEventSchemaGraph', () => {
    it('generates a rich CollectionPage with speakable selectors, Event ItemList, and FAQPage', () => {
      const graph = buildFestivalEventSchemaGraph({
        events: [
          {
            id: 'le-hoi-ok-om-bok',
            name: 'Lễ hội Ok Om Bok cúng trăng',
            summary: 'Di sản văn hóa phi vật thể quốc gia của đồng bào Khmer Trà Vinh - Vĩnh Long.',
            place_name: 'Chùa Âng / Chùa Hạnh Phúc Tăng',
            date_start: '2026-11-23',
            date_end: '2026-11-24',
          },
          {
            id: 'le-hoi-lang-ong-tien-quan-thong-che-dieu-bat',
            name: 'Lễ hội Lăng Ông Tiền quân Thống chế Điều bát',
            summary: 'Lễ hội truyền thống kỳ an tưởng nhớ Thống chế Điều bát Nguyễn Văn Tồn.',
            place_name: 'Lăng Ông Trà Ôn',
          },
        ],
        totalCount: 15,
        canonicalUrl: 'https://vinhlong360.vn/le-hoi',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Lễ hội truyền thống Vĩnh Long')
      expect(collection.about).toBeDefined()
      expect(collection.about.name).toBe('Tỉnh Vĩnh Long')
      expect(collection.about.geo.box).toBe('9.8 105.8 10.4 106.7')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.catalog-hero h1')
      expect(collection.speakable.cssSelector).toContain('.now-banner')

      // ItemList with Event nodes
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(15)
      expect(itemList.itemListElement).toHaveLength(2)

      const firstEventItem = itemList.itemListElement[0]
      expect(firstEventItem.position).toBe(1)
      expect(firstEventItem.item['@type']).toBe('Event')
      expect(firstEventItem.item.name).toBe('Lễ hội Ok Om Bok cúng trăng')
      expect(firstEventItem.item.location.name).toBe('Chùa Âng / Chùa Hạnh Phúc Tăng')
      expect(firstEventItem.item.startDate).toBe('2026-11-23')

      // FAQPage with cultural etiquette
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
      expect(faq.mainEntity[0].name).toContain('Văn hóa lễ hội Vĩnh Long')
    })
  })

  describe('pages/le-hoi.vue & assets/css/events.css Ergonomics & Tokens', () => {
    it('enforces purpose-based radius tokens and Liquid Glass styling', () => {
      const pageSrc = readFileSync(resolve(root, 'pages/le-hoi.vue'), 'utf8')
      const cssSrc = readFileSync(resolve(root, 'assets/css/events.css'), 'utf8')

      // R30.8 Radius Token Law in le-hoi.vue
      expect(pageSrc).not.toContain('var(--radius-full)')
      expect(pageSrc).toContain('var(--radius-pill, 999px)')
      expect(pageSrc).toContain('var(--radius-surface, 12px)')

      // events.css no active var(--radius-full)
      const cssWithoutComments = cssSrc.replace(/\/\*[\s\S]*?\*\//g, '')
      expect(cssWithoutComments).not.toContain('var(--radius-full)')
      expect(cssSrc).toContain('var(--radius-pill, 999px)')
      expect(cssSrc).toContain('var(--radius-surface, 12px)')

      // Liquid Glass & tactile physics on lunar ribbon
      expect(cssSrc).toContain('backdrop-filter: blur(12px)')
      expect(cssSrc).toContain('cubic-bezier(0.16, 1, 0.3, 1)')

      // Zero raw hex in events.css
      const cleanCss = cssWithoutComments.replace(/url\("data:[^"]+"\)/g, '')
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
