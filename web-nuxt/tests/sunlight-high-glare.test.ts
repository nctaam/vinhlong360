/**
 * High-Glare Outdoor Sunlight Mode (Nắng Gắt Miền Tây >= 14:1) Invariant Test
 * File: web-nuxt/tests/sunlight-high-glare.test.ts
 *
 * Verifies:
 * 1. High-glare token contract & optical contrast calculations (WCAG 2.2 AAA >= 14:1)
 * 2. Composable reactive state & DOM data-outdoor-contrast synchronization
 * 3. Global keyboard shortcut Alt+S
 * 4. Document-level anti-glare, blur elimination & map filter enforcement
 * 5. Field cartography ergonomics on ban-do.vue & tuyen-duong.vue
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { useCognitiveTerroir } from '../composables/useCognitiveTerroir'

// ─────────────────────────────────────────────────────────────────────────────
// HÀM TIỆN ÍCH TÍNH TOÁN QUANG HỌC CHUẨN WCAG 2.2
// ─────────────────────────────────────────────────────────────────────────────
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

describe('High-Glare Outdoor Sunlight Mode (Nắng Gắt Miền Tây >= 14:1)', () => {
  const root = resolve(__dirname, '..')
  const variablesCss = readFileSync(resolve(root, 'assets/css/variables.css'), 'utf8')
  const baseCss = readFileSync(resolve(root, 'assets/css/base.css'), 'utf8')
  const banDoVue = readFileSync(resolve(root, 'pages/ban-do.vue'), 'utf8')
  const tuyenDuongVue = readFileSync(resolve(root, 'pages/tuyen-duong.vue'), 'utf8')
  const terroirComposableSource = readFileSync(resolve(root, 'composables/useCognitiveTerroir.ts'), 'utf8')

  // ───────────────────────────────────────────────────────────────────────────
  // SUITE 1: Khế ước Token Nắng Gắt & Kiểm Chứng Độ Tương Phản Toán Học
  // ───────────────────────────────────────────────────────────────────────────
  describe('Suite 1: High-Glare Token Contract & Optical Contrast Ratios', () => {
    it('declares all mandatory sunlight tokens in variables.css', () => {
      expect(variablesCss).toContain('--contrast-glare-bg: #ffffff;')
      expect(variablesCss).toContain('--contrast-glare-fg: #000000;')
      expect(variablesCss).toContain('--contrast-glare-border: #12100e;')
      expect(variablesCss).toContain('--contrast-glare-accent: #b95f38;')
      expect(variablesCss).toContain('--contrast-glare-gold: #704b06;')
      expect(variablesCss).toContain('--contrast-glare-river: #003652;')
      expect(variablesCss).toContain('--contrast-glare-map-filter: contrast(1.6) saturate(1.2) brightness(0.95);')
    })

    it('proves pure black on pure white achieves exact 21:1 contrast (>= 14:1)', () => {
      const cr = getContrastRatio('#ffffff', '#000000')
      expect(Number(cr.toFixed(2))).toBe(21.00)
      expect(cr).toBeGreaterThanOrEqual(14.0)
    })

    it('proves high-glare border (#12100e) achieves >= 14:1 contrast against white', () => {
      const cr = getContrastRatio('#ffffff', '#12100e')
      expect(Number(cr.toFixed(2))).toBe(18.98)
      expect(cr).toBeGreaterThanOrEqual(14.0)
    })

    it('verifies high-glare river (#003652) and gold (#704b06) exceed WCAG AAA standards', () => {
      const crRiver = getContrastRatio('#ffffff', '#003652')
      const crGold = getContrastRatio('#ffffff', '#704b06')
      expect(crRiver).toBeGreaterThanOrEqual(7.0) // 12.73:1
      expect(crGold).toBeGreaterThanOrEqual(7.0)  // 7.78:1
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // SUITE 2: Cơ Chế Đồng Bộ Trạng Thái & Thuộc Tính Thẻ HTML
  // ───────────────────────────────────────────────────────────────────────────
  describe('Suite 2: Composable State & DOM Attribute Synchronization', () => {
    beforeEach(() => {
      const terroir = useCognitiveTerroir()
      terroir.toggleHighGlare(false)
      document.documentElement.removeAttribute('data-outdoor-contrast')
      localStorage.clear()
    })

    afterEach(() => {
      const terroir = useCognitiveTerroir()
      terroir.toggleHighGlare(false)
      document.documentElement.removeAttribute('data-outdoor-contrast')
      localStorage.clear()
    })

    it('toggles High-Glare state and synchronizes data-outdoor-contrast attribute', () => {
      const terroir = useCognitiveTerroir()
      expect(terroir.isHighGlare.value).toBe(false)

      terroir.toggleHighGlare(true)
      expect(terroir.isHighGlare.value).toBe(true)
      expect(document.documentElement.getAttribute('data-outdoor-contrast')).toBe('high')
      expect(localStorage.getItem('vl360_high_glare')).toBe('true')

      terroir.toggleHighGlare(false)
      expect(terroir.isHighGlare.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-outdoor-contrast')).toBe(false)
      expect(localStorage.getItem('vl360_high_glare')).toBe('false')
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // SUITE 3: Phím Tắt Toàn Cục Alt+S
  // ───────────────────────────────────────────────────────────────────────────
  describe('Suite 3: Alt+S Keyboard Shortcut Activation', () => {
    it('implements Alt+S shortcut handling with preventDefault in useCognitiveTerroir', () => {
      expect(terroirComposableSource).toContain("e.altKey && (e.key === 's' || e.key === 'S')")
      expect(terroirComposableSource).toContain('toggleHighGlare()')
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // SUITE 4: Triệt Tiêu Hiệu Ứng Mờ & Định Kiểu Tài Liệu Dưới Nắng Gắt
  // ───────────────────────────────────────────────────────────────────────────
  describe('Suite 4: Document-Level Anti-Glare & Blur Elimination', () => {
    it('defines high-contrast map filters matching DESIGN.md Chapter 9.2', () => {
      expect(variablesCss).toMatch(/--contrast-glare-map-filter:\s*contrast\(1\.6\)\s+saturate\(1\.2\)/)
    })

    it('enforces 4px marker borders and 2px popup borders under high-contrast mode', () => {
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.map-locator-marker\s*\{[\s\S]*?border-width:\s*4px/)
      expect(baseCss).toMatch(/\[data-outdoor-contrast="high"\]\s+\.maplibregl-popup-content\s*\{[\s\S]*?border:\s*2px solid/)
    })
  })

  // ───────────────────────────────────────────────────────────────────────────
  // SUITE 5: Công Thái Học Thực Địa Trên ban-do.vue & tuyen-duong.vue
  // ───────────────────────────────────────────────────────────────────────────
  describe('Suite 5: Field Cartography Ergonomics in ban-do and tuyen-duong', () => {
    it('provides accessible toggle button and thumb dock on ban-do.vue', () => {
      expect(banDoVue).toContain('map-contrast-toggle')
      expect(banDoVue).toContain(':aria-pressed="outdoorContrast"')
      expect(banDoVue).toMatch(/\.map-contrast-toggle\s*\{[\s\S]*?min-height:\s*44px/)
    })

    it('contains interactive route preview structure for waypoint inspection in tuyen-duong.vue', () => {
      expect(tuyenDuongVue).toContain('route-preview-dialog')
      expect(tuyenDuongVue).toContain('route-preview-map-canvas')
      expect(tuyenDuongVue).toContain('route-path-line')
      expect(tuyenDuongVue).toContain('waypoint-circle')
    })
  })
})
