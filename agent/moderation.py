"""
vinhlong360 — Auto Moderation Pipeline.

3-step pipeline:
  1. OpenAI Moderation API (text) — miễn phí, tiếng Việt hiệu năng cao
  2. Google Vision SafeSearch (ảnh) — free 1.000 ảnh/tháng
  3. Auto-decision: score < 0.3 → approve, 0.3-0.7 → queue, > 0.7 → flag

Chỉ gửi nội dung bài (không kèm định danh user) sang API nước ngoài → giảm rủi ro PDPL.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

from database import db

# ── Config ──

OPENAI_API_KEY = os.getenv("LLM_API_KEY", "")
OPENAI_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
VISION_API_KEY = os.getenv("VISION_API_KEY", "")

AUTO_APPROVE_THRESHOLD = 0.3
QUEUE_THRESHOLD = 0.7


async def moderate_content(content: str, image_urls: list[str] = None) -> dict:
    """
    Run moderation pipeline on content + images.
    Returns: {status, scores, reasons}
    """
    text_result = await _moderate_text(content)
    image_result = await _moderate_images(image_urls or [])
    link_result = _check_links(content)
    spam_result = _check_spam_patterns(content)

    max_score = max(text_result["score"], image_result["score"],
                    link_result["score"], spam_result["score"])
    reasons = text_result["reasons"] + image_result["reasons"] + \
              link_result["reasons"] + spam_result["reasons"]

    if max_score < AUTO_APPROVE_THRESHOLD:
        status = "approved"
    elif max_score < QUEUE_THRESHOLD:
        status = "pending"
    else:
        status = "flagged"

    return {
        "status": status,
        "score": round(max_score, 3),
        "reasons": reasons,
        "text_scores": text_result.get("categories", {}),
        "image_scores": image_result.get("categories", {}),
    }


_SHORTENER_PATTERN = re.compile(
    r'https?://(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|buff\.ly|adf\.ly|shorte\.st)\b',
    re.IGNORECASE,
)
_URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)

# P0-2: local spam patterns (works WITHOUT external API key).
# Catches common Vietnamese spam phrases, casino/gambling, crypto scams,
# phone-number harvesting, and repetitive character spam.
# Patterns handle BOTH diacritical (sòng bài) and ASCII (song bai) Vietnamese
# since spammers often strip diacritics to evade detection.
_SPAM_PATTERNS = [
    # Casino / gambling (diacritical + ASCII variants)
    re.compile(
        r'\b(casino|s[oò]ng\s*b[aà]i|c[aá]\s*c[uư][oớ]c|'
        r'x[oổ]\s*s[oố]\s*online|slot\s*game|n[oổ]\s*h[uũ]|'
        r'b[aắ]n\s*c[aá]\s*online)\b',
        re.IGNORECASE,
    ),
    # Crypto / investment scams
    re.compile(
        r'\b(ki[eế]m\s*ti[eề]n\s*online|l[aà]m\s*gi[aà]u\s*nhanh|'
        r'thu\s*nh[aậ]p\s*th[uụ]\s*[dđ][oộ]ng|[dđ][aầ]u\s*t[uư]\s*x\d+|'
        r'l[oợ]i\s*nhu[aậ]n\s*\d{2,3}%)',
        re.IGNORECASE,
    ),
    # Adult / sex spam
    re.compile(
        r'\b(g[aá]i\s*g[oọ]i|m[aạ]i\s*d[aâ]m|sex\s*online|18\+|phim\s*sex)\b',
        re.IGNORECASE,
    ),
    # Contact spam (repeated phone/Zalo/Telegram solicitation)
    re.compile(
        r'(li[eê]n\s*h[eệ]|inbox|zalo|telegram|whatsapp).{0,20}\d{9,}',
        re.IGNORECASE,
    ),
    # Repetitive character spam (e.g., "aaaaaaa" or "!!!!!!")
    re.compile(r'(.)\1{9,}'),
]


def _check_spam_patterns(content: str) -> dict:
    """P0-2: local spam pattern detection (no API needed).

    Catches common spam/scam phrases so even without an external moderation
    API key, harmful content is held for manual review.
    """
    if not content or not content.strip():
        return {"score": 0.0, "reasons": []}
    reasons = []
    score = 0.0
    for pattern in _SPAM_PATTERNS:
        match = pattern.search(content)
        if match:
            score = max(score, 0.5)
            reasons.append(f"spam:pattern_match({match.group()[:30]})")
    return {"score": score, "reasons": reasons}


def _check_links(content: str) -> dict:
    """Step 4: flag posts with suspicious link patterns (spam, phishing)."""
    if not content:
        return {"score": 0.0, "reasons": []}
    urls = _URL_PATTERN.findall(content)
    if not urls:
        return {"score": 0.0, "reasons": []}
    reasons = []
    score = 0.0
    if _SHORTENER_PATTERN.search(content):
        score = max(score, 0.6)
        reasons.append("link:shortener")
    if len(urls) >= 3:
        score = max(score, 0.5)
        reasons.append("link:excessive")
    elif len(urls) >= 1 and not reasons:
        score = max(score, 0.15)
    return {"score": score, "reasons": reasons}


async def _moderate_text(content: str) -> dict:
    """Step 1: OpenAI Moderation API (free, excellent Vietnamese support)."""
    if not content or not content.strip():
        return {"score": 0.0, "reasons": [], "categories": {}}

    if not OPENAI_API_KEY:
        return {"score": 0.0, "reasons": ["[dev] No moderation API key"], "categories": {}}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{OPENAI_BASE_URL}/moderations",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"input": content, "model": "omni-moderation-latest"},
            )
            data = resp.json()

        if "results" not in data or not data["results"]:
            return {"score": 0.0, "reasons": ["moderation API returned no results"], "categories": {}}

        result = data["results"][0]
        categories = result.get("category_scores", {})
        flagged_cats = result.get("categories", {})

        max_score = max(categories.values()) if categories else 0.0
        reasons = [cat for cat, flagged in flagged_cats.items() if flagged]

        return {
            "score": max_score,
            "reasons": [f"text:{r}" for r in reasons],
            "categories": categories,
        }
    except Exception as e:
        logger.warning("Text moderation error: %s", e)
        return {"score": 0.0, "reasons": [f"error: {e}"], "categories": {}}


async def _moderate_images(image_urls: list[str]) -> dict:
    """Step 2: Google Vision SafeSearch (free 1k/month)."""
    if not image_urls:
        return {"score": 0.0, "reasons": [], "categories": {}}

    if not VISION_API_KEY:
        return {"score": 0.0, "reasons": ["[dev] No Vision API key"], "categories": {}}

    max_score = 0.0
    all_reasons = []
    all_categories = {}

    likelihood_scores = {
        "VERY_UNLIKELY": 0.0,
        "UNLIKELY": 0.1,
        "POSSIBLE": 0.4,
        "LIKELY": 0.7,
        "VERY_LIKELY": 0.95,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for url in image_urls[:4]:
                resp = await client.post(
                    f"https://vision.googleapis.com/v1/images:annotate?key={VISION_API_KEY}",
                    json={
                        "requests": [{
                            "image": {"source": {"imageUri": url}},
                            "features": [{"type": "SAFE_SEARCH_DETECTION"}],
                        }]
                    },
                )
                data = resp.json()
                responses = data.get("responses", [])
                if not responses:
                    continue

                safe = responses[0].get("safeSearchAnnotation", {})
                for category in ("adult", "violence", "racy"):
                    likelihood = safe.get(category, "VERY_UNLIKELY")
                    score = likelihood_scores.get(likelihood, 0.0)
                    all_categories[f"image_{category}"] = score
                    if score > max_score:
                        max_score = score
                    if score >= QUEUE_THRESHOLD:
                        all_reasons.append(f"image:{category}={likelihood}")
    except Exception as e:
        logger.warning("Image moderation error: %s", e)

    return {
        "score": max_score,
        "reasons": all_reasons,
        "categories": all_categories,
    }


# ══════════════════════════════════════════════════
#  CONTENT FINGERPRINTING (duplicate / raid detection)
# ══════════════════════════════════════════════════

import hashlib as _hashlib
import unicodedata as _unicodedata
from collections import defaultdict as _defaultdict
from threading import Lock as _Lock
import time as _time

_content_hashes: dict[str, list[tuple[float, str]]] = _defaultdict(list)
_FINGERPRINT_WINDOW = 3600  # 1 hour
_FINGERPRINT_THRESHOLD = 3  # 3+ identical posts in 1h = raid
_fingerprint_lock = _Lock()


def _normalize_for_fingerprint(content: str) -> str:
    """Normalize content for fingerprint comparison.

    Strips whitespace variations, lowercases, removes diacritics so
    slight variations of the same spam don't evade dedup.
    """
    text = content.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    # Strip Vietnamese diacritics for comparison
    nfkd = _unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in nfkd if not _unicodedata.combining(c))
    return text


def content_fingerprint(content: str) -> str:
    """SHA-256 fingerprint of normalized content."""
    normalized = _normalize_for_fingerprint(content)
    return _hashlib.sha256(normalized.encode()).hexdigest()[:16]


def check_content_duplicate(content: str, user_id: str = "") -> dict:
    """Check if near-identical content has been posted recently (raid detection).

    Returns {is_duplicate: bool, count: int, score: float}
    """
    if not content or len(content) < 20:
        return {"is_duplicate": False, "count": 0, "score": 0.0}

    fp = content_fingerprint(content)
    now = _time.time()

    with _fingerprint_lock:
        entries = _content_hashes.get(fp, [])
        entries = [(ts, uid) for ts, uid in entries if now - ts < _FINGERPRINT_WINDOW]
        # Count posts from different users with same fingerprint
        unique_users = {uid for _, uid in entries if uid != user_id}
        count = len(entries)

        entries.append((now, user_id))
        _content_hashes[fp] = entries

        # GC
        if len(_content_hashes) > 50_000:
            cutoff = now - _FINGERPRINT_WINDOW
            dead = [k for k, v in _content_hashes.items()
                    if not v or v[-1][0] < cutoff]
            for k in dead:
                del _content_hashes[k]

    is_dup = count >= _FINGERPRINT_THRESHOLD
    score = min(1.0, count / _FINGERPRINT_THRESHOLD) * 0.7 if count > 0 else 0.0
    return {
        "is_duplicate": is_dup,
        "count": count,
        "unique_posters": len(unique_users),
        "score": round(score, 3),
    }


def _reset_fingerprints():
    """Test-only."""
    with _fingerprint_lock:
        _content_hashes.clear()


# ══════════════════════════════════════════════════
#  XSS PAYLOAD DETECTION
# ══════════════════════════════════════════════════

_XSS_PATTERNS = [
    re.compile(r'<script[\s>]', re.IGNORECASE),
    re.compile(r'javascript\s*:', re.IGNORECASE),
    re.compile(r'on(load|error|click|mouseover|focus|blur|submit)\s*=', re.IGNORECASE),
    re.compile(r'<iframe[\s>]', re.IGNORECASE),
    re.compile(r'<object[\s>]', re.IGNORECASE),
    re.compile(r'<embed[\s>]', re.IGNORECASE),
    re.compile(r'<svg[\s>].*?on\w+\s*=', re.IGNORECASE | re.DOTALL),
    re.compile(r'expression\s*\(', re.IGNORECASE),
    re.compile(r'url\s*\(\s*["\']?\s*javascript:', re.IGNORECASE),
    re.compile(r'data\s*:\s*text/html', re.IGNORECASE),
]


def check_xss_patterns(content: str) -> dict:
    """Detect XSS payload patterns in user-submitted content.

    Returns {has_xss: bool, score: float, reasons: list[str]}
    """
    if not content:
        return {"has_xss": False, "score": 0.0, "reasons": []}
    reasons = []
    for pattern in _XSS_PATTERNS:
        match = pattern.search(content)
        if match:
            reasons.append(f"xss:{match.group()[:30]}")
    if reasons:
        return {"has_xss": True, "score": 0.9, "reasons": reasons}
    return {"has_xss": False, "score": 0.0, "reasons": []}


# ══════════════════════════════════════════════════
#  UNICODE HOMOGLYPH DETECTION
# ══════════════════════════════════════════════════

# Map of commonly abused homoglyphs (Cyrillic/Greek that look like Latin)
_HOMOGLYPH_MAP = {
    'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E',
    'Н': 'H', 'К': 'K', 'М': 'M', 'О': 'O',
    'Р': 'P', 'Т': 'T', 'Х': 'X',
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',
    'с': 'c', 'у': 'y', 'х': 'x',
    'α': 'a', 'ο': 'o', 'ρ': 'p',  # Greek
    'і': 'i', 'ј': 'j',  # Ukrainian
    '‧': '.', '．': '.',  # fullwidth dot
}


def check_homoglyphs(content: str) -> dict:
    """Detect Unicode homoglyph abuse (used to bypass keyword filters).

    Returns {has_homoglyphs: bool, score: float, count: int}
    """
    if not content:
        return {"has_homoglyphs": False, "score": 0.0, "count": 0}
    count = sum(1 for c in content if c in _HOMOGLYPH_MAP)
    if count >= 3:
        return {
            "has_homoglyphs": True,
            "score": min(0.6, count * 0.1),
            "count": count,
        }
    return {"has_homoglyphs": False, "score": 0.0, "count": count}


def normalize_homoglyphs(content: str) -> str:
    """Replace known homoglyphs with their ASCII equivalents."""
    return ''.join(_HOMOGLYPH_MAP.get(c, c) for c in content)


# ══════════════════════════════════════════════════
#  ADDITIONAL VIETNAMESE SPAM PATTERNS
# ══════════════════════════════════════════════════

_SPAM_PATTERNS_V2 = [
    # MLM / pyramid scheme
    re.compile(
        r'\b(h[eệ]\s*th[oố]ng\s*ki[eế]m\s*ti[eề]n|'
        r'tuy[eể]n\s*[dđ][aạ]i\s*l[iyý]|'
        r'hoa\s*h[oồ]ng\s*\d+%|'
        r'c[oơ]\s*h[oộ]i\s*vi[eệ]c\s*l[aà]m\s*online)',
        re.IGNORECASE,
    ),
    # Loan shark / illegal lending
    re.compile(
        r'\b(vay\s*ti[eề]n\s*nhanh|'
        r'cho\s*vay\s*kh[oô]ng\s*c[aầ]n\s*th[eế]\s*ch[aấ]p|'
        r'gi[aả]i\s*ng[aâ]n\s*trong\s*\d+\s*ph[uú]t|'
        r'vay\s*online\s*uy\s*t[ií]n)',
        re.IGNORECASE,
    ),
    # Fake medicine / health scams
    re.compile(
        r'\b(thu[oố]c\s*gi[aả]m\s*c[aâ]n\s*nhanh|'
        r'ch[uữ]a\s*b[eệ]nh\s*\w+\s*trong\s*\d+\s*ng[aà]y|'
        r't[aă]ng\s*k[ií]ch\s*th[uư][oớ]c)',
        re.IGNORECASE,
    ),
    # Phishing / account steal
    re.compile(
        r'\b(x[aá]c\s*nh[aậ]n\s*t[aà]i\s*kho[aả]n|'
        r'c[aậ]p\s*nh[aậ]t\s*th[oô]ng\s*tin|'
        r'[dđ][aă]ng\s*nh[aậ]p\s*[dđ][eể]\s*nh[aậ]n)',
        re.IGNORECASE,
    ),
]


_SPAM_PATTERNS_SOUTHERN = [
    # Southern Vietnamese dialect spam variants (miền Tây)
    # "dzô" = "vô", "dui" = "vui", "dìa" = "về"
    re.compile(
        r'\b(ki[eế]m\s*l[ờợ]i\s*kh[uủ]ng|'
        r'nh[aậ]n\s*ti[eề]n\s*li[eề]n|'
        r'dzô\s*(link|web|trang)|'
        r'b[aấ]m\s*dzô\s*[dđ][aâ]y)',
        re.IGNORECASE,
    ),
    # Southern gambling slang: "đá gà", "lô đề", "bầu cua"
    re.compile(
        r'\b([dđ][aá]\s*g[aà]\s*online|'
        r'l[oô]\s*[dđ][eề]\s*online|'
        r'b[aầ]u\s*cua\s*online|'
        r'c[aá]\s*[dđ][oộ]\s*b[oó]ng)',
        re.IGNORECASE,
    ),
    # Southern slang for scam hooks: "dễ ợt", "ngon lành"
    re.compile(
        r'\b(ki[eế]m\s*ti[eề]n\s*d[eễ]\s*[oợ]t|'
        r'l[aà]m\s*gi[aà]u\s*d[eễ]\s*[oợ]t|'
        r'thu\s*nh[aậ]p\s*kh[uủ]ng\s*m[oỗ]i\s*ng[aà]y)',
        re.IGNORECASE,
    ),
]


def _check_spam_patterns_v2(content: str) -> dict:
    """Extended spam patterns: MLM, loan sharks, fake medicine, phishing, Southern dialect."""
    if not content or not content.strip():
        return {"score": 0.0, "reasons": []}

    # Normalize homoglyphs before checking
    text = normalize_homoglyphs(content)
    reasons = []
    score = 0.0
    for pattern in _SPAM_PATTERNS_V2 + _SPAM_PATTERNS_SOUTHERN:
        match = pattern.search(text)
        if match:
            score = max(score, 0.6)
            reasons.append(f"spam_v2:pattern_match({match.group()[:30]})")
    return {"score": score, "reasons": reasons}


# ══════════════════════════════════════════════════
#  GRADUATED RESPONSE SYSTEM
# ══════════════════════════════════════════════════

_user_moderation_history: dict[str, list[tuple[float, str]]] = {}
_mod_history_lock = _Lock()
_MOD_HISTORY_WINDOW = 86400 * 7  # 7 days


def get_user_trust_level(user_id: str) -> str:
    """Calculate user trust level based on moderation history.

    Returns: "trusted" | "normal" | "probation" | "restricted"
    """
    if not user_id:
        return "normal"
    now = _time.time()
    with _mod_history_lock:
        history = _user_moderation_history.get(user_id, [])
        recent = [(ts, action) for ts, action in history if now - ts < _MOD_HISTORY_WINDOW]
        _user_moderation_history[user_id] = recent

    flags = sum(1 for _, a in recent if a in ("flagged", "rejected"))
    approvals = sum(1 for _, a in recent if a == "approved")

    if flags >= 3:
        return "restricted"
    if flags >= 1:
        return "probation"
    if approvals >= 10:
        return "trusted"
    return "normal"


def record_moderation_outcome(user_id: str, action: str):
    """Record a moderation outcome for trust level tracking."""
    if not user_id:
        return
    now = _time.time()
    with _mod_history_lock:
        if user_id not in _user_moderation_history:
            _user_moderation_history[user_id] = []
        _user_moderation_history[user_id].append((now, action))
        if len(_user_moderation_history) > 50_000:
            cutoff = now - _MOD_HISTORY_WINDOW
            dead = [k for k, v in _user_moderation_history.items()
                    if not v or v[-1][0] < cutoff]
            for k in dead:
                del _user_moderation_history[k]


def adjust_thresholds_for_trust(trust_level: str) -> tuple[float, float]:
    """Return (auto_approve, queue) thresholds adjusted for trust level.

    Trusted users get looser thresholds; restricted users get stricter.
    """
    if trust_level == "trusted":
        return (0.4, 0.8)
    if trust_level == "probation":
        return (0.15, 0.5)
    if trust_level == "restricted":
        return (0.0, 0.3)  # nothing auto-approved, almost everything queued
    return (AUTO_APPROVE_THRESHOLD, QUEUE_THRESHOLD)  # normal


def _reset_moderation_history():
    """Test-only."""
    with _mod_history_lock:
        _user_moderation_history.clear()


# ══════════════════════════════════════════════════
#  DEEP URL ANALYSIS (phishing / malicious domain detection)
# ══════════════════════════════════════════════════

_PHISHING_TLD = frozenset({
    ".tk", ".ml", ".ga", ".cf", ".gq",  # free TLDs abused for phishing
    ".xyz", ".top", ".work", ".click", ".loan", ".date", ".racing",
    ".download", ".stream", ".bid", ".win",
})

_PHISHING_DOMAIN_PATTERNS = [
    re.compile(r'(paypal|facebook|google|apple|microsoft|amazon|netflix|bank)'
               r'[\-\.]?(login|verify|secure|account|update|confirm)', re.IGNORECASE),
    re.compile(r'\d{4,}\.', re.IGNORECASE),  # IP-like numbers in domain
    re.compile(r'[a-z0-9]{20,}\.', re.IGNORECASE),  # very long random subdomain
    re.compile(r'(secure|login|verify|account|update)\-', re.IGNORECASE),  # suspicious prefixes
]

_BRAND_IMPERSONATION = [
    re.compile(r'(fac[e3]b[o0]{2}k|g[o0]{2}gle|app[l1]e)', re.IGNORECASE),
]

_LEGITIMATE_HOSTS = frozenset({
    "vinhlong360.com", "www.vinhlong360.com", "api.vinhlong360.com",
})


def analyze_url_deep(url: str) -> dict:
    """Deep phishing/malicious URL analysis.

    Returns {risk_score: float, reasons: list[str], risk_level: str}
    """
    if not url:
        return {"risk_score": 0.0, "reasons": [], "risk_level": "safe"}

    import urllib.parse as _urlparse
    reasons = []
    score = 0.0

    try:
        parsed = _urlparse.urlparse(url if '://' in url else f"http://{url}")
        hostname = (parsed.hostname or "").lower()
        path = parsed.path or ""
    except (ValueError, AttributeError):
        return {"risk_score": 0.8, "reasons": ["unparseable_url"], "risk_level": "high"}

    # Skip analysis for legitimate domains
    if hostname in _LEGITIMATE_HOSTS:
        return {"risk_score": 0.0, "reasons": [], "risk_level": "safe"}

    # Check suspicious TLDs
    for tld in _PHISHING_TLD:
        if hostname.endswith(tld):
            score = max(score, 0.5)
            reasons.append(f"suspicious_tld:{tld}")
            break

    # Phishing domain patterns
    for pat in _PHISHING_DOMAIN_PATTERNS:
        if pat.search(hostname):
            score = max(score, 0.7)
            reasons.append("phishing_domain_pattern")
            break

    # Brand impersonation in URL
    full = hostname + path
    for pat in _BRAND_IMPERSONATION:
        if pat.search(full):
            score = max(score, 0.6)
            reasons.append("brand_impersonation")
            break

    # Excessive subdomains (more than 3 levels = suspicious)
    parts = hostname.split(".")
    if len(parts) > 4:
        score = max(score, 0.4)
        reasons.append("excessive_subdomains")

    # IP address as hostname
    try:
        import ipaddress as _ipa
        _ipa.ip_address(hostname)
        score = max(score, 0.5)
        reasons.append("ip_as_hostname")
    except (ValueError, TypeError):
        pass

    # @ symbol in URL (credential phishing: http://legit.com@evil.com)
    if "@" in url:
        score = max(score, 0.7)
        reasons.append("credential_in_url")

    # Homograph attack (non-ASCII in domain)
    if any(ord(c) > 127 for c in hostname):
        score = max(score, 0.6)
        reasons.append("idn_homograph")

    risk_level = "safe"
    if score >= 0.7:
        risk_level = "high"
    elif score >= 0.4:
        risk_level = "medium"
    elif score > 0:
        risk_level = "low"

    return {"risk_score": round(score, 3), "reasons": reasons, "risk_level": risk_level}


# ══════════════════════════════════════════════════
#  CONTENT ENTROPY ANALYSIS
# ══════════════════════════════════════════════════

import math as _math


def check_content_entropy(content: str) -> dict:
    """Analyze content entropy to detect encoded/obfuscated payloads.

    Normal Vietnamese text: entropy ~4.5-5.5 bits/char
    Base64 encoded: entropy ~5.5-6.0
    Random binary (hex/base64): entropy > 6.0
    Returns {entropy: float, is_suspicious: bool, encoding_likely: str}
    """
    if not content or len(content) < 20:
        return {"entropy": 0.0, "is_suspicious": False, "encoding_likely": "none"}

    freq: dict[str, int] = {}
    for c in content:
        freq[c] = freq.get(c, 0) + 1
    length = len(content)
    entropy = -sum(
        (count / length) * _math.log2(count / length)
        for count in freq.values()
    )

    encoding = "none"
    if entropy > 5.9:
        # Check if it looks like base64
        import re as _re
        b64_chars = sum(1 for c in content if c in
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        if b64_chars / length > 0.9:
            encoding = "base64"
        # Check if it looks like hex
        hex_chars = sum(1 for c in content if c in '0123456789abcdefABCDEF')
        if hex_chars / length > 0.9:
            encoding = "hex"

    return {
        "entropy": round(entropy, 3),
        "is_suspicious": entropy > 5.5 and len(content) > 50,
        "encoding_likely": encoding,
    }


# ══════════════════════════════════════════════════
#  COORDINATED INAUTHENTIC BEHAVIOR DETECTION
# ══════════════════════════════════════════════════

_coord_behavior: dict[str, list[tuple[float, str, str]]] = {}
_coord_lock = _Lock()
_COORD_BEHAVIOR_WINDOW = 300  # 5 minutes
_COORD_BEHAVIOR_THRESHOLD = 3  # 3+ users posting identical content = coordinated


def detect_coordinated_behavior(content: str, user_id: str, ip: str = "") -> dict:
    """Detect coordinated inauthentic behavior (sockpuppet/bot networks).

    Flags when multiple "different" users post identical content within a short window,
    especially from similar IPs.
    Returns {is_coordinated: bool, unique_users: int, unique_ips: int, score: float}
    """
    if not content or len(content) < 20 or not user_id:
        return {"is_coordinated": False, "unique_users": 0, "unique_ips": 0, "score": 0.0}

    import hashlib as _hl
    normalized = re.sub(r'\s+', ' ', content.lower().strip())
    fp = _hl.sha256(normalized.encode()).hexdigest()[:16]
    now = _time.time()

    with _coord_lock:
        if fp not in _coord_behavior:
            _coord_behavior[fp] = []
        entries = _coord_behavior[fp]
        entries = [(t, u, i) for t, u, i in entries if now - t < _COORD_BEHAVIOR_WINDOW]
        entries.append((now, user_id, ip))
        _coord_behavior[fp] = entries

        unique_users = len({u for _, u, _ in entries})
        unique_ips = len({i for _, _, i in entries if i})

        # GC
        if len(_coord_behavior) > 50_000:
            cutoff = now - _COORD_BEHAVIOR_WINDOW
            dead = [k for k, v in _coord_behavior.items()
                    if not v or v[-1][0] < cutoff]
            for k in dead:
                del _coord_behavior[k]

    is_coord = unique_users >= _COORD_BEHAVIOR_THRESHOLD
    # Higher score if posts come from SAME IP (sockpuppets)
    same_ip_bonus = 0.3 if unique_users > 1 and unique_ips == 1 else 0.0
    score = min(1.0, (unique_users / _COORD_BEHAVIOR_THRESHOLD) * 0.6 + same_ip_bonus) if unique_users > 1 else 0.0

    return {
        "is_coordinated": is_coord,
        "unique_users": unique_users,
        "unique_ips": unique_ips,
        "score": round(score, 3),
    }


def _reset_coordinated_behavior():
    """Test-only."""
    with _coord_lock:
        _coord_behavior.clear()


# ══════════════════════════════════════════════════
#  IMAGE / FILE CONTENT ANALYSIS
# ══════════════════════════════════════════════════

_IMAGE_SAFE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"})
_EXIF_STRIP_TAGS = frozenset({"GPSInfo", "GPSLatitude", "GPSLongitude"})


def sanitize_image_filename(filename: str) -> str:
    """Sanitize an uploaded image filename for safe storage."""
    if not filename:
        return "upload.jpg"
    # Strip path components
    name = filename.replace("\\", "/").split("/")[-1]
    # Remove null bytes
    name = name.replace("\x00", "")
    # Only allow safe characters
    name = re.sub(r'[^\w\-.]', '_', name)
    name = name.lstrip(".")
    if not name:
        return "upload.jpg"
    # Verify extension
    ext = ""
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
    if ext not in _IMAGE_SAFE_EXTENSIONS:
        name = name.rsplit(".", 1)[0] + ".jpg"
    if len(name) > 200:
        base = name[:190]
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ".jpg"
        name = base + ext
    return name


def check_image_content_safe(file_header: bytes) -> dict:
    """Check image file header for embedded scripts/exploits.

    Some attack vectors embed PHP/JS inside image EXIF data or after the image end marker.
    Returns {safe: bool, reasons: list[str]}
    """
    if not file_header:
        return {"safe": True, "reasons": []}
    reasons = []
    # Check for embedded scripts in binary content
    header_str = file_header[:4096].decode("latin-1", errors="replace").lower()
    if "<?php" in header_str:
        reasons.append("embedded_php")
    if "<script" in header_str:
        reasons.append("embedded_script")
    if "<%@" in header_str or "<%=" in header_str:
        reasons.append("embedded_jsp")
    # Polyglot: valid image header but also valid HTML/JS
    if header_str.startswith("gif89a") and "<script" in header_str:
        reasons.append("polyglot_gif_script")
    return {"safe": not reasons, "reasons": reasons}


# ══════════════════════════════════════════════════
#  ENHANCED MODERATION PIPELINE (unified)
# ══════════════════════════════════════════════════

# ══════════════════════════════════════════════════
#  TEXT OBFUSCATION DETECTION
# ══════════════════════════════════════════════════

_LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '7': 't', '8': 'b', '@': 'a', '!': 'i', '$': 's',
}

_ZERO_WIDTH_CHARS = frozenset({
    '​',  # zero-width space
    '‌',  # zero-width non-joiner
    '‍',  # zero-width joiner
    '‎',  # left-to-right mark
    '‏',  # right-to-left mark
    '⁠',  # word joiner
    '﻿',  # zero-width no-break space (BOM)
})


def detect_text_obfuscation(content: str) -> dict:
    """Detect text obfuscation techniques used to bypass filters.

    Checks: l33tspeak, zero-width chars, excessive spacing, Unicode tricks.
    Returns {is_obfuscated: bool, techniques: list[str], score: float}
    """
    if not content or len(content) < 5:
        return {"is_obfuscated": False, "techniques": [], "score": 0.0}

    techniques = []
    score = 0.0

    # Zero-width characters
    zw_count = sum(1 for c in content if c in _ZERO_WIDTH_CHARS)
    if zw_count >= 2:
        techniques.append("zero_width_chars")
        score = max(score, 0.6)

    # Excessive spacing between letters (c a s i n o)
    if re.search(r'[a-zA-Z]\s[a-zA-Z]\s[a-zA-Z]\s[a-zA-Z]', content):
        techniques.append("letter_spacing")
        score = max(score, 0.4)

    # L33tspeak density
    leet_count = sum(1 for c in content if c in _LEET_MAP)
    alpha_count = sum(1 for c in content if c.isalpha())
    if alpha_count > 0 and leet_count / max(1, alpha_count + leet_count) > 0.3:
        techniques.append("leetspeak")
        score = max(score, 0.4)

    # Mixed script (Cyrillic + Latin in same word)
    words = content.split()
    for word in words:
        has_latin = any('A' <= c <= 'z' for c in word)
        has_cyrillic = any('Ѐ' <= c <= 'ӿ' for c in word)
        if has_latin and has_cyrillic and len(word) > 3:
            techniques.append("mixed_script")
            score = max(score, 0.6)
            break

    # Fullwidth characters (ｈｅｌｌｏ)
    fullwidth_count = sum(1 for c in content if '！' <= c <= '～')
    if fullwidth_count >= 3:
        techniques.append("fullwidth_chars")
        score = max(score, 0.5)

    return {
        "is_obfuscated": bool(techniques),
        "techniques": techniques,
        "score": round(score, 3),
    }


def deobfuscate_text(content: str) -> str:
    """Attempt to deobfuscate text for content analysis.

    Strips zero-width chars, converts l33tspeak, collapses spacing.
    """
    if not content:
        return ""
    # Remove zero-width characters
    result = ''.join(c for c in content if c not in _ZERO_WIDTH_CHARS)
    # Collapse letter spacing (c a s i n o → casino)
    result = re.sub(r'([a-zA-Z])\s(?=[a-zA-Z]\s[a-zA-Z])', r'\1', result)
    # Convert l33tspeak
    result = ''.join(_LEET_MAP.get(c, c) for c in result)
    # Normalize fullwidth to ASCII
    normalized = []
    for c in result:
        code = ord(c)
        if 0xff01 <= code <= 0xff5e:
            normalized.append(chr(code - 0xfee0))
        else:
            normalized.append(c)
    return ''.join(normalized)


# ══════════════════════════════════════════════════
#  TARGETED HARASSMENT DETECTION
# ══════════════════════════════════════════════════

_harassment_tracking: dict[str, list[tuple[float, str, str]]] = {}
_harassment_lock = _Lock()
_HARASSMENT_WINDOW = 86400  # 24 hours
_HARASSMENT_THRESHOLD = 5   # 5+ negative interactions targeting same user


def check_targeted_harassment(
    author_id: str, target_id: str, content: str = ""
) -> dict:
    """Detect repeated negative interactions from one user toward another.

    Returns {is_harassment: bool, interaction_count: int, score: float}
    """
    if not author_id or not target_id or author_id == target_id:
        return {"is_harassment": False, "interaction_count": 0, "score": 0.0}

    pair_key = f"{author_id}→{target_id}"
    now = _time.time()

    with _harassment_lock:
        if pair_key not in _harassment_tracking:
            _harassment_tracking[pair_key] = []
        entries = _harassment_tracking[pair_key]
        entries = [(t, a, c) for t, a, c in entries if now - t < _HARASSMENT_WINDOW]
        entries.append((now, author_id, content[:100] if content else ""))
        _harassment_tracking[pair_key] = entries

        count = len(entries)

        # GC
        if len(_harassment_tracking) > 100_000:
            cutoff = now - _HARASSMENT_WINDOW
            dead = [k for k, v in _harassment_tracking.items()
                    if not v or v[-1][0] < cutoff]
            for k in dead:
                del _harassment_tracking[k]

    is_harassment = count >= _HARASSMENT_THRESHOLD
    score = min(1.0, count / _HARASSMENT_THRESHOLD) * 0.8 if count > 1 else 0.0

    return {
        "is_harassment": is_harassment,
        "interaction_count": count,
        "score": round(score, 3),
    }


def _reset_harassment_tracking():
    """Test-only."""
    with _harassment_lock:
        _harassment_tracking.clear()


# ══════════════════════════════════════════════════
#  CONTENT POLICY ENGINE (configurable rules)
# ══════════════════════════════════════════════════

_content_policies: list[dict] = []
_policy_lock = _Lock()


def add_content_policy(
    name: str, pattern: str, action: str = "flag",
    score: float = 0.7, case_sensitive: bool = False,
):
    """Add a configurable content policy rule.

    action: "flag", "block", "warn"
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = re.compile(pattern, flags)
    with _policy_lock:
        _content_policies.append({
            "name": name,
            "pattern": compiled,
            "raw_pattern": pattern,
            "action": action,
            "score": score,
        })


def remove_content_policy(name: str) -> bool:
    """Remove a content policy by name."""
    with _policy_lock:
        before = len(_content_policies)
        _content_policies[:] = [p for p in _content_policies if p["name"] != name]
        return len(_content_policies) < before


def check_content_policies(content: str) -> dict:
    """Run content through all configured policy rules.

    Returns {violated: bool, violations: list[dict], max_score: float, action: str}
    """
    if not content:
        return {"violated": False, "violations": [], "max_score": 0.0, "action": "none"}

    violations = []
    max_score = 0.0
    worst_action = "none"
    action_priority = {"none": 0, "warn": 1, "flag": 2, "block": 3}

    with _policy_lock:
        for policy in _content_policies:
            if policy["pattern"].search(content):
                violations.append({
                    "policy": policy["name"],
                    "action": policy["action"],
                    "score": policy["score"],
                })
                max_score = max(max_score, policy["score"])
                if action_priority.get(policy["action"], 0) > action_priority.get(worst_action, 0):
                    worst_action = policy["action"]

    return {
        "violated": bool(violations),
        "violations": violations,
        "max_score": round(max_score, 3),
        "action": worst_action,
    }


def list_content_policies() -> list[dict]:
    """List all configured content policies."""
    with _policy_lock:
        return [{"name": p["name"], "pattern": p["raw_pattern"],
                 "action": p["action"], "score": p["score"]}
                for p in _content_policies]


def _reset_content_policies():
    """Test-only."""
    with _policy_lock:
        _content_policies.clear()


# ══════════════════════════════════════════════════
#  RESPONSE BODY SCANNING (data leakage prevention)
# ══════════════════════════════════════════════════

_RESPONSE_LEAK_PATTERNS = [
    re.compile(r'password["\s]*[:=]\s*["\'][^"\']{3,}', re.IGNORECASE),
    re.compile(r'(secret|token|api_?key)["\s]*[:=]\s*["\'][^"\']{8,}', re.IGNORECASE),
    re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
    re.compile(r'(postgresql|mysql|mongodb|redis)://\S+:\S+@\S+', re.IGNORECASE),
    re.compile(r'AKIA[A-Z0-9]{16}'),  # AWS access key
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),  # OpenAI key
    re.compile(r'xox[bpras]-[a-zA-Z0-9\-]+'),  # Slack token
]


def scan_response_body(body: str) -> dict:
    """Scan outgoing response body for accidental data leakage.

    Returns {has_leak: bool, leak_types: list[str], count: int}
    """
    if not body:
        return {"has_leak": False, "leak_types": [], "count": 0}

    leak_types = []
    total = 0
    labels = [
        "password_leak", "secret_leak", "private_key_leak",
        "connection_string_leak", "aws_key_leak", "openai_key_leak",
        "slack_token_leak",
    ]

    for pattern, label in zip(_RESPONSE_LEAK_PATTERNS, labels):
        matches = pattern.findall(body)
        if matches:
            leak_types.append(label)
            total += len(matches)

    return {"has_leak": bool(leak_types), "leak_types": leak_types, "count": total}


def redact_response_leaks(body: str) -> str:
    """Redact detected leaks from response body."""
    if not body:
        return ""
    result = body
    for pattern in _RESPONSE_LEAK_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


# ══════════════════════════════════════════════════
#  CONTENT DIFF ATTACK DETECTION
# ══════════════════════════════════════════════════

_content_versions: dict[str, list[tuple[float, str]]] = {}
_content_version_lock = _Lock()
_DIFF_WINDOW = 3600  # 1 hour
_DIFF_THRESHOLD = 5   # 5+ rapid edits = suspicious


def check_edit_abuse(
    content_id: str, new_content: str, user_id: str = ""
) -> dict:
    """Detect edit-based abuse: rapid content changes to evade moderation.

    Pattern: post clean content → moderation approves → rapidly edit to harmful.
    Returns {is_abuse: bool, edit_count: int, velocity: float}
    """
    if not content_id or not new_content:
        return {"is_abuse": False, "edit_count": 0, "velocity": 0.0}

    now = _time.time()
    import hashlib as _hl
    content_hash = _hl.sha256(new_content.encode()).hexdigest()[:16]

    with _content_version_lock:
        if content_id not in _content_versions:
            _content_versions[content_id] = []
        versions = _content_versions[content_id]
        versions = [(t, h) for t, h in versions if now - t < _DIFF_WINDOW]

        # Check if this is actually a different version
        if versions and versions[-1][1] == content_hash:
            return {"is_abuse": False, "edit_count": len(versions), "velocity": 0.0}

        versions.append((now, content_hash))
        _content_versions[content_id] = versions

        edit_count = len(versions)

        # GC
        if len(_content_versions) > 50_000:
            cutoff = now - _DIFF_WINDOW
            dead = [k for k, v in _content_versions.items()
                    if not v or v[-1][0] < cutoff]
            for k in dead:
                del _content_versions[k]

    # Calculate edit velocity (edits per minute)
    if edit_count >= 2:
        span = versions[-1][0] - versions[0][0]
        velocity = (edit_count / (span / 60)) if span > 0 else float(edit_count)
    else:
        velocity = 0.0

    return {
        "is_abuse": edit_count >= _DIFF_THRESHOLD,
        "edit_count": edit_count,
        "velocity": round(velocity, 2),
    }


def _reset_content_versions():
    """Test-only."""
    with _content_version_lock:
        _content_versions.clear()


# ══════════════════════════════════════════════════
#  MULTI-LANGUAGE ANOMALY DETECTION
# ══════════════════════════════════════════════════

_SCRIPT_RANGES = [
    ("cyrillic", 0x0400, 0x04FF),
    ("arabic", 0x0600, 0x06FF),
    ("devanagari", 0x0900, 0x097F),
    ("thai", 0x0E00, 0x0E7F),
    ("cjk", 0x4E00, 0x9FFF),
    ("vietnamese", 0x1EA0, 0x1EF9),
    ("latin", 0x0041, 0x024F),
]

_EXPECTED_SCRIPTS = frozenset({"latin", "vietnamese"})


def detect_language_anomaly(content: str) -> dict:
    """Detect unexpected script usage in content.

    Vietnamese text should primarily contain Latin + Vietnamese diacritics.
    Unexpected scripts (Cyrillic, Arabic, CJK) in user content may indicate
    spam, phishing, or obfuscation.
    Returns {is_anomalous: bool, detected_scripts: list[str], unexpected: list[str]}
    """
    if not content or len(content) < 10:
        return {"is_anomalous": False, "detected_scripts": [], "unexpected": []}

    script_counts: dict[str, int] = {}
    for c in content:
        code = ord(c)
        for script, start, end in _SCRIPT_RANGES:
            if start <= code <= end:
                script_counts[script] = script_counts.get(script, 0) + 1
                break

    detected = [s for s, count in script_counts.items() if count >= 3]
    unexpected = [s for s in detected if s not in _EXPECTED_SCRIPTS]

    return {
        "is_anomalous": bool(unexpected),
        "detected_scripts": detected,
        "unexpected": unexpected,
    }


async def moderate_content_enhanced(
    content: str, user_id: str = "", ip: str = "",
    image_urls: list[str] = None,
) -> dict:
    """Enhanced moderation pipeline with all deep layers integrated.

    Runs: base moderation + XSS + homoglyphs + spam_v2 + duplicate +
          coordinated behavior + URL analysis + content entropy.
    Returns same shape as moderate_content() but with additional detail.
    """
    base_result = await moderate_content(content, image_urls)

    extra_reasons = []
    extra_score = 0.0

    # XSS check
    xss = check_xss_patterns(content)
    if xss["has_xss"]:
        extra_score = max(extra_score, xss["score"])
        extra_reasons.extend(xss["reasons"])

    # Homoglyph check
    homo = check_homoglyphs(content)
    if homo["has_homoglyphs"]:
        extra_score = max(extra_score, homo["score"])
        extra_reasons.append(f"homoglyphs:{homo['count']}")

    # Extended spam patterns
    spam_v2 = _check_spam_patterns_v2(content)
    if spam_v2["score"] > 0:
        extra_score = max(extra_score, spam_v2["score"])
        extra_reasons.extend(spam_v2["reasons"])

    # Duplicate detection
    if content and len(content) >= 20:
        dup = check_content_duplicate(content, user_id)
        if dup["is_duplicate"]:
            extra_score = max(extra_score, 0.7)
            extra_reasons.append(f"duplicate:count={dup['count']}")

    # Coordinated behavior
    if user_id:
        coord = detect_coordinated_behavior(content, user_id, ip)
        if coord["is_coordinated"]:
            extra_score = max(extra_score, coord["score"])
            extra_reasons.append(f"coordinated:users={coord['unique_users']}")

    # URL deep analysis
    urls = _URL_PATTERN.findall(content or "")
    for url in urls[:5]:
        url_result = analyze_url_deep(url)
        if url_result["risk_level"] in ("high", "medium"):
            extra_score = max(extra_score, url_result["risk_score"])
            extra_reasons.extend(url_result["reasons"])

    # Content entropy
    ent = check_content_entropy(content)
    if ent["is_suspicious"]:
        extra_score = max(extra_score, 0.4)
        extra_reasons.append(f"high_entropy:{ent['encoding_likely']}")

    # Text obfuscation (zero-width, leetspeak, fullwidth, visual tricks)
    obf = detect_text_obfuscation(content)
    if obf.get("is_obfuscated"):
        extra_score = max(extra_score, obf["score"])
        for tech in obf.get("techniques", []):
            extra_reasons.append(f"obfuscation:{tech}")

    # Transactional CTA check (intro-only policy)
    cta = check_transactional_cta(content)
    if cta["has_cta"]:
        extra_score = max(extra_score, 0.6)
        extra_reasons.append(f"transactional_cta:{','.join(cta['matches'][:3])}")

    # Merge scores
    final_score = max(base_result["score"], extra_score)
    all_reasons = base_result["reasons"] + extra_reasons

    # Re-evaluate status with trust level
    trust = get_user_trust_level(user_id)
    approve_thresh, queue_thresh = adjust_thresholds_for_trust(trust)

    if final_score < approve_thresh:
        status = "approved"
    elif final_score < queue_thresh:
        status = "pending"
    else:
        status = "flagged"

    return {
        **base_result,
        "status": status,
        "score": round(final_score, 3),
        "reasons": all_reasons,
        "trust_level": trust,
        "deep_layers": {
            "xss": xss["has_xss"],
            "homoglyphs": homo["has_homoglyphs"],
            "spam_v2": spam_v2["score"] > 0,
            "coordinated": user_id and detect_coordinated_behavior(content, user_id, ip).get("is_coordinated", False),
            "high_entropy": ent["is_suspicious"],
        },
    }


_TRANSACTIONAL_CTA = re.compile(
    r"\b(đặt\s*(ngay|tour|phòng|vé|hàng)|mua\s*ngay|thanh\s*toán|giỏ\s*hàng"
    r"|checkout|add\s*to\s*cart|book\s*now|buy\s*now|đặt\s*cọc|chuyển\s*khoản"
    r"|pay\s*now|order\s*now)\b",
    re.IGNORECASE,
)


def check_transactional_cta(text: str) -> dict:
    """Detect transactional CTA wording that violates the intro-only policy."""
    if not text:
        return {"has_cta": False, "matches": []}
    matches = _TRANSACTIONAL_CTA.findall(text)
    return {"has_cta": bool(matches), "matches": [m[0] if isinstance(m, tuple) else m for m in matches]}


log_moderation_orig = None  # forward ref


def log_moderation(target_type: str, target_id: str, action: str,
                    scores: dict, reason: str = None, moderator_id: str = None,
                    auto: bool = True):
    """Log moderation action to database."""
    ph = db._ph
    with db._conn() as conn:
        db._execute(conn, f"""
            INSERT INTO moderation_log (target_type, target_id, action, reason, moderator_id, auto, scores)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}::uuid, {ph}, {ph}::jsonb)
        """, (
            target_type, target_id, action, reason,
            moderator_id, auto, json.dumps(scores),
        ))
