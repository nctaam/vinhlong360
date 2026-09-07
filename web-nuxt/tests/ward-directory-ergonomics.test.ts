import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import WardTerroirDigest from '../components/ward/WardTerroirDigest.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mountDigest(props: any) {
  const wrapper = await mountSuspended(WardTerroirDigest, {
    props,
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

function readPage(relPath: string): string {
  return readFileSync(resolve(__dirname, '..', relPath), 'utf8')
}

describe('WardTerroirDigest & 24/7 Emergency Directory Ergonomics (Moc 127)', () => {
  describe('WardTerroirDigest component', () => {
    it('renders Cu Lao terroir specialties and island ferry transit advisories for An Binh', async () => {
      const place = {
        id: 'ward-an-binh',
        name: 'Xã An Bình',
        area: 'long-ho',
        attributes: {
          police_phone: '0270 3858 113',
        },
      }

      const wrapper = await mountDigest({ place })
      expect(wrapper.find('[data-ward-terroir-digest]').exists()).toBe(true)
      expect(wrapper.text()).toContain('Chôm chôm Bình Hòa Phước')
      expect(wrapper.text()).toContain('Nhãn xuồng cơm vàng Cù lao')
      expect(wrapper.text()).toContain('Sông nước & Cù lao')
      expect(wrapper.text()).toContain('phà An Bình')
      expect(wrapper.text()).toContain('0270 3858 113')
      expect(wrapper.find('a[href="tel:02703858113"]').exists()).toBe(true)
    })

    it('renders red pottery heritage and Thay Cai canal route advisories for Mang Thit', async () => {
      const place = {
        id: 'ward-nhon-phu',
        name: 'Xã Nhơn Phú',
        area: 'mang-thit',
      }

      const wrapper = await mountDigest({ place })
      expect(wrapper.text()).toContain('Gốm đỏ Di sản Đương đại')
      expect(wrapper.text()).toContain('Dọc Kênh Thầy Cai')
      expect(wrapper.text()).toContain('ĐT 902')
    })

    it('renders Nam Roi Pomelo PGI and My Hoa tofu skin craft for Binh Minh', async () => {
      const place = {
        id: 'ward-my-hoa',
        name: 'Xã Mỹ Hòa',
        area: 'binh-minh',
      }

      const wrapper = await mountDigest({ place })
      expect(wrapper.text()).toContain('Bưởi Năm Roi Hoàng Gia')
      expect(wrapper.text()).toContain('Chỉ dẫn PGI')
      expect(wrapper.text()).toContain('Tàu hũ ky làng nghề Mỹ Hòa')
      expect(wrapper.text()).toContain('Di sản Quốc gia')
      expect(wrapper.text()).toContain('Cầu Cần Thơ')
    })
  })

  describe('Integration in pages/xa-phuong/[id].vue', () => {
    it('integrates WardTerroirDigest with place data and respects line ceiling', () => {
      const src = readPage('pages/xa-phuong/[id].vue')
      expect(src).toContain('<WardTerroirDigest :place="data.place"')
      const lineCount = src.split('\n').length
      expect(lineCount).toBeLessThan(1050)
    })
  })

  describe('Integration in pages/danh-ba.vue (24/7 Tourism Rescue)', () => {
    it('renders 24/7 tourism rescue section with vital contact hotlines', () => {
      const src = readPage('pages/danh-ba.vue')
      expect(src).toContain('data-dir-emergency')
      expect(src).toContain('Cứu hộ Du lịch &amp; Hotline Khẩn cấp 24/7')
      expect(src).toContain('CSGT & Cứu nạn Đường thủy')
      expect(src).toContain('0270 3822 305')
      expect(src).toContain('115')
      expect(src).toContain('113')
      expect(src).toContain('Phà An Bình')
      expect(src).toContain('0270 3822 514')
      expect(src).toContain('0270 3822 188')
    })

    it('provides accessible direct calling links for emergency hotlines', () => {
      const src = readPage('pages/danh-ba.vue')
      expect(src).toContain('data-contact-action="phone"')
      expect(src).toContain('data-contact-surface="directory-emergency"')
      expect(src).toContain(':aria-label="`Gọi trực tiếp ${item.name}: ${item.phone}`"')
    })
  })

  describe('Design Token & Color Compliance', () => {
    it('has zero raw hex colors across all modified and new templates', () => {
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g

      const files = [
        'components/ward/WardTerroirDigest.vue',
        'pages/xa-phuong/[id].vue',
        'pages/danh-ba.vue',
      ]

      for (const f of files) {
        const src = readPage(f)
        const styleMatches = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)]
        for (const m of styleMatches) {
          const hexes = m[1].match(rawHexPattern) || []
          expect(hexes, `Found raw hex in ${f}`).toEqual([])
        }
      }
    })
  })
})
