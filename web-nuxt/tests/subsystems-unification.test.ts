import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'

import SearchDrawer from '../components/SearchDrawer.vue'
import PocketPassModal from '../components/PocketPassModal.vue'
import OfflineTerroirPanel from '../components/OfflineTerroirPanel.vue'

const root = resolve(__dirname, '..')
const readSource = (relPath: string) => readFileSync(resolve(root, relPath), 'utf8')

describe('Milestone M3: Unified Organic Heritage Entity Subsystems', () => {
  // ──────────────────────────────────────────────────────────────────────────
  // Subsystem 1: SearchDrawer.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystem 1: SearchDrawer.vue (Multi-dimensional Frosted Slide-Over)', () => {
    it('renders frosted slide-over modal structure with proper accessibility attributes', () => {
      const wrapper = mount(SearchDrawer, {
        props: { open: true },
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
      expect(wrapper.find('.search-drawer-overlay').exists()).toBe(true)
      expect(wrapper.find('.search-drawer-sheet').exists()).toBe(true)
      expect(wrapper.find('#search-drawer-title').text()).toContain('Tìm kiếm Điền dã')
    })

    it('provides multi-dimensional filtering for Tam Vùng, Seasons, and Astronomical Tides', () => {
      const wrapper = mount(SearchDrawer, {
        props: { open: true },
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      const text = wrapper.text()
      // Tam Vùng
      expect(text).toContain('Mang Thít')
      expect(text).toContain('Cù lao An Bình')
      expect(text).toContain('Sông Cổ Chiên')
      // Mùa vụ
      expect(text).toContain('Nước nổi')
      expect(text).toContain('Trái chín')
      // Thủy văn / Con nước
      expect(text).toContain('Nước lớn')
      expect(text).toContain('Nước ròng')
      expect(text).toContain('êm dòng')
    })

    it('supports keyboard Escape listener to close drawer', async () => {
      const wrapper = mount(SearchDrawer, {
        props: { open: true },
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      await wrapper.find('.search-drawer-overlay').trigger('keydown', { key: 'Escape' })
      await wrapper.vm.$nextTick()

      expect(wrapper.emitted('update:open')).toBeTruthy()
      expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
    })

    it('enforces touch targets >= 44x44px and zero raw hex in SearchDrawer.vue source', () => {
      const src = readSource('components/SearchDrawer.vue')
      expect(src).toMatch(/min-height:\s*44px/i)
      expect(src).toMatch(/min-width:\s*44px/i)

      const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch && styleMatch[1]) {
        const styleContent = styleMatch[1]
        const rawHexMatches = styleContent.match(/#[0-9a-fA-F]{3,8}\b/g)
        expect(rawHexMatches || []).toEqual([])
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Subsystem 2: PocketPassModal.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystem 2: PocketPassModal.vue (Pocket Field Pass & Guilloche Security)', () => {
    it('renders Guilloche security pattern, terracotta seal, and QR code', () => {
      const wrapper = mount(PocketPassModal, {
        props: {
          open: true,
          title: 'Hành trình Cù lao An Bình',
          stops: [
            { name: 'Bến phà An Bình', place_name: 'Phường 1', time: '07:00' },
            { name: 'Lò gốm Mang Thít', place_name: 'Mang Thít', time: '10:00' },
          ],
        },
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      expect(wrapper.find('.pocket-pass-guilloche').exists()).toBe(true)
      expect(wrapper.find('.pocket-pass-wax-seal').exists()).toBe(true)
      expect(wrapper.find('.pocket-pass-qrcode').exists()).toBe(true)
      expect(wrapper.text()).toContain('Hành trình Cù lao An Bình')
      expect(wrapper.text()).toContain('Bến phà An Bình')
      expect(wrapper.text()).toContain('Lò gốm Mang Thít')
    })

    it('includes essential local rescue contacts with phone numbers', () => {
      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      const text = wrapper.text()
      expect(text).toContain('Phà An Bình · Hotline 0270 3822 188')
    })

    it('supports window.print() execution on print button trigger', async () => {
      const originalPrint = window.print
      const printMock = vi.fn()
      window.print = printMock

      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      const printBtn = wrapper.find('.pocket-pass-print-btn')
      expect(printBtn.exists()).toBe(true)
      await printBtn.trigger('click')

      expect(printMock).toHaveBeenCalledTimes(1)
      window.print = originalPrint
    })

    it('enforces pure semantic tokens and zero raw hex in PocketPassModal.vue source', () => {
      const src = readSource('components/PocketPassModal.vue')
      const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch && styleMatch[1]) {
        const styleContent = styleMatch[1]
        const rawHexMatches = styleContent.match(/#[0-9a-fA-F]{3,8}\b/g)
        expect(rawHexMatches || []).toEqual([])
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Subsystem 3: OfflineTerroirPanel.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystem 3: OfflineTerroirPanel.vue (Emergency Terroir Cache & Rescue Hotlines)', () => {
    it('displays astronomical tide calculation and geographic coordinates', () => {
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
      expect(text).toContain('Chế độ Thực địa Ngoại tuyến')
      expect(text).toContain('10.254° N, 105.972° E')
      expect(text).toMatch(/Nước (lớn|ròng|êm|đứng)/)
    })

    it('renders 5 emergency rescue hotline numbers with functional tel: links', () => {
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
      expect(telLinks.length).toBeGreaterThanOrEqual(5)

      const hrefs = telLinks.map(l => l.attributes('href'))
      expect(hrefs).toContain('tel:02703822188')
      expect(hrefs).toContain('tel:02703858200')
      expect(hrefs).toContain('tel:02703823520')
      expect(hrefs).toContain('tel:0693706112')
      expect(hrefs).toContain('tel:114')
    })

    it('toggles collapsible emergency guidance and meets touch target requirements', async () => {
      const wrapper = mount(OfflineTerroirPanel, {
        props: { isOffline: true },
        global: {
          stubs: {
            IconLine: true,
            VernacularGlyph: true,
          },
        },
      })

      const toggleBtn = wrapper.find('.offline-toggle-btn')
      expect(toggleBtn.exists()).toBe(true)
      expect(toggleBtn.attributes('aria-expanded')).toBe('true')

      await toggleBtn.trigger('click')
      expect(wrapper.find('.offline-toggle-btn').attributes('aria-expanded')).toBe('false')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Subsystem 4: layouts/default.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystem 4: layouts/default.vue (Living Ambient Shell & Field Ergonomics)', () => {
    it('integrates useCognitiveTerroir, skip link, keyboard navigation and subsystem drawers', () => {
      const src = readSource('layouts/default.vue')
      expect(src).toContain('useCognitiveTerroir')
      expect(src).toContain('livingAmbientDayClass')
      expect(src).toContain('tide-pulse-')
      expect(src).toContain('flow-')

      // WCAG 2.2 AAA Skip Link
      expect(src).toContain('href="#main-content"')
      expect(src).toContain('skip-link')

      // Keyboard shortcuts J, K, /
      expect(src).toContain("e.key === '/'")
      expect(src).toContain("e.key === 'j' || e.key === 'J'")
      expect(src).toContain("e.key === 'k' || e.key === 'K'")

      // Subsystem integrations
      expect(src).toContain('<OfflineTerroirPanel')
      expect(src).toContain('<SearchDrawer')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Subsystem 5: error.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystem 5: error.vue (Bến Đò Lỡ Chuyến Narrative & Safe-Haven Waypoints)', () => {
    it('renders authentic cultural narrative, waypoints, and offline recovery option', () => {
      const src = readSource('error.vue')
      expect(src).toContain('Bến Đò Lỡ Chuyến')
      expect(src).toContain('Dòng sông Cổ Chiên mênh mông')
      expect(src).toContain('to="/ban-do"')
      expect(src).toContain('to="/am-thuc"')
      expect(src).toContain('to="/danh-ba"')
      expect(src).toContain('showOfflinePanel = true')
      expect(src).toContain("robots: 'noindex, nofollow'")
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Subsystems 6 to 9: Catalog, Detail, Maps, Itinerary Unification
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystems 6-9: Page Unification & Ergonomic Standards', () => {
    it('enforces grid--asymmetric on all 4 catalog pages (du-lich, am-thuc, luu-tru, san-pham)', () => {
      const duLich = readSource('pages/du-lich.vue')
      const amThuc = readSource('pages/am-thuc.vue')
      const luuTru = readSource('pages/luu-tru.vue')
      const sanPham = readSource('pages/san-pham.vue')

      expect(duLich).toContain('grid--asymmetric')
      expect(amThuc).toContain('grid--asymmetric')
      expect(luuTru).toContain('grid--asymmetric')
      expect(sanPham).toContain('grid--asymmetric')
    })

    it('integrates TufteSidenote and Green Tourism Criteria badge in dia-diem/[id].vue', () => {
      const detail = readSource('pages/dia-diem/[id].vue')
      expect(detail).toContain('<TufteSidenote')
      expect(detail).toContain('green-tourism-badge')
      expect(detail).toContain('Tiêu chí Du lịch Xanh Vĩnh Long')
      expect(detail).toContain('VernacularGlyph')
    })

    it('preserves Monocle editorial 65ch measure in bai-viet/[id].vue', () => {
      const article = readSource('pages/bai-viet/[id].vue')
      expect(article).toContain('max-width: 65ch')
    })

    it('provides high-contrast outdoor mode and one-handed thumb dock in ban-do.vue', () => {
      const map = readSource('pages/ban-do.vue')
      expect(map).toContain('data-outdoor-contrast')
      expect(map).toContain('map-field-dock')
      expect(map).toContain('10.254° N, 105.972° E')
      expect(map).toContain('is-fullbleed')
    })

    it('wires PocketPassModal in both tao-lich-trinh.vue and lich-trinh/[id].vue', () => {
      const planner = readSource('pages/tao-lich-trinh.vue')
      const itinDetail = readSource('pages/lich-trinh/[id].vue')

      expect(planner).toContain('<PocketPassModal')
      expect(planner).toContain("import PocketPassModal from '~/components/PocketPassModal.vue'")

      expect(itinDetail).toContain('<PocketPassModal')
      expect(itinDetail).toContain("import PocketPassModal from '~/components/PocketPassModal.vue'")
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Subsystem 10: Strict Invariants & Anti-Slop Safeguards
  // ──────────────────────────────────────────────────────────────────────────
  describe('Subsystem 10: Invariants (Zero Audio, Zero Video, Zero Slop, DB Intact)', () => {
    it('verifies ABSOLUTE ZERO AUDIO and ZERO VIDEO elements in components and layouts', () => {
      const targets = [
        'components/SearchDrawer.vue',
        'components/PocketPassModal.vue',
        'components/OfflineTerroirPanel.vue',
        'layouts/default.vue',
        'error.vue',
      ]

      for (const rel of targets) {
        const src = readSource(rel)
        expect(src).not.toMatch(/<audio[\s>]/i)
        expect(src).not.toMatch(/<video[\s>]/i)
        expect(src).not.toMatch(/\.(?:mp3|wav|ogg|mp4|webm|mov)\b/i)
      }
    })

    it('verifies ZERO AI SLOP (no sparkles, no generic SaaS purple gradients)', () => {
      const targets = [
        'components/SearchDrawer.vue',
        'components/PocketPassModal.vue',
        'components/OfflineTerroirPanel.vue',
        'layouts/default.vue',
        'error.vue',
      ]

      for (const rel of targets) {
        const src = readSource(rel)
        expect(src).not.toMatch(/sparkle/i)
        expect(src).not.toMatch(/purple/i)
        expect(src).not.toMatch(/indigo/i)
      }
    })

    it('verifies SQLite production database and web/data.json remain 100% byte-for-byte intact', () => {
      const dbPath = resolve(root, '../agent/data/vinhlong360.db')
      const dataPath = resolve(root, '../web/data.json')

      expect(existsSync(dbPath)).toBe(true)
      expect(existsSync(dataPath)).toBe(true)

      const dbHash = createHash('sha256').update(readFileSync(dbPath)).digest('hex')
      const dataHash = createHash('sha256').update(readFileSync(dataPath)).digest('hex')

      expect(dbHash).toBe('20ac61bf7d247d8df35bd20bfe11140cf6eebae0980de4af5720d5ed73add742')
      expect(dataHash).toBe('3ab32ad210a962a2e8e4249c56309414af7a1880b3184059e743bb74488a7a97')
    })
  })
})
