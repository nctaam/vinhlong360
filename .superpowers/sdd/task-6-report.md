# Task 6 Implementer Report

## Status

DONE_WITH_CONCERNS

## RED evidence

Command:

```powershell
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest agent/tests/test_generation_clock.py -q --tb=short
```

Result before implementation: collection failed with `ModuleNotFoundError: No module named 'control_plane.clock'` (the required modules did not exist).

## GREEN evidence

Focused acceptance command:

```powershell
$env:PYTEST_DEBUG_TEMPROOT='C:\vlt'; python -m pytest agent/tests/test_generation_clock.py tests/test_cache.py tests/test_semantic_cache.py tests/test_prompt_cache.py agent/tests/test_admin_common.py tests/integration/test_cross_boundary_proof.py -q
```

Result: `121 passed in 6.29s`.

Additional clock/adapter rerun: `8 passed in 3.88s`.

## Implementation

- Added injectable `Clock`, `SystemClock`, `FrozenClock`, UTC/Vietnam conversion and exact 16:59/17:00 boundary coverage.
- Added `SnapshotRef`, durable `entity_snapshot_generation` adapters (SQLite + PostgreSQL `UPDATE ... RETURNING`) and one invalidation registry covering L1/L2/Redis/review/similar/KB/place/homepage consumers.
- Added generation-aware cache keys and personalized namespace guard.
- Wired entity upsert/audit/description/delete, KB sync, reload/health/index timestamps, homepage/feed/chat/prompt/MCP seasonal paths to the canonical clock.
- Added PostgreSQL migration `083_entity_snapshot_generation.sql` and fresh-install DDL.

## PostgreSQL evidence

No PostgreSQL instance was provisioned or touched. A PG-like cursor/connection contract test verifies `%s` placeholders and atomic `UPDATE ... RETURNING`; production schema replay remains unverified.

## Concerns


## P1 Fix Report

### RED evidence

- Before the fix, schema contract tests failed because `PG_REQUIRED_SCHEMA_VERSION` was 83 while affected tests still asserted 82 (`2 failed`).
- Before the fix, publication generation tests failed because `CaseTransaction` had no generation bump hook and failed commits retained post-commit callbacks (`3 failed`).

### GREEN/regression evidence

- `python -m pytest agent/tests/test_task6_publication_generation.py -q --tb=short` -> `4 passed`.
- `python -m pytest agent/tests/test_database.py agent/tests/test_migration_chain.py agent/tests/test_pg_schema_readiness.py tests/test_check_migration_gate.py tests/test_release_quality_gates.py -q --tb=short` -> `257 passed, 1 xfailed`.
- Disposable loopback PostgreSQL on `127.0.0.1:5434`: applied 82 migrations through `083_entity_snapshot_generation.sql`; `pg_schema_status()` reported `schema_version=83`, `required_schema_version=83`; real insert/update/delete generations advanced `1/2/3`; transactional publication SQL path advanced to `1`; focused PG suites passed `62 passed`; database and cluster were dropped/stopped (`database after drop: None`).

### Implementation

- Centralized correction apply/rollback generation advancement in `CaseTransaction.apply_entity_patch`, exactly once for real changes and never for no-ops.
- Deferred cache invalidation until commit and discard callbacks on rollback/commit failure; publication apply/rollback pass correlation IDs and no longer double-bump.
- Raised all schema/readiness contracts and migration gate expectations consistently to 83.

### Concerns

- Full publication/rollback integration requires disposable PostgreSQL and was verified there; no production database or port 5432 was touched.
