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
