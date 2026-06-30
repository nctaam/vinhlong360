"""
P5 — Integration tests: TestClient HTTP tests for all major API paths.

Covers:
  - Public API (knowledge-base backed, works without Postgres)
  - SEO endpoints (data.json backed)
  - Social/Auth 503 guards and auth enforcement
  - Admin endpoints with dependency override
  - Query parameter validation (422 on bad input)
  - Response structure assertions
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import admin
import auth
import notifications
import public_api
import seo
import social
import saved
import plans
import visits
from database import db

pg_only = pytest.mark.skipif(
    not db._use_pg,
    reason="UGC/auth is Postgres-only. Set DATABASE_URL=postgresql://… to run.",
)


# ═══════════════════════════════════════════════════════════════════════════
#  Client factories
# ═══════════════════════════════════════════════════════════════════════════

def _public_client():
    app = FastAPI()
    app.include_router(public_api.router)
    return TestClient(app)


def _seo_client():
    app = FastAPI()
    app.include_router(seo.router)
    return TestClient(app)


def _admin_client():
    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[admin.require_admin] = lambda: "test-admin"
    return TestClient(app)


def _social_client():
    app = FastAPI()
    app.include_router(social.router)
    return TestClient(app)


def _auth_client():
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def _notif_client():
    app = FastAPI()
    app.include_router(notifications.router)
    return TestClient(app)


def _saved_client():
    app = FastAPI()
    app.include_router(saved.router)
    return TestClient(app)


def _plans_client():
    app = FastAPI()
    app.include_router(plans.router)
    app.include_router(plans.public_router)
    return TestClient(app)


def _visits_client():
    app = FastAPI()
    app.include_router(visits.router)
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API — Knowledge Base endpoints (SQLite, always available)
# ═══════════════════════════════════════════════════════════════════════════

class TestEntityList:
    def test_list_entities_200(self):
        resp = _public_client().get("/api/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "total" in data
        assert isinstance(data["entities"], list)
        assert isinstance(data["total"], int)

    def test_list_entities_with_type_filter(self):
        resp = _public_client().get("/api/entities?type=dish")
        assert resp.status_code == 200
        data = resp.json()
        for e in data["entities"]:
            assert e.get("type") == "dish"

    def test_list_entities_multi_type(self):
        resp = _public_client().get("/api/entities?type=dish,attraction")
        assert resp.status_code == 200
        data = resp.json()
        for e in data["entities"]:
            assert e.get("type") in ("dish", "attraction")

    def test_list_entities_pagination(self):
        resp = _public_client().get("/api/entities?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entities"]) <= 5

    def test_list_entities_minimal_fields(self):
        resp = _public_client().get("/api/entities?fields=minimal&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        if data["entities"]:
            e = data["entities"][0]
            assert "id" in e
            assert "name" in e

    def test_list_entities_with_search(self):
        resp = _public_client().get("/api/entities?q=test&limit=5")
        assert resp.status_code == 200
        assert "entities" in resp.json()

    def test_list_entities_with_area(self):
        resp = _public_client().get("/api/entities?area=vinh-long&limit=5")
        assert resp.status_code == 200

    def test_list_entities_with_month(self):
        resp = _public_client().get("/api/entities?month=6&limit=5")
        assert resp.status_code == 200

    def test_list_entities_month_validation(self):
        assert _public_client().get("/api/entities?month=0").status_code == 422
        assert _public_client().get("/api/entities?month=13").status_code == 422
        assert _public_client().get("/api/entities?month=-1").status_code == 422

    def test_list_entities_sort_options(self):
        for sort in ("rating", "newest", "name"):
            resp = _public_client().get(f"/api/entities?sort={sort}&limit=3")
            assert resp.status_code == 200

    def test_list_entities_cache_header(self):
        resp = _public_client().get("/api/entities?limit=1")
        assert "cache-control" in resp.headers
        assert "max-age" in resp.headers["cache-control"]


class TestEntityDetail:
    def _get_first_entity_id(self):
        resp = _public_client().get("/api/entities?limit=1")
        entities = resp.json().get("entities", [])
        return entities[0]["id"] if entities else None

    def test_entity_detail_200(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("id") == eid
        assert "name" in data

    def test_entity_detail_not_found(self):
        resp = _public_client().get("/api/entities/nonexistent-entity-12345")
        assert resp.status_code == 404

    def test_entity_detail_sql_injection_rejected(self):
        resp = _public_client().get("/api/entities/'; DROP TABLE--")
        assert resp.status_code == 400

    def test_entity_relationships(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}/relationships")
        assert resp.status_code == 200
        data = resp.json()
        assert "relationships" in data
        assert "total" in data

    def test_entity_stats_pg_guard(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}/stats")
        if not db._use_pg:
            assert resp.status_code == 503
        else:
            assert resp.status_code in (200, 404)

    def test_entity_gallery(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}/gallery")
        assert resp.status_code in (200, 404)

    def test_entity_similar(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}/similar")
        assert resp.status_code in (200, 404)

    def test_entity_nearby(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}/nearby")
        assert resp.status_code in (200, 404)


class TestEntityReviews:
    def _get_first_entity_id(self):
        resp = _public_client().get("/api/entities?limit=1")
        entities = resp.json().get("entities", [])
        return entities[0]["id"] if entities else None

    def test_entity_reviews_pg_guard(self):
        eid = self._get_first_entity_id()
        if not eid:
            pytest.skip("No entities in knowledge base")
        resp = _public_client().get(f"/api/entities/{eid}/reviews")
        if not db._use_pg:
            assert resp.status_code == 503
        else:
            assert resp.status_code == 200


class TestEntityTypes:
    def test_entity_types_200(self):
        resp = _public_client().get("/api/entity-types")
        assert resp.status_code == 200
        data = resp.json()
        assert "types" in data
        assert "total" in data
        assert isinstance(data["types"], list)
        if data["types"]:
            t = data["types"][0]
            assert "type" in t
            assert "count" in t

    def test_entity_types_cache_header(self):
        resp = _public_client().get("/api/entity-types")
        assert "max-age=3600" in resp.headers.get("cache-control", "")


class TestAreas:
    def test_areas_200(self):
        resp = _public_client().get("/api/areas")
        assert resp.status_code == 200
        data = resp.json()
        assert "areas" in data
        assert "total_places" in data
        assert isinstance(data["areas"], list)


class TestSearch:
    def test_search_with_query(self):
        resp = _public_client().get("/api/search?q=vinh+long")
        assert resp.status_code == 200
        data = resp.json()
        assert "q" in data
        assert "total" in data
        assert "results" in data

    def test_search_requires_query(self):
        resp = _public_client().get("/api/search")
        assert resp.status_code == 422

    def test_search_max_length(self):
        resp = _public_client().get(f"/api/search?q={'x' * 201}")
        assert resp.status_code == 422

    def test_search_strips_html(self):
        resp = _public_client().get("/api/search?q=<script>alert(1)</script>")
        assert resp.status_code == 200
        data = resp.json()
        assert "<script>" not in data.get("q", "")


class TestAutocomplete:
    def test_autocomplete_with_query(self):
        resp = _public_client().get("/api/autocomplete?q=vinh")
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_autocomplete_requires_query(self):
        resp = _public_client().get("/api/autocomplete")
        assert resp.status_code == 422


class TestStats:
    def test_stats_200(self):
        resp = _public_client().get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


class TestHomepage:
    def test_homepage_200(self):
        resp = _public_client().get("/api/homepage")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_homepage_cache_header(self):
        resp = _public_client().get("/api/homepage")
        assert "cache-control" in resp.headers


class TestMapPins:
    def test_map_pins_200(self):
        resp = _public_client().get("/api/map-pins")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_map_pins_with_type_filter(self):
        resp = _public_client().get("/api/map-pins?type=dish")
        assert resp.status_code == 200

    def test_map_pins_with_area_filter(self):
        resp = _public_client().get("/api/map-pins?area=vinh-long")
        assert resp.status_code == 200

    def test_map_pins_structure(self):
        resp = _public_client().get("/api/map-pins")
        data = resp.json()
        if data:
            pin = data[0]
            assert "id" in pin
            assert "name" in pin
            assert "lat" in pin
            assert "lng" in pin


class TestEvents:
    def test_events_200(self):
        resp = _public_client().get("/api/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data

    def test_events_include_past(self):
        resp = _public_client().get("/api/events?include_past=true")
        assert resp.status_code == 200


class TestTransparency:
    def test_transparency_200(self):
        resp = _public_client().get("/api/transparency")
        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "VinhLong360"
        assert "nd147_compliance" in data
        assert "content_policy" in data
        assert "data_practices" in data

    def test_transparency_nd147_fields(self):
        resp = _public_client().get("/api/transparency")
        nd = resp.json()["nd147_compliance"]
        assert nd["content_removal_within_24h"] is True
        assert nd["user_data_on_request"] is True


class TestEntityMapSearch:
    def test_map_search_200(self):
        resp = _public_client().get(
            "/api/entities/map?north=10.5&south=10.0&east=106.5&west=106.0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "bbox" in data

    def test_map_search_invalid_bounds(self):
        resp = _public_client().get(
            "/api/entities/map?north=10.0&south=10.5&east=106.5&west=106.0"
        )
        assert resp.status_code == 400

    def test_map_search_requires_all_params(self):
        resp = _public_client().get("/api/entities/map?north=10.5")
        assert resp.status_code == 422


class TestEntityCompare:
    def _get_two_entity_ids(self):
        resp = _public_client().get("/api/entities?limit=2")
        entities = resp.json().get("entities", [])
        return [e["id"] for e in entities] if len(entities) >= 2 else None

    def test_compare_two_entities(self):
        ids = self._get_two_entity_ids()
        if not ids:
            pytest.skip("Need at least 2 entities")
        resp = _public_client().get(f"/api/entities/compare?ids={ids[0]},{ids[1]}")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "count" in data

    def test_compare_requires_two(self):
        resp = _public_client().get("/api/entities/compare?ids=single-id")
        assert resp.status_code == 400


class TestEntityPopular:
    def test_popular_200(self):
        resp = _public_client().get("/api/entities/popular")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data

    def test_popular_with_type(self):
        resp = _public_client().get("/api/entities/popular?entity_type=dish")
        assert resp.status_code == 200


class TestEntitySearch:
    def test_entity_search_200(self):
        resp = _public_client().get("/api/entities/search?q=vinh")
        assert resp.status_code == 200


class TestSiteSettings:
    def test_site_settings_200(self):
        resp = _public_client().get("/api/site-settings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)


class TestFeatured:
    def test_featured_200(self):
        resp = _public_client().get("/api/featured")
        assert resp.status_code == 200
        data = resp.json()
        assert "featured" in data
        assert isinstance(data["featured"], list)


class TestCollections:
    def test_collections_pg_guard(self):
        resp = _public_client().get("/api/collections")
        if not db._use_pg:
            assert resp.status_code == 503
        else:
            assert resp.status_code == 200

    def test_collection_slug_pg_guard(self):
        resp = _public_client().get("/api/collections/test-slug")
        if not db._use_pg:
            assert resp.status_code == 503
        else:
            assert resp.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════════════════
#  SEO ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestSeoRobotsTxt:
    def test_robots_txt_200(self):
        resp = _seo_client().get("/robots.txt")
        assert resp.status_code == 200
        body = resp.text
        assert "User-agent: *" in body
        assert "Disallow: /admin" in body
        assert "Sitemap:" in body

    def test_robots_allows_google(self):
        body = _seo_client().get("/robots.txt").text
        assert "User-agent: Googlebot" in body
        assert "User-agent: GPTBot" in body


class TestSeoSitemap:
    def test_sitemap_xml_200(self):
        resp = _seo_client().get("/sitemap.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers.get("content-type", "")
        body = resp.text
        assert "<?xml" in body
        assert "<urlset" in body
        assert "<url>" in body

    def test_sitemap_contains_core_pages(self):
        body = _seo_client().get("/sitemap.xml").text
        assert "https://vinhlong360.vn/" in body

    def test_sitemap_index_200(self):
        resp = _seo_client().get("/sitemap-index.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers.get("content-type", "")


class TestSeoFavicon:
    def test_favicon_204(self):
        resp = _seo_client().get("/favicon.ico")
        assert resp.status_code == 204


class TestSeoOgMeta:
    def test_site_og_meta(self):
        resp = _seo_client().get("/seo/og")
        assert resp.status_code == 200
        data = resp.json()
        assert data["og:site_name"] == "VinhLong360"
        assert data["og:locale"] == "vi_VN"
        assert "og:title" in data
        assert "og:description" in data
        assert "og:image" in data
        assert "twitter:card" in data

    def test_entity_og_meta_not_found(self):
        resp = _seo_client().get("/seo/og/nonexistent-12345")
        assert resp.status_code == 404


class TestSeoJsonLd:
    def test_jsonld_site(self):
        resp = _seo_client().get("/seo/jsonld/site")
        assert resp.status_code == 200
        data = resp.json()
        assert "@context" in data or isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════
#  AUTH 503 GUARDS AND AUTH ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════

class TestAuthGuards:
    def test_otp_endpoints_guarded(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.post("/auth/request-otp", json={"phone": "0901234567"}).status_code == 503
            assert client.post("/auth/verify-otp", json={"phone": "0901234567", "code": "123456"}).status_code == 503
        else:
            assert client.post("/auth/request-otp", json={"phone": "0901234567"}).status_code != 404

    def test_me_endpoint_guarded(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.get("/auth/me").status_code == 503
        else:
            assert client.get("/auth/me").status_code in (401, 403)

    def test_logout_guarded(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.post("/auth/logout").status_code == 503
        else:
            assert client.post("/auth/logout").status_code in (401, 403)

    def test_profile_update_guarded(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.put("/auth/profile", json={"display_name": "Test"}).status_code == 503
        else:
            assert client.put("/auth/profile", json={"display_name": "Test"}).status_code in (401, 403)

    def test_avatar_guarded(self):
        client = _auth_client()
        if not db._use_pg:
            assert client.post("/auth/avatar", files={"file": ("t.png", b"\x89PNG", "image/png")}).status_code == 503


# ═══════════════════════════════════════════════════════════════════════════
#  SOCIAL 503 GUARDS
# ═══════════════════════════════════════════════════════════════════════════

class TestSocialGuards:
    def test_create_post_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.post("/api/posts", json={"content": "hello", "post_type": "share"}).status_code == 503
        else:
            assert client.post("/api/posts", json={"content": "hello", "post_type": "share"}).status_code in (401, 403)

    def test_feed_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/feed").status_code == 503
        else:
            assert client.get("/api/feed").status_code in (401, 403)

    def test_drafts_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/drafts").status_code == 503
        else:
            assert client.get("/api/drafts").status_code in (401, 403)

    def test_search_posts_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/search/posts?q=test").status_code == 503
        else:
            assert client.get("/api/search/posts?q=test").status_code in (401, 403, 200)

    def test_search_users_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/search/users?q=test").status_code == 503
        else:
            assert client.get("/api/search/users?q=test").status_code in (401, 403, 200)

    def test_community_stats_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/community/stats").status_code == 503

    def test_leaderboard_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/community/leaderboard").status_code == 503

    def test_trending_tags_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/community/trending-tags").status_code == 503

    def test_bookmarks_guarded(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/me/bookmarks").status_code == 503


# ═══════════════════════════════════════════════════════════════════════════
#  NOTIFICATION 503 GUARDS
# ═══════════════════════════════════════════════════════════════════════════

class TestNotificationGuards:
    def test_notifications_guarded(self):
        client = _notif_client()
        if not db._use_pg:
            assert client.get("/api/notifications").status_code == 503
        else:
            assert client.get("/api/notifications").status_code in (401, 403)

    def test_notification_preferences_guarded(self):
        client = _notif_client()
        if not db._use_pg:
            assert client.get("/api/notification-preferences").status_code == 503

    def test_unread_count_guarded(self):
        client = _notif_client()
        if not db._use_pg:
            assert client.get("/api/notifications/unread-count").status_code == 503


# ═══════════════════════════════════════════════════════════════════════════
#  SAVED / PLANS / VISITS 503 GUARDS
# ═══════════════════════════════════════════════════════════════════════════

class TestSavedGuards:
    def test_saved_list_guarded(self):
        client = _saved_client()
        if not db._use_pg:
            assert client.get("/api/saved").status_code == 503
        else:
            assert client.get("/api/saved").status_code in (401, 403)

    def test_saved_add_guarded(self):
        client = _saved_client()
        if not db._use_pg:
            assert client.post("/api/saved", json={"id": "x"}).status_code == 503

    def test_saved_delete_guarded(self):
        client = _saved_client()
        if not db._use_pg:
            assert client.delete("/api/saved/x").status_code == 503


class TestPlansGuards:
    def test_plans_list_guarded(self):
        client = _plans_client()
        if not db._use_pg:
            assert client.get("/api/my-plans").status_code == 503
        else:
            assert client.get("/api/my-plans").status_code in (401, 403)

    def test_plans_create_guarded(self):
        client = _plans_client()
        if not db._use_pg:
            assert client.post("/api/my-plans", json={"title": "test"}).status_code == 503


class TestVisitsGuards:
    def test_visits_list_guarded(self):
        client = _visits_client()
        if not db._use_pg:
            assert client.get("/api/me/visits").status_code == 503
        else:
            assert client.get("/api/me/visits").status_code in (401, 403)

    def test_visits_add_guarded(self):
        client = _visits_client()
        if not db._use_pg:
            assert client.post("/api/me/visits", json={"entity_id": "x", "status": "want"}).status_code == 503


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN ENDPOINTS (with dependency override)
# ═══════════════════════════════════════════════════════════════════════════

class TestAdminEndpoints:
    def test_admin_entity_list(self):
        client = _admin_client()
        resp = client.get("/admin/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data or "items" in data or isinstance(data, list)

    def test_admin_entity_detail(self):
        client = _admin_client()
        resp = client.get("/admin/entities?limit=1")
        data = resp.json()
        entities = data.get("entities") or data.get("items") or (data if isinstance(data, list) else [])
        if not entities:
            pytest.skip("No entities")
        eid = entities[0]["id"]
        resp = client.get(f"/admin/entities/{eid}")
        assert resp.status_code == 200

    def test_admin_entity_not_found(self):
        client = _admin_client()
        resp = client.get("/admin/entities/nonexistent-12345")
        assert resp.status_code == 404

    def test_admin_entity_sql_injection_rejected(self):
        client = _admin_client()
        resp = client.get("/admin/entities/'; DROP TABLE--")
        assert resp.status_code == 400

    def test_admin_stats(self):
        client = _admin_client()
        resp = client.get("/admin/stats")
        assert resp.status_code == 200

    def test_admin_activity_feed(self):
        client = _admin_client()
        resp = client.get("/admin/activity-feed")
        assert resp.status_code == 200
        data = resp.json()
        assert "actions" in data

    def test_admin_audit_log(self):
        client = _admin_client()
        resp = client.get("/admin/audit-log")
        assert resp.status_code == 200

    def test_admin_moderation_stats(self):
        client = _admin_client()
        resp = client.get("/admin/moderation/stats")
        if db._use_pg:
            assert resp.status_code == 200
        else:
            assert resp.status_code == 503


class TestRouteOrdering:
    """Verify static routes are not shadowed by parameterized catch-alls."""

    def test_public_entities_map_not_shadowed(self):
        resp = _public_client().get(
            "/api/entities/map?north=10.5&south=10.0&east=106.5&west=106.0"
        )
        assert resp.status_code == 200

    def test_public_entities_popular_not_shadowed(self):
        resp = _public_client().get("/api/entities/popular")
        assert resp.status_code == 200

    def test_public_entities_search_not_shadowed(self):
        resp = _public_client().get("/api/entities/search?q=test")
        assert resp.status_code == 200

    def test_admin_moderation_stats_not_shadowed(self):
        resp = _admin_client().get("/admin/moderation/stats")
        if db._use_pg:
            assert resp.status_code == 200
        else:
            assert resp.status_code == 503

    def test_social_posts_hidden_not_shadowed(self):
        client = _social_client()
        if not db._use_pg:
            assert client.get("/api/posts/hidden").status_code == 503
        else:
            assert client.get("/api/posts/hidden").status_code in (200, 401, 403)


# ═══════════════════════════════════════════════════════════════════════════
#  QUERY PARAMETER VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryValidation:
    def test_entities_limit_too_high(self):
        resp = _public_client().get("/api/entities?limit=5000")
        assert resp.status_code == 422

    def test_entities_offset_negative(self):
        resp = _public_client().get("/api/entities?offset=-1")
        assert resp.status_code == 422

    def test_search_empty_query(self):
        resp = _public_client().get("/api/search?q=")
        assert resp.status_code == 422

    def test_entities_limit_negative(self):
        resp = _public_client().get("/api/entities?limit=-1")
        assert resp.status_code == 422

    def test_map_search_lat_out_of_range(self):
        resp = _public_client().get(
            "/api/entities/map?north=100&south=10&east=106&west=105"
        )
        assert resp.status_code == 422

    def test_events_limit_too_high(self):
        resp = _public_client().get("/api/events?limit=500")
        assert resp.status_code == 422

    def test_entities_sort_invalid_pattern(self):
        resp = _public_client().get("/api/entities?sort=invalid")
        assert resp.status_code == 422
