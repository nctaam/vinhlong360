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
