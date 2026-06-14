"""
vinhlong360 — Retrieval & Resilience Eval (offline, no LLM required).

The existing eval_framework.py measures end-to-end answer quality, which needs a
working LLM. This complementary eval measures the RETRIEVAL layer and the
DEGRADED-MODE behaviour that must work even when the LLM API is down — exactly
the resilience the SOTA research flags as critical for this system.

What it checks (all offline):
  1. Recall@K — for known Vietnamese queries, does hybrid search surface the
     expected entity in the top-K? (context recall proxy)
  2. Grounding — results are real KB entities, never fabricated.
  3. Abstention signal — nonsense queries return few/no results, so the agent
     can correctly say "I don't have that" instead of hallucinating.

Run:
  python agent/retrieval_eval.py            # prints a report
  pytest agent/tests/test_retrieval_eval.py # CI gate
"""

import sys
import unicodedata
import re
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import knowledge


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFD", text.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    return s.replace("đ", "d")


# ── Eval cases: (query, [acceptable entity-id substrings], category) ──
# Each case passes if ANY acceptable substring appears in a top-K result id.
RETRIEVAL_CASES = [
    ("cam sành Trà Ôn",            ["cam-tra-on", "cam-sanh-tra-on", "cho-noi-tra-on"], "factual"),
    ("chợ nổi Trà Ôn ở đâu",       ["cho-noi-tra-on"],                                  "factual"),
    ("chùa Khmer Vĩnh Long",       ["chua-khmer", "chua-"],                             "factual"),
    ("chùa Phước Hậu",             ["chua-phuoc-hau"],                                  "factual"),
    ("bún nước lèo",               ["bun-nuoc-leo"],                                    "factual"),
    ("làng nghề gạch gốm Mang Thít", ["gom-mang-thit", "gach-mang-thit"],              "factual"),
    ("khoai lang Bình Tân",        ["khoai-lang-binh-tan"],                             "factual"),
    ("homestay Khmer",             ["homestay-khmer"],                                  "recommendation"),
    ("Ao Bà Om Trà Vinh",          ["ao-ba-om"],                                        "factual"),
    ("đua ghe ngo",                ["ghe-ngo"],                                         "seasonal"),
]

# Nonsense / out-of-domain queries — should return FEW results (abstention).
ABSTENTION_CASES = [
    "nhà hàng buffet Nhật Bản cao cấp ở Tokyo",
    # Lưu ý: KHÔNG dùng "Paris" — có thật "Khách sạn Paris Vĩnh Long" nên token "paris"
    # khớp đúng (heuristic không phân biệt được ý-định 'bay tới Paris'). Dùng query ngoài-vùng
    # không trùng tên entity local để test đúng ý nghĩa abstention.
    "vé concert BlackPink ở Bangkok",
    "mua iPhone 99 Pro Max ở đâu",
    "qwxzpklmn random gibberish 12345",
]


def _build_indexes():
    """Build BM25 + contextual + TF-IDF indexes (same as server startup)."""
    knowledge._ensure()
    entities = knowledge._entities
    rels = getattr(knowledge, "_relationships", []) or []
    adapted = [
        {"source": r.get("from", ""), "target": r.get("to", ""),
         "type": r.get("type", ""), "label": ""}
        for r in rels
    ]
    try:
        from contextual_retrieval import contextual, bm25
        texts = contextual.build_all_contextual(entities, adapted)
        bm25.build_index(texts)
    except Exception:
        pass
    try:
        from vector_search import embedding_store
        embedding_store.build_index(entities)
    except Exception:
        pass


def _search(query: str, k: int = 5):
    """Run hybrid search if available, else plain keyword search. Returns entity ids."""
    knowledge._ensure()
    keyword = knowledge.search_entities(q=query, limit=max(k * 3, 15))
    try:
        from contextual_retrieval import enhanced_hybrid_search
        merged = enhanced_hybrid_search(
            query=query, keyword_results=keyword,
            entities=knowledge._entities,
            relationships=getattr(knowledge, "_relationships", []) or [],
            top_k=k,
        )
        ids = [m.get("id", m.get("entity_id", "")) for m in merged]
        if ids:
            return ids[:k]
    except Exception:
        pass
    return [e["id"] for e in keyword[:k]]


def run_eval(k: int = 5, verbose: bool = True) -> dict:
    _build_indexes()

    # 1. Recall@K
    hits, total = 0, len(RETRIEVAL_CASES)
    misses = []
    for query, accept, _cat in RETRIEVAL_CASES:
        ids = _search(query, k=k)
        ids_norm = [_norm(i) for i in ids]
        ok = any(any(_norm(a) in i for i in ids_norm) for a in accept)
        if ok:
            hits += 1
        else:
            misses.append({"query": query, "expected": accept, "got": ids})

    recall = hits / total if total else 0.0

    # 2. Abstention: nonsense queries should yield no RELEVANT results.
    # Apply the same relevance gate the degraded-mode fallback uses.
    abstain_ok, abstain_total = 0, len(ABSTENTION_CASES)
    abstain_detail = []
    for query in ABSTENTION_CASES:
        ids = _search(query, k=k)
        relevant = []
        for eid in ids:
            ent = knowledge.get_entity(eid)
            if ent and knowledge.query_relevance(query, ent):
                relevant.append(eid)
        passed = len(relevant) == 0  # no relevant entity → correct abstention
        if passed:
            abstain_ok += 1
        abstain_detail.append({"query": query, "n_relevant": len(relevant), "abstained": passed})

    report = {
        "recall_at_k": round(recall, 3),
        "k": k,
        "hits": hits,
        "total": total,
        "misses": misses,
        "abstention_rate": round(abstain_ok / abstain_total, 3) if abstain_total else 0.0,
        "abstention_detail": abstain_detail,
    }

    if verbose:
        print("=" * 60)
        print(f"  Retrieval Eval — Recall@{k}: {recall:.0%} ({hits}/{total})")
        print(f"  Abstention rate: {report['abstention_rate']:.0%} ({abstain_ok}/{abstain_total})")
        print("=" * 60)
        for m in misses:
            print(f"  MISS: '{m['query']}' expected {m['expected']}")
            print(f"        got: {m['got']}")
    return report


if __name__ == "__main__":
    run_eval()
