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


# ── U-30: Entity claims — public submission ───────────────────────────

class TestEntityClaimsMigration:

    def test_migration_file_exists(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "029_entity_claims.sql"
        assert migration.exists()

    def test_migration_creates_table(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "029_entity_claims.sql"
        sql = migration.read_text()
        assert "CREATE TABLE IF NOT EXISTS entity_claims" in sql
        assert "claimant_id UUID" in sql
        assert "business_name TEXT NOT NULL" in sql
        assert "contact_phone TEXT NOT NULL" in sql
        assert "status TEXT DEFAULT 'pending'" in sql
        assert "CHECK (status IN ('pending', 'approved', 'rejected'))" in sql

    def test_migration_has_indexes(self):
        migration = Path(__file__).resolve().parent.parent / "migrations" / "029_entity_claims.sql"
        sql = migration.read_text()
        assert "idx_entity_claims_status" in sql
        assert "idx_entity_claims_entity" in sql
        assert "idx_entity_claims_claimant" in sql


class TestEntityClaimsEndpoint:

    def test_claim_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/claim" in paths

    def test_claim_endpoint_is_post(self):
        from public_api import router
        methods = {r.path: r.methods for r in router.routes if hasattr(r, "path")}
        assert "POST" in methods.get("/api/entities/{entity_id}/claim", set())

    def test_claim_requires_auth(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "require_user" in src

    def test_claim_requires_csrf(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "require_csrf" in src

    def test_claim_validates_path_id(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "validate_path_id" in src

    def test_claim_rate_limited(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "check_rate" in src
        assert "claim:" in src

    def test_claim_checks_entity_exists(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "entity_not_found" in src
        assert "404" in src

    def test_claim_prevents_duplicate_pending(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "duplicate_pending" in src
        assert "409" in src
        assert "status = 'pending'" in src

    def test_claim_inserts_record(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "INSERT INTO entity_claims" in src
        assert "business_name" in src
        assert "contact_phone" in src

    def test_claim_model_validates_business_name(self):
        from public_api import ClaimIn
        with pytest.raises(Exception):
            ClaimIn(business_name="", contact_phone="0123456789")

    def test_claim_model_validates_phone(self):
        from public_api import ClaimIn
        with pytest.raises(Exception):
            ClaimIn(business_name="Test", contact_phone="123")

    def test_claim_model_accepts_valid(self):
        from public_api import ClaimIn
        m = ClaimIn(business_name="Quán Ăn Ngon", contact_phone="0912345678")
        assert m.business_name == "Quán Ăn Ngon"
        assert m.contact_email is None

    def test_claim_requires_pg(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "require_pg" in src or "dependencies" in src
