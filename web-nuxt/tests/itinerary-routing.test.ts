// @vitest-environment node

import { describe, expect, it } from 'vitest'
import {
  buildRouteUrl,
  parseRouteResponse,
} from '../composables/useRouting'

describe('itinerary OSRM routing', () => {
  it('requests route steps and continue-straight', () => {
    expect(buildRouteUrl([[10, 106], [10.5, 106.5]])).toBe(
      'https://router.project-osrm.org/route/v1/car/'
      + '106,10;106.5,10.5?overview=full&geometries=geojson&'
      + 'steps=true&continue_straight=true',
    )
  })

  it('marks only the leg containing a uturn maneuver', () => {
    const result = parseRouteResponse({
      code: 'Ok',
      routes: [{
        distance: 3000,
        legs: [
          { distance: 1000, steps: [{ maneuver: { type: 'turn' } }] },
          { distance: 2000, steps: [{ maneuver: { type: 'uturn' } }] },
        ],
        geometry: { coordinates: [[106, 10], [106.5, 10.5]] },
      }],
    }, 'driving')

    expect(result?.legs.map(leg => leg.hasUturn)).toEqual([false, true])
    expect(result?.geometry).toEqual([[10, 106], [10.5, 106.5]])
  })

  it('treats missing steps as a leg without a detected uturn', () => {
    const result = parseRouteResponse({
      code: 'Ok',
      routes: [{
        distance: 1000,
        legs: [{ distance: 1000 }],
        geometry: { coordinates: [[106, 10], [106.1, 10.1]] },
      }],
    }, 'driving')

    expect(result?.legs[0]?.hasUturn).toBe(false)
  })

  it('rejects empty route responses', () => {
    expect(parseRouteResponse(
      { code: 'NoRoute', routes: [] },
      'driving',
    )).toBeNull()
    expect(parseRouteResponse(
      { code: 'Ok', routes: [] },
      'driving',
    )).toBeNull()
  })
})
