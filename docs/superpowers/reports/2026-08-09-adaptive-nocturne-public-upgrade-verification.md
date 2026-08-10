# Adaptive Nocturne public upgrade verification

> STATUS: local verification complete; rollout remains operator-controlled

Date: 2026-08-10 (Asia/Bangkok)
Base revision: `ffec3a8acc3a7be3459ac36372a4b749a12b6405`
Status: local rollout closure gates passed; no deployment or production setting was changed.

## Verification baseline

- Public route families: `/`, `/du-lich`, `/tim-kiem`, `/ban-do`, `/dia-diem/{id}`, `/tao-lich-trinh`.
- Deterministic state matrix: 6 routes x 9 states = 54 unique contracts covering loading, ready, partial, stale, empty, error, offline, confirmed 404 and retryable 5xx.
- Visual matrix: 6 routes x 2 themes x 5 widths = 60 ready-state PNGs at 375, 390, 768, 1024 and 1440px.
- Additional truthful-backend evidence: 2 homepage PNGs showing the retry state when the local backend is unavailable.
- Browser journey: homepage -> search -> map -> list -> detail -> planner -> back to detail -> back to search -> map renderer failure -> retryable detail 5xx.

## Feature flags and telemetry

The five independent public capability switches remain fail-closed by default:

| Capability | CMS key | Verified default |
| --- | --- | --- |
| Personalization | `public_personalization_v1` | `false` / deterministic |
| Contextual recommendation | `public_recommendation_v1` | `false` / deterministic |
| Search expansion | `public_search_expansion_v1` | `false` / deterministic |
| Planner optimizer | `public_optimizer_v1` | `false` / deterministic |
| Proactive notices | `public_proactive_notices_v1` | `false` / deterministic |

Missing, failed or malformed CMS settings keep all five capabilities deterministic. The flag-off path preserves search, detail and planner rather than hiding a core task.

Public telemetry is also opt-in: `NUXT_PUBLIC_TELEMETRY_ENABLED` must equal `1`; otherwise transport is disabled. The default endpoint is the same-origin `/feedback/public-telemetry`. The allowlist accepts only closed route, viewport, network, theme, area, outcome/harm and performance dimensions; raw coordinates, phone numbers, free-form query text and arbitrary keys are rejected. No live production RUM baseline is claimed by this local run because production telemetry and the external backend were not enabled.

## Browser and screenshot evidence

Fresh candidate directory: `%TEMP%\vinhlong360-task10-fix-round1-visual`

Separate exact-comparison baseline: `%TEMP%\vinhlong360-task10-fix-round1-exact-baseline`

- Fresh ready captures: 60/60, named `{route}__{theme}__{width}px__ready.png`, plus a 60-entry `visual-manifest.json` for run `fix-round1-20260810`.
- Every manifest entry binds the route/path, page recipe, selected theme, viewport, ready selector, rendered content identity, schema revision and PNG SHA-256.
- The separate baseline directory contains the same 60 reviewed candidates. `authoritative-exact-sha256` mode compared every scenario/content/pixel digest and passed with `0 pending of 60`.
- The two inherited backend-unavailable homepage captures remain in `%TEMP%\vinhlong360-task10-visual`; they are not counted as ready baselines.
- In-app Browser evidence: homepage at 1440x900 Nocturne and 390x844 Parchment had the correct URL/title, meaningful DOM, no framework overlay, no relevant console errors, no horizontal overflow and no action-dock overlap. The unavailable backend rendered an honest retry state.
- The search map toggle was exercised through the visible `Bản đồ` control: `data-panel` changed from `list` to `map`, `aria-pressed` became `true`, and console errors remained empty. The headless runner separately verifies the same observed postcondition and uses a bounded same-element click fallback only when Chromium drops a raw pointer event.

Visual resume no longer trusts filenames. It reuses an artifact only when the run ID, schema/scenario identity, content identity, manifest entry and current PNG digest all match. The final validation run reported `0 pending of 60`.

## Recovery and safety evidence

- Search state restored exactly after planner back-navigation: `/tim-kiem?q=g%E1%BB%91m&intent=place&area=vinh-long&type=craft_village`.
- Browser console errors: 0.
- Detail and planner fixed-action overlap: 0px.
- Map failure: WebGL was disabled for the map document so the actual renderer boundary failed while fixture results stayed available; `[data-map-fallback][data-map-state="error"]` was visible.
- Retryable detail 5xx: the retry UI was visible and the confirmed-404 message was absent.
- False-404 contract: confirmed 404 is accepted only for detail and requires a back-to-results action; retryable 5xx must expose retry and must not become 404.
- Legacy route sweep: all 20 routes passed their route contracts, same-origin asset reprobes and Runtime/Log/Network checks; runtime issue count was 0.
- Accessibility: Nocturne/Parchment, desktop/mobile, reduced-motion, forced-colors and native 200% zoom evidence was inherited from the completed Task 9 base. Task 10 reran the full frontend suite, exact color checker contracts and hard ratchets after reconciling the protected media plate/focus halo assertions.

## Fix round 1

- The state matrix now mounts the real `PageState` under every required route context for all 54 route/state rows. Detail confirmed-404 and retryable-503 fixtures also execute the production `resolveDetailFetchError` path.
- Visual capture now rejects route, recipe, hydration, theme, loading/error/recovery and ready-content mismatches before taking a screenshot. Freshness and exact-baseline behavior are executable rather than prose-only.
- The legacy 20-route sweep is restored alongside the 10-step journey, including route contracts, same-origin Nuxt asset reprobes, console/exception capture and `Log.entryAdded`/`Network.responseReceived` classification.
- The rollback transformation is executable in `scripts/ops/disable_public_feature_flags.ps1` and tested with a realistic `ConvertFrom-Json` `PSCustomObject`; unrelated flags are preserved while all five public capability flags become `false`.
- Managed smoke runs use an explicit loopback port, bounded startup, process-tree cleanup and an optional production-preview mode. The user-owned preview on port 4173 was never stopped or modified.

## Kill switch and rollback

Preferred operator path: `/admin/cai-dat/tinh-nang` -> group `Rollout công khai` -> turn off all five public capability switches -> `Lưu thay đổi`.

Equivalent API path: `PUT /admin-api/site-settings/features.flags`. To preserve unrelated flags, merge the current object before writing:

```powershell
$origin = 'https://vinhlong360.vn'
$headers = @{ Authorization = "Bearer $adminToken" }
$settings = Invoke-RestMethod -Method Get -Uri "$origin/admin-api/site-settings/features" -Headers $headers
$flags = @{}
(($settings.settings | Where-Object key -eq 'features.flags').value).PSObject.Properties |
  ForEach-Object { $flags[$_.Name] = $_.Value }
@('public_personalization_v1','public_recommendation_v1','public_search_expansion_v1','public_optimizer_v1','public_proactive_notices_v1') | ForEach-Object { $flags[$_] = $false }
Invoke-RestMethod -Method Put -Uri "$origin/admin-api/site-settings/features.flags" -Headers ($headers + @{ 'Content-Type' = 'application/json' }) -Body (@{ value = $flags } | ConvertTo-Json -Depth 6)
```

This rollback returns adaptive capabilities to deterministic composition without deleting planner drafts, saved items, search state or user data. If a code rollback is required, revert the Task 10 verification commit; do not revert the underlying Task 1-9 data contracts unless a separate migration/rollback decision authorizes it.

## Final gates

| Gate | Result |
| --- | --- |
| `npm --prefix web-nuxt run typecheck` | PASS |
| `npm --prefix web-nuxt test -- --maxWorkers=1` | PASS, 111 files / 1830 tests |
| `npm --prefix web-nuxt run build` | PASS; readiness manifest generated for `faac1b4f78f865061ba3d18c225467d74e79ebc7` |
| `python scripts/checks/run_hard.py --all` | PASS, hard=0; `fe_colors` 292<310 and `fe_emoji` 641<671 |
| Fresh production-preview smoke | PASS, 20/20 legacy routes, all 10 journey steps, runtime issues 0, 60/60 manifest-bound PNGs |
| Exact baseline comparison | PASS, `authoritative-exact-sha256`, 0 pending / 60 matched |

Known non-blocking build output: Nuxt reported the existing module-preload sourcemap warning, chunk-size advisory and a dependency trailing-slash deprecation warning. No assertion or gate was weakened to suppress them.
