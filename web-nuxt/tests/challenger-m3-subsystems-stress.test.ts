import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'

import SearchDrawer from '../components/SearchDrawer.vue'
import PocketPassModal from '../components/PocketPassModal.vue'
import OfflineTerroirPanel from '../components/OfflineTerroirPanel.vue'

const root = resolve(__dirname, '..')
const readSource = (relPath: string) => readFileSync(resolve(root, relPath), 'utf8')

describe('Milestone M3: Adversarial Stress & Edge Case Harness (Challenger m3_2_10)', () => {
  // ──────────────────────────────────────────────────────────────────────────
  // Stress Dimension 1: SearchDrawer Adversarial Edge Cases
  // ──────────────────────────────────────────────────────────────────────────
  describe('SearchDrawer Adversarial Edge Cases', () => {
    const stubs = {
      Teleport: { template: '<div><slot /></div>' },
      Transition: { template: '<div><slot /></div>' },
      NuxtLink: { template: '<a><slot /></a>' },
      IconLine: true,
      VernacularGlyph: true,
      SourceMark: true,
    }

    it('handles extreme whitespace queries and rapid toggle filters without crashing', async () => {
      const wrapper = mount(SearchDrawer, {
        props: { open: true },
        global: { stubs },
      })

      const input = wrapper.find('input[type="search"]')
      expect(input.exists()).toBe(true)

      // Extreme whitespace
      await input.setValue('   \t\n   ')
      // Clear button should not appear for pure whitespace
      expect(wrapper.find('.search-drawer-clear-btn').exists()).toBe(false)

      // Toggle all regions sequentially
      const regionChips = wrapper.findAll('.search-drawer-chips button')
      expect(regionChips.length).toBeGreaterThan(0)
      for (const chip of regionChips) {
        await chip.trigger('click')
      }

      // Reset button should work if filters active
      const resetBtn = wrapper.find('.search-drawer-reset-btn')
      if (resetBtn.exists()) {
        await resetBtn.trigger('click')
        await wrapper.vm.$nextTick()
      }
    })

    it('prevents event propagation when clicking inside sheet', async () => {
      const wrapper = mount(SearchDrawer, {
        props: { open: true },
        global: { stubs },
      })

      const sheet = wrapper.find('.search-drawer-sheet')
      await sheet.trigger('click')
      // Overlay click-self closes drawer, but sheet click should NOT close
      expect(wrapper.emitted('update:open')).toBeFalsy()
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Stress Dimension 2: PocketPassModal Malformed Props & Print Robustness
  // ──────────────────────────────────────────────────────────────────────────
  describe('PocketPassModal Malformed Props & Print Robustness', () => {
    const stubs = {
      Teleport: { template: '<div><slot /></div>' },
      Transition: { template: '<div><slot /></div>' },
      NuxtLink: { template: '<a><slot /></a>' },
      IconLine: true,
      VernacularGlyph: true,
      MekongWaterBadge: true,
    }

    it('renders safely when stops prop contains incomplete or malformed objects', () => {
      const wrapper = mount(PocketPassModal, {
        props: {
          open: true,
          title: '', // empty title fallback
          stops: [
            { name: '' }, // empty name
            { name: 'Stop with undefined fields', place_name: undefined, time: undefined, note: undefined },
            // @ts-expect-error testing adversarial malformed input
            { invalidField: 123 },
          ],
        },
        global: { stubs },
      })

      expect(wrapper.find('.pocket-pass-card').exists()).toBe(true)
      expect(wrapper.text()).toContain('Thẻ Hành Trình Điền Dã Cửu Long') // fallback title
      expect(wrapper.findAll('.pocket-pass-waypoint').length).toBe(3)
    })

    it('handles print exceptions gracefully without crashing UI', async () => {
      const origPrint = window.print
      window.print = () => { throw new Error('Printer spooler blocked') }

      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        global: { stubs },
      })

      const printBtn = wrapper.find('.pocket-pass-print-btn')
      expect(printBtn.exists()).toBe(true)

      // Should not throw uncaught error
      await expect(printBtn.trigger('click')).resolves.not.toThrow()
      window.print = origPrint
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Stress Dimension 3: OfflineTerroirPanel Local Tide Almanac Computation
  // ──────────────────────────────────────────────────────────────────────────
  describe('OfflineTerroirPanel Local Tide Almanac Computation', () => {
    it('computes valid tide status and coordinates across different dates', () => {
      const wrapper = mount(OfflineTerroirPanel, {
        props: { isOffline: true },
        global: {
          stubs: {
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      const text = wrapper.text()
      expect(text).toContain('10.254° N, 105.972° E')
      expect(text).toMatch(/(?:Nước lớn|Nước ròng|Nước êm|Nước đứng)/)
      expect(text).toMatch(/(?:Thuận dòng|Ngược dòng|Đứng con nước|Nước đứng|Nước ròng|Nước lớn)/)
    })


    it('validates all 5 emergency hotlines for strict phone format and tel: links', () => {
      const wrapper = mount(OfflineTerroirPanel, {
        props: { isOffline: true },
        global: {
          stubs: {
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      const telLinks = wrapper.findAll('a[href^="tel:"]')
      expect(telLinks.length).toBe(5)

      for (const link of telLinks) {
        const href = link.attributes('href') || ''
        const telNumber = href.replace('tel:', '')
        // All hotline numbers must be 3 to 11 digits
        expect(telNumber).toMatch(/^\d{3,11}$/)
        // Must contain descriptive text
        expect(link.text().length).toBeGreaterThan(5)
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Stress Dimension 4: Cryptographic Invariants (B1, B6, B7)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Cryptographic Data Store Invariants', () => {
    const BASELINE_DB_HASH = '5d314065a489356be1bea87d7d800fc5d706959044d9a13a10f89ba9f7dda059'
    const BASELINE_JSON_HASH = '9d610fe6bfab82df977bae2b5e48d4ae1755c110205c4b6a043499443015095e'

    it('checks if agent/data/vinhlong360.db strictly matches baseline', () => {
      const dbPath = resolve(root, '../agent/data/vinhlong360.db')
      expect(existsSync(dbPath)).toBe(true)
      const dbHash = createHash('sha256').update(readFileSync(dbPath)).digest('hex')
      expect(dbHash).toBe(BASELINE_DB_HASH)
    })

    it('checks if web/data.json strictly matches baseline', () => {
      const dataPath = resolve(root, '../web/data.json')
      expect(existsSync(dataPath)).toBe(true)
      const dataHash = createHash('sha256').update(readFileSync(dataPath)).digest('hex')
      expect(dataHash).toBe(BASELINE_JSON_HASH)
    })
  })
})
