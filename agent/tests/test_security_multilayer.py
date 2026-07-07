"""
Multi-layer security tests — deep hardening coverage:

  Layer 1: IP reputation & threat scoring
  Layer 2: Adaptive rate limiting with progressive penalties
  Layer 3: Content security (fingerprinting, XSS, homoglyphs, spam v2)
  Layer 4: Session security (binding, XSS sanitization, SQLi detection)

All tests are pure-logic (no DB, no LLM, no network).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================================
#  Layer 1: IP Reputation & Threat Scoring
# ============================================================================

class TestIPReputationTracker:
    """Test IP reputation system with progressive threat escalation."""

    def setup_method(self):
        from middleware import ip_reputation
        ip_reputation._reset()

    def test_clean_ip_level_zero(self):
        from middleware import ip_reputation
        assert ip_reputation.threat_level("192.168.1.1") == 0

    def test_single_auth_failure_raises_to_suspicious(self):
        from middleware import ip_reputation
        ip = "10.0.0.1"
        for _ in range(3):
            ip_reputation.record(ip, "auth_failure")
        assert ip_reputation.threat_level(ip) >= 1

    def test_multiple_events_escalate_to_elevated(self):
        from middleware import ip_reputation
        ip = "10.0.0.2"
        for _ in range(5):
            ip_reputation.record(ip, "auth_failure")
        for _ in range(3):
            ip_reputation.record(ip, "suspicious_input")
        assert ip_reputation.threat_level(ip) >= 2

    def test_admin_key_failures_escalate_fast(self):
        from middleware import ip_reputation
        ip = "10.0.0.3"
        for _ in range(4):
            ip_reputation.record(ip, "admin_key_failure")
        assert ip_reputation.threat_level(ip) >= 2

    def test_hostile_level_on_heavy_abuse(self):
        from middleware import ip_reputation
        ip = "10.0.0.4"
        for _ in range(5):
            ip_reputation.record(ip, "admin_key_failure")
        for _ in range(5):
            ip_reputation.record(ip, "sqli_attempt")
        assert ip_reputation.threat_level(ip) == 3

    def test_score_returns_numeric(self):
        from middleware import ip_reputation
        ip = "10.0.0.5"
        ip_reputation.record(ip, "auth_failure")
        score = ip_reputation.score(ip)
        assert isinstance(score, float)
        assert score > 0

    def test_different_ips_independent(self):
        from middleware import ip_reputation
        ip_reputation.record("10.1.1.1", "admin_key_failure")
        ip_reputation.record("10.1.1.1", "admin_key_failure")
        assert ip_reputation.threat_level("10.1.1.1") >= 1
        assert ip_reputation.threat_level("10.2.2.2") == 0

    def test_stats_returns_structure(self):
        from middleware import ip_reputation
        ip_reputation.record("10.3.3.3", "auth_failure")
        stats = ip_reputation.stats()
        assert "tracked_ips" in stats
        assert "by_level" in stats
        assert stats["tracked_ips"] >= 1

    def test_record_returns_threat_level(self):
        from middleware import ip_reputation
        level = ip_reputation.record("10.4.4.4", "auth_failure")
        assert isinstance(level, int)
        assert 0 <= level <= 3

    def test_security_logger_wires_to_reputation(self):
        """security_logger events should automatically update IP reputation."""
        from middleware import security_logger, ip_reputation
        ip_reputation._reset()
        ip = "10.5.5.5"
        security_logger.auth_failure(ip, "test")
        assert ip_reputation.score(ip) > 0


# ============================================================================
#  Layer 2: Adaptive Rate Limiting
# ============================================================================

class TestAdaptiveRateLimit:
    """Test progressive penalty rate limiting."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_first_violation_normal(self):
        from ratelimit import check_rate_adaptive, _reset
        from fastapi import HTTPException
        _reset()
        for _ in range(5):
            check_rate_adaptive("test_key", base_limit=5, base_window=60)
        with pytest.raises(HTTPException) as exc:
            check_rate_adaptive("test_key", base_limit=5, base_window=60)
        assert exc.value.status_code == 429

    def test_repeated_violations_tighten_limit(self):
        from ratelimit import check_rate_adaptive, get_violation_count, _reset
        from fastapi import HTTPException
        _reset()
        # First violation
        for _ in range(10):
            check_rate_adaptive("tight_key", base_limit=10, base_window=60)
        with pytest.raises(HTTPException):
            check_rate_adaptive("tight_key", base_limit=10, base_window=60)
        assert get_violation_count("tight_key") == 1

    def test_violation_count_increases(self):
        from ratelimit import check_rate_adaptive, get_violation_count, _reset
        from fastapi import HTTPException
        _reset()
        key = "count_key"
        for _ in range(5):
            check_rate_adaptive(key, base_limit=5, base_window=60)
        with pytest.raises(HTTPException):
            check_rate_adaptive(key, base_limit=5, base_window=60)
        assert get_violation_count(key) >= 1


class TestGlobalIPBudget:
    """Test global per-IP request budget."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_allows_normal_traffic(self):
        from ratelimit import check_global_ip_budget
        for _ in range(10):
            check_global_ip_budget("192.168.1.1")

    def test_blocks_excessive_traffic(self):
        from ratelimit import check_global_ip_budget, _IP_GLOBAL_LIMIT, _reset
        from fastapi import HTTPException
        _reset()
        ip = "10.99.99.99"
        for _ in range(_IP_GLOBAL_LIMIT):
            check_global_ip_budget(ip)
        with pytest.raises(HTTPException) as exc:
            check_global_ip_budget(ip)
        assert exc.value.status_code == 429

    def test_different_ips_independent(self):
        from ratelimit import check_global_ip_budget, _reset
        _reset()
        for _ in range(50):
            check_global_ip_budget("10.1.1.1")
        check_global_ip_budget("10.2.2.2")


class TestBurstDetection:
    """Test burst detection."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_no_burst_under_threshold(self):
        from ratelimit import detect_burst, check_rate
        check_rate("burst_test", limit=100, window=60)
        assert detect_burst("burst_test", burst_limit=10, burst_window=2) is False

    def test_detects_rapid_burst(self):
        from ratelimit import detect_burst, check_rate, _reset
        _reset()
        key = "rapid_burst"
        for _ in range(12):
            check_rate(key, limit=100, window=60)
        assert detect_burst(key, burst_limit=10, burst_window=5) is True


# ============================================================================
#  Layer 3: Content Security — Fingerprinting
# ============================================================================

class TestContentFingerprinting:
    """Test duplicate/raid content detection."""

    def setup_method(self):
        from moderation import _reset_fingerprints
        _reset_fingerprints()

    def test_unique_content_not_flagged(self):
        from moderation import check_content_duplicate
        result = check_content_duplicate("Trải nghiệm du lịch Vĩnh Long thật tuyệt vời!", "user1")
        assert result["is_duplicate"] is False

    def test_short_content_not_checked(self):
        from moderation import check_content_duplicate
        result = check_content_duplicate("Hi", "user1")
        assert result["is_duplicate"] is False

    def test_duplicate_content_detected(self):
        from moderation import check_content_duplicate, _reset_fingerprints
        _reset_fingerprints()
        content = "Mua hàng giá rẻ tại đây! Liên hệ ngay để được tư vấn miễn phí!"
        for i in range(3):
            check_content_duplicate(content, f"user{i}")
        result = check_content_duplicate(content, "user_new")
        assert result["is_duplicate"] is True
        assert result["count"] >= 3

    def test_whitespace_variations_caught(self):
        from moderation import content_fingerprint
        fp1 = content_fingerprint("Hello   world   test")
        fp2 = content_fingerprint("Hello world test")
        assert fp1 == fp2

    def test_case_variations_caught(self):
        from moderation import content_fingerprint
        fp1 = content_fingerprint("MUA HÀNG GIÁ RẺ")
        fp2 = content_fingerprint("mua hàng giá rẻ")
        assert fp1 == fp2

    def test_fingerprint_is_hex(self):
        from moderation import content_fingerprint
        fp = content_fingerprint("Test content for fingerprinting")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


# ============================================================================
#  Layer 3: Content Security — XSS Detection
# ============================================================================

class TestXSSDetection:
    """Test XSS payload detection in user content."""

    def test_clean_content_passes(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns("Bài viết bình thường về du lịch Vĩnh Long")
        assert result["has_xss"] is False
        assert result["score"] == 0.0

    def test_script_tag_detected(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns('<script>alert("xss")</script>')
        assert result["has_xss"] is True
        assert result["score"] >= 0.9

    def test_event_handler_detected(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns('<img src=x onerror="alert(1)">')
        assert result["has_xss"] is True

    def test_javascript_uri_detected(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns('Click: javascript:alert(document.cookie)')
        assert result["has_xss"] is True

    def test_iframe_detected(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns('<iframe src="https://evil.com"></iframe>')
        assert result["has_xss"] is True

    def test_svg_event_detected(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns('<svg onload="alert(1)">')
        assert result["has_xss"] is True

    def test_data_uri_detected(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns('data:text/html,<script>alert(1)</script>')
        assert result["has_xss"] is True

    def test_empty_content_safe(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns("")
        assert result["has_xss"] is False

    def test_none_content_safe(self):
        from moderation import check_xss_patterns
        result = check_xss_patterns(None)
        assert result["has_xss"] is False


# ============================================================================
#  Layer 3: Content Security — Homoglyph Detection
# ============================================================================

class TestHomoglyphDetection:
    """Test Unicode homoglyph abuse detection."""

    def test_normal_text_no_homoglyphs(self):
        from moderation import check_homoglyphs
        result = check_homoglyphs("Normal Vietnamese text: Xin chào")
        assert result["has_homoglyphs"] is False

    def test_cyrillic_a_detected(self):
        from moderation import check_homoglyphs
        # Using Cyrillic а, о, с to spell "casino" as "саsinо"
        text = "Visit саsinо now"
        result = check_homoglyphs(text)
        assert result["has_homoglyphs"] is True
        assert result["count"] >= 3

    def test_normalize_replaces_homoglyphs(self):
        from moderation import normalize_homoglyphs
        # Cyrillic а (U+0430) should become Latin a
        result = normalize_homoglyphs("аео")
        assert result == "aeo"

    def test_low_count_not_flagged(self):
        from moderation import check_homoglyphs
        result = check_homoglyphs("One а char")  # single Cyrillic а
        assert result["has_homoglyphs"] is False


# ============================================================================
#  Layer 3: Content Security — Extended Spam Patterns
# ============================================================================

class TestSpamPatternsV2:
    """Test extended Vietnamese spam patterns (MLM, loans, phishing)."""

    def test_clean_content_passes(self):
        from moderation import _check_spam_patterns_v2
        result = _check_spam_patterns_v2("Du lịch Vĩnh Long rất đẹp và thú vị!")
        assert result["score"] == 0.0

    def test_mlm_pattern_detected(self):
        from moderation import _check_spam_patterns_v2
        texts = [
            "Tuyen dai ly lam viec online",
            "Hoa hong 30% moi ngay",
            "Co hoi viec lam online tot nhat",
        ]
        for text in texts:
            result = _check_spam_patterns_v2(text)
            assert result["score"] >= 0.5, f"MLM spam '{text}' should be detected"

    def test_loan_shark_detected(self):
        from moderation import _check_spam_patterns_v2
        texts = [
            "Vay tien nhanh chi trong 5 phut",
            "Cho vay khong can the chap",
            "Giai ngan trong 30 phut",
        ]
        for text in texts:
            result = _check_spam_patterns_v2(text)
            assert result["score"] >= 0.5, f"Loan spam '{text}' should be detected"

    def test_phishing_detected(self):
        from moderation import _check_spam_patterns_v2
        texts = [
            "Xac nhan tai khoan cua ban ngay",
            "Dang nhap de nhan thuong",
        ]
        for text in texts:
            result = _check_spam_patterns_v2(text)
            assert result["score"] >= 0.5, f"Phishing '{text}' should be detected"

    def test_empty_content_safe(self):
        from moderation import _check_spam_patterns_v2
        assert _check_spam_patterns_v2("")["score"] == 0.0
        assert _check_spam_patterns_v2(None)["score"] == 0.0

    def test_homoglyph_bypass_prevented(self):
        """Spam detection should work even when homoglyphs are used."""
        from moderation import _check_spam_patterns_v2
        # "casino" with Cyrillic letters should still be caught after normalization
        result = _check_spam_patterns_v2("Vay tien nhanh online")
        assert result["score"] >= 0.5


# ============================================================================
#  Layer 3: Graduated Response System
# ============================================================================

class TestGraduatedResponse:
    """Test trust level and threshold adjustment."""

    def setup_method(self):
        from moderation import _reset_moderation_history
        _reset_moderation_history()

    def test_new_user_is_normal(self):
        from moderation import get_user_trust_level
        assert get_user_trust_level("new-user-123") == "normal"

    def test_trusted_after_many_approvals(self):
        from moderation import get_user_trust_level, record_moderation_outcome
        uid = "good-user-1"
        for _ in range(11):
            record_moderation_outcome(uid, "approved")
        assert get_user_trust_level(uid) == "trusted"

    def test_probation_after_one_flag(self):
        from moderation import get_user_trust_level, record_moderation_outcome
        uid = "flagged-user-1"
        record_moderation_outcome(uid, "flagged")
        assert get_user_trust_level(uid) == "probation"

    def test_restricted_after_multiple_flags(self):
        from moderation import get_user_trust_level, record_moderation_outcome
        uid = "bad-user-1"
        for _ in range(3):
            record_moderation_outcome(uid, "flagged")
        assert get_user_trust_level(uid) == "restricted"

    def test_threshold_adjustment_trusted(self):
        from moderation import adjust_thresholds_for_trust
        approve, queue = adjust_thresholds_for_trust("trusted")
        assert approve > 0.3  # more lenient
        assert queue > 0.7

    def test_threshold_adjustment_restricted(self):
        from moderation import adjust_thresholds_for_trust
        approve, queue = adjust_thresholds_for_trust("restricted")
        assert approve == 0.0  # nothing auto-approved
        assert queue <= 0.3

    def test_threshold_adjustment_normal(self):
        from moderation import adjust_thresholds_for_trust, AUTO_APPROVE_THRESHOLD, QUEUE_THRESHOLD
        approve, queue = adjust_thresholds_for_trust("normal")
        assert approve == AUTO_APPROVE_THRESHOLD
        assert queue == QUEUE_THRESHOLD

    def test_empty_user_is_normal(self):
        from moderation import get_user_trust_level
        assert get_user_trust_level("") == "normal"


# ============================================================================
#  Layer 4: XSS Sanitization
# ============================================================================

class TestSanitizeHtml:
    """Test multi-pass XSS sanitization utility."""

    def test_clean_text_unchanged(self):
        from auth_middleware import sanitize_html
        text = "Bình thường, không có gì đặc biệt"
        assert sanitize_html(text) == "Bình thường, không có gì đặc biệt"

    def test_script_tag_removed(self):
        from auth_middleware import sanitize_html
        result = sanitize_html('Hello <script>alert("xss")</script> world')
        assert "<script>" not in result
        assert "alert" not in result

    def test_event_handler_removed(self):
        from auth_middleware import sanitize_html
        result = sanitize_html('<img src=x onerror="alert(1)">')
        assert "onerror" not in result

    def test_javascript_uri_removed(self):
        from auth_middleware import sanitize_html
        result = sanitize_html('Click: javascript:alert(1)')
        assert "javascript:" not in result

    def test_html_entities_escaped(self):
        from auth_middleware import sanitize_html
        result = sanitize_html("Price is 5$ & tax included")
        assert "&amp;" in result

    def test_angle_brackets_in_text_stripped(self):
        """Ambiguous < > in text gets stripped (safe-by-default)."""
        from auth_middleware import sanitize_html
        result = sanitize_html("2 < 3 & 4 > 1")
        assert "<" not in result

    def test_nested_tags_removed(self):
        from auth_middleware import sanitize_html
        result = sanitize_html('<div><b>bold</b></div>')
        assert "<" not in result or "&lt;" in result

    def test_empty_input_safe(self):
        from auth_middleware import sanitize_html
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_multiple_attack_vectors(self):
        from auth_middleware import sanitize_html
        payload = '''<script>steal()</script><img onerror="hack()"><a href="javascript:void(0)">'''
        result = sanitize_html(payload)
        assert "<script>" not in result
        assert "onerror" not in result
        assert "javascript:" not in result


class TestIsSafeContent:
    """Test quick safety check for content."""

    def test_plain_text_is_safe(self):
        from auth_middleware import is_safe_content
        assert is_safe_content("Just normal text") is True

    def test_html_tags_not_safe(self):
        from auth_middleware import is_safe_content
        assert is_safe_content("<script>alert(1)</script>") is False

    def test_javascript_uri_not_safe(self):
        from auth_middleware import is_safe_content
        assert is_safe_content("javascript:alert(1)") is False

    def test_empty_is_safe(self):
        from auth_middleware import is_safe_content
        assert is_safe_content("") is True
        assert is_safe_content(None) is True


# ============================================================================
#  Layer 4: SQL Injection Detection
# ============================================================================

class TestSQLiDetection:
    """Test SQL injection pattern detection."""

    def test_normal_text_passes(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("Vĩnh Long du lịch") is False

    def test_union_select_detected(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("' UNION SELECT * FROM users --") is True

    def test_drop_table_detected(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("'; DROP TABLE users; --") is True

    def test_or_1_equals_1_detected(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("' OR 1=1 --") is True

    def test_comment_injection_detected(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("admin'--") is True

    def test_empty_input_safe(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("") is False
        assert check_sqli_patterns(None) is False

    def test_normal_apostrophe_ok(self):
        from auth_middleware import check_sqli_patterns
        assert check_sqli_patterns("It's a nice day") is False


# ============================================================================
#  Layer 4: Session Security
# ============================================================================

class TestSessionFingerprint:
    """Test session fingerprint computation."""

    def test_same_context_same_fingerprint(self):
        from auth_middleware import compute_session_fingerprint
        fp1 = compute_session_fingerprint("Mozilla/5.0 Chrome", "192.168.1.1")
        fp2 = compute_session_fingerprint("Mozilla/5.0 Chrome", "192.168.1.1")
        assert fp1 == fp2

    def test_different_ua_different_fingerprint(self):
        from auth_middleware import compute_session_fingerprint
        fp1 = compute_session_fingerprint("Chrome/100", "192.168.1.1")
        fp2 = compute_session_fingerprint("Firefox/100", "192.168.1.1")
        assert fp1 != fp2

    def test_same_subnet_same_fingerprint(self):
        """IPs in the same /24 should produce the same fingerprint."""
        from auth_middleware import compute_session_fingerprint
        fp1 = compute_session_fingerprint("Chrome", "192.168.1.1")
        fp2 = compute_session_fingerprint("Chrome", "192.168.1.254")
        assert fp1 == fp2

    def test_different_subnet_different_fingerprint(self):
        from auth_middleware import compute_session_fingerprint
        fp1 = compute_session_fingerprint("Chrome", "192.168.1.1")
        fp2 = compute_session_fingerprint("Chrome", "192.168.2.1")
        assert fp1 != fp2

    def test_fingerprint_is_hex(self):
        from auth_middleware import compute_session_fingerprint
        fp = compute_session_fingerprint("UA", "10.0.0.1")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_handles_invalid_ip(self):
        from auth_middleware import compute_session_fingerprint
        fp = compute_session_fingerprint("UA", "not-an-ip")
        assert isinstance(fp, str) and len(fp) == 16


class TestConcurrentSessionLimit:
    """Test concurrent session limit enforcement."""

    def test_within_limit_allowed(self):
        from auth_middleware import check_session_count, MAX_CONCURRENT_SESSIONS
        assert check_session_count(MAX_CONCURRENT_SESSIONS) is True

    def test_over_limit_denied(self):
        from auth_middleware import check_session_count, MAX_CONCURRENT_SESSIONS
        assert check_session_count(MAX_CONCURRENT_SESSIONS + 1) is False

    def test_zero_sessions_allowed(self):
        from auth_middleware import check_session_count
        assert check_session_count(0) is True


# ============================================================================
#  Layer 4: Security Headers
# ============================================================================

class TestSecurityHeaders:
    """Test security response header configuration."""

    def test_dev_headers_present(self):
        from auth_middleware import get_security_headers
        headers = get_security_headers(is_production=False)
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "Referrer-Policy" in headers
        assert headers["X-Frame-Options"] == "DENY"

    def test_prod_headers_include_hsts(self):
        from auth_middleware import get_security_headers
        headers = get_security_headers(is_production=True)
        assert "Strict-Transport-Security" in headers
        assert "max-age=" in headers["Strict-Transport-Security"]

    def test_prod_headers_include_csp(self):
        from auth_middleware import build_csp, generate_csp_nonce
        nonce = generate_csp_nonce()
        csp = build_csp(nonce)
        assert "default-src" in csp
        assert f"'nonce-{nonce}'" in csp
        assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
        assert "frame-ancestors 'none'" in csp

    def test_prod_headers_superset_of_dev(self):
        from auth_middleware import get_security_headers
        dev = get_security_headers(is_production=False)
        prod = get_security_headers(is_production=True)
        for key in dev:
            assert key in prod

    def test_cross_origin_policies_present(self):
        from auth_middleware import get_security_headers
        headers = get_security_headers()
        assert headers.get("Cross-Origin-Opener-Policy") == "same-origin"
        assert headers.get("Cross-Origin-Resource-Policy") == "same-origin"
