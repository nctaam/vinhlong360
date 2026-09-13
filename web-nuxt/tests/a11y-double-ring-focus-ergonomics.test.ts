/**
 * WCAG 2.2 AAA Double-Ring Focus & Ergonomics Quality Gate Invariant Test
 * File: web-nuxt/tests/a11y-double-ring-focus-ergonomics.test.ts
 *
 * Verifies:
 * 1. Double-Ring Focus tokens in variables.css (--focus-ring-inner, --focus-ring-outer)
 * 2. base.css outline + box-shadow double-ring for :focus-visible
 * 3. base.css forced-colors support for Windows High Contrast Mode
 * 4. SC 2.4.11 scroll-margin-top for sticky header
 * 5. SC 2.4.12 scroll-margin-bottom for bottom navigation bar
 * 6. SC 2.5.5 Touch Target minimum 44px on interactive targets
 * 7. Mobile bottom nav item min-height >= 52px
 * 8. Skip Link #main-content and tabindex="-1" on <main>
 * 9. J/K section navigation focus synchrony (.focus({ preventScroll: true }))
 * 10. Slash (/) search drawer trigger guarded by isEditableFocused
 * 11. Escape key dismissal of overlays
 * 12. Elder Reading Mode touch target >= 52px per DESIGN.md §9.1
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('WCAG 2.2 AAA Double-Ring Focus & Ergonomics Quality Gate', () => {
  const root = resolve(__dirname, '..')
  const variablesCss = readFileSync(resolve(root, 'assets/css/variables.css'), 'utf8')
  const baseCss = readFileSync(resolve(root, 'assets/css/base.css'), 'utf8')
  const shellCss = readFileSync(resolve(root, 'assets/css/shell.css'), 'utf8')
  const defaultLayout = readFileSync(resolve(root, 'layouts/default.vue'), 'utf8')

  // ───────────────────────────────────────────────────────────────────────────
  // Nhóm 1: Token Định Danh Vòng Tiêu Điểm Kép & Forced Colors
  // ───────────────────────────────────────────────────────────────────────────
  it('1. variables.css khai báo đầy đủ hệ thống token --focus-ring-inner và --focus-ring-outer', () => {
    expect(variablesCss).toMatch(/--focus-ring-inner:\s*#[0-9a-fA-F]{3,6}/)
    expect(variablesCss).toMatch(/--focus-ring-outer:\s*#[0-9a-fA-F]{3,6}/)
  })

  it('2. base.css áp dụng viền đôi kép (outline + box-shadow) cho selector :focus-visible', () => {
    expect(baseCss).toMatch(/outline:\s*2px\s+solid\s+var\(--focus-ring-outer/i)
    expect(baseCss).toMatch(/box-shadow:\s*0\s+0\s+0\s+2px\s+var\(--focus-ring-inner/i)
  })

  it('3. base.css hỗ trợ forced-colors cho Windows High Contrast Mode', () => {
    expect(baseCss).toMatch(/@media\s*\(\s*forced-colors:\s*active\s*\)/)
    expect(baseCss).toMatch(/outline:\s*3px\s+solid\s+Highlight/i)
  })

  // ───────────────────────────────────────────────────────────────────────────
  // Nhóm 2: SC 2.4.11 & SC 2.4.12 Focus Not Obscured (Không bị che khuất)
  // ───────────────────────────────────────────────────────────────────────────
  it('4. base.css chừa scroll-margin-top cho sticky header', () => {
    expect(baseCss).toMatch(/scroll-margin-top:\s*calc\(var\(--header-h\)/)
  })

  it('5. base.css chừa scroll-margin-bottom để thanh đáy mobile không che khuất phần tử nhận focus (SC 2.4.12)', () => {
    expect(baseCss).toMatch(/scroll-margin-bottom:\s*calc\(var\(--shell-public-bottom-nav-reserved-height/i)
  })

  // ───────────────────────────────────────────────────────────────────────────
  // Nhóm 3: Công thái học vùng chạm (SC 2.5.5 Touch Target AAA >= 44px)
  // ───────────────────────────────────────────────────────────────────────────
  it('6. base.css thiết lập chuẩn chạm tối thiểu 44px cho mọi phần tử tương tác', () => {
    expect(baseCss).toMatch(/min-height:\s*var\(--touch-min\)/)
    expect(variablesCss).toMatch(/--touch-min:\s*44px/)
  })

  it('7. shell.css thanh điều hướng đáy di động có min-height >= 52px cho mỗi mục chạm', () => {
    expect(shellCss).toMatch(/\.public-bottom-nav-item\s*\{[^}]*min-height:\s*(?:5[2-9]|[6-9]\d)px/i)
  })

  // ───────────────────────────────────────────────────────────────────────────
  // Nhóm 4: Điều Hướng Bàn Phím Bỏ Qua & Phím Tắt
  // ───────────────────────────────────────────────────────────────────────────
  it('8. default.vue có Skip Link #main-content và main có tabindex="-1"', () => {
    expect(defaultLayout).toMatch(/<a[^>]*href="#main-content"[^>]*class="skip-link"/)
    expect(defaultLayout).toMatch(/<main[^>]*id="main-content"[^>]*tabindex="-1"/)
  })

  it('9. default.vue phím tắt J/K điều hướng đồng bộ tiêu điểm DOM (focus synchrony)', () => {
    expect(defaultLayout).toMatch(/function\s+navigateSection/)
    expect(defaultLayout).toMatch(/\.focus\(\{\s*preventScroll:\s*true\s*\}\)/)
  })

  it('10. default.vue phím tắt / chỉ kích hoạt tìm kiếm khi không focus ô nhập liệu', () => {
    expect(defaultLayout).toMatch(/isEditableFocused/)
    expect(defaultLayout).toMatch(/e\.key\s*===\s*'\/'/)
  })

  it('11. default.vue phím Escape đóng sạch sẽ menu, catalog và search drawer', () => {
    expect(defaultLayout).toMatch(/e\.key\s*===\s*'Escape'/)
    expect(defaultLayout).toMatch(/searchDrawerOpen\.value\s*=\s*false/)
  })

  it('12. Chế độ Kính Lão (Elder Mode) nâng kích thước chạm lên >= 52px theo DESIGN.md §9.1', () => {
    expect(variablesCss).toMatch(/--elder-touch-target:\s*52px/)
  })
})
