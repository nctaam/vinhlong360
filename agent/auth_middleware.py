"""
vinhlong360 — Auth dependencies + security utilities for FastAPI.

Usage in routes:
  from auth_middleware import get_current_user, require_user, require_role

  @router.get("/feed")
  async def feed(user=Depends(get_current_user)):  # user or None
      ...

  @router.post("/posts")
  async def create_post(user=Depends(require_user)):  # must be logged in
      ...

  @router.delete("/admin/ban")
  async def ban(user=Depends(require_role("admin"))):
      ...

CSRF protection:
  from auth_middleware import require_csrf, generate_csrf_token

  @router.post("/sensitive")
  async def sensitive(request: Request, _=Depends(require_csrf)):
      ...

Input validation:
  from auth_middleware import validate_string_param, validate_path_id

  @router.get("/search")
  async def search(q: str):
      q = validate_string_param(q, max_length=200, param_name="q")
      ...
"""

import hashlib
import hmac
import os
import re
import secrets

from fastapi import Depends, HTTPException, Request

from auth import _get_current_user_or_none
from database import db


# ── Postgres guard (shared) ──

def require_pg():
    """Dependency: UGC/auth endpoints need Postgres. Returns 503 on SQLite."""
    if not db._use_pg:
        raise HTTPException(503, detail="Tính năng UGC/auth cần Postgres. Local dev: docker compose up postgres.")


# ── Auth Dependencies ──

async def get_current_user(request: Request) -> dict | None:
    """Returns current user or None. Does NOT raise."""
    return await _get_current_user_or_none(request)


async def require_user(request: Request) -> dict:
    """Requires authenticated user. Raises 401 if not logged in."""
    user = await _get_current_user_or_none(request)
    if not user:
        raise HTTPException(401, "Vui lòng đăng nhập để thực hiện thao tác này")
    return user


def require_role(*roles: str):
    """Factory: requires user with one of the given roles."""
    async def dep(request: Request) -> dict:
        user = await _get_current_user_or_none(request)
        if not user:
            raise HTTPException(401, "Vui lòng đăng nhập")
        if user.get("role") not in roles:
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
        return user
    return dep


# ══════════════════════════════════════════════════
#  CSRF PROTECTION
# ══════════════════════════════════════════════════

_CSRF_SECRET = os.environ.get("CSRF_SECRET", "")
if not _CSRF_SECRET:
    if os.environ.get("ENVIRONMENT") == "production":
        raise RuntimeError("CSRF_SECRET is required in production")
    _CSRF_SECRET = secrets.token_hex(32)

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def generate_csrf_token(session_id: str) -> str:
    """Generate HMAC-SHA256 CSRF token tied to a session.

    Token = HMAC(secret, session_id). Client sends it back via
    X-CSRF-Token header on state-changing requests.
    """
    return hmac.new(
        _CSRF_SECRET.encode(), session_id.encode(), hashlib.sha256
    ).hexdigest()


def _validate_csrf(request: Request, session_id: str) -> bool:
    """Check X-CSRF-Token header against expected value."""
    token = request.headers.get("X-CSRF-Token", "")
    if not token:
        return False
    expected = generate_csrf_token(session_id)
    return hmac.compare_digest(token, expected)


async def require_csrf(request: Request) -> None:
    """FastAPI dependency: validate CSRF token on state-changing requests.

    Safe methods (GET/HEAD/OPTIONS) are passed through.
    For POST/PUT/PATCH/DELETE, requires valid X-CSRF-Token header.

    Usage:
        @router.post("/action")
        async def action(request: Request, _=Depends(require_csrf)):
            ...
    """
    if request.method in _SAFE_METHODS:
        return

    user = await _get_current_user_or_none(request)
    if not user:
        return

    session_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not session_token:
        session_token = request.cookies.get("session_token", "")
    if not session_token:
        return

    if not _validate_csrf(request, session_token):
        from middleware import security_logger, get_client_ip
        ip = get_client_ip(request)
        security_logger.csrf_failure(ip, endpoint=str(request.url.path))
        raise HTTPException(403, "CSRF token không hợp lệ")


# ══════════════════════════════════════════════════
#  INPUT VALIDATION UTILITIES
# ══════════════════════════════════════════════════

_PATH_ID_RE = re.compile(r'^[a-zA-Z0-9\-_.]{1,128}$')
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)


def validate_string_param(
    value: str,
    max_length: int = 200,
    min_length: int = 0,
    param_name: str = "input",
    strip: bool = True,
) -> str:
    """Validate and bound a string query/body parameter.

    Raises HTTPException(400) if constraints are violated.
    Returns the (optionally stripped, truncated) value.
    """
    if value is None:
        if min_length > 0:
            raise HTTPException(400, f"{param_name} là bắt buộc")
        return ""
    if strip:
        value = value.strip()
    if len(value) < min_length:
        raise HTTPException(400, f"{param_name} phải có ít nhất {min_length} ký tự")
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_path_id(value: str, param_name: str = "id") -> str:
    """Validate a path parameter that should be a safe identifier.

    Allows alphanumeric, hyphens, underscores. Max 128 chars.
    Raises HTTPException(400) on invalid input.
    """
    if not value or not _PATH_ID_RE.match(value):
        raise HTTPException(400, f"{param_name} không hợp lệ")
    return value


def validate_uuid_param(value: str, param_name: str = "id") -> str:
    """Validate a UUID path/query parameter.

    Raises HTTPException(400) if not a valid UUID format.
    """
    if not value or not _UUID_RE.match(value):
        raise HTTPException(400, f"{param_name} không đúng định dạng UUID")
    return value


def validate_int_param(
    value: int,
    min_val: int = 0,
    max_val: int = 1000,
    param_name: str = "limit",
) -> int:
    """Clamp an integer parameter to safe bounds."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def sanitize_log_param(value: str, max_length: int = 100) -> str:
    """Sanitize a value before including it in log output (prevent log injection)."""
    if not value:
        return ""
    sanitized = value.replace("\n", " ").replace("\r", " ")
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


# ══════════════════════════════════════════════════
#  XSS SANITIZATION
# ══════════════════════════════════════════════════

import html as _html

_SCRIPT_RE = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r'<[^>]+>')
_EVENT_HANDLER_RE = re.compile(r'\bon\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
_JAVASCRIPT_URI_RE = re.compile(r'javascript\s*:', re.IGNORECASE)


def sanitize_html(value: str) -> str:
    """Multi-pass HTML sanitization for user-submitted content.

    1. Remove <script> blocks entirely
    2. Remove event handler attributes (onclick=, onerror=, etc.)
    3. Remove javascript: URIs
    4. Strip remaining HTML tags
    5. HTML-escape special characters

    Use this for content that will be rendered — it's more thorough than
    regex tag-stripping alone.
    """
    if not value:
        return ""
    text = _SCRIPT_RE.sub('', value)
    text = _EVENT_HANDLER_RE.sub('', text)
    text = _JAVASCRIPT_URI_RE.sub('', text)
    text = _TAG_RE.sub('', text)
    text = _html.escape(text)
    return text.strip()


def is_safe_content(value: str) -> bool:
    """Quick check: does the value contain any HTML/script patterns?

    Returns True if content appears safe (no tags, no event handlers).
    """
    if not value:
        return True
    if '<' in value and '>' in value:
        return False
    if _JAVASCRIPT_URI_RE.search(value):
        return False
    if _EVENT_HANDLER_RE.search(value):
        return False
    return True


# ══════════════════════════════════════════════════
#  SQL INJECTION DETECTION
# ══════════════════════════════════════════════════

_SQLI_PATTERNS = [
    re.compile(r"('\s*(OR|AND)\s+')|(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\s+(ALL\s+)?)",
               re.IGNORECASE),
    re.compile(r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s+", re.IGNORECASE),
    re.compile(r"--\s*$|/\*.*?\*/", re.IGNORECASE),
    re.compile(r"'\s*;\s*--", re.IGNORECASE),
    re.compile(r"(?:'\s*)?(?:OR|AND)\s+\d+\s*=\s*\d+", re.IGNORECASE),
]


def check_sqli_patterns(value: str) -> bool:
    """Detect common SQL injection patterns in user input.

    Returns True if suspicious patterns found.
    This is a defense-in-depth layer — parameterized queries are the primary defense.
    """
    if not value:
        return False
    for pattern in _SQLI_PATTERNS:
        if pattern.search(value):
            return True
    return False


# ══════════════════════════════════════════════════
#  SESSION SECURITY
# ══════════════════════════════════════════════════

def compute_session_fingerprint(user_agent: str, ip: str) -> str:
    """Compute a fingerprint from session context (UA + IP class).

    Used to detect session hijacking: if the fingerprint changes
    significantly mid-session, flag it as an anomaly.
    The IP is coarsened to /24 (IPv4) or /48 (IPv6) to tolerate
    mobile IP changes within the same carrier.
    """
    import ipaddress as _ipaddress

    ua_hash = hashlib.sha256((user_agent or "").encode()).hexdigest()[:8]

    ip_class = "unknown"
    try:
        addr = _ipaddress.ip_address(ip)
        if isinstance(addr, _ipaddress.IPv4Address):
            # Coarsen to /24
            ip_class = str(_ipaddress.IPv4Network(f"{ip}/24", strict=False).network_address)
        else:
            # Coarsen to /48
            ip_class = str(_ipaddress.IPv6Network(f"{ip}/48", strict=False).network_address)
    except (ValueError, TypeError):
        pass

    combined = f"{ua_hash}:{ip_class}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


async def check_session_binding(request: Request, user: dict) -> bool:
    """Check if the current request context matches the session's fingerprint.

    Returns True if the session appears valid (same UA class + IP range).
    Returns False if suspicious (possible session hijacking).

    Does NOT block — caller decides whether to log, warn, or revoke.
    """
    from middleware import get_client_ip, security_logger

    current_ip = get_client_ip(request)
    current_ua = request.headers.get("user-agent", "")
    current_fp = compute_session_fingerprint(current_ua, current_ip)

    # Compare with stored session context
    session_ip = user.get("session_ip", "")
    session_ua = user.get("session_ua", "")
    if not session_ip and not session_ua:
        return True  # no stored context to compare against

    stored_fp = compute_session_fingerprint(session_ua, session_ip)
    if current_fp != stored_fp:
        security_logger.session_anomaly(
            current_ip,
            reason="fingerprint_mismatch",
            stored_fp=stored_fp,
            current_fp=current_fp,
            user_id=str(user.get("id", "")),
        )
        return False
    return True


# ══════════════════════════════════════════════════
#  CONCURRENT SESSION LIMITING
# ══════════════════════════════════════════════════

MAX_CONCURRENT_SESSIONS = int(os.environ.get("MAX_SESSIONS_PER_USER", "5"))


def check_session_count(active_sessions: int) -> bool:
    """Check if a user has exceeded the concurrent session limit.

    Returns True if within limit, False if exceeded.
    """
    return active_sessions <= MAX_CONCURRENT_SESSIONS


# ══════════════════════════════════════════════════
#  SECURITY RESPONSE HEADERS
# ══════════════════════════════════════════════════

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(self)",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

SECURITY_HEADERS_PROD = {
    **SECURITY_HEADERS,
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
}


def generate_csp_nonce() -> str:
    return secrets.token_urlsafe(16)


def build_csp(nonce: str = "") -> str:
    script_src = f"'self' 'nonce-{nonce}'" if nonce else "'self'"
    return (
        "default-src 'self'; "
        f"script-src {script_src}; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )


def get_security_headers(is_production: bool = False) -> dict:
    """Return the appropriate security headers dict for the environment."""
    return SECURITY_HEADERS_PROD if is_production else SECURITY_HEADERS


# ══════════════════════════════════════════════════
#  BOT / SCANNER DETECTION
# ══════════════════════════════════════════════════

_BOT_UA_PATTERNS = [
    re.compile(r'\b(sqlmap|nikto|nessus|openvas|burpsuite|acunetix|netsparker)\b', re.IGNORECASE),
    re.compile(r'\b(masscan|zmap|zgrab|gobuster|dirbuster|dirb|wfuzz|ffuf)\b', re.IGNORECASE),
    re.compile(r'\b(nuclei|subfinder|amass|httpx|waybackurls|gau)\b', re.IGNORECASE),
    re.compile(r'\b(python-requests|python-urllib|go-http-client|java/\d|libwww-perl)\b', re.IGNORECASE),
    re.compile(r'\b(wget|curl)/\d', re.IGNORECASE),
    re.compile(r'\b(scrapy|phantomjs|headlesschrome|slimerjs)\b', re.IGNORECASE),
    re.compile(r'^\s*$'),  # empty UA
]

_LEGIT_BOT_PATTERNS = [
    re.compile(r'googlebot|bingbot|yandexbot|duckduckbot|slurp|baiduspider', re.IGNORECASE),
    re.compile(r'facebookexternalhit|twitterbot|linkedinbot|whatsapp', re.IGNORECASE),
]


def detect_bot_ua(user_agent: str) -> dict:
    """Analyze User-Agent string for bot/scanner signatures.

    Returns {is_bot: bool, is_legit_bot: bool, category: str, confidence: float}
    """
    if not user_agent or not user_agent.strip():
        return {"is_bot": True, "is_legit_bot": False, "category": "empty_ua", "confidence": 0.7}

    for pat in _LEGIT_BOT_PATTERNS:
        if pat.search(user_agent):
            return {"is_bot": True, "is_legit_bot": True, "category": "search_engine", "confidence": 0.9}

    for pat in _BOT_UA_PATTERNS:
        if pat.search(user_agent):
            return {"is_bot": True, "is_legit_bot": False, "category": "scanner", "confidence": 0.9}

    if len(user_agent) < 20:
        return {"is_bot": True, "is_legit_bot": False, "category": "short_ua", "confidence": 0.5}

    return {"is_bot": False, "is_legit_bot": False, "category": "normal", "confidence": 0.0}


# ══════════════════════════════════════════════════
#  SSRF PROTECTION
# ══════════════════════════════════════════════════

import ipaddress as _ipaddress

_SSRF_BLOCKED_SCHEMES = frozenset({"file", "ftp", "gopher", "ldap", "dict", "telnet"})


def validate_url_safe(url: str) -> dict:
    """Validate a user-supplied URL is safe to fetch (SSRF prevention).

    Blocks: private IPs, loopback, link-local, metadata endpoints,
    dangerous schemes, and cloud metadata services.
    Returns {safe: bool, reason: str}
    """
    if not url:
        return {"safe": False, "reason": "empty_url"}

    url_lower = url.strip().lower()

    # Block dangerous schemes
    for scheme in _SSRF_BLOCKED_SCHEMES:
        if url_lower.startswith(f"{scheme}://") or url_lower.startswith(f"{scheme}:"):
            return {"safe": False, "reason": f"blocked_scheme:{scheme}"}

    # Block cloud metadata endpoints
    _metadata_patterns = [
        "169.254.169.254",  # AWS/GCP metadata
        "metadata.google.internal",
        "metadata.azure.com",
        "100.100.100.200",  # Alibaba
    ]
    for meta in _metadata_patterns:
        if meta in url_lower:
            return {"safe": False, "reason": "cloud_metadata"}

    # Extract hostname (simple parsing — handles http(s)://host:port/path)
    import urllib.parse as _urlparse
    try:
        parsed = _urlparse.urlparse(url)
        hostname = parsed.hostname or ""
    except Exception:
        return {"safe": False, "reason": "invalid_url"}

    if not hostname:
        return {"safe": False, "reason": "no_hostname"}

    # Check if hostname resolves to private/reserved IP
    try:
        addr = _ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
            return {"safe": False, "reason": "private_ip"}
    except ValueError:
        # hostname is a domain name — check known dangerous patterns
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return {"safe": False, "reason": "loopback"}
        if hostname.endswith(".internal") or hostname.endswith(".local"):
            return {"safe": False, "reason": "internal_domain"}

    return {"safe": True, "reason": ""}


# ══════════════════════════════════════════════════
#  OPEN REDIRECT PREVENTION
# ══════════════════════════════════════════════════

_DEFAULT_ALLOWED_HOSTS = frozenset({
    "vinhlong360.com",
    "www.vinhlong360.com",
    "api.vinhlong360.com",
})


def validate_redirect_url(url: str, allowed_hosts: frozenset[str] | None = None) -> dict:
    """Validate a redirect URL to prevent open redirect attacks.

    Returns {safe: bool, reason: str}
    """
    if not url:
        return {"safe": False, "reason": "empty_url"}

    hosts = allowed_hosts or _DEFAULT_ALLOWED_HOSTS

    # Strip control chars and whitespace that browsers may ignore in scheme position
    import re as _re
    url_stripped = _re.sub(r'[\x00-\x1f\x7f\s]', '', url).lower()
    if url_stripped.startswith("javascript:") or url_stripped.startswith("data:") or url_stripped.startswith("vbscript:"):
        return {"safe": False, "reason": "dangerous_scheme"}

    # Relative URLs are safe
    if url.startswith("/") and not url.startswith("//"):
        return {"safe": True, "reason": "relative_path"}

    # Protocol-relative URLs — block (attacker-controlled host)
    if url.startswith("//"):
        return {"safe": False, "reason": "protocol_relative"}

    # Absolute URLs — check host
    import urllib.parse as _urlparse
    try:
        parsed = _urlparse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
    except Exception:
        return {"safe": False, "reason": "invalid_url"}

    if hostname in hosts:
        return {"safe": True, "reason": "allowed_host"}

    return {"safe": False, "reason": "unknown_host"}


# ══════════════════════════════════════════════════
#  PATH TRAVERSAL DETECTION
# ══════════════════════════════════════════════════

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r'\.\.[\\/]'),             # ../  ..\
    re.compile(r'%2e%2e[/\\%]', re.IGNORECASE),  # URL-encoded ../
    re.compile(r'%252e%252e', re.IGNORECASE),     # double-encoded
    re.compile(r'\.\.%2f', re.IGNORECASE),        # mixed encoding
    re.compile(r'%c0%ae', re.IGNORECASE),         # overlong UTF-8 encoding of .
    re.compile(r'%c1%1c', re.IGNORECASE),         # overlong /
    re.compile(r'\.\./'),                          # plain ../
]


def check_path_traversal(path: str) -> bool:
    """Detect path traversal attempts in user input.

    Returns True if traversal patterns found.
    """
    if not path:
        return False
    for pat in _PATH_TRAVERSAL_PATTERNS:
        if pat.search(path):
            return True
    # Null byte injection
    if '\x00' in path or '%00' in path:
        return True
    return False


# ══════════════════════════════════════════════════
#  PASSWORD STRENGTH CHECKER
# ══════════════════════════════════════════════════

import math as _math

_COMMON_PASSWORDS = frozenset({
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "dragon",
    "123123", "baseball", "abc123", "football", "monkey",
    "letmein", "shadow", "master", "666666", "qwerty123",
    "654321", "123321", "iloveyou", "admin", "welcome",
    "1q2w3e4r", "sunshine", "princess", "passw0rd", "P@ssw0rd",
    "matkhau", "matkhau123", "mk123456", "abcdef",
    "vinhlong", "vinhlong360", "password1", "admin123",
})

_KEYBOARD_SEQUENCES = [
    "qwerty", "asdfgh", "zxcvbn", "qweasd", "1qaz2wsx",
    "qazwsx", "12345678", "abcdefgh",
]


def check_password_strength(password: str) -> dict:
    """Evaluate password strength.

    Returns {strong: bool, score: int (0-5), issues: list[str]}
    """
    if not password:
        return {"strong": False, "score": 0, "issues": ["empty"]}

    issues = []
    score = 0

    if len(password) < 8:
        issues.append("too_short")
    elif len(password) >= 12:
        score += 1

    if password.lower() in _COMMON_PASSWORDS:
        issues.append("common_password")
        return {"strong": False, "score": 0, "issues": issues}

    for seq in _KEYBOARD_SEQUENCES:
        if seq in password.lower():
            issues.append("keyboard_sequence")
            break

    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[^a-zA-Z0-9]', password))

    char_classes = sum([has_lower, has_upper, has_digit, has_special])
    score += char_classes

    if char_classes < 2:
        issues.append("low_variety")

    charset_size = 0
    if has_lower: charset_size += 26
    if has_upper: charset_size += 26
    if has_digit: charset_size += 10
    if has_special: charset_size += 32
    if charset_size > 0:
        entropy = len(password) * _math.log2(charset_size)
        if entropy >= 50:
            score += 1
        if entropy < 28:
            issues.append("low_entropy")

    # Repeating characters
    if re.search(r'(.)\1{3,}', password):
        issues.append("repeated_chars")

    strong = score >= 3 and not issues
    return {"strong": strong, "score": min(5, score), "issues": issues}


# ══════════════════════════════════════════════════
#  SENSITIVE DATA LEAK DETECTION
# ══════════════════════════════════════════════════

_PII_PATTERNS = {
    "phone_vn": re.compile(r'\b(0[35789]\d{8})\b'),
    "email": re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    "cccd": re.compile(r'\b\d{12}\b'),  # Vietnamese Citizen ID (CCCD)
    "credit_card": re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'),
    "api_key": re.compile(r'\b(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})\b'),
}


def detect_pii(text: str) -> dict:
    """Detect potential PII/sensitive data in text.

    Returns {has_pii: bool, types: list[str], count: int}
    """
    if not text:
        return {"has_pii": False, "types": [], "count": 0}
    found_types = []
    total = 0
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found_types.append(pii_type)
            total += len(matches)
    return {"has_pii": bool(found_types), "types": found_types, "count": total}


def mask_pii(text: str) -> str:
    """Mask detected PII patterns in text for safe logging."""
    if not text:
        return ""
    result = text
    result = _PII_PATTERNS["phone_vn"].sub("[PHONE]", result)
    result = _PII_PATTERNS["email"].sub("[EMAIL]", result)
    result = _PII_PATTERNS["credit_card"].sub("[CARD]", result)
    result = _PII_PATTERNS["api_key"].sub("[API_KEY]", result)
    return result


# ══════════════════════════════════════════════════
#  ERROR MESSAGE SANITIZATION
# ══════════════════════════════════════════════════

_ERROR_LEAK_PATTERNS = [
    re.compile(r'File ".*?", line \d+', re.IGNORECASE),
    re.compile(r'Traceback \(most recent', re.IGNORECASE),
    re.compile(r'at [\w.]+\([\w.]+:\d+\)'),  # Java/JS-style stack frames
    re.compile(r'(password|secret|token|api_key)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(postgresql|mysql|sqlite|mongodb)://\S+', re.IGNORECASE),
    re.compile(r'SQLSTATE\[\w+\]', re.IGNORECASE),
]


def sanitize_error_message(error: str, is_production: bool = True) -> str:
    """Strip internal details from error messages before returning to clients.

    In production, replaces any error containing internal details with a generic message.
    In development, passes through for debugging.
    """
    if not error:
        return "Đã xảy ra lỗi. Vui lòng thử lại."
    if not is_production:
        return error
    for pattern in _ERROR_LEAK_PATTERNS:
        if pattern.search(error):
            return "Đã xảy ra lỗi. Vui lòng thử lại."
    return error


# ══════════════════════════════════════════════════
#  FILE UPLOAD VALIDATION
# ══════════════════════════════════════════════════

_ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})
_DANGEROUS_EXTENSIONS = frozenset({
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".msi",
    ".dll", ".com", ".scr", ".pif", ".php", ".jsp", ".asp", ".aspx",
    ".py", ".rb", ".pl", ".cgi", ".htaccess", ".svg",
})
_MAX_FILENAME_LENGTH = 255

# Magic bytes for image file validation
_IMAGE_MAGIC_BYTES = {
    b'\xff\xd8\xff': "image/jpeg",
    b'\x89PNG\r\n\x1a\n': "image/png",
    b'GIF87a': "image/gif",
    b'GIF89a': "image/gif",
    b'RIFF': "image/webp",  # WebP starts with RIFF....WEBP
}


def validate_file_upload(
    filename: str,
    content_type: str = "",
    file_size: int = 0,
    file_header: bytes = b"",
    max_size: int = 5_242_880,
) -> dict:
    """Validate a file upload for safety.

    Returns {safe: bool, issues: list[str]}
    """
    issues = []

    if not filename:
        return {"safe": False, "issues": ["no_filename"]}

    # Sanitize filename
    clean_name = filename.replace("\\", "/").split("/")[-1]
    if clean_name != filename:
        issues.append("path_in_filename")

    if len(clean_name) > _MAX_FILENAME_LENGTH:
        issues.append("filename_too_long")

    # Check extension
    ext = ""
    if "." in clean_name:
        ext = "." + clean_name.rsplit(".", 1)[-1].lower()

    if ext in _DANGEROUS_EXTENSIONS:
        issues.append(f"dangerous_extension:{ext}")

    # Double extension attack (e.g., image.php.jpg → still dangerous)
    parts = clean_name.lower().split(".")
    if len(parts) > 2:
        for p in parts[1:-1]:
            if f".{p}" in _DANGEROUS_EXTENSIONS:
                issues.append("double_extension_attack")
                break

    # Null byte in filename
    if "\x00" in filename or "%00" in filename:
        issues.append("null_byte_injection")

    # Content-Type validation
    if content_type and content_type not in _ALLOWED_IMAGE_TYPES:
        issues.append(f"disallowed_content_type:{content_type}")

    # Size validation
    if file_size > max_size:
        issues.append(f"file_too_large:{file_size}")

    # Magic byte validation (if header provided)
    if file_header and content_type in _ALLOWED_IMAGE_TYPES:
        matched_type = None
        for magic, mime in _IMAGE_MAGIC_BYTES.items():
            if file_header[:len(magic)] == magic:
                matched_type = mime
                break
        if matched_type is None:
            issues.append("magic_bytes_mismatch")
        elif content_type and matched_type != content_type:
            if not (content_type == "image/webp" and file_header[:4] == b'RIFF'):
                issues.append("content_type_mismatch")

    safe = not issues
    return {"safe": safe, "issues": issues}


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage. Strips path components and dangerous chars."""
    if not filename:
        return "unnamed"
    name = filename.replace("\\", "/").split("/")[-1]
    name = re.sub(r'[^\w\-.]', '_', name)
    name = name.lstrip(".")
    if not name:
        return "unnamed"
    if len(name) > _MAX_FILENAME_LENGTH:
        ext = ""
        if "." in name:
            ext = "." + name.rsplit(".", 1)[-1][:10]
        name = name[:_MAX_FILENAME_LENGTH - len(ext)] + ext
    return name


# ══════════════════════════════════════════════════
#  REQUEST SIGNING / INTEGRITY
# ══════════════════════════════════════════════════

def compute_request_signature(
    method: str, path: str, body: str, secret: str, timestamp: str = ""
) -> str:
    """Compute HMAC-SHA256 signature for request integrity verification.

    Payload = METHOD:PATH:TIMESTAMP:BODY
    """
    payload = f"{method.upper()}:{path}:{timestamp}:{body}"
    return hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def verify_request_signature(
    method: str, path: str, body: str, secret: str,
    signature: str, timestamp: str = "",
    max_age: int = 300,
) -> dict:
    """Verify request signature for API integrity.

    Returns {valid: bool, reason: str}
    """
    if not signature or not secret:
        return {"valid": False, "reason": "missing_signature_or_secret"}

    # Check timestamp freshness (prevent replay)
    if timestamp:
        try:
            import time as _time
            ts = int(timestamp)
            now = int(_time.time())
            if abs(now - ts) > max_age:
                return {"valid": False, "reason": "timestamp_expired"}
        except (ValueError, TypeError):
            return {"valid": False, "reason": "invalid_timestamp"}

    expected = compute_request_signature(method, path, body, secret, timestamp)
    if hmac.compare_digest(signature, expected):
        return {"valid": True, "reason": ""}
    return {"valid": False, "reason": "signature_mismatch"}


# ══════════════════════════════════════════════════
#  ACCOUNT LOCKOUT
# ══════════════════════════════════════════════════

import time as _time
from threading import Lock as _Lock

_login_failures: dict[str, list[float]] = {}
_locked_accounts: dict[str, float] = {}
_lockout_lock = _Lock()

LOCKOUT_THRESHOLD = int(os.environ.get("LOCKOUT_THRESHOLD", "5"))
LOCKOUT_DURATION = int(os.environ.get("LOCKOUT_DURATION", "900"))  # 15 minutes
LOCKOUT_WINDOW = int(os.environ.get("LOCKOUT_WINDOW", "300"))  # 5 minutes


def record_login_failure(identifier: str) -> dict:
    """Record a failed login attempt and check for lockout.

    identifier: username, email, or phone used in the attempt.
    Returns {locked: bool, remaining_attempts: int, lockout_until: float|None}
    """
    now = _time.time()
    with _lockout_lock:
        # Check if already locked
        if identifier in _locked_accounts:
            lock_until = _locked_accounts[identifier]
            if now < lock_until:
                return {
                    "locked": True,
                    "remaining_attempts": 0,
                    "lockout_until": lock_until,
                }
            else:
                del _locked_accounts[identifier]
                _login_failures.pop(identifier, None)

        # Record failure
        if identifier not in _login_failures:
            _login_failures[identifier] = []
        _login_failures[identifier].append(now)
        # Keep only failures within window
        cutoff = now - LOCKOUT_WINDOW
        _login_failures[identifier] = [t for t in _login_failures[identifier] if t > cutoff]

        failure_count = len(_login_failures[identifier])
        if failure_count >= LOCKOUT_THRESHOLD:
            lock_until = now + LOCKOUT_DURATION
            _locked_accounts[identifier] = lock_until
            _login_failures.pop(identifier, None)
            return {
                "locked": True,
                "remaining_attempts": 0,
                "lockout_until": lock_until,
            }

        return {
            "locked": False,
            "remaining_attempts": LOCKOUT_THRESHOLD - failure_count,
            "lockout_until": None,
        }


def is_account_locked(identifier: str) -> bool:
    """Check if an account is currently locked out."""
    now = _time.time()
    with _lockout_lock:
        if identifier in _locked_accounts:
            if now < _locked_accounts[identifier]:
                return True
            del _locked_accounts[identifier]
    return False


def clear_login_failures(identifier: str):
    """Clear failure history on successful login."""
    with _lockout_lock:
        _login_failures.pop(identifier, None)
        _locked_accounts.pop(identifier, None)


def _reset_lockouts():
    """Test-only."""
    with _lockout_lock:
        _login_failures.clear()
        _locked_accounts.clear()


# ══════════════════════════════════════════════════
#  CONTENT-TYPE ENFORCEMENT
# ══════════════════════════════════════════════════

_EXPECTED_CONTENT_TYPES = {
    "json": frozenset({"application/json", "application/json; charset=utf-8"}),
    "form": frozenset({"application/x-www-form-urlencoded", "multipart/form-data"}),
    "multipart": frozenset({"multipart/form-data"}),
}


def validate_content_type(
    content_type: str, expected: str = "json"
) -> dict:
    """Validate Content-Type header to prevent content-type confusion attacks.

    Returns {valid: bool, reason: str}
    """
    if not content_type:
        return {"valid": False, "reason": "missing_content_type"}

    allowed = _EXPECTED_CONTENT_TYPES.get(expected, set())
    ct_lower = content_type.lower().split(";")[0].strip()

    if expected == "multipart":
        if ct_lower.startswith("multipart/form-data"):
            return {"valid": True, "reason": ""}
        return {"valid": False, "reason": f"expected_multipart_got:{ct_lower}"}

    if ct_lower in allowed:
        return {"valid": True, "reason": ""}

    # Special case: allow charset variants for JSON
    if expected == "json" and ct_lower == "application/json":
        return {"valid": True, "reason": ""}

    return {"valid": False, "reason": f"unexpected_content_type:{ct_lower}"}


# ══════════════════════════════════════════════════
#  SECURE COOKIE CONFIGURATION
# ══════════════════════════════════════════════════

def get_secure_cookie_params(is_production: bool = False) -> dict:
    """Return secure cookie parameters for session cookies.

    Production: Secure + HttpOnly + SameSite=Lax + __Host- prefix
    Development: HttpOnly + SameSite=Lax (no Secure for localhost)
    """
    base = {
        "httponly": True,
        "samesite": "lax",
        "path": "/",
        "max_age": 86400 * 7,  # 7 days
    }
    if is_production:
        base["secure"] = True
        base["samesite"] = "lax"
        base["domain"] = ".vinhlong360.com"
    return base


# ══════════════════════════════════════════════════
#  RATE LIMIT RESPONSE HEADERS
# ══════════════════════════════════════════════════

def build_rate_limit_headers(
    limit: int, remaining: int, reset_seconds: int
) -> dict:
    """Build standard rate-limit response headers (RFC draft).

    Used by middleware to inform clients about their rate limit status.
    """
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Reset": str(reset_seconds),
        "Retry-After": str(reset_seconds) if remaining <= 0 else "",
    }


# ══════════════════════════════════════════════════
#  CORS ORIGIN VALIDATION
# ══════════════════════════════════════════════════

_ALLOWED_ORIGINS = frozenset({
    "https://vinhlong360.com",
    "https://www.vinhlong360.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
})

_ALLOWED_ORIGIN_PATTERNS = [
    re.compile(r'^https://[\w-]+\.vinhlong360\.com$'),
    re.compile(r'^https://vinhlong360-[\w-]+\.vercel\.app$'),
]


def validate_cors_origin(origin: str, is_production: bool = False) -> dict:
    """Validate CORS Origin header against allowed list.

    Returns {allowed: bool, reason: str}
    """
    if not origin:
        return {"allowed": False, "reason": "missing_origin"}

    if origin in _ALLOWED_ORIGINS:
        if is_production and origin.startswith("http://localhost"):
            return {"allowed": False, "reason": "localhost_in_production"}
        return {"allowed": True, "reason": "exact_match"}

    for pat in _ALLOWED_ORIGIN_PATTERNS:
        if pat.match(origin):
            return {"allowed": True, "reason": "pattern_match"}

    return {"allowed": False, "reason": "unknown_origin"}


# ══════════════════════════════════════════════════
#  JWT / TOKEN STRUCTURE VALIDATION
# ══════════════════════════════════════════════════

import base64 as _base64
import json as _json


def validate_token_structure(token: str) -> dict:
    """Validate JWT-like token structure (without verifying signature).

    Checks: format (3 base64 parts), header algorithm, expiry claim.
    This is a fast pre-check before expensive signature verification.
    Returns {valid: bool, issues: list[str], claims: dict}
    """
    if not token:
        return {"valid": False, "issues": ["empty_token"], "claims": {}}

    issues = []
    parts = token.split(".")

    if len(parts) != 3:
        return {"valid": False, "issues": ["invalid_format"], "claims": {}}

    # Check header
    try:
        padding = 4 - len(parts[0]) % 4
        header_b64 = parts[0] + "=" * padding
        header = _json.loads(_base64.urlsafe_b64decode(header_b64))
    except Exception:
        return {"valid": False, "issues": ["invalid_header"], "claims": {}}

    alg = header.get("alg", "")
    if alg.lower() == "none":
        issues.append("alg_none_attack")
    if alg in ("HS256",) and header.get("typ") != "JWT":
        issues.append("missing_typ")

    # Dangerous algorithms
    if alg in ("HS384", "HS512"):
        pass  # acceptable
    elif alg in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
        pass  # asymmetric — good
    elif alg == "HS256":
        pass  # common, acceptable

    # Check payload
    try:
        padding = 4 - len(parts[1]) % 4
        payload_b64 = parts[1] + "=" * padding
        claims = _json.loads(_base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {"valid": False, "issues": ["invalid_payload"], "claims": {}}

    # Check expiry
    exp = claims.get("exp")
    if exp:
        try:
            if float(exp) < _time.time():
                issues.append("token_expired")
        except (ValueError, TypeError):
            issues.append("invalid_exp")
    else:
        issues.append("no_expiry")

    return {
        "valid": not issues,
        "issues": issues,
        "claims": claims,
    }


# ══════════════════════════════════════════════════
#  REQUEST DEDUPLICATION
# ══════════════════════════════════════════════════

_seen_idempotency_keys: dict[str, float] = {}
_dedup_lock = _Lock()
_DEDUP_WINDOW = 300  # 5 minutes


def check_idempotency(key: str) -> dict:
    """Check if a request with this idempotency key was already processed.

    Returns {is_duplicate: bool, first_seen: float|None}
    """
    if not key:
        return {"is_duplicate": False, "first_seen": None}

    now = _time.time()
    with _dedup_lock:
        # GC old entries
        if len(_seen_idempotency_keys) > 50_000:
            cutoff = now - _DEDUP_WINDOW
            dead = [k for k, ts in _seen_idempotency_keys.items() if ts < cutoff]
            for k in dead:
                del _seen_idempotency_keys[k]

        if key in _seen_idempotency_keys:
            first = _seen_idempotency_keys[key]
            if now - first < _DEDUP_WINDOW:
                return {"is_duplicate": True, "first_seen": first}

        _seen_idempotency_keys[key] = now
        return {"is_duplicate": False, "first_seen": now}


async def require_idempotency(request: Request) -> None:
    """FastAPI dependency: reject duplicate POST requests via Idempotency-Key header."""
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        return
    user = await _get_current_user_or_none(request)
    if user:
        key = f"{user['id']}:{key}"
    result = check_idempotency(key)
    if result["is_duplicate"]:
        raise HTTPException(409, "Yêu cầu trùng lặp (idempotency key đã được xử lý)")


def _reset_idempotency():
    """Test-only."""
    with _dedup_lock:
        _seen_idempotency_keys.clear()


# ══════════════════════════════════════════════════
#  REFERRER VALIDATION (CSRF double-check)
# ══════════════════════════════════════════════════

_ALLOWED_REFERRERS = frozenset({
    "vinhlong360.com",
    "www.vinhlong360.com",
    "localhost",
    "127.0.0.1",
})


def validate_referrer(referrer: str, is_production: bool = False) -> dict:
    """Validate Referer header as secondary CSRF protection.

    Returns {valid: bool, reason: str}
    """
    if not referrer:
        return {"valid": False, "reason": "missing_referrer"}

    try:
        from urllib.parse import urlparse
        parsed = urlparse(referrer)
        host = (parsed.hostname or "").lower()
    except Exception:
        return {"valid": False, "reason": "unparseable_referrer"}

    if is_production and host in ("localhost", "127.0.0.1"):
        return {"valid": False, "reason": "localhost_in_production"}

    if host in _ALLOWED_REFERRERS:
        return {"valid": True, "reason": "allowed_host"}

    if host.endswith(".vinhlong360.com"):
        return {"valid": True, "reason": "subdomain_match"}

    return {"valid": False, "reason": "unknown_referrer"}


# ══════════════════════════════════════════════════
#  API KEY FORMAT VALIDATION
# ══════════════════════════════════════════════════

_API_KEY_PATTERNS = {
    "vl360": re.compile(r'^vl360_[a-zA-Z0-9]{32,64}$'),
    "generic": re.compile(r'^[a-zA-Z0-9_\-]{20,128}$'),
}


def validate_api_key_format(api_key: str, key_type: str = "generic") -> dict:
    """Validate API key format and entropy before checking against the database.

    Returns {valid: bool, issues: list[str]}
    """
    if not api_key:
        return {"valid": False, "issues": ["empty_key"]}

    issues = []

    if len(api_key) < 20:
        issues.append("too_short")
    if len(api_key) > 128:
        issues.append("too_long")

    pattern = _API_KEY_PATTERNS.get(key_type, _API_KEY_PATTERNS["generic"])
    if not pattern.match(api_key):
        issues.append("invalid_format")

    # Entropy check — low-entropy keys are likely guessed or trivial
    if len(api_key) >= 20:
        unique_chars = len(set(api_key))
        if unique_chars < 8:
            issues.append("low_entropy")

    # Check for obviously fake/test keys
    if api_key.lower() in ("test_key", "demo_key", "sk-test", "api_key_here"):
        issues.append("placeholder_key")

    return {"valid": not issues, "issues": issues}


# ══════════════════════════════════════════════════
#  IP ACCESS LIST (allow/deny)
# ══════════════════════════════════════════════════

import ipaddress as _ipaddress

_ip_allowlist: set[str] = set()
_ip_denylist: set[str] = set()
_ip_acl_lock = _Lock()


def add_ip_rule(ip: str, action: str = "deny"):
    """Add an IP to the allow or deny list."""
    with _ip_acl_lock:
        if action == "allow":
            _ip_allowlist.add(ip)
            _ip_denylist.discard(ip)
        elif action == "deny":
            _ip_denylist.add(ip)
            _ip_allowlist.discard(ip)


def remove_ip_rule(ip: str):
    """Remove an IP from both lists."""
    with _ip_acl_lock:
        _ip_allowlist.discard(ip)
        _ip_denylist.discard(ip)


def check_ip_access(ip: str) -> dict:
    """Check IP against access lists.

    Deny list is checked first. If neither list contains the IP, it's allowed.
    Returns {allowed: bool, reason: str}
    """
    if not ip:
        return {"allowed": False, "reason": "missing_ip"}

    with _ip_acl_lock:
        if ip in _ip_denylist:
            return {"allowed": False, "reason": "ip_denied"}
        if _ip_allowlist and ip not in _ip_allowlist:
            return {"allowed": False, "reason": "ip_not_in_allowlist"}

    # Check for private IP ranges in production-facing endpoints
    try:
        addr = _ipaddress.ip_address(ip)
        if addr.is_loopback:
            return {"allowed": True, "reason": "loopback"}
    except (ValueError, TypeError):
        return {"allowed": False, "reason": "invalid_ip"}

    return {"allowed": True, "reason": "default_allow"}


def _reset_ip_access():
    """Test-only."""
    with _ip_acl_lock:
        _ip_allowlist.clear()
        _ip_denylist.clear()


# ══════════════════════════════════════════════════
#  NONCE-BASED REPLAY PREVENTION
# ══════════════════════════════════════════════════

_used_nonces: dict[str, float] = {}
_nonce_lock = _Lock()
_NONCE_WINDOW = 300  # 5 minutes


def generate_nonce() -> str:
    """Generate a cryptographically secure nonce for request replay prevention."""
    return secrets.token_hex(16)


def verify_nonce(nonce: str, max_age: int = 0) -> dict:
    """Verify that a nonce hasn't been used before.

    Returns {valid: bool, reason: str}
    """
    if not nonce:
        return {"valid": False, "reason": "missing_nonce"}
    if len(nonce) < 16:
        return {"valid": False, "reason": "nonce_too_short"}

    window = max_age if max_age > 0 else _NONCE_WINDOW
    now = _time.time()

    with _nonce_lock:
        # GC old nonces
        if len(_used_nonces) > 100_000:
            cutoff = now - window
            dead = [k for k, ts in _used_nonces.items() if ts < cutoff]
            for k in dead:
                del _used_nonces[k]

        if nonce in _used_nonces:
            return {"valid": False, "reason": "nonce_reused"}

        _used_nonces[nonce] = now
        return {"valid": True, "reason": ""}


def _reset_nonces():
    """Test-only."""
    with _nonce_lock:
        _used_nonces.clear()


# ══════════════════════════════════════════════════
#  PERMISSION BOUNDARY CHECK (RBAC)
# ══════════════════════════════════════════════════

_ROLE_HIERARCHY = {
    "superadmin": 100,
    "admin": 80,
    "moderator": 60,
    "editor": 40,
    "user": 20,
    "guest": 0,
}


def check_permission_boundary(
    user_role: str, required_role: str
) -> dict:
    """Check if a user's role meets the minimum required permission level.

    Uses a hierarchical role model.
    Returns {allowed: bool, user_level: int, required_level: int}
    """
    user_level = _ROLE_HIERARCHY.get(user_role, 0)
    required_level = _ROLE_HIERARCHY.get(required_role, 0)

    return {
        "allowed": user_level >= required_level,
        "user_level": user_level,
        "required_level": required_level,
    }


# ══════════════════════════════════════════════════
#  WEBHOOK SIGNATURE VERIFICATION
# ══════════════════════════════════════════════════

def verify_webhook_signature(
    payload: bytes, signature: str, secret: str,
    algorithm: str = "sha256",
) -> dict:
    """Verify incoming webhook signature (GitHub, Stripe, etc.).

    Returns {valid: bool, reason: str}
    """
    if not payload or not signature or not secret:
        return {"valid": False, "reason": "missing_params"}

    algos = {"sha256": hashlib.sha256, "sha1": hashlib.sha1}
    hash_fn = algos.get(algorithm)
    if not hash_fn:
        return {"valid": False, "reason": "unsupported_algorithm"}

    expected = hmac.new(secret.encode(), payload, hash_fn).hexdigest()

    # Handle "sha256=..." prefix format (GitHub style)
    sig_value = signature
    prefix = f"{algorithm}="
    if sig_value.startswith(prefix):
        sig_value = sig_value[len(prefix):]

    if hmac.compare_digest(sig_value, expected):
        return {"valid": True, "reason": ""}
    return {"valid": False, "reason": "signature_mismatch"}


# ══════════════════════════════════════════════════
#  SESSION PRIVILEGE ESCALATION GUARD
# ══════════════════════════════════════════════════

def check_privilege_escalation(
    current_role: str, target_role: str
) -> dict:
    """Detect and prevent privilege escalation attempts.

    Users cannot elevate their own role beyond their current level.
    Returns {is_escalation: bool, reason: str}
    """
    current_level = _ROLE_HIERARCHY.get(current_role, 0)
    target_level = _ROLE_HIERARCHY.get(target_role, 0)

    if target_level > current_level:
        return {
            "is_escalation": True,
            "reason": f"cannot_escalate_{current_role}_to_{target_role}",
        }
    return {"is_escalation": False, "reason": ""}
