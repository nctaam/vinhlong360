import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref, watch } from 'vue'
import PlannerPage from '../pages/tao-lich-trinh.vue'

const mocks = vi.hoisted(() => ({
  applyPlacements: 0,
  commitMapGate: null as Promise<void> | null,
  commitMap: 0,
  discardPending: 0,
  fetchRoute: vi.fn(),
  mergeStops: 0,
  requestRoute: 0,
  resumeRoute: 0,
  runPlannerOptimization: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('~/composables/usePublicApi', () => ({
  usePublicApi: () => ({
    getEntity: vi.fn(),
    listEntities: vi.fn().mockResolvedValue({
      total: 3,
      entities: [
        { id: 'start', name: 'Start', type: 'attraction', coordinates: [10.01, 106.01] },
        { id: 'middle', name: 'Middle', type: 'attraction', coordinates: [10.02, 106.02] },
        { id: 'end', name: 'End', type: 'attraction', coordinates: [10.03, 106.03] },
      ],
    }),
  }),
}))

vi.mock('~/composables/useRouting', async importOriginal => {
  const actual = await importOriginal<typeof import('../composables/useRouting')>()
  return {
    ...actual,
    fetchRoute: mocks.fetchRoute,
    fetchRouteTable: vi.fn(),
  }
})

vi.mock('~/composables/useItineraryOptimization', async importOriginal => {
  const actual = await importOriginal<typeof import('../composables/useItineraryOptimization')>()
  return {
    ...actual,
    applySchedulePlacements: (...args: Parameters<typeof actual.applySchedulePlacements>) => {
      mocks.applyPlacements += 1
      return actual.applySchedulePlacements(...args)
    },
    commitPlannerOptimizationResult: (
      result: Parameters<typeof actual.commitPlannerOptimizationResult>[0],
      callbacks: Parameters<typeof actual.commitPlannerOptimizationResult>[1],
    ) => actual.commitPlannerOptimizationResult(result, {
      ...callbacks,
      updateMap: async (route) => {
        mocks.commitMap += 1
        if (mocks.commitMapGate) await mocks.commitMapGate
        await callbacks.updateMap(route)
      },
    }),
    createSuspendedRouteScheduler: (
      ...args: Parameters<typeof actual.createSuspendedRouteScheduler>
    ) => {
      const scheduler = actual.createSuspendedRouteScheduler(...args)
      return {
        ...scheduler,
        discardPending: (requestId: number | null) => {
          mocks.discardPending += 1
          scheduler.discardPending(requestId)
        },
        request: () => {
          mocks.requestRoute += 1
          return scheduler.request()
        },
        resume: () => {
          mocks.resumeRoute += 1
          scheduler.resume()
        },
      }
    },
    mergeOptimizedStops: (...args: Parameters<typeof actual.mergeOptimizedStops>) => {
      mocks.mergeStops += 1
      return actual.mergeOptimizedStops(...args)
    },
    runPlannerOptimization: mocks.runPlannerOptimization,
  }
})

mockNuxtImport('useAuth', () => () => ({
  authHeaders: () => ({}),
  fetchMe: vi.fn().mockResolvedValue(null),
  isLoggedIn: ref(false),
  user: ref(null),
}))
mockNuxtImport('useConfirm', () => () => ({ confirmDialog: vi.fn() }))
mockNuxtImport('useFavorites', () => () => ({ count: ref(0), favorites: ref([]) }))
mockNuxtImport('useNDAMap', () => () => ({ createMap: vi.fn() }))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))

beforeEach(() => {
  mocks.applyPlacements = 0
  mocks.commitMapGate = null
  mocks.commitMap = 0
  mocks.discardPending = 0
  mocks.fetchRoute.mockReset()
  mocks.mergeStops = 0
  mocks.requestRoute = 0
  mocks.resumeRoute = 0
  mocks.runPlannerOptimization.mockReset()
  mocks.showToast.mockReset()
  localStorage.clear()
})

describe('planner page lifecycle', () => {
  it('does not apply a planner result or finish UI and routing state after unmount', async () => {
    let resolveOptimization!: (result: ReturnType<typeof currentResult>) => void
    const pending = new Promise<ReturnType<typeof currentResult>>((resolve) => {
      resolveOptimization = resolve
    })
    mocks.runPlannerOptimization.mockReturnValue(pending)
    const wrapper = await mountPlannerWithThreeStops()
    const vm = wrapper.vm as unknown as Record<string, unknown>

    await wrapper.get('.optimize-route-btn').trigger('click')
    expect(vm.routeLoading).toBe(true)
    expect(vm.optimizing).toBe(true)
    wrapper.unmount()
    const effectsAtUnmount = lifecycleEffects()
    const stateAtUnmount = plannerState(vm)

    resolveOptimization(currentResult())
    await flushContinuation()

    expect(lifecycleEffects()).toEqual(effectsAtUnmount)
    expect(plannerState(vm)).toEqual(stateAtUnmount)
  })

  it('does not publish an optimization rejection or finish UI and routing state after unmount', async () => {
    let rejectOptimization!: (reason: Error) => void
    const pending = new Promise<never>((_resolve, reject) => {
      rejectOptimization = reject
    })
    mocks.runPlannerOptimization.mockReturnValue(pending)
    const wrapper = await mountPlannerWithThreeStops()
    const vm = wrapper.vm as unknown as Record<string, unknown>

    await wrapper.get('.optimize-route-btn').trigger('click')
    wrapper.unmount()
    const effectsAtUnmount = lifecycleEffects()
    const stateAtUnmount = plannerState(vm)
    rejectOptimization(new Error('late planner failure'))
    await flushContinuation()

    expect(lifecycleEffects()).toEqual(effectsAtUnmount)
    expect(plannerState(vm)).toEqual(stateAtUnmount)
  })

  it('does not finish the commit or publish messaging after disposal at an awaited map boundary', async () => {
    let releaseCommitBoundary!: () => void
    mocks.commitMapGate = new Promise<void>((resolve) => {
      releaseCommitBoundary = resolve
    })
    mocks.runPlannerOptimization.mockResolvedValue(currentResult())
    const wrapper = await mountPlannerWithThreeStops()
    const vm = wrapper.vm as unknown as Record<string, unknown>

    await wrapper.get('.optimize-route-btn').trigger('click')
    await waitForCommitBoundary()
    expect(mocks.commitMap).toBe(1)

    wrapper.unmount()
    const effectsAtUnmount = lifecycleEffects()
    const stateAtUnmount = plannerState(vm)
    releaseCommitBoundary()
    await flushContinuation()

    expect(lifecycleEffects()).toEqual(effectsAtUnmount)
    expect(plannerState(vm)).toEqual(stateAtUnmount)
  })

  it('does not publish the announcement after message-driven disposal at the next tick boundary', async () => {
    mocks.runPlannerOptimization.mockResolvedValue(currentResult())
    const wrapper = await mountPlannerWithThreeStops()
    const vm = wrapper.vm as unknown as Record<string, unknown>
    let stateAtUnmount: ReturnType<typeof plannerState> | null = null
    let effectsAtUnmount: ReturnType<typeof lifecycleEffects> | null = null
    const stopWatching = watch(
      () => vm.optimizationMessage,
      (message) => {
        if (!message || stateAtUnmount) return
        wrapper.unmount()
        stateAtUnmount = plannerState(vm)
        effectsAtUnmount = lifecycleEffects()
      },
      { flush: 'sync' },
    )

    await wrapper.get('.optimize-route-btn').trigger('click')
    await flushContinuation()
    stopWatching()

    expect(stateAtUnmount).not.toBeNull()
    expect(effectsAtUnmount).not.toBeNull()
    expect(plannerState(vm)).toEqual(stateAtUnmount)
    expect(lifecycleEffects()).toEqual(effectsAtUnmount)
  })
})

async function mountPlannerWithThreeStops() {
  const wrapper = await mountSuspended(PlannerPage, {
    global: {
      stubs: {
        Breadcrumb: true,
        ClientOnly: true,
        EmptyState: true,
        FilterChips: true,
      },
    },
  })
  const pickerItems = wrapper.findAll('.picker-item')
  expect(pickerItems).toHaveLength(3)
  for (const item of pickerItems) await item.trigger('click')
  await nextTick()
  expect(wrapper.findAll('.stop-item')).toHaveLength(3)
  return wrapper
}

async function flushContinuation() {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await Promise.resolve()
    await nextTick()
  }
  await new Promise<void>(resolve => setTimeout(resolve, 0))
  await nextTick()
}

async function waitForCommitBoundary() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (mocks.commitMap === 1) return
    await new Promise<void>(resolve => setTimeout(resolve, 0))
  }
}

function lifecycleEffects() {
  return {
    applyPlacements: mocks.applyPlacements,
    commitMap: mocks.commitMap,
    discardPending: mocks.discardPending,
    fetchRoute: mocks.fetchRoute.mock.calls.length,
    mergeStops: mocks.mergeStops,
    requestRoute: mocks.requestRoute,
    resumeRoute: mocks.resumeRoute,
    toast: mocks.showToast.mock.calls.length,
  }
}

function plannerState(vm: Record<string, unknown>) {
  return {
    routeResult: vm.routeResult,
    routeError: vm.routeError,
    optimizationMessage: vm.optimizationMessage,
    stopAnnounce: vm.stopAnnounce,
    routeLoading: vm.routeLoading,
    suspendAutoRoute: vm.suspendAutoRoute,
    optimizing: vm.optimizing,
  }
}

function currentResult() {
  return {
    status: 'current' as const,
    outcome: {
      attempts: 1 as const,
      optimization: {
        backtrack_ratio: 0,
        distance_after_km: 1,
        distance_before_km: 2,
        ordered_ids: ['planner-stop-0', 'planner-stop-1', 'planner-stop-2'],
        saved_distance_km: 1,
        schedule: {
          matrix_source: 'request' as const,
          minimum_slack_minutes: 30,
          overtime_minutes: 0,
          placements: [{
            arrival_minute: 480,
            end_visit_minute: 540,
            start_visit_minute: 480,
            stop_id: 'planner-stop-0',
          }],
          skipped: [],
          total_travel_minutes: 30,
          waiting_minutes: 0,
        },
        solver: 'schedule-exact' as const,
        warnings: [],
      },
      ordered: [
        { key: 'planner-stop-0' },
        { key: 'planner-stop-1' },
        { key: 'planner-stop-2' },
      ],
      route: {
        geometry: [],
        legs: [
          { distance: 1000, duration: 120, hasUturn: false },
          { distance: 1000, duration: 120, hasUturn: false },
        ],
        totalDistance: 2000,
        totalDuration: 240,
      },
      unresolvedUturn: false,
      warnings: [],
    },
    scheduleWarnings: [],
  }
}
