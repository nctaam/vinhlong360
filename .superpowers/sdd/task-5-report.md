# Task 5: Lifecycle Registry, Export/Erasure and Media Proof

## Status

Implemented locally on `codex/correction-case-pilot`. The implementation is
additive-first and keeps provider actions bounded and idempotent.

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

## TDD and Tests

- RED: `python -m pytest agent/tests/test_lifecycle_registry.py agent/tests/test_erasure_config.py agent/tests/test_external_store_erasure.py -q --basetemp=.tmp-task5-red` failed during collection because `control_plane.lifecycle` did not exist.
- GREEN: lifecycle tests `4 passed`.
- Task 5 focused suites: `67 passed, 8 skipped` (PostgreSQL tests skipped because no disposable loopback DSN was configured).
- Ruff and `git diff --check` passed.

## Evidence and Concerns

- No production PostgreSQL, object-store, CDN, or paid provider was touched.
- The local media receipt ledger is disposable process-local proof; a production
  deployment should persist the same tuple in a durable receipt table/provider
  audit stream before enabling remote deletion.
- External JSONL, bot, browser, object, and CDN exports are represented in the
  manifest with explicit adapter metadata; provider enumeration remains a
  deployment-specific integration concern.

## Commits

- `db5ecc3` — lifecycle registry, export/erasure proof, cleanup and media/browser adapters.
- `f75f232` — reconcile export queries with shipped migration schemas.
- `76b6ae9` — align lifecycle classifications with the existing policy taxonomy.
- `4b55cda` — expose the lifecycle erasure facade from `erasure.py`.
