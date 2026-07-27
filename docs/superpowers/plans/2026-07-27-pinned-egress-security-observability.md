# Pinned Egress Security Observability Implementation Plan

> STATUS: active - implementation has not started.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit one sanitized, consumer-aware warning for blocked pinned-egress destinations, peer mismatches, and redirect-policy denials without changing consumer return or HTTP behavior.

**Architecture:** `agent/pinned_http.py` owns the dedicated `security.egress` logger, audit-context sanitization, origin-only target formatting, reason mapping, and one-event-per-request logging at `PinnedHTTPClient.get()`. The three mapped consumers pass fixed audit contexts; auto-learn suppresses its existing raw-URL warning only for the three security-denial classes, while all other failure behavior remains unchanged.

**Tech Stack:** Python 3.10+, `logging`, `re`, `httpx`, `pytest`, Ruff, repository hard checks, and the bounded backend regression runner.

## Global Constraints

- `PinnedHTTPClient.get()` gains one required keyword-only `audit_context: str` argument.
- Production audit contexts are exactly `admin_image_review`, `auto_learn`, and `quality_burst`.
- The dedicated logger name is exactly `security.egress`, and matching records are `WARNING` events.
- Reason codes are exactly `blocked_address`, `peer_mismatch`, and `redirect_policy`.
- Log targets contain only normalized `scheme://ascii-host:effective-port`; never log userinfo, path, query, fragment, redirect `Location`, headers, body, or raw exception text.
- Log once at the `PinnedHTTPClient.get()` boundary, re-raise the original typed exception, and do not emit the security event for ordinary resolution, transport, deadline, saturation, body-limit, or encoding failures.
- Keep admin HTTP mappings, auto-learn return values, quality-burst silent return values, and all existing egress policy/deadline/body semantics unchanged.
- No external logging service, SIEM, metrics backend, alerting integration, paid dependency, database persistence, cookie jar, or migration of excluded outbound callers.
- No database/data-file rewrite, secret change, production deployment, indexing change, push, or remote mutation.
- Every task must leave the repository working, include tests before implementation, and commit only its scoped files.

---

### Task 1: Central Security-Denial Logging And Consumer Migration

**Files:**
- Modify: `agent/pinned_http.py` near the exception hierarchy and `PinnedHTTPClient.get()`.
- Modify: `agent/admin.py`, `agent/auto_learn.py`, `agent/gpt55_quality_burst.py`.
- Test: `tests/test_pinned_http.py`, `tests/test_admin_pinned_http.py`, `tests/test_auto_learn_fetch.py`, `tests/test_gpt55_quality_burst.py`, `tests/test_pinned_http_consumers.py`.

**Interfaces:**
- Consumes: existing `PinnedHTTPError` subclasses and `PinnedHTTPClient.get(url, user_agent, policy)` flow.
- Produces: `PinnedHTTPClient.get(url, *, user_agent, policy, audit_context)`; module logger `security.egress`; helpers that return sanitized context, origin, and stable reason code; fixed audit contexts at all three mapped call sites; no duplicate auto-learn raw-URL warning for security denials.

- [ ] **Step 1: Add RED tests for the audit-context and event contract.**

  Add tests in `tests/test_pinned_http.py` that call a real `PinnedHTTPClient` with injected resolver/transport doubles and assert:

  ```python
  with caplog.at_level(logging.WARNING, logger="security.egress"):
      with pytest.raises(ph.BlockedAddressError):
          client.get(
              "https://public.example/private?token=secret#fragment",
              user_agent="test-agent",
              policy=_policy(),
              audit_context="Quality / Burst",
          )

  assert len(caplog.records) == 1
  record = caplog.records[0]
  assert record.name == "security.egress"
  assert "consumer=quality_burst" in record.getMessage()
  assert "reason=blocked_address" in record.getMessage()
  assert "target=https://public.example:443" in record.getMessage()
  assert "/private" not in record.getMessage()
  assert "token" not in record.getMessage()
  assert "fragment" not in record.getMessage()
  ```

  Add direct helper cases for `"Admin Image/Review" -> "admin_image_review"`,
  a 100-character context truncating to 64 characters, an all-punctuation
  context becoming `unknown`, and `https://[2001:db8::1]/path?secret=1`
  becoming `https://[2001:db8::1]:443`.

  Add equivalent one-record tests for `PeerMismatchError` and
  `RedirectPolicyError`, including a redirect-hop count of `1` after one
  accepted redirect. Add a parameterized negative test proving
  `PinnedBodyLimitError`, `PinnedContentEncodingError`, `PinnedDeadlineExceeded`,
  `ResolverSaturatedError`, and ordinary `PinnedTransportError` produce no
  `security.egress` record. Pass `audit_context="test"` to every direct
  `PinnedHTTPClient.get()` call in this test file.

  Update the existing public-signature test so the parameter order is exactly
  `self, url, user_agent, policy, audit_context`, with `audit_context` required
  and keyword-only. Update every raw-response, redirect, deadline, and
  transport call in the file to pass `audit_context="test"`.

  Capture the keyword arguments in each consumer's pinned-client fake and assert
  the exact contexts `admin_image_review`, `auto_learn`, and `quality_burst`.
  Add an auto-learn blocked-address test that returns `None`, records exactly one
  `security.egress` warning, and emits no second raw-URL warning. Add real,
  no-network blocked-literal tests proving admin still maps to HTTP 400 and
  quality-burst still returns an empty string. Extend the AST consumer registry
  test to lock the exact audit-context literal for every mapped function.

- [ ] **Step 2: Run the RED tests and verify the failure is the missing contract.**

  Run:

  ```powershell
  python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q -k "audit_context or security_egress or denial_log or egress or silent"
  ```

  Expected: failures show the missing `audit_context` parameter or absent
  `security.egress` records; no unrelated transport/body test is allowed to be
  the first failure.

- [ ] **Step 3: Implement the smallest central logging boundary.**

  In `agent/pinned_http.py`:

  1. Import `logging` and `re`, then define `security_logger = logging.getLogger("security.egress")`.
  2. Add `_sanitize_audit_context(value: str) -> str` using the spec algorithm: lowercase ASCII text, replace each maximal run outside `[a-z0-9._-]` with `_`, strip leading/trailing separators, truncate to 64 characters, and return `unknown` when empty.
  3. Add `_safe_origin(url: httpx.URL | str) -> str` that returns only `scheme://ascii-host:effective-port`, brackets IPv6, and returns `<invalid>` if parsing or normalization fails.
  4. Add `_security_denial_reason(exc: BaseException) -> str | None` mapping only the three exact exception classes to the exact reason codes.
  5. Add `_log_security_denial(audit_context: str, target: httpx.URL | str, hop: int, exc: BaseException) -> None` using logger argument substitution and no exception text.
  6. Add required keyword-only `audit_context: str` to `PinnedHTTPClient.get()`. Keep the current loop intact, track the current URL and accepted-redirect count, and wrap the loop with a catch for only `BlockedAddressError`, `PeerMismatchError`, and `RedirectPolicyError`; log once, then `raise` unchanged. Do not catch or log other failures.

  Pass the exact audit-context keyword from the three production consumers. In
  `agent/auto_learn.py`, import the three security-denial classes, catch them
  before the broad warning handler, return `None`, and retain the broad warning
  unchanged for non-security exceptions. Do not add a consumer logger to
  quality-burst and do not change admin's localized HTTP mappings.

- [ ] **Step 4: Run the focused green suite and mutation-check the boundary.**

  Run:

  ```powershell
  python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q -k "audit_context or security_egress or denial_log or egress or silent"
  python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q
  ```

  Expected: the new tests pass, the full pinned client file remains green, and
  mutating any reason code, removing the catch, or logging raw target data makes
  at least one new assertion fail.

- [ ] **Step 5: Commit the working central boundary and all required callers.**

  ```powershell
  git add agent/pinned_http.py agent/admin.py agent/auto_learn.py agent/gpt55_quality_burst.py tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py
  git commit -m "feat: add pinned egress security denial observability"
  ```

### Task 2: Documentation Truth-Sync And Final Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-07-27-pinned-egress-security-observability-design.md`.
- Modify: `docs/ROADMAP.md`, `docs/HANDOFF.md`.
- Test: repository focused gates and bounded backend baseline.

**Interfaces:**
- Consumes: Task 1 implementation commit plus measured command output.
- Produces: revision-bound `STATUS: done` design result and removal of the operationally-silent egress residual while retaining genuine residuals.

- [ ] **Step 1: Run the complete verification set before editing result docs.**

  ```powershell
  python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q
  python -m ruff check agent/pinned_http.py agent/admin.py agent/auto_learn.py agent/gpt55_quality_burst.py tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py
  python scripts/checks/run_hard.py --all
  git diff --check
  python scripts/ops/run_backend_regression.py --deadline-seconds 7000
  ```

  Expected: every command exits `0`; the focused suite reports the exact measured
  count; hard checks report `hard=0` without ratchet increase; the bounded
  backend runner completes with its Phase A/Phase B counts; no database,
  `web/data.json`, or user-owned WAL/SHM file changes.

- [ ] **Step 2: Update result and residual documentation with literal evidence.**

  Change the design header to `STATUS: done` and append `## KẾT QUẢ` containing:

  - the two implementation commit hashes and final `git rev-parse HEAD`;
  - the exact focused pytest, Ruff, hard, diff, and bounded-backend commands with
    exit codes and measured counts;
  - the exact `security.egress` contract and three production contexts;
  - no push/deploy/data rewrite/secret/indexing mutation;
  - production observability still unproven pending separately authorized deploy.

  In `docs/ROADMAP.md`, replace the operationally-silent egress residual with a
  resolved entry and retain cookie-gate incompatibility, excluded callers, and
  production-observation debt. In `docs/HANDOFF.md`, update the current local
  revision and remove the stale “egress denials remain silent” wording while
  keeping the remaining residuals explicit.

- [ ] **Step 3: Review documentation consistency and commit it separately.**

  ```powershell
  rg -n "STATUS:|security\.egress|blocked_address|peer_mismatch|redirect_policy|silent|audit_context|KẾT QUẢ" docs/superpowers/specs/2026-07-27-pinned-egress-security-observability-design.md docs/ROADMAP.md docs/HANDOFF.md
  git diff --check
  git add docs/superpowers/specs/2026-07-27-pinned-egress-security-observability-design.md docs/ROADMAP.md docs/HANDOFF.md
  git commit -m "docs: record pinned egress observability verification"
  ```

- [ ] **Step 4: Final verification on the completed branch.**

  ```powershell
  python -m pytest tests/test_pinned_http.py tests/test_admin_pinned_http.py tests/test_auto_learn_fetch.py tests/test_gpt55_quality_burst.py tests/test_pinned_http_consumers.py -q
  python scripts/checks/run_hard.py --all
  git diff --check
  git status --short --branch
  ```

  Expected: all commands exit `0`, `hard=0`, no tracked/uncommitted code or test
  changes remain, and only the pre-existing user-owned untracked WAL/SHM and
  page-inventory files remain.
