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
  CaseAccessError,
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
    const { fetcher, call } = recordingFetcher()
    const cases = useCorrectionCases(fetcher as any)

    await cases.requestReview('the phone number is still wrong')

    expect(call(0).options.headers['X-Case-CSRF']).toBe('token-abc')
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
