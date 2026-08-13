# Task 4 Report: PostgreSQL Case Store

## Status
DONE. The PostgreSQL-only correction-case transaction boundary, canonical audit drafts, typed row mapping, CAS updates, append-only ledgers, and secret-free outbox participation are implemented.

## Files
- Added `agent/cases/store.py` and `agent/cases/audit.py`.
- Added `agent/tests/test_case_store.py`, `agent/tests/test_case_transaction_postgres.py`, and the narrow R20.7 pairing test `agent/tests/test_case_audit.py`.

## RED Evidence
- Initial command: `python -m pytest -q agent/tests/test_case_store.py agent/tests/test_case_transaction_postgres.py`.
- Result: collection failed in both files with `ModuleNotFoundError: No module named 'cases.audit'`, proving the requested audit/store boundaries were absent.
- Later focused RED cycles caught and then fixed: non-incrementing CAS snapshots (`2 failed, 7 passed` together with the audit allowlist case), direct non-allowlisted audit mappings, and transaction reuse after context exit (`1 failed, 9 passed`).

## GREEN Evidence
- Guarded real PostgreSQL focused suite on a uniquely named disposable loopback database -> `14 passed` before the final lifecycle hardening.
- Expanded disposable PostgreSQL regression covering store, database, migration apply/chain, schema 080, and Task 3 domain/transition/queue mapping -> `445 passed, 1 xfailed`.
- Final requested local suite without ambient DSN -> `201 passed, 7 skipped, 1 xfailed`; the seven skips are only the explicit loopback-DSN PostgreSQL tests already exercised above.
- Ruff on all four touched Python files -> `All checks passed!`.
- `git diff --check` -> exit 0.

## Transaction Design
- `PostgresCaseStore.transaction()` owns exactly one `db._conn(commit_on_success=False)` connection and constructs one connection-bound `CaseTransaction`.
- Clean exit explicitly calls `conn.commit()` once. No exception rollback is issued by the store; the existing `Database._conn` exceptional path performs the single rollback. On clean exit, `_conn(commit_on_success=False)` performs its documented final rollback after the explicit commit, leaving no open transaction.
- Every insert, audit, transition, outbox, load, and CAS method uses the transaction's connection. The transaction is invalidated in `finally` and rejects use after exit.
- `load_case(for_update=True)` emits `SELECT ... FOR UPDATE`. CAS uses `UPDATE ... WHERE case_id=%s AND current_revision=%s RETURNING`; a miss loads the current typed snapshot on the same connection and raises `RevisionConflict(current)`, or `CaseNotFound`.

## Boundary And Privacy Review
- PostgreSQL rows are copied to exact frozen `CaseSnapshot` objects with enum fields and persisted promise clocks; driver row objects never cross the boundary.
- Inputs are frozen typed drafts. SQL values are parameterized; the only dynamic SQL fragments are fixed internal column lists and the boolean-selected `FOR UPDATE` suffix.
- `CaseAuditDraft` sorts scopes deterministically, requires exact `Channel`, freezes projections, and allowlists only state/revision/promise-facing metadata. It omits service/category, reporter privacy, owner, waiting details, contacts, ciphertext, evidence, capabilities, and receipts.
- `OutboxDraft` requires a caller-supplied deterministic idempotency key, freezes a generic JSON descriptor, and rejects contact/phone/email/evidence/capability/receipt/secret/plaintext descriptor keys recursively. The store generates no random identifiers or keys.
- Repository methods expose only `append_transition` and `append_audit`; no update/delete ledger method exists. Real PostgreSQL tests also prove the schema triggers reject deletion.

## Atomicity And Concurrency Review
- Real PostgreSQL tests prove all create rows commit together and injected failures after interaction, audit, and outbox insertion roll back the entire unit.
- A two-writer test proves exactly one CAS update succeeds and the loser receives `RevisionConflict` carrying revision 2.
- A lock test proves a second `SELECT ... FOR UPDATE` blocks until the first transaction exits.
- Unit connection doubles prove one `_conn` acquisition, one connection across all methods, one explicit commit on success, and one exception rollback from `Database._conn`.

## Commit
- Commit created after the staged R20.7/hard gate with message `feat: persist correction cases atomically`.

## Concerns
- None. The disposable test database was dropped after verification.

## Fix round 1

### Review Verification And RED
- Verified the audit finding: direct drafts accepted nested contact/evidence/capability mappings, bytes, objects, enums, datetimes, and non-finite floats beneath allowlisted top-level fields. The focused RED command reported `10 failed, 4 passed`.
- Verified the lock-test finding: the previous event fired before the contender opened its transaction. Replacing it with a `pg_stat_activity` lock-wait assertion initially failed (`1 failed`) because the contender had no unique PostgreSQL application marker.

### Changes
- Replaced the shallow audit-key allowlist with a field-specific scalar schema. Audit projections now require known enum strings, positive integer revisions, required/optional text, and canonical timezone-aware ISO timestamps. Nested containers, bytes, arbitrary objects, domain enum objects in direct mappings, datetimes in direct mappings, and non-finite floats are rejected.
- `safe_case_projection()` explicitly canonicalizes normal frozen domain enum and datetime values into the same schema accepted by direct drafts. Both paths produce immutable, JSON-safe mappings.
- `append_audit()` revalidates and serializes both projections with `allow_nan=False` before executing audit SQL. Unit coverage proves no audit SQL is attempted for a corrupted draft; real PostgreSQL coverage proves an earlier case insert rolls back when audit validation fails.
- The row-lock test sets a unique transaction-local `application_name` immediately before `SELECT ... FOR UPDATE`, then polls `pg_stat_activity` until PostgreSQL reports `wait_event_type='Lock'` for that exact query. It surfaces contender exceptions while polling, asserts the contender has not acquired the row, releases the first transaction, and then requires bounded acquisition.

### GREEN And Gates
- Focused audit suite -> `14 passed`; audit module -> `12 passed`; deterministic lock test -> `1 passed`; lock plus rollback regression -> `2 passed`.
- Expanded disposable PostgreSQL store/database/schema/migration/Task 3 regression -> `460 passed, 1 xfailed`.
- Final local requested suite -> `215 passed, 7 skipped, 1 xfailed`; the seven skips are the explicitly guarded PostgreSQL cases already exercised on the disposable database.
- Touched-file Ruff -> `All checks passed!`; `git diff --check` -> exit 0. The staged R20.7/hard gate follows this report update.

### Concerns
- None. The disposable database is dropped after the final staged verification.
