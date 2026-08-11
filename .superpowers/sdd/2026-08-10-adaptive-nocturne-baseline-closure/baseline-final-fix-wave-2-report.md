# Baseline final planner fix wave 2 report

> STATUS: done

## Outcome

The planner now preserves the active server plan id and comparison revision in its local draft contract, restores that identity across remounts, and continues revision-safe saves through PUT without duplicating a plan. An unresolved revision conflict now disables publish for the active plan and is also enforced by a fail-closed handler guard, while unrelated saved plans remain publishable.

## Root-cause confirmation

1. `publishPlan()` previously accepted a publish response for the active conflicted plan, advanced `baseServerRevision`, and cleared `plannerRevisionConflict` without requiring Keep local, Use server, or manual comparison.
2. Planner draft snapshots previously omitted the active server plan id/base revision. Keep local survived only in memory; after remount the next authenticated save fell through to `POST /api/my-plans` and duplicated the server plan.
3. Final requirement review found that deleting the currently loaded server plan cleared identity only in memory. Without immediately persisting that transition, remount restored the deleted id/revision and attempted a stale PUT.

## Files changed

- `web-nuxt/composables/useItineraryOptimization.ts`
  - Adds optional `serverPlanId` and `serverRevision` to `PlannerDraftSnapshot`.
  - Serializes the pair only for server-source drafts with a trimmed non-empty id and positive integer revision.
  - Parses the pair only when both fields are valid, while retaining backward compatibility for legacy and malformed snapshots by omitting identity.
- `web-nuxt/pages/tao-lich-trinh.vue`
  - Persists and restores the active server comparison identity.
  - Fails closed for legacy/incomplete server drafts while revision-safe saving is enabled.
  - Disables and accessibly explains active-plan publish during an unresolved conflict, with a handler-level no-op guard.
  - Persists revisions returned by publish and clears persisted identity when the active server plan is deleted.
- `web-nuxt/tests/planner-draft-contract.test.ts`
  - Covers valid identity round-trip, local-source omission, malformed/partial pair omission, and legacy compatibility.
- `web-nuxt/tests/itinerary-lifecycle.test.ts`
  - Covers Keep-local remount/PUT, conflict-blocked publish, publish-revision remount, legacy fail-closed save, and delete/remount identity clearing through the mounted planner page.

## TDD RED evidence

Initial focused command before production edits:

```powershell
npm test -- --run tests/planner-draft-contract.test.ts tests/itinerary-lifecycle.test.ts -t "server identity contract|across remount|blocks active-plan publish|after remount|legacy server draft"
```

Result: exit `1`; 5 tests failed. The valid pair was absent from serialized snapshots, Keep-local and publish remounts fell through to POST, the active publish control remained enabled, and a legacy server draft posted a duplicate.

Additional delete-transition RED command found during final requirement review:

```powershell
npm test -- --run tests/itinerary-lifecycle.test.ts -t "drops deleted active-plan identity"
```

Result: exit `1`; after delete/remount the save called `PUT /api/my-plans/server-plan` with `expected_revision: 4` instead of creating a new plan.

## GREEN verification

Final fail-fast verification command:

```powershell
npm --prefix web-nuxt test -- --run tests/planner-draft-contract.test.ts tests/itinerary-lifecycle.test.ts tests/planner-friction.test.ts tests/planner-optimization-preview.test.ts tests/itinerary-routing.test.ts tests/itinerary-time-schedule.test.ts tests/itinerary-optimization.test.ts
npm --prefix web-nuxt test -- --run tests/smoke.test.ts -t "planner"
npm --prefix web-nuxt run typecheck
git diff --check
git diff cad1b7e7 --check
```

Results:

- Directly affected planner suite: exit `0`; 7 files passed, 93 tests passed.
- Planner smoke slice: exit `0`; 4 tests passed, 104 skipped.
- Nuxt typecheck: exit `0`.
- Both diff checks: exit `0`; only normal Windows LF-to-CRLF working-copy warnings.
- Commit hook: hard checks clean (`hard=0`, ratchet did not increase).

## Design boundaries

- Revision-safe behavior remains behind the existing `public_optimizer_v1`/optimizer-enabled boundary.
- Backend request and response shapes are unchanged.
- Existing create, merge, auth, privacy, navigation, sharing, and responsive Nocturne behavior is preserved.
- Invalid or legacy server identity fails closed rather than guessing an id/revision or silently creating a duplicate.

## Commit

Implementation commit: `3fd0a54de970f6b8f084d720fe5377b693415b85` (`fix(planner): preserve revision-safe draft identity`).

## Concerns

None. The report is committed separately so it can contain the exact implementation commit hash.
