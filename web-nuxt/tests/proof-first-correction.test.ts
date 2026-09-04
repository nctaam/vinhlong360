import { effectScope } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import {
  CorrectionProblemError,
  useCorrectionCases,
} from '../composables/useCorrectionCases'
import CorrectionIntakeForm from '../components/cases/CorrectionIntakeForm.vue'

const receipt = {
  publicReference: 'VL-COR-0000000000001',
  capability: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefg',
  receivedAt: '2026-08-31T09:00:00+00:00',
  nextUpdateAt: '2026-09-02T09:00:00+00:00',
  replayed: false,
}

const submission = {
  reporterPrivacy: 'anonymous' as const,
  items: [{
    entityId: 'p-quan-com',
    fieldPath: 'attributes.phone',
    reportedValue: null,
    reportedValueKnown: false,
    proposedValue: '0270 333 4444',
    baseEntityRevision: 7,
  }],
}

describe('proof-first correction contract', () => {
  it('keeps a correction draft but blocks a consented phone until its OTP is proven', async () => {
    const form = mount(CorrectionIntakeForm, {
      props: {
        entityId: 'p-quan-com',
        entityName: 'Quán Cơm Bà Tư',
        baseEntityRevision: 7,
        verificationReceipt: {
          receipt: 'challenge-1',
          expiresAt: '2026-09-02T04:10:00.000Z',
          retryAfter: 60,
          verified: false,
        },
      },
    })
    await form.get('#item-0-field').setValue('attributes.phone')
    await form.get('#item-0-proposed').setValue('0270 333 4444')
    await form.get('#optional-phone').setValue('0901234567')
    await form.get('#phone-consent input').setValue(true)
    await form.get('[data-role="review"]').trigger('click')

    expect(form.get('[data-role="verification-code"]').attributes('autocomplete')).toBe('one-time-code')
    expect(form.get('[data-role="submit"]').attributes('disabled')).toBeDefined()
    expect(form.get('[data-role="verification-required"]').text()).toContain('xác nhận')

    await form.setProps({ phoneVerified: true, verifiedPhone: '0901234567' })
    expect(form.get('[data-role="submit"]').attributes('disabled')).toBeUndefined()
    expect((form.get('#item-0-proposed').element as HTMLTextAreaElement).value).toBe('0270 333 4444')
  })

  it('keeps a phone verification receipt and sends it back with the code', async () => {
    const verification = {
      receipt: 'challenge-1',
      expiresAt: '2026-09-02T04:10:00.000Z',
      retryAfter: 60,
      verified: false,
    }
    const fetcher = vi.fn()
      .mockResolvedValueOnce(verification)
      .mockResolvedValueOnce({ ...verification, verified: true })
    const cases = useCorrectionCases(fetcher as any)

    await expect(cases.startPhoneVerification('0901234567')).resolves.toMatchObject(verification)
    await expect(cases.verifyPhone('123456')).resolves.toMatchObject({ verified: true })

    expect(fetcher.mock.calls[0]![0]).toBe('/api/cases/contact/start')
    expect(fetcher.mock.calls[1]![0]).toBe('/api/cases/contact/verify')
    expect(fetcher.mock.calls[1]![1].body).toEqual({ code: '123456', receipt: 'challenge-1' })
  })

  it('shows durable OTP success and removes resend/code controls until a new verification starts', async () => {
    const form = mount(CorrectionIntakeForm, {
      props: {
        entityId: 'p-quan-com',
        entityName: 'Quán Cơm Bà Tư',
        baseEntityRevision: 7,
        verificationReceipt: {
          receipt: 'challenge-1', expiresAt: '2026-09-02T04:10:00.000Z',
          retryAfter: 0, verified: true,
        },
        phoneVerified: true,
        verifiedPhone: '0901234567',
      },
    })
    await form.get('#optional-phone').setValue('0901234567')
    await form.get('#phone-consent input').setValue(true)

    expect(form.get('[data-role="verification-success"]').text()).toContain('xác nhận')
    expect(form.find('[data-role="verification-code"]').exists()).toBe(false)
    expect(form.find('[data-role="resend-code"]').exists()).toBe(false)
  })

  it('exposes structured verification errors without losing retry metadata', async () => {
    const problem = {
      code: 'invalid_contact_code',
      detail: 'Mã xác nhận không đúng.',
      status: 422,
      field: 'code',
      correlation_id: 'corr-otp',
      retry_after: 30,
    }
    const fetcher = vi.fn(async () => {
      throw Object.assign(new Error('invalid'), { statusCode: 422, data: problem })
    })
    const cases = useCorrectionCases(fetcher as any)

    await expect(cases.startPhoneVerification('0901234567')).rejects.toMatchObject({
      name: 'CorrectionProblemError',
      problem,
    })
  })

  it('turns a network verification failure into a safe retryable problem', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce({
        receipt: 'challenge-1', expiresAt: '2026-09-02T04:10:00.000Z', retryAfter: 60, verified: false,
      })
      .mockRejectedValueOnce(new Error('socket details must not reach UI'))
    const cases = useCorrectionCases(fetcher as any)
    await cases.startPhoneVerification('0901234567')

    await expect(cases.verifyPhone('123456')).rejects.toMatchObject({
      name: 'CorrectionProblemError',
      problem: {
        code: 'verification_unavailable',
        status: 503,
        retry_after: 30,
      },
    })
    expect(cases.verificationError.value?.detail).not.toContain('socket')
  })

  it('sends the explicit current-value discriminator', async () => {
    const fetcher = vi.fn(async () => receipt)
    const scope = effectScope()
    let cases!: ReturnType<typeof useCorrectionCases>
    scope.run(() => { cases = useCorrectionCases(fetcher as any) })

    await cases.createCorrection(submission)

    const call = fetcher.mock.calls[0] as unknown as [string, { body: { items: Array<Record<string, unknown>> }, headers: Record<string, string> }]
    const item = call[1].body.items[0]
    expect(item).toMatchObject({
      reportedValue: null,
      reportedValueKnown: false,
    })
    expect(call[1].headers['X-Correction-Contract-Version']).toBe('1')
    scope.stop()
  })

  it('keeps legacy submissions headerless while canonical submissions carry a version', async () => {
    const fetcher = vi.fn(async () => receipt)
    const cases = useCorrectionCases(fetcher as any)
    const { reportedValueKnown: _legacyDiscriminator, ...legacyItem } = submission.items[0]!
    await cases.createCorrection({
      ...submission,
      items: [legacyItem],
    })
    const call = fetcher.mock.calls[0] as unknown[] | undefined
    if (!call) throw new Error('fetcher was not called')
    const options = call[1] as { headers: Record<string, string> }
    expect(options.headers['X-Correction-Contract-Version']).toBeUndefined()
  })

  it('keeps the caller draft and exposes field-level 422 problem details', async () => {
    const problem = {
      code: 'invalid_request',
      detail: 'That request body is not accepted.',
      status: 422,
      field: 'items.0.reportedValueKnown',
      correlation_id: 'corr-422',
    }
    const fetcher = vi.fn(async () => {
      throw Object.assign(new Error('invalid'), { statusCode: 422, data: problem })
    })
    const cases = useCorrectionCases(fetcher as any)

    await expect(cases.createCorrection(submission)).rejects.toMatchObject({
      name: 'CorrectionProblemError',
      problem,
    })
    expect(submission.items[0]).toEqual({
      entityId: 'p-quan-com',
      fieldPath: 'attributes.phone',
      reportedValue: null,
      reportedValueKnown: false,
      proposedValue: '0270 333 4444',
      baseEntityRevision: 7,
    })
    expect(CorrectionProblemError).toBeTypeOf('function')
  })
})
