# Motion & Animation Reference

Derived from Apple WWDC 2018 (Fluid Interfaces), WWDC 2023 (Animate with Springs), adapted for CSS web.

---

## Spring Physics

Apple rejects duration-based Bezier in favor of spring physics. Springs preserve velocity from gestures, respond to interruption gracefully, and produce asymmetric motion.

### Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| **duration** | Overall pacing | ~0.3s |
| **bounce** | Character of settle | 0 (critically damped) |

### Bounce scale
| Value | Behavior | Use |
|-------|----------|-----|
| < 0 | Overdamped, sluggish | Avoid |
| 0 | Critically damped, smooth | **Default for all UI** |
| 0.15 | Barely noticeable bounce | Subtle emphasis |
| 0.3 | Noticeable bounce | Save/like pop |
| > 0.4 | Exaggerated | Avoid |

### Physics conversion
```
stiffness = (2π / duration)²
damping = 1 - 4π × bounce / duration  (bounce ≥ 0)
mass = 1
```

---

## Duration Tokens

| Token | Value | Use |
|-------|-------|-----|
| `--duration-fast` | 0.12s | Hover, press, color change |
| `--duration-normal` | 0.18s | Card lift, page transition |
| `--duration-slow` | 0.3s | Modal, panel slide |

- High-frequency (hover, press): fastest
- Navigation: normal
- Modals/overlays: slow (user needs to track change)
- Never > 0.5s on web
- Never animate frequently-occurring events

---

## Easing Tokens

| Token | Value | Character |
|-------|-------|-----------|
| `--ease-out` | `cubic-bezier(.2, .8, .2, 1)` | Smooth deceleration — default |
| `--ease-bounce` | `cubic-bezier(.34, 1.56, .64, 1)` | Playful overshoot — sparingly |

- **ease-out**: entering view, hover, focus, expand
- **ease-bounce**: emotional feedback only (heart save, star rate)
- **ease-in**: almost never — elements accelerating away feel wrong
- **linear**: scrolling, progress bars, spinners only

---

## Choreography

Different properties settle at different times. Don't sync.

### Staggered properties
```css
.card {
  transition:
    transform .18s var(--ease-out),
    opacity .12s ease,
    box-shadow .25s ease;
}
```

### Group stagger (list items)
```css
.card:nth-child(1) { transition-delay: 0s; }
.card:nth-child(2) { transition-delay: .03s; }
.card:nth-child(3) { transition-delay: .06s; }
```

### Anti-pattern
```css
.card { transition: all .2s ease; }
```

---

## When to Animate

### Yes
- State change confirmation (save pop, like fill)
- Spatial orientation (page slide, card lift, modal enter)
- Loading feedback (skeleton shimmer, spinner)
- Micro-feedback (button press scale(.97), focus ring)

### No
- Scroll-triggered parallax everywhere
- Auto-playing hero animations
- Bouncing arrows, pulsing CTAs
- Continuous animation without user trigger

### Rule
If removing the animation makes the UI harder to understand, keep it. If it just makes it less "fancy", remove it.

---

## Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Apple also reduces lateral slides to cross-fade automatically in UIKit. Consider: reduced-motion should still show instant state changes, not zero change.

### Reduce Transparency
```css
@media (prefers-reduced-transparency: reduce) {
  .topbar { background: var(--bg); backdrop-filter: none; }
  .cover-tag { background: #333; backdrop-filter: none; }
}
```

---

## CSS Implementation

### Compositor-only (60fps on weak devices)
```css
.card:hover { transform: translateY(-4px); }
@keyframes modalIn { from { opacity: 0; transform: translateY(16px) scale(.97); } }
```

### Avoid layout-triggering
```css
.card:hover { margin-top: -4px; }  /* reflows page */
.card:hover { height: 200px; }      /* layout recalc */
```

### Don't use `will-change`
Modern browsers handle this automatically. Declaring it on many elements wastes GPU memory.

### Keyframes in the project
```css
@keyframes savePop { 0% { transform: scale(1); } 40% { transform: scale(1.35); } 100% { transform: scale(1); } }
@keyframes modalIn { from { opacity: 0; transform: translateY(16px) scale(.97); } }
@keyframes toastIn { from { opacity: 0; transform: translateY(12px); } }
@keyframes toastOut { to { opacity: 0; transform: translateY(-8px); } }
@keyframes shimmer { to { background-position: -200% 0; } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes cbounce { to { opacity: .3; transform: translateY(-3px); } }
@keyframes jbSlideUp { from { opacity: 0; transform: translateX(-50%) translateY(16px); } }
```
