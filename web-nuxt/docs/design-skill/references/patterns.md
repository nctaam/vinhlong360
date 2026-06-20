# Component Patterns Reference

12 component patterns for vinhlong360. CSS classes, behavior, implementation notes.

---

## 1. Entity Cards

File: `cards.css`

```html
<NuxtLink :to="url" class="card">
  <div v-if="hasImage" class="cover-img">
    <NuxtImg :src="img" />
    <span class="cover-tag">Ẩm thực</span>
  </div>
  <div v-else :class="['cover', `cat-${cat}`]">
    <span>emoji</span>
    <span class="cover-tag">Ẩm thực</span>
  </div>
  <div class="card-b">
    <span class="card-type">typeName</span>
    <h3>name</h3>
    <p class="summary">summary</p>
    <p class="place">place</p>
    <div class="badges">...</div>
  </div>
</NuxtLink>
```

- `.cover` 96px (no-image), `.cover-img` 140px (with image)
- `.cover-tag`: unified dark glass — `rgba(0,0,0,.55)` + `backdrop-filter: blur(4px)`, white, 999px, .68rem
- Grid: `repeat(auto-fill, minmax(220px, 1fr))`, gap 16px
- Hover: `translateY(-4px)`, enhanced shadow
- Focus: `2px solid var(--primary)` outline
- Concentric radius: card 16px, cover-tag inside → capsule (999px)

---

## 2. Region Cards

File: `cards.css`

- `.region-card`: card with body text, for listings
- `.region-tile`: hero-style with bg image + overlay for homepage

Region tiles use gradient overlay for text readability over photos.

---

## 3. Buttons

File: `components.css`

| Class | Background | Text |
|-------|-----------|------|
| `.btn-primary` | `var(--primary)` | white |
| `.btn-accent` | `var(--accent)` | `var(--ink)` |
| `.btn-secondary` | `var(--secondary)` | white |
| `.btn-outline` | transparent + border | `var(--primary-fg)` |
| `.btn-ghost` | transparent | `var(--muted)` |

- Sizes: `.btn-sm` (32px), default (44px), `.btn-lg`
- Active: `scale(.97)`. Disabled: `opacity: .45`
- Focus: `outline: 2px solid var(--primary); outline-offset: 2px`
- Always `min-height: 44px; min-width: 44px`
- Apple mapping: Small = `.btn-sm`, Medium = `.btn`, Large = capsule, X-Large = `.btn-lg`

---

## 4. Inputs and Forms

File: `components.css`

```css
.input, .textarea, .select {
  width: 100%; padding: 12px 16px;
  border: 1.5px solid var(--border-input);
  border-radius: 10px; min-height: 44px;
}
```

- Focus: `border-color: var(--primary-fg)` + ring
- Error: `.input.error` = `border-color: #D94F3D`
- Font-size: 16px min (prevents iOS zoom)

```html
<div class="form-group">
  <label class="form-label">Label</label>
  <input class="input" />
  <span class="form-hint">Hint</span>
  <span class="form-error" v-if="error">Error</span>
</div>
```

---

## 5. Badges and Tags

### Cover tag (`.cover-tag`)
```css
.cover-tag {
  position: absolute; bottom: 6px; left: 6px;
  font-size: .68rem; font-weight: 700;
  padding: 3px 8px; border-radius: 999px;
  color: #fff; background: rgba(0,0,0,.55);
  backdrop-filter: blur(4px);
}
```

### Content badges (`.badge`)
`.badge.season`, `.badge.peak`, `.badge.ocop`, `.badge.year`

### Tags (`.tag`)
`.tag-primary`, `.tag-accent`, `.tag-secondary`, `.tag-tertiary`, `.tag-muted`
Translucent brand color (10-15% opacity) + corresponding fg color.

---

## 6. Modals

File: `components.css`

- Overlay: `rgba(43,38,34,.5)` + `backdrop-filter: blur(4px)`, z-index 500
- Modal: max-width 420px, 18px radius, slide-up animation
- Mobile (<520px): bottom sheet (full width, rounded top)
- Material: Apple systemMaterial thickness for overlay

---

## 7. Toasts

File: `components.css`

- Variants: default (dark), `.toast.success` (green), `.toast.error` (red), `.toast.warning` (amber)
- Auto-dismiss 3s via CSS animation
- Fixed bottom center, z-index 600
- `aria-live="polite"` for screen readers

---

## 8. Navigation

File: `base.css`

### Desktop
Horizontal flex nav, pill-shaped active: `background: var(--primary); color: #fff`.

### Topbar (systemMaterial)
```css
.topbar {
  position: sticky; top: 0; z-index: 100;
  background: var(--surface-translucent);
  backdrop-filter: blur(6px);
}
```

### Mobile (<820px)
Hamburger toggle, full-width vertical nav, backdrop overlay.
`aria-expanded` on toggle button.

---

## 9. Detail Page

File: `detail.css`

- Cover: `.detail-cover` (gradient) / `.detail-cover.has-cover-img` (image + overlay)
- Layout: `1fr 320px` (desktop), single column (<840px)
- Sidebar: sticky (`top: 78px`) — facts, OCOP, season, CTAs
- Highlights bar: quick-scan pills
- Reviews section with star ratings

---

## 10. Chat Widget

File: `base.css`

- FAB: 56px circle, fixed bottom-right, z-index 200
- Panel: 400px × 520px, glass header
- Mobile (<480px): full-screen
- Messages: user (right/primary) + assistant (left/card)
- Typing: bouncing dots
- `aria-live="polite"` on message container

---

## 11. Itinerary Builder

File: `catalog.css`

- Two-column: picker sidebar (360px sticky) + builder
- Timeline: numbered circles + vertical connector
- Stop cards: left-border colored by category
- Mobile: stacks single column

---

## 12. Social Feed

File: `base.css`

- Two-column: feed (1fr) + sidebar (300px)
- Image grids: 1-4 photos with smart layout
- Post type badges: review/share/recommend/question/discussion
