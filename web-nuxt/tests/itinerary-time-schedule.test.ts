// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'
import {
  buildTableUrl,
  fetchRouteTable,
  parseTableResponse,
  type RouteTableResult,
} from '../composables/useRouting'
import {
  applySchedulePlacement,
  applySchedulePlacements,
  buildPlannerScheduleEnvelope,
  collectRoutableStops,
  commitPlannerOptimizationResult,
  enrichPlannerStopFromDetail,
  formatScheduledInterval,
  getCachedRouteTable,
  invalidatePlannerInputs,
  mergeOptimizedStops,
  plannerMetadataForEntity,
  plannerMetadataForLoadedStop,
  requestOptimizedOrder,
  routeTableCacheKey,
  runPlannerOptimization,
  serializePlanStops,
  type OptimizeOrderResponse,
  type OptimizeScheduleRequest,
  type PlannerInputState,
  type PlannerScheduleMetadata,
} from '../composables/useItineraryOptimization'

const cachedTable: RouteTableResult = {
  distanceKm: [[0, 1], [1, 0]],
  durationMinutes: [[0, 2], [2, 0]],
  source: 'osrm-table',
}

describe('OSRM Table routing', () => {
  it('requests all-pairs distance and duration annotations', () => {
    expect(buildTableUrl([[10, 106], [10.2, 106.4]], 'driving')).toBe(
      'https://router.project-osrm.org/table/v1/car/'
      + '106,10;106.4,10.2?annotations=distance,duration',
    )
  })

  it('converts distances to non-driving durations consistently with route parsing', () => {
    const response = {
      code: 'Ok',
      distances: [[0, 40000], [40000, 0]],
      durations: [[0, 3600], [3600, 0]],
    }
    const cyclingTable = parseTableResponse(response, 'cycling')
    const footTable = parseTableResponse(response, 'foot')

    expect(cyclingTable?.distanceKm[0]?.[1]).toBe(40)
    expect(cyclingTable?.durationMinutes[0]?.[1]).toBe(160)
    expect(footTable?.durationMinutes[0]?.[1]).toBe(480)
    expect(cyclingTable?.source).toBe('osrm-table')
  })

  it('uses OSRM driving durations and distance fallback for missing cells', () => {
    const table = parseTableResponse({
      code: 'Ok',
      distances: [[0, 40000], [10000, 0]],
      durations: [[0, 1800], [null, 0]],
    }, 'driving')

    expect(table?.durationMinutes).toEqual([[0, 30], [15, 0]])
  })

  it('rejects incomplete, negative, or non-finite tables', () => {
    expect(parseTableResponse({
      code: 'Ok',
      distances: [[0, 1], [1]],
      durations: [[0, 1], [1, 0]],
    }, 'driving')).toBeNull()
    expect(parseTableResponse({
      code: 'Ok',
      distances: [[0, Number.POSITIVE_INFINITY], [1, 0]],
      durations: [[0, 1], [1, 0]],
    }, 'driving')).toBeNull()
    expect(parseTableResponse({
      code: 'Ok',
      distances: [[0, 1], [1, 0]],
      durations: [[0, 1], [1]],
    }, 'driving')).toBeNull()
    expect(parseTableResponse({
      code: 'Ok',
      distances: [[0, 1], [1, 0]],
      durations: [[0, Number.NaN], [1, 0]],
    }, 'driving')).toBeNull()
    expect(parseTableResponse({
      code: 'Ok',
      distances: [[0, 1], [1, 0]],
      durations: [[0, -1], [1, 0]],
    }, 'driving')).toBeNull()
    expect(parseTableResponse({
      code: 'NoRoute',
      distances: [],
      durations: [],
    }, 'driving')).toBeNull()
  })

  it('performs one injected Table request and parses its result', async () => {
    let calls = 0
    let requestedUrl = ''
    const result = await fetchRouteTable(
      [[10, 106], [10.2, 106.4]],
      'driving',
      async (url) => {
        calls += 1
        requestedUrl = url
        return {
          code: 'Ok',
          distances: [[0, 1000], [1000, 0]],
          durations: [[0, 120], [120, 0]],
        }
      },
    )

    expect(calls).toBe(1)
    expect(requestedUrl).toBe(
      'https://router.project-osrm.org/table/v1/car/'
      + '106,10;106.4,10.2?annotations=distance,duration',
    )
    expect(result).toEqual({
      distanceKm: [[0, 1], [1, 0]],
      durationMinutes: [[0, 2], [2, 0]],
      source: 'osrm-table',
    })
  })

  it('returns null after one failed Table request without retrying', async () => {
    let calls = 0
    const result = await fetchRouteTable(
      [[10, 106], [10.2, 106.4]],
      'driving',
      async () => {
        calls += 1
        throw new Error('offline')
      },
    )

    expect(result).toBeNull()
    expect(calls).toBe(1)
  })
})

describe('route Table cache', () => {
  it('rounds coordinates to five decimals and includes transport mode', () => {
    const drivingKey = routeTableCacheKey([
      [10.123456, 106.654321],
      [10.000004, 106.000004],
    ], 'driving')

    expect(drivingKey).toBe(
      'driving:10.12346,106.65432;10.00000,106.00000',
    )
    expect(routeTableCacheKey([
      [10.123456, 106.654321],
      [10.000004, 106.000004],
    ], 'cycling')).not.toBe(drivingKey)
  })

  it('caches successful and null results for the same key', async () => {
    let successCalls = 0
    const successFetcher = async () => {
      successCalls += 1
      return cachedTable
    }
    await getCachedRouteTable('cache-success', successFetcher)
    await getCachedRouteTable('cache-success', successFetcher)

    let nullCalls = 0
    const nullFetcher = async () => {
      nullCalls += 1
      return null
    }
    await getCachedRouteTable('cache-null', nullFetcher)
    await getCachedRouteTable('cache-null', nullFetcher)

    expect(successCalls).toBe(1)
    expect(nullCalls).toBe(1)
  })

  it('deduplicates concurrent calls for the same key', async () => {
    let calls = 0
    let resolveTable!: (value: RouteTableResult) => void
    const pending = new Promise<RouteTableResult>((resolve) => {
      resolveTable = resolve
    })
    const fetcher = () => {
      calls += 1
      return pending
    }

    const first = getCachedRouteTable('cache-concurrent', fetcher)
    const second = getCachedRouteTable('cache-concurrent', fetcher)
    expect(calls).toBe(1)

    resolveTable(cachedTable)
    const [firstResult, secondResult] = await Promise.all([first, second])
    expect(firstResult).toBe(cachedTable)
    expect(secondResult).toBe(cachedTable)
  })

  it('removes rejected pending entries so a later action can retry', async () => {
    let calls = 0
    const fetcher = async () => {
      calls += 1
      if (calls === 1) throw new Error('temporary failure')
      return cachedTable
    }

    const first = getCachedRouteTable('cache-rejection', fetcher)
    const concurrent = getCachedRouteTable('cache-rejection', fetcher)
    const rejected = await Promise.allSettled([first, concurrent])
    expect(rejected.map(result => result.status)).toEqual([
      'rejected',
      'rejected',
    ])
    expect(calls).toBe(1)

    await expect(getCachedRouteTable('cache-rejection', fetcher))
      .resolves.toBe(cachedTable)
    expect(calls).toBe(2)
  })

  it('expires entries after fifteen minutes', async () => {
    const now = vi.spyOn(Date, 'now').mockReturnValue(1_000_000)
    let calls = 0
    const fetcher = async () => {
      calls += 1
      return cachedTable
    }

    try {
      await getCachedRouteTable('cache-ttl', fetcher)
      now.mockReturnValue(1_000_000 + (15 * 60 * 1000) - 1)
      await getCachedRouteTable('cache-ttl', fetcher)
      expect(calls).toBe(1)

      now.mockReturnValue(1_000_000 + (15 * 60 * 1000) + 1)
      await getCachedRouteTable('cache-ttl', fetcher)
      expect(calls).toBe(2)
    } finally {
      now.mockRestore()
    }
  })

  it('evicts the oldest entry when the cache exceeds sixteen keys', async () => {
    let calls = 0
    const fetcher = async () => {
      calls += 1
      return cachedTable
    }

    for (let index = 0; index < 17; index += 1) {
      await getCachedRouteTable(`cache-budget-${index}`, fetcher)
    }
    await getCachedRouteTable('cache-budget-0', fetcher)
    await getCachedRouteTable('cache-budget-16', fetcher)

    expect(calls).toBe(18)
  })
})

describe('optional itinerary schedule request', () => {
  it('reuses the schedule envelope and matrix across a U-turn retry request', async () => {
    const routed = collectRoutableStops([
      { id: 'start', coords: [10, 106] as [number, number] },
      { id: 'end', coords: [10.2, 106.4] as [number, number] },
    ])
    const matrix = [[0, 20], [20, 0]]
    const schedule = {
      day_start_minute: 480,
      day_end_minute: 1080,
      mode: 'driving',
      stops: [
        { id: 'planner-stop-0', visit_minutes: 0, required: true },
        {
          id: 'planner-stop-1',
          visit_minutes: 30,
          opening_hours: '09:00-17:00',
          requested_time: '10:00-11:00',
          required: true,
        },
      ],
      duration_matrix_minutes: matrix,
    } satisfies OptimizeScheduleRequest
    const fallbackResponse: OptimizeOrderResponse = {
      ordered_ids: routed.map(item => item.key),
      distance_before_km: 10,
      distance_after_km: 10,
      saved_distance_km: 0,
      backtrack_ratio: 0,
      solver: 'schedule-beam',
      warnings: ['Khong the lap lich; giu thu tu tuyen duong'],
    }
    const requests: Array<{
      url: string
      options: { method: 'POST'; body: Record<string, unknown> }
    }> = []
    const fetcher = async (url: string, options: unknown) => {
      requests.push({
        url,
        options: options as { method: 'POST'; body: Record<string, unknown> },
      })
      return fallbackResponse
    }

    const first = await requestOptimizedOrder(routed, [], schedule, fetcher)
    await requestOptimizedOrder(
      routed,
      [['planner-stop-0', 'planner-stop-1']],
      schedule,
      fetcher,
    )

    expect(requests[0]).toEqual({
      url: '/api/itineraries/optimize-order',
      options: {
        method: 'POST',
        body: {
          stops: [
            { id: 'planner-stop-0', coordinates: [10, 106] },
            { id: 'planner-stop-1', coordinates: [10.2, 106.4] },
          ],
          strict_direction: true,
          blocked_edges: [],
          schedule,
        },
      },
    })
    expect(requests[0]?.options.body.schedule).toBe(schedule)
    expect(requests[1]?.options.body.schedule).toBe(schedule)
    expect(
      (requests[1]?.options.body.schedule as OptimizeScheduleRequest)
        .duration_matrix_minutes,
    ).toBe(matrix)
    expect(first.schedule).toBeUndefined()
    expect(first.warnings).toEqual([
      'Khong the lap lich; giu thu tu tuyen duong',
    ])
  })

  it('types schedule placements with end_visit_minute', () => {
    const placement: NonNullable<
      OptimizeOrderResponse['schedule']
    >['placements'][number] = {
      stop_id: 'planner-stop-1',
      arrival_minute: 500,
      start_visit_minute: 510,
      end_visit_minute: 540,
    }

    expect(placement.end_visit_minute).toBe(540)
  })
})

describe('manual planner schedule integration', () => {
  it('keeps manual fields while exposing a computed interval separately', () => {
    const stop = {
      id: 'a',
      type: 'attraction',
      time: '08:00',
      notes: 'da dat truoc',
    }

    const result = applySchedulePlacement(stop, {
      stop_id: 'planner-stop-0',
      arrival_minute: 500,
      start_visit_minute: 510,
      end_visit_minute: 600,
    })

    expect(result.stop).toBe(stop)
    expect(result.stop.time).toBe('08:00')
    expect(result.stop.notes).toBe('da dat truoc')
    expect(result.scheduledTime).toBe('08:30-10:00')
  })

  it('serializes only the original saved PlanStop keys', () => {
    const serialized = serializePlanStops([{
      id: 'a',
      name: 'A',
      type: 'attraction',
      place_name: 'Vinh Long',
      coords: [10, 106] as [number, number],
      time: '08:00',
      notes: 'giu nguyen',
      scheduledTime: '08:30-10:00',
      placement: { start_visit_minute: 510 },
    }])

    expect(serialized).toEqual([{
      id: 'a',
      name: 'A',
      type: 'attraction',
      place_name: 'Vinh Long',
      coords: [10, 106],
      time: '08:00',
      notes: 'giu nguyen',
    }])
    expect(Object.keys(serialized[0] ?? {}).sort()).toEqual([
      'coords',
      'id',
      'name',
      'notes',
      'place_name',
      'time',
      'type',
    ])
  })

  it('keeps the route-only path free of Table calls and schedule payloads', async () => {
    const routed = collectRoutableStops([
      { id: 'start', coords: [10.01, 106.01] as [number, number], time: '' },
      { id: 'middle', coords: [10.02, 106.02] as [number, number], time: '' },
      { id: 'end', coords: [10.03, 106.03] as [number, number], time: '' },
    ])
    let tableCalls = 0
    const schedules: Array<OptimizeScheduleRequest | undefined> = []
    const inputState: PlannerInputState = { version: 0 }

    const result = await runPlannerOptimization({
      scheduleEnabled: false,
      routed,
      metadataByStop: new WeakMap<object, PlannerScheduleMetadata>(),
      inputState,
      mode: 'driving',
      fetchTable: async () => {
        tableCalls += 1
        return cachedTable
      },
      requestOptimization: async (ordered, _blockedEdges, schedule) => {
        schedules.push(schedule)
        return orderResponse(ordered.map(item => item.key))
      },
      route: async coordinates => routeWithoutUturns(coordinates.length),
    })

    expect(tableCalls).toBe(0)
    expect(schedules).toEqual([undefined])
    expect(result.status).toBe('current')
    if (result.status !== 'current') throw new Error('expected current result')
    expect(result.scheduleEnvelope).toBeUndefined()
  })

  it('fetches one cached Table and reuses one envelope and matrix through the bounded retry', async () => {
    const routed = collectRoutableStops([
      { id: 'start', coords: [11.01, 107.01] as [number, number], time: '' },
      { id: 'middle', coords: [11.02, 107.02] as [number, number], time: '09:00-09:30' },
      { id: 'end', coords: [11.03, 107.03] as [number, number], time: '' },
    ])
    const metadataByStop = new WeakMap<object, PlannerScheduleMetadata>()
    routed.forEach((item, index) => metadataByStop.set(item.stop, {
      visitMinutes: index === 1 ? 30 : 0,
      openingHours: index === 1 ? '08:00-17:00' : null,
      warnings: index === 1 ? [] : ['opening-hours-unknown'],
    }))
    const table = {
      distanceKm: [[0, 1, 2], [1, 0, 1], [2, 1, 0]],
      durationMinutes: [[0, 10, 20], [10, 0, 10], [20, 10, 0]],
      source: 'osrm-table' as const,
    }
    let tableCalls = 0
    let routeCalls = 0
    const schedules: OptimizeScheduleRequest[] = []
    const inputState: PlannerInputState = { version: 0 }

    const result = await runPlannerOptimization({
      scheduleEnabled: true,
      routed,
      metadataByStop,
      inputState,
      mode: 'driving',
      fetchTable: async () => {
        tableCalls += 1
        return table
      },
      requestOptimization: async (ordered, _blockedEdges, schedule) => {
        if (schedule) schedules.push(schedule)
        return orderResponse(ordered.map(item => item.key), 'schedule-exact')
      },
      route: async (coordinates) => {
        routeCalls += 1
        return routeCalls === 1
          ? routeWithFirstLegUturn(coordinates.length)
          : routeWithoutUturns(coordinates.length)
      },
    })

    expect(result.status).toBe('current')
    if (result.status !== 'current') throw new Error('expected current result')
    expect(result.outcome.attempts).toBe(2)
    expect(tableCalls).toBe(1)
    expect(schedules).toHaveLength(2)
    expect(schedules[0]).toBe(result.scheduleEnvelope)
    expect(schedules[1]).toBe(result.scheduleEnvelope)
    expect(schedules[1]?.duration_matrix_minutes)
      .toBe(schedules[0]?.duration_matrix_minutes)
    expect(schedules[0]?.duration_matrix_minutes).toBe(table.durationMinutes)
    expect(schedules[0]?.stops[1]?.requested_time).toBe('09:00-09:30')
  })

  it('commits a current result through the page mutation callbacks in order', async () => {
    const routed = collectRoutableStops([
      { id: 'start', coords: [11.11, 107.11] as [number, number], time: '' },
      { id: 'middle', coords: [11.12, 107.12] as [number, number], time: '' },
      { id: 'end', coords: [11.13, 107.13] as [number, number], time: '' },
    ])
    const result = await runPlannerOptimization({
      scheduleEnabled: false,
      routed,
      metadataByStop: new WeakMap<object, PlannerScheduleMetadata>(),
      inputState: { version: 0 },
      mode: 'driving',
      fetchTable: async () => cachedTable,
      requestOptimization: async ordered => orderResponse(ordered.map(item => item.key)),
      route: async coordinates => routeWithoutUturns(coordinates.length),
    })
    const mutations: string[] = []

    const committed = await commitPlannerOptimizationResult(result, {
      applyPlacements: () => { mutations.push('placements') },
      reorderStops: () => { mutations.push('reorder') },
      applyRoute: () => { mutations.push('route') },
      updateMap: async () => { mutations.push('map') },
    })

    expect(committed).toBe(result)
    expect(mutations).toEqual(['placements', 'reorder', 'route', 'map'])
  })

  it('keeps every page mutation untouched when an in-flight result becomes stale', async () => {
    const stops = [
      { id: 'start', coords: [12.01, 108.01] as [number, number], time: '' },
      { id: 'middle', coords: [12.02, 108.02] as [number, number], time: '' },
      { id: 'end', coords: [12.03, 108.03] as [number, number], time: '' },
    ]
    const routed = collectRoutableStops(stops)
    const metadataByStop = new WeakMap<object, PlannerScheduleMetadata>()
    const inputState: PlannerInputState = { version: 4 }
    let resolveRequest!: (value: OptimizeOrderResponse) => void
    let markStarted!: () => void
    const started = new Promise<void>((resolve) => { markStarted = resolve })
    const deferredResponse = new Promise<OptimizeOrderResponse>((resolve) => {
      resolveRequest = resolve
    })

    const pending = runPlannerOptimization({
      scheduleEnabled: false,
      routed,
      metadataByStop,
      inputState,
      mode: 'driving',
      fetchTable: async () => cachedTable,
      requestOptimization: async () => {
        markStarted()
        return deferredResponse
      },
      route: async coordinates => routeWithoutUturns(coordinates.length),
    })

    await started
    invalidatePlannerInputs(inputState, stops, metadataByStop)
    resolveRequest(orderResponse(routed.map(item => item.key)))

    const result = await pending
    const mutations: string[] = []
    const committed = await commitPlannerOptimizationResult(result, {
      applyPlacements: () => { mutations.push('placements') },
      reorderStops: () => { mutations.push('reorder') },
      applyRoute: () => { mutations.push('route') },
      updateMap: async () => { mutations.push('map') },
    })

    expect(result).toEqual({ status: 'stale' })
    expect(committed).toBeNull()
    expect(mutations).toEqual([])
    expect(inputState.version).toBe(5)
  })

  it('invalidates before applying changed coordinates and metadata from deferred detail enrichment', async () => {
    const stop = { id: 'favorite', coords: null as [number, number] | null }
    const stops = [stop]
    const metadataByStop = new WeakMap<object, PlannerScheduleMetadata>()
    const inputState: PlannerInputState = { version: 9 }
    const originalMetadata: PlannerScheduleMetadata = {
      visitMinutes: 60,
      openingHours: null,
      warnings: ['opening-hours-unknown'],
      placement: {
        stop_id: 'planner-stop-0',
        arrival_minute: 530,
        start_visit_minute: 540,
        end_visit_minute: 600,
      },
    }
    metadataByStop.set(stop, originalMetadata)
    let resolveDetail!: (value: {
      coordinates: [number, number]
      metadata: PlannerScheduleMetadata
    }) => void
    const detail = new Promise<{
      coordinates: [number, number]
      metadata: PlannerScheduleMetadata
    }>((resolve) => { resolveDetail = resolve })

    const pending = enrichPlannerStopFromDetail({
      stop,
      fetchDetail: () => detail,
      isCurrentStop: candidate => stops.includes(candidate),
      coordinatesFromDetail: value => value.coordinates,
      metadataFromDetail: value => value.metadata,
      metadataByStop,
      invalidate: () => {
        expect(stop.coords).toBeNull()
        expect(metadataByStop.get(stop)).toBe(originalMetadata)
        invalidatePlannerInputs(inputState, stops, metadataByStop)
      },
    })

    resolveDetail({
      coordinates: [10.25, 106.75],
      metadata: {
        visitMinutes: 90,
        openingHours: '08:00-17:00',
        warnings: [],
      },
    })

    await expect(pending).resolves.toBe('updated')

    expect(inputState.version).toBe(10)
    expect(stop.coords).toEqual([10.25, 106.75])
    expect(metadataByStop.get(stop)).toEqual({
      visitMinutes: 90,
      openingHours: '08:00-17:00',
      warnings: [],
    })
    expect(formatScheduledInterval(metadataByStop.get(stop)?.placement)).toBe('')
  })

  it('does not invalidate or enrich a stop removed before its deferred detail resolves', async () => {
    const stop = { id: 'removed-favorite', coords: null as [number, number] | null }
    const stops = [stop]
    const metadataByStop = new WeakMap<object, PlannerScheduleMetadata>()
    const inputState: PlannerInputState = { version: 3 }
    const originalMetadata: PlannerScheduleMetadata = {
      visitMinutes: 60,
      openingHours: null,
      warnings: ['opening-hours-unknown'],
    }
    metadataByStop.set(stop, originalMetadata)
    let resolveDetail!: (value: {
      coordinates: [number, number]
      metadata: PlannerScheduleMetadata
    }) => void
    const detail = new Promise<{
      coordinates: [number, number]
      metadata: PlannerScheduleMetadata
    }>((resolve) => { resolveDetail = resolve })
    const pending = enrichPlannerStopFromDetail({
      stop,
      fetchDetail: () => detail,
      isCurrentStop: candidate => stops.includes(candidate),
      coordinatesFromDetail: value => value.coordinates,
      metadataFromDetail: value => value.metadata,
      metadataByStop,
      invalidate: () => invalidatePlannerInputs(inputState, stops, metadataByStop),
    })

    stops.splice(0, 1)
    resolveDetail({
      coordinates: [10.5, 106.5],
      metadata: {
        visitMinutes: 120,
        openingHours: '09:00-18:00',
        warnings: [],
      },
    })

    await expect(pending).resolves.toBe('removed')
    expect(inputState.version).toBe(3)
    expect(stop.coords).toBeNull()
    expect(metadataByStop.get(stop)).toBe(originalMetadata)
  })

  it('omits an invalid manual time from scheduling without mutating it', () => {
    const stops = [
      { id: 'start', coords: [10, 106] as [number, number], time: '' },
      { id: 'middle', coords: [10.1, 106.1] as [number, number], time: 'khoang chin gio' },
      { id: 'end', coords: [10.2, 106.2] as [number, number], time: '' },
    ]
    const routed = collectRoutableStops(stops)
    const metadataByStop = new WeakMap<object, PlannerScheduleMetadata>()
    routed.forEach(item => metadataByStop.set(item.stop, {
      visitMinutes: 60,
      openingHours: '08:00-17:00',
      warnings: [],
    }))

    const result = buildPlannerScheduleEnvelope(
      routed,
      metadataByStop,
      'driving',
      null,
    )

    expect(stops[1]?.time).toBe('khoang chin gio')
    expect(result.envelope.stops[1]).toEqual({
      id: 'planner-stop-1',
      visit_minutes: 60,
      opening_hours: '08:00-17:00',
      required: true,
    })
    expect(result.warnings).toContain('requested-time-invalid:planner-stop-1')
  })

  it('uses type defaults and an unknown-hours warning for loaded saved stops', () => {
    expect(plannerMetadataForLoadedStop('craft_village')).toEqual({
      visitMinutes: 60,
      openingHours: null,
      warnings: ['opening-hours-unknown'],
    })
    expect(plannerMetadataForEntity('attraction', {
      suggested_duration: '1 gio 30 phut',
      hours: 'mo ca ngay',
    })).toEqual({
      visitMinutes: 90,
      openingHours: 'mo ca ngay',
      warnings: ['opening-hours-invalid'],
    })
  })

  it('keeps placements attached to original stop objects across reorder and save', () => {
    const stops = [
      { id: 'a', name: 'A', type: 'attraction', coords: [10, 106] as [number, number], time: '', notes: '' },
      { id: 'b', name: 'B', type: 'attraction', coords: [10.1, 106.1] as [number, number], time: '09:00', notes: 'B note' },
      { id: 'c', name: 'C', type: 'attraction', coords: [10.2, 106.2] as [number, number], time: '', notes: '' },
    ]
    const routed = collectRoutableStops(stops)
    const metadataByStop = new WeakMap<object, PlannerScheduleMetadata>()
    const inputState: PlannerInputState = { version: 2 }
    routed.forEach(item => metadataByStop.set(item.stop, plannerMetadataForLoadedStop(item.stop.type)))

    applySchedulePlacements(routed, [{
      stop_id: 'planner-stop-1',
      arrival_minute: 530,
      start_visit_minute: 540,
      end_visit_minute: 600,
    }], metadataByStop, inputState)
    const reordered = mergeOptimizedStops(stops, routed, [
      'planner-stop-0',
      'planner-stop-2',
      'planner-stop-1',
    ])

    expect(reordered[2]).toBe(stops[1])
    expect(metadataByStop.get(reordered[2] as object)?.placement?.stop_id)
      .toBe('planner-stop-1')
    expect(inputState.version).toBe(3)
    expect(reordered[2]?.time).toBe('09:00')
    expect(reordered[2]?.notes).toBe('B note')
    expect(serializePlanStops(reordered)[2]).toEqual({
      id: 'b',
      name: 'B',
      type: 'attraction',
      coords: [10.1, 106.1],
      time: '09:00',
      notes: 'B note',
    })
  })
})

function orderResponse(
  orderedIds: string[],
  solver: OptimizeOrderResponse['solver'] = 'exact-dp',
): OptimizeOrderResponse {
  return {
    ordered_ids: orderedIds,
    distance_before_km: 2,
    distance_after_km: 2,
    saved_distance_km: 0,
    backtrack_ratio: 0,
    solver,
    warnings: [],
  }
}

function routeWithoutUturns(stopCount: number) {
  return {
    legs: Array.from({ length: Math.max(0, stopCount - 1) }, () => ({
      distance: 1000,
      duration: 120,
      hasUturn: false,
    })),
    totalDistance: Math.max(0, stopCount - 1) * 1000,
    totalDuration: Math.max(0, stopCount - 1) * 120,
    geometry: [] as [number, number][],
  }
}

function routeWithFirstLegUturn(stopCount: number) {
  const result = routeWithoutUturns(stopCount)
  const firstLeg = result.legs[0]
  if (firstLeg) firstLeg.hasUturn = true
  return result
}
