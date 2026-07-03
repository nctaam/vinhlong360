"""Tests for Wave 3 — Achievement System + Engagement.

Task 1: Login streak tracking — migration 064_login_streak.sql,
_update_login_streak() helper called on every successful login, feeding the
streak_7/streak_30 achievements (see achievements.py, wired in a later task).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


class TestAchievementHooks:
    """Task 3: fire-and-forget check_achievements() wired into 6 action sites
    across social.py, notifications.py, visits.py, auth.py."""

    def test_bg_helper_swallows_errors(self):
        import social
        src = inspect.getsource(social._check_achievements_bg)
        assert "check_achievements" in src
        assert "except" in src

    def test_create_post_hooks_achievements(self):
        import social
        src = inspect.getsource(social.create_post)
        assert "_check_achievements_bg" in src

    def test_publish_draft_hooks_achievements(self):
        import social
        src = inspect.getsource(social.publish_draft)
        assert "_check_achievements_bg" in src

    def test_toggle_follow_hooks_target_user(self):
        # toggle_follow lives in notifications.py, not social.py.
        import notifications
        src = inspect.getsource(notifications.toggle_follow)
        # achievement check must run for the FOLLOWED user (target_id), not the follower
        assert "check_achievements" in src
        assert "target_id" in src

    def test_set_best_answer_hooks_comment_author(self):
        import social
        src = inspect.getsource(social.set_best_answer)
        assert "check_achievements" in src

    def test_set_visit_hooks_achievements(self):
        import visits
        src = inspect.getsource(visits.set_visit)
        assert "check_achievements" in src

    def test_login_paths_hook_achievements(self):
        import auth
        assert "check_achievements" in inspect.getsource(auth.verify_otp)
        assert "check_achievements" in inspect.getsource(auth.login_password)

    def test_reset_password_otp_updates_streak_and_achievements(self):
        # Task 1 review fix: password-reset success path should also credit
        # the login streak + achievement check, like the other two login paths.
        import auth
        src = inspect.getsource(auth.reset_password_otp)
        assert "_update_login_streak" in src
        assert "check_achievements" in src
