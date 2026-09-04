# Task 8 P1 Review Remediation Implementation Plan

> STATUS: complete

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Task 8 entity/media mutations durable, truthful after commit, compensating before commit, and safe under partial or concurrent failure.

**Architecture:** Keep the database commit as the authoritative mutation boundary. Storage is compensated only before that boundary; invalidation becomes a separately recorded best-effort post-commit effect. JSON KB mutations use targeted CAS reversals, and generic sagas use the existing durable request-idempotency ledger.

**Tech Stack:** Python 3, FastAPI, PostgreSQL/SQLite database adapters, JSON CAS store, pytest.

## Global Constraints

- Preserve existing user changes and only stage Task 8 source/tests plus this plan.
- Add a focused RED test before each production behavior change.
- Do not contact production databases or object/CDN providers.
- A committed entity mutation must never be compensated because cache invalidation failed.

---

### Task 1: Commit Boundary and Claim Identity

**Files:**
- Modify: `agent/control_plane/saga.py`, `agent/entities/admin_api.py`
- Test: `agent/tests/test_media_saga.py`

- [ ] Add a RED test showing a claim decided by API-key authentication writes `NULL` to PostgreSQL `reviewer_id` while its audit envelope names a non-empty system actor.
- [ ] Run the test and confirm the current literal `admin` UUID cast fails.
- [ ] Allow `_apply_claim_decision` to receive nullable reviewer persistence separately from the audit actor, and pass `None` from routes without an admin user.
- [ ] Add a RED test where `invalidate_entity` raises after image approval commits; assert media, entity image, and suggestion approval remain committed and receipt carries the invalidation failure.
- [ ] Move invalidation behind the committed receipt and return a post-commit effect status without running upload cleanup.
- [ ] Run `python -m pytest agent/tests/test_media_saga.py -q`.

### Task 2: Direct Upload and Bulk Outcomes

**Files:**
- Modify: `agent/entities/admin_api.py`
- Test: `agent/tests/test_media_saga.py` or focused admin tests

- [ ] Add a RED test where a direct entity upload completes provider writes but `upsert_entity` fails; assert every uploaded URL is deleted.
- [ ] Extract/reuse a direct-upload compensation helper that cleans exact returned URLs and does not delete on post-commit invalidation failure.
- [ ] Add RED tests where `upsert_entity`/`delete_entity` raises for one bulk item and a blank relationship destination is supplied; assert each input has an explicit failed outcome.
- [ ] Catch individual bulk mutations and record stable failed outcomes including the original item identifier.
- [ ] Run focused tests for media saga and entity admin bulk paths.

### Task 3: Provisional CAS and Durable Generic Sagas

**Files:**
- Modify: `agent/kb_curation.py`, `agent/control_plane/saga.py`
- Test: `agent/tests/test_kb_curation.py`, `agent/tests/test_media_saga.py`

- [ ] Add a RED test that simulates a concurrent KB writer after promotion but before DB failure; assert rollback does not restore the old full file over the concurrent edit.
- [ ] Replace whole-document rollback with an entity-targeted CAS mutation that reverts only the exact provisional-to-verified change.
- [ ] Add a RED test where `auto_promote_pass` DB persistence fails; assert the JSON promotion is reverted or reported failed rather than silently succeeding.
- [ ] Make auto-promotion persist DB entities before final JSON commit or target-revert only its own promotion upon persistence failure.
- [ ] Add a RED test proving `run_saga` replays a durable receipt after `_SAGA_RECEIPTS` is cleared.
- [ ] Claim/record generic saga commands through `request_idempotency_keys`, preserving existing process-local cache as an optimization.
- [ ] Run all focused Task 8 suites, compile affected modules, lint, and `git diff --check`.

### Task 4: Review and Commit

**Files:**
- Modify: `docs/superpowers/plans/2026-09-01-task-8-p1-review-remediation.md`
- Test: relevant focused suites

- [ ] Review the diff for scope, especially no compensation after a committed write.
- [ ] Stage only Task 8 remediation files and commit with `fix: close task 8 media mutation review findings`.
