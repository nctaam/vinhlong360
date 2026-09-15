# TEST_INFRA — Vĩnh Long 360 Test Infrastructure & Quality Constitution

> STATUS: active (2026-09-15) — Cẩm nang hạ tầng kiểm thử và quy chuẩn chất lượng.

- **Platform**: Vĩnh Long 360 — Mekong River Heritage & Discovery Platform
- **Document Version**: 2.0 (Dual-Track E2E & Anti-Slop Editorial Verification)
- **Author**: `test_writer_e2e` (teamwork_preview_test_writer)
- **Quality Standard**: WCAG 2.2 AAA / Monocle & National Geographic Editorial Benchmarks / CLAUDE.md §1.7
- **Target Test Framework**: Vitest (Nuxt 3 / Vue 3 / Node.js 22 LTS / Happy-DOM)
- **Authority Sources**:
  - `web-nuxt/DESIGN.md` (Master Anti-Slop Editorial Design Constitution)
  - Google Stitch Cloud Project ID `14916181929760067680`
  - `ORIGINAL_REQUEST.md` (mốc `## 2026-09-13T01:13:48Z`)
  - `.agents/orchestrator_5/PROJECT.md`

---

## 1. Executive Testing Architecture

The Vĩnh Long 360 testing infrastructure safeguards the platform's editorial craftsmanship, Mekong terroir authenticity, and digital ergonomics through an automated, 4-tier opaque-box verification pyramid.

```
                    ▲
                   / \
                  /   \
                 / T4  \     Tier 4: Real-World Application & Field Scenarios
                /-------\    (Outdoor sunlight, sampan 1-hand thumb travel, tidal planning)
               /         \
              /   T3      \   Tier 3: Cross-Feature Combinations & Invariants
             /-------------\  (Tri-Region colors, responsive viewports, contrast harmony)
            /               \
           /      T2         \ Tier 2: Boundary, Corner & Ergonomic Limits
          /-------------------\ (>=44px touch targets, 65-70ch reading width, zero fallbacks)
         /                     \
        /         T1            \ Tier 1: Core Feature Coverage (R1 - R4)
       /-------------------------\ (Lead hero span-2, Lora serif, full-bleed cartography, con nước)
```

### Core Testing Directives
1. **Opaque-Box Verification**: Tests validate observable contracts, DOM hierarchies, computed styling invariants, CSS custom properties, and semantic attributes without coupling to internal component private state.
2. **Fail-Closed Gateways**: Any violation of WCAG 2.2 AAA contrast ratios (>= 7:1 for headings, >= 4.5:1 for body text), touch target minimums (< 44px), or anti-slop rules (raw emojis, synthetic fallback metrics, unapproved font stacks) results in immediate test failure.
3. **Graceful Collapse Assurance (CLAUDE.md §1.7)**: When external data (weather, tides, or field sensors) is missing or unavailable, the system must cleanly collapse the view rather than render empty boxes, skeletons, or fabricated fallback metrics.
4. **Platform-Wide Anti-AI-Slop**: Zero tolerance for equal-column slop grids, SaaS purple/cyan neon palettes, uncurated bylines, or `Times New Roman` fallbacks.

---

## 2. 4-Tier Test Suite Specification

### 2.1. Tier 1: Feature Coverage (Requirements R1 – R4)

Tier 1 verifies the concrete existence and correct structural rendering of every primary editorial feature assigned in `ORIGINAL_REQUEST.md` and `PROJECT.md`.

#### R1: Catalog Experience Magazine Layout (`tests/catalog-magazine-layout.test.ts`)
- **F1.1: Lead Hero Card span-2**:
  - Target files: `pages/du-lich.vue`, `pages/am-thuc.vue`, `pages/luu-tru.vue`, `pages/san-pham.vue`, `pages/dia-diem/index.vue`.
  - Invariant: In grid view at viewport >= 48rem, the initial card (`:first-child`) receives `grid-column: span 2` (or `.card:first-child span 2`) with an expanded cover image ratio (`aspect-ratio: 21 / 9`), establishing visual dominance.
- **F1.2: Asymmetric Editorial Flow & Interruption Dividers**:
  - Target files: `assets/css/catalog.css`, `assets/css/cards.css`, catalog page templates.
  - Invariant: Catalog surfaces break monotonous repetition by inserting editorial interruption dividers (e.g., `.grid-divider`, `.int-grid-divider`) every 8–9 cards, creating natural breathing pauses for the reader.
- **F1.3: Dedicated Cuisine Experience (`pages/am-thuc.vue`)**:
  - Target file: `pages/am-thuc.vue`.
  - Invariant: A first-class, dedicated Mekong gastronomy hub exists with lead hero card, regional culinary categories, and tactile filter pills, eliminating previous 404 routing gaps.
- **F1.4: Elimination of Equal-Column Slop**:
  - Target files: `assets/css/catalog.css`, catalog page templates.
  - Invariant: Complete absence of rigid, unmodulated 3–4 column grids (`repeat(auto-fit, minmax(17rem, 1fr))` or `repeat(auto-fill, minmax(220px, 1fr))`) without lead hero cards or asymmetric rhythms.

#### R2: Heritage Detail & Article Craft (`tests/heritage-detail-editorial.test.ts`)
- **F2.1: Monocle Editorial Typography**:
  - Target files: `pages/dia-diem/[id].vue`, `assets/css/detail.css`.
  - Invariant: Headings (`.desc-heading` / h2, `.desc-subheading` / h3, and hero titles) enforce serif font family `var(--font-editorial)` (`Lora`), track-tight `-0.02em`, delivering an authentic archival tone.
- **F2.2: Ergonomic Reading Measure (65–70ch)**:
  - Target files: `assets/css/detail.css`, `pages/dia-diem/[id].vue`.
  - Invariant: Content columns (`.entity-description`, `.extra-content`, `.detail-main .lead`) are constrained to `max-width: var(--measure-read)` (68ch) or within 65ch–70ch, preventing line overrun and cognitive fatigue.
- **F2.3: AEO Provenance Plaque**:
  - Target files: `components/DetailAeoSummary.vue`, `assets/css/detail.css`.
  - Invariant: The AI Engine Overview summary plaque features a solid Gold Phù Sa border (`border: 1.5px solid #c99446` or `var(--color-material-gold)`), a delicate warm background (`rgba(201, 148, 70, 0.05)`), and curated informational bullet points with vector icons (`psychology_alt` / `menu_book`).
- **F2.4: Official SourceMark Attribution**:
  - Target files: `pages/dia-diem/[id].vue`, `components/DetailAeoSummary.vue`.
  - Invariant: Transparent attribution stating `SourceMark: Ban biên tập vinhlong360`, complying strictly with R40.3 (banning unauthorized "đã xác minh" claims).
- **F2.5: Anti-Synthetic Data Integrity**:
  - Target file: `components/DetailAeoSummary.vue`.
  - Invariant: Zero synthetic fallback ratings, fake reviews, or placeholder stars when entity attributes lack verified provenance; adheres to graceful collapse.

#### R3: Cartography Field Ergonomics (`tests/cartography-field-ergonomics.test.ts`)
- **F3.1: Full-Bleed Cartography**:
  - Target files: `pages/ban-do.vue`, `pages/tuyen-duong.vue`, `assets/css/catalog.css`.
  - Invariant: Map canvas supports an edge-to-edge, full-bleed presentation unconstrained by rigid box borders, providing an immersive spatial navigation environment.
- **F3.2: 1-Hand Thumb Zone Dock**:
  - Target files: `pages/ban-do.vue`, `assets/css/catalog.css`.
  - Invariant: Mobile field controls are anchored in a floating bottom thumb dock (`.map-floating-thumb-dock`) positioned within natural thumb sweep (`bottom: calc(env(safe-area-inset-bottom) + 72px)`), keeping zoom, river presets, and GPS centering accessible on the move.
- **F3.3: High-Contrast Outdoor Sunlight Mode**:
  - Target files: `pages/ban-do.vue`, `assets/css/catalog.css`, `assets/css/base.css`.
  - Invariant: Activating `[data-outdoor-contrast="high"]` applies visual enhancement to the MapLibre canvas (`filter: contrast(1.25..1.3) saturate(1.1..1.2)`), bolds marker silhouettes, and renders high-visibility popup surfaces under direct tropical sunlight.
- **F3.4: Route Contrast AAA Remediation**:
  - Target file: `pages/tuyen-duong.vue`.
  - Invariant: Remediates the severe Bến Tre route header low contrast (1.71:1 -> > 7:1) by applying `--mekong-ink` text color against warm alluvial backgrounds.

#### R4: Culture, Events & Field Notes Chronicle (`tests/culture-events-chronicle.test.ts`)
- **F4.1: Mekong Water Flow & Tidal Badges**:
  - Target files: `components/MekongWaterBadge.vue`, `pages/su-kien.vue`, `pages/le-hoi.vue`, `pages/theo-mua.vue`, `pages/lich-van-nien.vue`.
  - Invariant: Component `MekongWaterBadge.vue` renders dynamic tidal state ("Con nước rong", "Con nước kém", "Nước lớn", "Nước ròng") linked to the Mekong lunar-solar rhythm.
- **F4.2: Classic Lora Pull-Quotes with `<cite>`**:
  - Target files: `pages/su-kien.vue`, `pages/le-hoi.vue`, `pages/theo-mua.vue`, `pages/lich-van-nien.vue`, `assets/css/editorial.css`.
  - Invariant: Editorial quotes (`.pull-quote`) are styled with Lora serif italic, left Mang Thít terracotta accent border, and mandatory `<cite>` attribution.
- **F4.3: Field Author Badges**:
  - Target files: `components/PostCard.vue`, `pages/cong-dong.vue`.
  - Invariant: Replaces anonymous social media avatars with verified contributor badges (`SourceMark: Ban biên tập vinhlong360` or verified field author tag).
- **F4.4: Complete Anti-AI-Slop Iconography**:
  - Target file: `components/PostCard.vue`.
  - Invariant: Zero raw emojis (e.g., `🔁`, `✍️`, ✨); 100% replacement with crisp SVG vector icons (`IconLine`).

---

### 2.2. Tier 2: Boundary, Corner & Ergonomic Limits

Tier 2 probes physical dimensions, boundary extremes, layout limits, and edge conditions to ensure that the interface never degrades at scale.

| Boundary Probe | Scope / Target | Specification Boundary | Verification Method |
|---|---|---|---|
| **B2.1: Touch Target Minimums** | Catalog chips, filter pills, route season tags, map markers | All interactive elements must strictly satisfy `min-height >= 44px` and `min-width >= 44px` (or extended hit area via `::before { min-width: 44px; min-height: 44px; }`). | Automated AST / regex inspection of CSS rules and computed selectors. |
| **B2.2: Line Length Bounds (CPL)** | Heritage detail description and editorial prose | Character-per-line bounds: min 45ch, optimal 65–70ch, max 75ch. Enforced via `max-width: var(--measure-read)` (68ch). | Style declaration check ensuring `.entity-description` and `.extra-content` cannot stretch past 70ch. |
| **B2.3: Zero / Missing Data Resilience** | Tidal indicators, weather readings, AEO metrics | If API or data attributes are absent, components must gracefully collapse (zero DOM output) rather than render skeleton placeholders. | Unit test passing `null`/`undefined` props; asserts element does not render in DOM. |
| **B2.4: Extreme Viewport Bounds** | Responsive grid behavior | Viewports tested: 320px (iPhone SE small), 390px (mobile standard), 768px (tablet portrait), 1024px (tablet landscape), 1280px (desktop), 1920px (ultra-wide). Lead hero cards must collapse to span 1 on mobile and expand to span 2 on desktop. | Container query and media query verification. |
| **B2.5: Contrast Mathematics** | Route headers & surface text tokens | Contrast must exceed 7.0:1 for large headers (AAA) and 4.5:1 for standard text across all color systems. | Color luminance math: $(L_1 + 0.05) / (L_2 + 0.05) \ge 7.0$. |

---

### 2.3. Tier 3: Cross-Feature Combinations & Invariants

Tier 3 exercises interactions between multiple distinct subsystems, verifying that cross-cutting concerns (color harmony, theme modes, typography stacks, accessibility) remain synchronized.

| Invariant Combination | Interacting Subsystems | Verification Requirement |
|---|---|---|
| **X3.1: Tri-Region x Theme Modes** | Bến Cloud (Light) vs Nocturne (Dark) vs Outdoor High-Contrast | Backgrounds, surface cards, text ink, and action buttons maintain compliant contrast ratios regardless of which mode is active. |
| **X3.2: Typography Stacks & Font Discipline** | Global CSS (`variables.css`, `base.css`, `catalog.css`, `detail.css`, `shell.css`) | No stylesheet may contain `Times New Roman`, `Arial`, or `Inter` as editorial titles. `Lora` must be the first serif font declared in `--font-editorial`. |
| **X3.3: Asymmetric Layout x Viewport Breakpoints** | Container queries x Grid layouts | `.grid--asymmetric > .card:first-child` gracefully responds to container widths without causing horizontal scrolling or visual clipping. |
| **X3.4: Accessibility Tree & ARIA States** | Interactive controls (`aria-pressed`, `role="list"`, `aria-label`) | Outdoor contrast button toggles `aria-pressed`, catalog filters maintain ARIA state, and screen readers perceive list hierarchies cleanly. |
| **X3.5: Anti-Slop Policy Compliance** | Codebase-wide scanner | Prohibits AI sparkle icons (`auto_awesome`, ✨, 🌟), SaaS neon purples (`#5B6CC4`, `#a855f7`), and fabricated reviews/ratings. |

---

### 2.4. Tier 4: Real-World Application & Field Ergonomics

Tier 4 validates the real-world utility of the platform from the perspective of an active traveler exploring the Mekong River province in field conditions.

```
+-----------------------------------------------------------------------------------+
|                           REAL-WORLD FIELD SCENARIOS                              |
+-----------------------------------------------------------------------------------+
|  [Scenario 1: Sun-Glare Exploration]                                              |
|  Traveler walking along Mang Thít brick kiln canal in bright tropical sun (11 AM).|
|  Enables Outdoor Contrast Mode -> map tiles become sharp, markers have bold       |
|  silhouettes, text ink remains legible with > 10:1 contrast on Bến Cloud paper.   |
+-----------------------------------------------------------------------------------+
|  [Scenario 2: Sampan Boat 1-Handed Navigation]                                    |
|  Traveler on a moving sampan holding phone with one hand. Controls placed at      |
|  bottom floating thumb dock allow quick switching of water presets and zoom       |
|  without reaching to the top of the screen or risking phone drop.                 |
+-----------------------------------------------------------------------------------+
|  [Scenario 3: Tidal Rhythm & River Festival Planning]                            |
|  Traveler planning a visit to Ok Om Bok festival or floating market. Tidal badge  |
|  displays "Con nước rong" or "Con nước kém", allowing user to coordinate timing   |
|  with authentic Mekong water cycles.                                              |
+-----------------------------------------------------------------------------------+
|  [Scenario 4: Monocle Editorial Deep Reading]                                     |
|  Cultural researcher reading historical monograph on Thoại Ngọc Hầu. Optimal     |
|  68ch line measure, Lora serif headings, and verified AEO plaque provide an        |
|  archival, trustworthy experience without digital eye fatigue.                    |
+-----------------------------------------------------------------------------------+
|  [Scenario 5: Gastronomy Discovery on Dedicated Hub]                              |
|  Food lover accessing `/am-thuc` to explore culinary heritage (Bún nước lèo,       |
|  Bánh xèo vịt xiêm). First dish appears in prominent 21:9 Lead Card followed by  |
|  tactile filter pills, delivering a curated epicurean journey.                    |
+-----------------------------------------------------------------------------------+
```

---

## 3. Test Suites & File Organization

| Test Suite File | Focus Area | Requirement Scope | Tier Level |
|---|---|---|---|
| `web-nuxt/tests/catalog-magazine-layout.test.ts` | Catalog Magazine Layout & Asymmetry | R1 | Tier 1, Tier 2, Tier 3 |
| `web-nuxt/tests/heritage-detail-editorial.test.ts` | Heritage Detail & Editorial Craft | R2 | Tier 1, Tier 2, Tier 3 |
| `web-nuxt/tests/cartography-field-ergonomics.test.ts` | Cartography & Field Ergonomics | R3 | Tier 1, Tier 2, Tier 4 |
| `web-nuxt/tests/culture-events-chronicle.test.ts` | Culture Events & Water Flow Chronicle | R4 | Tier 1, Tier 2, Tier 4 |
| `web-nuxt/tests/home/*.test.ts` (17 files) | Homepage Editorial & Terroir Verification | Baseline | Tier 1, Tier 3 |
| `web-nuxt/tests/tri-region-color-contract.test.ts` | Color Contrast & Surface Invariants | Baseline | Tier 2, Tier 3 |
| `web-nuxt/tests/map-terroir-ergonomics.test.ts` | Map Ergonomics Baseline | Baseline | Tier 1, Tier 2 |
| `web-nuxt/tests/ocop-gold-book-craft.test.ts` | OCOP Craft & Wax Seal Invariants | Baseline | Tier 1, Tier 2 |
| `web-nuxt/tests/platform-typography-anti-slop.test.ts`| Typography & Font Fallback Ban | Baseline | Tier 3 |

---

## 4. Execution & Verification Commands

```bash
# 1. Run all 4 new E2E and Design System test suites
cd web-nuxt && npx vitest run tests/catalog-magazine-layout.test.ts tests/heritage-detail-editorial.test.ts tests/cartography-field-ergonomics.test.ts tests/culture-events-chronicle.test.ts

# 2. Run the 17 homepage editorial test suites (81 tests)
cd web-nuxt && npx vitest run tests/home

# 3. Run the Tri-Region color contract test suite (78 tests)
cd web-nuxt && npx vitest run tests/tri-region-color-contract.test.ts

# 4. Run full Vitest suite
cd web-nuxt && npx vitest run

# 5. Run typecheck and hard-check invariants
cd web-nuxt && npm run typecheck
python ../scripts/checks/run_hard.py --all
```

---

## 5. Quality Invariants Checklist

- [x] 4-Tier test methodology established and documented.
- [x] Opaque-box testing principles enforced.
- [x] Fail-closed verification on touch targets (>= 44px) and WCAG 2.2 AAA contrast (>= 7:1 for headings).
- [x] Graceful collapse verification (CLAUDE.md §1.7) replacing synthetic fallback data.
- [x] Anti-AI-slop invariants covering fonts, emojis, layout symmetry, and color palettes.
- [x] Continuous alignment with Google Stitch Cloud Project `14916181929760067680`.
