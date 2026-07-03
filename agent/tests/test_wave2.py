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
