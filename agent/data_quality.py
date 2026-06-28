"""Data quality helpers for GPT candidate review and public trust signals."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from database import db

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "web" / "data.json"
DATA_JS_PATH = ROOT / "web" / "data.js"
BACKUP_DIR = ROOT / "agent" / "data" / "kb_snapshots"
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
            rows.append(item)
    rows.sort(key=lambda r: (r.get("bucket") != "auto_apply", r.get("kind", ""), r.get("entity_id", "")))
    offset = max(int(offset or 0), 0)
    limit = max(1, min(int(limit or 100), 500))
    return {"total": len(rows), "offset": offset, "limit": limit, "candidates": rows[offset:offset + limit]}

def _write_data_files(data: dict[str, Any]) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"data_quality_apply_{stamp}.json"
    shutil.copy2(DATA_PATH, backup)
    _write_data_without_backup(data)
    return str(backup)

def _write_data_without_backup(data: dict[str, Any]) -> None:
    tmp = DATA_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    tmp.replace(DATA_PATH)

    spec = importlib.util.spec_from_file_location("normalize_data", ROOT / "scripts" / "normalize_data.py")
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        tmp_js = DATA_JS_PATH.with_suffix(".tmp")
        tmp_js.write_text(module.render_data_js(data), encoding="utf-8", newline="\n")
        tmp_js.replace(DATA_JS_PATH)

def _apply_history_path(output_dir: Path | None = None) -> Path:
    output_dir = output_dir or BURST_DIR
    return output_dir / APPLY_HISTORY_FILE

def _append_apply_history(record: dict[str, Any], output_dir: Path | None = None) -> None:
    output_dir = output_dir or BURST_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    with _apply_history_path(output_dir).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

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

def is_evidence_auto_apply(record: dict[str, Any]) -> bool:
    if record.get("apply_policy") != "auto_apply":
        return False
    field = record.get("field")
    if field == "source":
        return bool(record.get("url_verified") and record.get("suggested_value") and any(is_valid_url(u) for u in record.get("evidence_urls") or []))
    if field == "coordinates":
        return bool(record.get("geocode_verified") and parse_coordinates(record.get("suggested_value")))
    return False

def apply_candidates(candidate_ids: list[str] | None = None, *, dry_run: bool = True) -> dict[str, Any]:
    queue = load_candidate_queue(refresh=True)
    wanted = set(candidate_ids or [])
    applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    batch_payload = f"{applied_at}:{','.join(sorted(wanted)) or 'all'}"
    batch_id = f"dq_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha1(batch_payload.encode('utf-8')).hexdigest()[:8]}"
    selected = []
    for record in queue.get("auto_apply", []):
        cid = record.get("candidate_id") or candidate_id(record)
        if wanted and cid not in wanted:
            continue
        if is_evidence_auto_apply(record):
            selected.append({**record, "candidate_id": cid})

    # GĐ3.8: nguồn = DB (nguồn sự thật), không còn đọc/ghi qua data.json.
    by_id = {str(e.get("id")): e for e in db.all_entities() if isinstance(e, dict) and e.get("id")}
    coordinate_owners: dict[tuple[float, float], str] = {}
    for entity_id, entity in by_id.items():
        key = _coordinate_key(entity.get("coordinates"))
        if key:
            coordinate_owners.setdefault(key, entity_id)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for record in selected:
        entity = by_id.get(str(record.get("entity_id")))
        if not entity:
            skipped.append({"candidate_id": record["candidate_id"], "reason": "entity not found"})
            continue
        field = str(record.get("field") or "")
        after = _candidate_after_value(record)
        if after is None:
            skipped.append({"candidate_id": record["candidate_id"], "reason": "invalid suggestion"})
            continue
        before = _current_field_value(entity, field)
        if _canonical_value(before) == _canonical_value(after):
            skipped.append({"candidate_id": record["candidate_id"], "entity_id": entity.get("id"), "field": field, "reason": "value already current"})
            continue
        if field == "coordinates":
            key = _coordinate_key(after)
            owner = coordinate_owners.get(key) if key else None
            if owner and owner != str(entity.get("id")):
                skipped.append({
                    "candidate_id": record["candidate_id"],
                    "entity_id": entity.get("id"),
                    "field": field,
                    "reason": "duplicate coordinates",
                    "duplicate_of": owner,
                    "coordinates": list(key) if key else None,
                })
                continue
            if key:
                coordinate_owners[key] = str(entity.get("id"))
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
        changes.append(change)
        applied.append({"candidate_id": record["candidate_id"], "entity_id": entity.get("id"), "field": field})

    backup = None
    if applied and not dry_run:
        # GĐ3.8: ghi THẲNG vào DB (chỉ entity thay đổi) — không DELETE-rồi-nạp-json,
        # nên KHÔNG xoá edit admin khác. Rollback dùng `before` trong history.
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
        "backup": backup,
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
