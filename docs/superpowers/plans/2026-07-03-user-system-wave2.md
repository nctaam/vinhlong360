# Wave 2: Activity Timeline + Profile Depth — Implementation Plan
> STATUS (2026-07-10): done — plan đã thực thi & ship.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add activity timeline, profile visit tracking, badge progress, user discovery, following feed enrichment, and weekly digest to deepen user engagement.

**Architecture:** Backend endpoints in `social.py` (timeline, badge-progress, profile views, friend activity) + one new scheduler task in `scheduler.py` (weekly digest). One migration for `profile_views` table. Frontend additions in `nguoi-dung/[id].vue` (timeline tab, badge showcase, view counter) and `cong-dong.vue` (user search results in community). All queries use the established `asyncio.to_thread(_query)` pattern with `db._conn()`.

**Tech Stack:** FastAPI (backend), Nuxt 4 SSR / Vue 3 Composition API (frontend), PostgreSQL, CSS design tokens

## Global Constraints

- **DB pattern:** `with db._conn() as conn:` context manager, wrap in `await asyncio.to_thread(_query)`. Use `db._ph` for parameterized queries (`%s` for PG). `db._fetchone()`, `db._fetchall()`, `db._row_to_dict()`.
- **Router:** `router = APIRouter(prefix="/api")` in `social.py`. Use `Depends(require_user)` for auth-required, `Depends(get_current_user)` for optional auth.
- **CSS tokens:** `--error` (not `--danger`), `--ink` (not `--text`), `--primary`, `--success`, `--warning`, `--muted`, `--line`, `--space-N`, `--surface`, `--bg`.
- **Auth:** `useAuth()` → `authHeaders()` includes CSRF. No separate `csrf` ref.
- **Block/mute:** Use `_block_sql(user, col)` and `_mute_sql(user, col)` helpers for filtering.
- **Path validation:** `validate_path_id(id, "param_name")` for all UUID path params.
- **Test pattern:** Use `inspect.getsource()` to verify SQL keywords and function signatures in source code tests.
- **Privacy:** Private profiles show limited info to non-self viewers. Check `is_private` before returning data.
- **Migration numbering:** Next available is `063`.
- **Composables:** Auto-imported, `useXxx()` pattern, use `useState()` for cross-component shared state.
- **YAGNI:** Do not add Wave 3 hooks (achievements) to timeline — spec says "khi Wave 3 done".
- **Scheduler:** `ScheduledTask(name, func, interval_seconds, enabled, run_immediately)` registered in `TASKS` list at `scheduler.py:799`.
- **Notifications:** `create_notification(user_id, type, title, body, ref_type, ref_id, actor_id)` — handles blocks/mutes/prefs internally.

---

### Task 1: Profile View Tracking (Migration + Backend)

**Files:**
- Create: `agent/migrations/063_profile_views.sql`
- Modify: `agent/social.py` (add view logging in `get_user_profile` at line ~3296, add `view_count_7d` to self-profile response)
- Test: `agent/tests/test_wave2.py`

**Interfaces:**
- Consumes: `get_user_profile()` at `social.py:3296`, `_reputation()` at `social.py:3238`
- Produces: `view_count_7d: int` field in profile response (self-only), `_log_profile_view(conn, viewer_id, viewed_id)` internal function

- [ ] **Step 1: Write the migration**

```sql
-- agent/migrations/063_profile_views.sql
CREATE TABLE IF NOT EXISTS profile_views (
    id BIGSERIAL PRIMARY KEY,
    viewer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    viewed_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    viewed_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(viewer_id, viewed_id, viewed_date)
);

CREATE INDEX idx_profile_views_viewed_id_date ON profile_views(viewed_id, viewed_date);
```

- [ ] **Step 2: Write the test**

```python
# agent/tests/test_wave2.py
import inspect
import pytest


class TestProfileViewTracking:
    def test_log_profile_view_function_exists(self):
        from social import _log_profile_view
        assert callable(_log_profile_view)

    def test_log_profile_view_deduplicates_per_day(self):
        src = inspect.getsource(__import__("social")._log_profile_view)
        assert "ON CONFLICT" in src or "INSERT" in src
        assert "viewed_date" in src

    def test_profile_response_includes_view_count_for_self(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert "view_count_7d" in src

    def test_profile_view_skips_self_view(self):
        src = inspect.getsource(__import__("social")._log_profile_view)
        assert "viewer_id" in src
        assert "viewed_id" in src
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave2.py::TestProfileViewTracking -v`
Expected: FAIL — `_log_profile_view` not found

- [ ] **Step 4: Implement `_log_profile_view` and integrate into `get_user_profile`**

Add to `social.py` before `get_user_profile` (around line 3295):

```python
def _log_profile_view(conn, viewer_id: str, viewed_id: str):
    """Log a profile view, deduplicated per viewer per day. Skip self-views."""
    if viewer_id == viewed_id:
        return
    ph = db._ph
    db._execute(conn, f"""
        INSERT INTO profile_views (viewer_id, viewed_id, viewed_date)
        VALUES ({ph}::uuid, {ph}::uuid, CURRENT_DATE)
        ON CONFLICT (viewer_id, viewed_id, viewed_date) DO NOTHING
    """, (viewer_id, viewed_id))
```

Inside `get_user_profile`, after the existing profile fetch query succeeds but before building the response dict, add view logging and self-only view count:

```python
# After line that fetches profile data, before building response:
if user and str(user["id"]) != str(profile_row["id"]):
    try:
        def _log_view():
            with db._conn() as c:
                _log_profile_view(c, str(user["id"]), str(profile_row["id"]))
        asyncio.get_event_loop().call_soon(lambda: asyncio.ensure_future(asyncio.to_thread(_log_view)))
    except Exception:
        pass

# In response dict, add for self only:
view_count_7d = 0
if is_self:
    def _get_views():
        with db._conn() as c:
            row = db._fetchone(c, f"""
                SELECT COUNT(DISTINCT viewer_id) AS c FROM profile_views
                WHERE viewed_id = {ph}::uuid AND viewed_date >= CURRENT_DATE - INTERVAL '7 days'
            """, (str(profile_row["id"]),))
            return db._row_to_dict(row)["c"] if row else 0
    view_count_7d = await asyncio.to_thread(_get_views)

# Add to the response dict:
# "view_count_7d": view_count_7d if is_self else None,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest agent/tests/test_wave2.py::TestProfileViewTracking -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest -q`
Expected: Same baseline (no regressions)

- [ ] **Step 7: Commit**

```bash
git add agent/migrations/063_profile_views.sql agent/social.py agent/tests/test_wave2.py
git commit -m "feat(user): profile view tracking — migration + deduped logging + 7-day count"
```

---

### Task 2: Activity Timeline Backend

**Files:**
- Modify: `agent/social.py` (add `get_user_timeline` endpoint)
- Test: `agent/tests/test_wave2.py` (add `TestActivityTimeline`)

**Interfaces:**
- Consumes: `_block_sql()`, `_mute_sql()`, `validate_path_id()`, `Depends(get_current_user)`
- Produces: `GET /api/users/{user_id}/timeline?page=1&limit=20` → `{"items": [...], "total": int, "page": int, "has_more": bool}`

Each timeline item: `{"type": "post"|"review"|"follow", "created_at": str, "data": {...}}`
- post: `{"id": str, "content": str (truncated 200 chars), "post_type": str, "entity_name": str|null, "like_count": int}`
- review: `{"id": str, "content": str (truncated 200 chars), "entity_name": str, "rating": int|null}`
- follow: `{"target_name": str, "target_id": str}`

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave2.py

class TestActivityTimeline:
    def test_timeline_endpoint_exists(self):
        src = inspect.getsource(__import__("social").get_user_timeline)
        assert "timeline" in src.lower()

    def test_timeline_uses_union_query(self):
        src = inspect.getsource(__import__("social").get_user_timeline)
        assert "UNION ALL" in src

    def test_timeline_respects_privacy(self):
        src = inspect.getsource(__import__("social").get_user_timeline)
        assert "is_private" in src

    def test_timeline_has_pagination(self):
        src = inspect.getsource(__import__("social").get_user_timeline)
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_timeline_returns_typed_items(self):
        src = inspect.getsource(__import__("social").get_user_timeline)
        for item_type in ("post", "review", "follow"):
            assert f"'{item_type}'" in src or f'"{item_type}"' in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave2.py::TestActivityTimeline -v`
Expected: FAIL — `get_user_timeline` not found

- [ ] **Step 3: Implement the timeline endpoint**

Add after the `get_user_profile` endpoint in `social.py` (after line ~3446):

```python
@router.get("/users/{user_id}/timeline",
            summary="User activity timeline",
            description="Chronological timeline of a user's posts, reviews, and follows.")
async def get_user_timeline(
    user_id: str,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(get_current_user),
):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph
    offset = (page - 1) * limit

    def _query():
        with db._conn() as conn:
            target = db._fetchone(conn, f"""
                SELECT id, is_private FROM users
                WHERE id::text = {ph} AND is_active = TRUE AND deleted_at IS NULL
            """, (user_id,))
            if not target:
                return None, 0
            target = db._row_to_dict(target)
            is_self = user and str(user["id"]) == str(target["id"])
            if target.get("is_private") and not is_self:
                return [], 0

            timeline_sql = f"""
                (SELECT 'post' AS type, p.created_at, p.id AS ref_id,
                        LEFT(p.content, 200) AS content, p.post_type,
                        e.name AS entity_name, NULL AS target_name,
                        p.like_count, NULL::int AS rating
                 FROM posts p
                 LEFT JOIN entities e ON e.id = p.entity_id
                 WHERE p.user_id::text = {ph} AND p.moderation_status = 'approved'
                       AND p.deleted_at IS NULL AND p.post_type != 'review')
                UNION ALL
                (SELECT 'review' AS type, p.created_at, p.id AS ref_id,
                        LEFT(p.content, 200) AS content, p.post_type,
                        e.name AS entity_name, NULL AS target_name,
                        p.like_count, p.rating
                 FROM posts p
                 LEFT JOIN entities e ON e.id = p.entity_id
                 WHERE p.user_id::text = {ph} AND p.moderation_status = 'approved'
                       AND p.deleted_at IS NULL AND p.post_type = 'review')
                UNION ALL
                (SELECT 'follow' AS type, f.created_at, f.target_id AS ref_id,
                        NULL AS content, NULL AS post_type,
                        NULL AS entity_name,
                        COALESCE(u2.display_name, u2.username, 'Người dùng') AS target_name,
                        NULL AS like_count, NULL::int AS rating
                 FROM follows f
                 LEFT JOIN users u2 ON u2.id::text = f.target_id
                 WHERE f.follower_id::text = {ph} AND f.target_type = 'user')
                ORDER BY created_at DESC
                LIMIT {ph} OFFSET {ph}
            """
            params = (user_id, user_id, user_id, limit, offset)
            rows = db._fetchall(conn, timeline_sql, params)

            count_sql = f"""
                SELECT (
                    (SELECT COUNT(*) FROM posts WHERE user_id::text = {ph}
                     AND moderation_status = 'approved' AND deleted_at IS NULL)
                    + (SELECT COUNT(*) FROM follows WHERE follower_id::text = {ph}
                       AND target_type = 'user')
                ) AS c
            """
            total_row = db._fetchone(conn, count_sql, (user_id, user_id))
            total = db._row_to_dict(total_row)["c"] if total_row else 0
            return rows, total

    result = await asyncio.to_thread(_query)
    if result[0] is None:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

    rows, total = result
    items = []
    for r in rows:
        d = db._row_to_dict(r)
        item = {"type": d["type"], "created_at": str(d["created_at"])}
        if d["type"] in ("post", "review"):
            item["data"] = {
                "id": str(d["ref_id"]),
                "content": d.get("content") or "",
                "post_type": d.get("post_type"),
                "entity_name": d.get("entity_name"),
                "like_count": d.get("like_count") or 0,
            }
            if d["type"] == "review":
                item["data"]["rating"] = d.get("rating")
        elif d["type"] == "follow":
            item["data"] = {
                "target_id": str(d["ref_id"]),
                "target_name": d.get("target_name") or "Người dùng",
            }
        items.append(item)

    return {"items": items, "total": total, "page": page, "has_more": offset + limit < total}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest agent/tests/test_wave2.py::TestActivityTimeline -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest -q`
Expected: Same baseline

- [ ] **Step 6: Commit**

```bash
git add agent/social.py agent/tests/test_wave2.py
git commit -m "feat(user): activity timeline endpoint — union posts+reviews+follows, paginated"
```

---

### Task 3: Activity Timeline FE

**Files:**
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (add "Hoạt động" tab + timeline panel)

**Interfaces:**
- Consumes: `GET /api/users/{user_id}/timeline?page=1&limit=20` (Task 2)
- Produces: New profile tab "Hoạt động" with infinite scroll timeline

- [ ] **Step 1: Add the tab button**

In the `.profile-tabs` `div` (line ~139), after the "Đánh giá" tab button and before the "Đã lưu" tab button, add:

```html
<button type="button" id="profile-tab-timeline" role="tab"
  :class="['chip', { active: tab === 'timeline' }]"
  :aria-selected="tab === 'timeline'"
  aria-controls="profile-panel-timeline"
  :tabindex="tab === 'timeline' ? 0 : -1"
  @click="setProfileTab('timeline')">Hoạt động</button>
```

- [ ] **Step 2: Add the timeline panel template**

Inside the `<div class="feed-main">` (line ~150), before the `<template v-else>` block that renders posts, add:

```html
<template v-if="tab === 'timeline'">
  <div v-if="timelineLoading && !timelineItems.length" class="profile-loading" role="status" aria-label="Đang tải">
    <div class="spinner"></div>
  </div>
  <div v-else-if="timelineItems.length" class="timeline-feed">
    <article v-for="item in timelineItems" :key="item.type + '-' + (item.data?.id || item.data?.target_id) + '-' + item.created_at" class="timeline-item">
      <span class="tl-icon" aria-hidden="true">{{ timelineIcon(item.type) }}</span>
      <div class="tl-body">
        <p class="tl-text">
          <template v-if="item.type === 'post'">
            Đã đăng bài{{ item.data.entity_name ? ` về ${item.data.entity_name}` : '' }}
          </template>
          <template v-else-if="item.type === 'review'">
            Đã đánh giá <strong>{{ item.data.entity_name || 'địa điểm' }}</strong>
            <span v-if="item.data.rating" class="tl-rating">{{ '⭐'.repeat(Math.min(item.data.rating, 5)) }}</span>
          </template>
          <template v-else-if="item.type === 'follow'">
            Đã theo dõi <strong>{{ item.data.target_name }}</strong>
          </template>
        </p>
        <p v-if="item.data?.content" class="tl-preview">{{ item.data.content }}</p>
        <time class="tl-time" :datetime="item.created_at">{{ formatTimeAgo(item.created_at) }}</time>
      </div>
    </article>
  </div>
  <EmptyState v-else icon="📅" title="Chưa có hoạt động" message="Hoạt động sẽ hiện khi người dùng tương tác trên cộng đồng." />
  <div v-if="timelineLoading && timelineItems.length" class="profile-loading" role="status"><div class="spinner"></div></div>
  <div ref="timelineSentinel" style="height:1px" />
</template>
```

- [ ] **Step 3: Add script logic**

In the `<script setup>` section, add:

```typescript
// Timeline state
const timelineItems = ref<Array<{ type: string; created_at: string; data: Record<string, unknown> }>>([])
const timelineLoading = ref(false)
const timelinePage = ref(1)
const timelineHasMore = ref(true)
const timelineSentinel = ref<HTMLElement | null>(null)

function timelineIcon(type: string): string {
  switch (type) {
    case 'post': return '✍️'
    case 'review': return '⭐'
    case 'follow': return '👥'
    default: return '📌'
  }
}

async function loadTimeline() {
  if (timelineLoading.value || !timelineHasMore.value) return
  timelineLoading.value = true
  try {
    const uid = profile.value?.id || route.params.id
    const res = await $fetch<{ items: typeof timelineItems.value; has_more: boolean }>(`/api/users/${encodeURIComponent(String(uid))}/timeline`, {
      params: { page: timelinePage.value, limit: 20 },
      headers: authHeaders(),
    })
    timelineItems.value.push(...(res.items || []))
    timelineHasMore.value = res.has_more
    timelinePage.value++
  } catch {
    /* silently fail — timeline is supplementary */
  } finally {
    timelineLoading.value = false
  }
}

// Reset timeline on tab switch
watch(() => tab.value, (newTab) => {
  if (newTab === 'timeline' && !timelineItems.value.length) {
    loadTimeline()
  }
})

// Infinite scroll for timeline
useInfiniteScroll(() => {
  if (tab.value === 'timeline') loadTimeline()
}, { enabled: computed(() => tab.value === 'timeline' && timelineHasMore.value) })
```

Note: The `useInfiniteScroll` composable's sentinel ref is separate — check the existing usage in the file to match the pattern. If the composable expects a `sentinel` ref to be returned and bound to a DOM element, use its return value. Otherwise adapt to the pattern used elsewhere in the file.

- [ ] **Step 4: Add CSS**

Add to the scoped `<style>` section:

```css
.timeline-feed { display: flex; flex-direction: column; gap: var(--space-2); }
.timeline-item { display: flex; gap: var(--space-3); padding: var(--space-3); border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); }
.tl-icon { font-size: 1.25rem; flex-shrink: 0; width: 2rem; text-align: center; }
.tl-body { flex: 1; min-width: 0; }
.tl-text { margin: 0; color: var(--ink); font-size: 0.9375rem; }
.tl-preview { margin: var(--space-1) 0 0; color: var(--muted); font-size: 0.875rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tl-time { font-size: 0.8125rem; color: var(--muted); }
.tl-rating { margin-left: var(--space-1); }
```

- [ ] **Step 5: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build passes

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): activity timeline tab on profile — posts, reviews, follows with infinite scroll"
```

---

### Task 4: Badge Progress Endpoint + Showcase FE

**Files:**
- Modify: `agent/social.py` (add `get_badge_progress` endpoint)
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (add badge showcase section)
- Test: `agent/tests/test_wave2.py` (add `TestBadgeProgress`)

**Interfaces:**
- Consumes: `_reputation()` at `social.py:3238`, badge definitions at `social.py:3281-3291`
- Produces: `GET /api/me/badge-progress` → `{"badges": [{"id": str, "label": str, "icon": str, "earned": bool, "current": int, "target": int}]}`

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave2.py

class TestBadgeProgress:
    def test_badge_progress_endpoint_exists(self):
        src = inspect.getsource(__import__("social").get_badge_progress)
        assert "badge" in src.lower()

    def test_badge_progress_returns_all_badges(self):
        src = inspect.getsource(__import__("social").get_badge_progress)
        for badge_id in ("first_review", "review_master", "photographer", "explorer",
                         "popular", "quality", "allrounder", "traveler", "local", "veteran"):
            assert badge_id in src

    def test_badge_progress_has_current_and_target(self):
        src = inspect.getsource(__import__("social").get_badge_progress)
        assert "current" in src
        assert "target" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave2.py::TestBadgeProgress -v`
Expected: FAIL

- [ ] **Step 3: Implement the endpoint**

Add after `_reputation()` in `social.py` (around line 3294):

```python
@router.get("/me/badge-progress",
            summary="Badge progress for current user",
            description="Returns all badges with current progress and target thresholds.")
async def get_badge_progress(user=Depends(require_user)):
    uid = str(user["id"])
    ph = db._ph

    def _query():
        with db._conn() as conn:
            post_stats = db._fetchone(conn, f"""
                SELECT COUNT(*) AS posts,
                       COUNT(*) FILTER (WHERE post_type = 'review') AS reviews,
                       COUNT(*) FILTER (WHERE (CASE WHEN jsonb_typeof(images)='array'
                           THEN jsonb_array_length(images) ELSE 0 END) > 0) AS photos,
                       COUNT(DISTINCT entity_id) FILTER (WHERE entity_id IS NOT NULL) AS places,
                       COALESCE(SUM(like_count), 0) AS likes
                FROM posts WHERE user_id::text = {ph}
                AND moderation_status = 'approved' AND deleted_at IS NULL
            """, (uid,))
            ps = db._row_to_dict(post_stats) if post_stats else {}
            reviews = int(ps.get("reviews") or 0)
            photos = int(ps.get("photos") or 0)
            places = int(ps.get("places") or 0)
            likes = int(ps.get("likes") or 0)

            follower_row = db._fetchone(conn, f"""
                SELECT COUNT(*) c FROM follows
                WHERE target_type='user' AND target_id={ph}
            """, (uid,))
            followers = int(db._row_to_dict(follower_row).get("c", 0)) if follower_row else 0

            visit_row = db._fetchone(conn, f"""
                SELECT COUNT(*) AS visits,
                       COUNT(DISTINCT e.area) FILTER (WHERE e.area IS NOT NULL) AS areas,
                       (SELECT EXTRACT(DAY FROM NOW() - created_at)::int FROM users WHERE id::text = {ph}) AS age_days
                FROM user_visits uv LEFT JOIN entities e ON e.id = uv.entity_id
                WHERE uv.user_id::text = {ph} AND uv.status = 'visited'
            """, (uid, uid))
            vd = db._row_to_dict(visit_row) if visit_row else {}
            visits = int(vd.get("visits") or 0)
            areas = int(vd.get("areas") or 0)
            age_days = int(vd.get("age_days") or 0)

            return reviews, photos, places, likes, followers, visits, areas, age_days

    reviews, photos, places, likes, followers, visits, areas, age_days = await asyncio.to_thread(_query)

    badge_defs = [
        {"id": "first_review", "label": "Đánh giá đầu tiên", "icon": "✍️", "current": reviews, "target": 1},
        {"id": "review_master", "label": "Bậc thầy đánh giá", "icon": "⭐", "current": reviews, "target": 25},
        {"id": "photographer", "label": "Nhiếp ảnh cộng đồng", "icon": "📸", "current": photos, "target": 10},
        {"id": "explorer", "label": "Người khám phá", "icon": "🧭", "current": places, "target": 10},
        {"id": "popular", "label": "Được yêu thích", "icon": "💛", "current": followers, "target": 20},
        {"id": "quality", "label": "Nội dung chất lượng", "icon": "🏆", "current": likes, "target": 50},
        {"id": "allrounder", "label": "Đa năng", "icon": "🌟",
         "current": min(places // 3, reviews // 5, photos // 3),
         "target": 1,
         "hint": f"Cần: {max(0, 3 - places)} nơi, {max(0, 5 - reviews)} đánh giá, {max(0, 3 - photos)} ảnh"},
        {"id": "traveler", "label": "Lữ khách", "icon": "🎒", "current": visits, "target": 10},
        {"id": "local", "label": "Người địa phương", "icon": "🏡", "current": areas, "target": 3},
        {"id": "veteran", "label": "Thành viên kỳ cựu", "icon": "🎖️", "current": age_days, "target": 180},
    ]

    for b in badge_defs:
        b["earned"] = b["current"] >= b["target"]

    return {"badges": badge_defs}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest agent/tests/test_wave2.py::TestBadgeProgress -v`
Expected: PASS

- [ ] **Step 5: Add badge showcase to profile FE**

In `nguoi-dung/[id].vue`, replace the existing inline badge display (lines ~54-61 showing `v-for="b in profile.reputation.badges"`) with an expanded section. Below the `profile-reputation` div, add a new expandable badge showcase:

```html
<details v-if="badgeProgress.length" class="badge-showcase" open>
  <summary class="bs-title">Thành tích ({{ earnedBadgeCount }}/{{ badgeProgress.length }})</summary>
  <div class="bs-grid">
    <div v-for="b in badgeProgress" :key="b.id" :class="['bs-card', { earned: b.earned }]">
      <span class="bs-icon">{{ b.icon }}</span>
      <span class="bs-label">{{ b.label }}</span>
      <div v-if="!b.earned" class="bs-progress">
        <div class="bs-bar"><div class="bs-fill" :style="{ width: Math.min(100, (b.current / b.target) * 100) + '%' }"></div></div>
        <span class="bs-hint">{{ b.hint || `${b.current}/${b.target}` }}</span>
      </div>
      <span v-else class="bs-earned-label">Đã đạt</span>
    </div>
  </div>
</details>
```

Add script logic:

```typescript
const badgeProgress = ref<Array<{ id: string; label: string; icon: string; earned: boolean; current: number; target: number; hint?: string }>>([])
const earnedBadgeCount = computed(() => badgeProgress.value.filter(b => b.earned).length)

async function loadBadgeProgress() {
  if (!isSelf.value) return
  try {
    const res = await $fetch<{ badges: typeof badgeProgress.value }>('/api/me/badge-progress', { headers: authHeaders() })
    badgeProgress.value = res.badges || []
  } catch { /* ignore */ }
}
```

Call `loadBadgeProgress()` in the existing `onMounted` when `isSelf` is true.

Add CSS:

```css
.badge-showcase { margin: var(--space-3) 0; }
.bs-title { font-weight: 600; font-size: 0.9375rem; cursor: pointer; padding: var(--space-2) 0; }
.bs-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-2); }
.bs-card { padding: var(--space-2); border-radius: var(--radius); border: 1px solid var(--line); text-align: center; background: var(--surface); }
.bs-card:not(.earned) { opacity: 0.6; }
.bs-card.earned { border-color: var(--primary); }
.bs-icon { font-size: 1.5rem; display: block; margin-bottom: var(--space-1); }
.bs-label { font-size: 0.8125rem; font-weight: 500; color: var(--ink); }
.bs-progress { margin-top: var(--space-1); }
.bs-bar { height: 4px; background: var(--line); border-radius: 2px; overflow: hidden; }
.bs-fill { height: 100%; background: var(--primary); border-radius: 2px; transition: width 0.3s ease; }
.bs-hint { font-size: 0.75rem; color: var(--muted); }
.bs-earned-label { font-size: 0.75rem; color: var(--success); font-weight: 500; }
```

- [ ] **Step 6: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build passes

- [ ] **Step 7: Commit**

```bash
git add agent/social.py agent/tests/test_wave2.py web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): badge progress endpoint + showcase with progress bars on profile"
```

---

### Task 5: Profile View Counter FE

**Files:**
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (add view count stat card)

**Interfaces:**
- Consumes: `view_count_7d` from profile API response (Task 1)
- Produces: Stat card showing "X lượt xem tuần này" on self-profile

- [ ] **Step 1: Add view count to the analytics card**

In `nguoi-dung/[id].vue`, in the existing `.profile-analytics` card (lines ~113-133), add a new stat for profile views. After the existing stats (likes_received, reactions_received, entities_reviewed, collections), add:

```html
<div v-if="profile.view_count_7d != null" class="pa-stat">
  <strong>{{ profile.view_count_7d }}</strong>
  <span>lượt xem tuần này</span>
</div>
```

- [ ] **Step 2: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build passes

- [ ] **Step 3: Commit**

```bash
git add web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): profile view counter stat in analytics card"
```

---

### Task 6: User Discovery in Community

**Files:**
- Modify: `web-nuxt/pages/cong-dong.vue` (show user cards in search results)

**Interfaces:**
- Consumes: `GET /api/search/users?q=xxx` (already exists at `social.py:1227`)
- Produces: When community search is active, show a "Người dùng" section above post results with matching user cards

- [ ] **Step 1: Add user search state and fetch function**

In `cong-dong.vue` `<script setup>`, add:

```typescript
const searchUsers = ref<Array<{ id: string; display_name: string; avatar_url: string; username: string; post_count: number }>>([])

async function fetchSearchUsers(query: string) {
  if (!query || query.length < 2) { searchUsers.value = []; return }
  try {
    const res = await $fetch<{ users: typeof searchUsers.value }>('/api/search/users', {
      params: { q: query, page: 1 },
      headers: authHeaders(),
    })
    searchUsers.value = (res.users || []).slice(0, 5)
  } catch {
    searchUsers.value = []
  }
}
```

Wire `fetchSearchUsers` into the existing search handler — find where post search is triggered (likely a `watch` on the search query or a submit handler) and call `fetchSearchUsers(query)` alongside the post search.

- [ ] **Step 2: Add user cards template**

In the template, above the post results area (but below the search input), add:

```html
<div v-if="searchUsers.length && searchQuery" class="search-users-section">
  <h3 class="section-label">Người dùng</h3>
  <div class="search-users-grid">
    <NuxtLink v-for="u in searchUsers" :key="u.id" :to="userPath(u.username || u.id)" class="search-user-card card">
      <AvatarPlaceholder :initial="(u.display_name || '?').charAt(0)" :src="u.avatar_url" :size="40" />
      <div class="suc-info">
        <strong>{{ u.display_name }}</strong>
        <span class="suc-meta">{{ u.post_count }} bài viết</span>
      </div>
    </NuxtLink>
  </div>
</div>
```

Note: `userPath` is available from `routePaths.ts` (added in Wave 1).

- [ ] **Step 3: Add CSS**

```css
.search-users-section { margin-bottom: var(--space-4); }
.search-users-grid { display: flex; gap: var(--space-2); overflow-x: auto; padding-bottom: var(--space-1); }
.search-user-card { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); min-width: 180px; flex-shrink: 0; text-decoration: none; }
.suc-info { min-width: 0; }
.suc-info strong { display: block; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--ink); }
.suc-meta { font-size: 0.75rem; color: var(--muted); }
```

- [ ] **Step 4: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build passes

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/pages/cong-dong.vue
git commit -m "feat(user): user discovery cards in community search results"
```

---

### Task 7: Following Feed Enhancement

**Files:**
- Modify: `agent/social.py` (add friend reviews + friend saves endpoints)
- Modify: `web-nuxt/pages/cong-dong.vue` (add friend activity sections in following tab)
- Test: `agent/tests/test_wave2.py` (add `TestFollowingFeedEnhancement`)

**Interfaces:**
- Consumes: `get_following_feed()` at `social.py:1012`, `_block_sql()`, `_mute_sql()`
- Produces: `GET /api/feed/friend-reviews?limit=5` → `{"reviews": [...]}`, `GET /api/feed/friend-saves?limit=5` → `{"saves": [...]}`

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave2.py

class TestFollowingFeedEnhancement:
    def test_friend_reviews_endpoint_exists(self):
        src = inspect.getsource(__import__("social").get_friend_reviews)
        assert "review" in src.lower()

    def test_friend_reviews_filters_by_followed_users(self):
        src = inspect.getsource(__import__("social").get_friend_reviews)
        assert "follows" in src
        assert "target_type" in src

    def test_friend_saves_endpoint_exists(self):
        src = inspect.getsource(__import__("social").get_friend_saves)
        assert "bookmark" in src.lower() or "save" in src.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave2.py::TestFollowingFeedEnhancement -v`
Expected: FAIL

- [ ] **Step 3: Implement friend reviews endpoint**

Add after `get_following_feed` in `social.py` (around line 1067):

```python
@router.get("/feed/friend-reviews",
            summary="Recent reviews from followed users",
            description="Returns the 5 most recent reviews posted by users the caller follows.")
async def get_friend_reviews(
    limit: int = Query(5, ge=1, le=20),
    user=Depends(require_user),
):
    uid = str(user["id"])
    ph = db._ph
    bc, bc_p = _block_sql(user, "p.user_id")
    mc, mc_p = _mute_sql(user, "p.user_id")

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT p.id, LEFT(p.content, 150) AS content, p.rating, p.created_at,
                       u.display_name, u.avatar_url, u.username,
                       e.name AS entity_name, e.type AS entity_type
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN entities e ON e.id = p.entity_id
                WHERE p.post_type = 'review' AND p.moderation_status = 'approved'
                  AND p.deleted_at IS NULL
                  AND p.user_id IN (SELECT target_id::uuid FROM follows
                                    WHERE follower_id = {ph}::uuid AND target_type='user')
                  {bc} {mc}
                ORDER BY p.created_at DESC
                LIMIT {ph}
            """, (uid, *bc_p, *mc_p, limit))
            return rows
    rows = await asyncio.to_thread(_query)
    reviews = []
    for r in rows:
        d = db._row_to_dict(r)
        reviews.append({
            "id": str(d["id"]),
            "content": d.get("content") or "",
            "rating": d.get("rating"),
            "created_at": str(d["created_at"]),
            "user": {"display_name": d.get("display_name"), "avatar_url": d.get("avatar_url"), "username": d.get("username")},
            "entity_name": d.get("entity_name"),
            "entity_type": d.get("entity_type"),
        })
    return {"reviews": reviews}
```

- [ ] **Step 4: Implement friend saves endpoint**

```python
@router.get("/feed/friend-saves",
            summary="Recent saves by followed users",
            description="Returns entities recently bookmarked by users the caller follows.")
async def get_friend_saves(
    limit: int = Query(5, ge=1, le=20),
    user=Depends(require_user),
):
    uid = str(user["id"])
    ph = db._ph
    bc, bc_p = _block_sql(user)

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT DISTINCT ON (b.entity_id) b.entity_id, e.name, e.type AS entity_type,
                       u.display_name, u.avatar_url, b.created_at
                FROM bookmarks b
                JOIN users u ON u.id = b.user_id
                JOIN entities e ON e.id = b.entity_id
                WHERE b.user_id IN (SELECT target_id::uuid FROM follows
                                    WHERE follower_id = {ph}::uuid AND target_type='user')
                  AND b.user_id != {ph}::uuid
                  {bc}
                ORDER BY b.entity_id, b.created_at DESC
                LIMIT {ph}
            """, (uid, uid, *bc_p, limit))
            return rows
    rows = await asyncio.to_thread(_query)
    saves = []
    for r in rows:
        d = db._row_to_dict(r)
        saves.append({
            "entity_id": str(d["entity_id"]),
            "entity_name": d.get("name"),
            "entity_type": d.get("entity_type"),
            "user": {"display_name": d.get("display_name"), "avatar_url": d.get("avatar_url")},
            "created_at": str(d["created_at"]),
        })
    return {"saves": saves}
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest agent/tests/test_wave2.py::TestFollowingFeedEnhancement -v`
Expected: PASS

- [ ] **Step 6: Add friend activity sections to community FE**

In `cong-dong.vue`, when the active tab is `following`, show friend reviews and friend saves above the regular following feed. Add to the template:

```html
<template v-if="activeTab === 'following' && isLoggedIn">
  <div v-if="friendReviews.length" class="friend-activity-section">
    <h3 class="section-label">Bạn bè đã đánh giá</h3>
    <div class="friend-reviews-scroll">
      <div v-for="r in friendReviews" :key="r.id" class="friend-review-card card">
        <div class="fr-header">
          <AvatarPlaceholder :initial="(r.user.display_name || '?').charAt(0)" :src="r.user.avatar_url" :size="28" />
          <span class="fr-name">{{ r.user.display_name }}</span>
        </div>
        <p class="fr-entity">{{ r.entity_name }}<span v-if="r.rating" class="fr-rating"> {{ '⭐'.repeat(Math.min(r.rating, 5)) }}</span></p>
        <p v-if="r.content" class="fr-preview">{{ r.content }}</p>
      </div>
    </div>
  </div>
  <div v-if="friendSaves.length" class="friend-activity-section">
    <h3 class="section-label">Được lưu bởi bạn bè</h3>
    <div class="friend-saves-scroll">
      <NuxtLink v-for="s in friendSaves" :key="s.entity_id" :to="entityPath(s.entity_id)" class="friend-save-chip">
        {{ s.entity_name }}
        <span class="fs-by">bởi {{ s.user.display_name }}</span>
      </NuxtLink>
    </div>
  </div>
</template>
```

Add script:

```typescript
const friendReviews = ref<Array<{ id: string; content: string; rating: number | null; entity_name: string; user: { display_name: string; avatar_url: string } }>>([])
const friendSaves = ref<Array<{ entity_id: string; entity_name: string; user: { display_name: string; avatar_url: string } }>>([])

async function loadFriendActivity() {
  try {
    const [reviews, saves] = await Promise.all([
      $fetch<{ reviews: typeof friendReviews.value }>('/api/feed/friend-reviews', { params: { limit: 5 }, headers: authHeaders() }),
      $fetch<{ saves: typeof friendSaves.value }>('/api/feed/friend-saves', { params: { limit: 5 }, headers: authHeaders() }),
    ])
    friendReviews.value = reviews.reviews || []
    friendSaves.value = saves.saves || []
  } catch { /* ignore */ }
}
```

Call `loadFriendActivity()` when the following tab is activated — use a `watch` on `activeTab`:

```typescript
watch(activeTab, (newTab) => {
  if (newTab === 'following' && isLoggedIn.value && !friendReviews.value.length) {
    loadFriendActivity()
  }
})
```

Add CSS:

```css
.friend-activity-section { margin-bottom: var(--space-4); }
.friend-reviews-scroll, .friend-saves-scroll { display: flex; gap: var(--space-2); overflow-x: auto; padding-bottom: var(--space-1); }
.friend-review-card { min-width: 220px; max-width: 280px; flex-shrink: 0; padding: var(--space-2); }
.fr-header { display: flex; align-items: center; gap: var(--space-1); margin-bottom: var(--space-1); }
.fr-name { font-size: 0.8125rem; font-weight: 500; color: var(--ink); }
.fr-entity { font-size: 0.875rem; font-weight: 600; margin: 0; }
.fr-rating { font-size: 0.75rem; }
.fr-preview { font-size: 0.8125rem; color: var(--muted); margin: var(--space-1) 0 0; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.friend-save-chip { display: inline-flex; flex-direction: column; padding: var(--space-1) var(--space-2); border-radius: var(--radius); border: 1px solid var(--line); background: var(--surface); text-decoration: none; font-size: 0.875rem; font-weight: 500; color: var(--ink); white-space: nowrap; }
.fs-by { font-size: 0.75rem; color: var(--muted); font-weight: 400; }
```

- [ ] **Step 7: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build passes

- [ ] **Step 8: Commit**

```bash
git add agent/social.py agent/tests/test_wave2.py web-nuxt/pages/cong-dong.vue
git commit -m "feat(user): following feed enhancement — friend reviews + friend saves sections"
```

---

### Task 8: Weekly Activity Digest

**Files:**
- Modify: `agent/scheduler.py` (add `task_weekly_digest` function + register in TASKS)
- Modify: `agent/notifications.py` (import `create_notification` is already available internally)
- Test: `agent/tests/test_wave2.py` (add `TestWeeklyDigest`)

**Interfaces:**
- Consumes: `create_notification()` from `notifications.py`, `db._conn()`, `db._fetchall()`
- Produces: `task_weekly_digest()` function registered as a `ScheduledTask` (weekly, 7 * 24 * 3600 seconds, run_immediately=False)

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave2.py

class TestWeeklyDigest:
    def test_weekly_digest_function_exists(self):
        from scheduler import task_weekly_digest
        assert callable(task_weekly_digest)

    def test_weekly_digest_registered_in_tasks(self):
        from scheduler import TASKS
        names = [t.name for t in TASKS]
        assert "weekly-digest" in names

    def test_weekly_digest_uses_create_notification(self):
        src = inspect.getsource(__import__("scheduler").task_weekly_digest)
        assert "create_notification" in src

    def test_weekly_digest_queries_weekly_stats(self):
        src = inspect.getsource(__import__("scheduler").task_weekly_digest)
        assert "7 days" in src or "7 day" in src or "INTERVAL" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave2.py::TestWeeklyDigest -v`
Expected: FAIL

- [ ] **Step 3: Implement the digest task**

Add to `scheduler.py`, before the `TASKS` list (around line 795):

```python
def task_weekly_digest():
    """Weekly activity digest — in-app notification summarizing each user's week.
    Runs every 7 days. Generates one notification per active user with stats."""
    from notifications import create_notification
    try:
        with db._conn() as conn:
            active_users = db._fetchall(conn, """
                SELECT id, display_name FROM users
                WHERE is_active = TRUE AND deleted_at IS NULL
                  AND last_active_at > NOW() - INTERVAL '30 days'
            """, ())
            if not active_users:
                _sched_logger.info("weekly-digest: no active users")
                return

            ph = db._ph
            for user_row in active_users:
                u = db._row_to_dict(user_row)
                uid = str(u["id"])
                name = u.get("display_name") or "bạn"

                stats = db._fetchone(conn, f"""
                    SELECT
                        (SELECT COUNT(*) FROM follows
                         WHERE target_type='user' AND target_id={ph}
                           AND created_at > NOW() - INTERVAL '7 days') AS new_followers,
                        (SELECT COALESCE(SUM(like_count), 0) FROM posts
                         WHERE user_id::text = {ph}
                           AND moderation_status='approved' AND deleted_at IS NULL
                           AND created_at > NOW() - INTERVAL '7 days') AS week_likes,
                        (SELECT COUNT(*) FROM posts
                         WHERE user_id::text = {ph}
                           AND moderation_status='approved' AND deleted_at IS NULL
                           AND created_at > NOW() - INTERVAL '7 days') AS week_posts
                """, (uid, uid, uid))
                s = db._row_to_dict(stats) if stats else {}
                new_followers = int(s.get("new_followers") or 0)
                week_likes = int(s.get("week_likes") or 0)
                week_posts = int(s.get("week_posts") or 0)

                if new_followers == 0 and week_likes == 0 and week_posts == 0:
                    continue

                parts = []
                if new_followers > 0:
                    parts.append(f"+{new_followers} người theo dõi mới")
                if week_likes > 0:
                    parts.append(f"{week_likes} lượt thích")
                if week_posts > 0:
                    parts.append(f"{week_posts} bài viết")

                body = ", ".join(parts) + ". Tiếp tục chia sẻ nhé!"
                create_notification(
                    user_id=uid,
                    notif_type="digest",
                    title=f"Tuần này của {name}",
                    body=body,
                    ref_type="digest",
                    ref_id=None,
                )

            _sched_logger.info("weekly-digest: sent digests to %d users", len(active_users))
    except Exception as exc:
        _sched_logger.error("weekly-digest error: %s", exc)
```

- [ ] **Step 4: Register the task**

In the `TASKS` list (line ~799), add before the closing `]`:

```python
ScheduledTask("weekly-digest", task_weekly_digest, interval_seconds=7 * 24 * 3600, run_immediately=False),  # Weekly
```

- [ ] **Step 5: Ensure "digest" notification type is handled**

Check `notifications.py` — the `_NOTIF_TYPE_PREF_MAP` dict (around line 358) maps notification types to preference columns. Add `"digest"` mapped to `pref_system` if not present:

```python
"digest": "pref_system",
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest agent/tests/test_wave2.py::TestWeeklyDigest -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest -q`
Expected: Same baseline

- [ ] **Step 8: Commit**

```bash
git add agent/scheduler.py agent/notifications.py agent/tests/test_wave2.py
git commit -m "feat(user): weekly activity digest — scheduler task + in-app notification"
```

---

### Task 9: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run pytest**

Run: `python -m pytest -q`
Expected: Same baseline as before Wave 2 (34 pre-existing failures, ~5106 passed)

- [ ] **Step 2: Run Nuxt build**

Run: `cd web-nuxt && npm run build`
Expected: Build passes successfully

- [ ] **Step 3: Start dev server and smoke test**

Run: `$env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python agent/server.py`

Verify endpoints respond:
- `GET /api/users/{id}/timeline?page=1&limit=5` — returns items array
- `GET /api/me/badge-progress` — returns badges array with current/target
- `GET /api/feed/friend-reviews?limit=3` — returns reviews array
- `GET /api/feed/friend-saves?limit=3` — returns saves array

- [ ] **Step 4: Verify migration file exists**

Run: `ls agent/migrations/063_profile_views.sql`
Expected: File exists

- [ ] **Step 5: Mark complete**
