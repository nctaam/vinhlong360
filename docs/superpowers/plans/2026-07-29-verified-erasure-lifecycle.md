# Verified Erasure Lifecycle Implementation Plan

> STATUS: active - implementation commits and focused evidence are complete; final closure remains pending the required disposable PostgreSQL gate and the documented full-baseline timeout debt. See `docs/superpowers/results/2026-07-29-verified-erasure-lifecycle.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current inline 30-day account cleanup with a durable, owner-blocking, externally verified erasure lifecycle that is deterministic at the exact deadline and safe to retry per user.

**Architecture:** PostgreSQL owns deletion state and row locks. `agent/owner_write_gate.py` is the single admission boundary for all owner-linked writes. `agent/data_lifecycle.py` registers every personal, pseudonymous, and aggregate store with purge/verify behavior. `agent/erasure.py` coordinates immediate quarantine, recoverable grace, and verified hard erasure; the scheduler only invokes this orchestrator in audit-only mode until a separate activation gate is approved. Database cleanup uses registered FK actions and explicit structured-reference scrubbers rather than broad text replacement.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, PostgreSQL, psycopg2, pytest, httpx ASGI transport, file-backed memory/cache stores, and the existing scheduler thread.

## Global Constraints

- Execute this plan only after the Runtime Trust Boundary plan is complete and its result gate is approved. This plan consumes `privacy_policy`, `feedback_policy`, safe owner-attributed sink records, and privacy source guards created there; it must not recreate substitute interfaces.
- The deadline is exactly 30 UTC days from the committed deletion request timestamp; active accounts do not receive a rolling TTL.
- `config/privacy-policy.json` and `agent/privacy_policy.py` from the Runtime Trust Boundary plan are the only policy authority. Do not reintroduce an independent `20` or `30` day default.
- Recovery is allowed only while `now < erasure_due_at`; at the exact deadline it fails closed. Recovery and erasure lock the same user row and use an injectable UTC clock in tests.
- A deletion request commits account disablement, credential/session revocation, `erasure_due_at`, and write blocking before best-effort external quarantine. Quarantine failure never re-enables the account.
- Hard erasure purges and verifies every registered personal/pseudonymous store before deleting or anonymizing PostgreSQL data. Residual data prevents the final database transaction.
- Every due user is isolated. One failure records a stable bounded code and cannot roll back successful users or stop later attempts.
- Scheduler code contains no account-deletion SQL. It invokes the orchestrator, is single-flight, runs startup catch-up and every five minutes, and remains audit-only until separately activated.
- User-owned foreign keys use `ON DELETE CASCADE`; actor-only references are nullable with `ON DELETE SET NULL`; pending/completed special workflows follow the explicit policy in the approved spec.
- Structured text/JSON cleanup targets registered fields and exact UUID/reference paths only. Never run a global UUID or substring replacement over user content.
- The legacy scrub defaults to dry-run, requires backup evidence and an explicit `--apply`, and is not run against production by this plan.
- No production deletion, deadline backfill `--apply`, scrub application, deploy, push, secret rotation, or real-data mutation is authorized by approving this plan.
- Use strict RED-GREEN-REFACTOR TDD. Each numbered task gets a fresh implementation subagent and an independent spec/compliance review before the next task starts. Each task commits only its scoped files.
- Migration `071` belongs to the Runtime Trust Boundary feedback receipt store. This plan reserves `072` and `073` for lifecycle state and FK/reference policy.

---

### Task 1: Durable Erasure State And Migration 072

**Files:**
- Create: `agent/migrations/072_account_erasure_state.sql`
- Modify: `init.sql`
- Modify: `agent/config.py`
- Modify: `agent/auth.py:1222`
- Create: `agent/erasure_state.py`
- Create: `agent/tests/test_erasure_state.py`
- Create: `agent/tests/test_account_deletion_transport.py`
- Modify: `agent/tests/test_migration_chain.py`

**Interfaces:**
- Produces frozen `ErasureState` with `deleted_at`, `erasure_due_at`, `erasure_attempt_count`, `erasure_last_attempt_at`, and `erasure_last_error_code`.
- Produces `request_account_erasure(user_id, *, now) -> ErasureState` and `load_erasure_state(conn, user_id, *, for_update=False)`.
- Produces `ERASURE_ERROR_CODES = {"STORE_UNAVAILABLE", "RESIDUAL_DATA", "DB_CONSTRAINT", "VERIFY_FAILED"}` and rejects arbitrary error text.

- [ ] **Step 1: Write failing state and migration tests**

Assert that the migration adds the four nullable/bounded metadata columns, a due-time index, and a check constraint for non-negative attempts and the allowlisted error codes. Assert migration 072 does not silently backfill legacy soft-deleted production rows. Assert that a new deletion request stores the exact injected timestamp plus 30 days, is idempotent for an already scheduled account, and never computes the due date from the current time on a retry. Through ASGI transport, require the response to contain the exact ISO deadline and `grace_days == 30`.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_erasure_state.py agent/tests/test_account_deletion_transport.py agent/tests/test_migration_chain.py
```

Expected: missing columns/module and the current endpoint response lacks `erasure_due_at`.

- [ ] **Step 3: Implement additive schema and state projection**

Add `erasure_due_at TIMESTAMPTZ`, `erasure_attempt_count INTEGER NOT NULL DEFAULT 0`, `erasure_last_attempt_at TIMESTAMPTZ`, and bounded `erasure_last_error_code TEXT`. Add a partial index for due rows. Keep migration replay-safe, register version 72, and leave pre-existing `deleted_at IS NOT NULL AND erasure_due_at IS NULL` rows unchanged for the audit-only backfill report in Task 7. In `erasure_state.py`, use UTC-aware datetimes, strict error-code validation, and row-to-dataclass conversion.

- [ ] **Step 4: Make deletion request transactional and exact**

Change `DELETE /account` to lock the user row and load its phone, set `deleted_at = COALESCE(deleted_at, now)`, set `erasure_due_at = COALESCE(erasure_due_at, now + timedelta(days=policy.account_erasure_deadline_days))`, disable the account, revoke `user_sessions`, phone-bound `otp_sessions`, `trusted_devices`, `pending_2fa`, and any other registered active challenge in one transaction, then return the stored deadline. Do not perform external purge before this commit.

- [ ] **Step 5: Run focused transport and migration tests**

```powershell
python -m pytest -q agent/tests/test_erasure_state.py agent/tests/test_account_deletion_transport.py agent/tests/test_migration_chain.py agent/tests/test_account_control_plane_security.py
```

- [ ] **Step 6: Commit and review**

```powershell
git add agent/migrations/072_account_erasure_state.sql init.sql agent/config.py agent/auth.py agent/erasure_state.py agent/tests/test_erasure_state.py agent/tests/test_account_deletion_transport.py agent/tests/test_migration_chain.py
git commit -m "feat: persist account erasure deadlines"
```

Review gate: confirm one authoritative duration, exact request-time arithmetic, row-locking, credential revocation coverage, migration replay safety, and no hard delete in the endpoint.

---

### Task 2: Central Owner Write Gate

**Files:**
- Create: `agent/owner_write_gate.py`
- Modify: `agent/memory.py`
- Modify: `agent/memory_graph.py`
- Modify: `agent/semantic_cache.py`
- Modify: `agent/analytics.py`
- Modify: `agent/cost_tracker.py`
- Modify: `agent/self_optimizer.py`
- Modify: `agent/experience_memory.py`
- Modify: `agent/prompt_compiler.py`
- Modify: `agent/ab_testing.py`
- Modify: `agent/feedback_policy.py`
- Modify: `agent/server.py`
- Create: `agent/tests/test_owner_write_gate.py`
- Create: `agent/tests/test_owner_write_source_guard.py`

**Interfaces:**
- Produces `OwnerWriteBlocked`, `OwnerWriteGate.assert_writable(owner_key)`, `OwnerWriteGate.refresh(owner_key)`, and `owner_write_gate` singleton.
- Produces `owner_key_for_user(user_id) -> "user:<uuid>"` and preserves the existing `anon:<sha256>` contract.
- Every owner-linked persistent write calls `assert_writable()` immediately before the write; reads remain available only where the endpoint policy permits them.

- [ ] **Step 1: Write failing gate and restart-persistence tests**

Use a fake durable account-state reader to prove active owners pass, a deleted user fails immediately, anonymous owners remain allowed unless a separate abuse policy blocks them, and a fresh gate instance still blocks a deleted user. Add source tests that inspect memory, graph, cache, feedback receipt ownership, cost attribution, optimizer, analytics, experience memory, prompt demonstrations, and A/B outcome write functions for a gate call before persistence.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_owner_write_gate.py agent/tests/test_owner_write_source_guard.py
```

Expected: module/import failure and existing stores accept writes after account deletion.

- [ ] **Step 3: Implement durable gate and fail-closed lookup**

Create a small gate that queries durable `users.deleted_at` through the existing DB abstraction for every authenticated-user write. Never cache a writable user decision: a stale positive cache would permit a post-deletion write. A short blocked-state cache is allowed as defense in depth and is invalidated on recovery. Any DB lookup failure raises `OwnerWriteBlocked` rather than allowing a write. Never log the owner key or user ID.

- [ ] **Step 4: Enforce the gate at all personal sinks**

Guard cold/hot memory, memory graph, exact and semantic personalized cache writes, analytics/cost/optimizer owner records, experience memory, prompt demonstrations, A/B outcome records, feedback receipt issuance, and any new owner-linked sink. Pass boundary-produced content from the runtime plan; do not reintroduce raw fallback writes. Keep deidentified aggregate rollups outside the owner gate only when they contain no stable owner reference.

- [ ] **Step 5: Add deletion/recovery invalidation hooks**

Expose explicit `block_owner()` and `unblock_owner()` hooks called after the deletion/recovery transactions commit. The durable check remains authoritative after process restart.

- [ ] **Step 6: Run focused sink and chat regressions**

```powershell
python -m pytest -q agent/tests/test_owner_write_gate.py agent/tests/test_owner_write_source_guard.py tests/test_memory.py tests/test_semantic_cache.py agent/tests/test_analytics.py tests/test_cost_tracker.py tests/test_self_optimizer.py agent/tests/test_experience_memory.py agent/tests/test_prompt_compiler.py tests/test_ab_testing.py agent/tests/test_chat_owner_boundary.py agent/tests/test_chat_usage_accounting.py
```

- [ ] **Step 7: Commit and review**

```powershell
git add agent/owner_write_gate.py agent/memory.py agent/memory_graph.py agent/semantic_cache.py agent/analytics.py agent/cost_tracker.py agent/self_optimizer.py agent/experience_memory.py agent/prompt_compiler.py agent/ab_testing.py agent/feedback_policy.py agent/server.py agent/tests/test_owner_write_gate.py agent/tests/test_owner_write_source_guard.py
git commit -m "feat: gate owner-linked writes"
```

Review gate: verify no process-memory-only authorization, fail-closed DB errors, all listed sinks covered, anonymous owner compatibility, and no aggregate owner leakage.

---

### Task 3: Lifecycle Registry And External Store Adapters

**Files:**
- Create: `agent/data_lifecycle.py`
- Modify: `agent/memory.py`
- Modify: `agent/memory_graph.py`
- Modify: `agent/semantic_cache.py`
- Modify: `agent/analytics.py`
- Modify: `agent/cost_tracker.py`
- Modify: `agent/self_optimizer.py`
- Modify: `agent/experience_memory.py`
- Modify: `agent/prompt_compiler.py`
- Modify: `agent/ab_testing.py`
- Modify: `agent/feedback_policy.py`
- Create: `agent/tests/test_data_lifecycle_registry.py`
- Create: `agent/tests/test_external_store_erasure.py`
- Modify: `agent/server.py`

**Interfaces:**
- Produces `DataStorePolicy(name, classification, purge, verify, description, quarantine_on_request=False)`, `PurgeResult`, `VerificationResult`, `lifecycle_registry`, `validate_lifecycle_registry()`, and `lifecycle_registry_readiness()`.
- Personal/pseudonymous adapters implement `purge_owner(owner_key) -> PurgeResult` and `verify_owner_absent(owner_key) -> VerificationResult`.
- Aggregate adapters explicitly declare `classification="aggregate"`, `subject_linked=False`, and the fields proving no raw text or stable owner reference is retained.

- [ ] **Step 1: Write failing completeness and idempotence tests**

Declare an expected store set covering hot memory, cold memory, memory graph, exact cache, semantic cache/leases, feedback receipts, owner-linked analytics, cost attribution, optimizer records, experience memory, prompt demonstrations, A/B outcome records, and any file-backed owner index found by source scan. Assert an undeclared personal adapter fails readiness, every immediate-phase store has `quarantine_on_request=True`, non-ephemeral recovery data does not, and each purge is idempotent. Assert a residual verification result blocks hard erasure.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_data_lifecycle_registry.py agent/tests/test_external_store_erasure.py
```

- [ ] **Step 3: Implement typed registry and adapters**

Use explicit names, stable classifications, and an explicit quarantine flag. Adapters must bound work, avoid logging content, and return counts/digests without owner identifiers. Mark hot memory, active personalized cache, in-flight semantic leases, and unused feedback receipts for immediate quarantine. Retain recoverable core/profile/UGC and non-ephemeral personal stores until hard erasure. The hard-erasure set additionally purges cold memory, graph nodes, owner analytics/cost/optimizer rows, experience memory, prompt demonstrations, A/B outcome records, and file-backed owner indexes. Verify by exact owner namespace/key, not broad deletion.

- [ ] **Step 4: Register feedback and aggregate exceptions**

Register pending feedback receipts as personal credentials; used receipts may be cleared by expiry. Register daily deidentified rollups and post-boundary operational logs as retained non-subject stores only if schema/source tests prove they have no owner, user, session, query, response, receipt, or entity identifiers. Registry validation must reject accidental owner columns or linked log fields in retained aggregate/operational adapters.

- [ ] **Step 5: Wire readiness and diagnostics**

Add `checks["lifecycle_registry"] = lifecycle_registry_readiness()` to readiness. Expose only store names, classifications, and stable adapter status in diagnostics; never expose owner IDs, paths containing IDs, or raw errors.

- [ ] **Step 6: Run adapter, readiness, and source tests**

```powershell
python -m pytest -q agent/tests/test_data_lifecycle_registry.py agent/tests/test_external_store_erasure.py agent/tests/test_owner_write_source_guard.py agent/tests/test_privacy_logging.py
```

- [ ] **Step 7: Commit and review**

```powershell
git add agent/data_lifecycle.py agent/memory.py agent/memory_graph.py agent/semantic_cache.py agent/analytics.py agent/cost_tracker.py agent/self_optimizer.py agent/experience_memory.py agent/prompt_compiler.py agent/ab_testing.py agent/feedback_policy.py agent/server.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_external_store_erasure.py
git commit -m "feat: register personal data stores"
```

Review gate: compare the registry against a fresh repository-wide owner-reference inventory and verify every personal adapter has purge plus verification, bounded errors, and exact namespace matching.

---

### Task 4: Foreign-Key And Structured-Reference Cleanup Policy

**Files:**
- Create: `agent/migrations/073_erasure_delete_actions.sql`
- Modify: `agent/database.py`
- Create: `agent/structured_references.py`
- Create: `agent/tests/test_erasure_constraints_postgres.py`
- Create: `agent/tests/test_structured_reference_cleanup.py`
- Modify: `agent/tests/test_migration_chain.py`
- Modify: `agent/tests/test_account_control_plane_postgres.py`

**Interfaces:**
- Produces `DeleteActionPolicy(table, column, action, special_policy)` and `registered_delete_actions()`.
- Produces `scrub_user_references(conn, user_id, *, actor_policy) -> ScrubSummary` for exact JSON/text reference fields.
- Produces `validate_user_fk_actions(conn)` which introspects `pg_constraint` and rejects unregistered restrictive actions.

- [ ] **Step 1: Write failing PostgreSQL introspection and sentinel tests**

Against the disposable PostgreSQL URL, introspect every FK to `users` and assert each action is registered as cascade, set-null, or named special policy. Seed a sentinel UUID in follows/reports target IDs, notification and audit ref pairs, mention arrays, and claim fields; assert the database scrub removes only registered references. Prove pending claims are deleted and completed claims retain only entity, status, and timestamps with claimant/reviewer/contact/evidence/free-text cleared. External memory graph and file-backed indexes are covered by Task 3 adapters, not this PostgreSQL scrubber.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py
```

Expected: current restrictive `entity_claims`/actor constraints and unregistered polymorphic references fail the contract.

- [ ] **Step 3: Implement migration 073 and policy registry**

Make user-owned foreign keys `ON DELETE CASCADE`; make actor-only columns nullable with `ON DELETE SET NULL`; preserve special workflows for claims, appeals, and audit decisions. The initial actor-policy inventory must explicitly cover reviewer/editor/moderator/featured-by/announcement/collection/admin-note references found in the current schema. Keep migration additive/replay-safe where possible and register version 73. Never silently alter a constraint without an explicit policy entry.

- [ ] **Step 4: Implement exact structured cleanup**

Define the initial PostgreSQL registry for `target_type/target_id`, `ref_type/ref_id`, structured mentions, and JSON owner fields. Delete or null exact matching entries and compact arrays; clear all approved completed-claim free-text/contact/evidence fields. Do not regex-replace arbitrary content or UUID-like substrings. Keep graph nodes and file-backed owner indexes in the external lifecycle registry from Task 3.

- [ ] **Step 5: Run real PostgreSQL migration and reference tests**

```powershell
python -m pytest -q agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_migration_chain.py agent/tests/test_account_control_plane_postgres.py
```

Run with `TRUST_ERASURE_TEST_DATABASE_URL` already set to the disposable PostgreSQL target. If the URL is absent, record the exact skip; do not substitute SQLite evidence.

- [ ] **Step 6: Commit and review**

```powershell
git add agent/migrations/073_erasure_delete_actions.sql agent/database.py agent/structured_references.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_migration_chain.py agent/tests/test_account_control_plane_postgres.py
git commit -m "feat: register erasure delete actions"
```

Review gate: verify all FK actions from catalog introspection are covered, claim policy is exact, JSON cleanup is field-scoped, and no broad text scrub is introduced.

---

### Task 5: Immediate Quarantine And Linearizable Recovery

**Files:**
- Create: `agent/quarantine.py`
- Modify: `agent/auth.py`
- Modify: `agent/owner_write_gate.py`
- Create: `agent/tests/test_quarantine.py`
- Create: `agent/tests/test_recovery_deadline.py`
- Create: `agent/tests/test_account_recovery_transport.py`

**Interfaces:**
- Produces `quarantine_account(user_id, *, now) -> QuarantineResult`, `retry_pending_quarantines(*, now, limit=50, audit_only=False) -> QuarantineBatchResult`, and `recover_account(user_id, *, now) -> RecoveryResult`.
- `quarantine_account` locks/rechecks the user row, derives the owner key, selects registry policies with `quarantine_on_request=True`, and purges hot memory, active personalized caches, in-flight semantic leases, and unused receipts after the account transaction commits; database sessions/challenges were already revoked inside the account transaction.
- Recovery locks the user row, succeeds only when `now < erasure_due_at`, atomically clears `deleted_at`, `erasure_due_at`, attempt/error metadata and re-enables the account, calls `unblock_owner` after commit, and creates a new session only after the state commit.

- [ ] **Step 1: Write failing quarantine/recovery tests**

Assert deletion immediately blocks new personal writes, revokes every session/challenge, purges ephemeral stores, and remains disabled if one external purge fails. Assert a crash after the account commit but before quarantine, plus a partial quarantine failure, is selected by the bounded retry function; successful retry clears the stable error. Assert recovery before the deadline succeeds, recovery exactly at and after the deadline fails, deleted hot memory/cache is not reconstructed, and concurrent recovery versus erasure produces one committed outcome.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_account_recovery_transport.py
```

- [ ] **Step 3: Implement quarantine after durable account commit**

Use a stable run ID and adapter names for retry diagnostics. After the deletion-state transaction commits, the endpoint calls `quarantine_account()` before returning; failure changes the diagnostic result but never re-enables credentials or rolls back the stored deletion request. `quarantine_account()` holds the same user-row lock used by recovery while it runs only the bounded immediate-phase adapters, then records success/error before commit; this prevents recovery from racing with a late purge of newly active data. The original deletion transaction remains authoritative, quarantine errors increment bounded attempt state, set only an allowlisted error code, and leave credentials disabled. A successful quarantine records `erasure_last_attempt_at` and clears the error. `retry_pending_quarantines()` selects pre-deadline deleted rows whose first quarantine never completed (`erasure_last_attempt_at IS NULL`) or whose last quarantine has an error; each selected account is rechecked by `quarantine_account()`, adapters run idempotently, and users are isolated. Never log user IDs, owner keys, raw exception text, or data content.

- [ ] **Step 4: Replace OTP reactivation with locked recovery**

Update `_reactivate_user`/OTP login to call the recovery service instead of clearing `deleted_at` directly. Lock the row and recheck the injected UTC clock. At/after the deadline, return the generic account-unavailable response and do not create a session.

- [ ] **Step 5: Run transport and concurrency regressions**

```powershell
python -m pytest -q agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_account_recovery_transport.py agent/tests/test_account_control_plane_security.py agent/tests/test_2fa_crypto.py
```

- [ ] **Step 6: Commit and review**

```powershell
git add agent/quarantine.py agent/auth.py agent/owner_write_gate.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_account_recovery_transport.py
git commit -m "feat: quarantine and lock account recovery"
```

Review gate: prove durable disablement precedes purge, exact-deadline fail-closed recovery, no session before commit, and race linearizability.

---

### Task 6: Verified Hard-Erasure Orchestrator

**Files:**
- Create: `agent/erasure.py`
- Modify: `agent/database.py`
- Modify: `agent/metrics.py`
- Create: `agent/tests/test_erasure_orchestrator.py`
- Create: `agent/tests/test_erasure_orchestrator_postgres.py`
- Modify: `agent/tests/test_data_lifecycle_registry.py`

**Interfaces:**
- Produces `erase_account(user_id, *, now, run_id=None) -> ErasureResult` and `erase_due_accounts(now, limit=50, *, audit_only=False) -> BatchErasureResult`.
- Produces bounded `ErasureResult(status, stores, error_code, verified)` and no raw exception fields. Internal controller state may carry a user ID, but result serialization, metrics, and logs must not.
- Uses a short `SELECT ... FOR UPDATE` preparation transaction to recheck `deleted_at` and `erasure_due_at`, record the bounded attempt state, and commit before external purge. The final database transaction locks and rechecks the row again.

- [ ] **Step 1: Write failing orchestrator and isolation tests**

Seed two due users and adapters where one fails. Assert the successful user is fully purged/deleted, the failed user remains due with incremented attempt metadata, and later users are still attempted. Assert a residual adapter blocks the final transaction, a crash before DB commit causes idempotent re-purge, and a committed deletion has already passed every verification adapter.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_orchestrator_postgres.py
```

- [ ] **Step 3: Implement per-user external purge and verify**

In a short preparation transaction, lock and recheck the account, skip non-due/non-deleted rows, mark a stable attempt timestamp, and commit. Run every personal/pseudonymous adapter outside the database transaction, then verify each reports zero residual owner data. On failure update only bounded attempt/error metadata in a small transaction and return without deleting the subject. Do not hold a database row lock across file I/O or external-store operations.

- [ ] **Step 4: Implement structured DB cleanup and final delete**

After external verification, run one transaction for pending-claim deletion, completed-claim anonymization, deletion of pending user-owned appeals, retention of completed decisions with null reviewers, actor nulling, exact structured-reference cleanup, cascade-owned data deletion, and a final parameterized delete constrained by `id`, `deleted_at IS NOT NULL`, and `erasure_due_at <= now`. Before commit, query within the same transaction to prove the user row and unapproved structured/restrictive references are absent; roll back on any mismatch. Post-commit verification may emit metrics but must not be the first point that detects a database residue.

- [ ] **Step 5: Add deidentified metrics and safe diagnostics**

Emit `erasure_due_total`, `erasure_completed_total`, `erasure_failed_total{code}`, and `erasure_overdue_total`. Logs carry run ID, store name, and stable code only. Never include user ID, owner key, raw SQL params, or exception text.

- [ ] **Step 6: Run real PostgreSQL orchestrator tests**

```powershell
python -m pytest -q agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_orchestrator_postgres.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py
```

Require the disposable PostgreSQL URL for final completion; a missing URL is a documented skip, not passing evidence.

- [ ] **Step 7: Commit and review**

```powershell
git add agent/erasure.py agent/database.py agent/metrics.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_orchestrator_postgres.py agent/tests/test_data_lifecycle_registry.py
git commit -m "feat: verify personal data before erasure"
```

Review gate: inspect lock order, retry/idempotence, residual-stop behavior, per-user isolation, final delete predicate, and deidentified-only observability.

---

### Task 7: Scheduler Audit-Only Integration And Observability

**Files:**
- Modify: `agent/scheduler.py`
- Modify: `agent/server.py`
- Modify: `agent/config.py`
- Create: `scripts/backfill_erasure_deadlines.py`
- Create: `scripts/run_account_erasure.py`
- Create: `agent/tests/test_erasure_scheduler.py`
- Create: `agent/tests/test_erasure_deadline_backfill.py`
- Create: `agent/tests/test_erasure_cli.py`
- Create: `agent/tests/test_scheduler_source_guard.py`

**Interfaces:**
- Produces `task_account_erasure()` that invokes `erase_due_accounts(now=utc_now(), limit=50, audit_only=settings.ERASURE_AUDIT_ONLY)`.
- Produces a sibling single-flight quarantine retry invocation using `retry_pending_quarantines(now=utc_now(), limit=50, audit_only=settings.ERASURE_AUDIT_ONLY)`.
- Scheduler runs a single-flight erasure task at startup and every five minutes with batch size 50; no inline `DELETE FROM users` or fixed `INTERVAL '30 days'` remains.
- Produces status fields `audit_only`, `last_run_at`, `last_result`, `due_count`, `overdue_count`, `legacy_missing_deadline_count`, and the bounded impact of computing legacy deadlines as `deleted_at + policy days`, without subject identifiers.
- Produces a dry-run-default backfill CLI that computes legacy deadlines from stored `deleted_at`, requires explicit `--apply` plus backup evidence to write, and is not applied by this plan.
- Produces an audit-only-default erasure CLI; mutation requires explicit `--activate`, validated backup evidence, and an explicit bounded `--limit` so the runbook can safely start with one due account.

- [ ] **Step 1: Write failing scheduler/source tests**

Assert startup catch-up and five-minute cadence, no overlapping lifecycle runs, batch size 50, retry of incomplete pre-deadline quarantine, audit-only mode reports quarantine backlog/due users/legacy rows missing deadlines without purging, deleting, backfilling, or updating attempt metadata, and per-user failures do not abort the task. Assert the backfill CLI defaults to dry-run, derives every deadline from `deleted_at + committed policy days`, and refuses `--apply` without backup evidence. Assert the erasure CLI defaults to audit-only and refuses mutation without `--activate`, backup evidence, and an explicit `--limit`. Source guard rejects account-deletion SQL in `scheduler.py` and rejects a hard-coded `30 days` interval outside the policy/orchestrator.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_erasure_scheduler.py agent/tests/test_erasure_deadline_backfill.py agent/tests/test_erasure_cli.py agent/tests/test_scheduler_source_guard.py
```

- [ ] **Step 3: Replace legacy session-cleanup account deletion**

Keep expired-session/OTP cleanup and stale-post cleanup where still authorized, but remove user hard-delete selection/deletion from `task_session_cleanup`. Add the dedicated single-flight erasure task and startup invocation. Make scheduler disablement explicit through configuration; no implicit production activation.

- [ ] **Step 4: Add audit-only reporting and readiness**

Add `ERASURE_AUDIT_ONLY = True` as the safe default and require an explicit, separately gated activation setting for normal execution. Audit-only execution performs read-only due/overdue inventory, reports the count and due/overdue effect of the proposed `erasure_due_at = deleted_at + policy days` legacy backfill, and checks adapter readiness; it never backfills, purges, verifies subject data, increments attempts, or enters the final database cleanup. Implement the backfill CLI with the same read-only report by default; `--apply` requires validated backup evidence and updates only rows whose `erasure_due_at IS NULL`. Implement the erasure CLI so audit-only is the default and mutating execution requires `--activate`, backup evidence, and `--limit` in `1..50`; it invokes the same orchestrator and does not toggle scheduler configuration. Readiness requires policy, lifecycle registry, and schema version 73; store outage is degraded capability, not readiness failure. Expose counts/status only.

- [ ] **Step 5: Run scheduler and readiness tests**

```powershell
python -m pytest -q agent/tests/test_erasure_scheduler.py agent/tests/test_erasure_deadline_backfill.py agent/tests/test_erasure_cli.py agent/tests/test_scheduler_source_guard.py agent/tests/test_session_be.py agent/tests/test_config.py
```

- [ ] **Step 6: Commit and review**

```powershell
git add agent/scheduler.py agent/server.py agent/config.py scripts/backfill_erasure_deadlines.py scripts/run_account_erasure.py agent/tests/test_erasure_scheduler.py agent/tests/test_erasure_deadline_backfill.py agent/tests/test_erasure_cli.py agent/tests/test_scheduler_source_guard.py
git commit -m "feat: run erasure lifecycle in audit mode"
```

Review gate: confirm no scheduler SQL policy remains, single-flight/catch-up behavior, safe default, five-minute cadence, non-identifying status, and that any separately approved backfill must run while erasure remains audit-only.

---

### Task 8: Legacy Raw-Data Scrub Tooling

**Files:**
- Create: `scripts/scrub_legacy_personal_data.py`
- Create: `agent/legacy_scrub.py`
- Create: `agent/tests/test_legacy_scrub.py`
- Create: `agent/tests/test_legacy_scrub_source_guard.py`
- Create: `docs/runbooks/personal-data-erasure.md`

**Interfaces:**
- Produces `ScrubPlan`, `ScrubManifest`, `build_scrub_plan(root, *, owner_ids)`, `write_scrub_manifest()`, and a CLI with `--dry-run` default plus explicit `--apply`.
- Requires backup evidence path and validates an immutable before-digest before any apply mutation.
- Writes before/after digests, affected store names/counts, PII-scan result, and tool version; never writes raw content to the manifest.
- Produces the operational runbook for audit-only observation, separately approved deadline backfill, backup gates, `limit=1` activation, per-store verification, normal batches, and the separately approved legacy scrub.

- [ ] **Step 1: Write failing dry-run/backup/source tests**

Assert default invocation performs no writes, reports affected legacy analytics/cost/feedback/memory files and linked structured/operational logs, refuses `--apply` without backup evidence, refuses a changed source digest, and rejects broad recursive deletion or global UUID replacement in source.

- [ ] **Step 2: Run the cross-task matrix and record gaps**

```powershell
python -m pytest -q agent/tests/test_legacy_scrub.py agent/tests/test_legacy_scrub_source_guard.py
```

- [ ] **Step 3: Implement field-scoped scrub planning**

Enumerate only registered file-backed stores, legacy structured/operational log locations, and exact structured fields. Remove exact subject references and redact PII-bearing log fields/messages through the mandatory privacy redactor. Produce a deterministic plan and digest manifest. Keep a quarantine/copy path for backup review; do not silently overwrite files during dry-run.

- [ ] **Step 4: Implement gated apply and post-scan**

Require `--apply`, a backup manifest, an explicit owner set, and matching before-digests. Apply atomic per-file rewrites, write after-digests, re-run the existing PII scanner, and fail closed if any sentinel/reference remains. No production invocation is part of this task.

- [ ] **Step 5: Run tooling tests and CLI help**

```powershell
python -m pytest -q agent/tests/test_legacy_scrub.py agent/tests/test_legacy_scrub_source_guard.py
python scripts/scrub_legacy_personal_data.py --help
```

Complete `docs/runbooks/personal-data-erasure.md` with the exact controlled sequence: keep audit-only enabled; collect due/legacy impact; create file and PostgreSQL backups; apply the deadline backfill only under separate approval; verify the backfill while still audit-only; activate one due account with `limit=1`; verify PostgreSQL plus every registered external store; then consider normal batches. Keep scrub `--apply` as an additional separate gate.

- [ ] **Step 6: Commit and review**

```powershell
git add scripts/scrub_legacy_personal_data.py agent/legacy_scrub.py agent/tests/test_legacy_scrub.py agent/tests/test_legacy_scrub_source_guard.py docs/runbooks/personal-data-erasure.md
git commit -m "feat: add gated legacy personal-data scrub"
```

Review gate: verify dry-run default, backup/digest gates, exact fields, atomic writes, no raw manifest content, and no destructive operation without `--apply`.

---

### Task 9: Lifecycle Integration, Race, And Evidence Tests

**Files:**
- Create: `agent/tests/test_erasure_lifecycle_integration.py`
- Create: `agent/tests/test_erasure_lifecycle_postgres.py`
- Create: `agent/tests/test_erasure_source_guards.py`
- Modify: `agent/tests/test_privacy_source_guards.py`
- Modify: `tests/test_integration.py`

**Interfaces:**
- Produces a deterministic end-to-end fixture that exercises request -> quarantine -> grace -> recovery or hard erasure, including all registered stores.
- Produces source guards for missing owner gates, raw lifecycle SQL in scheduler, unbounded error logging, direct `_reactivate_user` deletion resets, and aggregate stores containing owner-linked columns.

- [ ] **Step 1: Write failing end-to-end matrix**

Cover active account retention, exact 30-day deadline, immediate write blocking, recovery just before/at/after deadline, partial purge retry, residual-store stop, two-user isolation, claim policy, actor anonymization, structured references, aggregate retention, and audit-only scheduler behavior.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_erasure_lifecycle_integration.py agent/tests/test_erasure_lifecycle_postgres.py agent/tests/test_erasure_source_guards.py
```

These are cross-task verification tests rather than a new behavior unit, so they may already pass. Any failure is an integration gap and blocks this task: reopen the responsible earlier task under its reviewed fix loop, add the smallest focused regression, observe RED, fix it there, then rerun this matrix. Do not hide production fixes inside this test-only commit.

- [ ] **Step 3: Implement test fixtures and invariant scanners**

Use ASGI transport for request/recovery contracts and real PostgreSQL for locks, FK actions, transaction rollback, and deletion verification. Keep owner IDs and sentinel values in test data only; assert logs and manifests contain no raw subject data.

- [ ] **Step 4: Run the full lifecycle-focused gate**

```powershell
python -m pytest -q agent/tests/test_erasure_lifecycle_integration.py agent/tests/test_erasure_lifecycle_postgres.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_scheduler.py agent/tests/test_legacy_scrub.py agent/tests/test_erasure_source_guards.py
```

The PostgreSQL group must run with `TRUST_ERASURE_TEST_DATABASE_URL`; missing infrastructure is recorded as a skip/debt, never presented as green evidence.

- [ ] **Step 5: Commit and review**

```powershell
git add agent/tests/test_erasure_lifecycle_integration.py agent/tests/test_erasure_lifecycle_postgres.py agent/tests/test_erasure_source_guards.py agent/tests/test_privacy_source_guards.py tests/test_integration.py
git commit -m "test: verify erasure lifecycle invariants"
```

Review gate: trace each spec acceptance criterion to an executable assertion and verify race tests use real row locks, not only mocks.

---

### Task 10: Verified Erasure Lifecycle Final Gate

**Files:**
- Create: `docs/superpowers/results/2026-07-29-verified-erasure-lifecycle.md`
- Modify: `docs/superpowers/plans/2026-07-29-verified-erasure-lifecycle.md`
- Modify: `docs/superpowers/specs/2026-07-29-trust-erasure-closure-design.md`

**Interfaces:**
- Produces evidence mapping every lifecycle acceptance criterion to commands, migration versions, focused tests, and commits.
- Marks this plan `done` only after all required commands pass or a pre-existing timeout/debt is recorded with exact evidence.
- Does not authorize production activation, deadline backfill `--apply`, scrub `--apply`, deployment, push, or real-data deletion.

- [ ] **Step 1: Run migration and PostgreSQL gates**

```powershell
python -m pytest -q agent/tests/test_erasure_state.py agent/tests/test_erasure_constraints_postgres.py agent/tests/test_structured_reference_cleanup.py agent/tests/test_quarantine.py agent/tests/test_recovery_deadline.py agent/tests/test_erasure_orchestrator_postgres.py agent/tests/test_erasure_lifecycle_postgres.py
```

Run with `TRUST_ERASURE_TEST_DATABASE_URL` already set. Require the disposable PostgreSQL target for completion and record schema version 73 plus constraint introspection output.

- [ ] **Step 2: Run lifecycle integration and scheduler gates**

```powershell
python -m pytest -q agent/tests/test_owner_write_gate.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_erasure_orchestrator.py agent/tests/test_erasure_scheduler.py agent/tests/test_erasure_deadline_backfill.py agent/tests/test_erasure_cli.py agent/tests/test_legacy_scrub.py agent/tests/test_erasure_lifecycle_integration.py
```

- [ ] **Step 3: Run repository gates**

```powershell
git diff --check
python scripts/checks/run_hard.py --staged
python -m pytest -q
```

The full baseline must be allowed to finish; if the known closed-release rehearsal exceeds the configured limit, record elapsed time, last observed case, and focused-suite success without calling it a pass.

- [ ] **Step 4: Write result evidence**

Create the result document with status, commit list, exact commands, pass/skip/timeout counts, PostgreSQL target safety statement, registry inventory, FK-action table, deadline/race evidence, audit-only activation state, and a requirement-by-requirement table for immediate quarantine, recovery, hard erasure, batch isolation, claim anonymization, aggregate retention, and scrub safety.

- [ ] **Step 5: Mark documentation status and commit**

Change this plan status to `done`. Update the shared spec status to say both implementation plans are complete only if the Runtime Trust Boundary result is also complete; otherwise state exactly which plan remains pending. Do not imply production deletion or scrub activation.

```powershell
git add docs/superpowers/results/2026-07-29-verified-erasure-lifecycle.md docs/superpowers/plans/2026-07-29-verified-erasure-lifecycle.md docs/superpowers/specs/2026-07-29-trust-erasure-closure-design.md
git commit -m "docs: record verified erasure lifecycle evidence"
```

Final review gate: an independent reviewer compares result evidence, migration introspection, and the approved design before any activation gate is considered.
