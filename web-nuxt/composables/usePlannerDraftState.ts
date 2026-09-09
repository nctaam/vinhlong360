import { ref, watch, nextTick, type Ref } from 'vue'
import {
  type PlanStop,
  type PlanSnapshot,
  positiveRevision,
  plannerStopFromDraft,
} from '~/utils/plannerSnapshots'
import {
  serializePlanStops,
  createPlannerDraftSnapshot,
  parsePlannerDraftSnapshot,
  type PlannerInputState,
  type PlannerScheduleMetadata,
} from '~/composables/useItineraryOptimization'

export const LS_DRAFT = 'vl360_planner_draft'

export interface UsePlannerDraftStateOptions {
  planTitle: Ref<string>
  stops: Ref<PlanStop[]>
  travelBudgetMinutes: Ref<number | null>
  plannerScheduleMetadata: WeakMap<object, PlannerScheduleMetadata>
  plannerInputState: PlannerInputState
  plannerMetadataForLoadedStop: (type: string) => PlannerScheduleMetadata
  invalidatePlannerSchedule: () => void
  saving: Ref<boolean>
  acceptServerComparisonBase: (snapshot: PlanSnapshot) => void
}

export function usePlannerDraftState(options: UsePlannerDraftStateOptions) {
  const {
    planTitle,
    stops,
    travelBudgetMinutes,
    plannerScheduleMetadata,
    plannerInputState,
    plannerMetadataForLoadedStop,
    invalidatePlannerSchedule,
    saving,
    acceptServerComparisonBase,
  } = options

  const plannerOnline = ref(true)
  const draftSavedAt = ref<string | null>(null)
  const draftSource = ref<'local' | 'server'>('local')
  const localDraftRevision = ref(0)
  const localDirty = ref(false)
  const activeServerPlanId = ref<string | null>(null)
  const baseServerRevision = ref<number | null>(null)
  const plannerRevisionConflict = ref<PlanSnapshot | null>(null)
  const plannerDraftGeneration = ref(0)
  const plannerConflictEl = ref<{ focus: () => void } | null>(null)
  const draftPersistenceReady = ref(false)

  function isDraftPersistenceReady(): boolean {
    return draftPersistenceReady.value
  }

  function setDraftPersistenceReady(ready: boolean): void {
    draftPersistenceReady.value = ready
  }

  function advancePlannerDraftGeneration() {
    plannerDraftGeneration.value += 1
  }

  function clearActiveServerPlan() {
    advancePlannerDraftGeneration()
    activeServerPlanId.value = null
    baseServerRevision.value = null
    plannerRevisionConflict.value = null
  }

  function persistPlannerDraft() {
    if (!import.meta.client) return
    const savedAt = new Date().toISOString()
    draftSavedAt.value = savedAt
    try {
      localStorage.setItem(LS_DRAFT, JSON.stringify(createPlannerDraftSnapshot({
        title: planTitle.value,
        stops: stops.value,
        revision: localDraftRevision.value,
        savedAt,
        source: draftSource.value,
        travelBudgetMinutes: travelBudgetMinutes.value,
        serverPlanId: activeServerPlanId.value,
        serverRevision: baseServerRevision.value,
      })))
    } catch { /* local storage is an optional offline cache */ }
  }

  function restorePlannerDraft() {
    if (!import.meta.client || stops.value.length) return
    try {
      const raw = localStorage.getItem(LS_DRAFT)
      if (!raw) return
      const parsed = parsePlannerDraftSnapshot(JSON.parse(raw))
      if (!parsed?.stops.length) return
      stops.value = parsed.stops.map(stop => plannerStopFromDraft(stop))
      planTitle.value = parsed.title
      localDraftRevision.value = parsed.revision
      plannerInputState.version = localDraftRevision.value
      draftSavedAt.value = parsed.savedAt
      draftSource.value = parsed.source
      if (parsed.serverPlanId && positiveRevision(parsed.serverRevision)) {
        activeServerPlanId.value = parsed.serverPlanId
        baseServerRevision.value = parsed.serverRevision
      } else {
        activeServerPlanId.value = null
        baseServerRevision.value = null
      }
      travelBudgetMinutes.value = parsed.travelBudgetMinutes
      localDirty.value = true
      stops.value.forEach((stop) => {
        plannerScheduleMetadata.set(stop, plannerMetadataForLoadedStop(stop.type))
      })
    } catch { /* malformed draft is ignored without blocking the timeline */ }
  }

  function updatePlannerConnectivity() {
    if (!import.meta.client) return
    plannerOnline.value = navigator.onLine
  }

  async function choosePlannerConflict(choice: 'local' | 'server' | 'manual') {
    if (saving.value) return
    if (choice === 'manual') {
      await nextTick()
      plannerConflictEl.value?.focus()
      return
    }
    const snapshot = plannerRevisionConflict.value
    if (!snapshot) return
    const persistenceWasReady = draftPersistenceReady.value
    draftPersistenceReady.value = false
    acceptServerComparisonBase(snapshot)
    if (choice === 'server') {
      invalidatePlannerSchedule()
      planTitle.value = snapshot.title
      stops.value = serializePlanStops(snapshot.stops) as PlanStop[]
      stops.value.forEach(stop => plannerScheduleMetadata.set(stop, plannerMetadataForLoadedStop(stop.type)))
      localDraftRevision.value += 1
      localDirty.value = false
    } else {
      localDirty.value = true
    }
    plannerRevisionConflict.value = null
    await nextTick()
    draftPersistenceReady.value = persistenceWasReady
    persistPlannerDraft()
  }

  watch([planTitle, stops, travelBudgetMinutes], () => {
    if (!draftPersistenceReady.value) return
    localDraftRevision.value += 1
    localDirty.value = true
    persistPlannerDraft()
  }, { deep: true })

  return {
    plannerOnline,
    draftSavedAt,
    draftSource,
    localDraftRevision,
    localDirty,
    activeServerPlanId,
    baseServerRevision,
    plannerRevisionConflict,
    plannerDraftGeneration,
    plannerConflictEl,
    draftPersistenceReady,
    isDraftPersistenceReady,
    setDraftPersistenceReady,
    advancePlannerDraftGeneration,
    clearActiveServerPlan,
    persistPlannerDraft,
    restorePlannerDraft,
    updatePlannerConnectivity,
    choosePlannerConflict,
  }
}
