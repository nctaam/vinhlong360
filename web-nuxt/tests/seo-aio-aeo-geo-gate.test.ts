// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  buildFaqPageSchema,
  buildSpeakableSpecification,
  buildWebSiteSchema,
  buildOrganizationSchema,
  buildUnifiedSchemaGraph,
  safeJsonLd,
  SITE_URL,
} from '../composables/useSeoHelpers'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('SEO / AIO / AEO / GEO Architecture Quality Gate', () => {
  describe('Schema Helpers (composables/useSeoHelpers.ts)', () => {
    it('buildFaqPageSchema creates compliant FAQPage nodes with Question and Answer', () => {
      expect(buildFaqPageSchema([])).toBeNull()

      const faqs = [
        { q: 'Vĩnh Long có gì chơi?', a: 'Du lịch miệt vườn, di sản gốm Mang Thít và cù lao An Bình.' },
        { q: 'Đi mùa nào đẹp?', a: 'Mùa trái cây chín từ tháng 5 đến tháng 8.' },
      ]
      const schema = buildFaqPageSchema(faqs, 'https://vinhlong360.vn/test#faq')
      expect(schema).toEqual({
        '@type': 'FAQPage',
        '@id': 'https://vinhlong360.vn/test#faq',
        mainEntity: [
          {
            '@type': 'Question',
            name: faqs[0].q,
            acceptedAnswer: { '@type': 'Answer', text: faqs[0].a },
          },
          {
            '@type': 'Question',
            name: faqs[1].q,
            acceptedAnswer: { '@type': 'Answer', text: faqs[1].a },
          },
        ],
      })
    })

    it('buildSpeakableSpecification generates valid Schema.org SpeakableSpecification', () => {
      const defaultSpeakable = buildSpeakableSpecification()
      expect(defaultSpeakable).toEqual({
        '@type': 'SpeakableSpecification',
        cssSelector: ['.lead', 'h1', '.desc-heading'],
      })

      const customSpeakable = buildSpeakableSpecification(['.hero', 'h2'])
      expect(customSpeakable).toEqual({
        '@type': 'SpeakableSpecification',
        cssSelector: ['.hero', 'h2'],
      })
    })

    it('buildWebSiteSchema connects to #organization publisher', () => {
      const site = buildWebSiteSchema()
      expect(site['@type']).toBe('WebSite')
      expect(site['@id']).toBe(`${SITE_URL}/#website`)
      expect(site.publisher).toEqual({ '@id': `${SITE_URL}/#organization` })
      expect(site.inLanguage).toBe('vi-VN')
    })

    it('buildOrganizationSchema defines geographic knowledge authority', () => {
      const org = buildOrganizationSchema()
      expect(org['@type']).toBe('Organization')
      expect(org['@id']).toBe(`${SITE_URL}/#organization`)
      expect(org.areaServed).toEqual({
        '@type': 'AdministrativeArea',
        name: 'Tỉnh Vĩnh Long',
        '@id': `${SITE_URL}/#province`,
      })
      expect(org.knowsAbout).toContain('Du lịch Vĩnh Long')
      expect(org.knowsAbout).toContain('Làng nghề gốm Mang Thít')
    })

    it('buildUnifiedSchemaGraph strips nullish entries and wraps in @graph', () => {
      const graph = buildUnifiedSchemaGraph([
        buildWebSiteSchema(),
        null,
        undefined,
        buildOrganizationSchema(),
      ])
      expect(graph['@context']).toBe('https://schema.org')
      expect(Array.isArray(graph['@graph'])).toBe(true)
      expect(graph['@graph']).toHaveLength(2)
      expect(graph['@graph'][0]['@type']).toBe('WebSite')
      expect(graph['@graph'][1]['@type']).toBe('Organization')
    })

    it('safeJsonLd secures output against script injection and parses cleanly', () => {
      const maliciousData = {
        title: '</script><script>alert("xss")</script>',
        graph: buildUnifiedSchemaGraph([buildWebSiteSchema()]),
      }
      const serialized = safeJsonLd(maliciousData)
      expect(serialized).not.toContain('</script>')
      expect(serialized).toContain('<\\/script>')
      expect(() => JSON.parse(serialized)).not.toThrow()
    })
  })

  describe('Place Detail Knowledge Graph (pages/dia-diem/[id].vue)', () => {
    it('integrates unified @graph with WebPage, Speakable, Entity, Breadcrumb and FAQ', () => {
      const detail = doc('pages/dia-diem/[id].vue')
      expect(detail).toContain('buildUnifiedSchemaGraph')
      expect(detail).toContain('buildSpeakableSpecification')
      expect(detail).toContain('buildFaqPageSchema')
      expect(detail).toContain("isPartOf: { '@id': `${SITE_URL}/#website` }")
      expect(detail).toContain("publisher: { '@id': `${SITE_URL}/#organization` }")
      expect(detail).toContain("breadcrumb: { '@id': `${entityUrl}#breadcrumb` }")
      expect(detail).toContain("mainEntity: { '@id': `${entityUrl}#entity` }")
    })
  })

  describe('Administrative Ward Knowledge Graph (pages/xa-phuong/[id].vue)', () => {
    it('integrates unified @graph with AdministrativeArea, geo, hasMap, and localized FAQ', () => {
      const ward = doc('pages/xa-phuong/[id].vue')
      expect(ward).toContain('buildUnifiedSchemaGraph')
      expect(ward).toContain('buildSpeakableSpecification')
      expect(ward).toContain('buildFaqPageSchema')
      expect(ward).toContain("'@type': 'AdministrativeArea'")
      expect(ward).toContain('schema.hasMap = `https://www.google.com/maps/search/?api=1&query=${c[0]},${c[1]}`')
      expect(ward).toContain("containedInPlace: {")
    })
  })

  describe('OCOP Hub Knowledge Graph (pages/ocop.vue)', () => {
    it('publishes CollectionPage with program About node, Speakable, and 3-to-5 star FAQ', () => {
      const ocop = doc('pages/ocop.vue')
      expect(ocop).toContain('buildWebSiteSchema()')
      expect(ocop).toContain('buildOrganizationSchema()')
      expect(ocop).toContain('buildSpeakableSpecification')
      expect(ocop).toContain('buildFaqPageSchema')
      expect(ocop).toContain("name: 'Chương trình Mỗi xã Một sản phẩm (OCOP)'")
      expect(ocop).toContain("safeJsonLd({")
    })
  })

  describe('Festival Cultural Knowledge Graph (pages/le-hoi.vue)', () => {
    it('publishes CollectionPage with tri-ethnic cultural About node and etiquette FAQ', () => {
      const festival = doc('pages/le-hoi.vue')
      expect(festival).toContain('buildWebSiteSchema()')
      expect(festival).toContain('buildOrganizationSchema()')
      expect(festival).toContain('buildSpeakableSpecification')
      expect(festival).toContain('buildFaqPageSchema')
      expect(festival).toContain("name: 'Lễ hội truyền thống Vĩnh Long'")
    })
  })

  describe('Routes Travel Knowledge Graph (pages/tuyen-duong.vue)', () => {
    it('publishes CollectionPage with route ItemList, road-trip Speakable, and transit FAQ', () => {
      const routes = doc('pages/tuyen-duong.vue')
      expect(routes).toContain('buildWebSiteSchema()')
      expect(routes).toContain('buildOrganizationSchema()')
      expect(routes).toContain('buildSpeakableSpecification')
      expect(routes).toContain('buildFaqPageSchema')
      expect(routes).toContain("name: 'Tuyến đường gợi ý Vĩnh Long'")
      expect(routes).toContain("name: 'Lộ trình du lịch Vĩnh Long'")
    })
  })

  describe('Perpetual Calendar Astronomical Utility (pages/lich-van-nien.vue)', () => {
    it('publishes WebApplication schema with astronomical Speakable and computation FAQ', () => {
      const lvn = doc('pages/lich-van-nien.vue')
      expect(lvn).toContain('buildWebSiteSchema()')
      expect(lvn).toContain('buildOrganizationSchema()')
      expect(lvn).toContain('buildSpeakableSpecification')
      expect(lvn).toContain('buildFaqPageSchema')
      expect(lvn).toContain("'@type': 'WebApplication'")
      expect(lvn).toContain('safeJsonLd(lvnSchema.value)')
    })
  })

  describe('Regional Area Knowledge Graph (pages/khu-vuc/[area].vue)', () => {
    it('publishes AdministrativeArea with WebPage, Speakable, and regional FAQ', () => {
      const area = doc('pages/khu-vuc/[area].vue')
      expect(area).toContain('buildWebSiteSchema()')
      expect(area).toContain('buildOrganizationSchema()')
      expect(area).toContain('buildSpeakableSpecification')
      expect(area).toContain('buildFaqPageSchema')
      expect(area).toContain("'@type': 'AdministrativeArea'")
      expect(area).toContain("name: 'Tỉnh Vĩnh Long'")
      expect(area).toContain("safeJsonLd({")
    })
  })

  describe('Tourism Hub Knowledge Graph (pages/du-lich.vue)', () => {
    it('publishes CollectionPage with about Tourism, Speakable, and itinerary FAQ', () => {
      const tourism = doc('pages/du-lich.vue')
      expect(tourism).toContain('buildWebSiteSchema()')
      expect(tourism).toContain('buildOrganizationSchema()')
      expect(tourism).toContain('buildSpeakableSpecification')
      expect(tourism).toContain('buildFaqPageSchema')
      expect(tourism).toContain("name: 'Du lịch Vĩnh Long'")
      expect(tourism).toContain("safeJsonLd({")
    })
  })

  describe('Lodging Hub Knowledge Graph (pages/luu-tru.vue)', () => {
    it('publishes CollectionPage with about Lodging, Speakable, and homestay FAQ', () => {
      const lodging = doc('pages/luu-tru.vue')
      expect(lodging).toContain('buildWebSiteSchema()')
      expect(lodging).toContain('buildOrganizationSchema()')
      expect(lodging).toContain('buildSpeakableSpecification')
      expect(lodging).toContain('buildFaqPageSchema')
      expect(lodging).toContain("name: 'Lưu trú Vĩnh Long'")
      expect(lodging).toContain("safeJsonLd({")
    })
  })

  describe('Product Catalog Knowledge Graph (pages/san-pham.vue)', () => {
    it('publishes CollectionPage with about Products, Speakable, and gift FAQ', () => {
      const product = doc('pages/san-pham.vue')
      expect(product).toContain('buildWebSiteSchema()')
      expect(product).toContain('buildOrganizationSchema()')
      expect(product).toContain('buildSpeakableSpecification')
      expect(product).toContain('buildFaqPageSchema')
      expect(product).toContain("name: 'Sản phẩm địa phương Vĩnh Long'")
      expect(product).toContain("safeJsonLd({")
    })
  })

  describe('Seasonal Almanac Knowledge Graph (pages/theo-mua.vue)', () => {
    it('publishes CollectionPage with about Seasonal crops, Speakable, and harvest FAQ', () => {
      const season = doc('pages/theo-mua.vue')
      expect(season).toContain('buildWebSiteSchema()')
      expect(season).toContain('buildOrganizationSchema()')
      expect(season).toContain('buildSpeakableSpecification')
      expect(season).toContain('buildFaqPageSchema')
      expect(season).toContain("name: 'Lịch mùa vụ nông sản và du lịch Vĩnh Long'")
      expect(season).toContain("safeJsonLd({")
    })
  })

  describe('Events Hub Knowledge Graph (pages/su-kien.vue)', () => {
    it('publishes CollectionPage with about Events, Speakable, and cultural fair FAQ', () => {
      const events = doc('pages/su-kien.vue')
      expect(events).toContain('buildWebSiteSchema()')
      expect(events).toContain('buildOrganizationSchema()')
      expect(events).toContain('buildSpeakableSpecification')
      expect(events).toContain('buildFaqPageSchema')
      expect(events).toContain("name: 'Sự kiện & Hội chợ Vĩnh Long'")
      expect(events).toContain("safeJsonLd({")
    })
  })
})
