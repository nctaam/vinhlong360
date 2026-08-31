import { effectScope } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import {
  CorrectionProblemError,
  useCorrectionCases,
} from '../composables/useCorrectionCases'

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
