# TEST_READY — Vĩnh Long 360 Core Subsystems Comprehensive E2E Test Suite (Moc 134)

> STATUS: active (2026-09-15) — Tiêu chuẩn nghiệm thu kiểm thử tự động toàn diện.

- **Platform**: Vĩnh Long 360 — Mekong River Heritage & Discovery Platform
- **Milestone**: Moc 134 — Core Subsystems Comprehensive E2E Test Suite (R1–R4)
- **Author**: `test_writer_e2e_subsystems_1` (teamwork test writer / QA specialist)
- **Status**: **ALL 71 TARGETED E2E TESTS VERIFIED GREEN (100% PASS)**
- **Baseline Reference**: `ORIGINAL_REQUEST.md` (mốc `## 2026-09-13T04:03:15Z`), `.agents/orchestrator_8/TEST_INFRA.md`, `.agents/explorer_survey_infra_1/handoff.md`
- **Execution Timestamp**: 2026-09-13T04:27:00Z

---

## 1. Executive Test Readiness Summary

The automated end-to-end verification test suite for the 4 core subsystems (Itinerary Builder & Pocket Journal, Local Directory & Monocle Gazetteer, Contributor Honor Roll & Leaderboard, User Collections & Privacy Governance, Civic Transparency & Editorial Charter) has been authored, verified, and executed across all 4 tiers:

```
 RUN  v4.1.9 C:/Users/NCTaam/Documents/vinhlong360-correction-case-pilot/web-nuxt

 ✓ tests/user-collections-portfolio-craft.test.ts (14 tests) 24ms
 ✓ tests/civic-transparency-editorial-charter.test.ts (14 tests) 22ms
 ✓ tests/itinerary-expedition-journal-craft.test.ts (15 tests) 23ms
 ✓ tests/contributor-ranking-honor-roll.test.ts (14 tests) 19ms
 ✓ tests/local-directory-monocle-almanac.test.ts (14 tests) 22ms

 Test Files  5 passed (5)
      Tests  71 passed (71)
   Start at  11:26:53
   Duration  1.18s (transform 1.01s, setup 1.17s, import 1.23s, tests 110ms, environment 3ms)
```

- **Target Threshold**: $\ge 51$ total tests.
- **Actual Delivered Tests**: **71 / 71 PASSED (100% GREEN, 0 failed, 0 flaky)**.
- **Execution Speed**: **1.18 seconds** for all 5 test files.
- **Safety Invariant Attestation**:
  - `agent/data/vinhlong360.db`: Read-only verified; zero database modifications.
  - `web/data.json`: Read-only verified; zero mutations.
  - Tri-Region Color Debt: **PASS** (`node scripts/check-tri-region-color-debt.mjs` exits 0, 0 raw hex, 0 legacy primary).
  - Hard Checks: **PASS** (`python scripts/checks/run_hard.py --all` exits 0, hard=0, ratchet not increased).
  - Implementation Code Isolation: **100% compliant**; only new test files authored in `web-nuxt/tests/`.

---

## 2. Test Execution Commands

### Run Complete 5-Subsystem E2E Test Suite (71 Tests)
```bash
cd web-nuxt && npx vitest run \
  tests/itinerary-expedition-journal-craft.test.ts \
  tests/local-directory-monocle-almanac.test.ts \
  tests/contributor-ranking-honor-roll.test.ts \
  tests/user-collections-portfolio-craft.test.ts \
  tests/civic-transparency-editorial-charter.test.ts
```

### Run Subsystems Individually
- **R1 Itinerary Builder & Pocket Field Journal**:
  ```bash
  cd web-nuxt && npx vitest run tests/itinerary-expedition-journal-craft.test.ts
  ```
- **R2 Local Directory & Monocle Gazetteer**:
  ```bash
  cd web-nuxt && npx vitest run tests/local-directory-monocle-almanac.test.ts
  ```
- **R2 Contributor Honor Roll & Cultural Leaderboard**:
  ```bash
  cd web-nuxt && npx vitest run tests/contributor-ranking-honor-roll.test.ts
  ```
- **R3 User Space, Collections & Privacy Certificate**:
  ```bash
  cd web-nuxt && npx vitest run tests/user-collections-portfolio-craft.test.ts
  ```
- **R4 Civic Transparency & Editorial Charter**:
  ```bash
  cd web-nuxt && npx vitest run tests/civic-transparency-editorial-charter.test.ts
  ```

---

## 3. Systematic 4-Tier Test Coverage Matrix (71 Tests)

### Suite 1: `itinerary-expedition-journal-craft.test.ts` (R1 — 15 Tests)
| Tier | Test ID | Description / Invariant Tested | Status |
|---|---|---|:---:|
| **Tier 1** | F1-1 | Pocket Field Journal layout with narrative steps, chapter badges, and AEO plaque | **PASS** |
| **Tier 1** | F1-2 | Astronomical tide cycle integration & `<MekongWaterBadge>` on river transit | **PASS** |
| **Tier 1** | F1-3 | Cổ Chiên ferry crossing schedules (Phà An Bình 4h30–22h00, Phà Đình Khao 24/24) | **PASS** |
| **Tier 1** | F1-4 | Mang Thít terracotta heritage seal token (`--mangthit-500` / `#b95f38`) on milestones | **PASS** |
| **Tier 1** | F1-5 | Pocket field pass export modal with min 44x44px touch targets | **PASS** |
| **Tier 2** | B1-1 | Fallback gracefully to default step count when duration is zero or negative | **PASS** |
| **Tier 2** | B1-2 | River transit warning suppresses ferry alert on non-waterway routes | **PASS** |
| **Tier 2** | B1-3 | Read-only public sharing invariant: guest users cannot mutate planner state | **PASS** |
| **Tier 2** | B1-4 | WCAG 2.2 touch target compliance on mobile pass sheet action buttons | **PASS** |
| **Tier 3** | C1-1 | Lunar date & tidal state computation matches Southern Delta flood season | **PASS** |
| **Tier 3** | C1-2 | Responsive sheet collapse on mobile viewport (`max-width: 640px`) | **PASS** |
| **Tier 3** | C1-3 | Chapter timeline ordering and waypoint sequence continuity | **PASS** |
| **Tier 4** | J1-1 | Journey: Day-tripper plans crossing from Vĩnh Long to An Bình fruit orchards | **PASS** |
| **Tier 4** | J1-2 | Journey: Heritage enthusiast explores Mang Thít Red Kiln Canal route | **PASS** |
| **Tier 4** | J1-3 | Journey: Storm/Tide alert triggered and route advisory displays river safe alternatives | **PASS** |

### Suite 2: `local-directory-monocle-almanac.test.ts` (R2 Directory — 14 Tests)
| Tier | Test ID | Description / Invariant Tested | Status |
|---|---|---|:---:|
| **Tier 1** | F2-1 | Monocle gazetteer 4-pillar taxonomy (craft artisans, orchards, boat piers, administrative units) | **PASS** |
| **Tier 1** | F2-2 | Phone sanitization and `telHref` generation against Vietnamese carrier numbers | **PASS** |
| **Tier 1** | F2-3 | Official source badge `<SourceMark tier="official">` and `attributes.verifiedAt` | **PASS** |
| **Tier 1** | F2-4 | 24/7 emergency rescue priority card layout (`.dir-emergency-card--lead`) | **PASS** |
| **Tier 2** | B2-1 | Sanitizer handles invalid/malformed telephone strings gracefully | **PASS** |
| **Tier 2** | B2-2 | Emergency phone numbers dialable without carrier prefix mangling | **PASS** |
| **Tier 2** | B2-3 | Zero skeleton loading: uses calm inline states without jarring shift | **PASS** |
| **Tier 2** | B2-4 | WCAG 2.2 AAA text contrast against `--surface` and `--bg-alt` | **PASS** |
| **Tier 3** | C2-1 | WAI-ARIA tablist semantics and keyboard navigation (`ArrowLeft`, `ArrowRight`) | **PASS** |
| **Tier 3** | C2-2 | Responsive directory layout adapting from desktop 2-column to mobile single column | **PASS** |
| **Tier 3** | C2-3 | Search filtering across gazetteer categories and commune tags | **PASS** |
| **Tier 4** | J2-1 | Journey: Traveler experiences river emergency at night and reaches 24/7 hotline | **PASS** |
| **Tier 4** | J2-2 | Journey: Cultural researcher finds Mang Thít craft potter and verifies contact info | **PASS** |
| **Tier 4** | J2-3 | Journey: Commune administrative merger lookup across restructured wards | **PASS** |

### Suite 3: `contributor-ranking-honor-roll.test.ts` (R2 Contributor — 14 Tests)
| Tier | Test ID | Description / Invariant Tested | Status |
|---|---|---|:---:|
| **Tier 1** | F2-5 | Cultural leaderboard with 4 honor tiers (`Khởi hành`, `Thực địa`, `Nòng cốt`, `Đại sứ bản địa`) | **PASS** |
| **Tier 1** | F2-6 | Podium layout for top-3 contributors with gold, silver, bronze medals | **PASS** |
| **Tier 1** | F2-7 | Anti-inflation reputation metrics prioritizing field notes and verifications over raw volume | **PASS** |
| **Tier 1** | F2-8 | Contributor profile showcases field notes, badges, and verified contributions | **PASS** |
| **Tier 2** | B2-5 | Anti-slop copy: zero raw emoji salad in badges; uses semantic SVG `IconLine` | **PASS** |
| **Tier 2** | B2-6 | Bound handling for zero-contribution / newly registered contributors | **PASS** |
| **Tier 2** | B2-7 | Privacy guard: private profile robots noindex tag enforcement | **PASS** |
| **Tier 2** | B2-8 | WCAG 2.2 AAA contrast on leaderboard ranking badges and score pills | **PASS** |
| **Tier 3** | C2-4 | Level tier title mapping matches reputation score progression | **PASS** |
| **Tier 3** | C2-5 | Semantic `levelIcon` mapping matches tier badge SVG tokens (`sprout`, `users`, `award`, `trophy`) | **PASS** |
| **Tier 3** | C2-6 | Timeframe filtering (all-time, monthly, weekly) maintains ranking integrity | **PASS** |
| **Tier 4** | J2-4 | Journey: Local guide submits verified photo notes and reaches "Đại sứ bản địa" tier | **PASS** |
| **Tier 4** | J2-5 | Journey: Community member views top contributors and discovers heritage trails | **PASS** |
| **Tier 4** | J2-6 | Journey: Contributor sets profile to private and disappears from public leaderboard | **PASS** |

### Suite 4: `user-collections-portfolio-craft.test.ts` (R3 — 14 Tests)
| Tier | Test ID | Description / Invariant Tested | Status |
|---|---|---|:---:|
| **Tier 1** | F3-1 | Liquid Glass border tokens (`--border-liquid-glass`) and ambient card shadows on `da-luu.vue` | **PASS** |
| **Tier 1** | F3-2 | Asymmetric 1.35fr/1fr discovery grid and Mang Thít terracotta lead card in empty state | **PASS** |
| **Tier 1** | F3-3 | Purges obsolete district "Long Hồ" and establishes "Cù lao An Bình" terroir in suggestions | **PASS** |
| **Tier 1** | F3-4 | Decree 13/2023/ND-CP Privacy Certificate Badge on `tai-khoan.vue` (zero-telemetry assurance) | **PASS** |
| **Tier 1** | F3-5 | Calm editorial typography and non-distracting notifications on `thong-bao.vue` | **PASS** |
| **Tier 2** | B3-1 | Quiet loading state (`saved-quiet-loading`, `cp-quiet-loading`) without jarring skeleton shift | **PASS** |
| **Tier 2** | B3-2 | Adheres to design system semantic radii tokens (`--radius-sheet`, `--radius-surface`, `--radius-control`) | **PASS** |
| **Tier 2** | B3-3 | Strictly forbids raw untokenized hardcoded colors in user personal page styles | **PASS** |
| **Tier 2** | B3-4 | Enforces robots `noindex, nofollow` privacy guards on user data surfaces | **PASS** |
| **Tier 3** | C3-1 | Fully accessible WAI-ARIA tablist and tabpanel semantics on `da-luu.vue` | **PASS** |
| **Tier 3** | C3-2 | WCAG 2.2 touch target ergonomics ($\ge 44\times 44\text{px}$) on all user actions and controls | **PASS** |
| **Tier 3** | C3-3 | Semantic progress and meter roles for account completion and security scoring | **PASS** |
| **Tier 4** | J3-1 | Journey: Unauthenticated explorer arrives at collection, inspects terroir and auth prompt | **PASS** |
| **Tier 4** | J3-2 | Journey: Contributor conducts privacy compliance audit and verifies zero-telemetry governance | **PASS** |

### Suite 5: `civic-transparency-editorial-charter.test.ts` (R4 — 14 Tests)
| Tier | Test ID | Description / Invariant Tested | Status |
|---|---|---|:---:|
| **Tier 1** | F4-1 | Independent editorial charter and non-commercial conservation manifesto on `gioi-thieu.vue` | **PASS** |
| **Tier 1** | F4-2 | 3-tier fact-checking methodology across official, academic, and field witness sources | **PASS** |
| **Tier 1** | F4-3 | `<SourceMark tier="official">` masthead integration and `attributes.verifiedAt` transparency | **PASS** |
| **Tier 1** | F4-4 | Civic Correction Bridge Card and ombudsman accountability on `lien-he.vue` | **PASS** |
| **Tier 1** | F4-5 | Two-factor receipt lookup form with masked capability key on `yeu-cau/tra-cuu.vue` | **PASS** |
| **Tier 2** | B4-1 | Receipt lookup validation error feedback and disabled submit guards | **PASS** |
| **Tier 2** | B4-2 | Authentic editorial typography (Lora serif, drop-cap, pull-quote) and zero Times New Roman | **PASS** |
| **Tier 2** | B4-3 | Strictly forbids raw emoji salad and marketing promotional slop in civic content | **PASS** |
| **Tier 2** | B4-4 | Robots `noindex, nofollow` privacy guards on transactional intake pages | **PASS** |
| **Tier 3** | C4-1 | Capability secrets travel exclusively in POST body and never in browser URL history | **PASS** |
| **Tier 3** | C4-2 | Documents explicit ombudsman resolution SLAs on `lien-he.vue` (10d access, 15d consent withdrawal) | **PASS** |
| **Tier 3** | C4-3 | Input ergonomics (min-height $\ge 44\text{px}$) and semantic control radii on civic forms | **PASS** |
| **Tier 4** | J4-1 | Journey: Heritage researcher discovers discrepancy, inspects charter and files correction | **PASS** |
| **Tier 4** | J4-2 | Journey: Citizen checks ombudsman resolution status via two-factor receipt without leakage | **PASS** |

---

## 4. Verification & Quality Governance Checklist

- [x] **5 Comprehensive Test Suites authored and delivered in `web-nuxt/tests/`**.
- [x] **71 total tests (all passing, 100% green)**.
- [x] **Exceeds the $\ge 51$ test target threshold (+39% buffer)**.
- [x] **Zero hard checks violations** (`python scripts/checks/run_hard.py --all` passes with hard=0).
- [x] **Zero tri-region color debt** (`node scripts/check-tri-region-color-debt.mjs` passes with 0 violations).
- [x] **100% read-only integrity** maintained on `agent/data/vinhlong360.db` and `web/data.json`.
- [x] **Zero modifications** to application source code (authored tests exclusively).
