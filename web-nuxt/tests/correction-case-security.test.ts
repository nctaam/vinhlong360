// The reporter's key must not outlive the screen that showed it.
//
// A capability opens somebody's case. Anywhere it lingers — storage, a query
// string, route state, the SSR payload, telemetry — is somewhere it can be read
// by the next person on that browser, or by anything that scrapes a URL. These
// tests describe the places it must never reach.

import { effectScope } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import {
  CASE_ACCESS_RECOVERY_MESSAGE,
  CASE_REVIEW_NOT_CLOSED_MESSAGE,
  CaseAccessError,
  CaseReviewConflictError,
  newIdempotencyKey,
  readCaseCsrfToken,
  useCorrectionCases,
} from '../composables/useCorrectionCases'

const RECEIPT = {
  publicReference: 'VL-COR-0000000000001',
  capability: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefg',
  receivedAt: '2026-08-19T09:00:00+00:00',
  nextUpdateAt: '2026-08-21T09:00:00+00:00',
  replayed: false,
}

const SUBMISSION = {
  reporterPrivacy: 'anonymous' as const,
  items: [{
    entityId: 'p-quan-com',
    fieldPath: 'attributes.phone',
    reportedValue: '0270 111 2222',
    proposedValue: '0270 333 4444',
    baseEntityRevision: 7,
  }],
}

function recordingFetcher(response: unknown = RECEIPT) {
  const calls: Array<{ url: string, options: Record<string, any> }> = []
  const fetcher = vi.fn(async (url: string, options: Record<string, any> = {}) => {
    calls.push({ url, options })
    return response as any
  })
  const call = (index: number) => {
    const entry = calls[index]
    if (!entry) throw new Error(`no request was made at index ${index}`)
    return entry
  }
  return { fetcher, calls, call }
}

function failingFetcher(statusCode: number) {
  return vi.fn(async () => {
    throw Object.assign(new Error('nope'), { statusCode })
  })
}

describe('the one-time capability', () => {
  it('is never put into a query string', async () => {
    const { fetcher, call } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.exchangeReceipt(RECEIPT.publicReference, RECEIPT.capability)

    // A URL reaches history, referrers and access logs. The body does not.
    expect(call(0).url).toBe('/api/cases/access')
    expect(call(0).url).not.toContain(RECEIPT.capability)
    expect(call(0).options.body).toMatchObject({ capability: RECEIPT.capability })
  })

  it('is never written to local or session storage', async () => {
    const local = vi.spyOn(Storage.prototype, 'setItem')
    const { fetcher } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.createCorrection(SUBMISSION)

    // Storage survives the tab, the visit and the next person on the device.
    expect(local).not.toHaveBeenCalled()
    local.mockRestore()
  })

  it('is dropped when the screen holding it goes away', async () => {
    const { fetcher } = recordingFetcher()
    const scope = effectScope()
    let cases!: ReturnType<typeof useCorrectionCases>
    scope.run(() => { cases = useCorrectionCases(fetcher as any) })

    await cases.createCorrection(SUBMISSION)
    expect(cases.capability.value).toBe(RECEIPT.capability)
    scope.stop()

    expect(cases.capability.value).toBe('')
  })

  it('can be forgotten as soon as it has been read out', async () => {
    const { fetcher } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)
    await cases.createCorrection(SUBMISSION)

    cases.forgetCapability()

    expect(cases.capability.value).toBe('')
    expect(cases.publicReference.value).toBe(RECEIPT.publicReference)
  })

  it('goes away with the session when access is cleared', async () => {
    const { fetcher } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)
    await cases.createCorrection(SUBMISSION)

    await cases.clearAccess()

    expect(cases.capability.value).toBe('')
    expect(cases.status.value).toBeNull()
  })
})

describe('reading status', () => {
  it('carries no credential of its own, only the cookie', async () => {
    const { fetcher, call } = recordingFetcher({ publicReference: 'VL-COR-0000000000001' })
    const cases = useCorrectionCases(fetcher as any)

    await cases.loadStatus()

    expect(call(0).url).toBe('/api/cases/status')
    expect(JSON.stringify(call(0).options)).not.toContain(RECEIPT.capability)
    expect(call(0).options.credentials).toBe('include')
  })
})

describe('cross-site request tokens', () => {
  it('are read from the cookie at the moment of the mutation', () => {
    const jar = `other=1; vl360_case_csrf=token-abc; another=2`

    expect(readCaseCsrfToken(jar)).toBe('token-abc')
    expect(readCaseCsrfToken('nothing=here')).toBe('')
  })

  it('travel as a header on mutations', async () => {
    const jar = 'vl360_case_csrf=token-abc'
    vi.spyOn(document, 'cookie', 'get').mockReturnValue(jar)
    const { fetcher, call, calls } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.requestReview('the phone number is still wrong')

    // Neo theo LỜI GỌI GHI, không theo chỉ số. requestReview nay đọc /status
    // trước để lấy `currentRevision` (chốt tương-tranh-lạc-quan của máy chủ),
    // nên POST không còn là lời gọi thứ nhất; ghim index 0 sẽ soi nhầm sang
    // lượt GET vốn không mang header CSRF.
    const mutation = calls.find(entry => entry.options.method === 'POST')
    expect(mutation, 'không có lời gọi POST nào để soi').toBeTruthy()
    expect(mutation!.options.headers['X-Case-CSRF']).toBe('token-abc')
    expect(call(0).url).toBe('/api/cases/status')
    vi.restoreAllMocks()
  })

  it('are not kept anywhere between mutations', async () => {
    const { fetcher } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.requestReview('again')

    // Nothing on the returned surface holds it; it is read fresh every time.
    expect(JSON.stringify(Object.keys(cases))).not.toContain('csrf')
  })
})

describe('idempotency keys', () => {
  it('are a fresh random value per logical submit', async () => {
    const { fetcher, call } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.createCorrection(SUBMISSION)
    await cases.createCorrection(SUBMISSION)

    const first = call(0).options.headers['Idempotency-Key']
    const second = call(1).options.headers['Idempotency-Key']
    expect(first).toMatch(/^[0-9a-f-]{36}$/)
    // A reused key would replay the first receipt for a different correction.
    expect(second).not.toBe(first)
  })

  it('refuse to fall back to a guessable source of randomness', () => {
    vi.stubGlobal('crypto', undefined)

    // Math.random() keys would be guessable, and a guessed key replays somebody
    // else's receipt. Failing loudly is the only safe answer here.
    expect(() => newIdempotencyKey()).toThrow('secure_random_unavailable')

    vi.unstubAllGlobals()
  })
})

describe('refusals', () => {
  it.each([400, 401, 403, 404, 409, 410, 422])('read the same for %i', async status => {
    const cases = useCorrectionCases(failingFetcher(status) as any)

    await expect(cases.loadStatus()).rejects.toBeInstanceOf(CaseAccessError)
    await expect(cases.loadStatus()).rejects.toThrow(CASE_ACCESS_RECOVERY_MESSAGE)
  })

  it('do not say which of expired, revoked or never-existed happened', () => {
    const message = CASE_ACCESS_RECOVERY_MESSAGE.toLowerCase()

    for (const word of ['hết hạn', 'thu hồi', 'không tồn tại', 'sai mã']) {
      expect(message).not.toContain(word)
    }
  })

  it('let a server fault through rather than dressing it as a bad code', async () => {
    const cases = useCorrectionCases(failingFetcher(500) as any)

    // Telling somebody their code is wrong when our own service broke sends
    // them to re-enter a code that was fine.
    await expect(cases.loadStatus()).rejects.not.toBeInstanceOf(CaseAccessError)
  })
})

describe('xin xét lại', () => {
  const STATUS = {
    publicReference: 'VL-COR-0000000000001',
    receivedAt: '2026-08-19T09:00:00+00:00',
    currentStep: 'closed',
    waitingFor: null,
    nextAction: 'Yêu cầu đã khép.',
    nextUpdateAt: '2026-08-21T09:00:00+00:00',
    promiseHealth: 'on_track',
    itemDecisions: [],
    itemPublicationStates: [],
    reviewPath: '/api/cases/review',
    currentRevision: 5,
  }

  it('gửi kèm expectedRevision lấy đúng từ bản trạng thái đang đọc', async () => {
    // Bug tới 2026-08-30: chỗ này chỉ gửi { reason }, mà _ReviewIn khai
    // `expectedRevision` bắt buộc + forbid extra → 422 MỌI LƯỢT, rồi neutralise
    // dịch 422 thành "mã tra cứu sai" nên người báo đi sửa cái mã không hỏng.
    const { fetcher, calls } = recordingFetcher(STATUS)
    const cases = useCorrectionCases(fetcher as any)

    await cases.requestReview('reporter_requested')

    const mutation = calls.find(entry => entry.url === '/api/cases/review')
    expect(mutation, 'không có lời gọi POST /api/cases/review').toBeTruthy()
    expect(mutation!.options.body).toEqual({
      reason: 'reporter_requested',
      expectedRevision: 5,
    })
  })

  it('không dịch 409 thành "mã tra cứu sai" — người bấm nút đã mở được hồ sơ', async () => {
    // 409 nói về TRẠNG THÁI hồ sơ, không về mã. Gộp nó vào câu hướng dẫn kiểm
    // tra mã là chỉ sai hướng, và người báo sẽ loay hoay với cái mã vẫn tốt.
    let da_doc_trang_thai = false
    const fetcher = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (options.method !== 'POST') { da_doc_trang_thai = true; return STATUS as any }
      throw Object.assign(new Error('nope'), {
        statusCode: 409, data: { code: 'review_requires_a_closed_case' },
      })
    })
    const cases = useCorrectionCases(fetcher as any)

    await expect(cases.requestReview('reporter_requested'))
      .rejects.toBeInstanceOf(CaseReviewConflictError)
    await expect(cases.requestReview('reporter_requested'))
      .rejects.toThrow(CASE_REVIEW_NOT_CLOSED_MESSAGE)
    expect(da_doc_trang_thai).toBe(true)
  })

  it('vẫn giấu như cũ với 401/403/404/410 — đó mới là chuyện của mã', async () => {
    for (const statusCode of [401, 403, 404, 410]) {
      const fetcher = vi.fn(async (_url: string, options: Record<string, any> = {}) => {
        if (options.method !== 'POST') return STATUS as any
        throw Object.assign(new Error('nope'), { statusCode })
      })
      const cases = useCorrectionCases(fetcher as any)

      await expect(cases.requestReview('reporter_requested'))
        .rejects.toBeInstanceOf(CaseAccessError)
    }
  })
})

describe('the wire format', () => {
  it('sends the field names the API actually declares', async () => {
    const { fetcher, call } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.createCorrection(SUBMISSION)
    await cases.exchangeReceipt('VL-COR-0000000000001', 'A'.repeat(43))

    // Every field in agent/cases/public_api.py carries a camelCase alias and the
    // models forbid extras, so snake_case is not a near miss — it is a 422 for
    // the whole submission, which the page can only show the reporter as their
    // own mistake. This shipped that way until an audit walked the two sides.
    const create = call(0).options.body as Record<string, unknown>
    expect(Object.keys(create)).toEqual(expect.arrayContaining([
      'reporterPrivacy', 'optionalPhone', 'notificationConsent',
      'handoffDigest', 'handoffConfirmed',
    ]))
    expect(Object.keys(create)).not.toEqual(expect.arrayContaining(['reporter_privacy']))
    expect(Object.keys((create.items as Record<string, unknown>[])[0]!)).toEqual([
      'entityId', 'fieldPath', 'reportedValue', 'proposedValue', 'baseEntityRevision',
    ])

    const access = call(1).options.body as Record<string, unknown>
    expect(access).toHaveProperty('publicReference')
    expect(access).not.toHaveProperty('public_reference')
  })
})
