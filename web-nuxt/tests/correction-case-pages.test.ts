// The public journey, held to what it promises.
//
// These mount the real components. The receipt may show the key exactly once
// and must offer the reference for keeps; the form may not send a phone number
// nobody consented to; the timeline may not offer a review of an answer that
// does not exist yet; and no screen may promise a resolution time the kernel
// never agreed to.

import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

import CaseReceiptCard from '../components/cases/CaseReceiptCard.vue'
import CaseStatusTimeline from '../components/cases/CaseStatusTimeline.vue'
import CorrectionIntakeForm from '../components/cases/CorrectionIntakeForm.vue'
import DecisionPublicationState from '../components/cases/DecisionPublicationState.vue'
import type { CaseStatus } from '../types/cases'

const RECEIPT = {
  publicReference: 'VL-COR-0000000000001',
  capability: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefg',
  receivedAt: '2026-08-19T09:00:00+00:00',
  nextUpdateAt: '2026-08-21T09:00:00+00:00',
  replayed: false,
}

function statusWith(overrides: Partial<CaseStatus> = {}): CaseStatus {
  return {
    publicReference: 'VL-COR-0000000000001',
    receivedAt: '2026-08-19T09:00:00+00:00',
    currentStep: 'Đang xem xét',
    waitingFor: null,
    nextAction: 'Chúng tôi kiểm chứng thông tin đã báo',
    nextUpdateAt: '2026-08-21T09:00:00+00:00',
    promiseHealth: 'on_track',
    itemDecisions: [
      { itemId: 'i-1', outcome: null, dispositionFamily: 'undetermined' },
    ],
    itemPublicationStates: [
      { itemId: 'i-1', state: 'not_required' },
    ],
    reviewPath: '/api/cases/review',
    // Con số POST /api/cases/review đòi lại ở `expectedRevision`.
    currentRevision: 3,
    ...overrides,
  }
}

function intakeForm(props: Record<string, unknown> = {}) {
  return mount(CorrectionIntakeForm, {
    props: {
      entityId: 'p-quan-com',
      entityName: 'Quán Cơm Bà Tư',
      baseEntityRevision: 7,
      ...props,
    },
  })
}

describe('the receipt', () => {
  it('shows the one-time key with its warning beside it, exactly once', () => {
    const card = mount(CaseReceiptCard, { props: { receipt: RECEIPT } })

    expect(card.get('[data-role="capability"]').text()).toBe(RECEIPT.capability)
    const warning = card.get('[role="alert"]').text()
    expect(warning).toContain('một lần duy nhất')
    expect(warning).toContain('không thể cấp lại')
  })

  it('hides the key and asks the parent to forget it once the reader has saved it', async () => {
    const card = mount(CaseReceiptCard, { props: { receipt: RECEIPT } })

    await card.get('[data-role="confirm-saved"]').trigger('click')

    expect(card.find('[data-role="capability"]').exists()).toBe(false)
    expect(card.get('[data-role="capability-gone"]').text()).toContain('đã được ẩn')
    expect(card.emitted('forget')).toHaveLength(1)
    // The reference stays: it is the part that belongs on paper.
    expect(card.get('[data-role="public-reference"]').text()).toBe(RECEIPT.publicReference)
  })

  it('keeps the reference printable while keeping the key off paper', () => {
    const source = readFileSync(
      resolve(__dirname, '..', 'components', 'cases', 'CaseReceiptCard.vue'), 'utf8',
    )

    // Paper outlives screens. The print stylesheet must exist, and the block
    // holding the secret must be the one it hides.
    expect(source).toContain('@media print')
    expect(source).toMatch(/\.print-hidden\s*\{\s*display:\s*none/)
    expect(source).toContain('receipt-secret print-hidden')
    expect(source).not.toContain('public-reference print-hidden')
  })
})

describe('the intake form', () => {
  it('asks one question until the reader has chosen a field', async () => {
    const form = intakeForm()

    expect(form.find('#item-0-proposed').exists()).toBe(false)

    await form.get('#item-0-field').setValue('attributes.phone')

    expect(form.find('#item-0-proposed').exists()).toBe(true)
  })

  it('lets the reporter explicitly say the current value is unknown', async () => {
    const form = intakeForm()
    await form.get('#item-0-field').setValue('attributes.phone')
    await form.get('#item-0-reported').setValue('0270 111 2222')
    await form.get('#item-0-proposed').setValue('0270 333 4444')

    const known = form.get('#item-0-reported-known')
    expect(known.attributes('type')).toBe('checkbox')
    await known.setValue(false)
    await form.get('[data-role="review"]').trigger('click')
    await form.get('form').trigger('submit')

    const [submission] = form.emitted('submit')![0] as [Record<string, any>]
    expect(submission.items[0]).toMatchObject({
      reportedValueKnown: false,
      reportedValue: null,
      proposedValue: '0270 333 4444',
    })
  })

  it('never sends a phone number nobody consented to', async () => {
    const form = intakeForm()
    await form.get('#item-0-field').setValue('attributes.phone')
    await form.get('#item-0-proposed').setValue('0270 333 4444')
    await form.get('#optional-phone').setValue('0912 345 678')

    await form.get('form').trigger('submit')

    // Without the consent box the submit is refused, not silently stripped.
    expect(form.emitted('submit')).toBeUndefined()
    expect(form.get('[data-role="error-summary"]').text()).toContain('đồng ý')
  })

  it('offers phone verification only after consent', async () => {
    const form = intakeForm()
    await form.get('#optional-phone').setValue('0912 345 678')
    expect(form.find('[data-role="verify-phone"]').exists()).toBe(false)

    await form.get('#phone-consent input').setValue(true)

    await form.get('[data-role="verify-phone"]').trigger('click')
    expect(form.emitted('request-phone-verification')).toEqual([['0912 345 678']])
  })

  it('requires the reader to stand behind a Zalo handoff before it is filed', async () => {
    const form = intakeForm({ handoffDigest: 'a'.repeat(64) })
    await form.get('#item-0-field').setValue('attributes.phone')
    await form.get('#item-0-proposed').setValue('0270 333 4444')

    await form.get('form').trigger('submit')
    expect(form.emitted('submit')).toBeUndefined()

    await form.get('#handoff-confirm input').setValue(true)
    await form.get('form').trigger('submit')

    const [submission] = form.emitted('submit')![0] as [Record<string, unknown>]
    expect(submission.handoffConfirmed).toBe(true)
  })

  it('routes danger to the people who answer it, claiming nothing for itself', () => {
    const text = intakeForm().get('[data-role="urgent-routing"]').text()

    expect(text).toContain('113')
    // We edit pages; nothing here may read as an emergency service.
    for (const claim of ['chúng tôi sẽ can thiệp', 'cứu hộ', 'ứng cứu']) {
      expect(text.toLowerCase()).not.toContain(claim)
    }
  })

  it('mentions assisted hours only when the deployment provides them', () => {
    expect(intakeForm().find('[data-role="assisted-hours"]').exists()).toBe(false)
    expect(
      intakeForm({ assistedHours: '8h–17h các ngày làm việc' })
        .get('[data-role="assisted-hours"]').text(),
    ).toContain('8h–17h')
  })

  it('sends focus to the error summary so the fixes are the next thing read', async () => {
    const raf = vi.spyOn(globalThis, 'requestAnimationFrame')
      .mockImplementation(callback => { callback(0); return 0 })
    const form = intakeForm({ attachTo: undefined })

    await form.get('form').trigger('submit')

    const summary = form.get('[data-role="error-summary"]')
    expect(summary.attributes('tabindex')).toBe('-1')
    expect(summary.attributes('role')).toBe('alert')
    raf.mockRestore()
  })
})

describe('the status timeline', () => {
  it('offers a review only once there is an answer to contest', async () => {
    const undecided = mount(CaseStatusTimeline, { props: { status: statusWith() } })
    expect(undecided.find('[data-role="request-review"]').exists()).toBe(false)
    expect(undecided.get('[data-role="review-unavailable"]').text()).toContain('sau khi có kết quả')

    const decided = mount(CaseStatusTimeline, {
      props: {
        status: statusWith({
          itemDecisions: [{ itemId: 'i-1', outcome: 'corrected', dispositionFamily: 'action_taken' }],
        }),
      },
    })
    await decided.get('[data-role="request-review"]').trigger('click')

    expect(decided.emitted('request-review')).toHaveLength(1)
  })

  it('announces the current step through a live region', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: statusWith() } })

    const live = timeline.get('[data-role="live-step"]')
    expect(live.attributes('aria-live')).toBe('polite')
    expect(live.text()).toBe('Đang xem xét')
  })

  it('tells the truth when fulfilment hit trouble, without a terminal claim', () => {
    const timeline = mount(CaseStatusTimeline, {
      props: { status: statusWith({ promiseHealth: 'recovery' }) },
    })

    const note = timeline.get('[data-role="promise-note"]').text()
    expect(note).toContain('khắc phục')
    expect(note.toLowerCase()).not.toContain('đã xử lý')
  })
})

describe('the decision and publication pair', () => {
  it('reads accepted and visible-to-the-public as different sentences', () => {
    const accepted = mount(DecisionPublicationState, {
      props: {
        fieldLabel: 'Số điện thoại',
        dispositionFamily: 'action_taken' as const,
        publicationState: 'pending' as const,
      },
    })

    const decision = accepted.get('[data-role="decision"]').text()
    const publication = accepted.get('[data-role="publication"]').text()
    expect(decision).not.toBe(publication)
    // Accepted, and visibly still on its way: the reader is not sent to a page
    // that has not moved.
    expect(publication).toContain('chờ')
  })

  it('says a correction is live only in the verified state', () => {
    const verified = mount(DecisionPublicationState, {
      props: {
        fieldLabel: 'Số điện thoại',
        dispositionFamily: 'action_taken' as const,
        publicationState: 'verified' as const,
      },
    })
    const applied = mount(DecisionPublicationState, {
      props: {
        fieldLabel: 'Số điện thoại',
        dispositionFamily: 'action_taken' as const,
        publicationState: 'applied' as const,
      },
    })

    expect(verified.get('[data-role="publication"]').text()).toContain('Đã hiển thị đúng')
    expect(applied.get('[data-role="publication"]').text()).not.toContain('Đã hiển thị đúng')
  })
})

describe('promises the journey must not make', () => {
  it('never quotes a 24-48 hour resolution anywhere in the case components', () => {
    for (const file of [
      'CorrectionIntakeForm.vue', 'CaseReceiptCard.vue',
      'CaseStatusTimeline.vue', 'DecisionPublicationState.vue',
    ]) {
      const source = readFileSync(
        resolve(__dirname, '..', 'components', 'cases', file), 'utf8',
      )
      expect(source, `${file} promises a resolution window`).not.toMatch(/24[\s–-]*48|48\s*giờ|24\s*giờ/)
    }
  })
})

describe('the three pages', () => {
  const page = (name: string) => readFileSync(
    resolve(__dirname, '..', 'pages', 'yeu-cau', name), 'utf8',
  )

  it('leave robots ownership to the launch head', () => {
    // Indexability is decided once, at the application boundary
    // (useLaunchSafety); a page declaring robots itself would fork that
    // ownership, and the launch-head contract rejects it.
    for (const name of ['sua-thong-tin.vue', 'tra-cuu.vue', 'trang-thai.vue']) {
      expect(page(name), `${name} declares robots itself`).not.toMatch(/robots\s*:/)
    }
  })

  it('never routes the capability through a URL', () => {
    for (const name of ['sua-thong-tin.vue', 'tra-cuu.vue', 'trang-thai.vue']) {
      const source = page(name)
      // Navigation carries no state and no query: the exchange sets a cookie,
      // and the status page runs on that alone.
      expect(source).not.toMatch(/query\s*:\s*\{[^}]*capab/i)
      expect(source).not.toMatch(/capability=[^'"\s]/)
    }
  })

  it('hides the one-time key from shoulders and password managers at lookup', () => {
    const source = page('tra-cuu.vue')

    expect(source).toContain('type="password"')
    expect(source).toContain('autocomplete="off"')
  })

  it('drops the key from memory the moment the exchange has used it', () => {
    expect(page('tra-cuu.vue')).toContain("capability.value = ''")
  })

  it('reads entity name and revision from the projection, not from the URL', () => {
    const source = page('sua-thong-tin.vue')

    // The revision pins which wording the correction was written against; a
    // URL-supplied one would let a stale tab file against text already gone.
    expect(source).toContain('/api/entities/')
    expect(source).not.toMatch(/route\.query\.(revision|name)/)
  })

  it('passes structured correction problems through to the draft form', () => {
    const source = page('sua-thong-tin.vue')
    expect(source).toContain('CorrectionProblemError')
    expect(source).not.toContain('problem.correlation_id')
    expect(source).toContain(':server-problem="problem"')
    expect(source).toContain('problem.field')
  })

  it('renders a structured server problem without discarding the draft', () => {
    const form = mount(CorrectionIntakeForm, {
      props: {
        entityId: 'p-quan-com',
        entityName: 'Quán Cơm Bà Tư',
        baseEntityRevision: 7,
        serverProblem: {
          code: 'invalid_request',
          detail: 'reportedValueKnown must be a boolean',
          status: 422,
          field: 'items.0.reportedValueKnown',
          correlation_id: 'corr-page-1',
        },
      },
    })

    expect(form.get('[data-role="server-error"]').text()).toContain('invalid_request')
    expect(form.get('[data-role="server-error"]').text()).toContain('reportedValueKnown')
    expect(form.get('[data-role="server-error"]').text()).not.toContain('corr-page-1')
    expect(form.get('[data-role="server-error"] a').attributes('href')).toBe('#item-0-reported-known')
    expect(form.find('#item-0-field').exists()).toBe(true)
  })

  it('reflows as a single column with no fixed page width', () => {
    for (const name of ['sua-thong-tin.vue', 'tra-cuu.vue', 'trang-thai.vue']) {
      const source = page(name)
      expect(source).toContain('grid-template-columns: minmax(0, 1fr)')
      expect(source).not.toMatch(/width:\s*\d{3,}px/)
    }
  })
})

describe('a ruling the reporter can act on', () => {
  const refused = statusWith({
    itemDecisions: [{
      itemId: 'i-1', outcome: 'insufficient_evidence', dispositionFamily: 'no_action',
    }],
  })

  it('names which refusal it was, not just that nothing changed', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: refused } })

    // "Không thay đổi" covers three different refusals with three different
    // next steps. Somebody told no deserves to know which one they got.
    expect(timeline.get('[data-role="decision"]').text()).toContain('Chưa đủ căn cứ')
    expect(timeline.get('[data-role="decision"]').text()).toContain('gửi thêm nguồn')
  })

  it('offers the review action once the answer is settled, refusal included', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: refused } })

    // This is the control a declined reporter uses to contest. While every
    // refusal read as 'undetermined' it never appeared for them at all.
    expect(timeline.find('[data-role="request-review"]').exists()).toBe(true)
  })

  it('still withholds it while nothing is decided', () => {
    const undecided = statusWith()

    expect(mount(CaseStatusTimeline, { props: { status: undecided } })
      .find('[data-role="request-review"]').exists()).toBe(false)
  })

  it('never shows an internal decision reference as a heading', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: refused } })

    expect(timeline.text()).not.toContain('decision-row')
    expect(timeline.text()).toContain('Nội dung đã báo')
  })
})

describe('a promise the site has missed', () => {
  const late = statusWith({ promiseHealth: 'breached' })

  it('does not call a deadline it already missed still in effect', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: late } })

    const note = timeline.get('[data-role="promise-note"]').text()
    expect(note).toContain('đã trễ hạn')
    expect(note).not.toContain('vẫn có hiệu lực')
  })

  it('relabels the date as what was promised, not what is coming', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: late } })

    expect(timeline.get('[data-role="next-update"]').text()).toContain('Hạn đã hứa')
  })

  it('still reads as a live promise while the case is on time', () => {
    const timeline = mount(CaseStatusTimeline, { props: { status: statusWith() } })

    expect(timeline.get('[data-role="next-update"]').text()).toContain('Cập nhật trước')
    expect(timeline.find('[data-role="promise-note"]').exists()).toBe(false)
  })
})

describe('review before submit (WCAG 2.2 SC 3.3.4)', () => {
  function filled() {
    const form = mount(CorrectionIntakeForm, {
      props: { entityId: 'p-quan-com', entityName: 'Quán Cơm Bà Tư', baseEntityRevision: 7 },
    })
    return form
  }

  it('does not submit straight from the form', async () => {
    const form = filled()

    // SC 3.3.4 is Level AA and is triggered by this submission because it
    // modifies user-controllable data in a storage system — not because money
    // is involved. Claiming AA without one of reversible/checked/confirmed
    // would be claiming wrongly.
    expect(form.find('[data-role="review"]').exists()).toBe(true)
    expect(form.find('[data-role="submit"]').exists()).toBe(false)
  })

  it('shows what will be sent, and lets the reporter go back and change it', async () => {
    const form = filled()
    await form.get('#item-0-field').setValue('attributes.phone')
    await form.get('#item-0-reported').setValue('0270 111 2222')
    await form.get('#item-0-proposed').setValue('0270 333 4444')

    await form.get('[data-role="review"]').trigger('click')

    const panel = form.get('[data-role="review-panel"]')
    expect(panel.text()).toContain('Số điện thoại')
    expect(panel.get('[data-role="review-proposed"]').text()).toContain('0270 333 4444')
    // Confirmed, not merely warned: the submit button only exists here.
    expect(form.find('[data-role="submit"]').exists()).toBe(true)

    await form.get('[data-role="review-back"]').trigger('click')
    expect(form.find('[data-role="review-panel"]').exists()).toBe(false)
    expect(form.find('[data-role="submit"]').exists()).toBe(false)
  })

  it('says plainly when no phone was left', async () => {
    const form = filled()
    await form.get('#item-0-field').setValue('attributes.phone')
    await form.get('#item-0-reported').setValue('a')
    await form.get('#item-0-proposed').setValue('b')

    await form.get('[data-role="review"]').trigger('click')

    expect(form.get('[data-role="review-no-phone"]').text()).toContain('Không để lại số')
  })
})
