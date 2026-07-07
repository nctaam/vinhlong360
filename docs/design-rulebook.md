# Design Rulebook - vinhlong360

> **STATUS (2026-07-07): active — đã truth-sync.** Rules remain in force EXCEPT where marked with an APPROVED EXCEPTION / PROJECT DECISION note (R1.3 homepage hero, R4.3/R4.4/R4-AP2/R10.12 cinematic hero motion, R6 navigation, R11.12 noindex, R15.2 sentence rhythm) — those reflect owner-approved shipped decisions that override the original audit text.

Audit date: 2026-06-29  
Scope: Nuxt frontend, API-rendered content, JSON-LD, design tokens, accessibility, performance, Vietnamese travel UX.  
Rule style: every rule is written for an AI coding assistant to apply automatically before writing code.

## Table Of Contents

- [Source Keys](#source-keys)
- [Vietnam Context](#vietnam-context)
- [R1 Spacing](#r1-spacing)
- [R2 Typography](#r2-typography)
- [R3 Color](#r3-color)
- [R4 Motion](#r4-motion)
- [R5 Components](#r5-components)
- [R6 Navigation](#r6-navigation)
- [R7 Forms](#r7-forms)
- [R8 Images](#r8-images)
- [R9 Dark Mode](#r9-dark-mode)
- [R10 Accessibility](#r10-accessibility)
- [R11 SEO](#r11-seo)
- [R12 Performance](#r12-performance)
- [R13 Responsive](#r13-responsive)
- [R14 States](#r14-states)
- [R15 Content](#r15-content)
- [Appendix A Token Audit](#appendix-a-token-audit)
- [Appendix B Component State Matrix](#appendix-b-component-state-matrix)
- [Appendix C Sources And References](#appendix-c-sources-and-references)
- [Appendix D Cognitive Science Quick Reference](#appendix-d-cognitive-science-quick-reference)
- [Appendix E Changelog Vs Baseline](#appendix-e-changelog-vs-baseline)

## Source Keys

Use these short keys inside rules. Full URLs are repeated here to keep individual rules under 20 lines.

| Key | Source |
|---|---|
| A-HIG | Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines |
| A-ACC | Apple HIG Accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility |
| A-COLOR | Apple HIG Color/Dark Mode: https://developer.apple.com/design/human-interface-guidelines/color |
| A-LAYOUT | Apple HIG Layout: https://developer.apple.com/design/human-interface-guidelines/layout |
| A-MOTION | Apple HIG Motion: https://developer.apple.com/design/human-interface-guidelines/motion |
| M3 | Material Design 3: https://m3.material.io |
| M3-COLOR | M3 Color roles: https://m3.material.io/styles/color/roles |
| M3-TYPE | M3 Typography: https://m3.material.io/styles/typography |
| M3-MOTION | M3 Motion: https://m3.material.io/styles/motion |
| M3-LAYOUT | M3 Adaptive layout: https://m3.material.io/foundations/layout/applying-layout |
| M3-STATE | M3 Interaction states: https://m3.material.io/foundations/interaction/states |
| FIGMA | Figma design systems, variables, components: https://help.figma.com |
| GSC | Google Search Central: https://developers.google.com/search/docs |
| GSC-SD | Google structured data: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data |
| WCAG | WCAG 2.2: https://www.w3.org/TR/WCAG22 |
| WAI-APG | WAI-ARIA APG: https://www.w3.org/WAI/ARIA/apg |
| WEBDEV | web.dev performance and Core Web Vitals: https://web.dev |
| NNG | Nielsen Norman Group UX research: https://www.nngroup.com |
| BAYMARD | Baymard mobile/ecommerce UX research: https://baymard.com |
| LAWS | Laws of UX: https://lawsofux.com |
| DR | DataReportal Vietnam digital reports: https://datareportal.com |
| SC | StatCounter Vietnam stats: https://gs.statcounter.com |
| GSMA | GSMArena device specs: https://www.gsmarena.com |
| BASE | `docs/design-guidelines-apple-google-figma.md`, `docs/design-research-2026-06-27.md`, `docs/travel-platform-ux-research.md`, `docs/implementation-specs.md` |
| TOKENS | `web-nuxt/assets/css/variables.css`, `web-nuxt/assets/css/dark-overrides.css` |

## Vietnam Context

| Area | Decision for vinhlong360 |
|---|---|
| Devices | Support 360-430px CSS-width Android first, then 390/393/414px iPhone widths, 768px tablets, 1024px landscape tablets. Treat 360x800, 390x844, 393x873, 412x915, 414x896 as must-pass viewport classes. |
| OS/browser | Android Chrome and iOS Safari are primary; avoid hover-only UI and avoid input font under 16px because iOS zooms. |
| Network | Assume 4G but design for unstable rural/travel use: Save-Data, responsive images, SSR content, skeletons, no critical JS-only content. |
| Culture | Vietnamese only; left-to-right; "ban" is the neutral pronoun; Zalo/phone are primary contact paths, not email-first. |
| Travel behavior | Outdoor, one-hand, sunlight, moving vehicle. 44px targets, high contrast, short copy, and persistent contact actions are mandatory. |
| Business model | This is discovery/introduction, not booking/payment. Never add cart, checkout, fake scarcity, fake viewer counts, or paid-service dependencies. |
| Competitors | vinhlongtourist.vn is official but content-heavy; mytour.vn is hotel/booking oriented; Traveloka is mobile-polished but booking-centric. vinhlong360 should win on local knowledge, map/list UX, content trust, and no dark patterns. |

## R1 Spacing

### R1.1 Spacing scale - 4px grid [BASELINE+] [depth: consensus]
Source: BASE, A-LAYOUT, M3-LAYOUT, FIGMA.  
WHAT: All margin, padding, gap, inset use `--space-*`; default scale is 4/8/12/16/24/32/48/64/80/96.  
WHY: Gestalt proximity and Fitts's Law depend on predictable distance; irregular spacing increases visual parsing cost.  
RECONCILE: Apple 8pt grid and M3 adaptive spacing agree on regular increments; vinhlong360 keeps 4px subdivisions for CSS.  
CONTEXT: Vietnamese mobile users scan cards outdoors; consistent rhythm helps distinguish title, metadata, CTA fast.  
VERIFY: `rg -n "\b(margin|padding|gap|inset|top|left|right|bottom):\s*[0-9]+px" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: `1px/.5px` borders, map tiles, icon optical nudges `2px`, media-query breakpoints. DO/DON'T: `.card{padding:var(--space-4);gap:var(--space-2)}` / `.card{padding:15px;gap:10px}`.

### R1.2 Parent owns spacing [BASELINE+] [depth: 3-source]
Source: BASE, FIGMA, M3-LAYOUT.  
WHAT: Use parent `display:flex/grid` plus `gap`; children must not stack with repeated `margin-bottom`.  
WHY: Parent-owned spacing removes edge-margin bugs and keeps responsive rearrangement deterministic.  
RECONCILE: Figma auto-layout and CSS gap map directly; Apple layout margins are container concepts.  
CONTEXT: Entity cards, review lists, and community threads often change order on mobile; gap avoids leftover margins.  
VERIFY: `rg -n "margin-bottom:\s*var\(--space|margin-block-end" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Flow article prose may use `.prose > * + * { margin-block-start: var(--space-4) }`. DO/DON'T: `.list{display:grid;gap:var(--space-4)}` / `.item{margin-bottom:16px}`.

### R1.3 Section rhythm [BASELINE+] [depth: 3-source]
Source: BASE, A-LAYOUT, NNG.  
WHAT: Page sections use `--space-section` 64px desktop, 48px tablet, 32px mobile.  
WHY: Serial-position and F-pattern scanning improve when sections are visually separated but still connected.  
RECONCILE: Apple favors generous content margins; M3 compact classes reduce margins; use responsive semantic aliases.  
CONTEXT: 32-64px rhythm keeps next content visible. APPROVED EXCEPTION (2026-07-07): the original "no huge landing hero" clause is overridden — the homepage OPENS with the shipped, owner-approved cinematic hero masthead (`pages/index.vue`, see R4-AP2 exception); category access lives in the hero search + decision tiles below it. Do not strip the hero in a compliance pass.  
VERIFY: `rg -n "section|home-section|block" web-nuxt/pages/index.vue web-nuxt/assets/css/*.css`.  
EXCEPTION: Admin dashboards can use 24px vertical rhythm. DO/DON'T: `.section{padding-block:var(--space-section)}` / `.section{padding-block:120px}`.

### R1.4 Card internal padding [BASELINE+] [depth: consensus]
Source: BASE, M3 cards, A-LAYOUT.  
WHAT: Cards use 16px internal padding on mobile, 20-24px for dense desktop panels, 12px only for compact chips/cards.  
WHY: Too little padding merges content with borders; too much reduces information density and increases scrolling.  
RECONCILE: M3 cards commonly use 16dp+; Apple grouped content uses clear insets; Figma uses padding tokens.  
CONTEXT: Destination cards need image, badges, title, rating, Zalo/phone actions without crowding.  
VERIFY: `rg -n "\.card|Card" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Image-only gallery tiles may use 0 padding and a 4px grid gap. DO/DON'T: `.entity-card__body{padding:var(--space-4)}` / `.body{padding:7px}`.

### R1.5 Inline spacing [BASELINE+] [depth: 2-source]
Source: BASE, M3-LAYOUT, FIGMA.  
WHAT: Icon-to-text gap is 4-8px; badge internal horizontal padding is 8-12px.  
WHY: Similarity and proximity tell users which icon labels belong together.  
RECONCILE: Apple SF Symbol placement and M3 icon buttons both rely on optical alignment; use `--space-1/2/3`.  
CONTEXT: Vietnamese text is longer with diacritics; never squeeze labels to make an icon row fit.  
VERIFY: `rg -n "gap:\s*[0-9]+px|padding:\s*[0-9]+px" web-nuxt/components web-nuxt/pages`.  
EXCEPTION: Decorative icon-only marks may use `gap:0`. DO/DON'T: `.meta{gap:var(--space-2)}` / `.meta{gap:3px}`.

### R1.6 Touch target spacing [BASELINE+] [depth: research-backed]
Source: A-ACC, WCAG 2.5.8, M3 accessibility, NNG/Fitts.  
WHAT: Interactive targets are minimum 44x44px with 8px separation; prefer 48px when layout allows.  
WHY: Fitts's Law: larger, separated targets reduce acquisition time and accidental taps.  
RECONCILE: Apple says 44pt, M3 prefers 48dp, WCAG AA minimum is 24px; vinhlong360 minimum is 44px.  
CONTEXT: Users browse one-handed in sun or on xe may; 24px is legal but not good enough for this travel site.  
VERIFY: `rg -n "height:\s*[0-3][0-9]px|min-height:\s*[0-3][0-9]px" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Inline text links inside paragraphs; add underline and 8px tap padding if isolated. DO/DON'T: `.btn{min-height:var(--touch-min)}` / `.icon-btn{height:32px}`.

### R1.7 Reading width [BASELINE+] [depth: 3-source]
Source: BASE, NNG, WCAG Reflow.  
WHAT: Long prose max-width is 65-75ch; detail content max is `--detail-content-max` 680px.  
WHY: Very long lines increase regressions and rereads; cognitive load rises on mobile/desktop alike.  
RECONCILE: Travel platforms use narrow detail columns; Apple readable layout favors comfortable margins.  
CONTEXT: Vietnamese diacritics need line-height and narrow columns for older users.  
VERIFY: `rg -n "max-width:\s*(none|100%)|ch|--detail-content-max" web-nuxt/pages web-nuxt/assets/css`.  
EXCEPTION: Tables, maps, galleries, route timelines can exceed 75ch. DO/DON'T: `.prose{max-width:70ch}` / `.prose{max-width:1200px}`.

### R1.8 Safe area padding [BASELINE+] [depth: 2-source]
Source: A-LAYOUT, M3-LAYOUT.  
WHAT: Fixed bottom/top bars include `env(safe-area-inset-*)`; mobile contact bar pads bottom.  
WHY: iOS home indicators and notches can hide critical CTAs.  
RECONCILE: Apple safe areas are platform-specific; M3 adaptive layout still expects edge protection.  
CONTEXT: Zalo/phone bottom bar is business-critical and must not sit under the home indicator.  
VERIFY: `rg -n "position:\s*fixed|safe-area-inset" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Non-interactive full-bleed images may extend behind safe areas if text/CTA stays inside. DO/DON'T: `.bar{padding-bottom:calc(var(--space-2) + env(safe-area-inset-bottom))}` / `.bar{bottom:0}`.

### R1.9 Density modes [NEW] [depth: 2-source]
Source: M3-LAYOUT, BAYMARD, TOKENS.  
WHAT: Public travel UI uses comfortable density; admin tables may use compact density with 32-40px rows.  
WHY: Expert admin tasks need scan density; tourists need lower error rate and easier reading.  
RECONCILE: M3 adaptive density and Baymard mobile findings allow context-specific density.  
CONTEXT: Do not let admin density leak into public pages like `du-lich` or entity detail.  
VERIFY: `rg -n "admin|table|row" web-nuxt/layouts web-nuxt/pages/admin`.  
EXCEPTION: Public comparison tables can use 40px rows if every row has no primary CTA. DO/DON'T: `.admin-row{min-height:40px}` / `.public-card .cta{height:32px}`.

### R1.10 Sticky offset token [BASELINE+] [depth: 2-source]
Source: BASE, WCAG Focus Not Obscured, A-LAYOUT.  
WHAT: Any anchored/focused section under sticky header must use `scroll-padding-top` or `scroll-margin-top`.  
WHY: Hidden focused content breaks keyboard and in-page navigation.  
RECONCILE: WCAG defines the accessibility failure; Apple/M3 provide sticky navigation patterns.  
CONTEXT: Detail pages with sections, reviews, map, and route anchors need visible focus after jump.  
VERIFY: `rg -n "scroll-padding-top|scroll-margin-top|position:\s*sticky" web-nuxt`.  
EXCEPTION: Components without anchors or focusable descendants. DO/DON'T: `html{scroll-padding-top:var(--header-h,72px)}` / `.section:target{}` only.

### R1.11 Border and hairline spacing [BASELINE] [depth: 2-source]
Source: BASE, A-COLOR, M3-COLOR.  
WHAT: Use `.5px` or `1px` borders only through `--line`, `--border`, `--divider-*`, `--outline-*`.  
WHY: Subtle lines support grouping without adding heavy visual noise.  
RECONCILE: Apple separators and M3 outline roles both treat dividers as semantic, not decorative random colors.  
CONTEXT: Sand/ink palette needs quiet dividers so local images and titles remain primary.  
VERIFY: `rg -n "border[^;]*#[0-9A-Fa-f]|border[^;]*rgba\\(" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Category accent left border may use `--cat-*-accent`. DO/DON'T: `border:var(--divider-default)` / `border:1px solid #ddd`.

### R1.12 Layout containment [BASELINE+] [depth: 3-source]
Source: WEBDEV, BASE, M3-LAYOUT.  
WHAT: Large repeated cards/lists use `contain: content` and below-fold sections may use `content-visibility:auto`.  
WHY: CSS containment reduces layout/paint work and improves INP/LCP on long travel lists.  
RECONCILE: M3 layout can be complex; web.dev makes rendering containment measurable.  
CONTEXT: Catalog and community feeds can reach many cards on mobile; containment protects scrolling.  
VERIFY: `rg -n "contain:|content-visibility" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Elements whose size depends on outside layout or sticky descendants. DO/DON'T: `.result-card{contain:content}` / `.sticky-map{content-visibility:auto}`.

#### R1 Decision Tree

If it is repeated UI -> parent `gap`; if it is prose -> vertical rhythm selector; if it is fixed bar -> safe-area padding; if it is admin-only -> compact density allowed; otherwise public comfortable spacing wins.

#### R1 Anti-patterns

- R1-AP1: Random `15px/17px/22px` spacing. Consequence: uneven rhythm. Root: eyeballing CSS. Fix: replace with `--space-*`.
- R1-AP2: Child margins in card lists. Consequence: last item has stray space. Root: pre-grid CSS habit. Fix: parent `gap`.
- R1-AP3: 32px public icon buttons. Consequence: tap errors. Root: desktop-first sizing. Fix: `min-width/min-height:var(--touch-min)`.

#### R1 Checklist

Run hardcode spacing grep, verify 44px targets, inspect mobile 360px and 414px screenshots, confirm sticky focus is not hidden.

## R2 Typography

### R2.1 Type scale tokens [BASELINE+] [depth: consensus]
Source: BASE, A-HIG Typography, M3-TYPE, FIGMA.  
WHAT: Use `--text-*`, `--lh-*`, `--weight-*`; no raw font-size except tiny one-off admin labels.  
WHY: A consistent type ramp reduces cognitive load and avoids hierarchy drift.  
RECONCILE: Apple text styles and M3 type roles differ; vinhlong360 maps both to existing clamp tokens.  
CONTEXT: Vietnamese diacritics need adequate line-height; body text must stay readable on 360px screens.  
VERIFY: `rg -n "font-size:\s*[0-9.]+(px|rem)" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: `font-size:1rem` for native inputs is allowed to prevent iOS zoom. DO/DON'T: `font-size:var(--text-base)` / `font-size:15px`.

### R2.2 Body text minimum [BASELINE+] [depth: research-backed]
Source: A-ACC, WCAG, NNG cognitive accessibility.  
WHAT: Public body text is at least 16px, preferred 17-18px via `--text-base`; line-height 1.5+.  
WHY: Low literacy, aging eyes, and mobile glare increase reading effort below 16px.  
RECONCILE: Apple Body is 17pt; M3 body large is 16sp; vinhlong360 clamps 16->18.  
CONTEXT: Older Vietnamese smartphone users and tourists outdoors need larger body copy.  
VERIFY: `rg -n "font-size:\s*(1[0-5]px|0\\.[0-9]+rem)" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Metadata labels and badges can use `--text-xs` if nonessential. DO/DON'T: `.desc{font:var(--weight-body) var(--text-base)/var(--lh-base) var(--font-sans)}` / `.desc{font-size:13px}`.

### R2.3 Heading hierarchy [BASELINE+] [depth: 3-source]
Source: A-HIG, M3-TYPE, GSC, WAI.  
WHAT: One visible `h1` per page, sequential headings, no heading skipped for visual size.  
WHY: Screen readers, SEO, and F-pattern scanning all rely on semantic hierarchy.  
RECONCILE: Visual style can use classes, but DOM headings must remain structural.  
CONTEXT: Entity pages should expose "Cu lao An Binh" or "Banh khot" as `h1`, not hidden metadata.  
VERIFY: `rg -n "<h[1-6]|role=\"heading\"" web-nuxt/pages web-nuxt/components`.  
EXCEPTION: Dialog title can be `h2` if page already has `h1`. DO/DON'T: `<h2 class="text-xl">Danh gia</h2>` / `<div class="h2">Danh gia</div>`.

### R2.4 Vietnamese line-height [NEW] [depth: research-backed]
Source: NNG readability, WCAG Text Spacing, BASE.  
WHAT: Vietnamese paragraphs use line-height 1.5-1.65 and never below 20px computed.  
WHY: Tone marks and ascenders crowd at low line-height, increasing rereads.  
RECONCILE: M3 line heights are role-based; WCAG allows user spacing; use `--leading-normal/relaxed`.  
CONTEXT: Long descriptions and cultural stories must stay comfortable on small phones.  
VERIFY: `rg -n "line-height:\s*(1\\.[0-3]|[0-9]+px)" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Single-line buttons/badges may use tighter line-height if target height is 44px+. DO/DON'T: `.prose{line-height:var(--leading-relaxed)}` / `.prose{line-height:1.2}`.

### R2.5 Letter spacing [BASELINE+] [depth: 2-source]
Source: M3-TYPE, A-HIG, TOKENS.  
WHAT: Body Vietnamese uses `letter-spacing:0`; caps labels may use `--tracking-caps` only under 14px.  
WHY: Extra tracking can separate Vietnamese diacritics from letters and hurts word recognition.  
RECONCILE: M3 uses role-specific tracking; Apple applies optical tracking; web CSS should be conservative.  
CONTEXT: "Dac san Vinh Long" labels can use caps tracking; paragraphs must not.  
VERIFY: `rg -n "letter-spacing" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Uppercase admin/status chips at `--text-xs`. DO/DON'T: `.label{text-transform:uppercase;letter-spacing:var(--tracking-caps)}` / `.body{letter-spacing:.04em}`.

### R2.6 Font loading [BASELINE+] [depth: 3-source]
Source: WEBDEV, A-HIG, M3-TYPE.  
WHAT: Use system stack plus at most one web font under 100KB; `font-display:swap`; preload only critical font.  
WHY: Font blocking delays LCP and can cause CLS.  
RECONCILE: Apple/M3 define type behavior, web.dev defines network implementation.  
CONTEXT: Rural mobile networks make heavy font stacks feel broken; system fonts are acceptable and fast.  
VERIFY: `rg -n "@font-face|fonts.googleapis|preload.*font|font-display" web-nuxt`.  
EXCEPTION: Logo image/wordmark can be custom if not used for body text. DO/DON'T: `font-family:var(--font-sans)` / import three display fonts.

### R2.7 Text contrast roles [BASELINE+] [depth: consensus]
Source: WCAG 1.4.3, A-COLOR, M3-COLOR, TOKENS.  
WHAT: Use `--text-high`, `--text-medium`, `--text-low`; body and controls need 4.5:1.  
WHY: Contrast is the first accessibility gate in sunlight and dark mode.  
RECONCILE: Apple label alpha and M3 on-color roles align with semantic text roles.  
CONTEXT: Muted Vietnamese metadata must remain readable on warm sand backgrounds.  
VERIFY: Lighthouse Accessibility color contrast = 100%; `rg -n "color:\s*rgba|color:\s*#[0-9A-Fa-f]" web-nuxt`.  
EXCEPTION: Disabled text follows `--opacity-disabled-content` but must not carry essential info. DO/DON'T: `.meta{color:var(--text-medium)}` / `.meta{color:#aaa}`.

### R2.8 Clamp card titles [BASELINE+] [depth: 3-source]
Source: BASE travel research, BAYMARD, M3 cards.  
WHAT: Card titles clamp to 2 lines; descriptions clamp to 3; full text appears on detail page.  
WHY: Predictable card height supports comparison and reduces layout shift.  
RECONCILE: Travel platforms clamp lists; content pages can reveal full copy.  
CONTEXT: Vietnamese names are long; card grids must not become uneven masonry unless intentional.  
VERIFY: `rg -n "-webkit-line-clamp|line-clamp" web-nuxt/components web-nuxt/pages`.  
EXCEPTION: Search result rows may allow 3-line title if no image. DO/DON'T: `.title{-webkit-line-clamp:2}` / `.title{height:auto}` in cards.

### R2.9 Numerals and locale [NEW] [depth: 2-source]
Source: GSC, WCAG, BASE.  
WHAT: UI numbers use Vietnamese grouping where human-facing, but schema/rating decimals use dot (`4.5`).  
WHY: Schema parsers expect machine-normal values; users expect readable localized counts.  
RECONCILE: Google structured data is machine-first; UI copy can localize.  
CONTEXT: Show `1,2K luot xem` in UI only if product convention accepts comma; JSON-LD uses `4.5`.  
VERIFY: `rg -n "ratingValue|aggregateRating|toLocaleString|Intl.NumberFormat" web-nuxt server app`.  
EXCEPTION: Phone numbers keep local formatting. DO/DON'T: `new Intl.NumberFormat('vi-VN')` / `"ratingValue":"4,5"`.

### R2.10 Error text pattern [BASELINE+] [depth: 3-source]
Source: A-HIG Writing, M3 Text fields, WCAG 3.3.1.  
WHAT: Error copy says what happened, why, and how to fix in one short sentence.  
WHY: Vague errors increase abandonment and support cost.  
RECONCILE: Apple says direct/helpful; M3 text fields require supporting error text; WCAG requires identification.  
CONTEXT: Use plain Vietnamese: "So dien thoai chua dung. Nhap 10 chu so bat dau bang 0."  
VERIFY: `rg -n "error|loi|invalid|aria-invalid" web-nuxt/components web-nuxt/pages`.  
EXCEPTION: Admin logs may include technical detail after a plain summary. DO/DON'T: `<p id="phone-error">So dien thoai chua dung...</p>` / `Error 422`.

### R2.11 No text in decorative images [BASELINE+] [depth: consensus]
Source: WCAG 1.4.5, A-ACC, GSC image SEO.  
WHAT: Do not bake Vietnamese UI text into photos/illustrations; render text as HTML.  
WHY: Image text does not resize, translate to screen readers, or index reliably.  
RECONCILE: Brand marks are exceptions; content and CTAs must be real text.  
CONTEXT: Festival banners need real headings so users and search engines read them.  
VERIFY: Manual image audit; `rg -n "alt=|NuxtImg|background-image" web-nuxt`.  
EXCEPTION: Logo wordmark with proper accessible name. DO/DON'T: `<h1>Le hoi trai cay</h1>` / banner JPEG containing the only title.

### R2.12 Text alignment [BASELINE+] [depth: research-backed]
Source: NNG readability, WCAG cognitive, A-HIG.  
WHAT: Body Vietnamese is left-aligned; center alignment only for short empty states or hero copy under 2 lines.  
WHY: Ragged-left center blocks slow F-pattern scanning.  
RECONCILE: Aesthetic center layouts are acceptable for short moments, not reading content.  
CONTEXT: Entity descriptions and guides must be left aligned for older users.  
VERIFY: `rg -n "text-align:\s*center" web-nuxt/pages web-nuxt/components`.  
EXCEPTION: Buttons, badges, statistic numbers, empty state titles. DO/DON'T: `.prose{text-align:left}` / `.article{text-align:center}`.

#### R2 Decision Tree

If content is page title -> semantic heading token; if paragraph -> `--text-base` and relaxed line-height; if metadata -> `--text-sm/xs` with 4.5:1 if essential; if card title -> clamp; if schema -> machine number format.

#### R2 Anti-patterns

- R2-AP1: Raw font sizes in components. Consequence: hierarchy drift. Root: local CSS tweaks. Fix: use `--text-*`.
- R2-AP2: Centered long Vietnamese paragraphs. Consequence: slow scanning. Root: hero-page habit. Fix: left-align body.
- R2-AP3: Error copy as codes. Consequence: users cannot recover. Root: backend leakage. Fix: plain one-sentence recovery text.

#### R2 Checklist

Run font-size grep, check one `h1`, inspect line-height in Vietnamese prose, run Lighthouse text contrast, verify no critical image text.

## R3 Color

### R3.1 Semantic color only [BASELINE+] [depth: consensus]
Source: BASE, A-COLOR, M3-COLOR, FIGMA, TOKENS.  
WHAT: Components use semantic tokens (`--primary`, `--surface`, `--text`, `--line`), not raw hex.  
WHY: Semantic roles preserve dark mode, contrast, and meaning.  
RECONCILE: Apple system colors and M3 roles both separate primitive color from role.  
CONTEXT: Clay/amber/leaf/river tokens must signal local identity without random one-off colors.  
VERIFY: `rg -P -n "(?<!&)#[0-9A-Fa-f]{3,8}\\b" web-nuxt --glob "*.vue" --glob "*.css" --glob "!web-nuxt/assets/css/variables.css"`.  
EXCEPTION: Data visualization palettes may define component-scoped tokens first. DO/DON'T: `color:var(--primary-fg)` / `color:#9C3D22`.

### R3.2 On-color pairs [BASELINE+] [depth: consensus]
Source: M3-COLOR, WCAG, TOKENS.  
WHAT: Filled surfaces must use matching `--on-*` foregrounds: `--primary` with `--on-primary`, container with `--on-primary-container`.  
WHY: Contrast and meaning fail when foreground is guessed.  
RECONCILE: M3 names explicit pairs; Apple labels map to foreground roles.  
CONTEXT: Clay filled CTA needs white text; amber filled CTA needs ink text for contrast.  
VERIFY: `rg -n "background:\s*var\\(--(primary|accent|secondary|error)" web-nuxt`.  
EXCEPTION: Transparent buttons use text roles, not on-color roles. DO/DON'T: `.btn{background:var(--accent);color:var(--on-accent)}` / `.btn{background:var(--accent);color:white}`.

### R3.3 Primary means action [BASELINE+] [depth: 3-source]
Source: A-COLOR, M3-COLOR, NNG Von Restorff.  
WHAT: `--primary` is reserved for primary action/active state, not large decorative backgrounds.  
WHY: Distinct primary color makes the main action memorable.  
RECONCILE: Apple warns color must communicate consistently; M3 primary is key action color.  
CONTEXT: Use clay CTA for "Goi dien", "Nhan Zalo" companion; avoid clay everywhere.  
VERIFY: `rg -n "var\\(--primary\\)" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Brand logo or tiny active indicator. DO/DON'T: `.cta{background:var(--primary)}` / `.hero{background:var(--primary)}`.

### R3.4 Accent means warmth, not warning [BASELINE+] [depth: 2-source]
Source: BASE, A-COLOR, M3-COLOR.  
WHAT: Amber `--accent` is seasonal/highlight; warnings use `--warning`.  
WHY: Reusing amber for errors/warnings reduces semantic clarity.  
RECONCILE: M3 has separate error/warning-like roles; Apple destructive uses red.  
CONTEXT: Amber can mark "dac san" or sunshine, but not validation warnings.  
VERIFY: `rg -n "warning|warn|accent" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: A warning icon can include amber only through `--warning`. DO/DON'T: `.badge-season{color:var(--accent-text)}` / `.error{color:var(--accent)}`.

### R3.5 Contrast minimums [BASELINE+] [depth: consensus]
Source: WCAG 1.4.3/1.4.11, A-ACC, M3 accessibility.  
WHAT: Normal text >=4.5:1, large text and non-text UI >=3:1; target AAA 7:1 for critical public prose.  
WHY: Contrast loss is amplified by glare, age, and cheap screens.  
RECONCILE: WCAG AA is legal floor; vinhlong360 raises critical prose where feasible.  
CONTEXT: Outdoor Vinh Long travel use makes muted text risky on sand backgrounds.  
VERIFY: Lighthouse Accessibility color contrast = 100%; manual contrast checker for new token pairs.  
EXCEPTION: Disabled content may be lower if action is unavailable and not essential. DO/DON'T: `--muted:#586860` / `color:#b8b1a5` on cream.

### R3.6 Focus color [BASELINE+] [depth: consensus]
Source: WCAG 2.4.11, A-ACC, M3-STATE.  
WHAT: Focus ring uses `--focus-ring` plus 2px visible outline/offset when ring alone is low contrast.  
WHY: Keyboard users need visible current location.  
RECONCILE: M3 state layers show focus, WCAG requires visible appearance; Apple expects clear focus.  
CONTEXT: Admin and public forms must show focus on 360px and dark mode.  
VERIFY: `rg -n ":focus-visible|--focus-ring|outline" web-nuxt`.  
EXCEPTION: Native controls can keep browser outline if contrast passes. DO/DON'T: `.btn:focus-visible{box-shadow:var(--focus-ring)}` / `*:focus{outline:none}`.

### R3.7 Status colors [BASELINE+] [depth: 3-source]
Source: M3-COLOR, WCAG, A-COLOR.  
WHAT: Success/info/warning/error use existing `--success/--info/--warning/--error` plus bg/border tokens.  
WHY: Multiple channels color+icon+text prevent color-only interpretation.  
RECONCILE: Apple and WCAG forbid color-only state; M3 provides semantic roles.  
CONTEXT: Report moderation/admin statuses need unmistakable Vietnamese labels.  
VERIFY: `rg -n "success|warning|error|info|status-" web-nuxt`.  
EXCEPTION: Decorative category colors still need text labels. DO/DON'T: `.alert{color:var(--error);background:var(--error-bg)}` / `.alert{color:red}`.

### R3.8 Category color mapping [BASELINE+] [depth: 2-source]
Source: BASE travel research, M3-COLOR.  
WHAT: Category colors use `--cat-*` tokens and must be paired with text labels/icons.  
WHY: Categories need fast recognition without making color the only cue.  
RECONCILE: M3 supports extended color roles; WCAG requires non-color cues.  
CONTEXT: `attraction`, `dish`, `craft`, `accommodation`, `event` must feel local but readable.  
VERIFY: `rg -n "--cat-|data-type|category" web-nuxt`.  
EXCEPTION: Admin raw taxonomy view may use monochrome chips. DO/DON'T: `.cat-dish{border-color:var(--cat-dish-accent)}` / `.cat-dish{border-color:#f60}`.

### R3.9 Surface hierarchy [BASELINE+] [depth: consensus]
Source: M3-COLOR, A-COLOR, TOKENS.  
WHAT: Use `--bg`, `--surface`, `--surface-container-*`, `--card`; do not invent `#fafafa/#fff` surfaces.  
WHY: Surface roles keep light/dark mode coherent and preserve elevation logic.  
RECONCILE: Apple system backgrounds and M3 surface containers map cleanly to existing tokens.  
CONTEXT: Warm sand background with white card surfaces is brand-specific; raw white breaks dark mode.  
VERIFY: `rg -n "background:\s*(#fff|#ffffff|white|#fafafa)" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: White text on dark image overlay uses `--text-on-dark`. DO/DON'T: `.panel{background:var(--surface-container-low)}` / `.panel{background:#fff}`.

### R3.10 Overlay and scrim [BASELINE+] [depth: 2-source]
Source: A-COLOR, M3-COLOR, TOKENS.  
WHAT: Image overlays use `--overlay-dark`, `--overlay-light`, `--scrim`, never arbitrary black alpha.  
WHY: Text over images must stay readable across unknown AI-generated images.  
RECONCILE: Apple materials and M3 scrims both define overlays semantically.  
CONTEXT: Hero/detail images of river, orchard, heritage sites need stable text contrast.  
VERIFY: `rg -n "rgba\\(0,0,0|rgba\\(0, 0, 0" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Canvas/map libraries may output their own overlays. DO/DON'T: `.hero:after{background:var(--overlay-dark)}` / `.hero:after{background:rgba(0,0,0,.37)}`.

### R3.11 Zalo brand color [NEW] [depth: 2-source]
Source: Vietnamese market context, TOKENS.  
WHAT: Zalo buttons use `--brand-zalo` and `--brand-zalo-hover`; never recolor Zalo as clay.  
WHY: Familiar brand color reduces decision friction and supports Jakob's Law.  
RECONCILE: Brand identity exception is allowed inside semantic token system.  
CONTEXT: Zalo is more common than email for Vietnamese travel/local contact.  
VERIFY: `rg -n "Zalo|brand-zalo|0068FF" web-nuxt`.  
EXCEPTION: Text-only "Nhan Zalo" link inside paragraph can use normal link color with icon. DO/DON'T: `.zalo{background:var(--brand-zalo)}` / `.zalo{background:var(--primary)}`.

### R3.12 Seasonal theming [BASELINE+] [depth: 2-source]
Source: BASE, M3-COLOR, TOKENS.  
WHAT: Seasonal themes override only `--season-*`; do not override global `--primary`.  
WHY: Theme scoping prevents festival pages from corrupting global brand semantics.  
RECONCILE: M3 extended colors support local accents; core color roles stay stable.  
CONTEXT: Tet, he, mua nuoc, thu can tint pages without confusing CTAs.  
VERIFY: `rg -n "season-|--season-" web-nuxt/assets/css/variables.css web-nuxt`.  
EXCEPTION: A seasonal landing may use a hero gradient token. DO/DON'T: `.season-tet{--season-accent:#c9362c}` / `.season-tet{--primary:#c9362c}`.

### R3.13 Avoid one-hue palette [NEW] [depth: research-backed]
Source: NNG aesthetic-usability, A-COLOR, M3-COLOR.  
WHAT: Each major page must include neutral surface + one primary + one secondary/accent, not a monochrome clay wash.  
WHY: Aesthetic-usability depends on contrast, hierarchy, and memorability, not just brand repetition.  
RECONCILE: Brand consistency and Von Restorff distinctness must both hold.  
CONTEXT: Vinh Long identity needs clay, river, leaf, amber together in restrained roles.  
VERIFY: Manual screenshot review; `rg -n "--primary|--secondary|--accent|--tertiary" web-nuxt/pages/index.vue`.  
EXCEPTION: Admin utility screens may be mostly neutral. DO/DON'T: neutral cards + leaf tags + clay CTA / all headings, borders, backgrounds clay.

### R3.14 Link color [BASELINE+] [depth: consensus]
Source: WCAG, A-COLOR, TOKENS.  
WHAT: Links are visually distinct by color and underline/hover; dark mode must override default blue.  
WHY: Color-only and browser-default blue can fail contrast in dark mode.  
RECONCILE: WCAG requires non-color cues; Apple/M3 use semantic link/action roles.  
CONTEXT: Travel guide links must be obvious in Vietnamese prose.  
VERIFY: `rg -n "a\\s*\\{|text-decoration|link" web-nuxt/assets/css web-nuxt/pages`.  
EXCEPTION: Button-like links can omit underline if shape and role are clear. DO/DON'T: `.prose a{text-decoration:underline;color:var(--primary-fg)}` / `a{color:blue}`.

### R3.15 Color-mix discipline [NEW] [depth: 2-source]
Source: M3-COLOR, WEBDEV, TOKENS.  
WHAT: `color-mix()` must reference existing tokens and only for tints/containers, not primary semantic values in components.  
WHY: Unbounded mixes create untestable contrast drift.  
RECONCILE: M3 tonal palettes are systematic; ad hoc CSS mixes need guardrails.  
CONTEXT: `rgba(var(--primary-rgb), .08)` is OK for a tint, but not as the only error/success style.  
VERIFY: `rg -n "color-mix\\(|rgba\\(var\\(--" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Experimental seasonal pages can define a token first in `variables.css`. DO/DON'T: `--primary-container:color-mix(...)` / `.btn{background:color-mix(...)}`

#### R3 Decision Tree

If it communicates action -> primary/on-primary; if it communicates status -> status token; if it groups content -> surface/container; if it brands external service -> brand token; if decorative -> category/season token with non-color cue.

#### R3 Anti-patterns

- R3-AP1: Raw hex in Vue scoped CSS. Consequence: dark-mode breakage. Root: local patching. Fix: semantic token or add token.
- R3-AP2: Primary color on every section. Consequence: CTA no longer stands out. Root: branding overuse. Fix: neutral surfaces and one primary CTA.
- R3-AP3: Color-only status. Consequence: inaccessible to color-blind users. Root: visual shortcut. Fix: icon + text + color.

#### R3 Checklist

Run raw hex grep, run contrast audit, inspect light/dark screenshot, verify on-color pair, confirm Zalo uses brand token.

## R4 Motion

### R4.1 Motion token only [BASELINE+] [depth: consensus]
Source: BASE, A-MOTION, M3-MOTION, TOKENS.  
WHAT: Transitions use `--dur-*` or `--duration-*` and `--ease-*`; no raw `transition:.37s`.  
WHY: Consistent timing makes UI feel predictable and reduces motion debt.  
RECONCILE: Apple spring presets and M3 duration/easing scales map to existing tokens.  
CONTEXT: Motion should polish local travel discovery, not distract from content.  
VERIFY: `rg -n "transition:|animation:" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Third-party map library animations. DO/DON'T: `transition:transform var(--dur-medium2) var(--ease-emphasized)` / `transition:all .37s ease`.

### R4.2 Transform and opacity only [BASELINE+] [depth: 3-source]
Source: WEBDEV, M3-MOTION, Linear research in BASE.  
WHAT: Animate `transform` and `opacity`; do not animate layout/paint properties like `height`, `top`, `box-shadow`.  
WHY: Compositor-only animation protects INP and scroll smoothness.  
RECONCILE: M3 motion patterns work when implemented with web performance constraints.  
CONTEXT: Long mobile lists and cards must remain smooth on mid-range Android.  
VERIFY: `rg -n "transition:[^;]*(height|width|top|left|box-shadow|margin|padding)" web-nuxt`.  
EXCEPTION: Accordions can animate grid-template rows only if small and reduced-motion safe. DO/DON'T: `.card:hover{transform:translateY(-2px)}` / `.card:hover{top:-2px}`.

### R4.3 Reduced motion [BASELINE+] [depth: consensus]
Source: WCAG 2.3.3, A-MOTION, M3-MOTION.  
WHAT: Every nontrivial animation has `prefers-reduced-motion: reduce` fallback to fade/instant.  
WHY: Motion can trigger vestibular discomfort and cognitive overload.  
RECONCILE: Apple says reduce, not remove all feedback; use opacity/state changes.  
CONTEXT: Travel users may already be moving in vehicles; avoid parallax on dense grids and large slides.  
VERIFY: `rg -n "prefers-reduced-motion" web-nuxt`.  
EXCEPTION: Essential loading progress remains but without shimmer motion. APPROVED EXCEPTION (2026-07-07): hero Ken Burns + parallax are the shipped cinematic signature (`pages/index.vue` `.hero-kenburns`, `composables/useParallax.ts` no-op on reduce, `assets/css/editorial.css`); both switch off fully under `prefers-reduced-motion` — do not strip them in compliance passes. DO/DON'T: `@media(prefers-reduced-motion:reduce){*{animation:none}}` / parallax with no fallback.

### R4.4 Entrance duration [BASELINE+] [depth: 2-source]
Source: M3-MOTION, BASE.  
WHAT: Small UI entrance 150-250ms; page/section entrance 300-500ms; never exceed 800ms for interaction/entrance motion.  
WHY: Doherty Threshold rewards quick feedback; long motion delays perceived control.  
RECONCILE: M3 duration tokens and web.dev responsiveness agree.  
CONTEXT: Users checking directions or phone numbers should not wait for decorative animation.  
VERIFY: `rg -n "([8-9][0-9]{2}|[1-9][0-9]{3})ms|\\.8s|1s" web-nuxt --glob "*.css" --glob "*.vue"`.  
EXCEPTION: Skeleton shimmer loop is 1.5s because it signals loading, not interaction. APPROVED EXCEPTION (2026-07-07): ambient cinematic loops are exempt from the cap — hero Ken Burns runs 20-34s (`--dur-kenburns` in `assets/css/variables.css`, `.hero-kenburns` in `pages/index.vue`), reduced-motion gated; the 800ms ceiling applies to interaction feedback and entrances only. DO/DON'T: `animation:fade var(--dur-medium2)` / `animation:hero 1400ms` on an entrance.

### R4.5 Press feedback [BASELINE+] [depth: 3-source]
Source: M3-STATE, A-HIG Buttons, NNG Fitts.  
WHAT: Buttons/chips visibly respond within 100ms using state layer or `scale(.98)`.  
WHY: Immediate feedback confirms tap and reduces repeated taps.  
RECONCILE: M3 state layers and Apple button feedback both require visible response.  
CONTEXT: On slow mobile network, press feedback must happen before API completes.  
VERIFY: `rg -n ":active|--state-pressed|scale\\(.98" web-nuxt`.  
EXCEPTION: Destructive confirmation buttons may avoid scale if it looks playful. DO/DON'T: `.btn:active{transform:scale(.98)}` / no active style.

### R4.6 Loading motion [BASELINE+] [depth: 3-source]
Source: M3 loading, WEBDEV, WCAG.  
WHAT: Use skeleton for content cards/lists, spinner only for button-local pending, progress bar for determinate tasks.  
WHY: Skeletons preserve layout and reduce perceived wait; spinners give no structure.  
RECONCILE: M3 supports multiple loading indicators; choose by information certainty.  
CONTEXT: Entity cards and community feed should show skeletons on mobile.  
VERIFY: `rg -n "skeleton|spinner|aria-busy|progress" web-nuxt`.  
EXCEPTION: Admin one-click refresh can use a spinner in the button. DO/DON'T: `.cards[aria-busy=true] .skeleton` / full-page spinner for catalog.

### R4.7 Scroll reveal limits [BASELINE+] [depth: research-backed]
Source: NNG, WEBDEV, A-MOTION.  
WHAT: Scroll reveal is subtle opacity/translateY <=16px and must not hide content from no-JS users.  
WHY: Hidden-until-JS content harms progressive enhancement and scanning.  
RECONCILE: Aesthetic polish is allowed when web baseline stays readable.  
CONTEXT: Homepage discovery sections can reveal gently; detail facts and contact must render immediately.  
VERIFY: `rg -n "IntersectionObserver|reveal|opacity:\s*0" web-nuxt`.  
EXCEPTION: Decorative background elements. DO/DON'T: `.reveal{opacity:1}` baseline + enhanced class / `.card{opacity:0}` until JS.

### R4.8 No auto-advancing carousels [BASELINE+] [depth: 3-source]
Source: WCAG 2.2.2, BAYMARD, NNG.  
WHAT: Galleries do not auto-advance; user controls next/previous and swipe.  
WHY: Moving content steals attention and can hide decision-critical images.  
RECONCILE: Travel platforms use galleries, but user control is mandatory.  
CONTEXT: Tourist users inspect place photos; auto movement fights comparison.  
VERIFY: `rg -n "setInterval|autoplay|carousel" web-nuxt`.  
EXCEPTION: Decorative loading shimmer, not content carousel. DO/DON'T: `<button aria-label="Anh tiep">` / auto-rotate every 3s.

### R4.9 Overlay transitions [BASELINE+] [depth: 2-source]
Source: M3-MOTION, WAI-APG dialog, A-MOTION.  
WHAT: Dialog/sheet enter fades scrim 150ms and slides panel <=16px; focus moves immediately.  
WHY: Motion should explain spatial relation without delaying keyboard interaction.  
RECONCILE: M3 modal motion and ARIA focus requirements both apply.  
CONTEXT: Photo gallery and report dialogs must feel fast on mobile.  
VERIFY: `rg -n "dialog|modal|sheet|scrim|aria-modal" web-nuxt`.  
EXCEPTION: Native browser dialogs if used. DO/DON'T: `.sheet{transform:translateY(16px)}` / `.modal{transform:translateY(100vh)}`.

### R4.10 Will-change budget [NEW] [depth: 2-source]
Source: WEBDEV, BASE.  
WHAT: `will-change` is allowed on at most 3 visible elements and removed after animation when possible.  
WHY: Overusing `will-change` burns GPU memory and can slow low-end phones.  
RECONCILE: Performance guidance limits optimization hints to known hot paths.  
CONTEXT: Use for sticky CTAs or active cards, not every card in a feed.  
VERIFY: `rg -n "will-change" web-nuxt`.  
EXCEPTION: A single always-animated progress indicator. DO/DON'T: `.active-card{will-change:transform}` / `.card{will-change:transform}` for all cards.

#### R4 Micro-interaction Recipes

| # | Recipe | Implementation |
|---|---|---|
| 1 | Button press | `transform:scale(.98); transition:transform var(--dur-short2)` |
| 2 | Card hover | `translateY(-2px)` + shadow via `::after` opacity |
| 3 | Save toggle | icon scale `.92 -> 1`, color `--save-red`, aria-pressed |
| 4 | Zalo tap | 100ms state layer, keep external navigation immediate |
| 5 | Phone tap | reveal `tel:` link focus ring and pressed state |
| 6 | Chip select | state layer + active indicator, no layout shift |
| 7 | Search focus | border `--primary-fg`, `--focus-ring` |
| 8 | Autocomplete open | opacity + translateY(4px), focus first option only on arrow key |
| 9 | Dialog open | scrim fade 150ms, panel translateY(16px) |
| 10 | Bottom sheet close | opacity fade 100ms, focus returns to trigger |
| 11 | Skeleton | `--sk-gradient`, `--sk-duration:1.5s` |
| 12 | Toast | slide 8px + fade, auto-dismiss only noncritical |
| 13 | Error reveal | fade in error text, no shake |
| 14 | Success | check icon opacity fade, message persists long enough |
| 15 | Load more | button spinner inside 44px target |
| 16 | Map/list toggle | icon swap + selected state layer |
| 17 | Gallery next | crossfade, no horizontal flyover for reduced motion |
| 18 | Accordion | instant height or small opacity fade; no content hidden from no-JS |
| 19 | Skip link | appears instantly on focus |
| 20 | Sticky contact bar | no bounce; shadow opacity on scroll |
| 21 | Sort select | native focus state; no custom animated menu unless ARIA complete |
| 22 | Admin row select | background state layer, check icon appears |
| 23 | Report submit | button pending + `aria-busy=true` |
| 24 | Dark-mode switch | icon crossfade under 150ms |
| 25 | Offline notice | toast slides 8px and remains until connection returns |

#### R4 Decision Tree

If interaction confirms input -> 50-150ms; if it changes view -> 150-300ms; if it introduces page section -> 300-500ms; if user enabled reduced motion -> opacity/instant.

#### R4 Anti-patterns

- R4-AP1: `transition: all`. Consequence: accidental layout animation. Root: shortcut CSS. Fix: list properties.
- R4-AP2: Parallax/large slide on dense grids and content lists. Consequence: nausea and slow paint. Root: marketing design habit. Fix: subtle opacity/transform. APPROVED EXCEPTION (2026-07-07): hero/EntityFeature/StorySpread Ken Burns + parallax are the shipped, owner-approved cinematic signature — fully disabled under `prefers-reduced-motion` (`useParallax.ts` no-op, `animation:none` blocks) — do NOT remove.
- R4-AP3: Full-page spinner. Consequence: no structure, higher abandonment. Root: API-first loading. Fix: skeletons.

#### R4 Checklist

Run transition grep, verify reduced-motion block, test one slow-network load, confirm no auto carousel, count `will-change`.

## R5 Components

### R5.1 Buttons [BASELINE+] [depth: consensus]
Source: A-HIG Buttons, M3 buttons, WCAG, TOKENS.  
WHAT: Button min-height 44px, primary filled, secondary outlined/text, label is verb+noun.  
WHY: Clear actions reduce Hick's Law choice cost and tap errors.  
RECONCILE: Apple 44pt and M3 40-48dp; vinhlong360 uses 44px minimum, 48px preferred.  
CONTEXT: Use "Goi dien", "Nhan Zalo", "Xem ban do"; no "Dat ngay".  
VERIFY: `rg -n "<button|class=\".*btn|NuxtLink.*btn" web-nuxt`.  
EXCEPTION: Admin icon toolbar can be 32px if mouse-only and labelled. DO/DON'T: `.btn{min-height:var(--touch-min)}` / `.btn{height:36px}`.

### R5.2 Icon buttons [BASELINE+] [depth: 3-source]
Source: A-HIG Icons, M3 icon buttons, WCAG Name Role Value.  
WHAT: Icon buttons need 44x44 hitbox, visible focus, `aria-label`, and tooltip for non-obvious actions.  
WHY: Icons are often ambiguous without labels; hidden names support assistive tech.  
RECONCILE: Apple/M3 icon specs assume labelled actions; WCAG requires accessible name.  
CONTEXT: Save/share/map icons on cards must be understandable to older users.  
VERIFY: `rg -n "<button[^>]*(icon|aria-label)|btn-icon" web-nuxt`.  
EXCEPTION: Icon plus visible text can omit `aria-label` if text is the name. DO/DON'T: `<button aria-label="Luu dia diem">` / `<button>♡</button>`.

### R5.3 Entity cards [BASELINE+] [depth: 3-source]
Source: BASE travel research, M3 cards, BAYMARD.  
WHAT: EntityCard anatomy is image 3:2, category badge, title clamp 2, metadata, rating/count, contact/map CTA.  
WHY: Consistent card anatomy supports comparison and Jakob's Law for travel browsing.  
RECONCILE: Travel platform cards converge on image-first with compact metadata; vinhlong360 removes price/booking.  
CONTEXT: Highlight place/product/local story, not transaction.  
VERIFY: `rg -n "EntityCard|entity-card|card-meta|cover" web-nuxt`.  
EXCEPTION: Community posts can use text-first cards. DO/DON'T: image+title+facts+contact / price card with checkout CTA.

### R5.4 Cards are not nested [NEW] [depth: 2-source]
Source: M3 cards, NNG visual hierarchy.  
WHAT: Do not place card containers inside decorative cards; use section bands or unframed layouts.  
WHY: Nested cards blur hierarchy and waste mobile width.  
RECONCILE: M3 cards are contained objects, not page-section wrappers.  
CONTEXT: Homepage sections should be full-width bands, with cards only for repeated items.  
VERIFY: manual DOM/CSS review; `rg -n "card.*card|panel.*card" web-nuxt`.  
EXCEPTION: Modal content containing repeated item cards. DO/DON'T: `.section > .grid > .card` / `.section-card > .card`.

### R5.5 Chips [BASELINE+] [depth: consensus]
Source: M3 chips, BASE travel research, WCAG.  
WHAT: Filter chips height 36px allowed in horizontal scroll; active chip has text, color, and selected state.  
WHY: Compact chips enable many filters without overloading vertical space.  
RECONCILE: 36px chips are an exception to 44px because M3 compact chip context permits it.  
CONTEXT: Travel category filters need one-hand horizontal scrolling.  
VERIFY: `rg -n "chip|FilterChips|aria-pressed|aria-selected" web-nuxt`.  
EXCEPTION: Isolated chip as primary CTA must be 44px. DO/DON'T: `.chip{height:var(--chip-height)}` / `.chip{height:28px}`.

### R5.6 Search field [BASELINE+] [depth: 3-source]
Source: A-HIG Search fields, M3 search, BAYMARD.  
WHAT: Search field is full-width on mobile, 44px+, label/placeholder clear, suggestions keyboard accessible.  
WHY: Search is high-intent; poor autocomplete causes abandonment.  
RECONCILE: Apple and M3 both provide dedicated search patterns; ARIA governs custom suggestions.  
CONTEXT: Users search "banh khot", "cu lao", "cho noi"; tolerate Vietnamese with/without accents.  
VERIFY: `rg -n "search|autocomplete|combobox|listbox" web-nuxt`.  
EXCEPTION: Admin table filter can be compact if labelled. DO/DON'T: `<input type="search" autocomplete="off">` with listbox / fake div search.

### R5.7 Photo gallery [BASELINE+] [depth: 3-source]
Source: BASE travel research, GSC image SEO, WCAG.  
WHAT: Detail gallery uses 1 large + 4 thumbnails desktop, swipe carousel mobile, descriptive alt text.  
WHY: Travel decisions are visual; layout consistency prevents CLS and supports inspection.  
RECONCILE: Travel platforms use galleries; Google image requirements need crawlable images and alt.  
CONTEXT: AI-generated images must represent actual place/category and not fake facilities.  
VERIFY: `rg -n "PhotoGallery|NuxtImg|NuxtPicture|alt=" web-nuxt`.  
EXCEPTION: No image available -> semantic placeholder with text. DO/DON'T: `<NuxtPicture :alt="entity.name + ' o Vinh Long'">` / `alt=""` on content image.

### R5.8 Contact widget [BASELINE+] [depth: 3-source]
Source: BASE, BAYMARD mobile sticky CTA, A-HIG.  
WHAT: Replace booking widget with contact widget: Zalo + phone + map; desktop sticky sidebar, mobile bottom bar.  
WHY: Persistent primary contact lowers task friction without implying checkout.  
RECONCILE: Ecommerce sticky CTA pattern is adapted to non-transaction travel discovery.  
CONTEXT: vinhlong360 introduces places; it must not create fake booking/payment flows.  
VERIFY: `rg -n "ContactWidget|BookingWidget|checkout|payment|cart|Zalo|tel:" web-nuxt`.  
EXCEPTION: Admin contact editor is not a public CTA. DO/DON'T: `Nhan Zalo`/`Goi dien` / `Dat phong ngay`.

### R5.9 Map/list view [BASELINE+] [depth: 3-source]
Source: BASE travel research, M3 adaptive layout, WCAG pointer gestures.  
WHAT: Desktop map/list split 60/40; mobile list-first with map toggle; all map actions have button alternative.  
WHY: Maps help location decisions but can be hard to operate on mobile.  
RECONCILE: Travel patterns support split view; WCAG requires non-drag alternatives.  
CONTEXT: Local users may need directions more than price pins; use category markers.  
VERIFY: `rg -n "map|leaflet|MapList|aria-label.*map|button.*map" web-nuxt`.  
EXCEPTION: Static mini-map preview can link to full map. DO/DON'T: list+map toggle / map-only search results.

### R5.10 Review section [BASELINE+] [depth: 3-source]
Source: BASE, NNG social proof, GSC Review snippets.  
WHAT: Reviews show rating, count, distribution, newest/helpful sort, and transparent source.  
WHY: Social proof builds trust only when count and source are visible.  
RECONCILE: Google review schema needs real reviews; UX needs understandable summary.  
CONTEXT: Never fabricate "X nguoi da ghe tham" or hidden fake ratings.  
VERIFY: `rg -n "review|rating|aggregateRating|danh gia" web-nuxt server app`.  
EXCEPTION: No reviews -> honest empty state with invite. DO/DON'T: `4.5 (23 danh gia)` / `Pho bien nhat` without evidence.

### R5.11 Empty states [BASELINE+] [depth: 3-source]
Source: M3 empty states, A-HIG Feedback, NNG.  
WHAT: Empty state uses 48-64px icon, title, one sentence, one specific CTA.  
WHY: Helpful empty states recover users and reduce dead ends.  
RECONCILE: Apple feedback and M3 empty pattern align on actionability.  
CONTEXT: "Chua co danh gia nao. Hay chia se trai nghiem cua ban."  
VERIFY: `rg -n "empty-state|khong tim thay|chua co" web-nuxt`.  
EXCEPTION: Admin raw tables may show compact empty rows. DO/DON'T: icon+title+CTA / blank panel.

### R5.12 Toast/snackbar [BASELINE+] [depth: 2-source]
Source: M3 snackbar, WCAG status messages.  
WHAT: Toasts announce nonblocking results with `role="status"` and do not contain critical required actions.  
WHY: Timed messages can be missed by screen reader and low-vision users.  
RECONCILE: M3 snackbar is transient; WCAG requires status announcement.  
CONTEXT: "Da luu thanh cong" is toast; auth failure is inline/page error.  
VERIFY: `rg -n "toast|snackbar|role=\"status\"|aria-live" web-nuxt`.  
EXCEPTION: Undo action allowed if also available elsewhere. DO/DON'T: `<div role="status">Da luu</div>` / critical error toast only.

### R5.13 Dialogs [BASELINE+] [depth: consensus]
Source: WAI-APG Dialog, A-HIG Modality, M3 dialogs.  
WHAT: Dialogs have `role=dialog`, `aria-modal=true`, labelled title, focus trap, Escape close, return focus.  
WHY: Modal context must be explicit to keyboard and screen reader users.  
RECONCILE: Apple/M3 modality patterns match WAI behavior requirements.  
CONTEXT: Report content, photo lightbox, and confirmations must not strand users.  
VERIFY: `rg -n "role=\"dialog\"|aria-modal|ModalBase|Dialog" web-nuxt`.  
EXCEPTION: Nonmodal popover uses popover/menu pattern, not dialog. DO/DON'T: labelled dialog / div overlay without focus handling.

### R5.14 Bottom sheets [BASELINE+] [depth: 2-source]
Source: M3 sheets, A-HIG modality.  
WHAT: On mobile, filters/actions can become bottom sheet with drag handle plus close button.  
WHY: Sheets are reachable by thumb and preserve page context.  
RECONCILE: Apple action sheets and M3 bottom sheets converge for mobile choice panels.  
CONTEXT: Filter chips overflow, share, and route options fit sheets; contact CTA remains visible.  
VERIFY: `rg -n "sheet|bottom" web-nuxt/components web-nuxt/pages`.  
EXCEPTION: Simple 2-option menus can use native select/menu. DO/DON'T: bottom sheet with close / full-screen modal for 3 filters.

### R5.15 Tables [BASELINE+] [depth: 2-source]
Source: WCAG reflow, M3 data tables, BASE admin.  
WHAT: Public tables reflow to cards on mobile; admin tables can scroll horizontally with sticky headers.  
WHY: Dense data needs different behavior for expert vs public users.  
RECONCILE: M3 data tables are desktop-friendly; WCAG reflow requires no two-axis scroll for public reading.  
CONTEXT: Festival schedules public; admin entity moderation expert.  
VERIFY: `rg -n "<table|display:\s*table|admin-table" web-nuxt`.  
EXCEPTION: Admin-only wide tables. DO/DON'T: mobile schedule cards / public `overflow-x:auto` as only solution.

### R5.16 Badges [BASELINE+] [depth: 2-source]
Source: M3 badges, WCAG contrast, TOKENS.  
WHAT: Badges use `--text-xs`, 16-24px height, semantic/category tokens, and never carry sole meaning.  
WHY: Badges are glanceable labels, not primary content.  
RECONCILE: M3 badges are small but high contrast; WCAG requires text readability.  
CONTEXT: OCOP, season, area, verified source badges must include readable words.  
VERIFY: `rg -n "badge|chip|tag" web-nuxt`.  
EXCEPTION: Icon notification dot can be unlabeled if decorative and status text exists. DO/DON'T: `OCOP 4 sao` / color dot only.

### R5.17 Breadcrumbs [BASELINE+] [depth: 3-source]
Source: GSC BreadcrumbList, WCAG navigation, A-HIG Navigation.  
WHAT: Detail/content pages include visible breadcrumbs and JSON-LD BreadcrumbList.  
WHY: Breadcrumbs support orientation, SEO, and backtracking.  
RECONCILE: Google structured data and UX navigation both benefit.  
CONTEXT: Users should know "Trang chu > Dia diem > Cu lao An Binh".  
VERIFY: `rg -n "BreadcrumbList|breadcrumb" web-nuxt server app`.  
EXCEPTION: Homepage has no breadcrumb. DO/DON'T: visible + schema breadcrumb / schema only hidden nav.

### R5.18 Accordions [BASELINE+] [depth: 2-source]
Source: WAI-APG Accordion, NNG progressive disclosure.  
WHAT: Accordions use real buttons with `aria-expanded`; default open for critical info.  
WHY: Progressive disclosure reduces load but hidden essentials cause missed decisions.  
RECONCILE: NNG supports progressive disclosure; APG defines keyboard/ARIA.  
CONTEXT: "Gio mo cua" and contact should not be collapsed by default; long FAQ can.  
VERIFY: `rg -n "aria-expanded|accordion|details|summary" web-nuxt`.  
EXCEPTION: Native `<details>` acceptable if styled accessibly. DO/DON'T: `<button aria-expanded>` / clickable `<div>`.

### R5.19 Menus [BASELINE+] [depth: consensus]
Source: A-HIG Menus, M3 menus, WAI-APG Menu Button.  
WHAT: Menus are for actions/options, not page navigation; navigation uses links/tabs.  
WHY: Misusing menu roles confuses keyboard expectations.  
RECONCILE: Apple/M3 separate menu actions from navigation surfaces; APG defines role behavior.  
CONTEXT: "Sap xep" can be menu; "Kham pha" nav should be link/tab.  
VERIFY: `rg -n "role=\"menu|menuitem|dropdown" web-nuxt`.  
EXCEPTION: Native `<select>` for simple form choice. DO/DON'T: sort menu / nav inside ARIA menu.

### R5.20 Pagination/load more [BASELINE+] [depth: 3-source]
Source: BAYMARD, WCAG, WEBDEV.  
WHAT: Public lists use pagination or load-more with result counts; avoid infinite scroll without footer access.  
WHY: Infinite scroll hurts orientation, performance, and footer discovery.  
RECONCILE: Load-more gives control; pagination supports SEO and deep links.  
CONTEXT: Catalog pages should preserve route query and back button state.  
VERIFY: `rg -n "load more|Xem them|page=|infinite|IntersectionObserver" web-nuxt server`.  
EXCEPTION: Community feed can infinite-scroll only with accessible "Load more" fallback. DO/DON'T: button load-more / endless auto append.

### R5.21 Cards as links [BASELINE+] [depth: 2-source]
Source: WCAG Name Role Value, M3 cards, NNG.  
WHAT: If a card is clickable, use one primary link; nested buttons must not sit inside a link.  
WHY: Nested interactive controls create invalid HTML and confusing focus order.  
RECONCILE: M3 cards can be clickable; WCAG/HTML require clean interaction model.  
CONTEXT: Save/share buttons on EntityCard must be siblings, not children of card link.  
VERIFY: `rg -n "<NuxtLink[\\s\\S]*<button|role=\"button\"[\\s\\S]*<button" web-nuxt/components web-nuxt/pages`.  
EXCEPTION: Noninteractive card with separate CTA buttons. DO/DON'T: link title + separate save button / whole card link wrapping buttons.

### R5.22 Progressive enhancement for components [NEW] [depth: 3-source]
Source: WEBDEV, WCAG, Nuxt SSR in BASE.  
WHAT: Core component content renders in SSR without client-only dependency; JS enhances filtering, saving, maps.  
WHY: Slow networks and hydration failures should not blank content.  
RECONCILE: Nuxt SSR supports baseline content; rich interaction can layer on top.  
CONTEXT: Entity detail title, description, phone, address must appear before JS loads.  
VERIFY: `rg -n "ClientOnly|client-only|v-if=\"process.client" web-nuxt`.  
EXCEPTION: Map canvas can be client-only if address and directions link render server-side. DO/DON'T: SSR facts + client map / entire detail in ClientOnly.

#### R5 Decision Tree

If repeated object -> card; if choice/filter -> chip/select; if blocking decision -> dialog/sheet; if status -> toast/inline; if location task -> map/list with fallback; if transaction wording appears -> remove.

#### R5 Anti-patterns

- R5-AP1: Booking card copied from travel ecommerce. Consequence: false business promise. Root: competitor mimicry. Fix: ContactWidget.
- R5-AP2: Clickable card wrapping buttons. Consequence: invalid focus. Root: whole-card shortcut. Fix: one link + sibling controls.
- R5-AP3: Empty state with "No data". Consequence: dead end. Root: backend wording. Fix: helpful Vietnamese CTA.

#### R5 Checklist

Check 44px controls, no booking/payment labels, no nested interactive elements, all dialogs labelled, cards SSR content present.

## R6 Navigation

### R6.1 Mobile primary navigation [PROJECT DECISION 2026-07-07] [depth: consensus]
Source: A-HIG Tab bars, M3 navigation bar, NNG; overridden by shipped project decision.  
WHAT: The chosen, shipped standard is top nav + hamburger drawer on compact viewports (`layouts/default.vue` `.nav-toggle` opens the drawer); a bottom tab bar is NOT used anywhere and must not be added without owner approval.  
WHY: This nav architecture survived multiple UX audit rounds and was kept; adding a second nav system is a large structural change nobody approved.  
RECONCILE: Apple/M3 favor bottom bars generically, but newer project specs (e.g. `docs/superpowers/specs/2026-07-06-ux-scenario-matrix.md`) treat the hamburger/drawer nav as the mobile PASS criterion.  
CONTEXT: Core destinations (Trang chu, Kham pha, Cong dong, Lich trinh, Tai khoan) live in the top nav + drawer.  
VERIFY: `rg -n "nav-toggle" web-nuxt/layouts/default.vue` (present) and `rg -n "bottom-nav|tabbar" web-nuxt` (no component matches expected).  
EXCEPTION: Admin layout uses sidebar/topbar. DO/DON'T: keep top nav + drawer consistent / add a bottom tab bar in a compliance pass.

### R6.2 Medium navigation rail [BASELINE+] [depth: 2-source]
Source: M3-LAYOUT, A-HIG sidebars.  
WHAT: 600-839px can use rail or compact top nav; labels remain available on focus/expanded state.  
WHY: Tablets need more vertical content while keeping stable navigation.  
RECONCILE: M3 rail maps to medium class; Apple sidebars map to larger screens.  
CONTEXT: iPad/Android tablet users browsing travel map/list benefit from more content width.  
VERIFY: `rg -n "@media.*600|@media.*840|nav-rail" web-nuxt`.  
EXCEPTION: Simple pages may keep responsive top nav. DO/DON'T: rail + tooltip/label / icon-only mystery rail.

### R6.3 Desktop navigation [BASELINE+] [depth: 2-source]
Source: A-HIG Navigation, M3 navigation drawer, NNG Jakob.  
WHAT: Expanded desktop uses top nav or drawer with visible labels and predictable order.  
WHY: Users expect known travel categories and no hidden navigation on wide screens.  
RECONCILE: Apple top navigation and M3 drawer both expose destination labels.  
CONTEXT: Put "Kham pha" early, "Cong dong" and account/actions later.  
VERIFY: manual screenshot at 1280/1440; `rg -n "nav|NuxtLink" web-nuxt/components web-nuxt/layouts`.  
EXCEPTION: Admin has its own hierarchy. DO/DON'T: visible nav labels / desktop hamburger as primary.

### R6.4 Navigation item count [NEW] [depth: research-backed]
Source: Hick's Law, Miller's Law, NNG.  
WHAT: Primary nav max 5 mobile, max 7 desktop; overflow goes to grouped menu or footer.  
WHY: More choices increase decision time and memory burden.  
RECONCILE: Apple tab max and cognitive research align.  
CONTEXT: Do not expose every province/category in top nav; use discovery pages.  
VERIFY: manual count; `rg -n "nav-item|bottom-nav" web-nuxt`.  
EXCEPTION: Admin expert nav can exceed 7 if grouped. DO/DON'T: 5 public items / 11 top-level links.

### R6.5 Serial position order [NEW] [depth: research-backed]
Source: NNG serial position, LAWS, BASE.  
WHAT: Most important nav items are first and last; destructive/rare items never occupy those slots.  
WHY: First and last items are remembered best.  
RECONCILE: Cognitive law informs exact order within platform navigation patterns.  
CONTEXT: Put "Trang chu/Kham pha" first and "Tai khoan" last; "Bao cao" inside context.  
VERIFY: manual nav order review.  
EXCEPTION: Admin workflows may put dashboard first, settings last. DO/DON'T: Home Explore Community Account / Settings first on public nav.

### R6.6 Breadcrumb and back [BASELINE+] [depth: 3-source]
Source: GSC BreadcrumbList, A-HIG Navigation, WCAG.  
WHAT: Detail pages show breadcrumb plus a clear back/parent link; do not rely on browser back only.  
WHY: Users may enter from search/social and need orientation.  
RECONCILE: SEO breadcrumb and UX breadcrumb share data.  
CONTEXT: Travel users arriving from Zalo link should see where the entity belongs.  
VERIFY: `rg -n "breadcrumb|BreadcrumbList|back" web-nuxt/pages`.  
EXCEPTION: Modal opened from page returns focus to trigger instead. DO/DON'T: `Dia diem > Cu lao` / only browser back.

### R6.7 Search-first discovery [BASELINE+] [depth: 3-source]
Source: BAYMARD search UX, A-HIG Searching, M3 Search.  
WHAT: Discovery pages place search/filter above result list and keep query visible after navigation.  
WHY: Users need to refine without losing context.  
RECONCILE: Platform search patterns and web stateful routes agree.  
CONTEXT: Preserve `?q=banh+khot&type=dish` for share/back.  
VERIFY: `rg -n "useRoute|query|searchParams|q=" web-nuxt/pages`.  
EXCEPTION: Static guide articles may not need search. DO/DON'T: route query state / local-only search state lost on reload.

### R6.8 Footer navigation [BASELINE+] [depth: 2-source]
Source: NNG footer UX, GSC internal links.  
WHAT: Footer contains legal, contact, sitemap-like category links, not duplicate noisy primary nav only.  
WHY: Footers support recovery and crawl discovery.  
RECONCILE: SEO internal linking and UX escape hatch align.  
CONTEXT: Include "Lien he", "Dieu khoan", "Huong dan", core category links.  
VERIFY: `rg -n "footer|Dieu khoan|Lien he|sitemap" web-nuxt`.  
EXCEPTION: Admin shell can omit public footer. DO/DON'T: useful footer links / decorative footer only.

### R6.9 Skip link [BASELINE+] [depth: consensus]
Source: WCAG Bypass Blocks, A-ACC.  
WHAT: Every public layout has visible-on-focus skip link to main content.  
WHY: Keyboard users should not tab through nav on every page.  
RECONCILE: Accessibility standard drives implementation; visual design can hide until focus.  
CONTEXT: Long public nav and bottom bar require bypass.  
VERIFY: `rg -n "skip-link|#main|id=\"main\"" web-nuxt`.  
EXCEPTION: Minimal error page still needs main landmark, skip optional if no repeated nav. DO/DON'T: `<a class="skip-link" href="#main">Bo qua menu</a>` / none.

### R6.10 Active state [BASELINE+] [depth: 2-source]
Source: M3-STATE, WCAG, A-HIG.  
WHAT: Current nav item uses aria-current plus visual state layer/indicator.  
WHY: Users need orientation beyond color alone.  
RECONCILE: M3 selected state and WCAG state exposure align.  
CONTEXT: Bottom nav current section must be obvious in dark and light mode.  
VERIFY: `rg -n "aria-current|router-link-active|active" web-nuxt/components web-nuxt/layouts`.  
EXCEPTION: External links do not use aria-current. DO/DON'T: `<NuxtLink aria-current="page">` / color-only active.

#### R6 Decision Tree

Compact -> top nav + hamburger drawer (project decision, see R6.1); medium -> rail/top hybrid; expanded -> visible top/drawer; detail -> breadcrumb; long nav -> footer grouping; search page -> route query state.

#### R6 Anti-patterns

- R6-AP1: OVERRIDDEN (2026-07-07) — hamburger + top nav IS the chosen shipped standard (see R6.1); do not "fix" it with a bottom nav. Keep drawer item order stable and core paths near the top of the drawer instead.
- R6-AP2: Too many top-level links. Consequence: Hick's Law overload. Root: taxonomy exposed as nav. Fix: group categories.
- R6-AP3: No current state. Consequence: disorientation. Root: visual-only routing. Fix: `aria-current`.

#### R6 Checklist

Count nav items, test 360/768/1280 viewports, tab through skip link, confirm breadcrumbs and route query persistence.

## R7 Forms

### R7.1 Label every input [BASELINE+] [depth: consensus]
Source: WCAG 3.3.2, A-HIG Text fields, M3 text fields.  
WHAT: Every input/select/textarea has visible label or `aria-label`; placeholder is never the only label.  
WHY: Placeholders disappear and screen readers need persistent names.  
RECONCILE: Apple/M3 text fields include labels/supporting text; WCAG requires labels.  
CONTEXT: Forms in Vietnamese must remain clear for older users.  
VERIFY: `rg -n "<input|<select|<textarea" web-nuxt`.  
EXCEPTION: Search input can use visible adjacent label/icon plus `aria-label`. DO/DON'T: `<label for="phone">So dien thoai</label>` / placeholder-only.

### R7.2 Input size [BASELINE+] [depth: consensus]
Source: A-ACC, M3 text fields, WCAG Target Size.  
WHAT: Form controls min-height 44px, font-size 16px, padding via `--space-3/4`.  
WHY: Prevent iOS zoom and tap errors.  
RECONCILE: Apple 44pt and M3 56dp text fields; vinhlong360 minimum 44px, preferred 48-56px.  
CONTEXT: Phone/report/comment forms are often used outdoors on mobile.  
VERIFY: `rg -n "input|select|textarea|min-height|font-size" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Admin dense filters can be 40px with 16px font. DO/DON'T: `.input{min-height:44px;font-size:1rem}` / `.input{height:34px;font-size:14px}`.

### R7.3 Validation timing [BASELINE+] [depth: 3-source]
Source: M3 text fields, A-HIG Feedback, NNG forms.  
WHAT: Validate on blur/submit; do not shout errors while user is typing except format masks.  
WHY: Premature errors increase anxiety and interrupt completion.  
RECONCILE: M3 supporting text and Apple feedback should be helpful, not punitive.  
CONTEXT: Vietnamese phone/name fields should allow partial entry.  
VERIFY: `rg -n "@input|@blur|validate|aria-invalid" web-nuxt`.  
EXCEPTION: Character counter can update live without error state. DO/DON'T: blur validation / red error after first digit.

### R7.4 Error wiring [BASELINE+] [depth: consensus]
Source: WCAG 3.3.1/3.3.3, M3 error state.  
WHAT: Invalid fields set `aria-invalid=true` and `aria-describedby` to error/help text.  
WHY: Screen readers need programmatic connection from field to message.  
RECONCILE: M3 visual error plus WCAG semantics both required.  
CONTEXT: Report/comment/auth flows must be recoverable in Vietnamese.  
VERIFY: `rg -n "aria-invalid|aria-describedby|error" web-nuxt/components web-nuxt/pages`.  
EXCEPTION: Server page-level error also needs summary. DO/DON'T: `<input aria-describedby="phone-error">` / red border only.

### R7.5 Phone fields [NEW] [depth: 2-source]
Source: HTML input best practices, BASE Vietnamese content.  
WHAT: Phone input uses `type="tel"`, `inputmode="tel"`, accepts `0xxx.xxx.xxx` and `+84`; do not use number input.  
WHY: Number inputs strip leading zero and show wrong keyboard controls.  
RECONCILE: Native web semantics and Vietnamese phone formatting require tel.  
CONTEXT: Contact phone is central to vinhlong360.  
VERIFY: `rg -n "type=\"number\"|type=\"tel\"|inputmode" web-nuxt`.  
EXCEPTION: Pure numeric counts may use number input in admin. DO/DON'T: `<input type="tel" inputmode="tel">` / `<input type="number">` for phone.

### R7.6 OTP fields [BASELINE+] [depth: consensus]
Source: WCAG input purpose, Apple autocomplete, BASE.  
WHAT: OTP supports paste, `autocomplete="one-time-code"`, `inputmode="numeric"`, and one logical field or well-managed group.  
WHY: OTP friction is a major mobile drop-off point.  
RECONCILE: Platform autocomplete and accessibility both favor semantic input.  
CONTEXT: Vietnamese users often copy OTP from SMS/Zalo.  
VERIFY: `rg -n "one-time-code|otp|inputmode=\"numeric\"" web-nuxt`.  
EXCEPTION: Admin test harness can bypass OTP UI. DO/DON'T: paste-friendly OTP / six isolated fields blocking paste.

### R7.7 Permission requests [NEW] [depth: research-backed]
Source: A-HIG permissions, NNG trust, Cialdini trust.  
WHAT: Explain value before location permission: "Cho phep vi tri de tim diem gan ban."  
WHY: Users grant permission when benefit and scope are clear.  
RECONCILE: Apple requires purpose strings; UX writing clarifies value.  
CONTEXT: Location is useful for nearby attractions but must not be forced.  
VERIFY: `rg -n "geolocation|permissions|vi tri|navigator.geolocation" web-nuxt`.  
EXCEPTION: Manual address/map search must work without permission. DO/DON'T: explain then ask / browser prompt on page load.

### R7.8 Required fields [BASELINE+] [depth: consensus]
Source: WCAG 3.3.2, BAYMARD forms, M3 forms.  
WHAT: Mark required fields in label text and keep optional fields truly optional.  
WHY: Hidden required rules create failed submissions.  
RECONCILE: Baymard form research and WCAG labels align.  
CONTEXT: Reports should require reason/content, not phone/contact unless needed.  
VERIFY: `rg -n "required|aria-required|\\*" web-nuxt`.  
EXCEPTION: Admin batch tools may document required columns in a header. DO/DON'T: `Ly do (bat buoc)` / unlabeled red asterisk only.

### R7.9 Form layout [BASELINE+] [depth: 3-source]
Source: NNG forms, M3 layout, A-HIG.  
WHAT: Public forms are single-column; group related fields with 16-24px gaps and clear section labels.  
WHY: Multi-column forms break mobile flow and tab order.  
RECONCILE: Desktop density cannot override mobile-first completion.  
CONTEXT: Report, profile, contact, itinerary forms must feel simple.  
VERIFY: manual tab order; `rg -n "form|grid-template-columns" web-nuxt/pages web-nuxt/components`.  
EXCEPTION: Admin desktop filters can use multi-column if tab order remains logical. DO/DON'T: one-column public form / side-by-side phone+name on mobile.

### R7.10 Submit state [BASELINE+] [depth: 3-source]
Source: M3 states, WCAG status messages, WEBDEV.  
WHAT: Submit disables duplicate action, keeps button size, shows local spinner/text, and announces result.  
WHY: Prevents duplicate reports/comments and reassures users during network delay.  
RECONCILE: M3 loading state and WCAG live status both apply.  
CONTEXT: Mobile network may lag; feedback must appear immediately.  
VERIFY: `rg -n "isSubmitting|loading|disabled|aria-busy" web-nuxt`.  
EXCEPTION: Idempotent admin refresh can remain enabled with debounce. DO/DON'T: `<button :disabled="pending" aria-busy="pending">` / button text disappears and width shifts.

#### R7 Decision Tree

If value is contact -> tel/email/url input; if selection <=7 options -> radio/segmented; if many options -> select/search; if error -> inline; if permission -> explain before prompt.

#### R7 Anti-patterns

- R7-AP1: Placeholder-only labels. Consequence: lost context. Root: minimalist forms. Fix: visible label.
- R7-AP2: `type=number` for phone. Consequence: lost leading zero. Root: numeric thinking. Fix: `type=tel`.
- R7-AP3: Error on every keystroke. Consequence: anxiety. Root: eager validation. Fix: blur/submit validation.

#### R7 Checklist

Run input grep, test paste OTP/phone, tab through form, verify `aria-invalid/describedby`, simulate slow submit.

## R8 Images

### R8.1 Real content images [BASELINE+] [depth: 3-source]
Source: GSC image SEO, WCAG alt, BASE content rules.  
WHAT: Images must represent actual entity/category truth; no stock images, no fake facilities, no irrelevant atmosphere.  
WHY: Trust triangle requires integrity; misleading visuals damage travel decisions.  
RECONCILE: AI-generated assets are allowed only when faithful and labelled internally.  
CONTEXT: Local place/product images should reveal subject, not generic Mekong vibes.  
VERIFY: manual content audit; `rg -n "pexels|unsplash|shutterstock|wikimedia|stock" .`.  
EXCEPTION: Abstract illustration for empty state. DO/DON'T: local-specific AI image / stock-like sunset.

### R8.2 Responsive formats [BASELINE+] [depth: 3-source]
Source: WEBDEV images, GSC image SEO, BASE.  
WHAT: Use `<NuxtPicture>` or responsive `srcset/sizes`; AVIF then WebP/JPEG fallback; quality around 75.  
WHY: Images dominate mobile payload and LCP.  
RECONCILE: Google wants crawlable quality; web.dev wants responsive bytes.  
CONTEXT: Rural mobile data and travel browsing require small image variants.  
VERIFY: `rg -n "NuxtPicture|srcset|sizes|format=.*avif|loading=" web-nuxt`.  
EXCEPTION: Tiny SVG/icon assets. DO/DON'T: `<NuxtPicture sizes="100vw md:50vw">` / single 2400px JPEG.

### R8.3 LCP image priority [BASELINE+] [depth: consensus]
Source: WEBDEV LCP, GSC, BASE.  
WHAT: Above-fold hero/detail image is not lazy-loaded and uses `fetchpriority="high"`/preload when it is LCP.  
WHY: Lazy-loading LCP images delays first meaningful view.  
RECONCILE: Performance and SEO both need quick, visible primary image.  
CONTEXT: Entity detail cover image should load quickly but stay truthful.  
VERIFY: Lighthouse LCP; `rg -n "fetchpriority|preload|loading=\"lazy\"" web-nuxt`.  
EXCEPTION: Pages with text LCP and below-fold gallery can lazy-load all images. DO/DON'T: `fetchpriority="high"` for first cover / lazy LCP.

### R8.4 Reserve aspect ratio [BASELINE+] [depth: consensus]
Source: WEBDEV CLS, GSC image SEO, BASE.  
WHAT: Every content image reserves `width/height` or `aspect-ratio` before load.  
WHY: Prevents CLS and scroll jumps.  
RECONCILE: M3 cards specify aspect ratios; web.dev measures layout stability.  
CONTEXT: Card grids should not jump as AI images load.  
VERIFY: `rg -n "<img|NuxtImg|NuxtPicture|aspect-ratio" web-nuxt`.  
EXCEPTION: Decorative CSS background with fixed container. DO/DON'T: `.cover{aspect-ratio:var(--ratio-card)}` / image with auto container.

### R8.5 Alt text [BASELINE+] [depth: consensus]
Source: WCAG 1.1.1, GSC image SEO, A-ACC.  
WHAT: Informative images get concise Vietnamese alt; decorative images use empty alt or CSS background.  
WHY: Alt supports screen readers and image search.  
RECONCILE: Accessibility and SEO share the need for meaningful descriptions.  
CONTEXT: "Cong gom Mang Thit luc hoang hon" is useful; "image" is not.  
VERIFY: `rg -n "<img(?![^>]*alt=)|NuxtImg(?![^>]*alt=)|NuxtPicture(?![^>]*alt=)" web-nuxt -P`.  
EXCEPTION: Avatar initials may use accessible name from adjacent user text. DO/DON'T: `alt="Banh khot Vinh Long"` / `alt="photo"`.

### R8.6 Save-Data image mode [NEW] [depth: 3-source]
Source: WEBDEV, DR network context, BASE.  
WHAT: When `Save-Data:on` or `navigator.connection.saveData`, serve thumbnails, skip gallery preload, reduce animation.  
WHY: Data saver users explicitly prefer lower bytes.  
RECONCILE: Progressive enhancement respects user network preferences.  
CONTEXT: Vietnamese mobile data is cheap relative to past years but travel networks remain inconsistent.  
VERIFY: server/client grep `Save-Data|saveData|effectiveType`; manual Chrome DevTools.  
EXCEPTION: Primary content image remains available, just smaller. DO/DON'T: thumbnail list / full gallery eager load.

### R8.7 Image failure fallback [NEW] [depth: 2-source]
Source: WCAG, WEBDEV.  
WHAT: Broken images show stable placeholder, alt/name text, and no layout collapse.  
WHY: Network failures should not erase entity identity.  
RECONCILE: Accessibility alt plus performance layout reservation combine.  
CONTEXT: Users on weak signal still need name/address/contact.  
VERIFY: DevTools block image URL; visual test.  
EXCEPTION: Decorative image can disappear. DO/DON'T: placeholder with entity name / blank square collapse.

### R8.8 Gallery count honesty [NEW] [depth: research-backed]
Source: NNG trust, Cialdini social proof ethics, BASE.  
WHAT: "Xem X anh" count must match actual approved images; never inflate count.  
WHY: Trust depends on integrity and accurate expectations.  
RECONCILE: Social proof is useful only when truthful.  
CONTEXT: Local businesses/places should not appear more documented than they are.  
VERIFY: unit/API test count vs approved media; `rg -n "Xem .*anh|galleryCount|images.length" web-nuxt server`.  
EXCEPTION: None for public UI. DO/DON'T: actual count / fake "99+ anh".

#### R8 Decision Tree

If above-fold -> priority image; if below-fold -> lazy responsive; if decorative -> CSS/empty alt; if user Save-Data -> smaller; if no image -> semantic placeholder.

#### R8 Anti-patterns

- R8-AP1: Single giant JPEG. Consequence: LCP/data waste. Root: asset shortcut. Fix: responsive AVIF/WebP.
- R8-AP2: Atmospheric stock-like image. Consequence: low trust. Root: marketing filler. Fix: subject-specific AI/local asset.
- R8-AP3: Missing alt/aspect ratio. Consequence: inaccessible and CLS. Root: image component omission. Fix: alt + ratio.

#### R8 Checklist

Run image grep, Lighthouse LCP/CLS, throttle Slow 3G, block image URLs, verify no stock source strings.

## R9 Dark Mode

### R9.1 Semantic dark override [BASELINE+] [depth: consensus]
Source: A-COLOR Dark Mode, M3-COLOR, TOKENS.  
WHAT: Dark mode overrides semantic tokens in `.dark`, not individual components unless unavoidable.  
WHY: Central tokens prevent inconsistent surfaces and contrast regressions.  
RECONCILE: Apple dynamic colors and M3 roles both adapt by semantic role.  
CONTEXT: Current repo has `variables.css` plus `dark-overrides.css`; new components should need no scoped dark patch.  
VERIFY: `rg -n "^\\.dark|:global\\(\\.dark\\)" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Third-party/library or legacy scoped CSS needing bridge override. DO/DON'T: semantic token / `.dark .new-card{background:#222}`.

### R9.2 Dark surfaces [BASELINE+] [depth: consensus]
Source: A-COLOR, M3 tonal elevation, TOKENS.  
WHAT: Dark surfaces use `--surface-container-*` and `--surface-1..5`; avoid pure black large areas.  
WHY: Near-black reduces halation and maintains elevation separation.  
RECONCILE: Apple dark backgrounds and M3 tonal elevation align with token ramp.  
CONTEXT: Reading local stories at night should not glare.  
VERIFY: `rg -n "background:\s*#000|background:\s*black" web-nuxt`.  
EXCEPTION: Scrim/overlay can use `--scrim`/`--overlay-dark-heavy`. DO/DON'T: `background:var(--surface-container-low)` / `background:#000`.

### R9.3 Dark link color [BASELINE+] [depth: consensus]
Source: WCAG, A-COLOR, BASE gaps.  
WHAT: Links in dark mode use explicit token color and underline; never browser default blue.  
WHY: Default blue can fail contrast on dark warm surfaces.  
RECONCILE: WCAG contrast and Apple dynamic color require mode-specific treatment.  
CONTEXT: Guide articles and breadcrumbs must remain readable in dark mode.  
VERIFY: `rg -n "\\.dark .*a|a:hover|text-decoration" web-nuxt/assets/css`.  
EXCEPTION: Button links use button foreground. DO/DON'T: `.dark .prose a{color:var(--primary-fg-strong)}` / default anchor blue.

### R9.4 No color inversion filter [NEW] [depth: 2-source]
Source: A-COLOR, WEBDEV.  
WHAT: Do not implement dark mode by `filter: invert()` on the app.  
WHY: Inversion breaks images, brand colors, maps, and contrast pairs.  
RECONCILE: Semantic dynamic colors are the correct approach.  
CONTEXT: Local images and Zalo brand color must remain true.  
VERIFY: `rg -n "filter:\s*invert|mix-blend-mode" web-nuxt`.  
EXCEPTION: Individual monochrome icon can invert if decorative and tested. DO/DON'T: token overrides / whole-app invert.

### R9.5 Dark image treatment [BASELINE+] [depth: 2-source]
Source: A-COLOR, WEBDEV, BASE.  
WHAT: Dark mode can slightly reduce image brightness only under text overlays; do not globally dim all images.  
WHY: Users need to inspect actual place/product details.  
RECONCILE: Readability overlays are allowed; content integrity wins elsewhere.  
CONTEXT: Food/craft photos should stay appetizing and inspectable.  
VERIFY: `rg -n "filter:\s*brightness|contrast\\(" web-nuxt`.  
EXCEPTION: Background hero image under text. DO/DON'T: overlay token / global `img{filter:brightness(.8)}`.

### R9.6 Dark focus and outlines [BASELINE+] [depth: consensus]
Source: WCAG Focus Appearance, M3-STATE, TOKENS.  
WHAT: Dark focus ring uses `--focus-ring` and sufficient contrast against dark surface.  
WHY: Low-contrast glows disappear on dark backgrounds.  
RECONCILE: Token ring differs light/dark; state still same semantic role.  
CONTEXT: Admin tables and public forms need visible keyboard path at night.  
VERIFY: manual keyboard dark mode; `rg -n ":focus-visible" web-nuxt`.  
EXCEPTION: Native outline if contrast passes. DO/DON'T: dark focus token / transparent outline.

### R9.7 Dark mode font weight [BASELINE+] [depth: 2-source]
Source: BASE gap E5, A-COLOR, NNG readability.  
WHAT: Avoid ultra-light text in dark mode; body weight >=400, headings 500-700.  
WHY: Thin bright text blooms and becomes harder to read.  
RECONCILE: Apple dynamic text and readability research support sufficient stroke weight.  
CONTEXT: Vietnamese diacritics need enough weight on dark surfaces.  
VERIFY: `rg -n "font-weight:\s*(100|200|300)|--weight-light" web-nuxt`.  
EXCEPTION: Decorative wordmark only. DO/DON'T: `font-weight:var(--weight-normal)` / `font-weight:300` body.

### R9.8 Dark parity test [NEW] [depth: 3-source]
Source: WCAG, A-COLOR, M3-COLOR.  
WHAT: Every new component must be manually checked in light and dark at 360px/1280px before merge.  
WHY: Token intent does not guarantee component composition contrast.  
RECONCILE: Automated contrast catches text, manual catches surfaces/images/focus.  
CONTEXT: Existing `dark-overrides.css` shows legacy scoped fixes remain.  
VERIFY: screenshot checklist + Lighthouse dark mode if available.  
EXCEPTION: Admin-only feature may be checked at desktop + 768px. DO/DON'T: two-mode screenshot / light-only review.

#### R9 Decision Tree

If color differs by mode -> semantic token; if legacy scoped issue -> `dark-overrides.css`; if overlay text -> scrim; if brand/external -> dark-specific brand token; if image content -> preserve.

#### R9 Anti-patterns

- R9-AP1: Component-scoped raw dark colors. Consequence: drift. Root: quick fix. Fix: semantic token.
- R9-AP2: Global image dimming. Consequence: poor inspection. Root: dark aesthetic. Fix: overlay only.
- R9-AP3: Light focus ring copied to dark. Consequence: invisible keyboard focus. Root: no dark test. Fix: dark focus token.

#### R9 Checklist

Run `.dark` grep, test light/dark screenshots, verify link contrast, focus every interactive element, inspect images.

## R10 Accessibility

### R10.1 Landmark structure [BASELINE+] [depth: consensus]
Source: WCAG, WAI, A-ACC.  
WHAT: Pages include header/nav/main/footer landmarks; `main` is unique and focus targetable.  
WHY: Landmarks let assistive tech jump through page structure.  
RECONCILE: Semantic HTML is the shared base across platforms.  
CONTEXT: Long travel pages need quick navigation to content and contact.  
VERIFY: `rg -n "<main|role=\"main\"|<nav|<footer|skip-link" web-nuxt`.  
EXCEPTION: Modal-only error shell still needs main. DO/DON'T: `<main id="main">` / anonymous div page.

### R10.2 Keyboard complete [BASELINE+] [depth: consensus]
Source: WCAG 2.1.1, WAI-APG, A-ACC.  
WHAT: Every interactive feature works with keyboard: Tab, Shift+Tab, Enter, Space, Escape where relevant.  
WHY: Keyboard access is foundational for motor and power users.  
RECONCILE: ARIA patterns define keys; visual design must follow.  
CONTEXT: Map/list toggle, filters, gallery, comments, admin tables all need keyboard paths.  
VERIFY: Playwright keyboard tests or manual tab map.  
EXCEPTION: Raw map pan must have alternative buttons/list links. DO/DON'T: keyboard filter chips / pointer-only drag.

### R10.3 Accessible names [BASELINE+] [depth: consensus]
Source: WCAG 4.1.2, A-ACC, WAI-APG.  
WHAT: Buttons, links, inputs, iframes, icons have programmatic names.  
WHY: Screen readers announce role/name/state.  
RECONCILE: Apple VoiceOver labels and WCAG name-role-value align.  
CONTEXT: Icon-only save/share/report actions must say what they do in Vietnamese.  
VERIFY: `rg -n "<button(?![^>]*aria-label)|<iframe(?![^>]*title=)" web-nuxt -P`.  
EXCEPTION: Button with visible text has name. DO/DON'T: `aria-label="Chia se dia diem"` / unlabeled SVG button.

### R10.4 Target size [BASELINE+] [depth: research-backed]
Source: WCAG 2.5.8, A-ACC, M3, NNG/Fitts.  
WHAT: Public interactive targets are 44x44px minimum; spacing 8px; 48px preferred.  
WHY: Smaller targets raise error rate, especially outdoors.  
RECONCILE: WCAG AA 24px is floor; Apple/M3 better fit travel mobile.  
CONTEXT: One-hand Vietnamese mobile usage makes 44px nonnegotiable.  
VERIFY: same as R1.6 plus browser tap audit.  
EXCEPTION: Inline links in body text with underline. DO/DON'T: `min-height:var(--touch-min)` / `height:30px`.

### R10.5 Focus not obscured [BASELINE+] [depth: consensus]
Source: WCAG 2.4.11/2.4.12, BASE.  
WHAT: Focused element is at least partially visible and not hidden by sticky nav/contact bar.  
WHY: Hidden focus breaks keyboard interaction.  
RECONCILE: Sticky UI allowed only with scroll offset.  
CONTEXT: Bottom contact bar must not cover focused CTA or form input.  
VERIFY: keyboard through 360px page; `rg -n "scroll-padding|scroll-margin|position:\s*fixed" web-nuxt`.  
EXCEPTION: Browser-managed focus inside native select. DO/DON'T: scroll-padding / fixed bar covering last button.

### R10.6 Color not sole cue [BASELINE+] [depth: consensus]
Source: WCAG 1.4.1, A-ACC, M3.  
WHAT: Status/selection/error use color plus text/icon/shape.  
WHY: Color perception varies and color can be lost in glare.  
RECONCILE: All sources require redundant cues.  
CONTEXT: Category chips need labels; report status needs words.  
VERIFY: manual status audit; `rg -n "active|selected|error|success|warning" web-nuxt`.  
EXCEPTION: Decorative color accents with no meaning. DO/DON'T: icon+label+color / green border only.

### R10.7 ARIA only when needed [BASELINE+] [depth: consensus]
Source: WAI-APG, WCAG, A-ACC.  
WHAT: Prefer native HTML; add ARIA only for custom widgets following full pattern.  
WHY: Bad ARIA is worse than no ARIA.  
RECONCILE: Native controls already expose roles/states.  
CONTEXT: Use `<button>`, `<details>`, `<select>` before custom roles.  
VERIFY: `rg -n "role=\"" web-nuxt`.  
EXCEPTION: Combobox/listbox/dialog need ARIA if custom. DO/DON'T: native button / `div role=button` without key handlers.

### R10.8 Dialog focus trap [BASELINE+] [depth: consensus]
Source: WAI-APG Dialog, WCAG.  
WHAT: Modal traps focus, Escape closes if safe, trigger receives focus after close.  
WHY: Keyboard users must not tab into hidden page content.  
RECONCILE: ARIA modal behavior is standardized.  
CONTEXT: Photo/report/share dialogs must comply.  
VERIFY: Playwright keyboard test; `rg -n "aria-modal|focusTrap|Escape" web-nuxt`.  
EXCEPTION: Destructive confirmation may require explicit cancel/confirm but still handles focus. DO/DON'T: trap+return / overlay div only.

### R10.9 Live regions [BASELINE+] [depth: consensus]
Source: WCAG 4.1.3, WAI.  
WHAT: Async success/error/loading results use `role=status` or `aria-live=polite`; urgent errors use assertive sparingly.  
WHY: Screen reader users need status changes without focus theft.  
RECONCILE: M3 snackbars plus WCAG status messages.  
CONTEXT: Save/report/comment result messages must announce.  
VERIFY: `rg -n "aria-live|role=\"status\"|role=\"alert\"" web-nuxt`.  
EXCEPTION: Visual-only progress skeleton can be hidden if `aria-busy` on container. DO/DON'T: polite status / silent save.

### R10.10 Reduced cognitive load [NEW] [depth: research-backed]
Source: W3C COGA, NNG, Sweller cognitive load.  
WHAT: One primary task per screen region; progressive disclosure for secondary details.  
WHY: Extraneous load reduces completion and comprehension.  
RECONCILE: M3/Apple progressive disclosure implements cognitive science.  
CONTEXT: Entity detail first shows name, facts, contact; long history/story follows.  
VERIFY: manual page review; count primary CTAs per viewport <=1.  
EXCEPTION: Admin dashboards can show multiple expert actions grouped. DO/DON'T: one primary CTA / three equal CTAs in hero.

### R10.11 Language attribute [BASELINE+] [depth: consensus]
Source: WCAG 3.1.1, GSC, A-ACC.  
WHAT: HTML language is `vi`; English code terms in docs do not affect public pages.  
WHY: Screen readers need pronunciation rules.  
RECONCILE: Vietnamese-only product simplifies language handling.  
CONTEXT: Public UI is Vietnamese; avoid mixed English labels.  
VERIFY: `rg -n "lang=|htmlAttrs|useHead" web-nuxt`.  
EXCEPTION: Brand names remain unchanged. DO/DON'T: `<html lang="vi">` / missing lang.

### R10.12 Motion sensitivity [BASELINE+] [depth: consensus]
Source: WCAG 2.3.3, A-MOTION, M3-MOTION.  
WHAT: Support `prefers-reduced-motion`; no flashing or forced large movement; parallax only within the approved reduced-motion-gated cinematic layer (see R4-AP2 approved exception).  
WHY: Motion can cause vestibular symptoms and distraction.  
RECONCILE: See R4; accessibility makes it mandatory.  
CONTEXT: Users in moving vehicles may be more sensitive.  
VERIFY: `rg -n "prefers-reduced-motion|animation" web-nuxt`.  
EXCEPTION: Instant state changes. DO/DON'T: reduced CSS block / unavoidable scroll-jacking.

### R10.13 Accessible map alternatives [BASELINE+] [depth: consensus]
Source: WCAG Pointer Gestures, WCAG Dragging, BASE.  
WHAT: Map pan/drag/route reordering has button/list alternative and text address.  
WHY: Pointer gestures are not accessible to all users.  
RECONCILE: Rich map can exist only with equivalent controls.  
CONTEXT: Tourist can still get address/directions if map is unusable.  
VERIFY: `rg -n "drag|map|route|directions|Chi duong" web-nuxt`.  
EXCEPTION: Static decorative map image with adjacent address. DO/DON'T: address + "Chi duong" link / map-only location.

### R10.14 High contrast preference [NEW] [depth: 2-source]
Source: WCAG contrast, CSS `prefers-contrast`, BASE.  
WHAT: Support `@media (prefers-contrast: more)` by strengthening border/text/focus tokens.  
WHY: Some users request stronger contrast at OS level.  
RECONCILE: Token system can increase contrast without duplicating components.  
CONTEXT: Sand/cream UI must become sharper when requested.  
VERIFY: `rg -n "prefers-contrast" web-nuxt`.  
EXCEPTION: If unsupported, base contrast still must pass AA. DO/DON'T: contrast media tokens / ignore OS contrast.

#### R10 ARIA Pattern Sheet

| Pattern | Required |
|---|---|
| Dialog | `role=dialog`, `aria-modal=true`, labelled title, focus trap, Escape, return focus |
| Combobox | input `role=combobox`, `aria-expanded`, `aria-controls`, active descendant, arrow keys |
| Listbox | `role=listbox`, `role=option`, `aria-selected`, arrow/home/end keys |
| Tabs | `role=tablist/tab/tabpanel`, selected tab, arrow keys, visible focus |
| Accordion | real button, `aria-expanded`, `aria-controls`, panel labelled |
| Toast/status | `role=status` or `aria-live=polite`, no focus theft |

#### R10 Keyboard Map

| Key | Behavior |
|---|---|
| Tab/Shift+Tab | Move through focusable items in DOM order |
| Enter | Activate link/button, submit focused form button |
| Space | Activate button, toggle checkbox/chip |
| Escape | Close dialog/menu/sheet and return focus |
| Arrow keys | Move inside listbox/tabs/menu only when role supports it |
| Home/End | First/last option in listbox/tabs when implemented |

#### R10 Decision Tree

Use native HTML first; if custom widget -> APG pattern; if pointer gesture -> button alternative; if async -> live region; if sticky -> focus visibility test.

#### R10 Anti-patterns

- R10-AP1: `div role=button` with no keyboard. Consequence: inaccessible action. Root: styling shortcut. Fix: native button.
- R10-AP2: Modal without focus trap. Consequence: keyboard escapes behind overlay. Root: visual-only modal. Fix: APG dialog.
- R10-AP3: Color-only errors. Consequence: missed validation. Root: visual design shortcut. Fix: text+icon+ARIA.

#### R10 Checklist

Run Lighthouse Accessibility, keyboard-test main flows, run ARIA grep, verify reduced motion, check map alternatives.

## R11 SEO

### R11.1 One indexable H1 [BASELINE+] [depth: 3-source]
Source: GSC, WCAG, BASE.  
WHAT: Each indexable page has one descriptive `h1` matching page/entity intent.  
WHY: Headings help search engines and users understand topic quickly.  
RECONCILE: SEO and accessibility hierarchy align.  
CONTEXT: Use Vietnamese with accents: "Cu lao An Binh", "Dac san Vinh Long".  
VERIFY: `rg -n "<h1|useHead\\(|title:" web-nuxt/pages`.  
EXCEPTION: Error/admin utility pages may have non-indexable titles. DO/DON'T: entity name h1 / marketing slogan h1 only.

### R11.2 Title and meta description [BASELINE+] [depth: 3-source]
Source: GSC, BASE, NNG.  
WHAT: Public pages set unique title and 120-160 char Vietnamese description; no keyword stuffing.  
WHY: Search snippets and social previews need concise value.  
RECONCILE: Google may rewrite snippets, but good descriptions help users.  
CONTEXT: Mention Vinh Long/local area naturally.  
VERIFY: `rg -n "useSeoMeta|meta.*description|title:" web-nuxt/pages`.  
EXCEPTION: Admin noindex pages. DO/DON'T: `title:"Cho noi Tra On - Vinh Long"` / duplicate "vinhlong360".

### R11.3 Clean Vietnamese slugs [BASELINE+] [depth: 2-source]
Source: GSC URL guidance, BASE.  
WHAT: URL slugs are ASCII, hyphen-separated, stable; titles keep Vietnamese accents.  
WHY: Clean slugs are shareable and avoid encoding mess.  
RECONCILE: Content can be Vietnamese; URL technical layer stays ASCII.  
CONTEXT: `/dia-diem/cu-lao-an-binh`, not percent-encoded accents.  
VERIFY: tests for slugify; `rg -n "slug|slugify|encodeURIComponent" app server web-nuxt`.  
EXCEPTION: Existing legacy slugs need redirects. DO/DON'T: `banh-khot-vinh-long` / `bánh%20khọt`.

### R11.4 BreadcrumbList schema [BASELINE+] [depth: consensus]
Source: GSC-SD Breadcrumb, BASE.  
WHAT: Public non-home pages output JSON-LD BreadcrumbList matching visible breadcrumb.  
WHY: Helps search result context and user orientation.  
RECONCILE: Visible and structured breadcrumbs must not diverge.  
CONTEXT: Include category and entity when available.  
VERIFY: `rg -n "BreadcrumbList|itemListElement" web-nuxt server`.  
EXCEPTION: Homepage. DO/DON'T: visible+JSON-LD same chain / schema with hidden fake category.

### R11.5 Place/LocalBusiness schema [BASELINE+] [depth: 3-source]
Source: GSC-SD, schema.org, BASE.  
WHAT: Entity pages with real location/contact use `TouristAttraction`/`LocalBusiness` fields: name, address, geo, image, url, telephone when verified.  
WHY: Structured data improves machine understanding and AI citations.  
RECONCILE: Use type that matches entity; do not force all entities into LocalBusiness.  
CONTEXT: Accommodation/dish/business can be LocalBusiness; heritage/nature may be TouristAttraction/Place.  
VERIFY: Rich Results Test; `rg -n "TouristAttraction|LocalBusiness|GeoCoordinates|PostalAddress" web-nuxt server`.  
EXCEPTION: Unverified phone/address omitted, not fabricated. DO/DON'T: verified geo / fake telephone.

### R11.6 Review schema honesty [BASELINE+] [depth: 3-source]
Source: GSC Review snippet, NNG trust, BASE.  
WHAT: Only output `AggregateRating`/`Review` from real user reviews; never self-serving fake review snippets.  
WHY: Google policies and trust require authentic review data.  
RECONCILE: Social proof UX must obey structured-data rules.  
CONTEXT: Community review counts must be transparent.  
VERIFY: `rg -n "AggregateRating|Review|reviewRating|ratingValue" web-nuxt server`.  
EXCEPTION: Editorial "recommended" badge is not review schema. DO/DON'T: actual count/rating / hardcoded `ratingValue:5`.

### R11.7 Article schema [BASELINE+] [depth: 2-source]
Source: GSC Article, BASE.  
WHAT: Community/editorial articles use Article/BlogPosting with headline <110 chars, date, author/source, image when present.  
WHY: Article schema helps content discovery and AI extraction.  
RECONCILE: Not every entity page is Article; use appropriate type.  
CONTEXT: Local stories and guides fit Article; product/place detail does not need Article primary type.  
VERIFY: `rg -n "Article|BlogPosting|datePublished|author" web-nuxt server`.  
EXCEPTION: User comments are not standalone Article unless rendered as posts. DO/DON'T: guide Article / entity forced as BlogPosting.

### R11.8 Image SEO [BASELINE+] [depth: 3-source]
Source: GSC image SEO, WEBDEV images, WCAG.  
WHAT: Important images are crawlable, have alt, responsive sizes, and stable dimensions.  
WHY: Image search and page performance are both traffic factors.  
RECONCILE: Same implementation serves accessibility, SEO, and CWV.  
CONTEXT: Food/craft/local attraction images are high-intent search assets.  
VERIFY: `rg -n "robots|NuxtPicture|alt=|loading=" web-nuxt`.  
EXCEPTION: Decorative SVG/CSS backgrounds. DO/DON'T: crawlable content image / CSS background only for entity hero.

### R11.9 Internal linking [BASELINE+] [depth: 3-source]
Source: GSC links, NNG information scent, BASE travel patterns.  
WHAT: Detail pages link to related area/category/nearby/similar pages with descriptive anchor text.  
WHY: Internal links help crawling and user exploration.  
RECONCILE: SEO and travel discovery both benefit from related paths.  
CONTEXT: "Gan Cu lao An Binh" links to nearby entities; avoid generic "xem them" alone.  
VERIFY: `rg -n "related|nearby|similar|NuxtLink" web-nuxt/pages web-nuxt/components`.  
EXCEPTION: Admin pages noindex. DO/DON'T: `Xem dia diem gan Cu lao An Binh` / link text "click here".

### R11.10 GEO answer blocks [NEW] [depth: 2-source]
Source: GSC helpful content, BASE GEO notes.  
WHAT: Guides/entities include concise factual answer blocks for "o dau, co gi, di khi nao, lien he the nao".  
WHY: Generative engines cite clear, structured, factual passages.  
RECONCILE: Human scannability and AI extractability align.  
CONTEXT: Use local facts, season, address, coordinates, verified contact.  
VERIFY: content checklist; `rg -n "FAQ|Hoi dap|Cau hoi|accordion" web-nuxt`.  
EXCEPTION: Thin entities without verified data should not invent answers. DO/DON'T: factual FAQ / keyword-stuffed paragraph.

### R11.11 No fake urgency SEO [NEW] [depth: research-backed]
Source: GSC spam policies, Cialdini ethics, NNG trust.  
WHAT: Do not add fake countdowns, fake availability, or "dang co X nguoi xem" for SEO/CTR.  
WHY: Dark patterns destroy trust and may violate spam/user-first policies.  
RECONCILE: Scarcity can be seasonal truth only.  
CONTEXT: Say "Mua dep: thang 3-5" if true, not "Sap het cho".  
VERIFY: `rg -n "countdown|sap het|dang xem|urgency|limited" web-nuxt content app`.  
EXCEPTION: Real event date deadline with source. DO/DON'T: real festival dates / fake countdown.

### R11.12 Canonical/noindex hygiene [PROJECT DECISION 2026-07-07] [depth: 2-source]
Source: GSC canonical/noindex, BASE; overridden by shipped indexing strategy.  
WHAT: Indexability is NOT "index every public page" — it goes through the P0-1 quality gate `is_index_worthy()` (`agent/seo.py`): only entities passing it get index + sitemap, thin pages stay noindex. On top of that, site-wide noindex is currently ON deliberately (`NUXT_PUBLIC_SITE_NOINDEX` defaults to true in `nuxt.config.ts`; `server/middleware/noindex.ts` emits X-Robots-Tag) while content matures — ONLY the project owner flips it off. Canonicalize filtered lists; noindex admin/search states.  
WHY: Mass-indexing thin, unverified content is exactly the Google-spam risk the positioning avoids.  
RECONCILE: Search UX state can exist without all combinations indexed.  
CONTEXT: `/tim-kiem?q=...` may be noindex; category pages become indexable once the site-wide flag is opened and they pass the gate.  
VERIFY: `rg -n "canonical|noindex|robots|siteNoindex" web-nuxt`.  
EXCEPTION: Curated static search landing can index (once site-wide noindex is lifted). DO/DON'T: keep the deliberate noindex + per-page gate / "fix" the site-wide noindex flag or middleware in a compliance pass.

#### R11 GEO Guide

Each entity detail should include: one-sentence summary, verified location, best season, how to get there, contact method if verified, related places, FAQ with 3-5 factual answers, JSON-LD matching visible content.

#### R11 Decision Tree

Entity with verified location -> Place/TouristAttraction; business/contact -> LocalBusiness; post/guide -> Article; list -> ItemList; every non-home -> BreadcrumbList; unverified data -> omit.

#### R11 Anti-patterns

- R11-AP1: Schema with invisible/fake fields. Consequence: policy/trust risk. Root: SEO shortcut. Fix: visible verified data only.
- R11-AP2: Generic link text. Consequence: weak information scent. Root: template copy. Fix: descriptive anchors.
- R11-AP3: Keyword-stuffed Vietnamese. Consequence: poor readability. Root: old SEO habit. Fix: concise factual copy.

#### R11 Checklist

Run schema grep, Rich Results Test for templates, verify one H1/title/description, check canonical/noindex, review GEO answer blocks.

## R12 Performance

### R12.1 Core Web Vitals targets [BASELINE+] [depth: consensus]
Source: WEBDEV, GSC page experience, BASE.  
WHAT: Public pages target LCP <2.5s, CLS <0.1, INP <200ms; internal stretch targets below table.  
WHY: CWV captures perceived loading, stability, and responsiveness.  
RECONCILE: Google thresholds are floor; vinhlong360 budgets are stricter for mobile.  
CONTEXT: Travel users on unstable networks need fast first content.  
VERIFY: Lighthouse/PageSpeed/Chrome DevTools mobile.  
EXCEPTION: Admin pages can target LCP <3s, INP <200ms. DO/DON'T: budgets per page / "fast enough" without measurement.

### R12.2 Performance budgets [NEW] [depth: 3-source]
Source: WEBDEV, BASE, DR network context.  
WHAT: Enforce page budgets: homepage JS <150KB gz, CSS <30KB gz, images <500KB; list JS <100KB gz; detail image budget <800KB.  
WHY: Budgets prevent slow drift in a one-person codebase.  
RECONCILE: web.dev budget discipline plus project-specific page types.  
CONTEXT: Mobile-first Vietnam travel browsing should not ship desktop-heavy bundles.  
VERIFY: `npm run build` + bundle analyzer if available; Lighthouse transfer size.  
EXCEPTION: Admin pages JS <200KB gz acceptable. DO/DON'T: lazy route chunks / global import of heavy admin code.

### R12.3 SSR content baseline [BASELINE+] [depth: 3-source]
Source: WEBDEV progressive enhancement, Nuxt SSR BASE, WCAG.  
WHAT: Core page content renders SSR; JS enhances save/filter/map, not basic reading/contact.  
WHY: Hydration failure or slow JS should not blank travel info.  
RECONCILE: SSR and progressive enhancement are web-first solution.  
CONTEXT: Name, summary, address, phone, Zalo link must be in HTML.  
VERIFY: disable JS in browser; `rg -n "ClientOnly|v-if=\"mounted|process.client" web-nuxt`.  
EXCEPTION: Map canvas/gallery lightbox. DO/DON'T: SSR entity facts / client-only detail page.

### R12.4 Resource hints [BASELINE+] [depth: 2-source]
Source: WEBDEV resource hints, BASE.  
WHAT: Preconnect only critical origins; preload LCP image/font; prefetch likely next routes sparingly.  
WHY: Resource hints can improve LCP but overuse competes for bandwidth.  
RECONCILE: Hints need evidence from waterfall.  
CONTEXT: CDN/image origins may need preconnect; random third parties should not.  
VERIFY: `rg -n "preconnect|dns-prefetch|preload|prefetch|modulepreload" web-nuxt`.  
EXCEPTION: Nuxt modulepreload generated by framework. DO/DON'T: preload LCP image / prefetch every route.

### R12.5 JavaScript discipline [BASELINE+] [depth: 3-source]
Source: WEBDEV INP, BASE, M3 motion.  
WHAT: Defer noncritical JS, lazy-load below-fold widgets/admin modules, avoid long tasks >50ms.  
WHY: Long tasks degrade INP and make taps feel ignored.  
RECONCILE: Rich UI should not block input.  
CONTEXT: Search/filter/map pages need responsive typing and tapping.  
VERIFY: DevTools Performance long tasks; `rg -n "import .* from|defineAsyncComponent|lazy" web-nuxt`.  
EXCEPTION: Small shared utilities. DO/DON'T: async admin-only component / global heavy chart import.

### R12.6 CSS specificity budget [NEW] [depth: 2-source]
Source: WEBDEV CSS, FIGMA design systems.  
WHAT: No IDs in selectors; nesting max 3 levels; specificity target <=0-3-0.  
WHY: High specificity causes override wars and larger dark-mode patches.  
RECONCILE: Design tokens need predictable cascade.  
CONTEXT: Existing scoped CSS/dark overrides show specificity debt.  
VERIFY: `rg -n "#[A-Za-z][A-Za-z0-9_-]+\\s*\\{|(:deep|:global).*(:deep|:global)" web-nuxt`.  
EXCEPTION: `#mapContainer` for third-party map integration. DO/DON'T: `.card .title` / `#page .section .card .title`.

### R12.7 CSS layers [NEW] [depth: 2-source]
Source: WEBDEV CSS cascade layers, BASE.  
WHAT: Global CSS follows layer order reset -> base -> components -> utilities -> overrides.  
WHY: Layers make overrides intentional and reduce specificity escalation.  
RECONCILE: Figma design system tokens map to stable CSS architecture.  
CONTEXT: One-person team needs predictable cascade when adding components.  
VERIFY: `rg -n "@layer" web-nuxt/assets/css`.  
EXCEPTION: Legacy files can migrate gradually. DO/DON'T: `@layer components{.btn{...}}` / append random global rules.

### R12.8 Network-aware loading [NEW] [depth: 3-source]
Source: WEBDEV, DR, BASE.  
WHAT: If `effectiveType` is `2g/slow-2g` or Save-Data, load thumbnails, skip autoplay/reveals, reduce gallery.  
WHY: User/network context should shape payload.  
RECONCILE: Progressive enhancement adapts enhancement level.  
CONTEXT: Rural travel routes can have unstable signal.  
VERIFY: `rg -n "navigator.connection|effectiveType|saveData|Save-Data" web-nuxt server`.  
EXCEPTION: Critical text/facts always load. DO/DON'T: low-data mode / same heavy gallery for everyone.

### R12.9 Offline useful pages [NEW] [depth: 2-source]
Source: WEBDEV PWA/offline, NNG travel task context.  
WHAT: Cache last-viewed homepage, entity detail shell, and saved itinerary data where feasible; never cache stale contact as authoritative without timestamp.  
WHY: Travel users lose network while moving.  
RECONCILE: Offline support is progressive enhancement, not full app.  
CONTEXT: Viewed place detail should remain readable with "cap nhat luc..." note.  
VERIFY: DevTools offline; `rg -n "serviceWorker|workbox|caches|offline" web-nuxt`.  
EXCEPTION: Admin and auth-sensitive pages should not be offline cached. DO/DON'T: read-only offline detail / offline booking/payment.

### R12.10 Observed loading states [BASELINE+] [depth: research-backed]
Source: Doherty Threshold, WEBDEV, M3 loading.  
WHAT: Show feedback within 100ms, useful skeleton under 400ms, retry/error after timeout with clear action.  
WHY: Responses under 400ms feel fluid; silence causes repeated taps.  
RECONCILE: M3 loading indicators operationalize response-time research.  
CONTEXT: Slow API for search/reviews needs immediate local state.  
VERIFY: slow 3G simulation + throttled API; `rg -n "timeout|retry|skeleton|aria-busy" web-nuxt server`.  
EXCEPTION: Instant local toggles can update optimistically. DO/DON'T: skeleton+retry / inert blank area.

#### R12 Performance Budgets

| Page type | JS gz | CSS gz | Image total | LCP | CLS | INP |
|---|---:|---:|---:|---:|---:|---:|
| Homepage | <150KB | <30KB | <500KB | <2.0s | <0.05 | <150ms |
| Entity detail | <120KB | <25KB | <800KB | <2.5s | <0.05 | <150ms |
| Catalog/list | <100KB | <20KB | <400KB | <2.0s | <0.1 | <100ms |
| Community | <130KB | <25KB | <300KB | <2.5s | <0.1 | <150ms |
| Admin | <200KB | <35KB | N/A | <3.0s | <0.1 | <200ms |

#### R12 Resource Hint Template

```html
<link rel="preconnect" href="https://image-cdn.example" crossorigin>
<link rel="preload" as="image" href="/hero.avif" imagesrcset="/hero-640.avif 640w, /hero-1280.avif 1280w" imagesizes="100vw">
<link rel="preload" as="font" href="/fonts/app.woff2" type="font/woff2" crossorigin>
```

#### R12 Decision Tree

If content is above fold -> SSR and priority; if below fold -> lazy/content-visibility; if Save-Data -> low bytes; if admin-only -> lazy route; if API slow -> skeleton/retry.

#### R12 Anti-patterns

- R12-AP1: Lazy LCP image. Consequence: slow first impression. Root: blanket lazy rule. Fix: priority LCP.
- R12-AP2: Client-only entity page. Consequence: blank on slow JS. Root: SPA habit. Fix: SSR facts.
- R12-AP3: No performance budget. Consequence: slow drift. Root: feature creep. Fix: page-type budgets.

#### R12 Checklist

Run Lighthouse mobile, inspect DevTools waterfall, test Slow 3G + Save-Data, run hardcoded CSS/perf grep, verify SSR with JS disabled.

## R13 Responsive

### R13.1 Breakpoint classes [BASELINE+] [depth: consensus]
Source: M3-LAYOUT, BASE, SC device context.  
WHAT: Use compact 0-599, medium 600-839, expanded 840-1199, large 1200-1599, xlarge 1600+.  
WHY: Window-size classes reduce device-specific hacks.  
RECONCILE: M3 classes map to repo tokens and existing 600/768/1024/1280/1440 habits.  
CONTEXT: Must pass 360, 390, 414, 768, 1024, 1280 viewport widths.  
VERIFY: screenshot matrix; `rg -n "@media" web-nuxt --glob "*.vue" --glob "*.css"`.  
EXCEPTION: Component-specific overflow fixes allowed after screenshot evidence. DO/DON'T: class-based breakpoints / iPhone-model-only CSS.

### R13.2 Layout grids [BASELINE+] [depth: 2-source]
Source: M3-LAYOUT, A-LAYOUT.  
WHAT: Compact 4 columns/16px margins; medium 8 columns/24px; expanded 12 columns/24px.  
WHY: Responsive grids keep content aligned across devices.  
RECONCILE: Apple margins and M3 grid both scale with window.  
CONTEXT: Travel cards move 1 -> 2 -> 3/4 columns without awkward widths.  
VERIFY: manual grid screenshots; `rg -n "grid-template-columns|repeat\\(" web-nuxt`.  
EXCEPTION: Photo gallery custom 3fr/2fr layout. DO/DON'T: responsive repeat / fixed 4 columns mobile.

### R13.3 No horizontal overflow [BASELINE+] [depth: consensus]
Source: WCAG Reflow, WEBDEV CLS, BASE.  
WHAT: Public pages have no horizontal scroll at 320-430px except intentional chip/gallery scroll.  
WHY: Horizontal page overflow breaks reading and zoom.  
RECONCILE: WCAG allows component scroll only when necessary.  
CONTEXT: 360px Android is a must-pass viewport.  
VERIFY: Playwright screenshot + `document.documentElement.scrollWidth <= innerWidth`; manual.  
EXCEPTION: Horizontal filter chips with visible affordance. DO/DON'T: responsive wrap / page-wide 1100px panel.

### R13.4 Component adaptation [BASELINE+] [depth: 2-source]
Source: M3 adaptive, A-HIG modality.  
WHAT: Dialog on desktop can become bottom sheet on mobile; sidebar becomes bottom bar; table becomes cards.  
WHY: Components need fit and reach per viewport.  
RECONCILE: Platform patterns differ by size class, not brand.  
CONTEXT: Contact widget: sticky sidebar desktop, fixed bottom mobile.  
VERIFY: responsive screenshots; `rg -n "ContactWidget|sidebar|bottom" web-nuxt`.  
EXCEPTION: Admin desktop-only tools can show unsupported-mobile notice. DO/DON'T: adaptive component / desktop modal squeezed to 320px.

### R13.5 Content order [BASELINE+] [depth: research-backed]
Source: NNG F-pattern/Z-pattern, BASE travel.  
WHAT: Mobile order: title, key facts, contact, description, map, reviews, related; desktop can place contact aside.  
WHY: Users need decision facts before deep reading.  
RECONCILE: Z-pattern marketing is secondary to F-pattern information scanning on detail pages.  
CONTEXT: Phone/map must appear early for travelers on the go.  
VERIFY: mobile screenshot/manual DOM order.  
EXCEPTION: Editorial story pages can lead with narrative image/text. DO/DON'T: facts before long story / map buried after reviews.

### R13.6 Safe tap zones [BASELINE+] [depth: consensus]
Source: A-LAYOUT safe areas, WCAG Target Size.  
WHAT: Edge controls have 16px page gutter and safe-area padding; avoid tiny edge-only gestures.  
WHY: Notches, cases, and thumb reach make edges error-prone.  
RECONCILE: Apple safe areas plus WCAG target size.  
CONTEXT: Floating map/list and contact buttons must not hug screen edge.  
VERIFY: 360/414 screenshots; `rg -n "right:\s*0|left:\s*0|bottom:\s*0|safe-area" web-nuxt`.  
EXCEPTION: Full-bleed image content, not controls. DO/DON'T: `right:var(--space-4)` / `right:0` icon button.

### R13.7 Container queries optional [NEW] [depth: 2-source]
Source: WEBDEV responsive, FIGMA component systems.  
WHAT: Prefer component container behavior when component appears in variable widths; otherwise use page breakpoints.  
WHY: Component reuse in sidebars/grids breaks viewport-only assumptions.  
RECONCILE: Modern CSS container queries are progressive but should not require new dependencies.  
CONTEXT: EntityCard may render in carousel, grid, sidebar.  
VERIFY: `rg -n "@container|container-type" web-nuxt`.  
EXCEPTION: Legacy browsers fall back to viewport layout. DO/DON'T: `container-type:inline-size` for cards / hardcode `.card{width:33vw}`.

#### R13 Breakpoint Decision Table

| Width | Layout | Navigation | Content |
|---|---|---|---|
| 0-599 | 1 column, 16px gutter | Bottom bar | Bottom sheet, list-first |
| 600-839 | 2 columns where safe, 24px gutter | Rail/top hybrid | Split small panels |
| 840-1199 | 12-col grid | Top/drawer | Map/list possible |
| 1200-1599 | Constrained max width | Top/drawer | Sidebar contact |
| 1600+ | Wider whitespace, no over-stretched text | Top/drawer | Max readable widths |

#### R13 Decision Tree

If content overflows -> reduce columns or wrap; if controls at edge -> add gutter/safe area; if component reused in narrow container -> container query; if page is admin -> desktop density allowed.

#### R13 Anti-patterns

- R13-AP1: Device-model media query. Consequence: misses other phones. Root: testing one device. Fix: window-size classes.
- R13-AP2: Horizontal page overflow. Consequence: reflow failure. Root: fixed widths. Fix: minmax/grid/wrap.
- R13-AP3: Desktop modal on mobile. Consequence: unreachable actions. Root: one-size component. Fix: bottom sheet.

#### R13 Checklist

Screenshot 360/390/414/768/1024/1280, check scrollWidth, test bottom bars with safe area, verify content order.

## R14 States

### R14.1 State layer tokens [BASELINE+] [depth: consensus]
Source: M3-STATE, TOKENS.  
WHAT: Hover/focus/pressed/dragged use `--state-hover/focus/pressed/dragged` or opacity tokens.  
WHY: Consistent state feedback makes components learnable.  
RECONCILE: M3 state layer opacities are already in variables.css.  
CONTEXT: Chips, buttons, cards, admin rows should respond consistently.  
VERIFY: `rg -n "--state-|:hover|:active|:focus-visible" web-nuxt`.  
EXCEPTION: Native controls may use platform states. DO/DON'T: `background:var(--state-hover)` / random hover rgba.

### R14.2 Disabled state [BASELINE+] [depth: consensus]
Source: M3-STATE, WCAG, TOKENS.  
WHAT: Disabled uses foreground opacity 38%, container 12%, plus actual `disabled`/`aria-disabled`.  
WHY: Visual disabled state must match programmatic disabled state.  
RECONCILE: M3 opacities and WCAG semantics both required.  
CONTEXT: Submit buttons during pending should disable duplicate action.  
VERIFY: `rg -n "disabled|aria-disabled|opacity-disabled" web-nuxt`.  
EXCEPTION: Disabled-looking informational tag should not use disabled semantics. DO/DON'T: `<button disabled>` / `.disabled` only.

### R14.3 Selected state [BASELINE+] [depth: consensus]
Source: M3-STATE, WAI-APG.  
WHAT: Selected chips/tabs/nav set `aria-selected` or `aria-current` and visual selected layer.  
WHY: Users and assistive tech need current state.  
RECONCILE: M3 visual selected state and ARIA selected/current align.  
CONTEXT: Filters and bottom nav must be clear in light/dark.  
VERIFY: `rg -n "aria-selected|aria-current|aria-pressed|selected|active" web-nuxt`.  
EXCEPTION: Toggle button uses `aria-pressed`. DO/DON'T: selected attr + style / class only.

### R14.4 Error state [BASELINE+] [depth: consensus]
Source: M3 text fields, WCAG, A-HIG.  
WHAT: Error state has red/error outline, error text, icon if useful, `aria-invalid`, describedby.  
WHY: Red border alone is not accessible or actionable.  
RECONCILE: See R7; state matrix applies to all form fields.  
CONTEXT: Report/comment/auth forms must recover fast.  
VERIFY: `rg -n "aria-invalid|--error|error-text|role=\"alert\"" web-nuxt`.  
EXCEPTION: Page-level 404 uses error layout, not field state. DO/DON'T: full error pattern / border-only.

### R14.5 Loading state [BASELINE+] [depth: 3-source]
Source: M3 loading, WEBDEV, WCAG.  
WHAT: Loading reserves layout, marks busy container, and never shifts button/card dimensions.  
WHY: Layout stability and feedback reduce repeated actions.  
RECONCILE: Skeleton/progress/spinner choice in R4.  
CONTEXT: List cards and form submits need stable perceived flow.  
VERIFY: `rg -n "aria-busy|skeleton|spinner|loading" web-nuxt`.  
EXCEPTION: Tiny icon-only refresh can spin in place. DO/DON'T: skeleton same size / button shrinks to spinner.

### R14.6 Empty state [BASELINE+] [depth: 3-source]
Source: M3 empty states, A-HIG, NNG.  
WHAT: Empty is a real state with icon, title, description, CTA; not a blank/null response.  
WHY: Users need next action and confidence system is working.  
RECONCILE: Feedback patterns and content design align.  
CONTEXT: No search results should suggest broader query/category.  
VERIFY: `rg -n "empty|khong tim thay|chua co" web-nuxt`.  
EXCEPTION: Admin data table may show compact empty row plus action. DO/DON'T: helpful empty / blank list.

### R14.7 Optimistic state [NEW] [depth: 2-source]
Source: WEBDEV responsiveness, NNG feedback.  
WHAT: Use optimistic updates only for reversible low-risk actions; rollback with clear message on failure.  
WHY: Optimism improves speed but can break trust if irreversible.  
RECONCILE: Responsiveness and integrity must balance.  
CONTEXT: Save/bookmark can be optimistic; report submission/admin delete should wait or confirm.  
VERIFY: `rg -n "optimistic|rollback|catch\\(|try\\s*\\{" web-nuxt`.  
EXCEPTION: Server-authoritative security actions. DO/DON'T: optimistic save with undo / optimistic role change.

#### R14 State Layer CSS Mixin

```css
.stateful { position: relative; transition: background var(--dur-short3) var(--ease-standard); }
.stateful:hover { background: var(--state-hover); }
.stateful:focus-visible { box-shadow: var(--focus-ring); }
.stateful:active { background: var(--state-pressed); transform: scale(.98); }
.stateful:disabled { opacity: var(--opacity-disabled-content); pointer-events: none; }
```

#### R14 Decision Tree

If unavailable -> disabled; if active/current -> selected/current; if async -> loading/busy; if no data -> empty; if failed input -> error; if fast reversible -> optimistic.

#### R14 Anti-patterns

- R14-AP1: Hover-only feedback. Consequence: mobile no feedback. Root: desktop design. Fix: pressed/focus states.
- R14-AP2: Visual disabled without `disabled`. Consequence: keyboard can activate. Root: CSS-only state. Fix: semantic disabled.
- R14-AP3: Blank loading gap. Consequence: perceived broken. Root: missing loading state. Fix: skeleton/busy.

#### R14 Checklist

For each component verify enabled, hover, focus, pressed, disabled, selected, loading, error, empty in light/dark.

## R15 Content

### R15.1 Vietnamese tone [BASELINE+] [depth: 3-source]
Source: A-HIG Writing, M3 content, BASE.  
WHAT: Tone is friendly, direct, useful; use "ban"; avoid "quy khach" unless legal/formal.  
WHY: Clear copy lowers cognitive load and feels inclusive.  
RECONCILE: Apple directness and M3 clarity align with Vietnamese plain language.  
CONTEXT: vinhlong360 is local guide, not luxury hotel concierge.  
VERIFY: content grep `rg -n "quy khach|anh/chị|mày|tao|booking|checkout" web-nuxt content docs`.  
EXCEPTION: Legal documents may use formal language. DO/DON'T: "Ban co the goi dien..." / "Quy khach vui long...".

### R15.2 Heading vs body language [AMENDED 2026-07-07] [depth: 2-source]
Source: BASE Vietnamese SEO, GSC; amended for anti-AI editorial voice.  
WHAT: Headings may use Han-Viet SEO terms; body explains in plain Vietnamese with VARIED sentence rhythm — short sentences interleaved with longer 20-35-word ones. No mechanical word-count cap for prose/story content: uniformly short sentences read machine-generated, the exact tell the editorial voice fights. A ~15-word ceiling applies to UI microcopy (labels, tooltips, empty states) only.  
WHY: Balances search intent, readability, and a human editorial cadence (see `viet-content-optimizer` skill: alternate short and long sentences, never uniform length).  
RECONCILE: SEO vocabulary and cognitive accessibility both matter; so does not sounding like AI slop.  
CONTEXT: Heading "Am thuc Vinh Long"; body can say "Nhung mon ngon nen thu" and follow with a longer sensory sentence.  
VERIFY: manual content review; flag monotonous sentence length, not a hard cap.  
EXCEPTION: Proper names remain exact. DO/DON'T: SEO heading + plain body with mixed-length sentences / jargon everywhere or every sentence the same clipped length.

### R15.3 Button labels [BASELINE+] [depth: 3-source]
Source: A-HIG Writing, M3 content, NNG.  
WHAT: Buttons use verb+noun: "Xem ban do", "Goi dien", "Nhan Zalo", "Luu dia diem".  
WHY: Action labels reduce ambiguity.  
RECONCILE: All UX writing sources favor specific action language.  
CONTEXT: Do not use booking/payment verbs.  
VERIFY: `rg -n ">\\s*(Xem|Goi|Nhan|Luu|Dat|Thanh toan|Checkout)" web-nuxt`.  
EXCEPTION: Tiny icon button needs aria-label with verb+noun. DO/DON'T: "Chi duong" / "OK".

### R15.4 Ethical social proof [NEW] [depth: research-backed]
Source: Cialdini, NNG trust, GSC policies.  
WHAT: Show real counts/reviews/sources only; never fake viewers, countdowns, or scarcity.  
WHY: Social proof works by trust; fake proof is a dark pattern.  
RECONCILE: Persuasion principles must be bounded by integrity.  
CONTEXT: Use "23 danh gia" if real; use "Mua dep: thang 3-5" if seasonal fact.  
VERIFY: `rg -n "dang xem|countdown|sap het|limited|fake|viewer" web-nuxt content app`.  
EXCEPTION: None. DO/DON'T: real review count / fake "12 nguoi dang xem".

### R15.5 Authority and provenance [NEW] [depth: research-backed]
Source: Cialdini authority, NNG credibility, BASE data quality.  
WHAT: Important facts show source/provenance when available: official, community, admin-reviewed, last updated.  
WHY: Authority cues improve trust when accurate.  
RECONCILE: Authority bias must not become fake official endorsement.  
CONTEXT: "Nguon: So Du lich" only if actually sourced; otherwise "Cong dong dong gop".  
VERIFY: `rg -n "source|provenance|lastUpdated|cap nhat|nguon" web-nuxt server app`.  
EXCEPTION: Decorative category copy. DO/DON'T: verified source label / fake official badge.

### R15.6 Inclusive language [NEW] [depth: 2-source]
Source: W3C COGA, BASE Vietnamese plain language.  
WHAT: Avoid gender/age/region stereotypes; use specific place names, not "nha que/mien que" as value judgment.  
WHY: Inclusive wording prevents alienation and bias.  
RECONCILE: Local pride and respectful language align.  
CONTEXT: Say "vung nong thon", "lang nghe", or actual commune name.  
VERIFY: `rg -n "nha que|mien que|dan ba|phu nu nen|nguoi gia thi" content web-nuxt app`.  
EXCEPTION: Direct historical quote with context. DO/DON'T: "lang nghe Mang Thit" / "net nha que".

### R15.7 Permission microcopy [NEW] [depth: 3-source]
Source: A-HIG permissions, NNG trust, M3 content.  
WHAT: Ask permission after explaining value and providing fallback.  
WHY: Consent is more likely and more ethical when users know why.  
RECONCILE: Platform permission guidance and trust psychology align.  
CONTEXT: "Dung vi tri de goi y diem gan ban. Ban van co the tim bang ten dia diem."  
VERIFY: `rg -n "permission|geolocation|vi tri|Cho phep" web-nuxt`.  
EXCEPTION: None for sensitive permissions. DO/DON'T: value first / prompt on load.

### R15.8 Content truncation and reveal [BASELINE+] [depth: research-backed]
Source: NNG progressive disclosure, BASE, M3.  
WHAT: Cards truncate predictably; detail pages use "Xem them" only after meaningful first 3 lines.  
WHY: Users need scanable summaries and control over detail.  
RECONCILE: Progressive disclosure reduces load without hiding essentials.  
CONTEXT: Vietnamese entity descriptions open with the most important sentence.  
VERIFY: `rg -n "line-clamp|Xem them|Thu gon|read more" web-nuxt`.  
EXCEPTION: Legal text should not be hidden behind casual reveal. DO/DON'T: summary first + reveal / teaser with no facts.

#### R15 UI String Library

| Context | Strings |
|---|---|
| Navigation | Trang chu, Kham pha, Cong dong, Lich trinh, Tai khoan, Tim kiem |
| Actions | Xem them, Thu gon, Chia se, Luu dia diem, Goi dien, Nhan Zalo, Chi duong, Xem ban do |
| Feedback | Dang tai..., Khong tim thay ket qua, Da luu thanh cong, Co loi xay ra, Thu lai |
| Empty | Chua co danh gia nao. Hay chia se trai nghiem cua ban. |
| Permission | Cho phep vi tri de tim diem gan ban. Ban van co the tim bang ten dia diem. |
| Time | vua xong, X phut truoc, hom qua, X ngay truoc |
| Numbers | 1,2K luot xem in UI; `4.5` in schema/rating data |
| Errors | So dien thoai chua dung. Nhap 10 chu so bat dau bang 0. |

#### R15 Microcopy Patterns

| Goal | Preferred | Avoid |
|---|---|---|
| Contact | Goi dien, Nhan Zalo | Dat ngay, Thanh toan |
| Invite review | Chia se trai nghiem cua ban | Viet danh gia ngay! |
| Low pressure CTA | Luu dia diem | Ban se tiec neu bo qua |
| Permission | Explain value first | Browser prompt on load |
| Scarcity | Mua dep: thang 3-5 | Chi con 2 cho |

#### R15 Decision Tree

If action -> verb+noun; if error -> what/why/fix; if trust claim -> source; if social proof -> real count; if body text -> plain Vietnamese; if legal -> formal but clear.

#### R15 Anti-patterns

- R15-AP1: Booking/payment wording. Consequence: false expectation. Root: copied travel templates. Fix: contact/introduction wording.
- R15-AP2: Confirmshaming. Consequence: dark pattern. Root: growth-hacking copy. Fix: neutral choices.
- R15-AP3: Formal gendered pronouns. Consequence: less inclusive. Root: old service copy. Fix: "ban".

#### R15 Checklist

Search forbidden strings, verify button labels, review source badges, check sentence length, confirm no fake urgency/social proof.

## Appendix A Token Audit

### A1 Repo Measurements

Commands run on 2026-06-29:

```bash
rg -P -n "(?<!&)#[0-9A-Fa-f]{3,8}\b" web-nuxt --glob "*.vue" --glob "*.css" --glob "!web-nuxt/assets/css/variables.css"
rg -P -n "rgba?\((?!var\()" web-nuxt --glob "*.vue" --glob "*.css" --glob "!web-nuxt/assets/css/variables.css"
rg -n "\b(margin|padding|gap|height|width|min-height|min-width|max-width|border-radius|top|left|right|bottom):\s*[0-9]+px" web-nuxt --glob "*.vue" --glob "*.css" --glob "!web-nuxt/assets/css/variables.css"
```

| Metric | Result |
|---|---:|
| Tokens in `variables.css` | 369 |
| Tokens unused outside `variables.css` | 166 |
| Raw hex hits outside `variables.css` | 598 |
| Raw `rgb/rgba` function hits outside `variables.css` | 662 |
| Hardcoded layout px hits outside `variables.css` | 1309 |
| Dark override file exists | yes, `web-nuxt/assets/css/dark-overrides.css` |

### A2 Token Cross-reference

| Current token/group | Value/example | Apple HIG equiv | M3 equiv | Action |
|---|---|---|---|---|
| `--clay-*` | 50/100/400/600/700/900 | brand tint/accent | primary palette | OK; add 200/300/500/800 only if needed |
| `--amber-*` | 100/500/600/700 | system yellow/orange | tertiary/extended | OK; keep warning separate |
| `--leaf-*` | 100/600/700 | system green | secondary | OK; add container use examples |
| `--river-*` | 100/600 | system teal/blue | tertiary | FIX; `--river-rgb` currently appears purple-ish in baseline audit, verify value |
| `--sand-*` | 50-400 | system background/secondary bg | surface containers | OK |
| `--ink-*` | 700/900 | label/secondary label | on-surface/on-surface-variant | ADD `--ink-500` or remove references if any |
| `--primary/on-primary` | clay/white | tint + label | primary/on-primary | OK |
| `--accent/on-accent` | amber/ink | system orange/yellow | tertiary/on-tertiary-like | OK; document not warning |
| `--*-container` | color-mix | dynamic bg | container roles | FIX adoption; many container tokens unused |
| `--surface-container-*` | sand ramp | background hierarchy | surface container roles | OK; require component adoption |
| `--outline*` | line/input | separator | outline/outline-variant | OK |
| `--inverse-*` | inverse surface | inverse bg | inverse surface/primary | ADD usage examples |
| `--state-*` | 8/12/10/16% | focus/pressed states | state layers | OK; note focus opacity should be 10-12%, repo has 12% |
| `--touch-min` | 44px | 44pt | 48dp preferred | OK |
| `--text-*` | clamp scale | Dynamic Type styles | type scale roles | OK; stop raw font-size |
| `--lh-*` | 16-72px | line metrics | type line-height | OK; many unused, adopt |
| `--ls-*` | role tracking | optical tracking | M3 tracking | FIX; do not apply negative tracking to Vietnamese body |
| `--space-*` | 0-96px | 8pt + 4pt subgrid | spacing scale | OK |
| `--radius-*` | 4/10/14/20/28/full | rounded rects | shape scale | FIX; public cards should avoid over-rounded nested cards |
| `--dur-*` | 50-1000ms | spring/duration | duration scale | OK but unused; adopt |
| `--ease-*` | standard/emphasized | smooth/snappy | easing tokens | OK but unused; adopt |
| `--shadow-*` | xs-xl | elevation/material | elevation shadows | OK; prefer token |
| `--surface-1..5` | dark tonal | elevated bg | tonal elevation | OK |
| `--chip-*` | height/radius/gap | segmented/filter controls | filter chips | OK |
| `--gallery-*` | ratios/gap | image views | image lists | OK |
| `--contact-*` | 320px/48px | CTA area | adaptive component | OK |
| `--season-*` | accent/tint/gradient | extended tint | extended color | OK; scoped only |
| Missing `--link` | none | link color | primary/action link | ADD semantic link and `--link-hover` |
| Missing `--header-h` | fallback only | nav bar height | top app bar | ADD stable token |
| Missing `--grid-*` | none | layout margins | layout grid | ADD `--grid-margin-compact`, `--grid-gutter` |
| Missing `--page-js-budget` | none | n/a | n/a | ADD docs/config budget, not CSS |

### A3 Naming Audit

Current naming already follows 3 tiers: primitive (`--clay-600`), semantic (`--primary`), component (`--chip-height`). Keep this. New tokens must not skip directly from primitive to component unless component is brand-specific.

### A4 M3 Color Role Coverage

Mapped: primary, on-primary, secondary, on-secondary, tertiary, on-tertiary, error, on-error, surface containers, outline, inverse, scrim, containers. Missing/weak: `--link`, full fixed/accent roles (`primary-fixed`, `on-primary-fixed`), source color docs, complete tonal ramps 0-100. Action: do not add all M3 roles blindly; add only semantic roles used by components.

### A5 Dark Mode Coverage

Core semantic tokens have `.dark` overrides. Risk remains in component-scoped raw colors and `dark-overrides.css`. New code should use semantic tokens first; only patch dark overrides for legacy scoped leakage.

## Appendix B Component State Matrix

| Component | Enabled | Disabled | Hover | Focus | Pressed | Error | Loading | Empty | Selected |
|---|---|---|---|---|---|---|---|---|---|
| Button | `--primary/on-primary` or outline | opacity 38%, disabled attr | `--state-hover` | `--focus-ring` | scale .98 + pressed | n/a | spinner, same width | n/a | `aria-pressed` for toggle |
| IconButton | 44px, token color | 38%, disabled | state layer | ring | scale .98 | n/a | spinner icon | n/a | pressed/selected icon |
| Chip | 36px, border | 38%, aria-disabled | state layer | ring | pressed layer | n/a | n/a | n/a | active bg/text + aria |
| TextField | label, 44px | disabled attr | border stronger | ring + border | n/a | error border/text/icon | n/a | n/a | n/a |
| Card | surface + border | n/a | lift/token shadow | focus ring if link | slight scale | n/a | skeleton same size | empty placeholder | selected border/layer |
| Dialog | labelled modal | n/a | n/a | trapped focus | n/a | inline errors | busy region | n/a | n/a |
| BottomSheet | sheet surface | n/a | handle affordance | trapped focus | close press | inline errors | busy | n/a | n/a |
| Toast | status role | n/a | pause dismiss if hover | close focus | close press | alert role if urgent | n/a | n/a | n/a |
| NavItem | link | n/a | state layer | ring | pressed | n/a | n/a | n/a | aria-current + indicator |
| Tab | tab role | aria-disabled | state layer | arrow key focus | select | n/a | n/a | n/a | aria-selected |
| Accordion | button | disabled | state layer | ring | pressed | n/a | n/a | n/a | aria-expanded |
| Gallery | images/buttons | disabled nav at ends | button hover | ring | pressed | n/a | image skeleton | placeholder | current dot |
| MapToggle | button | disabled if no map | state layer | ring | pressed | n/a | map skeleton | address fallback | aria-pressed |
| ReviewWidget | rating/count | n/a | sort hover | ring | press | invalid review form | skeleton | invite CTA | selected sort |

## Appendix C Sources And References

### Primary Sources Reviewed

| Source | Sections used |
|---|---|
| Apple HIG | Accessibility, Color, Dark Mode, Layout, Motion, Typography, Buttons, Search fields, Menus, Modality, Navigation |
| Material Design 3 | Color roles, Typography, Motion, Layout/adaptive, State layers, Buttons, Cards, Chips, Dialogs, Navigation, Text fields |
| Google Search Central | Structured data intro, Breadcrumb, LocalBusiness, Article, Review snippet, image SEO, canonical/noindex guidance |
| Figma Help/Best practices | Variables, styles, components, component properties, design-system organization |

### Additional Sources

| Source | Why relevant |
|---|---|
| WCAG 2.2 / WAI | Target size, contrast, focus, reflow, status, forms, APG widget behavior |
| web.dev | Core Web Vitals, image optimization, resource hints, INP/LCP/CLS, CSS containment |
| Nielsen Norman Group | Fitts, Hick, Jakob, F-pattern, aesthetic-usability, forms, trust and usability |
| Baymard Institute | Mobile UX, form/filter/list mistakes adaptable from ecommerce/travel |
| Laws of UX | Fast lookup for cognitive principles used in rules |
| DataReportal Vietnam | Mobile/internet context for Vietnam |
| StatCounter Vietnam | Screen width/browser/OS context |
| GSMArena | Device class and screen size cross-check |
| Cialdini persuasion principles | Ethical social proof/authority/scarcity boundaries |
| W3C COGA | Cognitive accessibility objectives |
| Schema.org | Type vocabulary for Place/LocalBusiness/TouristAttraction |

Estimated source count used: baseline 4 repo docs plus 30+ external documentation/research pages or sections.

## Appendix D Cognitive Science Quick Reference

| Principle | Rule numbers | Application |
|---|---|---|
| Fitts's Law | R1.6, R5.1, R10.4 | 44px targets, spacing, CTA reach |
| Hick's Law | R6.4, R10.10 | Limit nav/actions/options |
| Miller's Law | R6.4, R15.8 | Chunk menus/content |
| Jakob's Law | R5.3, R6.3, R3.11 | Use familiar travel/contact patterns |
| Aesthetic-Usability Effect | R3.13, R4.1 | Polished but restrained UI |
| Von Restorff Effect | R3.3, R5.1 | Primary CTA stands out |
| Serial Position Effect | R6.5 | Nav ordering |
| Cognitive Load Theory | R10.10, R15.2 | Reduce extraneous content |
| F-pattern | R13.5, R15.8 | Detail/list information order |
| Z-pattern | R13.5 | Short promotional sections only |
| Doherty Threshold | R4.4, R12.10 | Feedback within 100-400ms |
| Peak-End Rule | R8.3, R15.4 | First image and final CTA/trust moments |
| Gestalt Proximity | R1.1, R1.2 | Grouping and spacing |
| Color Psychology | R3.4, R3.12 | Clay/amber/leaf/river meanings |
| Progressive Disclosure | R5.18, R15.8 | Accordions, reveal, filters |
| Social Proof | R5.10, R15.4 | Real ratings/counts |
| Authority Bias | R15.5 | Verified source labels |
| Mere Exposure | R3.13 | Consistent brand tokens |
| Endowment Effect | R14.7 | Saved itinerary/bookmark ownership |
| Paradox of Choice | R6.4 | Max nav/filter/card choice |
| Place Attachment | R8.1, R15.5 | Local stories and provenance |

## Appendix E Changelog Vs Baseline

| Tag | Count | Meaning |
|---|---:|---|
| `[BASELINE]` | 1 | Directly confirmed from existing repo research |
| `[BASELINE+]` | 131 | Existing baseline deepened with implementation, verification, or VN context |
| `[NEW]` | 33 | Added from token audit, cognitive/trust research, Vietnam context, progressive enhancement |
| `[UPDATED]` | 0 | No confirmed official-source change newer than 2026-06-27 was found in reviewed docs |
| Total rules | 165 | Minimum requested: 150 |

### Baseline Confirmed Still Correct

- 44px public touch target remains the vinhlong360 minimum.
- 4px/8pt spacing scale remains correct.
- M3 state layer opacity tokens in `variables.css` remain useful.
- Dark-mode semantic token approach remains correct.
- ContactWidget, not BookingWidget, remains the correct business pattern.

### Baseline Expanded

- Added explicit anti-patterns, decision trees, and checklists per section.
- Added token usage measurements and hardcode counts.
- Added Save-Data, offline, network-aware, and no-JS progressive-enhancement rules.
- Added ethical trust/social-proof boundaries and dark-pattern bans.
- Added ARIA pattern sheet, keyboard map, state matrix, page performance budgets, and UI string library.

### Quality Gate Self-check

| Gate | Result |
|---|---|
| QG1 6-layer rules | PASS: every rule has WHAT/WHY/RECONCILE/CONTEXT/VERIFY/EXCEPTION fields |
| QG2 actionable values | PASS: rules include concrete px/ms/ratios/tokens |
| QG3 code examples | PASS: every rule has DO/DON'T implementation text |
| QG4 cross-validation | PASS: each rule cites at least 2 source keys or BASE+external |
| QG5 Vietnamese context | PASS: every rule includes context line |
| QG6 verification | PASS: every rule includes grep/Lighthouse/manual verify |
| QG7 quantity | PASS: 165 rules, 45 anti-patterns, 25 micro-interactions, appendixes A-E |
| QG8 baseline | PASS: changelog and token audit included |
| QG9 conflict | PASS: no Tailwind/UI lib, no booking/payment, no stock image recommendation |
| QG10 readability | PASS target: compact rules; verify with line/count commands before commit |
