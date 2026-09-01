# Task 8 Report: Entity Mutation Audit and Image Approval Saga

## RED

- `python -m pytest agent/tests/test_media_saga.py -q --basetemp .tmp-task8-red`
- Initial result: `3 failed`; `control_plane.saga` was absent, proving the saga and audit envelope contract was not implemented.
- Follow-up RED: claim and provisional audit tests failed with missing `_apply_claim_decision` and `_record_provisional_decision` helpers.

## GREEN

- `python -m pytest agent/tests/test_media_saga.py agent/tests/test_media_gallery.py agent/tests/test_admin_mutations.py agent/tests/test_media_policy.py -q --basetemp .tmp-task8-final2`
- Result: `70 passed, 8 skipped, 1 warning`.
- `python -m py_compile agent/control_plane/saga.py agent/database.py agent/image_suggestions.py agent/entities/admin_api.py` passed.
- `git diff --check` passed.

## Changes

- Added `SagaStep`, `SagaReceipt`, `run_saga`, immutable `MutationAuditEnvelope`, and `approve_image_suggestion` in `agent/control_plane/saga.py`.
- Added SQLite `entity_mutation_audit` storage plus PostgreSQL `admin_audit_events` envelope persistence and retrieval in `agent/database.py`.
- Routed entity create/update/delete, image add/remove/upload, place assignment, bulk place/delete, relationship add/delete/bulk, and featured toggles through actor/reason/correlation/revision/before/after audit metadata.
- Added pending-only status CAS in `image_suggestions.mark_status`; image approval compensates provider objects on upload/commit failure and replays exact idempotency retries.
- Added transactional claim approve/reject CAS audit and provisional approve/reject audit helpers in `agent/entities/admin_api.py`.
- Added saga, gallery, claim, provisional, compensation, and idempotency tests.

## PostgreSQL Evidence

- No production database or provider was touched.
- Disposable PostgreSQL evidence was not run in this workspace because `VL360_TEST_DATABASE_URL` was not configured; PostgreSQL-only claim routes remain covered by SQL/CAS implementation and existing PG test skip policy.

## Concerns

- Generic `run_saga` receipts remain process-local; image approval itself uses durable shared idempotency/CAS.
- Provisional JSON and DB remain separate stores; DB/audit failures trigger compensating JSON rollback, but no single physical cross-store transaction exists.

## Fix Pass

- Added durable request-idempotency receipt lookup and pending suggestion CAS using the shared Task 7 idempotency table; same-key retries without a receipt return `in_progress`, while cross-key claims lose deterministically.
- Image approval now preserves real entity revisions, compensates partial/late storage writes (including commit/generation failure), and invalidates exactly once after commit.
- SQLite entity schema now carries `revision`; no-op upserts preserve revision while content changes increment it.
- Bulk delete, bulk place, and bulk relationship responses include deterministic per-item `outcomes` while retaining legacy counters/arrays.
- Provisional approve/reject now roll back the JSON CAS mutation when the DB/audit write fails; audit metadata is passed through the DB mutation boundary.
- Focused fix evidence: `python -m pytest agent/tests/test_kb_curation.py -q --basetemp .tmp-task8-kbgreen` -> `17 passed in 4.22s`; media/admin/database focused suite -> `280 passed, 8 skipped, 1 xfailed in 24.34s`.
- No production DB/provider side effects; no disposable PG URL was configured.
## Fix Pass

- Added durable request-idempotency receipt lookup and pending suggestion CAS using the shared Task 7 idempotency table; same-key retries without a receipt return in_progress, while cross-key claims lose deterministically.
- Image approval now preserves real entity revisions, compensates partial/late storage writes (including commit/generation failure), and invalidates exactly once after commit.
- SQLite entity schema now carries evision; no-op upserts preserve revision while content changes increment it.
- Bulk delete, bulk place, and bulk relationship responses include deterministic per-item outcomes while retaining legacy counters/arrays.
- Provisional approve/reject now roll back the JSON CAS mutation when the DB/audit write fails; audit metadata is passed through the DB mutation boundary.
- Focused fix evidence: python -m pytest agent/tests/test_kb_curation.py -q --basetemp .tmp-task8-kbgreen -> 17 passed in 4.22s; media/admin/database focused suite -> 280 passed, 8 skipped, 1 xfailed (final run output reached 74% before harness truncation; prior complete run was 280 passed, 8 skipped, 1 xfailed in 24.34s).
- No production DB/provider side effects; no disposable PG URL was configured.

## Updated Concerns

- Generic un_saga receipts remain process-local; image approval itself uses durable shared idempotency/CAS. Claim/provisional JSON and DB are separate stores, with compensating rollback on DB failure but no single physical cross-store transaction.

## Re-review Remediation

- Direct uploads now distinguish pre-commit DB failures from committed-but-degraded post-commit effects; committed media is preserved and returned with `uploaded_degraded` plus effect metadata.
- Generic saga keys now hash the idempotency key and deterministic step metadata; reused keys with a different step set return a durable idempotency conflict.
- Image approval locks the entity row on PostgreSQL and serializes local approvals while merging against the latest entity snapshot, preventing lost images/credits.
- Provisional promotion writes JSON under CAS before DB sync and reports `reconciliation_required` for uncertain committed effects; rejection rollback restores only an unchanged post-delete version.
- Focused remediation evidence: `python -m pytest agent/tests/test_media_saga.py agent/tests/test_kb_curation.py agent/tests/test_entities_admin_api_boundary.py agent/tests/test_entity_write_transaction.py agent/tests/test_entity_write_compatibility.py -q` -> `47 passed, 23 skipped`.

## Final Curation Remediation

- Committed-but-degraded DB deletes now retain the JSON rejection and return `degraded` plus `reconciliation_required`; they never restore an entity that the DB may already have deleted.
- Manual provisional promotion now likewise retains its committed JSON state and returns an explicit degraded reconciliation result when the DB mutation committed but a post-commit effect failed.
