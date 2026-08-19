// Transport for the correction workbench.
//
// Two rules carry this file. Every command that changes anything sends the
// revision the operator was looking at, and a 409 never retries blind: the
// current snapshot is reloaded and surfaced, and the person decides whether
// their action still applies to what is now on screen.
//
// Hiding a button is never authorization. The composable exposes what the
// server allowed and always forwards the server's refusal; the UI may tidy the
// surface, but the backend's answer is the only one that counts.

import { ref, type Ref } from 'vue'

import { apiFetch } from '../utils/apiFetch'

export interface AdminQueueItem {
  work_item_id: string
  case_id: string
  kind: string
  risk_class: string
  status: string
  revision: number
  promise_health?: string
  owner_ref?: string | null
}

export interface AdminCaseItem {
  item_id: string
  entity_id: string
  field_path: string
  risk_class: string
  evidence_level: string
  publication_state: string
}

export interface AdminCaseChangeSet {
  change_set_id: string
  apply_status: string
  risk_class: string
  base_entity_revision: number
}

export interface AdminCaseDetail {
  case_id: string
  phase: string
  activity: string
  disposition_family: string
  current_revision: number
  promise_health: string
  items: AdminCaseItem[]
  change_set?: AdminCaseChangeSet | null
}

/** A 409 carries the truth the screen no longer shows. */
export class RevisionConflictError extends Error {
  constructor(public readonly detail: unknown) {
    super('case_revision_conflict')
    this.name = 'RevisionConflictError'
  }
}

function statusOf(error: unknown): number {
  return Number((error as { statusCode?: number })?.statusCode
    ?? (error as { status?: number })?.status ?? 0)
}

export interface AdminCasesApi {
  queue: Ref<AdminQueueItem[]>
  current: Ref<AdminCaseDetail | null>
  stepUpSecret: Ref<string>
  loadQueue: (kind?: string) => Promise<void>
  openCase: (caseId: string) => Promise<AdminCaseDetail>
  claim: (workItemId: string, expectedRevision: number) => Promise<void>
  heartbeat: (workItemId: string) => Promise<void>
  release: (workItemId: string) => Promise<void>
  takeover: (workItemId: string, reason: string) => Promise<void>
  recuse: (workItemId: string, reason: string) => Promise<void>
  stepUp: (caseId: string) => Promise<void>
  dropStepUp: (caseId: string) => Promise<void>
  addEvidence: (body: Record<string, unknown>) => Promise<void>
  createAssisted: (body: Record<string, unknown>) => Promise<unknown>
  decide: (body: Record<string, unknown>) => Promise<void>
  buildChangeSet: (body: Record<string, unknown>) => Promise<void>
  applyChangeSet: (body: Record<string, unknown>) => Promise<unknown>
  verifyChangeSet: (body: Record<string, unknown>) => Promise<unknown>
  rollbackChangeSet: (body: Record<string, unknown>) => Promise<unknown>
}

export function useAdminCases(fetcher = apiFetch): AdminCasesApi {
  const queue = ref<AdminQueueItem[]>([])
  const current = ref<AdminCaseDetail | null>(null)
  // Held in memory for the fifteen minutes it lives, and nowhere else.
  const stepUpSecret = ref('')

  async function command<T>(url: string, body: Record<string, unknown>): Promise<T> {
    try {
      return await fetcher<T>(url, { method: 'POST', body, credentials: 'include' })
    } catch (error) {
      if (statusOf(error) === 409) {
        // The screen is stale. Reload the truth and hand the decision back to
        // the person; a silent retry would apply their action to a case they
        // have not read.
        if (current.value) await openCase(current.value.case_id).catch(() => {})
        throw new RevisionConflictError((error as { data?: unknown })?.data)
      }
      throw error
    }
  }

  async function loadQueue(kind?: string): Promise<void> {
    const query = kind ? `?kind=${encodeURIComponent(kind)}` : ''
    const page = await fetcher<{ items: AdminQueueItem[] }>(
      `/admin/cases${query}`, { credentials: 'include' },
    )
    queue.value = page.items
  }

  async function openCase(caseId: string): Promise<AdminCaseDetail> {
    const detail = await fetcher<AdminCaseDetail>(
      `/admin/cases/${encodeURIComponent(caseId)}`, { credentials: 'include' },
    )
    current.value = detail
    return detail
  }

  return {
    queue,
    current,
    stepUpSecret,
    loadQueue,
    openCase,
    claim: (workItemId, expectedRevision) => command('/admin/cases/work/claim', {
      work_item_id: workItemId, expected_revision: expectedRevision,
    }),
    heartbeat: workItemId => command('/admin/cases/work/heartbeat', { work_item_id: workItemId }),
    release: workItemId => command('/admin/cases/work/release', { work_item_id: workItemId }),
    takeover: (workItemId, reason) => command('/admin/cases/work/takeover', {
      work_item_id: workItemId, reason,
    }),
    recuse: (workItemId, reason) => command('/admin/cases/work/recuse', {
      work_item_id: workItemId, reason,
    }),
    stepUp: async (caseId) => {
      const grant = await command<{ access: string }>('/admin/cases/access/step-up', {
        case_id: caseId,
      })
      stepUpSecret.value = grant.access
    },
    dropStepUp: async (caseId) => {
      try {
        await fetcher(`/admin/cases/access/step-up?case_id=${encodeURIComponent(caseId)}`, {
          method: 'DELETE', credentials: 'include',
        })
      } finally {
        stepUpSecret.value = ''
      }
    },
    addEvidence: body => command('/admin/cases/evidence', body),
    createAssisted: body => command('/admin/cases/assisted/corrections', body),
    decide: body => command('/admin/cases/decisions', body),
    buildChangeSet: body => command('/admin/cases/change-sets', body),
    applyChangeSet: body => command('/admin/cases/change-sets/apply', body),
    verifyChangeSet: body => command('/admin/cases/change-sets/verify', body),
    rollbackChangeSet: body => command('/admin/cases/change-sets/rollback', body),
  }
}
