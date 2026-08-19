// The public correction-case contract, in the exact names the backend sends.
//
// These mirror `status_payload` and the create response in agent/cases/public_api.py.
// Renaming a field here without renaming it there would not fail a build; it
// would quietly render an empty status to somebody waiting on an answer, so the
// names are copied deliberately rather than adapted to local taste.

export type CasePromiseHealth = 'on_track' | 'at_risk' | 'breached' | 'recovery'

export type CaseDispositionFamily =
  | 'undetermined'
  | 'action_taken'
  | 'no_action'
  | 'transferred'
  | 'withdrawn'
  | 'duplicate'

/**
 * How far a promised public change has actually got.
 *
 * `applied` and `verified` are different facts and must read differently to the
 * person waiting: the first says we wrote it, the second says somebody checked
 * that a reader can see it.
 */
export type CasePublicationState =
  | 'not_required'
  | 'pending'
  | 'applied'
  | 'verified'
  | 'rolled_back'

export interface CaseItemDecision {
  itemId: string
  outcome: string | null
  dispositionFamily: CaseDispositionFamily
}

export interface CaseItemPublication {
  itemId: string
  state: CasePublicationState
}

export interface CaseStatus {
  publicReference: string
  receivedAt: string
  currentStep: string
  waitingFor: string | null
  nextAction: string
  nextUpdateAt: string
  promiseHealth: CasePromiseHealth
  itemDecisions: CaseItemDecision[]
  itemPublicationStates: CaseItemPublication[]
  reviewPath: string
}

/**
 * The create response. `capability` is shown once and never stored.
 *
 * It is the reporter's only key to their own case, which is why it is typed as
 * part of a transient result rather than as part of any state object: nothing
 * with this field in it may be put into a store, a cookie, or the SSR payload.
 */
export interface CaseReceipt {
  publicReference: string
  capability: string
  receivedAt: string
  nextUpdateAt: string
  replayed: boolean
}

export interface CorrectionItemInput {
  entityId: string
  fieldPath: string
  reportedValue: string
  proposedValue: string
  baseEntityRevision: number
}

export interface CorrectionSubmission {
  reporterPrivacy: 'anonymous' | 'attributed'
  items: CorrectionItemInput[]
  optionalPhone?: string | null
  notificationConsent?: boolean
  handoffDigest?: string | null
  handoffConfirmed?: boolean
}

/**
 * What each publication state means to the person who reported the mistake.
 *
 * `applied` and `verified` must not read the same. Telling somebody their
 * correction is live when we have only written it, and not yet checked that a
 * reader gets it back, is a promise we have not kept. A single generic phrase
 * for everything ("Đã xử lý") hides both the difference and the waiting.
 */
export const CASE_PUBLICATION_COPY: Record<CasePublicationState, string> = {
  not_required: 'Không cần đổi nội dung công khai',
  pending: 'Đã chấp nhận, đang chờ đăng',
  applied: 'Đã sửa trong dữ liệu, đang kiểm tra trang công khai',
  verified: 'Đã hiển thị đúng trên trang công khai',
  rolled_back: 'Đã hoàn tác, yêu cầu được mở lại',
}

/** The decision on an item, which is not the same thing as a public change. */
export const CASE_DECISION_COPY: Record<CaseDispositionFamily, string> = {
  undetermined: 'Đang xem xét',
  action_taken: 'Đã chấp nhận',
  no_action: 'Không thay đổi',
  transferred: 'Đã chuyển tiếp',
  withdrawn: 'Người gửi đã rút',
  duplicate: 'Trùng với yêu cầu khác',
}
