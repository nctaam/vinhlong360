import { ref, reactive, computed, nextTick, type Ref, type ComputedRef } from 'vue'
import type { PlanStop } from '~/utils/plannerSnapshots'
import type { Entity } from '~/types'
import type { RouteResult, TransportMode } from '~/composables/useRouting'
import {
  formatScheduledInterval,
  routeLegForStopIndex,
  type PlannerInputState,
  type PlannerScheduleMetadata,
  type RoutableStop,
} from '~/composables/useItineraryOptimization'

export interface UsePlannerStopOperationsOptions {
  stops: Ref<PlanStop[]>
  allEntities: ComputedRef<Entity[]> | Ref<Entity[]>
  favList: Ref<Entity[]> | ComputedRef<Entity[]>
  transportMode: Ref<TransportMode>
  routeResult: Ref<RouteResult | null>
  currentRoutableStops: ComputedRef<RoutableStop<PlanStop>[]> | Ref<RoutableStop<PlanStop>[]>
  plannerScheduleMetadata: WeakMap<object, PlannerScheduleMetadata>
  plannerInputState: PlannerInputState
  invalidatePlannerSchedule: () => void
  optimizationMessage: Ref<string>
  stopAnnounce: Ref<string>
}

export function usePlannerStopOperations(options: UsePlannerStopOperationsOptions) {
  const {
    stops,
    allEntities,
    favList,
    transportMode,
    routeResult,
    currentRoutableStops,
    plannerScheduleMetadata,
    plannerInputState,
    invalidatePlannerSchedule,
    optimizationMessage,
    stopAnnounce,
  } = options

  const draggedStopIndex = ref<number | null>(null)
  const dragOverStopIndex = ref<number | null>(null)
  const stopAccessFactsMap = reactive(new Map<string, string>())

  function removeStop(idx: number) {
    invalidatePlannerSchedule()
    const name = stops.value[idx]?.name || ''
    stops.value.splice(idx, 1)
    optimizationMessage.value = ''
    stopAnnounce.value = ''
    nextTick(() => { stopAnnounce.value = `Đã xóa ${name}. ${stops.value.length} điểm.` })
  }

  function moveStop(idx: number, dir: number) {
    const target = idx + dir
    if (target < 0 || target >= stops.value.length) return
    const temp = stops.value[idx]
    const targetStop = stops.value[target]
    if (!temp || !targetStop) return
    invalidatePlannerSchedule()
    stops.value[idx] = targetStop
    stops.value[target] = temp
    optimizationMessage.value = ''
    stopAnnounce.value = ''
    nextTick(() => { stopAnnounce.value = `${temp.name} chuyển sang vị trí ${target + 1}.` })
  }

  function beginStopDrag(index: number, event: DragEvent) {
    draggedStopIndex.value = index
    dragOverStopIndex.value = null
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/plain', String(index))
    }
  }

  function handleStopDragOver(index: number, event: DragEvent) {
    event.preventDefault()
    if (draggedStopIndex.value !== null && draggedStopIndex.value !== index) {
      dragOverStopIndex.value = index
    }
  }

  function handleStopDragLeave(index: number) {
    if (dragOverStopIndex.value === index) {
      dragOverStopIndex.value = null
    }
  }

  function dropStop(targetIndex: number) {
    const sourceIndex = draggedStopIndex.value
    draggedStopIndex.value = null
    dragOverStopIndex.value = null
    if (sourceIndex === null || sourceIndex === targetIndex) return
    const stop = stops.value[sourceIndex]
    if (!stop) return
    invalidatePlannerSchedule()
    stops.value.splice(sourceIndex, 1)
    stops.value.splice(targetIndex, 0, stop)
    optimizationMessage.value = ''
    stopAnnounce.value = ''
    nextTick(() => { stopAnnounce.value = `${stop.name} chuyển sang vị trí ${targetIndex + 1}.` })
  }

  function endStopDrag() {
    draggedStopIndex.value = null
    dragOverStopIndex.value = null
  }

  function plannerRouteLeg(stopIndex: number) {
    return routeLegForStopIndex(
      stopIndex,
      currentRoutableStops.value,
      routeResult.value?.legs || [],
    )
  }

  function scheduledIntervalForStop(stop: PlanStop): string {
    void plannerInputState.version
    return formatScheduledInterval(plannerScheduleMetadata.get(stop)?.placement)
  }

  function stopAccessFact(stop: PlanStop): string | null {
    if (stopAccessFactsMap.has(stop.id)) {
      return stopAccessFactsMap.get(stop.id) || null
    }
    const match = (allEntities.value as Entity[]).find(e => e.id === stop.id)
      || ((favList.value || []) as any[]).find(e => e.id === stop.id)
    const access = match?.attributes?.vehicle_access || match?.attributes?.road_access
    if (access && typeof access === 'string') {
      const trimmed = access.trim()
      stopAccessFactsMap.set(stop.id, trimmed)
      return trimmed
    }
    return null
  }

  function isVehicleAccessRestricted(stop: PlanStop): boolean {
    if (transportMode.value !== 'driving') return false
    const fact = (stopAccessFact(stop) || '').toLowerCase()
    return fact.includes('chỉ xe máy') || fact.includes('không vào được ô tô') || fact.includes('hẹp')
  }

  const plannerVisitDuration = computed(() => {
    return stops.value.reduce((total, stop) => (
      total + ((plannerScheduleMetadata.get(stop)?.visitMinutes || 0) * 60)
    ), 0)
  })

  const plannerTravelDuration = computed<number | null>(() => {
    if (stops.value.length < 2) return 0
    return routeResult.value?.totalDuration ?? null
  })

  const plannerTotalDurationPartial = computed(() => (
    stops.value.length >= 2 && plannerTravelDuration.value === null
  ))

  const plannerTotalDuration = computed<number | null>(() => {
    const visitDuration = plannerVisitDuration.value
    const travelDuration = plannerTravelDuration.value
    return travelDuration === null
      ? (visitDuration > 0 ? visitDuration : null)
      : travelDuration + visitDuration
  })

  return {
    draggedStopIndex,
    dragOverStopIndex,
    stopAccessFactsMap,
    beginStopDrag,
    handleStopDragOver,
    handleStopDragLeave,
    dropStop,
    endStopDrag,
    moveStop,
    removeStop,
    plannerRouteLeg,
    scheduledIntervalForStop,
    stopAccessFact,
    isVehicleAccessRestricted,
    plannerVisitDuration,
    plannerTravelDuration,
    plannerTotalDurationPartial,
    plannerTotalDuration,
  }
}
