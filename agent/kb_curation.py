"""
vinhlong360 — KB Curation (Quarantine review & promotion).

Auto-learned entities enter the KB as `status: provisional, verified: false`
(see learn_loop.py). They are down-weighted in ranking and labeled
"chưa kiểm chứng" in answers. This module manages their lifecycle:

  - list_provisional()      : the review queue
  - promote(id)             : provisional → verified (trusted)
  - reject(id)              : remove a bad provisional entity
  - auto_promote_pass()     : eval-gated automatic promotion of provisional
                              entities that have PROVEN useful (queried/hit with
                              no negative feedback). This realizes the user's
                              "eval-gated autonomous" choice: knowledge that
                              survives real use and doesn't hurt fitness graduates
                              to verified automatically.

All writes go to web/data.json and trigger knowledge.reload().
"""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
DATA_JSON = PROJECT_DIR / "web" / "data.json"
ANALYTICS_FILE = AGENT_DIR / "data" / "analytics.json"


def _load_kb() -> dict:
    return json.loads(DATA_JSON.read_text(encoding="utf-8"))


def _save_kb(data: dict):
    tmp = DATA_JSON.with_suffix(".curation.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_JSON)


def _reload():
    try:
        import knowledge
        knowledge.reload()
    except Exception:
        pass


# GĐ-audit (B1): DB là nguồn sự thật cho chat (knowledge.reload đọc DB). Mọi mutate KB
# PHẢI ghi DB, không chỉ data.json (nếu chỉ data.json thì chat không thấy + bị export ghi đè).
def _db_upsert(entity: dict):
    try:
        from database import db
        db.upsert_entity(entity)
    except Exception as e:  # noqa: BLE001 - không để lỗi DB làm hỏng thao tác (data.json vẫn ghi)
        logger.warning("DB upsert failed for %s: %s", entity.get("id"), e)


def _db_delete(entity_id: str):
    try:
        from database import db
        db.delete_entity(entity_id)  # cascade xoá cả relationships + FTS
    except Exception as e:  # noqa: BLE001
        logger.warning("DB delete failed for %s: %s", entity_id, e)


def _is_provisional(e: dict) -> bool:
    return e.get("status") == "provisional" or e.get("verified") is False


def list_provisional() -> list:
    """Return all provisional (unverified, auto-learned) entities."""
    kb = _load_kb()
    return [
        {
            "id": e["id"], "name": e.get("name", ""), "type": e.get("type", ""),
            "summary": e.get("summary", "")[:160],
            "learned_at": e.get("learned_at", ""), "source": e.get("source", {}),
        }
        for e in kb.get("entities", []) if _is_provisional(e)
    ]


def promote(entity_id: str) -> dict:
    """Promote a provisional entity to verified (trusted)."""
    kb = _load_kb()
    for e in kb["entities"]:
        if e["id"] == entity_id:
            if not _is_provisional(e):
                return {"ok": False, "error": "already verified"}
            e["status"] = "verified"
            e["verified"] = True
            _save_kb(kb)
            _db_upsert(e)   # B1: ghi DB để chat thấy
            _reload()
            return {"ok": True, "id": entity_id, "status": "verified"}
    return {"ok": False, "error": "not found"}


def reject(entity_id: str) -> dict:
    """Remove a provisional entity from the KB (rejected in review)."""
    kb = _load_kb()
    before = len(kb["entities"])
    target = next((e for e in kb["entities"] if e["id"] == entity_id), None)
    if target is None:
        return {"ok": False, "error": "not found"}
    if not _is_provisional(target):
        return {"ok": False, "error": "refusing to delete a verified entity via reject"}
    kb["entities"] = [e for e in kb["entities"] if e["id"] != entity_id]
    # Also drop relationships referencing it
    kb["relationships"] = [
        r for r in kb.get("relationships", [])
        if r.get("from") != entity_id and r.get("to") != entity_id
    ]
    _save_kb(kb)
    _db_delete(entity_id)   # B1: xoá khỏi DB (cascade rels) để chat thấy
    _reload()
    return {"ok": True, "id": entity_id, "removed": before - len(kb["entities"])}


import re as _re
import unicodedata as _ud

_DEDUP_STOP = frozenset({
    "khu", "diem", "du", "lich", "quan", "nha", "vuon", "co", "cua",
    "vinh", "long", "ben", "tre", "tra", "the", "va", "tham",
    # Category words — must NOT count toward similarity, else "Công viên A" and
    # "Công viên B" (distinct places) get flagged as duplicates of each other.
    "cong", "vien", "lang", "nghe", "ong", "cho", "di", "tich", "luu", "niem",
    "con", "dinh", "chua", "den", "mieu", "bao", "tang", "cang",
})


def _name_tokens(name: str) -> set:
    s = _ud.normalize("NFD", (name or "").lower())
    s = _re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")
    return {t for t in _re.split(r"[^a-z0-9]+", s) if len(t) >= 3 and t not in _DEDUP_STOP}


# Site-like types: the same physical place is often labeled differently
# (e.g. "Văn Thánh Miếu" as attraction vs history) → cross-check these types.
_SITE_TYPES = frozenset({"history", "attraction", "nature"})


def _full_norm_name(name: str) -> str:
    s = _ud.normalize("NFD", (name or "").lower())
    s = _re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")
    return _re.sub(r"[^a-z0-9]+", " ", s).strip()


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
        ex_name = e.get("name", "")
        if etype == candidate_type:
            ex_tokens = _name_tokens(ex_name)
            if not ex_tokens:
                continue
            overlap = cand_tokens & ex_tokens
            if len(overlap) >= 2 or (overlap and overlap == min(cand_tokens, ex_tokens, key=len)):
                return e.get("id")
        elif cand_is_site and etype in _SITE_TYPES:
            ex_full = _full_norm_name(ex_name)
            if not ex_full or len(min(cand_full, ex_full, key=len)) < 8:
                continue
            if cand_full in ex_full or ex_full in cand_full:
                return e.get("id")
    return None


def _entity_hits() -> dict:
    try:
        data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
        return data.get("entity_hits", {}) or {}
    except Exception:
        return {}


def auto_promote_pass(min_hits: int = 3, dry_run: bool = False) -> dict:
    """Promote provisional entities that have PROVEN useful in real queries.

    Criterion: the entity has been retrieved/hit >= min_hits times (signal that
    users actually reach it) — a lightweight, gameable-but-bounded usefulness
    proxy. Designed to be run inside guarded_evolve() so the whole promotion
    batch is rolled back if it regresses fitness.

    Returns {candidates, promoted: [ids]}.
    """
    kb = _load_kb()
    hits = _entity_hits()
    promoted = []
    candidates = 0
    for e in kb["entities"]:
        if not _is_provisional(e):
            continue
        candidates += 1
        if hits.get(e["id"], 0) >= min_hits:
            if not dry_run:
                e["status"] = "verified"
                e["verified"] = True
                _db_upsert(e)
            promoted.append(e["id"])
    if promoted and not dry_run:
        _save_kb(kb)
        _reload()
    return {"candidates": candidates, "promoted": promoted}


def stats() -> dict:
    kb = _load_kb()
    provisional = [e for e in kb.get("entities", []) if _is_provisional(e)]
    return {
        "provisional_count": len(provisional),
        "total_entities": len(kb.get("entities", [])),
    }
