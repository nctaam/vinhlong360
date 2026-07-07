# Nghiên cứu Design System — Apple HIG + Material Design 3 + Figma + WCAG 2.2

> **STATUS (2026-07-07): ARCHIVED — Tài liệu LỊCH SỬ đã archive (truth-sync 2026-07-07). KHÔNG làm theo chỉ dẫn trong file này — đối chiếu CLAUDE.md + docs/README.md.**
> Nghiên cứu lịch sử: measurements/component-spec còn tham khảo được, NHƯNG chỉ đạo 53-task wave + §18.3 migrate palette XANH LÁ đã obsolete (bản sắc clay-primary đã ship). Không thực thi task từ file này.

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

# ROUND 3: World-Class Design Patterns (Nghiên cứu lại đầy đủ)

> 120+ agent song song, 8 chiều nghiên cứu. Tất cả mảng bị dừng giữa chừng ở lần trước đã nghiên cứu lại thành công.

---

## 14. World-Class Design System Patterns (6 hệ thống)

### 14.1 Shopify Polaris — Dual-mode + HSLuv

- Token naming: `--p-{group}-{subgroup}-{variant}-{state}`. 2-tier: primitive → semantic
- Color space: HSLuv (perceptually uniform). 5 theme variants: light, dark, dim, light-HC, dark-HC
- Class-based switching (`[data-theme="dark"]`). Dual-mode: open internals + locked-down public API

### 14.2 Vercel Geist — AI-Native + Typography-First

- `design.md` at stable URL — machine-readable design contract cho AI/LLM
- Letter-spacing tightens theo size: `-2.88px` ở 48px → `0` ở 16px
- Ink-as-brand (`#171717`). Shadow-as-border pattern (shadow thay border)
- 10-step color scales (100→1000). 100=app bg, 900=solid fill, 1000=text

### 14.3 Linear — Performance-First Animation

- CHỈ animate `transform` + `opacity` (compositor-only, skip layout/paint)
- Asymmetric timing: enter 150ms decelerate, exit 100ms accelerate
- Duration scale: 100 / 150 / 250 / 350ms (cực ngắn → snappy feel)
- Code split 21MB → trăm chunks (>3KB = chunk riêng). SW precache ~1200 assets

### 14.4 Radix UI — Composition + Accessibility

- `data-state` unmount suspension: CSS-only exit animations KHÔNG cần JS library
- 12-step color scale: 1=app bg, 2=subtle bg, 3-5=component states, 6-7=borders, 8=focus, 9=primary solid, 10=hover solid, 11=secondary text, 12=primary text
- `asChild`/`Slot` composition: merge props vào child, DOM sạch hơn

### 14.5 GitHub Primer — Inverted Scale + 9 Themes (MỚI)

**Pattern quan trọng nhất:** Neutral scale 14 bước (0-13) **đảo chiều** giữa light/dark. Light: 0=trắng→13=đen. Dark: 0=đen→13=trắng. Functional tokens (`bgColor-default`, `fgColor-muted`) reference cùng step number → tự động đúng ở cả 2 mode. KHÔNG cần viết override riêng. **Không design system nào khác làm được.**

**9 production themes:** light, dark, dark-dimmed, light-HC, dark-HC, light-protanopia/deuteranopia, dark-protanopia/deuteranopia, light-tritanopia, dark-tritanopia. Override pattern: theme mới = diff file chỉ ghi những gì khác.

**3-tier tokens:**
1. **Base** — raw values (`--base-size-4`, `--base-color-green-5`). Không dùng trực tiếp
2. **Functional** — semantic (`--bgColor-default`, `--fgColor-muted`, `--borderColor-default`)
3. **Component** — scoped (`--button-primary-bgColor-hover`)

**Zoning neutral scale:** steps 0-5 = backgrounds, 7-8 = borders (đảm bảo contrast vs bg), 9-10 = text/icons

**Primer Prism** — tool tạo theme dùng HSLuv, auto-check WCAG contrast mọi cặp. Open source.

**Accessibility Annotation Toolkit** — Figma library cho designer annotate heading hierarchy, keyboard flow, ARIA trước khi code. GitHub data: **48% accessibility issues phòng ngừa được ở phase design.**

**Data-attribute theming:** `[data-color-mode="dark"]` thay `.dark-mode`. Hỗ trợ nested themes (dark sidebar trong light page).

**Contrast CI:** GitHub Action chạy mỗi PR, check contrast tất cả token pairings × 9 themes. Fail = block merge.

**Code-first workflow:** Components originate trong Storybook → sync sang Figma qua `story.to.design` plugin.

### 14.6 cmdk — Command Palette

- Composable unstyled, `command-score` fuzzy scoring, 2-3K items không cần virtualize
- Items hidden (không unmount) khi filter → faster re-show, preserve focus

**Áp dụng cho vinhlong360:**
- **Inverted neutral scale** (Primer) — giảm ~50% token overrides cho dark mode
- **Data-attribute theming** — `[data-color-mode]` thay class
- **Contrast CI** — script check token pairs mỗi commit
- **Animation rules Linear** — chỉ `transform`+`opacity`, 100-350ms
- **Shadow-as-border** (Geist) — cards dùng shadow thay border
- **Fluid letter-spacing** (Geist) — tightens theo font-size
- **`data-state` transitions** (Radix) — CSS-only modal/drawer exit

---

## 15. CSS Performance Optimization

### 15.1 CSS Custom Properties

| Technique | Improvement |
|---|---|
| `@property` with `inherits: false` | **848× faster** (3.90ms → 4.67μs per update) |
| 200+ tokens on `:root` | No perf issue — safe to scale |

```css
@property --vl-primary {
  syntax: '<color>';
  inherits: false;
  initial-value: #2d5016;
}
```

### 15.2 CSS Containment

| Site | Technique | Improvement |
|---|---|---|
| OpenTable | `contain: content` on cards | **6× faster** layout (11.21→1.89ms) |
| Generic | `content-visibility: auto` | **7× faster** render (232→30ms) |

```css
.entity-card { contain: content; }
.entity-list-item { content-visibility: auto; contain-intrinsic-size: auto 200px; }
```

Cảnh báo: `contain: paint` clips overflow (break tooltips). Dùng `contain: content`.

### 15.3 Rendering Pipeline (MỚI)

**Compositor-only properties** (skip layout AND paint): `transform`, `opacity`. 
`filter`, `backdrop-filter` chạy trên compositor CHỈ khi element đã composited.

**Layout/paint triggers:** `width/height/margin/padding` = layout+paint. `background-color`, `box-shadow` = paint only.

**GPU layer memory:** Mỗi layer = width × height × 4 bytes. 800×600 element = ~1.9MB. Mobile GPU budget ~200-300MB.

**box-shadow animation trick:**
```css
/* CHẬM: animate box-shadow (paint mỗi frame) */
.card:hover { box-shadow: 0 5px 15px rgba(0,0,0,.3); }

/* NHANH: animate opacity pseudo-element (compositor-only) */
.card::after {
  content: ''; position: absolute; inset: 0; border-radius: inherit;
  box-shadow: 0 5px 15px rgba(0,0,0,.3);
  opacity: 0; transition: opacity .3s;
}
.card:hover::after { opacity: 1; }
```

### 15.4 CSS @layer

```css
@layer reset, tokens, base, components, utilities, overrides;
```

Maintainability win (giảm `!important`), không phải perf win.

---

## 16. Core Web Vitals — INP + LCP (MỚI)

### 16.1 INP (Interaction to Next Paint)

**Ngưỡng:** Good ≤200ms | Needs improvement 200-500ms | Poor >500ms (thay FID từ 03/2024).

**Case studies:**
| Site | Before | After | Business Impact |
|---|---|---|---|
| QuintoAndar | 1,006ms | 216ms (-80%) | +36% conversions |
| Economic Times | ~1,000ms | 257ms (-4×) | -50% bounce, +43% pageviews |
| Disney+ Hotstar | — | -61% | +100% weekly card views |

**Fixes:**
```js
// scheduler.yield() — Chrome 129+, Firefox 142+
async function handleClick() {
  giveImmediateFeedback();
  await scheduler.yield();
  slowerComputation();
}

// Fallback universal
requestAnimationFrame(() => { setTimeout(() => { heavyWork(); }, 0); });
```

### 16.2 LCP (Largest Contentful Paint)

**Budget 2.5s:** TTFB ~1000ms + resource load delay <250ms + resource load ~1000ms + render delay <250ms.

```html
<!-- Hero image: fetchpriority="high", KHÔNG lazy -->
<img src="hero.webp" fetchpriority="high" alt="..." width="1200" height="800">

<!-- Preload with responsive -->
<link rel="preload" as="image" href="hero-800.webp"
      imagesrcset="hero-400.webp 400w, hero-800.webp 800w, hero-1600.webp 1600w"
      imagesizes="(max-width: 600px) 100vw, 50vw" fetchpriority="high">
```

Google Flights: `fetchpriority="high"` → LCP **2.6s→1.9s** (-27%). Vodafone: LCP optimizations → **+8% sales**.

### 16.3 Vietnam Network Context

- 4G coverage: **99.8%** dân số. 5G: **~90%**. Avg mobile: **188 Mbps** (rank 14th global)
- Tại 90 Mbps 4G, hero 200KB tải ~18ms → **TTFB và render delay quan trọng hơn image download**
- Nông thôn ĐBSCL vẫn có vùng 30-40 Mbps 4G

### 16.4 Network-Aware Design (MỚI)

```js
// composables/useNetworkQuality.ts
export function useNetworkQuality() {
  const quality = ref('unknown');
  function update() {
    const conn = navigator?.connection;
    if (!conn) { quality.value = 'unknown'; return; }
    if (conn.saveData) { quality.value = 'save-data'; return; }
    if (/slow-2g|2g/.test(conn.effectiveType)) { quality.value = 'slow'; return; }
    if (conn.effectiveType === '3g') { quality.value = 'medium'; return; }
    quality.value = 'fast';
  }
  onMounted(() => { update(); navigator.connection?.addEventListener('change', update); });
  const isSlow = computed(() => ['slow', 'save-data'].includes(quality.value));
  return { quality, isSlow };
}
```

Browser support ~77% (Chrome, Edge, Samsung). Safari/Firefox = `'unknown'` fallback (default full quality).

```css
[data-connection-quality="slow"] * {
  animation-duration: 0s !important;
  transition-duration: 0s !important;
}
```

**Server-side:** `Save-Data: on` header → FastAPI middleware trả ảnh nhỏ, skip gallery. PHẢI set `Vary: Save-Data`.

---

## 17. Font Loading + Image Optimization

### 17.1 Font Loading

- Mobile: `font-display: swap` + metric overrides → CLS=0. Desktop: `font-display: optional` + preload
- `@nuxtjs/fontaine` — auto-generates override CSS cho Nuxt, zero config
- Safari KHÔNG support `ascent-override`/`descent-override` (chỉ `size-adjust` từ 17+)

### 17.2 Image Optimization for Vietnam (MỚI)

**Vietnam browser share (05/2026):** Chrome 63%, Safari 28%, UC 3.2%, Cốc Cốc 2.7%.
**WebP:** ~99% VN users. **AVIF:** ~95% VN users.

| Format | Quality | Approx Size | vs JPEG |
|---|---|---|---|
| JPEG | q85 | ~120KB | baseline |
| WebP | q75 | ~70KB | **-42%** |
| AVIF | q50 | ~45KB | **-63%** |

**Recommendation:** WebP q75 primary (99% coverage, 40× faster encode vs AVIF). AVIF pre-generate chỉ cho hero images.

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  image: {
    provider: 'ipx',
    quality: 75,
    format: ['avif', 'webp'],
    densities: [1, 2],
    presets: {
      hero: { modifiers: { width: 1200, height: 800, fit: 'cover', format: 'webp', quality: 75 } },
      thumbnail: { modifiers: { width: 400, height: 300, fit: 'cover', format: 'webp', quality: 70 } }
    }
  }
})
```

```html
<!-- Above fold: eager + fetchpriority -->
<NuxtImg src="/hero.jpg" format="webp" quality="75" loading="eager" fetchpriority="high" />

<!-- Below fold: lazy + async -->
<NuxtImg src="/card.jpg" format="webp" quality="75" loading="lazy" decoding="async" />
```

---

## 18. OKLCH Color Science (MỚI)

### 18.1 Tại sao OKLCH thay HSL

HSL lightness là mathematical, KHÔNG perceptual. `hsl(120,100%,50%)` (green, L=50%) trông **sáng hơn nhiều** so với `hsl(240,100%,50%)` (blue, L=50%):

| Color | HSL L | OKLCH L | Thực tế |
|---|---|---|---|
| Green `#00FF00` | 50% | **86.6%** | Rất sáng |
| Blue `#0000FF` | 50% | **45.2%** | Rất tối |
| Red `#FF0000` | 50% | 62.8% | Trung bình |

OKLCH fix: cùng L = cùng perceived brightness, bất kể hue.

### 18.2 Browser Support

**90.55% global** (06/2026). Chrome 111+, Firefox 113+, Safari 15.4+, Edge 111+.

`color-mix(in oklch)` — cùng support. Ưu điểm: colors stay vibrant khi mix (không muddy/gray như sRGB).

### 18.3 Palette Generation — Green Scale cho vinhlong360

```css
:root {
  --green-50:  oklch(0.97 0.02 155);
  --green-100: oklch(0.93 0.05 155);
  --green-200: oklch(0.87 0.10 155);
  --green-300: oklch(0.79 0.14 155);
  --green-400: oklch(0.70 0.17 155);
  --green-500: oklch(0.62 0.19 155);  /* base */
  --green-600: oklch(0.53 0.17 155);
  --green-700: oklch(0.45 0.14 155);
  --green-800: oklch(0.36 0.11 155);
  --green-900: oklch(0.27 0.08 155);
}
```

Algorithm: fix hue, vary L linearly, giảm chroma ở cực sáng/tối.

### 18.4 Dark Mode = L Inversion

```css
:root { --surface: oklch(0.97 0.01 155); --text: oklch(0.20 0.02 155); }
@media (prefers-color-scheme: dark) {
  :root { --surface: oklch(0.15 0.02 155); --text: oklch(0.93 0.01 155); }
}
/* 2 dòng swap toàn bộ. H và C giữ nguyên. */
```

### 18.5 Accessibility: delta-L ≥ 0.40

| Text L | BG L | delta-L | Contrast Ratio |
|---|---|---|---|
| 0.15 | 0.95 | 0.80 | ~17:1 (AAA) |
| 0.30 | 0.90 | 0.60 | ~10:1 (AAA) |
| 0.40 | 0.80 | **0.40** | **~5:1 (AA)** |
| 0.45 | 0.80 | 0.35 | ~4:1 (fail) |

Rule: **delta-L ≥ 0.40 = WCAG AA.** Background L ≥ 0.87 = safe với black text.

### 18.6 Fallback + Wide Gamut

```css
:root { --brand: #2d5016; }
@supports (color: oklch(0% 0 0)) { :root { --brand: oklch(0.45 0.12 155); } }
@media (color-gamut: p3) {
  @supports (color: oklch(0% 0 0)) { :root { --brand: oklch(0.45 0.18 155); } }
}
```

### 18.7 Adoption

- **Tailwind v4:** Toàn bộ default palette = OKLCH. 242 shades, một số vượt sRGB vào P3.
- **Open Props v2:** 17 CSS custom properties generate full palette từ 1 hue angle.
- **Figma:** KHÔNG support OKLCH native (requested 3+ năm). Plugin OkColor là workaround.
- **Gradient caveat:** OKLCH gradients vibrant nhưng bất ngờ. Dùng **OKLab** (không OKLCH) cho gradient interpolation.

---

## 19. Cognitive Accessibility (MỞ RỘNG)

### 19.1 WCAG AAA

- **2.4.9 Link Purpose (Link Only):** "Xem thêm" fail → thêm `<span class="sr-only">về Chợ Nổi</span>`
- **3.1.5 Reading Level:** Câu <15 từ, ít Hán-Việt, cấu trúc đơn giản

### 19.2 W3C COGA — 8 Design Objectives (MỚI)

1. Giúp người dùng hiểu trang làm gì — heading rõ, hierarchy nhất quán
2. Giúp tìm nội dung — search nổi bật, chia nhỏ
3. Nội dung rõ ràng — plain language, không double negatives, tóm tắt
4. Tránh sai sót — auto-save, undo, input linh hoạt, upfront fees
5. Giữ tập trung — không autoplay, giảm content density
6. Không dựa trí nhớ — hiện lại data bước trước, passwordless/simple login
7. Trợ giúp — help link mỗi trang, tooltip, nói hệ quả trước khi action
8. Tùy chỉnh — user control motion, simple mode

### 19.3 Neurodiversity (MỚI)

**ADHD:** Generous whitespace, chunked content (<1 idea/section), clear headings, `prefers-reduced-motion`, limit competing CTAs.

**Dyslexia:** Sans-serif, `font-size: 16px+`, `line-height: 1.5+`, `max-width: 70ch`, `letter-spacing: 0.05em`, `text-align: left` (KHÔNG justify), bold > italic, word-spacing 0.16em.

**Autism:** Consistent layout mọi trang, explicit button labels (nói action sẽ xảy ra), breadcrumbs, tránh idioms/metaphors, muted transitions, no surprise audio.

### 19.4 Low-Literacy UX (MỚI)

- Icon **PHẢI** paired với label (icon alone = semantically opaque, SARAL framework CSCW 2021)
- Touch targets: **56-72px** cho elderly/low-dexterity (WCAG AAA 44px, nghiên cứu elderly 19mm+ ≈ 72px)
- Photo-heavy content, linear navigation, swipeable carousels
- Buttons: 2-3 words max, action verbs
- Breadcrumbs: max 2-3 levels, horizontal scroll mobile

### 19.5 Age-Inclusive 60+ (MỚI)

- Body text: **18-20px** (không 16px). Sans-serif, relative units (rem)
- Contrast: target **AAA 7:1** (compensation cho vision loss age-80 = ~20/80)
- Touch targets: **20mm minimum** (~76px). 80% seniors prefer size này
- **KHÔNG infinite scroll** — dùng pagination hoặc "Xem thêm" button. Infinite scroll = keyboard/SR unusable + cognitive overload
- Persistent breadcrumbs + visible "Quay lại" button
- Consistent navigation across pages

### 19.6 Tourism Cognitive Load (MỚI)

- **Cowan (2001):** Working memory = **~4 chunks** (Miller's 7±2 outdated). Nav menu >8 items = vượt capacity
- **Homepage:** 5-7 main categories max. Subcategories >10 items → split
- **Progressive disclosure:** Max **2 levels deep.** Day overview → activities → details
- **Decision fatigue:** Curated "Staff picks" + pre-built itineraries giảm paralysis
- **Scan, don't read:** Users muddle through. Visual hierarchy phải pre-process trang giùm user

### 19.7 Vietnamese Plain Language (MỚI)

| Hán-Việt | Thuần Việt | Ghi chú |
|---|---|---|
| tham quan | đi xem, đi chơi | "tham quan" hiểu rộng nhưng formal |
| ẩm thực | đồ ăn, ăn uống | đơn giản hơn nhiều |
| di tích | nơi lịch sử | nhưng "di tích" SEO tốt hơn |
| du khách | khách đi chơi | |
| lưu trú | nơi ở, chỗ ở | |
| giao thông | đi lại, đường đi | |

**Rule:** Heading dùng Hán-Việt (SEO value, formal). Body text dùng thuần Việt. Câu <15 từ. Paragraphs: 3-4 câu max.

---

## 20. Tourism UX Patterns (MỚI)

### 20.1 Airbnb

- **Split-view map+list** (desktop): 65% list / 35% map. 95% users engage map khi có split-view; 65% KHÔNG tìm map khi list-only (Baymard)
- **Mobile:** Map ẩn sau toggle button. Breakpoint ~1100px → collapse thành 1 column
- **Cards:** Rounded photo (12-20px radius), NO border/shadow. Photo carries the card. `repeat(auto-fill, minmax(230px, 1fr))`
- **Photo carousel:** 5 photos max/card, dot indicators, swipe. First image loads, rest lazy on swipe
- **Reviews:** Không hiện average rating dưới 3 reviews. Star + numeric + count: `4.92 (1,234)`
- **Heart save:** Switching star→heart tăng saves 30%. Cần thêm "Lưu" label giảm misclick
- **Bottom nav:** 5 tabs (Explore, Wishlists, Trips, Inbox, Profile). ~56px. Icon + label
- **Spacing:** 4px base — 4, 8, 12, 16, 24, 32, 48, 64. Cards 12-20px radius

### 20.2 Google Travel/Maps

- **Place card hierarchy:** Name (bold) → star rating → category tags → address → hours → action buttons
- **Hours display:** "Open" (green) / "Closed" (red) + next change. Expandable 7-day table, today bold
- **Photo strip:** Horizontal scroll, first = hero full-width. Category tabs (All, Menu, Inside, Outside)
- **Popular times:** 24 bars/day, relative height. Live overlay red bar at current hour
- **Structured data impact:** Pages với schema = **3.2× more likely** được AI cite

### 20.3 Booking.com / Klook

- **Trust signals:** Bold colored score pill (`8.6 Fabulous`), review count inline, "Verified" tag
- **ETHICAL social proof:** "Booked 3 times in 24h", "Last booked 5 min ago" — nếu data thật. EU đã phạt fake scarcity
- **Filter pills:** Horizontal scroll, ~32-40px height, multi-select toggle, "×" remove. Applied filters = removable tags
- **Skeleton screens:** CSS-only shimmer `background: linear-gradient(90deg, #eee 25%, #f5f5f5 50%, #eee 75%)` + `animation: shimmer 1.5s infinite`
- **Card hierarchy (Klook):** 50/50 photo/text. Title → Price (bold red) → Rating + count → Duration

### 20.4 Tourism UX Research Data

- **Photos per listing:** 5-8 optimal (Salsify/Baymard). 56% users explore images first. Multi-angle +22% conversion
- **Review display:** Ratings distribution bar chart = #1 most used feature (Baymard). 43% top sites lack it
- **Map on mobile:** `gestureHandling: 'cooperative'` — 1-finger scrolls page, 2-finger pans map (Google 2016)
- **Nearby recommendations:** 3-6 items horizontal carousel. Distance thresholds context-dependent
- **Mobile = 62.66% global traffic.** Mobile bounce 50-60% vs desktop 35-45%. 1s speed boost = +12% conversion

### 20.5 Vietnamese Tourism Sites Analysis

**vinhlongtourist.vn (fail):** Dense text walls, zero alt text, no visual hierarchy, legal text in UI, no search/filter, no social proof, no map integration.

**vietnam.travel (mixed):** Strong photography + card layout + multi-path discovery. Fails: no search, 100+ cards no filter (choice paralysis), weak CTAs, deep dropdowns.

**traveloka.com/vi-vn (best practices):** Specific discount amounts ("75,000₫ off"), layered social proof (rating + app stats), icon+label nav, consistent card design. Fail: 100+ footer links.

**Gap cả 3 sites chia sẻ:** Không có split-view map+list, không real search, không inline reviews.

---

## 21. SEO Structured Data (MỞ RỘNG)

### 21.1 Event/Festival + Place/GeoCoordinates (đã có §18 cũ)

`TouristAttraction` nested trong `LocalBusiness` → eligible cho rich results. `TouristAttraction` standalone = valid cho AI/Knowledge Graph nhưng KHÔNG trigger rich results.

### 21.2 BreadcrumbList (MỚI)

**Google bỏ breadcrumbs khỏi mobile** (01/2025). Vẫn hiện desktop. Vẫn recommend implement cho site hierarchy + AI crawling.

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Trang chủ", "item": "https://vinhlong360.vn/" },
    { "@type": "ListItem", "position": 2, "name": "Cái Bè", "item": "https://vinhlong360.vn/huyen/cai-be" },
    { "@type": "ListItem", "position": 3, "name": "Chợ Nổi Cái Bè" }
  ]
}
```

### 21.3 LocalBusiness / FoodEstablishment (MỚI)

Required: `name`, `address` (PostalAddress). Strongly recommended: `telephone`, `url`, `geo`, `openingHoursSpecification`, `priceRange`, `image` (≥50,000 pixels, 3 aspect ratios: 16:9, 4:3, 1:1).

`FoodEstablishment` subtypes: Restaurant, CafeOrCoffeeShop, Bakery, FastFoodRestaurant.

### 21.4 Review / AggregateRating (MỚI)

**Critical rule:** Self-serving reviews (entity review chính nó) = **KHÔNG eligible** cho star snippets (từ 09/2019).

**vinhlong360 = third-party platform** → eligible cho review stars (giống TripAdvisor model). Required: `author.name`, `itemReviewed.name`, `reviewRating.ratingValue`. Decimal dùng dot (4.4 không 4,4).

### 21.5 Article / BlogPosting (MỚI)

Vẫn generate rich results (2026). Without `image` = ineligible cho Top Stories/Discover. Image ≥696px wide, 3 aspect ratios. `headline` <110 chars.

### 21.6 ItemList / Carousel (MỚI)

Cho "Top 10 điểm đến" pages. Min 3 items, `position` integers, cùng domain. `itemListOrder: "ItemListOrderDescending"` cho rankings.

### 21.7 Organization (MỚI)

Đặt trên homepage hoặc `/gioi-thieu`. `sameAs` array → Zalo, Facebook. `logo` ≥112×112px (recommend 512×512). `areaServed` cho local SEO.

### 21.8 Vietnamese SEO Specifics (MỚI)

- **URL slugs:** ASCII only (không dấu). VnExpress, Tuổi Trẻ đều dùng unaccented. Giữ dấu trong content/title
- **hreflang:** Nếu thêm English: subdirectory `/en/`, self-referencing + bidirectional links, `x-default` → Vietnamese
- **.vn ccTLD:** Auto-targeted Vietnam. Không cần geo.region meta (Google bỏ qua). Dùng `LocalBusiness` schema thay thế
- **Google Search share Vietnam:** 94.41%. Cốc Cốc 4.41%
- **GBP (Google Business Profile):** Foundational cho Local Pack. Reviews trên Foody.vn + Facebook cũng quan trọng

### 21.9 GEO — Generative Engine Optimization (MỚI)

Pages có structured data = **3.2× more likely** được AI cite. Schema + Article/FAQPage/HowTo = **+73% selection rate** cho AI Overview citations.

**Schema types impact cho AI:**
1. FAQPage (strongest extraction lift — dù Google deprecated rich results)
2. HowTo (step-by-step mapping)
3. Article + BreadcrumbList (universal baseline)
4. TouristAttraction/TouristDestination (travel queries)
5. LocalBusiness (3.5× more voice search traffic)

**Tips:** Bullet points + clear H2/H3 + direct answers early. Content updated <3 tháng = avg 6 citations vs 3.6 older. Claude 30% more likely cite bullet-pointed pages.

---

## 22. Micro-Interaction Patterns

### 22.1 Animation Rules (Linear)

Chỉ `transform` + `opacity`. Enter 150ms decelerate, exit 100ms accelerate. `prefers-reduced-motion: reduce` → tắt hoàn toàn.

```css
@keyframes fadeSlideIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
```

### 22.2 box-shadow Fast Path

```css
.card::after {
  content: ''; position: absolute; inset: 0; border-radius: inherit;
  box-shadow: 0 5px 15px rgba(0,0,0,.3); opacity: 0; transition: opacity .3s;
}
.card:hover::after { opacity: 1; }
```

### 22.3 Scroll Reveals

IntersectionObserver + CSS transition. Stagger children 0/50/100ms delay.

---

## 23. Implementation: Round 3 Tasks (MỞ RỘNG)

### R3-FE — Frontend (15 tasks)

| ID | Task | Source | P |
|---|---|---|---|
| R3-FE-1 | CSS containment cards + `content-visibility: auto` lists | §15.2 | P1 |
| R3-FE-2 | `fetchpriority="high"` hero + responsive `srcset`/`sizes` | §16.2 | P1 |
| R3-FE-3 | `@nuxtjs/fontaine` install → CLS=0 | §17.1 | P1 |
| R3-FE-4 | `<NuxtPicture>` AVIF→WebP→JPEG fallback chain | §17.2 | P1 |
| R3-FE-5 | Network-aware composable + `[data-connection-quality]` | §16.4 | P1 |
| R3-FE-6 | OKLCH tokens migration (green palette, `@supports` fallback) | §18 | P2 |
| R3-FE-7 | `@property` registration component tokens `inherits: false` | §15.1 | P2 |
| R3-FE-8 | `@layer` architecture 6 layers | §15.4 | P2 |
| R3-FE-9 | Asymmetric animation timing 150/100ms + box-shadow fast path | §22 | P2 |
| R3-FE-10 | `data-state` transitions cho modals/drawers | §22 | P2 |
| R3-FE-11 | Fluid letter-spacing (tightens theo font-size) | §14.2 | P2 |
| R3-FE-12 | Link text AAA audit — `sr-only` context cho "Xem thêm" | §19.1 | P2 |
| R3-FE-13 | Age-inclusive: body 18px, touch 56px+, no infinite scroll | §19.5 | P2 |
| R3-FE-14 | Shadow-as-border cards (Geist pattern) | §14.2 | P3 |
| R3-FE-15 | Scroll-triggered reveals + stagger | §22.3 | P3 |

### R3-BE — Backend (5 tasks)

| ID | Task | Source | P |
|---|---|---|---|
| R3-BE-1 | JSON-LD: TouristAttraction nested trong LocalBusiness | §21.1 | P1 |
| R3-BE-2 | JSON-LD: BreadcrumbList + Organization (homepage) | §21.2,21.7 | P1 |
| R3-BE-3 | JSON-LD: Review/AggregateRating (third-party eligible) | §21.4 | P1 |
| R3-BE-4 | JSON-LD: Article/BlogPosting cho community posts | §21.5 | P2 |
| R3-BE-5 | `Save-Data` middleware + `Vary: Save-Data` | §16.4 | P2 |

### R3-QA — Content/Docs (6 tasks)

| ID | Task | Source | P |
|---|---|---|---|
| R3-QA-1 | Vietnamese plain language guide (Hán-Việt alternatives table) | §19.7 | P1 |
| R3-QA-2 | COGA + neurodiversity checklist | §19.2-19.4 | P1 |
| R3-QA-3 | Age-inclusive design checklist (60+) | §19.5 | P2 |
| R3-QA-4 | Tourism cognitive load guidelines (5-7 categories, 2-level disclosure) | §19.6 | P2 |
| R3-QA-5 | CSS performance benchmark script (containment + CLS + INP) | §15-16 | P2 |
| R3-QA-6 | SEO structured data implementation guide (all 7 types) | §21 | P2 |

---

## 24. Tổng hợp: Thứ tự thực hiện toàn bộ (Round 1-2-3)

**Wave 1 — P1 Critical (21 tasks):**
- FE: DS-FE-1,2,5,6,13,14,15,16,17,19,20 + R3-FE-1,2,3,4,5 (16)
- BE: DS-BE-5,6,7 + R3-BE-1,2,3 (6)
- QA: DS-QA-1,2,6 + R3-QA-1,2 (5)

**Wave 2 — P2 Polish (27 tasks):**
- FE: DS-FE-3,4,7,8,10,11,18 + R3-FE-6,7,8,9,10,11,12,13 (15)
- BE: DS-BE-1,3 + R3-BE-4,5 (4)
- QA: DS-QA-3,4,7,8,9 + R3-QA-3,4,5,6 (9)

**Wave 3 — P3 Nice-to-have (5 tasks):**
- FE: DS-FE-9,12 + R3-FE-14,15 (4)
- BE: DS-BE-2,4 (2)
- QA: DS-QA-5 (1)
