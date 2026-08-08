> STATUS: done — sổ tiến độ SDD của `codex/non-public-wave0` (đã hợp vào `main` 2026-08-08).
> Giữ lại làm hồ sơ: bản gốc nằm trong thư mục Git-ignore `.superpowers/`, mất khi gỡ worktree.

# SDD ledger — plan: docs/superpowers/plans/2026-07-28-non-public-wave0-rbac-state-foundation.md

Baseline for takeover: 8f2d913ed3808ff434b02ec821ea2fd2f23e6cb8.
Worktree: C:\Code\vl360-wt\non-public-wave0 (branch codex/non-public-wave0).
The inherited worktree contains uncommitted changes spanning Tasks 1–6; no
task is marked complete until its diff, focused tests, and review evidence are
reconciled. The homepage/public catalog/database constraints remain binding.

Dispatch note: fresh audit implementer failed with external provider error
`HTTP 404: No active credentials for provider: openai`; controller fallback is
recorded and must not be mistaken for independent review.

Inherited state: Tasks 1–6 appear partially implemented in the working tree;
Task 7 has not been verified. First action is a read-only diff and focused
baseline audit before any task-specific commit.

Controller fallback audit: Tasks 1–6 map to the approved plan and focused
verification is green (backend 101; frontend 110; typecheck/build PASS). No
Critical or Important finding identified. Integration concern: this worktree
has an older branch baseline and must be reconciled with the active branch
before merge.

Task 1: complete (commit ba9637c3, controller review fallback; focused backend
101 passed; Ruff clean). Independent reviewer dispatch was retried with an
explicit model and failed again because the configured provider returned
`HTTP 404: No active credentials for provider: openai`.

Task 2: complete (commit ba9637c3, included with Task 1; focused auth/admin
regression 101 passed).

Task 3: complete (commit 7603ab01; resolver test 7 passed).

Task 4: complete (commit 7603ab01; resolver + shell tests 23 passed).

Task 5: complete (commit 644580f6; state component test 2 passed).

Task 6: complete (commit 4e071db4; shell test 16 passed; no emoji icons).

Task 7: verification evidence:
- Backend focused suite: 101 passed in 3.58s.
- Frontend focused suite: 25 passed.
- Frontend full suite: 40 files, 937 tests passed.
- Nuxt typecheck: exit 0.
- Nuxt build + launch-readiness manifest: exit 0; only existing sourcemap,
  chunk-size, and Node deprecation warnings.
- `git diff --check`: clean for committed changes.
- Full backend `python -m pytest -q` exceeded the 10-minute harness timeout;
  no pass claim is made for that command.
- Follow-up isolation: `agent/tests` with the configured 60-second per-test
  timeout reaches `test_chat_history_continuity` (not marked `integration`)
  and hangs in FastAPI lifespan while `knowledge._ensure()` migrates the
  4.4 MB `web/data.json` relationship graph into a missing local SQLite DB.
  The first ten backend files pass (204 passed, 16 skipped); the next six
  non-chat-history files pass (260 passed, 2 deselected). This is a baseline
  test-selection/data-bootstrap issue outside NP-0, not an authorization or
  AdminCP regression.

Documentation handoff remains intentionally separate: the canonical plan and
page inventory are untracked files in the parallel Plan A worktree and are
not present on this older NP-0 branch. They were not copied or edited to avoid
overwriting the other session's work; reconcile them during the approved
conflict-aware integration.
