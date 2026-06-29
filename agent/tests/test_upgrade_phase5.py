"""Tests for Phase 5 upgrade cards: U-11, U-30."""
import inspect
from pathlib import Path
import pytest


# ── U-11: Review responses ──────────────────────────────────────────

class TestReviewResponses:

    def test_migration_file_exists(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "028_review_responses.sql"
        assert migration.exists()

    def test_migration_creates_table(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "028_review_responses.sql"
        sql = migration.read_text()
        assert "CREATE TABLE IF NOT EXISTS review_responses" in sql
        assert "UNIQUE(post_id)" in sql
        assert "responder_id UUID" in sql

    def test_admin_post_response_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/posts/{post_id}/response" in paths

    def test_admin_get_response_endpoint_exists(self):
        from admin import router
        all_methods: set = set()
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/admin/posts/{post_id}/response":
                all_methods.update(r.methods)
        assert "POST" in all_methods
        assert "GET" in all_methods

    def test_response_validates_review_type(self):
        src = inspect.getsource(__import__("admin").admin_review_response)
        assert "post_type" in src
        assert "review" in src

    def test_response_enforces_unique(self):
        src = inspect.getsource(__import__("admin").admin_review_response)
        assert "409" in src
        assert "existing" in src

    def test_response_body_model(self):
        from admin import ReviewResponseBody
        m = ReviewResponseBody(content="Cảm ơn bạn đã đánh giá!")
        assert m.content == "Cảm ơn bạn đã đánh giá!"

    def test_response_body_validates_length(self):
        from admin import ReviewResponseBody
        with pytest.raises(Exception):
            ReviewResponseBody(content="")

    def test_get_response_includes_responder(self):
        src = inspect.getsource(__import__("admin").get_review_response)
        assert "responder_name" in src
        assert "display_name" in src

    def test_post_response_validates_path(self):
        src = inspect.getsource(__import__("admin").admin_review_response)
        assert "validate_path_id" in src
