"""
vinhlong360 — Auto Moderation Pipeline.

3-step pipeline:
  1. OpenAI Moderation API (text) — miễn phí, tiếng Việt hiệu năng cao
  2. Google Vision SafeSearch (ảnh) — free 1.000 ảnh/tháng
  3. Auto-decision: score < 0.3 → approve, 0.3-0.7 → queue, > 0.7 → flag

Chỉ gửi nội dung bài (không kèm định danh user) sang API nước ngoài → giảm rủi ro PDPL.
"""

import json
import os
from datetime import datetime, timezone

import httpx

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

    max_score = max(text_result["score"], image_result["score"])
    reasons = text_result["reasons"] + image_result["reasons"]

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
        print(f"[MODERATION] Text moderation error: {e}")
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
        print(f"[MODERATION] Image moderation error: {e}")

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
