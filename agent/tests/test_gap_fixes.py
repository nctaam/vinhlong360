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


class TestFollowCountLimit:
    """Follow toggle enforces maximum follow count per type."""

    def test_follow_has_count_check(self):
        src = inspect.getsource(__import__("notifications").toggle_follow)
        assert "COUNT(*)" in src
        assert "cap" in src or "_MAX_FOLLOW" in src

    def test_follow_user_cap_500(self):
        src = inspect.getsource(__import__("notifications").toggle_follow)
        assert "_MAX_FOLLOW_USER" in src
        assert "500" in src

    def test_follow_entity_cap_1000(self):
        src = inspect.getsource(__import__("notifications").toggle_follow)
        assert "_MAX_FOLLOW_ENTITY" in src
        assert "1000" in src

    def test_follow_cap_raises_400(self):
        src = inspect.getsource(__import__("notifications").toggle_follow)
        assert "giới hạn follow" in src


class TestClearAllNotifications:
    """DELETE /api/notifications clears all user notifications."""

    def test_endpoint_exists(self):
        src = inspect.getsource(__import__("notifications"))
        assert "clear_all_notifications" in src

    def test_deletes_all_user_notifications(self):
        src = inspect.getsource(__import__("notifications").clear_all_notifications)
        assert "DELETE FROM notifications" in src
        assert "user_id" in src

    def test_returns_deleted_count(self):
        src = inspect.getsource(__import__("notifications").clear_all_notifications)
        assert '"deleted"' in src

    def test_has_rate_limit(self):
        src = inspect.getsource(__import__("notifications").clear_all_notifications)
        assert "check_rate" in src

    def test_requires_auth_and_csrf(self):
        src = inspect.getsource(__import__("notifications").clear_all_notifications)
        assert "require_user" in src
        assert "require_csrf" in src


class TestViewerMutedInProfile:
    """get_user_profile returns is_muted in viewer_relationship."""

    def test_profile_queries_user_mutes(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert "user_mutes" in src
        assert "muted_id" in src

    def test_profile_has_viewer_muted_var(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert "viewer_muted" in src

    def test_profile_returns_is_muted(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        assert '"is_muted"' in src
        assert "viewer_muted" in src

    def test_viewer_relationship_includes_muted(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        idx = src.find("viewer_relationship")
        block = src[idx:idx+200]
        assert "is_muted" in block

    def test_blocked_return_has_12_values(self):
        src = inspect.getsource(__import__("social").get_user_profile)
        idx = src.find('"blocked"')
        block = src[idx:idx+200]
        assert "False" in block


class TestAdminUserDetailActivity:
    """admin_user_detail returns last_login and last_post_at."""

    def test_queries_login_history(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "login_history" in src
        assert "success = TRUE" in src

    def test_returns_last_login(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert '"last_login"' in src

    def test_queries_last_post(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert "ORDER BY created_at DESC LIMIT 1" in src

    def test_returns_last_post_at(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        assert '"last_post_at"' in src

    def test_login_history_handles_missing_table(self):
        src = inspect.getsource(__import__("admin").admin_user_detail)
        idx = src.find("login_history")
        pre = src[max(0, idx-100):idx]
        assert "try" in pre or "except" in pre


class TestDeleteCommentAdminPermission:
    """Admin/moderator can delete any comment, not just own."""

    def test_admin_can_delete_comment(self):
        src = inspect.getsource(__import__("social").delete_comment)
        assert 'role' in src
        assert 'admin' in src
        assert 'moderator' in src

    def test_child_replies_deleted(self):
        src = inspect.getsource(__import__("social").delete_comment)
        assert "parent_id" in src


class TestReactionEnrichmentComprehensive:
    """All post-returning endpoints call _enrich_reactions."""

    def test_get_post_enriches_reactions(self):
        src = inspect.getsource(__import__("social").get_post)
        assert "_enrich_reactions" in src

    def test_hashtag_posts_enriches_reactions(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "_enrich_reactions" in src

    def test_related_posts_enriches_reactions(self):
        src = inspect.getsource(__import__("social").related_posts)
        assert "_enrich_reactions" in src

    def test_user_posts_enriches_reactions(self):
        src = inspect.getsource(__import__("social").get_user_posts)
        assert "_enrich_reactions" in src

    def test_user_reviews_enriches_reactions(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "_enrich_reactions" in src

    def test_collection_items_enriches_reactions(self):
        src = inspect.getsource(__import__("social").get_collection_items)
        assert "_enrich_reactions" in src

    def test_hashtag_posts_enriches_user_status(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "_enrich_user_status" in src


class TestAdminErrorMessagesVietnamese:
    """All user-facing admin error messages are in Vietnamese."""

    def test_no_english_entity_not_found(self):
        src = inspect.getsource(__import__("admin"))
        assert '"Entity not found"' not in src

    def test_no_english_itinerary_not_found(self):
        src = inspect.getsource(__import__("admin"))
        assert '"Itinerary not found"' not in src

    def test_no_english_requires_postgres(self):
        src = inspect.getsource(__import__("admin"))
        assert '"Requires Postgres"' not in src


class TestBlockedMutedPagination:
    """blocked-users and muted-users endpoints have proper pagination."""

    def test_blocked_users_has_page_param(self):
        src = inspect.getsource(__import__("notifications").list_blocked_users)
        assert "page" in src
        assert "limit" in src
        assert "offset" in src

    def test_blocked_users_returns_total(self):
        src = inspect.getsource(__import__("notifications").list_blocked_users)
        assert '"total"' in src
        assert '"has_more"' in src

    def test_muted_users_has_page_param(self):
        src = inspect.getsource(__import__("notifications").list_muted_users)
        assert "page" in src
        assert "limit" in src
        assert "offset" in src

    def test_muted_users_returns_total(self):
        src = inspect.getsource(__import__("notifications").list_muted_users)
        assert '"total"' in src
        assert '"has_more"' in src

    def test_blocked_users_count_query(self):
        src = inspect.getsource(__import__("notifications").list_blocked_users)
        assert "COUNT(*)" in src

    def test_muted_users_count_query(self):
        src = inspect.getsource(__import__("notifications").list_muted_users)
        assert "COUNT(*)" in src


class TestBlockEnforcementOnInteractions:
    """Like, comment-like, and reaction check blocks before acting."""

    def test_toggle_like_checks_blocks(self):
        src = inspect.getsource(__import__("social").toggle_like)
        assert "blocks" in src
        assert "blocker_id" in src

    def test_toggle_like_rejects_blocked(self):
        src = inspect.getsource(__import__("social").toggle_like)
        assert "Không thể thao tác với người dùng đã chặn" in src

    def test_comment_like_checks_blocks(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "blocks" in src
        assert "blocker_id" in src

    def test_comment_like_rejects_blocked(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "Không thể thao tác với người dùng đã chặn" in src

    def test_reaction_checks_blocks(self):
        src = inspect.getsource(__import__("social").toggle_reaction)
        assert "blocks" in src
        assert "blocker_id" in src

    def test_reaction_rejects_blocked(self):
        src = inspect.getsource(__import__("social").toggle_reaction)
        assert "Không thể thao tác với người dùng đã chặn" in src

    def test_block_check_bidirectional(self):
        src = inspect.getsource(__import__("social").toggle_like)
        assert src.count("blocker_id") >= 2
        assert src.count("blocked_id") >= 2


class TestBookmarksTotalCount:
    """get_my_bookmarks returns total count and enriches reactions."""

    def test_bookmarks_has_total(self):
        src = inspect.getsource(__import__("social").get_my_bookmarks)
        assert '"total"' in src
        assert "COUNT(*)" in src

    def test_bookmarks_enriches_reactions(self):
        src = inspect.getsource(__import__("social").get_my_bookmarks)
        assert "_enrich_reactions" in src

    def test_bookmarks_accurate_has_more(self):
        src = inspect.getsource(__import__("social").get_my_bookmarks)
        assert "offset + limit < total" in src


class TestHiddenPostsTotalCount:
    """list_hidden_posts returns total count."""

    def test_hidden_posts_has_total(self):
        src = inspect.getsource(__import__("social").list_hidden_posts)
        assert '"total"' in src
        assert "COUNT(*)" in src

    def test_hidden_posts_accurate_has_more(self):
        src = inspect.getsource(__import__("social").list_hidden_posts)
        assert "offset + limit < total" in src


class TestLikesTableName:
    """All code uses 'likes' table (not 'post_likes' which doesn't exist)."""

    def test_admin_engagement_uses_likes(self):
        src = inspect.getsource(__import__("admin").user_engagement_stats)
        assert "post_likes" not in src
        assert "FROM likes" in src

    def test_auth_export_uses_likes(self):
        src = inspect.getsource(__import__("auth").export_user_data)
        assert "post_likes" not in src
        assert "FROM likes" in src

    def test_admin_module_no_post_likes(self):
        src = inspect.getsource(__import__("admin"))
        assert "post_likes" not in src


class TestFollowingEndpointTotal:
    """GET /following returns total count."""

    def test_following_has_total(self):
        src = inspect.getsource(__import__("notifications").get_following)
        assert '"total"' in src
        assert "COUNT(*)" in src

    def test_following_accurate_has_more(self):
        src = inspect.getsource(__import__("notifications").get_following)
        assert "offset + limit < total" in src


# ── Post likers block filter ──


class TestPostLikersBlockFilter:
    """get_post_likers() must filter blocked users from likers list."""

    def test_likers_has_request_param(self):
        src = inspect.getsource(__import__("social").get_post_likers)
        assert "request: Request" in src

    def test_likers_calls_get_current_user(self):
        src = inspect.getsource(__import__("social").get_post_likers)
        assert "get_current_user(request)" in src

    def test_likers_applies_block_sql(self):
        src = inspect.getsource(__import__("social").get_post_likers)
        assert "_block_sql(user" in src

    def test_likers_block_clause_in_query(self):
        src = inspect.getsource(__import__("social").get_post_likers)
        assert "{bc}" in src


# ── i18n: no English error messages in user-facing endpoints ──


class TestI18nNotifications:
    """notification_stream must use Vietnamese error messages."""

    def test_no_english_token_required(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "Token required" not in src

    def test_no_english_invalid_token(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "Invalid token" not in src

    def test_has_vietnamese_token_messages(self):
        src = inspect.getsource(__import__("notifications").notification_stream)
        assert "token xác thực" in src.lower() or "token không hợp lệ" in src.lower()


class TestI18nPublicApi:
    """public_api map search must use Vietnamese error messages."""

    def test_no_english_north_south(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "north must be" not in src

    def test_has_vietnamese_north_south(self):
        src = inspect.getsource(__import__("public_api").entities_map_search)
        assert "north phải lớn hơn south" in src.lower() or "giá trị north" in src.lower()


class TestI18nAdmin:
    """Admin endpoints must use Vietnamese error messages."""

    def test_no_english_rate_limit(self):
        src = inspect.getsource(__import__("admin").require_admin)
        assert "Rate limit exceeded" not in src

    def test_no_english_invalid_credentials(self):
        src = inspect.getsource(__import__("admin").require_admin)
        assert "Invalid admin credentials" not in src

    def test_no_english_site_settings(self):
        from pathlib import Path
        admin_src = Path(AGENT_DIR / "admin.py").read_text(encoding="utf-8")
        assert "Site settings require PostgreSQL" not in admin_src

    def test_no_english_post_not_found(self):
        from pathlib import Path
        admin_src = Path(AGENT_DIR / "admin.py").read_text(encoding="utf-8")
        assert '"Post not found"' not in admin_src

    def test_no_english_suggestion_not_found(self):
        from pathlib import Path
        admin_src = Path(AGENT_DIR / "admin.py").read_text(encoding="utf-8")
        assert '"Suggestion not found"' not in admin_src

    def test_no_english_relationship_not_found(self):
        from pathlib import Path
        admin_src = Path(AGENT_DIR / "admin.py").read_text(encoding="utf-8")
        assert '"Relationship not found"' not in admin_src

    def test_no_english_requires_postgresql(self):
        from pathlib import Path
        admin_src = Path(AGENT_DIR / "admin.py").read_text(encoding="utf-8")
        assert '"Requires PostgreSQL"' not in admin_src


# ── Admin site-settings input validation ──


class TestSiteSettingsValidation:
    """Admin site-settings endpoints must validate key/category params."""

    def test_setting_key_regex_exists(self):
        from pathlib import Path
        admin_src = Path(AGENT_DIR / "admin.py").read_text(encoding="utf-8")
        assert "_SETTING_KEY_RE" in admin_src

    def test_update_setting_validates_key(self):
        src = inspect.getsource(__import__("admin").admin_update_setting)
        assert "_SETTING_KEY_RE" in src

    def test_get_category_validates(self):
        src = inspect.getsource(__import__("admin").admin_get_settings_by_category)
        assert "_SETTING_KEY_RE" in src

    def test_reset_category_validates(self):
        src = inspect.getsource(__import__("admin").admin_reset_category)
        assert "_SETTING_KEY_RE" in src


# ── Pagination accuracy: total count + offset-based has_more ──


class TestPaginationAccuracy:
    """All paginated endpoints must use total COUNT for accurate has_more."""

    def test_user_posts_has_total(self):
        src = inspect.getsource(__import__("social").get_user_posts)
        assert "offset + limit < total" in src
        assert '"total"' in src or "'total'" in src

    def test_user_reviews_has_total(self):
        src = inspect.getsource(__import__("social").get_user_reviews)
        assert "offset + limit < total" in src

    def test_explore_feed_has_total(self):
        src = inspect.getsource(__import__("social").explore_feed)
        assert "offset + limit < total" in src

    def test_list_following_has_total(self):
        src = inspect.getsource(__import__("social").list_following_users)
        assert "offset + limit < total" in src

    def test_list_followers_has_total(self):
        src = inspect.getsource(__import__("social").list_followers)
        assert "offset + limit < total" in src

    def test_search_users_has_total(self):
        src = inspect.getsource(__import__("social").search_users)
        assert "offset + limit < total" in src

    def test_list_drafts_has_total(self):
        src = inspect.getsource(__import__("social").list_drafts)
        assert "offset + limit < total" in src

    def test_list_scheduled_has_total(self):
        src = inspect.getsource(__import__("social").list_scheduled)
        assert "offset + limit < total" in src

    def test_collection_items_has_total(self):
        src = inspect.getsource(__import__("social").get_collection_items)
        assert "offset + limit < total" in src

    def test_no_len_equals_limit_pattern(self):
        """No endpoint should use len(results) == limit for has_more."""
        from pathlib import Path
        src = Path(AGENT_DIR / "social.py").read_text(encoding="utf-8")
        occurrences = src.count('len(posts) == limit') + src.count('len(users) == limit') + \
                      src.count('len(drafts) == limit') + src.count('len(scheduled) == limit')
        assert occurrences == 0, f"Found {occurrences} inaccurate has_more patterns"


# ── Hashtag posts has_more accuracy ──


class TestHashtagPostsHasMore:
    """hashtag_posts() must use total count for accurate has_more."""

    def test_has_total_count_query(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "COUNT(*)" in src

    def test_uses_total_for_has_more(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert "offset + limit < total" in src

    def test_does_not_use_len_for_has_more(self):
        src = inspect.getsource(__import__("social").hashtag_posts)
        assert 'len(posts) == limit' not in src


# ── User status enrichment completeness ──


class TestUserStatusEnrichment:
    """related_posts, collection_items, hidden_posts must enrich user status."""

    def test_related_posts_enriches_user_status(self):
        src = inspect.getsource(__import__("social").related_posts)
        assert "_enrich_user_status" in src

    def test_collection_items_enriches_user_status(self):
        src = inspect.getsource(__import__("social").get_collection_items)
        assert "_enrich_user_status" in src

    def test_hidden_posts_enriches_user_status(self):
        src = inspect.getsource(__import__("social").list_hidden_posts)
        assert "_enrich_user_status" in src

    def test_hidden_posts_enriches_reactions(self):
        src = inspect.getsource(__import__("social").list_hidden_posts)
        assert "_enrich_reactions" in src


# ── Notification type mapping completeness ──


class TestNotificationTypeMappings:
    """All notification types used in callers must be mapped to preferences."""

    def test_event_reminder_maps_to_system(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert _NOTIF_TYPE_TO_PREF["event_reminder"] == "pref_system"

    def test_moderation_mapped(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "moderation" in _NOTIF_TYPE_TO_PREF

    def test_repost_always_notifies(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "repost" not in _NOTIF_TYPE_TO_PREF

    def test_entity_post_always_notifies(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "entity_post" not in _NOTIF_TYPE_TO_PREF

    def test_social_mapped(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "social" in _NOTIF_TYPE_TO_PREF

    def test_comment_like_mapped(self):
        from notifications import _NOTIF_TYPE_TO_PREF
        assert "comment_like" in _NOTIF_TYPE_TO_PREF


# ── SEO aggregateRating dedup ──


class TestAggregateRatingDedup:
    """Second aggregateRating block must not overwrite the first (UGC-based)."""

    def test_fallback_guarded_by_not_in_ld(self):
        src = inspect.getsource(__import__("seo").build_entity_jsonld)
        assert '"aggregateRating" not in ld' in src

    def test_fallback_uses_ratingCount_not_reviewCount(self):
        src = inspect.getsource(__import__("seo").build_entity_jsonld)
        lines = src.split("\n")
        fallback_block = False
        for line in lines:
            if '"aggregateRating" not in ld' in line:
                fallback_block = True
            if fallback_block and "reviewCount" in line:
                pytest.fail("Fallback aggregateRating should use ratingCount, not reviewCount")
            if fallback_block and "ratingCount" in line:
                break

    def test_ugc_rating_block_still_exists(self):
        src = inspect.getsource(__import__("seo").build_entity_jsonld)
        assert "avg_rating" in src
        assert "rating_count" in src


# ── SEO type mappings ──


class TestSeoTypeMappings:
    """TYPE_SCHEMA should cover all common entity types."""

    def test_artisan_mapped(self):
        from seo import TYPE_SCHEMA
        assert "artisan" in TYPE_SCHEMA

    def test_craft_mapped(self):
        from seo import TYPE_SCHEMA
        assert "craft" in TYPE_SCHEMA

    def test_market_mapped(self):
        from seo import TYPE_SCHEMA
        assert "market" in TYPE_SCHEMA

    def test_festival_mapped(self):
        from seo import TYPE_SCHEMA
        assert "festival" in TYPE_SCHEMA

    def test_all_map_to_valid_schema_types(self):
        from seo import TYPE_SCHEMA
        valid = {"LodgingBusiness", "TouristAttraction", "CafeOrCoffeeShop",
                 "LocalBusiness", "Recipe", "Product", "Event", "CivicStructure",
                 "LandmarkOrHistoricalBuilding", "TouristTrip", "Organization",
                 "Person", "Place", "Restaurant", "Thing"}
        for etype, schema in TYPE_SCHEMA.items():
            assert schema in valid, f"{etype} maps to unknown schema type {schema}"


# ── Scheduler thread safety ──


class TestSchedulerThreadSafety:
    """start_scheduler must use a lock to prevent duplicate threads."""

    def test_scheduler_lock_exists(self):
        import scheduler
        assert hasattr(scheduler, "_scheduler_lock")

    def test_start_scheduler_uses_lock(self):
        src = inspect.getsource(__import__("scheduler").start_scheduler)
        assert "_scheduler_lock" in src


# ── Phone validation in all auth models ──


class TestPhoneValidationConsistency:
    """All auth models that accept phone must validate VN format, not just normalize."""

    def test_otp_verify_validates_phone(self):
        src = inspect.getsource(__import__("auth").OTPVerify)
        assert "VN_PHONE_RE" in src

    def test_password_login_validates_phone(self):
        src = inspect.getsource(__import__("auth").PasswordLogin)
        assert "VN_PHONE_RE" in src

    def test_reset_password_otp_validates_phone(self):
        src = inspect.getsource(__import__("auth").ResetPasswordOTP)
        assert "VN_PHONE_RE" in src

    def test_otp_request_validates_phone(self):
        src = inspect.getsource(__import__("auth").OTPRequest)
        assert "VN_PHONE_RE" in src

    def test_otp_verify_rejects_invalid_phone(self):
        from auth import OTPVerify
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            OTPVerify(phone="00000", code="123456")

    def test_password_login_rejects_invalid_phone(self):
        from auth import PasswordLogin
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            PasswordLogin(phone="invalid", password="Test1234")


# ── validate_path_id on session and relationship endpoints ──


class TestPathIdValidation:
    """All path params and entity IDs must go through validate_path_id."""

    def test_revoke_session_validates_id(self):
        src = inspect.getsource(__import__("auth").revoke_session)
        assert "validate_path_id" in src

    def test_add_relationship_validates_ids(self):
        src = inspect.getsource(__import__("admin").add_relationship)
        assert "validate_path_id" in src
        assert "from_id" in src
        assert "to_id" in src

    def test_add_relationships_bulk_validates_from_id(self):
        src = inspect.getsource(__import__("admin").add_relationships_bulk)
        assert "validate_path_id" in src

    def test_admin_backup_error_is_vietnamese(self):
        src = inspect.getsource(__import__("admin").trigger_backup)
        assert "backup_data.py not found" not in src


# ── Toggle race condition guards (rowcount checks) ──


class TestToggleRowcountGuard:
    """ON CONFLICT DO NOTHING toggles must check rowcount before updating counts or returning state."""

    def test_comment_like_checks_insert_rowcount(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "rowcount" in src

    def test_comment_like_checks_delete_rowcount(self):
        src = inspect.getsource(__import__("social").toggle_comment_like)
        assert "cur" in src and "rowcount" in src

    def test_reaction_checks_insert_rowcount(self):
        src = inspect.getsource(__import__("social").toggle_reaction)
        assert "rowcount" in src

    def test_bookmark_checks_insert_rowcount(self):
        src = inspect.getsource(__import__("social").toggle_bookmark)
        assert "rowcount" in src

    def test_rsvp_checks_insert_rowcount(self):
        src = inspect.getsource(__import__("notifications").toggle_rsvp)
        assert "rowcount" in src


# ── Cache-Control on public endpoints ──


class TestCacheControlCoverage:
    """All public GET endpoints in public_api.py should set Cache-Control."""

    _NO_CACHE_ENDPOINTS: set = set()

    def test_public_get_endpoints_have_cache_control(self):
        import public_api
        import fastapi
        for route in public_api.router.routes:
            if not isinstance(route, fastapi.routing.APIRoute):
                continue
            if "GET" not in route.methods:
                continue
            fn = route.endpoint
            name = fn.__name__
            if name in self._NO_CACHE_ENDPOINTS:
                continue
            src = inspect.getsource(fn)
            assert "Cache-Control" in src, f"{name} missing Cache-Control header"


class TestPrivacyRateLimit:
    """PUT /privacy must have rate limiting."""

    def test_update_privacy_has_rate_limit(self):
        import auth
        src = inspect.getsource(auth.update_privacy)
        assert "check_rate" in src, "update_privacy missing rate limiting"


class TestRelationshipDeleteValidation:
    """DELETE /relationships type param must be bounded."""

    def test_type_param_has_max_length(self):
        import admin
        src = inspect.getsource(admin.delete_relationship)
        assert "max_length" in src, "delete_relationship type param missing max_length"

    def test_from_id_validated(self):
        import admin
        src = inspect.getsource(admin.delete_relationship)
        assert "validate_path_id" in src


class TestWriteEndpointRateLimits:
    """All POST/PUT/DELETE/PATCH endpoints across social, notifications, auth should have rate limiting."""

    _EXEMPT = set()

    def _check_module_ratelimit(self, mod_name):
        import importlib
        import fastapi
        mod = importlib.import_module(mod_name)
        router = getattr(mod, "router")
        missing = []
        for route in router.routes:
            if not isinstance(route, fastapi.routing.APIRoute):
                continue
            methods = route.methods or set()
            if methods & {"POST", "PUT", "DELETE", "PATCH"}:
                fn = route.endpoint
                name = fn.__name__
                if name in self._EXEMPT:
                    continue
                src = inspect.getsource(fn)
                if "check_rate" not in src and "_otp_rate" not in src and "_login_ip_rate" not in src and "_check_phone_ip_rate" not in src and "_otp_verify_ip_rate" not in src:
                    missing.append(name)
        return missing

    def test_social_all_writes_have_ratelimit(self):
        missing = self._check_module_ratelimit("social")
        assert not missing, f"social.py write endpoints missing check_rate: {missing}"

    def test_notifications_all_writes_have_ratelimit(self):
        missing = self._check_module_ratelimit("notifications")
        assert not missing, f"notifications.py write endpoints missing check_rate: {missing}"

    def test_auth_all_writes_have_ratelimit(self):
        missing = self._check_module_ratelimit("auth")
        assert not missing, f"auth.py write endpoints missing check_rate: {missing}"
