import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import PocketPassModal from '../components/PocketPassModal.vue'
import SearchDrawer from '../components/SearchDrawer.vue'
import ErrorPage from '../error.vue'

const root = resolve(__dirname, '..')
const readSource = (relPath: string) => readFileSync(resolve(root, relPath), 'utf8')

describe('Empirical Challenger M3 Remediation Stress Suite', () => {
  let container: HTMLDivElement
  let backgroundButton: HTMLButtonElement

  beforeEach(() => {
    container = document.createElement('div')
    backgroundButton = document.createElement('button')
    backgroundButton.id = 'background-element'
    backgroundButton.textContent = 'Background Leaked Target'
    document.body.appendChild(backgroundButton)
    document.body.appendChild(container)
    document.body.style.overflow = ''
  })

  afterEach(() => {
    if (container.parentNode) document.body.removeChild(container)
    if (backgroundButton.parentNode) document.body.removeChild(backgroundButton)
    document.body.style.overflow = ''
  })

  // 1. PocketPassModal Focus Trap Confinement & Background DOM Isolation
  describe('1. PocketPassModal Focus Trap & Accessibility Rigor', () => {
    it('sets initial focus to the close button when opened', async () => {
      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        attachTo: container,
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            IconLine: true,
            VernacularGlyph: true,
            MekongWaterBadge: true,
          },
        },
      })

      await nextTick()
      await new Promise(r => setTimeout(r, 50))

      const closeBtn = wrapper.find('.pocket-pass-close-btn')
      expect(closeBtn.exists()).toBe(true)
      expect(document.activeElement).toBe(closeBtn.element)
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('confines focus: Tab on last element cycles to first element, Shift+Tab on first element cycles to last', async () => {
      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        attachTo: container,
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            IconLine: true,
            VernacularGlyph: true,
            MekongWaterBadge: true,
          },
        },
      })

      await nextTick()

      const containerEl = wrapper.find('.pocket-pass-container')
      expect(containerEl.exists()).toBe(true)

      const focusables = Array.from(
        containerEl.element.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      )

      expect(focusables.length).toBeGreaterThanOrEqual(8)
      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      expect(first).toBeDefined()
      expect(last).toBeDefined()
      if (!first || !last) return

      expect(first.classList.contains('pocket-pass-close-btn')).toBe(true)
      expect(last.classList.contains('pocket-pass-done-btn')).toBe(true)

      // Shift+Tab on first element -> wraps to last element
      first.focus()
      expect(document.activeElement).toBe(first)

      const overlay = wrapper.find('.pocket-pass-modal-overlay')
      const shiftTabEvent = new KeyboardEvent('keydown', {
        key: 'Tab',
        shiftKey: true,
        bubbles: true,
        cancelable: true,
      })
      const shiftPreventSpy = vi.spyOn(shiftTabEvent, 'preventDefault')
      overlay.element.dispatchEvent(shiftTabEvent)

      expect(shiftPreventSpy).toHaveBeenCalled()
      expect(document.activeElement).toBe(last)

      // Tab on last element -> wraps to first element
      last.focus()
      expect(document.activeElement).toBe(last)

      const tabEvent = new KeyboardEvent('keydown', {
        key: 'Tab',
        shiftKey: false,
        bubbles: true,
        cancelable: true,
      })
      const tabPreventSpy = vi.spyOn(tabEvent, 'preventDefault')
      overlay.element.dispatchEvent(tabEvent)

      expect(tabPreventSpy).toHaveBeenCalled()
      expect(document.activeElement).toBe(first)
    })

    it('ensures focus NEVER leaks to background DOM elements', async () => {
      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        attachTo: container,
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            IconLine: true,
            VernacularGlyph: true,
            MekongWaterBadge: true,
          },
        },
      })

      await nextTick()

      const overlay = wrapper.find('.pocket-pass-modal-overlay')

      // Stress test: cycle 50 Tab events across boundary and intermediate states
      for (let i = 0; i < 50; i++) {
        const isShift = i % 3 === 0

        const evt = new KeyboardEvent('keydown', {
          key: 'Tab',
          shiftKey: isShift,
          bubbles: true,
          cancelable: true,
        })
        overlay.element.dispatchEvent(evt)

        // Active element must NEVER be the background button or outside container
        expect(document.activeElement).not.toBe(backgroundButton)
        expect(document.activeElement?.id).not.toBe('background-element')
      }
    })
  })

  // 2. Emergency Rescue Contacts Scheme & Dialable tel: Invariants
  describe('2. Emergency Rescue Contacts Scheme & Dialable tel: Invariants', () => {
    it('renders all 5 verified emergency rescue contacts with active tel: links', () => {
      const wrapper = mount(PocketPassModal, {
        props: { open: true },
        attachTo: container,
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            IconLine: true,
            VernacularGlyph: true,
            MekongWaterBadge: true,
          },
        },
      })

      const contactCards = wrapper.findAll('a.emergency-contact-card')
      expect(contactCards.length).toBe(5)

      const expectedContacts = [
        { tel: 'tel:114', name: 'Cứu hộ PCCC & CNCH đường sông', phone: '114' },
        { tel: 'tel:115', name: 'Cấp cứu Y tế sông nước', phone: '115' },
        { tel: 'tel:02703823888', name: 'Cứu hộ Giao thông Thủy Vĩnh Long', phone: '0270 3823 888' },
        { tel: 'tel:02703822114', name: 'Cứu nạn Công an Tỉnh Vĩnh Long', phone: '0270 3822 114' },
        { tel: 'tel:02703833456', name: 'Điều hành Bến phà & Cứu hộ', phone: '0270 3833 456' },
      ]

      expectedContacts.forEach(expected => {
        const matchingCard = contactCards.find(card => card.attributes('href') === expected.tel)
        expect(matchingCard).toBeDefined()
        expect(matchingCard?.text()).toContain(expected.name)
        expect(matchingCard?.text()).toContain(expected.phone)

        // Verify accessible aria-label
        const ariaLabel = matchingCard?.attributes('aria-label')
        expect(ariaLabel).toBeDefined()
        expect(ariaLabel).toContain(expected.name)
      })
    })

    it('ensures all emergency contact touch targets meet >= 44px min-height', () => {
      const src = readSource('components/PocketPassModal.vue')
      expect(src).toMatch(/\.emergency-contact-card\s*\{[^}]*min-height:\s*44px/s)
    })
  })

  // 3. Mobile Viewport Close Button Layout & Geometry Safety
  describe('3. Mobile Viewport Close Button Layout & Geometry Safety', () => {
    it('provides safe top: 0, right: 0 and padding-top: 48px on mobile viewports', () => {
      const src = readSource('components/PocketPassModal.vue')

      // Check responsive media query
      expect(src).toContain('@media (max-width: 640px), (max-height: 640px)')

      // Check safe bounds for close button and container
      expect(src).toMatch(/padding-top:\s*48px/)
      expect(src).toMatch(/\.pocket-pass-close-btn\s*\{[^}]*top:\s*0/s)
      expect(src).toMatch(/\.pocket-pass-close-btn\s*\{[^}]*right:\s*0/s)

      // Check close button has min 44x44px touch targets
      expect(src).toMatch(/\.pocket-pass-close-btn\s*\{[^}]*min-width:\s*44px/s)
      expect(src).toMatch(/\.pocket-pass-close-btn\s*\{[^}]*min-height:\s*44px/s)
    })
  })

  // 4. error.vue Route Verification
  describe('4. error.vue Route Verification', () => {
    it('verifies line 131 routes to /am-thuc in popularLinks', () => {
      const src = readSource('error.vue')
      const lines = src.split('\n')

      // Locate line 131 (1-indexed -> 130 0-indexed)
      const line131 = lines[130] // 0-indexed
      expect(line131).toContain("to: '/am-thuc'")
      expect(line131).toContain("label: 'Ẩm thực'")
      expect(line131).toContain("icon: 'bowl'")

      // Also mount component and check rendered links
      const wrapper = mount(ErrorPage, {
        props: {
          error: { statusCode: 404 },
        },
        global: {
          stubs: {
            NuxtLink: {
              props: ['to'],
              template: '<a :href="to" class="nuxt-link-stub"><slot /></a>',
            },
            IconLine: true,
            VernacularGlyph: true,
            ClientOnly: { template: '<div><slot /></div>' },
            OfflineTerroirPanel: true,
          },
        },
      })

      const amThucLinks = wrapper.findAll('a[href="/am-thuc"]')
      expect(amThucLinks.length).toBeGreaterThanOrEqual(2)
      expect(wrapper.text()).toContain('Ký Sự Ẩm Thực')
      expect(wrapper.text()).toContain('Ẩm thực')
    })
  })

  // 5. SearchDrawer.vue Authentic Editorial Empty State
  describe('5. SearchDrawer.vue Authentic Editorial Empty State', () => {
    it('displays authentic empty state when no search query matches', async () => {
      const wrapper = mount(SearchDrawer, {
        props: { open: true },
        attachTo: container,
        global: {
          stubs: {
            Teleport: { template: '<div><slot /></div>' },
            Transition: { template: '<div><slot /></div>' },
            NuxtLink: { template: '<a><slot /></a>' },
            IconLine: true,
            VernacularGlyph: true,
            SourceMark: true,
          },
        },
      })

      const input = wrapper.find('.search-drawer-input')
      await input.setValue('xyz_khong_ton_tai_99999')
      await nextTick()

      // Should show authentic empty state, NOT arbitrary curated suggestions
      expect(wrapper.find('.search-drawer-empty-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('Chưa tìm thấy di sản hay tọa độ phù hợp')
      expect(wrapper.text()).toContain('xyz_khong_ton_tai_99999')
      expect(wrapper.find('.search-drawer-plaques').exists()).toBe(false)

      // Test reset button
      const resetBtn = wrapper.find('.empty-state-reset-btn')
      expect(resetBtn.exists()).toBe(true)
      await resetBtn.trigger('click')
      await nextTick()

      // Suggestions restored
      expect(wrapper.find('.search-drawer-empty-state').exists()).toBe(false)
      expect(wrapper.find('.search-drawer-plaques').exists()).toBe(true)
    })
  })
})
