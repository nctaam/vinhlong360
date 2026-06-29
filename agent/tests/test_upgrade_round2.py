"""Tests for upgrade round 2: feed improvements, notifications, performance."""
import inspect
from pathlib import Path
import pytest


AGENT_DIR = Path(__file__).resolve().parent.parent


class TestEntityFeedUnanswered:
    """Unanswered Q&A sort + post_type filter in entity feed."""

    def test_unanswered_in_sort_options(self):
        from social import _ENTITY_FEED_SORT_OPTIONS
        assert "unanswered" in _ENTITY_FEED_SORT_OPTIONS

    def test_feed_has_post_type_param(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "post_type" in src

    def test_unanswered_filters_questions(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "post_type = 'question'" in src
        assert "best_answer_id IS NULL" in src

    def test_unanswered_sorts_by_comment_count(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "comment_count ASC" in src

    def test_post_type_filter_validates(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "_VALID_POST_TYPES" in src
        assert "review" in src

    def test_post_type_filter_uses_parameterized(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "p.post_type = {ph}" in src

    def test_post_type_filter_in_total_count(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert src.count("p.post_type = {ph}") >= 2


class TestNotificationTypes:
    """New notification types: comment_reply, question_answer."""

    def test_comment_reply_type_in_pref_map(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "comment_reply" in _NOTIF_TYPE_TO_PREF

    def test_question_answer_type_in_pref_map(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "question_answer" in _NOTIF_TYPE_TO_PREF

    def test_event_reminder_in_pref_map(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "event_reminder" in _NOTIF_TYPE_TO_PREF

    def test_comment_reply_uses_comment_pref(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert _NOTIF_TYPE_TO_PREF["comment_reply"] == "pref_comment"

    def test_question_answer_uses_comment_pref(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert _NOTIF_TYPE_TO_PREF["question_answer"] == "pref_comment"

    def test_create_comment_sends_reply_type(self):
        src = inspect.getsource(__import__("social").create_comment)
        assert '"comment_reply"' in src

    def test_create_comment_sends_question_answer_type(self):
        src = inspect.getsource(__import__("social").create_comment)
        assert '"question_answer"' in src

    def test_create_comment_fetches_post_type(self):
        src = inspect.getsource(__import__("social").create_comment)
        assert "post_type" in src


class TestFeedPerformanceMigration:
    """Migration 031 for feed performance indexes."""

    def test_migration_exists(self):
        path = AGENT_DIR / "migrations" / "031_feed_performance.sql"
        assert path.exists()

    def test_migration_has_feed_index(self):
        path = AGENT_DIR / "migrations" / "031_feed_performance.sql"
        sql = path.read_text()
        assert "idx_posts_feed_approved" in sql
        assert "moderation_status = 'approved'" in sql

    def test_migration_has_user_recent_index(self):
        path = AGENT_DIR / "migrations" / "031_feed_performance.sql"
        sql = path.read_text()
        assert "idx_posts_user_recent" in sql

    def test_migration_has_notification_dedup_index(self):
        path = AGENT_DIR / "migrations" / "031_feed_performance.sql"
        sql = path.read_text()
        assert "idx_notifications_dedup" in sql

    def test_all_indexes_use_if_not_exists(self):
        path = AGENT_DIR / "migrations" / "031_feed_performance.sql"
        sql = path.read_text()
        assert sql.count("IF NOT EXISTS") >= 3


class TestUserProfileRelationship:
    """Viewer relationship status in user profile response."""

    def test_profile_returns_viewer_relationship(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert "viewer_relationship" in src
        assert "is_following" in src
        assert "is_blocked" in src

    def test_profile_checks_following(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert "viewer_following" in src
        assert "follows" in src

    def test_profile_checks_blocked(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert "viewer_blocked" in src
        assert "blocks" in src

    def test_profile_includes_is_self(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert '"is_self"' in src


class TestAutocomplete:
    """Entity autocomplete endpoint."""

    def test_autocomplete_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/autocomplete" in paths

    def test_autocomplete_has_type_filter(self):
        src = inspect.getsource(__import__("public_api").autocomplete)
        assert "type" in src

    def test_autocomplete_returns_suggestions(self):
        src = inspect.getsource(__import__("public_api").autocomplete)
        assert '"suggestions"' in src

    def test_autocomplete_rate_limited(self):
        src = inspect.getsource(__import__("public_api").autocomplete)
        assert "check_rate" in src

    def test_autocomplete_cached(self):
        src = inspect.getsource(__import__("public_api").autocomplete)
        assert "Cache-Control" in src


class TestTrendingPeriod:
    """Trending tags period filter."""

    def test_period_param_exists(self):
        src = inspect.getsource(__import__("social").trending_tags)
        assert "period" in src

    def test_period_options(self):
        from social import _TRENDING_PERIOD_DAYS
        assert "7d" in _TRENDING_PERIOD_DAYS
        assert "30d" in _TRENDING_PERIOD_DAYS
        assert "90d" in _TRENDING_PERIOD_DAYS

    def test_period_maps_to_days(self):
        from social import _TRENDING_PERIOD_DAYS
        assert _TRENDING_PERIOD_DAYS["7d"] == 7
        assert _TRENDING_PERIOD_DAYS["30d"] == 30

    def test_response_includes_period(self):
        src = inspect.getsource(__import__("social").trending_tags)
        assert '"period"' in src
        assert '"days"' in src


class TestResetPasswordOTP:
    """Password reset via OTP — forgot password flow."""

    def test_endpoint_exists(self):
        from auth import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/auth/reset-password-otp" in paths

    def test_model_validates_password_length(self):
        from auth import ResetPasswordOTP
        with pytest.raises(Exception):
            ResetPasswordOTP(phone="0901234567", code="123456", new_password="short")

    def test_model_validates_password_digit(self):
        from auth import ResetPasswordOTP
        with pytest.raises(Exception):
            ResetPasswordOTP(phone="0901234567", code="123456", new_password="NoDigitHere")

    def test_model_validates_password_letter(self):
        from auth import ResetPasswordOTP
        with pytest.raises(Exception):
            ResetPasswordOTP(phone="0901234567", code="123456", new_password="12345678")

    def test_model_accepts_valid(self):
        from auth import ResetPasswordOTP
        m = ResetPasswordOTP(phone="0901234567", code="123456", new_password="GoodPass1")
        assert m.new_password == "GoodPass1"

    def test_model_normalizes_phone(self):
        from auth import ResetPasswordOTP
        m = ResetPasswordOTP(phone="+84901234567", code="123456", new_password="GoodPass1")
        assert m.phone == "0901234567"

    def test_verifies_otp_before_reset(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "_hash_otp" in src
        assert "otp_sessions" in src
        assert "verified = TRUE" in src

    def test_uses_parameterized_queries(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "db._ph" in src
        assert "f-string" not in src or "{db._ph}" in src

    def test_revokes_all_sessions(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "DELETE FROM user_sessions" in src

    def test_rate_limited_by_ip(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "_otp_verify_ip_rate" in src

    def test_rate_limited_by_phone(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "_otp_verify_phone_rate" in src

    def test_logs_password_reset(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "_log_login" in src
        assert '"password_reset"' in src

    def test_requires_csrf(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "_require_csrf_lazy" in src or "_csrf" in src

    def test_updates_password_hash(self):
        src = inspect.getsource(__import__("auth").reset_password_otp)
        assert "_hash_password" in src
        assert "password_hash" in src


class TestBulkUserBanUnban:
    """Admin bulk ban/unban endpoints."""

    def test_bulk_ban_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/users/bulk-ban" in paths

    def test_bulk_unban_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/users/bulk-unban" in paths

    def test_bulk_ban_model_validates(self):
        from admin import BulkUserAction
        m = BulkUserAction(user_ids=["abc-123"], reason="test")
        assert len(m.user_ids) == 1

    def test_bulk_ban_model_max_50(self):
        from admin import BulkUserAction
        with pytest.raises(Exception):
            BulkUserAction(user_ids=[f"id-{i}" for i in range(51)])

    def test_bulk_ban_model_min_1(self):
        from admin import BulkUserAction
        with pytest.raises(Exception):
            BulkUserAction(user_ids=[])

    def test_bulk_ban_revokes_sessions(self):
        src = inspect.getsource(__import__("admin").bulk_ban_users)
        assert "DELETE FROM user_sessions" in src

    def test_bulk_ban_prevents_self(self):
        src = inspect.getsource(__import__("admin").bulk_ban_users)
        assert "Không thể tự ban chính mình" in src

    def test_bulk_ban_logs_actions(self):
        src = inspect.getsource(__import__("admin").bulk_ban_users)
        assert "_log_mod_action" in src

    def test_bulk_unban_logs_actions(self):
        src = inspect.getsource(__import__("admin").bulk_unban_users)
        assert "_log_mod_action" in src

    def test_bulk_ban_uses_parameterized(self):
        src = inspect.getsource(__import__("admin").bulk_ban_users)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_bulk_unban_skips_active(self):
        src = inspect.getsource(__import__("admin").bulk_unban_users)
        assert "is_active" in src


class TestHiddenPostsMigration:
    """Migration 032 for hidden posts + pinned comments."""

    def test_migration_exists(self):
        path = AGENT_DIR / "migrations" / "032_hidden_posts_pin_comment.sql"
        assert path.exists()

    def test_migration_creates_table(self):
        sql = (AGENT_DIR / "migrations" / "032_hidden_posts_pin_comment.sql").read_text()
        assert "user_hidden_posts" in sql
        assert "CREATE TABLE IF NOT EXISTS" in sql

    def test_migration_has_index(self):
        sql = (AGENT_DIR / "migrations" / "032_hidden_posts_pin_comment.sql").read_text()
        assert "idx_hidden_posts_user" in sql

    def test_migration_adds_pinned_column(self):
        sql = (AGENT_DIR / "migrations" / "032_hidden_posts_pin_comment.sql").read_text()
        assert "pinned_comment_id" in sql
        assert "ALTER TABLE posts" in sql


class TestHidePostEndpoints:
    """Hide/unhide post + list hidden posts."""

    def test_hide_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/{post_id}/hide" in paths

    def test_unhide_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/{post_id}/unhide" in paths

    def test_hidden_list_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/hidden" in paths

    def test_hide_uses_parameterized(self):
        src = inspect.getsource(__import__("social").hide_post)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_hide_requires_auth(self):
        src = inspect.getsource(__import__("social").hide_post)
        assert "require_user" in src

    def test_hide_uses_on_conflict(self):
        src = inspect.getsource(__import__("social").hide_post)
        assert "ON CONFLICT DO NOTHING" in src

    def test_unhide_uses_parameterized(self):
        src = inspect.getsource(__import__("social").unhide_post)
        assert "db._ph" in src

    def test_feed_filters_hidden(self):
        src = inspect.getsource(__import__("social").get_feed)
        assert "user_hidden_posts" in src

    def test_following_feed_filters_hidden(self):
        src = inspect.getsource(__import__("social").get_following_feed)
        assert "user_hidden_posts" in src


class TestPinComment:
    """Pin/unpin comment by post author."""

    def test_pin_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/{post_id}/pin-comment" in paths

    def test_pin_requires_auth(self):
        src = inspect.getsource(__import__("social").pin_comment)
        assert "require_user" in src

    def test_pin_checks_post_author(self):
        src = inspect.getsource(__import__("social").pin_comment)
        assert "user_id" in src
        assert "403" in src or "Chỉ tác giả" in src

    def test_pin_verifies_comment_belongs(self):
        src = inspect.getsource(__import__("social").pin_comment)
        assert "post_id" in src
        assert "comments" in src

    def test_pin_uses_parameterized(self):
        src = inspect.getsource(__import__("social").pin_comment)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_unpin_checks_author(self):
        src = inspect.getsource(__import__("social").unpin_comment)
        assert "user_id" in src
        assert "403" in src or "Chỉ tác giả" in src

    def test_format_post_includes_pinned(self):
        src = inspect.getsource(__import__("social")._format_post)
        assert "pinned_comment_id" in src


class TestEntityStats:
    """Entity stats endpoint."""

    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/stats" in paths

    def test_returns_review_count(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert '"review_count"' in src

    def test_returns_avg_rating(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert '"avg_rating"' in src
        assert "AVG(rating)" in src

    def test_returns_bookmark_count(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert '"bookmark_count"' in src
        assert "saved_entities" in src

    def test_returns_follower_count(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert '"follower_count"' in src
        assert "follows" in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_cached(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert "Cache-Control" in src

    def test_filters_approved_reviews(self):
        src = inspect.getsource(__import__("public_api").get_entity_stats)
        assert "approved" in src
        assert "post_type = 'review'" in src


class TestUserActivity:
    """User activity feed endpoint."""

    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/me/activity" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert "require_user" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert "check_rate" in src

    def test_returns_posts(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert '"post"' in src
        assert "posts" in src

    def test_returns_comments(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert '"comment"' in src

    def test_returns_likes(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert '"like"' in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert "db._ph" in src

    def test_merges_and_sorts(self):
        src = inspect.getsource(__import__("public_api").user_activity)
        assert "sorted" in src
        assert "created_at" in src


class TestVisitStats:
    """Visit stats endpoint."""

    def test_endpoint_exists(self):
        from visits import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/me/visits/stats" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("visits").visit_stats)
        assert "require_user" in src

    def test_returns_totals(self):
        src = inspect.getsource(__import__("visits").visit_stats)
        assert '"total"' in src
        assert '"visited"' in src
        assert '"want"' in src

    def test_returns_by_type(self):
        src = inspect.getsource(__import__("visits").visit_stats)
        assert '"by_type"' in src
        assert "e.type" in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("visits").visit_stats)
        assert "db._ph" in src

    def test_uses_filter_aggregation(self):
        src = inspect.getsource(__import__("visits").visit_stats)
        assert "FILTER" in src


class TestTrendingPosts:
    """Trending posts feed endpoint."""

    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/feed/trending" in paths

    def test_window_options(self):
        from social import _TRENDING_POSTS_WINDOWS
        assert "24h" in _TRENDING_POSTS_WINDOWS
        assert "7d" in _TRENDING_POSTS_WINDOWS
        assert "30d" in _TRENDING_POSTS_WINDOWS

    def test_engagement_weighted_sort(self):
        src = inspect.getsource(__import__("social").trending_posts)
        assert "like_count" in src
        assert "comment_count" in src

    def test_time_windowed(self):
        src = inspect.getsource(__import__("social").trending_posts)
        assert "INTERVAL" in src
        assert "days" in src

    def test_block_filter(self):
        src = inspect.getsource(__import__("social").trending_posts)
        assert "_block_sql" in src

    def test_response_includes_window(self):
        src = inspect.getsource(__import__("social").trending_posts)
        assert '"window"' in src
        assert '"days"' in src


class TestUserCounts:
    """User badge counts endpoint."""

    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/me/counts" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").user_counts)
        assert "require_user" in src

    def test_returns_unread_notifications(self):
        src = inspect.getsource(__import__("social").user_counts)
        assert '"unread_notifications"' in src

    def test_returns_posts_count(self):
        src = inspect.getsource(__import__("social").user_counts)
        assert '"posts"' in src

    def test_returns_bookmarks_count(self):
        src = inspect.getsource(__import__("social").user_counts)
        assert '"bookmarks"' in src
        assert "saved_entities" in src

    def test_returns_visits_count(self):
        src = inspect.getsource(__import__("social").user_counts)
        assert '"visits"' in src
        assert "user_visits" in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("social").user_counts)
        assert "db._ph" in src


class TestPostColsPinnedComment:
    """_POST_COLS includes pinned_comment_id."""

    def test_post_cols_has_pinned(self):
        from social import _POST_COLS
        assert "pinned_comment_id" in _POST_COLS


class TestRound2IndexesMigration:
    """Migration 033 for round 2 performance indexes."""

    def test_migration_exists(self):
        path = AGENT_DIR / "migrations" / "033_round2_indexes.sql"
        assert path.exists()

    def test_has_review_stats_index(self):
        sql = (AGENT_DIR / "migrations" / "033_round2_indexes.sql").read_text()
        assert "idx_posts_entity_review_stats" in sql

    def test_has_trending_index(self):
        sql = (AGENT_DIR / "migrations" / "033_round2_indexes.sql").read_text()
        assert "idx_posts_trending" in sql
        assert "like_count" in sql
        assert "comment_count" in sql

    def test_has_user_activity_indexes(self):
        sql = (AGENT_DIR / "migrations" / "033_round2_indexes.sql").read_text()
        assert "idx_comments_user_recent" in sql
        assert "idx_likes_user_recent" in sql

    def test_has_notification_unread_index(self):
        sql = (AGENT_DIR / "migrations" / "033_round2_indexes.sql").read_text()
        assert "idx_notifications_unread" in sql
        assert "is_read = FALSE" in sql

    def test_has_entity_stats_indexes(self):
        sql = (AGENT_DIR / "migrations" / "033_round2_indexes.sql").read_text()
        assert "idx_saved_entities_entity" in sql
        assert "idx_follows_entity_target" in sql

    def test_all_use_if_not_exists(self):
        sql = (AGENT_DIR / "migrations" / "033_round2_indexes.sql").read_text()
        assert sql.count("IF NOT EXISTS") >= 7
