#!/usr/bin/env python3
"""Parallel GPT-5.5 quality burst for vinhlong360.

Report-first workflow: build a shard manifest, run report-only streams, merge
candidate artifacts into a review queue, and never mutate web/data.json from
the audit streams.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
DATA_PATH = PROJECT_DIR / "web" / "data.json"
OUTPUT_DIR = AGENT_DIR / "data" / "gpt55_quality_burst"

sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except Exception:
    pass

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

try:
    import requests
except Exception:
    requests = None  # type: ignore[assignment]

try:
    import geocode as geo
except Exception:
    geo = None  # type: ignore[assignment]

STREAMS = ("source", "placeid", "location", "accuracy", "relationship", "eval")
STREAM_FILES = {
    "source": "source_candidates.jsonl",
    "placeid": "placeid_candidates.jsonl",
    "location": "location_candidates.jsonl",
    "accuracy": "entity_accuracy_audit.jsonl",
    "relationship": "relationship_audit.jsonl",
}
EVAL_FILE = "eval_cases.generated.json"
MANIFEST_FILE = "manifest.json"
REVIEW_QUEUE_FILE = "review_queue.json"
SUMMARY_FILE = "summary_report.md"
MERGED_CANDIDATES_FILE = "merged_candidates.json"
AUTO_APPLY_FILE = "auto_apply.json"
REJECT_FILE = "reject.json"
DATA_QUALITY_SUMMARY_FILE = "data_quality_summary.md"
LLM_USAGE_FILE = "llm_usage.json"

APPLY_POLICIES = {"auto_apply", "needs_review", "reject"}
AREAS = ("vinh-long", "ben-tre", "tra-vinh")
AREA_LABELS = {"vinh-long": "Vinh Long", "ben-tre": "Ben Tre", "tra-vinh": "Tra Vinh"}
PLACE_TYPE = "place"
DEFAULT_MODEL = os.environ.get("LLM_MODEL") or "cx/gpt-5.5"
MAX_NEAR_DISTANCE_KM = 50.0
REQUIRED_CANDIDATE_FIELDS = (
    "entity_id", "field", "current_value", "suggested_value", "confidence",
    "evidence_urls", "reason", "apply_policy",
)


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_data(path: Path = DATA_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    data.setdefault("entities", [])
    data.setdefault("relationships", [])
    data.setdefault("itineraries", [])
    return data


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def norm_text(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value: Any, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip()


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError:
        return str(value)


def chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    size = max(1, size)
    for index in range(0, len(items), size):
        yield items[index:index + size]


def limit_items(items: list[Any], limit: int | None) -> list[Any]:
    if limit is None or limit < 0:
        return items
    return items[:limit]


def is_valid_http_url(url: Any) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def url_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []



def as_confidence(value: Any, default: float = 0.0) -> float:
    if isinstance(value, str):
        label = value.strip().lower()
        mapped = {"very high": 0.95, "high": 0.90, "medium": 0.75, "low": 0.50, "none": 0.0}
        if label in mapped:
            return mapped[label]
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default

def entity_source_url(entity: dict[str, Any]) -> str | None:
    source = entity.get("source")
    if isinstance(source, dict):
        url = source.get("url")
        return str(url) if url else None
    if isinstance(source, str) and is_valid_http_url(source):
        return source
    return None


def entity_address(entity: dict[str, Any]) -> str:
    attrs = entity.get("attributes")
    if isinstance(attrs, dict):
        for key in ("address", "location", "dia_chi"):
            if attrs.get(key):
                return str(attrs[key])
    return str(entity.get("address") or entity.get("location") or "")


def parse_coordinates(value: Any) -> list[float] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value.strip())
        except Exception:
            return None
    if isinstance(value, dict):
        value = [value.get("lat", value.get("latitude")), value.get("lng", value.get("lon", value.get("longitude")))]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat, lon = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return [lat, lon]
    if -180 <= lat <= 180 and -90 <= lon <= 90:
        return [lon, lat]
    return None


def entity_coordinates(entity: dict[str, Any]) -> list[float] | None:
    return parse_coordinates(entity.get("coordinates"))


def classify_apply_policy(
    confidence: float,
    evidence_urls: Iterable[str] | None = None,
    *,
    conflict: bool = False,
    verified: bool = False,
    requires_url: bool = False,
) -> str:
    urls = list(evidence_urls or [])
    has_valid_url = any(is_valid_http_url(url) for url in urls)
    if conflict or confidence < 0.70:
        return "reject"
    if confidence >= 0.90 and verified and (not requires_url or has_valid_url):
        return "auto_apply"
    return "needs_review"


def validate_candidate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_CANDIDATE_FIELDS:
        if field not in record:
            errors.append(f"missing field: {field}")
    if not isinstance(record.get("entity_id"), str) or not record.get("entity_id"):
        errors.append("entity_id must be a non-empty string")
    if not isinstance(record.get("field"), str) or not record.get("field"):
        errors.append("field must be a non-empty string")
    try:
        confidence = float(record.get("confidence"))
    except (TypeError, ValueError):
        errors.append("confidence must be numeric")
    else:
        if confidence < 0 or confidence > 1:
            errors.append("confidence must be between 0 and 1")
    evidence_urls = record.get("evidence_urls")
    if not isinstance(evidence_urls, list):
        errors.append("evidence_urls must be a list")
    elif any(not is_valid_http_url(url) for url in evidence_urls):
        errors.append("evidence_urls contains invalid URL")
    if record.get("apply_policy") not in APPLY_POLICIES:
        errors.append("apply_policy must be auto_apply, needs_review, or reject")
    if record.get("apply_policy") == "auto_apply" and record.get("field") == "source":
        if not any(is_valid_http_url(url) for url in record.get("evidence_urls") or []):
            errors.append("auto-apply source candidates require a valid evidence URL")
    return errors


def make_candidate_record(
    *,
    entity_id: str,
    field: str,
    current_value: Any,
    suggested_value: Any,
    confidence: float,
    evidence_urls: Iterable[str] | None,
    reason: str,
    apply_policy: str,
    stream: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "entity_id": str(entity_id or ""),
        "field": field,
        "current_value": current_value,
        "suggested_value": suggested_value,
        "confidence": max(0.0, min(1.0, float(confidence or 0.0))),
        "evidence_urls": url_list(list(evidence_urls or [])),
        "reason": compact_text(reason, 900),
        "apply_policy": apply_policy if apply_policy in APPLY_POLICIES else "reject",
        "stream": stream,
        "generated_at": utc_now(),
    }
    if extra:
        record.update(extra)
    errors = validate_candidate_record(record)
    if errors:
        record["schema_errors"] = errors
        record["apply_policy"] = "reject"
    return record


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            text = line.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                value = make_candidate_record(
                    entity_id=f"__parse_error__:{path.name}:{line_no}",
                    field="artifact_parse_error",
                    current_value=None,
                    suggested_value=None,
                    confidence=0.0,
                    evidence_urls=[],
                    reason=f"Invalid JSONL line: {exc}",
                    apply_policy="reject",
                    stream="merge",
                )
            if isinstance(value, dict):
                records.append(value)
    return records


@dataclass
class BurstConfig:
    data_path: Path
    output_dir: Path
    model: str = DEFAULT_MODEL
    streams: tuple[str, ...] = STREAMS
    workers: int = 6
    item_workers: int = 2
    chunk_size: int = 25
    relationship_chunk_size: int = 50
    limit: int | None = None
    no_llm: bool = False
    no_web: bool = False
    no_geocode: bool = False


class JsonLLMClient:
    def __init__(self, model: str, no_llm: bool = False) -> None:
        self.model = model
        self.no_llm = no_llm
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.base_url = os.environ.get("LLM_BASE_URL", "")
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    @property
    def available(self) -> bool:
        return not self.no_llm and bool(self.api_key and self.base_url and OpenAI)

    def complete_json(self, *, system: str, payload: dict[str, Any], timeout: int = 90, max_tokens: int = 1500) -> Any:
        if not self.available:
            return None
        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)  # type: ignore[misc]
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            self.calls += 1
            usage = getattr(response, "usage", None)
            if usage:
                self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
            return parse_llm_json(response.choices[0].message.content or "")
        except Exception as exc:
            return {"_error": str(exc)}

    def stats(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "model": self.model,
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


def parse_llm_json(text: str) -> Any:
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def run_parallel(items: list[Any], worker_count: int, fn: Callable[[Any], Any]) -> list[Any]:
    if not items:
        return []
    if worker_count <= 1:
        return [fn(item) for item in items]
    out: list[Any] = []
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(fn, item) for item in items]
        for future in as_completed(futures):
            out.append(future.result())
    return out


def entity_stub(entity: dict[str, Any], *, include_source: bool = True) -> dict[str, Any]:
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    stub: dict[str, Any] = {
        "id": entity.get("id"),
        "name": entity.get("name"),
        "type": entity.get("type"),
        "area": entity.get("area"),
        "placeId": entity.get("placeId"),
        "address": entity_address(entity),
        "summary": compact_text(entity.get("summary"), 420),
        "coordinates": entity_coordinates(entity),
        "attributes_keys": sorted(attrs.keys())[:12] if attrs else [],
    }
    if include_source:
        stub["source"] = entity.get("source")
    return stub


def source_missing_targets(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    non_place = [e for e in entities if e.get("type") != PLACE_TYPE and not e.get("source")]
    places = [e for e in entities if e.get("type") == PLACE_TYPE and not e.get("source")]
    return sorted(non_place, key=lambda e: str(e.get("id"))) + sorted(places, key=lambda e: str(e.get("id")))


def placeid_targets(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [e for e in entities if e.get("type") != PLACE_TYPE and not e.get("placeId")],
        key=lambda e: (str(e.get("area") or ""), str(e.get("type") or ""), str(e.get("id") or "")),
    )


def location_targets(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [e for e in entities if entity_coordinates(e) is None],
        key=lambda e: (str(e.get("area") or ""), str(e.get("type") or ""), str(e.get("id") or "")),
    )


def relationship_source(rel: dict[str, Any]) -> str | None:
    value = rel.get("source_id") or rel.get("from_id") or rel.get("from")
    return str(value) if value else None


def relationship_target(rel: dict[str, Any]) -> str | None:
    value = rel.get("target_id") or rel.get("to_id") or rel.get("to")
    return str(value) if value else None


def relationship_type(rel: dict[str, Any]) -> str | None:
    value = rel.get("rel_type") or rel.get("type")
    return str(value) if value else None


def haversine_km(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b:
        return None
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    val = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(val))


def relationship_targets(data: dict[str, Any]) -> list[dict[str, Any]]:
    entities = {str(e.get("id")): e for e in data.get("entities", []) if isinstance(e, dict) and e.get("id")}
    targets: list[dict[str, Any]] = []
    for index, rel in enumerate(data.get("relationships", [])):
        if not isinstance(rel, dict):
            continue
        src = relationship_source(rel)
        dst = relationship_target(rel)
        rel_kind = relationship_type(rel)
        src_entity = entities.get(src or "")
        dst_entity = entities.get(dst or "")
        src_coords = entity_coordinates(src_entity or {})
        dst_coords = entity_coordinates(dst_entity or {})
        distance = haversine_km(src_coords, dst_coords)
        reasons: list[str] = []
        include = rel_kind != "near"
        if not src or not dst or not rel_kind:
            include = True
            reasons.append("missing relationship source, target, or type")
        if src and src_entity is None:
            include = True
            reasons.append("missing source entity")
        if dst and dst_entity is None:
            include = True
            reasons.append("missing target entity")
        if rel_kind == "near":
            if src_coords is None or dst_coords is None:
                include = True
                reasons.append("near edge has missing endpoint coordinates")
            elif distance is not None and distance > MAX_NEAR_DISTANCE_KM:
                include = True
                reasons.append(f"near edge distance is {distance:.1f} km")
        if include:
            targets.append(
                {
                    "index": index,
                    "source_id": src,
                    "target_id": dst,
                    "rel_type": rel_kind,
                    "source_name": (src_entity or {}).get("name"),
                    "target_name": (dst_entity or {}).get("name"),
                    "source_area": (src_entity or {}).get("area"),
                    "target_area": (dst_entity or {}).get("area"),
                    "distance_km": round(distance, 2) if distance is not None else None,
                    "heuristic_reasons": reasons,
                    "relationship": rel,
                }
            )
    return targets


def build_manifest(data: dict[str, Any], *, chunk_size: int = 25, relationship_chunk_size: int = 50) -> dict[str, Any]:
    entities = [e for e in data.get("entities", []) if isinstance(e, dict)]
    relationships = [r for r in data.get("relationships", []) if isinstance(r, dict)]
    source_targets = source_missing_targets(entities)
    place_targets = placeid_targets(entities)
    geo_targets = location_targets(entities)
    rel_targets = relationship_targets(data)
    shards: dict[str, list[dict[str, Any]]] = {stream: [] for stream in STREAMS}

    def add_entity_shards(stream: str, targets: list[dict[str, Any]], priority: str = "default") -> None:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for entity in targets:
            grouped[(str(entity.get("type") or "unknown"), str(entity.get("area") or "unknown"))].append(entity)
        seq = len(shards[stream])
        for (entity_type, area), group in sorted(grouped.items()):
            for batch in chunks(group, chunk_size):
                shards[stream].append(
                    {
                        "id": f"{stream}-{priority}-{seq:04d}",
                        "stream": stream,
                        "priority": priority,
                        "entity_type": entity_type,
                        "area": area,
                        "count": len(batch),
                        "entity_ids": [str(e.get("id")) for e in batch],
                    }
                )
                seq += 1

    non_place_source = [e for e in source_targets if e.get("type") != PLACE_TYPE]
    place_source = [e for e in source_targets if e.get("type") == PLACE_TYPE]
    add_entity_shards("source", non_place_source, priority="non_place_first")
    add_entity_shards("source", place_source, priority="place_second")
    add_entity_shards("placeid", place_targets)
    add_entity_shards("location", geo_targets)
    add_entity_shards("accuracy", entities)

    rel_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in rel_targets:
        rel_grouped[str(target.get("rel_type") or "unknown")].append(target)
    seq = 0
    for rel_kind, group in sorted(rel_grouped.items()):
        for batch in chunks(group, relationship_chunk_size):
            shards["relationship"].append(
                {
                    "id": f"relationship-{seq:04d}",
                    "stream": "relationship",
                    "rel_type": rel_kind,
                    "count": len(batch),
                    "relationship_indices": [item["index"] for item in batch],
                }
            )
            seq += 1

    shards["eval"].append(
        {
            "id": "eval-0000",
            "stream": "eval",
            "topics": ["tourism", "ocop", "accommodation", "khmer_culture", "itinerary"],
            "case_target": 30,
        }
    )
    return {
        "generated_at": utc_now(),
        "data_path": str(DATA_PATH),
        "strategy": "1 coordinator + 6 parallel report-only streams",
        "counts": {
            "entities": len(entities),
            "relationships": len(relationships),
            "missing_source": len(source_targets),
            "missing_source_non_place": len(non_place_source),
            "missing_source_place": len(place_source),
            "missing_place_id": len(place_targets),
            "missing_location": len(geo_targets),
            "relationship_audit_targets": len(rel_targets),
        },
        "entity_chunks_by_type_and_area": True,
        "relationship_chunks_by_rel_type": True,
        "streams": shards,
    }


def text_matches_entity(entity: dict[str, Any], text: str) -> bool:
    haystack = norm_text(text)
    name = norm_text(entity.get("name"))
    if not haystack or not name:
        return False
    if name in haystack:
        return True
    tokens = [token for token in name.split() if len(token) >= 3]
    if not tokens:
        return False
    hits = sum(1 for token in tokens if token in haystack)
    return hits >= max(2, math.ceil(len(tokens) * 0.6))


def fetch_url_text(url: str, *, timeout: int = 12, disabled: bool = False) -> str:
    if disabled or not is_valid_http_url(url) or requests is None:
        return ""
    try:
        response = requests.get(url, headers={"User-Agent": "vinhlong360-quality-burst/1.0"}, timeout=timeout)
        if response.status_code >= 400:
            return ""
        return compact_text(re.sub(r"<[^>]+>", " ", response.text or ""), 5000)
    except Exception:
        return ""


def verify_source_url(url: str, entity: dict[str, Any], *, no_web: bool = False) -> tuple[bool, str]:
    if not is_valid_http_url(url):
        return False, "invalid URL"
    page_text = fetch_url_text(url, disabled=no_web)
    if not page_text:
        return False, "URL could not be fetched"
    if text_matches_entity(entity, page_text):
        return True, "URL opens and page text matches entity name"
    return False, "URL opens but page text does not clearly match entity"


def search_web(query: str, *, max_results: int = 5, disabled: bool = False) -> list[dict[str, str]]:
    if disabled:
        return []
    try:
        from ddgs import DDGS
    except Exception:
        return []
    results: list[dict[str, str]] = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                if not isinstance(item, dict):
                    continue
                url = item.get("href") or item.get("url") or ""
                if not is_valid_http_url(url):
                    continue
                results.append(
                    {
                        "title": str(item.get("title") or ""),
                        "url": str(url),
                        "body": compact_text(item.get("body") or item.get("snippet"), 400),
                    }
                )
    except Exception:
        return results
    return results[:max_results]


def source_candidate_for_entity(entity: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> dict[str, Any]:
    query = " ".join(
        part for part in [f'"{entity.get("name", "")}"', AREA_LABELS.get(str(entity.get("area")), ""), "Vinh Long tourism source"] if part
    )
    search_results = search_web(query, disabled=config.no_web)
    if not llm.available:
        if not search_results:
            return make_candidate_record(
                entity_id=str(entity.get("id") or ""), field="source", current_value=entity.get("source"),
                suggested_value=None, confidence=0.0, evidence_urls=[],
                reason="No LLM/search candidate available; source verification deferred.", apply_policy="reject",
                stream="source", extra={"status": "needs_source", "query": query},
            )
        best = search_results[0]
        return make_candidate_record(
            entity_id=str(entity.get("id") or ""), field="source", current_value=entity.get("source"),
            suggested_value={"title": best.get("title") or best["url"], "url": best["url"]}, confidence=0.55,
            evidence_urls=[best["url"]], reason="Search result captured for later GPT review; not enough confidence to apply.",
            apply_policy="reject", stream="source", extra={"status": "candidate_unverified", "query": query, "search_results": search_results[:3]},
        )

    payload = {
        "task": "Choose the best source URL for this entity from search_results only.",
        "rules": [
            "Do not invent URLs.",
            "Prefer official tourism, government, venue, or reputable local sources.",
            "Return null URL and confidence below 0.70 if none of the results match.",
            "Return JSON with title, url, matched_fields, confidence, reason.",
        ],
        "entity": entity_stub(entity, include_source=False),
        "search_query": query,
        "search_results": search_results,
    }
    decision = llm.complete_json(system="You are a strict source verification auditor. Return JSON only.", payload=payload, max_tokens=900)
    if not isinstance(decision, dict) or decision.get("_error"):
        return make_candidate_record(
            entity_id=str(entity.get("id") or ""), field="source", current_value=entity.get("source"),
            suggested_value=None, confidence=0.0, evidence_urls=[],
            reason=f"LLM source audit failed: {decision.get('_error') if isinstance(decision, dict) else 'invalid JSON'}",
            apply_policy="reject", stream="source", extra={"status": "llm_error", "query": query, "search_results": search_results[:3]},
        )
    url = str(decision.get("url") or "").strip()
    title = str(decision.get("title") or url).strip()
    confidence = as_confidence(decision.get("confidence"), 0.0)
    verified, verify_reason = verify_source_url(url, entity, no_web=config.no_web)
    policy = classify_apply_policy(confidence, [url] if url else [], verified=verified, requires_url=True)
    return make_candidate_record(
        entity_id=str(entity.get("id") or ""), field="source", current_value=entity.get("source"),
        suggested_value={"title": title, "url": url} if url else None, confidence=confidence,
        evidence_urls=[url] if url else [], reason=f"{compact_text(decision.get('reason'), 500)}; verification: {verify_reason}",
        apply_policy=policy, stream="source",
        extra={"status": "verified" if verified else "needs_review", "matched_fields": decision.get("matched_fields") or [], "query": query, "url_verified": verified},
    )


def run_source_stream(data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> list[dict[str, Any]]:
    targets = limit_items(source_missing_targets(data.get("entities", [])), config.limit)
    return run_parallel(targets, config.item_workers, lambda entity: source_candidate_for_entity(entity, llm, config))


def candidate_places_for_entity(entity: dict[str, Any], places: list[dict[str, Any]], *, limit: int = 25) -> list[dict[str, Any]]:
    area = entity.get("area")
    text = norm_text(" ".join([str(entity.get("name") or ""), entity_address(entity), str(entity.get("summary") or "")]))
    scored: list[tuple[float, dict[str, Any]]] = []
    for place in places:
        place_area = place.get("area")
        score = 0.0
        if area and place_area == area:
            score += 2.0
        elif area and place_area and place_area != area:
            score -= 3.0
        place_name = norm_text(place.get("name"))
        tokens = [token for token in place_name.split() if len(token) >= 3]
        if place_name and place_name in text:
            score += 4.0
        score += sum(0.45 for token in tokens if token in text)
        if score > 0:
            scored.append((score, place))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored and area:
        scored = [(1.0, place) for place in places if place.get("area") == area][:limit]
    return [
        {"id": place.get("id"), "name": place.get("name"), "area": place.get("area"), "legacyArea": place.get("legacyArea")}
        for _score, place in scored[:limit]
    ]


def placeid_candidate_from_decision(
    entity: dict[str, Any],
    decision: dict[str, Any] | None,
    place_by_id: dict[str, dict[str, Any]],
    *,
    stream: str = "placeid",
) -> dict[str, Any]:
    decision = decision if isinstance(decision, dict) else {}
    candidate_id = str(decision.get("candidate_place_id") or decision.get("placeId") or "").strip()
    confidence = as_confidence(decision.get("confidence"), 0.0)
    evidence = decision.get("evidence") or decision.get("reason") or ""
    candidate_place = place_by_id.get(candidate_id)
    conflict = False
    conflict_reason = ""
    if candidate_id and candidate_place is None:
        conflict = True
        conflict_reason = "candidate placeId does not exist"
    entity_area = entity.get("area")
    place_area = candidate_place.get("area") if candidate_place else None
    if candidate_place and entity_area and place_area and entity_area != place_area:
        conflict = True
        conflict_reason = f"area conflict: entity={entity_area}, place={place_area}"
    policy = classify_apply_policy(confidence, [], conflict=conflict, verified=False)
    if policy == "auto_apply":
        policy = "needs_review"
    if not candidate_id:
        policy = "reject" if confidence < 0.70 else "needs_review"
    return make_candidate_record(
        entity_id=str(entity.get("id") or ""), field="placeId", current_value=entity.get("placeId"),
        suggested_value=candidate_id or None, confidence=confidence, evidence_urls=[],
        reason="; ".join(part for part in [compact_text(evidence, 600), conflict_reason] if part), apply_policy=policy,
        stream=stream,
        extra={
            "candidate_place": {"id": candidate_place.get("id"), "name": candidate_place.get("name"), "area": candidate_place.get("area")} if candidate_place else None,
            "area_conflict": conflict,
            "status": "conflicting" if conflict else "candidate",
        },
    )


def placeid_candidate_for_entity(entity: dict[str, Any], places: list[dict[str, Any]], place_by_id: dict[str, dict[str, Any]], llm: JsonLLMClient) -> dict[str, Any]:
    candidates = candidate_places_for_entity(entity, places)
    if not llm.available:
        decision = {"candidate_place_id": candidates[0]["id"], "confidence": 0.65, "evidence": "Heuristic place candidate; requires GPT/source review."} if candidates else {"candidate_place_id": None, "confidence": 0.0, "evidence": "No candidate place found."}
        return placeid_candidate_from_decision(entity, decision, place_by_id)
    payload = {
        "task": "Choose the most likely placeId for a non-place entity.",
        "rules": ["Only choose from candidate_places.", "Reject candidates in a different area/province.", "Return null candidate_place_id and low confidence if weak.", "Return JSON with entity_id, candidate_place_id, confidence, evidence."],
        "entity": entity_stub(entity),
        "candidate_places": candidates,
    }
    decision = llm.complete_json(system="You are a strict placeId consistency auditor. Return JSON only.", payload=payload, max_tokens=900)
    if not isinstance(decision, dict) or decision.get("_error"):
        decision = {"candidate_place_id": None, "confidence": 0.0, "evidence": f"LLM placeId audit failed: {decision.get('_error') if isinstance(decision, dict) else 'invalid JSON'}"}
    return placeid_candidate_from_decision(entity, decision, place_by_id)


def run_placeid_stream(data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> list[dict[str, Any]]:
    entities = data.get("entities", [])
    places = [e for e in entities if isinstance(e, dict) and e.get("type") == PLACE_TYPE and e.get("id")]
    place_by_id = {str(place.get("id")): place for place in places}
    targets = limit_items(placeid_targets(entities), config.limit)
    return run_parallel(targets, config.item_workers, lambda entity: placeid_candidate_for_entity(entity, places, place_by_id, llm))


def geocode_query_from_decision(entity: dict[str, Any], decision: dict[str, Any] | None) -> tuple[str, float, str]:
    decision = decision if isinstance(decision, dict) else {}
    query = str(decision.get("geocode_query") or decision.get("query") or "").strip()
    if not query:
        parts = [str(entity.get("name") or ""), entity_address(entity), AREA_LABELS.get(str(entity.get("area")), "")]
        query = ", ".join(part for part in parts if part)
    confidence = as_confidence(decision.get("confidence"), 0.65)
    reason = str(decision.get("reason") or decision.get("evidence") or "heuristic geocode query")
    return query, confidence, reason


def location_candidate_from_decision(
    entity: dict[str, Any],
    decision: dict[str, Any] | None,
    *,
    geocode_fn: Callable[[str, str, bool], list[float] | None] | None = None,
    no_geocode: bool = False,
) -> dict[str, Any]:
    query, confidence, reason = geocode_query_from_decision(entity, decision)
    coords = None
    region = AREA_LABELS.get(str(entity.get("area")), "Vinh Long")
    if not no_geocode:
        if geocode_fn is None and geo is not None:
            geocode_fn = geo.geocode  # type: ignore[assignment]
        if geocode_fn is not None:
            try:
                coords = geocode_fn(query, region, True)
            except TypeError:
                coords = geocode_fn(query, region)  # type: ignore[misc]
            except Exception:
                coords = None
    coords = parse_coordinates(coords)
    verified = coords is not None
    policy = classify_apply_policy(confidence, [], verified=verified)
    return make_candidate_record(
        entity_id=str(entity.get("id") or ""), field="coordinates", current_value=entity.get("coordinates"),
        suggested_value=coords, confidence=confidence if coords else min(confidence, 0.69), evidence_urls=[],
        reason=f"{compact_text(reason, 600)}; geocode_query={query}; coordinates accepted only from geocoder.",
        apply_policy=policy if coords else "reject", stream="location",
        extra={"status": "verified" if verified else "not_found", "geocode_query": query, "geocode_region": region, "geocode_verified": verified, "llm_supplied_coordinates_ignored": bool(isinstance(decision, dict) and decision.get("coordinates"))},
    )


def location_candidate_for_entity(entity: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> dict[str, Any]:
    if not llm.available:
        decision = {"geocode_query": ", ".join(part for part in [str(entity.get("name") or ""), entity_address(entity), AREA_LABELS.get(str(entity.get("area")), "")] if part), "confidence": 0.65, "reason": "Heuristic geocode query; LLM disabled."}
    else:
        payload = {"task": "Create a geocode query for this entity. Do not return coordinates.", "rules": ["Return JSON with entity_id, geocode_query, confidence, reason.", "Use name, address, area, and summary only.", "Never invent latitude/longitude."], "entity": entity_stub(entity)}
        decision = llm.complete_json(system="You prepare geocode queries. Return JSON only and no coordinates.", payload=payload, max_tokens=700)
        if not isinstance(decision, dict) or decision.get("_error"):
            decision = {"geocode_query": ", ".join(part for part in [str(entity.get("name") or ""), entity_address(entity)] if part), "confidence": 0.0, "reason": f"LLM geocode query failed: {decision.get('_error') if isinstance(decision, dict) else 'invalid JSON'}"}
    return location_candidate_from_decision(entity, decision, no_geocode=config.no_geocode)


def run_location_stream(data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> list[dict[str, Any]]:
    targets = limit_items(location_targets(data.get("entities", [])), config.limit)
    return run_parallel(targets, config.item_workers, lambda entity: location_candidate_for_entity(entity, llm, config))


def heuristic_quality_status(entity: dict[str, Any]) -> tuple[str, float, list[str]]:
    flags: list[str] = []
    if not entity.get("name"):
        flags.append("missing_name")
    if not entity.get("type"):
        flags.append("missing_type")
    if not entity.get("summary"):
        flags.append("missing_summary")
    if not entity.get("source"):
        flags.append("needs_source")
    if entity.get("type") != PLACE_TYPE and not entity.get("placeId"):
        flags.append("missing_placeId")
    if entity.get("type") != PLACE_TYPE and not entity.get("area"):
        flags.append("missing_area")
    if entity_coordinates(entity) is None:
        flags.append("missing_coordinates")
    if not flags:
        return "verified", 0.80, []
    if any(flag in flags for flag in ("missing_name", "missing_type", "missing_area")):
        return "needs_fix", 0.85, flags
    if "needs_source" in flags:
        return "needs_source", 0.82, flags
    return "unverified", 0.74, flags


def accuracy_record_from_status(
    entity: dict[str, Any],
    status: str,
    confidence: float,
    flags: list[str],
    reason: str,
    evidence_urls: list[str] | None = None,
    suggested_fixes: Any = None,
) -> dict[str, Any]:
    policy = "reject" if status == "verified" else "needs_review"
    if status in {"conflicting", "needs_fix"} and confidence < 0.70:
        policy = "reject"
    return make_candidate_record(
        entity_id=str(entity.get("id") or ""), field="entity_accuracy",
        current_value={"name": entity.get("name"), "type": entity.get("type"), "area": entity.get("area"), "placeId": entity.get("placeId"), "source_url": entity_source_url(entity), "quality_flags": flags},
        suggested_value={"status": status, "suggested_fixes": suggested_fixes or {}}, confidence=confidence,
        evidence_urls=evidence_urls or [], reason=reason, apply_policy=policy, stream="accuracy",
        extra={"status": status, "quality_flags": flags},
    )


def audit_accuracy_chunk(batch: list[dict[str, Any]], llm: JsonLLMClient) -> list[dict[str, Any]]:
    if not llm.available:
        records = []
        for entity in batch:
            status, confidence, flags = heuristic_quality_status(entity)
            records.append(accuracy_record_from_status(entity, status, confidence, flags, "Deterministic contract audit; LLM disabled.", [entity_source_url(entity)] if entity_source_url(entity) else []))
        return records
    payload = {
        "task": "Audit entity factual consistency and data quality.",
        "allowed_status": ["verified", "conflicting", "needs_source", "needs_fix", "unverified"],
        "checks": ["name", "type", "area/province", "summary", "source", "area/placeId consistency"],
        "rules": ["Return one JSON object per entity in a JSON array.", "Do not invent facts. Flag uncertainty as unverified or needs_source.", "Return: entity_id, status, confidence, conflicts, suggested_fixes, evidence_urls, reason."],
        "entities": [entity_stub(entity) for entity in batch],
    }
    decisions = llm.complete_json(system="You are a strict factual accuracy auditor. Return JSON array only.", payload=payload, max_tokens=2600)
    if not isinstance(decisions, list):
        return [accuracy_record_from_status(entity, "unverified", 0.0, ["llm_error"], f"LLM accuracy audit failed: {decisions.get('_error') if isinstance(decisions, dict) else 'invalid JSON'}") for entity in batch]
    by_id = {str(item.get("entity_id")): item for item in decisions if isinstance(item, dict)}
    records = []
    for entity in batch:
        decision = by_id.get(str(entity.get("id")), {})
        status = str(decision.get("status") or "unverified")
        if status not in {"verified", "conflicting", "needs_source", "needs_fix", "unverified"}:
            status = "unverified"
        flags = [str(flag) for flag in (decision.get("conflicts") or decision.get("quality_flags") or [])]
        records.append(accuracy_record_from_status(entity, status, as_confidence(decision.get("confidence"), 0.0), flags, str(decision.get("reason") or "LLM audit decision."), url_list(decision.get("evidence_urls")), decision.get("suggested_fixes") or {}))
    return records


def run_accuracy_stream(data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> list[dict[str, Any]]:
    targets = limit_items([e for e in data.get("entities", []) if isinstance(e, dict)], config.limit)
    nested = run_parallel(list(chunks(targets, config.chunk_size)), config.item_workers, lambda batch: audit_accuracy_chunk(batch, llm))
    return [record for records in nested for record in records]


def relationship_record_from_status(item: dict[str, Any], status: str, confidence: float, reason: str) -> dict[str, Any]:
    risk = "low"
    if status in {"conflicting", "needs_review"}:
        risk = "high" if "missing" in norm_text(reason) or "conflict" in norm_text(reason) else "medium"
    policy = "needs_review" if confidence >= 0.70 and risk in {"medium", "high"} else "reject"
    return make_candidate_record(
        entity_id=str(item.get("source_id") or ""), field="relationship",
        current_value={"index": item.get("index"), "source_id": item.get("source_id"), "target_id": item.get("target_id"), "rel_type": item.get("rel_type"), "distance_km": item.get("distance_km")},
        suggested_value={"status": status, "risk": risk}, confidence=confidence, evidence_urls=[], reason=reason,
        apply_policy=policy, stream="relationship",
        extra={"relationship_index": item.get("index"), "source_id": item.get("source_id"), "target_id": item.get("target_id"), "rel_type": item.get("rel_type"), "status": status, "risk": risk, "heuristic_reasons": item.get("heuristic_reasons") or []},
    )


def audit_relationship_chunk(batch: list[dict[str, Any]], llm: JsonLLMClient) -> list[dict[str, Any]]:
    if not llm.available:
        records = []
        for item in batch:
            reasons = item.get("heuristic_reasons") or []
            if reasons:
                status = "needs_review" if item.get("rel_type") == "near" else "conflicting"
                confidence = 0.86
                reason = "; ".join(str(reason) for reason in reasons)
            else:
                status = "verified"
                confidence = 0.75
                reason = "Relationship included by rel_type audit; no deterministic conflict found."
            records.append(relationship_record_from_status(item, status, confidence, reason))
        return records
    payload = {
        "task": "Audit relationship risk. Do not delete anything.",
        "rules": ["Return one JSON object per relationship in a JSON array.", "Allowed status: verified, needs_review, conflicting, unverified.", "For near relationships, use distance and coordinate availability as primary evidence.", "Return: relationship_index, status, confidence, reason, risk."],
        "relationships": [{"relationship_index": item.get("index"), "source_id": item.get("source_id"), "source_name": item.get("source_name"), "source_area": item.get("source_area"), "target_id": item.get("target_id"), "target_name": item.get("target_name"), "target_area": item.get("target_area"), "rel_type": item.get("rel_type"), "distance_km": item.get("distance_km"), "heuristic_reasons": item.get("heuristic_reasons") or []} for item in batch],
    }
    decisions = llm.complete_json(system="You are a relationship risk auditor. Return JSON array only.", payload=payload, max_tokens=2400)
    if not isinstance(decisions, list):
        return [relationship_record_from_status(item, "unverified", 0.0, f"LLM relationship audit failed: {decisions.get('_error') if isinstance(decisions, dict) else 'invalid JSON'}") for item in batch]
    by_index = {int(item.get("relationship_index")): item for item in decisions if isinstance(item, dict) and item.get("relationship_index") is not None}
    records = []
    for item in batch:
        decision = by_index.get(int(item.get("index")))
        if not decision:
            records.append(relationship_record_from_status(item, "unverified", 0.0, "LLM omitted this relationship."))
            continue
        status = str(decision.get("status") or "unverified")
        if status not in {"verified", "needs_review", "conflicting", "unverified"}:
            status = "unverified"
        records.append(relationship_record_from_status(item, status, as_confidence(decision.get("confidence"), 0.0), str(decision.get("reason") or "LLM relationship risk decision.")))
    return records


def run_relationship_stream(data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> list[dict[str, Any]]:
    targets = limit_items(relationship_targets(data), config.limit)
    nested = run_parallel(list(chunks(targets, config.relationship_chunk_size)), config.item_workers, lambda batch: audit_relationship_chunk(batch, llm))
    return [record for records in nested for record in records]


def select_entities(data: dict[str, Any], entity_type: str | None = None, area: str | None = None, text: str | None = None) -> list[dict[str, Any]]:
    out = []
    needle = norm_text(text) if text else ""
    for entity in data.get("entities", []):
        if not isinstance(entity, dict):
            continue
        if entity_type and entity.get("type") != entity_type:
            continue
        if area and entity.get("area") != area:
            continue
        if needle and needle not in norm_text(" ".join([str(entity.get("name") or ""), str(entity.get("summary") or "")])):
            continue
        out.append(entity)
    return out


def eval_case(query: str, entity_ids: list[str], keywords: list[str], category: str, difficulty: str = "medium") -> dict[str, Any]:
    return {"query": query, "expected_entities": entity_ids, "expected_tools": ["search"] if category != "itinerary" else ["search", "entity_detail"], "expected_keywords": keywords, "category": category, "difficulty": difficulty, "max_score": 10.0}


def generate_heuristic_eval_cases(data: dict[str, Any], *, case_target: int = 30) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    picked: set[str] = set()

    def take(pool: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
        chosen = []
        for entity in pool:
            entity_id = str(entity.get("id") or "")
            if not entity_id or entity_id in picked:
                continue
            picked.add(entity_id)
            chosen.append(entity)
            if len(chosen) >= count:
                break
        return chosen

    for entity in take(select_entities(data, "attraction"), 5):
        name = str(entity.get("name") or "")
        cases.append(eval_case(f"Gioi thieu diem tham quan {name} va vi sao nen den?", [str(entity["id"])], [name], "factual", "easy"))
    for entity in take(select_entities(data, "product"), 5):
        name = str(entity.get("name") or "")
        cases.append(eval_case(f"San pham OCOP hoac dac san {name} co gi noi bat?", [str(entity["id"])], [name], "recommendation"))
    for entity in take(select_entities(data, "accommodation"), 4):
        name = str(entity.get("name") or "")
        cases.append(eval_case(f"Neu toi muon luu tru gan {name}, can biet dieu gi?", [str(entity["id"])], [name], "recommendation"))
    khmer_pool = select_entities(data, area="tra-vinh", text="Khmer") or select_entities(data, "history", area="tra-vinh")
    for entity in take(khmer_pool, 5):
        name = str(entity.get("name") or "")
        cases.append(eval_case(f"{name} lien quan gi den van hoa Khmer Tra Vinh?", [str(entity["id"])], [name, "Khmer", "Tra Vinh"], "factual"))
    for area in AREAS:
        pool = take([e for e in data.get("entities", []) if isinstance(e, dict) and e.get("area") == area and e.get("type") in {"attraction", "history", "nature", "dish", "product"}], 3)
        if pool:
            area_label = AREA_LABELS.get(area, area)
            ids = [str(e.get("id")) for e in pool if e.get("id")]
            names = [str(e.get("name")) for e in pool[:2] if e.get("name")]
            cases.append(eval_case(f"Lap lich trinh mot ngay o {area_label} cho an uong va tham quan.", ids, [area_label] + names, "itinerary", "hard"))
    for entity in take(select_entities(data, "dish"), 5):
        name = str(entity.get("name") or "")
        cases.append(eval_case(f"Mon {name} nen thu o dau va co dac diem gi?", [str(entity["id"])], [name], "factual"))
    return cases[:case_target]


def valid_eval_case(case: dict[str, Any], entity_ids: set[str]) -> bool:
    if not isinstance(case, dict):
        return False
    if not case.get("query") or not isinstance(case.get("expected_entities"), list):
        return False
    if case.get("category") not in {"factual", "comparison", "itinerary", "seasonal", "recommendation", "edge_case"}:
        return False
    if case.get("difficulty") not in {"easy", "medium", "hard"}:
        return False
    return all(str(entity_id) in entity_ids for entity_id in case.get("expected_entities", []))


def run_eval_stream(data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> dict[str, Any]:
    entity_ids = {str(e.get("id")) for e in data.get("entities", []) if isinstance(e, dict) and e.get("id")}
    fallback_cases = generate_heuristic_eval_cases(data, case_target=30)
    cases = fallback_cases
    source = "heuristic"
    if llm.available:
        sample_entities = [entity_stub(entity, include_source=False) for entity in data.get("entities", [])[:120] if isinstance(entity, dict)]
        payload = {"task": "Generate reusable benchmark cases for this tourism knowledge system.", "topics": ["tourism", "OCOP", "accommodation", "Khmer culture", "itinerary"], "rules": ["Return a JSON array only.", "Use real entity IDs only.", "Make questions realistic and regression-oriented."], "sample_entities": sample_entities}
        decisions = llm.complete_json(system="You generate benchmark eval cases. Return JSON array only.", payload=payload, max_tokens=3500)
        if isinstance(decisions, list):
            generated = []
            for case in decisions:
                if not isinstance(case, dict):
                    continue
                case.setdefault("expected_tools", ["search"])
                case.setdefault("expected_keywords", [])
                case.setdefault("category", "factual")
                case.setdefault("difficulty", "medium")
                case.setdefault("max_score", 10.0)
                if valid_eval_case(case, entity_ids):
                    generated.append(case)
            if generated:
                cases = generated[:30]
                source = "gpt55"
    return {"generated_at": utc_now(), "model": llm.model, "source": source, "case_count": len(cases), "cases": cases}



def enforce_apply_policy(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    confidence = as_confidence(out.get("confidence"), 0.0)
    out["confidence"] = confidence
    field = out.get("field")
    if confidence < 0.70:
        out["apply_policy"] = "reject"
    elif out.get("apply_policy") == "auto_apply" and field == "source":
        if not out.get("url_verified") or not any(is_valid_http_url(url) for url in out.get("evidence_urls") or []):
            out["apply_policy"] = "needs_review"
    elif out.get("apply_policy") == "auto_apply" and field == "coordinates":
        if not out.get("geocode_verified"):
            out["apply_policy"] = "needs_review"
    elif out.get("apply_policy") == "auto_apply" and field == "placeId":
        out["apply_policy"] = "needs_review"
    elif out.get("apply_policy") not in APPLY_POLICIES:
        out["apply_policy"] = "reject"
    return out

def dedupe_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in records:
        key = (str(record.get("entity_id") or ""), str(record.get("field") or ""), canonical_json(record.get("suggested_value")))
        existing = best.get(key)
        if existing is None or float(record.get("confidence") or 0.0) > float(existing.get("confidence") or 0.0):
            best[key] = record
    return sorted(best.values(), key=lambda r: (str(r.get("field")), str(r.get("entity_id"))))


def write_summary_report(output_dir: Path, review_queue: dict[str, Any], *, manifest: dict[str, Any] | None = None, llm_stats: dict[str, Any] | None = None) -> None:
    counts = review_queue.get("counts", {})
    stream_counts = review_queue.get("stream_counts", {})
    manifest_counts = (manifest or {}).get("counts", {})
    lines = [
        "# GPT-5.5 Quality Burst Summary",
        "",
        f"Generated at: {review_queue.get('generated_at')}",
        f"Model: {(llm_stats or {}).get('model', DEFAULT_MODEL)}",
        f"LLM available: {(llm_stats or {}).get('available', False)}",
        "",
        "## Scope",
        "",
        f"- Entities: {manifest_counts.get('entities', 'unknown')}",
        f"- Relationships: {manifest_counts.get('relationships', 'unknown')}",
        f"- Missing source targets: {manifest_counts.get('missing_source', 'unknown')}",
        f"- Missing placeId targets: {manifest_counts.get('missing_place_id', 'unknown')}",
        f"- Missing location targets: {manifest_counts.get('missing_location', 'unknown')}",
        f"- Relationship audit targets: {manifest_counts.get('relationship_audit_targets', 'unknown')}",
        "",
        "## Output Counts",
        "",
    ]
    for stream in STREAM_FILES:
        lines.append(f"- {stream}: {stream_counts.get(stream, 0)} records")
    lines.extend([
        "",
        "## Merge Result",
        "",
        f"- Raw records: {counts.get('raw_records', 0)}",
        f"- Deduped records: {counts.get('deduped_records', 0)}",
        f"- Auto apply candidates: {counts.get('auto_apply', 0)}",
        f"- Needs review candidates: {counts.get('needs_review', 0)}",
        f"- Rejected/no-action records: {counts.get('reject', 0)}",
        f"- Schema errors: {counts.get('schema_errors', 0)}",
        "",
        "## Safety Notes",
        "",
        "- Streams do not modify web/data.json.",
        "- Source auto-apply requires a valid fetched URL that matches the entity.",
        "- Coordinates are accepted only from geocoder/source verification, never from LLM text.",
        "- PlaceId candidates are review-first unless a later verifier provides non-LLM evidence.",
        "- Relationship audit reports risk only; it does not delete edges.",
        "",
        "## Artifacts",
        "",
    ])
    for filename in [MANIFEST_FILE, *STREAM_FILES.values(), EVAL_FILE, MERGED_CANDIDATES_FILE, AUTO_APPLY_FILE, REVIEW_QUEUE_FILE, REJECT_FILE, SUMMARY_FILE, DATA_QUALITY_SUMMARY_FILE, LLM_USAGE_FILE]:
        lines.append(f"- `{filename}`")
    if llm_stats:
        lines.extend([
            "",
            "## LLM Usage",
            "",
            f"- Calls: {llm_stats.get('calls', 0)}",
            f"- Prompt tokens: {llm_stats.get('prompt_tokens', 0)}",
            f"- Completion tokens: {llm_stats.get('completion_tokens', 0)}",
        ])
    (output_dir / SUMMARY_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_outputs(output_dir: Path, *, manifest: dict[str, Any] | None = None, llm_stats: dict[str, Any] | None = None) -> dict[str, Any]:
    all_records: list[dict[str, Any]] = []
    schema_errors: list[dict[str, Any]] = []
    stream_counts: Counter[str] = Counter()
    for stream, filename in STREAM_FILES.items():
        records = read_jsonl(output_dir / filename)
        stream_counts[stream] = len(records)
        for record in records:
            record = enforce_apply_policy(record)
            errors = validate_candidate_record(record)
            if errors:
                record = dict(record)
                record["schema_errors"] = errors
                record["apply_policy"] = "reject"
                schema_errors.append({"stream": stream, "entity_id": record.get("entity_id"), "errors": errors})
            all_records.append(record)
    deduped = dedupe_candidates(all_records)
    auto_apply = [record for record in deduped if record.get("apply_policy") == "auto_apply"]
    needs_review = [record for record in deduped if record.get("apply_policy") == "needs_review"]
    reject = [record for record in deduped if record.get("apply_policy") == "reject"]
    review_queue = {
        "generated_at": utc_now(),
        "policy": {
            "auto_apply": "confidence >= 0.90 and verified by URL/geocoder/rule evidence",
            "needs_review": "0.70 <= confidence < 0.90 or not enough non-LLM evidence",
            "reject": "confidence < 0.70, schema error, missing evidence, or area/source conflict",
        },
        "counts": {"raw_records": len(all_records), "deduped_records": len(deduped), "auto_apply": len(auto_apply), "needs_review": len(needs_review), "reject": len(reject), "schema_errors": len(schema_errors)},
        "stream_counts": dict(stream_counts),
        "auto_apply": auto_apply,
        "needs_review": needs_review,
        "reject": reject,
        "schema_errors": schema_errors,
    }
    merged_payload = {
        "generated_at": review_queue["generated_at"],
        "counts": review_queue["counts"],
        "stream_counts": review_queue["stream_counts"],
        "candidates": deduped,
    }
    atomic_write_json(output_dir / MERGED_CANDIDATES_FILE, merged_payload)
    atomic_write_json(output_dir / AUTO_APPLY_FILE, {"generated_at": review_queue["generated_at"], "count": len(auto_apply), "candidates": auto_apply})
    atomic_write_json(output_dir / REVIEW_QUEUE_FILE, review_queue)
    atomic_write_json(output_dir / REJECT_FILE, {"generated_at": review_queue["generated_at"], "count": len(reject), "candidates": reject})
    write_summary_report(output_dir, review_queue, manifest=manifest, llm_stats=llm_stats)
    (output_dir / DATA_QUALITY_SUMMARY_FILE).write_text((output_dir / SUMMARY_FILE).read_text(encoding="utf-8"), encoding="utf-8")
    return review_queue


def run_stream(stream: str, data: dict[str, Any], llm: JsonLLMClient, config: BurstConfig) -> tuple[str, Any]:
    if stream == "source":
        return stream, run_source_stream(data, llm, config)
    if stream == "placeid":
        return stream, run_placeid_stream(data, llm, config)
    if stream == "location":
        return stream, run_location_stream(data, llm, config)
    if stream == "accuracy":
        return stream, run_accuracy_stream(data, llm, config)
    if stream == "relationship":
        return stream, run_relationship_stream(data, llm, config)
    if stream == "eval":
        return stream, run_eval_stream(data, llm, config)
    raise ValueError(f"Unknown stream: {stream}")


def run_quality_burst(data: dict[str, Any], config: BurstConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(data, chunk_size=config.chunk_size, relationship_chunk_size=config.relationship_chunk_size)
    manifest["config"] = {
        "model": config.model,
        "streams": list(config.streams),
        "workers": config.workers,
        "item_workers": config.item_workers,
        "chunk_size": config.chunk_size,
        "relationship_chunk_size": config.relationship_chunk_size,
        "limit": config.limit,
        "no_llm": config.no_llm,
        "no_web": config.no_web,
        "no_geocode": config.no_geocode,
    }
    atomic_write_json(config.output_dir / MANIFEST_FILE, manifest)
    llm = JsonLLMClient(config.model, no_llm=config.no_llm)
    selected_streams = tuple(stream for stream in config.streams if stream in STREAMS)
    print(f"Running streams: {', '.join(selected_streams)}")
    print(f"Output dir: {config.output_dir}")
    with ThreadPoolExecutor(max_workers=max(1, config.workers)) as pool:
        futures = {pool.submit(run_stream, stream, data, llm, config): stream for stream in selected_streams}
        for future in as_completed(futures):
            stream = futures[future]
            try:
                stream, payload = future.result()
            except Exception as exc:
                if stream == "eval":
                    payload = {"generated_at": utc_now(), "model": llm.model, "source": "stream_error", "case_count": 0, "cases": [], "error": str(exc)}
                else:
                    payload = [
                        make_candidate_record(
                            entity_id=f"__stream_error__:{stream}",
                            field="stream_error",
                            current_value=None,
                            suggested_value=None,
                            confidence=0.0,
                            evidence_urls=[],
                            reason=str(exc),
                            apply_policy="reject",
                            stream=stream,
                        )
                    ]
            if stream == "eval":
                atomic_write_json(config.output_dir / EVAL_FILE, payload)
                print(f"  {stream}: wrote {payload.get('case_count', 0)} eval cases")
            else:
                count = write_jsonl(config.output_dir / STREAM_FILES[stream], payload)
                print(f"  {stream}: wrote {count} records")
    llm_stats = llm.stats()
    atomic_write_json(config.output_dir / LLM_USAGE_FILE, llm_stats)
    review_queue = merge_outputs(config.output_dir, manifest=manifest, llm_stats=llm_stats)
    print(f"Review queue: {config.output_dir / REVIEW_QUEUE_FILE}")
    print(f"Summary: {config.output_dir / SUMMARY_FILE}")
    return review_queue


def parse_streams(value: str) -> tuple[str, ...]:
    streams = tuple(part.strip() for part in value.split(",") if part.strip())
    invalid = [stream for stream in streams if stream not in STREAMS]
    if invalid:
        raise argparse.ArgumentTypeError(f"Unknown stream(s): {', '.join(invalid)}")
    return streams or STREAMS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run report-only GPT-5.5 quality burst streams.")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="Path to web/data.json")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Batch artifact directory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model, defaults to LLM_MODEL or cx/gpt-5.5")
    parser.add_argument("--streams", type=parse_streams, default=STREAMS, help="Comma-separated stream list")
    parser.add_argument("--workers", type=int, default=6, help="Parallel stream workers")
    parser.add_argument("--item-workers", type=int, default=2, help="Parallel workers inside each stream")
    parser.add_argument("--chunk-size", type=int, default=25, help="Entity chunk size for LLM audits")
    parser.add_argument("--relationship-chunk-size", type=int, default=50, help="Relationship chunk size")
    parser.add_argument("--limit", type=int, default=None, help="Limit items per selected stream for smoke runs")
    parser.add_argument("--prepare", action="store_true", help="Only write manifest, do not run streams")
    parser.add_argument("--merge-only", action="store_true", help="Only merge existing stream artifacts")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM calls and use deterministic fallback")
    parser.add_argument("--no-web", action="store_true", help="Disable web search and URL fetch verification")
    parser.add_argument("--no-geocode", action="store_true", help="Disable geocoder calls")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_output()
    args = parse_args(argv)
    data = load_data(args.data)
    config = BurstConfig(
        data_path=args.data,
        output_dir=args.output_dir,
        model=args.model,
        streams=args.streams,
        workers=args.workers,
        item_workers=args.item_workers,
        chunk_size=args.chunk_size,
        relationship_chunk_size=args.relationship_chunk_size,
        limit=args.limit,
        no_llm=args.no_llm,
        no_web=args.no_web,
        no_geocode=args.no_geocode,
    )
    if args.merge_only:
        manifest_path = config.output_dir / MANIFEST_FILE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.exists() else None
        usage_path = config.output_dir / LLM_USAGE_FILE
        llm_stats = json.loads(usage_path.read_text(encoding="utf-8-sig")) if usage_path.exists() else {"model": config.model, "available": False}
        review_queue = merge_outputs(config.output_dir, manifest=manifest, llm_stats=llm_stats)
        print(f"Merged {review_queue['counts']['raw_records']} records into {config.output_dir / REVIEW_QUEUE_FILE}")
        return 0
    if args.prepare:
        manifest = build_manifest(data, chunk_size=config.chunk_size, relationship_chunk_size=config.relationship_chunk_size)
        manifest["config"] = {"model": config.model, "streams": list(config.streams), "prepare_only": True}
        atomic_write_json(config.output_dir / MANIFEST_FILE, manifest)
        write_summary_report(config.output_dir, {"generated_at": utc_now(), "counts": {}, "stream_counts": {}}, manifest=manifest, llm_stats={"model": config.model, "available": False})
        print(f"Prepared manifest at {config.output_dir / MANIFEST_FILE}")
        return 0
    run_quality_burst(data, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())






