# Closed Release Ops Recovery Implementation Plan

> STATUS: active
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the closed release package install the backup and watchdog runtime authorities correctly, refresh only truthfully verified release metadata, and stop before deployment when owner signing custody is absent.

**Architecture:** Extend the existing closed-release systemd authority set with the backup service and timer. Keep all runtime mutations behind `install_closed_release.sh`; the archive verifier, package manifest, installer, contracts, and tests must agree on the same seven-unit topology. Release authority and acceptance artifacts remain fail-closed until an external owner key signs the current bundle.

**Tech Stack:** Bash systemd units, Python release verifier/package builder, pytest launch-safety contracts, Git metadata.

**Spec:** `docs/runbooks/launch-safety-rollback.md`, `docs/deployment-guide.md`, `config/release-authority.json`, `config/decision-records.json`.

## Global Constraints

- Never bypass `verify_release_bundle.py`, `verify_closed_release.py`, migration gates, or owner/countersignature verification.
- Never create a signature, decision choice, authority timestamp, or staging receipt without its real issuer and custody.
- Never mutate production directly; production changes may only run through the closed installer after all gates pass.
- Preserve unrelated generated artifacts and frontend worktree ownership; stage only task-owned files.
- Every implementation change requires a failing test first and fresh verification before any completion claim.

### Task 1: Define the seven-unit runtime authority

**Files:**
- Create: `ops/systemd/vl-backup-db.service`
- Create: `ops/systemd/vl-backup-db.timer`
- Modify: `scripts/ops/verify_closed_release.py`
- Modify: `scripts/ops/install_closed_release.sh`
- Test: `tests/launch_safety/test_systemd_contract.py`
- Test: `tests/launch_safety/test_closed_installer.py`

**Interfaces:** The package verifier and installer must treat `vl-backup-db.service` and `vl-backup-db.timer` exactly like the existing watchdog units, while the backup script remains `/opt/vinhlong360/scripts/ops/backup_db_daily.sh`.

- [x] **Step 1: Write the failing contract tests** asserting the two units exist, match the reviewed `Type=oneshot`, `ExecStart`, timer cadence, and are included in the exact authority set and installer unit list.
- [x] **Step 2: Run the focused tests** and record the expected RED for the missing two-unit contract.
- [x] **Step 3: Add the two unit files** with LF line endings and the same restrictive systemd conventions as the existing units.
- [x] **Step 4: Extend verifier constants and installer unit arrays** so package admission, systemd backup/recovery, destination checks, and rollback evidence cover seven units.
- [x] **Step 5: Run the focused tests again** (`10 passed`) and the targeted installer regression (`6 passed, 297 deselected`).

### Task 2: Bind shell line endings and backup script packaging

**Files:**
- Modify: `.gitattributes`
- Modify: `tests/launch_safety/test_runtime_script_line_endings.py`
- Modify: `scripts/ops/verify_closed_release.py`
- Test: `tests/launch_safety/test_release_package.py`

**Interfaces:** Any `.sh` file shipped in the closed archive must be LF-only; the archive must contain `scripts/ops/backup_db_daily.sh` as a required runtime member.

- [x] **Step 0: Preserve LF for shipped shell scripts.** Commit `992a4942` adds the repository-wide `*.sh text eol=lf` rule and a regression test covering systemd-invoked scripts.
- [x] **Step 1: Add a failing package assertion** for the backup script member and LF bytes in the release snapshot.
- [x] **Step 2: Run the focused package tests** and record the expected RED before the verifier change.
- [x] **Step 3: Add the backup script to required package membership and preserve the LF attribute.**
- [x] **Step 4: Run package/verifier tests and confirm they pass** (`131 passed, 4 skipped` in the focused package/rollback run).

### Task 3: Truth-sync authority without fabricating approvals

**Files:**
- Modify: `.superpowers/sdd/2026-09-05-backend-completion-closure/progress.md` (force-add ignored ledger only after truthful update)
- Modify: `config/release-authority.json`
- Test: `tests/integration/test_cross_boundary_proof.py`

**Interfaces:** Authority must bind the current release commit, its archive digest, and the actual evidence scope while keeping unsigned decisions and absent owner custody as blocking reasons.

- [x] **Step 1: Record a truth-sync entry** with current HEAD, archive digest, test evidence, VPS read-only observations, and explicit blockers.
- [x] **Step 2: Run `python scripts/check_release_authority.py --root .` and verify the only remaining failures are genuine signing/decision custody or other explicitly documented gaps.
- [x] **Step 3: Do not change `config/decision-records.json` to signed or selected options; no owner key is present.**

### Task 4: Build and verify the current archive

**Files:**
- Generated outside Git: `E:\vl360-release-artifacts-20260911\dist\vl360-launch-release-<release-commit>.tar.gz*`
- Generated outside Git: `E:\vl360-release-artifacts-20260911\pilot-acceptance-<release-commit>*.json`

- [x] **Step 1: Rebuild Nuxt output for the current release commit.**
- [x] **Step 2: Run hard gates, focused tests, and package the archive.**
- [x] **Step 3: Run `verify_closed_release.py --require-closed` locally and on the VPS staging path.**
- [x] **Step 4: Stop before installer execution because `verify_release_bundle.py` is not `PASS` and owner/countersignature keys are absent.**

### Task 5: Production handoff gate

- [ ] **Step 1: Obtain the real owner signing key through the approved offline custody channel; never transmit it in chat or commit it.**
- [ ] **Step 2: Obtain signed decision records and current owner/countersignature attestations bound to HEAD and archive SHA.**
- [ ] **Step 3: Re-run all verifiers and execute the closed installer only after every gate passes.**
- [ ] **Step 4: Verify migrations, backup, service health, readiness, public HTTP 200, and rollback evidence after installation.**

## Current External Blocker

The owner and countersignature keys are absent from both the local machine and VPS. Tasks 1-4 are executable without them; Task 5 cannot be completed honestly until custody is provided by the owner.
