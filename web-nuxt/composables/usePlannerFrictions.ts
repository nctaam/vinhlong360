import { computed, type Ref, type ComputedRef } from 'vue'
import type { PlanStop, PlanSnapshot, OpeningHourConflict, PlannerConflictDifference } from '~/utils/plannerSnapshots'
import { diffPlannerPlanStops } from '~/utils/plannerSnapshots'
import {
  projectPlannerFrictions,
  isPlannerStopFreshnessStale,
  type PlannerFrictionNotice as PlannerFriction,
} from '~/composables/useItineraryOptimization'
import type { RouteResult } from '~/composables/useRouting'

export interface UsePlannerFrictionsOptions {
  stops: Ref<PlanStop[]>
  visibleOpeningHourConflicts: ComputedRef<OpeningHourConflict[]>
  routeResult: Ref<RouteResult | null>
  travelBudgetMinutes: Ref<number | null>
  plannerOnline: Ref<boolean>
  localDraftRevision: Ref<number>
  draftSavedAt: Ref<string | null>
  draftSource: Ref<'local' | 'server'>
  routeError: Ref<boolean>
  plannerRevisionConflict: Ref<PlanSnapshot | null>
  refreshPlannerStopEvidence: (stopId: string) => Promise<boolean>
}

export function usePlannerFrictions(options: UsePlannerFrictionsOptions) {
  const {
    stops,
    visibleOpeningHourConflicts,
    routeResult,
    travelBudgetMinutes,
    plannerOnline,
    localDraftRevision,
    draftSavedAt,
    draftSource,
    routeError,
    plannerRevisionConflict,
    refreshPlannerStopEvidence,
  } = options

  const stalePlannerStops = computed(() => stops.value
    .filter(stop => isPlannerStopFreshnessStale(stop.sourceFreshness))
    .map(stop => ({
      stopId: stop.id,
      label: stop.name || stop.id,
      status: stop.sourceFreshness?.status,
      updatedAt: stop.sourceFreshness?.updatedAt,
    })))

  const plannerFrictionNotices = computed<PlannerFriction[]>(() => projectPlannerFrictions({
    openingHourConflicts: visibleOpeningHourConflicts.value,
    travelMinutes: routeResult.value ? Math.round(routeResult.value.totalDuration / 60) : null,
    travelBudgetMinutes: travelBudgetMinutes.value,
    staleStops: stalePlannerStops.value,
    missingCoordinateStopIds: stops.value
      .filter(stop => !stop.coords)
      .map(stop => stop.name || stop.id),
    offlineDraft: plannerOnline.value ? false : {
      revision: localDraftRevision.value,
      savedAt: draftSavedAt.value,
      source: draftSource.value,
    },
    routeUnavailable: routeError.value,
  }))

  const plannerSummaryWarnings = computed(() => plannerFrictionNotices.value.map(notice => notice.reason))

  const plannerConflictDifferences = computed<PlannerConflictDifference[]>(() => (
    plannerRevisionConflict.value
      ? diffPlannerPlanStops(stops.value, plannerRevisionConflict.value.stops)
      : []
  ))

  function handleFrictionRecovery(notice: PlannerFriction) {
    if (!import.meta.client) return
    if (notice.recovery.action === 'edit-budget') {
      document.getElementById('planner-time-budget')?.focus()
      return
    }
    if (notice.recovery.action === 'edit-time') {
      document.querySelector<HTMLInputElement>('.stop-time-input')?.focus()
      return
    }
    if (notice.recovery.action === 'refresh-stop') {
      if (notice.stopId) void refreshPlannerStopEvidence(notice.stopId)
      return
    }
    if (notice.recovery.action === 'edit-stop' || notice.recovery.action === 'use-timeline') {
      document.querySelector<HTMLElement>('.stop-list, .planner-timeline-column')?.focus()
    }
  }

  return {
    stalePlannerStops,
    plannerFrictionNotices,
    plannerSummaryWarnings,
    plannerConflictDifferences,
    handleFrictionRecovery,
  }
}
