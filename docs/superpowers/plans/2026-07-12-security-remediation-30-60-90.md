# Security Remediation 30/60/90 Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the deep audit into an ordered 90-day remediation program that closes direct findings first and then removes their structural causes.

**Architecture:** The program is split into independent, testable workstreams. Each workstream lands tactical regression-backed fixes before introducing shared boundaries, feature flags, benchmarks, or migration work.

**Tech Stack:** FastAPI, Nuxt 4, PostgreSQL, Redis, Nginx, Docker Compose, GitHub Actions, pytest, Vitest, Ruff, TypeScript.

---

## Days 0-30: Direct closure and launch blockers

### Workstream 1: Public eligibility boundary

- [x] Execute `docs/superpowers/plans/2026-07-12-public-eligibility-boundary.md` on branch `codex/public-eligibility-boundary`.
- [x] Acceptance: all ten `REVIEW-06-003` through `REVIEW-06-012` paths and endpoint variants have regression coverage; public response shapes remain compatible.
- [x] Rollback: revert endpoint wiring while retaining the regression tests for review.

### Workstream 2: Social privacy and admin review

**Files:** `agent/social.py`, `web-nuxt/pages/admin/duyet-tu-hoc.vue`, focused social/admin tests.

- [x] Add RED tests for `show_saved=false`, followers-only/non-follower profile access, and hidden provisional fields in admin review.
- [x] Enforce privacy at SQL selection and return a restricted profile shape for unauthorized viewers.
- [x] Render every field that the approval request will verify, or exclude unrendered fields from approval.
- [x] Acceptance: denied viewers receive no private fields; admin approval payload equals the visible review payload.
- [x] Completed on branch `codex/social-privacy-admin-review`; findings `REVIEW-02-001`, `REVIEW-02-003`, and `REVIEW-16-003` have regression-backed closure.

### Workstream 3: Chat ownership, cache, URL, and budgets

**Files:** `agent/server.py`, `agent/memory.py`, `agent/guardrails.py`, `web-nuxt/components/ChatWidget.vue`, `web-nuxt/composables/useAI.ts`.

- [x] Add owner-mismatch tests for POST chat, SSE, welcome, exact cache, semantic cache, and budgets.
- [x] Introduce a server-derived owner key and bind hot memory, cold profiles, caches, and cost ledgers to it.
- [x] Move streaming prompt/history from query parameters to a POST/SSE-compatible protected transport.
- [x] Record provider-reported usage for every model round, including nested provider-backed tools and cancellation finalizers.
- [x] Acceptance: no synthetic sentinel crosses owners; provider usage equals ledger usage; URL logs contain no prompt/history.
- [x] Completed on branch `codex/chat-ownership-budgets`; fresh verified code HEAD `0ae1ceb6c39addc6d1f68c9a19febb46140681ab` after semantic dedup (`b053c4a`, `f7259a3`, `4b56bc8`, `240dac6`, `86c1353`), history continuity (`affa524`), and fragmented SSE/reader lifecycle (`8c1af0a`, `cad268a`, `0ae1ceb`) remediation groups.
- [x] Evidence: exact focused `350 passed, 51 deselected`; history continuity `22 passed`; full backend `6102 passed, 39 skipped, 78 deselected, 1 xfailed`; frontend `8` files / `125 passed`, typecheck/build exit `0`; owner/history `31 passed`; provider exact-once `13 passed`; lifecycle `28 passed`; frontend transport `23 passed`; cancellation stress `60/60`; fresh Browser fragmented UTF-8 proof rendered exactly one clean reply with no console warnings/errors.
- [x] Residuals/non-goals: anonymous identity resets when its signed cookie is cleared; no atomic reserve/commit across parallel admission; `/feedback` remains out of scope; all-zero provider usage is estimated; side-effect-then-raise settlement sinks are untested; pre-terminal stream usage is estimated; cancellation waits for provider completion; dedup pending is bounded at 501 against the nominal 500 cap; the development dynamic-import/large-chunk warning remains.
- [x] Rollback: revert Workstream 3 endpoint/owner/accounting commits together while retaining the regression tests; do not restore GET streaming or client-selected ownership/budget keys as a compatibility path.

### Workstream 4: Immediate account/control-plane fixes

**Files:** `agent/admin.py`, `agent/auth.py`, associated tests.

- [x] Add RED tests for admin-to-superadmin single/bulk ban and pending 2FA after password reset.
- [x] Centralize actor-target role comparison and revoke all pending authentication challenges during reset.
- [x] Acceptance: denied hierarchy operations have zero target database/session side effects; pre-reset challenges cannot create sessions.
- [x] Completed on branch `codex/account-control-plane`; findings `REVIEW-01-005`, `REVIEW-01-006`, and `REVIEW-08-001` have regression-backed closure.
- [x] Evidence: implementation/test HEAD `389eccfc01d524fdf85c53566851476f2788d2ce`; focused control-plane `66 passed, 8 skipped`; full backend `6168 passed, 47 skipped, 78 deselected, 1 xfailed, 1 warning`; disposable PostgreSQL 16.4 `8 passed`; Ruff, `py_compile`, and diff checks passed; final spec and quality reviews found no open Critical or Important issue.
- [x] Residuals: bulk locking uses up to 50 correctness-safe individual queries; real PostgreSQL coverage remains opt-in and should run serially in dedicated CI; AST/source-order regressions are maintenance coupling; the existing Starlette/httpx deprecation warning remains.
- [x] Rollback: revert the Workstream 4 production commits together while retaining regression tests; no migration or stored-data rewrite is involved, and rollback reopens the three findings until a replacement fix lands.

### Workstream 5: Launch policy alignment

**Files:** `web-nuxt/server/middleware/noindex.ts`, Nuxt SEO configuration, `robots.txt`, affected detail pages, legal roadmap documents.

- [ ] Owner confirms index/noindex state and legal decisions before code changes.
- [ ] Align meta robots, `X-Robots-Tag`, robots.txt, and sitemap behavior.
- [ ] Add visible AI-illustration labeling to entity detail/share contexts.
- [ ] Acceptance: automated browser tests observe one consistent indexing policy and AI images are never presented as documentary photography.

## Days 31-60: Shared control boundaries

### Workstream 6: Transactional publication state machine

**Files:** `agent/moderation.py`, `agent/social.py`, `agent/scheduler.py`, `agent/database.py`, `agent/self_evolve.py`, `agent/kb_versioning.py`, `agent/knowledge.py`.

- [ ] Encode state-transition tests for provider failure, scheduled publication, autonomous upsert, fitness failure, rollback, and reload.
- [ ] Add synchronized regressions for unrelated edits during a long guarded apply and for partial apply followed by an exception.
- [ ] Give each guarded operation an owned atomic commit/version, reentrant transaction boundary, or targeted three-way rollback so rollback cannot erase unrelated edits.
- [ ] Report `rollback_conflict` and `rollback_failed` as explicit failure outcomes; never emit `decision="rolled_back"` when the rejected mutation remains active.
- [ ] Introduce explicit pending/approved/rejected/quarantined transitions.
- [ ] Keep rejected autonomous mutations outside PostgreSQL or compensate them transactionally.
- [ ] Preserve file mode before fsync and define deployment requirements for ownership/ACL durability; validate on POSIX CI.
- [ ] Acceptance: unavailable moderation never creates public content; a reported rollback restores the authoritative DB state; unrelated concurrent edits survive guarded failures.

### Workstream 7: Shared pinned outbound HTTP client

**Files:** new focused egress module plus `agent/admin.py`, `agent/auto_learn.py`, `agent/gpt55_quality_burst.py`.

- [ ] Add mock DNS/redirect tests for allowed, blocked, mixed-address, and peer-mismatch cases.
- [ ] Resolve, classify, connect, and verify one peer set per hop while preserving TLS hostname validation.
- [ ] Acceptance: every mapped remote fetch uses the shared client and no redirect bypasses destination policy.

### Workstream 8: Closed production profile and release gates

**Files:** Compose manifests, Nginx configuration, startup validation, `.github/workflows/deploy.yml`.

- [ ] Add CI tests that reject public internal-service bindings and placeholder/fallback credentials.
- [ ] Establish one authoritative production profile with only HTTP(S) ingress published.
- [ ] Run tests/build/security gates before publishing trusted container tags.
- [ ] Acceptance: policy tests fail on unsafe Compose variants; no image is published before verification succeeds.

### Workstream 9: Export and sensitive-data hygiene

**Files:** admin CSV exporters, entity CSV frontend, LLM settings API, bot logging.

- [ ] Add harmless formula-prefix tests and neutralize cells at every spreadsheet export boundary.
- [ ] Separate secret-bearing settings storage from generic reads and redact private message logs.
- [ ] Acceptance: parsed CSV cells are text, generic settings responses contain no credential, and INFO logs contain no message body or platform identifier.

## Days 61-90: Containment, measurement, and architecture debt

### Workstream 10: Bounded work and cancellation

**Files:** ASGI middleware, image storage/decoding, webhook gateway, parallel tool executor, scheduler.

- [ ] Add bounded streaming-body, decoded-pixel, cancellation, lease, and overlap tests.
- [ ] Enforce limits at resource consumers rather than trusting `Content-Length` or `Future.result()` timeouts.
- [ ] Acceptance: oversized synthetic inputs stop before unbounded allocation; timed-out work cannot continue side effects or overlap retries.

### Workstream 11: Source-of-truth and provenance contracts

**Files:** DB/export tooling, prerender inputs, data schemas, validation tests.

- [ ] Define distinct `publishedAt`, `reviewedAt`, and `fieldVerifiedAt` semantics.
- [ ] Add DB-to-export contract tests and a restore drill that never imports stale JSON over newer PostgreSQL state.
- [ ] Complete the merged-province truth-sync inventory.
- [ ] Acceptance: exports cannot manufacture verification claims and restore direction is explicitly proven.

### Workstream 12: Measure and split high-complexity ownership boundaries

**Files:** `agent/admin.py`, `agent/social.py`, `agent/server.py`, scheduler modules, benchmark/test tooling.

- [ ] Record p50/p95 latency, peak RSS, queue depth, and provider-token parity for new boundaries.
- [ ] Split modules only along proven ownership boundaries: public projection, conversation context, egress, publication state, and managed work.
- [ ] Stabilize frontend default test timeout and Python 3.14 timing tests.
- [ ] Acceptance: no scorecard regression, no new test flakes, and each extracted component has a documented owner/interface and focused tests.

## Program Gates

- [ ] Every production change follows RED-GREEN-REFACTOR.
- [ ] No data operation runs without the backup requirement in `CLAUDE.md`.
- [ ] Each workstream ends with focused tests, owning-package tests, lint/type/build checks, and a rollback statement.
- [ ] Deployment, secret rotation, legal decisions, and paid-service changes require explicit owner approval.
- [ ] The 59 original findings are revalidated against the final implementation before closure.
