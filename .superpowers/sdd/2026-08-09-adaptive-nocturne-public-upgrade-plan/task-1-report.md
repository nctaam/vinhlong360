# Task 1 implementation report

## Files changed

- `web-nuxt/types/publicExperience.ts`
- `web-nuxt/composables/useSurfaceState.ts`
- `web-nuxt/composables/usePublicContextEnvelope.ts`
- `web-nuxt/utils/publicStateUrl.ts`
- `web-nuxt/tests/public-surface-state.test.ts`
- `web-nuxt/tests/public-context-envelope.test.ts`
- `web-nuxt/tests/public-state-url.test.ts`

## Interfaces

Added typed `SurfaceState<T>` variants and constructors for loading, ready, partial, stale, empty, error, and offline states. Added shared `ContextEnvelope`, `SearchViewState`, `AreaRef`, `MapViewport`, intent/filter, freshness, recovery, retry, and accessibility contracts. Added `usePublicContextEnvelope()` with deterministic unavailable/selected location semantics and explainable signal ids. Added URL parsing/serialization with bounded input, whitelisted intent/area/filter fields, deterministic malformed-value defaults, and privacy-safe rounded map tile (`z/x/y`) viewport serialization; raw coordinate pairs are never emitted.

## Verification

- `npm --prefix web-nuxt test -- public-surface-state.test.ts public-context-envelope.test.ts public-state-url.test.ts` — PASS (3 files, 5 tests).
- `npm --prefix web-nuxt run typecheck` — PASS (exit 0).

## Round 3 fixes

- Added a pure `projectLocation()` projection and an explicit matrix covering manual-selected while disabled, GPS, IP, and unavailable states, including source, accuracy, confidence/mode, and coordinate-redaction assertions.
- Strengthened viewport round-trip coverage by deriving x/y/z from the parsed tile center and requiring tile identity, while retaining invalid tile and raw-coordinate privacy checks.

Round 3 verification:

- `npm --prefix web-nuxt test -- public-surface-state.test.ts public-context-envelope.test.ts public-state-url.test.ts personalization-preferences.test.ts` — PASS (4 files, 53 tests).
- `npm --prefix web-nuxt run typecheck` — PASS (exit 0).

## Round 2 fixes

- Manual region selections remain `location.mode='selected'` with medium confidence even when location permission is disabled; GPS/IP signals continue to map to exact/approximate based on accuracy, while unavailable remains unavailable. Source, accuracy, and TTL evidence remain explicit and coordinate-free.
- Preference state is captured once when creating the envelope composable, avoiding watcher registration inside computed reevaluation.
- Serializer and parser now share the same filter-key grammar, so invalid keys are omitted before encoding and cannot create serialize/parse drift.
- Viewport tests assert sanitized tile-derived center bounds, invalid tile rejection, and absence of raw coordinate pairs.

Round 2 verification:

- `npm --prefix web-nuxt test -- public-surface-state.test.ts public-context-envelope.test.ts public-state-url.test.ts personalization-preferences.test.ts` — PASS (4 files, 48 tests).
- `npm --prefix web-nuxt run typecheck` — PASS (exit 0).

## Self-review

- Confirmed only Task 1 files were staged and committed; pre-existing dirty files remain untouched.
- SSR-safe parsing does not throw on malformed query/filter values.
- URL state excludes `selectedId`, panel, and raw coordinates; viewport is reduced to a bounded tile key.

## Concerns

- The task brief file contained only acceptance checklist bullets; implementation followed the authoritative Task 1 section in `docs/superpowers/plans/2026-08-09-adaptive-nocturne-public-upgrade-plan.md` and the associated design spec.
- Context accessibility/network signals are deterministic defaults; later tasks may wire runtime preference/network readers into the envelope.

Commits: `6f021cbe`, `d51d34b9`

## Round 1 fixes

- `usePublicContextEnvelope()` now distinguishes manual selected regions from GPS/IP inferred regions, disabled location, and unavailable state; source, accuracy, TTL, and explainable signal evidence are exposed without coordinates.
- URL filters and area keys are strictly whitelisted/bounded; malformed nested values are dropped deterministically. Sanitized tile `z/x/y` round-trip and invalid tile rejection are covered.
- Context time fields use explicit `Asia/Bangkok` local formatting rather than UTC ISO slicing.
- Added focused tests for coordinate redaction, tile validation, filter bounds, local-time shape, and privacy-safe context output. False-404, reduced-motion, 200% zoom, feature kill switches, and browser performance gates are delegated to later surface/UI tasks because Task 1 has no routing, rendering, or feature-flag implementation surface.

Fix verification:

- `npm --prefix web-nuxt test -- public-surface-state.test.ts public-context-envelope.test.ts public-state-url.test.ts` — PASS (3 files, 8 tests).
- `npm --prefix web-nuxt run typecheck` — PASS (exit 0).

## Fix round 4

- Replaced the projection-helper-only provenance matrix with envelope-level coverage that mutates the Nuxt preference snapshot and region source, then asserts the emitted `usePublicContextEnvelope().envelope.value` for manual-disabled, GPS, IP, and unavailable cases.
- Every case asserts the complete location mode/confidence/source/accuracy projection, `ttlSeconds`, explainable signals, coordinate redaction, and whether `area` is present or absent. No production changes were required.
- Mutation check: temporarily changing the envelope TTL from `300` to `301` made all four new matrix cases fail (`4 failed | 2 passed`); production was restored before verification.

Round 4 verification:

- `npm --prefix web-nuxt test -- public-context-envelope.test.ts personalization-preferences.test.ts public-state-url.test.ts public-surface-state.test.ts` — PASS (4 files, 52 tests; exit 0; duration 13.85s).
- `npm --prefix web-nuxt run typecheck` — PASS (exit 0).

Round 4 concerns: none.
