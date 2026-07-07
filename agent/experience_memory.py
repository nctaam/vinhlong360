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

import json
import logging
import re
import unicodedata
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
MEM_DIR = AGENT_DIR / "data" / "memory"
MEM_DIR.mkdir(parents=True, exist_ok=True)
BANK_FILE = MEM_DIR / "experience_bank.json"

_lock = Lock()
MAX_ITEMS = 500

_STOP = frozenset({
    "gi", "la", "co", "cua", "va", "o", "dau", "the", "nao", "khong", "duoc",
    "cho", "den", "tu", "ve", "mot", "cac", "nay", "do", "nen", "minh", "toi",
})


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def _tokens(text: str) -> set:
    return {t for t in _norm(text).split() if len(t) >= 3 and t not in _STOP}


def _intent(query: str) -> str:
    """Coarse intent bucket (keyword-based, no LLM)."""
    q = _norm(query)
    if re.search(r"lich trinh|ke hoach|hanh trinh|tour|di choi \d", q):
        return "itinerary"
    if re.search(r"so sanh|khac nhau|hay hon|vs", q):
        return "comparison"
    if re.search(r"goi y|de xuat|nen di|nen an|nen mua|dac san|co gi", q):
        return "recommendation"
    if re.search(r"mua|thang|le hoi|mua nao|theo mua", q):
        return "seasonal"
    return "factual"


def _load() -> list:
    if BANK_FILE.exists():
        try:
            return json.loads(BANK_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load experience bank: %s", exc)
            return []
    return []


def _save(items: list):
    tmp = BANK_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(BANK_FILE)


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


def record(query: str, tools_used: list, score: float, reply: str = "") -> dict | None:
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

    with _lock:
        items = _load()
        # Merge by (intent, polarity) — reinforce instead of duplicating
        for existing in items:
            if existing["intent"] == item["intent"] and existing["polarity"] == item["polarity"]:
                existing["uses"] = existing.get("uses", 1) + 1
                existing["query_sample"] = query[:120]
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
        item["uses"] = 1
        item["score"] = round(score, 1)
        items.append(item)
        if len(items) > MAX_ITEMS:
            # Drop least-used items
            items.sort(key=lambda x: x.get("uses", 0), reverse=True)
            items = items[:MAX_ITEMS]
        _save(items)
        return item


def retrieve(query: str, k: int = 3) -> list:
    """Top-k relevant strategy items by intent match + token overlap (offline)."""
    items = _load()
    if not items:
        return []
    intent = _intent(query)
    q_tokens = _tokens(query)

    scored = []
    for it in items:
        score = 0.0
        if it["intent"] == intent:
            score += 2.0
        sample_tokens = _tokens(it.get("query_sample", ""))
        overlap = len(q_tokens & sample_tokens)
        score += overlap
        score += 0.1 * it.get("uses", 1)  # mild reinforcement bias
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
    items = _load()
    return {
        "total": len(items),
        "positive": sum(1 for i in items if i["polarity"] == "positive"),
        "negative": sum(1 for i in items if i["polarity"] == "negative"),
        "by_intent": {k: sum(1 for i in items if i["intent"] == k)
                      for k in ("factual", "comparison", "itinerary", "recommendation", "seasonal")},
    }
