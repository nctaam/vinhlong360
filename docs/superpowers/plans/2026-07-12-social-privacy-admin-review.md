# Social Privacy and Admin Review Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the saved-list privacy bypass, followers-only profile bypass, and hidden-field provisional approval gap with regression-backed server and admin UI boundaries.

**Architecture:** Enforce saved visibility in SQL, centralize profile audience selection in a small helper, and bind manual approval to a complete canonical review snapshot with a stale-review token. Keep database schemas and internal entity storage unchanged.

**Tech Stack:** Python 3.14, FastAPI, pytest, Nuxt 4, Vue 3, TypeScript, Vitest.

---

### Task 1: Enforce saved-list visibility in the friend-saves query

**Files:**
- Modify: `agent/social.py:1188-1241`
- Create: `agent/tests/test_social_privacy_boundary.py`

- [ ] **Step 1: Write the failing query-boundary test**

Add a test that calls `get_friend_saves()` with monkeypatched connection helpers, captures the executed SQL, and asserts both controls are present:

```python
assert "LEFT JOIN user_privacy save_privacy ON save_privacy.user_id = s.user_id" in sql
assert "COALESCE(save_privacy.show_saved, TRUE) = TRUE" in sql
```

Also return one synthetic visible row from the fake query and assert the existing response shape is preserved.

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_social_privacy_boundary.py::test_friend_saves_enforces_owner_visibility_in_sql -q`

Expected: FAIL because the current SQL never reads `user_privacy.show_saved`.

- [ ] **Step 3: Add the minimal SQL control**

Inside the inner `saved_entities` query, add:

```sql
LEFT JOIN user_privacy save_privacy ON save_privacy.user_id = s.user_id
```

and the predicate:

```sql
AND COALESCE(save_privacy.show_saved, TRUE) = TRUE
```

Do not change ordering, deduplication, block filtering, limits, or response fields.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest agent/tests/test_social_privacy_boundary.py::test_friend_saves_enforces_owner_visibility_in_sql -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add agent/social.py agent/tests/test_social_privacy_boundary.py
git commit -m "fix: enforce saved-list privacy in friend feed"
```

### Task 2: Enforce followers-only profile visibility

**Files:**
- Modify: `agent/social.py:3705-3925`
- Test: `agent/tests/test_social_privacy_boundary.py`

- [ ] **Step 1: Add failing endpoint and policy tests**

Add a direct async endpoint test with `_profile_query` returning `vis="followers"`, `is_self=False`, and `is_follower=False`. Call `get_user_profile(..., user=None)` and assert the result has `is_private=True`, blank bio, zero post/review counts, and no reputation.

Add policy controls for the wished-for helper:

```python
assert _profile_can_view_full("public", False, False) is True
assert _profile_can_view_full("followers", False, False) is False
assert _profile_can_view_full("followers", False, True) is True
assert _profile_can_view_full("followers_only", False, False) is False
assert _profile_can_view_full("private", False, True) is True
assert _profile_can_view_full("private", False, False) is False
assert _profile_can_view_full("unknown", False, False) is False
assert _profile_can_view_full("followers", True, False) is True
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest agent/tests/test_social_privacy_boundary.py -q`

Expected: FAIL because `followers` currently reaches `_profile_full_response()` and `_profile_can_view_full` does not exist.

- [ ] **Step 3: Implement the audience helper and wire the endpoint**

Add:

```python
def _profile_can_view_full(vis: str, is_self: bool, is_follower: bool) -> bool:
    if is_self or vis == "public":
        return True
    if vis in {"followers", "followers_only", "private"}:
        return is_follower
    return False
```

After the blocked response, replace the literal `private` condition with:

```python
if not _profile_can_view_full(vis, is_self, is_follower):
    return _profile_private_response(profile, follower_count)
```

- [ ] **Step 4: Run GREEN and nearby profile tests**

Run: `python -m pytest agent/tests/test_social_privacy_boundary.py agent/tests/test_gap_fixes.py agent/tests/test_upgrade_round2.py agent/tests/test_wave3.py -q`

Expected: PASS with only documented baseline xfails/skips.

- [ ] **Step 5: Commit**

```powershell
git add agent/social.py agent/tests/test_social_privacy_boundary.py
git commit -m "fix: enforce followers-only profile audience"
```

### Task 3: Bind provisional approval to the complete reviewed snapshot

**Files:**
- Modify: `agent/kb_curation.py:21-99`
- Modify: `agent/admin.py:3315-3340`
- Modify: `agent/tests/test_kb_curation.py`
- Modify: `agent/tests/test_admin_mutations.py`
- Modify: `web-nuxt/pages/admin/duyet-tu-hoc.vue`
- Create: `web-nuxt/tests/admin-provisional-review.test.ts`

- [ ] **Step 1: Add failing backend review-contract tests**

Extend the provisional fixture with a long summary, `source`, coordinates, images, attributes, address, and an uncommon provider field. Assert `list_provisional()` returns:

```python
{
    "id": "prov-1",
    "review_token": <64 lowercase hex characters>,
    "entity": <the complete entity snapshot without status/verified>,
}
```

Assert the summary is not truncated and every supplied field remains in `entity`.

Capture a token, change one hidden field in the fixture, then assert:

```python
result = kb_curation.promote("prov-1", old_token)
assert result == {"ok": False, "error": "stale_review"}
```

Assert a matching current token promotes successfully.

- [ ] **Step 2: Run backend RED**

Run: `python -m pytest agent/tests/test_kb_curation.py -q`

Expected: FAIL because the list is abbreviated and `promote()` has no review token.

- [ ] **Step 3: Implement canonical snapshots and stale-review rejection**

In `kb_curation.py`, add canonical snapshot/token helpers using `copy.deepcopy`, `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)`, SHA-256, and `hmac.compare_digest`.

Exclude only `status` and `verified` from the review snapshot. Return `id`, `review_token`, and `entity` from `list_provisional()`. Change manual `promote` to require `review_token`, recompute it from the current entity, and return `stale_review` before any mutation when the token differs.

- [ ] **Step 4: Require the token at the admin API boundary**

Add a Pydantic request model with one required 64-character lowercase hex `review_token`. Pass it to `kb_curation.promote()`. Map `stale_review` to HTTP 409, `not found` to 404, and other failures to 400.

Update the mutation regression so approval without a body expects 422.

- [ ] **Step 5: Add the failing frontend contract test**

Create a Vitest source regression that asserts the page defines a dedicated `ProvisionalReview` interface, reads `e.entity`, visibly renders complete summary/source/coordinates/images/attributes and the full snapshot, and sends:

```ts
body: { review_token: e.review_token }
```

Run: `npm test -- --run tests/admin-provisional-review.test.ts`

Expected: FAIL against the abbreviated table and body-less approval request.

- [ ] **Step 6: Implement the review UI**

Replace the `Entity[]` cast with explicit review DTO interfaces. Render common publication fields in the review card/table and include an expandable canonical JSON block so uncommon provider fields are visible before approval. Normalize `source` for object, array, or string shapes. Send the review token in the approval body.

- [ ] **Step 7: Run backend and frontend GREEN**

Run:

```powershell
python -m pytest agent/tests/test_kb_curation.py agent/tests/test_admin_mutations.py agent/tests/test_chat_smoke.py -q
cd web-nuxt
npm test -- --run tests/admin-provisional-review.test.ts tests/smoke.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add agent/kb_curation.py agent/admin.py agent/tests/test_kb_curation.py agent/tests/test_admin_mutations.py web-nuxt/pages/admin/duyet-tu-hoc.vue web-nuxt/tests/admin-provisional-review.test.ts
git commit -m "fix: bind provisional approval to reviewed snapshot"
```

### Task 4: Cross-cutting verification and roadmap evidence

**Files:**
- Modify: `docs/superpowers/plans/2026-07-12-social-privacy-admin-review.md`
- Modify: `docs/superpowers/plans/2026-07-12-security-remediation-30-60-90.md`
- Modify: `docs/superpowers/specs/2026-07-12-social-privacy-admin-review-design.md`
- Write: existing scan bundle `artifacts/fix_report.md`

- [ ] **Step 1: Run focused security suites**

```powershell
python -m pytest agent/tests/test_social_privacy_boundary.py agent/tests/test_kb_curation.py agent/tests/test_admin_mutations.py agent/tests/test_gap_fixes.py agent/tests/test_upgrade_round2.py agent/tests/test_wave3.py -q
```

- [ ] **Step 2: Run backend static checks**

```powershell
python -m ruff check agent/social.py agent/kb_curation.py agent/admin.py agent/tests/test_social_privacy_boundary.py agent/tests/test_kb_curation.py agent/tests/test_admin_mutations.py
python -m py_compile agent/social.py agent/kb_curation.py agent/admin.py
git diff --check
```

- [ ] **Step 3: Run frontend checks**

```powershell
cd web-nuxt
npm test -- --run tests/admin-provisional-review.test.ts tests/smoke.test.ts
npm run typecheck
npm run build
```

- [ ] **Step 4: Run the full backend suite**

Run: `python -m pytest -q`

Expected baseline comparison: no new failures relative to `5922 passed, 37 skipped, 80 deselected, 1 xfailed`.

- [ ] **Step 5: Review bypass variants and preserve controls**

Recheck direct callers and sibling paths. Confirm missing privacy rows remain visible for friend saves, followers/self remain authorized for followers-only profiles, unknown profile visibility fails closed, stale approval makes no file/DB/reload mutation, reject remains unchanged, and automatic promotion remains explicitly out of the manual-token flow.

- [ ] **Step 6: Update evidence and commit**

Mark Workstream 2 complete only after all gates pass. Append this batch to the existing scan `artifacts/fix_report.md`, mark this plan/spec done, and commit the documentation changes.
