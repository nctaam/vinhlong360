import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import PlannerRiverTransitWarning from '../components/planner/PlannerRiverTransitWarning.vue'
import PlannerMobilePassModal from '../components/planner/PlannerMobilePassModal.vue'
import { buildItineraryDetailSchemaGraph, buildEntityDetailSchemaGraph } from '../composables/useSeoHelpers'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

describe('Milestone 138: Smart Itinerary Planning & Full SEO/GEO Knowledge Graph', () => {
  const root = resolve(process.cwd())

  describe('PlannerRiverTransitWarning & Mekong River Navigation', () => {
    const mockStops = [
      { id: 'ben-tau-vinh-long', name: 'Bến Tàu Du Lịch Vĩnh Long', place_area: 'vinh-long' },
      { id: 'vuon-an-binh', name: 'Nhà Vườn Cù Lao An Bình', place_area: 'an-binh' },
      { id: 'lo-gom-mang-thit', name: 'Lò Gốm Thầy Cai', place_area: 'mang-thit' },
    ]

    it('warns about ferry schedules, Thầy Cai waterway, and lunar tide peaks', async () => {
      const wrapper = await mountSuspended(PlannerRiverTransitWarning, {
        props: { stops: mockStops },
        global: { stubs: { IconLine: true } },
      })
      wrappers.push(wrapper)

      expect(wrapper.find('[data-planner-river-transit]').exists()).toBe(true)
      expect(wrapper.text()).toContain('Lưu ý đò phà & nhịp sông nước thực địa')
      expect(wrapper.text()).toContain('Phà An Bình')
      expect(wrapper.text()).toContain('kênh Thầy Cai')
      expect(wrapper.text()).toContain('triều cường')
      expect(wrapper.text()).toContain('tiền mặt lẻ')
    })
  })

  describe('PlannerMobilePassModal & Offline Boarding Pass', () => {
    const mockStops = [
      { id: 's1', name: 'Chùa Ông Thất Phủ Miếu', place_name: 'Phường 1' },
      { id: 's2', name: 'Văn Thánh Miếu', place_name: 'Phường 4' },
    ]

    it('renders offline-capable mobile boarding pass with emergency helpline', async () => {
      const wrapper = await mountSuspended(PlannerMobilePassModal, {
        props: {
          open: true,
          title: 'Hành trình Văn hóa & Di sản',
          stops: mockStops,
        },
        global: { stubs: { IconLine: true } },
      })
      wrappers.push(wrapper)

      expect(wrapper.text()).toContain('Thẻ hành trình thực địa')
      expect(wrapper.text()).toContain('Khả dụng ngoại tuyến')
      expect(wrapper.text()).toContain('0270 3822 188')
      expect(wrapper.text()).toContain('In hoặc Lưu PDF')
      expect(wrapper.text()).toContain('Chùa Ông Thất Phủ Miếu')
      expect(wrapper.text()).toContain('Văn Thánh Miếu')
    })

    it('adheres to purpose-based radius tokens and zero raw hex', () => {
      const src = readFileSync(resolve(root, 'components/planner/PlannerMobilePassModal.vue'), 'utf8')
      expect(src).not.toContain('--radius-base')
      expect(src).not.toContain('--radius-full')
      expect(src).toContain('--radius-pill, 999px')
      expect(src).toContain('--radius-surface, 12px')

      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}/g
      expect(src.match(rawHexPattern) || []).toEqual([])
    })

    it('keeps pages/tao-lich-trinh.vue strictly below 1.500 line ceiling', () => {
      const src = readFileSync(resolve(root, 'pages/tao-lich-trinh.vue'), 'utf8')
      const lineCount = src.split('\n').length
      expect(lineCount).toBeLessThan(1500)
    })
  })

  describe('SEO/AEO/GEO Linked Knowledge Graph (useSeoHelpers.ts)', () => {
    it('generates TouristTrip schema with geographic spatialCoverage and speakable selectors', () => {
      const graph = buildItineraryDetailSchemaGraph({
        itinerary: {
          id: 'itin-mot-ngay-an-binh',
          title: 'Một ngày xanh ngắt cù lao An Bình',
          duration: '1 ngày',
          stops: [
            { id: 'stop-1', name: 'Phà An Bình' },
            { id: 'stop-2', name: 'Vườn chôm chôm' },
          ],
        },
        itineraryTitle: 'Một ngày xanh ngắt cù lao An Bình',
        itineraryUrl: 'https://vinhlong360.vn/lich-trinh/itin-mot-ngay-an-binh',
      })

      const nodes = graph['@graph'] as any[]
      const trip = nodes.find(n => n['@type'] === 'TouristTrip')
      expect(trip).toBeDefined()
      expect(trip.spatialCoverage).toBeDefined()
      expect(trip.spatialCoverage.name).toBe('Tỉnh Vĩnh Long')
      expect(trip.spatialCoverage.geo.box).toBe('9.8 105.8 10.4 106.7')

      const webpage = nodes.find(n => n['@type'] === 'WebPage')
      expect(webpage.speakable).toBeDefined()
      expect(webpage.speakable.cssSelector).toContain('.step-note-callout')
      expect(webpage.speakable.cssSelector).toContain('.step-card strong')
    })

    it('enriches OCOP entities with award and category schema', () => {
      const entityGraph = buildEntityDetailSchemaGraph({
        entity: {
          id: 'buoi-nam-roi-hoang-gia',
          name: 'Bưởi Năm Roi Hoàng Gia',
          type: 'product',
          attributes: {
            ocop: 'OCOP 4 sao',
            ocop_star: 4,
            price: '85000',
          },
          quality: {
            source_url: 'https://snnptnt.vinhlong.gov.vn/ocop',
            source_title: 'Sở NN&PTNT tỉnh Vĩnh Long',
          },
        },
      })

      const nodes = entityGraph?.['@graph'] as any[]
      const product = nodes.find(n => n['@type'] === 'Product')
      expect(product).toBeDefined()
      expect(product.award).toBe('OCOP 4 sao')
      expect(product.category).toBe('Sản phẩm OCOP')
      expect(product.citation).toBeDefined()
      expect(product.citation.url).toBe('https://snnptnt.vinhlong.gov.vn/ocop')
    })
  })
})
