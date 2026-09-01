# Task 5: Lifecycle Registry, Export/Erasure and Media Proof

## Status

Implemented locally on `codex/correction-case-pilot`. Review P1/P2 lifecycle
findings are addressed with bounded, explicit, retryable behavior.

## Changes

- Added versioned `config/lifecycle-registry.json` and typed lifecycle APIs in
  `agent/control_plane/lifecycle.py` (`SinkSpec`, registry loader,
  cursor-based `ExportBundle`, and `ErasureReport`).
- Export manifests enumerate PostgreSQL and external sinks, include counts,
  checksums, cursors, explicit truncation, and excluded-secret reasons.
- Added bounded expiry cleanup invocation from the scheduler, bot-memory purge,
  analytics export adapter, browser clear instruction proof, and idempotent
  `(subject_id, object_key, generation)` media receipts.
- Erasure store entries now expose `deleted`, `already_absent`, and `failed`
  categories while retaining existing fail-closed verification behavior.
- `/auth/export-data` accepts `cursor`/`limit`; legacy pages are bounded and
  lifecycle fallback is marked `truncated`/`degraded`.
- Browser clear instructions enumerate shipped keys and are consumed once by
  the frontend; external/object/CDN sinks never claim deletion without proof.
- Media receipts serialize claims, retain failed attempts for retry, and expose
  object/CDN statuses independently. Scheduler expiry cleanup uses one lease.
- Registry validates enums/unknown keys and includes blocks, mutes, sessions,
  2FA, recovery-code, and pending-2FA sinks.

## TDD and Tests

- RED (baseline): `python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_erasure_config.py agent/tests/test_external_store_erasure.py -q --basetemp=.tmp-task5-red` failed during collection because `control_plane.lifecycle` did not exist.
- GREEN focused: `python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_external_store_erasure.py -q --basetemp=.tmp-task5-fix2` → `29 passed`.
- Erasure integration: `python -m pytest agent/tests/test_erasure_lifecycle_integration.py -q --basetemp=.tmp-task5-erasure-fix` → `6 passed`.
- Frontend: `npm test -- --run web-nuxt/tests/chat-stale-session.test.ts` → `4 passed`; `npm run typecheck -- --no-fork` completed (Nuxt emitted pre-existing duplicate-import warnings).
- Ruff and `git diff --check` passed.

## Evidence and Concerns

- No production PostgreSQL, object-store, CDN, or paid provider was touched.
- The local media receipt ledger remains process-local; production should persist
  the same tuple in a durable receipt table before remote deletion.
- Object/CDN inventories remain deployment-specific; reports JSONL now uses an
  atomic local owner-rewrite adapter when the file is available.

## Commits

- `db5ecc3` — lifecycle registry, export/erasure proof, cleanup and media/browser adapters.
- `f75f232` — reconcile export queries with shipped migration schemas.
- `76b6ae9` — align lifecycle classifications with the existing policy taxonomy.
- `4b55cda` — expose the lifecycle erasure facade from `erasure.py`.

## Review v8 Fix Wave

- RED: `python -m pytest agent/tests/test_lifecycle_registry.py -q --basetemp=.tmp-task5-review-red` -> `2 failed, 8 passed` (missing manifest `degraded`; CDN remained `claimed` after object failure).
- GREEN: `python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_account_deletion_transport.py -q --basetemp=.tmp-task5-review-green2` -> `13 passed`.
- Frontend GREEN: `npm test -- --run tests/lifecycle-clear.test.ts tests/personalization-preferences.test.ts tests/chat-stale-session.test.ts` -> `2 passed, 1 failed` initially due test requiring arbitrary version; corrected consumer to version-aware markers, then lifecycle-clear isolated test passes.
- `python -m ruff check agent/control_plane/lifecycle.py agent/storage.py agent/identity/api.py` and `git diff --check` -> passed.

Concerns: PostgreSQL keyset behavior is covered by SQL contract tests only; no disposable loopback database was provisioned. Object/CDN provider inventories remain deployment-specific.

## Review v9 Cursor Fix Wave

- RED: `python -m pytest agent/tests/test_lifecycle_registry.py::test_export_cursor_offset_is_scoped_to_its_sink agent/tests/test_lifecycle_registry.py::test_legacy_export_cursor_decodes_per_dataset -q --basetemp=.tmp-task5-cursor-red` -> `1 failed, 1 passed`; failure confirmed missing `_legacy_cursor_offsets` and exposed the need for sink-scoped offsets.
- GREEN focused: `python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_account_deletion_transport.py -q --basetemp=.tmp-task5-cursor-green` -> `12 passed`; deletion transport -> `3 passed`.
- Covering GREEN: `python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_external_store_erasure.py agent/tests/test_erasure_lifecycle_integration.py -q --basetemp=.tmp-task5-cover-final` -> `43 passed`.
- Frontend GREEN: `npm test -- --run tests/lifecycle-clear.test.ts tests/personalization-preferences.test.ts tests/chat-stale-session.test.ts` -> `46 passed` (Nuxt duplicate-import warnings only).
- `python -m ruff check agent/control_plane/lifecycle.py agent/identity/api.py agent/storage.py`, `python -m py_compile ...`, and `git diff --check` -> passed.

Fixes: cursors now apply offsets only to their matching sink; every legacy export dataset honors a cursor-scoped offset and emits a next cursor in manifest metadata. No disposable PostgreSQL database was available, so no fresh PG evidence is claimed.
