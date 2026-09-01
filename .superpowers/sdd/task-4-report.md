# Task 4 Report

Status: GREEN (review remediation)

Commit SHAs: `594aebf2..HEAD` (including `eae82e22`, `52de64f9`, `cf3127de`, `30bba3c7`, `6a37ae9b`, `b679c4cc`, `62c1f8ef`, `9c33118c`, `763a9651`, `e22ab2e7`, `a9f7462c`, `f523b580`, `e331ec64`, `e3bbe0c9`, `6cf852dc`, `a46d0d57`, `11cb0a0b`, and `46fd7b33`).

Files changed:

- `agent/cases/wiring.py`
- `agent/cases/correction.py`
- `agent/cases/service.py`
- `agent/cases/store.py`
- `agent/cases/audit.py`
- `agent/cases/publication.py`
- `agent/cases/admin_api.py`
- `agent/control_plane/audit.py`
- `agent/tests/test_case_proof_first.py`
- `agent/tests/test_case_store.py`
- `agent/tests/test_case_admin_api.py`
- `agent/tests/test_correction_decisions.py`
- `agent/tests/test_correction_journey_postgres.py`
- `agent/tests/test_case_public_api.py`
- `agent/tests/test_correction_admin_http.py`
- `agent/tests/test_correction_create.py`
- `agent/tests/test_correction_changesets.py`
- `agent/tests/test_correction_publication.py`
- `agent/tests/test_correction_publication_failure.py`
- `agent/tests/test_correction_rollback.py`

TDD evidence:

- RED: `python -m pytest agent/tests/test_case_proof_first.py -q --basetemp .tmp-task4-red` -> 7 failed (missing dependency bundle, evidence guards, and audit envelope interfaces).
- GREEN: `python -m pytest agent/tests/test_case_proof_first.py -q --basetemp .tmp-task4-green3` -> 7 passed.
- Focused: `python -m pytest agent/tests/test_case_wiring.py agent/tests/test_case_domain.py agent/tests/test_case_audit.py agent/tests/test_case_outbox.py agent/tests/test_case_idempotency_postgres.py -q --basetemp .tmp-task4-focused` -> 43 passed, 20 skipped.
- Regression: `python -m pytest agent/tests/test_correction_decisions.py agent/tests/test_correction_evidence.py agent/tests/test_correction_publication.py agent/tests/test_correction_changesets.py -q --basetemp .tmp-task4-regression2` -> 33 passed, 35 skipped.
- HTTP: `python -m pytest agent/tests/test_case_public_api.py agent/tests/test_correction_http_journey.py -q --basetemp .tmp-task4-http` -> 51 passed, 17 skipped, 1 existing Starlette deprecation warning.

Implementation notes:

- Dependency construction is immutable and publication is reset on any configure failure; disabled kernels are explicitly dormant.
- Evidence writes reject naive/future/expired/out-of-order timestamps; decisions filter through `usable_evidence` immediately before ruling.
- Decision and publication mutations emit one shared `AuditEvent`/outbox envelope carrying case, revision, generation and correlation metadata; responses expose persisted revision and event id.

Concerns:

- PostgreSQL tests were skipped because no disposable loopback `VL360_TEST_DATABASE_URL` was configured.
- Existing schema stores generation metadata in the outbox descriptor; no production migration was added in this scoped slice.

## Review remediation

Findings fixed:

- `validate_decision()` now requires the explicit command/field-policy scope and rejects an all-wrong-scope evidence set as `evidence_not_usable`; it never derives scope from the first record.
- Admin decisions derive the required scope from the stored correction field (`EVIDENCE_SCOPE_BY_FIELD_PATH`), and the verification response returns persisted `revision` and `outbox_event_id`.
- The real `CaseTransaction` fallback now carries event id, resource id, revision, generation and correlation id in `CaseAuditDraft`; `CaseTransaction.append_audit()` stores that envelope in the existing JSONB snapshot descriptor, while the outbox stores the same envelope without a migration.

TDD evidence for the review fixes:

- RED: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_case_store.py agent/tests/test_case_admin_api.py -q --basetemp .tmp-task4-review-red` -> 6 failed, 100 passed, 9 skipped (scope inference, unusable evidence, fallback envelope, durable descriptor, verification response, and stale route-double fields).
- GREEN proof: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_case_store.py agent/tests/test_case_admin_api.py -q --basetemp .tmp-task4-review-green1` -> 106 passed, 9 skipped.
- Focused domain/store: `python -m pytest agent/tests/test_correction_decisions.py agent/tests/test_correction_evidence.py agent/tests/test_case_domain.py -q --basetemp .tmp-task4-review-domain` -> 37 passed, 5 skipped.
- Focused Task 4: `python -m pytest agent/tests/test_case_wiring.py agent/tests/test_case_domain.py agent/tests/test_case_audit.py agent/tests/test_case_outbox.py agent/tests/test_case_idempotency_postgres.py -q --basetemp .tmp-task4-review-focused` -> 43 passed, 20 skipped.
- Correction/admin/store regression: `python -m pytest agent/tests/test_correction_decisions.py agent/tests/test_correction_evidence.py agent/tests/test_correction_publication.py agent/tests/test_correction_admin_http.py agent/tests/test_case_admin_api.py agent/tests/test_case_store.py agent/tests/test_case_proof_first.py -q --basetemp .tmp-task4-review-regression` -> 129 passed, 42 skipped.
- HTTP regression: `python -m pytest agent/tests/test_case_public_api.py agent/tests/test_correction_http_journey.py agent/tests/test_correction_admin_http.py -q --basetemp .tmp-task4-review-http` -> 51 passed, 25 skipped, 1 existing Starlette deprecation warning.
- PostgreSQL proof: `python -m pytest agent/tests/test_case_transaction_postgres.py -q --basetemp .tmp-task4-review-pgproof` -> 8 skipped because `VL360_TEST_DATABASE_URL` is not configured.

## Retry/audit remediation

Findings fixed:

- Decision retries use a stable case/item idempotency key, persist a command digest plus replay-safe ruling envelope, and return the original revision/event instead of inserting a second decision or colliding on the unique outbox key.
- Already-verified projection checks replay the committed verification receipt before lease/fetch/mutation, so a lost response cannot advance the case, complete work twice, or emit another transition/audit/outbox row.
- Verification failures record the actual check time in audit and keep the recovery `next_update_at` only as the outbox availability time.
- Audit fallback now carries actor scopes, channel, and policy revision; create responses expose the committed revision and received outbox event id, including idempotent replays.

TDD evidence for the retry/audit remediation:

- RED: `python -m pytest agent/tests/test_case_proof_first.py -q --basetemp .tmp-task4-retry-red-unit` -> 2 failed (audit metadata and occurrence/availability separation missing).
- GREEN: `python -m pytest agent/tests/test_case_proof_first.py -q --basetemp .tmp-task4-retry-green-unit` -> 17 passed.
- PG retry proof: decision retry, verified retry, failure timestamp, and create response tests -> 4 passed in 4.75s.
- PG correction/admin regression: `python -m pytest agent/tests/test_correction_decisions.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_admin_http.py agent/tests/test_correction_create.py agent/tests/test_case_public_api.py -q --basetemp .tmp-task4-pg-focused-final` -> 140 passed, 1 warning in 14.43s.
- PG Task 4 suites: `python -m pytest agent/tests/test_case_wiring.py agent/tests/test_case_domain.py agent/tests/test_case_audit.py agent/tests/test_case_outbox.py agent/tests/test_case_idempotency_postgres.py agent/tests/test_case_proof_first.py agent/tests/test_case_store.py agent/tests/test_case_admin_api.py -q --basetemp .tmp-task4-pg-task4-final` -> 186 passed in 8.73s.
- Disposable PG evidence: created `vl360_case_task4_retry_20260901` on loopback `127.0.0.1:5433`, applied the full migration chain through schema 82, ran the PG suites, then dropped the database and verified it no longer existed. The local default skip root cause was unset `VL360_TEST_DATABASE_URL`; host PostgreSQL and production databases were not touched.
- Full disposable PG gate (from the independent integration run): `27 passed in 9.24s` after create/migrate; database was dropped and final existence check returned null.

Concerns:

- R30.7 remains a pre-existing generated frontend bundle debt (802kB gz > 800kB); this backend-only commit used the documented soft skip for the commit hook and changed no frontend files.
- Existing schema stores event generation and replay metadata in outbox JSON; no production migration was added in this scoped slice.

## Retry/audit final remediation

Findings fixed:

- Apply and rollback now replay the committed receipt after a lost response, bypassing a second entity mutation, case revision, transition, audit row or outbox intent; receipts retain persisted entity and case revisions.
- Verification failures use a stable change-set event key and replay the original mismatches and recovery deadline instead of deriving a new key from `now` or fetching the projection again.
- Building a change set now detects the same case/item selection under the case lock, validates the persisted build digest, and replays the original change-set draft without duplicate change sets, work items, audit rows or outbox intents.
- Audit fallback stores the declared `reason`, `resource_type`, `action`, actor scopes, channel and policy revision; invalid or missing channels are rejected rather than coerced to `WEB`.

Focused TDD evidence:

- RED: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_rollback.py agent/tests/test_correction_changesets.py -q --basetemp .tmp-task4-retry-red-pg` -> 4 failed, 26 passed, 58 skipped (audit reason/resource metadata and invalid-channel guard were missing).
- GREEN: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_correction_changesets.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_rollback.py -q --basetemp .tmp-task4-retry-green-unit` -> 30 passed, 58 skipped.
- Covering: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_correction_decisions.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_create.py agent/tests/test_case_store.py agent/tests/test_case_audit.py agent/tests/test_case_outbox.py agent/tests/test_case_admin_api.py agent/tests/test_case_public_api.py agent/tests/test_correction_admin_http.py -q --basetemp .tmp-task4-covering-no-pg2` -> 218 passed, 82 skipped, 1 existing Starlette deprecation warning.
- Required final gate: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_correction_decisions.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_create.py agent/tests/test_case_store.py agent/tests/test_case_audit.py agent/tests/test_case_outbox.py agent/tests/test_case_admin_api.py agent/tests/test_case_public_api.py agent/tests/test_correction_admin_http.py agent/tests/test_case_wiring.py agent/tests/test_case_domain.py agent/tests/test_case_idempotency_postgres.py -q --basetemp .tmp-task4-required-final` -> 240 passed, 90 skipped, 1 existing Starlette deprecation warning.
- PostgreSQL retry tests are included in `test_correction_changesets.py`, `test_correction_publication.py`, `test_correction_publication_failure.py` and `test_correction_rollback.py`; this workspace has no `VL360_TEST_DATABASE_URL`, so those tests skip under the loopback-only guard.

## Recovery/reason final remediation

- Verification failure receipts replay during the promised retry window but permit a new projection check at the recovery deadline; a recovered projection can now complete exactly once.
- Rollback preserves the caller-provided `reason_code` (for example `source_retracted`) while retaining the stable audit action `change_set_rolled_back`.
- Replay helpers fail closed with `publication_receipt_missing` or `publication_receipt_invalid` when a committed state marker has no complete outbox receipt; they never fabricate revision/event metadata.

Fresh focused verification: `python -m pytest agent/tests/test_case_proof_first.py agent/tests/test_correction_changesets.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_rollback.py -q --basetemp .tmp-task4-recovery-controller` -> `30 passed, 60 skipped in 5.05s`.

Disposable PostgreSQL verification: `powershell -ExecutionPolicy Bypass -File .tmp-task4-pg-run.ps1` created a loopback-only cluster on `127.0.0.1:5433`, applied migrations through schema 82, then ran `agent/tests/test_case_idempotency_postgres.py`, `agent/tests/test_correction_changesets.py`, `agent/tests/test_correction_publication.py`, `agent/tests/test_correction_publication_failure.py`, and `agent/tests/test_correction_rollback.py`. It reported `79 passed in 27.70s`; the follow-up recovery-deadline regression reported `80 passed in 27.60s`. Each run dropped the disposable database and confirmed `database after drop: None`.

The final Task 4 commit range is `594aebf2..HEAD`; changed test files include `test_correction_changesets.py`, `test_correction_publication.py`, `test_correction_publication_failure.py`, and `test_correction_rollback.py`. The backend-only commits used approved `--no-verify` where the known R30.7 generated frontend-bundle debt blocked the hook; no frontend files changed.
