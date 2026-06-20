# Design Token Reference

Complete token table from `web-nuxt/assets/css/variables.css` + Apple HIG verified values.

## Table of Contents
1. [Primitive colors](#primitive-colors)
2. [Semantic colors (light)](#semantic-colors-light)
3. [Semantic colors (dark)](#semantic-colors-dark)
4. [Apple system colors](#apple-system-colors)
5. [Apple fill/label/separator hierarchy](#apple-hierarchy)
6. [Typography](#typography)
7. [Spacing](#spacing)
8. [Radius and motion](#radius-and-motion)
9. [Shadows and z-index](#shadows-and-z-index)
10. [Category gradients](#category-gradients)

---

## Primitive Colors

| Token | Hex | Use |
|-------|-----|-----|
| `--clay-50` | `#F7E9E3` | Lightest clay tint |
| `--clay-100` | `#EFD2C7` | Light clay |
| `--clay-400` | `#C4694E` | Medium clay |
| `--clay-600` | `#9C3D22` | **Primary brand** |
| `--clay-700` | `#7A2E18` | Dark clay |
| `--clay-900` | `#4A1C0E` | Deepest clay |
| `--amber-100` | `#FAEBD0` | Light amber |
| `--amber-500` | `#E8A33D` | **Accent** |
| `--amber-600` | `#C4872A` | Dark amber |
| `--leaf-100` | `#E7F3EC` | Light green |
| `--leaf-600` | `#2E7D5B` | **Secondary** |
| `--leaf-700` | `#1F5C41` | Dark green |
| `--river-100` | `#DCEAEC` | Light teal |
| `--river-600` | `#33646E` | **Tertiary** |
| `--sand-50` | `#FAF4E8` | **Page background** |
| `--sand-100` | `#F5EDD9` | Warm alternate bg |
| `--sand-200` | `#F0EBE0` | Alt background |
| `--sand-300` | `#E6E0D4` | Lines |
| `--sand-400` | `#D9D3C7` | Borders |
| `--ink-700` | `#586860` | Muted text (WCAG AA) |
| `--ink-900` | `#2B2622` | Primary text |
| `--white` | `#FFFFFF` | Card backgrounds |

---

## Semantic Colors (Light)

| Token | Maps to | Purpose |
|-------|---------|---------|
| `--primary` | `--clay-600` | Brand primary (backgrounds) |
| `--primary-dark` | `--clay-700` | Hover state |
| `--primary-light` | `--clay-400` | Lighter variant |
| `--primary-fg` | `--primary` | Brand as TEXT |
| `--primary-fg-strong` | `--primary-dark` | Emphasized brand text |
| `--accent` | `--amber-500` | Highlights, stars |
| `--accent-dark` | `--amber-600` | Accent hover |
| `--secondary` | `--leaf-600` | Secondary brand |
| `--secondary-fg` | `--secondary` | Secondary as text |
| `--tertiary` | `--river-600` | Tertiary brand |
| `--tertiary-fg` | `--tertiary` | Tertiary as text |
| `--bg` | `--sand-50` | Page background |
| `--bg-warm` | `--sand-100` | Warm sections |
| `--bg-alt` | `--sand-200` | Alternate |
| `--ink` | `--ink-900` | Primary text |
| `--muted` | `--ink-700` | Secondary text |
| `--line` | `--sand-300` | Subtle lines |
| `--border` | `--sand-400` | Stronger borders |
| `--border-input` | `#8F8676` | Input borders (WCAG 3:1) |
| `--card` | `--white` | Card surface |
| `--surface-translucent` | `rgba(255,255,255,.94)` | Blur surfaces |

---

## Semantic Colors (Dark)

| Token | Dark value | Notes |
|-------|-----------|-------|
| `--bg` | `#1a1a1a` | Base tier |
| `--bg-warm` | `#242424` | Slightly elevated |
| `--bg-alt` | `#2c2c2e` | Tertiary |
| `--ink` | `#e5e5e5` | Light text |
| `--muted` | `#9a9a9a` | Muted |
| `--line` | `#3a3a3c` | Line |
| `--border` | `#48484a` | Border |
| `--border-input` | `#7e7e82` | Input border (3:1 on card) |
| `--card` | `#2c2c2e` | Elevated surface |
| `--surface-translucent` | `rgba(28,28,30,.92)` | Blur |
| `--primary-fg` | `#D98A6F` | Lightened clay (4.5:1) |
| `--primary-fg-strong` | `#E09980` | Stronger |
| `--secondary-fg` | `#4BA97D` | Lightened leaf |
| `--tertiary-fg` | `#6BA6B2` | Lightened river |

---

## Apple System Colors (verified light/dark hex)

Reference values for when mapping to vinhlong360 semantic colors or creating status indicators.

| Color | Light | Dark | vinhlong360 use |
|-------|-------|------|-----------------|
| systemRed | #FF3B30 | #FF453A | Error states, danger |
| systemOrange | #FF9500 | #FF9F0A | Warnings |
| systemYellow | #FFCC00 | #FFD60A | Stars, highlights |
| systemGreen | #34C759 | #30D158 | Success, available |
| systemMint | (iOS 15+) | | — |
| systemTeal | #5AC8FA | #64D2FF | Info, links |
| systemCyan | (iOS 15+) | | — |
| systemBlue | #007AFF | #0A84FF | Interactive, links |
| systemIndigo | #5856D6 | #5E5CE6 | — |
| systemPurple | #AF52DE | #BF5AF2 | — |
| systemPink | #FF2D55 | #FF375F | — |
| systemBrown | (iOS 15+) | | — |
| systemGray | #8E8E93 | #8E8E93 | Neutral (identical both) |

Pattern: dark mode = brighter + more saturated.

---

## Apple Hierarchy (verified exact values)

### Fill colors (4 tiers)
| Level | Light hex | Light % | Dark hex | Dark % |
|-------|-----------|---------|----------|--------|
| systemFill | #78788033 | 20% | #7878805B | 36% |
| secondarySystemFill | #78788028 | 16% | #78788051 | 32% |
| tertiarySystemFill | #7676801E | 12% | #7676803D | 24% |
| quaternarySystemFill | #74748014 | 8% | #7676802D | 18% |

### Label colors (4 tiers)
| Level | Light | Dark | Opacity |
|-------|-------|------|---------|
| label | #000000 | #FFFFFF | 100% |
| secondaryLabel | #3C3C4399 | #EBEBF599 | 60% |
| tertiaryLabel | #3C3C434D | #EBEBF54D | 30% |
| quaternaryLabel | #3C3C432E | #EBEBF52E | 18% |

### Separator colors
| Type | Light | Dark |
|------|-------|------|
| separator (translucent) | #3C3C434A (29%) | #54545899 (60%) |
| opaqueSeparator | #C6C6C8 | #38383A |

### Background colors
| Level | Light | Dark |
|-------|-------|------|
| systemBackground | #FFFFFF | #000000 |
| secondarySystemBackground | #F2F2F7 | #1C1C1E |
| tertiarySystemBackground | #FFFFFF | #2C2C2E |

---

## Typography

Font: **Inter** (.woff2), system-ui fallback. `font-optical-sizing: auto`.

### Scale (verified from Apple iOS Dynamic Type)

| Token | Size | Rem | Apple equiv | Weight | Tracking | Leading |
|-------|------|-----|-------------|--------|----------|---------|
| `--text-xs` | 12px | .75rem | Caption 1 | Regular | +0.12px | 1.33 |
| `--text-sm` | 14px | .875rem | Subhead | Regular | 0px | 1.43 |
| `--text-base` | 16px | 1rem | Body | Regular | -0.43px | 1.5 |
| `--text-lg` | 18px | 1.125rem | Title 3 | Semibold | — | 1.35 |
| `--text-xl` | 22px | 1.375rem | Title 2 | Regular | — | 1.27 |
| `--text-2xl` | 28px | 1.75rem | Title 1 | Regular | — | 1.21 |
| `--text-3xl` | 36px | 2.25rem | Large Title | Regular | -1.05px | 1.2 |

### Line height ratios (verified)
| Range | Ratio | vinhlong360 |
|-------|-------|-------------|
| SF Text ≤19pt | 120-130% | `--leading-normal` (1.5) for Vietnamese |
| SF Display ≥20pt | 110-120% | `--leading-tight` (1.2) |
| Tight adjustment | -2pt | — |
| Loose adjustment | +2pt | — |

### Optical sizing masters
9, 11, 17, 28, 52, 144pt. Tracking interpolation zone: 17-28pt.

### CSS font families
| CSS keyword | Font |
|-------------|------|
| `system-ui` | San Francisco (replaces `-apple-system`) |
| `ui-rounded` | SF Pro Rounded (Safari only) |
| `ui-serif` | New York |
| `ui-monospace` | SF Mono |

### Weights
| Token | Value | Apple equiv |
|-------|-------|------------|
| `--weight-normal` | 400 | Regular |
| `--weight-semibold` | 600 | Semibold (Headline, Title 3) |
| `--weight-bold` | 700 | Bold (emphasized titles) |
| `--weight-extrabold` | 800 | (brand, project-specific) |

---

## Spacing

8-point grid (4px base):

| Token | Value |
|-------|-------|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |
| `--space-16` | 64px |

### Touch targets
- Standard: 44pt minimum (Apple)
- visionOS: 60pt center-to-center
- iPhone safe areas: top 44-62pt (varies by model), bottom 34pt

---

## Radius and Motion

### Radius
| Token | Value | Shape type |
|-------|-------|-----------|
| `--radius-sm` | 8px | Fixed (inner nested) |
| `--radius-md` | 12px | Fixed (buttons, inputs) |
| `--radius-lg` / `--radius` | 16px | Fixed (cards, panels) |
| `--radius-full` | 999px | Capsule (pills, chips) |

### Concentric formula
`inner-radius = outer-radius - padding`

### Motion
| Token | Value | Use |
|-------|-------|-----|
| `--duration-fast` | .12s | Hover, press |
| `--duration-normal` | .18s | Transitions |
| `--duration-slow` | .3s | Modal, panel |
| `--ease-out` | `cubic-bezier(.2,.8,.2,1)` | Default deceleration |
| `--ease-bounce` | `cubic-bezier(.34,1.56,.64,1)` | Playful overshoot |

---

## Shadows and Z-index

### Shadows
| Token | Value | Use |
|-------|-------|-----|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,.05)` | Subtle |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,.08)` | Dropdowns |
| `--shadow-lg` | `0 12px 32px rgba(0,0,0,.12)` | Modals |
| `--shadow` | clay-tinted dual shadow | Default cards |

### Z-index scale
| Token | Value | Layer |
|-------|-------|-------|
| `--z-dropdown` | 50 | Dropdowns, menus |
| `--z-sticky` | 100 | Topbar |
| `--z-overlay` | 200 | Chat fab, overlays |
| `--z-modal` | 500 | Modals |
| `--z-toast` | 600 | Toasts |

---

## Category Gradients

`linear-gradient(135deg, ...)` for card covers without images:

| Token | Colors | Category |
|-------|--------|----------|
| `--cat-experience` | `#2E7D5B → #4BA97D` | Trải nghiệm |
| `--cat-product` | `#E8A33D → #F0BE6A` | Sản phẩm |
| `--cat-attraction` | `#33646E → #4E8A96` | Điểm đến |
| `--cat-craft` | `#9C3D22 → #C4694E` | Làng nghề |
| `--cat-accommodation` | `#5B6CC4 → #8B9AF0` | Lưu trú |
| `--cat-dish` | `#D94F3D → #F07A5F` | Ẩm thực |
| `--cat-itinerary` | `#9C3D22 → #E8A33D` | Lịch trình |
| `--cat-org` | `#6B7B73 → #97A89C` | Tổ chức |
| `--cat-place` | `#33646E → #4E8A96` | Địa phương |
