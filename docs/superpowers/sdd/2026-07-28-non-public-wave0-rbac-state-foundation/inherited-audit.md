> STATUS: done — audit kế thừa NP-0, thực hiện trong `codex/non-public-wave0` (đã hợp vào `main` 2026-08-08).
> Giữ lại làm hồ sơ: bản gốc nằm trong thư mục Git-ignore `.superpowers/` của worktree, mất khi gỡ worktree.

# Inherited NP-0 audit — controller fallback

Reviewer status: independent audit dispatch failed because the configured
provider returned `HTTP 404: No active credentials for provider: openai`.
This file records the controller fallback review; it is not represented as an
independent reviewer verdict.

## Task mapping

- Task 1: implemented in `agent/admin_permissions.py`, `agent/admin.py`, and
  `agent/tests/test_admin_permissions.py`. Existing symbols remain importable
  from `admin`; unknown AdminCP routes now fail closed.
- Task 2: implemented in `agent/auth.py`; `_safe_user` exposes normalized
  `admin_scopes` for moderator, admin, superadmin, custom-scope, and regular
  user cases.
- Task 3: implemented in `web-nuxt/utils/adminAccess.ts`,
  `web-nuxt/types/index.ts`, and `web-nuxt/tests/admin-access.test.ts`.
- Task 4: implemented in `web-nuxt/utils/adminNavigation.ts` and
  `web-nuxt/middleware/admin.ts`; longest-prefix route resolution, unknown-route
  fail-closed behavior, moderator landing, and `/403` routing are covered.
- Task 5: implemented in `web-nuxt/components/system/SystemStatePanel.vue`,
  `web-nuxt/pages/403.vue`, and the component behavior test.
- Task 6: implemented in `web-nuxt/layouts/admin.vue` and shell behavior tests.
  `CommandPalette.vue` is also scope-filtered so a hidden route cannot remain
  exposed through the command surface.
- Task 7: verification is green; documentation/checkbox handoff still needs to
  be updated after the implementation commits exist.

## Verification evidence

- Backend focused suite: 101 passed.
- Frontend focused suite: 4 files, 110 tests passed.
- Nuxt typecheck: PASS.
- Nuxt production build: PASS.
- `git diff --check`: PASS; only line-ending conversion warnings were emitted.

## Review verdict

Spec compliance: PASS for Tasks 1–6.

Code quality: PASS with one integration concern. The inherited worktree starts
from `8f2d913e`, while the active public-foundation branch has newer commits;
the NP-0 commits should be integrated only after a conflict-aware rebase or
cherry-pick and a fresh full-suite run. No Critical or Important finding was
identified in the isolated NP-0 diff.

## Fresh verification after takeover

- Backend focused suite: 101 passed.
- Frontend full suite: 40 files / 937 tests passed.
- Frontend focused foundation suite: 3 files / 25 tests passed.
- Nuxt typecheck and production build: passed.
- Full backend suite: timed out after 10 minutes; treat as unverified until a
  later integration run can complete it.
- Isolation shows the timeout comes from `agent/tests/test_chat_history_continuity.py`:
  it uses `TestClient(server.app)` without the `integration` marker, causing
  lifespan startup to migrate `web/data.json` into a missing local knowledge
  SQLite database. This predates the NP-0 diff; the first ten files and the
  next six non-history files pass when run independently.
- Independent review provider remained unavailable after one explicit-model
  retry, so the controller fallback remains the only review evidence.
