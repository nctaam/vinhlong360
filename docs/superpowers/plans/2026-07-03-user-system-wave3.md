# Wave 3: Achievement System + Engagement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent achievement system, login-streak tracking, an XP/level progression bar, a contribution heatmap, and richer leaderboard filters to deepen user engagement.

**Architecture:** New `agent/achievements.py` module (definitions + `check_achievements` engine + `GET /api/me/achievements`) backed by two additive migrations (064 login-streak columns on `users`, 065 `achievements`+`user_achievements` tables). Achievement checks are hooked fire-and-forget after key actions (post/review/follow/best-answer/visit/login) and awarded self-healingly on read. Login streak is event-driven in `auth.py`. Frontend adds an achievement showcase (replacing the Wave 2 badge showcase's data source), an XP bar + streak chip, a 52-week contribution heatmap, and leaderboard time/category/search/self-highlight — all on the existing profile (`nguoi-dung/[id].vue`) and leaderboard (`bang-xep-hang.vue`) pages.

**Tech Stack:** FastAPI (backend), Nuxt 4 SSR / Vue 3 Composition API (frontend), PostgreSQL, CSS design tokens. No new Python or JS dependencies.

## Global Constraints

- **DB pattern:** `with db._conn() as conn:` context manager, wrap in `await asyncio.to_thread(_query)`. Use `db._ph` for parameterized queries (`%s` for PG). `db._fetchone()`, `db._fetchall()`, `db._execute()`, `db._row_to_dict()`.
- **Router:** New routers use `APIRouter(prefix="/api", tags=[...], dependencies=[Depends(_require_pg)])`. Import auth deps: `from auth_middleware import get_current_user, require_user, validate_path_id, require_csrf`. `_require_pg` = `from auth_middleware import require_pg as _require_pg`. Use `Depends(require_user)` for auth-required, `Depends(get_current_user)` for optional auth.
- **Migration convention:** Additive only — `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `INSERT ... ON CONFLICT DO NOTHING/UPDATE`. The runner (`scripts/apply_migrations.py`) **hard-blocks `DROP TABLE|TRUNCATE|DELETE FROM`**. Filename regex `^\d{3}_[a-z0-9_]+\.sql$`. New tables get `ALTER TABLE <t> OWNER TO vl360;` right after `CREATE TABLE`. Every migration ends with the exact `schema_version` upsert footer (see Task 1). **Do NOT bump `PG_REQUIRED_SCHEMA_VERSION` (database.py:90, currently 62) — project convention leaves it; migration 063 did not bump it. Do not touch `agent/tests/test_database.py:84`.**
- **Next migration numbers:** 064 (login streak), 065 (achievements). 063 is the latest existing.
- **create_notification signature:** `create_notification(user_id, notif_type, title, body=None, ref_type=None, ref_id=None, actor_id=None)` — sync, wrap calls in `asyncio.to_thread`. It internally checks blocks/mutes/prefs and dedups by `(user_id, type, ref_id)` within 5 min. Add `"achievement": "pref_system"` to `_NOTIF_TYPE_TO_PREF` (notifications.py:358-373); no new pref column/migration needed.
- **Fire-and-forget hook pattern:** mirror `_log_profile_view_threaded` (social.py:3489-3498): a background thread function that opens its own `with db._conn() as conn:` and swallows exceptions in a `try/except` logging a warning — a broken achievement check must never break the primary user action. Launch via `asyncio.create_task(asyncio.to_thread(_bg_fn, ...))`.
- **CSS tokens (exist in `web-nuxt/assets/css/variables.css`):** `--ink`, `--muted`, `--primary`, `--success`, `--warning`, `--error` (NOT `--danger` — undefined), `--line`, `--surface`, `--card`, `--bg`, `--accent`. Spacing `--space-0..--space-24`. Radius `--radius-xs/sm/md/lg/xl/full` (`--radius`=lg). Text `--text-2xs..--text-5xl` (fluid clamp). Weights `--weight-normal/medium/semibold/bold/extrabold`. RGB channels `--primary-rgb`, `--success-rgb`, `--accent-rgb` for `rgba()`. Motion `--ease-out`, `--ease-spring-gentle`, `--ease-bounce`, `--duration-*`.
- **Auth FE:** `const { authHeaders, handleSessionExpired } = useAuth()`; `await $fetch<T>('/api/...', { headers: authHeaders() })`. 401 → `if (getStatusCode(e) === 401) { handleSessionExpired(); return }`. `authHeaders()` already carries CSRF — no separate `csrf` ref.
- **Toast FE:** `const { show: showToast } = useToast()`; `showToast(message, type)` where type ∈ `'success'|'error'|'warning'|'info'`. No `'achievement'` type — use `'success'`.
- **Composables FE:** auto-imported. `useInfiniteScroll(cb, { enabled })` → `{ sentinel, loading }`. `useTimeAgo()` → `{ timeAgo }`. `useFilterUrl(refs, defaults)` syncs refs to `route.query`. `useDebounce(fn, ms)` → `{ debounced, cancel }`.
- **AvatarPlaceholder:** props `{ src?, initial?, alt? }` — **no `size` prop**. But the profile/leaderboard pages use inline `<span class="avatar avatar-xl">{{ initial }}</span>` spans directly — follow that inline convention there, not `<AvatarPlaceholder>`.
- **Achievements supersede badges (RESOLVED DECISION):** The Wave 2 `.badge-showcase` "Thành tích" section (`nguoi-dung/[id].vue:62-75`, driven by `/api/me/badge-progress`) switches its data source to the new `/api/me/achievements` (a superset). The `/api/me/badge-progress` endpoint stays untouched (additive-first §B2) — do NOT delete it.
- **Achievement metric consistency:** follower count for achievements uses the **no-7-day-filter** count (matching `get_badge_progress`, social.py:3432-3436), not `_reputation`'s 7-day-filtered count — so the showcase agrees with itself.
- **§B7 / §B1:** Do NOT run any destructive data command. Migrations are additive DDL and are NOT applied to prod in these tasks (deploy is a §4 stop condition — out of scope). Tests run against the source, not a live PG (no local Postgres in this environment — tests use `inspect.getsource()` keyword assertions, matching `agent/tests/test_wave2.py`).
- **Test pattern:** add to `agent/tests/test_wave3.py`. Use `inspect.getsource()` to assert SQL keywords, function signatures, and hook wiring in source code (the established no-local-PG pattern). Frontend tasks verify via `cd web-nuxt && npm run build`.

---

### Task 1: Login Streak Backend (Migration 064 + auth.py)

**Files:**
- Create: `agent/migrations/064_login_streak.sql`
- Modify: `agent/auth.py` (add `_update_login_streak` helper; call it in `verify_otp` at line ~612 and `login_password` at line ~715)
- Test: `agent/tests/test_wave3.py` (new file, `TestLoginStreak` class)

**Interfaces:**
- Consumes: `db._conn()`, `db._execute()`, `db._fetchone()`, `db._ph`. Login success sites in `auth.py`.
- Produces: `users.login_streak INT`, `users.last_login_date DATE` columns; `_update_login_streak(user_id: str) -> int` returning the new streak value.

- [ ] **Step 1: Write the migration**

```sql
-- agent/migrations/064_login_streak.sql
-- Migration 064: theo dõi chuỗi đăng nhập liên tiếp — Wave 3 "Achievement
-- System + Engagement", W3.3. login_streak tăng khi đăng nhập vào ngày kế
-- tiếp last_login_date; reset về 1 nếu cách >1 ngày; giữ nguyên nếu cùng ngày.
-- Nuôi 2 achievement streak_7/streak_30 (xem achievements.py). Additive.

ALTER TABLE users ADD COLUMN IF NOT EXISTS login_streak INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_date DATE;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 64, '064_login_streak.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
```

- [ ] **Step 2: Write the test**

```python
# agent/tests/test_wave3.py
import inspect
import pytest

import auth


class TestLoginStreak:
    def test_update_login_streak_exists(self):
        assert callable(auth._update_login_streak)

    def test_update_login_streak_handles_consecutive_day(self):
        src = inspect.getsource(auth._update_login_streak)
        # increments when last_login_date = yesterday
        assert "login_streak" in src
        assert "INTERVAL '1 day'" in src or "last_login_date" in src

    def test_update_login_streak_resets_on_gap(self):
        src = inspect.getsource(auth._update_login_streak)
        # resets to 1 when gap > 1 day (CASE expression present)
        assert "CASE" in src
        assert "last_login_date = CURRENT_DATE" in src or "CURRENT_DATE" in src

    def test_update_login_streak_swallows_errors(self):
        src = inspect.getsource(auth._update_login_streak)
        assert "except" in src

    def test_verify_otp_calls_streak_update(self):
        src = inspect.getsource(auth.verify_otp)
        assert "_update_login_streak" in src

    def test_login_password_calls_streak_update(self):
        src = inspect.getsource(auth.login_password)
        assert "_update_login_streak" in src
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave3.py::TestLoginStreak -v`
Expected: FAIL — `auth._update_login_streak` does not exist.

- [ ] **Step 4: Implement `_update_login_streak`**

Add to `agent/auth.py` near the other module-level helpers (e.g. after `_log_login`, ~line 1233). Uses a single atomic UPDATE with a CASE, computing the new streak relative to `last_login_date`:

```python
def _update_login_streak(user_id: str) -> int:
    """Cập nhật chuỗi đăng nhập liên tiếp. Trả về streak mới (0 nếu lỗi).
    - Cùng ngày (last_login_date = today): giữ nguyên (không tính 2 lần/ngày).
    - Hôm qua (today - 1): +1.
    - Cách >1 ngày hoặc lần đầu: reset về 1.
    Nuốt lỗi (không chặn đăng nhập), giống _log_login."""
    ph = db._ph
    try:
        with db._conn() as conn:
            row = db._fetchone(conn, f"""
                UPDATE users SET
                    login_streak = CASE
                        WHEN last_login_date = CURRENT_DATE THEN login_streak
                        WHEN last_login_date = CURRENT_DATE - INTERVAL '1 day' THEN login_streak + 1
                        ELSE 1
                    END,
                    last_login_date = CURRENT_DATE
                WHERE id::text = {ph}
                RETURNING login_streak
            """, (user_id,))
            return int(db._row_to_dict(row)["login_streak"]) if row else 0
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to update login streak for %s: %s", user_id, e)
        return 0
```

Note: `last_login_date - INTERVAL '1 day'` compares a DATE to a timestamp; Postgres casts fine, but to be exact the CASE compares `last_login_date = CURRENT_DATE - INTERVAL '1 day'` which yields a `timestamp` on the RHS — Postgres implicitly compares DATE to timestamp by casting the DATE. This is correct for the "yesterday" check.

- [ ] **Step 5: Wire into both login success paths**

In `verify_otp` (auth.py ~line 612), right after the existing `_log_login` call, add:

```python
        await asyncio.to_thread(_log_login, phone, "otp", True, request, str(user["id"]))
        await asyncio.to_thread(_update_login_streak, str(user["id"]))
```

In `login_password` (auth.py ~line 715), right after its `_log_login` call, add:

```python
        await asyncio.to_thread(_log_login, phone, "password", True, request, str(user["id"]))
        await asyncio.to_thread(_update_login_streak, str(user["id"]))
```

(Note: the achievement-unlock notification for streak_7/streak_30 is wired in Task 3, not here — Task 1 only maintains the counter.)

- [ ] **Step 6: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave3.py::TestLoginStreak -v` → PASS
Run: `python -m pytest -q` → baseline (34 pre-existing failures unchanged, no new failures)

- [ ] **Step 7: Commit**

```bash
git add agent/migrations/064_login_streak.sql agent/tests/test_wave3.py
git add -p agent/auth.py   # stage only the 3 hunks: helper + 2 call sites
git commit -m "feat(user): login streak tracking — migration 064 + auth hooks"
```

---

### Task 2: Achievement System Backend (Migration 065 + achievements.py)

**Files:**
- Create: `agent/migrations/065_achievements.sql`
- Create: `agent/achievements.py` (module: definitions, engine, router)
- Modify: `agent/server.py` (register the achievements router — find where other routers like `visits` are `include_router`'d and add `achievements`)
- Modify: `agent/notifications.py` (add `"achievement": "pref_system"` to `_NOTIF_TYPE_TO_PREF` at ~line 358-373)
- Test: `agent/tests/test_wave3.py` (`TestAchievementSystem` class)

**Interfaces:**
- Consumes: `db._conn/_fetchone/_fetchall/_execute/_ph/_row_to_dict`, `create_notification`, the metric SQL patterns from `get_badge_progress` (social.py:3406-3472), `users.login_streak` (Task 1).
- Produces:
  - `ACHIEVEMENTS: list[dict]` — 15 defs, each `{id, name, description, icon, category, target, metric}`.
  - `_compute_metrics(conn, user_id: str) -> dict[str, int]` — all metric values.
  - `check_achievements(conn, user_id: str, notify: bool = True) -> list[dict]` — awards newly-earned rows, returns newly-unlocked defs; creates notifications when `notify=True`.
  - `GET /api/me/achievements` → `{"achievements": [{id,name,description,icon,category,current,target,earned,unlocked_at}], "earned_count": int, "total": int}`.

- [ ] **Step 1: Write the migration**

```sql
-- agent/migrations/065_achievements.sql
-- Migration 065: hệ thống thành tích — Wave 3 W3.1. `achievements` = định nghĩa
-- (seed 15 dòng), `user_achievements` = trạng thái mở khóa/tiến độ mỗi user.
-- Additive; seed qua ON CONFLICT DO NOTHING nên chạy lại an toàn.

CREATE TABLE IF NOT EXISTS achievements (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    description       TEXT,
    icon              TEXT,
    category          TEXT,          -- content | explorer | social | veteran | special
    requirement_value INT NOT NULL DEFAULT 1,
    sort_order        INT NOT NULL DEFAULT 0
);
ALTER TABLE achievements OWNER TO vl360;

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id TEXT NOT NULL REFERENCES achievements(id),
    unlocked_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, achievement_id)
);
ALTER TABLE user_achievements OWNER TO vl360;

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

INSERT INTO achievements (id, name, description, icon, category, requirement_value, sort_order) VALUES
    ('first_post',    'Bài viết đầu tiên',  'Đăng bài viết đầu tiên',              '📝', 'content',  1,  1),
    ('writer_10',     'Nhà văn',            'Đăng 10 bài viết',                    '✒️', 'content',  10, 2),
    ('reviewer_5',    'Nhà phê bình',       'Viết 5 đánh giá',                     '📋', 'content',  5,  3),
    ('review_master', 'Bậc thầy đánh giá',  'Viết 25 đánh giá',                    '⭐', 'content',  25, 4),
    ('photographer',  'Nhiếp ảnh gia',      'Đăng 10 bài có ảnh',                  '📸', 'content',  10, 5),
    ('explorer_5',    'Nhà thám hiểm',      'Ghé thăm 5 địa điểm',                 '🧭', 'explorer', 5,  6),
    ('explorer_20',   'Lữ khách',           'Ghé thăm 20 địa điểm',                '🎒', 'explorer', 20, 7),
    ('local_3',       'Người địa phương',   'Khám phá 3 khu vực',                  '🏡', 'explorer', 3,  8),
    ('social_10',     'Kết nối',            'Có 10 người theo dõi',                '🤝', 'social',   10, 9),
    ('social_50',     'Ảnh hưởng',          'Có 50 người theo dõi',                '💫', 'social',   50, 10),
    ('helpful_5',     'Hữu ích',            'Có 5 câu trả lời hay nhất',           '💡', 'social',   5,  11),
    ('streak_7',      'Chăm chỉ',           'Đăng nhập 7 ngày liên tiếp',          '🔥', 'veteran',  7,  12),
    ('streak_30',     'Kiên trì',           'Đăng nhập 30 ngày liên tiếp',         '🏅', 'veteran',  30, 13),
    ('veteran_6m',    'Lão làng',           'Thành viên 6 tháng',                  '🎖️', 'veteran',  180,14),
    ('allrounder',    'Đa tài',             'Mở khóa mỗi nhóm ít nhất 1 thành tích','🌟', 'special',  4,  15)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name, description = EXCLUDED.description, icon = EXCLUDED.icon,
    category = EXCLUDED.category, requirement_value = EXCLUDED.requirement_value,
    sort_order = EXCLUDED.sort_order;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 65, '065_achievements.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
```

- [ ] **Step 2: Write the test**

```python
# Add to agent/tests/test_wave3.py

class TestAchievementSystem:
    def test_achievements_module_imports(self):
        import achievements
        assert hasattr(achievements, "ACHIEVEMENTS")
        assert hasattr(achievements, "check_achievements")
        assert hasattr(achievements, "router")

    def test_fifteen_achievements_defined(self):
        import achievements
        assert len(achievements.ACHIEVEMENTS) == 15
        ids = {a["id"] for a in achievements.ACHIEVEMENTS}
        for expected in ("first_post", "review_master", "explorer_5", "social_50",
                         "helpful_5", "streak_7", "veteran_6m", "allrounder"):
            assert expected in ids

    def test_each_achievement_has_required_fields(self):
        import achievements
        for a in achievements.ACHIEVEMENTS:
            for f in ("id", "name", "icon", "category", "target", "metric"):
                assert f in a, f"{a.get('id')} missing {f}"

    def test_compute_metrics_covers_all_metric_keys(self):
        import achievements
        src = inspect.getsource(achievements._compute_metrics)
        for key in ("posts", "reviews", "photos", "visits", "areas",
                    "followers", "best_answers", "account_age_days", "login_streak"):
            assert key in src

    def test_best_answers_counts_comment_author(self):
        import achievements
        src = inspect.getsource(achievements._compute_metrics)
        assert "best_answer_id" in src
        assert "comments" in src

    def test_check_achievements_awards_and_dedupes(self):
        import achievements
        src = inspect.getsource(achievements.check_achievements)
        assert "user_achievements" in src
        assert "ON CONFLICT" in src

    def test_check_achievements_notify_flag(self):
        import achievements
        sig = inspect.signature(achievements.check_achievements)
        assert "notify" in sig.parameters

    def test_check_achievements_creates_notification(self):
        import achievements
        src = inspect.getsource(achievements.check_achievements)
        assert "create_notification" in src
        assert "achievement" in src

    def test_endpoint_requires_auth_and_awards_on_read(self):
        import achievements
        src = inspect.getsource(achievements.get_my_achievements)
        assert "require_user" in src
        assert "check_achievements" in src
        assert "notify=False" in src

    def test_allrounder_checks_categories(self):
        import achievements
        src = inspect.getsource(achievements.check_achievements)
        assert "category" in src or "categories" in src

    def test_notif_type_registered(self):
        import notifications
        assert notifications._NOTIF_TYPE_TO_PREF.get("achievement") == "pref_system"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave3.py::TestAchievementSystem -v`
Expected: FAIL — `import achievements` fails (module doesn't exist).

- [ ] **Step 4: Create `agent/achievements.py`**

```python
"""Hệ thống thành tích (achievements) — Wave 3 W3.1.

Thành tích = bản bền vững, có mốc thời gian mở khóa + thông báo, mở rộng từ
badge compute-on-fly (get_badge_progress). Chỉ số dùng lại đúng SQL của
get_badge_progress (social.py) + thêm best_answers, login_streak.

check_achievements(): tính chỉ số, so ngưỡng, INSERT ON CONFLICT DO NOTHING vào
user_achievements, trả về thành tích MỚI mở khóa; gửi thông báo nếu notify=True.
Endpoint GET /api/me/achievements award-on-read (notify=False) để tự chữa lành
kể cả khi chưa có hook; hook (Task 3) gọi notify=True cho thông báo thời gian thực.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends

from database import db
from auth_middleware import require_user, require_pg as _require_pg

logger = logging.getLogger("achievements")

router = APIRouter(prefix="/api", tags=["achievements"], dependencies=[Depends(_require_pg)])

# metric = khóa trong dict trả về bởi _compute_metrics; target = ngưỡng đạt.
ACHIEVEMENTS: list[dict] = [
    {"id": "first_post",    "name": "Bài viết đầu tiên", "description": "Đăng bài viết đầu tiên",   "icon": "📝", "category": "content",  "target": 1,   "metric": "posts"},
    {"id": "writer_10",     "name": "Nhà văn",           "description": "Đăng 10 bài viết",          "icon": "✒️", "category": "content",  "target": 10,  "metric": "posts"},
    {"id": "reviewer_5",    "name": "Nhà phê bình",      "description": "Viết 5 đánh giá",           "icon": "📋", "category": "content",  "target": 5,   "metric": "reviews"},
    {"id": "review_master", "name": "Bậc thầy đánh giá", "description": "Viết 25 đánh giá",          "icon": "⭐", "category": "content",  "target": 25,  "metric": "reviews"},
    {"id": "photographer",  "name": "Nhiếp ảnh gia",     "description": "Đăng 10 bài có ảnh",        "icon": "📸", "category": "content",  "target": 10,  "metric": "photos"},
    {"id": "explorer_5",    "name": "Nhà thám hiểm",     "description": "Ghé thăm 5 địa điểm",       "icon": "🧭", "category": "explorer", "target": 5,   "metric": "visits"},
    {"id": "explorer_20",   "name": "Lữ khách",          "description": "Ghé thăm 20 địa điểm",      "icon": "🎒", "category": "explorer", "target": 20,  "metric": "visits"},
    {"id": "local_3",       "name": "Người địa phương",  "description": "Khám phá 3 khu vực",        "icon": "🏡", "category": "explorer", "target": 3,   "metric": "areas"},
    {"id": "social_10",     "name": "Kết nối",           "description": "Có 10 người theo dõi",      "icon": "🤝", "category": "social",   "target": 10,  "metric": "followers"},
    {"id": "social_50",     "name": "Ảnh hưởng",         "description": "Có 50 người theo dõi",      "icon": "💫", "category": "social",   "target": 50,  "metric": "followers"},
    {"id": "helpful_5",     "name": "Hữu ích",           "description": "Có 5 câu trả lời hay nhất", "icon": "💡", "category": "social",   "target": 5,   "metric": "best_answers"},
    {"id": "streak_7",      "name": "Chăm chỉ",          "description": "Đăng nhập 7 ngày liên tiếp","icon": "🔥", "category": "veteran",  "target": 7,   "metric": "login_streak"},
    {"id": "streak_30",     "name": "Kiên trì",          "description": "Đăng nhập 30 ngày liên tiếp","icon": "🏅","category": "veteran",  "target": 30,  "metric": "login_streak"},
    {"id": "veteran_6m",    "name": "Lão làng",          "description": "Thành viên 6 tháng",        "icon": "🎖️","category": "veteran",  "target": 180, "metric": "account_age_days"},
    {"id": "allrounder",    "name": "Đa tài",            "description": "Mở khóa mỗi nhóm ít nhất 1 thành tích", "icon": "🌟", "category": "special", "target": 4, "metric": "categories_covered"},
]

_ACH_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}
_CATEGORIES = ("content", "explorer", "social", "veteran")  # nhóm để tính allrounder


def _compute_metrics(conn, user_id: str) -> dict[str, int]:
    """Tính mọi chỉ số cho 1 user. Dùng lại đúng SQL của get_badge_progress
    (social.py:3406-3472) + best_answers + login_streak."""
    ph = db._ph
    post_stats = db._fetchone(conn, f"""
        SELECT COUNT(*) AS posts,
               COUNT(*) FILTER (WHERE post_type = 'review') AS reviews,
               COUNT(*) FILTER (WHERE (CASE WHEN jsonb_typeof(images)='array'
                   THEN jsonb_array_length(images) ELSE 0 END) > 0) AS photos
        FROM posts WHERE user_id::text = {ph}
        AND moderation_status = 'approved' AND deleted_at IS NULL
    """, (user_id,))
    ps = db._row_to_dict(post_stats) if post_stats else {}

    follower_row = db._fetchone(conn, f"""
        SELECT COUNT(*) c FROM follows
        WHERE target_type='user' AND target_id={ph}
    """, (user_id,))
    followers = int(db._row_to_dict(follower_row).get("c", 0)) if follower_row else 0

    visit_row = db._fetchone(conn, f"""
        SELECT COUNT(*) AS visits,
               COUNT(DISTINCT e.area) FILTER (WHERE e.area IS NOT NULL) AS areas,
               (SELECT EXTRACT(DAY FROM NOW() - created_at)::int FROM users WHERE id::text = {ph}) AS age_days
        FROM user_visits uv LEFT JOIN entities e ON e.id = uv.entity_id
        WHERE uv.user_id::text = {ph} AND uv.status = 'visited'
    """, (user_id, user_id))
    vd = db._row_to_dict(visit_row) if visit_row else {}

    best_row = db._fetchone(conn, f"""
        SELECT COUNT(*) c FROM posts p
        JOIN comments c2 ON c2.id = p.best_answer_id
        WHERE c2.user_id::text = {ph} AND p.deleted_at IS NULL
    """, (user_id,))
    best_answers = int(db._row_to_dict(best_row).get("c", 0)) if best_row else 0

    streak_row = db._fetchone(conn, f"""
        SELECT COALESCE(login_streak, 0) AS s FROM users WHERE id::text = {ph}
    """, (user_id,))
    login_streak = int(db._row_to_dict(streak_row).get("s", 0)) if streak_row else 0

    def _i(d, k):
        return int(d.get(k) or 0)

    return {
        "posts": _i(ps, "posts"),
        "reviews": _i(ps, "reviews"),
        "photos": _i(ps, "photos"),
        "followers": followers,
        "visits": _i(vd, "visits"),
        "areas": _i(vd, "areas"),
        "account_age_days": _i(vd, "age_days"),
        "best_answers": best_answers,
        "login_streak": login_streak,
    }


def check_achievements(conn, user_id: str, notify: bool = True) -> list[dict]:
    """Award thành tích mới đạt ngưỡng. Trả về danh sách def mới mở khóa.
    Idempotent qua ON CONFLICT DO NOTHING. allrounder tính sau (dựa trên nhóm
    đã có, kể cả mới mở khóa lượt này)."""
    ph = db._ph
    metrics = _compute_metrics(conn, user_id)

    earned_rows = db._fetchall(conn, f"""
        SELECT achievement_id FROM user_achievements WHERE user_id::text = {ph}
    """, (user_id,))
    earned_ids = {db._row_to_dict(r)["achievement_id"] for r in earned_rows}

    newly: list[dict] = []

    def _award(ach_id: str):
        db._execute(conn, f"""
            INSERT INTO user_achievements (user_id, achievement_id)
            VALUES ({ph}::uuid, {ph}) ON CONFLICT DO NOTHING
        """, (user_id, ach_id))
        earned_ids.add(ach_id)
        newly.append(_ACH_BY_ID[ach_id])

    # 1) Thành tích chỉ-số thường (bỏ allrounder tới cuối)
    for a in ACHIEVEMENTS:
        if a["id"] == "allrounder" or a["id"] in earned_ids:
            continue
        if metrics.get(a["metric"], 0) >= a["target"]:
            _award(a["id"])

    # 2) allrounder: đủ ≥1 thành tích ở mỗi nhóm content/explorer/social/veteran
    if "allrounder" not in earned_ids:
        cats = {_ACH_BY_ID[i]["category"] for i in earned_ids if i in _ACH_BY_ID}
        if all(c in cats for c in _CATEGORIES):
            _award("allrounder")

    # 3) Thông báo (thời gian thực khi hook gọi notify=True)
    if notify and newly:
        from notifications import create_notification
        for a in newly:
            try:
                create_notification(
                    user_id=user_id,
                    notif_type="achievement",
                    title=f"{a['icon']} Mở khóa thành tích: {a['name']}",
                    body=a.get("description") or "",
                    ref_type="achievement",
                    ref_id=a["id"],
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("achievement notify failed (%s/%s): %s", user_id, a["id"], e)

    return newly


@router.get("/me/achievements",
            summary="Achievements for current user",
            description="Tất cả thành tích với trạng thái mở khóa + tiến độ hiện tại. Award-on-read (không thông báo).")
async def get_my_achievements(user=Depends(require_user)):
    uid = str(user["id"])

    def _query():
        with db._conn() as conn:
            # award-on-read, im lặng (tránh spam thông báo lần đầu)
            check_achievements(conn, uid, notify=False)
            metrics = _compute_metrics(conn, uid)
            ph = db._ph
            rows = db._fetchall(conn, f"""
                SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id::text = {ph}
            """, (uid,))
            unlocked = {db._row_to_dict(r)["achievement_id"]: db._row_to_dict(r)["unlocked_at"] for r in rows}
            return metrics, unlocked

    metrics, unlocked = await asyncio.to_thread(_query)

    out = []
    for a in ACHIEVEMENTS:
        earned = a["id"] in unlocked
        if a["metric"] == "categories_covered":
            earned_cats = {_ACH_BY_ID[i]["category"] for i in unlocked if i in _ACH_BY_ID}
            current = sum(1 for c in _CATEGORIES if c in earned_cats)
        else:
            current = metrics.get(a["metric"], 0)
        out.append({
            "id": a["id"], "name": a["name"], "description": a["description"],
            "icon": a["icon"], "category": a["category"],
            "current": min(current, a["target"]), "target": a["target"],
            "earned": earned,
            "unlocked_at": str(unlocked[a["id"]]) if earned else None,
        })

    return {"achievements": out, "earned_count": len(unlocked), "total": len(ACHIEVEMENTS)}
```

- [ ] **Step 5: Register the router in `server.py`**

Find where `visits` router is included (search `include_router` in `agent/server.py`) and add alongside it:

```python
from achievements import router as achievements_router
app.include_router(achievements_router)
```

(Match the exact existing import + include style in server.py — some routers are imported at top, some inline. Follow the file's convention.)

- [ ] **Step 6: Register the notification type**

In `agent/notifications.py`, add to `_NOTIF_TYPE_TO_PREF` (~line 371, before the closing brace):

```python
    "digest": "pref_system",
    "achievement": "pref_system",
}
```

- [ ] **Step 7: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave3.py::TestAchievementSystem -v` → PASS
Run: `python -m pytest -q` → baseline unchanged

- [ ] **Step 8: Commit**

```bash
git add agent/migrations/065_achievements.sql agent/achievements.py agent/tests/test_wave3.py
git add -p agent/server.py agent/notifications.py
git commit -m "feat(user): achievement system — migration 065 + achievements.py engine + endpoint"
```

---

### Task 3: Achievement Action Hooks

**Files:**
- Modify: `agent/social.py` (hook `check_achievements` after `create_post` ~417-428, `publish_draft` ~576-587, `toggle_follow` ~493-500, `set_best_answer` ~2552-2576)
- Modify: `agent/visits.py` (hook after `set_visit` ~66-79)
- Modify: `agent/auth.py` (hook after `_update_login_streak` in both login paths)
- Test: `agent/tests/test_wave3.py` (`TestAchievementHooks` class)

**Interfaces:**
- Consumes: `achievements.check_achievements(conn, user_id, notify=True)`.
- Produces: a shared background helper `_check_achievements_bg(user_id)` (fire-and-forget, own connection, swallows exceptions) added to `social.py`; hook call-sites in 5 endpoints across 3 files.

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave3.py

class TestAchievementHooks:
    def test_bg_helper_swallows_errors(self):
        import social
        src = inspect.getsource(social._check_achievements_bg)
        assert "check_achievements" in src
        assert "except" in src

    def test_create_post_hooks_achievements(self):
        import social
        src = inspect.getsource(social.create_post)
        assert "_check_achievements_bg" in src

    def test_toggle_follow_hooks_target_user(self):
        import social
        src = inspect.getsource(social.toggle_follow)
        # achievement check must run for the FOLLOWED user (target_id), not the follower
        assert "_check_achievements_bg" in src
        assert "target_id" in src

    def test_set_best_answer_hooks_comment_author(self):
        import social
        src = inspect.getsource(social.set_best_answer)
        assert "_check_achievements_bg" in src

    def test_set_visit_hooks_achievements(self):
        import visits
        src = inspect.getsource(visits.set_visit)
        assert "check_achievements" in src

    def test_login_paths_hook_achievements(self):
        import auth
        assert "check_achievements" in inspect.getsource(auth.verify_otp)
        assert "check_achievements" in inspect.getsource(auth.login_password)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave3.py::TestAchievementHooks -v`
Expected: FAIL — `social._check_achievements_bg` does not exist.

- [ ] **Step 3: Add the shared background helper to `social.py`**

Near `_log_profile_view_threaded` (social.py:3489-3498), add:

```python
def _check_achievements_bg(user_id: str):
    """Fire-and-forget achievement check với thông báo. Nuốt lỗi để không
    chặn hành động chính (giống _log_profile_view_threaded)."""
    try:
        from achievements import check_achievements
        with db._conn() as conn:
            check_achievements(conn, user_id, notify=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("achievement check failed for %s: %s", user_id, e)
```

- [ ] **Step 4: Hook `create_post`**

In `create_post` (social.py ~417-428), inside the existing notify block that runs only when the post is approved, add a fire-and-forget check for the author. After the existing `await asyncio.to_thread(_notify_post)` (or equivalent notify call), add:

```python
            if status == "approved":
                asyncio.create_task(asyncio.to_thread(_check_achievements_bg, str(user["id"])))
```

(Guard on `status == "approved"` since all achievement counts require approved posts. Place it where `status` is in scope — the implementer must confirm the variable name from the surrounding code.)

- [ ] **Step 5: Hook `publish_draft`**

In `publish_draft` (social.py ~576-587), after the draft becomes an approved live post, add:

```python
    asyncio.create_task(asyncio.to_thread(_check_achievements_bg, str(user["id"])))
```

- [ ] **Step 6: Hook `toggle_follow` (for the FOLLOWED user)**

In `toggle_follow` (social.py ~493-500), inside the existing `if following and target_type == "user":` block (where the follow notification is already sent), add — checking the **target** user whose follower count changed:

```python
        if following and target_type == "user":
            # ... existing notify code ...
            asyncio.create_task(asyncio.to_thread(_check_achievements_bg, str(target_id)))
```

- [ ] **Step 7: Hook `set_best_answer` (for the COMMENT author)**

In `set_best_answer` (social.py ~2552-2576), after a best answer is set, the recipient is the **comment author**, not `user` (who is the post owner). The endpoint already looks up the comment; capture its `user_id` and check achievements for that author:

```python
    # sau khi UPDATE posts SET best_answer_id, và chỉ khi body.comment_id truthy:
    if body.comment_id:
        author = db._fetchone(conn, f"SELECT user_id FROM comments WHERE id::text = {ph}", (body.comment_id,))
        if author:
            author_id = str(db._row_to_dict(author)["user_id"])
            asyncio.create_task(asyncio.to_thread(_check_achievements_bg, author_id))
```

(The implementer must place this where `conn`/`ph` are in scope, or restructure to fetch the author id inside the existing `_query`/closure and launch the task after it returns. Do NOT check achievements for `user["id"]` — that's the post owner selecting the answer, not the helpful contributor.)

- [ ] **Step 8: Hook `set_visit` in `visits.py`**

In `set_visit` (visits.py ~66-79), only when `body.status == "visited"`, add after the upsert:

```python
    if body.status == "visited":
        from achievements import check_achievements
        def _bg():
            try:
                with db._conn() as conn:
                    check_achievements(conn, str(user["id"]), notify=True)
            except Exception:
                pass
        asyncio.create_task(asyncio.to_thread(_bg))
```

(visits.py has no `_check_achievements_bg`; use an inline background closure, or import the one from social — prefer the inline closure to avoid a cross-module social import in visits.py. Confirm `asyncio` is imported in visits.py; add `import asyncio` if missing.)

- [ ] **Step 9: Hook both login paths in `auth.py`**

In `verify_otp` and `login_password`, after the `_update_login_streak` call added in Task 1, add a fire-and-forget achievement check (feeds streak_7/streak_30 with real-time unlock notification):

```python
        await asyncio.to_thread(_update_login_streak, str(user["id"]))
        def _ach_bg(uid=str(user["id"])):
            try:
                from achievements import check_achievements
                with db._conn() as conn:
                    check_achievements(conn, uid, notify=True)
            except Exception:
                pass
        asyncio.create_task(asyncio.to_thread(_ach_bg))
```

- [ ] **Step 10: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave3.py::TestAchievementHooks -v` → PASS
Run: `python -m pytest -q` → baseline unchanged

- [ ] **Step 11: Commit**

```bash
git add agent/tests/test_wave3.py
git add -p agent/social.py agent/visits.py agent/auth.py
git commit -m "feat(user): achievement hooks — post/follow/best-answer/visit/login trigger checks"
```

---

### Task 4: Achievement Showcase FE

**Files:**
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (switch `.badge-showcase` section at ~62-75 to `/api/me/achievements`; add categories + unlock animation + toast)
- Test: build verification only

**Interfaces:**
- Consumes: `GET /api/me/achievements` → `{achievements:[{id,name,description,icon,category,current,target,earned,unlocked_at}], earned_count, total}`.
- Produces: an achievement showcase replacing the badge-progress data source on self-profile.

- [ ] **Step 1: Replace the showcase data source (script)**

The page currently loads `badgeProgress` from `/api/me/badge-progress` and renders `.badge-showcase`. Find `badgeProgress` (a `ref`) and its loader (search `badge-progress` in the file). Add a parallel achievements state and loader following the exact pattern of the existing badge loader and the auth/toast conventions (Global Constraints):

```ts
type Achievement = {
  id: string; name: string; description: string; icon: string; category: string
  current: number; target: number; earned: boolean; unlocked_at: string | null
}
const achievements = ref<Achievement[]>([])
const achievementsEarned = ref(0)

async function loadAchievements() {
  if (!isSelf.value) return
  try {
    const res = await $fetch<{ achievements: Achievement[]; earned_count: number }>(
      '/api/me/achievements', { headers: authHeaders() })
    achievements.value = res.achievements || []
    achievementsEarned.value = res.earned_count || 0
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    /* im lặng — showcase là bổ sung */
  }
}
```

Call `loadAchievements()` wherever `badgeProgress` is currently loaded (same `onMounted`/`watch(isSelf)` site). Keep the existing `badgeProgress` load OR remove its call if the section is fully replaced — but do NOT delete the `/api/me/badge-progress` endpoint (backend). Simplest: replace the badge loader call with `loadAchievements()` and repoint the template.

- [ ] **Step 2: Rewrite the `.badge-showcase` template block (~62-75)**

Group by category, render earned (colored + date via `useTimeAgo`) and locked (greyed + progress bar + "Còn X"). Reuse the existing `.bs-*` class names where possible; add category headers:

```html
<details v-if="isSelf && achievements.length" class="badge-showcase" open>
  <summary>Thành tích ({{ achievementsEarned }}/{{ achievements.length }})</summary>
  <div v-for="cat in achievementCategories" :key="cat.key" class="bs-cat">
    <h4 class="bs-cat-title">{{ cat.label }}</h4>
    <div class="bs-grid">
      <div v-for="a in cat.items" :key="a.id"
           class="bs-card" :class="{ 'bs-earned': a.earned, 'bs-locked': !a.earned }">
        <span class="bs-icon" aria-hidden="true">{{ a.icon }}</span>
        <div class="bs-info">
          <strong>{{ a.name }}</strong>
          <span v-if="a.earned" class="bs-date">{{ timeAgo(a.unlocked_at!) }}</span>
          <template v-else>
            <div class="bs-bar"><div class="bs-fill" :style="{ width: Math.round(a.current / a.target * 100) + '%' }" /></div>
            <span class="bs-hint">Còn {{ Math.max(0, a.target - a.current) }} nữa</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</details>
```

Add the `achievementCategories` computed (groups `achievements.value` by category, in fixed order content/explorer/social/veteran/special with Vietnamese labels):

```ts
const achievementCategories = computed(() => {
  const order: Array<[string, string]> = [
    ['content', 'Nội dung'], ['explorer', 'Khám phá'],
    ['social', 'Cộng đồng'], ['veteran', 'Kỳ cựu'], ['special', 'Đặc biệt'],
  ]
  return order
    .map(([key, label]) => ({ key, label, items: achievements.value.filter(a => a.category === key) }))
    .filter(c => c.items.length)
})
```

Ensure `timeAgo` is available (`const { timeAgo } = useTimeAgo()` — likely already imported for the timeline tab; reuse it).

- [ ] **Step 3: Add CSS (scoped block at bottom, ~875 near existing `.badge-showcase` styles)**

Reuse existing `.bs-grid`/`.bs-card` if present; add category + locked styling with tokens:

```css
.bs-cat { margin-top: var(--space-3); }
.bs-cat-title { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 var(--space-2); }
.bs-card.bs-locked { opacity: 0.55; }
.bs-card.bs-earned .bs-icon { filter: none; }
.bs-card.bs-locked .bs-icon { filter: grayscale(1); }
.bs-bar { height: 4px; background: var(--line); border-radius: var(--radius-full); overflow: hidden; margin-top: var(--space-1); }
.bs-fill { height: 100%; background: var(--primary); border-radius: var(--radius-full); transition: width var(--duration-slow, 0.5s) var(--ease-out); }
.bs-date { font-size: var(--text-2xs); color: var(--success); }
.bs-hint { font-size: var(--text-2xs); color: var(--muted); }
```

- [ ] **Step 4: Build verification**

Run: `cd C:/Code/vinhlong360/web-nuxt && npm run build`
Expected: build passes.

- [ ] **Step 5: Commit**

```bash
git add -p web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): achievement showcase — categorized grid on profile from /api/me/achievements"
```

---

### Task 5: Level/XP Bar + Login Streak Display FE

**Files:**
- Modify: `agent/social.py` (VERIFY `get_user_profile` exposes `reputation.points`; if not, add it — one line in the response dict) + expose `login_streak` on `/me/stats` or profile
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (XP bar under the reputation pill ~54-61; streak chip)
- Test: `agent/tests/test_wave3.py` (`TestProfilePointsExposed`) if backend touched

**Interfaces:**
- Consumes: `reputation.points` + `level` + `level_label` (already computed by `_reputation`, social.py:3402-3403); `_level_for` thresholds 20/80/200 (social.py:3340-3345). `users.login_streak` (Task 1).
- Produces: XP progress bar (client-computed) + streak chip on profile.

- [ ] **Step 1: Verify/expose `points` and `login_streak` (backend)**

Read `get_user_profile` (social.py ~3296+) and confirm the JSON response includes `reputation.points`. `_reputation` returns `points` in its dict (social.py:3402-3403), so if the whole reputation dict is passed through, `points` is already exposed — verify by reading the response construction. If `points` is stripped, add it. Also expose the streak for self: add `login_streak` to the profile response (self-only) by selecting it in the user query, OR add it to `/me/stats`. Prefer profile response, self-only:

```python
# trong get_user_profile, khi is_self, thêm vào dict trả về:
"login_streak": int(profile_row.get("login_streak") or 0) if is_self else None,
```

(The implementer must confirm the exact response-dict construction and the `is_self` variable name from the surrounding code, and ensure the user SELECT includes `login_streak`.)

If backend is touched, add a test:

```python
class TestProfilePointsExposed:
    def test_profile_exposes_points(self):
        src = inspect.getsource(social.get_user_profile)
        assert "points" in src
    def test_profile_exposes_login_streak(self):
        src = inspect.getsource(social.get_user_profile)
        assert "login_streak" in src
```

- [ ] **Step 2: Add XP bar + streak chip (FE, under `.profile-reputation` ~54-61)**

Compute XP progress client-side from `points` and the 4-tier thresholds (0/20/80/200):

```ts
const LEVEL_THRESHOLDS = [0, 20, 80, 200]
const xpProgress = computed(() => {
  const pts = profile.value?.reputation?.points ?? 0
  const lvl = profile.value?.reputation?.level ?? 1
  if (lvl >= 4) return { pct: 100, toNext: 0, max: true }
  const lo = LEVEL_THRESHOLDS[lvl - 1] ?? 0
  const hi = LEVEL_THRESHOLDS[lvl] ?? 20
  const pct = Math.min(100, Math.round((pts - lo) / (hi - lo) * 100))
  return { pct, toNext: Math.max(0, hi - pts), max: false }
})
```

Template — insert right after the `.profile-reputation` pill:

```html
<div v-if="profile?.reputation" class="xp-bar-wrap">
  <div class="xp-bar"><div class="xp-fill" :style="{ width: xpProgress.pct + '%' }" /></div>
  <span class="xp-label">
    {{ xpProgress.max ? 'Cấp tối đa' : `Còn ${xpProgress.toNext} điểm lên cấp` }}
  </span>
</div>
<div v-if="isSelf && (profile?.login_streak ?? 0) > 0" class="streak-chip">
  🔥 {{ profile.login_streak }} ngày liên tiếp
</div>
```

- [ ] **Step 3: CSS (reuse the `.pc-bar`/`.pc-fill` pattern at ~1044-1052)**

```css
.xp-bar-wrap { display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-1); }
.xp-bar { flex: 1; height: 6px; background: var(--line); border-radius: var(--radius-full); overflow: hidden; }
.xp-fill { height: 100%; background: linear-gradient(90deg, var(--primary), var(--accent)); border-radius: var(--radius-full); transition: width var(--duration-slow, 0.5s) var(--ease-out); }
.xp-label { font-size: var(--text-2xs); color: var(--muted); white-space: nowrap; }
.streak-chip { display: inline-flex; align-items: center; gap: var(--space-1); margin-top: var(--space-1); padding: var(--space-1) var(--space-2); background: color-mix(in srgb, var(--warning) 12%, transparent); border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--weight-medium); color: var(--ink); }
```

- [ ] **Step 4: Build + test verification**

Run: `python -m pytest agent/tests/test_wave3.py::TestProfilePointsExposed -v` (if backend touched) → PASS
Run: `cd C:/Code/vinhlong360/web-nuxt && npm run build` → passes

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_wave3.py
git add -p agent/social.py web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): XP progression bar + login streak chip on profile"
```

---

### Task 6: Contribution Heatmap (Backend + Frontend)

**Files:**
- Modify: `agent/social.py` (add `GET /api/users/{user_id}/activity-heatmap`)
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (52-week CSS grid section)
- Test: `agent/tests/test_wave3.py` (`TestActivityHeatmap`)

**Interfaces:**
- Consumes: `posts` (created_at, user_id, moderation_status, deleted_at), `validate_path_id`, `Depends(get_current_user)`.
- Produces: `GET /api/users/{user_id}/activity-heatmap` → `{"days": [{"date": "YYYY-MM-DD", "count": int}], "total": int, "max": int}` (only days with activity; FE fills the grid).

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave3.py

class TestActivityHeatmap:
    def test_heatmap_endpoint_exists(self):
        src = inspect.getsource(social.get_activity_heatmap)
        assert "heatmap" in src.lower() or "activity" in src.lower()

    def test_heatmap_groups_by_date(self):
        src = inspect.getsource(social.get_activity_heatmap)
        assert "DATE(created_at)" in src or "DATE(p.created_at)" in src
        assert "GROUP BY" in src

    def test_heatmap_365_day_window(self):
        src = inspect.getsource(social.get_activity_heatmap)
        assert "365 days" in src

    def test_heatmap_only_approved(self):
        src = inspect.getsource(social.get_activity_heatmap)
        assert "moderation_status = 'approved'" in src
        assert "deleted_at IS NULL" in src

    def test_heatmap_validates_path_id(self):
        src = inspect.getsource(social.get_activity_heatmap)
        assert "validate_path_id" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave3.py::TestActivityHeatmap -v`
Expected: FAIL — `get_activity_heatmap` not found.

- [ ] **Step 3: Implement the endpoint**

Add after `get_user_timeline` in social.py:

```python
@router.get("/users/{user_id}/activity-heatmap",
            summary="365-day activity heatmap",
            description="Số bài viết/đánh giá đã duyệt theo ngày trong 365 ngày qua (GitHub-style).")
async def get_activity_heatmap(user_id: str, user=Depends(get_current_user)):
    user_id = validate_path_id(user_id, "user_id")
    ph = db._ph

    def _query():
        with db._conn() as conn:
            rows = db._fetchall(conn, f"""
                SELECT DATE(created_at) AS d, COUNT(*) AS c
                FROM posts
                WHERE user_id::text = {ph}
                  AND moderation_status = 'approved' AND deleted_at IS NULL
                  AND created_at > NOW() - INTERVAL '365 days'
                GROUP BY DATE(created_at)
                ORDER BY d
            """, (user_id,))
            return [db._row_to_dict(r) for r in rows]

    rows = await asyncio.to_thread(_query)
    days = [{"date": str(r["d"]), "count": int(r["c"])} for r in rows]
    total = sum(d["count"] for d in days)
    mx = max((d["count"] for d in days), default=0)
    return {"days": days, "total": total, "max": mx}
```

- [ ] **Step 4: Add heatmap FE section**

Add a section on the profile (e.g. above `.profile-tabs` ~157, self+public visible). Load on mount; build a 53-week × 7-day grid client-side, shading by count. Script:

```ts
type HeatDay = { date: string; count: number }
const heatmap = ref<HeatDay[]>([])
const heatmapMax = ref(0)
const heatmapTotal = ref(0)

async function loadHeatmap() {
  try {
    const res = await $fetch<{ days: HeatDay[]; total: number; max: number }>(
      `/api/users/${encodedProfileId.value}/activity-heatmap`, { headers: authHeaders() })
    heatmap.value = res.days || []
    heatmapMax.value = res.max || 0
    heatmapTotal.value = res.total || 0
  } catch { /* im lặng */ }
}

// build 53 tuần cột × 7 ngày, level 0..4 theo count/max
const heatmapWeeks = computed(() => {
  const byDate = new Map(heatmap.value.map(d => [d.date, d.count]))
  const cells: Array<{ date: string; count: number; level: number }> = []
  const today = new Date()
  const start = new Date(today); start.setDate(today.getDate() - 364)
  // căn về Chủ nhật đầu tuần
  start.setDate(start.getDate() - start.getDay())
  const mx = heatmapMax.value || 1
  for (let i = 0; i < 53 * 7; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i)
    const iso = d.toISOString().slice(0, 10)
    const count = byDate.get(iso) || 0
    const level = count === 0 ? 0 : Math.min(4, Math.ceil(count / mx * 4))
    cells.push({ date: iso, count, level })
    if (d > today) break
  }
  // nhóm thành cột-tuần
  const weeks: typeof cells[] = []
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))
  return weeks
})
```

Note: `new Date()` / `toISOString` run only in `loadHeatmap`/computed on the client (Nuxt SSR renders the section empty until mount — acceptable for a supplementary widget). Confirm `encodedProfileId` exists (used by sibling fetches per exploration) — reuse it.

Template:

```html
<section v-if="heatmap.length" class="heatmap-section">
  <h3 class="section-label">Hoạt động 1 năm qua · {{ heatmapTotal }} đóng góp</h3>
  <div class="heatmap-grid">
    <div v-for="(week, wi) in heatmapWeeks" :key="wi" class="hm-week">
      <span v-for="(cell, di) in week" :key="di"
            class="hm-cell" :data-level="cell.level"
            :title="`${cell.date}: ${cell.count} đóng góp`" />
    </div>
  </div>
</section>
```

CSS:

```css
.heatmap-section { margin: var(--space-3) 0; }
.heatmap-grid { display: flex; gap: 3px; overflow-x: auto; padding-bottom: var(--space-1); }
.hm-week { display: flex; flex-direction: column; gap: 3px; }
.hm-cell { width: 11px; height: 11px; border-radius: 2px; background: var(--line); }
.hm-cell[data-level="1"] { background: color-mix(in srgb, var(--success) 30%, var(--line)); }
.hm-cell[data-level="2"] { background: color-mix(in srgb, var(--success) 55%, transparent); }
.hm-cell[data-level="3"] { background: color-mix(in srgb, var(--success) 78%, transparent); }
.hm-cell[data-level="4"] { background: var(--success); }
```

Call `loadHeatmap()` in `onMounted`.

- [ ] **Step 5: Run tests + build**

Run: `python -m pytest agent/tests/test_wave3.py::TestActivityHeatmap -v` → PASS
Run: `cd C:/Code/vinhlong360/web-nuxt && npm run build` → passes

- [ ] **Step 6: Commit**

```bash
git add agent/tests/test_wave3.py
git add -p agent/social.py web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): contribution heatmap — 365-day endpoint + GitHub-style grid on profile"
```

---

### Task 7: Leaderboard Improvements Backend

**Files:**
- Modify: `agent/social.py` (`community_leaderboard` ~1717-1787: add `period`, `category`, `q` params; add self-rank; fix cache key)
- Test: `agent/tests/test_wave3.py` (`TestLeaderboardFilters`)

**Interfaces:**
- Consumes: existing leaderboard SQL + `_calc_points`/`_level_for`; `_block_sql`/`_mute_sql`; `_leaderboard_cache`.
- Produces: `GET /api/community/leaderboard?limit=&period=&category=&q=` → `{"leaders": [{...,"rank":int}], "self": {...}|null}`. `period ∈ 7d|30d|all` (default all), `category ∈ posts|reviews|photos|total` (default total).

- [ ] **Step 1: Write the test**

```python
# Add to agent/tests/test_wave3.py

class TestLeaderboardFilters:
    def test_leaderboard_has_period_param(self):
        sig = inspect.signature(social.community_leaderboard)
        assert "period" in sig.parameters

    def test_leaderboard_has_category_param(self):
        sig = inspect.signature(social.community_leaderboard)
        assert "category" in sig.parameters

    def test_leaderboard_has_search_param(self):
        sig = inspect.signature(social.community_leaderboard)
        assert "q" in sig.parameters

    def test_leaderboard_period_filters_by_date(self):
        src = inspect.getsource(social.community_leaderboard)
        assert "created_at >" in src or "INTERVAL" in src

    def test_leaderboard_cache_key_includes_filters(self):
        # cache must not collide across period/category — key derived from params
        src = inspect.getsource(social.community_leaderboard)
        assert "period" in src and "category" in src
        # cache dict access keyed by a composite, not a single flat entry
        assert "cache_key" in src or "_leaderboard_cache" in src

    def test_leaderboard_returns_self_and_rank(self):
        src = inspect.getsource(social.community_leaderboard)
        assert "rank" in src
        assert "self" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest agent/tests/test_wave3.py::TestLeaderboardFilters -v`
Expected: FAIL — params don't exist.

- [ ] **Step 3: Implement filters + self-rank + cache-key fix**

Modify `community_leaderboard` (social.py:1717-1787). Key changes (the implementer adapts to the exact existing code):

1. **Signature** — add params:
```python
async def community_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    period: str = Query("all", pattern="^(7d|30d|all)$"),
    category: str = Query("total", pattern="^(posts|reviews|photos|total)$"),
    q: str = Query("", max_length=100),
    user=Depends(get_current_user),
):
```

2. **Cache key** — replace the flat `_leaderboard_cache` single-entry logic with a per-(period,category) key, and bypass cache when `q` or a personal block/mute filter is present:
```python
    cache_key = f"{period}:{category}"
    has_personal_filter = bool(bc or mc) or bool(q)
    # ... only read/write _leaderboard_cache[cache_key] when not has_personal_filter
```
Change `_leaderboard_cache` from `{"ts", "data"}` to a dict of `cache_key -> {"ts","data"}` (or a small dict keyed by cache_key). Preserve TTL logic per key.

3. **Period filter** — add to the `LEFT JOIN posts p ON ...` condition (so the join only counts posts in-window; the `HAVING COUNT(p.id) > 0` already drops zero-activity users):
```python
    period_days = {"7d": 7, "30d": 30}.get(period)
    period_clause = f"AND p.created_at > NOW() - CAST({ph} AS INTERVAL)" if period_days else ""
    # append period_clause to the "LEFT JOIN posts p ON p.user_id = u.id AND ..." join condition
    # param: f"{period_days} days" (only when period_days, spliced in the right position)
```

4. **Category sort** — after computing per-user metrics, sort by the chosen category instead of always `points`:
```python
    sort_key = {"posts": "posts", "reviews": "reviews", "photos": "photos", "total": "points"}[category]
    leaders.sort(key=lambda x: x.get(sort_key, x["points"]), reverse=True)
```
Ensure `photos` is included in each leader dict (currently only `posts`/`reviews`/`points` are returned — add `photos` to the appended dict, computed value already available in the row loop).

5. **User search** — filter `leaders` by `q` (diacritic-insensitive substring on display_name) before ranking, when `q` present. Reuse any existing normalize helper if present; else simple `.lower()` contains.

6. **Rank + self** — after sorting, assign `rank` (1-based) via `enumerate`, truncate to `limit`, and locate the current user's full entry (searching the full sorted list, not just the truncated top-N) for `self`:
```python
    for i, ld in enumerate(leaders):
        ld["rank"] = i + 1
    self_entry = None
    if user:
        uid = str(user["id"])
        self_entry = next((ld for ld in leaders if str(ld["id"]) == uid), None)
    result = {"leaders": leaders[:limit], "self": self_entry}
```

- [ ] **Step 4: Run tests + full suite**

Run: `python -m pytest agent/tests/test_wave3.py::TestLeaderboardFilters -v` → PASS
Run: `python -m pytest -q` → baseline unchanged (confirm existing leaderboard tests, if any, still pass)

- [ ] **Step 5: Commit**

```bash
git add agent/tests/test_wave3.py
git add -p agent/social.py
git commit -m "feat(user): leaderboard filters — period/category/search + self-rank + per-filter cache"
```

---

### Task 8: Leaderboard Improvements FE

**Files:**
- Modify: `web-nuxt/pages/bang-xep-hang.vue` (add time/category filter chips, search input, self-highlight)
- Test: build verification

**Interfaces:**
- Consumes: `GET /api/community/leaderboard?limit=50&period=&category=&q=` → `{leaders:[{...,rank}], self}`; `useAuth().user` for self-id; `FilterChips`, `useDebounce`.
- Produces: filtered, searchable leaderboard with the current user's row highlighted.

- [ ] **Step 1: Add filter state + refetch (script)**

The page currently does `useAsyncData('leaderboard', () => apiFetch('/api/community/leaderboard?limit=50'))`. Convert to reactive params:

```ts
const period = ref<'7d' | '30d' | 'all'>('all')
const category = ref<'total' | 'posts' | 'reviews' | 'photos'>('total')
const q = ref('')
const { user: currentUser } = useAuth()

const { data, refresh } = await useAsyncData('leaderboard',
  () => apiFetch(`/api/community/leaderboard?limit=50&period=${period.value}&category=${category.value}&q=${encodeURIComponent(q.value)}`),
  { watch: [period, category] })

const { debounced: debouncedRefresh } = useDebounce(() => refresh(), 350)
watch(q, () => debouncedRefresh())

const leaders = computed(() => data.value?.leaders || [])
const selfEntry = computed(() => data.value?.self || null)
```

- [ ] **Step 2: Add filter UI + search (template, above the list)**

```html
<div class="bxh-filters">
  <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm thành viên…" aria-label="Tìm thành viên" class="bxh-search" />
  <FilterChips :filters="periodFilters" :model-value="[period]" single-select
    @update:model-value="v => period = (v[0] as any) || 'all'" />
  <FilterChips :filters="categoryFilters" :model-value="[category]" single-select
    @update:model-value="v => category = (v[0] as any) || 'total'" />
</div>
<div v-if="selfEntry" class="bxh-self">
  Hạng của bạn: <strong>#{{ selfEntry.rank }}</strong> · {{ selfEntry.points }} điểm
</div>
```

With filter option arrays:

```ts
const periodFilters = [
  { value: 'all', label: 'Tất cả' }, { value: '30d', label: 'Tháng này' }, { value: '7d', label: 'Tuần này' },
]
const categoryFilters = [
  { value: 'total', label: 'Tổng hợp' }, { value: 'reviews', label: 'Đánh giá' },
  { value: 'posts', label: 'Bài viết' }, { value: 'photos', label: 'Ảnh' },
]
```

(Confirm `FilterChips` prop shape `{ value, label }` against `web-nuxt/components/FilterChips.vue` — exploration reported `filters: FilterOption[]` + `modelValue: string[]` + `singleSelect`.)

- [ ] **Step 3: Self-highlight the row**

On each leader `<li>`, add:

```html
<li v-for="m in leaders" :key="m.id" :class="{ 'is-self': m.id === currentUser?.id }">
```

CSS:

```css
.bxh-filters { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-3); }
.bxh-search { flex: 1 1 200px; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-input); border-radius: var(--radius-sm); background: var(--surface); color: var(--ink); }
.bxh-self { padding: var(--space-2) var(--space-3); background: color-mix(in srgb, var(--primary) 8%, transparent); border-radius: var(--radius-sm); margin-bottom: var(--space-2); font-size: var(--text-sm); }
.bxh-list li.is-self { outline: 2px solid var(--primary); border-radius: var(--radius-sm); }
```

- [ ] **Step 4: Build verification**

Run: `cd C:/Code/vinhlong360/web-nuxt && npm run build`
Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add -p web-nuxt/pages/bang-xep-hang.vue
git commit -m "feat(user): leaderboard filters FE — period/category chips, search, self-highlight"
```

---

### Task 9: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run pytest**

Run: `python -m pytest -q`
Expected: baseline (34 pre-existing failures unchanged) + all new `test_wave3.py` classes passing.

- [ ] **Step 2: Run Nuxt build**

Run: `cd web-nuxt && npm run build`
Expected: build passes.

- [ ] **Step 3: Verify routes registered**

Run (from `agent/`, PG-off env):
```python
import achievements, social
routes = [r.path for r in social.router.routes] + [r.path for r in achievements.router.routes]
for t in ["/api/me/achievements", "/api/users/{user_id}/activity-heatmap"]:
    assert t in routes, t
```
Confirm `GET /api/community/leaderboard` still present with new params.

- [ ] **Step 4: Verify migrations exist**

Run: `ls agent/migrations/064_login_streak.sql agent/migrations/065_achievements.sql`
Expected: both exist.

- [ ] **Step 5: Confirm PG_REQUIRED_SCHEMA_VERSION untouched**

Run: `python -c "import sys; sys.path.insert(0,'agent'); import database; assert database.PG_REQUIRED_SCHEMA_VERSION == 62"`
Expected: passes (convention: not bumped per-migration).

- [ ] **Step 6: Mark complete**

---

## Notes for the Executor

- **Task order matters:** Task 1 (login streak columns) must land before Task 2 (achievements read `users.login_streak`). Task 2 before Task 3 (hooks import `check_achievements`). FE tasks (4,5,6,8) depend on their backend counterparts (2,5,6,7).
- **Do NOT apply migrations to prod or run any destructive command** (§B7). Migration files are created + committed only; applying is a separate deploy step (§4 stop condition).
- **Pre-existing dirty branch:** `agent/social.py` and `nguoi-dung/[id].vue` carry unrelated uncommitted work from other sessions. Every task stages ONLY its own hunks (`git add -p` or hunk extraction) and verifies with `git diff --cached` before committing.
- **No local Postgres:** tests are `inspect.getsource()` structural assertions (the `test_wave2.py` convention). They verify wiring, not runtime results — note this when judging "tests pass" as a signal.
