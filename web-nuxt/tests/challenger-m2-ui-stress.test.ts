import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import VernacularGlyph from '../components/VernacularGlyph.vue'
import TufteSidenote from '../components/TufteSidenote.vue'
import fs from 'node:fs'
import path from 'node:path'

describe('Adversarial UI Stress Harness — Milestone M2', () => {
  let consoleWarnSpy: any
  let consoleErrorSpy: any

  beforeEach(() => {
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleWarnSpy.mockRestore()
    consoleErrorSpy.mockRestore()
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Vernacular Glyphs: 32 Canonical, SVG Validity, Aliases, Fallback & No Warnings
  // ──────────────────────────────────────────────────────────────────────────
  describe('VernacularGlyph.vue — Stress & SVG Validity', () => {
    const CANONICAL_32_GLYPHS = [
      'mangthit-kiln',
      'mekong-boat-eye',
      'barringtonia-flower',
      'water-lily',
      'three-plank-sampan',
      'conical-hat',
      'rice-husk-smoke',
      'coconut-palm',
      'pottery-wheel',
      'temple-roof',
      'fishing-basket',
      'silt-current',
      'wind-monsoon',
      'elder-glasses',
      'sun-glare',
      'guilloche-pass',
      'wax-seal',
      'green-lotus',
      'field-compass',
      'eoc-routing',
      'ancient-brick',
      'water-coconut',
      'lunar-tide',
      'rambutan-fruit',
      'durian-orchard',
      'tufte-marginalia',
      'ferry-landing',
      'mekong-net',
      'clay-artisan',
      'pagoda-spire',
      'bird-sanctuary',
      'sediment-delta',
    ]

    it('contains exactly 32 canonical glyphs in the test specification', () => {
      expect(CANONICAL_32_GLYPHS.length).toBe(32)
      // Verify all are unique
      const uniqueGlyphs = new Set(CANONICAL_32_GLYPHS)
      expect(uniqueGlyphs.size).toBe(32)
    })

    it('renders valid, well-formed SVG without parser errors or console warnings for all 32 glyphs', () => {
      for (const glyph of CANONICAL_32_GLYPHS) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: glyph },
        })

        const svgEl = wrapper.find('svg')
        expect(svgEl.exists(), `Glyph ${glyph} must render an SVG element`).toBe(true)
        expect(svgEl.classes()).toContain(`glyph--${glyph}`)
        expect(svgEl.attributes('viewBox')).toBe('0 0 24 24')
        expect(svgEl.attributes('fill')).toBe('none')
        expect(svgEl.attributes('stroke')).toBe('currentColor')
        expect(svgEl.attributes('stroke-width')).toBe('1.6')

        // Check XML/SVG validity via DOMParser
        const rawHtml = wrapper.html()
        const parser = new DOMParser()
        const doc = parser.parseFromString(rawHtml, 'image/svg+xml')
        const parseError = doc.querySelector('parsererror')
        expect(parseError, `Glyph ${glyph} produced XML parsererror: ${parseError?.textContent}`).toBeNull()

        // Check that SVG contains valid vector tags
        const vectorChildren = doc.querySelectorAll('path, circle, ellipse, rect, polygon')
        expect(vectorChildren.length, `Glyph ${glyph} must contain vector drawing elements`).toBeGreaterThan(0)

        // Ensure no console warnings/errors occurred
        expect(consoleWarnSpy).not.toHaveBeenCalled()
        expect(consoleErrorSpy).not.toHaveBeenCalled()

        wrapper.unmount()
      }
    })

    it('correctly maps all 28 cultural aliases and synonyms to valid canonical glyphs', () => {
      const aliases: Record<string, string> = {
        'mang-thit-kiln': 'mangthit-kiln',
        'eco-routing': 'eoc-routing',
        'water-coconut-palm': 'water-coconut',
        'ancient-communal-roof': 'temple-roof',
        'communal-house': 'temple-roof',
        'fish-trap-lo': 'fishing-basket',
        'bamboo-fish-trap': 'fishing-basket',
        'water-tide-pulse': 'silt-current',
        'elder-reading': 'elder-glasses',
        'high-glare-sun': 'sun-glare',
        'pocket-pass': 'guilloche-pass',
        'sourcemark-seal': 'wax-seal',
        'provenance-seal': 'wax-seal',
        'sourcemark-stamp': 'wax-seal',
        'lotus-lamp-ao-ba-om': 'green-lotus',
        'lotus-leaf': 'green-lotus',
        'clay-brick': 'ancient-brick',
        'tide-high': 'lunar-tide',
        'tide-low': 'lunar-tide',
        'durian-ri6': 'durian-orchard',
        'field-dossier-scroll': 'tufte-marginalia',
        'monocle-quill': 'tufte-marginalia',
        'ferry-crossing': 'ferry-landing',
        'an-binh-ferry': 'ferry-landing',
        'safe-haven': 'ferry-landing',
        'earthenware-jar': 'clay-artisan',
        'khmer-kbach-ornament': 'pagoda-spire',
        'co-chien-wave': 'sediment-delta',
        'nam-roi-pomelo': 'rambutan-fruit',
      }

      for (const [alias, expectedCanonical] of Object.entries(aliases)) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: alias },
        })

        expect(wrapper.classes()).toContain(`glyph--${expectedCanonical}`)
        const parser = new DOMParser()
        const doc = parser.parseFromString(wrapper.html(), 'image/svg+xml')
        expect(doc.querySelector('parsererror')).toBeNull()
        wrapper.unmount()
      }

      expect(consoleWarnSpy).not.toHaveBeenCalled()
      expect(consoleErrorSpy).not.toHaveBeenCalled()
    })

    it('falls back gracefully to mangthit-kiln on unknown, empty, or whitespace names', () => {
      const invalidInputs = [
        'completely-nonexistent-glyph',
        '',
        '   ',
        '???random#',
      ]

      for (const input of invalidInputs) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: input },
        })

        expect(wrapper.classes()).toContain('glyph--mangthit-kiln')
        expect(wrapper.html()).toContain('M4 21h16')
        const parser = new DOMParser()
        const doc = parser.parseFromString(wrapper.html(), 'image/svg+xml')
        expect(doc.querySelector('parsererror')).toBeNull()
        wrapper.unmount()
      }

      expect(consoleWarnSpy).not.toHaveBeenCalled()
      expect(consoleErrorSpy).not.toHaveBeenCalled()
    })

    it('normalizes uppercase and surrounding whitespace correctly', () => {
      const wrapper = mount(VernacularGlyph, {
        props: { name: '  MANGTHIT-KILN  ' },
      })
      expect(wrapper.classes()).toContain('glyph--mangthit-kiln')
      wrapper.unmount()

      const wrapperAlias = mount(VernacularGlyph, {
        props: { name: '  ECO-ROUTING  ' },
      })
      expect(wrapperAlias.classes()).toContain('glyph--eoc-routing')
      wrapperAlias.unmount()
    })

    it('supports size props (numbers, presets, and string numbers)', () => {
      const presets = [
        { prop: 'sm', expected: '16' },
        { prop: 'md', expected: '24' },
        { prop: 'lg', expected: '32' },
        { prop: 'xl', expected: '48' },
        { prop: 40, expected: '40' },
        { prop: '64', expected: '64' },
        { prop: 'invalid-size', expected: '24' },
      ]

      for (const { prop, expected } of presets) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: 'mangthit-kiln', size: prop as any },
        })
        expect(wrapper.attributes('width')).toBe(expected)
        expect(wrapper.attributes('height')).toBe(expected)
        wrapper.unmount()
      }
    })

    it('supports accent and custom color styling without color debt', () => {
      const accents = ['clay', 'silt', 'culao', 'cochien', 'ink'] as const
      for (const acc of accents) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: 'mangthit-kiln', accent: acc },
        })
        expect(wrapper.classes()).toContain(`glyph--accent-${acc}`)
        wrapper.unmount()
      }

      // 'current' accent produces no extra accent class
      const currentWrapper = mount(VernacularGlyph, {
        props: { name: 'mangthit-kiln', accent: 'current' },
      })
      expect(currentWrapper.classes()).not.toContain('glyph--accent-current')
      currentWrapper.unmount()

      // Color mapping
      const colors = [
        { color: 'clay', expectedStyle: 'color: var(--mangthit-500);' },
        { color: 'silt', expectedStyle: 'color: var(--harvest-600);' },
        { color: 'culao', expectedStyle: 'color: var(--orchard-600);' },
        { color: 'cochien', expectedStyle: 'color: var(--river-600);' },
        { color: 'ink', expectedStyle: 'color: var(--mekong-ink);' },
        { color: 'gold', expectedStyle: 'color: var(--alluvial-gold);' },
      ]
      for (const { color, expectedStyle } of colors) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: 'mangthit-kiln', color },
        })
        expect(wrapper.attributes('style')).toContain(expectedStyle)
        wrapper.unmount()
      }
    })

    it('handles accessibility props (role, aria-label, presentation aria-hidden)', () => {
      const imgWrapper = mount(VernacularGlyph, {
        props: { name: 'mangthit-kiln', role: 'img' },
      })
      expect(imgWrapper.attributes('role')).toBe('img')
      expect(imgWrapper.attributes('aria-label')).toBe('mangthit kiln')
      expect(imgWrapper.attributes('aria-hidden')).toBeUndefined()
      imgWrapper.unmount()

      const presWrapper = mount(VernacularGlyph, {
        props: { name: 'mangthit-kiln', role: 'presentation' },
      })
      expect(presWrapper.attributes('role')).toBe('presentation')
      expect(presWrapper.attributes('aria-hidden')).toBe('true')
      presWrapper.unmount()

      const customAriaWrapper = mount(VernacularGlyph, {
        props: { name: 'mangthit-kiln', ariaLabel: 'Biểu tượng Lò gạch Mang Thít' },
      })
      expect(customAriaWrapper.attributes('aria-label')).toBe('Biểu tượng Lò gạch Mang Thít')
      customAriaWrapper.unmount()
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 2. TufteSidenote: Desktop Gutter, Mobile Trigger (>=44x44), Bottom Sheet & Escape Listener
  // ──────────────────────────────────────────────────────────────────────────
  describe('TufteSidenote.vue — Ergonomics, A11y & Escape Key Listener', () => {
    it('verifies desktop gutter classes, role="note", aria-labelledby and IDs', () => {
      const wrapper = mount(TufteSidenote, {
        props: {
          number: 5,
          content: 'Khảo cứu địa chí sông Cổ Chiên thế kỷ 19.',
          notebookId: 'v-nh-long-v-nh-long-b-n-tre-tr',
          authorityTier: 'TIER_2_ACADEMIC',
          sourceTitle: 'Tập san Sử Địa Nam Bộ',
          sourceUrl: 'https://vinhlong.gov.vn/sudia',
          legalReference: 'Tập 4, trang 112',
          verifiedAt: '2026-09-12',
        },
        global: {
          stubs: {
            SourceMark: true,
          },
        },
      })

      // Desktop Gutter aside
      const aside = wrapper.find('aside.tufte-sidenote')
      expect(aside.exists()).toBe(true)
      expect(aside.attributes('role')).toBe('note')
      expect(aside.attributes('id')).toBe('tufte-note-5')
      expect(aside.attributes('aria-labelledby')).toBe('tufte-trigger-5')
      expect(aside.attributes('data-notebook-id')).toBe('v-nh-long-v-nh-long-b-n-tre-tr')
      expect(aside.attributes('data-authority-tier')).toBe('TIER_2_ACADEMIC')

      // Content and authority label
      expect(aside.text()).toContain('§5')
      expect(aside.text()).toContain('Khảo cứu Viện/Đại học')
      expect(aside.text()).toContain('Khảo cứu địa chí sông Cổ Chiên thế kỷ 19.')
      expect(aside.text()).toContain('Tập san Sử Địa Nam Bộ')
      expect(aside.text()).toContain('Tập 4, trang 112')

      // Trigger button IDs & aria attributes
      const trigger = wrapper.find('button.tufte-sidenote-trigger')
      expect(trigger.exists()).toBe(true)
      expect(trigger.attributes('id')).toBe('tufte-trigger-5')
      expect(trigger.attributes('aria-controls')).toBe('tufte-note-5')
      expect(trigger.attributes('aria-expanded')).toBe('false')

      wrapper.unmount()
    })

    it('enforces touch target size >= 44x44px in CSS source for mobile trigger and close button', () => {
      // Static CSS inspection of TufteSidenote.vue file
      const filePath = path.resolve(__dirname, '../components/TufteSidenote.vue')
      const source = fs.readFileSync(filePath, 'utf-8')

      // Ensure .tufte-sidenote-trigger has min-width: 44px and min-height: 44px
      const triggerCssMatch = source.match(/\.tufte-sidenote-trigger\s*\{[^}]*min-width:\s*44px[^}]*min-height:\s*44px[^}]*\}/s)
      expect(triggerCssMatch, 'Trigger button must declare min-width: 44px and min-height: 44px').not.toBeNull()

      // Ensure .tufte-sheet-close has min-width: 44px and min-height: 44px
      const closeCssMatch = source.match(/\.tufte-sheet-close\s*\{[^}]*min-width:\s*44px[^}]*min-height:\s*44px[^}]*\}/s)
      expect(closeCssMatch, 'Sheet close button must declare min-width: 44px and min-height: 44px').not.toBeNull()
    })

    it('verifies bottom sheet structure, ARIA dialog contract, drag handle, and slot support', async () => {
      const wrapper = mount(TufteSidenote, {
        props: {
          number: 7,
          sourceTitle: 'Sổ tay Vĩnh Long 360',
          authorityTier: 'TIER_1_GOVERNMENT',
        },
        slots: {
          default: '<span class="custom-slot-content">Nội dung truyền qua default slot</span>',
        },
        global: {
          stubs: {
            SourceMark: true,
            Teleport: true,
          },
        },
      })

      // Initially closed
      expect(wrapper.find('.tufte-bottom-sheet').exists()).toBe(false)
      expect(wrapper.find('.tufte-backdrop').exists()).toBe(false)

      // Open via mobile trigger click
      const trigger = wrapper.find('button.tufte-sidenote-trigger')
      await trigger.trigger('click')

      // Dialog and backdrop must be present
      expect(trigger.attributes('aria-expanded')).toBe('true')
      const backdrop = wrapper.find('.tufte-backdrop')
      expect(backdrop.exists()).toBe(true)
      expect(backdrop.attributes('aria-hidden')).toBe('true')

      const sheet = wrapper.find('.tufte-bottom-sheet')
      expect(sheet.exists()).toBe(true)
      expect(sheet.attributes('role')).toBe('dialog')
      expect(sheet.attributes('aria-modal')).toBe('true')
      expect(sheet.attributes('aria-label')).toBe('Chú giải lề học thuật số 7')

      // Drag pill handle
      const dragPill = sheet.find('.tufte-sheet-drag-pill')
      expect(dragPill.exists()).toBe(true)

      // Header title
      const title = sheet.find('.tufte-sheet-title')
      expect(title.text()).toContain('Chú giải học thuật · Edward Tufte')

      // Custom slot content
      const slotContent = sheet.find('.custom-slot-content')
      expect(slotContent.exists()).toBe(true)
      expect(slotContent.text()).toBe('Nội dung truyền qua default slot')

      // Citation block
      const cite = sheet.find('.tufte-sheet-cite')
      expect(cite.text()).toContain('Sổ tay Vĩnh Long 360')

      // Close via backdrop click
      await backdrop.trigger('click')
      expect(trigger.attributes('aria-expanded')).toBe('false')
      expect(wrapper.find('.tufte-bottom-sheet').exists()).toBe(false)

      wrapper.unmount()
    })

    it('handles Escape key listener cleanly on window and removes on unmount', async () => {
      const wrapper = mount(TufteSidenote, {
        props: {
          number: 9,
          content: 'Nội dung kiểm tra bàn phím Escape.',
        },
        global: {
          stubs: {
            SourceMark: true,
            Teleport: true,
          },
        },
      })

      const trigger = wrapper.find('button.tufte-sidenote-trigger')

      // Pressing Escape while closed does nothing
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      expect(trigger.attributes('aria-expanded')).toBe('false')
      expect(wrapper.find('.tufte-bottom-sheet').exists()).toBe(false)

      // Open sheet
      await trigger.trigger('click')
      expect(trigger.attributes('aria-expanded')).toBe('true')
      expect(wrapper.find('.tufte-bottom-sheet').exists()).toBe(true)

      // Pressing non-Escape key (e.g. Enter) does NOT close the sheet
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
      expect(trigger.attributes('aria-expanded')).toBe('true')

      // Pressing Escape closes the sheet
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      await wrapper.vm.$nextTick()
      expect(trigger.attributes('aria-expanded')).toBe('false')
      expect(wrapper.find('.tufte-bottom-sheet').exists()).toBe(false)

      // Open again, then unmount, then verify listener was removed
      await trigger.trigger('click')
      expect(trigger.attributes('aria-expanded')).toBe('true')

      // Spy on removeEventListener
      const removeListenerSpy = vi.spyOn(window, 'removeEventListener')
      wrapper.unmount()

      expect(removeListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
      removeListenerSpy.mockRestore()

      // Dispatching Escape after unmount does not throw or crash
      expect(() => {
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      }).not.toThrow()
    })

    it('supports custom id prop and maps authority tier labels accurately', () => {
      const tierMappings = [
        { tier: 'TIER_1_GOVERNMENT', expected: 'Thẩm quyền Nhà nước' },
        { tier: 'official', expected: 'Thẩm quyền Nhà nước' },
        { tier: 'TIER_2_ACADEMIC', expected: 'Khảo cứu Viện/Đại học' },
        { tier: 'verified', expected: 'Khảo cứu Viện/Đại học' },
        { tier: 'TIER_3_PRESS', expected: 'Báo chí & Lưu trữ' },
        { tier: 'community', expected: 'Báo chí & Lưu trữ' },
        { tier: '', expected: '' },
      ]

      for (const { tier, expected } of tierMappings) {
        const wrapper = mount(TufteSidenote, {
          props: {
            id: 'custom-note-id',
            number: '12',
            authorityTier: tier,
          },
          global: {
            stubs: { SourceMark: true },
          },
        })

        const aside = wrapper.find('aside.tufte-sidenote')
        expect(aside.attributes('id')).toBe('custom-note-id')
        if (expected) {
          expect(aside.text()).toContain(expected)
        }
        wrapper.unmount()
      }
    })
  })
})
