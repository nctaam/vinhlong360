// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('R1: Mekong Expedition Itinerary Builder & Pocket Field Journal (Moc 134)', () => {
  // ─── TIER 1: FEATURE COVERAGE (Core Requirements) ───────────────────────────
  describe('Tier 1: Feature Coverage — Pocket Field Journal & River Transit', () => {
    it('F1-1: renders Pocket Field Journal layout with narrative steps and editorial typography on pages/lich-trinh/[id].vue', () => {
      const src = doc('pages/lich-trinh/[id].vue')
      expect(src).toContain('data-color-system="tri-region-v1"')
      expect(src).toContain('class="timeline"')
      expect(src).toContain('class="step"')
      expect(src).toContain('step-time')
      expect(src).toContain('step-index')
      expect(src).toContain('step-card')
      expect(src).toContain('timeline-chapter')
      expect(src).toContain('CHAPTER_LABEL')
      expect(src).toContain('<CatalogAeoPlaque')
      expect(src).toContain('kicker="Góc nhìn bản địa · Tối ưu thời gian &amp; Điểm dừng chân"')
    })

    it('F1-2: integrates astronomical tide cycle and MekongWaterBadge on river transit components', () => {
      const transitWarning = doc('components/planner/PlannerRiverTransitWarning.vue')
      expect(transitWarning).toContain('<MekongWaterBadge')
      expect(transitWarning).toContain("import MekongWaterBadge from '~/components/MekongWaterBadge.vue'")
      expect(transitWarning).toMatch(/triều cường|triều dâng|con nước rằm/i)
      expect(transitWarning).toContain('sông Cổ Chiên')
    })

    it('F1-3: renders Cổ Chiên ferry crossing schedules and waypoints (Phà An Bình & Phà Đình Khao)', () => {
      const transitWarning = doc('components/planner/PlannerRiverTransitWarning.vue')
      expect(transitWarning).toContain('Phà An Bình (sông Cổ Chiên)')
      expect(transitWarning).toContain('4h30 đến 22h00')
      expect(transitWarning).toContain('Phà Đình Khao')
      expect(transitWarning).toContain('QL57 qua sông Cổ Chiên')
      expect(transitWarning).toContain('24/24')
      expect(transitWarning).toMatch(/kênh Thầy Cai/i)
      expect(transitWarning).toContain('lò gốm Mang Thít')
    })

    it('F1-4: enforces Mang Thít terra cotta heritage seal token (--mangthit-500 / #b95f38) on milestone markers', () => {
      const modal = doc('components/planner/PlannerMobilePassModal.vue')
      expect(modal).toMatch(/--mangthit-500/)
      
      const vars = doc('assets/css/variables.css')
      expect(vars).toMatch(/--mangthit-500:\s*#b95f38/)

      const itinCard = doc('components/ItineraryCard.vue')
      expect(itinCard).toContain('card-rule')
      expect(itinCard).toContain('--clay-600')
    })

    it('F1-5: provides pocket field pass export action with touch targets >= 44x44px', () => {
      const modal = doc('components/planner/PlannerMobilePassModal.vue')
      // Close button meets min 44x44px
      expect(modal).toMatch(/\.planner-pass-modal__close\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
      // Print and Done action buttons meet min 44px height
      expect(modal).toMatch(/\.planner-pass-modal__btn-print\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(modal).toMatch(/\.planner-pass-modal__btn-done\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('F1-6: preserves read-only public sharing invariants without destructive edit controls on pages/lich-trinh-chia-se/[id].vue', () => {
      const shared = doc('pages/lich-trinh-chia-se/[id].vue')
      expect(shared).toContain("'@type': 'TouristTrip'")
      expect(shared).toContain('copyShareLink')
      expect(shared).toContain('sp-btn-share')
      expect(shared).toContain('sp-btn-create')
      // Prohibit destructive authoring controls in public shared view
      expect(shared).not.toContain('deleteStop')
      expect(shared).not.toContain('removeStop')
      expect(shared).not.toContain('drag-handle')
      expect(shared).not.toContain('v-model="planTitle"')
    })
  })

  // ─── TIER 2: BOUNDARY & CORNER CASES (BVA & Anti-Slop) ─────────────────────
  describe('Tier 2: Boundary & Corner Cases — Anti-Slop, Semantics & Robustness', () => {
    it('B1-1: enforces semantic border radius (--radius-control: 8px) on pass modal action buttons', () => {
      const modal = doc('components/planner/PlannerMobilePassModal.vue')
      expect(modal).toMatch(/\.planner-pass-modal__btn-print\s*\{[\s\S]*?border-radius:\s*var\(--radius-control,\s*8px\);/)
      expect(modal).toMatch(/\.planner-pass-modal__btn-done\s*\{[\s\S]*?border-radius:\s*var\(--radius-control,\s*8px\);/)
      // Prohibit deprecated pill radius on rectangular action buttons
      expect(modal).not.toMatch(/\.planner-pass-modal__btn-done\s*\{[^}]*border-radius:\s*var\(--radius-pill/)
    })

    it('B1-2: purges raw emoji glyphs and SaaS gradients from itinerary index and cards', () => {
      const itinIndex = doc('pages/lich-trinh/index.vue')
      expect(itinIndex).not.toContain("icon: '🌅'")
      expect(itinIndex).not.toContain("icon: '🌤️'")
      expect(itinIndex).not.toContain("icon: '🌇'")
      expect(itinIndex).toContain("icon: 'cloud-sun'")
      expect(itinIndex).toContain("icon: 'sun'")
      expect(itinIndex).toContain("icon: 'cloud'")
      expect(itinIndex).toContain("icon: 'haze'")
    })

    it('B1-3: handles single-stop or empty itinerary boundary gracefully in transit warnings', () => {
      const transitWarning = doc('components/planner/PlannerRiverTransitWarning.vue')
      // Gracefully evaluates false when stops length is less than 2
      expect(transitWarning).toContain('if (!props.stops || props.stops.length < 2) return false')
    })

    it('B1-4: safeguards draft itinerary builder with robots noindex meta', () => {
      const planner = doc('pages/tao-lich-trinh.vue')
      expect(planner).toContain("robots: 'noindex, nofollow'")
      expect(planner).toContain("ogUrl: () => canonicalUrl('/tao-lich-trinh')")
    })

    it('B1-5: prohibits unauthorized raw hex colors across all planner components', () => {
      const rawHexRegex = /(?<![&w-])#(?!b95f38\b)[0-9a-fA-F]{3,8}\b/g
      const files = [
        'components/planner/PlannerMobilePassModal.vue',
        'components/planner/PlannerRiverTransitWarning.vue',
      ]
      for (const rel of files) {
        const content = doc(rel)
        const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/)
        if (styleMatch && styleMatch[1]) {
          const hexes = (styleMatch[1].match(rawHexRegex) || []).filter(h => h !== '#fff' && h !== '#ffffff')
          expect(hexes, `Found unauthorized raw hex in ${rel}`).toEqual([])
        }
      }
    })
  })

  // ─── TIER 3: PAIRWISE & COMBINATORIAL INTERACTIONS ────────────────────────
  describe('Tier 3: Pairwise & Combinatorial Interactions — Cross-Feature Synergy', () => {
    it('C1-1: transport mode selection preserves river transit awareness and tide telemetry', () => {
      const planner = doc('pages/tao-lich-trinh.vue')
      expect(planner).toContain('transportModes')
      expect(planner).toContain(':class="[\'chip\', { active: transportMode === m.value }]"')
      expect(planner).toContain('<PlannerRiverTransitWarning')
      expect(planner).toContain(':stops="stops"')
    })

    it('C1-2: island terroir stops trigger dedicated waterway notices for both Phà An Bình and Phà Đình Khao', () => {
      const transitWarning = doc('components/planner/PlannerRiverTransitWarning.vue')
      expect(transitWarning).toContain("s.place_area === 'an-binh'")
      expect(transitWarning).toContain("s.place_area === 'mang-thit'")
      expect(transitWarning).toContain("text.includes('đình khao')")
      expect(transitWarning).toContain("text.includes('thầy cai')")
      expect(transitWarning).toContain("text.includes('chợ lách')")
    })
  })

  // ─── TIER 4: REAL-WORLD WORKLOAD SCENARIOS ─────────────────────────────────
  describe('Tier 4: Real-World Workload Scenarios — Expedition Operational Journeys', () => {
    it('W1-1: expedition scenario: Cù lao An Bình orchard to Mang Thít pottery kilns crossing Cổ Chiên', () => {
      const transitWarning = doc('components/planner/PlannerRiverTransitWarning.vue')
      expect(transitWarning).toContain('Phà An Bình')
      expect(transitWarning).toContain('Phà Đình Khao')
      expect(transitWarning).toMatch(/kênh Thầy Cai/i)
      expect(transitWarning).toContain('tiền mặt lẻ')

      const detail = doc('pages/lich-trinh/[id].vue')
      expect(detail).toContain('timeline-head')
      expect(detail).toContain('step-type-label')
      expect(detail).toContain('route-leg-info')
      expect(detail).toContain('formatDistance')
      expect(detail).toContain('formatDuration')
    })

    it('W1-2: offline mobile field pass workflow: traveler generates pocket field card for remote navigation', () => {
      const modal = doc('components/planner/PlannerMobilePassModal.vue')
      expect(modal).toContain('role="dialog"')
      expect(modal).toContain('aria-modal="true"')
      expect(modal).toContain('Khả dụng ngoại tuyến')
      expect(modal).toContain('Thẻ hành trình thực địa')
      expect(modal).toContain('Cứu hộ &amp; Hỗ trợ địa phương:')
      expect(modal).toContain('Phà An Bình (24/7) · Hotline 0270 3822 188')
      expect(modal).toContain('printPass')
      expect(modal).toContain('window.print()')
    })
  })
})
