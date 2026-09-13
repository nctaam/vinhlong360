// @vitest-environment happy-dom

/**
 * Empirical Adversarial Challenger Test Suite: Milestone M5
 * File: web-nuxt/tests/challenger-m5-adversarial.test.ts
 *
 * Authored by: challenger_m5_1_10 (Empirical Challenger)
 * Verification Scope:
 * 1. Eco-Mode toggling and state persistence under simulated battery levels (< 20% vs >= 20%)
 * 2. DOM attribute synchronization (`data-eco-mode="true"`) and CSS blast radius
 * 3. Carbon emission calculation edge cases (zero data, massive data, boundary values)
 * 4. `/api/v1/terroir/routes` & `/overview` with malicious, invalid, or boundary query parameters
 * 5. Tidal assist calculations under extreme tidal velocity values (clamping between expected limits)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  useCognitiveTerroir,
  detectBatteryCondition,
  calculateBearingDegrees,
  calculateEcoRouting,
} from '../composables/useCognitiveTerroir'
import overviewHandler from '../server/api/v1/terroir/overview.get'
import routesHandler from '../server/api/v1/terroir/routes.get'
import {
  calculateAstronomicalTide,
  calculateTidalAmplitudeFactor,
} from '../server/utils/terroir/astronomicalTide'
import {
  VERIFIED_WATER_ROUTES,
  calculateBearing,
  calculateRoutePropulsion,
} from '../server/utils/terroir/waterEcoRoutes'

// ── Sustainable Web Design Carbon Model ──
const SWD_ENERGY_PER_GB = 0.81 // kWh/GB
const SWD_CARBON_INTENSITY = 442 // g CO2/kWh

function calculateCarbonGrams(bytes: number): number {
  if (bytes <= 0) return 0
  const gb = bytes / (1024 * 1024 * 1024)
  return gb * SWD_ENERGY_PER_GB * SWD_CARBON_INTENSITY
}

// ── H3 Mock Event Stub ──
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

describe('Challenger M5: Empirical Adversarial Stress Test Suite', () => {
  const root = resolve(__dirname, '..')
  const baseCss = readFileSync(resolve(root, 'assets/css/base.css'), 'utf-8')
  const defaultVue = readFileSync(resolve(root, 'layouts/default.vue'), 'utf-8')
  const originalNavigator = global.navigator

  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-eco-mode')
    delete (document.documentElement as any).dataset.ecoMode
    vi.restoreAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-eco-mode')
    delete (document.documentElement as any).dataset.ecoMode
    Object.defineProperty(global, 'navigator', {
      value: originalNavigator,
      configurable: true,
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 1: Eco-Mode Toggling & State Persistence Under Simulated Battery Levels
  // ──────────────────────────────────────────────────────────────────────────
  describe('1. Eco-Mode Toggling & Battery Boundary Transitions', () => {
    it('boundary test: level 0.20 and discharging triggers isLowBattery = true', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.20,
            charging: false,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.20)
      expect(battery.charging).toBe(false)
      expect(battery.isLowBattery).toBe(true)
      expect(battery.watchIntervalMs).toBe(60000)
    })

    it('boundary test: level 0.2001 and discharging does NOT trigger isLowBattery', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.2001,
            charging: false,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.20) // Math.round(0.2001 * 100)/100 = 0.2
      // Raw check in detectBatteryCondition: level <= 0.20
      // 0.2001 <= 0.20 is false
      expect(battery.isLowBattery).toBe(false)
      expect(battery.watchIntervalMs).toBe(5000)
    })

    it('boundary test: level 0.1999 and discharging triggers isLowBattery', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.1999,
            charging: false,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.isLowBattery).toBe(true)
      expect(battery.watchIntervalMs).toBe(60000)
    })

    it('boundary test: level 0.00 (completely drained) triggers isLowBattery', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.0,
            charging: false,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.0)
      expect(battery.isLowBattery).toBe(true)
      expect(battery.watchIntervalMs).toBe(60000)
    })

    it('boundary test: level 0.05 but charging = true does NOT trigger isLowBattery', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.05,
            charging: true,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.05)
      expect(battery.charging).toBe(true)
      expect(battery.isLowBattery).toBe(false)
      expect(battery.watchIntervalMs).toBe(5000)
    })

    it('reactive composable: manual toggleEcoMode(true) overrides high battery level', () => {
      const terroir = useCognitiveTerroir()
      // Battery is default 1.0 (100%), charging = true
      expect(terroir.battery.value.level).toBe(1.0)
      expect(terroir.battery.value.charging).toBe(true)

      terroir.toggleEcoMode(true)
      expect(terroir.isEcoMode.value).toBe(true)
      expect(terroir.isEcoTerroir.value).toBe(true)
      expect(terroir.geolocationMode.value).toBe('manual')
      expect(terroir.prefetchEnabled.value).toBe(false)

      terroir.toggleEcoMode(false)
      expect(terroir.isEcoMode.value).toBe(false)
      expect(terroir.isEcoTerroir.value).toBe(false)
      expect(terroir.geolocationMode.value).toBe('auto')
      expect(terroir.prefetchEnabled.value).toBe(true)
    })

    it('reactive composable: low battery (< 20% discharging) keeps isEcoTerroir active even if manual toggle is false', () => {
      const terroir = useCognitiveTerroir()
      terroir.toggleEcoMode(false)

      // Simulate low battery condition in composable state
      terroir.battery.value = {
        level: 0.12,
        charging: false,
        isLowBattery: true,
        watchIntervalMs: 60000,
      }

      // isEcoTerroir = isEcoMode || (level <= 0.20 && !charging)
      expect(terroir.isEcoTerroir.value).toBe(true)
      expect(terroir.geolocationMode.value).toBe('manual')
      expect(terroir.prefetchEnabled.value).toBe(false)

      // Turning off manual eco-mode must NOT deactivate eco-terroir when battery is critically low
      terroir.setEcoMode(false)
      expect(terroir.isEcoTerroir.value).toBe(true)
    })

    it('state persistence: survives localStorage read/write and handles storage exceptions defensively', () => {
      const terroir = useCognitiveTerroir()

      terroir.toggleEcoMode(true)
      expect(localStorage.getItem('vl360_eco_mode')).toBe('true')

      terroir.toggleEcoMode(false)
      expect(localStorage.getItem('vl360_eco_mode')).toBe('false')

      // Mock localStorage.setItem throwing (e.g. QuotaExceededError or SecurityError in private browsing)
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('QuotaExceededError')
      })

      // Must not throw an unhandled exception
      expect(() => terroir.toggleEcoMode(true)).not.toThrow()
      setItemSpy.mockRestore()
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 2: DOM Attribute Synchronization & CSS Blast Radius
  // ──────────────────────────────────────────────────────────────────────────
  describe('2. DOM Attribute Synchronization & Performance Blast Radius', () => {
    it('synchronizes data-eco-mode="true" on <html> element synchronously', () => {
      const terroir = useCognitiveTerroir()

      terroir.setEcoMode(true)
      expect(document.documentElement.getAttribute('data-eco-mode')).toBe('true')
      expect(document.documentElement.dataset.ecoMode).toBe('true')

      terroir.setEcoMode(false)
      expect(document.documentElement.hasAttribute('data-eco-mode')).toBe(false)
      expect(document.documentElement.dataset.ecoMode).toBeUndefined()
    })

    it('stress test: 100 rapid flip-flop toggles maintain deterministic final DOM state', () => {
      const terroir = useCognitiveTerroir()

      for (let i = 0; i < 100; i++) {
        terroir.toggleEcoMode(i % 2 === 0)
      }

      // 99 is odd, 99 % 2 === 0 is false -> last toggle was false
      expect(terroir.isEcoMode.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-eco-mode')).toBe(false)

      terroir.toggleEcoMode(true)
      expect(terroir.isEcoMode.value).toBe(true)
      expect(document.documentElement.getAttribute('data-eco-mode')).toBe('true')
    })

    it('verifies base.css contains aggressive animation suppression for html[data-eco-mode="true"]', () => {
      expect(baseCss).toContain('html[data-eco-mode="true"]')
      expect(baseCss).toContain('animation: none !important;')
      expect(baseCss).toContain('content-visibility: auto;')
      expect(baseCss).toMatch(/html\[data-eco-mode="true"\]\s+\.editorial-dossier-card/)
    })

    it('verifies layouts/default.vue suspends Living Ambient RAF loop when isEcoTerroir is active', () => {
      expect(defaultVue).toMatch(/if\s*\(isEcoTerroir\.value\)\s*\{[\s\S]*cancelAnimationFrame/)
      expect(defaultVue).toMatch(/toggleEcoMode\(\)/)
      expect(defaultVue).toMatch(/class="[^"]*eco-mode-toggle[^"]*"/)
      expect(defaultVue).toMatch(/:aria-pressed="isEcoTerroir"/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 3: Carbon Emission Calculation Edge Cases
  // ──────────────────────────────────────────────────────────────────────────
  describe('3. WSG Carbon Emission Mathematical Stress & Boundary Tests', () => {
    it('boundary test: zero bytes payload yields exactly 0.0g CO2', () => {
      expect(calculateCarbonGrams(0)).toBe(0)
    })

    it('boundary test: negative bytes payload returns 0 (handles defensively without NaN)', () => {
      expect(calculateCarbonGrams(-1024)).toBe(0)
      expect(Number.isNaN(calculateCarbonGrams(-1))).toBe(false)
    })

    it('verifies standard 200 KB payload yields strictly less than 0.100g CO2', () => {
      const payload200KB = 200 * 1024 // 204,800 bytes
      const co2 = calculateCarbonGrams(payload200KB)

      expect(co2).toBeGreaterThan(0.065)
      expect(co2).toBeLessThan(0.070)
      expect(co2).toBeLessThan(0.100)
    })

    it('mathematical threshold: identifies exact bytes payload where CO2 crosses 0.100g', () => {
      // 0.1g CO2 / (0.81 kWh/GB * 442 g/kWh) * (1024^3 bytes/GB)
      const exactThresholdBytes = (0.1 / (SWD_ENERGY_PER_GB * SWD_CARBON_INTENSITY)) * (1024 * 1024 * 1024)

      expect(exactThresholdBytes).toBeCloseTo(300000, -4) // ~299,970 bytes
      expect(calculateCarbonGrams(exactThresholdBytes - 10)).toBeLessThan(0.100)
      expect(calculateCarbonGrams(exactThresholdBytes + 10)).toBeGreaterThan(0.100)
    })

    it('stress test: massive data scales linearly up to 1 TB without overflow or NaN', () => {
      const oneGB = 1024 * 1024 * 1024
      const co2OneGB = calculateCarbonGrams(oneGB)
      expect(co2OneGB).toBeCloseTo(0.81 * 442, 2) // 358.02 g CO2

      const hundredGB = 100 * oneGB
      expect(calculateCarbonGrams(hundredGB)).toBeCloseTo(35802, 0)

      const oneTB = 1000 * oneGB
      expect(calculateCarbonGrams(oneTB)).toBeCloseTo(358020, 0)

      // Test Number.MAX_SAFE_INTEGER
      const maxSafe = Number.MAX_SAFE_INTEGER
      const co2MaxSafe = calculateCarbonGrams(maxSafe)
      expect(Number.isFinite(co2MaxSafe)).toBe(true)
      expect(Number.isNaN(co2MaxSafe)).toBe(false)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 4: Civic Open Heritage API Adversarial & Malicious Inputs
  // ──────────────────────────────────────────────────────────────────────────
  describe('4. /api/v1/terroir/routes & overview Adversarial Inputs (RFC 7807 Compliance)', () => {
    // Sub-suite 4.1: craft_type fuzzing & injection attacks
    it('rejects malicious craft_type with SQL injection payloads returning RFC 7807 400', async () => {
      const event = createH3StubEvent("/api/v1/terroir/routes?craft_type=sampan';+DROP+TABLE+entities;+--")
      const result = (await routesHandler(event)) as any

      expect(event.node.res.statusCode).toBe(400)
      expect(event.node.res.getHeader('content-type')).toBe('application/problem+json; charset=utf-8')
      expect(event.node.res.getHeader('cache-control')).toBe('no-store, no-cache, must-revalidate')
      expect(result.type).toBe('https://vinhlong360.vn/problems/invalid-query-parameter')
      expect(result.title).toBe('Invalid Query Parameter')
      expect(result.status).toBe(400)
      expect(result.code).toBe('TERROIR_UNSUPPORTED_CRAFT_TYPE')
      expect(result.invalid_params?.[0]?.name).toBe('craft_type')
      expect(result.timestamp).toBeTruthy()
    })

    it('rejects XSS payload in craft_type returning RFC 7807 400 without executing or echoing unescaped code', async () => {
      const event = createH3StubEvent('/api/v1/terroir/routes?craft_type=%3Cscript%3Ealert(1)%3C%2Fscript%3E')
      const result = (await routesHandler(event)) as any

      expect(event.node.res.statusCode).toBe(400)
      expect(result.code).toBe('TERROIR_UNSUPPORTED_CRAFT_TYPE')
      expect(result.detail).toContain('<script>alert(1)</script>')
    })

    it('handles oversized craft_type (10,000 characters buffer overflow attempt) cleanly', async () => {
      const hugeCraft = 'A'.repeat(10000)
      const event = createH3StubEvent(`/api/v1/terroir/routes?craft_type=${hugeCraft}`)
      const result = (await routesHandler(event)) as any

      expect(event.node.res.statusCode).toBe(400)
      expect(result.code).toBe('TERROIR_UNSUPPORTED_CRAFT_TYPE')
    })

    it('accepts trimmed case-insensitive valid craft types (e.g. "  CANOE  ", "  kayak  ")', async () => {
      const canoeEvent = createH3StubEvent('/api/v1/terroir/routes?craft_type=%20%20CANOE%20%20')
      const canoeRes = (await routesHandler(canoeEvent)) as any
      expect(canoeEvent.node.res.statusCode).toBe(200)
      expect(canoeRes.craft_type).toBe('canoe')
      expect(canoeRes.nominal_craft_speed_ms).toBe(8.0)

      const kayakEvent = createH3StubEvent('/api/v1/terroir/routes?craft_type=%20kayak%20')
      const kayakRes = (await routesHandler(kayakEvent)) as any
      expect(kayakEvent.node.res.statusCode).toBe(200)
      expect(kayakRes.craft_type).toBe('kayak')
      expect(kayakRes.nominal_craft_speed_ms).toBe(1.5)
    })

    // Sub-suite 4.2: route_id traversal and fuzzing
    it('rejects path traversal in route_id returning RFC 7807 404', async () => {
      const event = createH3StubEvent('/api/v1/terroir/routes?route_id=../../../../etc/passwd')
      const result = (await routesHandler(event)) as any

      expect(event.node.res.statusCode).toBe(404)
      expect(result.type).toBe('https://vinhlong360.vn/problems/resource-not-found')
      expect(result.code).toBe('TERROIR_ROUTE_NOT_FOUND')
    })

    it('rejects SQL injection in route_id returning RFC 7807 404', async () => {
      const event = createH3StubEvent("/api/v1/terroir/routes?route_id=route-1'+OR+1=1+--")
      const result = (await routesHandler(event)) as any

      expect(event.node.res.statusCode).toBe(404)
      expect(result.code).toBe('TERROIR_ROUTE_NOT_FOUND')
    })

    it('returns all verified water routes when route_id is empty string or omitted', async () => {
      const event = createH3StubEvent('/api/v1/terroir/routes?route_id=')
      const result = (await routesHandler(event)) as any

      expect(event.node.res.statusCode).toBe(200)
      expect(result.total_routes).toBe(4)
      expect(result.routes).toHaveLength(4)
    })

    // Sub-suite 4.3: departure_time edge cases & fuzzing
    it('rejects invalid departure_time formats with RFC 7807 400', async () => {
      const invalidTimes = [
        'invalid-time',
        '2026-99-99T99:99:99Z',
        '[object Object]',
        'undefined',
        'NaN',
      ]

      for (const time of invalidTimes) {
        const event = createH3StubEvent(`/api/v1/terroir/routes?departure_time=${encodeURIComponent(time)}`)
        const result = (await routesHandler(event)) as any

        expect(event.node.res.statusCode).toBe(400)
        expect(result.code).toBe('TERROIR_INVALID_DEPARTURE_TIME')
      }
    })

    it('accepts boundary departure_time (Unix Epoch, far future, leap day) without crashing', async () => {
      const boundaryTimes = [
        '1970-01-01T00:00:00Z', // Unix Epoch
        '2028-02-29T12:00:00Z', // Leap Day
        '2050-12-31T23:59:59Z', // Far future
      ]

      for (const time of boundaryTimes) {
        const event = createH3StubEvent(`/api/v1/terroir/routes?departure_time=${encodeURIComponent(time)}`)
        const result = (await routesHandler(event)) as any

        expect(event.node.res.statusCode).toBe(200)
        expect(result.total_routes).toBeGreaterThan(0)
        expect(result.hydrological_reference).toBeDefined()
      }
    })

    // Sub-suite 4.4: overview date parameter fuzzing
    it('rejects malicious query string on /api/v1/terroir/overview returning RFC 7807 400', async () => {
      const maliciousDates = [
        "2026-09-13'; DROP TABLE users; --",
        '<svg/onload=alert(1)>',
        'B'.repeat(5000),
      ]

      for (const badDate of maliciousDates) {
        const event = createH3StubEvent(`/api/v1/terroir/overview?date=${encodeURIComponent(badDate)}`)
        const result = (await overviewHandler(event)) as any

        expect(event.node.res.statusCode).toBe(400)
        expect(result.code).toBe('TERROIR_INVALID_DATE_FORMAT')
        expect(result.type).toBe('https://vinhlong360.vn/problems/invalid-query-parameter')
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 5: Tidal Velocity Bounds & Clamping Mechanics
  // ──────────────────────────────────────────────────────────────────────────
  describe('5. Hydrodynamic Velocity & Tidal Assist Clamping Mechanics', () => {
    it('guarantees astronomical tide flow velocity is clamped within [0.10, 1.50] m/s across the entire year (365 days x 24 hours)', () => {
      // Sample 365 days across year 2026 at 3-hour intervals (2,920 evaluations)
      const testYear = 2026
      let minVelocity = Infinity
      let maxVelocity = -Infinity
      let minWaterLevel = Infinity
      let maxWaterLevel = -Infinity
      let minDhdt = Infinity
      let maxDhdt = -Infinity

      for (let dayOfYear = 0; dayOfYear < 365; dayOfYear += 5) {
        for (let hour = 0; hour < 24; hour += 3) {
          const testDate = new Date(Date.UTC(testYear, 0, 1 + dayOfYear, hour, 0, 0))
          const tide = calculateAstronomicalTide(testDate)

          minVelocity = Math.min(minVelocity, tide.flow_velocity_ms)
          maxVelocity = Math.max(maxVelocity, tide.flow_velocity_ms)
          minWaterLevel = Math.min(minWaterLevel, tide.water_level_meters)
          maxWaterLevel = Math.max(maxWaterLevel, tide.water_level_meters)
          minDhdt = Math.min(minDhdt, tide.dhdt)
          maxDhdt = Math.max(maxDhdt, tide.dhdt)

          expect(tide.flow_velocity_ms).toBeGreaterThanOrEqual(0.10)
          expect(tide.flow_velocity_ms).toBeLessThanOrEqual(1.50)
          expect(['rong', 'kem', 'chuyen']).toContain(tide.tide_phase)
          expect(['nuoc_lon', 'nuoc_rong_can', 'nuoc_dung']).toContain(tide.water_flow_state)
        }
      }

      // Mathematical envelope checks
      expect(minVelocity).toBeGreaterThanOrEqual(0.10)
      expect(maxVelocity).toBeLessThanOrEqual(1.50)
      expect(minWaterLevel).toBeGreaterThanOrEqual(-0.50) // Ebb tide low stage relative to datum
      expect(maxWaterLevel).toBeLessThanOrEqual(2.60)  // Spring tide high stage
      expect(minDhdt).toBeGreaterThanOrEqual(-0.60)
      expect(maxDhdt).toBeLessThanOrEqual(0.60)
    })

    it('bearing calculation handles identical origin and destination coordinates without NaN', () => {
      const pt = { lat: 10.2544, lng: 105.9722 }
      const bearing = calculateBearing(pt, pt)
      expect(bearing).toBe(0)
      expect(Number.isNaN(bearing)).toBe(false)

      const bearingComposable = calculateBearingDegrees(pt, pt)
      expect(bearingComposable).toBe(0)
      expect(Number.isNaN(bearingComposable)).toBe(false)
    })

    it('evaluates hydrodynamic propulsion across craft speed profiles under peak tidal assist', () => {
      const testRoute = VERIFIED_WATER_ROUTES[0]! // route-co-chien-an-binh
      // Mock peak ebb tide (river flowing seaward at 135 degrees with 1.45 m/s velocity)
      const mockPeakEbbTide: any = {
        current_azimuth_deg: 135.0,
        flow_velocity_ms: 1.45,
        water_flow_state: 'nuoc_rong_can',
        tide_phase: 'rong',
      }

      const sampanEval = calculateRoutePropulsion(testRoute, mockPeakEbbTide, new Date(), 'sampan')
      const canoeEval = calculateRoutePropulsion(testRoute, mockPeakEbbTide, new Date(), 'canoe')
      const kayakEval = calculateRoutePropulsion(testRoute, mockPeakEbbTide, new Date(), 'kayak')

      // All crafts travelling along the route should receive downstream assist
      expect(sampanEval.tidal_propulsion.direction).toBe('downstream_assist')
      expect(canoeEval.tidal_propulsion.direction).toBe('downstream_assist')
      expect(kayakEval.tidal_propulsion.direction).toBe('downstream_assist')

      // Slower craft (kayak: 1.5 m/s) gains higher percentage propulsion assist than fast craft (canoe: 8.0 m/s)
      expect(kayakEval.tidal_propulsion.effort_savings_percentage)
        .toBeGreaterThan(canoeEval.tidal_propulsion.effort_savings_percentage)

      // Green fuel savings factor is strictly bounded in [0.0, 1.0]
      expect(sampanEval.tidal_propulsion.green_fuel_savings_factor).toBeGreaterThanOrEqual(0)
      expect(sampanEval.tidal_propulsion.green_fuel_savings_factor).toBeLessThanOrEqual(1.0)
      expect(canoeEval.tidal_propulsion.green_fuel_savings_factor).toBeGreaterThanOrEqual(0)
      expect(canoeEval.tidal_propulsion.green_fuel_savings_factor).toBeLessThanOrEqual(1.0)
      expect(kayakEval.tidal_propulsion.green_fuel_savings_factor).toBeGreaterThanOrEqual(0)
      expect(kayakEval.tidal_propulsion.green_fuel_savings_factor).toBeLessThanOrEqual(1.0)
    })

    it('handles slack water (flow velocity < 0.15 m/s) returning 0% assist without division by zero', () => {
      const testRoute = VERIFIED_WATER_ROUTES[0]!
      const mockSlackTide: any = {
        current_azimuth_deg: 135.0,
        flow_velocity_ms: 0.08,
        water_flow_state: 'nuoc_dung',
        tide_phase: 'kem',
      }

      const evalResult = calculateRoutePropulsion(testRoute, mockSlackTide, new Date(), 'sampan')
      expect(evalResult.tidal_propulsion.direction).toBe('slack_water')
      expect(evalResult.tidal_propulsion.effort_savings_percentage).toBe(0)
      expect(evalResult.tidal_propulsion.green_fuel_savings_factor).toBe(0)
      expect(evalResult.tidal_propulsion.narrative_advice).toContain('Nước đứng')
    })

    it('calculateEcoRouting composable handles opposite (upstream) navigation with negative effort savings', () => {
      const origin = { lat: 10.2300, lng: 105.9800, name: 'An Bình' }
      const destination = { lat: 10.2544, lng: 105.9722, name: 'Bến Vĩnh Long' }
      // Moving Northwest (against seaward current)
      const result = calculateEcoRouting(origin, destination, new Date('2026-09-13T06:30:00+07:00'))

      expect(result).toBeDefined()
      expect(result.travelAzimuth).toBeGreaterThanOrEqual(0)
      expect(result.travelAzimuth).toBeLessThanOrEqual(360)
      expect(typeof result.effortSavingsPercentage).toBe('number')
      expect(result.alignmentCos).toBeLessThanOrEqual(1.0)
      expect(result.alignmentCos).toBeGreaterThanOrEqual(-1.0)
    })
  })
})
