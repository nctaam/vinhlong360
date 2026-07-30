// @vitest-environment node

import { describe, expect, it } from 'vitest'
import {
  blockedEdgesForUturns,
  collectRoutableStops,
  mergeOptimizedStops,
  requestOptimizedOrder,
  routeLegForStopIndex,
  runBoundedOptimization,
} from '../composables/useItineraryOptimization'

const stops = [
  { id: 'same', coords: [10, 106] as [number, number], notes: 'start' },
  { id: 'missing', coords: null, notes: 'keep slot' },
  { id: 'same', coords: [10, 106.7] as [number, number], notes: 'late' },
  { id: 'early', coords: [10, 106.3] as [number, number], notes: 'early' },
  { id: 'end', coords: [10, 107] as [number, number], notes: 'end' },
]

describe('planner itinerary optimization helpers', () => {
  it('assigns unique keys when entity IDs repeat', () => {
    expect(collectRoutableStops(stops).map(item => item.key)).toEqual([
      'planner-stop-0',
      'planner-stop-2',
      'planner-stop-3',
      'planner-stop-4',
    ])
  })

  it('reorders coordinate slots without moving missing-coordinate slots', () => {
    const routed = collectRoutableStops(stops)
    const merged = mergeOptimizedStops(stops, routed, [
      'planner-stop-0',
      'planner-stop-3',
      'planner-stop-2',
      'planner-stop-4',
    ])

    expect(merged.map(stop => stop.notes)).toEqual([
      'start',
      'keep slot',
      'early',
      'late',
      'end',
    ])
  })

  it('rejects an optimizer response that is not a permutation', () => {
    const routed = collectRoutableStops(stops)

    expect(() => mergeOptimizedStops(stops, routed, [
      'planner-stop-0',
      'planner-stop-3',
      'planner-stop-3',
      'planner-stop-4',
    ])).toThrow('không khớp')
  })

  it('aligns route legs to coordinate-bearing origin indexes', () => {
    const routed = collectRoutableStops(stops)
    const legs = [
      { distance: 1, duration: 1, hasUturn: false },
      { distance: 2, duration: 2, hasUturn: false },
      { distance: 3, duration: 3, hasUturn: false },
    ]

    expect(routeLegForStopIndex(0, routed, legs)?.distance).toBe(1)
    expect(routeLegForStopIndex(1, routed, legs)).toBeNull()
    expect(routeLegForStopIndex(2, routed, legs)?.distance).toBe(2)
  })

  it('maps uturn legs to exact directed route keys', () => {
    const routed = collectRoutableStops(stops)
    const route = {
      legs: [
        { distance: 1, duration: 1, hasUturn: false },
        { distance: 2, duration: 2, hasUturn: true },
        { distance: 3, duration: 3, hasUturn: false },
      ],
      totalDistance: 6,
      totalDuration: 6,
      geometry: [],
    }

    expect(blockedEdgesForUturns(routed, route)).toEqual([
      ['planner-stop-2', 'planner-stop-3'],
    ])
  })

  it('posts stable route keys and coordinates to the public API', async () => {
    const routed = collectRoutableStops(stops)
    let request: { url: string; options: Record<string, unknown> } | null = null
    const fetcher = async (url: string, options: unknown) => {
      request = { url, options: options as Record<string, unknown> }
      return {
        ordered_ids: routed.map(item => item.key),
        distance_before_km: 10,
        distance_after_km: 8,
        saved_distance_km: 2,
        backtrack_ratio: 0,
        solver: 'exact-dp' as const,
        warnings: [],
      }
    }

    await requestOptimizedOrder(
      routed,
      [['planner-stop-0', 'planner-stop-2']],
      fetcher,
    )

    expect(request).toEqual({
      url: '/api/itineraries/optimize-order',
      options: {
        method: 'POST',
        body: {
          stops: [
            { id: 'planner-stop-0', coordinates: [10, 106] },
            { id: 'planner-stop-2', coordinates: [10, 106.7] },
            { id: 'planner-stop-3', coordinates: [10, 106.3] },
            { id: 'planner-stop-4', coordinates: [10, 107] },
          ],
          strict_direction: true,
          blocked_edges: [['planner-stop-0', 'planner-stop-2']],
        },
      },
    })
  })

  it('retries exactly once with the uturn edge', async () => {
    const blockedCalls: string[][][] = []
    const optimize = async (_routed: unknown, blocked: string[][]) => {
      blockedCalls.push(blocked)
      return {
        ordered_ids: blocked.length
          ? ['planner-stop-0', 'planner-stop-2', 'planner-stop-1', 'planner-stop-3']
          : ['planner-stop-0', 'planner-stop-1', 'planner-stop-2', 'planner-stop-3'],
        distance_before_km: blocked.length ? 8 : 10,
        distance_after_km: blocked.length ? 7 : 8,
        saved_distance_km: blocked.length ? 1 : 2,
        backtrack_ratio: 0,
        solver: 'exact-dp' as const,
        warnings: [],
      }
    }
    let routeCall = 0
    const route = async () => ({
      legs: [
        { distance: 1, duration: 1, hasUturn: routeCall++ === 0 },
        { distance: 1, duration: 1, hasUturn: false },
        { distance: 1, duration: 1, hasUturn: false },
      ],
      totalDistance: 3,
      totalDuration: 3,
      geometry: [],
    })
    const routed = collectRoutableStops([
      { id: 'a', coords: [10, 106] as [number, number] },
      { id: 'b', coords: [10.02, 106.5] as [number, number] },
      { id: 'c', coords: [9.98, 106.5] as [number, number] },
      { id: 'd', coords: [10, 107] as [number, number] },
    ])

    const result = await runBoundedOptimization(routed, optimize, route)

    expect(blockedCalls).toEqual([
      [],
      [['planner-stop-0', 'planner-stop-1']],
    ])
    expect(result.attempts).toBe(2)
    expect(result.ordered.map(item => item.key)).toEqual([
      'planner-stop-0',
      'planner-stop-2',
      'planner-stop-1',
      'planner-stop-3',
    ])
    expect(result.optimization.distance_before_km).toBe(10)
    expect(result.optimization.distance_after_km).toBe(7)
    expect(result.optimization.saved_distance_km).toBe(3)
    expect(result.unresolvedUturn).toBe(false)
  })

  it('never performs a third attempt when the retry still has a uturn', async () => {
    let optimizerCalls = 0
    const optimize = async (routed: Array<{ key: string }>) => {
      optimizerCalls += 1
      return {
        ordered_ids: routed.map(item => item.key),
        distance_before_km: 10,
        distance_after_km: 9,
        saved_distance_km: 1,
        backtrack_ratio: 0,
        solver: 'exact-dp' as const,
        warnings: [],
      }
    }
    const route = async () => ({
      legs: [
        { distance: 1, duration: 1, hasUturn: true },
        { distance: 1, duration: 1, hasUturn: false },
      ],
      totalDistance: 2,
      totalDuration: 2,
      geometry: [],
    })
    const routed = collectRoutableStops([
      { id: 'a', coords: [10, 106] as [number, number] },
      { id: 'b', coords: [10, 106.5] as [number, number] },
      { id: 'c', coords: [10, 107] as [number, number] },
    ])

    const result = await runBoundedOptimization(routed, optimize, route)

    expect(optimizerCalls).toBe(2)
    expect(result.attempts).toBe(2)
    expect(result.unresolvedUturn).toBe(true)
  })
})
