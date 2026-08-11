# Baseline final planner fix report

> STATUS: done

## Outcome

The mounted planner page now consumes the backend revision contract. Loaded server plans save through revision-safe PUT while the existing `public_optimizer_v1` planner rollout is enabled, and the disabled rollout preserves the create-only POST rollback path. Exact backend 409 snapshots now produce an accessible recovery comparison without mutating the local draft.

## Files changed

- `web-nuxt/pages/tao-lich-trinh.vue`
  - Retains server `revision` and `updatedAt`, plus active server plan identity/base revision.
  - Uses literal `PUT /api/my-plans/{id}` with `expected_revision` for active server plans under the existing planner rollout.
  - Consumes successful `{ plan: PlanSnapshot }` responses without adding a duplicate saved row.
  - Parses only `code: "plan_revision_conflict"` plus `current`, from either `response._data` or `data`.
  - Renders server title, revision, updated freshness, title comparison, and stop-level differences in a focused responsive recovery surface.
  - Implements keep-local, use-server, and manual-compare behavior; retains publish revisions for later PUTs.
  - Clears server identity when a local plan is loaded or the active draft is explicitly reset.
- `web-nuxt/tests/itinerary-lifecycle.test.ts`
  - Replaces the obsolete synthetic `serverPlan` conflict expectation with mounted-page PUT/409 lifecycle coverage.
  - Covers successful update/no duplication, exact conflict preservation/rendering, keep-local retry, use-server, manual compare, publish revision, disabled rollout, reset-to-new-plan, and local-plan identity clearing.

## TDD RED evidence

Initial command, before production edits:

```powershell
npm test -- --run tests/itinerary-lifecycle.test.ts -t "updates the loaded server plan|preserves the local draft and renders|keeps the local draft and retries|uses the returned server snapshot|keeps both snapshots unchanged|retains the revision returned by publish|rollout-disabled rollback"
```

Expected result: exit `1`; 6 failed, 1 passed, 14 skipped. The enabled-rollout cases showed authenticated edits still calling `POST /api/my-plans` instead of `PUT /api/my-plans/server-plan`, and the conflict cases could not find `[data-planner-conflict-diff]`. The disabled-rollout create-only test passed, proving the rollback baseline.

Additional identity RED commands:

```powershell
npm test -- --run tests/itinerary-lifecycle.test.ts -t "creates a new server plan after the active server draft is explicitly cleared"
npm test -- --run tests/itinerary-lifecycle.test.ts -t "clears the active server identity when a local saved plan is loaded"
```

Each exited `1` because the next save incorrectly called `PUT /api/my-plans/server-plan` with `expected_revision: 4` instead of creating through POST.

## GREEN verification

Final combined verification command:

```powershell
npm --prefix web-nuxt test -- --run tests/itinerary-lifecycle.test.ts tests/planner-friction.test.ts tests/planner-optimization-preview.test.ts tests/itinerary-routing.test.ts tests/itinerary-time-schedule.test.ts tests/itinerary-optimization.test.ts
npm --prefix web-nuxt test -- --run tests/smoke.test.ts -t "planner"
npm --prefix web-nuxt run typecheck
git diff --check
```

Results:

- Planner-focused Vitest: exit `0`; 6 files passed, 81 tests passed.
- Planner smoke slice: exit `0`; 4 tests passed, 104 skipped.
- Nuxt typecheck: exit `0`.
- `git diff --check`: exit `0`; only normal Windows LF-to-CRLF working-copy warnings.
- Commit hook: hard checks clean (`hard=0`, ratchet did not increase).

## Design decisions

- The existing planner capability rollout is `public_optimizer_v1`, already consumed by the page through `capabilityMode('optimizer')`; revision-safe PUT follows that same enabled/disabled boundary.
- New plans and reset/local plans remain POST-only. Merge, delete, auth headers, privacy, local draft persistence, navigation, and publish request semantics remain unchanged.
- Conflict recovery stores the complete returned server snapshot. Keep-local updates only the comparison base/list entry; use-server replaces the editable draft; manual compare only refocuses the open comparison.
- Stop differences are occurrence-aware so duplicate entity IDs are compared by occurrence and position rather than collapsed by ID.
- Publish supports the current backend `{ is_public, revision }` response and an additive full `plan` snapshot if supplied later.

## Commit

Implementation commit: `cd84818d` (`fix: consume planner revision conflicts`).

## Concerns

None. The final report is committed separately so it can contain the exact implementation commit hash.
