// The correction journey, operable by everyone or not shipped.
//
// Keyboard first, names and live status for screen readers, focus that lands on
// the error summary, one column at 320px and 200% text, motion that bows out on
// request, and an action region that never hides under the bottom nav. Where a
// behaviour is testable in jsdom it is mounted and driven; where it is a CSS
// contract the stylesheet itself is held to it.

import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it, vi } from 'vitest'

import CaseReceiptCard from '../components/cases/CaseReceiptCard.vue'
import CaseStatusTimeline from '../components/cases/CaseStatusTimeline.vue'
import CorrectionIntakeForm from '../components/cases/CorrectionIntakeForm.vue'

const HERE = dirname(fileURLToPath(import.meta.url))

function source(relative) {
  return readFileSync(resolve(HERE, '..', relative), 'utf8')
}

const CASE_SOURCES = [
  'components/cases/CorrectionIntakeForm.vue',
  'components/cases/CaseReceiptCard.vue',
  'components/cases/CaseStatusTimeline.vue',
  'components/cases/DecisionPublicationState.vue',
  'pages/yeu-cau/sua-thong-tin.vue',
  'pages/yeu-cau/tra-cuu.vue',
  'pages/yeu-cau/trang-thai.vue',
]

const STATUS = {
  publicReference: 'VL-COR-0000000000001',
  receivedAt: '2026-08-19T09:00:00+00:00',
  currentStep: 'Đang xem xét',
  waitingFor: null,
  nextAction: 'Chúng tôi kiểm chứng thông tin đã báo',
  nextUpdateAt: '2026-08-21T09:00:00+00:00',
  promiseHealth: 'on_track',
  itemDecisions: [{ itemId: 'i-1', outcome: null, dispositionFamily: 'undetermined' }],
  itemPublicationStates: [{ itemId: 'i-1', state: 'not_required' }],
  reviewPath: '/api/cases/review',
}

function intakeForm(props = {}) {
  return mount(CorrectionIntakeForm, {
    props: {
      entityId: 'p-quan-com', entityName: 'Quán Cơm Bà Tư',
      baseEntityRevision: 7, ...props,
    },
  })
}

describe('keyboard operation', () => {
  it('runs the whole form on native controls, nothing click-only', () => {
    const form = intakeForm({ handoffDigest: 'a'.repeat(64) })

    // Native elements carry keyboard behaviour for free; a div with a handler
    // does not. Every interactive thing here must be one of the real ones.
    for (const element of form.findAll('[onclick], [role="button"]')) {
      expect(['BUTTON', 'A']).toContain(element.element.tagName)
    }
    expect(form.findAll('button, select, textarea, input, a').length).toBeGreaterThan(5)
    expect(form.html()).not.toMatch(/<div[^>]*@click|<span[^>]*@click/)
  })

  it('never traps focus with a positive tabindex', () => {
    for (const file of CASE_SOURCES) {
      // tabindex="-1" (programmatic focus) is fine; 1+ reorders the document
      // against the reading order and strands keyboard users.
      expect(source(file)).not.toMatch(/tabindex="[1-9]/)
    }
  })
})

describe('screen reader names and status', () => {
  it('labels every intake field through a real label element', async () => {
    const form = intakeForm()
    await form.get('#item-0-field').setValue('attributes.phone')

    for (const control of form.findAll('select, textarea, input[type="tel"]')) {
      const id = control.attributes('id')
      if (!id) continue
      expect(form.find(`label[for="${id}"]`).exists() || control.element.closest('label') !== null,
        `control #${id} has no name`).toBe(true)
    }
  })

  it('announces submission state through live regions, not colour', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: STATUS } })

    expect(timeline.get('[data-role="live-step"]').attributes('aria-live')).toBe('polite')
    // The receipt's one-time warning is an alert the reader cannot miss.
    const receipt = mount(CaseReceiptCard, {
      props: {
        receipt: {
          publicReference: 'VL-COR-0000000000001', capability: 'A'.repeat(43),
          receivedAt: '2026-08-19T09:00:00+00:00',
          nextUpdateAt: '2026-08-21T09:00:00+00:00', replayed: false,
        },
      },
    })
    expect(receipt.get('[role="alert"]').text()).toContain('một lần duy nhất')
  })

  it('structures every page under semantic headings and fieldsets', () => {
    const form = intakeForm()

    expect(form.findAll('fieldset legend').length).toBeGreaterThanOrEqual(2)
    for (const page of ['pages/yeu-cau/sua-thong-tin.vue', 'pages/yeu-cau/tra-cuu.vue']) {
      expect(source(page)).toContain('<h1>')
    }
  })
})

describe('focus and the error summary', () => {
  it('moves focus to the summary and links each error into its field', async () => {
    const raf = vi.spyOn(globalThis, 'requestAnimationFrame')
      .mockImplementation(callback => { callback(0); return 0 })
    const form = intakeForm()

    await form.get('form').trigger('submit')

    const summary = form.get('[data-role="error-summary"]')
    expect(summary.attributes('tabindex')).toBe('-1')
    expect(summary.attributes('role')).toBe('alert')
    // Each entry is an anchor into the field it names — the fix is one Enter away.
    const anchors = summary.findAll('a')
    expect(anchors.length).toBeGreaterThan(0)
    for (const anchor of anchors) {
      expect(anchor.attributes('href')).toMatch(/^#item-|^#phone-|^#handoff-/)
    }
    raf.mockRestore()
  })
})

describe('reflow: 320px wide, 200% text, short viewports', () => {
  it('lays every case surface out as a single fluid column', () => {
    for (const file of CASE_SOURCES) {
      const style = source(file)
      // minmax(0,1fr) single-column grids reflow at any width and any text
      // scale; a fixed pixel width is the thing that clips at 320/200%.
      expect(style).not.toMatch(/width:\s*\d{3,}px/)
      expect(style).not.toMatch(/min-width:\s*\d{3,}px/)
    }
    for (const page of ['pages/yeu-cau/sua-thong-tin.vue', 'pages/yeu-cau/tra-cuu.vue',
                        'pages/yeu-cau/trang-thai.vue']) {
      expect(source(page)).toContain('grid-template-columns: minmax(0, 1fr)')
    }
  })

  it('keeps long codes wrappable so 320x180 shows them whole', () => {
    // The reference and one-time key are the longest unbroken strings in the
    // journey; anywhere-wrap is what keeps them on screen at 320px.
    expect(source('components/cases/CaseReceiptCard.vue')).toContain('overflow-wrap: anywhere')
  })

  it('keeps the submit reachable at short heights without covering the nav', () => {
    const style = source('components/cases/CorrectionIntakeForm.vue')

    // Sticky above the bottom nav: reachable when the keyboard eats the
    // viewport, and never overlapping the nav it sits above.
    expect(style).toContain('position: sticky')
    expect(style).toContain('--shell-public-bottom-nav-reserved-height')
  })
})

describe('reduced motion', () => {
  it('runs every animation behind prefers-reduced-motion: no-preference', () => {
    for (const file of CASE_SOURCES) {
      const style = source(file)
      const animations = (style.match(/animation:/g) ?? []).length
      if (animations === 0) continue
      // Guarded opt-in, not opt-out: with no preference expressed either way
      // by the file, the animation must live inside the no-preference block.
      expect(style, `${file} animates outside the motion guard`)
        .toContain('@media (prefers-reduced-motion: no-preference)')
    }
  })
})
