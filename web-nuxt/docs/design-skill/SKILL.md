---
name: vinhlong360-design
description: "Design system and UI guidelines for vinhlong360.vn — a Vietnamese tourism/OCOP/community web app. Use this skill whenever designing, building, or reviewing UI components, pages, layouts, or CSS for the vinhlong360 project. Trigger on: new component creation, page design, CSS refactoring, dark mode work, responsive layout, accessibility fixes, color/typography decisions, card/badge/button styling, animation/motion work, or any visual design question for vinhlong360. Also use when the user mentions 'thiet ke', 'giao dien', 'UI', 'component', 'layout', 'dark mode', 'responsive', 'animation', or 'accessibility' in context of this project."
---

# vinhlong360 Design System

Guide for designing and building UI that feels cohesive, accessible, and culturally appropriate for vinhlong360.vn — a tourism/OCOP/community platform covering Vinh Long, Ben Tre, and Tra Vinh.

## Context

- **Solo dev**, budget <1M VND/month, web-first, <10k users
- **Pure CSS + CSS custom properties** (no Tailwind, no Style Dictionary)
- **Nuxt 4 SSR** with `@nuxtjs/color-mode` for dark mode (`.dark` class on `<html>`)
- **Inter** font self-hosted via `@nuxt/fonts`
- Design tokens live in `web-nuxt/assets/css/variables.css`

## Core Principles (Apple HIG adapted)

### 1. Clarity over decoration
Content IS the interface — tourism photos, place names, descriptions dominate. Motion is purposeful and optional — never the sole communication channel for info.

### 2. Warm, not cold
Palette draws from Tây Nam Bộ landscape: terracotta clay, amber sunlight, leaf green, river teal, on warm cream sand. Avoid cold whites — in Vietnamese culture, pure white carries funerary associations. The cream `--sand-50` (#FAF4E8) base is intentional.

### 3. Semantic over literal
Name tokens by purpose, not color. Apple uses 4-level hierarchies everywhere:
- **Labels**: label (100%) → secondary (60%) → tertiary (30%) → quaternary (18%)
- **Fills**: systemFill (20%) → secondary (16%) → tertiary (12%) → quaternary (8%)

### 4. Additive, not destructive
Add new tokens alongside old aliases. Verify at each step. Matches project invariant B2.

### 5. Accessible by default
WCAG AA minimum. 44px touch targets. Focus outlines. `prefers-reduced-motion` respected. Colors must work in 4 contexts: light/dark × default/high-contrast.

---

## Token Architecture (3 tiers)

See `references/tokens.md` for the complete table.

### Tier 1: Primitive (landscape names)
`--clay-50..900`, `--amber-100..600`, `--leaf-100..700`, `--river-100..600`, `--sand-50..400`, `--ink-700..900`

### Tier 2: Semantic (purpose-based, auto-remap in .dark)
`--primary`, `--primary-fg`, `--accent`, `--secondary`, `--tertiary`, `--bg`, `--bg-warm`, `--bg-alt`, `--ink`, `--muted`, `--line`, `--border`, `--card`, `--surface-translucent`

### Tier 3: Component (scoped)
`--badge-season-bg`, `--cat-experience..`, `--border-input` (WCAG 3:1)

### Adding new tokens
1. Check if a semantic token already covers it
2. If not, add semantic alias → primitive
3. Add `.dark` override
4. Verify contrast (WCAG AA: 4.5:1 text, 3:1 UI)

---

## Typography

Font: **Inter** (self-hosted .woff2), `system-ui` fallback. `font-optical-sizing: auto` on body.

### Scale (mapped from Apple iOS Dynamic Type — verified exact values)

| Apple style | Size | Weight | Tracking | Leading | vinhlong360 token |
|-------------|------|--------|----------|---------|-------------------|
| Large Title | 34pt | Regular | -1.05px | 41pt | `--text-3xl` (36px) |
| Title 1 | 28pt | Regular | — | 34pt | `--text-2xl` (28px) |
| Title 2 | 22pt | Regular | — | 28pt | `--text-xl` (22px) |
| Title 3 | 20pt | Semibold | — | 25pt | `--text-lg` (18px) |
| Headline | 17pt | **Semibold** | — | 22pt | `--text-base` + semibold |
| Body | 17pt | Regular | -0.43px | 22pt | `--text-base` (16px) |
| Callout | 16pt | Regular | — | 20pt | `--text-base` |
| Subhead | 15pt | Regular | 0px | 19pt | `--text-sm` (14px) |
| Footnote | 13pt | Regular | +0.03px | 16pt | `--text-sm` |
| Caption 1 | 12pt | Regular | +0.12px | 15pt | `--text-xs` (12px) |
| Caption 2 | 11pt | Regular | +0.15px | 14pt | min size (.68rem) |

### Letter-spacing (SF Pro non-linear tracking curve — verified)
| Size | Tracking | CSS |
|------|----------|-----|
| < 12px | positive (+0.15 to +0.24pt) | `letter-spacing: .02em` |
| 12px | zero | `letter-spacing: 0` |
| 14-18px | negative (-0.43pt at 17pt) | `letter-spacing: -.01em` |
| 20-28px | near zero (+0.07pt at 24pt) | `letter-spacing: -.02em` |
| > 36px | zero | `letter-spacing: 0` |

### Line height
- **SF Text (≤19pt)**: 120-130% line height
- **SF Display (≥20pt)**: 110-120% line height
- **Tight**: default -2pt (watchOS -1pt)
- **Loose**: default +2pt (watchOS +1pt)
- Body default: 22pt leading on 17pt text = ~129%

### Optical sizing
Variable font masters at: 9, 11, 17, 28, 52, 144pt. Tracking interpolation zone: 17-28pt. Inter supports `font-optical-sizing: auto`.

### Vietnamese considerations
- Line-height min 1.5 for body (diacritics stack vertically)
- Min font-size 11px (Apple: 11pt min on iOS)
- iOS 16px minimum on inputs (prevent zoom)

---

## Dark Mode

### Two-tier background (Apple HIG verified)
- **Base**: `--bg: #1a1a1a` (recedes)
- **Elevated**: `--card: #2c2c2e` (cards, modals, floating surfaces)

### Apple background hierarchy
| Apple | Light | Dark |
|-------|-------|------|
| systemBackground | #FFFFFF | #000000 |
| secondarySystemBackground | #F2F2F7 | #1C1C1E |
| tertiarySystemBackground | #FFFFFF | #2C2C2E |

vinhlong360 uses warm variants: `--bg` (#FAF4E8), `--bg-warm` (#F5EDD9), `--bg-alt` (#F0EBE0) instead of Apple's cold grays.

### Label hierarchy (exact opacities — verified)
| Level | Light (base #000) | Dark (base #FFF) | Opacity |
|-------|-------------------|-------------------|---------|
| label | #000000 | #FFFFFF | 100% |
| secondaryLabel | #3C3C4399 | #EBEBF599 | 60% |
| tertiaryLabel | #3C3C434D | #EBEBF54D | 30% |
| quaternaryLabel | #3C3C432E | #EBEBF52E | 18% |

### Fill hierarchy (exact opacities — verified)
| Level | Light opacity | Dark opacity |
|-------|--------------|--------------|
| systemFill | 20% | 36% |
| secondarySystemFill | 16% | 32% |
| tertiarySystemFill | 12% | 24% |
| quaternarySystemFill | 8% | 18% |

Pattern: dark mode roughly doubles light mode opacity.

### Separator colors (verified)
| Type | Light | Dark |
|------|-------|------|
| separator (translucent) | #3C3C434A (29%) | #54545899 (60%) |
| opaqueSeparator | #C6C6C8 | #38383A |

### Brand foreground lightening
```css
.dark { --primary-fg: #D98A6F; --secondary-fg: #4BA97D; --tertiary-fg: #6BA6B2; }
```

---

## Color System

See `references/tokens.md` for the complete color table with all hex values.

### Apple system colors (verified light/dark)
| Color | Light | Dark |
|-------|-------|------|
| systemRed | #FF3B30 | #FF453A |
| systemBlue | #007AFF | #0A84FF |
| systemGreen | #34C759 | #30D158 |
| systemOrange | #FF9500 | #FF9F0A |
| systemYellow | #FFCC00 | #FFD60A |
| systemPurple | #AF52DE | #BF5AF2 |
| systemIndigo | #5856D6 | #5E5CE6 |
| systemPink | #FF2D55 | #FF375F |
| systemTeal | #5AC8FA | #64D2FF |

Dark mode pattern: shifts **brighter + more saturated** (not just lighter).

---

## Spacing

8-point grid (4px base). See `references/tokens.md` for full table.

### Key dimensions
- **Touch targets**: 44pt min (Apple standard). visionOS: 60pt center-to-center
- **Content margins**: responsive (Apple doesn't publish fixed values — uses SafeAreaLayoutGuide)
- **Safe area insets**: iPhone X top 44pt / bottom 34pt; iPhone 15-16 top ~59pt / bottom 34pt; tvOS 60/90pt
- **Standard gap**: `--space-4` (16px). Card padding: 14-18px. Section spacing: `--space-12` (48px)

---

## Motion & Animation

See `references/motion.md` for full details.

### Spring physics (preferred over Bezier)
Two parameters: **duration** (pacing) + **bounce** (character).
- bounce=0: critically damped (default for all UI)
- bounce>0.4: exaggerated — avoid

### Duration tokens
| Token | Value | Use |
|-------|-------|-----|
| `--duration-fast` | .12s | Hover, press |
| `--duration-normal` | .18s | Standard transitions |
| `--duration-slow` | .3s | Modals, panels |

### Rules
1. Default no bounce. Only add when gesture has momentum
2. Stagger, don't sync — different properties settle at different times
3. Only animate `transform` and `opacity` (compositor-only)
4. Respect `prefers-reduced-motion`: set all durations to 0.01ms

---

## Shapes & Radius

### Three shape types (verified — SwiftUI ConcentricRectangle API)
1. **Fixed**: constant radius → `--radius` (16px) for cards
2. **Capsule**: radius = height/2 → `--radius-full` (999px)
3. **Concentric**: inner = outer - padding → badge in card with 6px padding: 16-6=10px

### Radius tokens
| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 8px | Inner nested |
| `--radius-md` | 12px | Buttons, inputs |
| `--radius-lg` / `--radius` | 16px | Cards, panels |
| `--radius-full` | 999px | Pills, chips |

---

## Materials & Effects

### 5 material tiers (not 4 — verified)
1. **systemUltraThinMaterial**: most background visible
2. **systemThinMaterial**: cover-tag on images
3. **systemMaterial**: topbar, floating bars (the default)
4. **systemThickMaterial**: better text contrast
5. **systemChromeMaterial**: nav bars, tab bars, toolbars

Each × 3 variants (adaptable, light, dark) = **15 system material styles**.

### Liquid Glass (WWDC 2025)
- Blur radius: ≤40px iPhone / ≤60px iPad
- Inner shadow: 30% opacity
- Max 4 compositing layers

### vinhlong360 implementation
```css
/* Regular material (topbar) */
--surface-translucent: rgba(255, 255, 255, .94);
backdrop-filter: blur(6px);

/* Thin material (cover tags) */
background: rgba(0,0,0,.55);
backdrop-filter: blur(4px);
```

---

## Iconography

vinhlong360 uses **emoji** for category covers and **inline SVG/CSS** for UI icons (no SF Symbols on web). But Apple's icon principles apply:

### Rendering modes (for future icon system)
1. **Monochrome**: single color, simplest — default for UI
2. **Hierarchical**: single color + auto opacity levels — emphasis
3. **Palette**: explicit multiple colors — differentiation
4. **Multicolor**: system-defined — brand moments

### Weight matching
Icon weight should match adjacent text weight. Symbol scales (small/medium/large) adjust to text point size.

### Optical alignment
Icons sit on text baseline. When combining icon + text, ensure vertical alignment with `vertical-align: -2px` or flexbox `align-items: center`.

---

## Scroll Edge Effects

### Three styles (verified)
1. **Soft** (default iOS/iPadOS): subtle gradient dissolve for floating elements
2. **Hard** (macOS): opaque separator boundary for pinned headers, text
3. **Automatic**: system chooses based on context

### Rules
- Functional only — not decorative
- Only use when scroll view is behind floating interface elements
- Each pane in split view gets its own effect
- Apple does NOT publish specific blur/opacity values for scroll edges

### vinhlong360
- Topbar uses translucent material — scroll content flows behind
- Consider adding gradient mask at top edge when content scrolls under topbar

---

## Layout & Responsive

### Apple size classes (verified)
| Device | Portrait | Landscape |
|--------|----------|-----------|
| All iPhones | Compact W, Regular H | varies |
| iPhones ≥ 414pt width | Compact W, Regular H | **Regular W**, Compact H |
| iPhones < 414pt | Compact W, Regular H | Compact W, Compact H |
| All iPads (full-screen) | Regular W, Regular H | Regular W, Regular H |

### vinhlong360 breakpoints
| Width | Context |
|-------|---------|
| > 820px | Desktop: full layout, sidebar, multi-column |
| 641-820px | Tablet: reduced columns, stacked sidebar |
| 521-640px | Mobile large: single column, bottom sheet modals |
| 481-520px | Mobile: compact, full-width |
| ≤ 480px | Mobile small: chat full-screen |

---

## Accessibility Checklist

- [ ] Text contrast: 4.5:1 minimum (Apple demonstrates 7.5:1 for enhanced)
- [ ] UI control contrast: 3:1 minimum
- [ ] Touch targets: min 44px (visionOS: 60pt center spacing)
- [ ] Focus: `outline: 2px solid var(--primary); outline-offset: 2px`
- [ ] `prefers-reduced-motion`: kills all animation
- [ ] `prefers-reduced-transparency`: blur → solid color fallback
- [ ] `prefers-contrast: more`: enhanced color differentiation
- [ ] Semantic HTML (`<nav>`, `<main>`, `<article>`, `<button>`)
- [ ] ARIA: `aria-live="polite"` for toasts/chat, `aria-expanded` for menus
- [ ] Color never sole indicator (pair with text, icon, or pattern — `shouldDifferentiateWithoutColor`)
- [ ] `@ScaledMetric` equivalent: padding/image sizes scale with text preference
- [ ] Skip link to main content

---

## Anti-patterns

1. **No Tailwind** — pure CSS + variables
2. **No hardcoded colors** — always CSS variables
3. **No cold whites** for large surfaces — use `var(--bg)` cream
4. **No per-category badge colors** — unified dark glass
5. **No tabs for actions** — tabs = navigation only
6. **No heavy features** — no AR, audio guide, native app, booking
7. **No z-index wars** — use scale: dropdown(50) < sticky(100) < overlay(200) < modal(500) < toast(600)
8. **No gratuitous animation** — motion must be purposeful
9. **No synchronized timing** — stagger properties
10. **No `will-change`** — modern browsers handle automatically

---

## CSS File Organization

| File | Contents |
|------|----------|
| `variables.css` | Tokens only (primitives, semantic, component) |
| `base.css` | Page layout, topbar, footer, hero, nav, chat |
| `components.css` | Buttons, inputs, modals, avatars, toasts, tags |
| `cards.css` | Entity cards, region cards, place chips |
| `detail.css` | Detail page, breadcrumb, lightbox, reviews |
| `catalog.css` | Filters, search, timeline, itinerary |

## Reference files

- `references/tokens.md` — Complete token table (all colors, typography, spacing, radius, shadows, z-index)
- `references/patterns.md` — 12 component patterns with code
- `references/motion.md` — Spring physics, choreography, keyframes
- `references/principles.md` — Apple HIG principles, Vietnamese context, accessibility patterns
