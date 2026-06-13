"""
vinhlong360 — KB-in-Context builder.

For a small KB (~300 entities) the research consensus (Anthropic, W&B) is that
you can give the model the knowledge base directly in context instead of relying
purely on retrieval. This module builds a compact, cached digest of the KB and
injects it into the system prompt so the agent:

  - knows what entities EXIST (→ better search queries, correct abstention)
  - can answer simple lookups without a tool round-trip (fewer LLM calls — a win
    when the LLM API is flaky/slow)

Three modes (env var KB_CONTEXT_MODE):
  - "off"   : inject nothing (pure retrieval, original behaviour)
  - "index" : compact table-of-contents — names grouped by type/area (~3K tokens). DEFAULT.
  - "full"  : index + one-line summaries (~10-12K tokens). Use only when the LLM
              API supports prompt caching, otherwise it adds latency per call.

The digest is built once and cached in-memory; call invalidate() after a KB reload.
"""

import os
from threading import Lock

MODE = os.environ.get("KB_CONTEXT_MODE", "index").strip().lower()

# Token budget guard (rough): ~4 chars/token. Keep digest under this many chars.
_MAX_CHARS = {
    "index": 16000,   # ~4K tokens
    "full": 52000,    # ~13K tokens
}

_TYPE_LABELS = {
    "place": "Xã/phường",
    "experience": "Trải nghiệm",
    "product": "Sản phẩm/đặc sản",
    "dish": "Món ăn",
    "craft_village": "Làng nghề",
    "attraction": "Điểm tham quan",
    "accommodation": "Lưu trú",
    "person": "Nhân vật",
    "event": "Lễ hội/sự kiện",
    "history": "Lịch sử",
    "nature": "Thiên nhiên",
    "economy": "Kinh tế",
    "organization": "Tổ chức",
}

# Types worth listing in the in-context index (skip places — too many, low value)
_CONTENT_TYPES = [
    "attraction", "experience", "product", "dish", "craft_village",
    "accommodation", "event", "person", "history", "nature", "economy",
]

_lock = Lock()
_cache = {"text": None, "mode": None, "count": 0}


def _place_name(entity, entities_by_id):
    pid = entity.get("placeId")
    if pid and pid in entities_by_id:
        return entities_by_id[pid].get("name", "")
    return ""


def build_kb_index(entities: dict) -> str:
    """Compact table-of-contents: entity names grouped by type. ~3K tokens."""
    by_type: dict[str, list[str]] = {}
    for e in entities.values():
        et = e.get("type")
        if et not in _CONTENT_TYPES:
            continue
        place = _place_name(e, entities)
        label = e["name"] + (f" ({place})" if place else "")
        by_type.setdefault(et, []).append(label)

    lines = ["## Danh mục dữ liệu hiện có (để tra cứu — KHÔNG bịa ngoài danh mục này)"]
    for et in _CONTENT_TYPES:
        names = by_type.get(et)
        if not names:
            continue
        names.sort()
        lines.append(f"\n**{_TYPE_LABELS.get(et, et)}** ({len(names)}): " + "; ".join(names))

    text = "\n".join(lines)
    cap = _MAX_CHARS["index"]
    if len(text) > cap:
        text = text[:cap] + "\n…(danh mục bị cắt bớt)"
    return text


def build_kb_digest(entities: dict) -> str:
    """Index + one-line summaries. ~10-12K tokens. Use with prompt caching."""
    by_type: dict[str, list[str]] = {}
    for e in entities.values():
        et = e.get("type")
        if et not in _CONTENT_TYPES:
            continue
        place = _place_name(e, entities)
        summary = (e.get("summary") or "").strip().replace("\n", " ")
        if len(summary) > 100:
            summary = summary[:100] + "…"
        ocop = e.get("attributes", {}).get("ocop")
        tag = " [OCOP]" if ocop else ""
        loc = f" — {place}" if place else ""
        by_type.setdefault(et, []).append(f"- {e['name']}{loc}{tag}: {summary}")

    lines = ["## Cơ sở dữ liệu (tóm tắt — chỉ dùng dữ liệu trong đây, không bịa)"]
    for et in _CONTENT_TYPES:
        items = by_type.get(et)
        if not items:
            continue
        items.sort()
        lines.append(f"\n### {_TYPE_LABELS.get(et, et)} ({len(items)})")
        lines.extend(items)

    text = "\n".join(lines)
    cap = _MAX_CHARS["full"]
    if len(text) > cap:
        text = text[:cap] + "\n…(tóm tắt bị cắt bớt — dùng tool search để xem thêm)"
    return text


def get_kb_context(entities: dict) -> str:
    """Return the cached KB context block for the active mode (or '' if off)."""
    if MODE == "off":
        return ""
    with _lock:
        if _cache["text"] is not None and _cache["mode"] == MODE:
            return _cache["text"]
        if MODE == "full":
            text = build_kb_digest(entities)
        else:  # "index" (default)
            text = build_kb_index(entities)
        _cache["text"] = text
        _cache["mode"] = MODE
        _cache["count"] = len(entities)
    return text


def invalidate():
    """Clear the cached digest (call after KB reload)."""
    with _lock:
        _cache["text"] = None
        _cache["mode"] = None
        _cache["count"] = 0


def stats() -> dict:
    with _lock:
        return {
            "mode": MODE,
            "cached": _cache["text"] is not None,
            "chars": len(_cache["text"]) if _cache["text"] else 0,
            "approx_tokens": (len(_cache["text"]) // 4) if _cache["text"] else 0,
        }
