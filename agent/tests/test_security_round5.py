"""
Ultra-deep security layer tests — Round 5:

  Layer 22: Referrer validation, API key format validation
  Layer 23: IP access lists (allow/deny), nonce replay prevention
  Layer 24: Permission boundary (RBAC), webhook signature verification
  Layer 25: Privilege escalation guard
  Layer 26: Abuse escalation engine, security metrics aggregator
  Layer 27: Request forensics, behavioral fingerprinting
  Layer 28: Penalty box, sliding window counter, rate limit callbacks
  Layer 29: Content policy engine, response body scanning
  Layer 30: Edit abuse detection, language anomaly detection

All tests are pure-logic (no DB, no LLM, no network).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ══════════════════════════════════════════════════
#  REFERRER VALIDATION
# ══════════════════════════════════════════════════

class TestReferrerValidation:
    def test_valid_referrer_main_domain(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("https://vinhlong360.com/page")
        assert r["valid"] is True

    def test_valid_referrer_www(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("https://www.vinhlong360.com/page")
        assert r["valid"] is True

    def test_valid_referrer_subdomain(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("https://api.vinhlong360.com/v1/test")
        assert r["valid"] is True
        assert r["reason"] == "subdomain_match"

    def test_valid_referrer_localhost_dev(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("http://localhost:3000/dashboard")
        assert r["valid"] is True

    def test_invalid_referrer_unknown_host(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("https://evil.com/phishing")
        assert r["valid"] is False
        assert r["reason"] == "unknown_referrer"

    def test_missing_referrer(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("")
        assert r["valid"] is False
        assert r["reason"] == "missing_referrer"

    def test_localhost_blocked_in_production(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("http://localhost:3000/test", is_production=True)
        assert r["valid"] is False
        assert r["reason"] == "localhost_in_production"

    def test_unparseable_referrer(self):
        from auth_middleware import validate_referrer
        r = validate_referrer("://not-a-url")
        # urlparse handles most strings, so this may or may not fail
        # at minimum it should not crash
        assert "valid" in r


# ══════════════════════════════════════════════════
#  API KEY FORMAT VALIDATION
# ══════════════════════════════════════════════════

class TestAPIKeyValidation:
    def test_valid_generic_key(self):
        from auth_middleware import validate_api_key_format
        key = "abcdefghijklmnopqrstuvwxyz123456"
        r = validate_api_key_format(key)
        assert r["valid"] is True
        assert r["issues"] == []

    def test_valid_vl360_key(self):
        from auth_middleware import validate_api_key_format
        key = "vl360_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        r = validate_api_key_format(key, key_type="vl360")
        assert r["valid"] is True

    def test_empty_key(self):
        from auth_middleware import validate_api_key_format
        r = validate_api_key_format("")
        assert r["valid"] is False
        assert "empty_key" in r["issues"]

    def test_too_short_key(self):
        from auth_middleware import validate_api_key_format
        r = validate_api_key_format("short")
        assert r["valid"] is False
        assert "too_short" in r["issues"]

    def test_low_entropy_key(self):
        from auth_middleware import validate_api_key_format
        key = "aaaaaaaaaaaaaaaaaaaaaa"  # 22 chars but only 1 unique
        r = validate_api_key_format(key)
        assert "low_entropy" in r["issues"]

    def test_placeholder_key(self):
        from auth_middleware import validate_api_key_format
        r = validate_api_key_format("test_key")
        assert "placeholder_key" in r["issues"]


# ══════════════════════════════════════════════════
#  IP ACCESS LISTS
# ══════════════════════════════════════════════════

class TestIPAccessList:
    def setup_method(self):
        from auth_middleware import _reset_ip_access
        _reset_ip_access()

    def test_default_allow(self):
        from auth_middleware import check_ip_access
        r = check_ip_access("1.2.3.4")
        assert r["allowed"] is True
        assert r["reason"] == "default_allow"

    def test_deny_ip(self):
        from auth_middleware import add_ip_rule, check_ip_access
        add_ip_rule("1.2.3.4", "deny")
        r = check_ip_access("1.2.3.4")
        assert r["allowed"] is False
        assert r["reason"] == "ip_denied"

    def test_allow_overrides_deny(self):
        from auth_middleware import add_ip_rule, check_ip_access
        add_ip_rule("1.2.3.4", "deny")
        add_ip_rule("1.2.3.4", "allow")
        r = check_ip_access("1.2.3.4")
        assert r["allowed"] is True

    def test_allowlist_mode(self):
        from auth_middleware import add_ip_rule, check_ip_access
        add_ip_rule("10.0.0.1", "allow")
        r = check_ip_access("1.2.3.4")
        assert r["allowed"] is False
        assert r["reason"] == "ip_not_in_allowlist"

    def test_remove_rule(self):
        from auth_middleware import add_ip_rule, remove_ip_rule, check_ip_access
        add_ip_rule("1.2.3.4", "deny")
        remove_ip_rule("1.2.3.4")
        r = check_ip_access("1.2.3.4")
        assert r["allowed"] is True

    def test_loopback_allowed(self):
        from auth_middleware import check_ip_access
        r = check_ip_access("127.0.0.1")
        assert r["allowed"] is True
        assert r["reason"] == "loopback"

    def test_missing_ip(self):
        from auth_middleware import check_ip_access
        r = check_ip_access("")
        assert r["allowed"] is False


# ══════════════════════════════════════════════════
#  NONCE REPLAY PREVENTION
# ══════════════════════════════════════════════════

class TestNonceReplayPrevention:
    def setup_method(self):
        from auth_middleware import _reset_nonces
        _reset_nonces()

    def test_fresh_nonce_valid(self):
        from auth_middleware import generate_nonce, verify_nonce
        nonce = generate_nonce()
        r = verify_nonce(nonce)
        assert r["valid"] is True

    def test_reused_nonce_rejected(self):
        from auth_middleware import generate_nonce, verify_nonce
        nonce = generate_nonce()
        verify_nonce(nonce)
        r = verify_nonce(nonce)
        assert r["valid"] is False
        assert r["reason"] == "nonce_reused"

    def test_empty_nonce_rejected(self):
        from auth_middleware import verify_nonce
        r = verify_nonce("")
        assert r["valid"] is False
        assert r["reason"] == "missing_nonce"

    def test_short_nonce_rejected(self):
        from auth_middleware import verify_nonce
        r = verify_nonce("abc")
        assert r["valid"] is False
        assert r["reason"] == "nonce_too_short"

    def test_generate_nonce_length(self):
        from auth_middleware import generate_nonce
        nonce = generate_nonce()
        assert len(nonce) == 32  # hex of 16 bytes

    def test_multiple_unique_nonces(self):
        from auth_middleware import generate_nonce, verify_nonce
        nonces = [generate_nonce() for _ in range(10)]
        assert len(set(nonces)) == 10  # all unique
        for n in nonces:
            r = verify_nonce(n)
            assert r["valid"] is True


# ══════════════════════════════════════════════════
#  PERMISSION BOUNDARY (RBAC)
# ══════════════════════════════════════════════════

class TestPermissionBoundary:
    def test_admin_can_access_moderator(self):
        from auth_middleware import check_permission_boundary
        r = check_permission_boundary("admin", "moderator")
        assert r["allowed"] is True

    def test_user_cannot_access_admin(self):
        from auth_middleware import check_permission_boundary
        r = check_permission_boundary("user", "admin")
        assert r["allowed"] is False

    def test_same_role_allowed(self):
        from auth_middleware import check_permission_boundary
        r = check_permission_boundary("editor", "editor")
        assert r["allowed"] is True

    def test_guest_minimal_access(self):
        from auth_middleware import check_permission_boundary
        r = check_permission_boundary("guest", "user")
        assert r["allowed"] is False

    def test_superadmin_can_access_everything(self):
        from auth_middleware import check_permission_boundary
        for role in ["admin", "moderator", "editor", "user", "guest"]:
            r = check_permission_boundary("superadmin", role)
            assert r["allowed"] is True

    def test_unknown_role_gets_zero(self):
        from auth_middleware import check_permission_boundary
        r = check_permission_boundary("unknown_role", "guest")
        assert r["allowed"] is True
        assert r["user_level"] == 0


# ══════════════════════════════════════════════════
#  WEBHOOK SIGNATURE VERIFICATION
# ══════════════════════════════════════════════════

class TestWebhookSignature:
    def test_valid_signature(self):
        from auth_middleware import verify_webhook_signature
        import hashlib
        import hmac as _hmac
        secret = "webhook_secret_123"
        payload = b'{"event": "test"}'
        sig = _hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        r = verify_webhook_signature(payload, sig, secret)
        assert r["valid"] is True

    def test_invalid_signature(self):
        from auth_middleware import verify_webhook_signature
        r = verify_webhook_signature(b"test", "wrong_sig", "secret")
        assert r["valid"] is False
        assert r["reason"] == "signature_mismatch"

    def test_github_style_prefix(self):
        from auth_middleware import verify_webhook_signature
        import hashlib
        import hmac as _hmac
        secret = "my_secret"
        payload = b'{"action": "push"}'
        sig = "sha256=" + _hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        r = verify_webhook_signature(payload, sig, secret)
        assert r["valid"] is True

    def test_missing_params(self):
        from auth_middleware import verify_webhook_signature
        r = verify_webhook_signature(b"", "", "secret")
        assert r["valid"] is False
        assert r["reason"] == "missing_params"

    def test_sha1_algorithm(self):
        from auth_middleware import verify_webhook_signature
        import hashlib
        import hmac as _hmac
        secret = "secret"
        payload = b"body"
        sig = _hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
        r = verify_webhook_signature(payload, sig, secret, algorithm="sha1")
        assert r["valid"] is True


# ══════════════════════════════════════════════════
#  PRIVILEGE ESCALATION GUARD
# ══════════════════════════════════════════════════

class TestPrivilegeEscalation:
    def test_escalation_detected(self):
        from auth_middleware import check_privilege_escalation
        r = check_privilege_escalation("user", "admin")
        assert r["is_escalation"] is True

    def test_same_level_not_escalation(self):
        from auth_middleware import check_privilege_escalation
        r = check_privilege_escalation("editor", "editor")
        assert r["is_escalation"] is False

    def test_downgrade_not_escalation(self):
        from auth_middleware import check_privilege_escalation
        r = check_privilege_escalation("admin", "user")
        assert r["is_escalation"] is False

    def test_guest_to_superadmin(self):
        from auth_middleware import check_privilege_escalation
        r = check_privilege_escalation("guest", "superadmin")
        assert r["is_escalation"] is True
        assert "guest" in r["reason"]


# ══════════════════════════════════════════════════
#  ABUSE ESCALATION ENGINE
# ══════════════════════════════════════════════════

class TestAbuseEscalation:
    def setup_method(self):
        from middleware import abuse_escalation, ip_reputation
        abuse_escalation._reset()
        ip_reputation._reset()

    def test_clean_score(self):
        from middleware import abuse_escalation
        r = abuse_escalation.evaluate("1.2.3.4", score=10)
        assert r["tier"] == "clean"
        assert r["action"] == "none"
        assert r["should_block"] is False

    def test_warning_tier(self):
        from middleware import abuse_escalation
        r = abuse_escalation.evaluate("1.2.3.4", score=30)
        assert r["tier"] == "warning"
        assert r["action"] == "throttle"

    def test_restrict_tier(self):
        from middleware import abuse_escalation
        r = abuse_escalation.evaluate("1.2.3.4", score=60)
        assert r["tier"] == "restrict"
        assert r["action"] == "restrict"

    def test_block_tier(self):
        from middleware import abuse_escalation
        r = abuse_escalation.evaluate("1.2.3.4", score=85)
        assert r["tier"] == "block"
        assert r["should_block"] is True

    def test_escalation_log(self):
        from middleware import abuse_escalation
        abuse_escalation.evaluate("1.2.3.4", score=50)
        abuse_escalation.evaluate("5.6.7.8", score=80)
        log = abuse_escalation.recent_escalations()
        assert len(log) == 2


# ══════════════════════════════════════════════════
#  SECURITY METRICS AGGREGATOR
# ══════════════════════════════════════════════════

class TestSecurityMetrics:
    def test_snapshot_structure(self):
        from middleware import security_metrics
        snap = security_metrics.snapshot()
        assert "ts" in snap
        assert "ip_reputation_tracked" in snap
        assert "correlator_tracked_ips" in snap
        assert "honeypot_total_hits" in snap
        assert "cb_moderation_state" in snap

    def test_health_check_healthy(self):
        from middleware import security_metrics, cb_moderation_api, cb_vision_api
        cb_moderation_api._reset()
        cb_vision_api._reset()
        h = security_metrics.health_check()
        assert h["healthy"] is True
        assert h["issues"] == []

    def test_health_check_cb_open(self):
        from middleware import security_metrics, cb_moderation_api
        cb_moderation_api._reset()
        for _ in range(5):
            cb_moderation_api.record_failure()
        h = security_metrics.health_check()
        assert "circuit_breaker_moderation_open" in h["issues"]
        cb_moderation_api._reset()


# ══════════════════════════════════════════════════
#  REQUEST FORENSICS
# ══════════════════════════════════════════════════

class TestRequestForensics:
    def setup_method(self):
        from middleware import request_forensics
        request_forensics._reset()

    def test_collect_above_threshold(self):
        from middleware import request_forensics
        collected = request_forensics.maybe_collect(
            ip="1.2.3.4", method="POST", path="/api/login",
            headers={"user-agent": "bot/1.0"},
            abuse_score_val=50, user_id="user1",
        )
        assert collected is True

    def test_skip_below_threshold(self):
        from middleware import request_forensics
        collected = request_forensics.maybe_collect(
            ip="1.2.3.4", method="GET", path="/",
            headers={}, abuse_score_val=10,
        )
        assert collected is False

    def test_retrieve_by_ip(self):
        from middleware import request_forensics
        request_forensics.maybe_collect(
            ip="1.2.3.4", method="POST", path="/api/login",
            headers={"user-agent": "bot"}, abuse_score_val=50,
        )
        request_forensics.maybe_collect(
            ip="5.6.7.8", method="GET", path="/admin",
            headers={}, abuse_score_val=60,
        )
        records = request_forensics.get_records(ip="1.2.3.4")
        assert len(records) == 1
        assert records[0]["ip"] == "1.2.3.4"

    def test_stats(self):
        from middleware import request_forensics
        request_forensics.maybe_collect(
            ip="1.2.3.4", method="POST", path="/api",
            headers={}, abuse_score_val=50,
        )
        s = request_forensics.stats()
        assert s["total_records"] == 1


# ══════════════════════════════════════════════════
#  BEHAVIORAL FINGERPRINTING
# ══════════════════════════════════════════════════

class TestBehavioralFingerprint:
    def setup_method(self):
        from middleware import behavioral_fp
        behavioral_fp._reset()

    def test_no_data_not_bot(self):
        from middleware import behavioral_fp
        r = behavioral_fp.analyze("unknown_ip")
        assert r["is_bot_like"] is False
        assert r["request_count"] == 0

    def test_normal_user_pattern(self):
        from middleware import behavioral_fp
        for i in range(5):
            behavioral_fp.record("user1", f"/page/{i}", "GET", ua_hash="ua1")
        r = behavioral_fp.analyze("user1")
        assert r["is_bot_like"] is False
        assert r["request_count"] == 5

    def test_bot_crawling_pattern(self):
        from middleware import behavioral_fp
        for i in range(120):
            behavioral_fp.record("bot_ip", f"/page/{i}", "GET", ua_hash="ua1")
        r = behavioral_fp.analyze("bot_ip")
        assert r["request_count"] == 120
        assert r["unique_paths"] == 120
        assert "excessive_crawling" in r["reasons"]

    def test_ua_rotation_detected(self):
        from middleware import behavioral_fp
        for i in range(25):
            ua = f"ua_{i % 5}"  # 5 different UAs
            behavioral_fp.record("rotator", "/api", "POST", ua_hash=ua)
        r = behavioral_fp.analyze("rotator")
        assert r["ua_changes"] == 5
        assert "ua_rotation" in r["reasons"]

    def test_get_only_pattern(self):
        from middleware import behavioral_fp
        for i in range(35):
            behavioral_fp.record("scraper", f"/p/{i}", "GET", ua_hash="ua1")
        r = behavioral_fp.analyze("scraper")
        assert "get_only_pattern" in r["reasons"]


# ══════════════════════════════════════════════════
#  PENALTY BOX
# ══════════════════════════════════════════════════

class TestPenaltyBox:
    def setup_method(self):
        import ratelimit
        ratelimit._reset()

    def test_add_to_penalty_box(self):
        from ratelimit import add_to_penalty_box, is_in_penalty_box
        add_to_penalty_box("1.2.3.4", duration=60)
        assert is_in_penalty_box("1.2.3.4") is True

    def test_not_in_penalty_box(self):
        from ratelimit import is_in_penalty_box
        assert is_in_penalty_box("1.2.3.4") is False

    def test_remove_from_penalty_box(self):
        from ratelimit import add_to_penalty_box, remove_from_penalty_box, is_in_penalty_box
        add_to_penalty_box("1.2.3.4", duration=60)
        remove_from_penalty_box("1.2.3.4")
        assert is_in_penalty_box("1.2.3.4") is False

    def test_penalty_blocks_requests(self):
        from ratelimit import add_to_penalty_box, check_rate_with_penalty
        add_to_penalty_box("1.2.3.4", duration=60)
        with pytest.raises(Exception) as exc_info:
            check_rate_with_penalty("test_key", "1.2.3.4", 100, 60)
        assert exc_info.value.status_code == 429

    def test_penalty_auto_on_violations(self):
        from ratelimit import check_rate_with_penalty, is_in_penalty_box
        for _ in range(50):
            try:
                check_rate_with_penalty("penalty_test", "10.0.0.1", 5, 60, penalty_after=3)
            except Exception:
                pass
        assert is_in_penalty_box("10.0.0.1") is True


# ══════════════════════════════════════════════════
#  SLIDING WINDOW COUNTER
# ══════════════════════════════════════════════════

class TestSlidingWindowCounter:
    def setup_method(self):
        import ratelimit
        ratelimit._reset()

    def test_increment_and_count(self):
        from ratelimit import increment_sliding_counter, get_sliding_window_count
        count = increment_sliding_counter("counter1", window=60)
        assert count >= 1
        assert get_sliding_window_count("counter1", 60) >= 1

    def test_multiple_increments(self):
        from ratelimit import increment_sliding_counter
        for _ in range(10):
            increment_sliding_counter("counter2", window=60)
        from ratelimit import get_sliding_window_count
        assert get_sliding_window_count("counter2", 60) == 10

    def test_empty_counter(self):
        from ratelimit import get_sliding_window_count
        assert get_sliding_window_count("nonexistent", 60) == 0


# ══════════════════════════════════════════════════
#  RATE LIMIT CALLBACKS
# ══════════════════════════════════════════════════

class TestRateLimitCallbacks:
    def setup_method(self):
        import ratelimit
        ratelimit._reset()

    def test_callback_fired_on_violation(self):
        from ratelimit import register_rate_limit_callback, check_rate_with_callback
        callback_data = []
        register_rate_limit_callback(lambda k, ip, lim: callback_data.append((k, ip, lim)))

        for _ in range(10):
            try:
                check_rate_with_callback("cb_key", "1.2.3.4", 3, 60)
            except Exception:
                pass

        assert len(callback_data) > 0
        assert callback_data[0][0] == "cb_key"
        assert callback_data[0][1] == "1.2.3.4"

    def test_no_callback_under_limit(self):
        from ratelimit import register_rate_limit_callback, check_rate_with_callback
        import ratelimit
        ratelimit._reset()
        callback_data = []
        register_rate_limit_callback(lambda k, ip, lim: callback_data.append(True))

        check_rate_with_callback("safe_key", "1.2.3.4", 100, 60)
        assert len(callback_data) == 0


# ══════════════════════════════════════════════════
#  CONTENT POLICY ENGINE
# ══════════════════════════════════════════════════

class TestContentPolicyEngine:
    def setup_method(self):
        from moderation import _reset_content_policies
        _reset_content_policies()

    def test_add_and_check_policy(self):
        from moderation import add_content_policy, check_content_policies
        add_content_policy("no_crypto", r"\b(bitcoin|ethereum|crypto)\b", action="flag", score=0.8)
        r = check_content_policies("Invest in bitcoin today!")
        assert r["violated"] is True
        assert r["violations"][0]["policy"] == "no_crypto"
        assert r["action"] == "flag"

    def test_no_violation(self):
        from moderation import add_content_policy, check_content_policies
        add_content_policy("no_drugs", r"\b(drugs|cocaine)\b", action="block")
        r = check_content_policies("Beautiful scenery in Vinh Long")
        assert r["violated"] is False
        assert r["action"] == "none"

    def test_multiple_policies(self):
        from moderation import add_content_policy, check_content_policies
        add_content_policy("no_crypto", r"\bcrypto\b", action="flag", score=0.5)
        add_content_policy("no_gambling", r"\b(casino|betting)\b", action="block", score=0.9)
        r = check_content_policies("Win big at casino with crypto!")
        assert r["violated"] is True
        assert len(r["violations"]) == 2
        assert r["action"] == "block"  # highest priority action

    def test_remove_policy(self):
        from moderation import add_content_policy, remove_content_policy, check_content_policies
        add_content_policy("temp_rule", r"test_word", action="flag")
        assert remove_content_policy("temp_rule") is True
        r = check_content_policies("test_word here")
        assert r["violated"] is False

    def test_list_policies(self):
        from moderation import add_content_policy, list_content_policies
        add_content_policy("rule1", r"pattern1", action="flag")
        add_content_policy("rule2", r"pattern2", action="block")
        policies = list_content_policies()
        assert len(policies) == 2
        assert policies[0]["name"] == "rule1"

    def test_case_insensitive_by_default(self):
        from moderation import add_content_policy, check_content_policies
        add_content_policy("no_spam", r"buy now", action="warn")
        r = check_content_policies("BUY NOW limited offer!")
        assert r["violated"] is True

    def test_empty_content(self):
        from moderation import add_content_policy, check_content_policies
        add_content_policy("rule", r"anything", action="flag")
        r = check_content_policies("")
        assert r["violated"] is False


# ══════════════════════════════════════════════════
#  RESPONSE BODY SCANNING
# ══════════════════════════════════════════════════

class TestResponseBodyScanning:
    def test_detect_password_leak(self):
        from moderation import scan_response_body
        body = '{"user": "admin", "password": "s3cr3t123"}'
        r = scan_response_body(body)
        assert r["has_leak"] is True
        assert "password_leak" in r["leak_types"]

    def test_detect_private_key_leak(self):
        from moderation import scan_response_body
        body = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJ..."
        r = scan_response_body(body)
        assert r["has_leak"] is True
        assert "private_key_leak" in r["leak_types"]

    def test_detect_connection_string(self):
        from moderation import scan_response_body
        body = 'db_url: postgresql://user:pass@host:5432/db'
        r = scan_response_body(body)
        assert r["has_leak"] is True
        assert "connection_string_leak" in r["leak_types"]

    def test_detect_aws_key(self):
        from moderation import scan_response_body
        body = 'key: AKIAIOSFODNN7EXAMPLE'
        r = scan_response_body(body)
        assert r["has_leak"] is True
        assert "aws_key_leak" in r["leak_types"]

    def test_clean_response(self):
        from moderation import scan_response_body
        body = '{"status": "ok", "message": "Tour created successfully"}'
        r = scan_response_body(body)
        assert r["has_leak"] is False

    def test_redact_leaks(self):
        from moderation import redact_response_leaks
        body = 'config: postgresql://admin:hunter2@db.local/prod'
        result = redact_response_leaks(body)
        assert "hunter2" not in result
        assert "[REDACTED]" in result

    def test_empty_body(self):
        from moderation import scan_response_body
        r = scan_response_body("")
        assert r["has_leak"] is False


# ══════════════════════════════════════════════════
#  EDIT ABUSE DETECTION
# ══════════════════════════════════════════════════

class TestEditAbuseDetection:
    def setup_method(self):
        from moderation import _reset_content_versions
        _reset_content_versions()

    def test_single_edit_not_abuse(self):
        from moderation import check_edit_abuse
        r = check_edit_abuse("post_1", "Hello world")
        assert r["is_abuse"] is False
        assert r["edit_count"] == 1

    def test_rapid_edits_detected(self):
        from moderation import check_edit_abuse
        for i in range(6):
            r = check_edit_abuse("post_2", f"Version {i}")
        assert r["is_abuse"] is True
        assert r["edit_count"] >= 5

    def test_same_content_not_counted(self):
        from moderation import check_edit_abuse
        for _ in range(10):
            r = check_edit_abuse("post_3", "Same content every time")
        assert r["is_abuse"] is False

    def test_velocity_calculated(self):
        from moderation import check_edit_abuse
        for i in range(3):
            check_edit_abuse("post_4", f"Edit {i}")
        r = check_edit_abuse("post_4", "Edit final")
        assert r["velocity"] > 0

    def test_empty_params(self):
        from moderation import check_edit_abuse
        r = check_edit_abuse("", "content")
        assert r["is_abuse"] is False


# ══════════════════════════════════════════════════
#  LANGUAGE ANOMALY DETECTION
# ══════════════════════════════════════════════════

class TestLanguageAnomaly:
    def test_normal_vietnamese_text(self):
        from moderation import detect_language_anomaly
        r = detect_language_anomaly("Xin chào, đây là bài viết về Vĩnh Long")
        assert r["is_anomalous"] is False

    def test_cyrillic_detected(self):
        from moderation import detect_language_anomaly
        r = detect_language_anomaly("Привет мир это тест контент")
        assert r["is_anomalous"] is True
        assert "cyrillic" in r["unexpected"]

    def test_arabic_detected(self):
        from moderation import detect_language_anomaly
        r = detect_language_anomaly("هذا النص باللغة العربية للاختبار")
        assert r["is_anomalous"] is True
        assert "arabic" in r["unexpected"]

    def test_short_content_ignored(self):
        from moderation import detect_language_anomaly
        r = detect_language_anomaly("Hi")
        assert r["is_anomalous"] is False

    def test_empty_content(self):
        from moderation import detect_language_anomaly
        r = detect_language_anomaly("")
        assert r["is_anomalous"] is False

    def test_latin_only_ok(self):
        from moderation import detect_language_anomaly
        r = detect_language_anomaly("This is a normal English comment about the tour")
        assert r["is_anomalous"] is False
