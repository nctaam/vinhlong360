// @vitest-environment node

import { describe, expect, it, vi } from 'vitest'
import {
  buildTableUrl,
  fetchRouteTable,
  parseTableResponse,
  type RouteTableResult,
} from '../composables/useRouting'
import {
  collectRoutableStops,
  getCachedRouteTable,
  requestOptimizedOrder,
  routeTableCacheKey,
  type OptimizeOrderResponse,
  type OptimizeScheduleRequest,
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
