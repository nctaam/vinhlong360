import { ref, computed, watch, nextTick, getCurrentInstance, onBeforeUnmount, type Ref, type ComputedRef } from 'vue'
import {
  fetchRoute,
  fetchRouteTable,
  resolvePlannerRouteSurface,
  type TransportMode,
  type RouteResult,
} from '~/composables/useRouting'
import {
  applySchedulePlacements,
  collectRoutableStops,
  commitPlannerOptimizationResult,
  createSuspendedRouteScheduler,
  invalidatePlannerInputs,
  mergeOptimizedStops,
  requestOptimizedOrder,
  runPlannerOptimization,
  createPlannerOptimizationPreview,
  type PlannerInputState,
  type PlannerOptimizationPreview as PlannerPreviewTransaction,
  type CurrentPlannerOptimizationResult,
  type RoutableStop,
  type PlannerScheduleMetadata,
} from '~/composables/useItineraryOptimization'
import type { PlanStop, OpeningHourConflict } from '~/utils/plannerSnapshots'
import {
  optimizationTradeoffs,
  openingHourConflictsFor,
} from '~/utils/plannerTradeoffs'
import { extractErrorMessage } from '~/composables/useFetchError'

export interface UsePlannerRouteOptimizationOptions {
  stops: Ref<PlanStop[]>
  transportMode: Ref<TransportMode>
  plannerScheduleMetadata: WeakMap<object, PlannerScheduleMetadata>
  plannerInputState: PlannerInputState
  itineraryScheduleV2: boolean
  optimizerEnabled: ComputedRef<boolean> | Ref<boolean>
  isPlannerLifecycleActive?: () => boolean
  updateMap: (result: RouteResult | null) => Promise<void>
  showToast: (msg: string, type: 'success' | 'warning' | 'error' | 'info') => void
  stopAnnounce: Ref<string>
}

export function usePlannerRouteOptimization(options: UsePlannerRouteOptimizationOptions) {
  const {
    stops,
    transportMode,
    plannerScheduleMetadata,
    plannerInputState,
    itineraryScheduleV2,
    optimizerEnabled,
    isPlannerLifecycleActive = () => true,
    updateMap,
    showToast,
    stopAnnounce,
  } = options

  const routeError = ref(false)
  const routeResult = ref<RouteResult | null>(null)
  const routeLoading = ref(false)
  const optimizing = ref(false)
  const optimizationMessage = ref('')
  const optimizationPreview = ref<PlannerPreviewTransaction<PlanStop> | null>(null)
  let pendingOptimization: {
    result: CurrentPlannerOptimizationResult<PlanStop>
    routed: RoutableStop<PlanStop>[]
  } | null = null
  const suspendAutoRoute = ref(false)
  let latestAutoRouteRequest: number | null = null
  const candidateOpeningHourConflicts = ref<OpeningHourConflict[]>([])
  const confirmedOpeningHourConflicts = ref<OpeningHourConflict[]>([])

  const currentRoutableStops = computed(() => collectRoutableStops(stops.value))

  const canOptimizeRoute = computed(() => {
    if (!optimizerEnabled.value) return false
    const routed = currentRoutableStops.value
    return routed.length >= 3
      && routed[0]?.originalIndex === 0
      && routed[routed.length - 1]?.originalIndex === stops.value.length - 1
  })

  const optimizeRouteTitle = computed(() => {
    if (!optimizerEnabled.value) return 'Tối ưu nâng cao đang tạm tắt; bạn vẫn có thể chỉnh và lưu lịch trình'
    if (stops.value.length < 3) return 'Cần ít nhất 3 điểm để tối ưu thứ tự'
    if (currentRoutableStops.value.length < 3) return 'Cần ít nhất 3 điểm có tọa độ'
    if (!canOptimizeRoute.value) return 'Điểm đầu và điểm cuối cần có tọa độ hợp lệ'
    return 'Giữ nguyên điểm đầu, điểm cuối và tối ưu các điểm ở giữa'
  })

  const visibleOpeningHourConflicts = computed(() => (
    optimizationPreview.value
      ? candidateOpeningHourConflicts.value
      : confirmedOpeningHourConflicts.value
  ))

  function clearPendingOptimizationPreview() {
    optimizationPreview.value = null
    pendingOptimization = null
    candidateOpeningHourConflicts.value = []
  }

  function invalidatePlannerSchedule() {
    clearPendingOptimizationPreview()
    confirmedOpeningHourConflicts.value = []
    invalidatePlannerInputs(
      plannerInputState,
      stops.value,
      plannerScheduleMetadata,
    )
  }

  async function announceOptimization(message: string) {
    optimizationMessage.value = message
    if (!isPlannerLifecycleActive()) return
    stopAnnounce.value = ''
    await nextTick()
    if (isPlannerLifecycleActive()) stopAnnounce.value = message
  }

  async function optimizePlanRoute() {
    if (!canOptimizeRoute.value || optimizing.value) {
      optimizationMessage.value = optimizeRouteTitle.value
      return
    }

    const routed = currentRoutableStops.value
    optimizing.value = true
    suspendAutoRoute.value = true
    routeLoading.value = true
    routeError.value = false
    clearPendingOptimizationPreview()
    optimizationMessage.value = ''
    autoRouteScheduler.cancelScheduled()

    try {
      const plannerResult = await runPlannerOptimization({
        scheduleEnabled: itineraryScheduleV2,
        routed,
        metadataByStop: plannerScheduleMetadata,
        inputState: plannerInputState,
        mode: transportMode.value,
        fetchTable: (coordinates, mode) => fetchRouteTable(coordinates, mode),
        requestOptimization: (ordered, blockedEdges, schedule) => schedule
          ? requestOptimizedOrder(ordered, blockedEdges, schedule)
          : requestOptimizedOrder(ordered, blockedEdges),
        route: coordinates => fetchRoute(coordinates, transportMode.value),
      })
      if (!isPlannerLifecycleActive() || plannerResult.status === 'stale') return

      const candidateStops = mergeOptimizedStops(
        stops.value,
        routed,
        plannerResult.outcome.ordered.map(item => item.key),
      )
      pendingOptimization = { result: plannerResult, routed }
      candidateOpeningHourConflicts.value = openingHourConflictsFor(plannerResult, routed, plannerScheduleMetadata)
      optimizationPreview.value = await createPlannerOptimizationPreview(
        stops.value,
        candidateStops,
        { tradeoffs: optimizationTradeoffs(plannerResult, routed, stops.value.length, itineraryScheduleV2) },
      )
      await announceOptimization('Đã tạo bản xem trước. Thứ tự hiện tại chưa thay đổi.')
    } catch (error: unknown) {
      if (!isPlannerLifecycleActive()) return
      const message = extractErrorMessage(error, 'Không thể tối ưu tuyến lúc này')
      optimizationMessage.value = message
      showToast(message, 'error')
    } finally {
      if (!isPlannerLifecycleActive()) return
      routeLoading.value = false
      await nextTick()
      if (!isPlannerLifecycleActive()) return
      suspendAutoRoute.value = false
      autoRouteScheduler.resume()
      optimizing.value = false
    }
  }

  async function confirmOptimizationPreview() {
    const transaction = pendingOptimization
    if (!transaction || !optimizationPreview.value) return
    for (let attempt = 0; attempt < 3 && optimizing.value; attempt += 1) {
      await nextTick()
    }
    if (optimizing.value || !isPlannerLifecycleActive()) return
    optimizing.value = true
    suspendAutoRoute.value = true
    routeLoading.value = true
    autoRouteScheduler.cancelScheduled()
    const routeRequestBeforeCommit = latestAutoRouteRequest
    let reorderInputVersion: number | null = null
    let optimizerWatcherRequest: number | null = null

    try {
      const committedResult = await commitPlannerOptimizationResult(transaction.result, {
        isActive: isPlannerLifecycleActive,
        applyPlacements: (result) => {
          const schedule = result.outcome.optimization.schedule
          if (schedule) {
            applySchedulePlacements(
              transaction.routed,
              schedule.placements,
              plannerScheduleMetadata,
              plannerInputState,
            )
          } else if (itineraryScheduleV2) {
            applySchedulePlacements(transaction.routed, [], plannerScheduleMetadata, plannerInputState)
          }
        },
        reorderStops: (orderedKeys) => {
          reorderInputVersion = plannerInputState.version
          stops.value = mergeOptimizedStops(stops.value, transaction.routed, orderedKeys)
        },
        applyRoute: (route) => {
          routeResult.value = route
          routeError.value = resolvePlannerRouteSurface(transaction.routed.length, route).kind === 'fallback'
        },
        updateMap: async (route) => {
          await nextTick()
          if (!isPlannerLifecycleActive()) return
          if (
            reorderInputVersion !== null
            && plannerInputState.version === reorderInputVersion
            && latestAutoRouteRequest !== routeRequestBeforeCommit
          ) {
            optimizerWatcherRequest = latestAutoRouteRequest
          }
          await updateMap(route)
        },
      })
      if (!committedResult || !isPlannerLifecycleActive()) return
      autoRouteScheduler.discardPending(optimizerWatcherRequest)
      const message = optimizationTradeoffs(committedResult, transaction.routed, stops.value.length, itineraryScheduleV2).join(' ')
      confirmedOpeningHourConflicts.value = candidateOpeningHourConflicts.value.map(conflict => ({ ...conflict }))
      clearPendingOptimizationPreview()
      await announceOptimization(message || 'Đã áp dụng thứ tự đề xuất.')
    } finally {
      if (!isPlannerLifecycleActive()) return
      routeLoading.value = false
      suspendAutoRoute.value = false
      autoRouteScheduler.resume()
      optimizing.value = false
    }
  }

  async function cancelOptimizationPreview() {
    if (!optimizationPreview.value) return
    optimizationPreview.value.cancel()
    clearPendingOptimizationPreview()
    await announceOptimization('Đã giữ nguyên thứ tự hiện tại.')
  }

  async function computeRoute() {
    const coords = stops.value.map(s => s.coords).filter(Boolean) as [number, number][]
    if (coords.length < 2) {
      routeResult.value = null
      routeError.value = false
      updateMap(null)
      return
    }
    routeLoading.value = true
    routeError.value = false
    const result = await fetchRoute(coords, transportMode.value)
    routeResult.value = result
    routeError.value = resolvePlannerRouteSurface(coords.length, result).kind === 'fallback'
    routeLoading.value = false
    updateMap(result)
  }

  const autoRouteScheduler = createSuspendedRouteScheduler(
    computeRoute,
    () => suspendAutoRoute.value,
  )

  function scheduleRouteCalc() {
    latestAutoRouteRequest = autoRouteScheduler.request()
  }

  // Recalculate route when stop coords or transport mode change
  watch(
    () => [stops.value.map(s => (s.coords ? s.coords.join(',') : 'x')).join('|'), transportMode.value],
    scheduleRouteCalc,
  )
  watch(transportMode, invalidatePlannerSchedule)

  if (getCurrentInstance()) {
    onBeforeUnmount(() => {
      autoRouteScheduler.dispose()
    })
  }

  return {
    routeResult,
    routeLoading,
    routeError,
    optimizing,
    optimizationMessage,
    optimizationPreview,
    suspendAutoRoute,
    currentRoutableStops,
    canOptimizeRoute,
    optimizeRouteTitle,
    candidateOpeningHourConflicts,
    confirmedOpeningHourConflicts,
    visibleOpeningHourConflicts,
    clearPendingOptimizationPreview,
    invalidatePlannerSchedule,
    announceOptimization,
    optimizePlanRoute,
    confirmOptimizationPreview,
    cancelOptimizationPreview,
    computeRoute,
    autoRouteScheduler,
    scheduleRouteCalc,
  }
}
