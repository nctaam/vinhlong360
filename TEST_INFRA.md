# TEST_INFRA — Vĩnh Long 360 Test Infrastructure & Quality Constitution

> **STATUS:** ACTIVE (2026-09-16) — Hiến pháp hạ tầng kiểm thử và quy chuẩn chất lượng E2E.
> **Platform:** Vĩnh Long 360 — Cổng Khám Phá & Lữ Hành Di Sản Miệt Vườn Sông Nước
> **Scope:** Homepage Redesign & Restructuring (Modern Editorial Travel Platform)
> **Google Stitch Cloud Project ID:** `5074017185594308685`
> **Author:** `test_writer_e2e` (E2E Testing Architecture Specialist)
> **Authority Sources:**
> - `ORIGINAL_REQUEST.md` (Mốc `## 2026-09-16T01:32:33Z` — R1 to R5)
> - `.agents/orchestrator_1/PROJECT.md`
> - `web-nuxt/DESIGN.md` (Hiến pháp Thiết kế v2.0)
> - `agent/data/vinhlong360.db` & `web/data.json`

---

## 1. Test Philosophy & Core Directives

The Vĩnh Long 360 testing infrastructure safeguards the platform's editorial craftsmanship, Mekong terroir authenticity, and digital ergonomics through an automated, 4-tier opaque-box verification pyramid.

```
                    ▲
                   / \
                  /   \
                 / T4  \     Tier 4: Real-World Workload Scenarios
                /-------\    (First-time tourist, foodie trail, sunlight sampan, weekend explorer, 3G resilience)
               /         \
              /   T3      \   Tier 3: Cross-Feature Combinations & Invariants
             /-------------\  (Search x Showcases, Anchors x Planner, Typography x Tokens, A11y Contrast)
            /               \
           /      T2         \ Tier 2: Boundary, Corner & Ergonomic Limits
          /-------------------\ (>=44px touch targets, regex sanitization, ferry midnight bounds, viewport extremes)
         /                     \
        /         T1            \ Tier 1: Feature Coverage (R1 – R5)
       /-------------------------\ (Smart Hero, Quick Anchors, Curated Showcases, Companion, Stitch MCP, Zero Media)
```

### Core Testing Directives
1. **Opaque-Box Requirement-Driven Verification**:
   - Tests validate observable contracts, DOM hierarchies, computed styling invariants, CSS custom properties, and semantic attributes without coupling to internal component private state.
   - Assertions are derived strictly from `ORIGINAL_REQUEST.md` R1-R5 and `PROJECT.md`.
2. **Fail-Closed Gateways**:
   - Any violation of WCAG 2.2 AAA contrast ratios (>= 7:1 for headings, >= 4.5:1 for body text, >= 14:1 in outdoor high-glare), touch target minimums (< 44x44px), or anti-slop rules (sparkles, neon purples/cyans, equal-column SaaS slop) results in immediate test failure.
3. **Graceful Collapse Assurance (CLAUDE.md §1.7)**:
   - When external data (weather, tides, or field sensors) is missing or unavailable, the system must cleanly collapse the view rather than render empty boxes, skeleton placeholders, or fabricated fallback metrics.
4. **Data Authenticity & Invariance**:
   - 100% of displayed entities must stem from verified SQLite and JSON records (`vinhlong360.db` and `data.json`).
   - Bit-for-bit SHA-256 hash preservation is strictly enforced.
5. **Absolute Zero Audio, Zero Video Policy**:
   - Complete prohibition of `<audio>`, `<video>`, `.mp3`, `.mp4`, `.webm`, autoplay media, or background soundtracks across all public surfaces.

---

## 2. 4-Tier Test Design Methodology

### 2.1. Tier 1: Feature Coverage (Requirements R1 – R5)
Every primary requirement is verified with at least 5 dedicated, automated test cases in `web-nuxt/tests/home-editorial-e2e.test.ts` and co-located home suites.

#### R1: Tourism-First Discovery Architecture
- **F1.1: Smart Travel Hero Structure**: Validates cinematic Mekong visual framing, discovery kicker, headline, and search integration.
- **F1.2: 5 Travel Intent Quick Anchors**: Validates 5 core tourism intents:
  1. *Du lịch Sinh thái Miệt vườn* (ecotourism)
  2. *Ký sự Làng nghề Truyền thống* (craft-village)
  3. *Hành trình Tâm linh Di sản* (heritage-spirit)
  4. *Ẩm thực & Chợ nổi* (culinary)
  5. *Nghỉ dưỡng Homestay Ven sông* (riverside-stays)
- **F1.3: Quick Anchors Ergonomics**: Enforces touch target bounds `>= 44x44px` (`--touch-min`).
- **F1.4: Multi-Criteria Search Discovery**: Verifies search capabilities across destinations, homestays, culinary dishes, and travel duration (1-2-3 days).
- **F1.5: Discovery over Monograph Positioning**: Ensures primary discovery path emphasizes travel exploration rather than raw geological thesis banners.

#### R2: Curated Travel Showcase
- **F2.1: Must-Visit Destinations Inventory**: Verifies authentic presence of Cù Lao An Bình, Lò gạch Mang Thít, Chợ nổi Trà Ôn, Chùa Hạnh Phúc Tăng, and KDL Vinh Sang in authoritative data stores.
- **F2.2: Vinh Long Culinary Trail**: Verifies authentic iconic dishes: Cá tai tượng chiên xù, Bánh xèo hến Cổ Chiên, Khoai lang mắm sống cuốn lá cách, Cháo cá lóc rau đắng / Lẩu cua đồng, and Ốc lác.
- **F2.3: Authentic Riverside Stays**: Verifies ASEAN-standard homestays (Út Trinh Homestay, Mekong Riverside, Ba Linh).
- **F2.4: Asymmetric Magazine Layout**: Banning uniform 4-column equal SaaS grids; enforcing Fibonacci proportions and editorial rhythm.
- **F2.5: Anti-Synthetic Data Integrity**: Strictly eliminates fake ratings, review generators, or placeholder stars per CLAUDE.md §1.7.

#### R3: Smart Travel Planner & Traveler Live Companion
- **F3.1: Curated Itineraries (1, 2, 3 Days)**: Verifies 1-day ("Một ngày làm nông dân cù lao"), 2-day ("Về miền di sản gốm đỏ Mang Thít"), and 3-day ("Toàn cảnh đất phương Nam").
- **F3.2: Real-Time Logistical Ferry Data**: Verifies Bến phà Đình Khao (24/24h continuous service, 10-15m day, 30-45m night) and Bến phà An Bình (04:30 - 22:30).
- **F3.3: Verified Emergency Hotlines Directory**: Validates Waterway rescue (`0270 3822 305`), Tourism support (`0270 3822 188`), Medical (`115`), Police (`113`) in `server/utils/terroir/emergencyHotlines.ts`.
- **F3.4: Practical Traveler Logistics**: Replaces dry pedology formulas with real-time river guidance, crossing frequency, and weather briefings.
- **F3.5: Graceful Collapse**: Verifies zero skeleton mush and zero technical error leak under data absence.

#### R4: Google Stitch MCP Visual Grounding
- **F4.1: Stitch Cloud Project Alignment**: Aligns design tokens and screens with Project ID `5074017185594308685` and Asset `assets/d2b2b7344efd4dc891e671fe846db9e3`.
- **F4.2: Editorial Aldine Typography**: Enforces **Lora** serif for display/headings and **Be Vietnam Pro** for clean Vietnamese body typography.
- **F4.3: Mobile Fieldwork Thumb Dock**: Enforces bottom thumb-zone dock ergonomics (`safe-area-inset-bottom`) for one-handed operation.
- **F4.4: Eradication of AI Sparkles**: Zero sparkles (`sparkle`, `auto_awesome`, ✨, 🌟) across 100% of Vue components.
- **F4.5: Eradication of SaaS Neon Gradients**: Prohibits neon purples (`#a855f7`, `#7c3aed`) and cyans (`#00f0ff`) in stylesheets.

#### R5: Strict Technical & Safety Standards
- **F5.1: Zero Audio / Zero Video Invariant**: Absolute prohibition of audio/video elements across templates, layouts, and components.
- **F5.2: Extreme Accessibility WCAG 2.2 AAA**: Text contrast `>= 7:1` on background canvas/surface; `>= 14:1` in high-glare outdoor mode.
- **F5.3: Interactive Touch Target Minimums**: 100% buttons, chips, and links meet `>= 44x44px`.
- **F5.4: SHA-256 Immutability**:
  - `agent/data/vinhlong360.db`: `8b093b9537711ef6c060a4b5a49e4228cf11b840862b20647009254cc19ac5cf`
  - `web/data.json`: `45e528447c08205c774695acae1c9a7a4c8e9a535fc7a945e3a7120360d598c8`
- **F5.5: 9 Protected Variables Under `[data-home-pilot="nocturne-b1"]`**: Preserves `--home-color-amber-text`, `--home-color-amber-surface`, `--home-color-focus-on-action`, `--home-color-focus-on-media`, `--home-color-focus-on-media-halo`, `--home-color-on-media-text`, `--home-color-on-media-plate`, `--home-color-today-text`, `--home-color-today-surface`.

---

### 2.2. Tier 2: Boundary & Corner Cases

Probes edge limits, extreme input sizes, boundary transitions, and error resilience:

| Test ID | Requirement | Edge Condition / Boundary Tested | Invariant Enforced |
|---|---|---|---|
| **B1.1** | R1 Search | Empty or whitespace query (`"   "`) | Clean silent handling, no crashes or empty errors |
| **B1.2** | R1 Search | Special regex characters (`[2026]* + ? ^ $ \`) | Input sanitized, no RegExp evaluation syntax errors |
| **B1.3** | R1 Search | Ultra-long search string (300+ chars) | Input bounded, no layout blowout |
| **B1.4** | R1 Anchors | Rapid sequential switching between 5 anchors | Deterministic active state resolution |
| **B1.5** | R1 Search | Zero-result search query | Provides authentic category recovery suggestions |
| **B2.1** | R2 Showcase | Entity with null/omitted optional summary | Graceful fallback text, no `"undefined"` or `"null"` leak |
| **B2.2** | R2 Showcase | Missing cover image | Fallback scrim applied, no broken image icon |
| **B2.3** | R2 Showcase | Reading line length boundary | Constrained to `--measure-read` (68ch) |
| **B2.4** | R2 Showcase | Vietnamese diacritics in entity names | NFC unicode normalization verified |
| **B2.5** | R2 Showcase | Single-entity showcase list | Renders without carousel fracture or broken layout |
| **B3.1** | R3 Logistics | Midnight ferry schedule transition (22:00 – 04:00)| Accurate night frequency (30-45m) vs day (10-15m) |
| **B3.2** | R3 Companion | Hotline phone numbers RFC 3966 `tel:` URI format | Valid telephone URIs for one-touch dialing |
| **B3.3** | R3 Companion | Total network failure on live briefing API | Returns clean null (graceful collapse), no fake mock data |
| **B3.4** | R3 Planner | Itinerary duration bounds | Strictly 1, 2, or 3 days; rejects <=0 or >=4 |
| **B3.5** | R3 Planner | Missing GPS coordinates on route stops | Does not crash mapping parser |
| **B4.1** | R4 Ergonomics | Ultra-narrow viewport (320px iPhone SE) | Enforces `--maxw` / no horizontal overflow |
| **B4.2** | R4 Ergonomics | Ultra-wide viewport (1920px desktop) | Constrains layout width to `--maxw: 1140px` |
| **B4.3** | R4 Ergonomics | High-glare outdoor mode contrast | Elevates contrast to `>= 14:1` on sunlight canvas |
| **B4.4** | R4 Ergonomics | `prefers-reduced-motion` media query | Eliminates kinetic triggers and CSS transitions |
| **B4.5** | R4 Ergonomics | `prefers-reduced-transparency` media query | Replaces semi-transparent glass with solid plates |
| **B5.1** | R5 Safety | Non-finite numbers in computed CSS tokens | Fails closed on `NaN` or non-finite values |
| **B5.2** | R5 Safety | Negative or undersized touch target dimensions | Rejects dimensions `< 44px` |
| **B5.3** | R5 Safety | Malicious CSS overrides hidden in comments | Detects and blocks illicit style resets |
| **B5.4** | R5 Safety | Hex color syntax case-insensitivity & validity | Validates hex codes across variables |
| **B5.5** | R5 Safety | SHA-256 hash constant immutability | 64-char hex integrity checked against tampering |

---

### 2.3. Tier 3: Cross-Feature Combinations (Pairwise Coverage)

Validates seamless interaction and invariant synchronization across disparate modules:

- **X3.1: R1 Search × R2 Curated Showcases**:
  - Ensures showcase entities (Cù Lao An Bình, Lò gạch Mang Thít, Chợ Nổi Trà Ôn, Cá tai tượng, Homestay Út Trinh) are indexed and matchable through search discovery.
- **X3.2: R1 Intent Anchors × R3 Curated Itineraries**:
  - Ensures selecting intent anchors (e.g. `ecotourism`, `craft-village`, `heritage-spirit`) links directly to curated itineraries (`mot-ngay-cu-lao-an-binh`, `di-san-mang-thit-tra-vinh`, `mien-tay-3-ngay`).
- **X3.3: R2 Showcase Typography × R4 Stitch Design System**:
  - Enforces Lora serif headline typography and Fibonacci spacing tokens (`--space-fib-1` through `--space-fib-6`) across showcase containers.
- **X3.4: R3 Live Companion Cards × R5 WCAG AAA Contrast**:
  - Validates logistical cards (ferry, weather, emergency contacts) satisfy `>= 7:1` contrast in both light and dark themes using `--color-on-action`, `--surface-white`, and `--color-action`.
- **X3.5: R4 Mobile Thumb Dock × R5 Touch Target Minimums**:
  - Validates dock controls strictly satisfy `min-height` and `min-width` `>= var(--touch-min)` (44px) within natural thumb sweep.

---

### 2.4. Tier 4: Real-World Workload Scenarios

Models complete, authentic user journeys under real-world Mekong field conditions:

1. **Scenario 1: First-Time Tourist Discovery Journey**:
   - Traveler lands on homepage, inputs "Mang Thít" into Smart Hero Search, selects travel intent anchor "Ký sự Làng nghề Truyền thống", and reviews the 2-day itinerary `di-san-mang-thit-tra-vinh`.
2. **Scenario 2: Foodie Epicurean Expedition**:
   - Food lover navigates to the Vinh Long Culinary Trail, identifies iconic "Cá tai tượng chiên xù", verifies authentic venue coordinates, and confirms absence of fabricated ratings or review slop.
3. **Scenario 3: River Fieldwork under Bright Sunlight**:
   - Traveler standing at Đình Khao ferry terminal at midday under tropical sun; enables High-Glare Outdoor Mode (`>= 14:1` contrast) and operates bottom floating thumb dock with one-hand touch targets `>= 44px`.
4. **Scenario 4: Cultural Heritage Weekend Explorer**:
   - Cultural researcher visits the Mang Thít Brick Kiln Contemporary Heritage site, checks availability of ASEAN-certified Út Trinh Homestay, and confirms immediate access to waterway rescue hotline `0270 3822 305`.
5. **Scenario 5: Degraded River Network Resilience**:
   - Traveler on a remote river sampan experiencing spotty 3G connectivity; external weather API fails; homepage gracefully collapses the briefing widget with zero skeleton mush and zero app crashes.

---

## 3. Test Suite Inventory & Alignment

| Test File | Focus Area | Tier Alignment | Tests Count | Status |
|---|---|---|---|---|
| `web-nuxt/tests/home-editorial-e2e.test.ts` | Complete 4-Tier E2E Verification (R1-R5) | Tier 1, 2, 3, 4 | 60 | **PASS (60/60)** |
| `web-nuxt/tests/home-nocturne-page.test.ts` | Page mounting, data contracts, hydration | Tier 1, Tier 2 | 17 | **PASS (17/17)** |
| `web-nuxt/tests/home-anti-slop-craft.test.ts` | Anti-slop, haptics, physics, no neon/sparkle | Tier 1, Tier 2 | 9 | **PASS (9/9)** |
| `web-nuxt/tests/home-product-lead.test.ts` | Product lead display & feature flag toggles | Tier 1, Tier 2 | 8 | **PASS (8/8)** |
| `web-nuxt/tests/home-ocop-ledger.test.ts` | OCOP golden ledger & CLAUDE.md §1.7 | Tier 1, Tier 2 | 7 | **PASS (7/7)** |
| `web-nuxt/tests/home-local-briefing.test.ts` | Weather briefing & graceful collapse | Tier 1, Tier 2 | 7 | **PASS (7/7)** |
| `web-nuxt/tests/home-feature-dossier.test.ts` | Hero feature dossier & photo licensing | Tier 1, Tier 2 | 7 | **PASS (7/7)** |
| `web-nuxt/tests/home-nocturne-color-cascade.test.ts` | Amber text contrast in light/dark modes | Tier 2, Tier 3 | 6 | **PASS (6/6)** |
| `web-nuxt/tests/home-native-stories.test.ts` | Native stories mount & length bounds | Tier 1, Tier 2 | 6 | **PASS (6/6)** |
| `web-nuxt/tests/home-world-class-editorial.test.ts` | Editorial layout & typography hierarchy | Tier 1, Tier 3 | 5 | **PASS (5/5)** |
| `web-nuxt/tests/home-nocturne-components.test.ts` | Subcomponents & media disclosure | Tier 1, Tier 3 | 5 | **PASS (5/5)** |
| `web-nuxt/tests/home-smart-terroir.test.ts` | Terroir context data flow | Tier 1 | 4 | **PASS (4/4)** |
| `web-nuxt/tests/home-layout-asymmetry.test.ts` | Asymmetric editorial layout | Tier 1, Tier 2 | 4 | **PASS (4/4)** |
| `web-nuxt/tests/home-aeo-plaque.test.ts` | Seasonal AEO plaque verification | Tier 1, Tier 2 | 4 | **PASS (4/4)** |
| `web-nuxt/tests/home-terroir-resilience.test.ts` | Resilience against missing data | Tier 2 | 3 | **PASS (3/3)** |
| `web-nuxt/tests/home-category-balance.test.ts` | Category distribution balance | Tier 1 | 3 | **PASS (3/3)** |
| `web-nuxt/tests/home-decision-category.test.ts` | Quick decisions ledger | Tier 1 | 3 | **PASS (3/3)** |
| `web-nuxt/tests/home-nocturne-presentation.test.ts` | Presentation helper logic | Tier 1, Tier 2 | 3 | **PASS (3/3)** |
| `web-nuxt/tests/home-visual-prominence.test.ts` | Visual prominence of lead items | Tier 1 | 2 | **PASS (2/2)** |
| `web-nuxt/tests/home-community-editorial.test.ts` | Community feed editorial standards | Tier 1 | 2 | **PASS (2/2)** |
| `web-nuxt/tests/home-hero-dossier-polish.test.ts` | Hero dossier polish details | Tier 1 | 1 | **PASS (1/1)** |
| `web-nuxt/tests/home-ocop-aeo-polish.test.ts` | OCOP AEO polish details | Tier 1 | 1 | **PASS (1/1)** |
| **TOTAL tests/home** | **22 test files** | **Tiers 1–4** | **167** | **100% PASS** |
| `web-nuxt/tests/tri-region-color-contract.test.ts` | Tri-Region contrast, mutations, 9 protected vars | Tier 2, Tier 3 | 78 | **100% PASS** |
| **GRAND TOTAL VERIFIED** | **23 test files** | **All Tiers** | **245** | **100% PASS** |

---

## 4. Verification Execution Commands

To execute independent verification, run the following commands:

```bash
# 1. Run all Homepage & Editorial E2E tests (167 tests, 22 files)
cd web-nuxt && npx vitest run tests/home

# 2. Run the Tri-Region Color Contract suite (78 tests, mutation-tested)
cd web-nuxt && npx vitest run tests/tri-region-color-contract.test.ts

# 3. Run Nuxt TypeScript Typecheck (0 errors)
cd web-nuxt && npm run typecheck

# 4. Run Hard Safety Gates across entire repository
python ../scripts/checks/run_hard.py --all
```

---

## 5. Escalated Implementation Defects (QA Findings)

During verification of the newly created component files authored by `worker_implementation_1`, the hard safety check (`run_hard.py --all`) detected 18 violations of rule **R30.3 (fe_colors)**:

- **Root Cause**: The following newly created Vue components include hardcoded hex color fallbacks inside `var(...)` and `color-mix(...)` declarations instead of referencing clean design tokens:
  1. `web-nuxt/components/home/HomeCulinaryTrail.vue`: line 232 (`#d99b26`)
  2. `web-nuxt/components/home/HomeCuratedShowcase.vue`: line 305 (`#b95f38`)
  3. `web-nuxt/components/home/HomeIntentAnchors.vue`: lines 185, 186, 190, 191, 195, 196, 200, 201, 205, 206
  4. `web-nuxt/components/home/HomeRiversideStays.vue`: lines 256, 336
  5. `web-nuxt/components/home/HomeTravelCompanion.vue`: lines 288, 289, 293, 294
- **Remediation Action Required**: Strip the hardcoded fallback parameter from `var(--token, #hex)` so it becomes `var(--token)`. All tokens are already defined in `variables.css`.
- **Classification**: Implementation Defect (Escalated to `worker_implementation_1` and parent orchestrator).
