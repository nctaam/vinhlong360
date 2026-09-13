// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

// Relative luminance formula per WCAG 2.2 specs
function sRGBtoLin(c: number): number {
  const norm = c / 255
  return norm <= 0.04045 ? norm / 12.92 : Math.pow((norm + 0.055) / 1.055, 2.4)
}

function getLuminance(hex: string): number {
  const clean = hex.replace('#', '')
  const r = sRGBtoLin(parseInt(clean.substring(0, 2), 16))
  const g = sRGBtoLin(parseInt(clean.substring(2, 4), 16))
  const b = sRGBtoLin(parseInt(clean.substring(4, 6), 16))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function getContrast(hex1: string, hex2: string): number {
  const l1 = getLuminance(hex1)
  const l2 = getLuminance(hex2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

describe('Adversarial Verification & Empirical Stress Harness (Moc 134)', () => {
  const targetPages = [
    'pages/tao-lich-trinh.vue',
    'pages/lich-trinh/[id].vue',
    'pages/lich-trinh-chia-se/[id].vue',
    'pages/danh-ba.vue',
    'pages/bang-xep-hang.vue',
    'pages/nguoi-dung/[id].vue',
    'pages/da-luu.vue',
    'pages/tai-khoan.vue',
    'pages/cai-dat.vue',
    'pages/thong-bao.vue',
    'pages/gioi-thieu.vue',
    'pages/lien-he.vue',
  ]

  // ──────────────────────────────────────────────────────────────────────────
  // 1. TOUCH TARGET HITBOX VERIFICATION (>= 44x44px)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Touch Hitbox Ergonomics: All interactive targets must satisfy >= 44x44px', () => {
    it('verifies all 12 target page files exist and are readable', () => {
      for (const page of targetPages) {
        const content = doc(page)
        expect(content.length, `${page} should not be empty`).toBeGreaterThan(100)
      }
    })

    it('verifies pages/tao-lich-trinh.vue stop controls, action dock and summary toggle meet min 44x44px', () => {
      const src = doc('pages/tao-lich-trinh.vue')
      expect(src).toMatch(/\.stop-card-actions\s+button\s*\{[\s\S]*?min-height:\s*44px;[\s\S]*?min-width:\s*44px;/)
      expect(src).toMatch(/\.stop-card-actions\s+\.btn-icon-sm\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.planner-summary-toggle\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/lich-trinh/[id].vue action buttons meet min 44x44px', () => {
      const src = doc('pages/lich-trinh/[id].vue')
      expect(src).toMatch(/\.itin-actions\s+\.btn\s*\{[\s\S]*?min-height:\s*44px;[\s\S]*?min-width:\s*44px;/)
    })

    it('verifies pages/lich-trinh-chia-se/[id].vue buttons and step markers meet min 44x44px', () => {
      const src = doc('pages/lich-trinh-chia-se/[id].vue')
      expect(src).toMatch(/\.sp-num\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.sp-btn-pass,\s*\.sp-btn-share,\s*\.sp-btn-create\s*\{[\s\S]*?min-height:\s*44px;[\s\S]*?min-width:\s*44px;/)
    })

    it('verifies pages/danh-ba.vue gazetteer tabs, hotline call buttons, and reports meet min 44px', () => {
      const src = doc('pages/danh-ba.vue')
      expect(src).toMatch(/\.gazetteer-tab\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.gazetteer-call-btn\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.gazetteer-report-link\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.dir-emergency-call\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.dir-emergency-call--priority\s*\{[\s\S]*?min-height:\s*48px;/)
      expect(src).toMatch(/\.fac-row\s+a\[href\^="tel:"\]\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.fac-report\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/bang-xep-hang.vue search input, podium links and rows meet touch standards', () => {
      const src = doc('pages/bang-xep-hang.vue')
      expect(src).toMatch(/\.bxh-search\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.bxh-row\s*\{[\s\S]*?min-height:\s*56px;/)
      expect(src).toMatch(/\.bxh-avatar\s*\{[\s\S]*?width:\s*44px;[\s\S]*?height:\s*44px;/)
    })

    it('verifies pages/nguoi-dung/[id].vue follow modal, clickable stats and insight link meet min 44px', () => {
      const src = doc('pages/nguoi-dung/[id].vue')
      expect(src).toMatch(/\.stat-clickable\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.profile-insight-link\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.fm-tab\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.fm-close\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.fm-user\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/da-luu.vue tabs, search input and remove actions meet min 44x44px', () => {
      const src = doc('pages/da-luu.vue')
      expect(src).toMatch(/\.saved-tab\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.saved-search\s+input\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.saved-remove\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/tai-khoan.vue action items, data rows, mini links and wide buttons meet min 44px', () => {
      const src = doc('pages/tai-khoan.vue')
      expect(src).toMatch(/\.cp-mini-link\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.cp-action-item,\s*\.cp-data-row\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.cp-activity-item\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.cp-load-more,\s*\.cp-wide-btn\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/cai-dat.vue tabs, theme buttons, toggles and delete confirmation meet min 44px', () => {
      const src = doc('pages/cai-dat.vue')
      expect(src).toMatch(/\.settings-tab\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.theme-btn\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.toggle\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\[data-action="load-consent-history"\]\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.delete-confirm\s+\.btn\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/thong-bao.vue chips, item links and dismiss buttons meet min 44x44px', () => {
      const src = doc('pages/thong-bao.vue')
      expect(src).toMatch(/\.tb-filters\s+\.chip\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.tb-item-link\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(src).toMatch(/\.tb-dismiss\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/)
    })

    it('verifies pages/gioi-thieu.vue and pages/lien-he.vue action CTA buttons meet min 44px', () => {
      const about = doc('pages/gioi-thieu.vue')
      expect(about).toMatch(/\.about-cta\s+\.btn\s*\{[\s\S]*?min-height:\s*44px;/)

      const contact = doc('pages/lien-he.vue')
      expect(contact).toMatch(/\.card-action\s+\.btn\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(contact).toMatch(/\.contact-card\s+\.card-note\s+a\s*\{[\s\S]*?min-height:\s*44px;/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 2. CONTRAST RATIOS (WCAG 2.2 AAA EMPIRICAL TESTING)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Contrast Ratios: Empirical calculation against WCAG 2.2 AAA (>= 7:1 for headings, >= 4.5:1 for body)', () => {
    const tokens = {
      mekongInk: '#081A16',
      mekongMuted: '#415450',
      alluvialPaper: '#F9F7F1',
      surfaceWhite: '#FDFCF9',
      pureWhite: '#FFFFFF',
      nightCanvas: '#071210',
      nightSurface: '#111D1B',
      nightRaised: '#1D2927',
      nightText: '#EDEBE5',
      nightMuted: '#A4B1AE',
      river700: '#00434E',
      orchard600: '#255D34',
      harvest700: '#855A16',
      alluvialGold: '#C99446',
      mangthit500: '#B95F38',
      mangthit600: '#95402B',
      mangthit700: '#722B1A',
    }

    it('verifies primary ink text achieves >= 7:1 contrast on all light surfaces (AAA Headings & Body)', () => {
      const contrastPaper = getContrast(tokens.mekongInk, tokens.alluvialPaper)
      const contrastSurface = getContrast(tokens.mekongInk, tokens.surfaceWhite)
      const contrastWhite = getContrast(tokens.mekongInk, tokens.pureWhite)

      expect(contrastPaper, 'Ink on canvas').toBeGreaterThanOrEqual(15.0)
      expect(contrastSurface, 'Ink on surface').toBeGreaterThanOrEqual(15.0)
      expect(contrastWhite, 'Ink on white').toBeGreaterThanOrEqual(15.0)
    })

    it('verifies muted editorial text achieves >= 4.5:1 contrast on light surfaces (AAA Body / AA Large)', () => {
      const contrastPaper = getContrast(tokens.mekongMuted, tokens.alluvialPaper)
      const contrastSurface = getContrast(tokens.mekongMuted, tokens.surfaceWhite)

      expect(contrastPaper, 'Muted on canvas').toBeGreaterThanOrEqual(7.0)
      expect(contrastSurface, 'Muted on surface').toBeGreaterThanOrEqual(7.0)
    })

    it('verifies dark mode nightText and nightMuted satisfy WCAG 2.2 AAA contrast standards', () => {
      const textOnCanvas = getContrast(tokens.nightText, tokens.nightCanvas)
      const textOnSurface = getContrast(tokens.nightText, tokens.nightSurface)
      const textOnRaised = getContrast(tokens.nightText, tokens.nightRaised)

      expect(textOnCanvas, 'Night text on canvas').toBeGreaterThanOrEqual(15.0)
      expect(textOnSurface, 'Night text on surface').toBeGreaterThanOrEqual(14.0)
      expect(textOnRaised, 'Night text on raised').toBeGreaterThanOrEqual(12.0)

      const mutedOnCanvas = getContrast(tokens.nightMuted, tokens.nightCanvas)
      const mutedOnSurface = getContrast(tokens.nightMuted, tokens.nightSurface)
      const mutedOnRaised = getContrast(tokens.nightMuted, tokens.nightRaised)

      expect(mutedOnCanvas, 'Night muted on canvas').toBeGreaterThanOrEqual(8.0)
      expect(mutedOnSurface, 'Night muted on surface').toBeGreaterThanOrEqual(7.0)
      expect(mutedOnRaised, 'Night muted on raised').toBeGreaterThanOrEqual(6.5)
    })

    it('empirically identifies white text on alluvial-gold button as a contrast defect (DEFECT-1)', () => {
      // In pages/danh-ba.vue: .dir-emergency-call--priority sets background: var(--alluvial-gold) (#c99446)
      // and color: var(--color-on-action, var(--white)) (#ffffff)
      const whiteOnGold = getContrast(tokens.pureWhite, tokens.alluvialGold)
      // Contrast is only ~2.69:1! This severely fails 4.5:1 and 7:1
      expect(whiteOnGold).toBeLessThan(3.0)
      // Whereas dark ink on alluvial gold reaches 6.68:1
      const inkOnGold = getContrast(tokens.mekongInk, tokens.alluvialGold)
      expect(inkOnGold).toBeGreaterThanOrEqual(6.5)
    })

    it('empirically identifies mangthit-500 badge text on light surface as falling short of 4.5:1 (DEFECT-2)', () => {
      // In pages/tao-lich-trinh.vue and pages/lich-trinh-chia-se/[id].vue:
      // .stop-mangthit-badge and .sp-mangthit-badge use color: var(--mangthit-500) (#B95F38)
      // on a light tinted surface (~#F6ECE6)
      const contrast = getContrast(tokens.mangthit500, tokens.surfaceWhite)
      expect(contrast).toBeLessThan(4.5) // 4.30:1 fails WCAG AA 4.5:1 for body text
      // Whereas mangthit-700 (#722B1A) achieves 9.86:1 (satisfies AAA >= 7:1)
      const contrast700 = getContrast(tokens.mangthit700, tokens.surfaceWhite)
      expect(contrast700).toBeGreaterThanOrEqual(7.0)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 3. BOUNDARY VALUES & CORNER CASES
  // ──────────────────────────────────────────────────────────────────────────
  describe('Boundary Values: 0 stops, 20+ stops, empty collections, empty notifications, unauthenticated visitors', () => {
    it('verifies 0 stops in itinerary builder displays empty state and disables save action', () => {
      const src = doc('pages/tao-lich-trinh.vue')
      expect(src).toContain('v-if="!stops.length" class="builder-empty"')
      expect(src).toContain('<EmptyState')
      expect(src).toContain('icon-name="compass"')
      expect(src).toContain('title="Chưa có điểm dừng nào"')
      // Save button is disabled when stops.length === 0
      expect(src).toContain(':disabled="!stops.length || saving"')
      // Transport mode selector hidden when stops < 2
      expect(src).toContain('v-if="stops.length >= 2" class="transport-mode"')
    })

    it('verifies 20+ stops boundary enforcement and capacity limits in itinerary builder', () => {
      const src = doc('pages/tao-lich-trinh.vue')
      expect(src).toContain('MAX_STOPS = 20')
      expect(src).toContain('stops.value.length >= MAX_STOPS')
      expect(src).toContain('v-if="stops.length >= 20" class="max-stops-warn"')
      expect(src).toContain('Đã đạt tối đa 20 điểm mỗi lịch trình.')
    })

    it('verifies sunArcDots distributes stops evenly instead of collapsing to 50% when stops lack timestamps (DEFECT-3 remediated)', () => {
      // When known.length === 0 (no stop has parsed time), stops are distributed evenly
      // along the rail instead of collapsing to 50%, preventing milestone collapse.
      const src = doc('pages/lich-trinh/[id].vue')
      expect(src).not.toContain(': 50)')
      expect(src).toContain('(i / (stops.length - 1 || 1)) * 100')
    })

    it('verifies empty collections in pages/da-luu.vue present terroir catalysts and authentic empty states', () => {
      const src = doc('pages/da-luu.vue')
      expect(src).toContain('class="saved-catalyst-box"')
      expect(src).toContain('Hành trình sông nước của bạn chưa được đánh dấu')
      expect(src).toContain('Vương quốc gốm đỏ')
      expect(src).toContain('Cù lao An Bình miệt vườn sinh thái')
      expect(src).toContain('Chợ nổi ngã ba sông Hậu')
    })

    it('verifies empty notifications in pages/thong-bao.vue handle category-specific empty hints', () => {
      const src = doc('pages/thong-bao.vue')
      expect(src).toContain('Thích bài viết để bắt đầu nhận thông báo lượt thích.')
      expect(src).toContain('Viết bình luận để nhận phản hồi từ cộng đồng.')
      expect(src).toContain('Theo dõi người dùng để nhận thông báo khi họ đăng bài mới.')
      expect(src).toContain('Khi ai đó nhắc đến bạn trong bài viết hoặc bình luận, bạn sẽ thấy ở đây.')
      expect(src).toContain('v-if="isLoggedIn && items.some(n => !n.is_read)"')
    })

    it('verifies unauthenticated visitor states are strictly protected across all personal hubs', () => {
      const taiKhoan = doc('pages/tai-khoan.vue')
      expect(taiKhoan).toContain('v-if="!isLoggedIn" class="cp-guest"')
      expect(taiKhoan).toContain('title="Tài khoản — Hồ sơ hành trình"')

      const caiDat = doc('pages/cai-dat.vue')
      expect(caiDat).toContain('v-if="!isLoggedIn" class="settings-guest card"')
      expect(caiDat).toContain('Bạn cần đăng nhập để chỉnh sửa hồ sơ.')

      const thongBao = doc('pages/thong-bao.vue')
      expect(thongBao).toContain('v-if="!isLoggedIn" class="tb-guest"')
      expect(thongBao).toContain('title="Đăng nhập để xem thông báo"')

      const daLuu = doc('pages/da-luu.vue')
      expect(daLuu).toContain('v-if="!isLoggedIn" class="saved-guest-banner"')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 4. LONG TITLES, OVERFLOW & RESPONSIVE LAYOUT STRESS-TESTING
  // ──────────────────────────────────────────────────────────────────────────
  describe('Long Titles, Overflow Resilience & Responsive Layouts', () => {
    it('verifies itinerary builder protects against title overflow with character limit and counter', () => {
      const src = doc('pages/tao-lich-trinh.vue')
      expect(src).toContain('maxlength="100"')
      expect(src).toContain('v-if="planTitle.length > 80" class="title-counter"')
      expect(src).toContain(':class="{ warn: planTitle.length >= 95 }"')
    })

    it('verifies leaderboard podium and list handle arbitrary name lengths without layout blowouts', () => {
      const src = doc('pages/bang-xep-hang.vue')
      expect(src).toMatch(/\.podium-name\s*\{[\s\S]*?overflow-wrap:\s*anywhere;/)
      expect(src).toMatch(/\.bxh-name\s*\{[\s\S]*?overflow:\s*hidden;\s*text-overflow:\s*ellipsis;/)
    })

    it('verifies responsive mobile breakpoints collapse grids without horizontal scroll overflows', () => {
      const danhBa = doc('pages/danh-ba.vue')
      expect(danhBa).toMatch(/@media\s*\(min-width:\s*640px\)\s*\{\s*\.gazetteer-card-grid\s*\{\s*grid-template-columns:\s*repeat\(2,\s*1fr\);/)

      const bxh = doc('pages/bang-xep-hang.vue')
      expect(bxh).toMatch(/@media\s*\(max-width:\s*620px\)\s*\{\s*\.bxh-podium\s*\{\s*grid-template-columns:\s*1fr;/)

      const settings = doc('pages/cai-dat.vue')
      expect(settings).toMatch(/@media\s*\(max-width:\s*600px\)\s*\{[\s\S]*?\.settings-tabs\s*\{/)
    })
  })
})
