"""Data quality helpers for GPT candidate review and public trust signals."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from database import db

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "web" / "data.json"
BURST_DIR = ROOT / "agent" / "data" / "gpt55_quality_burst"

FIELD_KIND = {
    "source": "source",
    "coordinates": "location",
    "placeId": "placeid",
    "entity_accuracy": "accuracy",
    "relationship": "relationship",
}

QUEUE_FILE = "review_queue.json"
APPLY_HISTORY_FILE = "apply_history.jsonl"
DECISION_HISTORY_FILE = "review_decisions.jsonl"

def is_valid_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

def parse_coordinates(value: Any) -> list[float] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return None
    if isinstance(value, dict):
        value = [value.get("lat", value.get("latitude")), value.get("lng", value.get("lon", value.get("longitude")))]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat = float(value[0])
        lng = float(value[1])
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return [lat, lng]
    if -180 <= lat <= 180 and -90 <= lng <= 90:
        return [lng, lat]
    return None

def load_data(path: Path | None = None) -> dict[str, Any]:
    path = path or DATA_PATH
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    data.setdefault("entities", [])
    data.setdefault("relationships", [])
    data.setdefault("itineraries", [])
    return data

def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))

def _canonical_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _is_external_url(url: Any) -> bool:
    """Valid http(s) URL that is NOT our own site (self-citation is not a source)."""
    if not is_valid_url(url):
        return False
    u = str(url).lower()
    return ("//vinhlong360.vn" not in u) and ("//www.vinhlong360.vn" not in u)


def source_info(entity: dict[str, Any]) -> dict[str, Any]:
    source = entity.get("source")
    if isinstance(source, list):  # entities store source as a list of {title,url,maps}; use the first
        source = source[0] if source else None
    if isinstance(source, str):
        return {"title": source, "url": source if _is_external_url(source) else None}
    if isinstance(source, dict):
        url = source.get("url")
        return {
            "title": source.get("title") or source.get("name") or "",
            "url": str(url) if _is_external_url(url) else None,
        }
    return {"title": "", "url": None}

def entity_quality(entity: dict[str, Any]) -> dict[str, Any]:
    src = source_info(entity)
    has_source = bool(src.get("url"))
    has_location = parse_coordinates(entity.get("coordinates")) is not None
    has_place = bool(entity.get("placeId")) or entity.get("type") == "place"
    missing = []
    if not has_source:
        missing.append("source")
    if not has_location:
        missing.append("location")
    if not has_place:
        missing.append("placeId")
    score = round((sum([has_source, has_location, has_place]) / 3) * 100)
    return {
        "has_source": has_source,
        "has_location": has_location,
        "has_place": has_place,
        "source_title": src.get("title") or None,
        "source_url": src.get("url"),
        "missing": missing,
        "score": score,
    }

def summarize_data(data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or load_data()
    entities = [e for e in data.get("entities", []) if isinstance(e, dict)]
    non_place = [e for e in entities if e.get("type") != "place"]
    qualities = {str(e.get("id")): entity_quality(e) for e in entities if e.get("id")}
    return {
        "entities": len(entities),
        "public_entities": len(non_place),
        "relationships": len(data.get("relationships", [])),
        "itineraries": len(data.get("itineraries", [])),
        "missing_source": sum(1 for e in entities if not qualities.get(str(e.get("id")), {}).get("has_source")),
        "missing_location": sum(1 for e in entities if not qualities.get(str(e.get("id")), {}).get("has_location")),
        "missing_place_id_non_place": sum(1 for e in non_place if not e.get("placeId")),
        "entity_types": dict(Counter(str(e.get("type")) for e in entities).most_common()),
    }

def candidate_id(record: dict[str, Any]) -> str:
    payload = json.dumps({
        "entity_id": record.get("entity_id"),
        "field": record.get("field"),
        "suggested_value": record.get("suggested_value"),
        "stream": record.get("stream"),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

def merge_candidate_outputs(output_dir: Path = BURST_DIR) -> dict[str, Any]:
    import gpt55_quality_burst as burst

    manifest_path = output_dir / burst.MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.exists() else None
    usage_path = output_dir / burst.LLM_USAGE_FILE
    llm_stats = json.loads(usage_path.read_text(encoding="utf-8-sig")) if usage_path.exists() else None
    return burst.merge_outputs(output_dir, manifest=manifest, llm_stats=llm_stats)

def _queue_cache_meta(output_dir: Path = BURST_DIR) -> dict[str, Any]:
    queue_path = output_dir / QUEUE_FILE
    if not queue_path.exists():
        return {"path": str(queue_path), "exists": False}
    stat = queue_path.stat()
    return {
        "path": str(queue_path),
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }

def load_candidate_queue(output_dir: Path = BURST_DIR, *, refresh: bool = False) -> dict[str, Any]:
    queue_path = output_dir / QUEUE_FILE
    if refresh or not queue_path.exists():
        queue = merge_candidate_outputs(output_dir)
    else:
        queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    for bucket in ("auto_apply", "needs_review", "reject"):
        for record in queue.get(bucket, []):
            record.setdefault("candidate_id", candidate_id(record))
            record.setdefault("kind", FIELD_KIND.get(str(record.get("field")), str(record.get("field") or "unknown")))
    queue.setdefault("cache", _queue_cache_meta(output_dir))
    return queue

def filter_candidates(queue: dict[str, Any], *, kind: str | None = None, bucket: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    buckets = [bucket] if bucket in {"auto_apply", "needs_review", "reject"} else ["auto_apply", "needs_review", "reject"]
    decisions = latest_candidate_decisions()
    rows: list[dict[str, Any]] = []
    for name in buckets:
        for record in queue.get(name, []):
            row_kind = FIELD_KIND.get(str(record.get("field")), str(record.get("field") or "unknown"))
            if kind and row_kind != kind:
                continue
            item = dict(record)
            item["bucket"] = name
            item.setdefault("kind", row_kind)
            item.setdefault("candidate_id", candidate_id(item))
            decision = decisions.get(str(item["candidate_id"]))
            if decision:
                item["decision"] = decision.get("decision")
                item["decision_note"] = decision.get("note")
                item["decision_at"] = decision.get("decided_at")
                item["decision_by"] = decision.get("reviewer")
            rows.append(item)
    rows.sort(key=lambda r: (r.get("bucket") != "auto_apply", r.get("kind", ""), r.get("entity_id", "")))
    offset = max(int(offset or 0), 0)
    limit = max(1, min(int(limit or 100), 500))
    return {"total": len(rows), "offset": offset, "limit": limit, "candidates": rows[offset:offset + limit]}


def _apply_history_path(output_dir: Path | None = None) -> Path:
    output_dir = output_dir or BURST_DIR
    return output_dir / APPLY_HISTORY_FILE

def _append_apply_history(record: dict[str, Any], output_dir: Path | None = None) -> None:
    output_dir = output_dir or BURST_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    with _apply_history_path(output_dir).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

def _decision_history_path(output_dir: Path | None = None) -> Path:
    output_dir = output_dir or BURST_DIR
    return output_dir / DECISION_HISTORY_FILE

def _append_decision_history(record: dict[str, Any], output_dir: Path | None = None) -> None:
    output_dir = output_dir or BURST_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    with _decision_history_path(output_dir).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

def load_decision_history(limit: int = 100, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or BURST_DIR
    path = _decision_history_path(output_dir)
    if not path.exists():
        return {"total": 0, "decisions": []}
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"record_type": "parse_error", "raw": line[:500]})
    rows.reverse()
    limit = max(1, min(int(limit or 100), 500))
    return {"total": len(rows), "decisions": rows[:limit]}

def latest_candidate_decisions(output_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    decisions = load_decision_history(limit=500, output_dir=output_dir).get("decisions", [])
    latest: dict[str, dict[str, Any]] = {}
    for row in decisions:
        for cid in row.get("candidate_ids") or []:
            latest.setdefault(str(cid), row)
    return latest

def load_apply_history(limit: int = 50, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or BURST_DIR
    path = _apply_history_path(output_dir)
    if not path.exists():
        return {"total": 0, "history": []}
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"record_type": "parse_error", "raw": line[:500]})
    rows.reverse()
    limit = max(1, min(int(limit or 50), 200))
    return {"total": len(rows), "history": rows[:limit]}

def _candidate_after_value(record: dict[str, Any]) -> Any:
    field = record.get("field")
    if field == "source":
        source = record.get("suggested_value")
        if isinstance(source, dict) and is_valid_url(source.get("url")):
            return {"title": source.get("title") or source.get("url"), "url": source.get("url")}
    if field == "coordinates":
        return parse_coordinates(record.get("suggested_value"))
    return None

def _current_field_value(entity: dict[str, Any], field: str) -> Any:
    if field == "source":
        return entity.get("source")
    if field == "coordinates":
        return parse_coordinates(entity.get("coordinates")) or entity.get("coordinates")
    return entity.get(field)

def _set_entity_field(entity: dict[str, Any], field: str, value: Any) -> None:
    if field == "source":
        entity["source"] = value
    elif field == "coordinates":
        entity["coordinates"] = value
    else:
        entity[field] = value

def _coordinate_key(value: Any) -> tuple[float, float] | None:
    coords = parse_coordinates(value)
    if not coords:
        return None
    return (round(coords[0], 7), round(coords[1], 7))

def _coordinate_owner_map(by_id: dict[str, dict[str, Any]]) -> dict[tuple[float, float], str]:
    """First-writer-wins owner of each rounded coordinate key across all entities."""
    coordinate_owners: dict[tuple[float, float], str] = {}
    for entity_id, entity in by_id.items():
        key = _coordinate_key(entity.get("coordinates"))
        if key:
            coordinate_owners.setdefault(key, entity_id)
    return coordinate_owners

def _duplicate_coord_owner(
    key: tuple[float, float] | None,
    entity: dict[str, Any],
    coordinate_owners: dict[tuple[float, float], str],
) -> str | None:
    """Return the id of a different entity that already owns `key`, else None."""
    owner = coordinate_owners.get(key) if key else None
    if owner and owner != str(entity.get("id")):
        return owner
    return None

def _coordinate_dup_skip(
    record: dict[str, Any],
    entity: dict[str, Any],
    after: Any,
    coordinate_owners: dict[tuple[float, float], str],
) -> dict[str, Any] | None:
    """Claim `after`'s coord for `entity`, or return a duplicate-coordinates skip dict."""
    key = _coordinate_key(after)
    owner = _duplicate_coord_owner(key, entity, coordinate_owners)
    if owner:
        return {
            "candidate_id": record["candidate_id"],
            "entity_id": entity.get("id"),
            "field": "coordinates",
            "reason": "duplicate coordinates",
            "duplicate_of": owner,
            "coordinates": list(key) if key else None,
        }
    if key:
        coordinate_owners[key] = str(entity.get("id"))
    return None

def _process_candidate_change(
    record: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    coordinate_owners: dict[tuple[float, float], str],
    *,
    dry_run: bool,
    reviewer: str | None,
    entity_id_on_invalid: bool,
    include_review_fields: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Apply one candidate against `by_id`; return (applied, change, skip).

    Exactly one of the three is non-None. Behaviour matches the inline loop bodies
    of apply_candidates / _apply_reviewed_records; `entity_id_on_invalid` and
    `include_review_fields` parametrise the two call sites' differences.
    """
    entity = by_id.get(str(record.get("entity_id")))
    if not entity:
        return None, None, {"candidate_id": record["candidate_id"], "reason": "entity not found"}
    field = str(record.get("field") or "")
    after = _candidate_after_value(record)
    if after is None:
        skip = {"candidate_id": record["candidate_id"], "reason": "invalid suggestion"}
        if entity_id_on_invalid:
            skip = {"candidate_id": record["candidate_id"], "entity_id": entity.get("id"),
                    "field": field, "reason": "invalid suggestion"}
        return None, None, skip
    before = _current_field_value(entity, field)
    if _canonical_value(before) == _canonical_value(after):
        return None, None, {"candidate_id": record["candidate_id"], "entity_id": entity.get("id"),
                            "field": field, "reason": "value already current"}
    if field == "coordinates":
        dup_skip = _coordinate_dup_skip(record, entity, after, coordinate_owners)
        if dup_skip is not None:
            return None, None, dup_skip
    if not dry_run:
        _set_entity_field(entity, field, after)
    change = {
        "candidate_id": record["candidate_id"],
        "entity_id": entity.get("id"),
        "entity_name": entity.get("name"),
        "field": field,
        "before": _json_clone(before),
        "after": _json_clone(after),
        "evidence_urls": record.get("evidence_urls") or [],
        "reason": record.get("reason"),
    }
    if include_review_fields:
        change["reviewer"] = reviewer
        change["review_bucket"] = record.get("bucket")
    applied = {"candidate_id": record["candidate_id"], "entity_id": entity.get("id"), "field": field}
    return applied, change, None

def is_evidence_auto_apply(record: dict[str, Any]) -> bool:
    if record.get("apply_policy") != "auto_apply":
        return False
    field = record.get("field")
    if field == "source":
        return bool(record.get("url_verified") and record.get("suggested_value") and any(is_valid_url(u) for u in record.get("evidence_urls") or []))
    if field == "coordinates":
        return bool(record.get("geocode_verified") and parse_coordinates(record.get("suggested_value")))
    return False

def _selected_auto_apply(queue: dict[str, Any], wanted: set[str]) -> list[dict[str, Any]]:
    """Evidence-backed auto-apply records, filtered by `wanted` candidate ids (empty = all)."""
    selected = []
    for record in queue.get("auto_apply", []):
        cid = record.get("candidate_id") or candidate_id(record)
        if wanted and cid not in wanted:
            continue
        if is_evidence_auto_apply(record):
            selected.append({**record, "candidate_id": cid})
    return selected

def _persist_applied_changes(
    *,
    batch_id: str,
    applied_at: str,
    applied: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Record the apply-history entry and upsert changed entities; return upsert errors."""
    errors: list[dict[str, Any]] = []
    _append_apply_history({
        "record_type": "apply",
        "batch_id": batch_id,
        "applied_at": applied_at,
        "backend": "db",
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "changes": changes,
        "skipped": skipped,
    })
    changed_ids = {str(c["entity_id"]) for c in changes}
    for eid in changed_ids:
        entity = by_id.get(eid)
        if entity:
            try:
                db.upsert_entity(entity)
            except Exception as exc:
                errors.append({"entity_id": eid, "error": str(exc)})
    return errors

def apply_candidates(candidate_ids: list[str] | None = None, *, dry_run: bool = True) -> dict[str, Any]:
    queue = load_candidate_queue(refresh=True)
    wanted = set(candidate_ids or [])
    applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    batch_payload = f"{applied_at}:{','.join(sorted(wanted)) or 'all'}"
    batch_id = f"dq_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha1(batch_payload.encode('utf-8')).hexdigest()[:8]}"
    selected = _selected_auto_apply(queue, wanted)

    # GĐ3.8: nguồn = DB (nguồn sự thật), không còn đọc/ghi qua data.json.
    by_id = {str(e.get("id")): e for e in db.all_entities() if isinstance(e, dict) and e.get("id")}
    coordinate_owners = _coordinate_owner_map(by_id)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for record in selected:
        applied_entry, change, skip = _process_candidate_change(
            record, by_id, coordinate_owners,
            dry_run=dry_run, reviewer=None,
            entity_id_on_invalid=False, include_review_fields=False,
        )
        if skip is not None:
            skipped.append(skip)
            continue
        changes.append(change)
        applied.append(applied_entry)

    errors: list[dict[str, Any]] = []
    if applied and not dry_run:
        errors = _persist_applied_changes(
            batch_id=batch_id, applied_at=applied_at,
            applied=applied, skipped=skipped, changes=changes, by_id=by_id,
        )
    return {
        "dry_run": dry_run,
        "batch_id": batch_id,
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
        "changes": changes,
        "errors": errors,
    }

def _all_candidate_rows(queue: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bucket in ("auto_apply", "needs_review", "reject"):
        for record in queue.get(bucket, []):
            item = dict(record)
            item["bucket"] = bucket
            item.setdefault("candidate_id", candidate_id(item))
            item.setdefault("kind", FIELD_KIND.get(str(item.get("field")), str(item.get("field") or "unknown")))
            rows.append(item)
    return rows

def _apply_reviewed_records(
    selected: list[dict[str, Any]],
    *,
    reviewer: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seed = ",".join(sorted(str(r.get("candidate_id") or candidate_id(r)) for r in selected))
    batch_id = f"dq_review_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:8]}"

    by_id = {str(e.get("id")): e for e in db.all_entities() if isinstance(e, dict) and e.get("id")}
    coordinate_owners = _coordinate_owner_map(by_id)

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for raw in selected:
        record = dict(raw)
        record.setdefault("candidate_id", candidate_id(record))
        applied_entry, change, skip = _process_candidate_change(
            record, by_id, coordinate_owners,
            dry_run=dry_run, reviewer=reviewer,
            entity_id_on_invalid=True, include_review_fields=True,
        )
        if skip is not None:
            skipped.append(skip)
            continue
        changes.append(change)
        applied.append(applied_entry)

    if applied and not dry_run:
        changed_ids = {str(c["entity_id"]) for c in changes}
        for eid in changed_ids:
            entity = by_id.get(eid)
            if entity:
                db.upsert_entity(entity)
        _append_apply_history({
            "record_type": "apply",
            "batch_id": batch_id,
            "applied_at": applied_at,
            "backend": "db",
            "source": "review_decision",
            "reviewer": reviewer,
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "changes": changes,
            "skipped": skipped,
        })
    return {
        "dry_run": dry_run,
        "batch_id": batch_id,
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
        "changes": changes,
    }

def _resolve_candidate_records(
    ids: list[str], queue: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Split requested candidate ids into (found records, missing ids), preserving order."""
    by_id = {str(r.get("candidate_id") or candidate_id(r)): r for r in _all_candidate_rows(queue)}
    selected = []
    missing = []
    for cid in ids:
        record = by_id.get(cid)
        if record:
            selected.append(record)
        else:
            missing.append(cid)
    return selected, missing

def decide_candidates(
    candidate_ids: list[str],
    *,
    decision: str,
    note: str = "",
    reviewer: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    decision = (decision or "").strip().lower()
    if decision not in {"approve", "reject", "defer"}:
        raise ValueError("decision must be approve, reject, or defer")
    ids = [str(cid).strip() for cid in candidate_ids or [] if str(cid).strip()]
    if not ids:
        raise ValueError("candidate_ids is required")
    queue = load_candidate_queue(refresh=False)
    selected, missing = _resolve_candidate_records(ids, queue)

    decided_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    batch_id = f"dq_decision_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha1((','.join(ids) + decision).encode('utf-8')).hexdigest()[:8]}"
    decision_record = {
        "record_type": "decision",
        "batch_id": batch_id,
        "candidate_ids": [str(r.get("candidate_id")) for r in selected],
        "missing_candidate_ids": missing,
        "decision": decision,
        "note": note.strip(),
        "reviewer": reviewer,
        "decided_at": decided_at,
        "apply": bool(apply and decision == "approve"),
    }
    _append_decision_history(decision_record)
    apply_result = None
    if decision == "approve" and apply and selected:
        apply_result = _apply_reviewed_records(selected, reviewer=reviewer, dry_run=False)
    return {
        "success": True,
        "batch_id": batch_id,
        "decision": decision,
        "decided": len(selected),
        "missing": missing,
        "apply_result": apply_result,
    }

def rollback_apply(batch_id: str, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or BURST_DIR
    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id is required")
    history = load_apply_history(limit=200, output_dir=output_dir).get("history", [])
    target = next((row for row in history if row.get("record_type") == "apply" and row.get("batch_id") == batch_id), None)
    if not target:
        raise FileNotFoundError(f"apply batch '{batch_id}' not found")
    # GĐ3.8: rollback DB-native — đặt lại từng field về `before` đã lưu trong history.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    reverted = 0
    for change in target.get("changes") or []:
        eid = str(change.get("entity_id") or "")
        entity = db.get_entity(eid)
        if not entity:
            continue
        _set_entity_field(entity, str(change.get("field") or ""), change.get("before"))
        db.upsert_entity(entity)
        reverted += 1

    rolled_back_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _append_apply_history({
        "record_type": "rollback",
        "batch_id": f"rollback_{batch_id}_{stamp}",
        "rollback_of": batch_id,
        "rolled_back_at": rolled_back_at,
        "backend": "db",
        "restored_changes": reverted,
    }, output_dir=output_dir)
    return {
        "status": "rolled_back",
        "rollback_of": batch_id,
        "restored_changes": reverted,
    }
