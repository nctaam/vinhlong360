// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { telHref } from '../utils/safe'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('R2: Monocle Local Directory & Gazetteer Almanac Craft (Moc 134)', () => {
  // ─── TIER 1: FEATURE COVERAGE (Core Requirements) ───────────────────────────
  describe('Tier 1: Feature Coverage — Monocle Gazetteer & Authentic Directory', () => {
    it('F2-1: formats directory as Monocle gazetteer on pages/danh-ba.vue with curated sections', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toContain('gazetteer-nav-block')
      expect(src).toContain('gazetteer-tabs')
      expect(src).toContain('gazetteer-tab')
      expect(src).toContain('gazetteer-panel')
      expect(src).toContain('gazetteer-entry-card')
      expect(src).toContain('entry-tag--orchard')
      expect(src).toContain('entry-tag--pier')
      expect(src).toMatch(/gốm Mang Thít|Vương quốc gốm đỏ/i)
      expect(src).toMatch(/sầu riêng|bưởi Năm Roi|cù lao An Bình/i)
      expect(src).toMatch(/phà An Bình|bến đò/i)
    })

    it('F2-2: strictly enforces verified phone numbers with direct tel: links using telHref', () => {
      // Test the telHref helper contract
      expect(telHref('0270 3822 305')).toBe('tel:02703822305')
      expect(telHref('+84 270 3822 188')).toBe('tel:+842703822188')
      expect(telHref('0270.3858.113')).toBe('tel:02703858113')
      expect(telHref('(0270) 3822 514')).toBe('tel:02703822514')
      expect(telHref('')).toBe('#')
      expect(telHref(null)).toBe('#')
      expect(telHref(undefined)).toBe('#')

      const src = doc('pages/danh-ba.vue')
      expect(src).toContain('gazetteer-call-btn')
      expect(src).toContain(':href="telHref(')
    })

    it('F2-3: equips tactile filter tabs, category pills and call buttons with touch targets >= 44x44px', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toMatch(/\.gazetteer-tab\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.gazetteer-call-btn\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.dir-emergency-call\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.dir-emergency-call--priority\s*\{[\s\S]*?min-height:\s*48px;/)
    })

    it('F2-4: integrates standardized SourceMark component across verified entries', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toContain('<SourceMark tier="official"')
      expect(src).toContain('SourceMark')
    })

    it('F2-5: presents 24/7 Tourism Emergency Rescue Hotline with priority layout', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toContain('data-dir-emergency')
      expect(src).toMatch(/CSGT &amp; Cứu nạn|CSGT & Cứu nạn/i)
      expect(src).toContain('0270 3822 305')
      expect(src).toContain('115')
      expect(src).toContain('113')
      expect(src).toContain('Phà An Bình')
      expect(src).toContain('0270 3822 188')
    })
  })

  // ─── TIER 2: BOUNDARY & CORNER CASES (BVA & Anti-Slop) ─────────────────────
  describe('Tier 2: Boundary & Corner Cases — Anti-Slop & Data Integrity', () => {
    it('B2-1: eliminates skeleton loading during directory fetching per CLAUDE.md §1.7', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).not.toContain('.fac-card-skel')
      expect(src).not.toContain('.fac-sk-item')
      expect(src).not.toContain('<SkeletonList')
    })

    it('B2-2: rejects equal 3-column layout slop in favor of priority hierarchy and responsive grid', () => {
      const src = doc('pages/danh-ba.vue')
      // Prohibit equal 3-column slop in emergency grid
      expect(src).not.toContain('grid-template-columns: repeat(3, 1fr); /* Equal 3-column slop */')
      expect(src).toContain('.dir-emergency-card--lead')
      expect(src).toContain('.gazetteer-card-grid')
    })

    it('B2-3: phone sanitization rejects malformed input and preserves emergency hotlines', () => {
      expect(telHref('115')).toBe('tel:115')
      expect(telHref('113')).toBe('tel:113')
      expect(telHref('114')).toBe('tel:114')
      expect(telHref('abc')).toBe('#')
      expect(telHref('   ')).toBe('#')
    })

    it('B2-4: handles empty search and category filter boundary with polite empty state', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toMatch(/empty-hint|<EmptyState/i)
      expect(src).toContain('Chọn một xã/phường')
    })

    it('B2-5: enforces zero raw hex color leaks in directory styles', () => {
      const src = doc('pages/danh-ba.vue')
      const styleMatch = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)
      if (styleMatch && styleMatch[1]) {
        const rawHexRegex = /(?<![&w-])#[0-9a-fA-F]{3,8}\b/g
        const hexes = (styleMatch[1].match(rawHexRegex) || []).filter(h => h !== '#fff' && h !== '#ffffff')
        expect(hexes, 'Found raw hex colors in pages/danh-ba.vue style block').toEqual([])
      }
    })
  })

  // ─── TIER 3: PAIRWISE & COMBINATORIAL INTERACTIONS ────────────────────────
  describe('Tier 3: Pairwise & Combinatorial Interactions — Gazetteer Facets', () => {
    it('C2-1: gazetteer tab filtering maps traditional craft artisans, orchards and boat piers', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toContain("activeGazetteerTab === 'artisans'")
      expect(src).toContain("activeGazetteerTab === 'orchards'")
      expect(src).toContain("activeGazetteerTab === 'piers'")
      expect(src).toContain("activeGazetteerTab === 'facilities'")
    })

    it('C2-2: accessible direct dialing pairs valid tel: href with descriptive aria-label', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toContain('data-contact-action="phone"')
      expect(src).toMatch(/:aria-label="`Gọi trực tiếp/)
    })
  })

  // ─── TIER 4: REAL-WORLD WORKLOAD SCENARIOS ─────────────────────────────────
  describe('Tier 4: Real-World Workload Scenarios — Traveler Directory Journeys', () => {
    it('W2-1: river emergency rescue scenario: stranded traveler accesses priority emergency hotline', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toContain('Cứu hộ Du lịch &amp; Hotline Khẩn cấp 24/7')
      expect(src).toMatch(/CSGT &amp; Cứu nạn|CSGT & Cứu nạn/i)
      expect(src).toContain('Phà An Bình')
      expect(src).toContain('0270 3822 188')
      expect(src).toContain('dir-emergency-call--priority')
    })

    it('W2-2: cultural artisan gazetteer lookup: researcher locates Mang Thít pottery kilns with verified credentials', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toMatch(/Gốm Đỏ|gốm đỏ Mang Thít/i)
      expect(src).toContain('entry-tag')
      expect(src).toContain('entry-locality')
      expect(src).toContain('entry-address')
      expect(src).toContain('SourceMark')
      expect(src).toContain('Báo thông tin chưa đúng')
    })
  })
})
