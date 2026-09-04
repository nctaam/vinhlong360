import { nextTick, type Ref, type ComputedRef } from 'vue'
import { serializePlanStops, type PlannerScheduleMetadata } from '~/composables/useItineraryOptimization'
import { formatDistance, formatDuration, type RouteResult } from '~/composables/useRouting'
import {
  type PlanStop,
  type SavedPlan,
  type PlanSnapshot,
  positiveRevision,
  normalizePlanSnapshot,
  conflictSnapshot,
} from '~/utils/plannerSnapshots'
import { extractErrorMessage } from '~/composables/useFetchError'

export const LS_PLANS = 'vl360_plans'

export interface UsePlannerServerPlansOptions {
  planTitle: Ref<string>
  stops: Ref<PlanStop[]>
  savedPlans: Ref<SavedPlan[]>
  saving: Ref<boolean>
  planBusy: Ref<number>
  savePulse: Ref<boolean>
  activeServerPlanId: Ref<string | null>
  baseServerRevision: Ref<number | null>
  localDraftRevision: Ref<number>
  draftSource: Ref<'local' | 'server'>
  localDirty: Ref<boolean>
  plannerRevisionConflict: Ref<PlanSnapshot | null>
  plannerDraftGeneration: Ref<number>
  revisionSafeSaveEnabled: ComputedRef<boolean> | Ref<boolean>
  plannerConflictEl: Ref<{ focus: () => void } | null>
  plannerScheduleMetadata: WeakMap<object, PlannerScheduleMetadata>
  routeResult: Ref<RouteResult | null>
  optimizationMessage: Ref<string>
  isDraftPersistenceReady: () => boolean
  setDraftPersistenceReady: (ready: boolean) => void
  persistPlannerDraft: () => void
  invalidatePlannerSchedule: () => void
  refreshPlannerStopEvidence: (stopId: string) => Promise<boolean>
  plannerMetadataForLoadedStop: (type: string) => PlannerScheduleMetadata
  clearActiveServerPlan: () => void
  advancePlannerDraftGeneration: () => void
  showToast: (msg: string, type: 'success' | 'warning' | 'error' | 'info') => void
  confirmDialog: (message: string, options?: { title?: string; confirmText?: string; cancelText?: string; danger?: boolean }) => Promise<boolean>
  isLoggedIn: Ref<boolean>
  authHeaders: () => Record<string, string>
}

export function usePlannerServerPlans(options: UsePlannerServerPlansOptions) {
  const {
    planTitle,
    stops,
    savedPlans,
    saving,
    planBusy,
    savePulse,
    activeServerPlanId,
    baseServerRevision,
    localDraftRevision,
    draftSource,
    localDirty,
    plannerRevisionConflict,
    plannerDraftGeneration,
    revisionSafeSaveEnabled,
    plannerConflictEl,
    plannerScheduleMetadata,
    routeResult,
    optimizationMessage,
    isDraftPersistenceReady,
    setDraftPersistenceReady,
    persistPlannerDraft,
    invalidatePlannerSchedule,
    refreshPlannerStopEvidence,
    plannerMetadataForLoadedStop,
    clearActiveServerPlan,
    advancePlannerDraftGeneration,
    showToast,
    confirmDialog,
    isLoggedIn,
    authHeaders,
  } = options

  let savePulseTimer: ReturnType<typeof setTimeout> | null = null

  function replaceSavedServerPlan(snapshot: PlanSnapshot) {
    const index = savedPlans.value.findIndex(plan => plan.id === snapshot.id)
    if (index < 0) return
    const currentRevision = savedPlans.value[index]?.revision
    if (!positiveRevision(currentRevision) || snapshot.revision >= currentRevision) {
      savedPlans.value.splice(index, 1, snapshot)
    }
  }

  function acceptServerComparisonBase(snapshot: PlanSnapshot) {
    advancePlannerDraftGeneration()
    replaceSavedServerPlan(snapshot)
    activeServerPlanId.value = snapshot.id
    baseServerRevision.value = snapshot.revision
    draftSource.value = 'server'
  }

  function persistLocal(plans: SavedPlan[]) {
    if (import.meta.client) {
      try { localStorage.setItem(LS_PLANS, JSON.stringify(plans.filter(p => !p.id))) } catch {}
    }
  }

  function finishSaveFeedback(title: string) {
    savePulse.value = true
    if (savePulseTimer) clearTimeout(savePulseTimer)
    savePulseTimer = setTimeout(() => { savePulse.value = false }, 220)
    showToast(`Đã lưu "${title}"${isLoggedIn.value ? ' (đồng bộ tài khoản)' : ''}`, 'success')
  }

  async function savePlan() {
    if (!stops.value.length || saving.value) return
    saving.value = true
    try { await _doSave() } finally { saving.value = false }
  }

  async function _doSave() {
    const request = {
      title: planTitle.value.trim() || 'Lịch trình chưa đặt tên',
      stops: serializePlanStops(stops.value),
      savedAt: new Date().toISOString(),
      activeServerPlanId: activeServerPlanId.value,
      baseServerRevision: baseServerRevision.value,
      draftRevision: localDraftRevision.value,
      draftSource: draftSource.value,
      conflict: plannerRevisionConflict.value,
      draftGeneration: plannerDraftGeneration.value,
    }
    const identityStillMatches = () => (
      activeServerPlanId.value === request.activeServerPlanId
      && baseServerRevision.value === request.baseServerRevision
      && draftSource.value === request.draftSource
      && plannerRevisionConflict.value === request.conflict
      && plannerDraftGeneration.value === request.draftGeneration
    )
    const discardStaleResult = () => {
      showToast('Kết quả lưu cũ đã được bỏ qua vì lịch trình đang mở đã thay đổi.', 'warning')
    }
    let plan: SavedPlan = {
      title: request.title,
      stops: request.stops,
      savedAt: request.savedAt,
    }
    if (isLoggedIn.value) {
      try {
        if (revisionSafeSaveEnabled.value && request.activeServerPlanId) {
          if (!positiveRevision(request.baseServerRevision)) {
            showToast('Không thể xác định phiên bản máy chủ. Hãy tải lại lịch trình đã lưu.', 'error')
            return
          }
          const res = await $fetch<{ plan: unknown }>(`/api/my-plans/${request.activeServerPlanId}`, {
            method: 'PUT', headers: authHeaders(),
            body: {
              title: request.title,
              stops: request.stops,
              expected_revision: request.baseServerRevision,
            },
          })
          if (!identityStillMatches()) {
            discardStaleResult()
            return
          }
          const snapshot = normalizePlanSnapshot(res.plan)
          if (!snapshot || snapshot.id !== request.activeServerPlanId) {
            showToast('Phản hồi lưu lịch trình không hợp lệ. Hãy tải lại trước khi tiếp tục.', 'error')
            return
          }
          acceptServerComparisonBase(snapshot)
          plannerRevisionConflict.value = null
          localDirty.value = localDraftRevision.value !== request.draftRevision
          persistPlannerDraft()
          finishSaveFeedback(snapshot.title)
          return
        }
        if (revisionSafeSaveEnabled.value && request.draftSource === 'server') {
          showToast('Bản nháp máy chủ thiếu thông tin phiên bản. Hãy tải lại lịch trình đã lưu trước khi lưu.', 'error')
          return
        }
        const res = await $fetch<{ id: string; revision?: number; updatedAt?: string; plan?: unknown }>('/api/my-plans', {
          method: 'POST', headers: authHeaders(),
          body: { title: request.title, stops: request.stops },
        })
        if (!identityStillMatches()) {
          discardStaleResult()
          return
        }
        const snapshot = normalizePlanSnapshot(res.plan)
        plan = snapshot || {
          ...plan,
          id: res.id,
          ...(positiveRevision(res.revision) ? { revision: res.revision } : {}),
          ...(typeof res.updatedAt === 'string' ? { updatedAt: res.updatedAt } : {}),
        }
      } catch (e: unknown) {
        if (!identityStillMatches()) {
          discardStaleResult()
          return
        }
        const snapshot = conflictSnapshot(e, request.activeServerPlanId)
        if (snapshot) {
          plannerRevisionConflict.value = snapshot
          await nextTick()
          plannerConflictEl.value?.focus()
          showToast('Bản máy chủ mới hơn cần được đối chiếu trước khi lưu.', 'warning')
          return
        }
        showToast(extractErrorMessage(e, 'Không thể lưu lên tài khoản'), 'error')
        return
      }
    } else {
      persistLocal([plan, ...savedPlans.value])
    }
    if (plan.id) {
      advancePlannerDraftGeneration()
      draftSource.value = 'server'
      activeServerPlanId.value = plan.id
      baseServerRevision.value = positiveRevision(plan.revision) ? plan.revision : null
      plannerRevisionConflict.value = null
      localDirty.value = localDraftRevision.value !== request.draftRevision
    } else {
      draftSource.value = 'local'
      clearActiveServerPlan()
      localDirty.value = false
    }
    persistPlannerDraft()
    savedPlans.value.unshift(plan)
    finishSaveFeedback(plan.title)
  }

  async function loadPlan(idx: number) {
    if (saving.value) return
    if (stops.value.length && !await confirmDialog('Thay thế lịch trình đang tạo bằng bản đã lưu?', { confirmText: 'Thay thế' })) return
    if (saving.value) return
    const plan = savedPlans.value[idx]
    if (!plan) return
    const persistenceWasReady = isDraftPersistenceReady()
    setDraftPersistenceReady(false)
    planTitle.value = plan.title
    invalidatePlannerSchedule()
    stops.value = serializePlanStops(plan.stops)
    stops.value.forEach((stop) => {
      plannerScheduleMetadata.set(stop, plannerMetadataForLoadedStop(stop.type))
    })
    draftSource.value = plan.id ? 'server' : 'local'
    localDraftRevision.value += 1
    localDirty.value = false
    if (plan.id) {
      advancePlannerDraftGeneration()
      activeServerPlanId.value = plan.id
      baseServerRevision.value = positiveRevision(plan.revision) ? plan.revision : null
      plannerRevisionConflict.value = null
    } else {
      clearActiveServerPlan()
    }
    optimizationMessage.value = ''
    await nextTick()
    setDraftPersistenceReady(persistenceWasReady)
    persistPlannerDraft()
    void Promise.all(stops.value
      .filter(stop => !stop.sourceFreshness)
      .map(stop => refreshPlannerStopEvidence(stop.id)))
  }

  async function deletePlan(idx: number) {
    if (saving.value) return
    const plan = savedPlans.value[idx]
    if (!await confirmDialog(`Xóa lịch trình "${plan?.title || 'chưa đặt tên'}"?`, { danger: true, confirmText: 'Xóa' })) return
    if (saving.value) return
    planBusy.value = idx
    try {
      if (plan?.id && isLoggedIn.value) {
        await $fetch(`/api/my-plans/${plan.id}`, { method: 'DELETE', headers: authHeaders() })
      }
      savedPlans.value.splice(idx, 1)
      if (plan?.id === activeServerPlanId.value) {
        draftSource.value = 'local'
        clearActiveServerPlan()
        persistPlannerDraft()
      }
      persistLocal(savedPlans.value)
      showToast('Đã xóa lịch trình', 'success')
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Không thể xoá trên tài khoản'), 'error')
    } finally { planBusy.value = -1 }
  }

  function publishBlockedByConflict(plan: SavedPlan): boolean {
    return Boolean(
      plannerRevisionConflict.value
      && plan.id
      && plan.id === activeServerPlanId.value,
    )
  }

  async function publishPlan(idx: number) {
    if (saving.value) return
    const plan = savedPlans.value[idx]
    if (!plan?.id) return
    if (publishBlockedByConflict(plan)) return
    if (!positiveRevision(plan.revision)) {
      showToast('Không thể xác định phiên bản máy chủ. Hãy tải lại lịch trình đã lưu.', 'error')
      return
    }
    const planId = plan.id
    const expectedRevision = plan.revision
    const conflictAtStart = plannerRevisionConflict.value
    planBusy.value = idx
    const next = !plan.is_public
    try {
      const res = await $fetch<{ is_public?: boolean; revision?: number; plan?: unknown }>(`/api/my-plans/${plan.id}/publish`, {
        method: 'POST', headers: authHeaders(), body: { is_public: next, expected_revision: expectedRevision },
      })
      const snapshot = normalizePlanSnapshot(res.plan)
      if (!snapshot || snapshot.id !== planId || snapshot.revision !== expectedRevision + 1) {
        showToast('Phản hồi đổi trạng thái không hợp lệ. Hãy tải lại trước khi tiếp tục.', 'error')
        return
      }
      replaceSavedServerPlan(snapshot)
      if (planId === activeServerPlanId.value
        && baseServerRevision.value === expectedRevision
        && plannerRevisionConflict.value === conflictAtStart) {
        advancePlannerDraftGeneration()
        baseServerRevision.value = snapshot.revision
        persistPlannerDraft()
      }
      if (snapshot.is_public && import.meta.client) {
        const link = `${location.origin}/lich-trinh-chia-se/${planId}`
        try { await navigator.clipboard?.writeText(link); showToast('Đã công khai — link đã sao chép', 'success') }
        catch { showToast('Đã công khai', 'success') }
      } else {
        showToast('Đã chuyển về riêng tư', 'success')
      }
    } catch (e: unknown) {
      const snapshot = conflictSnapshot(e, planId)
      if (snapshot) {
        if (activeServerPlanId.value === planId
          && baseServerRevision.value === expectedRevision
          && plannerRevisionConflict.value === conflictAtStart) {
          plannerRevisionConflict.value = snapshot
          await nextTick()
          plannerConflictEl.value?.focus()
          showToast('Bản máy chủ mới hơn cần được đối chiếu trước khi đổi trạng thái.', 'warning')
        } else {
          replaceSavedServerPlan(snapshot)
          showToast('Lịch trình đã thay đổi trên thiết bị khác. Hãy tải lại rồi thử lại.', 'warning')
        }
        return
      }
      showToast(extractErrorMessage(e, 'Không thể đổi trạng thái'), 'error')
    }
    finally { planBusy.value = -1 }
  }

  function sharePlan(idx: number) {
    const plan = savedPlans.value[idx]
    if (!plan) return
    const legs = routeResult.value?.legs || []
    const text = `${plan.title}\n\n` + plan.stops.map((s, i) => {
      let line = `${i + 1}. ${s.name}${s.time ? ` (${s.time})` : ''}${s.notes ? ` — ${s.notes}` : ''}`
      if (i < plan.stops.length - 1 && legs[i]) {
        line += `\n   → ${formatDistance(legs[i].distance)}, ${formatDuration(legs[i].duration)}`
      }
      return line
    }).join('\n')

    if (navigator.share) {
      navigator.share({ title: plan.title, text }).catch(() => {})
    } else if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast('Đã sao chép lịch trình vào clipboard', 'success')
      }).catch(() => {
        showToast('Không thể sao chép', 'error')
      })
    } else {
      showToast('Trình duyệt không hỗ trợ sao chép', 'error')
    }
  }

  return {
    savePlan,
    loadPlan,
    deletePlan,
    publishPlan,
    sharePlan,
    publishBlockedByConflict,
    replaceSavedServerPlan,
    acceptServerComparisonBase,
    persistLocal,
  }
}
