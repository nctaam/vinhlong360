import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref, watch } from 'vue'
import PlannerPage from '../pages/tao-lich-trinh.vue'

const mocks = vi.hoisted(() => ({
  applyPlacements: 0,
  commitMapGate: null as Promise<void> | null,
  commitMap: 0,
  createMap: vi.fn(),
  discardPending: 0,
  fetchRoute: vi.fn(),
  getEntity: vi.fn(),
  listEntities: vi.fn(),
  mergeStops: 0,
  requestRoute: 0,
  resumeRoute: 0,
  runPlannerOptimization: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('~/composables/usePublicApi', () => ({
  usePublicApi: () => ({
    getEntity: mocks.getEntity,
    listEntities: mocks.listEntities,
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
mockNuxtImport('useNDAMap', () => () => ({ createMap: mocks.createMap }))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))

beforeEach(() => {
  mocks.applyPlacements = 0
  mocks.commitMapGate = null
  mocks.commitMap = 0
  mocks.createMap.mockReset()
  mocks.discardPending = 0
  mocks.fetchRoute.mockReset()
  mocks.getEntity.mockReset()
  mocks.listEntities.mockReset()
  mocks.listEntities.mockResolvedValue(defaultEntityResponse())
  mocks.mergeStops = 0
  mocks.requestRoute = 0
  mocks.resumeRoute = 0
  mocks.runPlannerOptimization.mockReset()
  mocks.showToast.mockReset()
  localStorage.clear()
})

describe('planner page lifecycle', () => {
  it('keeps normal title, budget, and stop edits local without fabricating a server conflict', async () => {
    const wrapper = await mountSuspended(PlannerPage, {
      global: { stubs: plannerStubs() },
    })
    const vm = wrapper.vm as unknown as {
      loadPlan: (index: number) => Promise<void>
      savedPlans: Array<Record<string, unknown>>
      stops: Array<{ notes: string }>
    }
    vm.savedPlans = [{
      id: 'server-plan',
      title: 'Baseline',
      revision: 4,
      savedAt: '2026-08-09T08:00:00Z',
      stops: [planStop('start', 'Start'), planStop('middle', 'Middle')],
    }]
    await vm.loadPlan(0)
    await nextTick()

    await wrapper.get('.builder-title').setValue('Local title')
    await wrapper.get('#planner-time-budget').setValue('90')
    await wrapper.get('.stop-note-input').setValue('Local note')
    await nextTick()

    expect(wrapper.find('[data-friction-code="revision-conflict"]').exists()).toBe(false)
    expect(wrapper.find('[data-planner-conflict-diff]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('opens only an explicit newer server snapshot and wires manual, keep-local, and accept-server resolution', async () => {
    const wrapper = await mountSuspended(PlannerPage, {
      global: { stubs: plannerStubs() },
    })
    const vm = wrapper.vm as unknown as {
      observePlannerServerSnapshot?: (plan: Record<string, unknown>) => boolean
      loadPlan: (index: number) => Promise<void>
      savedPlans: Array<Record<string, unknown>>
      stops: Array<{ id: string; notes: string }>
      planTitle: string
    }
    vm.savedPlans = [{
      id: 'server-plan',
      title: 'Baseline',
      revision: 4,
      savedAt: '2026-08-09T08:00:00Z',
      stops: [planStop('start', 'Start')],
    }]
    await vm.loadPlan(0)
    await nextTick()
    await wrapper.get('.stop-note-input').setValue('Local note')

    if (!vm.observePlannerServerSnapshot) {
      wrapper.unmount()
      expect(vm.observePlannerServerSnapshot).toEqual(expect.any(Function))
      return
    }
    expect(vm.observePlannerServerSnapshot({
      id: 'server-plan',
      title: 'Server revision 5',
      revision: 5,
      savedAt: '2026-08-09T09:00:00Z',
      stops: [planStop('start', 'Start', 'Server note')],
    })).toBe(true)
    await nextTick()

    expect(wrapper.get('[data-friction-code="revision-conflict"]').text()).toContain('revision 5')
    expect(wrapper.get('[data-planner-conflict-diff]').text()).toContain('notes')

    await wrapper.get('[data-conflict-manual]').trigger('click')
    expect(wrapper.find('[data-planner-conflict-diff]').exists()).toBe(true)
    expect(vm.stops[0]?.notes).toBe('Local note')

    await wrapper.get('[data-conflict-local]').trigger('click')
    await nextTick()
    expect(wrapper.find('[data-planner-conflict-diff]').exists()).toBe(false)
    expect(vm.stops[0]?.notes).toBe('Local note')

    expect(vm.observePlannerServerSnapshot({
      id: 'server-plan',
      title: 'Server revision 6',
      revision: 6,
      savedAt: '2026-08-09T10:00:00Z',
      stops: [planStop('server', 'Server stop', 'Server wins')],
    })).toBe(true)
    await nextTick()
    await wrapper.get('[data-conflict-server]').trigger('click')
    await nextTick()

    expect(vm.planTitle).toBe('Server revision 6')
    expect(vm.stops.map(stop => stop.id)).toEqual(['server'])
    expect(vm.stops[0]?.notes).toBe('Server wins')
    expect(wrapper.find('[data-planner-conflict-diff]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('derives stale stop evidence and refreshes only the affected stop from returned facts', async () => {
    mocks.listEntities.mockResolvedValue({
      total: 2,
      entities: [
        entityWithFreshness('start', 'Start', 'stale', '2026-06-01T00:00:00Z'),
        entityWithFreshness('middle', 'Middle', 'aging', '2026-07-01T00:00:00Z'),
      ],
    })
    mocks.getEntity.mockImplementation(async (id: string) => (
      id === 'start'
        ? entityWithFreshness('start', 'Start', 'fresh', '2026-08-09T10:00:00Z')
        : entityWithFreshness('middle', 'Middle', 'aging', '2026-07-01T00:00:00Z')
    ))
    const wrapper = await mountSuspended(PlannerPage, {
      global: { stubs: plannerStubs() },
    })
    for (const item of wrapper.findAll('.picker-item')) await item.trigger('click')
    await flushContinuation()

    expect(wrapper.findAll('[data-friction-code="stale-stop-facts"]')).toHaveLength(2)
    await wrapper.findAll('[data-friction-code="stale-stop-facts"]')[0]!
      .get('[data-friction-recovery]')
      .trigger('click')
    await flushContinuation()

    const vm = wrapper.vm as unknown as {
      stops: Array<{ id: string; sourceFreshness?: { status: string; updatedAt?: string } }>
    }
    expect(mocks.getEntity).toHaveBeenCalledWith('start')
    expect(vm.stops.find(stop => stop.id === 'start')?.sourceFreshness).toEqual(expect.objectContaining({
      status: 'fresh',
      updatedAt: '2026-08-09T10:00:00Z',
    }))
    expect(vm.stops.find(stop => stop.id === 'middle')?.sourceFreshness?.status).toBe('aging')
    expect(wrapper.findAll('[data-friction-code="stale-stop-facts"]')).toHaveLength(1)
    expect(wrapper.get('[data-friction-code="stale-stop-facts"]').text()).toContain('Middle')
    wrapper.unmount()
  })

  it('promotes confirmed opening-hour conflicts, clears them on schedule edits, and drops cancelled candidates', async () => {
    mocks.runPlannerOptimization.mockResolvedValue(currentResult(undefined, [{
      stop_id: 'planner-stop-1',
      reason: 'opening_hours_conflict',
    }]))
    const wrapper = await mountPlannerWithThreeStops()

    await wrapper.get('.optimize-route-btn').trigger('click')
    await flushContinuation()
    expect(wrapper.findAll('[data-friction-code="opening-hours-conflict"]')).toHaveLength(1)
    await wrapper.get('[data-preview-cancel]').trigger('click')
    await nextTick()
    expect(wrapper.find('[data-friction-code="opening-hours-conflict"]').exists()).toBe(false)

    await wrapper.get('.optimize-route-btn').trigger('click')
    await flushContinuation()
    await wrapper.get('[data-preview-confirm]').trigger('click')
    await flushContinuation()
    expect(wrapper.findAll('[data-friction-code="opening-hours-conflict"]')).toHaveLength(1)

    await wrapper.findAll('.stop-time-input')[1]!.setValue('10:00-11:00')
    await nextTick()
    expect(wrapper.find('[data-friction-code="opening-hours-conflict"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('renders unavailable travel and a partial total instead of zero when routing fails', async () => {
    mocks.fetchRoute.mockResolvedValue(null)
    const wrapper = await mountSuspended(PlannerPage, {
      global: { stubs: plannerStubs() },
    })
    const items = wrapper.findAll('.picker-item')
    await items[0]!.trigger('click')
    await items[1]!.trigger('click')
    await flushContinuation()

    expect(wrapper.get('[data-summary-travel-duration]').text()).toContain('Chưa xác định')
    expect(wrapper.get('[data-summary-total-duration]').text()).toContain('chưa gồm di chuyển')
    expect(wrapper.get('[data-summary-travel-duration]').text()).not.toContain('0 phút')
    wrapper.unmount()
  })

  it('keeps live stops unchanged until confirm and preserves revision on cancel', async () => {
    mocks.runPlannerOptimization.mockResolvedValue(currentResult([
      'planner-stop-0',
      'planner-stop-2',
      'planner-stop-1',
    ]))
    const wrapper = await mountPlannerWithThreeStops()
    const vm = wrapper.vm as unknown as {
      stops: Array<{ id: string }>
      plannerInputState: { version: number }
    }
    const beforeIds = vm.stops.map(stop => stop.id)
    const beforeRevision = vm.plannerInputState.version

    await wrapper.get('.optimize-route-btn').trigger('click')
    await flushContinuation()
    expect(vm.stops.map(stop => stop.id)).toEqual(beforeIds)
    expect(mocks.applyPlacements).toBe(0)
    await wrapper.get('[data-preview-cancel]').trigger('click')
    expect(vm.stops.map(stop => stop.id)).toEqual(beforeIds)
    expect(vm.plannerInputState.version).toBe(beforeRevision)

    await wrapper.get('.optimize-route-btn').trigger('click')
    await flushContinuation()
    await wrapper.get('[data-preview-confirm]').trigger('click')
    await flushContinuation()
    expect(vm.stops.map(stop => stop.id)).toEqual(['start', 'end', 'middle'])
    expect(mocks.applyPlacements).toBe(1)
    wrapper.unmount()
  })

  it('reorders the editable timeline by drag while retaining button alternatives', async () => {
    const wrapper = await mountPlannerWithThreeStops()
    const vm = wrapper.vm as unknown as { stops: Array<{ id: string }> }
    const rows = wrapper.findAll('.stop-item')
    const dataTransfer = { effectAllowed: '', setData: vi.fn() }

    await rows[0]!.trigger('dragstart', { dataTransfer })
    await rows[2]!.trigger('drop')
    await nextTick()

    expect(vm.stops.map(stop => stop.id)).toEqual(['middle', 'end', 'start'])
    expect(wrapper.findAll('.stop-card-actions .move')).toHaveLength(4)
    wrapper.unmount()
  })


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
    expect(mocks.commitMap).toBe(0)
    await wrapper.get('[data-preview-confirm]').trigger('click')
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

  it('removes a non-null map handed off after disposal before the await continuation', async () => {
    let wrapper!: Awaited<ReturnType<typeof mountPlannerWithThreeStops>>
    const mapEffects: string[] = []
    const map = {
      remove: vi.fn(() => mapEffects.push('remove')),
      on: vi.fn(() => {
        mapEffects.push('on')
        return map
      }),
      addControl: vi.fn(() => {
        mapEffects.push('addControl')
        return map
      }),
      hasImage: vi.fn(),
      addImage: vi.fn(),
      getSource: vi.fn(),
      removeLayer: vi.fn(),
      removeSource: vi.fn(),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      fitBounds: vi.fn(),
    }
    const maplibregl = {
      AttributionControl: class {},
      NavigationControl: class {},
      Marker: class {},
      Popup: class {},
      LngLatBounds: class {},
    }
    mocks.runPlannerOptimization.mockResolvedValue(currentResult())
    wrapper = await mountPlannerWithThreeStops({ includeMap: true })
    await flushContinuation()
    mocks.createMap.mockClear()
    mocks.createMap.mockImplementation(() => ({
      then(resolve: (value: unknown) => void) {
        queueMicrotask(() => {
          wrapper.unmount()
          resolve({ map, maplibregl })
        })
      },
    }))

    await wrapper.get('.optimize-route-btn').trigger('click')
    expect(mocks.createMap).not.toHaveBeenCalled()
    await wrapper.get('[data-preview-confirm]').trigger('click')
    await flushContinuation()

    expect(mocks.createMap).toHaveBeenCalledTimes(1)
    expect(map.remove).toHaveBeenCalledTimes(1)
    expect(mapEffects).toEqual(['remove'])
    expect(map.on).not.toHaveBeenCalled()
    expect(map.addControl).not.toHaveBeenCalled()
    expect(map.hasImage).not.toHaveBeenCalled()
    expect(map.addImage).not.toHaveBeenCalled()
    expect(map.getSource).not.toHaveBeenCalled()
    expect(map.removeLayer).not.toHaveBeenCalled()
    expect(map.removeSource).not.toHaveBeenCalled()
    expect(map.addSource).not.toHaveBeenCalled()
    expect(map.addLayer).not.toHaveBeenCalled()
    expect(map.fitBounds).not.toHaveBeenCalled()
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

async function mountPlannerWithThreeStops(options: { includeMap?: boolean } = {}) {
  const includeMap = options.includeMap ?? false
  const wrapper = await mountSuspended(PlannerPage, {
    global: {
      stubs: plannerStubs(includeMap),
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

function currentResult(orderedKeys = [
  'planner-stop-0',
  'planner-stop-1',
  'planner-stop-2',
], skipped: Array<{ stop_id: string; reason: string }> = []) {
  return {
    status: 'current' as const,
    outcome: {
      attempts: 1 as const,
      optimization: {
        backtrack_ratio: 0,
        distance_after_km: 1,
        distance_before_km: 2,
        ordered_ids: orderedKeys,
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
          skipped,
          total_travel_minutes: 30,
          waiting_minutes: 0,
        },
        solver: 'schedule-exact' as const,
        warnings: [],
      },
      ordered: orderedKeys.map(key => ({ key })),
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

function plannerStubs(includeMap = false) {
  return {
    Breadcrumb: true,
    ClientOnly: includeMap ? { template: '<slot />' } : true,
    EmptyState: true,
    FilterChips: true,
  }
}

function defaultEntityResponse() {
  return {
    total: 3,
    entities: [
      { id: 'start', name: 'Start', type: 'attraction', coordinates: [10.01, 106.01] },
      { id: 'middle', name: 'Middle', type: 'attraction', coordinates: [10.02, 106.02] },
      { id: 'end', name: 'End', type: 'attraction', coordinates: [10.03, 106.03] },
    ],
  }
}

function planStop(id: string, name: string, notes = '') {
  return {
    id,
    name,
    type: 'attraction',
    coords: [10.01, 106.01] as [number, number],
    time: '',
    notes,
  }
}

function entityWithFreshness(
  id: string,
  name: string,
  status: 'fresh' | 'aging' | 'stale',
  updatedAt: string,
) {
  return {
    id,
    name,
    type: 'attraction',
    coordinates: [10.01, 106.01] as [number, number],
    source_freshness: {
      freshness_status: status,
      updated_at: updatedAt,
      source_title: 'Nguồn kiểm chứng',
    },
  }
}
