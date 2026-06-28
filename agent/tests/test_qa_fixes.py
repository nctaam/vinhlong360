"""Tests for QA audit fixes — pagination bounds, CSRF fail-closed,
system gate always-on, check-phone privacy, IP hashing, review stats limit."""
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import public_api
import auth
import auth_middleware
import server


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
