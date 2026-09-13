/**
 * Empirical Adversarial Challenger Test Suite for Milestone M4 (Extreme Accessibility)
 * File: web-nuxt/tests/challenger-m4-empirical-stress.test.ts
 *
 * Scope:
 * 1. Elder mode attribute sync (data-elder-mode and data-reading-mode)
 * 2. Font-size 125% and touch targets >= 52px
 * 3. Mathematical contrast ratio >= 14:1 calculation for --contrast-glare-fg and --contrast-glare-border against white
 * 4. Reactive sync in ban-do.vue
 * 5. Stress edge-cases, state thrashing, SSR boundary conditions, and token integrity
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { computed, ref } from 'vue'
import { useCognitiveTerroir } from '../composables/useCognitiveTerroir'

// ── Color & Luminance Math ──
function srgbToLinear(c: number): number {
  const norm = c / 255
  return norm <= 0.04045 ? norm / 12.92 : Math.pow((norm + 0.055) / 1.055, 2.4)
}

function getRelativeLuminance(hex: string): number {
  const clean = hex.replace('#', '')
  const r = srgbToLinear(parseInt(clean.substring(0, 2), 16))
  const g = srgbToLinear(parseInt(clean.substring(2, 4), 16))
  const b = srgbToLinear(parseInt(clean.substring(4, 6), 16))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function calculateContrastRatio(hex1: string, hex2: string): number {
  const l1 = getRelativeLuminance(hex1)
  const l2 = getRelativeLuminance(hex2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

describe('Challenger M4 Empirical Stress Test', () => {
  const root = resolve(__dirname, '..')
  const variablesCss = readFileSync(resolve(root, 'assets/css/variables.css'), 'utf-8')
  const baseCss = readFileSync(resolve(root, 'assets/css/base.css'), 'utf-8')
  const banDoVue = readFileSync(resolve(root, 'pages/ban-do.vue'), 'utf-8')

  beforeEach(() => {
    localStorage.clear()
    const terroir = useCognitiveTerroir()
    terroir.toggleElderMode(false)
    terroir.toggleHighGlare(false)
    document.documentElement.removeAttribute('data-reading-mode')
    document.documentElement.removeAttribute('data-elder-mode')
    document.documentElement.removeAttribute('data-outdoor-contrast')
  })

  afterEach(() => {
    localStorage.clear()
    const terroir = useCognitiveTerroir()
    terroir.toggleElderMode(false)
    terroir.toggleHighGlare(false)
    document.documentElement.removeAttribute('data-reading-mode')
    document.documentElement.removeAttribute('data-elder-mode')
    document.documentElement.removeAttribute('data-outdoor-contrast')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 1: Elder Mode Dual Attribute Sync & State Thrashing
  // ──────────────────────────────────────────────────────────────────────────
  describe('Challenge 1: Elder Mode Attribute Sync & State Thrashing', () => {
    it('synchronizes data-elder-mode and data-reading-mode simultaneously on documentElement', () => {
      const terroir = useCognitiveTerroir()
      expect(document.documentElement.hasAttribute('data-reading-mode')).toBe(false)
      expect(document.documentElement.hasAttribute('data-elder-mode')).toBe(false)

      terroir.setElderMode(true)
      expect(document.documentElement.getAttribute('data-reading-mode')).toBe('elder')
      expect(document.documentElement.getAttribute('data-elder-mode')).toBe('true')

      terroir.setElderMode(false)
      expect(document.documentElement.hasAttribute('data-reading-mode')).toBe(false)
      expect(document.documentElement.hasAttribute('data-elder-mode')).toBe(false)
    })

    it('survives rapid state thrashing (100 rapid toggles) without desynchronization', () => {
      const terroir = useCognitiveTerroir()
      for (let i = 0; i < 100; i++) {
        terroir.toggleElderMode()
      }
      // After 100 toggles starting from false, it should be false
      expect(terroir.isElderMode.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-reading-mode')).toBe(false)
      expect(document.documentElement.hasAttribute('data-elder-mode')).toBe(false)

      // 101st toggle
      terroir.toggleElderMode()
      expect(terroir.isElderMode.value).toBe(true)
      expect(document.documentElement.getAttribute('data-reading-mode')).toBe('elder')
      expect(document.documentElement.getAttribute('data-elder-mode')).toBe('true')
    })

    it('shares singleton state across independent calls to useCognitiveTerroir()', () => {
      const instanceA = useCognitiveTerroir()
      const instanceB = useCognitiveTerroir()

      expect(instanceA.isElderMode.value).toBe(false)
      expect(instanceB.isElderMode.value).toBe(false)

      instanceA.toggleElderMode(true)
      expect(instanceB.isElderMode.value).toBe(true)

      instanceB.toggleElderMode(false)
      expect(instanceA.isElderMode.value).toBe(false)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 2: Font-size 125% and Touch Target >= 52px Enforcements
  // ──────────────────────────────────────────────────────────────────────────
  describe('Challenge 2: Font-Size 125% and Touch Target >= 52px', () => {
    it('variables.css specifies exact --font-scale-elder and --elder-touch-target values', () => {
      expect(variablesCss).toMatch(/--font-scale-elder:\s*1\.25;/)
      expect(variablesCss).toMatch(/--line-height-elder:\s*2\.0;/)
      expect(variablesCss).toMatch(/--elder-stroke:\s*3px;/)
      expect(variablesCss).toMatch(/--elder-touch-target:\s*52px;/)
    })

    it('base.css sets font-size to 125% on html under elder mode attributes', () => {
      // Must match either data-reading-mode="elder" or data-elder-mode="true"
      expect(baseCss).toMatch(/:where\(html\[data-reading-mode="elder"\],\s*html\[data-elder-mode="true"\]\)/)
      expect(baseCss).toMatch(/font-size:\s*calc\(100%\s*\*\s*var\(--font-scale-elder,\s*1\.25\)\);/)
    })

    it('base.css enforces min-height >= 52px and min-width >= 52px on interactive elements', () => {
      expect(baseCss).toMatch(/min-height:\s*var\(--elder-touch-target,\s*52px\);/)
      expect(baseCss).toMatch(/min-width:\s*var\(--elder-touch-target,\s*52px\);/)
      expect(baseCss).toMatch(/border-width:\s*var\(--elder-stroke,\s*3px\);/)
    })

    it('base.css enforces line-height 2.0 on body/prose/reading paragraphs', () => {
      expect(baseCss).toMatch(/line-height:\s*var\(--line-height-elder,\s*2\.0\)\s*!important;/)
    })

    it('base.css suppresses animations and transitions under elder mode', () => {
      expect(baseCss).toMatch(/animation-duration:\s*0\.01ms\s*!important;/)
      expect(baseCss).toMatch(/transform:\s*none\s*!important;/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 3: Mathematical Contrast Ratio Calculation (>= 14:1)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Challenge 3: Mathematical Contrast Ratio >= 14:1 Against White', () => {
    const white = '#ffffff'
    const fg = '#000000'
    const border = '#12100e'
    const accentText = '#4a1b0a'

    it('--contrast-glare-fg (#000000) achieves 21.00:1 contrast against #ffffff', () => {
      const cr = calculateContrastRatio(white, fg)
      expect(cr).toBeCloseTo(21.0, 1)
      expect(cr).toBeGreaterThanOrEqual(14.0)
    })

    it('--contrast-glare-border (#12100e) achieves >= 14:1 contrast against #ffffff', () => {
      const cr = calculateContrastRatio(white, border)
      // Exact calculation yields ~18.98:1
      expect(cr).toBeGreaterThanOrEqual(14.0)
      expect(cr).toBeGreaterThan(18.5)
    })

    it('--contrast-glare-accent-text (#4a1b0a) achieves high contrast against #ffffff', () => {
      const cr = calculateContrastRatio(white, accentText)
      // #4a1b0a on white yields ~12.3:1 (exceeds WCAG AAA 7:1)
      expect(cr).toBeGreaterThanOrEqual(7.0)
    })

    it('verifies high-glare background is pure white #ffffff in variables.css', () => {
      expect(variablesCss).toContain('--contrast-glare-bg: #ffffff;')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 4: Reactive Sync in ban-do.vue
  // ──────────────────────────────────────────────────────────────────────────
  describe('Challenge 4: Reactive Sync in ban-do.vue', () => {
    it('binds outdoorContrast to useCognitiveTerroir().isHighGlare with getter and setter', () => {
      expect(banDoVue).toMatch(/const\s+terroir\s*=\s*useCognitiveTerroir\(\)/)
      expect(banDoVue).toMatch(/const\s+outdoorContrast\s*=\s*computed\(\{\s*get:\s*\(\)\s*=>\s*terroir\.isHighGlare\.value,\s*set:\s*\(val:\s*boolean\)\s*=>\s*terroir\.toggleHighGlare\(val\),?\s*\}\)/)
    })

    it('propagates outdoorContrast changes bidirectionally between ban-do and composable', () => {
      const terroir = useCognitiveTerroir()
      // Simulate ban-do.vue computed behavior
      const banDoOutdoorContrast = computed({
        get: () => terroir.isHighGlare.value,
        set: (val: boolean) => terroir.toggleHighGlare(val),
      })

      expect(banDoOutdoorContrast.value).toBe(false)
      expect(terroir.isHighGlare.value).toBe(false)

      // 1. ban-do changes outdoorContrast
      banDoOutdoorContrast.value = true
      expect(terroir.isHighGlare.value).toBe(true)
      expect(document.documentElement.getAttribute('data-outdoor-contrast')).toBe('high')

      // 2. Global composable changes isHighGlare
      terroir.toggleHighGlare(false)
      expect(banDoOutdoorContrast.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-outdoor-contrast')).toBe(false)
    })

    it('ban-do.vue template sets :data-outdoor-contrast="outdoorContrast ? \'high\' : \'normal\'"', () => {
      expect(banDoVue).toMatch(/:data-outdoor-contrast="outdoorContrast\s*\?\s*'high'\s*:\s*'normal'"/)
    })

    it('ban-do.vue applies map canvas filter var(--contrast-glare-map-filter)', () => {
      expect(banDoVue).toMatch(/\[data-outdoor-contrast="high"\][\s\S]*?filter:\s*var\(--contrast-glare-map-filter/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 5: Edge Cases & Graceful Degradation
  // ──────────────────────────────────────────────────────────────────────────
  describe('Challenge 5: Robustness, Error Handling & SSR Safety', () => {
    it('handles localStorage unavailability gracefully without crashing', () => {
      const terroir = useCognitiveTerroir()
      const originalSetItem = localStorage.setItem
      localStorage.setItem = () => {
        throw new DOMException('Quota exceeded or storage disabled', 'QuotaExceededError')
      }

      expect(() => terroir.toggleElderMode(true)).not.toThrow()
      expect(terroir.isElderMode.value).toBe(true)

      expect(() => terroir.toggleHighGlare(true)).not.toThrow()
      expect(terroir.isHighGlare.value).toBe(true)

      localStorage.setItem = originalSetItem
    })

    it('preserves clean DOM state when toggling repeatedly with identical values', () => {
      const terroir = useCognitiveTerroir()
      terroir.setElderMode(true)
      terroir.setElderMode(true)
      expect(document.documentElement.getAttribute('data-reading-mode')).toBe('elder')
      expect(document.documentElement.getAttribute('data-elder-mode')).toBe('true')

      terroir.setElderMode(false)
      terroir.setElderMode(false)
      expect(document.documentElement.hasAttribute('data-reading-mode')).toBe(false)
      expect(document.documentElement.hasAttribute('data-elder-mode')).toBe(false)
    })
  })
})
