import { describe, expect, it } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import * as plannerOptimization from '../composables/useItineraryOptimization'
import PlannerFrictionNotice from '../components/planner/PlannerFrictionNotice.vue'
import PlannerSummary from '../components/planner/PlannerSummary.vue'

describe('planner friction projection', () => {
  it('renders a recoverable notice with explicit code and severity', async () => {
    const wrapper = await mountSuspended(PlannerFrictionNotice, {
      props: {
        code: 'missing-coordinates',
        severity: 'warning',
        reason: 'Điểm dừng chưa có tọa độ.',
        recovery: { label: 'Mở chỉnh sửa thủ công', action: 'edit-stop' },
      },
    })

    expect(wrapper.get('[data-friction-code="missing-coordinates"]').attributes('data-friction-severity')).toBe('warning')
    expect(wrapper.text()).toContain('Điểm dừng chưa có tọa độ.')
    expect(wrapper.get('[data-friction-recovery]').text()).toContain('Mở chỉnh sửa thủ công')
    await wrapper.get('[data-friction-recovery]').trigger('click')
    expect(wrapper.emitted('recover')).toHaveLength(1)
    wrapper.unmount()
  })

  it('keeps summary evidence visible when warnings are present', async () => {
    const wrapper = await mountSuspended(PlannerSummary, {
      props: {
        stopCount: 3,
        totalDuration: 7200,
        travelDuration: 1800,
        warnings: ['Bản đồ tạm thời không khả dụng.'],
      },
    })

    expect(wrapper.get('[data-summary-stop-count]').text()).toBe('3')
    expect(wrapper.get('[data-summary-total-duration]').text()).toContain('2 giờ')
    expect(wrapper.get('[data-summary-travel-duration]').text()).toContain('30 phút')
    expect(wrapper.get('[data-summary-warnings]').text()).toContain('Bản đồ tạm thời không khả dụng.')
    wrapper.unmount()
  })

  it('reports an opening-hour conflict with a targeted recovery', () => {
    const project = (plannerOptimization as Record<string, unknown>)
      .projectPlannerFrictions as undefined | ((input: Record<string, unknown>) => Array<Record<string, unknown>>)

    expect(project).toEqual(expect.any(Function))
    if (!project) return

    const [notice] = project({
      openingHourConflicts: [{ stopId: 'museum', requestedTime: '07:00-08:00', openingHours: '09:00-17:00' }],
    })
    expect(notice).toMatchObject({
      code: 'opening-hours-conflict',
      severity: 'warning',
      reason: expect.stringContaining('07:00-08:00'),
      recovery: expect.objectContaining({ label: expect.stringContaining('khung giờ') }),
    })
  })

  it('reports travel time over budget without inventing a route estimate', () => {
    const project = (plannerOptimization as Record<string, unknown>)
      .projectPlannerFrictions as undefined | ((input: Record<string, unknown>) => Array<Record<string, unknown>>)

    expect(project).toEqual(expect.any(Function))
    if (!project) return

    const [notice] = project({ travelMinutes: 185, travelBudgetMinutes: 120 })
    expect(notice).toMatchObject({
      code: 'travel-time-over-budget',
      severity: 'warning',
      reason: expect.stringContaining('185'),
      recovery: expect.objectContaining({ label: expect.stringContaining('ngân sách') }),
    })
  })

  it.each([
    ['stale-stop-facts', { staleStopIds: ['market'] }],
    ['missing-coordinates', { missingCoordinateStopIds: ['orchard'] }],
    ['offline-draft', { offlineDraft: { revision: 4, savedAt: '2026-08-09T08:00:00Z' } }],
    ['revision-conflict', { revisionConflict: { localRevision: 4, serverRevision: 5 } }],
  ])('reports the recoverable %s friction state', (code, input) => {
    const project = (plannerOptimization as Record<string, unknown>)
      .projectPlannerFrictions as undefined | ((value: Record<string, unknown>) => Array<Record<string, unknown>>)

    expect(project).toEqual(expect.any(Function))
    if (!project) return

    const [notice] = project(input)
    expect(notice?.code).toBe(code)
    expect(notice?.recovery).toMatchObject({ label: expect.any(String) })
  })

  it('keeps map and routing failure as an additive fallback notice', () => {
    const project = (plannerOptimization as Record<string, unknown>)
      .projectPlannerFrictions as undefined | ((input: Record<string, unknown>) => Array<Record<string, unknown>>)

    expect(project).toEqual(expect.any(Function))
    if (!project) return

    expect(project({ routeUnavailable: true })[0]).toMatchObject({
      code: 'route-unavailable',
      severity: 'info',
      recovery: expect.objectContaining({ label: expect.stringContaining('danh sách') }),
    })
  })

  it('diffs a revision conflict per stop without choosing a winner', () => {
    const local = [
      { id: 'a', name: 'A', notes: 'ghi chú local' },
      { id: 'b', name: 'B', notes: '' },
    ]
    const server = [
      { id: 'a', name: 'A', notes: 'ghi chú server' },
      { id: 'c', name: 'C', notes: '' },
    ]

    expect(plannerOptimization.diffPlannerStops(local, server)).toEqual([
      { id: 'a', local: local[0], server: server[0], changedFields: ['notes'] },
      { id: 'b', local: local[1], server: null, changedFields: ['stop'] },
      { id: 'c', local: null, server: server[1], changedFields: ['stop'] },
    ])
    expect(local.map(stop => stop.id)).toEqual(['a', 'b'])
  })

  it('treats a server reorder as a per-stop position diff', () => {
    const local = [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }]
    const server = [local[1]!, local[0]!]

    expect(plannerOptimization.diffPlannerStops(local, server).map(conflict => ({
      id: conflict.id,
      changedFields: conflict.changedFields,
    }))).toEqual([
      { id: 'a', changedFields: ['position'] },
      { id: 'b', changedFields: ['position'] },
    ])
  })

  it('creates a deterministic offline draft without mutating editable stops', () => {
    const createSnapshot = (plannerOptimization as Record<string, unknown>)
      .createPlannerDraftSnapshot as undefined | ((input: Record<string, unknown>) => Record<string, unknown>)

    expect(createSnapshot).toEqual(expect.any(Function))
    if (!createSnapshot) return

    const stops = [{
      id: 'a',
      name: 'A',
      type: 'attraction',
      coords: [10, 106] as [number, number],
      time: '08:00-09:00',
      notes: 'ghi chú local',
      transient: 'không lưu',
    }]
    const snapshot = createSnapshot({
      title: 'Một ngày',
      stops,
      revision: 7,
      savedAt: '2026-08-09T09:00:00Z',
      source: 'local',
      travelBudgetMinutes: 120,
    })

    expect(snapshot).toEqual({
      title: 'Một ngày',
      stops: [{
        id: 'a', name: 'A', type: 'attraction', coords: [10, 106],
        time: '08:00-09:00', notes: 'ghi chú local',
      }],
      revision: 7,
      savedAt: '2026-08-09T09:00:00Z',
      source: 'local',
      travelBudgetMinutes: 120,
    })
    expect(stops[0]?.transient).toBe('không lưu')
  })
})
