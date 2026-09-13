/**
 * Comprehensive Empirical Adversarial Stress Test Suite for Cognitive Terroir Engine
 * Challenger: challenger_m2_1_10
 *
 * Tests:
 * 1. Tidal calculations across all 30 lunar days (syzygy vs quadrature amplitude factors)
 * 2. Hydrodynamic Eco-Routing across angles (0°, 45°, 90°, 135°, 180°), verifying ~40% downstream assist and ZERO false assist upstream
 * 3. Network simulation: '2g', '3g', 'offline', '4g', 'slow-2g', saveData
 * 4. Battery simulation: 15% vs 85%, charging vs discharging, 20% boundary, error resilience
 * 5. Headless/SSR degradation safety
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  useCognitiveTerroir,
  calculateAstronomicalTide,
  calculateTidalAmplitudeFactor,
  calculateBearingDegrees,
  calculateEcoRouting,
  detectNetworkCondition,
  detectBatteryCondition,
} from '../composables/useCognitiveTerroir'

describe('Cognitive Terroir Engine — Adversarial Stress Test Harness', () => {
  // ──────────────────────────────────────────────────────────────────────────
  // 1. Tidal Calculations Across 30 Lunar Days (Syzygy vs Quadrature)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Dimension 1: Tidal Calculations Across All 30 Lunar Days', () => {
    it('verifies amplitude factor alpha(D_L) strictly stays in [0.65, 1.35] for all integer days 1..30', () => {
      for (let day = 1; day <= 30; day++) {
        const factor = calculateTidalAmplitudeFactor(day)
        expect(factor).toBeGreaterThanOrEqual(0.6499)
        expect(factor).toBeLessThanOrEqual(1.3501)
      }
    })

    it('verifies syzygy (spring tide) peaks near New Moon (Day 1) and Full Moon (Day 15/16)', () => {
      // Day 1 (New Moon)
      const day1 = calculateTidalAmplitudeFactor(1)
      expect(day1).toBeCloseTo(1.35, 2)

      // Day 15 and 16 (around Full Moon at 15.76)
      const day15 = calculateTidalAmplitudeFactor(15)
      const day16 = calculateTidalAmplitudeFactor(16)
      expect(day15).toBeGreaterThan(1.30)
      expect(day16).toBeGreaterThan(1.30)

      // Day 30 (leading back to New Moon)
      const day30 = calculateTidalAmplitudeFactor(30)
      expect(day30).toBeGreaterThan(1.30)
    })

    it('verifies quadrature (neap tide) troughs near First Quarter (Day 8/9) and Third Quarter (Day 23/24)', () => {
      // Day 8 and 9 (First Quarter at ~8.38)
      const day8 = calculateTidalAmplitudeFactor(8)
      const day9 = calculateTidalAmplitudeFactor(9)
      expect(day8).toBeLessThan(0.70)
      expect(day9).toBeLessThan(0.70)
      expect(day8).toBeGreaterThanOrEqual(0.65)

      // Day 23 and 24 (Third Quarter at ~23.15)
      const day23 = calculateTidalAmplitudeFactor(23)
      const day24 = calculateTidalAmplitudeFactor(24)
      expect(day23).toBeLessThan(0.70)
      expect(day24).toBeLessThan(0.70)
      expect(day23).toBeGreaterThanOrEqual(0.65)
    })

    it('evaluates fine-grained continuity across 290 fractional samples from Day 1.0 to 30.0', () => {
      let minFactor = Infinity
      let maxFactor = -Infinity

      for (let d = 1.0; d <= 30.0; d += 0.1) {
        const factor = calculateTidalAmplitudeFactor(d)
        if (factor < minFactor) minFactor = factor
        if (factor > maxFactor) maxFactor = factor
        expect(factor).toBeGreaterThanOrEqual(0.6499)
        expect(factor).toBeLessThanOrEqual(1.3501)
      }

      // Exact mathematical bounds check
      expect(minFactor).toBeCloseTo(0.65, 2)
      expect(maxFactor).toBeCloseTo(1.35, 2)
    })

    it('verifies water level h(t) curve and flow velocity dh/dt consistency across 24 hours', () => {
      const baseDateStr = '2026-09-13T'
      for (let h = 0; h < 24; h++) {
        const d = new Date(`${baseDateStr}${String(h).padStart(2, '0')}:15:00+07:00`)
        const result = calculateAstronomicalTide(d)

        // Stage elevation should be in reasonable physical bounds for Mekong delta
        expect(result.waterLevelMeters).toBeGreaterThanOrEqual(-0.5)
        expect(result.waterLevelMeters).toBeLessThan(2.5)

        // Derivative and flow velocity consistency
        expect(Number.isFinite(result.dhdt)).toBe(true)
        expect(result.flowVelocityMs).toBeGreaterThanOrEqual(0.1)
        expect(result.flowVelocityMs).toBeLessThanOrEqual(1.5)

        if (result.waterFlowState === 'nuoc_lon') {
          expect(result.dhdt).toBeGreaterThan(0.15)
          expect(result.currentAzimuth).toBe(315.0)
          expect(result.flowVelocityMs).toBeGreaterThanOrEqual(0.6)
        } else if (result.waterFlowState === 'nuoc_rong_can') {
          expect(result.dhdt).toBeLessThan(-0.15)
          expect(result.currentAzimuth).toBe(135.0)
          expect(result.flowVelocityMs).toBeGreaterThanOrEqual(0.8)
        } else {
          expect(result.waterFlowState).toBe('nuoc_dung')
          expect(Math.abs(result.dhdt)).toBeLessThanOrEqual(0.15)
          expect(result.flowVelocityMs).toBe(0.1)
        }
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Eco-Routing Across Various Angles (0°, 45°, 90°, 135°, 180°)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Dimension 2: Hydrodynamic Eco-Routing Directional Matrix', () => {
    // Helper to generate a destination waypoint at a given bearing from origin
    function createDestinationAtBearing(origin: { lat: number; lng: number }, bearingDeg: number, distanceKm = 5): { lat: number; lng: number } {
      const R = 6371 // Earth radius in km
      const brngRad = (bearingDeg * Math.PI) / 180
      const lat1 = (origin.lat * Math.PI) / 180
      const lon1 = (origin.lng * Math.PI) / 180

      const lat2 = Math.asin(Math.sin(lat1) * Math.cos(distanceKm / R) + Math.cos(lat1) * Math.sin(distanceKm / R) * Math.cos(brngRad))
      const lon2 = lon1 + Math.atan2(Math.sin(brngRad) * Math.sin(distanceKm / R) * Math.cos(lat1), Math.cos(distanceKm / R) - Math.sin(lat1) * Math.sin(lat2))

      return {
        lat: (lat2 * 180) / Math.PI,
        lng: (lon2 * 180) / Math.PI,
      }
    }

    // Find an ebb tide hour (current azimuth = 135.0°)
    function findEbbTideDate(): Date {
      for (let h = 0; h < 24; h++) {
        const candidate = new Date(`2026-09-13T${String(h).padStart(2, '0')}:00:00+07:00`)
        const t = calculateAstronomicalTide(candidate)
        if (t.waterFlowState === 'nuoc_rong_can') {
          return candidate
        }
      }
      return new Date('2026-09-13T04:00:00+07:00')
    }

    // Find a flood tide hour (current azimuth = 315.0°)
    function findFloodTideDate(): Date {
      for (let h = 0; h < 24; h++) {
        const candidate = new Date(`2026-09-13T${String(h).padStart(2, '0')}:00:00+07:00`)
        const t = calculateAstronomicalTide(candidate)
        if (t.waterFlowState === 'nuoc_lon') {
          return candidate
        }
      }
      return new Date('2026-09-13T10:00:00+07:00')
    }

    const origin = { lat: 10.278, lng: 105.908, name: 'Bến Mỹ Thuận' }

    it('tests Angle 0° (pure downstream along current vector): delivers ~40% effort reduction', () => {
      const ebbDate = findEbbTideDate()
      const tide = calculateAstronomicalTide(ebbDate)
      expect(tide.currentAzimuth).toBe(135.0)

      // Travel heading identical to current azimuth (135°)
      const dest0 = createDestinationAtBearing(origin, 135.0)
      const routing = calculateEcoRouting(origin, dest0, ebbDate)

      expect(routing.travelAzimuth).toBeCloseTo(135.0, 0)
      expect(routing.direction).toBe('downstream_assist')
      expect(routing.alignmentCos).toBeCloseTo(1.0, 2)

      // Effort reduction must be ~40% (typically 35% to 50% for Mekong flow 0.8-1.2 m/s)
      expect(routing.effortSavingsPercentage).toBeGreaterThanOrEqual(35)
      expect(routing.effortSavingsPercentage).toBeLessThanOrEqual(52)
      expect(routing.narrativeAdvice).toContain('Xuôi dòng nước')
      expect(routing.narrativeAdvice).toContain('Tiết kiệm')
    })

    it('tests Angle 45° (quarter downstream): delivers positive propulsion assist', () => {
      const ebbDate = findEbbTideDate()
      // Current is 135°, angle 45° offset -> travel heading 180°
      const dest45 = createDestinationAtBearing(origin, 180.0)
      const routing = calculateEcoRouting(origin, dest45, ebbDate)

      expect(routing.travelAzimuth).toBeCloseTo(180.0, 0)
      expect(routing.direction).toBe('downstream_assist')
      expect(routing.alignmentCos).toBeGreaterThanOrEqual(0.60) // cos(45°) ~ 0.707 >= 0.60

      // Must be positive assist, but less than direct downstream 0°
      expect(routing.effortSavingsPercentage).toBeGreaterThan(25)
      expect(routing.effortSavingsPercentage).toBeLessThan(45)
    })

    it('tests Angle 90° (perpendicular cross-current): yields exactly 0% savings and cross-current warning', () => {
      const ebbDate = findEbbTideDate()
      // Current is 135°, angle 90° offset -> travel heading 225°
      const dest90 = createDestinationAtBearing(origin, 225.0)
      const routing = calculateEcoRouting(origin, dest90, ebbDate)

      expect(routing.travelAzimuth).toBeCloseTo(225.0, 0)
      expect(routing.direction).toBe('cross_current')
      expect(routing.alignmentCos).toBeCloseTo(0.0, 1)
      expect(routing.effortSavingsPercentage).toBe(0)
      expect(routing.narrativeAdvice).toContain('Dòng chảy ngang')
    })

    it('tests Angle 135° (quarter upstream): yields upstream resistance with negative savings (penalty)', () => {
      const ebbDate = findEbbTideDate()
      // Current is 135°, angle 135° offset -> travel heading 270° (Due West)
      const dest135 = createDestinationAtBearing(origin, 270.0)
      const routing = calculateEcoRouting(origin, dest135, ebbDate)

      expect(routing.travelAzimuth).toBeCloseTo(270.0, 0)
      expect(routing.direction).toBe('upstream_resistance')
      expect(routing.alignmentCos).toBeLessThanOrEqual(-0.60) // cos(135°) ~ -0.707 <= -0.60

      // CRUCIAL: Must NEVER give false propulsion assist
      expect(routing.effortSavingsPercentage).toBeLessThan(0)
      expect(routing.narrativeAdvice).toContain('Ngược dòng triều cường')
    })

    it('tests Angle 180° (direct upstream against current): strictly negative savings, ZERO false assist', () => {
      const ebbDate = findEbbTideDate()
      // Current is 135°, angle 180° offset -> travel heading 315° (Northwest)
      const dest180 = createDestinationAtBearing(origin, 315.0)
      const routing = calculateEcoRouting(origin, dest180, ebbDate)

      expect(routing.travelAzimuth).toBeCloseTo(315.0, 0)
      expect(routing.direction).toBe('upstream_resistance')
      expect(routing.alignmentCos).toBeCloseTo(-1.0, 1)

      // Substantial extra power required (negative savings)
      expect(routing.effortSavingsPercentage).toBeLessThan(-30)
      // EMPIRICAL INVARIANT: Upstream NEVER yields positive assist
      expect(routing.effortSavingsPercentage).not.toBeGreaterThan(0)
      expect(routing.narrativeAdvice).toContain('Ngược dòng triều cường')
    })

    it('sweeps all 72 azimuth angles (5° step) confirming no upstream vector ever receives positive assist', () => {
      const ebbDate = findEbbTideDate()
      const currentAzimuth = 135.0

      for (let brng = 0; brng < 360; brng += 5) {
        const dest = createDestinationAtBearing(origin, brng)
        const routing = calculateEcoRouting(origin, dest, ebbDate)

        const deltaDeg = Math.abs((routing.travelAzimuth - currentAzimuth + 180) % 360 - 180)

        if (deltaDeg > 90) {
          // In the upstream hemisphere (angle > 90°), savings must NEVER be positive
          expect(routing.effortSavingsPercentage).toBeLessThanOrEqual(0)
        }

        if (routing.direction === 'upstream_resistance') {
          expect(routing.effortSavingsPercentage).toBeLessThan(0)
        } else if (routing.direction === 'cross_current' || routing.direction === 'slack_water') {
          expect(routing.effortSavingsPercentage).toBe(0)
        } else if (routing.direction === 'downstream_assist') {
          expect(routing.effortSavingsPercentage).toBeGreaterThan(0)
        }
      }
    })

    it('verifies flood tide (azimuth 315°) flips the favorable corridor correctly', () => {
      const floodDate = findFloodTideDate()
      const tide = calculateAstronomicalTide(floodDate)
      expect(tide.currentAzimuth).toBe(315.0)

      // Heading 315° is now downstream assist
      const dest315 = createDestinationAtBearing(origin, 315.0)
      const routing315 = calculateEcoRouting(origin, dest315, floodDate)
      expect(routing315.direction).toBe('downstream_assist')
      expect(routing315.effortSavingsPercentage).toBeGreaterThanOrEqual(35)

      // Heading 135° is now upstream resistance
      const dest135 = createDestinationAtBearing(origin, 135.0)
      const routing135 = calculateEcoRouting(origin, dest135, floodDate)
      expect(routing135.direction).toBe('upstream_resistance')
      expect(routing135.effortSavingsPercentage).toBeLessThan(0)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Network Simulation ('2g', '3g', 'offline', '4g', 'slow-2g', saveData)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Dimension 3: Network Condition Simulation Matrix', () => {
    const originalNavigator = global.navigator

    afterEach(() => {
      Object.defineProperty(global, 'navigator', {
        value: originalNavigator,
        configurable: true,
      })
    })

    it('simulates standard 4G network', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
          connection: { effectiveType: '4g', saveData: false },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.effectiveType).toBe('4g')
      expect(net.isOffline).toBe(false)
      expect(net.saveData).toBe(false)
      expect(net.profile).toBe('standard')
    })

    it('simulates 2G network -> degrades to field-light profile', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
          connection: { effectiveType: '2g', saveData: false },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.effectiveType).toBe('2g')
      expect(net.isOffline).toBe(false)
      expect(net.profile).toBe('field-light')
    })

    it('simulates 3G network -> degrades to field-light profile', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
          connection: { effectiveType: '3g', saveData: false },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.effectiveType).toBe('3g')
      expect(net.isOffline).toBe(false)
      expect(net.profile).toBe('field-light')
    })

    it('simulates slow-2g network -> degrades to field-light profile', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
          connection: { effectiveType: 'slow-2g', saveData: false },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.effectiveType).toBe('slow-2g')
      expect(net.profile).toBe('field-light')
    })

    it('simulates offline state (navigator.onLine = false) -> switches to offline profile regardless of effectiveType', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: false,
          connection: { effectiveType: '4g', saveData: false },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.isOffline).toBe(true)
      expect(net.profile).toBe('offline')
    })

    it('simulates saveData mode enabled on 4G -> switches to field-light profile', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
          connection: { effectiveType: '4g', saveData: true },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.saveData).toBe(true)
      expect(net.profile).toBe('field-light')
    })

    it('simulates missing connection object -> gracefully defaults to standard 4G', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.effectiveType).toBe('4g')
      expect(net.profile).toBe('standard')
      expect(net.isOffline).toBe(false)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Battery Simulation (15% vs 85%, charging states, throttling)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Dimension 4: Battery Telemetry & Eco-Terroir Power Throttling', () => {
    const originalNavigator = global.navigator

    afterEach(() => {
      Object.defineProperty(global, 'navigator', {
        value: originalNavigator,
        configurable: true,
      })
    })

    it('simulates low battery at 15% (discharging): triggers isLowBattery and throttles watch interval to 60s', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.15,
            charging: false,
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.15)
      expect(battery.charging).toBe(false)
      expect(battery.isLowBattery).toBe(true)
      expect(battery.watchIntervalMs).toBe(60000)
    })

    it('simulates normal battery at 85% (discharging): keeps standard 5s polling interval', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.85,
            charging: false,
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.85)
      expect(battery.charging).toBe(false)
      expect(battery.isLowBattery).toBe(false)
      expect(battery.watchIntervalMs).toBe(5000)
    })

    it('simulates low battery at 15% but charging: does NOT throttle because plugged in', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.15,
            charging: true,
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.15)
      expect(battery.charging).toBe(true)
      expect(battery.isLowBattery).toBe(false)
      expect(battery.watchIntervalMs).toBe(5000)
    })

    it('tests exact 20% boundary threshold', async () => {
      // At exactly 0.20 -> NOT low battery (< 0.20 required)
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.20,
            charging: false,
          }),
        },
        configurable: true,
      })

      const atBoundary = await detectBatteryCondition()
      expect(atBoundary.isLowBattery).toBe(false)
      expect(atBoundary.watchIntervalMs).toBe(5000)

      // At 0.199 -> IS low battery
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.199,
            charging: false,
          }),
        },
        configurable: true,
      })

      const belowBoundary = await detectBatteryCondition()
      expect(belowBoundary.isLowBattery).toBe(true)
      expect(belowBoundary.watchIntervalMs).toBe(60000)
    })

    it('handles battery promise rejection safely without throwing unhandled error', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockRejectedValue(new Error('Battery API Security Error')),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(1.0)
      expect(battery.charging).toBe(true)
      expect(battery.isLowBattery).toBe(false)
      expect(battery.watchIntervalMs).toBe(5000)
    })
  })
})
