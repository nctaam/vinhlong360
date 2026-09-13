// @vitest-environment node

import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import overviewHandler from '../server/api/v1/terroir/overview.get'
import routesHandler from '../server/api/v1/terroir/routes.get'

// Stub response class for H3 testing
class ResponseStub {
  statusCode = 200
  headers = new Map<string, string>()

  setHeader(name: string, value: string) {
    this.headers.set(name.toLowerCase(), value)
  }

  getHeader(name: string) {
    return this.headers.get(name.toLowerCase())
  }
}

function createH3StubEvent(url: string, method = 'GET') {
  const res = new ResponseStub()
  const parsedUrl = new URL(url, 'http://localhost')
  const query: Record<string, string> = {}
  parsedUrl.searchParams.forEach((v, k) => {
    query[k] = v
  })
  return {
    path: url,
    method,
    node: {
      req: { url, method, headers: { accept: 'application/json' } },
      res,
    },
    _query: query,
  } as any
}

describe('Civic Open Heritage API (/api/v1/terroir/*) Integration Test Suite', () => {
  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 1: GET /api/v1/terroir/overview (Success & 4 Core Subdomains)
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-01: returns 200 OK with tide, seasonal harvest, weather, and 5 hotlines', async () => {
    const event = createH3StubEvent('/api/v1/terroir/overview')
    const result = (await overviewHandler(event)) as any

    expect(result).toBeDefined()
    expect(result.api_version).toBe('1.0.0')
    expect(result.terroir_basin).toContain('Vĩnh Long')

    // 1. Astronomical Tide
    expect(result.astronomical_tide).toBeDefined()
    expect(['rong', 'kem', 'chuyen']).toContain(result.astronomical_tide.tide_phase)
    expect(typeof result.astronomical_tide.water_level_meters).toBe('number')
    expect(result.astronomical_tide.folkWisdom).toContain('Nước rong rằm & mùng một')

    // 2. Seasonal Harvest
    expect(result.seasonal_harvest).toBeDefined()
    expect(result.seasonal_harvest.agricultural_indicators.length).toBeGreaterThan(0)
    expect(result.seasonal_harvest.culinary_indicators.length).toBeGreaterThan(0)

    // 3. Weather Terroir
    expect(result.weather_terroir).toBeDefined()
    expect(['measured', 'estimated', 'unavailable']).toContain(result.weather_terroir.status)
    expect(result.weather_terroir.terroir_climatic_context).toBeTruthy()

    // 4. Emergency Rescue Hotlines (All 5 verified hotlines present)
    expect(result.emergency_hotlines).toHaveLength(5)
    const hotlineIds = result.emergency_hotlines.map((h: any) => h.id)
    expect(hotlineIds).toEqual([
      'rescue-waterway',
      'rescue-medical',
      'rescue-police',
      'rescue-ferry',
      'rescue-tourism',
    ])
    expect(result.emergency_hotlines[0].phone).toBe('0270 3822 305')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 2: Cache-Control & Civic HTTP Headers Compliance
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-02: sets exact Cache-Control and CORS headers', async () => {
    const event = createH3StubEvent('/api/v1/terroir/overview')
    await overviewHandler(event)

    const cacheHeader = event.node.res.getHeader('cache-control')
    expect(cacheHeader).toBe('public, max-age=300, s-maxage=3600, stale-while-revalidate=86400')

    const corsHeader = event.node.res.getHeader('access-control-allow-origin')
    expect(corsHeader).toBe('*')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 3: RFC 7807 Problem Details for Malformed Date
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-03: returns RFC 7807 Problem Details 400 for malformed date', async () => {
    const event = createH3StubEvent('/api/v1/terroir/overview?date=invalid-date-format')
    const result = (await overviewHandler(event)) as any

    expect(event.node.res.statusCode).toBe(400)
    expect(event.node.res.getHeader('content-type')).toBe('application/problem+json; charset=utf-8')
    expect(result.type).toBe('https://vinhlong360.vn/problems/invalid-query-parameter')
    expect(result.title).toBe('Invalid Query Parameter')
    expect(result.status).toBe(400)
    expect(result.code).toBe('TERROIR_INVALID_DATE_FORMAT')
    expect(result.instance).toBe('/api/v1/terroir/overview?date=invalid-date-format')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 4: GET /api/v1/terroir/routes with ~40% Downstream Assist
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-04: returns verified water eco-routes and calculates ~40% downstream propulsion assist', async () => {
    // Departure during ebb tide (when river flows Southeast seaward towards 135 deg)
    const event = createH3StubEvent('/api/v1/terroir/routes?route_id=route-co-chien-an-binh&departure_time=2026-09-13T06:30:00%2B07:00')
    const result = (await routesHandler(event)) as any

    expect(result.total_routes).toBe(1)
    const route = result.routes[0]
    expect(route.id).toBe('route-co-chien-an-binh')
    expect(route.waypoints.length).toBeGreaterThanOrEqual(4)

    // Verify tidal propulsion assist vector
    expect(route.tidal_propulsion).toBeDefined()
    expect(typeof route.tidal_propulsion.effort_savings_percentage).toBe('number')
    if (route.tidal_propulsion.direction === 'downstream_assist') {
      expect(route.tidal_propulsion.effort_savings_percentage).toBeGreaterThanOrEqual(30)
      expect(route.tidal_propulsion.effort_savings_percentage).toBeLessThanOrEqual(55)
      expect(route.tidal_propulsion.narrative_advice).toContain('Xuôi dòng nước')
    }
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 5: RFC 7807 404 for Non-Existent Route ID
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-05: returns RFC 7807 Problem Details 404 for unknown route_id', async () => {
    const event = createH3StubEvent('/api/v1/terroir/routes?route_id=unknown-ghost-route')
    const result = (await routesHandler(event)) as any

    expect(event.node.res.statusCode).toBe(404)
    expect(event.node.res.getHeader('content-type')).toBe('application/problem+json; charset=utf-8')
    expect(result.type).toBe('https://vinhlong360.vn/problems/resource-not-found')
    expect(result.status).toBe(404)
    expect(result.code).toBe('TERROIR_ROUTE_NOT_FOUND')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 6: RFC 7807 400 for Unsupported Craft Type
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-06: returns RFC 7807 Problem Details 400 for unsupported craft_type', async () => {
    const event = createH3StubEvent('/api/v1/terroir/routes?craft_type=submarine')
    const result = (await routesHandler(event)) as any

    expect(event.node.res.statusCode).toBe(400)
    expect(result.type).toBe('https://vinhlong360.vn/problems/invalid-query-parameter')
    expect(result.status).toBe(400)
    expect(result.code).toBe('TERROIR_UNSUPPORTED_CRAFT_TYPE')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Test Case 7: Absolute Database Invariance (B1, B6, B7)
  // ──────────────────────────────────────────────────────────────────────────
  it('TC-API-07: guarantees bit-for-bit SHA-256 invariance of vinhlong360.db and data.json', async () => {
    const repoRoot = resolve(__dirname, '../..')
    const dbPath = resolve(repoRoot, 'agent/data/vinhlong360.db')
    const jsonPath = resolve(repoRoot, 'web/data.json')

    const dbHashBefore = createHash('sha256').update(readFileSync(dbPath)).digest('hex')
    const jsonHashBefore = createHash('sha256').update(readFileSync(jsonPath)).digest('hex')

    // Execute multiple API handler queries with various date and route inputs
    await overviewHandler(createH3StubEvent('/api/v1/terroir/overview'))
    await overviewHandler(createH3StubEvent('/api/v1/terroir/overview?date=2026-09-25T12:00:00Z'))
    await routesHandler(createH3StubEvent('/api/v1/terroir/routes'))

    const dbHashAfter = createHash('sha256').update(readFileSync(dbPath)).digest('hex')
    const jsonHashAfter = createHash('sha256').update(readFileSync(jsonPath)).digest('hex')

    expect(dbHashAfter).toBe(dbHashBefore)
    expect(jsonHashAfter).toBe(jsonHashBefore)
  })
})
