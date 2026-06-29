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
