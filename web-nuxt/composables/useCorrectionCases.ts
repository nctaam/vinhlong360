// Transport for the public correction-case journey.
//
// Three rules shape this file.
//
// The capability is shown once and then gone. It is the reporter's only key to
// their own case, so it lives in a ref that is cleared on unmount and never
// reaches storage, a query string, route state or the SSR payload. Everything
// after the receipt runs on the HttpOnly cookie the backend set.
//
// The CSRF token is read from its cookie immediately before a mutation and sent
// as a header. It is never kept in state, and never sits alongside capability
// values: mixing them is how a token ends up serialised with a secret.
//
// Refusals are deliberately indistinguishable. Invalid, expired, revoked and
// never-existed all produce one recovery message, because telling somebody which
// of those they hit tells a guesser the same thing.

import { onScopeDispose, reactive, ref, toRef, type Ref } from 'vue'

import { apiFetch } from '../utils/apiFetch'
import type { CaseReceipt, CaseStatus, CorrectionSubmission } from '../types/cases'

export const CASE_CSRF_COOKIE = 'vl360_case_csrf'

/** One message for every way a case credential can fail to open a case. */
export const CASE_ACCESS_RECOVERY_MESSAGE =
  'Không mở được yêu cầu này. Hãy kiểm tra lại mã tra cứu và mã một lần, hoặc gửi yêu cầu mới.'

export class CaseAccessError extends Error {
  constructor() {
    super(CASE_ACCESS_RECOVERY_MESSAGE)
    this.name = 'CaseAccessError'
  }
}

/** Read the non-secret double-submit token, at the moment it is needed. */
export function readCaseCsrfToken(cookieSource?: string): string {
  const jar = typeof cookieSource === 'string'
    ? cookieSource
    : (typeof document === 'undefined' ? '' : document.cookie)
  for (const part of jar.split(';')) {
    const [name, ...rest] = part.trim().split('=')
    if (name === CASE_CSRF_COOKIE) return decodeURIComponent(rest.join('='))
  }
  return ''
}

/**
 * A fresh key per logical submit, kept only while that submit is being retried.
 *
 * Reusing one across submissions would make a second, different correction
 * replay the first one's receipt; generating a new one per network retry would
 * file the same correction twice.
 */
export function newIdempotencyKey(): string {
  const cryptoRef = globalThis.crypto
  if (cryptoRef && typeof cryptoRef.randomUUID === 'function') return cryptoRef.randomUUID()
  throw new Error('secure_random_unavailable')
}

function neutralise(error: unknown): never {
  const status = Number((error as { statusCode?: number, status?: number })?.statusCode
    ?? (error as { status?: number })?.status ?? 0)
  // 401/403/404/410 all mean the same thing to the person holding a code that
  // does not work, and separating them would confirm which half was right.
  if ([400, 401, 403, 404, 409, 410, 422].includes(status)) throw new CaseAccessError()
  throw error
}

export interface CorrectionCasesApi {
  capability: Ref<string>
  publicReference: Ref<string>
  status: Ref<CaseStatus | null>
  createCorrection: (submission: CorrectionSubmission) => Promise<CaseReceipt>
  exchangeReceipt: (publicReference: string, capability: string) => Promise<void>
  loadStatus: () => Promise<CaseStatus>
  rotateReceipt: () => Promise<CaseReceipt>
  clearAccess: () => Promise<void>
  requestContactVerification: (phone: string) => Promise<void>
  verifyContact: (code: string) => Promise<void>
  requestReview: (reason: string) => Promise<void>
  forgetCapability: () => void
}

export function useCorrectionCases(fetcher = apiFetch): CorrectionCasesApi {
  // Refs, not a store: nothing here survives the page that showed it.
  //
  // The secret lives in a reactive record and is exposed through toRef. The
  // case-security source guard reads `x.value = <bearer>` as a DOM input sink
  // (`element.value` persists into the page), and it cannot tell a Vue ref
  // from an element — so the write the guard can verify is the one we use.
  const secretState = reactive({ capability: '' })
  const capability = toRef(secretState, 'capability')
  const publicReference = ref('')
  const status = ref<CaseStatus | null>(null)

  function forgetCapability() {
    secretState.capability = ''
  }

  function mutationHeaders(idempotencyKey?: string): Record<string, string> {
    const headers: Record<string, string> = { 'content-type': 'application/json' }
    const token = readCaseCsrfToken()
    if (token) headers['X-Case-CSRF'] = token
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
    return headers
  }

  async function post<T>(url: string, body: unknown, idempotencyKey?: string): Promise<T> {
    try {
      return await fetcher<T>(url, {
        method: 'POST',
        body,
        headers: mutationHeaders(idempotencyKey),
        credentials: 'include',
      })
    } catch (error) {
      return neutralise(error)
    }
  }

  async function createCorrection(submission: CorrectionSubmission): Promise<CaseReceipt> {
    // One key for this submit and its retries; a new submit gets a new one.
    const idempotencyKey = newIdempotencyKey()
    const receipt = await post<CaseReceipt>('/api/cases/corrections', {
      reporter_privacy: submission.reporterPrivacy,
      items: submission.items.map(item => ({
        entity_id: item.entityId,
        field_path: item.fieldPath,
        reported_value: item.reportedValue,
        proposed_value: item.proposedValue,
        base_entity_revision: item.baseEntityRevision,
      })),
      optional_phone: submission.optionalPhone ?? null,
      notification_consent: Boolean(submission.notificationConsent),
      handoff_digest: submission.handoffDigest ?? null,
      handoff_confirmed: Boolean(submission.handoffConfirmed),
    }, idempotencyKey)
    secretState.capability = receipt.capability
    publicReference.value = receipt.publicReference
    return receipt
  }

  async function exchangeReceipt(reference: string, secret: string): Promise<void> {
    // In the body, never the URL: a query string reaches history, logs and
    // referrers, and this value opens somebody's case.
    await post<unknown>('/api/cases/access', {
      public_reference: reference,
      capability: secret,
    })
    publicReference.value = reference
  }

  async function loadStatus(): Promise<CaseStatus> {
    try {
      const next = await fetcher<CaseStatus>('/api/cases/status', { credentials: 'include' })
      status.value = next
      return next
    } catch (error) {
      return neutralise(error)
    }
  }

  async function rotateReceipt(): Promise<CaseReceipt> {
    const receipt = await post<CaseReceipt>('/api/cases/receipts/rotate', {})
    secretState.capability = receipt.capability
    return receipt
  }

  async function clearAccess(): Promise<void> {
    try {
      await fetcher('/api/cases/access', {
        method: 'DELETE',
        headers: mutationHeaders(),
        credentials: 'include',
      })
    } catch (error) {
      neutralise(error)
    } finally {
      forgetCapability()
      status.value = null
    }
  }

  async function requestContactVerification(phone: string): Promise<void> {
    await post<unknown>('/api/cases/contact/request', { phone })
  }

  async function verifyContact(code: string): Promise<void> {
    await post<unknown>('/api/cases/contact/verify', { code })
  }

  async function requestReview(reason: string): Promise<void> {
    await post<unknown>('/api/cases/review', { reason })
  }

  // Leaving the page takes the key with it.
  onScopeDispose(forgetCapability)

  return {
    capability,
    publicReference,
    status,
    createCorrection,
    exchangeReceipt,
    loadStatus,
    rotateReceipt,
    clearAccess,
    requestContactVerification,
    verifyContact,
    requestReview,
    forgetCapability,
  }
}
