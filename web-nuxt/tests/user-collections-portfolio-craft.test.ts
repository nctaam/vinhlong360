// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('R3: User Space, Personal Collections & Privacy Governance (Moc 134)', () => {
  // ─── TIER 1: FEATURE COVERAGE (Core Requirements) ───────────────────────────
  describe('Tier 1: Feature Coverage — Heritage Portfolio Craft & Privacy Certification', () => {
    it('F3-1: applies Liquid Glass border tokens and ambient card shadows on pages/da-luu.vue', () => {
      const src = doc('pages/da-luu.vue')
      expect(src).toContain('data-color-system="tri-region-v1"')
      expect(src).toContain('var(--border-liquid-glass')
      expect(src).toContain('var(--shadow-card-ambient)')
      expect(src).toMatch(/\.saved-overview-item\s*\{[\s\S]*?var\(--border-liquid-glass/)
      expect(src).toMatch(/\.saved-empty-catalyst\s*\{[\s\S]*?var\(--border-liquid-glass/)
      expect(src).toMatch(/\.saved-sugg-card\s*\{[\s\S]*?var\(--border-liquid-glass/)
    })

    it('F3-2: renders asymmetric 1.35fr/1fr discovery grid and Mang Thít terracotta lead card in empty state', () => {
      const src = doc('pages/da-luu.vue')
      expect(src).toMatch(/grid-template-columns:\s*1\.35fr\s+1fr/)
      expect(src).toContain('saved-sugg-lead')
      expect(src).toMatch(/border-left:\s*3px solid var\(--mangthit-500\)/)
      expect(src).toContain('Lò gạch gốm đỏ ven sông Thầy Kay')
      expect(src).toContain('Vương quốc gốm đỏ')
    })

    it('F3-3: purges obsolete colonial/district "Long Hồ" and establishes "Cù lao An Bình" terroir in suggestions', () => {
      const src = doc('pages/da-luu.vue')
      // Must contain Cù lao An Bình miệt vườn sinh thái
      expect(src).toContain('Cù lao An Bình miệt vườn sinh thái')
      expect(src).toContain('Vườn trái cây bốn mùa · 10p phà Cổ Chiên')
      // Must not contain obsolete recommendation label "Long Hồ"
      expect(src).not.toMatch(/<span class="sugg-badge[^"]*">Long Hồ<\/span>/)
      expect(src).not.toMatch(/Long Hồ miệt vườn/)
    })

    it('F3-4: establishes Decree 13/2023/ND-CP Privacy Certificate Badge on pages/tai-khoan.vue', () => {
      const src = doc('pages/tai-khoan.vue')
      expect(src).toContain('cp-privacy-cert-badge')
      expect(src).toContain('Chứng thư minh bạch')
      expect(src).toContain('Nghị định 13/2023/NĐ-CP')
      expect(src).toContain('zero-telemetry')
      expect(src).toContain('kiểm soát lưu trữ cục bộ trên thiết bị')
      expect(src).toContain('/cai-dat#du-lieu')
      expect(src).toContain('/cai-dat#rieng-tu')
    })

    it('F3-5: establishes calm editorial typography and non-distracting notifications on pages/thong-bao.vue', () => {
      const src = doc('pages/thong-bao.vue')
      expect(src).toContain('dateline-eyebrow')
      expect(src).toContain('HỘP THƯ · SỔ TAY CỦA BẠN')
      expect(src).toContain('var(--font-editorial)')
      expect(src).toContain('tb-dot')
      expect(src).toContain('tb-dismiss')
      expect(src).toContain('Đọc tất cả')
    })
  })

  // ─── TIER 2: BOUNDARY, TOKEN & EDGE CASES ────────────────────────────────────
  describe('Tier 2: Boundary, Token & Privacy Invariants', () => {
    it('B3-1: enforces quiet loading state (saved-quiet-loading) without jarring skeleton layout shift', () => {
      const srcSaved = doc('pages/da-luu.vue')
      expect(srcSaved).toContain('saved-quiet-loading')
      expect(srcSaved).toContain('Đang đồng bộ địa điểm đã lưu...')
      expect(srcSaved).not.toContain('<SkeletonGrid')

      const srcAccount = doc('pages/tai-khoan.vue')
      expect(srcAccount).toContain('cp-quiet-loading')
      expect(srcAccount).toContain('Đang đồng bộ hoạt động gần đây...')
    })

    it('B3-2: adheres to design system semantic radii tokens across user pages', () => {
      const srcSaved = doc('pages/da-luu.vue')
      expect(srcSaved).toContain('var(--radius-sheet)')
      expect(srcSaved).toContain('var(--radius-surface)')
      expect(srcSaved).toContain('var(--radius-control)')
      expect(srcSaved).toContain('var(--radius-pill')

      const srcAccount = doc('pages/tai-khoan.vue')
      expect(srcAccount).toContain('var(--radius-sheet)')
      expect(srcAccount).toContain('var(--radius-surface)')
      expect(srcAccount).toContain('var(--radius-control)')
    })

    it('B3-3: strictly forbids raw untokenized hardcoded colors in user personal page styles', () => {
      const srcSaved = doc('pages/da-luu.vue')
      const scopedStyle = srcSaved.split('<style scoped>')[1] || ''
      // Should not contain untokenized hex codes in scoped CSS (e.g. #fff, #000, #333)
      const rawHexMatches = scopedStyle.match(/#[0-9a-fA-F]{3,8}\b/g) || []
      expect(rawHexMatches).toHaveLength(0)
    })

    it('B3-4: strictly enforces robots noindex/nofollow privacy guards on user data surfaces', () => {
      const srcSaved = doc('pages/da-luu.vue')
      expect(srcSaved).toMatch(/robots:\s*['"]noindex,\s*nofollow['"]/)

      const srcAccount = doc('pages/tai-khoan.vue')
      expect(srcAccount).toMatch(/robots:\s*['"]noindex,\s*nofollow['"]/)

      const srcNotif = doc('pages/thong-bao.vue')
      expect(srcNotif).toMatch(/robots:\s*['"]noindex,\s*nofollow['"]/)
    })
  })

  // ─── TIER 3: COMBINATORIAL & ACCESSIBILITY ──────────────────────────────────
  describe('Tier 3: Combinatorial States & Interactive Accessibility', () => {
    it('C3-1: provides fully accessible WAI-ARIA tablist and tabpanel semantics on pages/da-luu.vue', () => {
      const src = doc('pages/da-luu.vue')
      expect(src).toContain('role="tablist"')
      expect(src).toContain('aria-orientation="horizontal"')
      expect(src).toContain('role="tab"')
      expect(src).toContain(':aria-selected="tab === t.key"')
      expect(src).toContain(':aria-controls="`saved-panel-${t.key}`"')
      expect(src).toContain('role="tabpanel"')
    })

    it('C3-2: enforces WCAG 2.2 touch target ergonomics (>= 44x44px) on all user actions and controls', () => {
      const srcSaved = doc('pages/da-luu.vue')
      expect(srcSaved).toMatch(/\.saved-remove\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
      expect(srcSaved).toMatch(/\.saved-tab\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(srcSaved).toMatch(/\.saved-search input\s*\{[\s\S]*?min-height:\s*44px;/)

      const srcAccount = doc('pages/tai-khoan.vue')
      expect(srcAccount).toMatch(/\.cp-mini-link\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(srcAccount).toMatch(/\.cp-load-more[^{]*\{[\s\S]*?min-height:\s*44px;/)

      const srcNotif = doc('pages/thong-bao.vue')
      expect(srcNotif).toMatch(/\.tb-dismiss\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
    })

    it('C3-3: implements semantic progress and meter roles for account completion and security scoring', () => {
      const src = doc('pages/tai-khoan.vue')
      expect(src).toContain('role="meter"')
      expect(src).toContain('aria-valuemin="0"')
      expect(src).toContain('aria-valuemax="100"')
      expect(src).toContain(':aria-valuenow="accountScore"')
      expect(src).toContain('role="progressbar"')
      expect(src).toContain(':aria-valuenow="profileCompletion"')
    })
  })

  // ─── TIER 4: REAL-WORLD JOURNEYS ─────────────────────────────────────────────
  describe('Tier 4: Real-World Personal Curation & Privacy Audit Journeys', () => {
    it('J3-1: Journey — Unauthenticated explorer arrives at personal collection, inspects terroir suggestions and auth prompt', () => {
      const src = doc('pages/da-luu.vue')
      // Guest banner gives clear local storage warning and sync CTA
      expect(src).toContain('saved-guest-banner')
      expect(src).toContain('Danh sách đang lưu trên trình duyệt này')
      expect(src).toContain('Đăng nhập để đồng bộ')
      // Journey action rail appears in empty state
      expect(src).toContain('v-if="totalSaved === 0 && savedJourneyActions.length"')
      // Catalyst box provides starting points for the Delta
      expect(src).toContain('saved-catalyst-box')
      expect(src).toContain('Hành trình sông nước của bạn chưa được đánh dấu')
      expect(src).toContain('/dia-diem?q=Mang+Thít')
      expect(src).toContain('/dia-diem?q=An+Bình')
      expect(src).toContain('/dia-diem?q=Trà+Ôn')
    })

    it('J3-2: Journey — Contributor conducts privacy compliance audit and verifies zero-telemetry self-governance', () => {
      const src = doc('pages/tai-khoan.vue')
      // Contributor views transparent privacy cert
      expect(src).toContain('cp-privacy-cert-badge')
      expect(src).toContain('Hệ thống bảo đảm 100% zero-telemetry')
      // Verified profile completion checklist
      expect(src).toContain('completedProfileChecks')
      expect(src).toContain('securitySummary')
      // Data export links
      expect(src).toContain('to="/cai-dat#du-lieu"')
      expect(src).toContain('to="/cai-dat#rieng-tu"')
      // Live smart recommendations mounted client-side only
      expect(src).toContain('<ClientOnly>')
      expect(src).toContain('<LazySmartRecommendations')
    })
  })
})
