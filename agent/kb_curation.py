"""
vinhlong360 — KB Curation (Quarantine review & promotion).

Auto-learned entities enter the KB as `status: provisional, verified: false`
(see learn_loop.py). They are down-weighted in ranking and labeled
"chưa kiểm chứng" in answers. This module manages their lifecycle:

  - list_provisional()      : the review queue
  - promote(id, token)      : reviewed provisional snapshot → verified
  - reject(id)              : remove a bad provisional entity
  - auto_promote_pass()     : eval-gated automatic promotion of provisional
                              entities that have PROVEN useful (queried/hit with
                              no negative feedback). This realizes the user's
                              "eval-gated autonomous" choice: knowledge that
                              survives real use and doesn't hurt fitness graduates
                              to verified automatically.

All writes go to web/data.json and trigger knowledge.reload().
"""

import copy
import hashlib
import hmac
import json
import logging
import re as _re
import unicodedata as _ud
from functools import lru_cache
from pathlib import Path

from versioned_json_store import compare_and_swap_json, load_json, load_json_versioned, mutate_json
from structured_logging import install_redaction_filter

logger = logging.getLogger(__name__)
install_redaction_filter(logger)

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
DATA_JSON = PROJECT_DIR / "web" / "data.json"
ANALYTICS_FILE = AGENT_DIR / "data" / "analytics.json"
_PROVISIONAL_AUDIT_CONTEXT: dict[str, tuple[str, str]] = {}


def _load_kb() -> dict:
    if DATA_JSON == PROJECT_DIR / "web" / "data.json":
        try:
            import knowledge
            if getattr(knowledge, "_data_source", None) == "db" and getattr(knowledge, "_entities", None):
                return {"entities": list(knowledge._entities.values())}
        except Exception:
            pass
    return load_json(DATA_JSON)


def _reload():
    try:
        import knowledge
        knowledge.reload()
    except Exception as exc:
        logger.warning("Failed to reload knowledge: %s", exc)


# GĐ-audit (B1): DB là nguồn sự thật cho chat (knowledge.reload đọc DB). Mọi mutate KB
# PHẢI ghi DB, không chỉ data.json (nếu chỉ data.json thì chat không thấy + bị export ghi đè).
def _db_upsert(entity: dict, *, actor_id: str = "system", reason: str = "entity_upsert", strict: bool = False):
    actor_id, reason = _PROVISIONAL_AUDIT_CONTEXT.pop(entity.get("id"), (actor_id, reason))
    try:
        from database import db
        db.upsert_entity(entity, actor_id=actor_id, reason=reason,
                         correlation_id=f"{reason}:{entity.get('id', '')}")
        return True
    except Exception as e:  # noqa: BLE001 - không để lỗi DB làm hỏng thao tác (data.json vẫn ghi)
        logger.exception("DB upsert failed for %s: %s", entity.get("id"), e)
        if getattr(e, "committed", False):
            return {"ok": False, "committed": True, "error": "post_commit_effect_failed"}
        if getattr(e, "commit_outcome_unknown", False):
            return {"ok": False, "committed": "unknown", "error": "commit_outcome_unknown"}
        if strict:
            raise
        return False


def _db_delete(entity_id: str, *, actor_id: str = "system", reason: str = "entity_delete", strict: bool = False):
    actor_id, reason = _PROVISIONAL_AUDIT_CONTEXT.pop(entity_id, (actor_id, reason))
    try:
        from database import db
        db.delete_entity(entity_id, actor_id=actor_id, reason=reason,
                         correlation_id=f"{reason}:{entity_id}")
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("DB delete failed for %s: %s", entity_id, e)
        if getattr(e, "committed", False):
            return {"ok": False, "committed": True, "error": "post_commit_effect_failed"}
        if getattr(e, "commit_outcome_unknown", False):
            return {"ok": False, "committed": "unknown", "error": "commit_outcome_unknown"}
        if strict:
            raise
        return False


def _is_provisional(e: dict) -> bool:
    return e.get("status") == "provisional" or e.get("verified") is False


def _review_snapshot(entity: dict) -> dict:
    return {k: v for k, v in entity.items() if k not in ("status", "verified")}


def _review_token(snapshot: dict) -> str:
    canonical = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _rollback_promotion(entity_id: str, original: dict, promoted: dict) -> bool:
    """Undo only our exact promotion, preserving unrelated concurrent edits."""
    def revert(data: dict):
        for index, entity in enumerate(data.get("entities", [])):
            if entity.get("id") != entity_id:
                continue
            if entity != promoted:
                return False, False
            data["entities"][index] = copy.deepcopy(original)
            return True, True
        return False, False

    return bool(mutate_json(DATA_JSON, revert))


def _rollback_rejection(entity: dict, relationships: list[dict], expected_after: dict, expected_version: str) -> bool:
    """Restore only a rejected entity and its removed edges under the JSON lock."""
    current, version = load_json_versioned(DATA_JSON)
    if version != expected_version or current != expected_after:
        return False
    restored = copy.deepcopy(expected_after)
    restored.setdefault("entities", []).append(copy.deepcopy(entity))
    restored.setdefault("relationships", []).extend(copy.deepcopy(relationships))
    return bool(compare_and_swap_json(DATA_JSON, expected_version, restored))


def _db_compensation_succeeded(result: object) -> bool:
    """Accept only an explicit successful DB restore outcome.

    A compensation boundary may return a structured failure even when the
    original write was not committed. Treat unknown or false-y outcomes as
    uncertain so JSON is retained for reconciliation instead of being rolled
    back against a still-verified DB row.
    """
    if result is True:
        return True
    return (
        isinstance(result, dict)
        and result.get("ok") is True
        and not result.get("committed")
    )


def list_provisional() -> list:
    """Return all provisional (unverified, auto-learned) entities."""
    kb = _load_kb()
    reviews = []
    for entity in kb.get("entities", []):
        if not _is_provisional(entity):
            continue
        snapshot = _review_snapshot(entity)
        reviews.append({
            "id": entity["id"],
            "review_token": _review_token(snapshot),
            "entity": snapshot,
        })
    return reviews


def promote(entity_id: str, review_token: str) -> dict:
    """Promote a provisional entity to verified (trusted)."""
    kb, version = load_json_versioned(DATA_JSON)
    e = next((item for item in kb["entities"] if item["id"] == entity_id), None)
    if e is None:
        return {"ok": False, "error": "not found"}
    if not _is_provisional(e):
        return {"ok": False, "error": "already verified"}
    current_token = _review_token(_review_snapshot(e))
    if not isinstance(review_token, str) or not hmac.compare_digest(current_token, review_token):
        return {"ok": False, "error": "stale_review"}
    before = copy.deepcopy(e)
    e["status"] = "verified"
    e["verified"] = True
    promoted = copy.deepcopy(e)
    if not compare_and_swap_json(DATA_JSON, version, kb):
        return {"ok": False, "error": "stale_review"}
    _PROVISIONAL_AUDIT_CONTEXT[entity_id] = ("admin", "provisional_approve")
    try:
        db_result = _db_upsert(promoted)
        if db_result is False:
            raise RuntimeError("db_write_failed")
    except Exception:
        rolled_back = _rollback_promotion(entity_id, before, promoted)
        return {"ok": False, "error": "db_write_failed"} if rolled_back else {
            "ok": False, "error": "db_write_failed", "degraded": True,
            "reconciliation_required": [entity_id],
        }
    if isinstance(db_result, dict) and db_result.get("committed"):
        _reload()
        return {"ok": False, "error": "db_write_failed", "degraded": True,
                "reconciliation_required": True}
    _reload()
    return {"ok": True, "id": entity_id, "status": "verified"}


def _prepare_rejection(kb: dict, entity_id: str) -> dict:
    target = next((e for e in kb["entities"] if e["id"] == entity_id), None)
    if target is None:
        return {"error": "not_found"}
    if not _is_provisional(target):
        return {"error": "verified"}
    removed_target = copy.deepcopy(target)
    removed_relationships = [
        copy.deepcopy(r)
        for r in kb.get("relationships", [])
        if r.get("from") == entity_id or r.get("to") == entity_id
    ]
    kb["entities"] = [e for e in kb["entities"] if e["id"] != entity_id]
    kb["relationships"] = [
        r for r in kb.get("relationships", [])
        if r.get("from") != entity_id and r.get("to") != entity_id
    ]
    return {
        "before": len(kb["entities"]) + 1,
        "removed_target": removed_target,
        "removed_relationships": removed_relationships,
    }


def _rejection_db_failure(plan: dict, post_delete_snapshot: dict, post_delete_version: int) -> dict:
    rolled_back = _rollback_rejection(
        plan["removed_target"],
        plan["removed_relationships"],
        post_delete_snapshot,
        post_delete_version,
    )
    if rolled_back:
        return {"ok": False, "error": "db_write_failed"}
    return {"ok": False, "error": "db_write_failed", "reconciliation_required": True}


def reject(entity_id: str) -> dict:
    """Remove a provisional entity from the KB (rejected in review)."""
    kb, version = load_json_versioned(DATA_JSON)
    plan = _prepare_rejection(kb, entity_id)
    if plan.get("error") == "not_found":
        return {"ok": False, "error": "not found"}
    if plan.get("error") == "verified":
        return {"ok": False, "error": "refusing to delete a verified entity via reject"}
    if not compare_and_swap_json(DATA_JSON, version, kb):
        return {"ok": False, "error": "stale_review"}
    _, post_delete_version = load_json_versioned(DATA_JSON)
    post_delete_snapshot = copy.deepcopy(kb)
    try:
        _PROVISIONAL_AUDIT_CONTEXT[entity_id] = ("admin", "provisional_reject")
        db_result = _db_delete(entity_id)
        if db_result is False:
            raise RuntimeError("db_write_failed")
    except Exception:
        return _rejection_db_failure(plan, post_delete_snapshot, post_delete_version)
    if isinstance(db_result, dict) and db_result.get("committed"):
        _reload()
        return {"ok": False, "error": "db_write_failed", "degraded": True,
                "reconciliation_required": True}
    result = {"ok": True, "id": entity_id, "removed": plan["before"] - len(kb["entities"])}
    _reload()
    return result


_DEDUP_STOP = frozenset({
    "khu", "diem", "du", "lich", "quan", "nha", "vuon", "co", "cua",
    "vinh", "long", "ben", "tre", "tra", "the", "va", "tham",
    # Category words — must NOT count toward similarity, else "Công viên A" and
    # "Công viên B" (distinct places) get flagged as duplicates of each other.
    "cong", "vien", "lang", "nghe", "ong", "cho", "di", "tich", "luu", "niem",
    "con", "dinh", "chua", "den", "mieu", "bao", "tang", "cang",
})

_COMBINING_MARKS_RE = _re.compile(r"[\u0300-\u036f]")
_NON_ALNUM_RE = _re.compile(r"[^a-z0-9]+")


@lru_cache(maxsize=4096)
def _cached_name_tokens(name: str) -> frozenset[str]:
    s = _ud.normalize("NFD", (name or "").lower())
    s = _COMBINING_MARKS_RE.sub("", s).replace("đ", "d")
    return frozenset(t for t in _NON_ALNUM_RE.split(s) if len(t) >= 3 and t not in _DEDUP_STOP)


def _name_tokens(name: str) -> set:
    return set(_cached_name_tokens(name or ""))


# Site-like types: the same physical place is often labeled differently
# (e.g. "Văn Thánh Miếu" as attraction vs history) → cross-check these types.
_SITE_TYPES = frozenset({"history", "attraction", "nature"})


@lru_cache(maxsize=4096)
def _full_norm_name(name: str) -> str:
    s = _ud.normalize("NFD", (name or "").lower())
    s = _COMBINING_MARKS_RE.sub("", s).replace("đ", "d")
    return _NON_ALNUM_RE.sub(" ", s).strip()


# Sentinel distinguishing "no match" from "matched entity whose id is falsy".
_NO_DUP = object()


def _same_type_dup_id(cand_tokens: set | frozenset, e: dict):
    """Same-type near-duplicate check for one entity.

    Returns the entity id on match (mirrors ``e.get("id")`` verbatim), else
    the ``_NO_DUP`` sentinel (candidate looks distinct vs this entity).
    """
    ex_tokens = _cached_name_tokens(e.get("name", ""))
    if not ex_tokens:
        return _NO_DUP
    overlap = cand_tokens & ex_tokens
    if len(overlap) >= 2 or (overlap and len(overlap) == min(len(cand_tokens), len(ex_tokens))):
        return e.get("id")
    return _NO_DUP


def _cross_site_dup_id(cand_full: str, e: dict):
    """Cross site-type containment check for one entity.

    Returns the entity id on match (mirrors ``e.get("id")`` verbatim), else
    the ``_NO_DUP`` sentinel.
    """
    ex_full = _full_norm_name(e.get("name", ""))
    if not ex_full or len(min(cand_full, ex_full, key=len)) < 8:
        return _NO_DUP
    if cand_full in ex_full or ex_full in cand_full:
        return e.get("id")
    return _NO_DUP


def find_near_duplicate(candidate_name: str, candidate_type: str, entities: list) -> str | None:
    """Detect a likely near-duplicate / contradiction (offline, no LLM).

    Two checks:
      1. SAME type: >= 2 shared significant name tokens (or full containment of
         the smaller name's tokens).
      2. CROSS site-types ({history, attraction, nature}): one full normalized
         name contained in the other — catches the same physical place filed
         under a different type ("Văn Thánh Miếu" attraction vs
         "Văn Thánh Miếu Vĩnh Long" history) without false-flagging distinct
         places that merely share words.

    Returns the conflicting entity id, or None if the candidate looks novel.
    """
    cand_tokens = _name_tokens(candidate_name)
    if not cand_tokens:
        return None
    cand_full = _full_norm_name(candidate_name)
    cand_is_site = candidate_type in _SITE_TYPES

    for e in entities:
        etype = e.get("type")
        if etype == candidate_type:
            dup = _same_type_dup_id(cand_tokens, e)
            if dup is not _NO_DUP:
                return dup
        elif cand_is_site and etype in _SITE_TYPES:
            dup = _cross_site_dup_id(cand_full, e)
            if dup is not _NO_DUP:
                return dup
    return None


def _entity_hits() -> dict:
    try:
        data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
        return data.get("entity_hits", {}) or {}
    except Exception as exc:
        logger.debug("Failed to load entity hits: %s", exc)
        return {}


def _promotion_pairs(provisional: list[dict], hits: dict, min_hits: int):
    selected = [e for e in provisional if hits.get(e.get("id"), 0) >= min_hits]
    return [
        (original, {**copy.deepcopy(original), "status": "verified", "verified": True})
        for original in selected
    ]


def _apply_promotions(kb: dict, promoted_pairs, candidates: int) -> tuple[bool, dict]:
    entities = kb.get("entities", [])
    index_by_id = {str(entity.get("id")): (i, entity) for i, entity in enumerate(entities)}
    for original, _ in promoted_pairs:
        entry = index_by_id.get(str(original.get("id")))
        if entry is None or entry[1] != original:
            return False, {"candidates": candidates, "promoted": [], "error": "stale_review"}
    for original, promoted in promoted_pairs:
        idx = index_by_id[str(original.get("id"))][0]
        entities[idx] = copy.deepcopy(promoted)
    return bool(promoted_pairs), {
        "candidates": candidates,
        "promoted": [e["id"] for _, e in promoted_pairs],
    }


def _rollback_failed_promotions(promoted_pairs, persisted, degraded):
    reconciliation: list[str] = list(degraded)
    for previous, previous_promoted in persisted:
        if str(previous.get("id")) in degraded:
            continue
        try:
            restore_result = _db_upsert(previous)
            if not _db_compensation_succeeded(restore_result):
                reconciliation.append(str(previous.get("id")))
                continue
            if not _rollback_promotion(previous.get("id"), previous, previous_promoted):
                reconciliation.append(str(previous.get("id")))
        except Exception:
            logger.error("Auto-promotion compensation failed for %s", previous.get("id"))
            reconciliation.append(str(previous.get("id")))
    return reconciliation


def _persist_promotions(promoted_pairs, candidates):
    persisted: list[tuple[dict, dict]] = []
    degraded: list[str] = []
    for original, promoted in promoted_pairs:
        try:
            db_result = _db_upsert(promoted)
            if db_result is False:
                raise RuntimeError("db_write_failed")
            persisted.append((original, promoted))
            if isinstance(db_result, dict) and db_result.get("committed"):
                degraded.append(str(promoted.get("id")))
        except Exception:
            reconciliation = _rollback_failed_promotions(
                promoted_pairs, persisted, degraded
            )
            if str(promoted.get("id")) not in degraded:
                _rollback_promotion(promoted.get("id"), original, promoted)
            retained = [
                str(entity.get("id"))
                for _, entity in promoted_pairs
                if str(entity.get("id")) in reconciliation
            ]
            response = {"candidates": candidates, "promoted": retained, "error": "db_write_failed"}
            if reconciliation:
                response["degraded"] = True
                response["reconciliation_required"] = retained
            return response, None
    return None, degraded


def auto_promote_pass(min_hits: int = 3, dry_run: bool = False) -> dict:
    """Promote provisional entities that have PROVEN useful in real queries.

    Criterion: the entity has been retrieved/hit >= min_hits times (signal that
    users actually reach it) — a lightweight, gameable-but-bounded usefulness
    proxy. Designed to be run inside guarded_evolve() so the whole promotion
    batch is rolled back if it regresses fitness.

    Returns {candidates, promoted: [ids]}.
    """
    hits = _entity_hits()
    source = _load_kb()
    provisional = [e for e in source.get("entities", []) if _is_provisional(e)]
    candidates = len(provisional)
    promoted_pairs = [
        (copy.deepcopy(original), {**copy.deepcopy(original), "status": "verified", "verified": True})
        for original in provisional
        if hits.get(original.get("id"), 0) >= min_hits
    ]
    if dry_run:
        return {"candidates": candidates, "promoted": [e["id"] for _, e in promoted_pairs]}

    result = mutate_json(DATA_JSON, lambda kb: _apply_promotions(kb, promoted_pairs, candidates))
    if result.get("error") or not promoted_pairs:
        return result

    persist_error, degraded = _persist_promotions(promoted_pairs, candidates)
    if persist_error is not None:
        return persist_error
    _reload()
    if degraded:
        result["degraded"] = True
        result["reconciliation_required"] = degraded
    return result


def stats() -> dict:
    kb = _load_kb()
    entities = kb.get("entities", [])
    return {
        "provisional_count": sum(1 for e in entities if _is_provisional(e)),
        "total_entities": len(entities),
    }


def normalize_curation_summary(summary: object) -> dict[str, int]:
    """Return the canonical provisional queue count; legacy ``pending`` is rejected."""
    if not isinstance(summary, dict):
        return {"provisional_count": 0}
    count = summary.get("provisional_count")
    # Do not silently treat the unrelated moderation word ``pending`` as this queue.
    if type(count) is not int or count < 0:
        count = 0
    return {"provisional_count": count}
