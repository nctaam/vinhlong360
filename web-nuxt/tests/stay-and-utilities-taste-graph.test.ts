import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { buildStayCatalogSchemaGraph } from '../composables/useSeoHelpers'

describe('Moc 145: Stay Catalog Schema Graph and Utilities Ergonomics', () => {
  it('generates a rich unified schema graph for Stay Catalog (pages/luu-tru.vue)', () => {
    const graph = buildStayCatalogSchemaGraph({
      items: [
        {
          id: 'stay-ut-trinh',
          name: 'Út Trinh Homestay Cù Lao An Bình',
          summary: 'Homestay miệt vườn truyền thống tại cù lao An Bình với vườn nhãn và xuồng chèo.',
          place_name: 'Xã An Bình, Long Hồ',
          type: 'homestay',
        },
        {
          id: 'hotel-cuu-long',
          name: 'Khách sạn Cửu Long',
          summary: 'Khách sạn ven sông Cổ Chiên trung tâm TP Vĩnh Long.',
          place_name: 'Phường 1, TP Vĩnh Long',
          type: 'hotel',
        },
      ],
      totalCount: 42,
      canonicalUrl: 'https://vinhlong360.vn/luu-tru',
    })

    expect(graph['@context']).toBe('https://schema.org')
    expect(Array.isArray(graph['@graph'])).toBe(true)

    const nodes = graph['@graph'] as Record<string, any>[]
    const collectionPage = nodes.find(n => n['@type'] === 'CollectionPage')
    expect(collectionPage).toBeDefined()
    expect(collectionPage?.url).toBe('https://vinhlong360.vn/luu-tru')
    expect(collectionPage?.numberOfItems).toBe(42)
    expect(collectionPage?.speakable).toBeDefined()
    expect(collectionPage?.spatialCoverage?.geo?.box).toBe('10.0 105.8 10.4 106.2')

    const itemList = nodes.find(n => n['@type'] === 'ItemList')
    expect(itemList).toBeDefined()
    expect(itemList?.numberOfItems).toBe(42)
    expect(itemList?.itemListElement).toHaveLength(2)

    // Homestay should map to BedAndBreakfast
    const firstItem = itemList?.itemListElement[0]
    expect(firstItem.item['@type']).toBe('BedAndBreakfast')
    expect(firstItem.item.name).toBe('Út Trinh Homestay Cù Lao An Bình')
    expect(firstItem.item.address?.addressLocality).toBe('Xã An Bình, Long Hồ')

    // Hotel should map to LodgingBusiness
    const secondItem = itemList?.itemListElement[1]
    expect(secondItem.item['@type']).toBe('LodgingBusiness')

    const faqPage = nodes.find(n => n['@type'] === 'FAQPage')
    expect(faqPage).toBeDefined()
    expect(faqPage?.mainEntity?.length).toBeGreaterThanOrEqual(3)
  })

  it('enforces R30.8 Radius Token Law across all modernized catalog & utility pages', () => {
    const rootDir = resolve(__dirname, '..')
    const pagesToCheck = [
      'pages/luu-tru.vue',
      'pages/bang-xep-hang.vue',
      'pages/lich-van-nien.vue',
      'pages/danh-ba.vue',
      'pages/lich-trinh/index.vue',
      'pages/lich-trinh/[id].vue',
    ]

    for (const relPath of pagesToCheck) {
      const content = readFileSync(resolve(rootDir, relPath), 'utf-8')
      // No occurrences of var(--radius-full)
      expect(content).not.toContain('var(--radius-full)')
      // No bare --radius-full
      expect(content).not.toMatch(/--radius-full\b/)
    }
  })

  it('verifies pages/luu-tru.vue uses buildStayCatalogSchemaGraph', () => {
    const rootDir = resolve(__dirname, '..')
    const content = readFileSync(resolve(rootDir, 'pages/luu-tru.vue'), 'utf-8')
    expect(content).toContain('buildStayCatalogSchemaGraph')
  })

  it('verifies pages/danh-ba.vue uses unified directorySchema without duplicate jsonLd', () => {
    const rootDir = resolve(__dirname, '..')
    const content = readFileSync(resolve(rootDir, 'pages/danh-ba.vue'), 'utf-8')
    expect(content).toContain('buildDirectorySchemaGraph')
    expect(content).not.toContain('const jsonLd = computed')
  })

  it('strictly protects line count ceilings for the 4 critical pages', () => {
    const rootDir = resolve(__dirname, '..')
    const ceilings: Record<string, number> = {
      'pages/dia-diem/[id].vue': 1200,
      'pages/tao-lich-trinh.vue': 1500,
      'pages/tim-kiem.vue': 1100,
      'pages/xa-phuong/[id].vue': 1050,
    }

    for (const [relPath, maxLines] of Object.entries(ceilings)) {
      const content = readFileSync(resolve(rootDir, relPath), 'utf-8')
      const lineCount = content.split('\n').length
      expect(lineCount).toBeLessThan(maxLines)
    }
  })
})
