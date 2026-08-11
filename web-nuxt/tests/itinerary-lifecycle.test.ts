import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref, watch } from 'vue'
import PlannerPage from '../pages/tao-lich-trinh.vue'
import { useJourneyThread } from '../composables/useJourneyThread'

const mocks = vi.hoisted(() => ({
  applyPlacements: 0,
  commitMapGate: null as Promise<void> | null,
  commitMap: 0,
  confirmDialog: vi.fn(),
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
const authState = vi.hoisted(() => ({
  isLoggedIn: { value: false },
  user: { value: null as { id: string } | null },
}))
const publicOptimizerMode = vi.hoisted(() => ({ mode: 'enhanced' as 'enhanced' | 'deterministic' }))

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
  isLoggedIn: authState.isLoggedIn,
  user: authState.user,
}))
mockNuxtImport('useConfirm', () => () => ({ confirmDialog: mocks.confirmDialog }))
mockNuxtImport('useFavorites', () => () => ({ count: ref(0), favorites: ref([]) }))
mockNuxtImport('useNDAMap', () => () => ({ createMap: mocks.createMap }))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))
mockNuxtImport('useFeature', () => () => ({
  capabilityMode: (capability: string) => capability === 'optimizer' ? publicOptimizerMode.mode : 'deterministic',
}))

beforeEach(() => {
  authState.isLoggedIn.value = false
  authState.user.value = null
  publicOptimizerMode.mode = 'enhanced'
  mocks.applyPlacements = 0
  mocks.commitMapGate = null
  mocks.commitMap = 0
  mocks.confirmDialog.mockReset()
  mocks.confirmDialog.mockResolvedValue(true)
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
  vi.unstubAllGlobals()
  localStorage.clear()
  sessionStorage.clear()
})

describe('planner page lifecycle', () => {
  it('keeps planner editing and saving usable when optimizer enhancement is disabled', async () => {
    publicOptimizerMode.mode = 'deterministic'
    const wrapper = await mountPlannerWithThreeStops()

    expect(wrapper.find('.optimize-route-btn').exists()).toBe(false)
    expect(wrapper.find('.builder-title').exists()).toBe(true)
    expect(wrapper.find('.planner-action-dock').exists()).toBe(true)
    wrapper.unmount()
  })

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

  it('updates the loaded server plan with its revision without duplicating the saved row', async () => {
    const updated = serverPlan({
      title: 'Local title',
      revision: 5,
      updatedAt: '2026-08-11T09:30:00Z',
      stops: [planStop('start', 'Start', 'Local note')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans/server-plan' && options.method === 'PUT') return { plan: updated }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/server-plan', {
        method: 'PUT',
        headers: {},
        body: {
          title: 'Local title',
          stops: [planStop('start', 'Start', 'Local note')],
          expected_revision: 4,
        },
      })
      expect(wrapper.findAll('.saved-plan-item')).toHaveLength(1)
      expect(wrapper.get('.saved-plan-info').text()).toContain('Local title')
      const vm = wrapper.vm as unknown as {
        baseServerRevision: number
        localDirty: boolean
        savedPlans: Array<{ updatedAt?: string }>
      }
      expect(vm.baseServerRevision).toBe(5)
      expect(vm.localDirty).toBe(false)
      expect(vm.savedPlans[0]?.updatedAt).toBe('2026-08-11T09:30:00Z')
    } finally {
      wrapper.unmount()
    }
  })

  it('preserves the local draft and renders the exact 409 current snapshot for recovery', async () => {
    const current = serverPlan({
      title: 'Server title',
      revision: 5,
      updatedAt: '2026-08-11T10:45:00Z',
      stops: [
        planStop('start', 'Start', 'Server note'),
        planStop('middle', 'Middle', 'Server-only stop'),
      ],
    })
    const fetchPlan = conflictFetch(current, 'response')
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      const vm = wrapper.vm as unknown as { planTitle: string; stops: Array<{ notes: string }> }
      expect(vm.planTitle).toBe('Local title')
      expect(vm.stops[0]?.notes).toBe('Local note')
      const recovery = wrapper.get('[data-planner-conflict-diff]')
      expect(recovery.attributes('role')).toBe('alert')
      expect(recovery.text()).toContain('Server title')
      expect(recovery.text()).toContain('Local title')
      expect(recovery.text()).toContain('Bản máy chủ 5')
      expect(recovery.text()).toContain('Cập nhật 11/8/2026')
      expect(recovery.text()).toContain('Start')
      expect(recovery.text()).toContain('Middle')
      expect(recovery.text()).toContain('Ghi chú')
      expect(recovery.text()).toContain('Chỉ có trên máy chủ')
      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/server-plan', expect.objectContaining({ method: 'PUT' }))
    } finally {
      wrapper.unmount()
    }
  })

  it('keeps the local comparison base across remount and retries PUT with the returned revision', async () => {
    const current = serverPlan({
      title: 'Server title',
      revision: 5,
      updatedAt: '2026-08-11T10:45:00Z',
      stops: [planStop('start', 'Start', 'Server note')],
    })
    const overwritten = serverPlan({
      title: 'Local title',
      revision: 6,
      updatedAt: '2026-08-11T10:47:00Z',
      stops: [planStop('start', 'Start', 'Local note')],
    })
    let puts = 0
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans/server-plan' && options.method === 'PUT') {
        puts += 1
        if (puts === 1) throw revisionConflict(current, 'data')
        return { plan: overwritten }
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    let wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()
      await wrapper.get('[data-conflict-local]').trigger('click')
      await nextTick()

      expect(wrapper.find('[data-planner-conflict-diff]').exists()).toBe(false)
      expect((wrapper.get('.builder-title').element as HTMLInputElement).value).toBe('Local title')
      wrapper.unmount()
      wrapper = await mountAuthenticatedPlanner(fetchPlan)
      expect((wrapper.get('.builder-title').element as HTMLInputElement).value).toBe('Local title')
      expect((wrapper.get('.stop-note-input').element as HTMLInputElement).value).toBe('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      const putCalls = fetchPlan.mock.calls.filter(([url, options]) => (
        url === '/api/my-plans/server-plan' && options?.method === 'PUT'
      ))
      expect(putCalls).toHaveLength(2)
      expect(putCalls[1]?.[1]?.body).toEqual({
        title: 'Local title',
        stops: [planStop('start', 'Start', 'Local note')],
        expected_revision: 5,
      })
      expect(fetchPlan.mock.calls.some(([url, options]) => url === '/api/my-plans' && options?.method === 'POST')).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('blocks active-plan publish at the control and handler while a conflict is unresolved', async () => {
    const current = serverPlan({
      title: 'Server title',
      revision: 5,
      updatedAt: '2026-08-11T10:45:00Z',
      stops: [planStop('start', 'Start', 'Server note')],
    })
    const other = serverPlan({ id: 'other-plan', title: 'Other plan', revision: 2 })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan(), other] }
      if (url === '/api/my-plans/server-plan' && options.method === 'PUT') {
        throw revisionConflict(current, 'response')
      }
      if (url === '/api/my-plans/other-plan/publish' && options.method === 'POST') {
        return { is_public: true, revision: 3, plan: { ...other, is_public: true, revision: 3 } }
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    authState.isLoggedIn.value = true
    authState.user.value = { id: 'planner-user' }
    vi.stubGlobal('$fetch', fetchPlan)
    const wrapper = await mountSuspended(PlannerPage, { global: { stubs: plannerStubs() } })
    try {
      await flushContinuation()
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      const publishButtons = wrapper.findAll('.saved-plan-actions .btn').filter(button => (
        button.text() === 'Riêng tư' || button.text() === 'Công khai'
      ))
      expect(publishButtons).toHaveLength(2)
      expect(publishButtons[0]!.attributes('disabled')).toBeDefined()
      expect(publishButtons[0]!.attributes('aria-describedby')).toBe('planner-publish-conflict-reason')
      expect(wrapper.get('#planner-publish-conflict-reason').text()).toContain('Hãy xử lý xung đột trước')
      expect(publishButtons[1]!.attributes('disabled')).toBeUndefined()

      const vm = wrapper.vm as unknown as {
        publishPlan: (index: number) => Promise<void>
        baseServerRevision: number
        plannerRevisionConflict: { revision: number }
        planTitle: string
        stops: Array<{ notes: string }>
      }
      const callsBeforeGuard = fetchPlan.mock.calls.length
      await vm.publishPlan(0)
      await nextTick()
      expect(fetchPlan).toHaveBeenCalledTimes(callsBeforeGuard)
      expect(vm.baseServerRevision).toBe(4)
      expect(vm.plannerRevisionConflict.revision).toBe(5)
      expect(vm.planTitle).toBe('Local title')
      expect(vm.stops[0]?.notes).toBe('Local note')

      await publishButtons[1]!.trigger('click')
      await flushContinuation()
      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/other-plan/publish', {
        method: 'POST', headers: {}, body: { is_public: true, expected_revision: 2 },
      })
    } finally {
      wrapper.unmount()
    }
  })

  it('keeps the active local draft and old comparison base when conditional publish conflicts', async () => {
    const current = serverPlan({
      title: 'Server title',
      revision: 5,
      updatedAt: '2026-08-11T10:45:00Z',
      stops: [planStop('start', 'Start', 'Server note')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans/server-plan/publish' && options.method === 'POST') {
        throw revisionConflict(current, 'response')
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.saved-plan-actions .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/server-plan/publish', {
        method: 'POST',
        headers: {},
        body: { is_public: true, expected_revision: 4 },
      })
      const vm = wrapper.vm as unknown as {
        baseServerRevision: number
        plannerRevisionConflict: { revision: number }
        planTitle: string
        stops: Array<{ notes: string }>
      }
      expect(vm.baseServerRevision).toBe(4)
      expect(vm.plannerRevisionConflict.revision).toBe(5)
      expect(vm.planTitle).toBe('Local title')
      expect(vm.stops[0]?.notes).toBe('Local note')
      expect(wrapper.get('[data-planner-conflict-diff]').text()).toContain('Bản máy chủ 5')
    } finally {
      wrapper.unmount()
    }
  })

  it('refreshes only the saved snapshot when a non-active conditional publish conflicts', async () => {
    const other = serverPlan({ id: 'other-plan', title: 'Other plan', revision: 2 })
    const currentOther = serverPlan({
      id: 'other-plan',
      title: 'Other plan updated elsewhere',
      revision: 3,
      updatedAt: '2026-08-11T10:50:00Z',
      is_public: true,
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan(), other] }
      if (url === '/api/my-plans/other-plan/publish' && options.method === 'POST') {
        throw revisionConflict(currentOther, 'data')
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan, 2)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local active title')
      await wrapper.findAll('.saved-plan-actions .btn')[3]!.trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/other-plan/publish', {
        method: 'POST',
        headers: {},
        body: { is_public: true, expected_revision: 2 },
      })
      const vm = wrapper.vm as unknown as {
        activeServerPlanId: string
        baseServerRevision: number
        plannerRevisionConflict: unknown
        planTitle: string
        savedPlans: Array<{ id?: string; revision?: number; title: string }>
      }
      expect(vm.activeServerPlanId).toBe('server-plan')
      expect(vm.baseServerRevision).toBe(4)
      expect(vm.planTitle).toBe('Local active title')
      expect(vm.plannerRevisionConflict).toBeNull()
      expect(vm.savedPlans[1]).toEqual(expect.objectContaining({
        id: 'other-plan',
        revision: 3,
        title: 'Other plan updated elsewhere',
      }))
      expect(mocks.showToast).toHaveBeenCalledWith(
        'Lịch trình đã thay đổi trên thiết bị khác. Hãy tải lại rồi thử lại.',
        'warning',
      )
    } finally {
      wrapper.unmount()
    }
  })

  it('uses the returned server snapshot when the user selects the server recovery', async () => {
    const current = serverPlan({
      title: 'Server title',
      revision: 5,
      updatedAt: '2026-08-11T10:45:00Z',
      stops: [planStop('start', 'Start', 'Server note')],
    })
    const wrapper = await mountAuthenticatedPlanner(conflictFetch(current, 'response'))
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()
      await wrapper.get('[data-conflict-server]').trigger('click')
      await flushContinuation()

      const vm = wrapper.vm as unknown as {
        planTitle: string
        stops: Array<{ notes: string }>
        savedPlans: Array<{ title: string; revision: number }>
        baseServerRevision: number
      }
      expect(vm.planTitle).toBe('Server title')
      expect(vm.stops[0]?.notes).toBe('Server note')
      expect(vm.savedPlans).toHaveLength(1)
      expect(vm.savedPlans[0]).toEqual(expect.objectContaining({ title: 'Server title', revision: 5 }))
      expect(vm.baseServerRevision).toBe(5)
      expect(wrapper.find('[data-planner-conflict-diff]').exists()).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('keeps both snapshots unchanged and the comparison focused for manual recovery', async () => {
    const current = serverPlan({
      title: 'Server title',
      revision: 5,
      updatedAt: '2026-08-11T10:45:00Z',
      stops: [planStop('start', 'Start', 'Server note')],
    })
    const wrapper = await mountAuthenticatedPlanner(conflictFetch(current, 'response'))
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.builder-title').setValue('Local title')
      await wrapper.get('.stop-note-input').setValue('Local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()
      const recoveryBefore = wrapper.get('[data-planner-conflict-diff]')
      const before = recoveryBefore.text()
      const focus = vi.spyOn(recoveryBefore.element as HTMLElement, 'focus')
      await wrapper.get('[data-conflict-manual]').trigger('click')
      await nextTick()

      const recovery = wrapper.get('[data-planner-conflict-diff]')
      const vm = wrapper.vm as unknown as { planTitle: string; stops: Array<{ notes: string }> }
      expect(recovery.text()).toBe(before)
      expect(focus).toHaveBeenCalledTimes(1)
      expect(vm.planTitle).toBe('Local title')
      expect(vm.stops[0]?.notes).toBe('Local note')
    } finally {
      wrapper.unmount()
    }
  })

  it('persists the snapshot revision returned by conditional publish for the next PUT after remount', async () => {
    const published = serverPlan({ revision: 5, is_public: true, updatedAt: '2026-08-11T11:00:00Z' })
    const updated = serverPlan({
      revision: 6,
      is_public: true,
      updatedAt: '2026-08-11T11:02:00Z',
      stops: [planStop('start', 'Start', 'After publish')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans/server-plan/publish' && options.method === 'POST') {
        return { is_public: true, revision: published.revision, plan: published }
      }
      if (url === '/api/my-plans/server-plan' && options.method === 'PUT') return { plan: updated }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    let wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.saved-plan-actions .btn').trigger('click')
      await flushContinuation()
      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/server-plan/publish', {
        method: 'POST',
        headers: {},
        body: { is_public: true, expected_revision: 4 },
      })
      wrapper.unmount()
      wrapper = await mountAuthenticatedPlanner(fetchPlan)
      await wrapper.get('.stop-note-input').setValue('After publish')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans/server-plan', {
        method: 'PUT',
        headers: {},
        body: {
          title: 'Baseline',
          stops: [planStop('start', 'Start', 'After publish')],
          expected_revision: 5,
        },
      })
    } finally {
      wrapper.unmount()
    }
  })

  it('fails closed for a restored legacy server draft without identity', async () => {
    localStorage.setItem('vl360_planner_draft', JSON.stringify({
      title: 'Legacy local title',
      stops: [planStop('start', 'Start', 'Legacy local note')],
      revision: 7,
      savedAt: '2026-08-11T12:00:00Z',
      source: 'server',
      travelBudgetMinutes: null,
    }))
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      expect((wrapper.get('.builder-title').element as HTMLInputElement).value).toBe('Legacy local title')
      expect((wrapper.get('.stop-note-input').element as HTMLInputElement).value).toBe('Legacy local note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan.mock.calls).toEqual([['/api/my-plans', { headers: {} }]])
      expect(mocks.showToast).toHaveBeenCalledWith(
        'Bản nháp máy chủ thiếu thông tin phiên bản. Hãy tải lại lịch trình đã lưu trước khi lưu.',
        'error',
      )
      expect((wrapper.get('.builder-title').element as HTMLInputElement).value).toBe('Legacy local title')
      expect((wrapper.get('.stop-note-input').element as HTMLInputElement).value).toBe('Legacy local note')
    } finally {
      wrapper.unmount()
    }
  })

  it('drops deleted active-plan identity before remount so the draft creates instead of updating', async () => {
    let deleted = false
    const created = serverPlan({ id: 'replacement-plan', title: 'Baseline', revision: 1 })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) {
        return { plans: deleted ? [] : [serverPlan()] }
      }
      if (url === '/api/my-plans/server-plan' && options.method === 'DELETE') {
        deleted = true
        return {}
      }
      if (url === '/api/my-plans' && options.method === 'POST') {
        return { id: created.id, revision: created.revision, plan: created }
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    let wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.saved-plan-actions .danger').trigger('click')
      await flushContinuation()
      wrapper.unmount()

      wrapper = await mountSuspended(PlannerPage, { global: { stubs: plannerStubs() } })
      await flushContinuation()
      expect(wrapper.findAll('.saved-plan-item')).toHaveLength(0)
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans', {
        method: 'POST', headers: {}, body: {
          title: 'Baseline',
          stops: [planStop('start', 'Start')],
        },
      })
      expect(fetchPlan.mock.calls.some(([url, options]) => (
        url === '/api/my-plans/server-plan' && options?.method === 'PUT'
      ))).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('keeps the rollout-disabled rollback path create-only', async () => {
    publicOptimizerMode.mode = 'deterministic'
    const created = serverPlan({
      id: 'server-copy',
      revision: 1,
      updatedAt: '2026-08-11T12:00:00Z',
      stops: [planStop('start', 'Start', 'Rollback note')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return { id: created.id, plan: created }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.stop-note-input').setValue('Rollback note')
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans', {
        method: 'POST',
        headers: {},
        body: {
          title: 'Baseline',
          stops: [planStop('start', 'Start', 'Rollback note')],
        },
      })
      expect(fetchPlan.mock.calls.some(([url, options]) => url.includes('server-plan') && options?.method === 'PUT')).toBe(false)
      expect(wrapper.findAll('.saved-plan-item')).toHaveLength(2)
    } finally {
      wrapper.unmount()
    }
  })

  it('creates a new server plan after the active server draft is explicitly cleared', async () => {
    const created = serverPlan({
      id: 'new-server-plan',
      title: 'Lịch trình chưa đặt tên',
      revision: 1,
      updatedAt: '2026-08-11T12:30:00Z',
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return { id: created.id, plan: created }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      await wrapper.get('.planner-action-dock .btn-ghost').trigger('click')
      await flushContinuation()
      await wrapper.get('.picker-item').trigger('click')
      await flushContinuation()
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans', {
        method: 'POST',
        headers: {},
        body: {
          title: 'Lịch trình chưa đặt tên',
          stops: [planStop('start', 'Start')],
        },
      })
      expect(fetchPlan.mock.calls.some(([url, options]) => url === '/api/my-plans/server-plan' && options?.method === 'PUT')).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('clears the active server identity when a local saved plan is loaded', async () => {
    const created = serverPlan({
      id: 'local-promoted-plan',
      title: 'Local saved plan',
      revision: 1,
      updatedAt: '2026-08-11T12:45:00Z',
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return { id: created.id, plan: created }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await loadFirstSavedPlan(wrapper)
      const vm = wrapper.vm as unknown as { savedPlans: Array<Record<string, unknown>> }
      vm.savedPlans.push({
        title: 'Local saved plan',
        stops: [planStop('start', 'Start')],
        savedAt: '2026-08-11T12:40:00Z',
      })
      await nextTick()
      await wrapper.findAll('.saved-plan-btn')[1]!.trigger('click')
      await flushContinuation()
      await wrapper.get('.planner-action-dock .btn').trigger('click')
      await flushContinuation()

      expect(fetchPlan).toHaveBeenCalledWith('/api/my-plans', {
        method: 'POST',
        headers: {},
        body: {
          title: 'Local saved plan',
          stops: [planStop('start', 'Start')],
        },
      })
      expect(fetchPlan.mock.calls.some(([url, options]) => url === '/api/my-plans/server-plan' && options?.method === 'PUT')).toBe(false)
    } finally {
      wrapper.unmount()
    }
  })

  it('guards saved-plan loading while an authenticated create is pending and preserves later local edits', async () => {
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const existing = serverPlan({ id: 'other-plan', title: 'Other plan', revision: 2 })
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:00:00Z',
      stops: [planStop('start', 'Start')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [existing] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      await wrapper.get('.builder-title').setValue('Create draft')
      const vm = wrapper.vm as unknown as {
        activeServerPlanId: string | null
        baseServerRevision: number | null
        loadPlan: (index: number) => Promise<void>
        localDirty: boolean
        planTitle: string
        savePlan: () => Promise<void>
        saving: boolean
        stops: Array<{ notes: string }>
      }
      const save = vm.savePlan()
      await nextTick()

      const loadControl = wrapper.get('.saved-plan-btn')
      expect(loadControl.attributes('disabled')).toBeDefined()
      const confirmationsBefore = mocks.confirmDialog.mock.calls.length
      await loadControl.trigger('click')
      await vm.loadPlan(0)
      expect(mocks.confirmDialog).toHaveBeenCalledTimes(confirmationsBefore)
      expect(vm.planTitle).toBe('Create draft')
      expect(vm.activeServerPlanId).toBeNull()

      await wrapper.get('.builder-title').setValue('Create draft edited')
      await wrapper.get('.stop-note-input').setValue('Later local edit')
      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()

      expect(vm.activeServerPlanId).toBe('created-plan')
      expect(vm.baseServerRevision).toBe(1)
      expect(vm.planTitle).toBe('Create draft edited')
      expect(vm.stops[0]?.notes).toBe('Later local edit')
      expect(vm.localDirty).toBe(true)
    } finally {
      wrapper.unmount()
    }
  })

  it('guards clear through the rendered control and handler until an authenticated create settles', async () => {
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:05:00Z',
      stops: [planStop('start', 'Start')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      await wrapper.get('.builder-title').setValue('Create draft')
      const vm = wrapper.vm as unknown as {
        activeServerPlanId: string | null
        clearPlan: () => Promise<void>
        planTitle: string
        savePlan: () => Promise<void>
        stops: Array<{ id: string }>
      }
      const save = vm.savePlan()
      await nextTick()

      const clearControl = wrapper.get('.planner-action-dock .btn-ghost')
      expect(clearControl.attributes('disabled')).toBeDefined()
      const confirmationsBefore = mocks.confirmDialog.mock.calls.length
      await clearControl.trigger('click')
      await vm.clearPlan()
      expect(mocks.confirmDialog).toHaveBeenCalledTimes(confirmationsBefore)
      expect(vm.planTitle).toBe('Create draft')
      expect(vm.stops.map(stop => stop.id)).toEqual(['start'])
      expect(vm.activeServerPlanId).toBeNull()

      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()
      expect(vm.activeServerPlanId).toBe('created-plan')
      expect(vm.planTitle).toBe('Create draft')
      expect(vm.stops.map(stop => stop.id)).toEqual(['start'])
    } finally {
      wrapper.unmount()
    }
  })

  it('rechecks saving after a pending clear confirmation before mutating the draft', async () => {
    const pendingConfirmation = deferred<boolean>()
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:15:00Z',
      stops: [planStop('start', 'Start')],
    })
    mocks.confirmDialog.mockImplementationOnce(() => pendingConfirmation.promise)
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      await wrapper.get('.builder-title').setValue('Create draft')
      const vm = wrapper.vm as unknown as {
        activeServerPlanId: string | null
        clearPlan: () => Promise<void>
        planTitle: string
        savePlan: () => Promise<void>
        stops: Array<{ id: string }>
      }

      const clear = vm.clearPlan()
      expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
      const save = vm.savePlan()
      await nextTick()
      expect(wrapper.get('.planner-action-dock .btn-ghost').attributes('disabled')).toBeDefined()

      pendingConfirmation.resolve(true)
      await clear
      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()

      expect(vm.planTitle).toBe('Create draft')
      expect(vm.stops.map(stop => stop.id)).toEqual(['start'])
      expect(vm.activeServerPlanId).toBe('created-plan')
    } finally {
      wrapper.unmount()
    }
  })

  it('rechecks saving after a pending load confirmation before switching the draft', async () => {
    const pendingConfirmation = deferred<boolean>()
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const existing = serverPlan({ id: 'other-plan', title: 'Other plan', revision: 2 })
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:20:00Z',
      stops: [planStop('start', 'Start')],
    })
    mocks.confirmDialog.mockImplementationOnce(() => pendingConfirmation.promise)
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [existing] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      await wrapper.get('.builder-title').setValue('Create draft')
      const vm = wrapper.vm as unknown as {
        activeServerPlanId: string | null
        loadPlan: (index: number) => Promise<void>
        planTitle: string
        savePlan: () => Promise<void>
        stops: Array<{ id: string }>
      }

      const load = vm.loadPlan(0)
      expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
      const save = vm.savePlan()
      await nextTick()
      expect(wrapper.get('.saved-plan-btn').attributes('disabled')).toBeDefined()

      pendingConfirmation.resolve(true)
      await load
      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()

      expect(vm.planTitle).toBe('Create draft')
      expect(vm.stops.map(stop => stop.id)).toEqual(['start'])
      expect(vm.activeServerPlanId).toBe('created-plan')
    } finally {
      wrapper.unmount()
    }
  })

  it('rechecks saving after a pending delete confirmation before deleting a saved plan', async () => {
    const pendingConfirmation = deferred<boolean>()
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:25:00Z',
      stops: [planStop('start', 'Start')],
    })
    let deletes = 0
    mocks.confirmDialog.mockImplementationOnce(() => pendingConfirmation.promise)
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      if (url === '/api/my-plans/server-plan' && options.method === 'DELETE') {
        deletes += 1
        return {}
      }
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      const vm = wrapper.vm as unknown as {
        deletePlan: (index: number) => Promise<void>
        savePlan: () => Promise<void>
        savedPlans: Array<{ id?: string }>
      }

      const remove = vm.deletePlan(0)
      expect(mocks.confirmDialog).toHaveBeenCalledTimes(1)
      const save = vm.savePlan()
      await nextTick()
      expect(wrapper.get('.saved-plan-actions .danger').attributes('disabled')).toBeDefined()

      pendingConfirmation.resolve(true)
      await remove
      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()

      expect(deletes).toBe(0)
      expect(vm.savedPlans.map(plan => plan.id)).toEqual(['created-plan', 'server-plan'])
    } finally {
      wrapper.unmount()
    }
  })

  it('discards a late create result when the draft generation advances with the same identity tuple', async () => {
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:30:00Z',
      stops: [planStop('start', 'Start')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      await wrapper.get('.builder-title').setValue('Create draft')
      const vm = wrapper.vm as unknown as {
        activeServerPlanId: string | null
        clearActiveServerPlan: () => void
        planTitle: string
        savePlan: () => Promise<void>
        savedPlans: Array<{ id?: string }>
        stops: Array<{ id: string }>
      }

      const save = vm.savePlan()
      await nextTick()
      vm.clearActiveServerPlan()
      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()

      expect(vm.activeServerPlanId).toBeNull()
      expect(vm.planTitle).toBe('Create draft')
      expect(vm.stops.map(stop => stop.id)).toEqual(['start'])
      expect(vm.savedPlans.some(plan => plan.id === 'created-plan')).toBe(false)
      expect(mocks.showToast).toHaveBeenCalledWith(
        'Kết quả lưu cũ đã được bỏ qua vì lịch trình đang mở đã thay đổi.',
        'warning',
      )
    } finally {
      wrapper.unmount()
    }
  })

  it('guards publish and delete controls and handlers while a save is pending', async () => {
    const pendingCreate = deferred<{ plan: ReturnType<typeof serverPlan> }>()
    const created = serverPlan({
      id: 'created-plan',
      title: 'Create draft',
      revision: 1,
      updatedAt: '2026-08-11T13:10:00Z',
      stops: [planStop('start', 'Start')],
    })
    const fetchPlan = vi.fn(async (url: string, options: Record<string, any> = {}) => {
      if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
      if (url === '/api/my-plans' && options.method === 'POST') return pendingCreate.promise
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
    })
    const wrapper = await mountAuthenticatedPlanner(fetchPlan)
    try {
      await wrapper.get('.picker-item').trigger('click')
      const vm = wrapper.vm as unknown as {
        deletePlan: (index: number) => Promise<void>
        publishPlan: (index: number) => Promise<void>
        savePlan: () => Promise<void>
        savedPlans: Array<{ id?: string }>
      }
      const save = vm.savePlan()
      await nextTick()

      const publishControl = wrapper.get('.saved-plan-actions .btn')
      const deleteControl = wrapper.get('.saved-plan-actions .danger')
      expect(publishControl.attributes('disabled')).toBeDefined()
      expect(deleteControl.attributes('disabled')).toBeDefined()
      const requestsBefore = fetchPlan.mock.calls.length
      const confirmationsBefore = mocks.confirmDialog.mock.calls.length
      await publishControl.trigger('click')
      await deleteControl.trigger('click')
      await vm.publishPlan(0)
      await vm.deletePlan(0)
      expect(fetchPlan).toHaveBeenCalledTimes(requestsBefore)
      expect(mocks.confirmDialog).toHaveBeenCalledTimes(confirmationsBefore)
      expect(vm.savedPlans[0]?.id).toBe('server-plan')

      pendingCreate.resolve({ plan: created })
      await save
      await flushContinuation()
    } finally {
      wrapper.unmount()
    }
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

  it('keeps known stale evidence when refresh returns partial, malformed, or status-less detail', async () => {
    const originalEvidence = {
      status: 'stale',
      updatedAt: '2026-06-01T00:00:00Z',
      sourceTitle: 'Nguồn kiểm chứng',
    }
    mocks.listEntities.mockResolvedValue({
      total: 1,
      entities: [entityWithFreshness('start', 'Start', 'stale', originalEvidence.updatedAt)],
    })
    mocks.getEntity
      .mockResolvedValueOnce({
        id: 'start', name: 'Start', type: 'attraction', coordinates: [10.01, 106.01],
        source_freshness: { source_title: 'Nguồn chỉ có tên' },
      })
      .mockResolvedValueOnce({
        id: 'start', name: 'Start', type: 'attraction', coordinates: [10.01, 106.01],
        source_freshness: {
          freshness_status: 'recent-enough',
          updated_at: '2026-08-09T11:00:00Z',
        },
      })
      .mockResolvedValueOnce({
        id: 'start', name: 'Start', type: 'attraction', coordinates: [10.01, 106.01],
      })
    const wrapper = await mountSuspended(PlannerPage, {
      global: { stubs: plannerStubs() },
    })

    try {
      await wrapper.get('.picker-item').trigger('click')
      await flushContinuation()
      const vm = wrapper.vm as unknown as {
        stops: Array<{ id: string; sourceFreshness?: typeof originalEvidence }>
      }

      for (let attempt = 0; attempt < 3; attempt += 1) {
        await wrapper.get('[data-friction-code="stale-stop-facts"] [data-friction-recovery]').trigger('click')
        await flushContinuation()
        expect(wrapper.find('[data-friction-code="stale-stop-facts"]').exists()).toBe(true)
        expect(vm.stops[0]?.sourceFreshness).toEqual(originalEvidence)
      }

      const persisted = JSON.parse(localStorage.getItem('vl360_planner_draft') || '{}')
      expect(persisted.stops?.[0]?.sourceFreshness).toEqual(originalEvidence)
    } finally {
      wrapper.unmount()
    }
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

  it('advances the guest Journey Thread to planning and clears it with an explicit plan reset', async () => {
    useJourneyThread({ ownerScope: 'guest' }).snapshot({
      intent: 'explore',
      returnPath: '/tim-kiem?q=g%E1%BB%91m',
      currentPath: '/dia-diem/cong-vien-an-hoi',
    })
    const wrapper = await mountSuspended(PlannerPage, {
      route: '/tao-lich-trinh',
      global: { stubs: plannerStubs() },
    })
    const vm = wrapper.vm as unknown as { clearPlan: () => Promise<void> }

    expect(useJourneyThread({ ownerScope: 'guest' }).restore()).toEqual(expect.objectContaining({
      intent: 'plan',
      returnPath: '/tim-kiem?q=g%E1%BB%91m',
      currentPath: '/tao-lich-trinh',
    }))

    await vm.clearPlan()
    expect(useJourneyThread({ ownerScope: 'guest' }).restore()).toBeNull()
    wrapper.unmount()
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

async function mountAuthenticatedPlanner(fetchPlan: ReturnType<typeof vi.fn>, expectedPlanCount = 1) {
  authState.isLoggedIn.value = true
  authState.user.value = { id: 'planner-user' }
  vi.stubGlobal('$fetch', fetchPlan)
  const wrapper = await mountSuspended(PlannerPage, {
    global: { stubs: plannerStubs() },
  })
  await flushContinuation()
  expect(wrapper.findAll('.saved-plan-item')).toHaveLength(expectedPlanCount)
  return wrapper
}

async function loadFirstSavedPlan(wrapper: Awaited<ReturnType<typeof mountSuspended>>) {
  await wrapper.get('.saved-plan-btn').trigger('click')
  await flushContinuation()
  expect(wrapper.findAll('.stop-item')).toHaveLength(1)
}

function conflictFetch(current: ReturnType<typeof serverPlan>, surface: 'response' | 'data') {
  return vi.fn(async (url: string, options: Record<string, any> = {}) => {
    if (url === '/api/my-plans' && !options.method) return { plans: [serverPlan()] }
    if (url === '/api/my-plans/server-plan' && options.method === 'PUT') {
      throw revisionConflict(current, surface)
    }
    throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`)
  })
}

function revisionConflict(current: ReturnType<typeof serverPlan>, surface: 'response' | 'data') {
  const payload = {
    detail: 'Lịch trình đã thay đổi trên thiết bị khác',
    code: 'plan_revision_conflict',
    current,
  }
  return surface === 'response'
    ? { response: { status: 409, _data: payload } }
    : { statusCode: 409, data: payload }
}

function serverPlan(overrides: Partial<{
  id: string
  title: string
  stops: ReturnType<typeof planStop>[]
  savedAt: string
  updatedAt: string
  revision: number
  is_public: boolean
}> = {}) {
  return {
    id: 'server-plan',
    title: 'Baseline',
    stops: [planStop('start', 'Start')],
    savedAt: '2026-08-09T08:00:00Z',
    updatedAt: '2026-08-10T08:00:00Z',
    revision: 4,
    is_public: false,
    ...overrides,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
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
