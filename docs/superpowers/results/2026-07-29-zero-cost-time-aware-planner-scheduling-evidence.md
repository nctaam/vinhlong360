# Phase 2A time-aware planner scheduling evidence

> STATUS: done — focused Phase 2A closure evidence captured locally on 2026-07-30. This document does not claim a full repository backend-suite pass, production deployment, migration, or Phase 2B/3-6 completion.

## Scope and contract decisions

- Phase 2A covers the feature-flagged manual planner only. Phase 2B generator adoption and Phases 3-6 remain pending and require separate plans.
- The existing order-only request/response remains valid. Schedule fields are optional, and a runtime scheduling failure returns a complete route-only response with `schedule-fallback-order-only`; no partial schedule is returned.
- First-hop travel is counted. The public matrix fixture places `early` at minute `490`, not `480`.
- Public placement output uses `end_visit_minute`. The nested schedule IDs must be an exact permutation of outer stop IDs with matching fixed first/last endpoints.
- `requested_time` is a hard window and intersects trusted opening-hours windows. Invalid request-time text returns HTTP 422.
- The enabled planner budget is at most one Table request per optimization fingerprint, one initial route request, one U-turn retry, and zero background OSRM requests. Missing Table data is handled only by the local Haversine fallback.
- `NUXT_PUBLIC_ITINERARY_SCHEDULE_V2` defaults off and enables only for the exact value `1`. Schedule metadata is ephemeral `WeakMap` state; the saved `PlanStop` schema is unchanged.
- The approved frontend coverage imports and executes real config and planner helpers. Earlier source-text and tautological serialization proposals were replaced by behavior tests.

## Pre-documentation absence check

Command:

```powershell
rg -n "duration_matrix_minutes|itineraryScheduleV2" docs/api-contract.md
```

Result: exit 1 with no output, as expected before the API contract update.

The worktree was clean at `85e10a8490b530e669a7b7732f2f3b522ffb590a` before verification and remained clean after the production build.

## Fresh focused verification before documentation edits

### Backend focused matrix

Command:

```powershell
python -m pytest agent/tests/test_itinerary_schedule.py agent/tests/test_public_itinerary_optimizer_api.py agent/tests/test_itinerary_optimizer.py agent/tests/test_cov_itinerary_gen.py -q
```

Result: exit 0; `189 passed, 1 warning in 6.27s` (command-runner wall time `8.9s`).

The warning was recorded, not suppressed:

```text
C:\Python314\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

### Frontend focused matrix

Command from `web-nuxt/`:

```powershell
npm test -- tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts tests/itinerary-time-schedule.test.ts tests/smoke.test.ts
```

Result: exit 0; `4 passed (4)` files and `124 passed (124)` tests. Vitest duration was `20.05s` (`transform 16.06s`, `setup 1.13s`, `import 1.26s`, `tests 16.85s`, `environment 2.04s`); command-runner wall time was `33.4s`.

### Typecheck

Command from `web-nuxt/`:

```powershell
npm run typecheck
```

Result: exit 0; `nuxt typecheck` completed without diagnostics. Command-runner wall time was `43.5s`.

### Production build

Command from `web-nuxt/`:

```powershell
npm run build
```

Result: exit 0 in command-runner wall time `210.5s`; Nuxt `4.4.8`, Nitro `2.13.4`, Vite `7.3.5`, and Vue `3.5.35`; `752 modules transformed`; Nitro reported `Build complete!`; the launch-readiness manifest was generated for `85e10a8490b530e669a7b7732f2f3b522ffb590a`.

The build emitted the existing warnings:

- `[plugin nuxt:module-preload-polyfill]` transformed files without generating a matching sourcemap.
- Some minified chunks exceeded `500 kB`.
- Node emitted `DEP0155` for the deprecated trailing-slash `"./"` package export mapping used by the Nuxt/Vue toolchain.

None caused build failure.

## Behavior evidence inside the focused matrix

- `fetches one cached Table and reuses one envelope and matrix through the bounded retry` forces a U-turn retry and asserts `tableCalls === 1`, two bounded optimizer attempts, identity reuse of the schedule envelope, and identity reuse of `duration_matrix_minutes`.
- `keeps the route-only path free of Table calls and schedule payloads` proves feature-flag-off behavior performs zero Table calls and sends no schedule envelope.
- Backend fallback tests cover local Haversine matrix use, matrix-builder and scheduler runtime failures returning route-only output with `schedule-fallback-order-only`, preservation of the legacy no-route HTTP 409, and impossible required schedules returning HTTP 409 without partial placements.
- API behavior tests assert the first scheduled intermediate placement begins at minute `490`, expose `end_visit_minute`, reject invalid `requested_time` with HTTP 422, enforce hard-window intersection, and reject nested endpoint/order-reference drift.
- Frontend behavior tests assert the saved-plan serializer emits only the original `PlanStop` keys and that `WeakMap` placements remain attached to original stop objects across reorder without persistence.

## Limitations and branch-level debt

- The full repository backend suite was deliberately not run in this closure task. Earlier Phase 2A task reports record a known branch-level history of full-suite runs not completing within roughly 600-1800 seconds without a reported failure. Therefore this evidence claims only the exact focused matrix above.
- The focused matrix does not deploy, call a real network service, run migrations, alter dependencies, or enable the default-off feature in production.
- Phase 2B generator adoption is not complete: the generator still has its fixed 30-minute travel assumption and no generator-specific meal/rest anchors.
- Phases 3-6 remain pending.

## Final scope inspection

`git diff --check` exited 0 with no whitespace error. Git printed only its configured working-copy notices that LF will be replaced by CRLF for the two existing modified Markdown files.

`git status --short` showed exactly the intended Phase 2A documentation closure files:

```text
 M docs/api-contract.md
 M docs/superpowers/specs/2026-07-29-zero-cost-itinerary-intelligence-roadmap-design.md
?? docs/superpowers/results/2026-07-29-zero-cost-time-aware-planner-scheduling-evidence.md
```

`git log -8 --oneline` before the documentation commit was:

```text
85e10a84 test: cover planner schedule invalidation paths
33753bad fix: invalidate stale planner schedules
eca28c57 feat: add feature-flagged time-aware planner scheduling
2e1f3fea feat: add cached zero-cost route time matrix
689e58be fix: pin itinerary endpoints and add schedule fallback
86a7aa5c feat: expose optional time-aware itinerary scheduling
9734d6dc fix: count first-hop travel in schedules
14abbf86 feat: schedule itinerary stops within time windows
```
