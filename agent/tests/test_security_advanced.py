"""
Advanced security layer tests — Round 4 depth:

  Layer 15: Account lockout mechanism
  Layer 16: Content-Type enforcement, secure cookies, CORS validation
  Layer 17: JWT token validation, request deduplication
  Layer 18: Honeypot/canary endpoints, circuit breaker
  Layer 19: Unified abuse scoring, geo-anomaly detection
  Layer 20: Text obfuscation detection, targeted harassment detection
  Layer 21: Rate limit exemptions, load-aware rate limiting

All tests are pure-logic (no DB, no LLM, no network).
"""

import base64
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================================
#  Layer 15: Account Lockout
# ============================================================================

class TestAccountLockout:
    """Test account lockout after repeated failed login attempts."""

    def setup_method(self):
        from auth_middleware import _reset_lockouts
        _reset_lockouts()

    def test_single_failure_not_locked(self):
        from auth_middleware import record_login_failure
        result = record_login_failure("user@example.com")
        assert result["locked"] is False
        assert result["remaining_attempts"] > 0

    def test_lockout_after_threshold(self):
        from auth_middleware import record_login_failure, LOCKOUT_THRESHOLD
        for _ in range(LOCKOUT_THRESHOLD):
            result = record_login_failure("victim@example.com")
        assert result["locked"] is True
        assert result["remaining_attempts"] == 0
        assert result["lockout_until"] is not None

    def test_is_account_locked(self):
        from auth_middleware import record_login_failure, is_account_locked, LOCKOUT_THRESHOLD
        ident = "locked_user"
        for _ in range(LOCKOUT_THRESHOLD):
            record_login_failure(ident)
        assert is_account_locked(ident) is True

    def test_not_locked_initially(self):
        from auth_middleware import is_account_locked
        assert is_account_locked("fresh_user") is False

    def test_clear_login_failures(self):
        from auth_middleware import record_login_failure, clear_login_failures, LOCKOUT_THRESHOLD
        ident = "cleared_user"
        for _ in range(LOCKOUT_THRESHOLD - 1):
            record_login_failure(ident)
        clear_login_failures(ident)
        result = record_login_failure(ident)
        assert result["locked"] is False

    def test_different_accounts_independent(self):
        from auth_middleware import record_login_failure, is_account_locked, LOCKOUT_THRESHOLD
        for _ in range(LOCKOUT_THRESHOLD):
            record_login_failure("user_a")
        assert is_account_locked("user_a") is True
        assert is_account_locked("user_b") is False

    def test_remaining_attempts_decreases(self):
        from auth_middleware import record_login_failure, _reset_lockouts
        _reset_lockouts()
        r1 = record_login_failure("counter_user")
        r2 = record_login_failure("counter_user")
        assert r2["remaining_attempts"] < r1["remaining_attempts"]


# ============================================================================
#  Layer 16: Content-Type Enforcement
# ============================================================================

class TestContentTypeEnforcement:
    """Test Content-Type validation for request bodies."""

    def test_json_content_type_valid(self):
        from auth_middleware import validate_content_type
        result = validate_content_type("application/json", "json")
        assert result["valid"] is True

    def test_json_with_charset_valid(self):
        from auth_middleware import validate_content_type
        result = validate_content_type("application/json; charset=utf-8", "json")
        assert result["valid"] is True

    def test_html_rejected_for_json(self):
        from auth_middleware import validate_content_type
        result = validate_content_type("text/html", "json")
        assert result["valid"] is False

    def test_multipart_valid(self):
        from auth_middleware import validate_content_type
        result = validate_content_type("multipart/form-data; boundary=---", "multipart")
        assert result["valid"] is True

    def test_missing_content_type(self):
        from auth_middleware import validate_content_type
        result = validate_content_type("", "json")
        assert result["valid"] is False


# ============================================================================
#  Layer 16: Secure Cookie Configuration
# ============================================================================

class TestSecureCookieConfig:
    """Test secure cookie parameter generation."""

    def test_dev_cookies_have_httponly(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params(is_production=False)
        assert params["httponly"] is True
        assert params["samesite"] == "lax"

    def test_prod_cookies_have_secure(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params(is_production=True)
        assert params["secure"] is True
        assert params["httponly"] is True

    def test_prod_cookies_have_domain(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params(is_production=True)
        assert "domain" in params

    def test_cookies_have_max_age(self):
        from auth_middleware import get_secure_cookie_params
        params = get_secure_cookie_params()
        assert params["max_age"] > 0


# ============================================================================
#  Layer 16: CORS Origin Validation
# ============================================================================

class TestCORSValidation:
    """Test CORS origin validation."""

    def test_allowed_origin_passes(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("https://vinhlong360.com")
        assert result["allowed"] is True

    def test_localhost_dev_allowed(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("http://localhost:3000", is_production=False)
        assert result["allowed"] is True

    def test_localhost_prod_blocked(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("http://localhost:3000", is_production=True)
        assert result["allowed"] is False

    def test_unknown_origin_blocked(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("https://evil.com")
        assert result["allowed"] is False

    def test_subdomain_pattern_allowed(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("https://staging.vinhlong360.com")
        assert result["allowed"] is True

    def test_missing_origin_blocked(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("")
        assert result["allowed"] is False

    def test_vercel_preview_allowed(self):
        from auth_middleware import validate_cors_origin
        result = validate_cors_origin("https://vinhlong360-abc123.vercel.app")
        assert result["allowed"] is True


# ============================================================================
#  Layer 17: JWT Token Structure Validation
# ============================================================================

class TestJWTValidation:
    """Test JWT token structure validation."""

    def _make_jwt(self, header: dict, payload: dict, sig: str = "fakesig") -> str:
        h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{h}.{p}.{sig}"

    def test_valid_jwt_structure(self):
        from auth_middleware import validate_token_structure
        token = self._make_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {"sub": "user1", "exp": time.time() + 3600}
        )
        result = validate_token_structure(token)
        assert result["valid"] is True
        assert result["claims"]["sub"] == "user1"

    def test_alg_none_attack_detected(self):
        from auth_middleware import validate_token_structure
        token = self._make_jwt(
            {"alg": "none", "typ": "JWT"},
            {"sub": "admin", "exp": time.time() + 3600}
        )
        result = validate_token_structure(token)
        assert result["valid"] is False
        assert "alg_none_attack" in result["issues"]

    def test_expired_token_detected(self):
        from auth_middleware import validate_token_structure
        token = self._make_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {"sub": "user1", "exp": time.time() - 3600}
        )
        result = validate_token_structure(token)
        assert "token_expired" in result["issues"]

    def test_no_expiry_flagged(self):
        from auth_middleware import validate_token_structure
        token = self._make_jwt(
            {"alg": "HS256", "typ": "JWT"},
            {"sub": "user1"}
        )
        result = validate_token_structure(token)
        assert "no_expiry" in result["issues"]

    def test_empty_token_rejected(self):
        from auth_middleware import validate_token_structure
        result = validate_token_structure("")
        assert result["valid"] is False

    def test_invalid_format_rejected(self):
        from auth_middleware import validate_token_structure
        result = validate_token_structure("not.a.valid.jwt.token")
        assert result["valid"] is False

    def test_two_parts_rejected(self):
        from auth_middleware import validate_token_structure
        result = validate_token_structure("header.payload")
        assert result["valid"] is False


# ============================================================================
#  Layer 17: Request Deduplication
# ============================================================================

class TestRequestDeduplication:
    """Test idempotency key deduplication."""

    def setup_method(self):
        from auth_middleware import _reset_idempotency
        _reset_idempotency()

    def test_first_request_not_duplicate(self):
        from auth_middleware import check_idempotency
        result = check_idempotency("key-001")
        assert result["is_duplicate"] is False

    def test_second_request_is_duplicate(self):
        from auth_middleware import check_idempotency
        check_idempotency("key-002")
        result = check_idempotency("key-002")
        assert result["is_duplicate"] is True

    def test_different_keys_independent(self):
        from auth_middleware import check_idempotency
        check_idempotency("key-a")
        result = check_idempotency("key-b")
        assert result["is_duplicate"] is False

    def test_empty_key_not_checked(self):
        from auth_middleware import check_idempotency
        result = check_idempotency("")
        assert result["is_duplicate"] is False

    def test_first_seen_timestamp(self):
        from auth_middleware import check_idempotency
        result = check_idempotency("key-ts")
        assert result["first_seen"] is not None
        assert result["first_seen"] > 0


# ============================================================================
#  Layer 18: Honeypot / Canary Endpoints
# ============================================================================

class TestHoneypotEndpoints:
    """Test honeypot endpoint detection."""

    def setup_method(self):
        from middleware import honeypot, ip_reputation
        honeypot._reset()
        ip_reputation._reset()

    def test_normal_path_not_honeypot(self):
        from middleware import honeypot
        result = honeypot.check("/api/users/123", "10.0.0.1")
        assert result["is_honeypot"] is False

    def test_phpmyadmin_is_honeypot(self):
        from middleware import honeypot
        result = honeypot.check("/phpmyadmin", "10.0.0.1")
        assert result["is_honeypot"] is True

    def test_wp_login_is_honeypot(self):
        from middleware import honeypot
        result = honeypot.check("/wp-login.php", "10.0.0.1")
        assert result["is_honeypot"] is True

    def test_env_file_is_honeypot(self):
        from middleware import honeypot
        result = honeypot.check("/.env", "10.0.0.1")
        assert result["is_honeypot"] is True

    def test_git_config_is_honeypot(self):
        from middleware import honeypot
        result = honeypot.check("/.git/config", "10.0.0.1")
        assert result["is_honeypot"] is True

    def test_honeypot_escalates_reputation(self):
        from middleware import honeypot, ip_reputation
        ip = "10.99.0.1"
        honeypot.check("/phpmyadmin", ip)
        honeypot.check("/.env", ip)
        honeypot.check("/.git/config", ip)
        assert ip_reputation.threat_level(ip) >= 1

    def test_get_scanner_ips(self):
        from middleware import honeypot
        honeypot.check("/wp-login.php", "10.1.1.1")
        scanners = honeypot.get_scanner_ips()
        assert "10.1.1.1" in scanners

    def test_stats_returns_structure(self):
        from middleware import honeypot
        honeypot.check("/phpmyadmin", "10.0.0.1")
        stats = honeypot.stats()
        assert "tracked_ips" in stats
        assert "total_hits" in stats
        assert stats["total_hits"] >= 1


# ============================================================================
#  Layer 18: Circuit Breaker
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker for downstream service protection."""

    def setup_method(self):
        from middleware import cb_moderation_api
        cb_moderation_api._reset()

    def test_initial_state_closed(self):
        from middleware import cb_moderation_api
        assert cb_moderation_api.state == "closed"
        assert cb_moderation_api.allow_request() is True

    def test_opens_after_failures(self):
        from middleware import cb_moderation_api
        for _ in range(cb_moderation_api.failure_threshold):
            cb_moderation_api.record_failure()
        assert cb_moderation_api.state == "open"
        assert cb_moderation_api.allow_request() is False

    def test_success_resets_failures(self):
        from middleware import cb_moderation_api
        cb_moderation_api.record_failure()
        cb_moderation_api.record_failure()
        cb_moderation_api.record_success()
        assert cb_moderation_api.state == "closed"

    def test_stats_returns_structure(self):
        from middleware import cb_moderation_api
        stats = cb_moderation_api.stats()
        assert "name" in stats
        assert "state" in stats
        assert stats["name"] == "moderation_api"

    def test_half_open_success_closes(self):
        from middleware import CircuitBreaker
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0, success_threshold=1)
        cb.record_failure()
        cb.record_failure()
        # recovery_timeout=0 → immediately transitions to half_open on next state check
        assert cb.state == "half_open"
        cb.record_success()
        assert cb.state == "closed"

    def test_half_open_failure_reopens(self):
        from middleware import CircuitBreaker
        cb = CircuitBreaker("test2", failure_threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        # Trigger half_open transition
        assert cb.state == "half_open"
        cb.record_failure()
        # half_open + failure → back to open
        # But recovery_timeout=0 means it immediately transitions again
        # The important check: allow_request should be False right after failure in half_open
        # Since timeout=0, state oscillates — check the internal _state via stats
        stats = cb.stats()
        assert stats["state"] == "open"


# ============================================================================
#  Layer 19: Unified Abuse Scoring
# ============================================================================

class TestAbuseScoring:
    """Test unified abuse score calculator."""

    def setup_method(self):
        from middleware import ip_reputation, credential_stuffing, event_correlator, honeypot
        ip_reputation._reset()
        credential_stuffing._reset()
        event_correlator._reset()
        honeypot._reset()

    def test_clean_ip_low_score(self):
        from middleware import abuse_score
        result = abuse_score.calculate("1.2.3.4")
        assert result["score"] == 0
        assert result["level"] == "clean"

    def test_hostile_ip_high_score(self):
        from middleware import abuse_score, ip_reputation
        ip = "10.99.0.1"
        for _ in range(10):
            ip_reputation.record(ip, "admin_key_failure")
        result = abuse_score.calculate(ip)
        assert result["score"] > 0
        assert result["level"] in ("elevated", "high", "critical")

    def test_honeypot_hit_increases_score(self):
        from middleware import abuse_score, honeypot
        ip = "10.88.0.1"
        honeypot.check("/phpmyadmin", ip)
        result = abuse_score.calculate(ip)
        assert result["score"] > 0
        assert result["signals"]["honeypot_hits"] > 0

    def test_bot_signal_increases_score(self):
        from middleware import abuse_score
        result = abuse_score.calculate("1.2.3.4", extra_signals={"is_bot": True})
        assert result["score"] > 0
        assert result["signals"].get("bot_detection", 0) > 0

    def test_score_capped_at_100(self):
        from middleware import abuse_score, ip_reputation, honeypot, credential_stuffing
        ip = "10.77.0.1"
        for _ in range(10):
            ip_reputation.record(ip, "admin_key_failure")
        honeypot.check("/phpmyadmin", ip)
        for i in range(6):
            credential_stuffing.record_failure(ip, f"user_{i}")
        result = abuse_score.calculate(ip)
        assert result["score"] <= 100

    def test_signals_dict_included(self):
        from middleware import abuse_score
        result = abuse_score.calculate("5.6.7.8")
        assert "signals" in result
        assert isinstance(result["signals"], dict)


# ============================================================================
#  Layer 19: Geo-Anomaly Detection
# ============================================================================

class TestGeoAnomalyDetection:
    """Test impossible travel detection."""

    def setup_method(self):
        from middleware import geo_anomaly
        geo_anomaly._reset()

    def test_first_login_not_suspicious(self):
        from middleware import geo_anomaly
        result = geo_anomaly.check_login("user1", "192.168.1.1")
        assert result["suspicious"] is False

    def test_same_ip_class_not_suspicious(self):
        from middleware import geo_anomaly
        geo_anomaly.check_login("user2", "192.168.1.1")
        result = geo_anomaly.check_login("user2", "192.168.1.50")
        assert result["suspicious"] is False

    def test_different_ip_class_suspicious(self):
        from middleware import geo_anomaly
        geo_anomaly.check_login("user3", "192.168.1.1")
        result = geo_anomaly.check_login("user3", "10.0.1.1")
        assert result["suspicious"] is True
        assert result["reason"] == "ip_class_change"

    def test_different_users_independent(self):
        from middleware import geo_anomaly
        geo_anomaly.check_login("userA", "192.168.1.1")
        result = geo_anomaly.check_login("userB", "10.0.1.1")
        assert result["suspicious"] is False

    def test_empty_user_not_checked(self):
        from middleware import geo_anomaly
        result = geo_anomaly.check_login("", "192.168.1.1")
        assert result["suspicious"] is False

    def test_returns_elapsed_seconds(self):
        from middleware import geo_anomaly
        geo_anomaly.check_login("user5", "192.168.1.1")
        result = geo_anomaly.check_login("user5", "10.0.1.1")
        if result["suspicious"]:
            assert "elapsed_seconds" in result


# ============================================================================
#  Layer 20: Text Obfuscation Detection
# ============================================================================

class TestTextObfuscation:
    """Test text obfuscation technique detection."""

    def test_normal_text_not_obfuscated(self):
        from moderation import detect_text_obfuscation
        result = detect_text_obfuscation("Du lịch Vĩnh Long rất đẹp")
        assert result["is_obfuscated"] is False

    def test_zero_width_chars_detected(self):
        from moderation import detect_text_obfuscation
        text = "cas​ino​ online"  # zero-width space inside words
        result = detect_text_obfuscation(text)
        assert result["is_obfuscated"] is True
        assert "zero_width_chars" in result["techniques"]

    def test_letter_spacing_detected(self):
        from moderation import detect_text_obfuscation
        text = "c a s i n o online"
        result = detect_text_obfuscation(text)
        assert result["is_obfuscated"] is True
        assert "letter_spacing" in result["techniques"]

    def test_fullwidth_chars_detected(self):
        from moderation import detect_text_obfuscation
        text = "ｃａｓｉｎｏ online"
        result = detect_text_obfuscation(text)
        assert result["is_obfuscated"] is True
        assert "fullwidth_chars" in result["techniques"]

    def test_short_text_not_checked(self):
        from moderation import detect_text_obfuscation
        result = detect_text_obfuscation("hi")
        assert result["is_obfuscated"] is False

    def test_deobfuscate_zero_width(self):
        from moderation import deobfuscate_text
        text = "cas​ino"
        result = deobfuscate_text(text)
        assert "​" not in result

    def test_deobfuscate_leetspeak(self):
        from moderation import deobfuscate_text
        result = deobfuscate_text("c@sin0")
        assert result == "casino"

    def test_deobfuscate_fullwidth(self):
        from moderation import deobfuscate_text
        result = deobfuscate_text("ｈｅｌｌｏ")
        assert result == "hello"

    def test_deobfuscate_empty(self):
        from moderation import deobfuscate_text
        assert deobfuscate_text("") == ""
        assert deobfuscate_text(None) == ""

    def test_obfuscation_wired_into_enhanced_pipeline(self):
        """detect_text_obfuscation must be called inside moderate_content_enhanced."""
        import inspect
        from moderation import moderate_content_enhanced
        src = inspect.getsource(moderate_content_enhanced)
        assert "detect_text_obfuscation" in src, "Obfuscation detection must be wired into enhanced pipeline"


# ============================================================================
#  Layer 20: Targeted Harassment Detection
# ============================================================================

class TestTargetedHarassment:
    """Test repeated harassment detection between users."""

    def setup_method(self):
        from moderation import _reset_harassment_tracking
        _reset_harassment_tracking()

    def test_single_interaction_not_harassment(self):
        from moderation import check_targeted_harassment
        result = check_targeted_harassment("author1", "target1", "comment")
        assert result["is_harassment"] is False

    def test_repeated_targeting_detected(self):
        from moderation import check_targeted_harassment
        for _ in range(5):
            result = check_targeted_harassment("bully", "victim", "mean comment")
        assert result["is_harassment"] is True
        assert result["interaction_count"] >= 5

    def test_same_user_not_counted(self):
        from moderation import check_targeted_harassment
        result = check_targeted_harassment("user1", "user1", "self-reply")
        assert result["is_harassment"] is False

    def test_different_targets_independent(self):
        from moderation import check_targeted_harassment, _reset_harassment_tracking
        _reset_harassment_tracking()
        for _ in range(5):
            check_targeted_harassment("author", "target_a", "msg")
        result = check_targeted_harassment("author", "target_b", "msg")
        assert result["interaction_count"] == 1

    def test_empty_ids_not_checked(self):
        from moderation import check_targeted_harassment
        result = check_targeted_harassment("", "target", "msg")
        assert result["is_harassment"] is False

    def test_score_increases_with_count(self):
        from moderation import check_targeted_harassment, _reset_harassment_tracking
        _reset_harassment_tracking()
        r1 = check_targeted_harassment("a", "b", "msg")
        check_targeted_harassment("a", "b", "msg")
        r3 = check_targeted_harassment("a", "b", "msg")
        assert r3["score"] > r1["score"]


# ============================================================================
#  Layer 21: Rate Limit Exemptions
# ============================================================================

class TestRateLimitExemptions:
    """Test rate limit exemption list."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_exempt_ip_bypasses_limit(self):
        from ratelimit import add_rate_limit_exemption, check_rate_with_exemption, _reset
        _reset()
        add_rate_limit_exemption(ip="10.0.0.1")
        # Should not raise even though limit would be exceeded
        for _ in range(20):
            check_rate_with_exemption("test", "10.0.0.1", limit=5, window=60)

    def test_non_exempt_ip_still_limited(self):
        from ratelimit import check_rate_with_exemption, _reset
        from fastapi import HTTPException
        _reset()
        for _ in range(5):
            check_rate_with_exemption("test2", "10.0.0.2", limit=5, window=60)
        with pytest.raises(HTTPException):
            check_rate_with_exemption("test2", "10.0.0.2", limit=5, window=60)

    def test_remove_exemption(self):
        from ratelimit import add_rate_limit_exemption, remove_rate_limit_exemption, is_exempt
        add_rate_limit_exemption(ip="10.0.0.3")
        assert is_exempt(ip="10.0.0.3") is True
        remove_rate_limit_exemption(ip="10.0.0.3")
        assert is_exempt(ip="10.0.0.3") is False

    def test_exempt_by_key(self):
        from ratelimit import add_rate_limit_exemption, is_exempt
        add_rate_limit_exemption(key="admin:master")
        assert is_exempt(key="admin:master") is True
        assert is_exempt(key="user:regular") is False


# ============================================================================
#  Layer 21: Load-Aware Rate Limiting
# ============================================================================

class TestLoadAwareRateLimiting:
    """Test dynamic rate limiting based on server load."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_normal_load_full_limit(self):
        from ratelimit import check_rate_load_aware, set_load_multiplier, _reset
        _reset()
        set_load_multiplier(1.0)
        for _ in range(10):
            check_rate_load_aware("load_test", base_limit=10, base_window=60)

    def test_high_load_reduces_limit(self):
        from ratelimit import check_rate_load_aware, set_load_multiplier, _reset
        from fastapi import HTTPException
        _reset()
        set_load_multiplier(0.5)  # 50% of normal
        for _ in range(5):
            check_rate_load_aware("load_test2", base_limit=10, base_window=60)
        with pytest.raises(HTTPException):
            check_rate_load_aware("load_test2", base_limit=10, base_window=60)

    def test_multiplier_clamped(self):
        from ratelimit import set_load_multiplier, get_load_multiplier, _reset
        _reset()
        set_load_multiplier(10.0)
        assert get_load_multiplier() == 2.0
        set_load_multiplier(0.001)
        assert get_load_multiplier() == 0.1

    def test_reset_restores_multiplier(self):
        from ratelimit import set_load_multiplier, get_load_multiplier, _reset
        set_load_multiplier(0.5)
        _reset()
        assert get_load_multiplier() == 1.0


# ============================================================================
#  Layer 16+17: Rate Limit Headers
# ============================================================================

class TestRateLimitHeaders:
    """Test standard rate-limit response headers."""

    def test_builds_headers(self):
        from auth_middleware import build_rate_limit_headers
        headers = build_rate_limit_headers(limit=100, remaining=95, reset_seconds=60)
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "95"
        assert headers["X-RateLimit-Reset"] == "60"

    def test_retry_after_when_exhausted(self):
        from auth_middleware import build_rate_limit_headers
        headers = build_rate_limit_headers(limit=100, remaining=0, reset_seconds=30)
        assert headers["Retry-After"] == "30"

    def test_no_retry_after_when_remaining(self):
        from auth_middleware import build_rate_limit_headers
        headers = build_rate_limit_headers(limit=100, remaining=50, reset_seconds=60)
        assert headers["Retry-After"] == ""

    def test_remaining_never_negative(self):
        from auth_middleware import build_rate_limit_headers
        headers = build_rate_limit_headers(limit=10, remaining=-5, reset_seconds=60)
        assert headers["X-RateLimit-Remaining"] == "0"
