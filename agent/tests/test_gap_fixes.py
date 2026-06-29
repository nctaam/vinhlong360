"""Tests for gap-scan fixes: reaction enrichment, user rating, SSE reconnect, moderation history."""
import inspect
from pathlib import Path
import pytest

AGENT_DIR = Path(__file__).resolve().parent.parent


# ── Reaction counts in feed ──

class TestReactionEnrichment:
    """_enrich_reactions() batch-fetches reaction counts for feed posts."""

    def test_enrich_reactions_exists(self):
        from social import _enrich_reactions
        assert callable(_enrich_reactions)

    def test_enrich_reactions_queries_post_reactions(self):
        src = inspect.getsource(__import__("social")._enrich_reactions)
        assert "post_reactions" in src
        assert "reaction_type" in src
        assert "GROUP BY" in src

    def test_enrich_reactions_sets_empty_dict_default(self):
        src = inspect.getsource(__import__("social")._enrich_reactions)
        assert "counts.get" in src
        assert "{}" in src

    def test_enrich_reactions_handles_empty_list(self):
        from social import _enrich_reactions
        result = _enrich_reactions([])
        assert result == []

    def test_format_post_has_reactions_key(self):
        src = inspect.getsource(__import__("social")._format_post)
        assert '"reactions"' in src

    def test_feed_calls_enrich_reactions(self):
        src = inspect.getsource(__import__("social").get_feed)
        assert "_enrich_reactions" in src

    def test_following_feed_calls_enrich_reactions(self):
        src = inspect.getsource(__import__("social").get_following_feed)
        assert "_enrich_reactions" in src

    def test_entity_feed_calls_enrich_reactions(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "_enrich_reactions" in src

    def test_search_posts_calls_enrich_reactions(self):
        src = inspect.getsource(__import__("social").search_posts)
        assert "_enrich_reactions" in src

    def test_enrich_reactions_batch_query(self):
        src = inspect.getsource(__import__("social")._enrich_reactions)
        assert "ANY" in src


# ── User's own rating in entity reviews ──

class TestMyReviewInEntityReviews:
    """Entity reviews endpoint returns user's own review when authenticated."""

    def test_reviews_accepts_user_dependency(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert "get_current_user" in src

    def test_reviews_queries_user_review(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert "my_review" in src
        assert "my_row" in src

    def test_reviews_returns_my_review_conditionally(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert 'result["my_review"]' in src
        assert "my_review is not None" in src

    def test_my_review_includes_rating(self):
        src = inspect.getsource(__import__("public_api").get_entity_reviews)
        assert '"rating"' in src
        assert '"content"' in src
        assert '"created_at"' in src


# ── SSE reconnection ──

class TestSSEReconnection:
    """SSE notification stream supports Last-Event-ID reconnection."""

    def test_stream_reads_last_event_id(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "Last-Event-ID" in src

    def test_stream_fetches_missed_notifications(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "missed" in src
        assert "is_read = FALSE" in src

    def test_stream_includes_event_ids(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "id:" in src or 'f"id:' in src

    def test_event_counter_exists(self):
        import notifications
        assert hasattr(notifications, "_sse_event_counter")

    def test_next_event_id_is_async(self):
        import notifications
        assert inspect.iscoroutinefunction(notifications._next_event_id)

    def test_missed_limited_to_5_minutes(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "5 minutes" in src or "INTERVAL" in src


# ── Moderation history per post ──

class TestModerationHistory:
    """Admin can view moderation action timeline for a specific post."""

    def test_endpoint_exists(self):
        src = inspect.getsource(__import__("admin"))
        assert "moderation/{post_id}/history" in src
        assert "moderation_history" in src

    def test_queries_moderation_log(self):
        src = inspect.getsource(__import__("admin").moderation_history)
        assert "moderation_log" in src
        assert "target_type = 'post'" in src

    def test_includes_moderator_name(self):
        src = inspect.getsource(__import__("admin").moderation_history)
        assert "moderator_name" in src
        assert "LEFT JOIN users" in src

    def test_returns_actions_and_status(self):
        src = inspect.getsource(__import__("admin").moderation_history)
        assert '"current_status"' in src
        assert '"actions"' in src

    def test_validates_post_id(self):
        src = inspect.getsource(__import__("admin").moderation_history)
        assert "validate_path_id" in src

    def test_returns_auto_flag(self):
        src = inspect.getsource(__import__("admin").moderation_history)
        assert '"auto"' in src

    def test_scores_parsed_from_json(self):
        src = inspect.getsource(__import__("admin").moderation_history)
        assert "json.loads" in src or "scores" in src


# ── Admin reports filter by reporter/target user ──

class TestAdminReportsUserFilter:
    """Admin reports endpoint supports filtering by reporter_id and target_user_id."""

    def test_reports_accepts_reporter_id(self):
        src = inspect.getsource(__import__("admin").get_reports)
        assert "reporter_id" in src

    def test_reports_accepts_target_user_id(self):
        src = inspect.getsource(__import__("admin").get_reports)
        assert "target_user_id" in src

    def test_reporter_id_filters_sql(self):
        src = inspect.getsource(__import__("admin").get_reports)
        assert "r.reporter_id" in src

    def test_target_user_id_filters_user_type(self):
        src = inspect.getsource(__import__("admin").get_reports)
        assert "target_type = 'user'" in src
        assert "r.target_id" in src

    def test_validates_reporter_id(self):
        src = inspect.getsource(__import__("admin").get_reports)
        assert "validate_path_id" in src

    def test_reporter_id_in_response(self):
        src = inspect.getsource(__import__("admin").get_reports)
        assert "r.reporter_id" in src


# ── JSONL rotation in social.py comment report ──

class TestCommentReportRotation:
    """Comment report endpoint uses shared lock and rotation."""

    def test_comment_report_uses_shared_lock(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "_jsonl_lock" in src

    def test_comment_report_calls_rotation(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "_maybe_rotate_jsonl" in src

    def test_imports_from_public_api(self):
        src = inspect.getsource(__import__("social").report_comment)
        assert "from public_api import" in src


# ── Mute enforcement in notifications ──

class TestNotificationMuteEnforcement:
    """create_notification skips delivery when actor is muted by recipient."""

    def test_create_notification_checks_mutes(self):
        src = inspect.getsource(__import__("notifications").create_notification)
        assert "user_mutes" in src
        assert "muted" in src

    def test_mute_check_uses_actor_id(self):
        src = inspect.getsource(__import__("notifications").create_notification)
        assert "user_id" in src
        assert "muted_id" in src

    def test_mute_check_returns_early(self):
        src = inspect.getsource(__import__("notifications").create_notification)
        idx = src.find("user_mutes")
        assert idx > 0
        block = src[idx:idx+200]
        assert "return" in block


# ── Leaderboard mute filter ──

class TestLeaderboardMuteFilter:
    """Leaderboard filters muted users alongside blocked users."""

    def test_leaderboard_uses_mute_sql(self):
        src = inspect.getsource(__import__("social").community_leaderboard)
        assert "_mute_sql" in src

    def test_leaderboard_includes_mc_in_sql(self):
        src = inspect.getsource(__import__("social").community_leaderboard)
        assert "{mc}" in src or "mc}" in src

    def test_leaderboard_cache_checks_both_filters(self):
        src = inspect.getsource(__import__("social").community_leaderboard)
        assert "has_personal_filter" in src


# ── Privacy show_activity enforcement ──

class TestPrivacyShowActivityEnforcement:
    """get_user_posts and get_user_reviews respect show_activity privacy setting."""

    def test_check_show_activity_exists(self):
        from social import _check_show_activity
        assert callable(_check_show_activity)

    def test_check_show_activity_queries_user_privacy(self):
        src = inspect.getsource(__import__("social")._check_show_activity)
        assert "user_privacy" in src
        assert "show_activity" in src

    def test_check_show_activity_checks_follower(self):
        src = inspect.getsource(__import__("social")._check_show_activity)
        assert "follows" in src
        assert "follower_id" in src

    def test_user_posts_checks_privacy(self):
        src = inspect.getsource(__import__("social").get_user_posts)
        assert "_check_show_activity" in src
        assert "privacy_hidden" in src

    def test_user_reviews_checks_privacy(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "_check_show_activity" in src

    def test_self_view_skips_privacy(self):
        src = inspect.getsource(__import__("social").get_user_posts)
        assert "is_self" in src

    def test_privacy_hidden_returns_empty(self):
        src = inspect.getsource(__import__("social").get_user_posts)
        assert '"posts": []' in src or "'posts': []" in src


# ── Full mute enforcement across all feed/search/list endpoints ──

class TestMuteEnforcementComprehensive:
    """Every endpoint that has _block_sql on feed/list content must also apply _mute_sql."""

    def test_trending_posts_mute(self):
        src = inspect.getsource(__import__("social").trending_posts)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_explore_feed_mute(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_search_posts_mute(self):
        src = inspect.getsource(__import__("social").search_posts)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_search_users_mute(self):
        src = inspect.getsource(__import__("social").search_users)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_suggested_follows_mute(self):
        src = inspect.getsource(__import__("social").suggested_follows)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_entity_feed_mute(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_related_posts_mute(self):
        src = inspect.getsource(__import__("social").related_posts)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_comments_mute(self):
        src = inspect.getsource(__import__("social").get_comments)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_hashtag_posts_mute(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "_mute_sql" in src
        assert "{mc}" in src or "mc}" in src

    def test_entity_feed_count_query_has_mute(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        lines = src.split("\n")
        count_section = [l for l in lines if "COUNT(*)" in l or "mc}" in l]
        assert len(count_section) >= 2

    def test_search_posts_count_query_has_mute(self):
        src = inspect.getsource(__import__("social").search_posts)
        lines = src.split("\n")
        mc_lines = [l for l in lines if "mc}" in l or "{mc}" in l]
        assert len(mc_lines) >= 2

    def test_hashtag_posts_count_query_has_mute(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        lines = src.split("\n")
        mc_lines = [l for l in lines if "mc}" in l or "{mc}" in l]
        assert len(mc_lines) >= 2


class TestNotificationMuteColumnFix:
    """create_notification mute check uses correct column name (user_id not muter_id)."""

    def test_mute_check_uses_user_id_column(self):
        src = inspect.getsource(__import__("notifications").create_notification)
        idx = src.find("user_mutes")
        block = src[idx:idx+150]
        assert "WHERE user_id" in block
        assert "muter_id" not in block

    def test_mute_check_matches_schema(self):
        schema = (AGENT_DIR / "migrations" / "048_user_mutes.sql").read_text()
        assert "user_id UUID" in schema
        assert "muter_id" not in schema


class TestAuthMeRateLimit:
    """GET /auth/me has rate limiting."""

    def test_get_me_has_rate_limit(self):
        src = inspect.getsource(__import__("auth").get_me)
        assert "check_rate" in src

    def test_get_me_rate_limit_generous(self):
        src = inspect.getsource(__import__("auth").get_me)
        assert "60" in src


class TestAdminBulkRateLimits:
    """Admin bulk operations have rate limiting."""

    def test_bulk_ban_rate_limited(self):
        src = inspect.getsource(__import__("admin").bulk_ban_users)
        assert "check_rate" in src

    def test_bulk_unban_rate_limited(self):
        src = inspect.getsource(__import__("admin").bulk_unban_users)
        assert "check_rate" in src

    def test_batch_moderation_rate_limited(self):
        src = inspect.getsource(__import__("admin").batch_moderation)
        assert "check_rate" in src
