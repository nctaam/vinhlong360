"""
vinhlong360 — Image Upload Recognition module.

Nhận diện hình ảnh du lịch qua LLM Vision API:
  - Xác định nội dung ảnh (món ăn, danh lam, phong cảnh, ...)
  - Đối sánh với entities đã biết thuộc Vĩnh Long / Bến Tre / Trà Vinh
  - Mô tả bằng tiếng Việt

Fallback: nếu Vision API lỗi, dùng filename để đoán nội dung.

Thread-safe, chỉ dùng stdlib + openai.
"""

import base64
import json
import logging
import os
import re
import threading
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

from openai import OpenAI

# ── Config ──

_client_lock = threading.Lock()
_client: OpenAI | None = None

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

CATEGORIES = ("food", "landmark", "nature", "craft", "event", "person", "other")

# Map from image category to entity types in the knowledge base
_CATEGORY_TO_ENTITY_TYPES: dict[str, list[str]] = {
    "food": ["dish", "product"],
    "landmark": ["attraction", "history"],
    "nature": ["nature", "attraction"],
    "craft": ["craft_village", "product", "experience"],
    "event": ["event", "experience"],
    "person": ["person"],
    "other": [],
}


def _get_client() -> OpenAI:
    """Lazy-init OpenAI client (thread-safe)."""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            _client = OpenAI(
                api_key=os.environ.get("LLM_API_KEY", ""),
                base_url=os.environ["LLM_BASE_URL"],
                timeout=30,
            )
        return _client


def _get_model() -> str:
    return os.environ.get("LLM_MODEL", "cx/gpt-5.4")


# ══════════════════════════════════════════════════
#  Vietnamese text utilities
# ══════════════════════════════════════════════════

def _normalize_vn(text: str) -> str:
    """Bỏ dấu tiếng Việt để fuzzy match."""
    s = unicodedata.normalize("NFD", text.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = s.replace("đ", "d").replace("Đ", "D")
    return s


def _tokenize(text: str) -> set[str]:
    """Tách text thành set of normalized tokens."""
    raw = re.split(r"[\s,.\-_/\\;:!?()\"']+", text.lower())
    tokens = set()
    for w in raw:
        w = w.strip()
        if len(w) >= 2:
            tokens.add(w)
            tokens.add(_normalize_vn(w))
    return tokens


# ══════════════════════════════════════════════════
#  Build vision message
# ══════════════════════════════════════════════════

def build_vision_message(image_base64: str, user_text: str = "") -> list[dict]:
    """
    Build OpenAI-compatible message list with image content for vision API.

    Args:
        image_base64: Base64-encoded image data (without the data URI prefix).
        user_text: Optional additional text from the user.

    Returns:
        List with a single user message containing text + image_url content parts.
    """
    prompt_parts = [
        "Hãy nhận diện nội dung bức ảnh này. Đây là ảnh liên quan đến du lịch "
        "vùng Vĩnh Long, Bến Tre, hoặc Trà Vinh (miền Tây Nam Bộ, Việt Nam).",
        "",
        "Hãy trả lời dưới dạng JSON với các trường sau:",
        '  "description": mô tả chi tiết bằng tiếng Việt (2-3 câu)',
        '  "category": một trong ["food", "landmark", "nature", "craft", "event", "person", "other"]',
        '  "identified_items": danh sách tên các đối tượng nhận diện được (tiếng Việt)',
        '  "tags": danh sách từ khóa (tiếng Việt)',
        "",
        "Chỉ trả về JSON, không thêm giải thích.",
    ]
    if user_text:
        prompt_parts.append(f"\nNgười dùng ghi chú: {user_text}")

    text_content = "\n".join(prompt_parts)

    # Detect MIME type from base64 header if present, default to jpeg
    mime = "image/jpeg"
    if image_base64.startswith("/9j/"):
        mime = "image/jpeg"
    elif image_base64.startswith("iVBOR"):
        mime = "image/png"
    elif image_base64.startswith("R0lGOD"):
        mime = "image/gif"
    elif image_base64.startswith("UklGR"):
        mime = "image/webp"

    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text_content},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{image_base64}",
                    },
                },
            ],
        }
    ]


# ══════════════════════════════════════════════════
#  Entity matching
# ══════════════════════════════════════════════════

def match_to_entities(
    description: str,
    entities: dict,
    top_k: int = 5,
) -> list[dict]:
    """
    Given a text description from vision, find matching entities via
    keyword + fuzzy matching.

    Args:
        description: Text description of the image content (from vision API).
        entities: Dict mapping entity_id -> entity dict (from knowledge.py).
        top_k: Maximum number of matches to return.

    Returns:
        List of dicts: [{"entity_id": str, "name": str, "score": float, "reason": str}]
        Sorted by score descending.
    """
    if not description or not entities:
        return []

    desc_tokens = _tokenize(description)
    desc_norm = _normalize_vn(description)

    scored: list[tuple[float, str, str, str]] = []  # (score, id, name, reason)

    # Entity types that are matchable content (not places)
    content_types = {
        "attraction", "product", "dish", "craft_village", "nature",
        "event", "experience", "person", "history", "accommodation",
        "organization", "economy",
    }

    for eid, entity in entities.items():
        if entity.get("type") not in content_types:
            continue

        name = entity.get("name", "")
        summary = entity.get("summary", "")
        tags = entity.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        # Build searchable text for this entity
        entity_text = f"{name} {summary} {' '.join(tags)}"
        entity_tokens = _tokenize(entity_text)
        entity_norm = _normalize_vn(entity_text)
        name_norm = _normalize_vn(name)

        score = 0.0
        reasons = []

        # Exact name match in description (highest signal)
        if name.lower() in description.lower():
            score += 0.5
            reasons.append(f"tên '{name}' xuất hiện trong mô tả")
        elif name_norm in desc_norm:
            score += 0.4
            reasons.append(f"tên '{name}' khớp (không dấu)")

        # Token overlap
        overlap = desc_tokens & entity_tokens
        if overlap and entity_tokens:
            overlap_ratio = len(overlap) / max(len(entity_tokens), 1)
            token_score = min(overlap_ratio * 0.4, 0.3)
            if token_score > 0.05:
                score += token_score
                sample = ", ".join(list(overlap)[:3])
                reasons.append(f"từ khóa chung: {sample}")

        # Substring matching for multi-word entity names
        name_words = [w for w in name.lower().split() if len(w) >= 2]
        matched_words = sum(1 for w in name_words if w in description.lower())
        if name_words and matched_words >= 2:
            word_score = (matched_words / len(name_words)) * 0.2
            score += word_score
            reasons.append(f"{matched_words}/{len(name_words)} từ trong tên khớp")

        if score > 0.05:
            reason = "; ".join(reasons) if reasons else "khớp từ khóa"
            scored.append((score, eid, name, reason))

    # Sort by score descending, take top_k
    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "entity_id": eid,
            "name": name,
            "score": round(score, 3),
            "reason": reason,
        }
        for score, eid, name, reason in scored[:top_k]
    ]


# ══════════════════════════════════════════════════
#  Filename-based fallback
# ══════════════════════════════════════════════════

# Common Vietnamese filename patterns → search keywords
_FILENAME_PATTERNS: dict[str, str] = {
    "bun": "bún",
    "pho": "phở",
    "com": "cơm",
    "banh": "bánh",
    "hu-tieu": "hủ tiếu",
    "nuoc-leo": "nước lèo",
    "bun-nuoc-leo": "bún nước lèo",
    "nem": "nem",
    "goi-cuon": "gỏi cuốn",
    "ca": "cá",
    "tom": "tôm",
    "dua": "dừa",
    "keo-dua": "kẹo dừa",
    "cau": "cầu",
    "chua": "chùa",
    "cho": "chợ",
    "song": "sông",
    "vuon": "vườn",
    "nha-co": "nhà cổ",
    "lang-nghe": "làng nghề",
    "gom": "gốm",
    "det": "dệt",
    "chieu": "chiếu",
}


def _guess_from_filename(filename: str) -> str | None:
    """Đoán nội dung từ tên file. Trả về từ khóa tìm kiếm hoặc None."""
    if not filename:
        return None

    # Remove extension and normalize
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[_\s]+", "-", stem)

    # Try exact pattern matches (longest first)
    for pattern, keyword in sorted(
        _FILENAME_PATTERNS.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if pattern in stem:
            return keyword

    # Return cleaned stem as a fallback search term
    cleaned = stem.replace("-", " ").strip()
    return cleaned if len(cleaned) >= 2 else None


def _fallback_recognize(
    filename: str, entities: dict
) -> dict:
    """Fallback recognition khi Vision API không khả dụng."""
    guess = _guess_from_filename(filename)

    matched = []
    description = ""

    if guess and entities:
        # Search entities using the guessed keyword
        description = f"Dựa trên tên file '{filename}', có thể liên quan đến: {guess}"
        matched = match_to_entities(guess, entities, top_k=5)
    else:
        description = f"Không thể nhận diện nội dung từ tên file '{filename}'"

    return {
        "description": description,
        "identified_entities": [
            {"id": m["entity_id"], "name": m["name"], "confidence": m["score"]}
            for m in matched
        ],
        "category": "other",
        "tags": [guess] if guess else [],
        "fallback": True,
        "reason": "Vision API unavailable",
    }


# ══════════════════════════════════════════════════
#  Core: recognize_image
# ══════════════════════════════════════════════════

def recognize_image(
    image_data: str | bytes,
    entities: dict,
    filename: str = "",
) -> dict:
    """
    Nhận diện nội dung ảnh qua LLM Vision API, sau đó đối sánh
    với entities du lịch đã biết.

    Args:
        image_data: Base64 string hoặc raw bytes của ảnh.
        entities: Dict entity_id -> entity (từ knowledge.py).
        filename: Tên file gốc (dùng cho fallback).

    Returns:
        {
            "description": str,           # Mô tả tiếng Việt
            "identified_entities": [       # Entities khớp
                {"id": str, "name": str, "confidence": float}
            ],
            "category": str,              # food/landmark/nature/craft/event/person/other
            "tags": [str],                # Từ khóa
        }
        Nếu fallback: thêm "fallback": True, "reason": str
    """
    # Normalize image_data to base64 string
    if isinstance(image_data, bytes):
        image_b64 = base64.b64encode(image_data).decode("ascii")
    else:
        # Already base64; strip data URI prefix if present
        if "," in image_data and image_data.startswith("data:"):
            image_b64 = image_data.split(",", 1)[1]
        else:
            image_b64 = image_data

    # Try Vision API
    try:
        client = _get_client()
        model = _get_model()
        messages = build_vision_message(image_b64)

        logger.debug("Calling vision API model=%s", model)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
            timeout=30,  # P1-2: vision call có thể chậm — tránh treo worker
        )

        raw = response.choices[0].message.content.strip()
        logger.debug("Vision API response length=%d", len(raw))

        # Parse JSON from response (handle markdown code fences)
        json_text = raw
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
        if fence_match:
            json_text = fence_match.group(1).strip()

        vision_result = json.loads(json_text)

    except json.JSONDecodeError as exc:
        logger.warning("Vision API JSON parse error: %s, raw=%s", exc, raw[:200])
        # If we got text but not valid JSON, use the raw text as description
        vision_result = {
            "description": raw[:500] if raw else "Không thể phân tích kết quả",
            "category": "other",
            "identified_items": [],
            "tags": [],
        }
    except Exception as exc:
        logger.warning("Vision API error: %s", exc)
        return _fallback_recognize(filename, entities)

    # Normalize result fields
    description = vision_result.get("description", "")
    category = vision_result.get("category", "other")
    if category not in CATEGORIES:
        category = "other"

    identified_items = vision_result.get("identified_items", [])
    tags = vision_result.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    # Build search text from all vision outputs for entity matching
    search_parts = [description]
    search_parts.extend(identified_items if isinstance(identified_items, list) else [])
    search_parts.extend(tags)
    search_text = " ".join(str(p) for p in search_parts)

    # Match to known entities
    matched = match_to_entities(search_text, entities, top_k=5)

    return {
        "description": description,
        "identified_entities": [
            {"id": m["entity_id"], "name": m["name"], "confidence": m["score"]}
            for m in matched
        ],
        "category": category,
        "tags": tags,
    }


# ══════════════════════════════════════════════════
#  process_upload
# ══════════════════════════════════════════════════

def process_upload(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> dict:
    """
    Xử lý upload ảnh: validate, convert, nhận diện.

    Args:
        file_bytes: Nội dung file dạng bytes.
        filename: Tên file gốc.
        content_type: MIME type (vd: 'image/jpeg').

    Returns:
        Dict chứa kết quả nhận diện + metadata:
        {
            "filename": str,
            "content_type": str,
            "size_bytes": int,
            "description": str,
            "identified_entities": [...],
            "category": str,
            "tags": [...],
        }

    Raises:
        ValueError: Nếu file không hợp lệ (sai type hoặc quá lớn).
    """
    # Validate content type
    ct = content_type.lower().split(";")[0].strip()
    if ct not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Loại file không được hỗ trợ: {ct}. "
            f"Chấp nhận: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    # Validate size
    size = len(file_bytes)
    if size > MAX_FILE_SIZE:
        raise ValueError(
            f"File quá lớn: {size / 1024 / 1024:.1f} MB. "
            f"Giới hạn: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
        )

    if size == 0:
        raise ValueError("File rỗng")

    logger.info("Processing upload: %s (%s, %.1f KB)", filename, ct, size / 1024)

    # Load entities from knowledge base
    try:
        import knowledge
        knowledge._ensure()
        entities = knowledge._entities or {}
    except Exception as exc:
        logger.warning("Could not load entities: %s", exc)
        entities = {}

    # Convert to base64 and recognize
    image_b64 = base64.b64encode(file_bytes).decode("ascii")
    result = recognize_image(image_b64, entities, filename=filename)

    # Add metadata
    result["filename"] = filename
    result["content_type"] = ct
    result["size_bytes"] = size

    return result
