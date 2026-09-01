# Task 7 Report: Community State Machine, Scheduled Worker, Moderation CAS

## RED
- Command: `python -m pytest agent/tests/test_state_cas.py -q --basetemp .tmp-task7-red`
- Initial result: 3 failures (`ModuleNotFoundError: control_plane.concurrency`), proving the new contract was absent.

## GREEN
- Command: `python -m pytest agent/tests/test_state_cas.py agent/tests/test_case_contention_postgres.py agent/tests/test_scheduler.py agent/tests/test_moderation*.py -q --basetemp .tmp-task7-final`
- Result: `64 passed, 5 skipped`.
- Regression: `python -m pytest agent/tests/test_auth_security_hardening.py -q --basetemp .tmp-task7-final` -> `91 passed`.

## PostgreSQL evidence
A disposable loopback PostgreSQL 16 cluster was initialized on `127.0.0.1:55437`, migrations applied through schema 83, and dropped/stopped in the same script. Readiness reported `ok=True`, schema 83, no missing tables/columns/triggers. Real threaded PG proof reported `1 passed, 10 deselected` for leased due-row CAS; teardown reported `database after drop: None`.

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
