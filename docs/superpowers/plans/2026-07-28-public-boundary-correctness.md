# Public Boundary Correctness Implementation Plan

> STATUS: active - approved design is `docs/superpowers/specs/2026-07-28-public-boundary-correctness-design.md`; implementation is authorized in the isolated `codex/security-correctness-wave0` worktree.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce one fail-closed public profile policy, prevent authenticated responses from entering shared caches, make logout truthful, and bound Nuxt backend requests.

**Architecture:** A new backend `profile_access` module owns audience/activity decisions and is consumed by all profile-section endpoints. Authentication dependencies mark successfully resolved viewers so final response middleware can override unsafe public caching. Frontend auth state changes only after authoritative server outcomes, while shared and launch-specific fetch boundaries receive explicit total deadlines.

**Tech Stack:** Python 3.14, FastAPI, pytest, Nuxt 4, Vue 3, TypeScript, Vitest, ofetch.

## Global Constraints

- Do not modify `agent/admin.py`, `agent/auth.py`, admin authorization/navigation code, or the concurrent non-public Wave 0 spec and plan.
- Do not modify homepage/design-system work, modal UX, mention autocomplete, or service-worker policy.
- Preserve audience semantics: `public` allows non-blocked viewers; `followers`, `followers_only`, and `private` allow self or current followers; unknown visibility fails closed; a missing privacy row uses the legacy `followers_only` audience fallback and explicit activity permission is required for activity-bearing sections.
- `show_activity=false` hides posts, reviews, engagement, timeline, and heatmap from non-self viewers, but does not independently hide follower/following lists.
- Hidden collection endpoints keep their current empty response shapes; hidden engagement returns the same keys with zero values; missing/inactive/deleted targets remain 404.
- Authenticated API responses must end with `Cache-Control: private, no-store`, even if the endpoint set a public value; anonymous public TTLs remain unchanged.
- `Vary` merging is case-insensitive and must retain existing members while adding `Authorization`, `Cookie`, and `Accept` for API/auth/admin routes.
- Logout clears local auth state only after backend 2xx. CSRF 403, network failures, deadlines, and 5xx preserve local state and surface an error.
- Deadline constants are exact: ordinary API/auth `10_000 ms`, launch attestation `3_000 ms`, guarded sitemap `5_000 ms`.
- No database migration, dependency addition, data rewrite, or API version bump.
- Every behavior change follows strict red-green-refactor TDD and each task commits only its scoped files.

---

### Task 1: Shared Profile Access Decision

**Files:**
- Create: `agent/profile_access.py`
- Modify: `agent/social.py`
- Test: `agent/tests/test_social_privacy_boundary.py`

**Interfaces:**
- Produces: `ProfileAccessDecision`, `can_view_profile_audience()`, and `resolve_profile_access()`.
- `resolve_profile_access(conn, target_id, viewer_id, require_activity)` returns a frozen decision with `status`, `target_id`, `is_self`, and `can_view_activity`.
- Later tasks consume this interface without duplicating audience, follower, block, or activity checks.

- [ ] **Step 1: Write failing policy tests**

Add literal table tests to `agent/tests/test_social_privacy_boundary.py`:

```python
from profile_access import can_view_profile_audience, resolve_profile_access


@pytest.mark.parametrize(
    ("visibility", "is_self", "is_follower", "expected"),
    [
        ("public", False, False, True),
        ("followers", False, False, False),
        ("followers", False, True, True),
        ("followers_only", False, True, True),
        ("private", False, True, True),
        ("private", False, False, False),
        ("unknown", False, False, False),
        ("public", True, False, True),
    ],
)
def test_profile_access_audience_matrix(visibility, is_self, is_follower, expected):
    assert can_view_profile_audience(visibility, is_self, is_follower) is expected
```

Use a deterministic fake connection/fetch sequence to prove `resolve_profile_access()` returns `not_found` for inactive/deleted targets; `hidden` for bidirectional blocks, unauthorized non-followers, unknown visibility, and disabled/missing activity permission; and `ok` for self plus authorized follower cases. For a missing privacy row, assert that an anonymous viewer is hidden and a follower may view relationships but not activity.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_social_privacy_boundary.py
```

Expected: collection/import failure because `profile_access` does not exist.

- [ ] **Step 3: Implement the minimal policy module**

Create `agent/profile_access.py` with this public shape:

```python
from dataclasses import dataclass
from typing import Literal

from database import db

AccessStatus = Literal["ok", "hidden", "not_found"]


@dataclass(frozen=True)
class ProfileAccessDecision:
    status: AccessStatus
    target_id: str | None = None
    is_self: bool = False
    can_view_activity: bool = False


def can_view_profile_audience(visibility: str, is_self: bool, is_follower: bool) -> bool:
    if is_self or visibility == "public":
        return True
    return visibility in {"followers", "followers_only", "private"} and is_follower


def resolve_profile_access(conn, target_id: str, viewer_id: str | None, *, require_activity: bool) -> ProfileAccessDecision:
    ph = db._ph
    row = db._fetchone(conn, f"""
        SELECT u.id, pv.profile_visibility, pv.show_activity
        FROM users u
        LEFT JOIN user_privacy pv ON pv.user_id = u.id
        WHERE u.id::text = {ph} AND u.is_active = TRUE AND u.deleted_at IS NULL
    """, (target_id,))
    if not row:
        return ProfileAccessDecision("not_found")
    target = db._row_to_dict(row)
    resolved_id = str(target["id"])
    is_self = viewer_id == resolved_id
    if is_self:
        return ProfileAccessDecision("ok", resolved_id, True, True)
    if viewer_id:
        blocked = db._fetchone(conn, f"""
            SELECT 1 FROM blocks
            WHERE (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
               OR (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
        """, (viewer_id, resolved_id, resolved_id, viewer_id))
        if blocked:
            return ProfileAccessDecision("hidden", resolved_id)
    visibility = target.get("profile_visibility") or "followers_only"
    is_follower = False
    if viewer_id and visibility != "public":
        is_follower = db._fetchone(conn, f"""
            SELECT 1 FROM follows
            WHERE follower_id = {ph}::uuid AND target_type = 'user' AND target_id = {ph}
        """, (viewer_id, resolved_id)) is not None
    if not can_view_profile_audience(visibility, False, is_follower):
        return ProfileAccessDecision("hidden", resolved_id)
    can_view_activity = target.get("show_activity") is True
    if require_activity and not can_view_activity:
        return ProfileAccessDecision("hidden", resolved_id)
    return ProfileAccessDecision("ok", resolved_id, False, can_view_activity)
```

The implementation must query an active, non-deleted user and its privacy row, default missing privacy to fail-closed `followers_only` for non-self viewers, check blocks in both directions, query follower state only when needed, and enforce `show_activity` only when `require_activity=True`.

Replace `social._profile_can_view_full()` with an import/alias to the pure predicate. Refactor `_timeline_visibility_gate()` to consume `resolve_profile_access()` and preserve its `notfound`/`hidden`/`ok` adapter return.

- [ ] **Step 4: Run focused and compatibility tests**

Run:

```powershell
python -m pytest -q agent/tests/test_social_privacy_boundary.py agent/tests/test_gap_fixes.py agent/tests/test_qa_fixes.py
```

Expected: all pass, with the existing PostgreSQL-only skip allowed.

- [ ] **Step 5: Commit**

```powershell
git add agent/profile_access.py agent/social.py agent/tests/test_social_privacy_boundary.py
git commit -m "fix: centralize profile access decisions"
```

---

### Task 2: Enforce Profile Access Across Sibling Endpoints

**Files:**
- Modify: `agent/social.py`
- Modify: `agent/public_api.py`
- Test: `agent/tests/test_social_privacy_boundary.py`

**Interfaces:**
- Consumes: `resolve_profile_access()` from Task 1.
- Produces: uniform privacy enforcement for posts, reviews, following, followers, heatmap, and engagement; timeline/profile behavior remains compatible.

- [ ] **Step 1: Write failing endpoint-family regressions**

Add tests that inject literal `ProfileAccessDecision` results and verify each route maps them correctly:

```python
def test_hidden_user_posts_returns_existing_empty_shape(monkeypatch):
    monkeypatch.setattr(social, "resolve_profile_access", lambda *_a, **_k: ProfileAccessDecision("hidden", USER_ID))
    result = asyncio.run(social.get_user_posts(USER_ID, _request(None), page=2, limit=20))
    assert result == {"posts": [], "total": 0, "page": 2, "has_more": False}
```

Add equivalent literal assertions for reviews, following, followers, and heatmap. Add engagement tests for anonymous hidden, authorized follower, blocked viewer, and missing target. The hidden engagement value must be:

```python
{
    "user_id": USER_ID,
    "total_posts": 0,
    "total_reviews": 0,
    "avg_rating": 0.0,
    "total_questions": 0,
    "entities_reviewed": 0,
    "followers": 0,
    "total_likes_received": 0,
}
```

The engagement query must count questions only when `moderation_status='approved'`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_social_privacy_boundary.py
```

Expected: protected sibling endpoints still query/return data or do not accept viewer auth.

- [ ] **Step 3: Add one adapter per response family**

At the start of each endpoint's database worker, call `resolve_profile_access()` with:

- `require_activity=True`: posts, reviews, heatmap, engagement;
- `require_activity=False`: following, followers.

Use `viewer_id = str(user["id"]) if user else None`. Add optional authentication to engagement with `request: Request` and `user=Depends(get_current_user)`. Return 404 only for `not_found`, the exact empty shape for `hidden`, and query data only for `ok`. Do not reimplement follower/block/privacy SQL in the endpoints.

- [ ] **Step 4: Run privacy and route compatibility suites**

Run:

```powershell
python -m pytest -q agent/tests/test_social_privacy_boundary.py agent/tests/test_wave2.py agent/tests/test_wave3.py agent/tests/test_writepaths_ugc.py agent/tests/test_qa_fixes.py
```

Expected: all pass, with environment-specific PostgreSQL skips allowed.

- [ ] **Step 5: Commit**

```powershell
git add agent/social.py agent/public_api.py agent/tests/test_social_privacy_boundary.py
git commit -m "fix: enforce privacy across profile sections"
```

---

### Task 3: Final Personalized Cache Classification

**Files:**
- Modify: `agent/auth_middleware.py`
- Modify: `agent/server.py`
- Create: `agent/tests/test_personalized_cache_policy.py`
- Modify: `agent/tests/test_salvage_hardening.py`

**Interfaces:**
- Produces: request-state marker `authenticated_user_id` after valid auth resolution.
- Produces: `_merge_vary_header()` and `_apply_final_cache_policy(request, response)` in `agent/server.py`.

- [ ] **Step 1: Write failing auth-state and response-policy tests**

Create `agent/tests/test_personalized_cache_policy.py` with real Starlette `Request`/`Response` objects. Cover:

```python
def test_authenticated_api_response_overrides_public_cache():
    request = _request("/api/search")
    request.state.authenticated_user_id = USER_ID
    response = Response(headers={"Cache-Control": "public, max-age=30", "Vary": "Accept-Encoding"})
    server._apply_final_cache_policy(request, response)
    assert response.headers["Cache-Control"] == "private, no-store"
    assert {part.strip().lower() for part in response.headers["Vary"].split(",")} == {
        "accept-encoding", "authorization", "cookie", "accept",
    }
```

Also prove anonymous public cache survives, invalid/no credentials do not set the marker, valid `get_current_user`, `require_user`, and `require_role` do set it, and repeated/case-varied `Vary` members are deduplicated.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest -q agent/tests/test_personalized_cache_policy.py
```

Expected: missing marker/policy helpers and unsafe public cache remains.

- [ ] **Step 3: Implement auth marking and final policy**

In `agent/auth_middleware.py`, add one private helper that records `str(user["id"])` only after `_get_current_user_or_none()` returns a valid user. Call it from `get_current_user`, `require_user`, and `require_role`; never mark absent/invalid credentials.

In `agent/server.py`, implement case-insensitive `Vary` merging and call `_apply_final_cache_policy()` from `security_headers()` after `call_next()`. For `/api/`, `/auth/`, and `/admin/`, merge `Authorization`, `Cookie`, and `Accept`. For authenticated `/api/` responses, override any existing cache header with `private, no-store`. Preserve endpoint public cache for anonymous responses and existing no-store/private values.

Update the legacy salvage assertion to validate behavior through the helper rather than requiring an exact source line.

- [ ] **Step 4: Run cache/security regression suites**

Run:

```powershell
python -m pytest -q agent/tests/test_personalized_cache_policy.py agent/tests/test_salvage_hardening.py agent/tests/test_policy_http.py agent/tests/test_session_be.py
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add agent/auth_middleware.py agent/server.py agent/tests/test_personalized_cache_policy.py agent/tests/test_salvage_hardening.py
git commit -m "fix: prevent shared caching of authenticated responses"
```

---

### Task 4: Truthful Frontend Logout

**Files:**
- Modify: `web-nuxt/composables/useAuth.ts`
- Modify: `web-nuxt/components/UserMenu.vue`
- Create: `web-nuxt/tests/auth-logout.test.ts`

**Interfaces:**
- `logout(): Promise<void>` rejects on non-2xx and clears all client auth state only after backend success.
- `UserMenu` shows `Không thể đăng xuất. Phiên của bạn vẫn đang hoạt động.` as an error toast on rejection.

- [ ] **Step 1: Write failing composable and component tests**

In `web-nuxt/tests/auth-logout.test.ts`, initialize real Nuxt state through `useAuth()`, set a user/token/CSRF/2FA challenge, and stub `$fetch` for the logout call. Assert:

```typescript
await expect(auth.logout()).rejects.toThrow('csrf rejected')
expect(auth.user.value?.id).toBe('user-1')
expect(auth.token.value).toBe('session-token')
```

For success, assert user/token/CSRF and `twoFactorChallenge` are all cleared. Mount the real `UserMenu` with a mocked rejecting `logout` and real toast spy; click `Đăng xuất` and assert the exact error copy and type `error`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
npx vitest run tests/auth-logout.test.ts
```

Expected: current logout resolves and clears state after failure; component does not show an error.

- [ ] **Step 3: Implement server-authoritative state transition**

Remove the swallow-all `try/catch` from `logout()`. Await the backend request first, then clear `token`, `user`, `csrfToken`, and `twoFactorChallenge`. In `UserMenu.doLogout()`, catch rejection and call:

```typescript
showToast('Không thể đăng xuất. Phiên của bạn vẫn đang hoạt động.', 'error', 5000)
```

Do not navigate, reload, or call `handleSessionExpired()` on a generic logout failure.

- [ ] **Step 4: Run focused frontend tests**

Run:

```powershell
npx vitest run tests/auth-logout.test.ts tests/ui-foundation-shell.test.ts
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add web-nuxt/composables/useAuth.ts web-nuxt/components/UserMenu.vue web-nuxt/tests/auth-logout.test.ts
git commit -m "fix: keep logout state truthful"
```

---

### Task 5: Bounded Nuxt Backend Requests

**Files:**
- Create: `web-nuxt/utils/requestDeadline.ts`
- Modify: `web-nuxt/utils/apiFetch.ts`
- Modify: `web-nuxt/composables/useAuth.ts`
- Modify: `web-nuxt/server/utils/launch/backendAttestation.ts`
- Modify: `web-nuxt/server/utils/launch/guardedSitemapProxy.ts`
- Create: `web-nuxt/tests/api-fetch-timeout.test.ts`
- Modify: `web-nuxt/tests/auth-logout.test.ts`
- Modify: `web-nuxt/tests/launch-attestation.test.ts`
- Modify: `web-nuxt/tests/launch-guarded-sitemap.test.ts`

**Interfaces:**
- Exports: `DEFAULT_API_TIMEOUT_MS = 10_000`, `ATTESTATION_TIMEOUT_MS = 3_000`, `SITEMAP_TIMEOUT_MS = 5_000`.
- Exports: `withRequestDeadline<T>(timeoutMs, operation)` that aborts and rejects a never-settling operation.
- `apiFetch` supplies `DEFAULT_API_TIMEOUT_MS` unless the caller explicitly sets `timeout`.

- [ ] **Step 1: Write failing deadline tests**

Add boundary tests proving `apiFetch` passes `timeout: 10_000`, preserves `timeout: 750`, and all auth requests use `apiFetch`. Extend launch tests with fake timers and a fetcher that never settles:

```typescript
vi.useFakeTimers()
const pending = fetchBackendAttestation({
  baseURL: 'http://agent.internal:8360',
  fetcher: vi.fn((_request, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new Error('aborted')))
  })),
})
await vi.advanceTimersByTimeAsync(3_000)
await expect(pending).rejects.toThrow(/unavailable/i)
```

Add the equivalent `5_000 ms` guarded-sitemap transport test. Add auth tests proving timeout/5xx from `fetchMe()` preserves existing user/token, while 401 clears them.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
npx vitest run tests/api-fetch-timeout.test.ts tests/auth-logout.test.ts tests/launch-attestation.test.ts tests/launch-guarded-sitemap.test.ts
```

Expected: missing constants/deadline helper; never-settling fetches remain pending; transient auth errors clear state.

- [ ] **Step 3: Implement deadline utilities and adoption**

Create `requestDeadline.ts` with an `AbortController`, timer, and `finally` cleanup. The operation receives the controller signal; timeout aborts and rejects with an error containing the deadline. Extend attestation and sitemap fetcher option types with `signal`; wrap their real calls in `withRequestDeadline()` using the exact constants.

In `apiFetch`, merge options as `{ timeout: DEFAULT_API_TIMEOUT_MS, ...opts }` so explicit callers win. Replace direct `$fetch` calls in `useAuth.ts` with `apiFetch`, including `authFetch`. Update `fetchMe()` so only status 401 clears established auth state; deadline/network/5xx preserve it. Preserve existing initial anonymous behavior.

- [ ] **Step 4: Run full frontend verification**

Run:

```powershell
npx vitest run tests/api-fetch-timeout.test.ts tests/auth-logout.test.ts tests/launch-attestation.test.ts tests/launch-guarded-sitemap.test.ts
npm test
npm run typecheck
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```powershell
git add web-nuxt/utils/requestDeadline.ts web-nuxt/utils/apiFetch.ts web-nuxt/composables/useAuth.ts web-nuxt/server/utils/launch/backendAttestation.ts web-nuxt/server/utils/launch/guardedSitemapProxy.ts web-nuxt/tests/api-fetch-timeout.test.ts web-nuxt/tests/auth-logout.test.ts web-nuxt/tests/launch-attestation.test.ts web-nuxt/tests/launch-guarded-sitemap.test.ts
git commit -m "fix: bound Nuxt backend requests"
```

---

## Final Verification

After all task reviews are clean, run:

```powershell
python -m pytest -q agent/tests/test_social_privacy_boundary.py agent/tests/test_personalized_cache_policy.py agent/tests/test_policy_http.py agent/tests/test_session_be.py agent/tests/test_wave2.py agent/tests/test_wave3.py agent/tests/test_writepaths_ugc.py agent/tests/test_qa_fixes.py
python -m pytest -q tests/checks
npm test --prefix web-nuxt
npm run typecheck --prefix web-nuxt
npm run build --prefix web-nuxt
python scripts/checks/run_hard.py --all
```

Then dispatch one whole-branch reviewer over the full branch diff and resolve its findings through one fix wave and one scoped re-review.
