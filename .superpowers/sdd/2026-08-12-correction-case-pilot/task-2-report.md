# Task 2 report

## Status

Implemented additive migration 080, fresh `init.sql` parity, schema version/readiness registration, and dormant-versus-enabled Case Kernel readiness behavior. No production import, cutover, legacy mutation, or SQLite Case Kernel path was added.

## Files changed

- `agent/migrations/080_correction_case_kernel.sql`
- `init.sql`
- `agent/database.py`, `agent/server.py`
- `agent/tests/test_migration_chain.py`, `agent/tests/test_migration_apply.py`, `agent/tests/test_case_schema_postgres.py`
- Compatibility/readiness expectations: `agent/tests/test_migration_readiness_postgres.py`, `agent/tests/test_database.py`, `agent/tests/test_pg_schema_readiness.py`

## RED evidence

Command:

`python -m pytest -q agent/tests/test_migration_chain.py agent/tests/test_case_schema_postgres.py agent/tests/test_migration_apply.py`

Result before implementation: `4 failed, 28 passed, 9 skipped`. The failures were the intended missing behavior: migration 080 absent, case tables absent from `init.sql`, `entities.revision` absent, and readiness still fixed at schema version 79. PostgreSQL tests skipped at this first RED invocation because no explicit disposable DSN had yet been injected.

## PostgreSQL target

- Server: local PostgreSQL 16 on `127.0.0.1:5432`.
- Disposable databases created for this task: `vl360_case_task2_test` and `vl360_case_task2_fresh_test`.
- Test DSNs were supplied only through the repository's guarded `VL360_TEST_DATABASE_URL` and `MIGRATION_APPLY_TEST_DATABASE_URL` mechanisms; both names contain `test` and resolve to loopback.
- No ambient `DATABASE_URL` or non-loopback target was used.

## GREEN evidence

- Required PostgreSQL gate:
  `python -m pytest -q agent/tests/test_migration_chain.py agent/tests/test_case_schema_postgres.py agent/tests/test_migration_apply.py agent/tests/test_migration_readiness_postgres.py`
  -> `58 passed`.
- Relevant compatibility/readiness gate:
  `python -m pytest -q agent/tests/test_database.py agent/tests/test_pg_schema_readiness.py agent/tests/test_case_policy.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_privacy_policy.py`
  -> `233 passed, 1 xfailed` (the xfail is pre-existing/expected in the database suite).
- Combined focused verification earlier in the same final phase:
  -> `291 passed, 1 xfailed`.
- Ruff:
  `python -m ruff check agent/database.py agent/server.py agent/tests/test_database.py agent/tests/test_migration_apply.py agent/tests/test_migration_chain.py agent/tests/test_migration_readiness_postgres.py agent/tests/test_pg_schema_readiness.py agent/tests/test_case_schema_postgres.py`
  -> `All checks passed!`.
- Fresh-schema parity script applied the full migration chain, captured all Case Kernel/correction columns, rebuilt the database from `init.sql`, and compared `(table, column, type, nullability, default)` row-for-row -> `parity rows: 188`.
- `git diff --check` returned exit 0.

## Implementation notes

- All nineteen required tables use UUID primary keys and are owned by `vl360`.
- Canonical domain values are bounded with database checks matching the locked Task 1 contracts.
- Private material uses digests or concrete `*_enc` columns; there are no plaintext capability/contact/evidence content columns.
- Immutable transition/audit ledgers reject database updates/deletes; current case state remains a mutable revisioned snapshot rather than event sourcing.
- Queue, promise, outbox retry, access-expiry, and legacy-reconciliation indexes are partial/ordered as required.
- `entities.revision` is additive, defaults to 1, and has a positive constraint; there is no content-changing entity backfill and `attributes.verifiedAt` is untouched.
- Readiness registers the complete version-80 table/column contract. Core runtime remains gated at version 79 while all case flags are false; Case Kernel reports stable dormant codes. Enabled Case Kernel requires PostgreSQL and a clean version-80 case schema/policy result.

## Self-review

- Confirmed migration 080 contains no `DROP TABLE`, `TRUNCATE`, or `DELETE FROM` and uses monotonic schema-version upsert.
- Confirmed no production data mutation/import/cutover and no SQLite shadow tables.
- Confirmed `review_of_case_id` is on `cases`; the cross-row closed-case rule remains intentionally deferred to service guards.
- Confirmed owners, foreign keys, named constraints, digest shape, active lease uniqueness, idempotency expiry, change-set base revision, legacy locator uniqueness, and ledger immutability through real PostgreSQL inspection/execution.
- Confirmed migration and fresh schema parity for all 188 Case Kernel/correction column definitions.

## Commit

`dac9960b feat: add correction case schema`

## Concerns

- The existing readiness response continues to expose the repository's general schema snapshot under `schema_version`; Case Kernel-specific public checks are redacted to stable codes and do not expose DSN/schema contents.
- The case schema is intentionally broad enough for Tasks 4, 5, 11, and 17. Service-level guards and transaction methods are not implemented in Task 2.

## Fix round 1

### Finding resolutions

- Moved `entities.revision` exclusively into `CASE_KERNEL_REQUIRED_COLUMNS`, so core schema-79 readiness remains dormant-compatible while enabled Case Kernel readiness requires it; also registered `cases.severity`.
- Enabled `/health/ready` now revalidates the live encryption-key and owner settings on each probe and reports only stable redacted codes: `case_encryption_key_required` and `case_owner_individual_required`.
- Bound `case_decisions.outcome_code` and both `case_transitions` phases with PostgreSQL checks for the locked domain values; real PostgreSQL tests inspect the generated definitions.
- Replaced `correction_change_sets.item_ids` with relational `correction_change_set_items`, foreign keys, same-case trigger enforcement, and immutability triggers in both migration 080 and `init.sql`.
- Added the missing reverse integrity guard: a correction item already linked to a change set cannot be reassigned to a different case, preventing post-link same-case drift.

### RED evidence

- `VL360_TEST_DATABASE_URL=postgresql://...@127.0.0.1:5432/vl360_case_task2_test python -m pytest -q agent/tests/test_case_schema_postgres.py -k change_set_item_linkage`
  -> `1 failed, 8 deselected`: updating a linked `correction_items.case_id` to another case did not raise. This isolated the post-link same-case enforcement gap.

### GREEN evidence

- After rebuilding only the guarded loopback disposable schema through `MIGRATION_APPLY_TEST_DATABASE_URL=postgresql://...@127.0.0.1:5432/vl360_case_task2_test`, the same regression command -> `1 passed, 8 deselected`.
- Required Task 2 gate:
  `python -m pytest -q agent/tests/test_migration_chain.py agent/tests/test_case_schema_postgres.py agent/tests/test_migration_apply.py agent/tests/test_migration_readiness_postgres.py`
  with guarded loopback `VL360_TEST_DATABASE_URL` and `MIGRATION_APPLY_TEST_DATABASE_URL` -> `63 passed`.
- Compatibility/readiness gate:
  `python -m pytest -q agent/tests/test_database.py agent/tests/test_pg_schema_readiness.py agent/tests/test_case_policy.py agent/tests/test_data_lifecycle_registry.py agent/tests/test_privacy_policy.py`
  -> `233 passed, 1 xfailed` (pre-existing expected xfail).
- Ruff on all touched Python files -> `All checks passed!`.
- `git diff --check` -> exit 0.
- Fresh full migration-chain versus `init.sql` parity for the Task 2 tables plus `entities.revision`, comparing `(table, column, type, nullability, default)` -> `Task 2 case schema column parity: 191 rows`.

### Self-review

- Confirmed replay order: the immutable-ledger function is defined before every new trigger that invokes it; all trigger creation remains idempotent with `DROP TRIGGER IF EXISTS`.
- Confirmed linkage deletion is blocked before FK cascade paths can bypass ledger immutability, and linked item case moves are independently guarded.
- Confirmed the dormant status projection does not inspect key/owner configuration and schema-79 core columns exclude the Case Kernel-only entity revision.

### Commit

This fix round's scoped commit contains this report entry.

## Fix round 2

### Finding resolutions

- Tightened `case_decisions.outcome_code` to exactly the seven `CorrectionOutcome` values in migration 080 and `init.sql`; `accepted` and `rejected` are no longer valid decision outcomes.
- Verified the reviewer replay premise against `scripts/apply_migrations.py`: the normal runner applies only migrations with a version greater than `schema_version`, so an already-version-80 provisional database does not rerun edited 080 automatically.
- Kept the locked one-migration/080 plan. Directly rerunning 080 now idempotently reconciles its own provisional shape: it replaces named outcome and transition checks, copies validated JSONB `item_ids` into `correction_change_set_items`, then removes the obsolete column and installs the relational triggers.
- Reconciliation fails closed with `correction_change_set_item_ids_unmigratable` if legacy `item_ids` is not an array, contains a non-string/non-UUID value, or references an item outside its change set's case. No values are discarded.

### RED evidence

- `VL360_TEST_DATABASE_URL=postgresql://...@127.0.0.1:5432/vl360_case_task2_test python -m pytest -q agent/tests/test_case_schema_postgres.py -k "outcome_constraint or rerunning_080"`
  -> `2 failed, 9 deselected`: provisional 080 accepted invalid outcome values and did not reconcile an old `dac9960b` shape. The first attempt also exposed and then fixed a Windows-only test-helper decoding error before the schema fixture could run.
- The focused outcome/replay command initially confirmed the exact constraint failure; after adding the replay test it exercised direct old-080 then current-080 execution, not the normal version-gated runner.

### GREEN evidence

- Focused exact outcome/replay coverage -> `2 passed, 9 deselected`.
- Fail-closed malformed replay coverage:
  `VL360_TEST_DATABASE_URL=postgresql://...@127.0.0.1:5432/vl360_case_task2_test python -m pytest -q agent/tests/test_case_schema_postgres.py -k "rerunning_080"`
  -> `2 passed, 10 deselected`.
- Required Task 2 gate with guarded loopback `VL360_TEST_DATABASE_URL` and `MIGRATION_APPLY_TEST_DATABASE_URL` -> `65 passed`.
- Compatibility/readiness gate -> `233 passed, 1 xfailed` (pre-existing expected xfail).
- Ruff on touched Python -> `All checks passed!`; `python scripts/check_migration_gate.py` -> `OK`; `git diff --check` -> exit 0.
- Fresh migration-chain versus `init.sql` parity on Task 2 tables plus `entities.revision`, comparing `(table, column, type, nullability, default)` -> `Task 2 case schema column parity: 191 rows`.

### Self-review

- The normal runner still intentionally does not rerun version 80. The direct replay path is specifically idempotent for the unmerged provisional migration shape, satisfying the task's replay-safe requirement without introducing prohibited migration 081.
- The data validation occurs before `item_ids` removal in the same transaction; a failure rolls back the link copy and preserves the prior JSONB column/data.
- Fresh `init.sql` remains at the final relational shape and matches the current migration chain column-for-column.

### Commit

Pending this fix-round commit.
