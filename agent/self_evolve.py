"""
vinhlong360 — Eval-Gated Self-Evolution Orchestrator.

Wraps any autonomous KB-modifying step (learn_loop, relationship_discovery,
auto_learn) in a safety harness:

    fitness_before  →  snapshot  →  apply change  →  reload  →  fitness_after
                                                                      │
                                          ┌───────────────────────────┘
                                          ▼
                          regression?  ── yes ──►  ROLLBACK + log
                                  │
                                  no
                                  ▼
                              KEEP + log

This implements the user-chosen "eval-gated autonomous" model: self-evolution
runs unattended, but a change that fails the fitness gate (self_eval.py) is
automatically reverted from the snapshot (kb_versioning.py). Every decision is
appended to an audit log.

The whole harness is offline — fitness uses retrieval eval + KB health, no LLM —
so the gate works even when the LLM API is down.
"""

import json
import logging
import sys
import traceback
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import knowledge
import self_eval
import kb_versioning

_logger = logging.getLogger("self_evolve")
AUDIT_LOG = AGENT_DIR / "data" / "self_evolve_log.jsonl"


def _audit(record: dict):
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def guarded_evolve(name: str, apply_fn, snapshot_id: str | None = None,
                   timestamp: str | None = None) -> dict:
    """Run `apply_fn` (a KB-modifying step) behind the fitness gate.

    Args:
        name: label for logging (e.g. "learn_loop", "relationship_discovery").
        apply_fn: zero-arg callable that mutates web/data.json. May call
            knowledge.reload() itself; we reload again defensively.
        snapshot_id: stable id for the pre-change snapshot (pass a timestamp from
            the caller if available; else a counter id is used).
        timestamp: optional ISO timestamp string for the audit record.

    Returns a summary dict {name, decision, reason, before, after, change_result}.
    """
    # 1. Fitness before
    try:
        before = self_eval.compute_fitness()
    except Exception as e:
        _logger.error(f"[{name}] fitness_before failed: {e}")
        before = None

    # 2. Snapshot (rollback point)
    snap = kb_versioning.snapshot(reason=f"pre:{name}", snapshot_id=snapshot_id)

    # 3. Apply the change
    change_result = None
    apply_error = None
    try:
        change_result = apply_fn()
    except Exception as e:
        apply_error = f"{e}\n{traceback.format_exc()}"
        _logger.error(f"[{name}] apply_fn failed: {e}")

    # Ensure live KB reflects any file changes
    try:
        knowledge.reload()
    except Exception:
        pass

    # 4. Fitness after
    try:
        after = self_eval.compute_fitness()
    except Exception as e:
        _logger.error(f"[{name}] fitness_after failed: {e}")
        after = None

    # 5. Gate decision
    decision = "kept"
    reason = "no baseline" if before is None else "no regression"
    if apply_error:
        decision = "rolled_back"
        reason = f"apply error: {apply_error[:120]}"
    elif before is not None and after is not None:
        regressed, why = self_eval.is_regression(before, after)
        if regressed:
            decision = "rolled_back"
            reason = why

    # 6. Rollback if needed
    rollback_result = None
    if decision == "rolled_back" and snap is not None:
        rollback_result = kb_versioning.rollback(snap["id"])
        try:
            knowledge.reload()
        except Exception:
            pass

    summary = {
        "name": name,
        "timestamp": timestamp,
        "decision": decision,
        "reason": reason,
        "snapshot": snap["id"] if snap else None,
        "before": before,
        "after": after,
        "rollback": rollback_result,
        "change_result": change_result if isinstance(change_result, (dict, list, str, int, float, type(None))) else str(change_result),
    }
    _audit(summary)
    _logger.info(f"[{name}] decision={decision} reason={reason}")
    return summary


def recent_decisions(limit: int = 20) -> list:
    """Return the most recent self-evolution audit records."""
    if not AUDIT_LOG.exists():
        return []
    try:
        lines = AUDIT_LOG.read_text(encoding="utf-8").strip().split("\n")
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out
    except Exception:
        return []


def status() -> dict:
    decisions = recent_decisions(limit=50)
    kept = sum(1 for d in decisions if d.get("decision") == "kept")
    rolled = sum(1 for d in decisions if d.get("decision") == "rolled_back")
    return {
        "recent_count": len(decisions),
        "kept": kept,
        "rolled_back": rolled,
        "snapshots": kb_versioning.stats(),
        "last_decision": decisions[-1] if decisions else None,
    }
