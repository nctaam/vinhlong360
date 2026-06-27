# Nghiên cứu Design System — Apple HIG + Material Design 3 + Figma + WCAG 2.2
> Ngày: 2026-06-27 | Cập nhật: Round 3 world-class research | Mục đích: Gap analysis + component specs + world-class patterns → task cho 3 session branches

---

## 1. Tổng quan hệ thống hiện tại (Audit kết quả)

Design system hiện tại **đã đạt S+ tier** với:
- **200+ color tokens** (3-tier: primitive landscape-named → semantic → component)
- **50+ typography tokens** (fluid `clamp()`, per-size line-height/tracking, 8 composite roles)
- **25+ spacing tokens** (8px grid, 2px→96px, semantic aliases)
- **6 radius tokens** (Apple HIG-style, squircle progressive enhancement)
- **15+ shadow tokens** (M3-aligned 8-level + semantic elevation roles)
- **30+ motion tokens** (M3 + Apple easing, 16 duration steps)
- **Full dark mode** (~60 token overrides), **accessibility** (touch targets, focus, contrast, reduced motion)
- **Container queries**, **forced-colors**, **prefers-reduced-motion** support

## 2. Gap Analysis vs. Apple HIG + Material Design 3 + Figma + WCAG 2.2

### 2.1 Những gì ĐÃ ĐÚNG chuẩn

| Nguyên lý | Apple HIG | M3 | Figma | Hiện tại |
|---|---|---|---|---|
| 3-tier token hierarchy | — | ✓ | ✓ | ✓ đầy đủ |
| Semantic color roles | system colors | primary/secondary/tertiary/surface/error | function-based | ✓ M3-aligned |
| Touch target 44px | ✓ (default) | 48dp | — | ✓ `--touch-min: 44px` |
| Color contrast ≥4.5:1 | ✓ WCAG AA | ✓ 3:1 pairs | ✓ | ✓ verified |
| Dark mode parity | ✓ variants | ✓ auto dark | ✓ reassign | ✓ 60+ overrides |
| 8px spacing grid | — | ✓ space100=8dp | ✓ | ✓ `--space-2: 8px` |
| Fluid typography | Dynamic Type | — | — | ✓ `clamp()` scale |
| Reduced motion | ✓ | — | — | ✓ all animations |
| Elevation system | — | ✓ 5 levels | — | ✓ 8 levels + roles |
| M3 easing curves | — | ✓ standard/emphasized | — | ✓ complete |
| Focus-visible | ✓ | ✓ | ✓ | ✓ `--focus-ring` |
| Container queries | — | — | ✓ | ✓ card grids |
| State layers (hover/focus/press) | — | ✓ opacity-based | — | ✓ `::before` |
| Surface container hierarchy | — | ✓ 5 levels | — | ✓ lowest→highest |
| Inverse colors | — | ✓ snackbar/toast | — | ✓ `--inverse-*` |

### 2.2 GAP: Thiếu hoặc cần cải thiện

#### A. Từ Apple HIG

| # | Gap | Mô tả | Mức ưu tiên |
|---|---|---|---|
| A1 | **Increased Contrast mode** | Chưa có `@media (prefers-contrast: more)` riêng | P1 |
| A2 | **Color consistency audit** | Cần xác minh không có màu primary dùng cho cả CTA lẫn decorative | P2 |
| A3 | **Inclusive color indicators** | Badge/status/tag dùng color-only cần thêm icon/pattern | P1 |
| A4 | **Typography hierarchy audit** | Kiểm tra quá nhiều text style trộn lẫn | P2 |
| A5 | **Content-to-edge layout** | Review padding thừa | P2 |
| A6 | **Padding between controls** | ~12pt quanh bezel, ~24pt quanh non-bezel — audit | P2 |
| A7 | **Skeleton loading screens** | Thay spinner "Đang tải..." bằng skeleton >300ms | P1 |
| A8 | **Empty state guidance** | Icon+title+description+CTA cho danh sách trống | P1 |

#### B. Từ Material Design 3

| # | Gap | Mô tả | Mức ưu tiên |
|---|---|---|---|
| B1 | **Outline vs Outline Variant** | Audit usage: outline cho boundaries, outline-variant cho dividers | P1 |
| B2 | **Color roles pairing** | Verify primary↔on-primary, container↔on-container | P1 |
| B3 | **Opacity scale tokens** | Hardcoded `.06-.82` → centralize | P2 |
| B4 | **Border width tokens** | `.5px-3px` hardcoded → `--border-width-*` | P2 |
| B5 | **Elevation hover** | Interactive components tăng 1 level khi hover | P2 |
| B6 | **Typography role mapping** | 8 composite → M3 5-role system | P2 |
| B7 | **Shape radius XXL** | Thiếu `--radius-2xl: 48px` | P3 |
| B8 | **Spacing padding-first** | Audit margin trên child → padding+gap trên parent | P2 |
| B9 | **Dark mode surface tint** | Elevation dùng primary tint overlay (0dp=0%, 1dp=5%, 3dp=8%, 6dp=11%, 12dp=12%, 24dp=15%) | P2 |

#### C. Từ Figma Best Practices

| # | Gap | Mô tả | Mức ưu tiên |
|---|---|---|---|
| C1 | **Component props > class explosion** | Audit Vue components | P2 |
| C2 | **CSS pseudo-classes > class states** | `.is-hover` → `:hover` | P2 |
| C3 | **Token naming alignment** | Document mapping | P3 |
| C4 | **Design system documentation** | Chưa có doc chính thức | P1 |
| C5 | **Print stylesheet** | Không có `@media print` | P3 |

#### D. Từ WCAG 2.2

| # | Gap | Mô tả | Mức ưu tiên |
|---|---|---|---|
| D1 | **Focus Not Obscured (2.4.11)** | Focused element bị ẩn bởi sticky header | P1 |
| D2 | **Target Size (2.5.8)** | Mọi target ≥24×24 CSS px | P1 |
| D3 | **Dragging (2.5.7)** | Drag phải có click alternative | P1 |
| D4 | **Consistent Help (3.2.6)** | Chat/Zalo CTA cùng DOM order | P1 |
| D5 | **Redundant Entry (3.3.7)** | Không nhập lại thông tin đã nhập | P2 |
| D6 | **Accessible Auth (3.3.8)** | OTP hỗ trợ paste + `autocomplete="one-time-code"` | P1 |
| D7 | **Text spacing (1.4.12)** | Tolerate: line-height 1.5×, letter 0.12×, word 0.16× | P2 |
| D8 | **Reflow (1.4.10)** | Không scroll 2D ở 320px | P2 |

#### E. Từ UX Patterns

| # | Gap | Mô tả | Mức ưu tiên |
|---|---|---|---|
| E1 | **Error message placement** | Adjacent to field, 3 signals | P1 |
| E2 | **Form validation timing** | Validate on blur, không mid-typing | P2 |
| E3 | **Loading thresholds** | <100ms none, 300ms skeleton, >10s progress | P2 |
| E4 | **Dark mode link colors** | Default blue chỉ 2.23:1 — re-specify | P1 |
| E5 | **Dark mode font weight** | ≥400 weight, tránh halation | P2 |
| E6 | **Input font-size 16px** | Ngăn iOS auto-zoom | P1 |

### 2.3 Hardcoded values cần extract

| # | Giá trị | Token đề xuất |
|---|---|---|
| H1 | Opacity `.06-.82` | `--opacity-*` scale |
| H2 | Border widths `.5px-3px` | `--border-width-*` |
| H3 | SVG gradient `#586860` | `currentColor` / token |
| H4 | Modal radius `18px` | `--radius-xl` |
| H5 | Scroll-padding `72px` | `var(--header-h)` |
| H6 | Stagger delays `.05s-.15s` | `--reveal-stagger` |

---

## 3. Nguyên lý then chốt (tổng hợp tất cả nguồn)

### 3.1 Color
1. Color roles, không hardcode hex. Pair đúng cặp (M3). Không cùng 1 màu cho 2 nghĩa (HIG).
2. Thông tin không chỉ qua màu — icon/text/shape backup (HIG, WCAG).
3. Test 4 context: light/dark × default/high-contrast.
4. Dark mode link colors PHẢI re-specify.

### 3.2 Typography
1. Min 1-2 font family. Hierarchy qua weight+size+color. Min 14pt body.
2. 5-role mapping: Display→Headline→Title→Body→Label (M3).
3. Dark mode ≥400 weight. Input ≥16px (ngăn iOS zoom).

### 3.3 Layout
1. Content-first, edge-to-edge. Padding parent, không margin child (M3).
2. Container queries cho components. Reflow 320px (WCAG).

### 3.4 Elevation
1. Surface tint > shadow. Hover +1 level. Dark mode = tint overlay.

### 3.5 Motion
1. Emphasized enter, standard exit (M3). Duration: nhỏ→nhanh, lớn→chậm.
2. `prefers-reduced-motion`: tắt hoàn toàn. Spring cho micro-interactions.

### 3.6 Accessibility
1. Touch ≥44px (HIG), WCAG ≥24×24px. Focus-visible rõ ràng.
2. Focus Not Obscured (sticky headers). Dragging alternatives.
3. Accessible auth: OTP paste + autocomplete. Consistent help DOM order.

---

## 4. Component Specs (Round 2)

### 4.1 Nav Bar / Header
- 44px height + safe area. Blur: `saturate(180%) blur(20px)`.
- Light: `rgba(255,255,255,0.92)`, dark: `rgba(29,29,31,0.90)`.
- Hairline 0.5px border (không shadow). Large title: 34px→17px on scroll.
- `scroll-padding-top` = header height.

### 4.2 Bottom Tab Bar
- 56px height, 3-5 tabs. Icon 24px + label (không icon-only mobile).
- Selected: accent fill; unselected: gray outline. Badge: red oval.
- Desktop >768px: sidebar/top nav. ARIA: `role="tab"`, `aria-selected`.

### 4.3 Buttons
- 44×44px tap target. 4 tiers: Plain→Gray→Tinted→Filled.
- M3: Text→Outlined→Tonal→Filled→Elevated. Height 40dp.
- Press: `opacity:0.7` / `scale(0.97)` (HIG), state layer 10% (M3).
- Disabled: container 12%, content 38% (M3).

### 4.4 Cards
- 12-16px radius squircle. 3 variants: Elevated/Filled/Outlined (M3).
- Hover: shadow increase + `scale(1.01)`.
- Grid: `repeat(auto-fill, minmax(15em, 1fr))`.

### 4.5 Text Fields
- Height 44px (HIG) / 56dp (M3). Font ≥16px.
- Label ALWAYS visible above. Validate on blur.
- Error: below field, red outline+text+icon. `aria-invalid`.
- `autocomplete`: name, email, tel, one-time-code.

### 4.6 Dialogs / Sheets
- Scrim: `rgba(0,0,0,0.4)`. Corner radius 28dp (M3) / 10px top (HIG).
- `<dialog>` + `::backdrop`. Focus trap. Escape = dismiss.
- ARIA: `role="dialog"`, `aria-modal="true"`.

### 4.7 Search
- 36px visual, 44px tap. 10px radius. Debounce 300ms.
- Magnifier icon, clear X khi có text. Inline results.
- `role="searchbox"`, `aria-label`. Suggestions: `role="listbox"`.

### 4.8 Lists
- Row 44px (HIG) / 56-88dp (M3). Separator inset.
- M3 states: hover 8%, focus 10%, press 10%, drag 16%.

### 4.9 Loading
- <100ms: none. 300ms-1s: skeleton. >10s: progress bar.
- Skeleton: match layout, shimmer 1.5s. `aria-busy="true"`.

### 4.10 Empty States
- Icon (48-64px) + Title (20px) + Description + CTA button.
- CTA cụ thể ("Duyệt địa điểm" không "Bắt đầu").

### 4.11 Snackbar / Toast
- Inverse colors: container `inverse-surface`, text `inverse-on-surface`.
- 48dp single-line, 68dp two-line. 4-10s auto-dismiss.
- Action snackbar KHÔNG auto-dismiss. `aria-live="polite"`.

### 4.12 Chips
- 32dp height, 8dp radius, icon 18dp. 4 types: Assist/Filter/Input/Suggestion.
- Min chip width 88dp cho trailing icon 48×48 target.

### 4.13 Badges
- Small: 6dp circle. Large: 16dp height, max "999+".
- Color: error/on-error. Contrast ≥3:1.

---

## 5. WCAG 2.2 AA Quick Reference

| Tiêu chí | Level | Ngưỡng | Áp dụng |
|---|---|---|---|
| 2.4.11 Focus Not Obscured | AA | Không ẩn hoàn toàn | Sticky header + chat widget |
| 2.5.7 Dragging | AA | Click alternative | Map pan, itinerary reorder |
| 2.5.8 Target Size | AA | ≥24×24 CSS px | Icon buttons nhỏ |
| 3.2.6 Consistent Help | A | Cùng DOM order | Chat + Zalo CTA |
| 3.3.7 Redundant Entry | A | Không nhập lại | Multi-step forms |
| 3.3.8 Accessible Auth | AA | Paste + autofill | OTP input |

**Ngưỡng số kế thừa:** Text 4.5:1, non-text 3:1, target 24px, reflow 320px, text spacing (line 1.5×, paragraph 2×, letter 0.12×, word 0.16×).

---

## 6. M3 Motion Token Reference

### Easing
| Token | cubic-bezier | Dùng khi |
|---|---|---|
| standard | `(0.2, 0, 0, 1)` | On-screen transitions |
| standard.decelerate | `(0, 0, 0, 1)` | Entering |
| standard.accelerate | `(0.3, 0, 1, 1)` | Exiting |
| emphasized.decelerate | `(0.05, 0.7, 0.1, 1)` | Enter expressive |
| emphasized.accelerate | `(0.3, 0, 0.8, 0.15)` | Exit expressive |

### Duration
| short1-4 | 50, 100, 150, 200ms | Micro: checkbox, toggle |
|---|---|---|
| medium1-4 | 250, 300, 350, 400ms | Card expand, nav drawer |
| long1-4 | 450, 500, 550, 600ms | Full-screen, hero |
| xlong1-4 | 700, 800, 900, 1000ms | Complex orchestration |

### M3 State Layer Opacity
| State | Opacity |
|---|---|
| Hover | 8% (0.08) |
| Focus | 10% (0.10) |
| Press | 10% (0.10) |
| Drag | 16% (0.16) |
| Disabled container | 12% (0.12) |
| Disabled content | 38% (0.38) |

---

## 7. Dark Mode Reference

### Apple HIG Semantic Colors
| Token | Light | Dark |
|---|---|---|
| systemBackground | `#FFFFFF` | `#000000` |
| secondarySystemBg | `#F2F2F7` | `#1C1C1E` |
| tertiarySystemBg | `#FFFFFF` | `#2C2C2E` |

Dark tint: blue `#0A84FF`, green `#30D158`, red `#FF453A`, orange `#FF9F0A`.

### Rules
1. Background: `#121212` (M3) / `#1C1C1E` (HIG). KHÔNG `#000000`.
2. Text: off-white `#EEEEEE`. Weight ≥400.
3. Accent: desaturate (tone ~80 vs ~40 light).
4. Images: `filter: brightness(0.8) contrast(1.2)`. SVG: `currentColor`.
5. Elevation = surface tint. Link colors PHẢI re-specify.
6. `<meta name="color-scheme" content="dark light">`.

### Materials (Apple)
- Nav bar: `blur(20px) saturate(180%)`, light 92% / dark 86-90%.
- Fallback: `@supports not (backdrop-filter)` → solid.
- `@media (prefers-reduced-transparency: reduce)` → opaque.

---

## 8. Responsive Design Reference

### Breakpoints
- Content-based: ~30em / ~44em / ~66em. Container queries cho components.
- M3: <600dp compact, 600-839dp medium, 840-1199dp expanded, ≥1200dp large.

### Navigation per Viewport
- Mobile (<44em): bottom tab 3-5 items.
- Tablet (44-66em): rail hoặc collapsible sidebar.
- Desktop (>66em): persistent sidebar hoặc horizontal nav.

### Images
- `max-inline-size: 100%; block-size: auto`. Width/height attrs (ngăn CLS).
- `loading="lazy"` below-fold. `srcset` w-descriptors.

### Reading Width
- `max-inline-size: 66ch` cho text dài.
- Card grids: `repeat(auto-fill, minmax(15em, 1fr))`.

---

## 9. Form Design Reference

### Input Sizing
- Font ≥16px (iOS zoom). Height ≥48px touch.
- `@media (pointer: coarse)` → enlarge checkbox 30px.

### Validation
- Label ABOVE field. Validate on blur. Error below field 3 signals.
- `enterkeyhint="next"` trừ field cuối (`"done"`).

### Vietnamese-specific
- `type="tel"` cho SĐT, cho phép `+84`.
- OTP: `inputmode="numeric"` + `autocomplete="one-time-code"` + paste.
- KHÔNG `type="number"` cho OTP. Unicode names: cho phép dấu.

---

## 10. Community/Social UX Reference

- 90% lurk, 9% contribute, 1% drives — thiết kế cho pattern này.
- Giảm friction: star/rating simple hơn essay. Templates > blank slate.
- Recognition qua badges, NOT cash. Highlight quality over volume.

---

## 11. Content Design Reference (M3)

### UX Writing
- Sentence case everywhere. Explain consequences neutrally.
- Skip periods on single sentences. Use contractions.
- Avoid abbreviations, idioms. Spell out for global audiences.

### Notifications
- Title <29 chars, collapsed body <40, expanded <80.
- Day-specific (không "hôm nay"/"ngày mai"). Không name product twice.

---

## 12. Phân chia task cho 3 session branches (EXPANDED)

### SESSION-FE (Frontend) — 20 tasks

| ID | Task | Gap | P |
|---|---|---|---|
| DS-FE-1 | `prefers-contrast: more` support | A1 | P1 |
| DS-FE-2 | Inclusive color indicators audit | A3 | P1 |
| DS-FE-3 | Opacity scale tokens | B3,H1 | P2 |
| DS-FE-4 | Border width tokens | B4,H2 | P2 |
| DS-FE-5 | Outline usage audit | B1 | P1 |
| DS-FE-6 | Color role pairing audit | B2 | P1 |
| DS-FE-7 | Elevation hover consistency | B5 | P2 |
| DS-FE-8 | Typography role mapping | B6 | P2 |
| DS-FE-9 | SVG hardcoded colors | H3 | P3 |
| DS-FE-10 | Spacing parent-first audit | B8 | P2 |
| DS-FE-11 | Pseudo-class audit | C2 | P2 |
| DS-FE-12 | Shape radius XXL | B7 | P3 |
| DS-FE-13 | **Skeleton loading** — thay spinner, shimmer 1.5s, `aria-busy` | A7,E3 | P1 |
| DS-FE-14 | **Empty states redesign** — icon+title+desc+CTA pattern | A8 | P1 |
| DS-FE-15 | **Focus not obscured** — `scroll-padding-top: var(--header-h)` | D1 | P1 |
| DS-FE-16 | **Dark mode link/font audit** — re-specify links, weight ≥400 | E4,E5 | P1 |
| DS-FE-17 | **Input font-size 16px** — ngăn iOS zoom | E6 | P1 |
| DS-FE-18 | **Dark mode surface tint** — elevation dùng primary tint | B9 | P2 |
| DS-FE-19 | **Error message UX** — adjacent + 3 signals + preserve input | E1 | P1 |
| DS-FE-20 | **Target size WCAG 2.2** — audit ≥24×24px + spacing | D2 | P1 |

### SESSION-BE (Backend) — 7 tasks

| ID | Task | Gap | P |
|---|---|---|---|
| DS-BE-1 | Image alt text enforcement | A3 | P2 |
| DS-BE-2 | Accessibility metadata API | A1 | P3 |
| DS-BE-3 | Contrast validation script | A1 | P2 |
| DS-BE-4 | OG image typography tokens | B6 | P3 |
| DS-BE-5 | **OTP autocomplete support** — verify paste + `autocomplete` | D6 | P1 |
| DS-BE-6 | **Consistent help placement** — Chat/Zalo cùng DOM order | D4 | P1 |
| DS-BE-7 | **Drag alternatives** — map pan, itinerary reorder buttons | D3 | P1 |

### SESSION-CONTENT (Docs/Scripts/Tests) — 9 tasks

| ID | Task | Gap | P |
|---|---|---|---|
| DS-QA-1 | Design system docs | C4 | P1 |
| DS-QA-2 | Accessibility checklist (WCAG 2.2 AA) | A1-A6,D1-D8 | P1 |
| DS-QA-3 | Color pairing test script | B2 | P2 |
| DS-QA-4 | Token inventory test | H1-H6 | P2 |
| DS-QA-5 | Print stylesheet | C5 | P3 |
| DS-QA-6 | **WCAG 2.2 audit script** | D1-D8 | P1 |
| DS-QA-7 | **Component spec reference doc** | §4 | P2 |
| DS-QA-8 | **Text spacing tolerance test** | D7 | P2 |
| DS-QA-9 | **Dark mode checklist doc** | §7 | P2 |

---

## 13. Thứ tự thực hiện

**Wave 1 — P1 Critical:**
- FE: 1,2,5,6,13,14,15,16,17,19,20 (11 tasks)
- BE: 5,6,7 (3 tasks)
- QA: 1,2,6 (3 tasks)

**Wave 2 — P2 Polish:**
- FE: 3,4,7,8,10,11,18 (7 tasks)
- BE: 1,3 (2 tasks)
- QA: 3,4,7,8,9 (5 tasks)

**Wave 3 — P3 Nice-to-have:**
- FE: 9,12 (2 tasks)
- BE: 2,4 (2 tasks)
- QA: 5 (1 task)

---

# ROUND 3: World-Class Design Patterns

> Nghiên cứu sâu 8 chiều nâng hệ thống từ "đạt chuẩn" lên "world-class". ~80 agent song song phân tích design systems hàng đầu, CSS performance, font loading, cognitive accessibility, SEO structured data, micro-interactions.

---

## 14. World-Class Design System Patterns

### 14.1 Shopify Polaris — Dual-mode Architecture

**Token naming:** `--p-{group}-{subgroup}-{variant}-{state}` (2-tier: primitive → semantic).

**Color space:** HSLuv (perceptually uniform) cho toàn bộ palette. 5 theme variants: light, dark, dim, light-high-contrast, dark-high-contrast. Class-based switching (`[data-theme="dark"]`).

**Dual-mode pattern:** Open internals cho team + locked-down public API cho 3rd-party apps. Đây là mô hình phù hợp vinhlong360 nếu sau này mở API cho đối tác OCOP.

**Áp dụng cho vinhlong360:**
- Adopt HSLuv / OKLCH cho color generation → đảm bảo perceptual uniformity across palette
- 5 theme variants (hiện có 2: light/dark) → thêm dim + 2 high-contrast
- Token naming convention `--vl-{group}-{variant}-{state}` nhất quán hơn

### 14.2 Vercel Geist — AI-Native Design System

**design.md as machine-readable contract:** Geist duy trì 1 file `design.md` tại URL ổn định — AI/LLM đọc được, developer đọc được. Đây là pattern mới: design system documentation vừa cho người vừa cho máy.

**Typography-first:** Geist Sans / Mono / Pixel. Letter-spacing tightens theo size: `-2.88px` ở 48px → `0` ở 16px. Dark-first canonical surface.

**Ink-as-brand:** `#171717` là brand color, KHÔNG dùng brand color truyền thống. Shadow-as-border pattern (shadows thay border cho elevation).

**10-step color scales:** 100→1000 (thay 50→900 truyền thống). Semantic rõ: 100=app bg, 900=solid fill, 1000=primary text.

**Áp dụng cho vinhlong360:**
- Tạo `docs/design.md` machine-readable (AI/LLM-friendly) — useful cho agent nội bộ
- Letter-spacing tightens theo size (hiện cố định) → fluid tracking
- Shadow-as-border cho cards (giảm visual noise)

### 14.3 Linear — Performance-First Design

**Local-first sync:** IndexedDB → MobX → UI. Server chỉ là sync target, không phải source. App hoạt động offline.

**Animation rules cứng:**
- CHỈ animate `transform` + `opacity` (composited, không trigger layout/paint)
- Asymmetric timing: instant appear (0ms), 150ms fade-out
- Duration scale: 0.1s / 0.15s / 0.25s / 0.35s (rất ngắn — feels snappy)
- MobX per-property subscriptions (chỉ re-render component khi đúng property thay đổi)

**Code splitting:** 21MB JS split trăm chunks, per-package chunking (>3KB = chunk riêng). Service worker precache ~1200 assets.

**Áp dụng cho vinhlong360:**
- Adopt animation rules: chỉ `transform` + `opacity`, asymmetric timing
- Duration scale ngắn hơn hiện tại: 100/150/250/350ms thay 200-1000ms
- Service worker precache cho static assets (Nuxt built-in)

### 14.4 Radix UI — Composition + Accessibility

**`data-state` unmount suspension:** Khi element exit, Radix giữ nó trong DOM với `data-state="closed"` → CSS transition chạy xong → unmount. Pattern này cho phép CSS-only exit animations KHÔNG cần JS animation library.

```css
/* Pattern: CSS-only exit animation */
[data-state="open"] { animation: slideIn 150ms ease-out; }
[data-state="closed"] { animation: slideOut 100ms ease-in; }
```

**`asChild` / `Slot` composition:** Thay vì wrapper `<div>`, Radix merge props vào child element qua `React.cloneElement`. Kết quả: DOM sạch hơn, accessibility attributes truyền trực tiếp.

**12-step color scale:**
| Step | Semantic | Ví dụ |
|---|---|---|
| 1 | App background | page bg |
| 2 | Subtle background | card bg |
| 3-5 | Component bg (default → hover → active) | button states |
| 6-7 | Border (subtle → strong) | input border |
| 8 | Solid bg | focus ring |
| 9 | Solid bg (primary) | primary button |
| 10 | Hovered solid | button:hover |
| 11 | Low-contrast text | secondary text |
| 12 | High-contrast text | primary text |

**Áp dụng cho vinhlong360:**
- `data-state` pattern cho modals/drawers/dropdowns (Vue `<Transition>` tương đương)
- 12-step color scale mapping: verify tokens hiện tại cover steps 1-12
- Bake WAI-ARIA patterns vào base components

### 14.5 cmdk — Command Palette Architecture

**Linear's foundation:** Composable unstyled command palette. `useSyncExternalStore` store pattern. Items stay in React tree when filtered (hidden, not unmounted — preserves focus).

**Fuzzy scoring:** `command-score` library. Good up to 2-3K items without virtualization.

**Áp dụng cho vinhlong360:**
- Admin command palette (Ctrl+K) — plan B8a đã có, dùng pattern cmdk
- Entity search: fuzzy scoring thay exact match
- Keep items in DOM (hidden) thay unmount khi filter → faster re-show

---

## 15. CSS Performance Optimization

### 15.1 CSS Custom Properties — Benchmark Data

| Technique | Before | After | Improvement |
|---|---|---|---|
| `@property` with `inherits: false` | 3.90ms per update | 4.67μs | **848× faster** |
| Registering 25k properties | — | ~32ms one-time | Negligible cost |
| 200+ tokens on `:root` | — | No perf issue | Safe to scale |

**`@property` with `inherits: false`** ngăn trình duyệt recalculate toàn bộ subtree khi custom property thay đổi. Thay vì cascade xuống mọi descendant, chỉ element trực tiếp bị ảnh hưởng.

```css
/* Đăng ký property — 848× faster khi thay đổi */
@property --vl-primary {
  syntax: '<color>';
  inherits: false;
  initial-value: #2d5016;
}
```

**Áp dụng:** Đăng ký tất cả component-level tokens với `inherits: false`. Semantic tokens (cần cascade cho dark mode) giữ `inherits: true`.

### 15.2 CSS Containment — Real-World Benchmarks

| Site | Technique | Before | After | Improvement |
|---|---|---|---|---|
| OpenTable | `contain: content` on cards | 11.21ms layout | 1.89ms | **6× faster** |
| Generic | `content-visibility: auto` | 232ms render | 30ms | **7× faster** |

**`contain: content`** (= `contain: layout paint style`) là safe default cho cards. Nó nói trình duyệt: "nội dung bên trong không ảnh hưởng layout bên ngoài" → skip recalc siblings.

**`content-visibility: auto`** cho off-screen content: trình duyệt skip rendering hoàn toàn, chỉ render khi scroll vào viewport. Cần `contain-intrinsic-size` để tránh scroll jumps.

```css
/* Card containment — 6× layout speed */
.entity-card {
  contain: content;
}

/* Off-screen skip — 7× rendering speed */
.entity-list-item {
  content-visibility: auto;
  contain-intrinsic-size: auto 200px;
}
```

**Cảnh báo:** `contain: paint` clips overflow — break tooltips, dropdowns. Dùng `contain: content` (không có `size`) cho cards.

### 15.3 CSS Nesting & @layer

**CSS Nesting:** Zero perf difference — trình duyệt desugar thành flat selectors trước khi matching (confirmed cả WebKit lẫn Blink). Dùng nesting cho readability, không phải perf.

**CSS @layer:** Maintainability win (giảm `!important`), không phải perf win. Không benchmark nào isolate `!important` là perf variable.

```css
/* Layer architecture cho vinhlong360 */
@layer reset, tokens, base, components, utilities, overrides;
```

**Áp dụng:** Adopt `@layer` cho token cascade clarity. 6 layers: reset → tokens → base → components → utilities → overrides.

---

## 16. Font Loading Excellence

### 16.1 Strategy: swap + metric overrides

**Mobile:** `font-display: swap` + font metric overrides → zero CLS.
**Desktop:** `font-display: optional` + `<link rel="preload">` → no FOUT.

**Font metric overrides** (CSS) tạo fallback font dimensions khớp chính xác custom font:

```css
@font-face {
  font-family: 'Inter Fallback';
  src: local('Arial');
  size-adjust: 107.64%;
  ascent-override: 90.49%;
  descent-override: 22.56%;
  line-gap-override: 0%;
}
```

**Kết quả:** CLS từ 0.1+ → effectively 0. Duda platform: **30% CLS improvement** across 1M+ sites.

### 16.2 Safari Compatibility

Safari **KHÔNG** support `ascent-override`, `descent-override`, `line-gap-override` (chỉ `size-adjust` từ Safari 17+). Fallback: chấp nhận minor CLS trên Safari, hoặc dùng JS-based approach.

### 16.3 Nuxt Integration

**`@nuxtjs/fontaine`** — auto-generates override CSS cho Nuxt. Zero config:

```js
// nuxt.config.ts
export default defineNuxtConfig({
  modules: ['@nuxtjs/fontaine'],
  // Tự động tạo fallback @font-face với metric overrides
})
```

**Áp dụng:** Install `@nuxtjs/fontaine` → CLS improvement tự động, không cần manual metric calculation.

---

## 17. Advanced Accessibility — WCAG AAA Cognitive

### 17.1 Link Purpose — Link Only (2.4.9 AAA)

Mỗi link text phải tự giải thích, KHÔNG cần context xung quanh. "Xem thêm" / "Chi tiết" fail.

**Patterns:**
```html
<!-- FAIL (AAA) -->
<a href="/dia-diem/cho-noi">Xem thêm</a>

<!-- PASS (AAA) — visually hidden text -->
<a href="/dia-diem/cho-noi">
  Xem thêm <span class="sr-only">về Chợ Nổi Cái Bè</span>
</a>

<!-- PASS (AAA) — aria-label -->
<a href="/dia-diem/cho-noi" aria-label="Xem thêm về Chợ Nổi Cái Bè">
  Xem thêm
</a>
```

### 17.2 Reading Level (3.1.5 AAA)

Nội dung vượt trình độ THCS (lớp 9) cần phiên bản đơn giản hóa.

**Thách thức tiếng Việt:** Không có công thức readability chuẩn (Flesch-Kincaid dựa syllable, không áp dụng cho tiếng Việt đơn âm). Thay vào đó, đánh giá theo:
- Chiều dài câu (>20 từ = phức tạp)
- Mật độ từ Hán-Việt (cao = khó đọc)
- Cấu trúc câu (mệnh đề phụ lồng nhau = khó đọc)

**Áp dụng:** Summary entities / điểm đến dùng câu ngắn (<15 từ), ít từ Hán-Việt, cấu trúc chủ-vị-bổ đơn giản. Nội dung chuyên sâu (lịch sử, pháp lý) thêm `<details>` "Giải thích đơn giản".

---

## 18. SEO Structured Data for Tourism

### 18.1 Schema.org — Event/Festival

**Lưu ý:** `FAQPage` rich results **deprecated bởi Google tháng 5/2026**. Vẫn valid cho Bing/AI nhưng không hiện rich snippet trên Google Search nữa.

```json
{
  "@context": "https://schema.org",
  "@type": "Festival",
  "name": "Lễ hội Trái cây Vĩnh Long",
  "startDate": "2026-06-01",
  "endDate": "2026-06-05",
  "location": {
    "@type": "Place",
    "name": "Công viên Tượng đài Chiến thắng",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "Vĩnh Long",
      "addressRegion": "Vĩnh Long",
      "addressCountry": "VN"
    },
    "geo": {
      "@type": "GeoCoordinates",
      "latitude": 10.2539,
      "longitude": 105.9572
    }
  },
  "description": "Lễ hội trái cây thường niên...",
  "organizer": {
    "@type": "Organization",
    "name": "UBND tỉnh Vĩnh Long"
  }
}
```

### 18.2 Place + GeoCoordinates + containedInPlace

```json
{
  "@context": "https://schema.org",
  "@type": "TouristAttraction",
  "name": "Chợ Nổi Cái Bè",
  "description": "Chợ nổi truyền thống trên sông...",
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 10.3731,
    "longitude": 106.0089
  },
  "containedInPlace": {
    "@type": "AdministrativeArea",
    "name": "Huyện Cái Bè",
    "containedInPlace": {
      "@type": "AdministrativeArea",
      "name": "Tỉnh Vĩnh Long"
    }
  },
  "image": "https://vinhlong360.vn/images/cho-noi-cai-be.webp",
  "isAccessibleForFree": true
}
```

### 18.3 Event Subtypes phù hợp

| Subtype | Dùng cho |
|---|---|
| `Festival` | Lễ hội trái cây, Vía Bà, đua ghe |
| `FoodEvent` | Hội chợ ẩm thực, food tour |
| `ExhibitionEvent` | Triển lãm gốm, OCOP fair |
| `Event` (generic) | Hội thảo du lịch, ra mắt sản phẩm |

**Áp dụng:** Auto-generate JSON-LD từ entity data trong Nuxt `useHead()`. `containedInPlace` hierarchy cho SEO địa phương. Tất cả events có `startDate` + `location` + `geo`.

---

## 19. Micro-Interaction Patterns

### 19.1 Animation Rules (từ Linear)

```css
/* CHỈ animate composited properties */
.card-enter { 
  animation: fadeSlideIn 150ms var(--ease-decelerate) forwards; 
}
.card-exit { 
  animation: fadeOut 100ms var(--ease-accelerate) forwards; 
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeOut {
  from { opacity: 1; }
  to   { opacity: 0; }
}
```

**Rules:**
1. Chỉ `transform` + `opacity` — never `width`, `height`, `top`, `left`, `margin`, `padding`
2. Enter chậm hơn exit (150ms vs 100ms) — asymmetric timing
3. Enter = decelerate, Exit = accelerate
4. `prefers-reduced-motion: reduce` → tắt hoàn toàn, không giảm

### 19.2 State Transition Pattern (từ Radix)

```css
/* data-state pattern cho Vue Transition */
.modal[data-state="open"] {
  animation: dialogIn 200ms var(--ease-emphasized-decelerate);
}
.modal[data-state="closed"] {
  animation: dialogOut 150ms var(--ease-emphasized-accelerate);
}

/* Scrim */
.scrim[data-state="open"]   { animation: fadeIn 200ms ease-out; }
.scrim[data-state="closed"] { animation: fadeOut 150ms ease-in; }
```

### 19.3 Hover Feedback

```css
/* Card hover — subtle elevation + scale */
.entity-card {
  transition: box-shadow 200ms var(--ease-standard),
              transform 200ms var(--ease-standard);
}
.entity-card:hover {
  box-shadow: var(--shadow-3); /* +1 level */
  transform: scale(1.01);
}

/* Button press — instant feedback */
.btn:active {
  transform: scale(0.97);
  transition-duration: 50ms;
}
```

### 19.4 Scroll-triggered Reveals

```css
/* Intersection Observer + CSS */
.reveal {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 300ms var(--ease-decelerate),
              transform 300ms var(--ease-decelerate);
}
.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Stagger children */
.reveal-group > .reveal:nth-child(1) { transition-delay: 0ms; }
.reveal-group > .reveal:nth-child(2) { transition-delay: 50ms; }
.reveal-group > .reveal:nth-child(3) { transition-delay: 100ms; }
```

---

## 20. Implementation: Round 3 Tasks

### NEW-FE — Frontend (Round 3)

| ID | Task | Source | P |
|---|---|---|---|
| R3-FE-1 | **CSS containment** — `contain: content` cho cards, `content-visibility: auto` cho lists | §15.2 | P1 |
| R3-FE-2 | **@property registration** — component tokens `inherits: false` | §15.1 | P2 |
| R3-FE-3 | **@layer architecture** — 6 layers: reset→tokens→base→components→utilities→overrides | §15.3 | P2 |
| R3-FE-4 | **Font loading** — install `@nuxtjs/fontaine`, verify CLS=0 | §16 | P1 |
| R3-FE-5 | **Asymmetric animation timing** — enter 150ms/exit 100ms, decelerate/accelerate | §19.1 | P2 |
| R3-FE-6 | **data-state transitions** — modals/drawers dùng `data-state` pattern | §19.2 | P2 |
| R3-FE-7 | **Scroll-triggered reveals** — IntersectionObserver + stagger | §19.4 | P3 |
| R3-FE-8 | **Shadow-as-border** — cards dùng shadow thay border (Geist pattern) | §14.2 | P3 |
| R3-FE-9 | **Fluid letter-spacing** — tightens theo font-size (Geist pattern) | §14.2 | P2 |
| R3-FE-10 | **Link text AAA** — audit "Xem thêm" → contextual sr-only text | §17.1 | P2 |

### NEW-BE — Backend (Round 3)

| ID | Task | Source | P |
|---|---|---|---|
| R3-BE-1 | **JSON-LD structured data** — auto-generate TouristAttraction/Festival/Event | §18 | P1 |
| R3-BE-2 | **containedInPlace hierarchy** — entity→district→province nesting | §18.2 | P1 |
| R3-BE-3 | **design.md machine-readable** — AI-native design documentation | §14.2 | P3 |

### NEW-QA — Content/Docs (Round 3)

| ID | Task | Source | P |
|---|---|---|---|
| R3-QA-1 | **Reading level guidelines** — câu <15 từ, ít Hán-Việt, cấu trúc đơn | §17.2 | P2 |
| R3-QA-2 | **Cognitive accessibility checklist** — Vietnamese-specific patterns | §17 | P2 |
| R3-QA-3 | **CSS performance benchmark script** — verify containment + font CLS | §15-16 | P2 |

---

## 21. Tổng hợp: Thứ tự thực hiện toàn bộ (Round 1-2-3)

**Wave 1 — P1 Critical (Round 1-2 + Round 3):**
- FE: DS-FE-1,2,5,6,13,14,15,16,17,19,20 + **R3-FE-1,4** (13 tasks)
- BE: DS-BE-5,6,7 + **R3-BE-1,2** (5 tasks)
- QA: DS-QA-1,2,6 (3 tasks)

**Wave 2 — P2 Polish (Round 1-2 + Round 3):**
- FE: DS-FE-3,4,7,8,10,11,18 + **R3-FE-2,3,5,6,9,10** (13 tasks)
- BE: DS-BE-1,3 (2 tasks)
- QA: DS-QA-3,4,7,8,9 + **R3-QA-1,2,3** (8 tasks)

**Wave 3 — P3 Nice-to-have (Round 1-2 + Round 3):**
- FE: DS-FE-9,12 + **R3-FE-7,8** (4 tasks)
- BE: DS-BE-2,4 + **R3-BE-3** (3 tasks)
- QA: DS-QA-5 (1 task)
