# Phase 2A final page-lifecycle fix report

## Scope and starting state

- Started from `11e615b09dfdf0d09f2476218c60b2467b60eb25` on `codex/zero-cost-route-optimizer`.
- The only inherited worktree change was the untracked `web-nuxt/tests/itinerary-lifecycle.test.ts`; no production source had been edited.
- Scope stayed limited to the planner page lifecycle, the page-used commit seam, and its behavior test. No backend, API/schema, dependency, feature-flag, request-budget, or real OSRM changes were made.

## Root cause

`autoRouteScheduler.dispose()` correctly neutralized scheduler requests, queued timers, and resume calls, but it did not invalidate the already-running `optimizePlanRoute()` continuation. A planner promise settling after page unmount could therefore enter the commit callbacks, mutate placement/order/route/UI refs, invoke map work, publish an error toast, and execute `finally` cleanup. The commit sequence also had no lifecycle checkpoint before each callback or after its awaited map boundary.

## TDD and regression evidence

### Behavior RED before production edits

Command:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm test -- tests/itinerary-lifecycle.test.ts --pool=forks --maxWorkers=1
```

The inherited full-page test mounted successfully with the larger heap and one fork; this avoided the interrupted agent's default-heap OOM without replacing the page with a source-text assertion.

- Exit 1, `1` file failed, `2/2` tests failed.
- Late resolve after unmount changed zero-effect expectations to `applyPlacements=1`, `mergeStops=1`, and `commitMap=1`.
- Late reject after unmount changed zero-effect expectations to `toast=1` and `resumeRoute=1`.
- These were assertion failures on the missing lifecycle behavior, not import, transform, network, or harness errors.

### Awaited-boundary and announcement RED checks

- The awaited commit/map test pauses the real page-used `commitPlannerOptimizationResult()` callback, unmounts the page, releases the boundary, and compares all tracked effects and planner state to the unmount snapshot.
- After strengthening the async settle helper, a deliberate lifecycle-predicate mutation reproduced the missing guard: the focused awaited-boundary test exited 1 because `discardPending` changed `0 -> 1` and `resumeRoute` changed `0 -> 1`. Restoring the predicate returned the test to GREEN.
- Before adding the final post-message checkpoints, the message-driven disposal test exited 1 because `stopAnnounce` changed after the unmount snapshot (`"Da them End. 3 diem." -> ""` in the rendered test state). The minimal checkpoints made it GREEN.

## Implementation

### `web-nuxt/composables/useItineraryOptimization.ts`

- Added an optional `isActive` predicate to the existing commit callbacks.
- `commitPlannerOptimizationResult()` now checks lifecycle activity before every placement/reorder/route/map callback and again after the awaited map callback.
- Calls without the predicate retain the existing active behavior and callback order.

### `web-nuxt/pages/tao-lich-trinh.vue`

- Added a page-instance lifecycle flag and set it inactive at the start of `onBeforeUnmount()`, before scheduler disposal and map cleanup.
- Added guards after planner resolution, throughout commit completion, before catch publication, inside `finally`, and around the post-message `nextTick()` boundary.
- Added map checkpoints at entry and after `createNDAMap()` and map-load awaits so an in-flight map continuation cannot resume page work after disposal.
- Preserved scheduler token provenance, discard/resume behavior while active, stale-result behavior, debounce, route/Table budgets, default-off scheduling, manual controls, and saved-plan serialization.

### `web-nuxt/tests/itinerary-lifecycle.test.ts`

- Mounts the real planner page and exercises the real commit seam and scheduler implementation while mocking only external/page-environment boundaries.
- Covers late resolve, late reject, disposal during the awaited commit/map boundary, and disposal at the announcement `nextTick()` checkpoint.
- Asserts unchanged state plus zero new placement/reorder/map/scheduler/toast effects after the unmount snapshot.

## Verification

Final pre-report frontend matrix from `web-nuxt/`:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm test -- tests/itinerary-lifecycle.test.ts tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts tests/itinerary-time-schedule.test.ts tests/smoke.test.ts --pool=forks --maxWorkers=1
```

- Exit 0: `5` files passed, `134/134` tests passed.
- The existing active commit test still verifies `placements -> reorder -> route -> map` callback order.

Typecheck:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm run typecheck
```

- Exit 0; `nuxt typecheck` completed without diagnostics.

Diff checks:

- `git diff --check` and staged diff checks exited 0; only repository LF-to-CRLF working-copy notices were printed.
- Commit hook reported `run_hard: sach (hard=0, ratchet khong tang)`.

## Self-review

- Lifecycle inactivity is established before scheduler/map cleanup.
- Post-unmount resolve and reject paths do not change page refs or invoke placement, reorder, map, toast, discard, request, or resume callbacks.
- Disposal during the awaited commit boundary allows already-completed active callbacks to stand but blocks every remaining callback and post-commit UI cleanup.
- Active callers without `isActive` retain the prior commit contract; the focused routing/optimization/scheduling/smoke suites remain green.
- No real OSRM request was made and no unrelated files or contracts changed.

## Commits

- `494b769694cabe618608de06358d78ceb8007f23` - `fix: stop planner continuation after unmount`
- The report and strengthened async-settle test helper are recorded in the follow-up reporting commit.

## Concerns

- The full-page Nuxt lifecycle test is stable with an 8 GB Node heap and one fork; the default heap previously OOMed during transform. This is a test-runner resource constraint, not a production behavior concern.
