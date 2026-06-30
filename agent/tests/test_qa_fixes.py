"""Tests for QA audit fixes — pagination bounds, CSRF fail-closed,
system gate always-on, check-phone privacy, IP hashing, review stats limit,
SMS retry, itinerary pagination, comment thread assembly, CTA lint,
orphan cleanup, reputation anti-sybil."""
import inspect
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import public_api
import auth
import auth_middleware
import server
import social
import moderation
import admin


class TestPaginationBounds:
    """Finding-025/026: pagination ge=1 prevents zero/negative limit."""

    def _get_limit_param(self, func):
        sig = inspect.signature(func)
        for name, p in sig.parameters.items():
            if name == "limit":
                return p
        return None

    def test_entities_list_limit_ge1(self):
        p = self._get_limit_param(public_api.list_entities)
        assert p is not None
        src = inspect.getsource(public_api.list_entities)
        assert "ge=1" in src or "ge = 1" in src

    def test_search_limit_ge1(self):
        p = self._get_limit_param(public_api.search)
        assert p is not None
        src = inspect.getsource(public_api.search)
        assert "ge=1" in src or "ge = 1" in src

    def test_events_limit_ge1(self):
        p = self._get_limit_param(public_api.list_events)
        assert p is not None
        src = inspect.getsource(public_api.list_events)
        assert "ge=1" in src or "ge = 1" in src


class TestUnboundedFetchCaps:
    """Finding-027/028/029: no limit=100000 in production queries."""

    def test_no_100k_limits(self):
        src = inspect.getsource(public_api)
        matches = re.findall(r"limit\s*=\s*100000", src)
        assert len(matches) == 0, f"Found {len(matches)} unbounded limit=100000"

    def test_homepage_fetch_bounded(self):
        src = inspect.getsource(public_api.homepage_curated)
        limits = re.findall(r"limit\s*=\s*(\d+)", src)
        for lim in limits:
            assert int(lim) <= 5000, f"Homepage uses limit={lim}"

    def test_map_pins_fetch_bounded(self):
        src = inspect.getsource(public_api.get_map_pins)
        limits = re.findall(r"limit\s*=\s*(\d+)", src)
        for lim in limits:
            assert int(lim) <= 5000, f"Map pins uses limit={lim}"

    def test_events_fetch_bounded(self):
        src = inspect.getsource(public_api.list_events)
        limits = re.findall(r"limit\s*=\s*(\d+)", src)
        for lim in limits:
            assert int(lim) <= 5000, f"Events uses limit={lim}"


class TestCSRFFailClosed:
    """Finding-005: CSRF_SECRET must fail-closed in production."""

    def test_csrf_production_check_exists(self):
        src = inspect.getsource(auth_middleware)
        assert 'ENVIRONMENT' in src
        assert 'production' in src
        assert 'RuntimeError' in src or 'raise' in src

    def test_csrf_fallback_for_dev(self):
        src = inspect.getsource(auth_middleware)
        assert 'token_hex' in src


class TestSystemGateAlwaysOn:
    """Finding-006: system endpoint gate active in ALL environments."""

    def test_gate_middleware_exists(self):
        src = inspect.getsource(server.gate_internal_endpoints)
        assert "/system" in src
        assert "/analytics" in src
        assert "/metrics" in src

    def test_gate_not_conditional_on_prod(self):
        src = inspect.getsource(server.gate_internal_endpoints)
        assert "_IS_PROD" not in src
        assert "is_prod" not in src.lower() or "is_production" not in src.lower()

    def test_gate_returns_404(self):
        src = inspect.getsource(server.gate_internal_endpoints)
        assert "404" in src


class TestCheckPhonePrivacy:
    """Finding-008: /auth/check-phone must not reveal has_password."""

    def test_no_has_password_in_response(self):
        src = inspect.getsource(auth.check_phone)
        assert "has_password" not in src

    def test_returns_exists_only(self):
        src = inspect.getsource(auth.check_phone)
        assert '"exists"' in src or "'exists'" in src


class TestUserProfileSlug:
    """Regression: /api/users/{username} must not be rejected as non-UUID."""

    def test_profile_allows_username_slug(self):
        src = inspect.getsource(social.get_user_profile)
        assert "validate_path_id(user_id" not in src
        assert "lower(username)" in src

    def test_user_posts_resolve_username_slug(self):
        src = inspect.getsource(social.get_user_posts)
        assert "validate_path_id(user_id" not in src
        assert "_resolve_user_id" in src

class TestAuthMePasswordState:
    """Regression: /auth/me must expose the account password state."""

    def test_safe_user_includes_has_password(self):
        src = inspect.getsource(auth._safe_user)
        assert "has_password" in src
        assert "password_hash" in src

class TestAuthCsrfBootstrap:
    """Regression: frontend write requests must get a CSRF token after login."""

    def test_csrf_endpoint_mounted(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(auth.router)
        routes = {(tuple(r.methods), r.path) for r in app.routes if hasattr(r, "path")}
        assert any("/auth/csrf" == path and "GET" in methods for methods, path in routes)

    def test_csrf_endpoint_uses_session_token(self):
        src = inspect.getsource(auth.get_csrf)
        assert "_extract_token" in src
        assert "generate_csrf_token" in src

    def test_frontend_auth_headers_include_csrf(self):
        src = (Path(__file__).resolve().parents[2] / "web-nuxt/composables/useAuth.ts").read_text(encoding="utf-8")
        assert "/auth/csrf" in src
        assert "X-CSRF-Token" in src
        assert "auth-csrf-token-for" not in src

    def test_saved_merge_does_not_auto_post_when_local_cache_empty(self):
        src = (Path(__file__).resolve().parents[2] / "web-nuxt/composables/useFavorites.ts").read_text(encoding="utf-8")
        assert "hasLocalItems" in src
        assert "/api/saved/merge" in src
        assert "await $fetch<{ items?: FavoriteItem[] }>('/api/saved', { headers: authHeaders() })" in src

class TestSessionListCleanup:
    """Regression: internal script sessions must not pollute user UI."""

    def test_internal_session_filter_exists(self):
        src = inspect.getsource(auth.list_sessions)
        assert "_is_internal_session" in src
        assert "hidden_internal_count" in src

class TestProductionFeedCleanup:
    """Regression: production community feed hides known seed/test posts."""

    def test_main_feed_filters_seed_posts(self):
        src = inspect.getsource(social.get_feed)
        assert "_prod_seed_post_filter" in src

    def test_following_feed_filters_seed_posts(self):
        src = inspect.getsource(social.get_following_feed)
        assert "_prod_seed_post_filter" in src

class TestReputationLikeCount:
    """Regression: profile and leaderboard must use posts.like_count, not old posts.likes."""

    def test_profile_reputation_uses_like_count(self):
        src = inspect.getsource(social._reputation)
        assert "like_count" in src
        assert "jsonb_typeof(likes)" not in src

    def test_leaderboard_uses_like_count(self):
        src = inspect.getsource(social.community_leaderboard)
        assert "p.like_count" in src
        assert "p.likes" not in src

class TestIPHashing:
    """Finding-011/012: IP addresses must be hashed, not stored raw."""

    def test_report_hashes_ip(self):
        src = inspect.getsource(public_api.submit_report)
        assert "ip_hash" in src
        assert "sha256" in src
        lines = src.split("\n")
        for line in lines:
            if '"ip"' in line and "ip_hash" not in line:
                assert "sha256" in line or "hash" in line, \
                    f"Raw IP stored: {line.strip()}"

    def test_contact_view_hashes_ip(self):
        src = inspect.getsource(public_api.track_contact_view)
        assert "ip_hash" in src
        assert "sha256" in src


class TestReviewStatsLimit:
    """Finding-030: review stats content query must have LIMIT."""

    def test_content_query_has_limit(self):
        src = inspect.getsource(public_api.get_review_stats)
        assert "LIMIT" in src
        limit_match = re.search(r"LIMIT\s+(\d+)", src)
        assert limit_match, "No LIMIT clause found in review stats query"
        limit_val = int(limit_match.group(1))
        assert limit_val <= 500, f"LIMIT too high: {limit_val}"


class TestSMSRetry:
    """Finding-018: SMS delivery with retry + exponential backoff."""

    def test_send_sms_has_retry_loop(self):
        src = inspect.getsource(auth._send_sms)
        assert "_SMS_MAX_RETRIES" in src or "range(" in src
        assert "asyncio.sleep" in src

    def test_send_sms_has_backoff(self):
        src = inspect.getsource(auth._send_sms)
        assert "2 **" in src or "2**" in src

    def test_max_retries_is_reasonable(self):
        assert 2 <= auth._SMS_MAX_RETRIES <= 5


class TestItineraryPagination:
    """Finding-031: itinerary listing must have pagination."""

    def test_itinerary_endpoint_has_limit_param(self):
        sig = inspect.signature(public_api.list_itineraries)
        assert "limit" in sig.parameters
        assert "offset" in sig.parameters

    def test_itinerary_limit_has_bounds(self):
        src = inspect.getsource(public_api.list_itineraries)
        assert "ge=1" in src


class TestCommentThreadAssembly:
    """Finding-035: comments must page top-level first, then fetch replies."""

    def test_get_comments_pages_top_level_first(self):
        src = inspect.getsource(social.get_comments)
        assert "parent_id IS NULL" in src

    def test_get_comments_fetches_replies_for_top_ids(self):
        src = inspect.getsource(social.get_comments)
        assert "parent_id" in src
        assert "IN (" in src or "IN(" in src


class TestTransactionalCTALint:
    """Finding-021: transactional CTA wording must be detected."""

    def test_cta_detects_vietnamese_buy_now(self):
        r = moderation.check_transactional_cta("Mua ngay sản phẩm")
        assert r["has_cta"] is True

    def test_cta_detects_booking(self):
        r = moderation.check_transactional_cta("Đặt tour ngay hôm nay")
        assert r["has_cta"] is True

    def test_cta_detects_checkout(self):
        r = moderation.check_transactional_cta("Go to checkout now")
        assert r["has_cta"] is True

    def test_cta_clean_content_passes(self):
        r = moderation.check_transactional_cta("Đây là quán ăn rất ngon ở Vĩnh Long")
        assert r["has_cta"] is False

    def test_cta_empty_passes(self):
        r = moderation.check_transactional_cta("")
        assert r["has_cta"] is False

    def test_cta_integrated_in_moderation(self):
        src = inspect.getsource(moderation.moderate_content_enhanced)
        assert "check_transactional_cta" in src
        assert "transactional_cta" in src


class TestOrphanRefCleanup:
    """Finding-033: admin endpoint to clean orphaned UGC entity refs."""

    def test_cleanup_endpoint_mounted(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(admin.router)
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/admin/cleanup-orphan-refs" in routes

    def test_cleanup_requires_pg(self):
        src = inspect.getsource(admin.admin_cleanup_orphan_entity_refs)
        assert "503" in src or "_use_pg" in src

    def test_cleanup_checks_ugc_tables(self):
        src = inspect.getsource(admin.admin_cleanup_orphan_entity_refs)
        assert "saved_entities" in src
        assert "user_visits" in src
        assert "event_rsvp" in src


class TestReputationAntiSybil:
    """Finding-020: reputation ignores followers from accounts < 7 days old."""

    def test_leaderboard_filters_new_followers(self):
        src = inspect.getsource(social.community_leaderboard)
        assert "7 days" in src or "INTERVAL" in src

    def test_reputation_filters_new_followers(self):
        src = inspect.getsource(social._reputation)
        assert "7 days" in src or "INTERVAL" in src

    def test_both_join_users_for_age(self):
        lb_src = inspect.getsource(social.community_leaderboard)
        rep_src = inspect.getsource(social._reputation)
        assert "fu.created_at" in lb_src or "created_at" in lb_src
        assert "fu.created_at" in rep_src or "created_at" in rep_src


class TestOrderBySQLiRegression:
    """Finding-024: ORDER BY must use whitelist, not raw caller input."""

    def test_list_entities_sort_whitelist(self):
        import database
        src = inspect.getsource(database.Database.list_entities)
        assert '"name"' in src or "'name'" in src
        assert '"rating"' in src or "'rating'" in src
        assert "ORDER BY" in src
        assert "sort" not in src.split("ORDER BY")[1].split("LIMIT")[0], \
            "Raw sort param must not appear directly in ORDER BY clause"
