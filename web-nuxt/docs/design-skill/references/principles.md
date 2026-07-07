# Design Principles Reference

Apple HIG principles adapted for vinhlong360 web context, Vietnamese cultural context, accessibility patterns, iconography guidelines.

---

## Apple's 8 Design Principles

### 1. Aesthetic Integrity
Appearance matches function. Tourism discovery app = warm, inviting, easy to explore — not corporate.

**vinhlong360**: Warm cream palette, organic shapes, photography-forward cards.

### 2. Consistency
Standard patterns and conventions. Users expect standard behaviors from standard-looking controls.

**vinhlong360**: One button system (5 variants), one card pattern, unified badge style.

### 3. Direct Manipulation
Act on content directly, not through abstraction layers.

**vinhlong360**: Cards link to detail. Map markers click to entities. Save immediately toggles (heart pop).

### 4. Feedback
Every action has visible response.

**vinhlong360**: Press scale(.97), hover lift, save pop, toast confirmations, skeleton loading.

### 5. Metaphors
Ground abstract concepts in real-world analogies.

**vinhlong360**: "Journey" for itinerary. Card as brochure. Region tile as map overlay.

### 6. User Control
Users initiate and control. No surprises.

**vinhlong360**: No auto-play video. No forced modals. Chat is user-initiated (FAB). Dark mode user-selected.

### 7. Depth
Visual layering for hierarchy.

**vinhlong360**: Z-index scale, shadow tokens, translucent topbar, modal overlay.

### 8. Deference
Content comes first. Chrome is minimal.

**vinhlong360**: Photos dominate cards. Hero is full-width. Typography is clean. Chrome is translucent.

---

## Vietnamese Cultural Context

### Color psychology
| Color | Meaning | Use |
|-------|---------|-----|
| Red/clay | Luck, prosperity | Primary brand — appropriate for tourism |
| Gold/amber | Royalty, wealth | Accent/highlight |
| Green/leaf | Growth, nature | Secondary (agricultural region) |
| White | Mourning | Avoid pure #fff for page bg → use cream --sand-50 |
| Blue/teal | Calm, trust | Tertiary (Mekong delta water) |

### Typography
- Vietnamese diacritics (ă, â, ê, ô, ơ, ư + tone marks) stack vertically → line-height 1.5 min
- Long proper nouns (Thành phố Vĩnh Long, Huyện Mang Thít) → responsive text truncation
- Inter handles Vietnamese diacritics well

### Imagery
- Mekong delta: river, green orchards, terracotta tiles, golden sunlight
- Avoid generic tropical stock → specifically Tây Nam Bộ
- Copyright: AI-generated only (CLAUDE.md §1.5) — no stock, no Wikimedia, no UGC photos

### Naming
- Vietnamese entity names: title case with diacritics ("Nhà Cổ Cai Cường")
- Category names: "Ẩm thực", "Trải nghiệm", "Điểm đến", "Làng nghề"

---

## Accessibility Patterns

### WCAG AA compliance
| Criterion | Requirement | Implementation |
|-----------|-------------|----------------|
| 1.4.3 | 4.5:1 text contrast | All semantic tokens verified |
| 1.4.11 | 3:1 non-text contrast | `--border-input` set 3:1+ |
| 2.4.7 | Focus visible | 2px solid primary + 2px offset |
| 2.5.5 | 44px touch target | All buttons min 44px |
| 1.4.12 | Text spacing | line-height 1.5, generous padding |

### Apple's 4-context color model
1. **Light default** — `--bg: #FAF4E8`
2. **Dark default** — `--bg: #1a1a1a`
3. **Light high-contrast** — `@media (prefers-contrast: more)`
4. **Dark high-contrast** — `@media (prefers-contrast: more) and (prefers-color-scheme: dark)`

Currently implemented: 1 and 2. 3 and 4 are candidates for future pass.

### Reduce Transparency
```css
@media (prefers-reduced-transparency: reduce) {
  .topbar { background: var(--bg); backdrop-filter: none; }
  .cover-tag { background: #333; backdrop-filter: none; }
}
```

### Reduce Motion
UIKit auto-converts lateral slides → cross-fade. `isVideoAutoplayEnabled` API.
Web: `prefers-reduced-motion: reduce` media query.

### Differentiate Without Color
API: `shouldDifferentiateWithoutColor`. Always pair color with shape/text/icon.

### Dynamic Type scaling
- Branch layout at `accessibilityMedium` threshold
- `@ScaledMetric` (SwiftUI) — equivalent on web: use `rem` + root font-size scaling
- Set `numberOfLines = 0` (web: no truncation) for accessibility sizes
- 11 text styles, NOT linear multiplier — each has discrete values per size category

### Screen readers
- Semantic HTML: `<nav>`, `<main>`, `<article>`, `<section>`, `<button>`
- ARIA: `aria-live="polite"` for toasts/chat, `aria-expanded` for menus, `aria-label` for icon buttons
- Skip link to main content
- Image `alt`: descriptive for informational, empty for decorative

### Bold Text
Ensure layouts don't break when font-weight increases system-wide. Use flexible containers, avoid `white-space: nowrap` on expandable text.

---

## Iconography Guidelines

vinhlong360 uses emoji for category covers and inline SVG/CSS for UI. Apple SF Symbols principles still apply conceptually.

### Icon design principles
- Match icon weight to adjacent text weight
- Optical alignment: icons sit on text baseline (`vertical-align: -2px` or flexbox center)
- Consistent stroke width across all icons in a set
- Padding: adequate space between icon and text (8px min)

### Rendering mode mapping (for web icon systems)
| Apple mode | Web equivalent | When |
|-----------|---------------|------|
| Monochrome | Single color SVG | Default UI |
| Hierarchical | SVG with opacity layers | Emphasis |
| Palette | Multi-color SVG | Differentiation |
| Multicolor | Full-color illustration | Brand moments |

### SF Symbols reference
- 5000+ symbols across 3 axes: scale (s/m/l), weight (9 levels: ultraLight → black), point size
- 7 animation presets: appear, disappear, bounce, scale, pulse, variable color, replace
- Variable color: cumulative vs iterative mode
- Replace: directional (down/up, up/up) with 3-plane spatial model

---

## Content-First Hierarchy

### Visual weight order
1. Hero image / cover photo — largest
2. Entity name (h1/h2) — largest text
3. Key info (highlights bar) — scannable pills
4. Body content — description, details, reviews
5. Sidebar / supplementary — facts, CTAs
6. Navigation chrome — translucent, minimal

### Card information hierarchy
1. Cover (image or category gradient) — visual hook
2. Type label — small, muted
3. Name (h3) — primary identifier
4. Summary — 2-line truncated
5. Place — location context
6. Badges — supplementary metadata

### Typography pairing
- **Hero/page title**: `--text-2xl` to `--text-3xl`, bold/extrabold
- **Section headings**: `--text-xl`, semibold
- **Card titles**: `--text-lg`, semibold
- **Body text**: `--text-base`, normal
- **Secondary/meta**: `--text-sm`, normal, `color: var(--muted)`
- **Captions/labels**: `--text-xs`, normal

---

## Color Usage Rules

1. **Primary (clay)** for actions — buttons, links, active states
2. **Accent (amber)** sparingly for delight — stars, featured badges
3. **Secondary (leaf)** for positive — success, available
4. **Tertiary (river)** for informational — help text, neutral badges
5. **Neutral (sand/ink)** for structure — backgrounds, text, borders
6. Never color alone — always pair with text, icon, or pattern

---

## Responsive Strategy

### Layout by breakpoint
| Width | Layout |
|-------|--------|
| > 820px | 2-column detail (1fr 320px), 3-4 col cards, sidebar nav |
| 641-820px | Collapse to 2-col cards, hamburger nav |
| 521-640px | Single column, bottom sheet modals |
| ≤ 480px | Chat full-screen, minimal padding |

### Content density
- Desktop: comfortable (--space-4 to --space-6 gaps)
- Mobile: tighter (--space-3 to --space-4) but never cramped
- Touch targets: 44px minimum regardless of density

### iPhone logical widths (verified)
320 → 375 → 390 → 393 → 402 → 414 → 420 → 428-440pt

### Size class rule
- Compact width: all iPhones portrait + small iPhones landscape
- Regular width: iPhones ≥ 414pt landscape + all iPads
