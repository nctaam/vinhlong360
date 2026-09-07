import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import DetailAeoSummary from '../components/DetailAeoSummary.vue'
import WardTerroirDigest from '../components/ward/WardTerroirDigest.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

describe('Milestone 137: Field Discovery, Map Ergonomics & Local Terroir Digest', () => {
  const root = resolve(process.cwd())

  describe('DetailAeoSummary & Destination Field Digest', () => {
    const mockEntity: any = {
      id: 'vuon-trai-cay-an-binh',
      name: 'Vườn Trái Cây Cù Lao An Bình',
      type: 'experience',
      place_area: 'an-binh',
      description: 'Miệt vườn chôm chôm, nhãn xuồng trĩu quả giữa bốn bề sông Cổ Chiên.',
      attributes: {
        highlight: 'Trải nghiệm hái trái tại cây và chèo xuồng ba lá ven rạch.',
        best_time: 'Sáng sớm 7h00 - 10h00',
        transport: 'Qua phà An Bình, đi đường đan 2km',
        suggested_duration: '3 giờ',
        price: '50.000đ/người',
        local_tip: 'Nên mang dép bệt chống trơn khi vào vườn sau cơn mưa nhỏ.',
      },
    }

    it('renders field verification stamp and river tide cue', async () => {
      const wrapper = await mountSuspended(DetailAeoSummary, {
        props: { entity: mockEntity, accent: 'river' },
        global: { stubs: { IconLine: true } },
      })
      wrappers.push(wrapper)

      expect(wrapper.find('.detail-aeo-summary__stamp').exists()).toBe(true)
      expect(wrapper.text()).toContain('Xác thực thực địa bản xứ')
      expect(wrapper.text()).toContain('Thủy triều sông Cổ Chiên')
      expect(wrapper.attributes('data-material-accent')).toBe('river')
      expect(wrapper.text()).toContain('Trải nghiệm hái trái tại cây')
      expect(wrapper.text()).toContain('50.000đ/người')
    })

    it('adheres to purpose-based radius and zero color debt', () => {
      const src = readFileSync(resolve(root, 'components/DetailAeoSummary.vue'), 'utf8')
      expect(src).not.toContain('--radius-base')
      expect(src).not.toContain('--radius-full')
      expect(src).toContain('--radius-pill, 999px')
      expect(src).toContain('--radius-surface, 12px')

      // Zero raw hex
      const rawHexPattern = /(?<![&w-])#[0-9a-fA-F]{3,8}/g
      expect(src.match(rawHexPattern) || []).toEqual([])
    })

    it('keeps pages/dia-diem/[id].vue strictly below 1.200 line ceiling', () => {
      const src = readFileSync(resolve(root, 'pages/dia-diem/[id].vue'), 'utf8')
      const lineCount = src.split('\n').length
      expect(lineCount).toBeLessThan(1200)
    })

    it('detail primary action provides >= 48px min-height for mobile thumb-zone', () => {
      const css = readFileSync(resolve(root, 'assets/css/detail.css'), 'utf8')
      expect(css).toMatch(/\.detail-primary-action\s*\{[^}]*min-height:\s*48px/)
      expect(css).toContain('cubic-bezier(0.16, 1, 0.3, 1)')
    })
  })

  describe('Bản Đồ Số Thực Địa (pages/ban-do.vue)', () => {
    it('provides "Bến phà & Đò ngang" quick filter preset with enhanced ferry matching', () => {
      const src = readFileSync(resolve(root, 'pages/ban-do.vue'), 'utf8')
      expect(src).toContain("label: 'Bến phà & Đò ngang'")
      expect(src).toContain("icon: 'compass'")
      expect(src).toContain("activeWaterPreset.value === 'ferry'")
      expect(src).toContain('cổ chiên')
      expect(src).toContain('sông tiền')
    })

    it('implements Outdoor High-Legibility Mode with high-contrast borders and tactile ease', () => {
      const src = readFileSync(resolve(root, 'pages/ban-do.vue'), 'utf8')
      expect(src).toContain('data-outdoor-contrast="high"')
      expect(src).toContain('border: 2px solid var(--color-brand)')
      expect(src).toContain('--radius-pill, 999px')
      expect(src).not.toContain('--radius-full')
      expect(src).toContain('cubic-bezier(0.16, 1, 0.3, 1)')
    })
  })

  describe('WardTerroirDigest & Xã/Phường Bản Xứ', () => {
    const mockPlace = {
      id: 'xa-binh-hoa-phuoc',
      name: 'Xã Bình Hòa Phước',
      area: 'long-ho',
      level: 'xa',
      attributes: {
        phone: '02703859111',
        police_phone: '02703859113',
      },
    }

    it('renders agricultural season tags and local verification stamp', async () => {
      const wrapper = await mountSuspended(WardTerroirDigest, {
        props: { place: mockPlace },
        global: { stubs: { IconLine: true } },
      })
      wrappers.push(wrapper)

      expect(wrapper.find('.ward-terroir-digest__stamp').exists()).toBe(true)
      expect(wrapper.text()).toContain('Xác thực thực địa bản xứ')
      expect(wrapper.text()).toContain('Chôm chôm Bình Hòa Phước')
      expect(wrapper.text()).toContain('Rộ tháng 5 – 7 âm lịch')
    })

    it('enforces telemetry contract with outcome="navigation" on phone actions', async () => {
      const wrapper = await mountSuspended(WardTerroirDigest, {
        props: { place: mockPlace },
        global: { stubs: { IconLine: true } },
      })
      wrappers.push(wrapper)

      const callBtns = wrapper.findAll('.ward-terroir-digest__call-btn')
      expect(callBtns.length).toBeGreaterThanOrEqual(3)
      for (const btn of callBtns) {
        expect(btn.attributes('data-contact-action')).toBe('phone')
        expect(btn.attributes('data-contact-surface')).toBe('ward-detail')
        expect(btn.attributes('data-contact-outcome')).toBe('navigation')
        expect(btn.attributes('data-contact-entity-id')).toBeTruthy()
      }
    })

    it('keeps pages/xa-phuong/[id].vue strictly below 1.050 line ceiling', () => {
      const src = readFileSync(resolve(root, 'pages/xa-phuong/[id].vue'), 'utf8')
      const lineCount = src.split('\n').length
      expect(lineCount).toBeLessThan(1050)
    })
  })
})
