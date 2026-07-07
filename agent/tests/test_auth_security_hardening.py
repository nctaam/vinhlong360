"""
Auth & security hardening tests — T7/T10 coverage:

  T7: CSRF protection, input validation, rate-limit coverage, auth bypass audit
  T10: Security event logging

Complements test_p0_security_hardening.py (P0-1/3/4) with higher-level
security checks. All tests are pure-logic (no DB, no LLM, no network).
"""

import hashlib
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================================
#  T7: CSRF Protection
# ============================================================================

class TestCSRFTokenGeneration:
    """Verify CSRF token generation and validation logic."""

    def test_generate_csrf_produces_hex_string(self):
        from auth_middleware import generate_csrf_token
        token = generate_csrf_token("test-session-123")
        assert isinstance(token, str)
        assert len(token) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_csrf_deterministic(self):
        from auth_middleware import generate_csrf_token
        t1 = generate_csrf_token("session-abc")
        t2 = generate_csrf_token("session-abc")
        assert t1 == t2

    def test_generate_csrf_different_sessions_different_tokens(self):
        from auth_middleware import generate_csrf_token
        t1 = generate_csrf_token("session-1")
        t2 = generate_csrf_token("session-2")
        assert t1 != t2

    def test_validate_csrf_correct_token(self):
        from auth_middleware import generate_csrf_token, _validate_csrf
        session_id = "test-session-valid"
        token = generate_csrf_token(session_id)
        request = MagicMock()
        request.headers = {"X-CSRF-Token": token}
        assert _validate_csrf(request, session_id) is True

    def test_validate_csrf_wrong_token(self):
        from auth_middleware import _validate_csrf
        request = MagicMock()
        request.headers = {"X-CSRF-Token": "wrong-token-value"}
        assert _validate_csrf(request, "session-1") is False

    def test_validate_csrf_missing_header(self):
        from auth_middleware import _validate_csrf
        request = MagicMock()
        request.headers = {}
        assert _validate_csrf(request, "session-1") is False

    def test_validate_csrf_empty_header(self):
        from auth_middleware import _validate_csrf
        request = MagicMock()
        request.headers = {"X-CSRF-Token": ""}
        assert _validate_csrf(request, "session-1") is False

    def test_csrf_uses_hmac_not_plain_hash(self):
        """CSRF token must use HMAC (keyed hash), not a plain hash of session_id."""
        from auth_middleware import generate_csrf_token
        session_id = "test-session"
        token = generate_csrf_token(session_id)
        plain_hash = hashlib.sha256(session_id.encode()).hexdigest()
        assert token != plain_hash, "CSRF token must use HMAC, not plain SHA-256"

    def test_require_csrf_is_fastapi_dependency(self):
        """require_csrf must be an async function usable as Depends()."""
        from auth_middleware import require_csrf
        assert inspect.iscoroutinefunction(require_csrf)


class TestCSRFSafeMethodsBypass:
    """Safe HTTP methods (GET/HEAD/OPTIONS) should bypass CSRF."""

    def test_safe_methods_set_is_correct(self):
        from auth_middleware import _SAFE_METHODS
        assert "GET" in _SAFE_METHODS
        assert "HEAD" in _SAFE_METHODS
        assert "OPTIONS" in _SAFE_METHODS
        assert "POST" not in _SAFE_METHODS
        assert "PUT" not in _SAFE_METHODS
        assert "DELETE" not in _SAFE_METHODS
        assert "PATCH" not in _SAFE_METHODS


# ============================================================================
#  T7: Input Validation Utilities
# ============================================================================

class TestValidateStringParam:
    """Test the validate_string_param utility."""

    def test_normal_string_passes(self):
        from auth_middleware import validate_string_param
        result = validate_string_param("hello world", max_length=200)
        assert result == "hello world"

    def test_strips_whitespace_by_default(self):
        from auth_middleware import validate_string_param
        result = validate_string_param("  hello  ", max_length=200)
        assert result == "hello"

    def test_truncates_at_max_length(self):
        from auth_middleware import validate_string_param
        long_str = "a" * 500
        result = validate_string_param(long_str, max_length=200)
        assert len(result) == 200

    def test_min_length_enforced(self):
        from auth_middleware import validate_string_param
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_string_param("ab", min_length=3)
        assert exc_info.value.status_code == 400

    def test_none_with_min_length_raises(self):
        from auth_middleware import validate_string_param
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_string_param(None, min_length=1)

    def test_none_without_min_length_returns_empty(self):
        from auth_middleware import validate_string_param
        result = validate_string_param(None, min_length=0)
        assert result == ""

    def test_empty_string_with_min_length_raises(self):
        from auth_middleware import validate_string_param
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_string_param("", min_length=1)


class TestValidatePathId:
    """Test path parameter validation."""

    def test_valid_alphanumeric_id(self):
        from auth_middleware import validate_path_id
        assert validate_path_id("abc-123_def") == "abc-123_def"

    def test_valid_uuid_style_id(self):
        from auth_middleware import validate_path_id
        assert validate_path_id("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    def test_rejects_sql_injection_attempt(self):
        from auth_middleware import validate_path_id
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_path_id("1'; DROP TABLE users; --")
        assert exc_info.value.status_code == 400

    def test_rejects_path_traversal(self):
        from auth_middleware import validate_path_id
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_path_id("../../etc/passwd")

    def test_rejects_empty_string(self):
        from auth_middleware import validate_path_id
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_path_id("")

    def test_rejects_overly_long_id(self):
        from auth_middleware import validate_path_id
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_path_id("a" * 129)

    def test_rejects_special_characters(self):
        from auth_middleware import validate_path_id
        from fastapi import HTTPException
        for bad in ["<script>", "id&param=val", "id;rm -rf /", "id|cat /etc"]:
            with pytest.raises(HTTPException):
                validate_path_id(bad)


class TestValidateUuidParam:
    """Test UUID parameter validation."""

    def test_valid_uuid(self):
        from auth_middleware import validate_uuid_param
        assert validate_uuid_param("550e8400-e29b-41d4-a716-446655440000")

    def test_rejects_non_uuid(self):
        from auth_middleware import validate_uuid_param
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_uuid_param("not-a-uuid")

    def test_rejects_empty(self):
        from auth_middleware import validate_uuid_param
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_uuid_param("")


class TestValidateIntParam:
    """Test integer parameter clamping."""

    def test_clamps_to_max(self):
        from auth_middleware import validate_int_param
        assert validate_int_param(9999, max_val=100) == 100

    def test_clamps_to_min(self):
        from auth_middleware import validate_int_param
        assert validate_int_param(-5, min_val=0) == 0

    def test_passes_within_range(self):
        from auth_middleware import validate_int_param
        assert validate_int_param(50, min_val=0, max_val=100) == 50


class TestSanitizeLogParam:
    """Test log injection prevention."""

    def test_strips_newlines(self):
        from auth_middleware import sanitize_log_param
        result = sanitize_log_param("line1\nline2\rline3")
        assert "\n" not in result
        assert "\r" not in result

    def test_truncates_long_values(self):
        from auth_middleware import sanitize_log_param
        result = sanitize_log_param("a" * 200, max_length=100)
        assert len(result) <= 104  # 100 + "..."

    def test_handles_empty(self):
        from auth_middleware import sanitize_log_param
        assert sanitize_log_param("") == ""
        assert sanitize_log_param(None) == ""


# ============================================================================
#  T10: Security Event Logging
# ============================================================================

class TestSecurityEventLogger:
    """Test security event logging infrastructure."""

    def test_security_logger_singleton_exists(self):
        from middleware import security_logger
        assert security_logger is not None

    def test_auth_failure_logged(self):
        from middleware import security_logger
        initial = len(security_logger.recent())
        security_logger.auth_failure("10.0.0.1", "invalid_token", endpoint="/auth/login")
        events = security_logger.recent()
        assert len(events) > initial
        last = events[-1]
        assert last["event"] == "auth_failure"
        assert last["ip"] == "10.0.0.1"
        assert last["reason"] == "invalid_token"

    def test_rate_limit_hit_logged(self):
        from middleware import security_logger
        security_logger.rate_limit_hit("10.0.0.2", "/chat", key="chat:10.0.0.2")
        last = security_logger.recent()[-1]
        assert last["event"] == "rate_limit_hit"
        assert last["endpoint"] == "/chat"

    def test_suspicious_input_logged(self):
        from middleware import security_logger
        security_logger.suspicious_input(
            "10.0.0.3", "/search", "'; DROP TABLE --"
        )
        last = security_logger.recent()[-1]
        assert last["event"] == "suspicious_input"
        assert "DROP TABLE" in last["detail"]

    def test_suspicious_input_detail_truncated(self):
        from middleware import security_logger
        long_input = "x" * 500
        security_logger.suspicious_input("10.0.0.4", "/search", long_input)
        last = security_logger.recent()[-1]
        assert len(last["detail"]) <= 200

    def test_admin_key_failure_logged(self):
        from middleware import security_logger
        security_logger.admin_key_failure("10.0.0.5", endpoint="/admin/entities")
        last = security_logger.recent()[-1]
        assert last["event"] == "admin_key_failure"

    def test_csrf_failure_logged(self):
        from middleware import security_logger
        security_logger.csrf_failure("10.0.0.6", endpoint="/api/posts")
        last = security_logger.recent()[-1]
        assert last["event"] == "csrf_failure"

    def test_session_anomaly_logged(self):
        from middleware import security_logger
        security_logger.session_anomaly("10.0.0.7", "ip_changed", old_ip="1.2.3.4")
        last = security_logger.recent()[-1]
        assert last["event"] == "session_anomaly"
        assert last["reason"] == "ip_changed"

    def test_filter_by_event_type(self):
        from middleware import security_logger
        security_logger.auth_failure("10.0.0.8", "test_filter")
        events = security_logger.recent(event_type="auth_failure")
        assert all(e["event"] == "auth_failure" for e in events)

    def test_stats_returns_counts(self):
        from middleware import security_logger
        stats = security_logger.stats()
        assert "total_events" in stats
        assert "by_type" in stats
        assert isinstance(stats["by_type"], dict)


class TestAdminKeyFailureLogging:
    """Verify that verify_admin_key logs failures."""

    def test_wrong_key_triggers_security_log(self):
        from middleware import verify_admin_key, security_logger
        request = MagicMock()
        request.headers = {"X-Admin-Key": "wrong-key"}
        request.client = MagicMock()
        request.client.host = "10.99.99.1"
        request.url = "/admin/test"

        initial_count = len(security_logger.recent(event_type="admin_key_failure"))
        verify_admin_key(request)
        new_count = len(security_logger.recent(event_type="admin_key_failure"))
        assert new_count > initial_count

    def test_missing_key_does_not_log(self):
        """Missing key is normal (public endpoint) — should NOT log as failure."""
        from middleware import verify_admin_key, security_logger
        request = MagicMock()
        request.headers = {}
        initial_count = len(security_logger.recent(event_type="admin_key_failure"))
        verify_admin_key(request)
        new_count = len(security_logger.recent(event_type="admin_key_failure"))
        assert new_count == initial_count


# ============================================================================
#  T7: Rate Limit Coverage — Code-Level Contract Checks
# ============================================================================

class TestRateLimitProfiles:
    """Verify rate limit profiles exist for critical endpoint categories."""

    def test_phone_check_profile_exists(self):
        from ratelimit import RATE_PROFILES
        assert "phone_check" in RATE_PROFILES
        assert RATE_PROFILES["phone_check"]["limit"] <= 20

    def test_llm_trigger_profile_exists(self):
        from ratelimit import RATE_PROFILES
        assert "llm_trigger" in RATE_PROFILES
        assert RATE_PROFILES["llm_trigger"]["limit"] <= 10

    def test_checkpoint_profile_exists(self):
        from ratelimit import RATE_PROFILES
        assert "checkpoint" in RATE_PROFILES

    def test_search_profile_exists(self):
        from ratelimit import RATE_PROFILES
        assert "search" in RATE_PROFILES

    def test_public_write_profile_exists(self):
        from ratelimit import RATE_PROFILES
        assert "public_write" in RATE_PROFILES


class TestRateLimitUtilities:
    """Test new rate-limit helper functions."""

    def test_check_rate_ip_blocks_after_limit(self):
        from ratelimit import check_rate_ip, _reset
        from fastapi import HTTPException
        _reset()
        for _ in range(5):
            check_rate_ip("10.0.0.1", "test_action", limit=5, window=60)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_ip("10.0.0.1", "test_action", limit=5, window=60)
        assert exc_info.value.status_code == 429
        _reset()

    def test_is_rate_limited_does_not_record(self):
        from ratelimit import is_rate_limited, check_rate, _reset
        _reset()
        check_rate("peek_test", limit=5, window=60)
        assert is_rate_limited("peek_test", limit=5, window=60) is False
        # is_rate_limited should not add a hit
        for _ in range(10):
            is_rate_limited("peek_test", limit=5, window=60)
        assert is_rate_limited("peek_test", limit=5, window=60) is False
        _reset()

    def test_check_rate_profile_enforces_limit(self):
        from ratelimit import check_rate_profile, _reset, RATE_PROFILES
        from fastapi import HTTPException
        _reset()
        profile = "public_write"
        limit = RATE_PROFILES[profile]["limit"]
        for _ in range(limit):
            check_rate_profile("test_user", profile)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_profile("test_user", profile)
        assert exc_info.value.status_code == 429
        _reset()

    def test_check_rate_profile_unknown_profile_noop(self):
        from ratelimit import check_rate_profile
        check_rate_profile("key", "nonexistent_profile")


# ============================================================================
#  T7: Auth Bypass Audit — Code-Level Contract Checks
# ============================================================================

class TestAuthBypassAudit:
    """Verify that write endpoints in social.py and auth.py use auth dependencies."""

    def test_social_create_post_requires_auth(self):
        import social
        src = inspect.getsource(social.create_post)
        assert "require_user" in src or "_get_current_user_or_none" in src

    def test_social_delete_post_requires_auth(self):
        import social
        src = inspect.getsource(social.delete_post)
        assert "require_user" in src or "_get_current_user_or_none" in src

    def test_social_create_comment_requires_auth(self):
        import social
        src = inspect.getsource(social.create_comment)
        assert "require_user" in src or "_get_current_user_or_none" in src

    def test_social_like_requires_auth(self):
        import social
        src = inspect.getsource(social.toggle_like)
        assert "require_user" in src or "_get_current_user_or_none" in src

    def test_social_upload_requires_auth(self):
        import social
        src = inspect.getsource(social.upload_image)
        assert "require_user" in src or "_get_current_user_or_none" in src

    def test_social_create_post_has_rate_limit(self):
        import social
        src = inspect.getsource(social.create_post)
        assert "check_rate" in src

    def test_social_create_comment_has_rate_limit(self):
        import social
        src = inspect.getsource(social.create_comment)
        assert "check_rate" in src

    def test_social_upload_has_rate_limit(self):
        import social
        src = inspect.getsource(social.upload_image)
        assert "check_rate" in src

    def test_auth_set_password_requires_session(self):
        import auth
        src = inspect.getsource(auth.set_password)
        assert "_get_current_user_or_none" in src or "require_user" in src

    def test_auth_logout_references_session(self):
        import auth
        src = inspect.getsource(auth.logout)
        assert "session_token" in src or "_hash_token" in src

    def test_auth_profile_update_requires_session(self):
        import auth
        src = inspect.getsource(auth.update_profile)
        assert "_get_current_user_or_none" in src or "require_user" in src

    def test_auth_profile_update_sanitizes_input(self):
        """Profile update must sanitize user input (XSS prevention)."""
        import auth
        src = inspect.getsource(auth.update_profile)
        assert "html.escape" in src or "escape" in src or "sanitize" in src


class TestAuthPasswordSecurity:
    """Verify password handling security properties."""

    def test_password_uses_pbkdf2_or_bcrypt(self):
        """Password hashing must use a proper KDF."""
        import auth
        src = inspect.getsource(auth)
        has_kdf = ("pbkdf2" in src.lower() or "bcrypt" in src.lower()
                   or "argon2" in src.lower() or "scrypt" in src.lower())
        assert has_kdf, "auth.py must use a proper password KDF (PBKDF2/bcrypt/argon2)"

    def test_set_password_checks_current_password(self):
        """set_password should verify the current password before allowing change."""
        import auth
        src = inspect.getsource(auth.set_password)
        assert "current" in src.lower() or "old" in src.lower() or "verify" in src.lower()


# ============================================================================
#  T7: Input Validation Audit — Server Endpoint Checks
# ============================================================================

class TestChatInputValidation:
    """Verify chat endpoint input validation via source inspection.

    server.py cannot be imported in test env (requires LLM_API_KEY),
    so we inspect the source file directly.
    """

    @pytest.fixture(autouse=True)
    def _load_server_source(self):
        src_path = Path(__file__).resolve().parent.parent / "server.py"
        self.server_src = src_path.read_text(encoding="utf-8")

    def test_chat_request_has_max_length(self):
        """ChatRequest model must constrain message length."""
        assert "max_length" in self.server_src or "maxLength" in self.server_src or \
               "le=" in self.server_src, "ChatRequest.message must have max_length"

    def test_chat_request_has_min_length(self):
        assert "min_length" in self.server_src or "minLength" in self.server_src or \
               "ge=" in self.server_src

    def test_chat_sanitizes_html(self):
        """Chat handler must sanitize HTML from user input."""
        assert "sanitize" in self.server_src.lower() or \
               "escape" in self.server_src.lower() or \
               "_sanitize_message" in self.server_src


class TestAdminAuthGate:
    """Verify admin endpoints are protected."""

    def test_admin_router_has_auth_dependency(self):
        """admin.py router must use require_admin or verify_admin_key."""
        import admin
        src = inspect.getsource(admin)
        assert "require_admin" in src or "verify_admin_key" in src

    def test_admin_rate_limiter_exists(self):
        from middleware import admin_limiter
        assert admin_limiter is not None
        assert admin_limiter.max_requests <= 120


class TestMiddlewareSecurityHeaders:
    """Verify security-related middleware configuration."""

    def test_admin_key_constant_time_comparison(self):
        """verify_admin_key must use hmac.compare_digest (timing-safe)."""
        import middleware
        src = inspect.getsource(middleware.verify_admin_key)
        assert "compare_digest" in src

    def test_admin_key_fail_closed_without_key(self):
        from middleware import verify_admin_key
        request = MagicMock()
        request.headers = {"X-Admin-Key": "any-key"}
        import middleware
        original = middleware.ADMIN_API_KEY
        try:
            middleware.ADMIN_API_KEY = ""
            assert verify_admin_key(request) is False
        finally:
            middleware.ADMIN_API_KEY = original

    def test_client_ip_validates_format(self):
        from middleware import _is_valid_ip
        assert _is_valid_ip("192.168.1.1") is True
        assert _is_valid_ip("::1") is True
        assert _is_valid_ip("not-an-ip") is False
        assert _is_valid_ip("") is False
        assert _is_valid_ip(None) is False

    def test_client_ip_ignores_xff_from_untrusted(self):
        """X-Forwarded-For should only be trusted from known proxies."""
        from middleware import get_client_ip
        request = MagicMock()
        request.client.host = "1.2.3.4"
        request.headers = {"X-Forwarded-For": "10.0.0.1"}
        ip = get_client_ip(request)
        assert ip == "1.2.3.4"  # should NOT use XFF from untrusted source

    def test_client_ip_trusts_xff_from_proxy(self):
        from middleware import get_client_ip, TRUSTED_PROXIES
        request = MagicMock()
        request.client.host = TRUSTED_PROXIES[0] if TRUSTED_PROXIES else "127.0.0.1"
        request.headers = {"X-Forwarded-For": "203.0.113.50"}
        ip = get_client_ip(request)
        assert ip == "203.0.113.50"


# ============================================================================
#  Session Fixation Prevention
# ============================================================================

class TestSessionFixationPrevention:
    """Verify session management prevents fixation attacks."""

    def test_login_generates_new_token(self):
        """Login must generate a fresh token, not reuse an existing one.

        Wave 4 Task 3: token generation now lives in the shared _finish_login
        helper (called from login_password's non-2FA success path) rather than
        inline in login_password itself.
        """
        import auth
        src = inspect.getsource(auth.login_password)
        assert "_finish_login" in src, "login must reach the session-creation helper"
        assert "_generate_token" in inspect.getsource(auth._finish_login), \
            "login must generate a new session token"

    def test_verify_otp_generates_new_token(self):
        """OTP verification must generate a fresh session token.

        Wave 4 Task 3: token generation now lives in the shared _finish_login
        helper (called from verify_otp's non-2FA success path) rather than
        inline in verify_otp itself.
        """
        import auth
        src = inspect.getsource(auth.verify_otp)
        assert "_finish_login" in src, "verify_otp must reach the session-creation helper"
        assert "_generate_token" in inspect.getsource(auth._finish_login), \
            "verify_otp must generate a new session token"

    def test_set_password_revokes_other_sessions(self):
        """Password change should revoke other sessions."""
        import auth
        src = inspect.getsource(auth.set_password)
        assert "DELETE" in src.upper() or "delete" in src or "revoke" in src.lower()


# ============================================================================
#  Moderation Integration Checks
# ============================================================================

class TestModerationCoverage:
    """Verify moderation coverage across UGC write paths."""

    def test_create_post_calls_moderation(self):
        import social
        src = inspect.getsource(social.create_post)
        assert "moderate_content" in src or "moderation" in src

    def test_update_post_calls_moderation(self):
        """Post updates with content changes should re-run moderation."""
        import social
        src = inspect.getsource(social.update_post)
        assert "moderate_content" in src or "moderation" in src

    def test_image_upload_has_size_limit(self):
        import social
        src = inspect.getsource(social.upload_image)
        assert "MAX_IMAGE" in src or "max_size" in src.lower() or "5 * 1024" in src or "5_000_000" in src or "5242880" in src
