# Project: Vinh Long 360 Visual-First Homepage Redesign

## Architecture
Vinh Long 360 (`vinhlong360`) is an editorial travel and living heritage platform for Vĩnh Long Province in the Mekong Delta. The system architecture encompasses:
- **Cloud Design Grounding**: Google Stitch MCP Project `5074017185594308685` bound to Design System `assets/d2b2b7344efd4dc891e671fe846db9e3` (Co Chien Blue `#006798`, Mang Thit Terracotta `#b95f38`, Alluvial Amber `#c99446`, Cu Lao Green `#1b8844`, Bến Cloud `#faf9f7`, Lora display serif, Be Vietnam Pro sans).
- **Frontend Layer**: Nuxt 4 application (`web-nuxt/`) using Vue 3 SFCs, standard CSS variables/tokens (`variables.css`, `tri-region-color.css`, `home-nocturne.css`), and strict WCAG 2.2 AAA accessibility. Zero Tailwind, zero external stock imagery, zero audio/video autoplay.
- **Data Layer**: Authentic local travel dataset in `web/data.json` and SQLite `agent/data/vinhlong360.db` (220 destinations, 164 homestays, 186 restaurants, 120 dishes, 91 activities, 16 itineraries) cryptographically protected with SHA-256 bit-for-bit invariants.
- **Verification Layer**: 22 home test suites (167 tests), 78 color contract tests, zero token debt auditor, TypeScript typecheck, and Python `run_hard.py` invariant gates (30 rules).

## Feature Inventory
Every feature identified from the authoritative request (`ORIGINAL_REQUEST.md`) and the Phase 0 survey is mapped to an assigned milestone.

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1. Visual-First Ratio & Text Brevity | $\ge 75\%$ photo visual area, $\le 25\%$ text, descriptions $\le 120$ characters or 2 short lines, eliminate text-walls, concise pill badges and micro-stats | M1 | ORIGINAL_REQUEST §R1 |
| 2 | F2. Full-Bleed Cinematic Hero & Frosted Search | Edge-to-edge widescreen river hero, floating frosted-glass multi-criteria search bar (`backdrop-blur-xl bg-white/20`), keyword input, duration pills (1D, 2D1N, 3D2N), travel style filters, quick trending tags | M1 | ORIGINAL_REQUEST §R2 |
| 3 | F3. 5 Visual Intent Pills | 5 tactile navigation pills with circular photographic thumbnails (36-40px diameter) + category icons (*Sinh Thái*, *Làng Nghề*, *Tâm Linh*, *Ẩm Thực*, *Homestay*) | M1 | ORIGINAL_REQUEST §R2 |
| 4 | F4. Curated Wonder Gallery Mosaic | Asymmetric magazine layout: Mang Thít lead tile (80% photo), An Bình orchard, Trà Ôn floating market, Khmer pagoda, KDL Vinh Sang; subtle zoom on hover (`scale(1.04)`), location pill badges, interactive Save Bookmark button (`useFavorites().toggle()`) | M1 | ORIGINAL_REQUEST §R2 |
| 5 | F5. Gastro Trail (5 Full-Bleed Food Cards) | Edge-to-edge mouth-watering food photography cards for 5 signature dishes (Cá tai tượng chiên xù, Bánh xèo hến, Lẩu cua đồng, Ốc lác nướng tiêu, Khoai lang chấm mắm sống), zero dry recipe text, dish title, reputable venue pill badge, and directions action button | M1 | ORIGINAL_REQUEST §R3 |
| 6 | F6. Riverside Retreat Lookbook | 16:9 widescreen evocative photo cards for authentic homestays (Út Trinh Homestay, Mekong Riverside, Ba Linh Homestay), peaceful riverfront verandas, direct booking/contact action buttons ($\ge 44\text{px}$) | M1 | ORIGINAL_REQUEST §R3 |
| 7 | F7. Google Stitch MCP Cloud Sync | Update Project `5074017185594308685` with Desktop Homepage screen and Mobile Fieldwork screen adhering to Design System `assets/d2b2b7344efd4dc891e671fe846db9e3` and Visual-First standards | M1 | ORIGINAL_REQUEST §R4 |
| 8 | F8. Strict Technical & Safety Gates | 0 audio, 0 video auto-play; WCAG 2.2 AAA (contrast $\ge 7:1$, touch target $\ge 44\times 44\text{px}$); 100% pass across all test suites (`npx vitest run tests/home`, `npx vitest run tests/tri-region-color-contract.test.ts`, `node scripts/check-tri-region-color-debt.mjs`, `npm run typecheck`, `python ../scripts/checks/run_hard.py --all`); bit-for-bit SHA-256 database integrity | M1 | ORIGINAL_REQUEST §R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Visual-First Homepage Redesign (Stitch Cloud & Nuxt Implementation) | Full execution of Visual-First homepage redesign: (1) Generate Desktop & Mobile screens on Google Stitch MCP project `5074017185594308685` with Design System `assets/d2b2b7344efd4dc891e671fe846db9e3`; (2) Implement Nuxt components (`HomeIntentAnchors.vue`, `HomeCuratedShowcase.vue`, `HomeCulinaryTrail.vue`, `HomeRiversideStays.vue`, `pages/index.vue`, `assets/css/home-nocturne.css`) with $\ge 75\%$ photo coverage, $\le 120$ chars copy, bookmark button, full-bleed hero, frosted search island; (3) Pass 100% test suites (167+ home tests, 78 color contract tests), 0 token debt, 0 typecheck errors, 0 hard check violations, WCAG 2.2 AAA compliance, and bit-for-bit SHA-256 database integrity. | none | IN_PROGRESS |

## Interface Contracts
### `HomeIntentAnchors` ↔ `pages/index.vue`
- Emits: navigation route triggers.
- Visual contract: 5 pill capsules with 36-40px circular photo avatars, icon, title, $\ge 44\times 44\text{px}$ tap target.

### `HomeCuratedShowcase` ↔ `pages/index.vue` / `useFavorites`
- Visual contract: Asymmetric mosaic (Lead Mang Thít 80% photo, satellites $\ge 75\%$ photo).
- Interactive contract: Bookmark toggle calls `useFavorites().toggle(item.id)`. Descriptions strictly $\le 120$ characters.

### `HomeCulinaryTrail` ↔ `pages/index.vue`
- Visual contract: 5 full-bleed macro food cards (Cá tai tượng, Bánh xèo hến, Lẩu cua đồng, Ốc lác, Khoai lang).
- Content contract: Zero recipe text. Title, venue name pill, map action button $\ge 44\text{px}$.

### `HomeRiversideStays` ↔ `pages/index.vue`
- Visual contract: 16:9 widescreen photo cards. Peaceful riverfront lookbook.
- Content contract: Descriptions $\le 120$ characters. Booking phone/action button $\ge 44\text{px}$.

### `pages/index.vue` Section Sequence Allowlist
- Preserved strict order: `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']`.

## Code Layout
- `web-nuxt/pages/index.vue`: Homepage root template, full-bleed hero, floating frosted-glass search bar.
- `web-nuxt/components/home/HomeIntentAnchors.vue`: 5 Visual Intent Pills with circular photo thumbnails.
- `web-nuxt/components/home/HomeCuratedShowcase.vue`: Curated Wonder Gallery Asymmetric Mosaic with bookmark save.
- `web-nuxt/components/home/HomeCulinaryTrail.vue`: 5 Macro Food Photography Full-Bleed Cards.
- `web-nuxt/components/home/HomeRiversideStays.vue`: Riverside Retreat Lookbook.
- `web-nuxt/assets/css/home-nocturne.css`: Homepage stylesheet and CSS variable tokens.
- `web-nuxt/tests/home/*`: Vitest homepage test suite (167 tests).
- `web-nuxt/tests/tri-region-color-contract.test.ts`: Color token contract tests (78 tests).
