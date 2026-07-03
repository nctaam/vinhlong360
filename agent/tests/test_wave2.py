"""Tests for Wave 2 — User System Deep Upgrade (Activity Timeline + Profile Depth).

Task 1: Profile view tracking — migration 063_profile_views.sql,
_log_profile_view() dedup-per-day helper, view_count_7d in self-profile response.
"""
import os
import sys
import inspect
import pathlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import social

ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestProfileViewMigration:
    """Migration 063 creates profile_views with per-day dedup + owner fix."""

    MIG = (ROOT / "agent" / "migrations" / "063_profile_views.sql").read_text(encoding="utf-8")

    def test_migration_file_exists_and_creates_table(self):
        assert "CREATE TABLE IF NOT EXISTS profile_views" in self.MIG

    def test_table_has_viewer_and_viewed_fk_to_users(self):
        assert "viewer_id" in self.MIG
        assert "viewed_id" in self.MIG
        assert self.MIG.count("REFERENCES users(id) ON DELETE CASCADE") >= 2

    def test_dedup_unique_constraint_per_viewer_viewed_date(self):
        assert "UNIQUE(viewer_id, viewed_id, viewed_date)" in self.MIG

    def test_index_on_viewed_id_and_date_for_7day_count_query(self):
        assert "idx_profile_views_viewed_id_date" in self.MIG
        assert "profile_views(viewed_id, viewed_date)" in self.MIG

    def test_new_table_has_explicit_owner(self):
        # Bài học ownership (deploy gotcha, xem test_migration_chain.py) — bảng
        # mới phải ALTER OWNER TO vl360 nếu không sẽ vỡ quyền ghi trên prod.
        assert "ALTER TABLE profile_views OWNER TO vl360" in self.MIG

    def test_records_schema_version_63_monotonic(self):
        assert "VALUES ('agent', 63," in self.MIG
        assert "GREATEST(schema_version.version, EXCLUDED.version)" in self.MIG

    def test_no_sqlite_dialect_leakage(self):
        assert "AUTOINCREMENT" not in self.MIG


class TestProfileViewTracking:
    def test_log_profile_view_function_exists(self):
        from social import _log_profile_view
        assert callable(_log_profile_view)

    def test_log_profile_view_deduplicates_per_day(self):
        src = inspect.getsource(social._log_profile_view)
        assert "ON CONFLICT" in src or "INSERT" in src
        assert "viewed_date" in src

    def test_log_profile_view_uses_on_conflict_do_nothing(self):
        src = inspect.getsource(social._log_profile_view)
        assert "ON CONFLICT" in src
        assert "DO NOTHING" in src

    def test_profile_view_skips_self_view(self):
        src = inspect.getsource(social._log_profile_view)
        assert "viewer_id" in src
        assert "viewed_id" in src
        # Guard chặn tự-xem-tự (không log, không cộng view ảo).
        assert "viewer_id == viewed_id" in src or "viewer_id != viewed_id" in src

    def test_profile_response_includes_view_count_for_self(self):
        src = inspect.getsource(social.get_user_profile)
        assert "view_count_7d" in src

    def test_view_logging_is_fire_and_forget_non_blocking(self):
        # Không được await trực tiếp _log_profile_view trên request path —
        # phải qua create_task/to_thread để không làm chậm response chính.
        src = inspect.getsource(social.get_user_profile)
        assert "_log_profile_view" in src
        assert "create_task" in src or "ensure_future" in src

    def test_view_count_query_scoped_to_7_days(self):
        src = inspect.getsource(social.get_user_profile)
        assert "INTERVAL '7 days'" in src

    def test_view_count_uses_distinct_viewer_to_avoid_double_count(self):
        src = inspect.getsource(social.get_user_profile)
        assert "COUNT(DISTINCT viewer_id)" in src


class TestActivityTimeline:
    """Task 2: GET /api/users/{user_id}/timeline — union of posts, reviews,
    and follows for a user's chronological activity feed."""

    def test_timeline_endpoint_exists(self):
        src = inspect.getsource(social.get_user_timeline)
        assert "timeline" in src.lower()

    def test_timeline_uses_union_query(self):
        src = inspect.getsource(social.get_user_timeline)
        assert "UNION ALL" in src

    def test_timeline_respects_privacy(self):
        src = inspect.getsource(social.get_user_timeline)
        assert "is_private" in src

    def test_timeline_has_pagination(self):
        src = inspect.getsource(social.get_user_timeline)
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_timeline_returns_typed_items(self):
        src = inspect.getsource(social.get_user_timeline)
        for item_type in ("post", "review", "follow"):
            assert f"'{item_type}'" in src or f'"{item_type}"' in src

    def test_timeline_validates_path_id(self):
        # Bảo vệ path param user_id giống các endpoint /users/{user_id}/* khác.
        src = inspect.getsource(social.get_user_timeline)
        assert "validate_path_id" in src

    def test_timeline_uses_optional_auth_dependency(self):
        # Timeline công khai xem được (nếu không private) — auth optional,
        # dùng get_current_user chứ không phải require_user.
        src = inspect.getsource(social.get_user_timeline)
        assert "Depends(get_current_user)" in src

    def test_timeline_excludes_unapproved_and_deleted_posts(self):
        src = inspect.getsource(social.get_user_timeline)
        assert "moderation_status" in src
        assert "deleted_at IS NULL" in src

    def test_timeline_response_has_expected_top_level_keys(self):
        src = inspect.getsource(social.get_user_timeline)
        for key in ("items", "total", "page", "has_more"):
            assert f'"{key}"' in src

    def test_timeline_404_for_missing_user(self):
        src = inspect.getsource(social.get_user_timeline)
        assert "404" in src

    def test_timeline_applies_prod_seed_post_filter(self):
        # Wave 2 review fix: get_user_posts/get_user_reviews đều splice
        # _prod_seed_post_filter để loại bài seed/test admin trên prod —
        # timeline (UNION 2 nhánh post+review) đã thiếu filter này.
        src = inspect.getsource(social.get_user_timeline)
        assert "_prod_seed_post_filter" in src


class TestBadgeProgress:
    """Task 4: GET /api/me/badge-progress — all 10 badges with earned status
    and current/target progress toward the ones not yet earned."""

    def test_badge_progress_endpoint_exists(self):
        src = inspect.getsource(social.get_badge_progress)
        assert "badge" in src.lower()

    def test_badge_progress_returns_all_badges(self):
        src = inspect.getsource(social.get_badge_progress)
        for badge_id in ("first_review", "review_master", "photographer", "explorer",
                         "popular", "quality", "allrounder", "traveler", "local", "veteran"):
            assert badge_id in src

    def test_badge_progress_has_current_and_target(self):
        src = inspect.getsource(social.get_badge_progress)
        assert "current" in src
        assert "target" in src

    def test_badge_progress_requires_auth(self):
        # Dùng require_user (không phải get_current_user) — badge tiến độ là
        # dữ liệu riêng tư của người dùng, không công khai như timeline.
        src = inspect.getsource(social.get_badge_progress)
        assert "Depends(require_user)" in src

    def test_badge_progress_marks_earned_flag(self):
        src = inspect.getsource(social.get_badge_progress)
        assert "earned" in src


class TestFollowingFeedEnhancement:
    """Task 7: GET /api/feed/friend-reviews + /api/feed/friend-saves — recent
    review/save activity from users the caller follows, surfaced in the
    community page's "Đang theo dõi" tab."""

    def test_friend_reviews_endpoint_exists(self):
        src = inspect.getsource(social.get_friend_reviews)
        assert "review" in src.lower()

    def test_friend_reviews_filters_by_followed_users(self):
        src = inspect.getsource(social.get_friend_reviews)
        assert "follows" in src
        assert "target_type" in src

    def test_friend_reviews_requires_auth(self):
        src = inspect.getsource(social.get_friend_reviews)
        assert "Depends(require_user)" in src

    def test_friend_reviews_excludes_unapproved_and_deleted(self):
        src = inspect.getsource(social.get_friend_reviews)
        assert "moderation_status" in src
        assert "deleted_at IS NULL" in src

    def test_friend_reviews_applies_block_and_mute_filters(self):
        src = inspect.getsource(social.get_friend_reviews)
        assert "_block_sql" in src
        assert "_mute_sql" in src

    def test_friend_reviews_applies_prod_seed_post_filter(self):
        # Wave 2 review fix: get_following_feed đã có _prod_seed_post_filter,
        # friend-reviews (siblings cùng tab "Đang theo dõi") thì thiếu.
        src = inspect.getsource(social.get_friend_reviews)
        assert "_prod_seed_post_filter" in src

    def test_friend_reviews_excludes_hidden_posts(self):
        # Wave 2 review fix: get_following_feed loại post viewer đã ẩn qua
        # user_hidden_posts — friend-reviews thiếu filter này nên review đã
        # ẩn có thể lọt lại vào tab "Đang theo dõi".
        src = inspect.getsource(social.get_friend_reviews)
        assert "user_hidden_posts" in src

    def test_friend_saves_endpoint_exists(self):
        src = inspect.getsource(social.get_friend_saves)
        assert "bookmark" in src.lower() or "save" in src.lower()

    def test_friend_saves_filters_by_followed_users(self):
        src = inspect.getsource(social.get_friend_saves)
        assert "follows" in src
        assert "target_type" in src

    def test_friend_saves_requires_auth(self):
        src = inspect.getsource(social.get_friend_saves)
        assert "Depends(require_user)" in src

    def test_friend_saves_excludes_own_saves(self):
        # Không hiện lại chính-mình trong danh sách "được lưu bởi bạn bè".
        src = inspect.getsource(social.get_friend_saves)
        assert "!=" in src


class TestWeeklyDigest:
    """Task 8: Weekly activity digest — scheduler task sends an in-app
    notification once per week summarizing each active user's new followers,
    likes, and posts. Registered as a ScheduledTask (7-day interval,
    run_immediately=False so it doesn't fire on every server restart)."""

    def test_weekly_digest_function_exists(self):
        import scheduler
        assert callable(scheduler.task_weekly_digest)

    def test_weekly_digest_registered_in_tasks(self):
        import scheduler
        names = [t.name for t in scheduler.TASKS]
        assert "weekly-digest" in names

    def test_weekly_digest_registered_with_weekly_interval_and_not_immediate(self):
        import scheduler
        task = next(t for t in scheduler.TASKS if t.name == "weekly-digest")
        assert task.interval == 7 * 24 * 3600
        # run_immediately=False → next_run_after scheduled in the future, not 0.
        assert task.next_run_after > 0

    def test_weekly_digest_uses_create_notification(self):
        import scheduler
        src = inspect.getsource(scheduler.task_weekly_digest)
        assert "create_notification" in src

    def test_weekly_digest_queries_weekly_stats(self):
        import scheduler
        src = inspect.getsource(scheduler.task_weekly_digest)
        assert "7 days" in src or "7 day" in src or "INTERVAL" in src

    def test_weekly_digest_does_not_reference_nonexistent_last_active_at_column(self):
        # last_active_at was never added to the users table (verified against
        # init.sql + every migration) — using it would crash the task at
        # runtime with UndefinedColumn. Guard against reintroducing it.
        import scheduler
        src = inspect.getsource(scheduler.task_weekly_digest)
        assert "last_active_at" not in src

    def test_weekly_digest_filters_active_non_deleted_users(self):
        import scheduler
        src = inspect.getsource(scheduler.task_weekly_digest)
        assert "is_active" in src
        assert "deleted_at IS NULL" in src

    def test_weekly_digest_guards_postgres_only(self):
        # UGC tables (users/posts/follows) are Postgres-only per
        # architecture-decisions.md — sibling tasks (task_event_reminders,
        # task_notification_cleanup) all guard with `if not db._use_pg: return`.
        import scheduler
        src = inspect.getsource(scheduler.task_weekly_digest)
        assert "_use_pg" in src

    def test_weekly_digest_skips_users_with_no_activity(self):
        # Don't send an empty/noise notification to users with zero new
        # followers, likes, and posts this week.
        import scheduler
        src = inspect.getsource(scheduler.task_weekly_digest)
        assert "continue" in src
