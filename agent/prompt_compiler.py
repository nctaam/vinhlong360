"""
vinhlong360 — Prompt Compiler (lightweight BootstrapFewShot).

DSPy's simplest, most production-credible optimizer is BootstrapFewShot:
collect metric-FILTERED high-quality (input, output) examples and compile them
into few-shot demonstrations. This module implements that essence WITHOUT the
heavy `dspy` dependency or an unstable compile step — important because this
system's LLM API is intermittent.

How it works:
  - record_demo(query, answer, score): captures high-scoring (>=8) interactions.
  - compile(): selects a small, DIVERSE, deduped set of canonical exemplars per
    intent and writes a static artifact (compiled_demos.json).
  - get_demos(query, k): returns relevant compiled demos for prompt injection.

The compiled artifact is STATIC → usable even when the LLM API is down. Few-shot
injection adds tokens per call, so it is OFF by default (env FEWSHOT_DEMOS=on)
and capped tightly; turn it on when the API supports prompt caching.
"""

import json
import os
import re
import unicodedata
from pathlib import Path
from threading import Lock

from owner_write_gate import owner_write_gate

AGENT_DIR = Path(__file__).resolve().parent
DEMO_DIR = AGENT_DIR / "data" / "optimizer"
DEMO_DIR.mkdir(parents=True, exist_ok=True)
RAW_FILE = DEMO_DIR / "demo_pool.json"
COMPILED_FILE = DEMO_DIR / "compiled_demos.json"

ENABLED = os.environ.get("FEWSHOT_DEMOS", "off").strip().lower() in ("on", "true", "1")
MIN_SCORE = 8.0
MAX_POOL = 300
DEMOS_PER_INTENT = 2     # keep the few-shot block tiny
MAX_ANSWER_CHARS = 600

_lock = Lock()

_STOP = frozenset({"gi", "la", "co", "cua", "va", "o", "dau", "the", "nao", "nen"})


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFD", (text or "").lower())
    s = re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def _tokens(text: str) -> set:
    return {t for t in _norm(text).split() if len(t) >= 3 and t not in _STOP}


def _intent(query: str) -> str:
    q = _norm(query)
    if re.search(r"lich trinh|ke hoach|hanh trinh|tour", q):
        return "itinerary"
    if re.search(r"so sanh|khac nhau|hay hon", q):
        return "comparison"
    if re.search(r"goi y|de xuat|nen di|nen an|dac san", q):
        return "recommendation"
    if re.search(r"mua|thang|le hoi", q):
        return "seasonal"
    return "factual"


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _save(path: Path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def record_demo(
    query: str,
    answer: str,
    score: float,
    *,
    owner_key: str = "",
):
    """Capture a high-scoring (query, answer) pair into the demo pool."""
    if score < MIN_SCORE or not answer or len(answer) < 80:
        return
    owner_write_gate.assert_writable(owner_key)
    with _lock:
        pool = _load(RAW_FILE, [])
        pool.append({
            "intent": _intent(query),
            "query": query[:160],
            "answer": answer[:MAX_ANSWER_CHARS],
            "score": round(score, 1),
            "owner_key": owner_key,
        })
        if len(pool) > MAX_POOL:
            pool.sort(key=lambda d: d.get("score", 0), reverse=True)
            pool = pool[:MAX_POOL]
        _save(RAW_FILE, pool)


def compile() -> dict:
    """Select diverse canonical demos per intent → static artifact.

    Diversity: within each intent, greedily pick demos whose query tokens are
    least similar to already-picked ones (avoids near-duplicate exemplars).
    """
    with _lock:
        pool = _load(RAW_FILE, [])
        by_intent: dict[str, list] = {}
        for d in pool:
            by_intent.setdefault(d["intent"], []).append(d)

        compiled: dict[str, list] = {}
        for intent, demos in by_intent.items():
            demos.sort(key=lambda d: d.get("score", 0), reverse=True)
            picked = []
            picked_tokens = []
            for d in demos:
                dt = _tokens(d["query"])
                # Skip if too similar to an already-picked demo
                if any(len(dt & pt) >= max(2, len(dt) // 2) for pt in picked_tokens):
                    continue
                picked.append(d)
                picked_tokens.append(dt)
                if len(picked) >= DEMOS_PER_INTENT:
                    break
            compiled[intent] = picked

        artifact = {"demos": compiled, "pool_size": len(pool)}
        _save(COMPILED_FILE, artifact)
        return {"intents": list(compiled.keys()),
                "total_demos": sum(len(v) for v in compiled.values()),
                "pool_size": len(pool)}


def _without_owner(entries, owner_key: str, error_message: str) -> tuple[list, int]:
    if not isinstance(entries, list):
        raise ValueError(error_message)
    retained = [
        entry for entry in entries if entry.get("owner_key", "") != owner_key
    ]
    return retained, len(entries) - len(retained)


def _compiled_without_owner(artifact, owner_key: str) -> tuple[dict, int]:
    if not isinstance(artifact, dict):
        raise ValueError("Invalid compiled prompt store")
    demos = artifact.get("demos", {})
    if not isinstance(demos, dict):
        raise ValueError("Invalid compiled prompt store")
    retained_demos = {}
    removed = 0
    for intent, entries in demos.items():
        retained, intent_removed = _without_owner(
            entries, owner_key, "Invalid compiled prompt store"
        )
        retained_demos[intent] = retained
        removed += intent_removed
    return retained_demos, removed


def purge_owner(owner_key: str) -> int:
    """Remove an exact owner's raw and compiled demonstration copies."""
    with _lock:
        pool = _load(RAW_FILE, [])
        retained_pool, removed = _without_owner(
            pool, owner_key, "Invalid prompt demo pool"
        )
        if removed:
            _save(RAW_FILE, retained_pool)

        artifact = _load(COMPILED_FILE, {"demos": {}})
        retained_demos, removed_compiled = _compiled_without_owner(
            artifact, owner_key
        )
        if removed_compiled or (removed and COMPILED_FILE.exists()):
            artifact["demos"] = retained_demos
            artifact["pool_size"] = len(retained_pool)
            _save(COMPILED_FILE, artifact)
        return removed + removed_compiled


def verify_owner_absent(owner_key: str) -> bool:
    with _lock:
        if RAW_FILE.exists():
            pool = json.loads(RAW_FILE.read_text(encoding="utf-8"))
            if not isinstance(pool, list):
                raise ValueError("Invalid prompt demo pool")
            if any(demo.get("owner_key", "") == owner_key for demo in pool):
                return False
        if not COMPILED_FILE.exists():
            return True
        artifact = json.loads(COMPILED_FILE.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict) or not isinstance(
            artifact.get("demos", {}), dict
        ):
            raise ValueError("Invalid compiled prompt store")
        return not any(
            demo.get("owner_key", "") == owner_key
            for entries in artifact.get("demos", {}).values()
            for demo in entries
        )


def get_demos(query: str, k: int = DEMOS_PER_INTENT) -> list:
    """Return compiled demos relevant to the query (by intent)."""
    if not ENABLED:
        return []
    artifact = _load(COMPILED_FILE, {"demos": {}})
    demos = artifact.get("demos", {})
    return demos.get(_intent(query), [])[:k]


def build_prompt(query: str) -> str:
    """Build a few-shot demonstration block for injection ('' if disabled/empty)."""
    demos = get_demos(query)
    if not demos:
        return ""
    lines = ["## Ví dụ tham khảo (cách trả lời tốt cho dạng câu hỏi này)"]
    for d in demos:
        lines.append(f"\nHỏi: {d['query']}\nĐáp (mẫu tốt): {d['answer']}")
    return "\n".join(lines)


def stats() -> dict:
    pool = _load(RAW_FILE, [])
    artifact = _load(COMPILED_FILE, {"demos": {}})
    return {
        "enabled": ENABLED,
        "pool_size": len(pool),
        "compiled_intents": list(artifact.get("demos", {}).keys()),
        "compiled_demos": sum(len(v) for v in artifact.get("demos", {}).values()),
    }
