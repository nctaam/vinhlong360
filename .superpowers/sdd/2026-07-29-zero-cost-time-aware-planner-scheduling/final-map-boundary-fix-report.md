# Phase 2A final map-boundary fix report

## Scope and starting state

- Started from `3fcc4e691cd521138ef7ca32f3e8da21542559ca` on `codex/zero-cost-route-optimizer`.
- Scope was limited to `web-nuxt/composables/useNDAMap.ts`, the planner page map call seam, and a focused behavior test. No backend, API/schema, dependency, scheduler, or real-OSRM changes were made.

## Root cause

`tao-lich-trinh.vue` checked the planner lifecycle only after `await createNDAMap(...)`. The real `useNDAMap.createMap()` first awaited the MapLibre module and CSS imports, then constructed a Map and installed its error listener and controls. If the page unmounted during either import, the page cleanup still had no `mapInstance` to remove; the import continuation then created an unowned map and performed map setup after disposal. A second ownership gap existed immediately after construction: disposal could occur before the page assigned the returned map.

## TDD evidence

### RED before production edits

Command:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm test -- tests/use-nda-map-lifecycle.test.ts --pool=forks --maxWorkers=1
```

- Exit 1, both tests failed with behavior assertions (not transform, OOM, import, or harness errors).
- During delayed MapLibre import, the test expected `null` and zero construction/configuration effects but received a constructed `{ map, maplibregl }` result.
- When disposal was triggered by the fake Map constructor, the test expected teardown before listener/control setup but received a configured map result.

The test uses the real `useNDAMap.createMap()` implementation and delays the external MapLibre module boundary; it does not replace the composable or assert source text.

### GREEN after implementation

Focused map boundary test:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm test -- tests/use-nda-map-lifecycle.test.ts --pool=forks --maxWorkers=1
```

- Exit 0: 1 file passed, 2/2 tests passed.

Focused frontend matrix:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm test -- tests/use-nda-map-lifecycle.test.ts tests/itinerary-lifecycle.test.ts tests/itinerary-routing.test.ts tests/itinerary-optimization.test.ts tests/itinerary-time-schedule.test.ts tests/smoke.test.ts --pool=forks --maxWorkers=1
```

- Exit 0: 6 files passed, 136/136 tests passed.

Typecheck:

```text
NODE_OPTIONS=--max-old-space-size=8192 npm run typecheck
```

- Exit 0; Nuxt typecheck completed without diagnostics.

Diff check:

- `git diff --check` exited 0; only repository LF-to-CRLF working-copy notices were printed.

## Implementation and ownership reasoning

### `web-nuxt/composables/useNDAMap.ts`

- Added an optional `isActive` lifecycle predicate while preserving the non-lifecycle overload and behavior for existing map callers.
- Checked the predicate before import, after each dynamic import, before Map construction, after construction, before/after listener registration, and before/after each control construction/registration.
- If disposal is observed after construction, call `map.remove()` before returning `null`; no listener or control is installed for the disposed page.
- The recoverable-resource error listener also ignores events after lifecycle disposal, preventing fallback `setStyle()` work after teardown.

### `web-nuxt/pages/tao-lich-trinh.vue`

- Passes `isPlannerLifecycleActive` into the page-owned map creation call.
- Treats a disposed/null map result as an immediate no-op before assigning map ownership or installing page listeners.

### `web-nuxt/tests/use-nda-map-lifecycle.test.ts`

- Covers disposal during delayed MapLibre import: no Map construction, listener, control, or teardown side effects occur.
- Covers disposal triggered immediately after Map construction: the constructed Map is removed and no listener/control setup occurs.

## Commit

- `3175e505` - `fix: guard map creation across planner disposal`

## Self-review and concerns

- Active callers without `isActive` retain the existing return shape and callback/setup order; typecheck and routing/optimization/schedule/smoke suites remain green.
- Page unmount still removes any map that has already been assigned; the new seam closes the pre-ownership window and explicitly removes an unowned constructed Map.
- No real OSRM request was made.
- Concern: the full-page Nuxt suites require an 8 GB Node heap and one fork in this repository; this is a test-runner resource constraint, not a production behavior concern.
