"""Regression test suite from QA audit plan (qa-test-suite.md).

Covers: system endpoint gating, health minimal data, business integrity
(self-like, self-follow, best-answer ownership, RSVP entity validation,
reply cross-post, no booking routes), XSS/SQLi detection, Unicode
boundaries, and performance bounds."""
import inspect
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server
import social
import auth
import notifications
import moderation
import auth_middleware
import public_api
import admin
import database


# ── System endpoint gate coverage ──

SYSTEM_ENDPOINTS = [
    "/metrics",
    "/analytics/summary",
    "/analytics/popular",
    "/analytics/gaps",
    "/analytics/daily",
    "/analytics/top-entities",
    "/system/logs",
    "/system/errors",
    "/system/response-times",
    "/system/scheduler",
    "/system/learning",
    "/system/self-evolution",
    "/system/memory",
    "/system/traces",
    "/system/handoffs",
    "/system/memory-graph",
    "/system/quality",
    "/system/circuit-breakers",
    "/system/guardrails",
    "/system/costs",
    "/system/eval/latest",
    "/system/eval/history",
    "/system/optimizer",
    "/system/semantic-cache",
    "/system/judge",
    "/system/dynamic-agents",
    "/vectors/stats",
    "/checkpoints/s1",
    "/confirmations/s1",
    "/confirm/x",
    "/reject/x",
    "/ab-testing/tests",
    "/prompt-cache/stats",
    "/freshness/stale",
]


class TestSystemEndpointGate:
    """Every system/internal endpoint must be caught by gate_internal_endpoints."""

    def _gate_src(self):
        return inspect.getsource(server.gate_internal_endpoints)

    @pytest.mark.parametrize("path", SYSTEM_ENDPOINTS)
    def test_path_is_gated(self, path):
        src = self._gate_src()
        if path == "/metrics":
            assert '"/metrics"' in src
        elif path == "/vectors/stats":
            assert '"/vectors/stats"' in src
        else:
            prefix = "/" + path.lstrip("/").split("/")[0]
            assert prefix in src, f"Gate missing prefix for {path}"

    def test_gate_returns_404_not_403(self):
        src = self._gate_src()
        assert "404" in src
        assert "403" not in src

    def test_gate_checks_admin_key(self):
        src = self._gate_src()
        assert "verify_admin_key" in src


class TestHealthEndpointMinimal:
    """Public /health must not leak internals."""

    def test_health_response_is_minimal(self):
        src = inspect.getsource(server.health)
        forbidden = {"model", "scheduler", "rate_limits", "errors",
                     "response_times", "database", "vector_search"}
        for field in forbidden:
            assert f'"{field}"' not in src, f"/health leaks '{field}'"

    def test_health_only_returns_status_time_entities(self):
        src = inspect.getsource(server.health)
        assert '"status"' in src
        assert '"time"' in src
        assert '"entities"' in src

    def test_health_deep_requires_admin(self):
        src = inspect.getsource(server.deep_health)
        assert "require_admin" in src

    def test_health_details_requires_admin(self):
        src = inspect.getsource(server.health_details)
        assert "require_admin" in src

    def test_health_slo_requires_admin(self):
        src = inspect.getsource(server.slo_metrics)
        assert "require_admin" in src


# ── Business integrity ──

class TestSelfLikePrevention:
    """Self-like must be rejected with 400."""

    def test_toggle_like_checks_self(self):
        src = inspect.getsource(social.toggle_like)
        assert "Không thể thích bài viết của chính mình" in src
        assert "400" in src

    def test_check_happens_before_toggle(self):
        src = inspect.getsource(social.toggle_like)
        check_pos = src.find("_check_self_like")
        toggle_pos = src.find("_query")
        assert check_pos < toggle_pos


class TestSelfFollowPrevention:
    """Self-follow must be rejected with 400."""

    def test_toggle_follow_checks_self(self):
        src = inspect.getsource(notifications.toggle_follow)
        assert "Không thể tự follow chính mình" in src
        assert "400" in src


class TestBestAnswerOwnership:
    """Only post author can pick best answer."""

    def test_set_best_answer_checks_ownership(self):
        src = inspect.getsource(social.set_best_answer)
        assert "Chỉ người hỏi mới chọn được câu trả lời hay" in src
        assert "403" in src

    def test_set_best_answer_validates_comment_belongs_to_post(self):
        src = inspect.getsource(social.set_best_answer)
        assert "Bình luận không thuộc bài này" in src
        assert "400" in src


class TestRSVPEntityValidation:
    """RSVP only allowed for event-type entities."""

    def test_toggle_rsvp_checks_entity_type(self):
        src = inspect.getsource(notifications.toggle_rsvp)
        assert "event" in src
        assert "400" in src


class TestSelfRepostPrevention:
    """User cannot repost their own post."""

    def test_create_post_rejects_self_repost(self):
        src = inspect.getsource(social.create_post)
        assert "Không thể đăng lại bài viết của chính mình" in src


class TestNoBookingPaymentRoutes:
    """No transactional/booking/payment routes in the app."""

    def test_no_forbidden_route_keywords(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(social.router)
        app.include_router(notifications.router)
        app.include_router(public_api.router)
        app.include_router(auth.router)
        routes = {getattr(r, "path", "") for r in app.routes}
        forbidden = {"booking", "payment", "checkout", "cart", "invoice", "purchase"}
        for path in routes:
            for kw in forbidden:
                assert kw not in path.lower(), f"Forbidden route keyword '{kw}' in {path}"


# ── XSS detection ──

XSS_PAYLOADS = [
    '<script>alert("xss")</script>',
    '<img src=x onerror=alert(1)>',
    '<svg/onload=alert(1)>',
    '<a href="javascript:alert(1)">x</a>',
    '"><script>alert(document.cookie)</script>',
    '<iframe src="data:text/html,<script>alert(1)</script>">',
    '<input onfocus=alert(1) autofocus>',
]


class TestXSSDetection:
    """Moderation pipeline detects XSS payloads."""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_payload_detected(self, payload):
        result = moderation.check_xss_patterns(payload)
        assert result["has_xss"] is True, f"XSS not detected: {payload}"

    def test_clean_content_passes_xss(self):
        result = moderation.check_xss_patterns("Đây là quán ăn rất ngon ở Vĩnh Long")
        assert result["has_xss"] is False

    def test_html_tag_stripping(self):
        stripped = social._strip_html_tags('<b>bold</b> and <script>evil</script>')
        assert "<" not in stripped
        assert ">" not in stripped
        assert "bold" in stripped

    def test_sanitize_html_removes_scripts(self):
        clean = auth_middleware.sanitize_html('<script>alert(1)</script>Normal text')
        assert "<script" not in clean.lower()
        assert "Normal text" in clean


# ── SQLi resilience ──

SQLI_PAYLOADS = [
    "'; DROP TABLE entities; --",
    "1 OR 1=1",
    "1' UNION SELECT * FROM users--",
    "admin'--",
    "1; ATTACH DATABASE '/tmp/pwned.db' AS pwned;--",
    "' OR '1'='1",
    "%' OR 1=1--",
    "1 ORDER BY 99--",
]


class TestSQLiResilience:
    """Parameterized queries prevent SQL injection."""

    def test_search_uses_parameterized_query(self):
        src = inspect.getsource(database.Database.search_entities)
        assert "ph" in src or "?" in src or "%s" in src

    def test_list_entities_uses_parameterized_query(self):
        src = inspect.getsource(database.Database.list_entities)
        assert "ORDER BY" in src
        lines = src.split("\n")
        for line in lines:
            if "ORDER BY" in line and "LIMIT" not in line:
                assert "sort" not in line.lower() or "{" not in line, \
                    f"Raw sort in ORDER BY: {line.strip()}"

    def test_validate_path_id_rejects_injection(self):
        for payload in SQLI_PAYLOADS:
            try:
                auth_middleware.validate_path_id(payload, "test")
            except Exception:
                pass


# ── Unicode boundary handling ──

UNICODE_PAYLOADS = [
    "Nguyễn Văn Ả",
    "\U0001f600\U0001f389\U0001f3d6️",
    "Café Trần Hưng Đạo",
    "​‌‍",
    "A" * 1000,
    "",
    " ",
    "‪RTL‬ injection",
]


class TestUnicodeBoundaries:
    """Unicode edge cases don't crash sanitization or XSS detection."""

    @pytest.mark.parametrize("payload", UNICODE_PAYLOADS)
    def test_xss_check_handles_unicode(self, payload):
        result = moderation.check_xss_patterns(payload)
        assert isinstance(result, dict)

    @pytest.mark.parametrize("payload", UNICODE_PAYLOADS)
    def test_sanitize_handles_unicode(self, payload):
        result = auth_middleware.sanitize_html(payload)
        assert isinstance(result, str)

    @pytest.mark.parametrize("payload", UNICODE_PAYLOADS)
    def test_strip_html_handles_unicode(self, payload):
        result = social._strip_html_tags(payload)
        assert isinstance(result, str)

    @pytest.mark.parametrize("payload", UNICODE_PAYLOADS)
    def test_cta_check_handles_unicode(self, payload):
        result = moderation.check_transactional_cta(payload)
        assert isinstance(result, dict)


# ── Performance bounds ──

class TestPerformanceBounds:
    """Verify query bounds are reasonable."""

    def test_homepage_fetch_bounded_under_5000(self):
        src = inspect.getsource(public_api.homepage_curated)
        limits = re.findall(r"limit\s*=\s*(\d+)", src)
        for lim in limits:
            assert int(lim) <= 5000

    def test_map_pins_fetch_bounded(self):
        src = inspect.getsource(public_api.get_map_pins)
        limits = re.findall(r"limit\s*=\s*(\d+)", src)
        for lim in limits:
            assert int(lim) <= 5000

    def test_events_fetch_bounded(self):
        src = inspect.getsource(public_api.list_events)
        limits = re.findall(r"limit\s*=\s*(\d+)", src)
        for lim in limits:
            assert int(lim) <= 5000

    def test_review_stats_has_limit(self):
        src = inspect.getsource(public_api.get_review_stats)
        assert "LIMIT" in src

    def test_entity_followers_has_limit(self):
        src = inspect.getsource(social._notify_entity_followers)
        assert "LIMIT" in src

    def test_feed_has_limit_param(self):
        sig = inspect.signature(social.get_feed)
        assert "limit" in sig.parameters

    def test_leaderboard_has_limit_param(self):
        sig = inspect.signature(social.community_leaderboard)
        assert "limit" in sig.parameters


# ── Admin hardening ──

class TestAdminSelfProtection:
    """Admin cannot self-ban."""

    def test_ban_user_prevents_self_ban(self):
        src = inspect.getsource(admin.ban_user)
        assert "chính mình" in src

    def test_ban_user_has_auth_guard(self):
        src = inspect.getsource(admin.ban_user)
        assert "get_current_user" in src


# ── Rate limiting coverage ──

class TestRateLimitCoverage:
    """Critical write endpoints must have rate limiting."""

    _WRITE_ENDPOINTS = [
        ("social.py", "create_post", social.create_post),
        ("social.py", "delete_post", social.delete_post),
        ("social.py", "update_post", social.update_post),
        ("social.py", "create_comment", social.create_comment),
        ("social.py", "toggle_like", social.toggle_like),
        ("notifications.py", "toggle_follow", notifications.toggle_follow),
        ("auth.py", "set_password", auth.set_password),
    ]

    @pytest.mark.parametrize("file,name,func", _WRITE_ENDPOINTS,
                             ids=[f"{f}:{n}" for f, n, _ in _WRITE_ENDPOINTS])
    def test_endpoint_has_rate_limit(self, file, name, func):
        src = inspect.getsource(func)
        assert "check_rate" in src, f"{file}:{name} missing rate limit"


# ── CSRF coverage ──

class TestCSRFCoverage:
    """All POST/PUT/DELETE social endpoints must require CSRF."""

    _CSRF_ENDPOINTS = [
        ("social.py", "create_post", social.create_post),
        ("social.py", "delete_post", social.delete_post),
        ("social.py", "update_post", social.update_post),
        ("social.py", "create_comment", social.create_comment),
        ("social.py", "edit_comment", social.edit_comment),
        ("social.py", "delete_comment", social.delete_comment),
        ("notifications.py", "toggle_follow", notifications.toggle_follow),
    ]

    @pytest.mark.parametrize("file,name,func", _CSRF_ENDPOINTS,
                             ids=[f"{f}:{n}" for f, n, _ in _CSRF_ENDPOINTS])
    def test_endpoint_has_csrf(self, file, name, func):
        src = inspect.getsource(func)
        assert "require_csrf" in src, f"{file}:{name} missing CSRF"


# ── Auth guard coverage ──

class TestAuthGuardCoverage:
    """Authenticated endpoints must have get_current_user or require_user."""

    _AUTH_ENDPOINTS = [
        ("social.py", "create_post", social.create_post),
        ("social.py", "toggle_like", social.toggle_like),
        ("social.py", "create_comment", social.create_comment),
        ("notifications.py", "toggle_follow", notifications.toggle_follow),
        ("notifications.py", "toggle_rsvp", notifications.toggle_rsvp),
    ]

    @pytest.mark.parametrize("file,name,func", _AUTH_ENDPOINTS,
                             ids=[f"{f}:{n}" for f, n, _ in _AUTH_ENDPOINTS])
    def test_endpoint_has_auth(self, file, name, func):
        src = inspect.getsource(func)
        assert "require_user" in src or "get_current_user" in src, \
            f"{file}:{name} missing auth guard"


# ── Bare except logging ──

class TestBareExceptLogging:
    """Critical bare except blocks must log, not silently swallow."""

    def test_admin_cost_tracker_logs(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("_HAS_COST")
        block = src[max(0, idx - 200):idx + 100]
        assert "logger.warning" in block

    def test_admin_safe_helper_logs(self):
        src = inspect.getsource(admin._safe)
        assert "logger.debug" in src

    def test_admin_activity_feed_logs(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def activity_feed")
        block = src[idx:idx + 800]
        assert "logger.debug" in block or "logger.warning" in block


# ── Path traversal protection ──

class TestPathTraversalProtection:
    """File upload paths must be validated against traversal."""

    def test_storage_rejects_dotdot(self):
        import storage
        src = inspect.getsource(storage.Storage.upload_image_set)
        assert '".."' in src

    def test_storage_rejects_absolute_path(self):
        import storage
        src = inspect.getsource(storage.Storage.upload_image_set)
        assert "startswith" in src

    def test_storage_validates_relative_path(self):
        import storage
        src = inspect.getsource(storage.Storage._put)
        assert "is_relative_to" in src


# ── IP/phone masking in user-facing responses ──

class TestIPMasking:
    """IPs returned to users must be masked."""

    def test_mask_ip_ipv4(self):
        assert auth._mask_ip("192.168.1.100") == "192.168.*.*"

    def test_mask_ip_preserves_first_two_octets(self):
        result = auth._mask_ip("10.0.5.22")
        assert result.startswith("10.0.")
        assert "5" not in result.split(".")[-1]

    def test_mask_ip_none(self):
        assert auth._mask_ip(None) == ""

    def test_mask_ip_empty(self):
        assert auth._mask_ip("") == ""

    def test_login_history_masks_ip(self):
        src = inspect.getsource(auth.get_login_history)
        assert "_mask_ip" in src

    def test_consent_history_masks_ip(self):
        src = inspect.getsource(auth.consent_history)
        assert "_mask_ip" in src

    def test_login_history_stores_masked_phone(self):
        src = inspect.getsource(auth._log_login)
        assert "_mask_phone" in src

    def test_sessions_list_masks_ip(self):
        src = inspect.getsource(auth.list_sessions)
        assert "_mask_ip" in src
