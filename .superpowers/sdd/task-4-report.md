# Task 4 Report

Status: GREEN (review remediation)

Commit SHAs: `594aebf2`, `eae82e22`, `52de64f9`, `30bba3c7`, `b679c4cc`, `9c33118c`, `e22ab2e7`

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
