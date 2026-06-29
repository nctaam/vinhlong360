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


# ── Entity claims ──

class TestEntityClaimsMigration:
    """Migration 037: entity_claims table."""

    def test_migration_file_exists(self):
        path = AGENT_DIR / "migrations" / "037_entity_claims.sql"
        assert path.exists()

    def test_creates_table(self):
        sql = (AGENT_DIR / "migrations" / "037_entity_claims.sql").read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS entity_claims" in sql

    def test_status_check(self):
        sql = (AGENT_DIR / "migrations" / "037_entity_claims.sql").read_text(encoding="utf-8")
        assert "pending" in sql
        assert "approved" in sql
        assert "rejected" in sql

    def test_unique_per_entity_user(self):
        sql = (AGENT_DIR / "migrations" / "037_entity_claims.sql").read_text(encoding="utf-8")
        assert "UNIQUE" in sql

    def test_has_indexes(self):
        sql = (AGENT_DIR / "migrations" / "037_entity_claims.sql").read_text(encoding="utf-8")
        assert "idx_entity_claims_status" in sql
        assert "idx_entity_claims_entity" in sql


class TestSubmitEntityClaim:
    """POST /api/entities/{entity_id}/claim — user submits ownership claim."""

    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/claim" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "require_user" in src

    def test_has_csrf(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "require_csrf" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "check_rate" in src

    def test_validates_entity_id(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "validate_path_id" in src

    def test_checks_entity_exists(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "get_entity" in src
        assert "404" in src

    def test_prevents_duplicate(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "409" in src

    def test_inserts_claim(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "INSERT INTO entity_claims" in src

    def test_html_escapes(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "_html.escape" in src

    def test_model_validation(self):
        from public_api import EntityClaimIn
        claim = EntityClaimIn(business_name="Test", contact_phone="0901234567")
        assert claim.business_name == "Test"


class TestAdminClaims:
    """Admin claim management endpoints."""

    def test_list_claims_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/claims" in paths

    def test_approve_claim_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/claims/{claim_id}/approve" in paths

    def test_reject_claim_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/claims/{claim_id}/reject" in paths

    def test_list_claims_pagination(self):
        src = inspect.getsource(__import__("admin").list_claims)
        assert '"total"' in src
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_list_claims_status_filter(self):
        src = inspect.getsource(__import__("admin").list_claims)
        assert "pending" in src
        assert "all" in src

    def test_approve_claim_updates_status(self):
        src = inspect.getsource(__import__("admin").approve_claim)
        assert "'approved'" in src
        assert "UPDATE" in src

    def test_reject_claim_uses_reason(self):
        src = inspect.getsource(__import__("admin").reject_claim)
        assert "body.reason" in src
        assert "'rejected'" in src

    def test_claim_status_check(self):
        src = inspect.getsource(__import__("admin").approve_claim)
        assert '"pending"' in src
        assert "409" in src or "not_pending" in src

    def test_claim_parameterized(self):
        src = inspect.getsource(__import__("admin").approve_claim)
        assert "db._ph" in src
        assert "validate_path_id" in src


# ── Pinned posts migration ──

class TestPinnedPostsMigration:
    def test_migration_file_exists(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "038_pinned_posts.sql"
        assert p.exists()

    def test_adds_is_pinned_column(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "038_pinned_posts.sql"
        sql = p.read_text(encoding="utf-8")
        assert "is_pinned" in sql
        assert "BOOLEAN" in sql

    def test_creates_index(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "038_pinned_posts.sql"
        sql = p.read_text(encoding="utf-8")
        assert "idx_posts_pinned" in sql


# ── Pin post to profile ──

class TestPinPostToProfile:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/{post_id}/pin-to-profile" in paths

    def test_endpoint_is_post(self):
        from social import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "POST" in methods.get("/api/posts/{post_id}/pin-to-profile", set())

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "require_user" in src

    def test_requires_csrf(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "require_csrf" in src

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "validate_path_id" in src

    def test_rate_limited(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "check_rate" in src

    def test_checks_ownership(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "403" in src
        assert "user_id" in src

    def test_checks_approved(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "approved" in src
        assert "400" in src

    def test_max_pinned_limit(self):
        from social import _MAX_PINNED_POSTS
        assert _MAX_PINNED_POSTS == 3

    def test_toggle_unpin(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "is_pinned" in src
        assert "FALSE" in src

    def test_parameterized(self):
        src = inspect.getsource(__import__("social").pin_post_to_profile)
        assert "db._ph" in src

    def test_is_pinned_in_format_post(self):
        src = inspect.getsource(__import__("social")._format_post)
        assert '"is_pinned"' in src

    def test_user_posts_pinned_first(self):
        src = inspect.getsource(__import__("social").get_user_posts)
        assert "is_pinned" in src
        assert "DESC" in src


# ── Admin user growth ──

class TestAdminUserGrowth:
    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/user-growth" in paths

    def test_requires_pg(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert "_use_pg" in src

    def test_returns_total_users(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert '"total_users"' in src

    def test_returns_growth_rate(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert '"growth_rate_pct"' in src

    def test_returns_daily_signups(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert '"daily_signups"' in src
        assert "DATE(created_at)" in src

    def test_weekly_comparison(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert "signups_this_week" in src
        assert "signups_prev_week" in src

    def test_deactivated_count(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert "deactivated_users" in src
        assert "is_active = FALSE" in src

    def test_growth_rate_calculation(self):
        src = inspect.getsource(__import__("admin").user_growth)
        assert "growth_rate" in src
        assert "round" in src


# ── Hashtag posts endpoint ──

class TestHashtagPosts:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/hashtags/{tag}/posts" in paths

    def test_endpoint_is_get(self):
        from social import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "GET" in methods.get("/api/hashtags/{tag}/posts", set())

    def test_filters_by_hashtag(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "hashtags @>" in src
        assert "jsonb" in src

    def test_sort_options(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "popular" in src
        assert "newest" in src

    def test_block_filter(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "_block_sql" in src

    def test_pagination(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "LIMIT" in src
        assert "OFFSET" in src
        assert '"total"' in src

    def test_returns_tag_name(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert '"tag"' in src

    def test_formats_posts(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "_format_post" in src


# ── Nearby entities endpoint ──

class TestNearbyEntities:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/nearby" in paths

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "validate_path_id" in src

    def test_checks_entity_exists(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "404" in src

    def test_uses_haversine(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "_haversine_km" in src

    def test_radius_filter(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "radius_km" in src

    def test_excludes_self(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "entity_id" in src
        assert "continue" in src

    def test_sorts_by_distance(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "distance_km" in src
        assert "sort" in src

    def test_type_filter(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "type" in src

    def test_handles_no_coordinates(self):
        src = inspect.getsource(__import__("public_api").get_nearby_entities)
        assert "coordinates" in src
        assert "nearby" in src


# ── Admin content stats ──

class TestAdminContentStats:
    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/content-stats" in paths

    def test_requires_pg(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert "_use_pg" in src

    def test_posts_by_type(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert '"posts_by_type"' in src
        assert "post_type" in src

    def test_posts_by_status(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert '"posts_by_status"' in src
        assert "moderation_status" in src

    def test_avg_rating(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert '"avg_review_rating"' in src
        assert "AVG(rating)" in src

    def test_daily_posts(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert '"daily_posts"' in src
        assert "DATE(created_at)" in src

    def test_total_comments(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert '"total_comments"' in src

    def test_parameterized(self):
        src = inspect.getsource(__import__("admin").content_stats)
        assert "INTERVAL" in src


# ── User reviews endpoint ──

class TestUserReviews:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/users/{user_id}/reviews" in paths

    def test_endpoint_is_get(self):
        from social import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "GET" in methods.get("/api/users/{user_id}/reviews", set())

    def test_filters_by_review(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "post_type = 'review'" in src

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "validate_path_id" in src

    def test_block_filter(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "_block_sql" in src

    def test_pagination(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_formats_posts(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "_format_post" in src

    def test_resolves_user_id(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "_resolve_user_id" in src


# ── Unread notification count ──

class TestUnreadNotificationCount:
    def test_endpoint_exists(self):
        from notifications import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/notifications/unread-count" in paths

    def test_endpoint_is_get(self):
        from notifications import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "GET" in methods.get("/api/notifications/unread-count", set())

    def test_requires_auth(self):
        src = inspect.getsource(__import__("notifications").unread_count)
        assert "require_user" in src

    def test_returns_count(self):
        src = inspect.getsource(__import__("notifications").unread_count)
        assert '"unread_count"' in src

    def test_queries_unread(self):
        src = inspect.getsource(__import__("notifications").unread_count)
        assert "is_read = FALSE" in src

    def test_parameterized(self):
        src = inspect.getsource(__import__("notifications").unread_count)
        assert "db._ph" in src


# ── Entity types endpoint ──

class TestEntityTypes:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entity-types" in paths

    def test_returns_types(self):
        src = inspect.getsource(__import__("public_api").entity_types)
        assert '"types"' in src

    def test_returns_counts(self):
        src = inspect.getsource(__import__("public_api").entity_types)
        assert '"count"' in src

    def test_returns_total(self):
        src = inspect.getsource(__import__("public_api").entity_types)
        assert '"total"' in src

    def test_sorted_by_count(self):
        src = inspect.getsource(__import__("public_api").entity_types)
        assert "sorted" in src


# ── Areas endpoint ──

class TestAreas:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/areas" in paths

    def test_returns_areas(self):
        src = inspect.getsource(__import__("public_api").list_areas)
        assert '"areas"' in src

    def test_returns_places(self):
        src = inspect.getsource(__import__("public_api").list_areas)
        assert '"places"' in src

    def test_returns_total(self):
        src = inspect.getsource(__import__("public_api").list_areas)
        assert '"total_places"' in src

    def test_filters_place_type(self):
        src = inspect.getsource(__import__("public_api").list_areas)
        assert 'entity_type="place"' in src


# ── Explore feed ──

class TestExploreFeed:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/feed/explore" in paths

    def test_endpoint_is_get(self):
        from social import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "GET" in methods.get("/api/feed/explore", set())

    def test_excludes_following(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "NOT IN" in src
        assert "follows" in src

    def test_block_filter(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "_block_sql" in src

    def test_ranking_algorithm(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "like_count" in src
        assert "comment_count" in src

    def test_time_window(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "90 days" in src

    def test_pagination(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_formats_posts(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "_format_post" in src


# ── Admin system health ──

class TestAdminSystemHealth:
    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/system-health" in paths

    def test_checks_sqlite(self):
        src = inspect.getsource(__import__("admin").system_health)
        assert "sqlite" in src
        assert "size_mb" in src

    def test_checks_postgres(self):
        src = inspect.getsource(__import__("admin").system_health)
        assert "postgres" in src
        assert "tables" in src

    def test_counts_table_rows(self):
        src = inspect.getsource(__import__("admin").system_health)
        assert "users" in src
        assert "posts" in src
        assert "comments" in src

    def test_active_sessions(self):
        src = inspect.getsource(__import__("admin").system_health)
        assert "active_sessions" in src
        assert "expires_at" in src

    def test_db_size(self):
        src = inspect.getsource(__import__("admin").system_health)
        assert "pg_database_size" in src


# ── Featured entities ──

class TestFeaturedEntitiesMigration:
    def test_migration_file_exists(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "039_featured_entities.sql"
        assert p.exists()

    def test_creates_table(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "039_featured_entities.sql"
        sql = p.read_text(encoding="utf-8")
        assert "featured_entities" in sql
        assert "entity_id" in sql

    def test_unique_entity(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "039_featured_entities.sql"
        sql = p.read_text(encoding="utf-8")
        assert "UNIQUE" in sql


class TestAdminFeatured:
    def test_list_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/featured" in paths

    def test_toggle_endpoint(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/featured/{entity_id}" in paths

    def test_toggle_validates_entity(self):
        src = inspect.getsource(__import__("admin").toggle_featured)
        assert "validate_path_id" in src
        assert "404" in src

    def test_toggle_logic(self):
        src = inspect.getsource(__import__("admin").toggle_featured)
        assert "DELETE" in src
        assert "INSERT" in src

    def test_list_resolves_entities(self):
        src = inspect.getsource(__import__("admin").list_featured)
        assert "get_entity" in src

    def test_sort_order(self):
        src = inspect.getsource(__import__("admin").list_featured)
        assert "sort_order" in src


class TestPublicFeatured:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/featured" in paths

    def test_returns_entities(self):
        src = inspect.getsource(__import__("public_api").get_featured_entities)
        assert '"featured"' in src

    def test_includes_entity_details(self):
        src = inspect.getsource(__import__("public_api").get_featured_entities)
        assert '"name"' in src
        assert '"type"' in src

    def test_limited(self):
        src = inspect.getsource(__import__("public_api").get_featured_entities)
        assert "LIMIT" in src


# ══════════════════════════════════════════════════════════════════════════
# Announcements (migration 040 + admin CRUD + public endpoint)
# ══════════════════════════════════════════════════════════════════════════

class TestAnnouncementsMigration:
    def test_migration_file_exists(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "040_announcements.sql"
        assert p.exists()

    def test_migration_creates_table(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "040_announcements.sql"
        sql = p.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS announcements" in sql

    def test_migration_has_types_check(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "040_announcements.sql"
        sql = p.read_text(encoding="utf-8")
        assert "info" in sql
        assert "warning" in sql
        assert "maintenance" in sql
        assert "update" in sql

    def test_migration_has_active_index(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "040_announcements.sql"
        sql = p.read_text(encoding="utf-8")
        assert "idx_announcements_active" in sql

    def test_migration_has_expiry(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "040_announcements.sql"
        sql = p.read_text(encoding="utf-8")
        assert "expires_at" in sql


class TestAdminAnnouncementsCRUD:
    def test_list_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/announcements" in paths

    def test_create_endpoint_exists(self):
        from admin import router
        methods_paths = [(list(r.methods)[0] if hasattr(r, "methods") else "", r.path)
                        for r in router.routes if hasattr(r, "path")]
        assert ("POST", "/admin/announcements") in methods_paths

    def test_update_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/announcements/{announcement_id}" in paths

    def test_delete_endpoint_exists(self):
        from admin import router
        methods_paths = [(list(r.methods)[0] if hasattr(r, "methods") else "", r.path)
                        for r in router.routes if hasattr(r, "path")]
        assert ("DELETE", "/admin/announcements/{announcement_id}") in methods_paths

    def test_create_validates_type(self):
        from admin import AnnouncementCreate
        import pytest
        with pytest.raises(Exception):
            AnnouncementCreate(title="Test", type="invalid_type")

    def test_create_accepts_valid_types(self):
        from admin import AnnouncementCreate
        for t in ("info", "warning", "maintenance", "update"):
            m = AnnouncementCreate(title="Test", type=t)
            assert m.type == t

    def test_create_title_required(self):
        from admin import AnnouncementCreate
        import pytest
        with pytest.raises(Exception):
            AnnouncementCreate(title="", type="info")

    def test_update_allows_partial(self):
        from admin import AnnouncementUpdate
        m = AnnouncementUpdate(title="New title")
        assert m.title == "New title"
        assert m.content is None
        assert m.type is None

    def test_list_has_pagination(self):
        src = inspect.getsource(__import__("admin").list_announcements)
        assert "LIMIT" in src
        assert "OFFSET" in src
        assert "total" in src

    def test_list_has_active_filter(self):
        src = inspect.getsource(__import__("admin").list_announcements)
        assert "is_active" in src

    def test_update_validates_path_id(self):
        src = inspect.getsource(__import__("admin").update_announcement)
        assert "validate_path_id" in src

    def test_delete_validates_path_id(self):
        src = inspect.getsource(__import__("admin").delete_announcement)
        assert "validate_path_id" in src

    def test_create_uses_parameterized(self):
        src = inspect.getsource(__import__("admin").create_announcement)
        assert "db._ph" in src or "ph" in src


class TestPublicAnnouncements:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/announcements" in paths

    def test_filters_active_only(self):
        src = inspect.getsource(__import__("public_api").list_active_announcements)
        assert "is_active = TRUE" in src

    def test_filters_by_time(self):
        src = inspect.getsource(__import__("public_api").list_active_announcements)
        assert "starts_at" in src
        assert "expires_at" in src

    def test_orders_by_priority(self):
        src = inspect.getsource(__import__("public_api").list_active_announcements)
        assert "priority DESC" in src

    def test_requires_pg(self):
        src = inspect.getsource(__import__("public_api").list_active_announcements)
        assert "_require_pg" in src

    def test_has_limit(self):
        src = inspect.getsource(__import__("public_api").list_active_announcements)
        assert "LIMIT" in src


# ══════════════════════════════════════════════════════════════════════════
# Entity Map Search (bounding box)
# ══════════════════════════════════════════════════════════════════════════

class TestEntityMapSearch:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/map" in paths

    def test_requires_bbox_params(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "north" in src
        assert "south" in src
        assert "east" in src
        assert "west" in src

    def test_validates_north_gt_south(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "north" in src and "south" in src
        assert "400" in src or "must be" in src

    def test_filters_by_coordinates(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "coordinates" in src
        assert "lat" in src
        assert "lng" in src

    def test_supports_type_filter(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "entity_type" in src

    def test_returns_bbox_in_response(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert '"bbox"' in src

    def test_returns_entity_fields(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert '"name"' in src
        assert '"type"' in src
        assert '"coordinates"' in src

    def test_respects_limit(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "limit" in src

    def test_handles_antimeridian(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "west" in src and "east" in src


# ══════════════════════════════════════════════════════════════════════════
# User Engagement Stats
# ══════════════════════════════════════════════════════════════════════════

class TestUserEngagementStats:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/users/{user_id}/engagement" in paths

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "validate_path_id" in src

    def test_requires_pg(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "_require_pg" in src

    def test_checks_user_exists(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "404" in src
        assert "is_active" in src

    def test_returns_post_counts(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "total_posts" in src
        assert "total_reviews" in src

    def test_returns_avg_rating(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "avg_rating" in src

    def test_returns_followers(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "followers" in src

    def test_returns_likes_received(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "total_likes_received" in src or "total_likes" in src

    def test_uses_parameterized_queries(self):
        src = inspect.getsource(__import__("public_api").user_engagement_stats)
        assert "db._ph" in src or "ph" in src


# ══════════════════════════════════════════════════════════════════════════
# Entity Rating Breakdown
# ══════════════════════════════════════════════════════════════════════════

class TestEntityRatingBreakdown:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/rating-breakdown" in paths

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert "validate_path_id" in src

    def test_requires_pg(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert "_require_pg" in src

    def test_returns_breakdown_dict(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert '"breakdown"' in src

    def test_5_star_keys(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert "range(1, 6)" in src

    def test_returns_percentages(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert '"percentages"' in src

    def test_returns_total_and_avg(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert '"total_reviews"' in src
        assert '"avg_rating"' in src

    def test_filters_approved_only(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert "approved" in src

    def test_404_for_missing_entity(self):
        src = inspect.getsource(__import__("public_api").get_entity_rating_breakdown)
        assert "404" in src


# ══════════════════════════════════════════════════════════════════════════
# Entity Trending
# ══════════════════════════════════════════════════════════════════════════

class TestEntityTrending:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/trending" in paths

    def test_requires_pg(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert "_require_pg" in src

    def test_has_days_param(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert "days" in src
        assert "INTERVAL" in src

    def test_has_type_filter(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert "entity_type" in src

    def test_returns_activity_count(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert "activity_count" in src

    def test_returns_entity_details(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert '"name"' in src
        assert '"type"' in src

    def test_respects_limit(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert "limit" in src

    def test_orders_by_activity(self):
        src = inspect.getsource(__import__("public_api").entities_trending)
        assert "ORDER BY activity_count DESC" in src


# ══════════════════════════════════════════════════════════════════════════
# Admin User Detail
# ══════════════════════════════════════════════════════════════════════════

class TestAdminUserDetail:
    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/users/{user_id}" in paths

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "validate_path_id" in src

    def test_returns_user_data(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert '"user"' in src

    def test_returns_post_stats(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "approved" in src
        assert "rejected" in src
        assert "pending" in src

    def test_returns_follow_stats(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert '"following"' in src
        assert '"followers"' in src

    def test_masks_phone(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "_mask" in src

    def test_includes_session_count(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "active_sessions" in src

    def test_404_for_missing_user(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "404" in src


# ══════════════════════════════════════════════════════════════════════════
# Admin Content Search
# ══════════════════════════════════════════════════════════════════════════

class TestAdminContentSearch:
    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/content/search" in paths

    def test_searches_posts(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "ILIKE" in src
        assert "posts" in src.lower()

    def test_searches_comments(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "comments" in src.lower()

    def test_supports_content_type_filter(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "content_type" in src
        assert "post" in src
        assert "comment" in src

    def test_supports_status_filter(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "moderation_status" in src

    def test_supports_post_type_filter(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "post_type" in src
        assert "review" in src

    def test_truncates_content(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "300" in src

    def test_has_pagination(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_uses_escape_like(self):
        src = inspect.getsource(__import__("admin").admin_content_search)
        assert "_escape_like" in src


# ══════════════════════════════════════════════════════════════════════════
# Admin Post Detail
# ══════════════════════════════════════════════════════════════════════════

class TestAdminPostDetail:
    def test_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/posts/{post_id}" in paths

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert "validate_path_id" in src

    def test_returns_post_with_author(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert "author_name" in src

    def test_includes_comments(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert '"comments"' in src

    def test_includes_reports(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert '"reports"' in src
        assert "report_count" in src

    def test_masks_author_phone(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert "_mask" in src

    def test_404_for_missing_post(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert "404" in src

    def test_verified_like_count(self):
        src = inspect.getsource(__import__("admin").admin_post_detail)
        assert "like_count_verified" in src


# ══════════════════════════════════════════════════════════════════════════
# Migration 041: Round-3 indexes
# ══════════════════════════════════════════════════════════════════════════

class TestRound3Indexes:
    def test_migration_file_exists(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "041_round3_indexes.sql"
        assert p.exists()

    def test_rating_breakdown_index(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "041_round3_indexes.sql"
        sql = p.read_text(encoding="utf-8")
        assert "idx_posts_entity_rating" in sql

    def test_trending_index(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "041_round3_indexes.sql"
        sql = p.read_text(encoding="utf-8")
        assert "idx_posts_entity_recent" in sql

    def test_reports_indexes(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "041_round3_indexes.sql"
        sql = p.read_text(encoding="utf-8")
        assert "idx_reports_reporter" in sql
        assert "idx_reports_target" in sql

    def test_announcements_time_index(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "041_round3_indexes.sql"
        sql = p.read_text(encoding="utf-8")
        assert "idx_announcements_active_time" in sql

    def test_all_use_if_not_exists(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "041_round3_indexes.sql"
        sql = p.read_text(encoding="utf-8")
        for line in sql.split("\n"):
            if line.strip().startswith("CREATE INDEX"):
                assert "IF NOT EXISTS" in line


# ══════════════════════════════════════════════════════════════════════════
# Security: all new admin endpoints use admin guard
# ══════════════════════════════════════════════════════════════════════════

class TestRound3SecurityGuards:
    def test_admin_router_has_global_admin_dependency(self):
        import admin
        deps = [d.dependency.__name__ if hasattr(d, 'dependency') and hasattr(d.dependency, '__name__') else str(d)
                for d in (admin.router.dependencies or [])]
        has_admin = any("require_admin" in str(d) for d in deps)
        if not has_admin:
            has_admin = any("admin" in str(d).lower() for d in admin.router.dependencies)
        assert has_admin, "Admin router must have require_admin dependency"

    def test_all_new_endpoints_exist_under_admin_router(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        new_admin_paths = [
            "/admin/announcements",
            "/admin/content/search",
            "/admin/posts/{post_id}",
            "/admin/users/{user_id}",
        ]
        for p in new_admin_paths:
            assert p in paths, f"Missing admin endpoint: {p}"

    def test_public_announcements_not_under_admin(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/announcements" in paths

    def test_all_new_public_endpoints_validate_path_id(self):
        for func_name in ["get_entity_rating_breakdown", "user_engagement_stats"]:
            src = inspect.getsource(getattr(__import__("public_api"), func_name))
            assert "validate_path_id" in src, f"{func_name} missing validate_path_id"

    def test_all_new_admin_endpoints_validate_path_id(self):
        for func_name in ["admin_user_detail", "admin_post_detail",
                          "update_announcement", "delete_announcement"]:
            src = inspect.getsource(getattr(__import__("admin"), func_name))
            assert "validate_path_id" in src, f"{func_name} missing validate_path_id"

    def test_all_new_endpoints_use_parameterized_queries(self):
        for mod_name, func_name in [
            ("admin", "admin_content_search"),
            ("admin", "admin_post_detail"),
            ("admin", "admin_user_detail"),
            ("admin", "create_announcement"),
            ("public_api", "get_entity_rating_breakdown"),
            ("public_api", "entities_trending"),
            ("public_api", "user_engagement_stats"),
        ]:
            src = inspect.getsource(getattr(__import__(mod_name), func_name))
            assert "db._ph" in src or "ph" in src, f"{mod_name}.{func_name} missing parameterized queries"


# ══════════════════════════════════════════════════════════════════════════
# Share Tracking
# ══════════════════════════════════════════════════════════════════════════

class TestShareTracking:
    def test_migration_file_exists(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "042_share_count.sql"
        assert p.exists()

    def test_migration_adds_column(self):
        p = Path(__file__).resolve().parent.parent / "migrations" / "042_share_count.sql"
        sql = p.read_text(encoding="utf-8")
        assert "share_count" in sql
        assert "ALTER TABLE posts" in sql

    def test_endpoint_exists(self):
        from social import router
        methods_paths = [(list(r.methods)[0] if hasattr(r, "methods") else "", r.path)
                        for r in router.routes if hasattr(r, "path")]
        assert ("POST", "/api/posts/{post_id}/share") in methods_paths

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("social").track_share)
        assert "validate_path_id" in src

    def test_increments_count(self):
        src = inspect.getsource(__import__("social").track_share)
        assert "share_count" in src
        assert "+ 1" in src or "+1" in src

    def test_returns_new_count(self):
        src = inspect.getsource(__import__("social").track_share)
        assert '"share_count"' in src

    def test_only_approved_posts(self):
        src = inspect.getsource(__import__("social").track_share)
        assert "approved" in src

    def test_format_post_includes_share_count(self):
        src = inspect.getsource(__import__("social")._format_post)
        assert "share_count" in src

    def test_post_cols_includes_share_count(self):
        from social import _POST_COLS
        assert "share_count" in _POST_COLS


# ══════════════════════════════════════════════════════════════════════════
# Admin Comment List
# ══════════════════════════════════════════════════════════════════════════

class TestAdminCommentList:
    def test_list_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/comments" in paths

    def test_delete_endpoint_exists(self):
        from admin import router
        methods_paths = [(list(r.methods)[0] if hasattr(r, "methods") else "", r.path)
                        for r in router.routes if hasattr(r, "path")]
        assert ("DELETE", "/admin/comments/{comment_id}") in methods_paths

    def test_list_has_search(self):
        src = inspect.getsource(__import__("admin").admin_list_comments)
        assert "ILIKE" in src
        assert "_escape_like" in src

    def test_list_has_post_filter(self):
        src = inspect.getsource(__import__("admin").admin_list_comments)
        assert "post_id" in src

    def test_list_has_pagination(self):
        src = inspect.getsource(__import__("admin").admin_list_comments)
        assert "LIMIT" in src
        assert "OFFSET" in src

    def test_list_includes_author(self):
        src = inspect.getsource(__import__("admin").admin_list_comments)
        assert "author_name" in src

    def test_list_includes_post_info(self):
        src = inspect.getsource(__import__("admin").admin_list_comments)
        assert "post_title" in src

    def test_delete_validates_path_id(self):
        src = inspect.getsource(__import__("admin").admin_delete_comment)
        assert "validate_path_id" in src

    def test_delete_decrements_comment_count(self):
        src = inspect.getsource(__import__("admin").admin_delete_comment)
        assert "comment_count" in src
        assert "GREATEST" in src

    def test_delete_logs_mod_action(self):
        src = inspect.getsource(__import__("admin").admin_delete_comment)
        assert "_log_mod_action" in src


# ══════════════════════════════════════════════════════════════════════════
# Hashtag Browse Listing
# ══════════════════════════════════════════════════════════════════════════

class TestHashtagBrowse:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/hashtags" in paths

    def test_method_is_get(self):
        from social import router
        routes = {r.path: set(r.methods) if hasattr(r, "methods") else set()
                  for r in router.routes if hasattr(r, "path")}
        assert "GET" in routes.get("/api/hashtags", set())

    def test_has_pagination(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "page" in src
        assert "limit" in src
        assert "offset" in src

    def test_has_search_filter(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "search" in src
        assert "LIKE" in src

    def test_uses_escape_like(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "escape_like" in src

    def test_counts_approved_only(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "moderation_status = 'approved'" in src

    def test_returns_total(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert '"total"' in src
        assert '"has_more"' in src

    def test_returns_post_count(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "post_count" in src

    def test_uses_jsonb_array_elements(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "jsonb_array_elements_text" in src

    def test_groups_by_tag(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "GROUP BY tag" in src


# ══════════════════════════════════════════════════════════════════════════
# User Self Stats
# ══════════════════════════════════════════════════════════════════════════

class TestUserSelfStats:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/me/stats" in paths

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert "require_user" in src

    def test_returns_reviews(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert '"reviews"' in src
        assert '"avg_rating"' in src

    def test_returns_questions(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert '"questions"' in src

    def test_returns_followers_following(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert '"followers"' in src
        assert '"following"' in src

    def test_returns_likes_received(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert '"likes_received"' in src

    def test_returns_entities_reviewed(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert '"entities_reviewed"' in src

    def test_returns_reputation(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert '"reputation"' in src

    def test_uses_parameterized_queries(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert "db._ph" in src or "_ph" in src
        assert "f-string" not in src or "{ph}" in src

    def test_uses_asyncio_thread(self):
        src = inspect.getsource(__import__("social").user_stats)
        assert "asyncio.to_thread" in src


# ══════════════════════════════════════════════════════════════════════════
# Post Report Shortcut
# ══════════════════════════════════════════════════════════════════════════

class TestPostReport:
    def test_endpoint_exists(self):
        from social import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/posts/{post_id}/report" in paths

    def test_method_is_post(self):
        from social import router
        routes = {r.path: set(r.methods) if hasattr(r, "methods") else set()
                  for r in router.routes if hasattr(r, "path")}
        assert "POST" in routes.get("/api/posts/{post_id}/report", set())

    def test_requires_auth(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "require_user" in src

    def test_validates_path_id(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "validate_path_id" in src

    def test_has_rate_limit(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "check_rate" in src

    def test_prevents_self_report(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "chính mình" in src or "self" in src.lower()

    def test_prevents_duplicate_report(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "pending" in src

    def test_inserts_to_pg_reports(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "INSERT INTO reports" in src
        assert "target_type" in src

    def test_uses_parameterized_queries(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "db._ph" in src or "_ph" in src

    def test_report_body_model(self):
        from social import ReportPostBody
        assert hasattr(ReportPostBody, "model_fields")
        fields = ReportPostBody.model_fields
        assert "reason" in fields
        assert "detail" in fields


# ══════════════════════════════════════════════════════════════════════════
# Entity Search with Advanced Filters
# ══════════════════════════════════════════════════════════════════════════

class TestEntitySearch:
    def test_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/search" in paths

    def test_method_is_get(self):
        from public_api import router
        routes = {r.path: set(r.methods) if hasattr(r, "methods") else set()
                  for r in router.routes if hasattr(r, "path")}
        assert "GET" in routes.get("/api/entities/search", set())

    def test_has_type_filter(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "entity_type" in src

    def test_has_area_filter(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "area" in src

    def test_has_image_filter(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "has_image" in src

    def test_has_sort_options(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "sort" in src
        assert "relevance" in src
        assert "name" in src
        assert "newest" in src

    def test_has_pagination(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "page" in src
        assert "limit" in src
        assert '"has_more"' in src

    def test_has_rate_limit(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "check_rate" in src

    def test_returns_filters_metadata(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert '"filters"' in src

    def test_has_cache_control(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "Cache-Control" in src


# ══════════════════════════════════════════════════════════════════════════
# Admin CSV Exports
# ══════════════════════════════════════════════════════════════════════════

class TestAdminCSVExports:
    def test_users_export_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/export/users" in paths

    def test_posts_export_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/export/posts" in paths

    def test_users_export_is_get(self):
        from admin import router
        routes = {r.path: set(r.methods) if hasattr(r, "methods") else set()
                  for r in router.routes if hasattr(r, "path")}
        assert "GET" in routes.get("/admin/export/users", set())

    def test_posts_export_is_get(self):
        from admin import router
        routes = {r.path: set(r.methods) if hasattr(r, "methods") else set()
                  for r in router.routes if hasattr(r, "path")}
        assert "GET" in routes.get("/admin/export/posts", set())

    def test_users_export_csv_format(self):
        src = inspect.getsource(__import__("admin").export_users_csv)
        assert "text/csv" in src
        assert "filename=users.csv" in src

    def test_posts_export_csv_format(self):
        src = inspect.getsource(__import__("admin").export_posts_csv)
        assert "text/csv" in src
        assert "filename=posts.csv" in src

    def test_users_export_masks_phone(self):
        src = inspect.getsource(__import__("admin").export_users_csv)
        assert "_mask" in src

    def test_users_export_includes_stats(self):
        src = inspect.getsource(__import__("admin").export_users_csv)
        assert "post_count" in src
        assert "follower_count" in src

    def test_posts_export_has_status_filter(self):
        src = inspect.getsource(__import__("admin").export_posts_csv)
        assert "moderation_status" in src

    def test_posts_export_has_days_filter(self):
        src = inspect.getsource(__import__("admin").export_posts_csv)
        assert "days" in src
        assert "INTERVAL" in src

    def test_users_export_streaming(self):
        src = inspect.getsource(__import__("admin").export_users_csv)
        assert "StreamingResponse" in src

    def test_posts_export_streaming(self):
        src = inspect.getsource(__import__("admin").export_posts_csv)
        assert "StreamingResponse" in src


# ══════════════════════════════════════════════════════════════════════════
# Round-4 Security Guards
# ══════════════════════════════════════════════════════════════════════════

class TestRound4SecurityGuards:
    def test_all_new_social_write_endpoints_have_rate_limit(self):
        src = inspect.getsource(__import__("social"))
        lines = src.split("\n")
        for i, line in enumerate(lines):
            if "async def report_post(" in line or "async def list_hashtags(" in line:
                block = "\n".join(lines[i:i + 10])
                if "async def report_post(" in line:
                    assert "check_rate" in block, f"social.py write endpoint missing rate limit: {line.strip()}"

    def test_entity_search_has_rate_limit(self):
        src = inspect.getsource(__import__("public_api").entity_search)
        assert "check_rate" in src

    def test_post_report_uses_parameterized_queries(self):
        src = inspect.getsource(__import__("social").report_post)
        assert "{ph}" in src
        assert "INSERT" in src

    def test_admin_exports_under_admin_router(self):
        from admin import router
        admin_paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/export/users" in admin_paths
        assert "/admin/export/posts" in admin_paths

    def test_hashtag_browse_no_auth_required(self):
        src = inspect.getsource(__import__("social").list_hashtags)
        assert "require_user" not in src
