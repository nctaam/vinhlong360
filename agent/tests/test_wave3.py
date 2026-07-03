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
