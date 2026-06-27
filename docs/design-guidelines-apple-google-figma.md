# Nghiên cứu toàn diện: Apple HIG + Google Material Design 3 + Figma
> Ngày: 2026-06-27 | Nguồn: developer.apple.com/design, design.google, help.figma.com
> Mục đích: Tham chiếu thiết kế cho vinhlong360.vn (web-first, CSS thuần, solo dev)

---

## MỤC LỤC

- [PHẦN A: APPLE HUMAN INTERFACE GUIDELINES](#phần-a-apple-human-interface-guidelines)
  - [A1. Foundations](#a1-foundations)
  - [A2. Components](#a2-components)
  - [A3. Patterns & Inputs](#a3-patterns--inputs)
  - [A4. Technologies & Platform](#a4-technologies--platform)
- [PHẦN B: GOOGLE MATERIAL DESIGN 3](#phần-b-google-material-design-3)
  - [B1. Color System & HCT](#b1-color-system--hct)
  - [B2. Typography](#b2-typography)
  - [B3. Components (30 loại)](#b3-components)
  - [B4. Motion & Animation](#b4-motion--animation)
  - [B5. Adaptive Design](#b5-adaptive-design)
  - [B6. Inclusive Design](#b6-inclusive-design)
  - [B7. Design Practices](#b7-design-practices)
- [PHẦN C: FIGMA](#phần-c-figma)
  - [C1. Design Fundamentals](#c1-design-fundamentals)
  - [C2. Design Systems](#c2-design-systems)
  - [C3. Prototyping](#c3-prototyping)
  - [C4. Dev Mode & Handoff](#c4-dev-mode--handoff)
- [PHẦN D: CROSS-REFERENCE & ÁP DỤNG CHO VINHLONG360](#phần-d-cross-reference--áp-dụng-cho-vinhlong360)

---

# PHẦN A: APPLE HUMAN INTERFACE GUIDELINES

## A1. Foundations

### A1.1 Color System

**iOS System Colors (Light / Dark hex):**

| Color | Light | Dark |
|-------|-------|------|
| systemBlue | #007AFF | #0A84FF |
| systemGreen | #34C759 | #30D158 |
| systemIndigo | #5856D6 | #5E5CE6 |
| systemOrange | #FF9500 | #FF9F0A |
| systemPink | #FF2D55 | #FF375F |
| systemPurple | #AF52DE | #BF5AF2 |
| systemRed | #FF3B30 | #FF453A |
| systemTeal | #5AC8FA | #64D2FF |
| systemYellow | #FFCC00 | #FFD60A |

**Background Colors:**

| Role | Light | Dark |
|------|-------|------|
| systemBackground | #FFFFFF | #000000 |
| secondarySystemBackground | #F2F2F7 | #1C1C1E |
| tertiarySystemBackground | #FFFFFF | #2C2C2E |

**Label Colors (alpha):**

| Role | Light alpha | Dark alpha |
|------|------------|-----------|
| label | 100% | 100% |
| secondaryLabel | 60% | 60% |
| tertiaryLabel | 30% | 30% |
| quaternaryLabel | 18% | 18% |

**Gray Scale:** 6 cấp (systemGray → systemGray6)

**Contrast Requirements:**
- Text thường: 4.5:1 minimum
- Text lớn / non-text: 3:1 minimum

### A1.2 Typography

**Font:** SF Pro (Display cho 20pt+, Text cho ≤19pt). SF Mono cho code. New York cho serif.

**13 Text Styles (tại default "Large" size):**

| Style | Size | Weight | Line Height | Tracking |
|-------|------|--------|-------------|----------|
| Extra Large Title | 36pt | Bold | 43pt | — |
| Large Title | 34pt | Regular | 41pt | 0.37 |
| Title 1 | 28pt | Regular | 34pt | 0.36 |
| Title 2 | 22pt | Regular | 28pt | 0.35 |
| Title 3 | 20pt | Semibold | 24pt | 0.38 |
| Headline | 17pt | Semibold | 22pt | -0.41 |
| Body | 17pt | Regular | 22pt | -0.41 |
| Callout | 16pt | Regular | 21pt | -0.32 |
| Subheadline | 15pt | Regular | 20pt | -0.24 |
| Footnote | 13pt | Regular | 18pt | -0.08 |
| Caption 1 | 12pt | Regular | 16pt | 0 |
| Caption 2 | 11pt | Regular | 13pt | 0.07 |

**Dynamic Type:** Body text scale tới 200%+. Minimum 11pt cho Caption 2.

### A1.3 Layout & Spacing

| Token | Value |
|-------|-------|
| Grid system | 8pt grid, 4pt subdivision |
| Min tap target | 44×44pt (iOS), 60×60pt (visionOS) |
| Button spacing | 12–48pt |
| Stacked controls (Regular) | 12px min |
| Stacked controls (Small) | 10px min |
| Label-to-control spacing | 8px (Regular), 6px (Small) |
| View layout margins | 8pt each side |
| View controller horizontal margins | 20pt from superview |

**Safe Area Insets (iPhone X+):**
- Portrait: Top 44–59pt, Bottom 34pt
- Landscape: Left/Right 44pt each

### A1.4 Animation

**Spring Animation:** duration + bounce parameters
- Bounce 0–0.4 safe range
- Presets: `.smooth`, `.snappy`, `.bouncy`
- Reduce Motion: thay bằng dissolve/fade, không xóa hoàn toàn

### A1.5 Liquid Glass (iOS 26)

- **Material:** Translucent, reflect/refract surroundings, real-time rendering
- **2 variants:** Regular (versatile, adaptive) + Clear (permanently transparent)
- **Áp dụng:** Buttons, switches, sliders, tab bars, sidebars, nav bars, toolbars, widgets
- **Concentricity:** inner radius = outer radius − padding
- **Dark mode:** 2 elevation levels (base #000000, elevated #1C1C1E / #2C2C2E)

### A1.6 Materials (Vibrancy)

5 cấp độ blur: ultra-thin, thin, regular, thick, ultra-thick

### A1.7 Accessibility

| Requirement | Spec |
|-------------|------|
| Min touch target | 44×44pt (iOS), 60×60pt (visionOS) |
| Color contrast (normal text) | 4.5:1 |
| Color contrast (large text) | 3:1 |
| Min text size | 11pt |
| Dynamic Type | Tất cả text phải scale |
| VoiceOver labels | Tất cả interactive element phải có label |
| State communication | Không chỉ dùng color |
| Reduce Motion | Support preference |

---

## A2. Components

### A2.1 Navigation

**Navigation Bar:**
- Height: 44pt (iPhone), 50pt (iPad)
- Large Title: +52pt
- iOS 26: Floating glass appearance

**Tab Bar:**
- Height: 49pt (portrait), 32pt (landscape). iPhone X+: 83pt / 53pt
- Icon: 25×25pt filled SF Symbols
- Max tabs: 5 (iPhone), 7 (iPad)
- Badge: Red oval + white text

**Toolbar:**
- Height: 44pt (iPhone), 50pt (iPad)
- Icon stroke: 1–1.5pt outlined
- iOS 26: Floating glass above content

**Search Field:**
- Styles: Prominent (opaque bg) / Minimal (translucent)
- Scope bar optional for category filtering

### A2.2 Content

**Charts:** Swift Charts API, auto accessibility labels, audio graphs for VoiceOver

**Image Views:** PNG, JPEG, PDF. Modes: stretch, scale (fit/fill), pin

**Text Views:** Multiline styled text, optionally editable. Dynamic Type scaling

**Web Views:** WKWebView. Không thay native UI patterns

**Maps:** Apple Maps với annotations, overlays, gestures (pan, pinch-zoom, rotate)

### A2.3 Input Controls

**Buttons:**
- Min touch: 44×44pt
- Styles: `.plain`, `.borderless`, `.bordered`, `.borderedProminent`, `.glass` (iOS 26)
- Roles: `.none`, `.destructive` (red), `.cancel` (bold safe choice)
- Sizes: `.mini`, `.small`, `.regular`, `.large`
- Border shapes: `.capsule`, `.roundedRectangle`, `.circle`

**Text Fields:**
- Single-line, fixed-height, rounded corners
- Placeholder text, clear button, left/right images
- Keyboard types: 12 loại (default, email, phone, URL, numberPad, etc.)
- Secure text fields cho passwords

**Toggles/Switches:**
- Dimensions: 51×31pt (fixed)
- Thumb: 27px
- On = green, Off = gray
- iOS 26: Liquid Glass material

**Segmented Controls:**
- Max 5–7 segments
- Icon constraints: 17×15px (Regular), 14×13px (Small)

**Sliders:**
- Horizontal track + thumb
- Min/max icons customizable
- iOS 26: Liquid Glass applied

**Date Pickers:**
- Styles: Textual, Graphical (calendar), Wheels
- Formats: Month/Day/Year, Hour/Minute/Second, etc.

### A2.4 Presentation

**Action Sheets:** 2+ choices, Cancel luôn ở bottom, destructive = red text ở top

**Alerts:**
- Cancel + destructive: Cancel là bold (safe option)
- Cancel KHÔNG BAO GIỜ là destructive action
- iOS 26: Bolder, left-aligned typography

**Sheets:** Scoped task modal. Include clear dismiss action

**Popovers:** Arrow trỏ tới element. iPhone: thành sheets

**Scroll Views:** Show scroll indicators, support paging, respect safe area

### A2.5 Status

**Progress Indicators:**
- Activity Indicator (spinner): unquantifiable tasks
- Progress Bar: quantifiable tasks, show percentage
- Prefer progress bars over spinners khi có thể

**Notifications:**
- Types: Banner (temporary) / Alert (persistent)
- Max 4 action buttons trong expanded view
- Không gửi multiple notifications cho cùng event
- Không include app name/icon (system tự thêm)

---

## A3. Patterns & Inputs

### A3.1 Entering Data

- **Prefer selection over typing** — dùng picker/menu thay text field khi có thể
- **Leverage system data** — dùng autofill APIs (`UITextContentType`)
- **Provide sensible defaults** — pre-populate probable values
- **Validate dynamically** — validate ngay sau khi nhập
- **Show appropriate keyboard** — email keyboard cho email, phone cho phone

### A3.2 Searching

- Dùng search bar (không plain text field)
- Styles: Prominent (primary function) / Minimal (infrequent search)
- Support search suggestions, tokens, scope bars
- Show results as users type khi có thể

### A3.3 Managing Accounts

- **Delay sign-in** — let users explore before requiring account
- **Auth hierarchy:** Sign in with Apple > Passkeys > Passwords
- **Account deletion MANDATORY** nếu cho tạo account
- Nếu có third-party sign-in, PHẢI có Sign in with Apple

### A3.4 Loading

- Show screen immediately — dùng placeholder text/graphics
- Replace placeholders progressively as content loads
- Preload upcoming content during non-critical moments
- Determinate (progress bar) > Indeterminate (spinner)
- Activity indicator PHẢI luôn quay — stationary = stalled

### A3.5 Notifications

- Banner (auto-dismiss) / Alert (manual dismiss)
- Nội dung: complete sentences, sentence case, proper punctuation
- Không include app name/icon (system tự thêm)
- Không gửi multiple notifications cho cùng event
- Max 4 action buttons
- Custom sounds: short, distinctive, professionally produced

### A3.6 Gestures

| Gesture | Action |
|---------|--------|
| Tap | Activate control / select item |
| Drag | Move element |
| Flick | Scroll/pan quickly |
| Swipe | Back navigation / reveal actions |
| Double tap | Zoom in/out |
| Pinch | Zoom in (outward) / out (inward) |
| Long press | Additional options / rearrangement |
| Shake | Undo/redo |
| 3-finger pinch in/out | Copy/paste text |
| 3-finger swipe L/R | Undo/redo |

**KHÔNG chặn system gestures** (bottom edge = Home, top edge = Control Center)

### A3.7 Haptics

3 feedback types:
- **Impact** (Light/Medium/Heavy): physical collisions, snapping
- **Selection**: change in selection (picker scrolling)
- **Notification** (success/warning/error): task outcomes

Reserve haptics cho significant moments — excessive haptics gây overwhelming

### A3.8 Keyboard Navigation

- Support keyboard-only interaction
- Full Keyboard Access mode: navigate ALL elements via keyboard
- Tab di chuyển giữa focus groups; arrow keys navigate trong group
- Standard shortcuts: Cmd+C/V/Z, etc.

---

## A4. Technologies & Platform

### A4.1 Widgets

| Family | Size (pt) |
|--------|-----------|
| systemSmall | 169×169 (2×2) |
| systemMedium | 360×169 (4×2) |
| systemLarge | 360×376 (4×4) |
| systemExtraLarge | iPad only |

Min touch target trong widget: 44×44pt

### A4.2 Live Activities & Dynamic Island

- Compact: height 36px, icon 24px, text 15pt
- Expanded: max height 144pt
- Lock Screen truncation: 160pt

### A4.3 visionOS

- Primary input: eyes + hands (indirect gesture)
- Min target: 60pt
- Hover effect BẮT BUỘC trên tất cả interactive elements
- Privacy: no raw eye-tracking data exposed to apps

### A4.4 Sign in with Apple

- Button height: 44pt default
- Corner radius: 0–50
- PHẢI offer nếu có third-party sign-in

---

# PHẦN B: GOOGLE MATERIAL DESIGN 3

## B1. Color System & HCT

### B1.1 HCT Color Space

**Dimensions:**
- **Hue (H):** 0–360 (circular)
- **Chroma (C):** 0–~120 (0 = grey, higher = more colorful)
- **Tone (T):** 0–100 (0 = black, 100 = white, = L* trong CIELAB)

**Key advantage:** Tone difference ↔ contrast ratio trực tiếp:
- Δtone ~50 ≈ 4.5:1 contrast (WCAG AA)
- Tones 30 vs 98 ≈ 7:1 contrast
- Tones 50 vs 98 ≈ 3:1 contrast

### B1.2 Dynamic Color

Từ 1 source color → 5 tonal palettes → 13 tones mỗi palette:

| Palette | Đặc điểm |
|---------|----------|
| Primary | High chroma — main accent |
| Secondary | Moderate chroma — supporting |
| Tertiary | Contrasting hue — additional accent |
| Neutral | Very low chroma — backgrounds |
| Neutral Variant | Slightly more chroma — outlines |

**13 Tones:** 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100

### B1.3 Complete Color Role Mapping

#### Accent Colors

| Role | Palette | Light Tone | Dark Tone |
|------|---------|-----------|----------|
| primary | primary | 40 | 80 |
| onPrimary | primary | 100 | 20 |
| primaryContainer | primary | 90 | 30 |
| onPrimaryContainer | primary | 30 | 90 |
| inversePrimary | primary | 80 | 40 |
| secondary | secondary | 40 | 80 |
| onSecondary | secondary | 100 | 20 |
| secondaryContainer | secondary | 90 | 30 |
| onSecondaryContainer | secondary | 30 | 90 |
| tertiary | tertiary | 40 | 80 |
| onTertiary | tertiary | 100 | 20 |
| tertiaryContainer | tertiary | 90 | 30 |
| onTertiaryContainer | tertiary | 30 | 90 |
| error | error | 40 | 80 |
| onError | error | 100 | 20 |
| errorContainer | error | 90 | 30 |
| onErrorContainer | error | 30 | 90 |

#### Surface & Neutral Colors

| Role | Palette | Light Tone | Dark Tone |
|------|---------|-----------|----------|
| surface | neutral | 98 | 6 |
| onSurface | neutral | 10 | 90 |
| surfaceDim | neutral | 87 | 6 |
| surfaceBright | neutral | 98 | 24 |
| surfaceContainerLowest | neutral | 100 | 4 |
| surfaceContainerLow | neutral | 96 | 10 |
| surfaceContainer | neutral | 94 | 12 |
| surfaceContainerHigh | neutral | 92 | 17 |
| surfaceContainerHighest | neutral | 90 | 22 |
| surfaceVariant | neutralVariant | 90 | 30 |
| onSurfaceVariant | neutralVariant | 30 | 80 |
| outline | neutralVariant | 50 | 60 |
| outlineVariant | neutralVariant | 80 | 30 |

#### Utility Colors

| Role | Light Tone | Dark Tone |
|------|-----------|----------|
| inverseSurface | 20 | 90 |
| inverseOnSurface | 95 | 20 |
| surfaceTint | 40 (primary) | 80 (primary) |
| shadow | 0 | 0 |
| scrim | 0 | 0 |

### B1.4 State Layer Opacity

| State | Opacity | Color Source |
|-------|---------|-------------|
| Hover | 8% | content/on-color |
| Focus | 10% | content/on-color |
| Pressed | 10% | content/on-color |
| Dragged | 16% | content/on-color |
| Disabled container | 12% | on-surface |
| Disabled content | 38% | on-surface |

### B1.5 Dark Theme

- Surface: tone 98 (light) → 6 (dark)
- Accent colors swap tới lighter tones (primary 40→80)
- **Tonal elevation** thay vì shadow elevation trong dark mode
- Surface container scale: 4 → 10 → 12 → 17 → 22

---

## B2. Typography

### B2.1 Complete Type Scale

| Role | Size (sp) | Line Height | Weight | Letter Spacing |
|------|-----------|-------------|--------|---------------|
| Display Large | 57 | 64 | 400 | -0.25 |
| Display Medium | 45 | 52 | 400 | 0 |
| Display Small | 36 | 44 | 400 | 0 |
| Headline Large | 32 | 40 | 400 | 0 |
| Headline Medium | 28 | 36 | 400 | 0 |
| Headline Small | 24 | 32 | 400 | 0 |
| Title Large | 22 | 28 | 400 | 0 |
| Title Medium | 16 | 24 | 500 | 0.15 |
| Title Small | 14 | 20 | 500 | 0.1 |
| Body Large | 16 | 24 | 400 | 0.5 |
| Body Medium | 14 | 20 | 400 | 0.25 |
| Body Small | 12 | 16 | 400 | 0.4 |
| Label Large | 14 | 20 | 500 | 0.1 |
| Label Medium | 12 | 16 | 500 | 0.5 |
| Label Small | 11 | 16 | 500 | 0.5 |

**Default font:** Roboto. Weight patterns: Regular (400) cho Display/Headline/Body, Medium (500) cho Title Medium/Small/Label.

### B2.2 Roboto Flex Variable Axes

| Axis | Tag | Min | Default | Max |
|------|-----|-----|---------|-----|
| Weight | wght | 100 | 400 | 1000 |
| Width | wdth | 25 | 100 | 151 |
| Optical Size | opsz | 8 | 14 | 144 |
| Grade | GRAD | -200 | 0 | 150 |

**Grade (GRAD):** Thay đổi stroke thickness KHÔNG thay đổi character width — line breaks giữ nguyên. Hữu ích cho hover/focus states và dark mode.

### B2.3 Responsive Typography

- Không prescribe auto font-size changes across breakpoints
- Giữ text **40–60 characters per line** across breakpoints
- Layout adapts (reflow, reposition) thay vì type scale thay đổi

---

## B3. Components

### B3.1 Buttons

**Size Scale (M3 Expressive):**

| Size | Height |
|------|--------|
| XS | 32dp |
| S (default) | 36dp |
| M | 40dp |
| L | 48dp |
| XL | 56dp |

**5 Types (high → low emphasis):**
1. **Filled**: `primary` bg, `onPrimary` text — final/important actions
2. **Filled Tonal**: `secondaryContainer` bg — secondary actions
3. **Elevated**: `surface` bg + shadow — layered surfaces
4. **Outlined**: transparent + `outline` border — medium emphasis
5. **Text**: transparent — tertiary actions

**Common specs:**
- Corner: Full (pill shape)
- Icon size: 18dp (baseline), 20dp (Expressive)
- Icon-to-label spacing: 8dp
- Min touch target: 48dp
- Text case: Sentence case (KHÔNG ALL CAPS)
- Padding: 24dp LR (text only), 16dp L / 24dp R (with icon)

### B3.2 Cards

**3 Types:**

| Type | Elevation | Container |
|------|-----------|-----------|
| Elevated | 1dp | `surface-container-low` |
| Filled | 0dp | `surface-container-highest` |
| Outlined | 0dp | `surface` + 1dp outline |

- Corner radius: 12dp (`corner-medium`)
- Content padding: 16dp
- Dragged elevation: 8dp
- Outline stroke: 1dp `outline-variant`

### B3.3 Navigation

**Navigation Bar (bottom):**
- Height: 80dp (M3), 64dp (M3 Expressive)
- Active indicator: 56×32dp, pill shape
- 3–5 destinations
- Container: `surface-container`

**Navigation Rail (side):**
- Width: 80dp (M3), 96dp (Expressive)
- 3–7 destinations
- FAB integration

**Navigation Drawer:**
- Max width: 280dp (standard), 360dp (modal)
- Corner: 16dp
- Item shape: pill (50% corner)

### B3.4 Text Fields

- Recommended width: 245dp
- 2 styles: Filled / Outlined
- Stroke: 1dp (enabled), 2dp (focused)
- Min touch target: 48dp

### B3.5 Tabs

- Height: 48dp
- Min width: 72dp
- Indicator: 2dp
- Elastic animation: 250ms

### B3.6 Chips

**4 types:**
- Assist: trigger actions
- Filter: checkable, filter content
- Input: removable, user-entered data
- Suggestion: dynamic suggestions

**Specs:** Min height 32dp, corner 8dp, icon 18dp, spacing 8dp

### B3.7 Dialogs

- Corner: 28dp
- Horizontal margin: ≥24dp
- Vertical margin: ≥80dp
- Internal padding: 24dp
- Scrim: 32% black
- Container: `surface-container-high`
- Max 2 action buttons in basic dialog

### B3.8 Bottom Sheets

- Max width: 640dp
- Top corner: 28dp
- Drag handle: 32×4dp
- Scrim (modal): 32%
- Standard peek height: 100dp

### B3.9 FABs

| Size | Dimensions | Icon | Corner |
|------|-----------|------|--------|
| Standard | 56×56dp | 24dp | 16dp |
| Medium | 80×80dp | 24dp | Large |
| Large | 96×96dp | 36dp | 28dp |
| Extended | 56dp height | 24dp + label | 16dp |

Default elevation: 6dp, hover: 8dp

### B3.10 Lists

| Lines | Height |
|-------|--------|
| 1-line | 48dp (dense: 40dp) |
| 2-line | 72dp |
| 3-line | 88dp |

Leading avatar: 40dp, leading image: 56×56dp, item padding: 16dp LR

### B3.11 Menus

- Item height: 48dp (mobile), 32dp (desktop)
- Container elevation: 3dp
- Top/bottom padding: 8dp

### B3.12 Checkboxes

- Container: 18dp
- State layer: 40dp
- Touch target: 48dp
- Corner: 2dp
- Selected fill: `primary`

### B3.13 Switch

- Track: 52×32dp
- Thumb: 16dp (unchecked), 24dp (checked), 28dp (pressed)

### B3.14 Badges

- Small (dot): 6×6dp
- Large (count): 16dp height, 16dp min width
- Color: `error` bg, `on-error` text

### B3.15 Snackbar

- Min height: 48dp
- Corner: 4dp
- LENGTH_SHORT ~4s, LENGTH_LONG ~10s

### B3.16 Top App Bar

| Size | Height |
|------|--------|
| Small | 64dp |
| Medium | 112dp |
| Large | 152dp |

Scroll behaviors: noScroll, scroll, exitUntilCollapsed, snap

### B3.17 Search

- Bar height: 56dp
- Corner: 28dp

### B3.18 Slider

- Track height: 16dp
- Thumb: 4×44dp

### B3.19 Progress

- Linear track: 4dp height
- Circular: 40dp diameter

### B3.20 Carousel

| Strategy | Description |
|----------|-------------|
| Hero | 1 large + 1-2 small items |
| Multi-browse | Large + medium + small |
| Uncontained | Fixed-size, clip at edges |
| Full-screen | 1 item at a time |

Container corner: 28dp, small item min width: 40dp

### B3.21 Dividers

- Regular: 1dp, Heavy: 8dp
- Color: `outline-variant`
- Full-bleed / Inset (16dp) / Middle (16dp both sides)

### B3.22 Date Pickers

- Variants: Docked, Modal, Modal Date Input, Modal Range
- Container corner: 28dp
- Day cell touch target: 48dp, visual: 40dp
- Today: `primary` stroke 1dp
- Selected: `primary` fill

---

## B4. Motion & Animation

### B4.1 Easing Curves

| Easing | CSS cubic-bezier |
|--------|-----------------|
| Emphasized | cubic-bezier(0.2, 0, 0, 1) |
| Emphasized Decelerate | cubic-bezier(0.05, 0.7, 0.1, 1) |
| Emphasized Accelerate | cubic-bezier(0.3, 0, 0.8, 0.15) |
| Standard | cubic-bezier(0.2, 0, 0, 1) |
| Standard Decelerate | cubic-bezier(0, 0, 0, 1) |
| Standard Accelerate | cubic-bezier(0.3, 0, 1, 1) |
| Linear | cubic-bezier(0, 0, 1, 1) |

### B4.2 Duration Tokens

| Token | Duration |
|-------|----------|
| Short 1–4 | 50, 100, 150, 200ms |
| Medium 1–4 | 250, 300, 350, 400ms |
| Long 1–4 | 450, 500, 550, 600ms |
| Extra Long 1–4 | 700, 800, 900, 1000ms |

### B4.3 Spring Physics (M3 Expressive)

**Spatial Springs (position, size, rotation — có bounce):**

| Type | Damping | Stiffness |
|------|---------|-----------|
| Fast Spatial | 0.9 | 1400 |
| Default Spatial | 0.9 | 700 |
| Slow Spatial | 0.9 | 300 |

**Effects Springs (color, opacity — critically damped, không bounce):**

| Type | Damping | Stiffness |
|------|---------|-----------|
| Fast Effects | 1.0 | 3800 |
| Default Effects | 1.0 | 1600 |
| Slow Effects | 1.0 | 800 |

### B4.4 Transition Patterns

| Transition | Duration | Use Case |
|-----------|----------|----------|
| Container Transform | 300ms/250ms | Hero moments — 1 element → another |
| Shared Axis | 300ms | Forward/backward navigation |
| Fade Through | 300ms | No spatial relationship |
| Fade | 150ms/75ms | Single element enter/exit |

### B4.5 Ripple Effect

- M3: subtle sparkle (thay wave của M2)
- Pressed opacity: 12%
- Enter duration: ~450ms (Android), ~150ms (web)

### B4.6 prefers-reduced-motion

- Dùng subtle fades thay sliding/scaling
- Disable: parallax, shape morphing, decorative motion
- Keep: essential feedback (state changes), simplify to opacity-only
- CSS: `@media (prefers-reduced-motion: reduce)`

### B4.7 CSS Custom Properties

```css
--md-sys-motion-easing-emphasized: cubic-bezier(0.2, 0, 0, 1);
--md-sys-motion-easing-emphasized-decelerate: cubic-bezier(0.05, 0.7, 0.1, 1);
--md-sys-motion-easing-emphasized-accelerate: cubic-bezier(0.3, 0, 0.8, 0.15);
--md-sys-motion-easing-standard: cubic-bezier(0.2, 0, 0, 1);
--md-sys-motion-easing-standard-decelerate: cubic-bezier(0, 0, 0, 1);
--md-sys-motion-easing-standard-accelerate: cubic-bezier(0.3, 0, 1, 1);

--md-sys-motion-duration-short1: 50ms;
--md-sys-motion-duration-short2: 100ms;
--md-sys-motion-duration-short3: 150ms;
--md-sys-motion-duration-short4: 200ms;
--md-sys-motion-duration-medium1: 250ms;
--md-sys-motion-duration-medium2: 300ms;
--md-sys-motion-duration-medium3: 350ms;
--md-sys-motion-duration-medium4: 400ms;
--md-sys-motion-duration-long1: 450ms;
--md-sys-motion-duration-long2: 500ms;
--md-sys-motion-duration-long3: 550ms;
--md-sys-motion-duration-long4: 600ms;
--md-sys-motion-duration-extra-long1: 700ms;
--md-sys-motion-duration-extra-long2: 800ms;
--md-sys-motion-duration-extra-long3: 900ms;
--md-sys-motion-duration-extra-long4: 1000ms;
```

---

## B5. Adaptive Design

### B5.1 Window Size Classes

| Class | Width | Typical Devices |
|-------|-------|----------------|
| Compact | <600dp | Phone portrait |
| Medium | 600–839dp | Tablet portrait, foldable |
| Expanded | 840–1199dp | Tablet landscape, desktop |
| Large | 1200–1599dp | Desktop |
| Extra-Large | ≥1600dp | Ultra-wide |

### B5.2 Navigation by Breakpoint

| Width | Component |
|-------|-----------|
| <600dp (Compact) | Navigation Bar (bottom), 3–5 items |
| 600–839dp (Medium) | Navigation Rail (side), 3–7 items |
| 840dp+ (Expanded) | Navigation Rail expanded / Drawer |
| 1200dp+ (Large) | Permanent Navigation Drawer, 280dp |

### B5.3 Canonical Layouts

- **List-Detail:** 2 panes side-by-side (compact: single pane with back nav)
- **Supporting Pane:** Primary ~2/3 + secondary ~1/3
- **Feed:** Configurable grid, 1 column compact → N columns wider

### B5.4 Grid System

- Baseline grid: 8dp layout, 4dp sub-elements
- Columns: flexible count by breakpoint
- Text: 40–60 characters per line
- Touch target min: 48×48dp all platforms

### B5.5 Foldable Devices

- Flat / Half-opened Tabletop / Half-opened Book
- Tránh interactive elements gần fold
- Text overlaying fold khó đọc
- Position dialogs không overlay fold

---

## B6. Inclusive Design

### B6.1 Core Framework

- "Build with, not for" — involve affected communities
- "Who else?" — hỏi suốt quá trình phát triển
- Embed equity vào tất cả activities

### B6.2 Emerging Markets

**Connectivity:**
- 95% dùng prepaid data, nhiều người chỉ 250MB/tháng
- Internet cost tới 11% thu nhập (Uganda)
- Thiết kế offline-first

**Device constraints:**
- Test ở 480×800px và màn hình <4 inch
- Typical devices $40–60, 512MB RAM
- Older OS, limited storage

**Low literacy:**
- Minimize text inputs
- Pair text with images/icons
- Offer voice input, autocomplete

**Aesthetics:**
- Minimal Western design (white space, muted colors) bị reject
- Users prefer feature-dense design

### B6.3 Accessibility

| Element | Min Ratio |
|---------|-----------|
| Normal text | 4.5:1 |
| Large text (18px+ / 14px+ bold) | 3.0:1 |
| UI components | 3.0:1 |
| Touch target | 48×48dp |

- Never rely solely on color — supplement với bold, strokes, patterns
- 5%+ male population colorblind
- 80% people with disabilities live in emerging markets
- Support magnification tới 200%

---

## B7. Design Practices

### B7.1 M3 Expressive (2025)

Backed bởi 46 studies với 18,000+ participants:
- 87% users 18–24 prefer expressive design
- Users spot key UI elements **4x faster** with expressive
- 32% increase brand relevance, 34% boost modernity
- 35 new shapes với built-in shape morphing
- Spring-based physics motion system
- 15 new/updated components

### B7.2 Design Sprints

5-day process: Understand → Sketch → Decide → Prototype → Validate

### B7.3 Material Symbols

**4 variable axes:**

| Axis | Range |
|------|-------|
| FILL | 0–1 |
| Weight (wght) | 100–700 |
| Grade (GRAD) | -50 to 200 |
| Optical Size (opsz) | 20–48dp |

3 styles: Outlined, Rounded, Sharp

**Performance:** Full file 295KB (3,800+ icons). Subset via `&icon_names` — 3 icons ≈ 1.7KB

### B7.4 Google Fonts

- **Variable fonts:** 1 file thay nhiều static weight files
- **Subsetting:** giảm 70%+ file size
- `font-display: swap` prevents invisible text
- Max 2 font families per site
- **Vietnamese:** Source Sans Pro, Be Vietnam Pro
- Preconnect: `<link rel="preconnect" href="https://fonts.googleapis.com">`

### B7.5 Design Tokens

3-tier hierarchy:
1. **Reference tokens** (`--md-ref-*`): concrete values
2. **System tokens** (`--md-sys-*`): design decisions
3. **Component tokens** (`--md-comp-*`): per-component

### B7.6 Shape System

| Token | Value |
|-------|-------|
| None | 0dp |
| Extra Small | 4dp |
| Small | 8dp |
| Medium | 12dp |
| Large | 16dp |
| Extra Large | 28dp |
| Full | 9999dp (pill) |

### B7.7 Elevation System

| Level | dp | Usage |
|-------|-----|-------|
| 0 | 0 | Flat components |
| 1 | 1 | Elevated cards, sheets |
| 2 | 3 | Navigation bar, menus |
| 3 | 6 | FABs, dialogs |
| 4 | 8 | Hover states |
| 5 | 12 | Highest emphasis |

---

# PHẦN C: FIGMA

## C1. Design Fundamentals

### C1.1 Frames vs Groups

| Property | Frame | Group |
|----------|-------|-------|
| Dimensions | Explicit | Derived from children |
| Clip content | Yes | No |
| Fill/Stroke | Yes | No |
| Auto layout | Yes | No |
| Layout grids | Yes | No |
| Constraints | Children can have | Cannot apply |
| Prototyping | Yes | No |
| Corner radius | Yes | No |

**Shortcuts:** Frame `F`/`A`, wrap `Ctrl+Alt+G`, Group `Ctrl+G`, Ungroup `Shift+Ctrl+G`

### C1.2 Auto Layout

**Shortcut:** Add `Shift+A`, Remove `Alt+Shift+A`

**3 flow directions:** Horizontal, Vertical, Grid (with span support)

**Spacing:** Numeric value hoặc Auto (space-between)

**Padding:** Uniform / V-H / Individual. CSS shorthand: `Ctrl` + click, type `1,2,3,4`

**Sizing:**
- **Hug contents:** frame shrinks to fit children
- **Fill container:** child stretches to fill parent
- **Fixed:** explicit dimension
- Min/Max dimensions available

**Alignment:** 9-point grid. Baseline alignment: `B` key

**Absolute positioning:** `Ctrl` + drag child opts out of flow

### C1.3 Constraints

| Constraint | Behavior |
|-----------|----------|
| Left/Top | Maintain distance from left/top (default) |
| Right/Bottom | Maintain distance from right/bottom |
| Left and Right | Maintain both; layer may grow/shrink |
| Center | Maintain relative to center |
| Scale | Proportional to parent |

`Ctrl` while resizing = bypass constraints temporarily

### C1.4 Layout Grids

3 types: Uniform Grid, Columns, Rows

Toggle: `Shift+G`. Multiple grids per frame. Saveable as styles.

**8-point grid:** Hard grid = uniform size 8. Soft grid = columns/rows divisible by 8.

### C1.5 Vector Networks

- Paths can branch in multiple directions from any point
- Any point connects to any other (unlike traditional Bezier)
- **Paint/Bucket tool** (`Shift+B`): fill closed regions
- **Variable Width tool:** modify stroke width at any point
- **Boolean operations:** Union (`Alt+Shift+U`), Subtract (`Alt+Shift+S`), Intersect (`Alt+Shift+I`), Exclude (`Alt+Shift+E`)
- **Flatten** (`Ctrl+E`): destructive — converts to single path

### C1.6 Text

**Resizing modes:**
- **Auto width:** grows with content, no wrapping
- **Auto height:** height adjusts, text wraps at container width
- **Fixed:** both fixed, may overflow

**Features:** Dynamic Type, variable fonts, OpenType, ligatures, stylistic sets, fractions, slashed zero

**Truncation:** Enable Truncate text + set Max lines

### C1.7 Color

**Models:** HEX (default), RGB, HSB, HSL, CSS

**Profiles:** sRGB (default, most supported) / Display P3 (49% more colors)

**WCAG contrast check:** Built into color picker. Click indicator to auto-correct.

**Gradients:** Linear, Radial, Angular, Diamond. Multiple stops per gradient.

### C1.8 Effects

Per-layer max: 8 drop shadows, 8 inner shadows, 1 layer blur, 1 background blur, 2 noise, 1 texture, 1 glass

**Drop shadow:** X, Y, Blur, Spread, Color+Opacity

**Glass effect:** Light angle/intensity, Refraction, Depth, Dispersion, Frost, Splay. Incompatible with SVG export.

### C1.9 Blend Modes

19 blend modes: Pass through, Normal, Darken, Multiply, Plus darker, Color burn, Lighten, Screen, Plus lighter, Color dodge, Overlay, Soft light, Hard light, Difference, Exclusion, Hue, Saturation, Color, Luminosity

### C1.10 Images

Fill modes: Fill (cover), Fit (contain), Crop, Tile

Adjustment filters: Exposure, Contrast, Saturation, Temperature, Tint, Highlights, Shadows

### C1.11 Masks

3 types: Alpha (default), Vector, Luminance

Shortcut: `Ctrl+Alt+M`

### C1.12 Export

| Format | Type | Transparency | Best For |
|--------|------|-------------|---------|
| PNG | Raster, lossless | Yes | Logos, charts, UI assets |
| JPG | Raster, lossy | No | Photos |
| SVG | Vector | Yes | Responsive, icons |
| PDF | Fixed layout | N/A | Print, docs |

Scale: 0.5x, 1x, 2x, 3x, 4x, custom, fixed width/height

Bulk export: `Shift+Ctrl+E`

---

## C2. Design Systems

### C2.1 Variables

**6 types:** Color, Number, String, Boolean, Timing, Easing

**Limits:** 5,000 per collection, 40 modes per collection (API)

**Scoping:** Restrict where variables apply

**Aliasing:** Foundation of 3-tier token hierarchy (primitive → semantic → component)

**Groups:** `/` separator naming

**CSS output:** `var(--variable-name, fallback)`

**Limitations:** No gradients, composite shadows, typography composites

### C2.2 Styles vs Variables

- Styles: reusable visual properties (fills, strokes, effects, text)
- Variables: dynamic values switchable between modes
- Variables preferred for design tokens; Styles for complex visual properties

### C2.3 Components

**Properties:** Boolean, Instance swap, Text, Variant

**Variants naming:** `componentName/property1value/property2value`

### C2.4 Libraries

- Publishing + updates (blue badge)
- Analytics (Org/Enterprise)
- Branching/merging
- Multi-library architecture: tokens → core components → patterns → icons → platform-specific

### C2.5 Design Tokens Best Practices

3-tier hierarchy matching CSS custom properties:
1. **Primitive:** raw values (colors, sizes)
2. **Semantic:** role-based (primary, surface, body-text)
3. **Component:** specific element (button-bg, card-border)

---

## C3. Prototyping

### C3.1 Triggers (12 types)

On Click, On Drag, While Hovering, While Pressing, Keyboard/Gamepad, Mouse Enter, Mouse Leave, Mouse Down, Mouse Up, After Delay, When Video Hits, When Video Ends

### C3.2 Actions (14 types)

Navigate to, Back, Open Overlay, Close Overlay, Swap Overlay, Scroll to, Open Link, Set Variable, Set Variable Mode, Conditional, Change to, Play/Pause Video, Mute/Unmute Video, Set to Specific Time

Multiple actions per trigger. Sequential execution.

### C3.3 Animations (7 transitions)

| Transition | Behavior |
|-----------|----------|
| Instant | No animation |
| Dissolve | Fade in/out |
| Smart Animate | Match layers by name, animate differences |
| Move In/Out | Slide in/out |
| Push | Push current, slide in new |
| Slide In/Out | Offset + dissolve |

### C3.4 Easing

**7 Bezier presets:** Linear, Ease In, Ease Out, Ease In And Out, Ease In Back, Ease Out Back, Ease In And Out Back

**4 Spring presets:** Gentle, Quick, Bouncy, Slow (configurable Stiffness, Damping, Mass)

**Custom:** cubic-bezier(x1, y1, x2, y2), CSS-compatible

### C3.5 Smart Animate

Matches layers by name + hierarchy. Animatable: position, scale, rotation, opacity, fill, texture, noise, blur. NOT: drop shadow, inner shadow, shape morphing.

### C3.6 Variables in Prototyping

- Set Variable action: modify values via expressions
- Conditional action: if/else branching
- Expressions: `+`, `-`, `*`, `/`, `==`, `!=`, `>`, `<`, `and`, `or`, `not`
- Binding: variables → component variants, layer properties, visibility

### C3.7 Overflow Scrolling

Vertical / Horizontal / Both / None

Scroll position: Scroll with parent / Fixed / Sticky

### C3.8 Interactive Components

- Built on variants within component sets
- **Change To** action switches variants
- Interactions propagate to all instances
- State memorization: components retain last-set variant

---

## C4. Dev Mode & Handoff

### C4.1 Inspect Panel

Code generation:
- **Web:** CSS (px, rem)
- **iOS:** SwiftUI, UIKit (pt)
- **Android:** Compose, XML (dp, sp)

Variables appear in code snippets as valid variable names.

### C4.2 Measurements & Annotations

- Measurements: `Shift+M` — saveable, repositionable
- Annotations: `Shift+T` — 4 categories (Development, Interaction, Accessibility, Content)
- Custom categories with colors

### C4.3 Ready for Dev

3 statuses: Ready for Dev / Completed (Org/Enterprise) / Changed (auto-triggered)

Notifications via email, desktop, mobile, Slack, Teams.

### C4.4 Code Connect

Links codebase components to Figma design components:
- **CLI:** local repo, API token, deeper integration
- **UI:** inside Figma, connects GitHub, no local install

### C4.5 Figma for VS Code

- Browse frames by section/status/page
- View code snippets
- Auto-complete suggestions
- Dev Resources tab
- Real-time comment notifications

### C4.6 MCP Server

Generally available 2025. Connects Figma to AI tools (Claude Code, Cursor, VS Code). Write to Canvas + Code to Canvas.

### C4.7 Collaboration

- **Comments:** threaded, @mentions, emoji, attachments (max 5), 100/hour rate limit
- **Cursor Chat:** `/` to activate, ephemeral (5s), max 52 chars
- **Audio Chat:** in-file voice collaboration
- **Version History:** auto-save 30min, named versions `Ctrl+Alt+S`
- **Branching:** Org/Enterprise only, review process, conflict resolution

### C4.8 AI Features (2025–2026)

- **Figma Agent:** text → editable designs, design discovery, rename layers, add interactions
- **Figma Make:** prompt → prototype → web app
- **Figma Motion:** timeline, keyframes, easing variables, spring animations (open beta)
- **Weave Tools:** AI image editing, vector, video, audio on canvas
- **Code Layers:** working code as editable layers (closed beta)
- **3D Transforms:** coming soon

---

# PHẦN D: CROSS-REFERENCE & ÁP DỤNG CHO VINHLONG360

## D1. Touch Target Consensus

| Source | Min Target |
|--------|-----------|
| Apple HIG | 44×44pt |
| Google M3 | 48×48dp |
| WCAG 2.2 | 24×24px (Level AA), 44×44px (recommended) |
| **vinhlong360 nên dùng** | **44×44px min** (consensus safe) |

## D2. Color Contrast Consensus

| Rule | Apple | Google | WCAG |
|------|-------|--------|------|
| Normal text | 4.5:1 | 4.5:1 | 4.5:1 (AA) |
| Large text | 3:1 | 3:1 | 3:1 (AA) |
| Non-text / UI | 3:1 | 3:1 | 3:1 (AA) |

## D3. Typography Scale Mapping (M3 → CSS)

| M3 Role | Size | CSS Suggestion |
|---------|------|---------------|
| Display Large | 57sp | `--text-display-lg: 3.5625rem` |
| Headline Small | 24sp | `--text-headline-sm: 1.5rem` |
| Title Medium | 16sp | `--text-title-md: 1rem` |
| Body Large | 16sp | `--text-body-lg: 1rem` |
| Body Medium | 14sp | `--text-body-md: 0.875rem` |
| Label Large | 14sp | `--text-label-lg: 0.875rem` |
| Label Small | 11sp | `--text-label-sm: 0.6875rem` |

## D4. Motion System (CSS Variables)

```css
/* Easing — lấy từ M3 */
--ease-emphasized: cubic-bezier(0.2, 0, 0, 1);
--ease-decelerate: cubic-bezier(0.05, 0.7, 0.1, 1);
--ease-accelerate: cubic-bezier(0.3, 0, 0.8, 0.15);
--ease-standard: cubic-bezier(0.2, 0, 0, 1);

/* Duration — lấy từ M3 */
--duration-short: 150ms;   /* Short 3 */
--duration-medium: 300ms;  /* Medium 2 */
--duration-long: 500ms;    /* Long 2 */

/* prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## D5. Spacing Scale (8pt grid, M3 + Apple consensus)

```css
--space-1: 4px;   /* sub-grid */
--space-2: 8px;   /* base unit */
--space-3: 12px;
--space-4: 16px;  /* standard padding */
--space-5: 20px;
--space-6: 24px;  /* section spacing */
--space-8: 32px;
--space-10: 40px;
--space-12: 48px; /* large spacing */
--space-16: 64px;
```

## D6. Corner Radius Scale (M3 shape tokens → CSS)

```css
--radius-none: 0;
--radius-xs: 4px;    /* Extra Small */
--radius-sm: 8px;    /* Small — chips, small cards */
--radius-md: 12px;   /* Medium — cards, dialogs */
--radius-lg: 16px;   /* Large — FABs, drawers */
--radius-xl: 28px;   /* Extra Large — sheets */
--radius-full: 9999px; /* Pill — buttons, badges */
```

## D7. Breakpoints (M3 Window Size Classes → CSS)

```css
/* Mobile-first */
--bp-compact: 0;        /* < 600px: single column */
--bp-medium: 600px;     /* tablet: 2 columns */
--bp-expanded: 840px;   /* desktop: 3 columns */
--bp-large: 1200px;     /* wide desktop */
```

## D8. Elevation (CSS box-shadow mapping)

```css
--elevation-0: none;
--elevation-1: 0 1px 2px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.15);
--elevation-2: 0 1px 2px rgba(0,0,0,0.3), 0 2px 6px rgba(0,0,0,0.15);
--elevation-3: 0 4px 8px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.15);
--elevation-4: 0 6px 10px rgba(0,0,0,0.3), 0 2px 3px rgba(0,0,0,0.15);
--elevation-5: 0 8px 12px rgba(0,0,0,0.3), 0 4px 4px rgba(0,0,0,0.15);
```

## D9. State Layers (M3 → CSS)

```css
/* Interactive state overlays */
--state-hover: 0.08;    /* 8% opacity */
--state-focus: 0.10;    /* 10% opacity */
--state-pressed: 0.10;  /* 10% opacity */
--state-dragged: 0.16;  /* 16% opacity */
--state-disabled-bg: 0.12;
--state-disabled-fg: 0.38;
```

## D10. Key Recommendations for vinhlong360

1. **Font:** Be Vietnam Pro (Google Fonts, Vietnamese-optimized) + variable font subsetting
2. **Font subsetting:** giảm 70%+ file size. `font-display: swap` cho CWV
3. **Material Symbols subset:** 3 icons ≈ 1.7KB (vs 295KB full)
4. **Touch targets:** 44×44px minimum — quan trọng cho outdoor mobile
5. **Offline-first patterns:** emerging market users, prepaid data
6. **Test ở 480×800px** — device constraints Vietnam
7. **Never rely solely on color** — supplement bold/strokes/patterns
8. **40–60 chars per line** — responsive typography
9. **Constrain ML/AI zones** — preserve navigation predictability
10. **8pt grid** — consensus spacing system Apple + Google

---

*Tài liệu này là tham chiếu thiết kế tĩnh. Không chứa code implementation. Sử dụng cùng `docs/design-research-2026-06-27.md` cho context đầy đủ.*
