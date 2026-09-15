# Project: Vinh Long 360 Unified Anti-Slop Editorial Design System

> STATUS: active (2026-09-15) — Hồ sơ kiến trúc dự án và cấu trúc thư mục chuẩn hóa.

## Architecture
- **Framework**: Nuxt 3 (SSR + Nitro node-server), Vue 3 SFCs.
- **Design Tokens**: Single Source of Truth in `web-nuxt/app/assets/css/variables.css`.
- **CSS Architecture**: Vanilla CSS tokens & utility layers (no Tailwind, zero CDN dependencies).
- **Typography**: Editorial Serif `Lora` + Vietnamese-optimized Sans `Be Vietnam Pro` (0 Times New Roman).
- **Palette**: Terroir Tri-Region (Mang Thit Terracotta `#b95f38`, Co Chien Alluvium `#c99446`, Cu Lao Green `#1b8844`, Co Chien River `#006798`, Ben Cloud `#faf9f7`, Nocturne `#12100e`).
- **Semantic Radius**: `--radius-control` (8px), `--radius-surface` (12px), `--radius-sheet` (20px), `--radius-full` (9999px).
- **Elevation & Depth**: Mekong charcoal ink shadows (`--shadow-xs..xl`), Liquid Glass border (`oklch(100% 0 0 / 0.12)`).
- **Cloud Design System**: Google Stitch Project `14916181929760067680`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Multi-Perspective Critique (R1) | Evaluate current UI against Rijksmuseum, NatGeo, Visit Oslo, Monocle, and Stitch | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Unified Token Foundation (R2) | Consolidate variables.css, Tam Vùng palette, liquid glass, charcoal ink shadows | M1 | ORIGINAL_REQUEST §R2 |
| 3 | Purge Purple SaaS Gradients (R2) | Eliminate `#5B6CC4` from `--cat-accommodation` and replace with River Co Chien | M1 | Survey Report UI |
| 4 | Typography & Zero Times New Roman (R2) | Enforce Lora + Be Vietnam Pro, zero Times New Roman fallbacks | M1 | ORIGINAL_REQUEST §R2 |
| 5 | Purge AI Slop Sparkles (R2 & R3) | Replace 17 `sparkles` icons across 11 files with grounded cultural vector icons | M2 | Survey Report UI |
| 6 | Shell Header & Nav Touch Targets (R3 & R5) | Ensure theme button (26px), catalog button (26px), nav links (34px), auth btn (36px) have >= 44x44px hit-areas | M2 | Survey Report UI |
| 7 | Shell Frosted Glass & Dock (R3) | Refined Frosted Glass backdrop-filter, thumb-zone mobile dock ergonomics | M2 | ORIGINAL_REQUEST §R3 |
| 8 | Catalog & Filters Ergonomics (R3) | Tactile pills >= 44px, macro-rhythm card balance, eliminate generic grids | M3 | ORIGINAL_REQUEST §R3 |
| 9 | Terroir Interactive Map (R3) | One-hand controls, high-contrast sunlight mode, accurate GPS coordinates | M3 | ORIGINAL_REQUEST §R3 |
| 10 | National OCOP Gold Book (R3) | Guilloche security watermark, Mang Thit wax seal, ergonomic star ranking filters | M3 | ORIGINAL_REQUEST §R3 |
| 11 | Article & Travelogue Detail (R3) | Lora pull-quotes, golden-bordered AEO Answer Plaque, SourceMark citations | M3 | ORIGINAL_REQUEST §R3 |
| 12 | CLAUDE.md §1.7 Unavailable Policy (R5) | Graceful collapse on missing data, zero fake numbers, zero empty frames | M3 | CLAUDE.md §1.7 |
| 13 | Author DESIGN.md & Sync to Stitch (R4) | Author comprehensive DESIGN.md and upload to Google Stitch via MCP | M4 | ORIGINAL_REQUEST §R4 |
| 14 | Sync Stitch Design System Tokens (R4) | Update Stitch DS v3 to Lora + Be Vietnam Pro, Tam Vùng colors, remove slop | M4 | ORIGINAL_REQUEST §R4 |
| 15 | Full Test Suite Verification (R5) | 165+ Vitest tests passing (home 79, color contract 78, specialized 8) | M5 | ORIGINAL_REQUEST §R5 |
| 16 | Launch Safety, Typecheck, Build (R5) | run_hard.py (0 violations), npm run typecheck (0 errors), npm run build (clean) | M5 | ORIGINAL_REQUEST §R5 |
| 17 | Multi-Agent Review & Challenge (R5) | 2 Reviewers APPROVE, 2 Challengers APPROVE | M5 | Orchestrator Gate |
| 18 | Forensic Integrity Audit (R5) | teamwork_preview_auditor CLEAN verdict (Zero slop, zero fakes, zero mocks) | M5 | Orchestrator Gate |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Unified Design Tokens & Foundation | Update variables.css: Purge purple SaaS gradient, add liquid glass token, convert shadows to charcoal ink, clean dead tokens | none | DONE |
| M2 | Shell, Navigation & Sparkle Purge | Purge all 17 sparkles icons across 11 files, fix Shell touch targets >= 44px | M1 | DONE |
| M3 | Subsystems Refinement & Craft | Refine Catalog chips, Terroir Map, OCOP Gold Book, Article Detail & §1.7 checks | M2 | DONE |
| M4 | Google Stitch MCP Cloud Sync | Author DESIGN.md, upload to Stitch Project 14916181929760067680, sync tokens & screens | M1, M2, M3 | DONE |
| M5 | Comprehensive Verification & Forensic Gate | Run all 165+ tests, WCAG 2.2 AAA, typecheck, build, 2 Reviewers, 2 Challengers, 1 Auditor | M4 | DONE |

## Code Layout
- `web-nuxt/app/assets/css/variables.css`: Design tokens, colors, typography, elevation, radius.
- `web-nuxt/app/assets/css/shell.css`: Header, navigation, footer, mobile dock.
- `web-nuxt/app/assets/css/components.css`: Buttons, cards, pills, drawers, docks.
- `web-nuxt/app/components/`: Vue components for Shell, Catalog, Map, OCOP, Article Detail.
- `web-nuxt/DESIGN.md`: Single source of truth design constitution.
- `web-nuxt/tests/`: Vitest test suites (home, tri-region color contract, specialized tests).

## Interface Contracts
### Variables & Component Tokens
- `--border-liquid-glass`: `oklch(100% 0 0 / 0.12)`
- `--cat-accommodation`: `linear-gradient(135deg, var(--river-700), var(--river-600))`
- `--cat-accommodation-accent`: `var(--river-600)`
- `--shadow-xs..xl`: `rgba(var(--mekong-ink-rgb, 8, 26, 22), ...)`
- Touch targets: Minimum 44x44px bounding hit area on all interactive controls.
- Iconography: Semantic line icons (`compass`, `bulb`, `book`, `shield`), zero sparkles.
