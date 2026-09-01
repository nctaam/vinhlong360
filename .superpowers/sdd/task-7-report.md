# Task 7 Report: Community State Machine, Scheduled Worker, Moderation CAS

## RED
- Command: `python -m pytest agent/tests/test_state_cas.py -q --basetemp .tmp-task7-red`
- Initial result: 3 failures (`ModuleNotFoundError: control_plane.concurrency`), proving the new contract was absent.

## GREEN
- Command: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py agent/tests/test_scheduler.py agent/tests/test_moderation*.py -q --basetemp .tmp-task7-final`
- Result: `64 passed, 5 skipped`.
- Regression: `python -m pytest agent/tests/test_auth_security_hardening.py -q --basetemp .tmp-task7-final` -> `91 passed`.

## PostgreSQL evidence
A disposable loopback PostgreSQL 16 cluster was initialized on `127.0.0.1:55437`, migrations applied through schema 84, and dropped/stopped in the same script. Readiness reported `ok=True`, schema 84, no missing tables/columns/triggers. Real threaded PG proof reported `1 passed, 10 deselected` for leased due-row CAS; teardown reported `database after drop: None`.

## Changes
- `agent/control_plane/concurrency.py`: idempotency claim/replay/conflict, status+revision CAS (deterministic HTTP 409), leased due-row claim with PostgreSQL `FOR UPDATE SKIP LOCKED`, additive state schema helpers.
- `agent/community/admin_api.py`: moderation and appeals use CAS; side effects happen only after a winning commit; batch moderation skips conflicts.
- `agent/scheduler.py`: bounded `task_publish_due_posts()` consumer with claim leases, immediate moderation recheck, visible `publish_failed` retry metadata, and scheduled task registration.
- `agent/ratelimit.py`: production fail-closed behavior when shared PostgreSQL rate-limit backend is unavailable, plus health telemetry.
- Tests: `agent/tests/test_state_cas.py`, real PG contention test in `agent/tests/test_case_contention_postgres.py`.

## Concerns
- Existing correction publication/rollback contention tests remain unrelated baseline failures (they predate this task and still report multiple successful applies).
- Existing `test_gap_fixes.py` has six unrelated source-shape failures in retention cleanup assertions.
- The community helper adds missing state columns lazily; production should eventually promote these additive DDLs to a numbered migration.

## Review Fix Wave

### RED
- `test_pending_unavailable_moderation_does_not_reject` initially failed because a pending provider result was coerced to `rejected` (`failed=0`, `rejected=1`).
- `test_due_claim_skips_draft_and_non_pending_rows` initially claimed an approved draft instead of the pending post.
- `test_production_alias_prd_fails_closed` initially allowed the in-memory fallback when `ENVIRONMENT=prd`.

### GREEN
- Command: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py agent/tests/test_scheduler.py agent/tests/test_moderation*.py agent/tests/test_migration_chain.py agent/tests/test_database.py agent/tests/test_auth_security_hardening.py -q --basetemp .tmp-task7-review-final/base4`
- Result: `388 passed, 5 skipped, 1 xfailed in 20.05s`.
- `python -m py_compile agent/control_plane/concurrency.py agent/community/api.py agent/community/admin_api.py agent/database.py agent/scheduler.py agent/ratelimit.py` passed.
- `git diff --check` passed.
- Repository migration contracts were updated for migration 084; `python -m pytest tests/test_check_migration_gate.py tests/test_release_quality_gates.py -q --basetemp .tmp-task7-review-final/gates2` -> `24 passed in 2.59s`.

### PostgreSQL review evidence
- A fresh disposable loopback PostgreSQL 16 cluster on `127.0.0.1:55437` applied all 83 migration files through `084_community_state_cas.sql`; readiness reported schema version 84, `ok=True`, and no missing tables, columns, triggers, or issues.
- Real threaded PostgreSQL proof: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py -q --tb=short -k community_cas_and_due` -> `1 passed, 13 deselected in 4.55s`.
- Teardown dropped the database (`database after drop: None`), stopped the server, and removed the disposable cluster.

### Review changes
- `create_post` now claims and records the durable shared idempotency receipt, replaying exact retries and returning 409 for a hash mismatch before rate-limit/moderation side effects.
- Scheduled moderation treats unavailable or non-terminal provider results as `publish_failed` with `MODERATION_UNAVAILABLE`, preserving the schedule and retry metadata.
- Due-row claims exclude drafts and non-`pending`/`flagged` rows and return the actual state column under PostgreSQL row locking.
- Production rate limiting recognizes `production`, `prod`, and `prd` aliases for fail-closed behavior.
- Migration 084 and readiness contracts raise the required schema version to 84 and persist community CAS/lease fields.

### Residual concerns
- Idempotency claim and receipt recording use separate transactions from the post insert; a process crash between them can leave a claimed key without a receipt. Exact successful retries are replay-safe, but full command/receipt atomicity needs a future transaction boundary refactor.
- Other community write routes still use the legacy validation-only `require_idempotency` dependency; `create_post` is the route wired to the shared receipt implementation in this review wave.
- The existing correction publication/rollback contention failures and `test_gap_fixes.py` source-shape failures remain unrelated baseline concerns noted above.

## Review Fix Wave 2

### RED
- `test_pg_schema_verification_never_runs_hot_path_ddl` caught runtime `DROP CONSTRAINT` DDL.
- `test_idempotency_pending_retry_returns_in_progress_without_duplicate` showed a claimed key with no receipt could be retried without a deterministic response.
- `test_scheduler_missing_moderation_availability_fails_closed` published a result missing `moderation_available`.
- `test_due_claim_lease_expiry_uses_current_time_not_due_cutoff` produced a lease expiring from the stale schedule cutoff.
- `test_publish_failed_post_is_automatically_retryable` could not reclaim `publish_failed` rows.
- Disposable PostgreSQL verification initially found migration 084 retained the legacy four-state check under the same constraint name.

### GREEN
- Command: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py agent/tests/test_scheduler.py agent/tests/test_moderation*.py agent/tests/test_migration_chain.py agent/tests/test_database.py agent/tests/test_migration_readiness_postgres.py agent/tests/test_auth_security_hardening.py tests/test_check_migration_gate.py tests/test_release_quality_gates.py -q --basetemp .tmp-task7-review-v2-green/full`
- Result: `431 passed, 8 skipped, 1 xfailed in 25.54s`.
- Blocker-specific crash, schema, scheduler, lease, and retry tests pass; `python -m py_compile ...` and `git diff --check` pass.

### PostgreSQL fix evidence
- Disposable loopback run: `powershell -NoProfile -ExecutionPolicy Bypass -File .tmp-task7-pg-run.ps1`.
- Migrations applied through `084_community_state_cas.sql` (schema 84); readiness `ok=True` with no missing tables, columns, triggers, or issues.
- Real concurrent proof: `1 passed, 21 deselected in 4.29s`; teardown reported `database after drop: None`, server stopped, and cluster removed.

### Review Fix Wave 2 changes
- `ensure_state_schema()` now performs PostgreSQL read/verify only and fails closed when CAS columns or the stable moderation constraint are absent; SQLite retains compatibility additions.
- Migration 084 replaces any legacy moderation-status check with the durable `publish_failed`-aware constraint.
- Idempotency retries with a claimed key and no receipt return deterministic `409 idempotency_in_progress`; an injected crash after insert proves no second insert occurs.
- Scheduler publishes only when moderation status is terminal and `moderation_available is True`; missing/unknown availability is persisted as `publish_failed`.
- Due leases expire from the worker's actual current time, and `publish_failed` rows are explicitly retryable.
