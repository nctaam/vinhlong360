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
    except Exception as exc:
        _logger.debug("Failed to write audit log: %s", exc)


def _safe_fitness(name: str, phase: str):
    """Compute fitness, swallowing errors into None (verbatim from phases 1 & 4)."""
    try:
        return self_eval.compute_fitness()
    except Exception as e:
        _logger.error("[%s] fitness_%s failed: %s", name, phase, e)
        return None


def _reload_kb(context: str):
    """Reload live KB defensively, logging any failure (verbatim reload block)."""
    try:
        knowledge.reload()
    except Exception as exc:
        _logger.warning("knowledge.reload after %s failed: %s", context, exc)


def _apply_change(name: str, apply_fn):
    """Run apply_fn; return (change_result, apply_error) (verbatim phase 3)."""
    change_result = None
    apply_error = None
    try:
        change_result = apply_fn()
    except Exception as e:
        apply_error = f"{e}\n{traceback.format_exc()}"
        _logger.error("[%s] apply_fn failed: %s", name, e)
    return change_result, apply_error


def _decide_gate(apply_error, before, after):
    """Compute (decision, reason) from apply outcome + fitness (verbatim phase 5)."""
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
    return decision, reason


def _maybe_rollback(decision: str, snap):
    """Roll back + reload when the gate rejected the change (verbatim phase 6)."""
    rollback_result = None
    if decision == "rolled_back" and snap is not None:
        rollback_result = kb_versioning.rollback(snap["id"])
        _reload_kb("rollback")
    return rollback_result


def _serialize_change_result(change_result):
    """JSON-safe change_result: passthrough for primitives else str() (verbatim)."""
    if isinstance(change_result, (dict, list, str, int, float, type(None))):
        return change_result
    return str(change_result)


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
    before = _safe_fitness(name, "before")

    # 2. Snapshot (rollback point)
    snap = kb_versioning.snapshot(reason=f"pre:{name}", snapshot_id=snapshot_id)

    # 3. Apply the change
    change_result, apply_error = _apply_change(name, apply_fn)

    # Ensure live KB reflects any file changes
    _reload_kb("apply")

    # 4. Fitness after
    after = _safe_fitness(name, "after")

    # 5. Gate decision
    decision, reason = _decide_gate(apply_error, before, after)

    # 6. Rollback if needed
    rollback_result = _maybe_rollback(decision, snap)

    summary = {
        "name": name,
        "timestamp": timestamp,
        "decision": decision,
        "reason": reason,
        "snapshot": snap["id"] if snap else None,
        "before": before,
        "after": after,
        "rollback": rollback_result,
        "change_result": _serialize_change_result(change_result),
    }
    _audit(summary)
    _logger.info("[%s] decision=%s reason=%s", name, decision, reason)
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
            except (json.JSONDecodeError, ValueError):
                pass
        return out
    except Exception as exc:
        _logger.warning("Failed to read audit log: %s", exc)
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
