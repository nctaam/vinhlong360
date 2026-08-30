# Claude Code Desktop Handoff: Correction Case Pilot

> STATUS: active
> Date: 2026-08-18
> Scope: local continuation only; no push, deploy, production mutation, or secret rotation is authorized.

## Open The Correct Checkout First

> **ĐÍNH CHÍNH ĐƯỜNG DẪN — 2026-08-30.** Toàn bộ cây `C:\Code\` mô tả bên dưới
> **không còn tồn tại trên máy này** (đã kiểm: cả `C:\Code\vinhlong360` lẫn `C:\Code`
> đều không có). Kho nay nằm ở **`C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot`**
> và là một checkout thường, KHÔNG phải worktree phụ. Đây là đính chính đường dẫn,
> KHÔNG phải mất mã: `9b265f45` (HEAD lúc bàn giao), `aebf4afe` (tip `main` cũ) và
> `b60ce900` đều còn nguyên và đều là tổ tiên của HEAD hiện tại (3.197 commit).
> Nhánh `main` không còn nhãn ở local — chỉ còn `codex/correction-case-pilot`,
> `breaker-base`, `claude/focused-nash-e88299`. Vẫn CHƯA có remote nào.
>
> Câu lệnh xác nhận danh tính, bản dùng được:
>
> ```powershell
> Set-Location 'C:\Users\NCTaam\Documents\vinhlong360-correction-case-pilot'
> git status --short --branch
> git rev-parse HEAD
> git branch --show-current
> git remote -v      # rỗng: chưa có remote, nên không thể push (CLAUDE.md §4)
> ```

- Worktree: `C:\Code\vinhlong360\.worktrees\correction-case-pilot` *(đường dẫn LỊCH SỬ — xem đính chính trên)*
- Branch: `codex/correction-case-pilot`
- Implementation HEAD at handoff: `9b265f451ff34090443a75c6214904a4cc1fb5f6`
- This branch is local-only and has no configured upstream. Do not push or create an upstream without explicit owner authorization.
- The main checkout at `C:\Code\vinhlong360` is dirty and user-owned. Do not edit, reset, clean, checkout, stash, or otherwise mutate it. Open the correction worktree above as the Claude Code Desktop workspace. *(Không còn áp dụng: cây đó đã không còn trên máy.)*
- Preserve all existing diffs. Never use destructive reset/checkout commands to make the tree look clean.

At the start of every session, confirm identity before doing any work:

```powershell
Set-Location 'C:\Code\vinhlong360\.worktrees\correction-case-pilot'
git status --short --branch
git rev-parse HEAD
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
```

The last command is expected to fail with "no upstream configured". At this handoff, `git status` was clean before the documentation-only handoff commit.

## Authority And Reading Order

Read these files before changing implementation:

1. `CLAUDE.md` — repository constitution and stop conditions.
2. `docs/superpowers/plans/2026-08-12-correction-case-pilot.md` — approved Tasks 1-18 implementation plan.
3. `docs/superpowers/specs/2026-08-11-nocturne-civic-whole-service-constitution-design.md` — parent whole-service constitution.
4. `docs/superpowers/specs/2026-08-12-service-ownership-assisted-channels-design.md` — authoritative Case Kernel, correction, ownership, assisted-channel, receipt, publication, and operating contract.
5. `.superpowers/sdd/2026-08-12-correction-case-pilot/progress.md` — task/fix-round/review ledger.
6. `.superpowers/sdd/2026-08-12-correction-case-pilot/task-5-report.md` — Task 5 TDD, security, PostgreSQL, and verification evidence.

When sources conflict, follow the repository authority order in `CLAUDE.md`; do not silently reinterpret the approved plan or specs.

## Current State And Breaker

- Tasks 1-4 are complete. Tasks 1, 2, and 4 ended review-clean. Task 3 completed with three explicitly parked, non-load-bearing defense-in-depth items listed below.
- Task 5 is committed through `9b265f45` after five fix rounds.
- Task 5 is **not review-clean**. Its runtime/security suites and staged hard gate were green, but the final independent review retained two Important findings.
- Do **not** mark Task 5 complete and do **not** start Task 6 until both findings are fixed or the owner explicitly accepts the residual risk.
- If the findings are fixed, record the work as **breaker remediation after the five-round ceiling**, with TDD RED -> GREEN and a fresh independent review. Do not silently label it "fix round 6" and do not reuse the reviewer as implementer.

### Open Important Finding 1: catalog readiness can accept weakened PostgreSQL enforcement

References: `agent/database.py:264`, `agent/database.py:295`, `agent/database.py:557`, `agent/database.py:612`, and `agent/tests/test_migration_readiness_postgres.py:173`.

The readiness query validates FK target table/columns/action but does not capture the target namespace. A same-named target such as `shadow.case_receipts(case_id, receipt_id)` can therefore satisfy the current identity comparison even though the FK no longer protects `public.case_receipts`. The trigger query validates table, function schema/name, event bitmask, enabled state, and update columns, but not `pg_trigger.tgqual` or the trigger function body/definition. Concrete bypasses include adding a restrictive `WHEN (...)` predicate to the expected trigger, or replacing `public.reject_case_receipt_case_move` / `public.enforce_case_access_same_case` with a no-op function body while retaining the expected names and trigger metadata; readiness can still report healthy.

Remediation must fail closed on exact FK target schema and on semantically required trigger predicate/function definition, with live disposable-PostgreSQL drift tests that first reproduce both bypasses.

### Open Important Finding 2: frontend bearer source guard misses executable templates and property assignments

References: `agent/tests/test_case_security_source_guard.py:35`, `agent/tests/test_case_security_source_guard.py:39`, and `agent/tests/test_case_security_source_guard.py:142`.

The frontend scanner removes complete backtick literals and scans call arguments only. A bearer embedded in an executable template expression, for example ``console.log(`token=${access_token}`)``, is stripped before identifier analysis. Browser property-assignment sinks are not calls, so examples such as `window.location.href = access_token`, `document.body.textContent = case_capability`, or equivalent location/DOM/storage property writes bypass the guard.

Remediation should use syntax-aware JavaScript/TypeScript/Vue analysis, or an equivalently bounded parser, so `${...}` expressions and dangerous assignment sinks are checked without returning to file-wide false positives. Add RED fixtures for template expressions and browser property assignments before implementation.

## Locked Architecture And Security Decisions

- The Case Kernel runtime is PostgreSQL-only. SQLite is not an alternate Case Kernel authority.
- Case feature flags default to `false`; rollout must be explicit.
- Migration `080` remains additive-first and replay-safe, and `agent/init.sql` must remain in parity. Do not introduce migration `081` merely to patch this branch.
- Receipt capabilities use 32 random bytes encoded as strict canonical unpadded URL-safe Base64: exactly 43 characters. Persist only digests. Receipt expiry is 365 days.
- Access sessions last 15 minutes, persist digest only, and are invalidated by revocation/rotation. Revocation takes precedence over otherwise valid queued or session effects.
- Lost-response replay is Fernet-encrypted, expires after 24 hours, and is scoped/bound to the authorized operation rather than becoming a secret-recovery channel.
- HKDF derivation salts are exactly `vl360-case-replay-v1` and `vl360-case-capability-v1`.
- The access cookie is `HttpOnly`, `Secure` in production, `SameSite=Lax`, path `/api/cases`, and max age 900 seconds.
- CSRF requires same-origin checks and HMAC binding to the access-session digest; malformed or noncanonical credentials fail with stable public credential errors.
- Never place bearer secrets in URLs, logs, analytics, notifications, local storage, session storage, or persisted DOM. Never persist raw receipt capabilities or access tokens.
- Receipt issuance/rotation/revocation and encrypted idempotent replay must preserve case authority, transaction composition, deterministic locking, constant-time comparison after bounded lookup, and same-case receipt/session linkage.

## Verification Evidence At `9b265f45`

The committed Task 5 report records the following GREEN results for fix round 5:

- `agent/tests/test_case_security_source_guard.py`: `7 passed`.
- `agent/tests/test_case_access_security.py` with guarded PostgreSQL: `11 passed`.
- `agent/tests/test_case_store.py`: `15 passed`.
- `agent/tests/test_case_transaction_postgres.py`: `8 passed`.
- `agent/tests/test_case_schema_postgres.py`: `13 passed`.
- Migration/readiness suite, including live catalog drift probes: `14 passed`.
- `agent/tests/test_database.py`: `198 passed, 1 xfailed`.
- Ruff passed on all touched Python files; `git diff --check` and the staged repository hard gate passed.

Earlier bounded Task 5 verification also recorded `221 passed, 13 skipped, 1 xfailed`, plus `45 passed` against a freshly migrated disposable PostgreSQL database. Disposable loopback databases used by prior rounds, including `vl360_case_task5_fix2_test` and `vl360_case_task5_fix4_test`, were dropped after their gates. Do not assume a shared or production database is disposable; PostgreSQL integration tests must use a loopback DSN whose database name contains `test`, then explicitly drop only that verified test database.

Because the final review is not clean, green evidence above is evidence of the current baseline, not permission to advance past the breaker.

## Safe Resume Verification

These commands contain no secrets and are intentionally bounded. Run them separately to avoid the prior combined-command timeout:

```powershell
Set-Location 'C:\Code\vinhlong360\.worktrees\correction-case-pilot'
git status --short --branch
git rev-parse HEAD
python -m pytest -q agent/tests/test_case_security_source_guard.py
python -m pytest -q agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_privacy_logging.py
python -m pytest -q agent/tests/test_case_store.py
python -m pytest -q agent/tests/test_case_transaction_postgres.py
python -m pytest -q agent/tests/test_case_schema_postgres.py agent/tests/test_migration_readiness_postgres.py
python -m pytest -q agent/tests/test_database.py
python -m ruff check agent/cases/security.py agent/cases/store.py agent/database.py agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py agent/tests/test_migration_readiness_postgres.py agent/tests/test_database.py
git diff --check
```

PostgreSQL tests may skip without their guarded disposable-test environment. Do not place a DSN, password, key, capability, token, or cookie value in this handoff, source files, shell history, test output pasted into docs, or Git.

## Parked Task 3 Defense-In-Depth Items

These are real hostile in-process Python-object hardening gaps, parked as non-load-bearing because serialized/API/store paths construct ordinary domain objects. Final program review must triage them; do not misreport them as fixed:

1. A hostile tuple subclass can override `__iter__` and escape transition-item validation.
2. A hostile waiting-field object can raise or alter behavior through `__bool__` when another waiting field is absent.
3. An exact `datetime` with custom `tzinfo.utcoffset()` that raises can escape the awareness-check boundary.

## Remaining Approved Plan

Do not start any of these while the Task 5 breaker remains open:

6. Correction Create Command And Idempotency.
7. Public Case API, Status Projection, Receipt Rotation, And ReviewCase.
8. Optional Phone Verification And At-Least-Once Notification Outbox.
9. Policy-Derived Queue, Leases, Takeover, Recusal, And Escalation.
10. Evidence Registry, Risk Decisions, Domain Outcomes, And Immutable Change Sets.
11. Transaction-Aware Entity Write And Provenance Boundary.
12. Atomic Publication Apply, Projection Verification, Recovery, And Rollback.
13. Action-Scoped Admin API And Guided Assisted Intake.
14. Public Nuxt Contract, Intake, One-Time Receipt, Lookup, And Status.
15. Integrate Directory, Detail, Ward, Contact Router, And Legacy Entry Routes.
16. AdminCP Queue And Correction Workbench.
17. Legacy JSONL Shadow Import, Reconciliation, Cutover, And Rollback Controls.
18. Capacity Evidence, Retention, End-To-End Journeys, Accessibility, Privacy, And Operating Docs.

### Task 6 First-Session Contract

Files from the approved plan:

- Create `agent/cases/service.py`.
- Create `agent/cases/rate_limit.py`.
- Modify `agent/cases/store.py`.
- Create tests `agent/tests/test_correction_create.py` and `agent/tests/test_case_idempotency_postgres.py`.

Required interface:

- `CreateCorrectionCommand(envelope, reporter_privacy, items, optional_phone, notification_consent, authenticated_user_ref, handoff)`.
- `CreateCorrectionResult(case_id, public_reference, capability, received_at, next_update_at, replayed)`.
- `CaseService.create_correction(...)` atomically commits case, interaction, optional party authority, E0 evidence, items, clocks, initial work, transition, audit, receipt, encrypted replay, and notification-outbox intent.
- `check_case_rate_limit(bucket, subject_digest, *, limit, window, now)` is PostgreSQL-backed for create, receipt exchange, contact OTP, review, and rotation; local memory is not authoritative.

Only after the Task 5 breaker is closed or owner-accepted, begin Task 6 with the plan's RED command:

```powershell
python -m pytest -q agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py
```

Expected initial RED: the create command/service is missing. After implementation, the plan's GREEN/commit preparation commands are:

```powershell
python -m pytest -q agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py agent/tests/test_case_transaction_postgres.py
git add agent/cases/service.py agent/cases/rate_limit.py agent/cases/store.py agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py
git commit -m "feat: create correction cases idempotently"
```

Task 6 must cover anonymous/contact/handoff behavior, server-derived authenticated linkage, public operator rejection, bounded multi-item fields, safe emergency-language routing, durable PostgreSQL rate limits, exact idempotent replay, and `409 idempotency_conflict` for a reused key with a different body. It must not treat optional contact as identity, trust a submitted user ID, import a Zalo transcript, or let receipt/outbox-intent failure partially commit a case.

## Execution Discipline

- Continue the approved subagent-driven/TDD workflow: fresh implementer per numbered task, RED -> GREEN, independent review after each task, and preservation of every diff.
- For the current breaker, use a fresh remediation implementer and a fresh independent reviewer. Update both the progress ledger and Task 5 report with commands/results and the review disposition.
- Do not mutate production, deploy, push, create a PR, configure an upstream, rotate real secrets, or expose secrets. None of those actions has been performed or authorized in this handoff.
