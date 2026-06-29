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


class TestDeleteNotification:
    """Delete individual notification endpoint."""

    def test_endpoint_exists(self):
        from notifications import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/notifications/{notif_id}" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("notifications").delete_notification)
        assert "require_user" in src

    def test_requires_csrf(self):
        src = inspect.getsource(__import__("notifications").delete_notification)
        assert "require_csrf" in src or "_csrf" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("notifications").delete_notification)
        assert "check_rate" in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("notifications").delete_notification)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_scoped_to_user(self):
        src = inspect.getsource(__import__("notifications").delete_notification)
        assert "user_id" in src


class TestCommentLikes:
    """Comment like/unlike toggle."""

    def test_migration_exists(self):
        path = AGENT_DIR / "migrations" / "034_comment_likes.sql"
        assert path.exists()

    def test_migration_creates_table(self):
        sql = (AGENT_DIR / "migrations" / "034_comment_likes.sql").read_text()
        assert "comment_likes" in sql
        assert "CREATE TABLE IF NOT EXISTS" in sql

    def test_migration_adds_like_count(self):
        sql = (AGENT_DIR / "migrations" / "034_comment_likes.sql").read_text()
        assert "like_count" in sql
        assert "ALTER TABLE comments" in sql

    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/comments/{comment_id}/like" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "require_user" in src

    def test_prevents_self_like(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "chính mình" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "check_rate" in src

    def test_returns_liked_and_count(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert '"liked"' in src
        assert '"like_count"' in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_format_comment_has_like_count(self):
        src = inspect.getsource(__import__("social")._format_comment)
        assert "like_count" in src


class TestEntityReviews:
    """Dedicated entity reviews endpoint."""

    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/reviews" in paths

    def test_sort_options(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert "newest" in src
        assert "helpful" in src
        assert "highest" in src
        assert "lowest" in src

    def test_returns_distribution(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert '"distribution"' in src
        assert "GROUP BY p.rating" in src

    def test_returns_avg_rating(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert '"avg_rating"' in src
        assert "AVG" in src

    def test_min_rating_filter(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert "min_rating" in src
        assert "p.rating >=" in src

    def test_uses_parameterized(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert "db._ph" in src
        assert "validate_path_id" in src

    def test_cached(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert "Cache-Control" in src

    def test_pagination(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert '"has_more"' in src
        assert '"page"' in src
        assert '"total"' in src


# ── User data export (GDPR) ──

class TestUserDataExport:
    """GET /auth/export-data — user downloads all their data."""

    def test_endpoint_exists(self):
        from auth import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/auth/export-data" in paths

    def test_method_is_get(self):
        from auth import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/auth/export-data":
                assert "GET" in r.methods

    def test_requires_auth(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "_get_current_user_or_none" in src
        assert "401" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "check_rate" in src
        assert "export-data" in src

    def test_queries_posts(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "FROM posts WHERE user_id" in src

    def test_queries_comments(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "FROM comments WHERE user_id" in src

    def test_queries_likes(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "FROM post_likes WHERE user_id" in src

    def test_queries_bookmarks(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "FROM saved_entities WHERE user_id" in src

    def test_queries_follows(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "FROM follows WHERE user_id" in src

    def test_queries_visits(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "FROM user_visits WHERE user_id" in src

    def test_returns_profile(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert '"profile"' in src
        assert "_safe_user" in src

    def test_returns_exported_at(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert '"exported_at"' in src

    def test_parameterized_queries(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "db._ph" in src
        assert "uid" in src

    def test_uses_asyncio_to_thread(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "asyncio.to_thread" in src

    def test_docstring_updated(self):
        import auth
        assert "export-data" in auth.__doc__


# ── Report comment ──

class TestReportComment:
    """POST /api/comments/{comment_id}/report — report a comment."""

    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/comments/{comment_id}/report" in paths

    def test_method_is_post(self):
        from social import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/api/comments/{comment_id}/report":
                assert "POST" in r.methods

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "require_user" in src

    def test_has_csrf(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "require_csrf" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "check_rate" in src
        assert "report-comment" in src

    def test_validates_comment_id(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "validate_path_id" in src

    def test_checks_comment_exists(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "FROM comments WHERE" in src
        assert "404" in src

    def test_prevents_self_report(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "uid" in src
        assert "400" in src

    def test_writes_to_reports_jsonl(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "reports.jsonl" in src
        assert '"target_type": "comment"' in src

    def test_report_reasons(self):
        from social import _COMMENT_REPORT_REASONS
        assert "spam" in _COMMENT_REPORT_REASONS
        assert "harassment" in _COMMENT_REPORT_REASONS
        assert "inappropriate" in _COMMENT_REPORT_REASONS

    def test_model_validation(self):
        from social import ReportCommentBody
        body = ReportCommentBody(reason="spam", detail="test")
        assert body.reason == "spam"

    def test_parameterized_query(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "db._ph" in src


# ── Moderation appeals (NĐ147 compliance) ──

class TestAppealsMigration:
    """Migration 035: moderation_appeals table."""

    def test_migration_file_exists(self):
        path = AGENT_DIR / "migrations" / "035_moderation_appeals.sql"
        assert path.exists()

    def test_creates_table(self):
        sql = (AGENT_DIR / "migrations" / "035_moderation_appeals.sql").read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS moderation_appeals" in sql

    def test_has_status_check(self):
        sql = (AGENT_DIR / "migrations" / "035_moderation_appeals.sql").read_text(encoding="utf-8")
        assert "pending" in sql
        assert "approved" in sql
        assert "rejected" in sql

    def test_unique_per_user_post(self):
        sql = (AGENT_DIR / "migrations" / "035_moderation_appeals.sql").read_text(encoding="utf-8")
        assert "UNIQUE" in sql

    def test_has_indexes(self):
        sql = (AGENT_DIR / "migrations" / "035_moderation_appeals.sql").read_text(encoding="utf-8")
        assert "idx_moderation_appeals_status" in sql
        assert "idx_moderation_appeals_user" in sql


class TestAppealPostEndpoint:
    """POST /api/posts/{post_id}/appeal — user appeals rejected post."""

    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/{post_id}/appeal" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "require_user" in src

    def test_has_csrf(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "require_csrf" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "check_rate" in src

    def test_validates_post_id(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "validate_path_id" in src

    def test_checks_post_ownership(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "403" in src
        assert "user_id" in src

    def test_requires_rejected_status(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert '"rejected"' in src
        assert "400" in src

    def test_prevents_duplicate_appeal(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "409" in src
        assert "moderation_appeals" in src

    def test_inserts_appeal(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "INSERT INTO moderation_appeals" in src

    def test_parameterized(self):
        src = inspect.getsource(__import__("social").appeal_post)
        assert "db._ph" in src

    def test_model_validation(self):
        from social import AppealBody
        body = AppealBody(reason="This is a valid appeal reason")
        assert len(body.reason) >= 10


class TestGetAppealStatus:
    """GET /api/posts/{post_id}/appeal — user checks appeal status."""

    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        get_paths = []
        for r in router.routes:
            if hasattr(r, "path") and "GET" in getattr(r, "methods", set()):
                get_paths.append(r.path)
        assert "/api/posts/{post_id}/appeal" in get_paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").get_appeal_status)
        assert "require_user" in src

    def test_returns_appeal_fields(self):
        src = inspect.getsource(__import__("social").get_appeal_status)
        assert '"status"' in src
        assert '"reviewer_note"' in src
        assert '"created_at"' in src


class TestAdminAppeals:
    """Admin appeal management endpoints."""

    def test_list_appeals_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/appeals" in paths

    def test_approve_appeal_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/appeals/{appeal_id}/approve" in paths

    def test_reject_appeal_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/appeals/{appeal_id}/reject" in paths

    def test_list_appeals_pagination(self):
        src = inspect.getsource(__import__("admin").list_appeals)
        assert '"total"' in src
        assert '"page"' in src
        assert "LIMIT" in src

    def test_list_appeals_status_filter(self):
        src = inspect.getsource(__import__("admin").list_appeals)
        assert "pending" in src
        assert "all" in src

    def test_approve_appeal_updates_post(self):
        src = inspect.getsource(__import__("admin").approve_appeal)
        assert "moderation_status = 'approved'" in src

    def test_approve_appeal_notifies_user(self):
        src = inspect.getsource(__import__("admin").approve_appeal)
        assert "create_notification" in src

    def test_reject_appeal_notifies_user(self):
        src = inspect.getsource(__import__("admin").reject_appeal)
        assert "create_notification" in src

    def test_appeal_status_check(self):
        src = inspect.getsource(__import__("admin").approve_appeal)
        assert '"pending"' in src
        assert "400" in src

    def test_appeal_parameterized(self):
        src = inspect.getsource(__import__("admin").approve_appeal)
        assert "db._ph" in src
        assert "validate_path_id" in src


# ── Search query logging & analytics ──

class TestSearchQueryLogging:
    """Search endpoint logs queries to JSONL for analytics."""

    def test_search_calls_log(self):
        src = inspect.getsource(__import__("public_api").search)
        assert "_log_search_query" in src

    def test_log_function_exists(self):
        from public_api import _log_search_query
        assert callable(_log_search_query)

    def test_log_writes_jsonl(self):
        src = inspect.getsource(__import__("public_api")._log_search_query)
        assert "SEARCH_LOG_FILE" in src
        assert "json.dumps" in src

    def test_log_records_fields(self):
        src = inspect.getsource(__import__("public_api")._log_search_query)
        assert '"q"' in src
        assert '"type"' in src
        assert '"results"' in src
        assert '"ts"' in src

    def test_log_uses_lock(self):
        src = inspect.getsource(__import__("public_api")._log_search_query)
        assert "_jsonl_lock" in src

    def test_log_rotates(self):
        src = inspect.getsource(__import__("public_api")._log_search_query)
        assert "_maybe_rotate_jsonl" in src

    def test_log_silent_failure(self):
        src = inspect.getsource(__import__("public_api")._log_search_query)
        assert "except" in src


class TestAdminSearchAnalytics:
    """GET /admin/search-analytics — aggregated search insights."""

    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/search-analytics" in paths

    def test_returns_top_queries(self):
        src = inspect.getsource(__import__("admin").search_analytics)
        assert '"top_queries"' in src

    def test_returns_zero_results(self):
        src = inspect.getsource(__import__("admin").search_analytics)
        assert '"zero_results"' in src

    def test_returns_total(self):
        src = inspect.getsource(__import__("admin").search_analytics)
        assert '"total_searches"' in src

    def test_filters_by_period(self):
        src = inspect.getsource(__import__("admin").search_analytics)
        assert "cutoff" in src
        assert "days" in src

    def test_reads_jsonl(self):
        src = inspect.getsource(__import__("admin").search_analytics)
        assert "search_queries.jsonl" in src

    def test_uses_asyncio_to_thread(self):
        src = inspect.getsource(__import__("admin").search_analytics)
        assert "asyncio.to_thread" in src


# ── Dashboard alerts includes appeals ──

class TestDashboardAlertsAppeals:
    """Dashboard alerts include pending appeals count."""

    def test_alerts_check_appeals(self):
        src = inspect.getsource(__import__("admin").dashboard_alerts)
        assert "moderation_appeals" in src
        assert '"appeals"' in src

    def test_appeals_alert_priority(self):
        src = inspect.getsource(__import__("admin").dashboard_alerts)
        assert "khiếu nại" in src


# ── User engagement stats ──

class TestUserEngagementStats:
    """GET /admin/user-engagement — engagement metrics for admin."""

    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/user-engagement" in paths

    def test_returns_metrics(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert '"active_posters"' in src
        assert '"active_commenters"' in src
        assert '"active_likers"' in src

    def test_returns_new_users(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert '"new_users"' in src

    def test_returns_retained_users(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert '"retained_users"' in src

    def test_returns_engagement_rate(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert '"engagement_rate"' in src

    def test_returns_daily_active(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert '"daily_active"' in src
        assert "DATE(created_at)" in src

    def test_requires_pg(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert "db._use_pg" in src

    def test_period_param(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert "days" in src
        assert "period_days" in src


# ── Review responses ──

class TestReviewResponseMigration:
    """Migration 036: review_responses table."""

    def test_migration_file_exists(self):
        path = AGENT_DIR / "migrations" / "036_review_responses.sql"
        assert path.exists()

    def test_creates_table(self):
        sql = (AGENT_DIR / "migrations" / "036_review_responses.sql").read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS review_responses" in sql

    def test_unique_per_post(self):
        sql = (AGENT_DIR / "migrations" / "036_review_responses.sql").read_text(encoding="utf-8")
        assert "UNIQUE(post_id)" in sql

    def test_has_index(self):
        sql = (AGENT_DIR / "migrations" / "036_review_responses.sql").read_text(encoding="utf-8")
        assert "idx_review_responses_post" in sql


class TestAdminReviewResponse:
    """POST /admin/posts/{post_id}/response — admin responds to review."""

    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/posts/{post_id}/response" in paths

    def test_validates_post_id(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert "validate_path_id" in src

    def test_only_reviews(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert '"review"' in src
        assert "400" in src

    def test_prevents_duplicate(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert "409" in src

    def test_inserts_response(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert "INSERT INTO review_responses" in src

    def test_notifies_author(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert "create_notification" in src

    def test_html_escapes_content(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert "_html.escape" in src

    def test_parameterized(self):
        src = inspect.getsource(__import__("admin").add_review_response)
        assert "db._ph" in src

    def test_model_validation(self):
        from admin import ReviewResponseBody
        body = ReviewResponseBody(content="Test response")
        assert body.content == "Test response"


class TestDeleteReviewResponse:
    """DELETE /admin/posts/{post_id}/response."""

    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/posts/{post_id}/response" in paths

    def test_validates_post_id(self):
        src = inspect.getsource(__import__("admin").delete_review_response)
        assert "validate_path_id" in src

    def test_returns_404_if_none(self):
        src = inspect.getsource(__import__("admin").delete_review_response)
        assert "404" in src


class TestFormatPostReviewResponse:
    """_format_post includes review_response field."""

    def test_includes_review_response(self):
        src = inspect.getsource(__import__("social")._format_post)
        assert '"review_response"' in src
        assert '"response_content"' in src
        assert '"responder_name"' in src
