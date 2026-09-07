import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildSeasonalitySchemaGraph } from '../composables/useSeoHelpers'

describe('Milestone 139: Seasonal Almanac, Mekong River Tides & Stitch Tactile Ergonomics', () => {
  const root = resolve(process.cwd())

  describe('buildSeasonalitySchemaGraph', () => {
    it('generates a rich CollectionPage with speakable selectors, geo containment, and ItemList', () => {
      const graph = buildSeasonalitySchemaGraph({
        month: 6,
        quarterTag: 'cao điểm mùa hè',
        quarterNote: 'Nắng vàng rực rỡ, nhiều đặc sản vào chính vụ nhất trong năm.',
        totalInSeason: 18,
        items: [
          { id: 'chom-chom-binh-hoa-phuoc', name: 'Chôm chôm Bình Hòa Phước', type: 'product' },
          { id: 'sau-rieng-ri6', name: 'Sầu riêng Ri6 Long Hồ', type: 'product' },
        ],
        canonicalUrl: 'https://vinhlong360.vn/theo-mua',
      })

      const nodes = graph['@graph'] as any[]
      const collection = nodes.find(n => n['@type'] === 'CollectionPage')
      expect(collection).toBeDefined()
      expect(collection.name).toContain('Tháng 6')
      expect(collection.about).toBeDefined()
      expect(collection.about.name).toBe('Tỉnh Vĩnh Long')
      expect(collection.about.geo.box).toBe('9.8 105.8 10.4 106.7')

      // Speakable voice selectors
      expect(collection.speakable).toBeDefined()
      expect(collection.speakable.cssSelector).toContain('.season-moment-text strong')
      expect(collection.speakable.cssSelector).toContain('.season-tide-cue')

      // ItemList
      const itemList = nodes.find(n => n['@type'] === 'ItemList')
      expect(itemList).toBeDefined()
      expect(itemList.numberOfItems).toBe(18)
      expect(itemList.itemListElement).toHaveLength(2)
      expect(itemList.itemListElement[0].name).toBe('Chôm chôm Bình Hòa Phước')
      expect(itemList.itemListElement[0].url).toBe('https://vinhlong360.vn/dia-diem/chom-chom-binh-hoa-phuoc')

      // FAQPage
      const faq = nodes.find(n => n['@type'] === 'FAQPage')
      expect(faq).toBeDefined()
      expect(faq.mainEntity.length).toBeGreaterThanOrEqual(3)
    })
  })

  describe('pages/theo-mua.vue Ergonomics & Design Tokens', () => {
    it('uses purpose-based radius tokens and Stitch tactile physics', () => {
      const src = readFileSync(resolve(root, 'pages/theo-mua.vue'), 'utf8')

      // R30.8 Radius Token Law: no --radius-full
      expect(src).not.toContain('--radius-full')
      expect(src).toContain('--radius-pill, 999px')

      // Mekong river terroir tide cue
      expect(src).toContain('season-tide-cue')
      expect(src).toContain('seasonalTideCue')

      // Stitch tactile physics
      expect(src).toContain('cubic-bezier(0.16, 1, 0.3, 1)')

      // Color-mix clean tokens
      expect(src).toContain('color-mix(in srgb, var(--color-material-river)')

      // Zero raw hex in stylesheet
      const styleMatches = src.match(/<style[^>]*>([\s\S]*?)<\/style>/g) || []
      const styleContent = styleMatches.join('\n')
      // exclude data URIs
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
