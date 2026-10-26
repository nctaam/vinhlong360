# Project: Vinh Long 360 — Quiet Luxury & Mobile Ergonomics Overhaul

## Architecture
- **Framework**: Nuxt 4.5.2 + Nitro 2.13.4 SSR.
- **Styling Architecture**: Native CSS tokens in `assets/css/` (`variables.css`, `base.css`, `shell.css`, `cards.css`, `home-nocturne.css`). Strict constraint: `no_tailwind` (R30.1), `fe_colors` tokenized (R30.3), `fe_radius_scale` (R30.8).
- **Component Architecture**: Scoped Vue 3 components (`EntityCard.vue`, `FilterChips.vue`, `SaveButton.vue`, `PocketPassModal.vue`, etc.).
- **Verification Harnesses**: Python check engine (`scripts/checks/run_hard.py`), Vitest (248 test suites in `web-nuxt`), Nitro build pipeline + launch readiness manifest.
- **Deployment Target**: VPS `66.42.57.202`, systemd service `vl-nuxt.service`, reverse proxy Nginx serving `https://vinhlong360.vn/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Dark Hero Scrim Fix (R3) | Fix white milk-glass wash `rgba(var(--ink-rgb), 0.72)` in `home-nocturne.css:2220` to dark gradient to restore hero text contrast. | M1 | Survey Obs-1 |
| 2 | EntityCard Decluttering (R1) | Remove redundant "Quanh năm" badges, remove `.card-rule` decorative line, ensure "One Primary Focal Point" for imagery and title. | M1 | Survey Obs-2 |
| 3 | FilterChips Refinement (R1) | Remove 3-color underline gradient pseudo-element on active chips, refine chip spacing and visual breathing room. | M1 | Survey Obs-4 |
| 4 | Catalog Route Spacing & Negative Space (R1) | Tinh giản khung viền hộp lồng nhau trên `/du-lich`, `/am-thuc`, `/danh-ba`, `/ocop`, mở rộng negative space. | M1 | Survey Obs-3 |
| 5 | Color Token Contrast Tuning (R3) | Replace/adjust low-contrast tokens like `--mangthit-500` in `danh-ba.vue` and secondary tokens to meet WCAG 2.2 AAA standards. | M1 | Survey Obs-5 |
| 6 | 320px Header Overflow Elimination (R2) | Eliminate ~30px overflow on <=400px viewports in `shell.css` by hiding display settings button on ultra-narrow mobile. | M1 | Survey Obs-1 |
| 7 | CSS Grid Blowout Fix (R2) | Fix `HomeRiversideStays.vue` grid template columns to `minmax(min(100%, 260px), 1fr)`. | M1 | Survey Obs-2 |
| 8 | Double-Gutter Padding Trap Elimination (R2) | Eliminate 80px double padding trap between `.page` and `.block` on mobile viewports. | M1 | Survey Obs-3 |
| 9 | SaveButton Touch Target 44px (R2) | Ensure `SaveButton.vue` (`.save-btn-sm`) satisfies minimum 44px x 44px touch target requirement. | M1 | Survey Obs-4 |
| 10 | Micro-Typography & Vietnamese Word-Wrapping (R2) | In `EntityCard.vue`, replace `hyphens: auto; overflow-wrap: anywhere;` with `overflow-wrap: break-word; text-wrap: pretty;`, restore `text-wrap: balance` for section headings. | M1 | Survey Obs-5,6 |
| 11 | Map Dock & Modal Viewport Ergonomics (R2) | Hide `.map-floating-thumb-dock` on `/ban-do` when in list panel mode; adjust `PocketPassModal.vue` close button for short mobile viewports. | M1 | Survey Obs-7,8 |
| 12 | System Integrity Gate (Acceptance) | Run `python scripts/checks/run_hard.py --all` verifying hard=0 and zero ratchet increases. | M2 | Acceptance Criteria |
| 13 | Vitest 248 Suites Green (Acceptance) | Run `npm test` in `web-nuxt` ensuring 100% pass across all 248 test suites (3348+ tests). | M2 | Acceptance Criteria |
| 14 | Clean Build & Bundle Check (Acceptance) | Run `npm run build` with manifest generation and verify bundle budget check. | M2 | Acceptance Criteria |
| 15 | VPS Deployment & Live HTTP 200 (Acceptance) | Deploy new build to VPS `66.42.57.202`, restart `vl-nuxt.service`, curl test `https://vinhlong360.vn/` returning HTTP 200 OK. | M2 | Acceptance Criteria |
| 16 | Comprehensive Audit & Scorecard (Acceptance) | Produce detailed system review report and Quiet Luxury ergonomics scorecard. | M2 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Frontend Craft Overhaul (Quiet Luxury, Contrast & Ergonomics) | Features #1 to #11 (R1, R2, R3) | none | IN_PROGRESS |
| 2 | M2: Integrity Verification, VPS Deployment & Live Sign-off | Features #12 to #16 (Acceptance) | M1 | PLANNED |

## Interface Contracts
### Styling & Token Contract (R30.1, R30.3, R30.8)
- Absolutely NO Tailwind utility classes in `.vue` or `.css` files (`no_tailwind` hard gate).
- Colors MUST use existing CSS custom properties defined in `variables.css` or semantic variables (`fe_colors` hard-ratchet 0).
- Radii MUST use `--radius-*` tokens (`fe_radius_scale` hard-ratchet 0).
- Touch targets for interactive elements MUST have minimum 44px x 44px bounds (`ui-ux-ergonomics-gate.test.ts`).

### Component Contracts
- `EntityCard.vue`: Props (`entity`, `variant`, `density`) and event emitters must remain unchanged. No visual regression on card links.
- `FilterChips.vue`: Model value and change events must remain unchanged.
- `SaveButton.vue`: Button contract and bookmark storage event handling must remain unchanged.

## Code Layout
- `web-nuxt/assets/css/variables.css`: Design tokens & theme variables (Parchment & Nocturne).
- `web-nuxt/assets/css/base.css`: Base typography & layout classes.
- `web-nuxt/assets/css/shell.css`: Header shell & navigation styling.
- `web-nuxt/assets/css/cards.css`: Card layout rules.
- `web-nuxt/assets/css/home-nocturne.css`: Homepage Nocturne theme overrides & hero scrims.
- `web-nuxt/components/EntityCard.vue`: Primary entity showcase card.
- `web-nuxt/components/FilterChips.vue`: Catalog filter chip row.
- `web-nuxt/components/SaveButton.vue`: Bookmark action button.
- `web-nuxt/components/PocketPassModal.vue`: PocketPass dialog modal.
- `web-nuxt/components/home/HomeRiversideStays.vue`: Riverside stays section.
- `web-nuxt/pages/`: Catalog and map routes (`du-lich.vue`, `am-thuc.vue`, `danh-ba.vue`, `ocop.vue`, `ban-do.vue`).
