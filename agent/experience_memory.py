"""
vinhlong360 — Experience Memory (ReasoningBank-lite).

Implements the 2025 SOTA pattern (ReasoningBank, arXiv 2509.25140): instead of
storing raw trajectories or only "Score N" boilerplate, distill each interaction
into a compact STRATEGY ITEM and — crucially — learn from FAILURES as NEGATIVE
CONSTRAINTS. Retrieved top-k by intent and injected as a "lessons" block.

Item shape:
    {id, intent, polarity: "positive"|"negative",
     title, principles: [str], query_sample, uses, score}

Safety (per the "misevolution" research): the injected block is explicitly
labeled "tham khảo, không phải chân lý" (reference, not ground truth) so learned
lessons never override the core domain/grounding rules. Retrieval is offline
(token overlap on normalized Vietnamese) — works when the LLM API is down.

No LLM required: distillation is rule-based from the tool sequence + answer
shape, so the loop keeps learning during API outages.
"""

from functools import lru_cache
import json
import logging
import re
import unicodedata
from pathlib import Path
from threading import RLock

from owner_write_gate import owner_write_gate

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
MEM_DIR = AGENT_DIR / "data" / "memory"
MEM_DIR.mkdir(parents=True, exist_ok=True)
BANK_FILE = MEM_DIR / "experience_bank.json"

_lock = RLock()
MAX_ITEMS = 500
_bank_cache_key: tuple[str, int, int] | None = None
_bank_cache_items: list[dict] = []

_DIACRITIC_RE = re.compile(r"[̀-ͯ]")
_WS_RE = re.compile(r"\s+")
_INTENT_ITINERARY_RE = re.compile(r"lich trinh|ke hoach|hanh trinh|tour|di choi \d")
_INTENT_COMPARISON_RE = re.compile(r"so sanh|khac nhau|hay hon|vs")
_INTENT_RECOMMEND_RE = re.compile(r"goi y|de xuat|nen di|nen an|nen mua|dac san|co gi")
_INTENT_SEASONAL_RE = re.compile(r"mua|thang|le hoi|mua nao|theo mua")

_STOP = frozenset({
    "gi", "la", "co", "cua", "va", "o", "dau", "the", "nao", "khong", "duoc",
    "cho", "den", "tu", "ve", "mot", "cac", "nay", "do", "nen", "minh", "toi",
})


@lru_cache(maxsize=1024)
def _norm(text: str) -> str:
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = _DIACRITIC_RE.sub("", s).replace("đ", "d")
    return _WS_RE.sub(" ", s).strip()


@lru_cache(maxsize=1024)
def _tokens_cached(text: str) -> frozenset[str]:
    return frozenset(t for t in _norm(text).split() if len(t) >= 3 and t not in _STOP)


def _tokens(text: str) -> set:
    return set(_tokens_cached(text))


def _intent(query: str) -> str:
    """Coarse intent bucket (keyword-based, no LLM)."""
    q = _norm(query)
    if _INTENT_ITINERARY_RE.search(q):
        return "itinerary"
    if _INTENT_COMPARISON_RE.search(q):
        return "comparison"
    if _INTENT_RECOMMEND_RE.search(q):
        return "recommendation"
    if _INTENT_SEASONAL_RE.search(q):
        return "seasonal"
    return "factual"


def _load() -> list:
    global _bank_cache_key, _bank_cache_items
    if BANK_FILE.exists():
        try:
            st = BANK_FILE.stat()
            key = (str(BANK_FILE), st.st_mtime_ns, st.st_size)
            if _bank_cache_key == key:
                return [dict(it) for it in _bank_cache_items]
            data = json.loads(BANK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                _bank_cache_key = key
                _bank_cache_items = [dict(it) if isinstance(it, dict) else it for it in data]
            return data
        except Exception as exc:
            _bank_cache_key = None
            logger.warning("Failed to load experience bank: %s", exc)
            return []
    _bank_cache_key = None
    return []


def _save(items: list):
    global _bank_cache_key, _bank_cache_items
    from versioned_json_store import atomic_write_json

    atomic_write_json(BANK_FILE, items, indent=2)
    try:
        st = BANK_FILE.stat()
        _bank_cache_key = (str(BANK_FILE), st.st_mtime_ns, st.st_size)
        _bank_cache_items = [dict(it) if isinstance(it, dict) else it for it in items]
    except OSError:
        _bank_cache_key = None


def _tool_names(tools_used: list) -> list:
    names = []
    for t in tools_used or []:
        n = t.split("(")[0] if isinstance(t, str) and "(" in t else t
        if n and n not in names:
            names.append(n)
    return names


def _distill_positive(query: str, tools: list) -> dict:
    intent = _intent(query)
    tool_names = [t for t in _tool_names(tools) if t not in ("suggest_followups",)]
    principles = []
    if tool_names:
        principles.append("Dùng công cụ theo thứ tự: " + " → ".join(tool_names))
    principles.append("Trả lời có cấu trúc, trích dẫn dữ liệu từ tool, đúng trọng tâm câu hỏi.")
    return {
        "intent": intent,
        "polarity": "positive",
        "title": f"Chiến lược tốt cho câu hỏi dạng '{intent}'",
        "principles": principles,
    }


def _distill_negative(query: str, tools: list, reply: str) -> dict:
    intent = _intent(query)
    tool_names = _tool_names(tools)
    principles = []
    if not tool_names:
        principles.append("KHÔNG trả lời mà chưa gọi tool tra cứu — phải verify bằng dữ liệu.")
    if reply and len(reply) < 120:
        principles.append("Tránh trả lời quá ngắn/sơ sài; bổ sung chi tiết, ví dụ cụ thể.")
    if not principles:
        principles.append("Xem lại cách tiếp cận cho dạng câu hỏi này — kết quả chưa đạt.")
    return {
        "intent": intent,
        "polarity": "negative",
        "title": f"Ràng buộc cần tránh cho câu hỏi dạng '{intent}'",
        "principles": principles,
    }


def record(
    query: str,
    tools_used: list,
    score: float,
    reply: str = "",
    *,
    owner_key: str = "",
) -> dict | None:
    """Distill an interaction into a strategy item (positive) or constraint (negative).

    score: reflexion answer score (0-10). >=8 → positive lesson; <5 → negative.
    Returns the stored/merged item, or None if the interaction is unremarkable.
    """
    if score >= 8:
        item = _distill_positive(query, tools_used)
    elif score < 5:
        item = _distill_negative(query, tools_used, reply)
    else:
        return None  # middling — nothing to learn

    owner_write_gate.assert_writable(owner_key)
    with _lock:
        items = _load()
        # Merge by (intent, polarity) — reinforce instead of duplicating
        for existing in items:
            if (
                existing["intent"] == item["intent"]
                and existing["polarity"] == item["polarity"]
                and existing.get("owner_key", "") == owner_key
            ):
                existing["uses"] = existing.get("uses", 1) + 1
                existing["query_sample"] = query[:120]
                existing["owner_key"] = owner_key
                # Union principles (keep it tight)
                merged = existing.get("principles", [])
                for p in item["principles"]:
                    if p not in merged:
                        merged.append(p)
                existing["principles"] = merged[:5]
                _save(items)
                return existing

        item["id"] = f"exp_{len(items) + 1:05d}"
        item["query_sample"] = query[:120]
        item["owner_key"] = owner_key
        item["uses"] = 1
        item["score"] = round(score, 1)
        items.append(item)
        if len(items) > MAX_ITEMS:
            # Drop least-used items
            items.sort(key=lambda x: x.get("uses", 0), reverse=True)
            items = items[:MAX_ITEMS]
        _save(items)
        return item


def purge_owner(owner_key: str) -> int:
    """Remove every learned item attributed to one exact owner."""
    with _lock:
        items = _load()
        retained = [
            item for item in items if item.get("owner_key", "") != owner_key
        ]
        removed = len(items) - len(retained)
        if removed:
            _save(retained)
        return removed


def verify_owner_absent(owner_key: str) -> bool:
    with _lock:
        if not BANK_FILE.exists():
            return True
        items = json.loads(BANK_FILE.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError("Invalid experience store")
        return not any(
            item.get("owner_key", "") == owner_key for item in items
        )


def retrieve(query: str, k: int = 3) -> list:
    """Top-k relevant strategy items by intent match + token overlap (offline)."""
    with _lock:
        items = _load()
    if not items:
        return []
    intent = _intent(query)
    q_tokens = _tokens_cached(query)

    scored = []
    for it in items:
        score = 2.0 if it["intent"] == intent else 0.0
        sample_tokens = _tokens_cached(it.get("query_sample", ""))
        score += len(q_tokens & sample_tokens) + 0.1 * it.get("uses", 1)
        if score > 0:
            scored.append((score, it))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]


def build_prompt(query: str, k: int = 3) -> str:
    """Build the 'lessons' context block for injection (or '' if nothing relevant)."""
    items = retrieve(query, k=k)
    if not items:
        return ""
    pos = [it for it in items if it["polarity"] == "positive"]
    neg = [it for it in items if it["polarity"] == "negative"]

    lines = ["## Kinh nghiệm rút ra (THAM KHẢO — không ghi đè quy tắc cốt lõi)"]
    for it in pos:
        for p in it.get("principles", [])[:2]:
            lines.append(f"- ✓ {p}")
    for it in neg:
        for p in it.get("principles", [])[:2]:
            lines.append(f"- ✗ Tránh: {p}")
    return "\n".join(lines) if len(lines) > 1 else ""


def stats() -> dict:
    with _lock:
        items = _load()
    return {
        "total": len(items),
        "positive": sum(1 for i in items if i["polarity"] == "positive"),
        "negative": sum(1 for i in items if i["polarity"] == "negative"),
        "by_intent": {k: sum(1 for i in items if i["intent"] == k)
                      for k in ("factual", "comparison", "itinerary", "recommendation", "seasonal")},
    }
