/**
 * Empirical Adversarial Challenger Test Suite: Milestone M4 (Accessibility & High-Glare)
 * File: web-nuxt/tests/challenger-m4-adversarial.test.ts
 *
 * Authored by: challenger_m4_1_10 (Empirical Challenger)
 * Verification Scope:
 * 1. Elder Mode simultaneous dual attribute sync ('data-elder-mode' & 'data-reading-mode')
 * 2. 125% exact font scaling on Lora / editorial typography and touch targets >= 52px
 * 3. Exact mathematical contrast ratios (WCAG 2.2 AAA >= 14:1) for fg and border
 * 4. Two-way reactive synchrony in ban-do.vue (isHighGlare <-> outdoorContrast <-> map filter & button)
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { computed, ref } from 'vue'
import { useCognitiveTerroir } from '../composables/useCognitiveTerroir'

// ── WCAG 2.2 Mathematical Contrast Functions ──
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

function getContrastRatio(hex1: string, hex2: string): number {
  const l1 = getRelativeLuminance(hex1)
  const l2 = getRelativeLuminance(hex2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

describe('Challenger M4 Adversarial Stress Testing', () => {
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
    vi.restoreAllMocks()
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
  // 1. Elder Mode Simultaneous Attribute Synchronization & Stress
  // ──────────────────────────────────────────────────────────────────────────
  describe('1. Elder Mode: Simultaneous Dual Attribute Invariants', () => {
    it('EMP-1.1: Enabling elder mode simultaneously sets data-elder-mode="true" and data-reading-mode="elder"', () => {
      const t = useCognitiveTerroir()
      t.setElderMode(true)

      const el = document.documentElement
      expect(el.getAttribute('data-elder-mode')).toBe('true')
      expect(el.getAttribute('data-reading-mode')).toBe('elder')
      expect(t.isElderMode.value).toBe(true)
    })

    it('EMP-1.2: Disabling elder mode simultaneously removes both attributes', () => {
      const t = useCognitiveTerroir()
      t.setElderMode(true)
      expect(document.documentElement.hasAttribute('data-elder-mode')).toBe(true)
      expect(document.documentElement.hasAttribute('data-reading-mode')).toBe(true)

      t.setElderMode(false)
      expect(document.documentElement.hasAttribute('data-elder-mode')).toBe(false)
      expect(document.documentElement.hasAttribute('data-reading-mode')).toBe(false)
      expect(t.isElderMode.value).toBe(false)
    })

    it('EMP-1.3: Adversarial multi-toggle stress (100 rapid toggles maintains zero desync)', () => {
      const t1 = useCognitiveTerroir()
      const t2 = useCognitiveTerroir()
      const el = document.documentElement

      for (let i = 0; i < 100; i++) {
        t1.toggleElderMode()
        const expected = i % 2 === 0 // 0th iteration was false -> true
        expect(t1.isElderMode.value).toBe(expected)
        expect(t2.isElderMode.value).toBe(expected) // Singleton check

        if (expected) {
          expect(el.getAttribute('data-elder-mode')).toBe('true')
          expect(el.getAttribute('data-reading-mode')).toBe('elder')
        } else {
          expect(el.hasAttribute('data-elder-mode')).toBe(false)
          expect(el.hasAttribute('data-reading-mode')).toBe(false)
        }
      }
    })

    it('EMP-1.4: Direct override idempotency (calling setElderMode multiple times with same value)', () => {
      const t = useCognitiveTerroir()
      const el = document.documentElement

      t.setElderMode(true)
      t.setElderMode(true)
      t.setElderMode(true)
      expect(el.getAttribute('data-elder-mode')).toBe('true')
      expect(el.getAttribute('data-reading-mode')).toBe('elder')

      t.setElderMode(false)
      t.setElderMode(false)
      expect(el.hasAttribute('data-elder-mode')).toBe(false)
      expect(el.hasAttribute('data-reading-mode')).toBe(false)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Font-size 125% Exact Scaling & Touch Targets >= 52px
  // ──────────────────────────────────────────────────────────────────────────
  describe('2. Ergonomic Geometry: 125% Font Scaling & >= 52px Touch Targets', () => {
    it('EMP-2.1: variables.css declares font scale factor exactly 1.25', () => {
      const match = variablesCss.match(/--font-scale-elder:\s*([0-9.]+);/)
      expect(match).not.toBeNull()
      const factor = parseFloat(match![1]!)
      expect(factor).toBe(1.25)
    })

    it('EMP-2.2: base.css applies exactly 125% scale to html root under elder mode', () => {
      // Must match font-size: calc(100% * var(--font-scale-elder, 1.25));
      expect(baseCss).toMatch(/font-size:\s*calc\(100%\s*\*\s*var\(--font-scale-elder,\s*1\.25\)\);/)
    })

    it('EMP-2.3: Editorial / Lora elements scale by exactly 125% (1.05rem * 1.25 = 1.3125rem)', () => {
      expect(baseCss).toMatch(/font-size:\s*calc\(1\.05rem\s*\*\s*var\(--font-scale-elder,\s*1\.25\)\);/)
      const baseRem = 1.05
      const scaledRem = baseRem * 1.25
      expect(scaledRem).toBeCloseTo(1.3125, 4)
      expect((scaledRem / baseRem) * 100).toBe(125)
    })

    it('EMP-2.4: Paragraphs receive elder line-height token (2.0)', () => {
      const match = variablesCss.match(/--line-height-elder:\s*([0-9.]+);/)
      expect(match).not.toBeNull()
      expect(parseFloat(match![1]!)).toBe(2.0)
      expect(baseCss).toMatch(/line-height:\s*var\(--line-height-elder,\s*2\.0\)\s*!important;/)
    })

    it('EMP-2.5: Interactive touch targets measure >= 52px under elder mode', () => {
      const match = variablesCss.match(/--elder-touch-target:\s*([0-9]+)px;/)
      expect(match).not.toBeNull()
      const touchTargetPx = parseInt(match![1]!, 10)
      expect(touchTargetPx).toBeGreaterThanOrEqual(52)

      // Verify CSS rule enforces min-height and min-width
      expect(baseCss).toMatch(/min-height:\s*var\(--elder-touch-target,\s*52px\);/)
      expect(baseCss).toMatch(/min-width:\s*var\(--elder-touch-target,\s*52px\);/)
      expect(baseCss).toMatch(/border-width:\s*var\(--elder-stroke,\s*3px\);/)
    })

    it('EMP-2.6: Glyphs and icons increase stroke width to 3px', () => {
      const match = variablesCss.match(/--elder-stroke:\s*([0-9]+)px;/)
      expect(match).not.toBeNull()
      expect(parseInt(match![1]!, 10)).toBe(3)
      expect(baseCss).toMatch(/stroke-width:\s*var\(--elder-stroke,\s*3px\)\s*!important;/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 3. High-Glare Mode Mathematical Contrast Ratios (>= 14:1)
  // ──────────────────────────────────────────────────────────────────────────
  describe('3. High-Glare Sunlight Optics: Mathematical Contrast Verification', () => {
    const bg = '#ffffff'
    const fg = '#000000'
    const border = '#12100e'
    const river = '#003652'
    const gold = '#704b06'

    it('EMP-3.1: Token values in variables.css match optical specifications', () => {
      expect(variablesCss).toContain(`--contrast-glare-bg: ${bg};`)
      expect(variablesCss).toContain(`--contrast-glare-fg: ${fg};`)
      expect(variablesCss).toContain(`--contrast-glare-border: ${border};`)
      expect(variablesCss).toContain(`--contrast-glare-river: ${river};`)
      expect(variablesCss).toContain(`--contrast-glare-gold: ${gold};`)
    })

    it('EMP-3.2: Exact mathematical contrast of --contrast-glare-fg (#000000) on white (#ffffff) is 21.00:1 (>= 14:1)', () => {
      const cr = getContrastRatio(bg, fg)
      expect(cr).toBeCloseTo(21.00, 2)
      expect(cr).toBeGreaterThanOrEqual(14.0)
    })

    it('EMP-3.3: Exact mathematical contrast of --contrast-glare-border (#12100e) on white (#ffffff) is >= 14:1', () => {
      const cr = getContrastRatio(bg, border)
      // Calculated mathematically: ~19.33:1
      expect(cr).toBeGreaterThanOrEqual(14.0)
      expect(cr).toBeGreaterThan(18.5)
    })

    it('EMP-3.4: Complementary tokens (river & gold) satisfy WCAG 2.2 AAA contrast (>= 7:1)', () => {
      const crRiver = getContrastRatio(bg, river)
      const crGold = getContrastRatio(bg, gold)
      expect(crRiver).toBeGreaterThanOrEqual(7.0)
      expect(crGold).toBeGreaterThanOrEqual(7.0)
    })

    it('EMP-3.5: Total backdrop-filter elimination and opaque styling enforced under high-glare', () => {
      expect(baseCss).toMatch(/html\[data-outdoor-contrast="high"\]\s+\*[\s\S]*?backdrop-filter:\s*none\s*!important;/)
      expect(baseCss).toMatch(/html\[data-outdoor-contrast="high"\]\s+\.card[\s\S]*?border:\s*2px solid var\(--contrast-glare-border\)\s*!important;/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 4. ban-do.vue Reactive Synchrony & Canvas Filter Verification
  // ──────────────────────────────────────────────────────────────────────────
  describe('4. ban-do.vue: Reactive Synchrony and Cartographic Filter', () => {
    it('EMP-4.1: ban-do.vue imports and binds useCognitiveTerroir isHighGlare with outdoorContrast', () => {
      expect(banDoVue).toContain("import { useCognitiveTerroir } from '~/composables/useCognitiveTerroir'")
      expect(banDoVue).toContain('const terroir = useCognitiveTerroir()')
      expect(banDoVue).toMatch(/const outdoorContrast = computed\(\{[\s\S]*?get:\s*\(\)\s*=>\s*terroir\.isHighGlare\.value[\s\S]*?set:\s*\(val:\s*boolean\)\s*=>\s*terroir\.toggleHighGlare\(val\)[\s\S]*?\}\)/)
    })

    it('EMP-4.2: Two-way reactive synchrony between composable and simulated ban-do state', () => {
      const terroir = useCognitiveTerroir()
      const outdoorContrast = computed({
        get: () => terroir.isHighGlare.value,
        set: (val: boolean) => terroir.toggleHighGlare(val),
      })

      expect(outdoorContrast.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-outdoor-contrast')).toBe(false)

      // External update via composable updates component
      terroir.toggleHighGlare(true)
      expect(outdoorContrast.value).toBe(true)
      expect(document.documentElement.getAttribute('data-outdoor-contrast')).toBe('high')

      // Component toggle updates composable and DOM
      outdoorContrast.value = false
      expect(terroir.isHighGlare.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-outdoor-contrast')).toBe(false)

      outdoorContrast.value = true
      expect(terroir.isHighGlare.value).toBe(true)
      expect(document.documentElement.getAttribute('data-outdoor-contrast')).toBe('high')
    })

    it('EMP-4.3: Toggle button aria-pressed and label react to state change', () => {
      expect(banDoVue).toContain(':class="{ \'is-high\': outdoorContrast }"')
      expect(banDoVue).toContain(':aria-pressed="outdoorContrast"')
      expect(banDoVue).toContain("outdoorContrast ? 'Tương phản ngoài trời: BẬT' : 'Độ tương phản thực địa'")
    })

    it('EMP-4.4: Map canvas filter token is defined and applied under data-outdoor-contrast="high"', () => {
      expect(variablesCss).toMatch(/--contrast-glare-map-filter:\s*contrast\(1\.6\)\s+saturate\(1\.2\)\s+brightness\(0\.95\);/)
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.maplibregl-canvas\s*\{[\s\S]*?filter:\s*var\(--contrast-glare-map-filter/)
    })

    it('EMP-4.5: ban-do.vue root element reflects outdoorContrast in data-outdoor-contrast', () => {
      expect(banDoVue).toContain(":data-outdoor-contrast=\"outdoorContrast ? 'high' : 'normal'\"")
    })
  })
})
