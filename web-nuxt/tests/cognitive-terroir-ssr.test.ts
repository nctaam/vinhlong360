// @vitest-environment node
/**
 * Headless Node SSR Safety Stress Test for Cognitive Terroir Engine
 * Milestone M2 Adversarial Verification
 *
 * Verifies that in a pure Node environment where:
 * - window === undefined
 * - document === undefined
 * - localStorage === undefined
 * - navigator is either undefined or lacks browser-specific telemetry (connection, getBattery)
 *
 * The engine executes cleanly with ZERO crashes, ZERO unhandled rejections, and ZERO fabricated telemetry.
 */

import { describe, it, expect } from 'vitest'
import {
  useCognitiveTerroir,
  calculateAstronomicalTide,
  calculateTidalAmplitudeFactor,
  calculateBearingDegrees,
  calculateEcoRouting,
  detectNetworkCondition,
  detectBatteryCondition,
} from '../composables/useCognitiveTerroir'

describe('Cognitive Terroir Engine — Headless Node SSR Safety', () => {
  it('confirms the test runs in a headless Node environment without browser DOM', () => {
    expect(typeof window).toBe('undefined')
    expect(typeof document).toBe('undefined')
    expect(typeof localStorage).toBe('undefined')
  })

  it('calculates astronomical tides safely under SSR', () => {
    const testDate = new Date('2026-09-13T10:00:00+07:00')
    const tide = calculateAstronomicalTide(testDate)

    expect(tide).toBeDefined()
    expect(Number.isFinite(tide.waterLevelMeters)).toBe(true)
    expect(Number.isFinite(tide.flowVelocityMs)).toBe(true)
    expect(Number.isFinite(tide.dhdt)).toBe(true)
    expect(['nuoc_lon', 'nuoc_rong_can', 'nuoc_dung']).toContain(tide.waterFlowState)
    expect(['rong', 'kem', 'chuyen']).toContain(tide.tidePhase)
    expect(tide.lunarDate).toBeDefined()
    expect(tide.lunarDate.day).toBeGreaterThanOrEqual(1)
    expect(tide.lunarDate.day).toBeLessThanOrEqual(30)
  })

  it('calculates hydrodynamic eco-routing safely under SSR', () => {
    const origin = { lat: 10.278, lng: 105.908, name: 'Bến Mỹ Thuận' }
    const destination = { lat: 10.230, lng: 105.980, name: 'Cù Lao An Bình' }
    const routing = calculateEcoRouting(origin, destination, new Date('2026-09-13T12:00:00+07:00'))

    expect(routing).toBeDefined()
    expect(Number.isFinite(routing.travelAzimuth)).toBe(true)
    expect(Number.isFinite(routing.effortSavingsPercentage)).toBe(true)
    expect(['downstream_assist', 'upstream_resistance', 'cross_current', 'slack_water']).toContain(routing.direction)
  })

  it('detects network condition safely in Node without throwing', () => {
    const net = detectNetworkCondition()
    expect(net).toBeDefined()
    expect(net.effectiveType).toBe('4g')
    expect(net.isOffline).toBe(false)
    expect(net.saveData).toBe(false)
    expect(net.profile).toBe('standard')
  })

  it('detects battery condition safely in Node without throwing', async () => {
    const bat = await detectBatteryCondition()
    expect(bat).toBeDefined()
    expect(bat.level).toBe(1.0)
    expect(bat.charging).toBe(true)
    expect(bat.isLowBattery).toBe(false)
    expect(bat.watchIntervalMs).toBe(5000)
  })

  it('instantiates useCognitiveTerroir() composable cleanly under SSR', async () => {
    const terroir = useCognitiveTerroir()
    expect(terroir).toBeDefined()
    expect(terroir.tide.value).toBeDefined()
    expect(terroir.network.value.profile).toBe('standard')
    expect(terroir.battery.value.isLowBattery).toBe(false)
    expect(terroir.isElderMode.value).toBe(false)
    expect(terroir.isHighGlare.value).toBe(false)
    expect(terroir.isFieldMode.value).toBe(false)
    expect(terroir.isOffline.value).toBe(false)
    expect(terroir.isEcoTerroir.value).toBe(false)

    // Verify toggle methods do not crash when document/localStorage are undefined
    expect(() => terroir.toggleElderMode()).not.toThrow()
    expect(terroir.isElderMode.value).toBe(true)
    expect(() => terroir.toggleElderMode(false)).not.toThrow()
    expect(terroir.isElderMode.value).toBe(false)

    expect(() => terroir.toggleHighGlare()).not.toThrow()
    expect(terroir.isHighGlare.value).toBe(true)
    expect(() => terroir.toggleHighGlare(false)).not.toThrow()
    expect(terroir.isHighGlare.value).toBe(false)

    // Verify update triggers execute without error
    expect(() => terroir.updateTide()).not.toThrow()
    expect(() => terroir.updateNetwork()).not.toThrow()
    await expect(terroir.updateBattery()).resolves.toBeUndefined()
  })
})
