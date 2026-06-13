"""
vinhlong360 — Self-Evaluation Fitness Function.

The fitness function that gates all self-evolution. Every autonomous KB change
(learn_loop, relationship_discovery, auto_learn) is wrapped so that a change is
only KEPT if it does not regress this fitness score — otherwise it is rolled back
(see self_evolve.py). This is the "eval-as-fitness" discipline the SOTA research
flags as mandatory for safe self-evolution (arXiv 2509.26354 "misevolution").

Design goals:
  - OFFLINE: runs without the LLM (uses retrieval eval + KB health stats), so the
    gate works even when the LLM API is down.
  - FAST-ish: builds indexes once per call (~seconds), fine for a 3h cycle.
  - MULTI-DIMENSIONAL: never a single scalar that can be reward-hacked — tracks
    retrieval recall, abstention, and KB-health sub-metrics separately, plus a
    composite for convenience.

Usage:
    from self_eval import compute_fitness, is_regression
    before = compute_fitness()
    ... apply a self-change + knowledge.reload() ...
    after = compute_fitness()
    if is_regression(before, after): rollback()
"""

import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import knowledge

# Content entity types (exclude places/admin units)
_CONTENT_TYPES = frozenset([
    "experience", "product", "dish", "craft_village", "attraction",
    "accommodation", "person", "event", "history", "nature", "economy",
    "organization",
])


def _kb_health(entities: dict) -> dict:
    """Structural health metrics of the KB (no LLM)."""
    content = [e for e in entities.values() if e.get("type") in _CONTENT_TYPES]
    n = len(content)
    if n == 0:
        return {"entities": 0, "summary_coverage": 0.0, "avg_confidence": 0.0,
                "dup_ratio": 0.0, "provisional_ratio": 0.0}

    with_summary = sum(1 for e in content if len((e.get("summary") or "").strip()) >= 20)
    confidences = [e.get("confidence", 0) for e in content if e.get("confidence") is not None]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    # Duplicate detection by normalized name (cheap proxy)
    seen = {}
    dups = 0
    for e in content:
        key = knowledge._normalize_vn(e.get("name", "")).strip()
        if not key:
            continue
        if key in seen:
            dups += 1
        else:
            seen[key] = True

    provisional = sum(1 for e in content if e.get("status") == "provisional" or e.get("verified") is False)

    return {
        "entities": n,
        "summary_coverage": round(with_summary / n, 4),
        "avg_confidence": round(avg_conf, 4),
        "dup_ratio": round(dups / n, 4),
        "provisional_ratio": round(provisional / n, 4),
    }


def compute_fitness(verbose: bool = False) -> dict:
    """Compute the multi-dimensional fitness of the current KB + retrieval layer.

    Returns a dict with sub-metrics and a composite score in [0, 1].
    """
    knowledge.reload() if False else knowledge._ensure()

    # Retrieval quality (offline) — recall@5 + abstention rate.
    try:
        import retrieval_eval
        report = retrieval_eval.run_eval(k=5, verbose=False)
        recall = report["recall_at_k"]
        abstention = report["abstention_rate"]
    except Exception:
        recall = 0.0
        abstention = 0.0

    health = _kb_health(knowledge._entities)

    # Composite: retrieval quality dominates; KB health is a guardrail.
    # Penalize duplicates heavily (they signal KB pollution).
    composite = (
        0.45 * recall +
        0.15 * abstention +
        0.20 * health["summary_coverage"] +
        0.10 * min(health["avg_confidence"], 1.0) +
        0.10 * (1.0 - min(health["dup_ratio"] * 5, 1.0))  # dups hurt fast
    )

    result = {
        "composite": round(composite, 4),
        "recall_at_5": recall,
        "abstention_rate": abstention,
        **health,
    }
    if verbose:
        print("Fitness:", result)
    return result


# Tolerance: how much the composite may drop before we call it a regression.
COMPOSITE_EPSILON = 0.01
# Recall is a hard guardrail — never allow it to drop more than this.
RECALL_HARD_DROP = 0.05


def is_regression(before: dict, after: dict) -> tuple[bool, str]:
    """Decide whether `after` is a regression vs `before`.

    Returns (is_regression, reason). A change is a regression if:
      - the composite drops by more than COMPOSITE_EPSILON, OR
      - recall@5 drops by more than RECALL_HARD_DROP (hard guardrail), OR
      - duplicate ratio increases meaningfully (KB pollution signal).
    """
    if after.get("recall_at_5", 0) < before.get("recall_at_5", 0) - RECALL_HARD_DROP:
        return True, (f"recall dropped {before.get('recall_at_5')}→{after.get('recall_at_5')}")
    if after.get("composite", 0) < before.get("composite", 0) - COMPOSITE_EPSILON:
        return True, (f"composite dropped {before.get('composite')}→{after.get('composite')}")
    if after.get("dup_ratio", 0) > before.get("dup_ratio", 0) + 0.02:
        return True, (f"duplicate ratio rose {before.get('dup_ratio')}→{after.get('dup_ratio')}")
    return False, "no regression"


if __name__ == "__main__":
    import json
    print(json.dumps(compute_fitness(verbose=False), ensure_ascii=False, indent=2))
