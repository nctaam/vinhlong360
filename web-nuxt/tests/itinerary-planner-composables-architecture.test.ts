import { describe, it, expect, vi } from 'vitest'
import { ref, reactive } from 'vue'
import { usePlannerRouteOptimization } from '../composables/usePlannerRouteOptimization'
import { usePlannerDraftState } from '../composables/usePlannerDraftState'
import { usePlannerFrictions } from '../composables/usePlannerFrictions'
import type { PlanStop } from '../utils/plannerSnapshots'
import type { TransportMode } from '../composables/useRouting'
import type { PlannerScheduleMetadata, PlannerInputState } from '../composables/useItineraryOptimization'

describe('Itinerary Planner Composables Architecture', () => {
  describe('usePlannerRouteOptimization', () => {
    it('initializes with expected default reactive state', () => {
      const stops = ref<PlanStop[]>([])
      const transportMode = ref<TransportMode>('driving')
      const plannerScheduleMetadata = new WeakMap<object, PlannerScheduleMetadata>()
      const plannerInputState = reactive<PlannerInputState>({ version: 0 })
      const optimizerEnabled = ref(true)
      const stopAnnounce = ref('')
      const updateMap = vi.fn().mockResolvedValue(undefined)
      const showToast = vi.fn()

      const {
        routeResult,
        routeLoading,
        routeError,
        optimizing,
        optimizationMessage,
        optimizationPreview,
        canOptimizeRoute,
        optimizeRouteTitle,
      } = usePlannerRouteOptimization({
        stops,
        transportMode,
        plannerScheduleMetadata,
        plannerInputState,
        itineraryScheduleV2: true,
        optimizerEnabled,
        updateMap,
        showToast,
        stopAnnounce,
      })

      expect(routeResult.value).toBeNull()
      expect(routeLoading.value).toBe(false)
      expect(routeError.value).toBe(false)
      expect(optimizing.value).toBe(false)
      expect(optimizationMessage.value).toBe('')
      expect(optimizationPreview.value).toBeNull()
      expect(canOptimizeRoute.value).toBe(false)
      expect(optimizeRouteTitle.value).toBe('Cần ít nhất 3 điểm để tối ưu thứ tự')
    })

    it('evaluates canOptimizeRoute when at least 3 valid routable stops exist', () => {
      const stops = ref<PlanStop[]>([
        { id: '1', name: 'Stop 1', type: 'attraction', place_name: '', coords: [10.2, 105.9], time: '', notes: '' },
        { id: '2', name: 'Stop 2', type: 'attraction', place_name: '', coords: [10.25, 105.95], time: '', notes: '' },
        { id: '3', name: 'Stop 3', type: 'attraction', place_name: '', coords: [10.3, 106.0], time: '', notes: '' },
      ])
      const transportMode = ref<TransportMode>('driving')
      const plannerScheduleMetadata = new WeakMap<object, PlannerScheduleMetadata>()
      const plannerInputState = reactive<PlannerInputState>({ version: 0 })
      const optimizerEnabled = ref(true)
      const stopAnnounce = ref('')
      const updateMap = vi.fn().mockResolvedValue(undefined)
      const showToast = vi.fn()

      const { canOptimizeRoute, optimizeRouteTitle } = usePlannerRouteOptimization({
        stops,
        transportMode,
        plannerScheduleMetadata,
        plannerInputState,
        itineraryScheduleV2: true,
        optimizerEnabled,
        updateMap,
        showToast,
        stopAnnounce,
      })

      expect(canOptimizeRoute.value).toBe(true)
      expect(optimizeRouteTitle.value).toBe('Giữ nguyên điểm đầu, điểm cuối và tối ưu các điểm ở giữa')
    })

    it('clears preview and resets candidate conflicts when cleared', () => {
      const stops = ref<PlanStop[]>([])
      const transportMode = ref<TransportMode>('driving')
      const plannerScheduleMetadata = new WeakMap<object, PlannerScheduleMetadata>()
      const plannerInputState = reactive<PlannerInputState>({ version: 0 })
      const optimizerEnabled = ref(true)
      const stopAnnounce = ref('')
      const updateMap = vi.fn().mockResolvedValue(undefined)
      const showToast = vi.fn()

      const {
        clearPendingOptimizationPreview,
        candidateOpeningHourConflicts,
        optimizationPreview,
        invalidatePlannerSchedule,
      } = usePlannerRouteOptimization({
        stops,
        transportMode,
        plannerScheduleMetadata,
        plannerInputState,
        itineraryScheduleV2: true,
        optimizerEnabled,
        updateMap,
        showToast,
        stopAnnounce,
      })

      candidateOpeningHourConflicts.value = [{
        stopId: 'stop-1',
        title: 'Stop 1',
        detail: 'Closed at arrival',
        code: 'CLOSED_AT_ARRIVAL',
        severity: 'warning',
      }]
      clearPendingOptimizationPreview()
      expect(candidateOpeningHourConflicts.value).toEqual([])
      expect(optimizationPreview.value).toBeNull()

      invalidatePlannerSchedule()
      expect(plannerInputState.version).toBeGreaterThan(0)
    })
  })

  describe('usePlannerDraftState', () => {
    it('initializes draft state and manages revisions cleanly', () => {
      const planTitle = ref('Hành trình mẫu')
      const stops = ref<PlanStop[]>([])
      const travelBudgetMinutes = ref<number | null>(60)
      const plannerScheduleMetadata = new WeakMap<object, PlannerScheduleMetadata>()
      const plannerInputState = reactive<PlannerInputState>({ version: 0 })
      const plannerMetadataForLoadedStop = vi.fn().mockReturnValue({})
      const invalidatePlannerSchedule = vi.fn()
      const saving = ref(false)
      const acceptServerComparisonBase = vi.fn()

      const {
        plannerOnline,
        localDraftRevision,
        localDirty,
        activeServerPlanId,
        baseServerRevision,
        plannerDraftGeneration,
        advancePlannerDraftGeneration,
        clearActiveServerPlan,
        isDraftPersistenceReady,
        setDraftPersistenceReady,
      } = usePlannerDraftState({
        planTitle,
        stops,
        travelBudgetMinutes,
        plannerScheduleMetadata,
        plannerInputState,
        plannerMetadataForLoadedStop,
        invalidatePlannerSchedule,
        saving,
        acceptServerComparisonBase,
      })

      expect(plannerOnline.value).toBe(true)
      expect(localDraftRevision.value).toBe(0)
      expect(localDirty.value).toBe(false)
      expect(activeServerPlanId.value).toBeNull()
      expect(baseServerRevision.value).toBeNull()
      expect(plannerDraftGeneration.value).toBe(0)
      expect(isDraftPersistenceReady()).toBe(false)

      setDraftPersistenceReady(true)
      expect(isDraftPersistenceReady()).toBe(true)

      advancePlannerDraftGeneration()
      expect(plannerDraftGeneration.value).toBe(1)

      activeServerPlanId.value = 'server-123'
      baseServerRevision.value = 2
      clearActiveServerPlan()
      expect(activeServerPlanId.value).toBeNull()
      expect(baseServerRevision.value).toBeNull()
      expect(plannerDraftGeneration.value).toBe(2)
    })
  })

  describe('usePlannerFrictions', () => {
    it('detects stale stops and formats warnings properly', () => {
      const stops = ref<PlanStop[]>([
        {
          id: 's1',
          name: 'Điểm cũ',
          type: 'attraction',
          place_name: 'Vĩnh Long',
          coords: [10.2, 105.9],
          time: '',
          notes: '',
          sourceFreshness: { status: 'stale', updatedAt: '2023-01-01' },
        },
      ])
      const visibleOpeningHourConflicts = ref([])
      const routeResult = ref(null)
      const travelBudgetMinutes = ref(null)
      const plannerOnline = ref(true)
      const localDraftRevision = ref(0)
      const draftSavedAt = ref(null)
      const draftSource = ref<'local' | 'server'>('local')
      const routeError = ref(false)
      const plannerRevisionConflict = ref(null)
      const refreshPlannerStopEvidence = vi.fn().mockResolvedValue(true)

      const {
        stalePlannerStops,
        plannerFrictionNotices,
        plannerSummaryWarnings,
        handleFrictionRecovery,
      } = usePlannerFrictions({
        stops,
        visibleOpeningHourConflicts: visibleOpeningHourConflicts as any,
        routeResult,
        travelBudgetMinutes,
        plannerOnline,
        localDraftRevision,
        draftSavedAt,
        draftSource,
        routeError,
        plannerRevisionConflict,
        refreshPlannerStopEvidence,
      })

      expect(stalePlannerStops.value).toHaveLength(1)
      expect(stalePlannerStops.value[0]?.stopId).toBe('s1')
      expect(stalePlannerStops.value[0]?.status).toBe('stale')

      const staleNotice = plannerFrictionNotices.value.find(n => n.code === 'stale-stop-facts')
      expect(staleNotice).toBeDefined()
      expect(plannerSummaryWarnings.value).toContain(staleNotice?.reason)

      if (staleNotice) {
        handleFrictionRecovery(staleNotice)
        expect(refreshPlannerStopEvidence).toHaveBeenCalledWith('s1')
      }
    })
  })
})
