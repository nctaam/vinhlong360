# Task 4 Report

Status: GREEN

Commit SHAs: `594aebf2`, `eae82e22`, `52de64f9`, `30bba3c7`

Files changed:

- `agent/cases/wiring.py`
- `agent/cases/correction.py`
- `agent/cases/publication.py`
- `agent/cases/admin_api.py`
- `agent/control_plane/audit.py`
- `agent/tests/test_case_proof_first.py`

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
