"""Integration test suite — verify all 21 upgrade cards are properly wired."""
import inspect
import re
from pathlib import Path
import pytest


AGENT_DIR = Path(__file__).resolve().parent.parent


class TestUpgradeIntegrationEndpoints:
    """Verify every upgrade endpoint exists and is reachable."""

    def _get_all_routes(self):
        from public_api import router as pub
        from admin import router as adm
        from visits import router as vis
        routes = {}
        for r in pub.routes:
            if hasattr(r, "path"):
                routes.setdefault(r.path, set()).update(r.methods)
        for r in adm.routes:
            if hasattr(r, "path"):
                routes.setdefault(r.path, set()).update(r.methods)
        for r in vis.routes:
            if hasattr(r, "path"):
                routes.setdefault(r.path, set()).update(r.methods)
        return routes

    # U-02: Source freshness
    def test_u02_report_stale(self):
        routes = self._get_all_routes()
        assert "POST" in routes.get("/api/entities/{entity_id}/report-stale", set())

    # U-04: Review sort/filter
    def test_u04_entity_feed_has_sort(self):
        import social
        src = inspect.getsource(social.get_entity_feed)
        assert "sort" in src

    # U-07: Practical facts
    def test_u07_practical_facts(self):
        import public_api
        assert callable(public_api._build_practical_facts)
        assert "phone" in public_api._PRACTICAL_FACTS_KEYS
        assert "hours" in public_api._PRACTICAL_FACTS_KEYS

    # U-08: Field-level report
    def test_u08_report_model_has_field(self):
        from public_api import ReportStaleIn
        m = ReportStaleIn(field="phone", detail="Sai số")
        assert m.field == "phone"

    # U-09: Entity Q&A
    def test_u09_entity_qa(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/api/entities/{entity_id}/qa", set())

    # U-11: Review responses
    def test_u11_review_response_admin(self):
        routes = self._get_all_routes()
        methods = routes.get("/admin/posts/{post_id}/response", set())
        assert "POST" in methods
        assert "GET" in methods

    # U-12: AggregateRating gating
    def test_u12_rating_min_count(self):
        import seo
        assert hasattr(seo, "AGGREGATE_RATING_MIN_COUNT")
        assert seo.AGGREGATE_RATING_MIN_COUNT >= 3

    # U-15: What's-new feed
    def test_u15_feed_new_since(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/api/feed/new-since", set())

    # U-17: Stale queue
    def test_u17_stale_queue(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/admin/stale-queue", set())
        assert "POST" in routes.get("/admin/stale-queue/{entity_id}/mark-reviewed", set())

    # U-20: Review prompts
    def test_u20_review_prompts(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/api/me/visits/review-prompts", set())

    # U-22: Contact funnel
    def test_u22_contact_funnel(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/admin/contact-funnel", set())
        assert "GET" in routes.get("/admin/contact-funnel/export", set())

    # U-24: Q&A queue
    def test_u24_qa_queue(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/admin/qa-queue", set())
        assert "POST" in routes.get("/admin/qa-queue/{post_id}/set-best-answer", set())

    # U-25: Day plan
    def test_u25_day_plan(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/api/places/{place_id}/day-plan", set())

    # U-26: Event reminders
    def test_u26_event_reminders(self):
        from scheduler import TASKS
        names = [t.name for t in TASKS]
        assert "event-reminders" in names

    # U-28: Collections
    def test_u28_collections_public(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/api/collections", set())
        assert "GET" in routes.get("/api/collections/{slug}", set())

    def test_u28_collections_admin(self):
        routes = self._get_all_routes()
        assert "POST" in routes.get("/admin/collections", set())
        assert "DELETE" in routes.get("/admin/collections/{collection_id}", set())

    # U-29: Similar entities
    def test_u29_similar(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/api/entities/{entity_id}/similar", set())

    # U-30: Entity claims
    def test_u30_claim_submit(self):
        routes = self._get_all_routes()
        assert "POST" in routes.get("/api/entities/{entity_id}/claim", set())

    def test_u30_claim_admin(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/admin/claims", set())
        assert "POST" in routes.get("/admin/claims/{claim_id}/approve", set())
        assert "POST" in routes.get("/admin/claims/{claim_id}/reject", set())

    # BE-5: Block enforcement
    def test_be5_block_in_feeds(self):
        import social
        for fn_name in ["get_entity_feed", "get_following_feed", "search_users", "suggested_follows", "get_comments"]:
            src = inspect.getsource(getattr(social, fn_name))
            assert "_block_sql" in src or "block" in src.lower(), f"Block missing in {fn_name}"

    # BE-10: Completeness
    def test_be10_completeness(self):
        routes = self._get_all_routes()
        assert "GET" in routes.get("/admin/completeness", set())
        assert "GET" in routes.get("/admin/completeness/details", set())


class TestUpgradeMigrations:
    """Verify all upgrade migrations exist and are valid SQL."""

    @pytest.mark.parametrize("num,table", [
        ("027", "collections"),
        ("028", "review_responses"),
        ("029", "entity_claims"),
        ("030", "upgrade_indexes"),
    ])
    def test_migration_exists(self, num, table):
        path = AGENT_DIR / "migrations" / f"{num}_{table}.sql"
        assert path.exists(), f"Migration {num}_{table}.sql missing"

    @pytest.mark.parametrize("num,table", [
        ("027", "collections"),
        ("028", "review_responses"),
        ("029", "entity_claims"),
    ])
    def test_migration_has_if_not_exists(self, num, table):
        path = AGENT_DIR / "migrations" / f"{num}_{table}.sql"
        sql = path.read_text()
        assert "IF NOT EXISTS" in sql

    def test_indexes_migration_has_partial_indexes(self):
        path = AGENT_DIR / "migrations" / "030_upgrade_indexes.sql"
        sql = path.read_text()
        assert "WHERE" in sql
        assert "idx_posts_entity_question" in sql
        assert "idx_posts_entity_review" in sql


class TestUpgradeAuthGuards:
    """Verify auth/admin guards on all upgrade endpoints."""

    def test_public_write_endpoints_have_rate_limit(self):
        import public_api
        for fn_name in ["report_stale_field", "submit_entity_claim"]:
            src = inspect.getsource(getattr(public_api, fn_name))
            assert "check_rate" in src or "limiter" in src, f"{fn_name} missing rate limit"

    def test_claim_requires_auth(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "require_user" in src

    def test_review_prompts_requires_auth(self):
        src = inspect.getsource(__import__("visits").review_prompts)
        assert "require_user" in src

    def test_admin_router_has_global_admin_guard(self):
        from admin import router
        dep_names = []
        for d in router.dependencies:
            if hasattr(d, "dependency"):
                dep_names.append(getattr(d.dependency, "__name__", ""))
        assert "require_admin" in dep_names


class TestUpgradeParameterizedQueries:
    """Spot-check that upgrade endpoints use parameterized queries."""

    def test_claim_uses_parameterized(self):
        src = inspect.getsource(__import__("public_api").submit_entity_claim)
        assert "f\"" not in src or "{ph}" in src
        assert "entity_claims" in src

    def test_admin_claims_uses_parameterized(self):
        src = inspect.getsource(__import__("admin").list_claims)
        assert "{ph}" in src
        assert "entity_claims" in src

    def test_review_prompts_uses_parameterized(self):
        src = inspect.getsource(__import__("visits").review_prompts)
        assert "{ph}" in src
