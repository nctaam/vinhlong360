# Data Contract Reconciliation Phase B Dry-Run Implementation Plan

> STATUS: implementation complete for fixture-only dry-run/apply harness (2026-09-24); live protected-store application remains blocked pending reviewed locking/approval.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a deterministic, read-only reconciliation plan that exposes every evidence-backed mutation and defers ambiguous SQLite/JSON conflicts for owner review.

**Architecture:** A standalone Python dry-run command loads the reviewed parity report and named remediation ledgers, validates that all input hashes still match, then emits a versioned JSON plan. The command has no apply mode and never writes either protected data store; only an explicit output path may be written.

**Tech Stack:** Python 3, stdlib `sqlite3` read-only URI mode, JSON, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-22-data-contract-recovery-and-reconciliation.md`

## Global Constraints

- Read SQLite with `mode=ro&immutable=1`; never mutate `agent/data/vinhlong360.db`.
- Parse `web/data.json` as UTF-8; never mutate it.
- Consume parity evidence and named remediation ledgers; do not copy one store wholesale.
- Every proposed mutation includes a deterministic ID, store, record, operation, field, before value, after value, reason, and evidence source.
- Ambiguous mutations are deferred with the conflicting options and evidence; the dry run never chooses a store blindly.
- The command is separate from `scripts/checks/audit_data_parity.py` and has no apply or export behavior.
- Preserve R10.6 image attribution: source name/URL when available, author, and license/permission attribution.
- Generated forensic plans belong under `.superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/`; do not rewrite `outputs/data-parity-audit-2026-09-22.json`.

### Task 1: Read-Only Reconciliation Plan Generator

**Files:**
- Create: `scripts/checks/reconcile_data_dry_run.py`
- Test: `tests/checks/test_reconcile_data_dry_run.py`

**Interfaces:**
- Consumes: `scripts.checks.audit_data_parity.build_report` semantics and the parity JSON schema; SQLite tables `entities` and `relationships`; ledgers `remediation_phase7_log.json`, `remediation_spatial.json`, `data_remediation_ledger.json`, `batch_culinary_restaurants_photos.json`, `remediation_phase21_image_log.json`, `batch7_master_enrichment_log.json`, and `remediation_temporal.json`.
- Produces: `build_plan(sqlite_path, json_path, parity_path, ledger_paths) -> dict`, `render_plan(plan) -> str`, and CLI `main(argv) -> int`.

- [ ] **Step 1: Write failing tests**

  Add tests that prove: stale parity input hashes fail closed; production evidence yields 478 relationship type updates plus 4 removal-only SQLite rows and 6 duplicate-JSON removals; the six deterministic `prov-1` spatial/image/graph families are present with exact before/after values; the Bến Phà caption/key-facts proposals are present; the Chôl Chhnăm conflict and verifiedAt differences are deferred; output is deterministic and protected inputs remain byte-identical; and CLI output path collisions return exit code 2.

- [ ] **Step 2: Run the focused tests to verify RED**

  Run `pytest -q tests/checks/test_reconcile_data_dry_run.py`. Expected: collection or assertion failures because the module and interfaces do not yet exist.

- [ ] **Step 3: Implement the minimal read-only generator**

  Implement a versioned plan with top-level keys `schemaVersion`, `mode`, `status`, `inputs`, `summary`, `mutations`, `deferred`, and `errors`. Validate every input hash against the parity report before deriving proposals. Sort mutations by `(store, recordType, recordId, field, operation, mutationId)` and deferred items by `(recordType, recordId, itemId)`.

  Derive relationship updates only when a Phase 7 ledger `(from,to,old_type,new_type)` matches a SQLite-only old triple and JSON-only new triple; emit removal-only deletes when the old triple is SQLite-only but the new triple is already shared; retain shared `near` rows. Remove exactly one highest-index duplicate JSON occurrence per duplicate triple. Use SQLite `rowid` as a deterministic relationship row locator and JSON list index for duplicate removal.

  Derive field-level `prov-1` coordinate/placeId/address repairs from the spatial ledgers, image and attribution fields from the culinary photo ledger, and six graph edges from the explicit orphan remediation ledger. Derive the Bến Phà image-caption correction from the Phase 21 ledger and `attributes.key_facts` from the Batch 7 ledger only when the current value matches the ledger's declared old value or is absent as specified. Do not invent a source URL that a ledger does not provide.

  Add deferred items for the owner-approved Chôl Chhnăm option conflict, the three verifiedAt differences, `prov-1` description/subcategory/season gaps, and the unresolved Vườn trái cây “nổi tiếng” prose correction. A deferred item must retain its evidence path and any competing options.

- [ ] **Step 4: Run focused tests and lint**

  Run `pytest -q tests/checks/test_reconcile_data_dry_run.py` and `ruff check scripts/checks/reconcile_data_dry_run.py tests/checks/test_reconcile_data_dry_run.py`. Expected: all focused tests pass and Ruff reports no errors.

- [ ] **Step 5: Commit**

  Commit with `feat: add read-only reconciliation dry run` after the focused verification succeeds. The controller may preserve the user's no-commit constraint by leaving the worktree uncommitted while recording the exact diff in the SDD ledger.

### Task 2: Evidence Artifact, Documentation, and Independent Verification

**Files:**
- Create: `.superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/phase-b-parity-2026-09-23.json`
- Create: `.superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/phase-b-dry-run-2026-09-23.json`
- Modify: `docs/superpowers/specs/2026-09-22-data-contract-recovery-and-reconciliation.md`
- Modify: `docs/superpowers/plans/2026-09-23-data-contract-reconciliation-phase-b.md`
- Modify: `.superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/progress.md`

**Interfaces:**
- Consumes: Task 1 CLI and the installed logical recovery candidate `agent/data/vinhlong360.db`.
- Produces: byte-stable Phase B parity evidence, a reviewable dry-run plan, and documentation that explicitly blocks apply until a separate approval with a confirmation flag.

- [ ] **Step 1: Generate fresh read-only parity evidence**

  Run `python scripts/checks/audit_data_parity.py --output .superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/phase-b-parity-2026-09-23.json`; record normal exit `0` with `status=drift` and do not overwrite the published Phase A artifact.

- [ ] **Step 2: Generate the dry-run plan**

  Run `python scripts/checks/reconcile_data_dry_run.py --parity .superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/phase-b-parity-2026-09-23.json --output .superpowers/sdd/2026-09-23-data-contract-reconciliation-phase-b/phase-b-dry-run-2026-09-23.json`; verify no SQLite WAL/SHM/journal appears and both protected hashes remain unchanged.

- [ ] **Step 3: Document review boundary**

  Add the artifact paths, measured proposal/deferred counts, current input hashes, and the explicit rule that no apply/export/migration is authorized until the generated plan is reviewed and a separate confirmation flag is supplied.

- [ ] **Step 4: Run independent verification**

  Run the focused dry-run tests, Ruff, normal and strict parity commands, and a before/after hash/mtime check for SQLite and JSON. Review the generated JSON twice and assert byte-for-byte deterministic rendering.

- [ ] **Step 5: Record completion**

  Append the exact verification outputs and any `Ruling:` entries to the Phase B SDD ledger. Do not install further data changes or enable hard-gate parity in this task.

### Task 3: R10.6 Provenance Hardening and Dry-Run Deferrals

**Files:**
- Modify: `scripts/checks/reconcile_data_dry_run.py`
- Modify: `tests/checks/test_reconcile_data_dry_run.py`
- Modify: `scripts/checks/check_banned_claims.py`
- Test: `tests/checks/test_hard_checks.py`

**Interfaces:**
- Consumes: the Phase B dry-run plan and the media constitution in `CLAUDE.md`, `docs/standards/10-data.md`, and `docs/content-creation-guide.md`.
- Produces: a plan that defers the full `prov-1` seven-field documentary-image bundle until it has a real image-specific source URL and permission evidence, plus a checker that rejects placeholder `example.test` provenance.

- [ ] **Step 1: Write failing tests**

  Assert that `prov-1` image URL/author/source/license/type/verified mutations are not in `mutations` and appear as one deferred item with the missing URL/permission requirements. Add a hard-check fixture proving `https://example.test/source` does not satisfy R10.6 traceability.

- [ ] **Step 2: Run tests to verify RED**

  Run the focused tests and confirm the current implementation incorrectly emits the seven mutations and accepts the placeholder URL.

- [ ] **Step 3: Implement the minimal hardening**

  Gate documentary-image proposals on a non-placeholder image-specific URL plus explicit rights/permission evidence. Preserve the valid spatial `prov-1` mutations and Bến Phà caption correction. Reject known placeholder hosts in the image-source policy checker while preserving the existing constitutional allowance for properly sourced press/documentary images.

- [ ] **Step 4: Run focused validation**

  Run `pytest -q tests/checks/test_reconcile_data_dry_run.py tests/checks/test_hard_checks.py` with a dedicated basetemp and `ruff check` on changed Python files. Regenerate the Phase B plan and record the new mutation/deferred counts.

### Task 4: Transactional Apply Harness (Never Execute in This Task)

**Files:**
- Create: `scripts/checks/apply_data_reconciliation.py`
- Create: `tests/checks/test_apply_data_reconciliation.py`
- Modify: `docs/superpowers/specs/2026-09-22-data-contract-recovery-and-reconciliation.md`
- Modify: `docs/superpowers/plans/2026-09-23-data-contract-reconciliation-phase-b.md`

**Interfaces:**
- Consumes: an approved dry-run plan, matching parity/input hashes, SQLite and JSON paths, and an explicit `--confirm-phase-b` flag.
- Produces: a transactional, backup-first apply command that is implemented and tested only against temporary fixtures in this task; it must refuse live execution without explicit confirmation and a reviewed-plan marker.

- [ ] **Step 1: Write failing tests**

  Cover missing confirmation, stale input hash, missing/unreadable backup, plan with deferred items not explicitly accepted, SQLite rollback on a failed mutation, atomic JSON replacement, and successful fixture apply with post-apply parity verification.

- [ ] **Step 2: Run tests to verify RED**

  Run `pytest -q tests/checks/test_apply_data_reconciliation.py` and observe failures because the apply module does not exist.

- [ ] **Step 3: Implement the minimum safe harness**

  Require `--confirm-phase-b`, a plan status of `approved`, a plan hash match, readable backups created before writes, one SQLite transaction, atomic JSON replacement, and rollback on any validation failure. Refuse to operate on the repository live paths unless an additional explicit `--allow-live-protected-inputs` flag is supplied; do not invoke that flag here.

- [ ] **Step 4: Run fixture-only validation**

  Run the focused apply tests and Ruff. Do not run the command against `agent/data/vinhlong360.db` or `web/data.json`, and do not enable parity hard gates.

Implementation note: the harness accepts only an approved plan carrying a reviewed-plan marker and a matching caller-supplied canonical SHA-256. It verifies readable byte-identical SQLite/JSON backups before opening one SQLite transaction, stages JSON through an atomic replacement, and performs post-apply ID/relationship parity verification. Missing confirmation, stale hashes, unreadable backups, unaccepted deferred items, mutation errors, and protected live paths fail closed. Task 4 is fixture-only and does not execute the current 499-mutation review-required plan.

Review hardening also requires exact before-value checks for every update/delete,
descending JSON index application with duplicate-index rejection, independent
single-link backups, a post-`BEGIN` hash recheck, parity counts/duplicate/endpoint
checks, and atomic staged restoration if commit or post-validation fails.

### Recovery integration clarification (2026-09-24)

The fixture apply harness now acquires a cooperative `ReconciliationLock` before
preflight, writes a durable `prepared` journal before SQLite mutation, and records
monotonic `sqlite_committed`, `json_published`, and `complete` phases. An existing
journal blocks a new apply until `--recover-phase-b-journal` explicitly restores
both stores from the verified backups. `--maintenance-window` does not bypass the
live-path refusal; the separate existing `--allow-live-protected-inputs` flag is
also required, and no live invocation is authorized by this plan.
