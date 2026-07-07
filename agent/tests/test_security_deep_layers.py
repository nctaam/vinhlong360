"""
Deep security layer tests — unlimited depth:

  Layer 5: Bot/scanner detection, SSRF protection, open redirect prevention
  Layer 6: Path traversal, password strength, file upload validation
  Layer 7: PII detection, error sanitization, request signing
  Layer 8: Credential stuffing detection, security event correlation
  Layer 9: Request anomaly detection (entropy, encoding, headers)
  Layer 10: Reputation-aware rate limiting, coordinated attack detection
  Layer 11: Slow-rate attack detection, token bucket rate limiting
  Layer 12: Deep URL analysis, content entropy, coordinated behavior
  Layer 13: Image content safety, filename sanitization
  Layer 14: Enhanced moderation pipeline integration

All tests are pure-logic (no DB, no LLM, no network).
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================================
#  Layer 5: Bot / Scanner Detection
# ============================================================================

class TestBotDetection:
    """Test User-Agent based bot/scanner detection."""

    def test_normal_browser_not_bot(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        assert result["is_bot"] is False
        assert result["category"] == "normal"

    def test_empty_ua_is_bot(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("")
        assert result["is_bot"] is True
        assert result["category"] == "empty_ua"

    def test_none_ua_is_bot(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua(None)
        assert result["is_bot"] is True

    def test_sqlmap_detected(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("sqlmap/1.6#stable")
        assert result["is_bot"] is True
        assert result["is_legit_bot"] is False
        assert result["category"] == "scanner"

    def test_nikto_detected(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("Nikto/2.1.6")
        assert result["is_bot"] is True
        assert result["category"] == "scanner"

    def test_python_requests_detected(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("python-requests/2.28.1")
        assert result["is_bot"] is True

    def test_curl_detected(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("curl/7.88.1")
        assert result["is_bot"] is True

    def test_googlebot_legit(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("Googlebot/2.1 (+http://www.google.com/bot.html)")
        assert result["is_bot"] is True
        assert result["is_legit_bot"] is True
        assert result["category"] == "search_engine"

    def test_bingbot_legit(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("Mozilla/5.0 (compatible; bingbot/2.0)")
        assert result["is_bot"] is True
        assert result["is_legit_bot"] is True

    def test_short_ua_suspicious(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("Bot")
        assert result["is_bot"] is True
        assert result["category"] == "short_ua"

    def test_nuclei_scanner_detected(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("nuclei/2.9.1")
        assert result["is_bot"] is True
        assert result["category"] == "scanner"

    def test_gobuster_detected(self):
        from auth_middleware import detect_bot_ua
        result = detect_bot_ua("gobuster/3.5")
        assert result["is_bot"] is True


# ============================================================================
#  Layer 5: SSRF Protection
# ============================================================================

class TestSSRFProtection:
    """Test URL validation for SSRF prevention."""

    def test_public_url_safe(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("https://example.com/api/data")
        assert result["safe"] is True

    def test_private_ip_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("http://192.168.1.1/admin")
        assert result["safe"] is False
        assert "private" in result["reason"]

    def test_loopback_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("http://127.0.0.1/secret")
        assert result["safe"] is False

    def test_localhost_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("http://localhost:8080/admin")
        assert result["safe"] is False

    def test_aws_metadata_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("http://169.254.169.254/latest/meta-data/")
        assert result["safe"] is False
        assert "metadata" in result["reason"]

    def test_file_scheme_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("file:///etc/passwd")
        assert result["safe"] is False

    def test_gopher_scheme_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("gopher://evil.com/")
        assert result["safe"] is False

    def test_internal_domain_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("http://api.internal/secrets")
        assert result["safe"] is False

    def test_empty_url_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("")
        assert result["safe"] is False

    def test_10x_private_ip_blocked(self):
        from auth_middleware import validate_url_safe
        result = validate_url_safe("http://10.0.0.1/admin")
        assert result["safe"] is False


# ============================================================================
#  Layer 5: Open Redirect Prevention
# ============================================================================

class TestOpenRedirectPrevention:
    """Test redirect URL validation."""

    def test_relative_path_safe(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("/dashboard")
        assert result["safe"] is True

    def test_allowed_host_safe(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("https://vinhlong360.com/home")
        assert result["safe"] is True

    def test_unknown_host_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("https://evil.com/steal")
        assert result["safe"] is False

    def test_javascript_scheme_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("javascript:alert(1)")
        assert result["safe"] is False

    def test_data_scheme_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("data:text/html,<script>alert(1)</script>")
        assert result["safe"] is False

    def test_protocol_relative_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("//evil.com/steal")
        assert result["safe"] is False

    def test_empty_url_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("")
        assert result["safe"] is False

    def test_custom_allowed_hosts(self):
        from auth_middleware import validate_redirect_url
        hosts = frozenset({"trusted.com"})
        result = validate_redirect_url("https://trusted.com/ok", allowed_hosts=hosts)
        assert result["safe"] is True

    def test_javascript_with_whitespace_bypass(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("java\nscript:alert(1)")
        assert result["safe"] is False

    def test_javascript_with_tab_bypass(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("java\tscript:alert(1)")
        assert result["safe"] is False

    def test_javascript_uppercase_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("JAVASCRIPT:alert(1)")
        assert result["safe"] is False

    def test_vbscript_blocked(self):
        from auth_middleware import validate_redirect_url
        result = validate_redirect_url("vbscript:MsgBox")
        assert result["safe"] is False


# ============================================================================
#  Layer 6: Path Traversal Detection
# ============================================================================

class TestPathTraversalDetection:
    """Test path traversal attack detection."""

    def test_normal_path_safe(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("/api/users/123") is False

    def test_dotdot_slash_detected(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("../../etc/passwd") is True

    def test_backslash_traversal_detected(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("..\\..\\windows\\system32") is True

    def test_url_encoded_traversal_detected(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("%2e%2e%2f%2e%2e%2f") is True

    def test_double_encoded_detected(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("%252e%252e%252f") is True

    def test_null_byte_detected(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("image.jpg%00.php") is True

    def test_empty_path_safe(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("") is False

    def test_overlong_utf8_detected(self):
        from auth_middleware import check_path_traversal
        assert check_path_traversal("%c0%ae%c0%ae/") is True


# ============================================================================
#  Layer 6: Password Strength Checker
# ============================================================================

class TestPasswordStrength:
    """Test password quality evaluation."""

    def test_empty_password_weak(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("")
        assert result["strong"] is False
        assert "empty" in result["issues"]

    def test_common_password_rejected(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("password")
        assert result["strong"] is False
        assert "common_password" in result["issues"]

    def test_short_password_flagged(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("Ab1!")
        assert "too_short" in result["issues"]

    def test_strong_password_passes(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("Tr0ub4dor&3Xtra!")
        assert result["strong"] is True
        assert result["score"] >= 3

    def test_keyboard_sequence_flagged(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("qwerty12345678")
        assert "keyboard_sequence" in result["issues"]

    def test_repeated_chars_flagged(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("aaaaaAAA111!")
        assert "repeated_chars" in result["issues"]

    def test_low_variety_flagged(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("alllowercase")
        assert "low_variety" in result["issues"]

    def test_score_range(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("Test123!@#Complex")
        assert 0 <= result["score"] <= 5

    def test_vietnamese_common_password(self):
        from auth_middleware import check_password_strength
        result = check_password_strength("matkhau123")
        assert result["strong"] is False
        assert "common_password" in result["issues"]


# ============================================================================
#  Layer 6: File Upload Validation
# ============================================================================

class TestFileUploadValidation:
    """Test file upload security checks."""

    def test_normal_jpeg_safe(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("photo.jpg", "image/jpeg", 1024000)
        assert result["safe"] is True

    def test_no_filename_rejected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("", "image/jpeg")
        assert result["safe"] is False

    def test_dangerous_extension_rejected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("malware.exe", "application/octet-stream")
        assert result["safe"] is False
        assert any("dangerous_extension" in i for i in result["issues"])

    def test_php_extension_rejected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("shell.php", "text/php")
        assert result["safe"] is False

    def test_double_extension_detected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("image.php.jpg", "image/jpeg")
        assert any("double_extension" in i for i in result["issues"])

    def test_null_byte_injection_detected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("image.jpg\x00.php", "image/jpeg")
        assert any("null_byte" in i for i in result["issues"])

    def test_path_in_filename_detected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("../../uploads/evil.jpg", "image/jpeg")
        assert any("path_in_filename" in i for i in result["issues"])

    def test_oversized_file_rejected(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("big.jpg", "image/jpeg", file_size=10_000_000)
        assert any("file_too_large" in i for i in result["issues"])

    def test_magic_bytes_jpeg_valid(self):
        from auth_middleware import validate_file_upload
        header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        result = validate_file_upload("photo.jpg", "image/jpeg", 1000, file_header=header)
        assert result["safe"] is True

    def test_magic_bytes_mismatch_detected(self):
        from auth_middleware import validate_file_upload
        header = b'NOT_AN_IMAGE_HEADER' + b'\x00' * 100
        result = validate_file_upload("photo.jpg", "image/jpeg", 1000, file_header=header)
        assert any("magic_bytes" in i for i in result["issues"])

    def test_filename_too_long(self):
        from auth_middleware import validate_file_upload
        result = validate_file_upload("a" * 300 + ".jpg", "image/jpeg")
        assert any("filename_too_long" in i for i in result["issues"])

    def test_sanitize_filename_strips_path(self):
        from auth_middleware import sanitize_filename
        assert "/" not in sanitize_filename("../../evil/file.jpg")
        assert "\\" not in sanitize_filename("..\\..\\file.jpg")

    def test_sanitize_filename_removes_special_chars(self):
        from auth_middleware import sanitize_filename
        result = sanitize_filename("file<script>.jpg")
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_filename_empty(self):
        from auth_middleware import sanitize_filename
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename(None) == "unnamed"


# ============================================================================
#  Layer 7: PII / Sensitive Data Detection
# ============================================================================

class TestPIIDetection:
    """Test PII leak detection in output text."""

    def test_no_pii_in_normal_text(self):
        from auth_middleware import detect_pii
        result = detect_pii("Du lịch Vĩnh Long rất đẹp")
        assert result["has_pii"] is False

    def test_detects_vn_phone_number(self):
        from auth_middleware import detect_pii
        result = detect_pii("Liên hệ: 0912345678 để biết thêm")
        assert result["has_pii"] is True
        assert "phone_vn" in result["types"]

    def test_detects_email(self):
        from auth_middleware import detect_pii
        result = detect_pii("Send to admin@example.com for details")
        assert result["has_pii"] is True
        assert "email" in result["types"]

    def test_detects_api_key(self):
        from auth_middleware import detect_pii
        result = detect_pii("Key: sk-1234567890abcdefghijklmnop")
        assert result["has_pii"] is True
        assert "api_key" in result["types"]

    def test_masks_phone(self):
        from auth_middleware import mask_pii
        result = mask_pii("Call 0912345678 now")
        assert "0912345678" not in result
        assert "[PHONE]" in result

    def test_masks_email(self):
        from auth_middleware import mask_pii
        result = mask_pii("Email: user@example.com")
        assert "user@example.com" not in result
        assert "[EMAIL]" in result

    def test_empty_text_safe(self):
        from auth_middleware import detect_pii
        result = detect_pii("")
        assert result["has_pii"] is False

    def test_mask_empty_returns_empty(self):
        from auth_middleware import mask_pii
        assert mask_pii("") == ""
        assert mask_pii(None) == ""


# ============================================================================
#  Layer 7: Error Message Sanitization
# ============================================================================

class TestErrorSanitization:
    """Test error message sanitization for production."""

    def test_generic_error_passes_through(self):
        from auth_middleware import sanitize_error_message
        result = sanitize_error_message("Không tìm thấy dữ liệu", is_production=True)
        assert result == "Không tìm thấy dữ liệu"

    def test_traceback_stripped_in_prod(self):
        from auth_middleware import sanitize_error_message
        error = 'Traceback (most recent call last):\n  File "server.py", line 42'
        result = sanitize_error_message(error, is_production=True)
        assert "Traceback" not in result
        assert "server.py" not in result

    def test_db_connection_string_stripped(self):
        from auth_middleware import sanitize_error_message
        error = "Connection failed: postgresql://user:pass@db:5432/mydb"
        result = sanitize_error_message(error, is_production=True)
        assert "postgresql://" not in result

    def test_password_leak_stripped(self):
        from auth_middleware import sanitize_error_message
        error = "Auth failed: password=secret123"
        result = sanitize_error_message(error, is_production=True)
        assert "secret123" not in result

    def test_dev_mode_passes_through(self):
        from auth_middleware import sanitize_error_message
        error = 'File "server.py", line 42, in handle'
        result = sanitize_error_message(error, is_production=False)
        assert result == error

    def test_empty_error_returns_generic(self):
        from auth_middleware import sanitize_error_message
        result = sanitize_error_message("")
        assert result  # should return some generic message

    def test_sql_error_stripped(self):
        from auth_middleware import sanitize_error_message
        error = "SQLSTATE[42000]: Syntax error near 'SELECT'"
        result = sanitize_error_message(error, is_production=True)
        assert "SQLSTATE" not in result


# ============================================================================
#  Layer 7: Request Signing / Integrity
# ============================================================================

class TestRequestSigning:
    """Test HMAC request signing for API integrity."""

    def test_compute_signature_deterministic(self):
        from auth_middleware import compute_request_signature
        sig1 = compute_request_signature("POST", "/api/data", '{"key":"value"}', "secret123")
        sig2 = compute_request_signature("POST", "/api/data", '{"key":"value"}', "secret123")
        assert sig1 == sig2

    def test_different_body_different_signature(self):
        from auth_middleware import compute_request_signature
        sig1 = compute_request_signature("POST", "/api", "body1", "secret")
        sig2 = compute_request_signature("POST", "/api", "body2", "secret")
        assert sig1 != sig2

    def test_different_secret_different_signature(self):
        from auth_middleware import compute_request_signature
        sig1 = compute_request_signature("POST", "/api", "body", "secret1")
        sig2 = compute_request_signature("POST", "/api", "body", "secret2")
        assert sig1 != sig2

    def test_verify_valid_signature(self):
        from auth_middleware import compute_request_signature, verify_request_signature
        secret = "test-secret-key"
        sig = compute_request_signature("POST", "/api", "body", secret)
        result = verify_request_signature("POST", "/api", "body", secret, sig)
        assert result["valid"] is True

    def test_verify_invalid_signature(self):
        from auth_middleware import verify_request_signature
        result = verify_request_signature("POST", "/api", "body", "secret", "wrong-sig")
        assert result["valid"] is False

    def test_verify_missing_signature(self):
        from auth_middleware import verify_request_signature
        result = verify_request_signature("POST", "/api", "body", "secret", "")
        assert result["valid"] is False

    def test_signature_is_hex(self):
        from auth_middleware import compute_request_signature
        sig = compute_request_signature("GET", "/", "", "key")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)


# ============================================================================
#  Layer 8: Credential Stuffing Detection
# ============================================================================

class TestCredentialStuffingDetection:
    """Test credential stuffing attack detection."""

    def setup_method(self):
        from middleware import credential_stuffing
        credential_stuffing._reset()

    def test_single_failure_not_stuffing(self):
        from middleware import credential_stuffing
        result = credential_stuffing.record_failure("10.0.0.1", "user1")
        assert result["is_stuffing"] is False

    def test_same_account_repeated_not_stuffing(self):
        from middleware import credential_stuffing
        for _ in range(4):
            result = credential_stuffing.record_failure("10.0.0.1", "same_user")
        assert result["is_stuffing"] is False
        assert result["unique_accounts"] == 1

    def test_multiple_accounts_triggers_stuffing(self):
        from middleware import credential_stuffing
        for i in range(6):
            result = credential_stuffing.record_failure("10.0.0.1", f"user_{i}")
        assert result["is_stuffing"] is True
        assert result["unique_accounts"] >= 5

    def test_is_suspicious_after_stuffing(self):
        from middleware import credential_stuffing
        ip = "10.0.0.2"
        for i in range(6):
            credential_stuffing.record_failure(ip, f"victim_{i}")
        assert credential_stuffing.is_suspicious(ip) is True

    def test_different_ips_independent(self):
        from middleware import credential_stuffing
        for i in range(6):
            credential_stuffing.record_failure("10.1.1.1", f"user_{i}")
        assert credential_stuffing.is_suspicious("10.1.1.1") is True
        assert credential_stuffing.is_suspicious("10.2.2.2") is False

    def test_stats_returns_structure(self):
        from middleware import credential_stuffing
        stats = credential_stuffing.stats()
        assert "tracked_ips" in stats
        assert "threshold" in stats


# ============================================================================
#  Layer 8: Security Event Correlation
# ============================================================================

class TestSecurityEventCorrelation:
    """Test cross-signal security event correlation."""

    def setup_method(self):
        from middleware import event_correlator
        event_correlator._reset()

    def test_single_event_no_attack(self):
        from middleware import event_correlator
        result = event_correlator.check("10.0.0.1")
        assert result["is_attack"] is False

    def test_brute_force_pattern_detected(self):
        from middleware import event_correlator
        ip = "10.0.0.1"
        for _ in range(6):
            event_correlator.ingest(ip, "auth_failure")
        result = event_correlator.check(ip)
        assert result["is_attack"] is True
        assert "brute_force" in result["patterns"]

    def test_multi_vector_attack_detected(self):
        from middleware import event_correlator
        ip = "10.0.0.2"
        event_correlator.ingest(ip, "auth_failure")
        event_correlator.ingest(ip, "suspicious_input")
        event_correlator.ingest(ip, "rate_limit_hit")
        event_correlator.ingest(ip, "csrf_failure")
        event_correlator.ingest(ip, "admin_key_failure")
        result = event_correlator.check(ip)
        assert result["is_attack"] is True
        assert "multi_vector" in result["patterns"]

    def test_severity_escalates_with_patterns(self):
        from middleware import event_correlator
        ip = "10.0.0.3"
        # Trigger multiple patterns
        for _ in range(6):
            event_correlator.ingest(ip, "auth_failure")
        event_correlator.ingest(ip, "admin_key_failure")
        event_correlator.ingest(ip, "suspicious_input")
        event_correlator.ingest(ip, "suspicious_input")
        event_correlator.ingest(ip, "suspicious_input")
        result = event_correlator.check(ip)
        if len(result["patterns"]) >= 2:
            assert result["severity"] == "critical"

    def test_recent_alerts_tracked(self):
        from middleware import event_correlator
        ip = "10.0.0.4"
        for _ in range(6):
            event_correlator.ingest(ip, "auth_failure")
        alerts = event_correlator.recent_alerts()
        assert len(alerts) >= 1
        assert alerts[-1]["ip"] == ip

    def test_stats_returns_structure(self):
        from middleware import event_correlator
        stats = event_correlator.stats()
        assert "tracked_ips" in stats
        assert "total_alerts" in stats

    def test_correlator_wired_to_security_logger(self):
        """Security logger events should automatically feed the correlator."""
        from middleware import security_logger, event_correlator
        event_correlator._reset()
        ip = "10.0.0.5"
        for _ in range(6):
            security_logger.auth_failure(ip, "test_correlation")
        result = event_correlator.check(ip)
        assert result["is_attack"] is True


# ============================================================================
#  Layer 9: Request Anomaly Detection
# ============================================================================

class TestRequestAnomalyDetection:
    """Test request payload and header anomaly detection."""

    def test_normal_text_low_entropy(self):
        from middleware import request_anomaly
        result = request_anomaly.check_payload_entropy("Du lịch Vĩnh Long rất đẹp và thú vị!")
        assert result["is_anomalous"] is False

    def test_random_data_high_entropy(self):
        from middleware import request_anomaly
        # Simulate random-looking data
        payload = "aZ3kR9mN2qW8eT5yU1iO4pL7jH0gF6dS"
        result = request_anomaly.check_payload_entropy(payload * 3)
        assert result["entropy"] > 4.0

    def test_short_payload_not_anomalous(self):
        from middleware import request_anomaly
        result = request_anomaly.check_payload_entropy("hi")
        assert result["is_anomalous"] is False

    def test_double_encoding_detected(self):
        from middleware import request_anomaly
        result = request_anomaly.check_encoding_attack("%252e%252e%252f")
        assert result["is_attack"] is True
        assert "double_url_encoding" in result["reasons"]

    def test_null_byte_encoding_detected(self):
        from middleware import request_anomaly
        result = request_anomaly.check_encoding_attack("file.jpg%00.php")
        assert result["is_attack"] is True
        assert "null_byte" in result["reasons"]

    def test_excessive_encoding_detected(self):
        from middleware import request_anomaly
        result = request_anomaly.check_encoding_attack("%41%42%43%44%45%46%47%48%49%4A%4B")
        assert result["is_attack"] is True
        assert "excessive_url_encoding" in result["reasons"]

    def test_normal_url_not_encoding_attack(self):
        from middleware import request_anomaly
        result = request_anomaly.check_encoding_attack("/api/users?q=hello")
        assert result["is_attack"] is False

    def test_missing_accept_header_flagged(self):
        from middleware import request_anomaly
        result = request_anomaly.check_header_anomalies({})
        assert result["score"] > 0
        assert "missing_accept" in result["reasons"]

    def test_normal_headers_low_score(self):
        from middleware import request_anomaly
        result = request_anomaly.check_header_anomalies({
            "accept": "text/html",
            "accept-language": "vi-VN",
            "connection": "keep-alive",
        })
        assert result["score"] < 0.2

    def test_empty_value_not_encoding_attack(self):
        from middleware import request_anomaly
        result = request_anomaly.check_encoding_attack("")
        assert result["is_attack"] is False


# ============================================================================
#  Layer 10: Reputation-Aware Rate Limiting
# ============================================================================

class TestReputationAwareRateLimit:
    """Test rate limiting adjusted by IP reputation."""

    def setup_method(self):
        from ratelimit import _reset
        from middleware import ip_reputation
        _reset()
        ip_reputation._reset()

    def test_clean_ip_gets_full_limit(self):
        from ratelimit import check_rate_reputation_aware, _reset
        from fastapi import HTTPException
        _reset()
        # Clean IP: full 10 requests allowed
        for _ in range(10):
            check_rate_reputation_aware("test", "1.2.3.4", base_limit=10, base_window=60)
        with pytest.raises(HTTPException):
            check_rate_reputation_aware("test", "1.2.3.4", base_limit=10, base_window=60)

    def test_hostile_ip_gets_reduced_limit(self):
        from ratelimit import check_rate_reputation_aware, _reset
        from middleware import ip_reputation
        from fastapi import HTTPException
        _reset()
        ip_reputation._reset()
        # Make IP hostile
        ip = "10.99.0.1"
        for _ in range(10):
            ip_reputation.record(ip, "admin_key_failure")
        assert ip_reputation.threat_level(ip) == 3
        # Hostile IP: 25% of base limit = 2 requests
        for _ in range(2):
            check_rate_reputation_aware(f"rep_test:{ip}", ip, base_limit=10, base_window=60)
        with pytest.raises(HTTPException):
            check_rate_reputation_aware(f"rep_test:{ip}", ip, base_limit=10, base_window=60)


# ============================================================================
#  Layer 10: Coordinated Attack Detection
# ============================================================================

class TestCoordinatedAttackDetection:
    """Test multi-IP coordinated attack detection."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_single_ip_not_coordinated(self):
        from ratelimit import check_coordinated_attack
        result = check_coordinated_attack("/api/login", "10.0.0.1")
        assert result["is_coordinated"] is False

    def test_many_ips_same_resource_detected(self):
        from ratelimit import check_coordinated_attack, _reset
        _reset()
        for i in range(12):
            result = check_coordinated_attack("/api/login", f"10.0.{i}.1")
        assert result["is_coordinated"] is True
        assert result["unique_ips"] >= 10

    def test_different_resources_independent(self):
        from ratelimit import check_coordinated_attack, _reset
        _reset()
        for i in range(12):
            check_coordinated_attack("/api/login", f"10.0.{i}.1")
        result = check_coordinated_attack("/api/search", "10.99.99.1")
        assert result["is_coordinated"] is False


# ============================================================================
#  Layer 11: Slow-Rate Attack Detection
# ============================================================================

class TestSlowRateAttackDetection:
    """Test slow-rate L7 attack detection."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_few_requests_not_attack(self):
        from ratelimit import detect_slow_attack
        result = detect_slow_attack("10.0.0.1")
        assert result["is_slow_attack"] is False

    def test_returns_request_count(self):
        from ratelimit import detect_slow_attack, _reset
        _reset()
        for _ in range(5):
            detect_slow_attack("10.0.0.2")
        result = detect_slow_attack("10.0.0.2")
        assert result["request_count"] == 6

    def test_regularity_is_float(self):
        from ratelimit import detect_slow_attack
        result = detect_slow_attack("10.0.0.3")
        assert isinstance(result["regularity"], float)


# ============================================================================
#  Layer 11: Token Bucket Rate Limiting
# ============================================================================

class TestTokenBucketRateLimit:
    """Test token bucket rate limiting."""

    def setup_method(self):
        from ratelimit import _reset
        _reset()

    def test_allows_burst(self):
        from ratelimit import check_rate_token_bucket
        # Should allow up to capacity requests in a burst
        for _ in range(5):
            check_rate_token_bucket("tb_test", capacity=5, refill_rate=1.0)

    def test_blocks_when_empty(self):
        from ratelimit import check_rate_token_bucket, _reset
        from fastapi import HTTPException
        _reset()
        for _ in range(5):
            check_rate_token_bucket("tb_block", capacity=5, refill_rate=0.01)
        with pytest.raises(HTTPException) as exc:
            check_rate_token_bucket("tb_block", capacity=5, refill_rate=0.01)
        assert exc.value.status_code == 429

    def test_different_keys_independent(self):
        from ratelimit import check_rate_token_bucket, _reset
        _reset()
        for _ in range(5):
            check_rate_token_bucket("tb_a", capacity=5, refill_rate=0.01)
        # Different key should still have tokens
        check_rate_token_bucket("tb_b", capacity=5, refill_rate=1.0)


# ============================================================================
#  Layer 12: Deep URL Analysis
# ============================================================================

class TestDeepURLAnalysis:
    """Test phishing/malicious URL detection."""

    def test_normal_url_safe(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("https://vinhlong360.com/tour/1")
        assert result["risk_level"] == "safe"

    def test_phishing_tld_flagged(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("https://login-secure.tk/verify")
        assert result["risk_score"] >= 0.4
        assert any("suspicious_tld" in r for r in result["reasons"])

    def test_phishing_domain_pattern_flagged(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("https://paypal-login-verify.com/secure")
        assert result["risk_level"] in ("high", "medium")

    def test_ip_as_hostname_flagged(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("http://185.143.223.1/login")
        assert result["risk_score"] > 0
        assert "ip_as_hostname" in result["reasons"]

    def test_credential_in_url_flagged(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("http://legit.com@evil.com/steal")
        assert result["risk_score"] >= 0.7
        assert "credential_in_url" in result["reasons"]

    def test_excessive_subdomains_flagged(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("https://a.b.c.d.e.example.com/login")
        assert any("excessive_subdomains" in r for r in result["reasons"])

    def test_empty_url_safe(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("")
        assert result["risk_level"] == "safe"

    def test_brand_impersonation_flagged(self):
        from moderation import analyze_url_deep
        result = analyze_url_deep("https://fac3b00k-login.com/verify")
        assert result["risk_score"] > 0


# ============================================================================
#  Layer 12: Content Entropy Analysis
# ============================================================================

class TestContentEntropy:
    """Test content entropy analysis for encoded payload detection."""

    def test_normal_text_low_entropy(self):
        from moderation import check_content_entropy
        result = check_content_entropy("Du lịch Vĩnh Long thật tuyệt vời, cảnh đẹp quá!")
        assert result["is_suspicious"] is False

    def test_base64_high_entropy(self):
        from moderation import check_content_entropy
        # Simulated base64-like content
        b64 = "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBiYXNlNjQgZW5jb2RlZCBzdHJpbmcgdGhhdCBpcyBsb25nIGVub3VnaA=="
        result = check_content_entropy(b64)
        assert result["entropy"] > 4.0

    def test_short_content_not_suspicious(self):
        from moderation import check_content_entropy
        result = check_content_entropy("short")
        assert result["is_suspicious"] is False
        assert result["entropy"] == 0.0

    def test_empty_content_safe(self):
        from moderation import check_content_entropy
        result = check_content_entropy("")
        assert result["is_suspicious"] is False

    def test_returns_encoding_type(self):
        from moderation import check_content_entropy
        result = check_content_entropy("Normal text that is long enough to analyze properly")
        assert result["encoding_likely"] in ("none", "base64", "hex")


# ============================================================================
#  Layer 12: Coordinated Inauthentic Behavior
# ============================================================================

class TestCoordinatedBehavior:
    """Test sockpuppet/bot network detection."""

    def setup_method(self):
        from moderation import _reset_coordinated_behavior
        _reset_coordinated_behavior()

    def test_single_post_not_coordinated(self):
        from moderation import detect_coordinated_behavior
        result = detect_coordinated_behavior(
            "Bài viết bình thường về du lịch", "user1", "10.0.0.1"
        )
        assert result["is_coordinated"] is False

    def test_same_user_not_coordinated(self):
        from moderation import detect_coordinated_behavior, _reset_coordinated_behavior
        _reset_coordinated_behavior()
        content = "Mua hàng giá rẻ tại đây liên hệ ngay"
        for _ in range(5):
            detect_coordinated_behavior(content, "same_user", "10.0.0.1")
        result = detect_coordinated_behavior(content, "same_user", "10.0.0.1")
        assert result["unique_users"] == 1

    def test_multiple_users_same_content_detected(self):
        from moderation import detect_coordinated_behavior, _reset_coordinated_behavior
        _reset_coordinated_behavior()
        content = "Spam content that multiple bots post simultaneously"
        for i in range(4):
            detect_coordinated_behavior(content, f"bot_{i}", f"10.0.0.{i}")
        result = detect_coordinated_behavior(content, "bot_final", "10.0.0.99")
        assert result["is_coordinated"] is True
        assert result["unique_users"] >= 3

    def test_same_ip_increases_score(self):
        from moderation import detect_coordinated_behavior, _reset_coordinated_behavior
        _reset_coordinated_behavior()
        content = "Sockpuppet spam from same IP address testing"
        for i in range(4):
            detect_coordinated_behavior(content, f"sock_{i}", "10.0.0.1")
        result = detect_coordinated_behavior(content, "sock_final", "10.0.0.1")
        assert result["score"] > 0

    def test_short_content_not_checked(self):
        from moderation import detect_coordinated_behavior
        result = detect_coordinated_behavior("Hi", "user1", "10.0.0.1")
        assert result["is_coordinated"] is False


# ============================================================================
#  Layer 13: Image Content Safety
# ============================================================================

class TestImageContentSafety:
    """Test image file content analysis for embedded exploits."""

    def test_clean_header_safe(self):
        from moderation import check_image_content_safe
        header = b'\xff\xd8\xff\xe0' + b'\x00' * 200
        result = check_image_content_safe(header)
        assert result["safe"] is True

    def test_embedded_php_detected(self):
        from moderation import check_image_content_safe
        header = b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'<?php system($_GET["cmd"]); ?>'
        result = check_image_content_safe(header)
        assert result["safe"] is False
        assert "embedded_php" in result["reasons"]

    def test_embedded_script_detected(self):
        from moderation import check_image_content_safe
        header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100 + b'<script>alert(1)</script>'
        result = check_image_content_safe(header)
        assert result["safe"] is False
        assert "embedded_script" in result["reasons"]

    def test_empty_header_safe(self):
        from moderation import check_image_content_safe
        result = check_image_content_safe(b"")
        assert result["safe"] is True


# ============================================================================
#  Layer 13: Image Filename Sanitization
# ============================================================================

class TestImageFilenameSanitization:
    """Test image filename sanitization for safe storage."""

    def test_normal_filename_unchanged(self):
        from moderation import sanitize_image_filename
        assert sanitize_image_filename("photo.jpg") == "photo.jpg"

    def test_path_stripped(self):
        from moderation import sanitize_image_filename
        result = sanitize_image_filename("../../uploads/evil.jpg")
        assert ".." not in result

    def test_unsafe_extension_replaced(self):
        from moderation import sanitize_image_filename
        result = sanitize_image_filename("shell.php")
        assert result.endswith(".jpg")
        assert "php" not in result.split(".")[-1]

    def test_empty_filename_defaults(self):
        from moderation import sanitize_image_filename
        assert sanitize_image_filename("") == "upload.jpg"
        assert sanitize_image_filename(None) == "upload.jpg"

    def test_null_bytes_removed(self):
        from moderation import sanitize_image_filename
        result = sanitize_image_filename("image\x00.php.jpg")
        assert "\x00" not in result

    def test_long_filename_truncated(self):
        from moderation import sanitize_image_filename
        result = sanitize_image_filename("a" * 300 + ".jpg")
        assert len(result) <= 200


# ============================================================================
#  Layer 14: Enhanced Moderation Pipeline Integration
# ============================================================================

class TestEnhancedModerationPipeline:
    """Test the unified enhanced moderation pipeline."""

    def setup_method(self):
        from moderation import _reset_fingerprints, _reset_moderation_history, _reset_coordinated_behavior
        _reset_fingerprints()
        _reset_moderation_history()
        _reset_coordinated_behavior()

    def test_clean_content_approved(self):
        from moderation import moderate_content_enhanced
        result = asyncio.run(
            moderate_content_enhanced("Du lịch Vĩnh Long rất đẹp!", user_id="user1")
        )
        assert result["status"] == "approved"
        assert "trust_level" in result
        assert "deep_layers" in result

    def test_xss_content_flagged(self):
        from moderation import moderate_content_enhanced
        result = asyncio.run(
            moderate_content_enhanced('<script>alert("xss")</script>', user_id="user1")
        )
        assert result["score"] >= 0.9
        assert result["deep_layers"]["xss"] is True

    def test_spam_content_flagged(self):
        from moderation import moderate_content_enhanced
        result = asyncio.run(
            moderate_content_enhanced("Casino online song bai uy tin nhat", user_id="user1")
        )
        assert result["score"] >= 0.5

    def test_result_includes_deep_layers(self):
        from moderation import moderate_content_enhanced
        result = asyncio.run(
            moderate_content_enhanced("Normal content for testing", user_id="user1")
        )
        layers = result["deep_layers"]
        assert "xss" in layers
        assert "homoglyphs" in layers
        assert "spam_v2" in layers
        assert "high_entropy" in layers

    def test_trust_level_affects_threshold(self):
        from moderation import moderate_content_enhanced, record_moderation_outcome
        uid = "trusted_user"
        for _ in range(11):
            record_moderation_outcome(uid, "approved")
        result = asyncio.run(
            moderate_content_enhanced("Normal content testing trust level", user_id=uid)
        )
        assert result["trust_level"] == "trusted"
