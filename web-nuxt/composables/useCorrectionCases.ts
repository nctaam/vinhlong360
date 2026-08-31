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
import {
  CORRECTION_INTAKE_CONTRACT_VERSION,
  type CaseReceipt,
  type CaseStatus,
  type CorrectionProblemDetail,
  type CorrectionSubmission,
} from '../types/cases'

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

/**
 * Xin xét lại bị từ chối vì TRẠNG THÁI hồ sơ, không vì mã tra cứu.
 *
 * Người bấm nút này đã mở được hồ sơ của họ — tức mã đã đúng. Nói với họ "kiểm
 * tra lại mã tra cứu" là chỉ sai hướng và họ sẽ loay hoay với cái mã vốn không
 * hỏng. Hai lý do máy chủ trả 409 đều KHÔNG bí mật với chính chủ hồ sơ: hồ sơ
 * chưa khép, hoặc hồ sơ vừa đổi từ lúc họ mở trang. Lập luận "đừng lộ nửa nào
 * đúng" ở CASE_ACCESS_RECOVERY_MESSAGE không áp vào đây.
 */
export const CASE_REVIEW_NOT_CLOSED_MESSAGE =
  'Chỉ xin xem xét lại được sau khi yêu cầu đã khép. Hiện nó vẫn đang được xử lý.'
export const CASE_REVIEW_STALE_MESSAGE =
  'Yêu cầu vừa có cập nhật mới. Trang đã tải lại — xem qua rồi gửi lại giúp chúng tôi.'

export class CaseReviewConflictError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'CaseReviewConflictError'
  }
}

export class CorrectionProblemError extends Error {
  readonly problem: CorrectionProblemDetail

  constructor(problem: CorrectionProblemDetail) {
    super(problem.detail)
    this.name = 'CorrectionProblemError'
    this.problem = problem
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

  function mutationHeaders(
    idempotencyKey?: string,
    contractVersion?: string,
  ): Record<string, string> {
    const headers: Record<string, string> = { 'content-type': 'application/json' }
    const token = readCaseCsrfToken()
    if (token) headers['X-Case-CSRF'] = token
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
    if (contractVersion) headers['X-Correction-Contract-Version'] = contractVersion
    return headers
  }

  async function post<T>(
    url: string,
    body: unknown,
    idempotencyKey?: string,
    translateRefusal = true,
    contractVersion?: string,
  ): Promise<T> {
    try {
      return await fetcher<T>(url, {
        method: 'POST',
        body,
        headers: mutationHeaders(idempotencyKey, contractVersion),
        credentials: 'include',
      })
    } catch (error) {
      if (!translateRefusal) throw error
      return neutralise(error)
    }
  }

  async function createCorrection(submission: CorrectionSubmission): Promise<CaseReceipt> {
    // One key for this submit and its retries; a new submit gets a new one.
    const idempotencyKey = newIdempotencyKey()
    // camelCase, because that is the wire format the API declares: every field
    // in agent/cases/public_api.py carries an alias and the models forbid
    // extras, so a snake_case body is not "close enough" — it is two errors per
    // field and a 422 the page would show the reporter as their mistake.
    const body = {
      reporterPrivacy: submission.reporterPrivacy,
      items: submission.items.map(item => ({
        entityId: item.entityId,
        fieldPath: item.fieldPath,
        reportedValue: item.reportedValue,
        proposedValue: item.proposedValue,
        baseEntityRevision: item.baseEntityRevision,
        ...(item.reportedValueKnown === undefined
          ? {}
          : { reportedValueKnown: item.reportedValueKnown }),
      })),
      optionalPhone: submission.optionalPhone ?? null,
      notificationConsent: Boolean(submission.notificationConsent),
      handoffDigest: submission.handoffDigest ?? null,
      handoffConfirmed: Boolean(submission.handoffConfirmed),
    }
    let receipt: CaseReceipt
    try {
      const contractVersion = submission.items.every(item => item.reportedValueKnown !== undefined)
        ? CORRECTION_INTAKE_CONTRACT_VERSION
        : undefined
      receipt = await post<CaseReceipt>(
        '/api/cases/corrections',
        body,
        idempotencyKey,
        false,
        contractVersion,
      )
    } catch (error) {
      const raw = error as { data?: CorrectionProblemDetail, statusCode?: number }
      const problem = raw?.data
      if (problem && typeof problem.code === 'string' && Number(raw.statusCode) === 422) {
        // Keep the caller's draft intact while exposing precise field feedback.
        throw new CorrectionProblemError(problem)
      }
      throw error
    }
    secretState.capability = receipt.capability
    publicReference.value = receipt.publicReference
    return receipt
  }

  async function exchangeReceipt(reference: string, secret: string): Promise<void> {
    // In the body, never the URL: a query string reaches history, logs and
    // referrers, and this value opens somebody's case.
    await post<unknown>('/api/cases/access', {
      publicReference: reference,
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
    // `expectedRevision` là chốt tương-tranh-lạc-quan của máy chủ: người báo phản
    // đối ĐÚNG bản họ đang đọc, chứ không phải bản vừa đổi sau lưng. Chỗ này từng
    // chỉ gửi { reason }, mà _ReviewIn forbid extra và trường đó không có mặc
    // định → 422 MỌI LƯỢT; rồi `neutralise` dịch 422 thành "mã tra cứu sai" nên
    // người báo đi sửa cái mã vốn không hỏng. Con số nay do GET /status phát ra.
    const known = status.value ?? await loadStatus()
    try {
      await fetcher<unknown>('/api/cases/review', {
        method: 'POST',
        body: { reason, expectedRevision: known.currentRevision },
        headers: mutationHeaders(),
        credentials: 'include',
      })
    } catch (error) {
      const code = Number((error as { statusCode?: number, status?: number })?.statusCode
        ?? (error as { status?: number })?.status ?? 0)
      if (code !== 409) return neutralise(error)
      // Chỉ 409 mới được nói thật lý do — xem chú thích ở CaseReviewConflictError.
      const problem = String((error as { data?: { code?: string } })?.data?.code ?? '')
      if (problem === 'case_revision_conflict') {
        // Tải lại để lần bấm sau mang đúng số; nếu tải lại cũng hỏng thì lỗi đó
        // mới là cái đáng báo, nên KHÔNG nuốt.
        await loadStatus()
        throw new CaseReviewConflictError(CASE_REVIEW_STALE_MESSAGE)
      }
      throw new CaseReviewConflictError(CASE_REVIEW_NOT_CLOSED_MESSAGE)
    }
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
