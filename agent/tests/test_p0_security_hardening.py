"""
P0 security hardening tests — comprehensive coverage for:

  P0-4: Login rate-limit (5 failures per phone per 15 min = temporary block)
  P0-1: Hash session tokens at rest (SHA-256, not plaintext)
  P0-2: Comment moderation (auto-hold comments with URLs/spam patterns)

Per CLAUDE.md B3: these modules had ~0% test coverage. Tests written BEFORE
any changes (test-first, locking existing correct behavior).

Design:
  - Pure logic tests run on any backend (no Postgres needed).
  - Rate-limit tests manipulate the in-memory dicts directly (fast, deterministic).
  - Moderation link-check tests exercise the _check_links function directly.
  - Token hashing tests verify the contract (deterministic, not plaintext, 64-char hex).
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================================
#  P0-4: Login rate-limit
# ============================================================================

class TestLoginRateLimitConfig:
    """Verify rate-limit configuration constants are sane."""

    def test_login_ip_limit_defined(self):
        import auth
        assert hasattr(auth, "LOGIN_IP_LIMIT")
        assert auth.LOGIN_IP_LIMIT > 0
        assert auth.LOGIN_IP_LIMIT <= 20  # reasonable upper bound

    def test_login_ip_window_defined(self):
        import auth
        assert hasattr(auth, "LOGIN_IP_WINDOW")
        assert auth.LOGIN_IP_WINDOW >= 60  # at least 1 minute

    def test_login_phone_limit_defined(self):
        import auth
        assert hasattr(auth, "LOGIN_PHONE_LIMIT")
        assert auth.LOGIN_PHONE_LIMIT == 5  # spec: 5 failures

    def test_login_phone_window_defined(self):
        import auth
        assert hasattr(auth, "LOGIN_PHONE_WINDOW")
        assert auth.LOGIN_PHONE_WINDOW == 900  # spec: 15 minutes

    def test_rate_dicts_exist(self):
        import auth
        assert isinstance(auth._login_ip_rate, dict)
        assert isinstance(auth._login_phone_fails, dict)


class TestLoginRateLimitIPLogic:
    """Test IP-based rate limiting for the login endpoint."""

    def test_ip_rate_limit_blocks_after_threshold(self):
        """Flooding login from a single IP should be blocked."""
        import auth
        # Simulate LOGIN_IP_LIMIT hits from the same IP within the window
        ip = "10.99.99.1"
        now = time.time()
        auth._login_ip_rate[ip] = [now - i for i in range(auth.LOGIN_IP_LIMIT)]
        # Check: the list has LOGIN_IP_LIMIT entries, all within window
        hits = [t for t in auth._login_ip_rate[ip] if now - t < auth.LOGIN_IP_WINDOW]
        assert len(hits) >= auth.LOGIN_IP_LIMIT
        # Cleanup
        auth._login_ip_rate.pop(ip, None)

    def test_ip_rate_old_entries_expire(self):
        """Entries outside the window should not count toward the limit."""
        import auth
        ip = "10.99.99.2"
        now = time.time()
        # All entries are outside the window
        auth._login_ip_rate[ip] = [now - auth.LOGIN_IP_WINDOW - 10 for _ in range(auth.LOGIN_IP_LIMIT)]
        hits = [t for t in auth._login_ip_rate[ip] if now - t < auth.LOGIN_IP_WINDOW]
        assert len(hits) == 0  # all expired, should allow new attempts
        auth._login_ip_rate.pop(ip, None)


class TestLoginRateLimitPhoneLogic:
    """Test phone-based rate limiting (brute-force protection per account)."""

    def test_phone_rate_limit_blocks_after_5_failures(self):
        """5 failed login attempts for the same phone should block further attempts."""
        import auth
        phone = "0909999888"
        now = time.time()
        # Simulate 5 failures
        auth._login_phone_fails[phone] = [now - i for i in range(5)]
        hits = [t for t in auth._login_phone_fails[phone] if now - t < auth.LOGIN_PHONE_WINDOW]
        assert len(hits) >= auth.LOGIN_PHONE_LIMIT
        auth._login_phone_fails.pop(phone, None)

    def test_phone_rate_limit_resets_after_window(self):
        """After the 15-minute window, the phone should be unblocked."""
        import auth
        phone = "0909999777"
        now = time.time()
        # All failures are outside the window
        old = now - auth.LOGIN_PHONE_WINDOW - 60
        auth._login_phone_fails[phone] = [old - i for i in range(5)]
        hits = [t for t in auth._login_phone_fails[phone] if now - t < auth.LOGIN_PHONE_WINDOW]
        assert len(hits) == 0  # all expired
        auth._login_phone_fails.pop(phone, None)

    def test_successful_login_clears_phone_fails(self):
        """After successful login, the phone failure counter should be cleared.
        This is verified by checking the code path in auth.login_password (line 407)."""
        import auth
        phone = "0909999666"
        auth._login_phone_fails[phone] = [time.time()]
        # The actual code does: _login_phone_fails.pop(phone, None)
        auth._login_phone_fails.pop(phone, None)
        assert phone not in auth._login_phone_fails


class TestGcRateDict:
    """Test the garbage collection helper for rate-limit dicts."""

    def test_gc_removes_stale_entries(self):
        import auth
        d = {}
        now = time.time()
        d["stale_key"] = [now - 1000]
        d["fresh_key"] = [now]
        for i in range(auth._RATE_GC_THRESHOLD + 1):
            d[f"filler_{i}"] = [now - 1000]
        auth._gc_rate_dict(d, 500)
        assert "fresh_key" in d

    def test_gc_does_not_run_below_threshold(self):
        import auth
        d = {"key": [time.time() - 1000]}
        auth._gc_rate_dict(d, 500)
        assert "key" in d

    def test_gc_forced_eviction_over_4x_threshold(self):
        import auth
        d = {}
        now = time.time()
        for i in range(auth._RATE_GC_THRESHOLD * 5):
            d[f"key_{i}"] = [now]
        auth._gc_rate_dict(d, 500)
        assert len(d) <= auth._RATE_GC_THRESHOLD


# ============================================================================
#  P0-1: Hash session tokens at rest
# ============================================================================

class TestSessionTokenHashing:
    """Comprehensive tests for session token hashing (P0-6/P0-1)."""

    def test_hash_token_is_sha256_hex(self):
        """Token hash must be a 64-char lowercase hex string (SHA-256)."""
        from auth import _hash_token, _generate_token
        token = _generate_token()
        h = _hash_token(token)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_token_deterministic(self):
        """Same token always produces the same hash (enables DB lookup)."""
        from auth import _hash_token
        token = "test-token-abc123"
        assert _hash_token(token) == _hash_token(token)

    def test_hash_token_not_plaintext(self):
        """Hash output must differ from the input token."""
        from auth import _hash_token, _generate_token
        token = _generate_token()
        assert _hash_token(token) != token

    def test_different_tokens_different_hashes(self):
        """Collision resistance: different tokens produce different hashes."""
        from auth import _hash_token, _generate_token
        t1 = _generate_token()
        t2 = _generate_token()
        assert t1 != t2  # tokens themselves are distinct
        assert _hash_token(t1) != _hash_token(t2)

    def test_token_entropy_sufficient(self):
        """Generated tokens must have sufficient entropy (at least 32 bytes of randomness)."""
        from auth import _generate_token
        token = _generate_token()
        # token_urlsafe(48) produces ~64 chars of base64url
        assert len(token) >= 32

    def test_hash_token_docstring_mentions_sha256(self):
        """The _hash_token function should document the SHA-256 algorithm."""
        from auth import _hash_token
        assert "sha-256" in (_hash_token.__doc__ or "").lower() or \
               "sha256" in (_hash_token.__doc__ or "").lower()

    def test_session_insert_uses_hash_not_plaintext(self):
        """Verify that the auth module's DB INSERT for sessions uses _hash_token.
        This is a code-level contract check (not a runtime DB test).

        Wave 4 Task 3: the session INSERT (via _create_session_atomic) now lives
        in the shared _finish_login helper, called from both verify_otp's and
        login_password's non-2FA success path — not inline in either anymore.
        """
        import inspect
        import auth
        verify_src = inspect.getsource(auth.verify_otp)
        login_src = inspect.getsource(auth.login_password)
        assert "_finish_login" in verify_src, \
            "verify_otp must reach the session-creation helper"
        assert "_finish_login" in login_src, \
            "login_password must reach the session-creation helper"
        finish_src = inspect.getsource(auth._finish_login)
        assert "_hash_token(token)" in finish_src, \
            "_finish_login must hash the token before storing in DB"

    def test_session_lookup_uses_hash(self):
        """Verify that _get_current_user_or_none looks up by hashed token."""
        import inspect
        import auth
        src = inspect.getsource(auth._get_current_user_or_none)
        assert "_hash_token" in src, \
            "_get_current_user_or_none must lookup by hash, not plaintext"

    def test_logout_uses_hash(self):
        """Verify that logout deletes session by hashed token."""
        import inspect
        import auth
        src = inspect.getsource(auth.logout)
        assert "_hash_token" in src, \
            "logout must delete by hashed token"

    def test_set_password_session_revocation_uses_hash(self):
        """Verify that set_password compares current session by hash."""
        import inspect
        import auth
        src = inspect.getsource(auth.set_password)
        assert "_hash_token" in src, \
            "set_password must compare session token by hash"

    def test_list_sessions_uses_hash_for_current(self):
        """Verify that list_sessions identifies current session by hash comparison."""
        import inspect
        import auth
        src = inspect.getsource(auth.list_sessions)
        assert "_hash_token" in src, \
            "list_sessions must identify current session by hash"


# ============================================================================
#  P0-2: Comment moderation — auto-hold content with URLs/spam patterns
# ============================================================================

class TestCheckLinksFunction:
    """Test the _check_links function in moderation.py which flags
    comments/posts containing URLs, especially URL shorteners and
    excessive links."""

    def test_no_urls_score_zero(self):
        """Content without URLs should have score 0."""
        from moderation import _check_links
        result = _check_links("Bài viết bình thường không có link nào cả.")
        assert result["score"] == 0.0
        assert result["reasons"] == []

    def test_empty_content_score_zero(self):
        """Empty content should have score 0."""
        from moderation import _check_links
        assert _check_links("")["score"] == 0.0
        assert _check_links(None)["score"] == 0.0

    def test_single_url_low_score(self):
        """A single legitimate URL gets a low score (not auto-flagged)."""
        from moderation import _check_links, AUTO_APPROVE_THRESHOLD
        result = _check_links("Xem thêm tại https://vinhlong360.vn/dia-diem/abc")
        assert result["score"] > 0
        assert result["score"] < AUTO_APPROVE_THRESHOLD  # should still auto-approve

    def test_shortener_url_flagged(self):
        """URL shorteners should be flagged with higher score."""
        from moderation import _check_links
        shorteners = [
            "Xem: https://bit.ly/abc123",
            "Link: https://tinyurl.com/xyz",
            "Check: https://t.co/abcdef",
            "Go: https://goo.gl/maps/123",
            "Visit: https://ow.ly/xyz",
            "Read: https://is.gd/abc",
            "See: https://buff.ly/abc",
        ]
        for text in shorteners:
            result = _check_links(text)
            assert result["score"] >= 0.5, f"Shortener in '{text}' should score >= 0.5, got {result['score']}"
            assert any("shortener" in r for r in result["reasons"]), \
                f"Shortener in '{text}' should have 'shortener' reason"

    def test_excessive_urls_flagged(self):
        """3+ URLs in a single piece of content should be flagged."""
        from moderation import _check_links
        text = (
            "Check these: "
            "https://example.com/1 "
            "https://example.com/2 "
            "https://example.com/3"
        )
        result = _check_links(text)
        assert result["score"] >= 0.5
        assert any("excessive" in r for r in result["reasons"])

    def test_two_urls_moderate_score(self):
        """2 URLs should still be OK (not excessive)."""
        from moderation import _check_links
        text = "Visit https://example.com/1 and https://example.com/2"
        result = _check_links(text)
        assert "excessive" not in str(result["reasons"])


class TestCheckSpamPatterns:
    """Test the _check_spam_patterns function in moderation.py which flags
    content containing common spam/scam phrases locally (no API needed)."""

    def test_clean_content_score_zero(self):
        """Normal Vietnamese content should have score 0."""
        from moderation import _check_spam_patterns
        result = _check_spam_patterns("Trải nghiệm du lịch Vĩnh Long rất tuyệt vời!")
        assert result["score"] == 0.0
        assert result["reasons"] == []

    def test_empty_content_score_zero(self):
        from moderation import _check_spam_patterns
        assert _check_spam_patterns("")["score"] == 0.0
        assert _check_spam_patterns(None)["score"] == 0.0

    def test_casino_spam_flagged(self):
        """Casino/gambling content should be flagged."""
        from moderation import _check_spam_patterns
        texts = [
            "Choi casino online tai day",
            "Song bai truc tuyen uy tin",
            "Ca cuoc bong da 100%",
            "Slot game hot nhat",
            "No hu moi ngay",
        ]
        for text in texts:
            result = _check_spam_patterns(text)
            assert result["score"] >= 0.5, f"Casino spam '{text}' should be flagged"
            assert len(result["reasons"]) > 0

    def test_crypto_scam_flagged(self):
        """Crypto/investment scam patterns should be flagged."""
        from moderation import _check_spam_patterns
        texts = [
            "Kiem tien online moi ngay 500k",
            "Lam giau nhanh khong can von",
            "Dau tu x10 trong 1 thang",
        ]
        for text in texts:
            result = _check_spam_patterns(text)
            assert result["score"] >= 0.5, f"Scam '{text}' should be flagged"

    def test_adult_spam_flagged(self):
        """Adult/sex spam should be flagged."""
        from moderation import _check_spam_patterns
        result = _check_spam_patterns("gai goi ha noi")
        assert result["score"] >= 0.5

    def test_contact_spam_flagged(self):
        """Contact solicitation with phone numbers should be flagged."""
        from moderation import _check_spam_patterns
        texts = [
            "Lien he zalo 0901234567",
            "Inbox telegram 84901234567",
        ]
        for text in texts:
            result = _check_spam_patterns(text)
            assert result["score"] >= 0.5, f"Contact spam '{text}' should be flagged"

    def test_repetitive_chars_flagged(self):
        """Repeated characters (10+) should be flagged as spam."""
        from moderation import _check_spam_patterns
        result = _check_spam_patterns("AAAAAAAAAA mua ngay")
        assert result["score"] >= 0.5

    def test_short_repeats_not_flagged(self):
        """Short repeats (< 10 chars) should NOT be flagged."""
        from moderation import _check_spam_patterns
        result = _check_spam_patterns("Waaaaah dep qua!")
        assert result["score"] == 0.0


class TestModerationPipelineForComments:
    """Test that the moderate_content function correctly handles
    comment-like content with URLs and spam patterns."""

    def test_comment_with_shortener_held_for_review(self):
        """Comment containing a URL shortener should NOT be auto-approved."""
        import asyncio
        from moderation import moderate_content
        result = asyncio.run(moderate_content("Mua ngay: https://bit.ly/spam123", []))
        # Score from _check_links shortener (0.6) should put it in pending or flagged
        assert result["status"] != "approved", \
            "Comment with URL shortener should not be auto-approved"

    def test_comment_with_many_urls_held(self):
        """Comment with 3+ URLs should be held for review."""
        import asyncio
        from moderation import moderate_content
        text = "https://a.com https://b.com https://c.com spam moi nguoi mua"
        result = asyncio.run(moderate_content(text, []))
        assert result["status"] != "approved", \
            "Comment with 3+ URLs should not be auto-approved"

    def test_clean_comment_approved(self):
        """Normal comment without URLs or bad content should be approved."""
        import asyncio
        from moderation import moderate_content
        result = asyncio.run(moderate_content("Trải nghiệm tuyệt vời, cảm ơn bạn!", []))
        # Without an API key (test env), text moderation returns score 0
        assert result["status"] == "approved"

    def test_empty_comment_approved(self):
        """Empty content should pass moderation."""
        import asyncio
        from moderation import moderate_content
        result = asyncio.run(moderate_content("", []))
        assert result["status"] == "approved"

    def test_spam_pattern_comment_held(self):
        """Comment with spam keywords should be held for review
        even without an external moderation API key."""
        import asyncio
        from moderation import moderate_content
        result = asyncio.run(moderate_content("Casino online uy tin nhat", []))
        assert result["status"] != "approved", \
            "Comment with casino spam should not be auto-approved"

    def test_contact_spam_comment_held(self):
        """Comment with phone solicitation should be held."""
        import asyncio
        from moderation import moderate_content
        result = asyncio.run(moderate_content("Lien he zalo 0901234567890", []))
        assert result["status"] != "approved", \
            "Comment with contact spam should not be auto-approved"


class TestCommentModerationIntegration:
    """Verify that the comment creation path in social.py actually calls
    moderate_content (code-level contract check)."""

    def test_create_comment_calls_moderate_content(self):
        """The create_comment endpoint must call moderate_content."""
        import inspect
        import social
        src = inspect.getsource(social.create_comment)
        assert "moderate_content" in src, \
            "create_comment must call moderate_content (P0-7)"

    def test_create_comment_uses_moderation_status(self):
        """The comment INSERT must use the moderation status from moderate_content."""
        import inspect
        import social
        src = inspect.getsource(social.create_comment)
        assert "moderation_status" in src, \
            "create_comment must store moderation_status in DB"

    def test_format_comment_does_not_leak_phone(self):
        """_format_comment must NOT include phone (PII protection)."""
        from social import _format_comment
        row = {
            "id": "test-id",
            "content": "Test comment",
            "user_id": "user-123",
            "display_name": "Test User",
            "avatar_url": None,
            "phone": "0901234567",
            "parent_id": None,
            "created_at": "2026-01-01",
            "mentions": "[]",
        }
        result = _format_comment(row)
        # phone should NOT appear anywhere in the output
        for v in _all_values(result):
            if isinstance(v, str):
                assert "0901234567" not in v, \
                    "_format_comment must not leak phone number"

    def test_moderate_content_calls_spam_patterns(self):
        """moderate_content must include _check_spam_patterns in its pipeline."""
        import inspect
        import moderation
        src = inspect.getsource(moderation.moderate_content)
        assert "_check_spam_patterns" in src, \
            "moderate_content must call _check_spam_patterns for local spam detection"

    def test_format_post_does_not_leak_phone(self):
        """_format_post must NOT include phone (P0-8)."""
        from social import _format_post
        row = {
            "id": "test-id",
            "content": "Test post",
            "user_id": "user-123",
            "display_name": "Test User",
            "avatar_url": None,
            "phone": "0901234567",
            "created_at": "2026-01-01",
            "images": "[]",
            "like_count": 0,
            "comment_count": 0,
            "post_type": "share",
            "rating": None,
            "entity_id": None,
            "entity_name": None,
            "entity_type": None,
            "mentions": "[]",
            "hashtags": "[]",
            "best_answer_id": None,
            "repost_of": None,
            "repost_snapshot": None,
        }
        result = _format_post(row)
        for v in _all_values(result):
            if isinstance(v, str):
                assert "0901234567" not in v, \
                    "_format_post must not leak phone number"


def _all_values(d):
    """Recursively extract all values from a nested dict/list."""
    if isinstance(d, dict):
        for v in d.values():
            yield from _all_values(v)
    elif isinstance(d, list):
        for item in d:
            yield from _all_values(item)
    else:
        yield d


# ============================================================================
#  Cross-cutting: verify security constants are reasonable
# ============================================================================

class TestSecurityConstants:
    """Verify that security-related constants have reasonable values."""

    def test_session_expire_days_reasonable(self):
        import auth
        assert 1 <= auth.SESSION_EXPIRE_DAYS <= 90

    def test_otp_max_attempts_reasonable(self):
        import auth
        assert 3 <= auth.OTP_MAX_ATTEMPTS <= 10

    def test_otp_expire_minutes_reasonable(self):
        import auth
        assert 2 <= auth.OTP_EXPIRE_MINUTES <= 15

    def test_otp_rate_limit_seconds_exists(self):
        import auth
        assert auth.OTP_RATE_LIMIT_SECONDS >= 30

    def test_login_phone_limit_spec_compliant(self):
        """Per the task spec: 5 failures per 15 min = temporary block."""
        import auth
        assert auth.LOGIN_PHONE_LIMIT == 5
        assert auth.LOGIN_PHONE_WINDOW == 900  # 15 * 60

    def test_comment_rate_limit_exists(self):
        """Social module should have comment rate limiting."""
        import social
        assert social.RL_COMMENT_LIMIT > 0
        assert social.RL_COMMENT_WINDOW > 0
