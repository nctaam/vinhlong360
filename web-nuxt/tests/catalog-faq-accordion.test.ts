import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  TOURISM_CATALOG_FAQS,
  PRODUCT_CATALOG_FAQS,
  STAY_CATALOG_FAQS,
  EVENT_CATALOG_FAQS,
  buildTourismCatalogSchemaGraph,
  buildProductCatalogSchemaGraph,
  buildStayCatalogSchemaGraph,
  buildContemporaryEventSchemaGraph,
} from '../composables/useSeoHelpers'

function readSource(relPath: string) {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('CatalogFaqAccordion & Structured FAQ Surface (Moc 151)', () => {
  it('CatalogFaqAccordion component has accessible semantic markup with details/summary and token styling', () => {
    const component = readSource('components/CatalogFaqAccordion.vue')
    expect(component).toContain('<details')
    expect(component).toContain('<summary class="catalog-faq-summary">')
    expect(component).toContain('<IconLine name="chevron-down"')
    expect(component).toContain('aria-labelledby="catalog-faq-title"')
    expect(component).toContain('class="catalog-faq-answer"')
    expect(component).not.toContain('#')
    expect(component).toContain('var(--card)')
    expect(component).toContain('var(--ink)')
    expect(component).toContain('var(--line)')
  })

  it('exports valid FAQ sets for all four major catalog verticals', () => {
    expect(TOURISM_CATALOG_FAQS.length).toBeGreaterThanOrEqual(3)
    expect(PRODUCT_CATALOG_FAQS.length).toBeGreaterThanOrEqual(3)
    expect(STAY_CATALOG_FAQS.length).toBeGreaterThanOrEqual(3)
    expect(EVENT_CATALOG_FAQS.length).toBeGreaterThanOrEqual(3)

    for (const faq of [...TOURISM_CATALOG_FAQS, ...PRODUCT_CATALOG_FAQS, ...STAY_CATALOG_FAQS, ...EVENT_CATALOG_FAQS]) {
      expect(faq.q).toBeTruthy()
      expect(faq.a).toBeTruthy()
      expect(faq.q.endsWith('?')).toBe(true)
    }
  })

  it('Schema graphs include FAQPage with matching questions and answers', () => {
    const tourismGraph = buildTourismCatalogSchemaGraph({ items: [] })
    const tourismFaq = tourismGraph['@graph'].find((n: any) => n['@type'] === 'FAQPage')
    expect(tourismFaq).toBeDefined()
    expect(tourismFaq.mainEntity).toHaveLength(TOURISM_CATALOG_FAQS.length)
    expect(tourismFaq.mainEntity[0].name).toBe(TOURISM_CATALOG_FAQS[0].q)
    expect(tourismFaq.mainEntity[0].acceptedAnswer.text).toBe(TOURISM_CATALOG_FAQS[0].a)

    const productGraph = buildProductCatalogSchemaGraph({ items: [] })
    const productFaq = productGraph['@graph'].find((n: any) => n['@type'] === 'FAQPage')
    expect(productFaq).toBeDefined()
    expect(productFaq.mainEntity).toHaveLength(PRODUCT_CATALOG_FAQS.length)
    expect(productFaq.mainEntity[0].name).toBe(PRODUCT_CATALOG_FAQS[0].q)

    const stayGraph = buildStayCatalogSchemaGraph({ items: [] })
    const stayFaq = stayGraph['@graph'].find((n: any) => n['@type'] === 'FAQPage')
    expect(stayFaq).toBeDefined()
    expect(stayFaq.mainEntity).toHaveLength(STAY_CATALOG_FAQS.length)
    expect(stayFaq.mainEntity[0].name).toBe(STAY_CATALOG_FAQS[0].q)

    const eventGraph = buildContemporaryEventSchemaGraph({ events: [] })
    const eventFaq = eventGraph['@graph'].find((n: any) => n['@type'] === 'FAQPage')
    expect(eventFaq).toBeDefined()
    expect(eventFaq.mainEntity).toHaveLength(EVENT_CATALOG_FAQS.length)
    expect(eventFaq.mainEntity[0].name).toBe(EVENT_CATALOG_FAQS[0].q)
  })

  it('four key catalog pages visually render CatalogFaqAccordion with their domain FAQs', () => {
    const tourism = readSource('pages/du-lich.vue')
    expect(tourism).toContain('<CatalogFaqAccordion')
    expect(tourism).toContain(':items="TOURISM_CATALOG_FAQS"')
    expect(tourism).toContain('TOURISM_CATALOG_FAQS')

    const product = readSource('pages/san-pham.vue')
    expect(product).toContain('<CatalogFaqAccordion')
    expect(product).toContain(':items="PRODUCT_CATALOG_FAQS"')
    expect(product).toContain('PRODUCT_CATALOG_FAQS')

    const stay = readSource('pages/luu-tru.vue')
    expect(stay).toContain('<CatalogFaqAccordion')
    expect(stay).toContain(':items="STAY_CATALOG_FAQS"')
    expect(stay).toContain('STAY_CATALOG_FAQS')

    const event = readSource('pages/su-kien.vue')
    expect(event).toContain('<CatalogFaqAccordion')
    expect(event).toContain(':items="EVENT_CATALOG_FAQS"')
    expect(event).toContain('EVENT_CATALOG_FAQS')
  })
})
