"""
vinhlong360 -- Knowledge Evolution Engine.

Auto schema learning, relation inference, and knowledge gap detection
for the vinhlong360 Knowledge Agent.

Features:
  - SchemaAnalyzer:       scan entities, discover field patterns & inconsistencies
  - RelationInferrer:     infer geographic/type/co-occurrence/temporal relations
  - KnowledgeGapDetector: find missing fields, orphan entities, thin descriptions
  - EvolutionTracker:     track changes over time with drift detection
  - AutoEnricher:         suggest & apply enrichments based on similar entities

Data dir: agent/data/evolution/
Thread-safe: each class uses its own threading.Lock.
"""

import json
import logging
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent / "data" / "evolution"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RELATIONS_FILE = DATA_DIR / "relations.json"
CHANGELOG_FILE = DATA_DIR / "changelog.json"
ENRICHMENT_LOG_FILE = DATA_DIR / "enrichment_log.json"
COOCCURRENCE_FILE = DATA_DIR / "cooccurrence.json"

MAX_CHANGELOG = 5000
MAX_ENRICHMENT_LOG = 2000

# ── Import knowledge layer ─────────────────────────────────────────────────────

try:
    import knowledge as _kb  # type: ignore[import]
except ImportError:
    import agent.knowledge as _kb  # type: ignore[import]

# Convenience accessors (must go through module to see post-_ensure() values)
def _ensure():
    _kb._ensure()

def _get_entities() -> dict:
    _ensure()
    return _kb._entities

def _get_relationships() -> list:
    _ensure()
    return _kb._relationships or []

# Entity types that represent actual content (not places)
CARD_TYPES = [
    "experience", "product", "dish", "craft_village", "attraction",
    "accommodation", "person", "event", "history", "nature", "economy",
]

# ── Helpers ────────────────────────────────────────────────────────────────────


def _atomic_write(path: Path, data):
    """Write JSON atomically via temp file + rename."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _load_json(path: Path, default=None):
    if default is None:
        default = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt file %s, using default", path)
    return default


def _content_entities() -> dict:
    """Return only content entities (not places)."""
    ents = _get_entities()
    return {eid: e for eid, e in ents.items() if e.get("type") in CARD_TYPES}


def _all_entities() -> dict:
    """Return all entities."""
    return dict(_get_entities())


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _days_since(iso_date: str) -> float:
    """Return days since an ISO date string (YYYY-MM-DD or ISO datetime)."""
    try:
        date_str = iso_date[:10]
        parts = date_str.split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        import calendar
        then = time.mktime((y, m, d, 0, 0, 0, 0, 0, -1))
        return (time.time() - then) / 86400
    except Exception:
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  1. SchemaAnalyzer
# ══════════════════════════════════════════════════════════════════════════════


class SchemaAnalyzer:
    """Scan entities, discover field patterns, detect inconsistencies."""

    def __init__(self):
        self._lock = Lock()

    def analyze_schema(self) -> dict:
        """Full schema analysis: fields, coverage, type distribution."""
        entities = _content_entities()
        if not entities:
            return {"total": 0, "fields": {}, "types": {}, "coverage": {}}

        all_fields: Counter = Counter()
        field_types: dict[str, Counter] = defaultdict(Counter)

        for e in entities.values():
            for k, v in e.items():
                all_fields[k] += 1
                field_types[k][type(v).__name__] += 1

        total = len(entities)
        coverage = {f: round(count / total, 4) for f, count in all_fields.items()}
        field_info = {}
        for f, count in all_fields.most_common():
            types_dist = dict(field_types[f].most_common())
            field_info[f] = {
                "count": count,
                "coverage": coverage[f],
                "value_types": types_dist,
            }

        return {
            "total": total,
            "fields": field_info,
            "types": self.get_type_distribution(),
            "coverage": coverage,
        }

    def get_field_coverage(self) -> dict[str, float]:
        """What % of content entities have each field."""
        entities = _content_entities()
        if not entities:
            return {}

        total = len(entities)
        field_counts: Counter = Counter()
        for e in entities.values():
            for k in e.keys():
                field_counts[k] += 1

        return {f: round(c / total, 4) for f, c in field_counts.most_common()}

    def suggest_schema_additions(self) -> list[dict]:
        """Fields that some entities have but most don't -- suggest adding them."""
        coverage = self.get_field_coverage()
        entities = _content_entities()
        if not entities:
            return []

        suggestions = []
        # Fields present in 20-80% of entities are good candidates
        for field_name, cov in coverage.items():
            if field_name in ("id", "type", "name"):
                continue
            if 0.20 <= cov < 0.80:
                # Which entity types are missing this field?
                missing_types: Counter = Counter()
                for e in entities.values():
                    if field_name not in e:
                        missing_types[e["type"]] += 1
                suggestions.append({
                    "field": field_name,
                    "coverage": round(cov, 4),
                    "missing_count": sum(missing_types.values()),
                    "missing_by_type": dict(missing_types.most_common()),
                    "priority": "high" if cov >= 0.5 else "medium",
                    "reason": (
                        f"Field '{field_name}' present in {cov:.0%} of entities. "
                        f"Missing from {sum(missing_types.values())} entities."
                    ),
                })

        suggestions.sort(key=lambda s: s["coverage"], reverse=True)
        return suggestions

    def get_type_distribution(self) -> dict[str, int]:
        """Count entities by type."""
        entities = _content_entities()
        dist: Counter = Counter()
        for e in entities.values():
            dist[e.get("type", "unknown")] += 1
        return dict(dist.most_common())

    def detect_inconsistencies(self) -> list[dict]:
        """Detect same field with different formats/types across entities."""
        entities = _content_entities()
        if not entities:
            return []

        field_values: dict[str, list] = defaultdict(list)
        for e in entities.values():
            for k, v in e.items():
                field_values[k].append((e["id"], v))

        inconsistencies = []

        for field_name, values in field_values.items():
            if field_name in ("id", "name", "summary"):
                continue

            # Check type consistency
            type_counter: Counter = Counter()
            for _, v in values:
                type_counter[type(v).__name__] += 1

            if len(type_counter) > 1:
                # Multiple value types for same field
                examples = {}
                for eid, v in values:
                    tname = type(v).__name__
                    if tname not in examples:
                        examples[tname] = {"entity_id": eid, "value": repr(v)[:100]}
                inconsistencies.append({
                    "field": field_name,
                    "issue": "mixed_types",
                    "types": dict(type_counter),
                    "examples": examples,
                    "severity": "high" if "NoneType" in type_counter else "medium",
                })

            # Check format consistency for string fields
            if type_counter.get("str", 0) > 5:
                str_values = [v for _, v in values if isinstance(v, str)]
                # Check if some have URLs and some don't (for url-like fields)
                if field_name in ("source", "image", "url"):
                    url_pattern = re.compile(r"^https?://")
                    has_url = sum(1 for v in str_values if url_pattern.match(v))
                    no_url = len(str_values) - has_url
                    if has_url > 0 and no_url > 0:
                        inconsistencies.append({
                            "field": field_name,
                            "issue": "mixed_formats",
                            "detail": f"{has_url} with URL, {no_url} without",
                            "severity": "medium",
                        })

        inconsistencies.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))
        return inconsistencies


# ══════════════════════════════════════════════════════════════════════════════
#  2. RelationInferrer
# ══════════════════════════════════════════════════════════════════════════════


class RelationInferrer:
    """Discover relationships from entity data using heuristic rules."""

    def __init__(self):
        self._lock = Lock()
        self._relations: list[dict] = []
        self._load()

    def _load(self):
        data = _load_json(RELATIONS_FILE, default=[])
        if isinstance(data, list):
            self._relations = data
        elif isinstance(data, dict):
            self._relations = data.get("relations", [])
        else:
            self._relations = []

    def _save(self):
        _atomic_write(RELATIONS_FILE, self._relations)

    def infer_relations(self, entities: dict = None) -> list[dict]:
        """Discover relationships from entity data. Returns new relations found."""
        if entities is None:
            entities = _content_entities()

        with self._lock:
            existing_keys = {
                (r["from"], r["to"], r["type"]) for r in self._relations
            }
            new_relations = []

            # Geographic: same placeId -> "located_in"
            by_place: dict[str, list] = defaultdict(list)
            for e in entities.values():
                pid = e.get("placeId")
                if pid:
                    by_place[pid].append(e)

            for pid, group in by_place.items():
                if len(group) < 2:
                    continue
                for i, a in enumerate(group):
                    for b in group[i + 1:]:
                        key = (a["id"], b["id"], "located_in")
                        rev_key = (b["id"], a["id"], "located_in")
                        if key not in existing_keys and rev_key not in existing_keys:
                            rel = {
                                "from": a["id"],
                                "to": b["id"],
                                "type": "located_in",
                                "evidence": f"same placeId: {pid}",
                                "confidence": 0.8,
                                "inferred_at": _now_iso(),
                            }
                            new_relations.append(rel)
                            existing_keys.add(key)

            # Type: same type + same area -> "similar_to"
            by_type_area: dict[tuple, list] = defaultdict(list)
            for e in entities.values():
                pid = e.get("placeId")
                if pid:
                    all_ents = _all_entities()
                    place = all_ents.get(pid, {})
                    area = place.get("area")
                    if area:
                        by_type_area[(e["type"], area)].append(e)

            for (etype, area), group in by_type_area.items():
                if len(group) < 2:
                    continue
                for i, a in enumerate(group):
                    for b in group[i + 1:]:
                        if a.get("placeId") == b.get("placeId"):
                            continue  # Already covered by located_in
                        key = (a["id"], b["id"], "similar_to")
                        rev_key = (b["id"], a["id"], "similar_to")
                        if key not in existing_keys and rev_key not in existing_keys:
                            rel = {
                                "from": a["id"],
                                "to": b["id"],
                                "type": "similar_to",
                                "evidence": f"same type '{etype}' in area '{area}'",
                                "confidence": 0.5,
                                "inferred_at": _now_iso(),
                            }
                            new_relations.append(rel)
                            existing_keys.add(key)

            # Co-occurrence: from analytics data
            cooccurrence = _load_json(COOCCURRENCE_FILE, default={})
            pairs = cooccurrence.get("pairs", {})
            for pair_key, count in pairs.items():
                if count < 3:
                    continue
                parts = pair_key.split("|")
                if len(parts) != 2:
                    continue
                a_id, b_id = parts
                if a_id not in entities or b_id not in entities:
                    continue
                key = (a_id, b_id, "associated_with")
                rev_key = (b_id, a_id, "associated_with")
                if key not in existing_keys and rev_key not in existing_keys:
                    conf = min(1.0, count / 20)
                    rel = {
                        "from": a_id,
                        "to": b_id,
                        "type": "associated_with",
                        "evidence": f"co-queried {count} times",
                        "confidence": round(conf, 2),
                        "inferred_at": _now_iso(),
                    }
                    new_relations.append(rel)
                    existing_keys.add(key)

            # Temporal: same season/peak -> "same_season"
            by_peak: dict[tuple, list] = defaultdict(list)
            for e in entities.values():
                season = e.get("season")
                if not season:
                    continue
                peak = season.get("peak")
                if peak:
                    peak_key = tuple(sorted(peak))
                    by_peak[peak_key].append(e)

            for peak_months, group in by_peak.items():
                if len(group) < 2 or not peak_months:
                    continue
                for i, a in enumerate(group):
                    for b in group[i + 1:]:
                        key = (a["id"], b["id"], "same_season")
                        rev_key = (b["id"], a["id"], "same_season")
                        if key not in existing_keys and rev_key not in existing_keys:
                            rel = {
                                "from": a["id"],
                                "to": b["id"],
                                "type": "same_season",
                                "evidence": f"shared peak months: {list(peak_months)}",
                                "confidence": 0.6,
                                "inferred_at": _now_iso(),
                            }
                            new_relations.append(rel)
                            existing_keys.add(key)

            self._relations.extend(new_relations)
            self._save()

            logger.info(
                "RelationInferrer: %d new relations inferred (total %d)",
                len(new_relations), len(self._relations),
            )
            return new_relations

    def get_relation_types(self) -> list[str]:
        """All discovered relation types."""
        with self._lock:
            return list({r["type"] for r in self._relations})

    def get_relations_for(self, entity_id: str) -> list[dict]:
        """All relations involving a specific entity."""
        with self._lock:
            return [
                r for r in self._relations
                if r["from"] == entity_id or r["to"] == entity_id
            ]

    def confidence_score(self, relation: dict) -> float:
        """Return confidence score 0-1 based on evidence strength."""
        base = relation.get("confidence", 0.5)

        # Boost if relation type has strong evidence
        rtype = relation.get("type", "")
        type_weights = {
            "located_in": 0.9,
            "similar_to": 0.5,
            "associated_with": 0.6,
            "same_season": 0.65,
        }
        weight = type_weights.get(rtype, 0.5)

        # Blend stored confidence with type weight
        return round(min(1.0, (base + weight) / 2), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  3. KnowledgeGapDetector
# ══════════════════════════════════════════════════════════════════════════════


class KnowledgeGapDetector:
    """Find missing knowledge in the entity database."""

    def __init__(self):
        self._lock = Lock()

    def detect_gaps(self) -> list[dict]:
        """Find all knowledge gaps. Returns list of gap dicts."""
        entities = _content_entities()
        all_ents = _all_entities()
        if not entities:
            return []

        gaps = []
        coverage = SchemaAnalyzer().get_field_coverage()

        # Common fields = fields present in > 60% of entities
        common_fields = {f for f, c in coverage.items() if c > 0.60 and f not in ("id", "type", "name")}

        for eid, e in entities.items():
            # missing_field: entity lacks a common field
            for f in common_fields:
                if f not in e:
                    gaps.append({
                        "type": "missing_field",
                        "entity_id": eid,
                        "entity_name": e.get("name", eid),
                        "entity_type": e.get("type"),
                        "detail": f"Missing common field: '{f}'",
                        "field": f,
                    })

            # thin_description: summary < 50 chars
            summary = e.get("summary", "")
            if len(summary) < 50:
                gaps.append({
                    "type": "thin_description",
                    "entity_id": eid,
                    "entity_name": e.get("name", eid),
                    "entity_type": e.get("type"),
                    "detail": f"Summary only {len(summary)} chars (min 50)",
                    "summary_length": len(summary),
                })

            # no_image: entity without image field
            if not e.get("image") and not e.get("images"):
                gaps.append({
                    "type": "no_image",
                    "entity_id": eid,
                    "entity_name": e.get("name", eid),
                    "entity_type": e.get("type"),
                    "detail": "No image or images field",
                })

            # stale_data: not updated in > 180 days
            updated = e.get("updatedAt")
            if updated:
                days = _days_since(updated)
                if days > 180:
                    gaps.append({
                        "type": "stale_data",
                        "entity_id": eid,
                        "entity_name": e.get("name", eid),
                        "entity_type": e.get("type"),
                        "detail": f"Last updated {int(days)} days ago ({updated})",
                        "days_since_update": int(days),
                    })

        # orphan_entity: entities with no relations to others
        rels = _get_relationships()
        related_ids = set()
        for r in rels:
            related_ids.add(r.get("from"))
            related_ids.add(r.get("to"))

        # Also check inferred relations
        inferred = _load_json(RELATIONS_FILE, default=[])
        if isinstance(inferred, list):
            for r in inferred:
                related_ids.add(r.get("from"))
                related_ids.add(r.get("to"))

        for eid, e in entities.items():
            if eid not in related_ids:
                gaps.append({
                    "type": "orphan_entity",
                    "entity_id": eid,
                    "entity_name": e.get("name", eid),
                    "entity_type": e.get("type"),
                    "detail": "No relations to any other entity",
                })

        # empty_area: areas with < 3 content entities
        area_counts: Counter = Counter()
        known_areas = set()
        for e in entities.values():
            pid = e.get("placeId")
            if pid:
                place = all_ents.get(pid, {})
                area = place.get("area")
                if area:
                    area_counts[area] += 1
                    known_areas.add(area)

        # Also scan places for all known areas
        for e in all_ents.values():
            if e.get("type") == "place" and e.get("area"):
                known_areas.add(e["area"])

        for area in known_areas:
            count = area_counts.get(area, 0)
            if count < 3:
                gaps.append({
                    "type": "empty_area",
                    "detail": f"Area '{area}' has only {count} content entities (min 3)",
                    "area": area,
                    "entity_count": count,
                })

        # missing_category: entity types with < 5 entities
        type_counts = SchemaAnalyzer().get_type_distribution()
        for etype in CARD_TYPES:
            count = type_counts.get(etype, 0)
            if count < 5:
                gaps.append({
                    "type": "missing_category",
                    "detail": f"Category '{etype}' has only {count} entities (min 5)",
                    "category": etype,
                    "entity_count": count,
                })

        return gaps

    def get_gap_priority(self) -> list[dict]:
        """Gaps sorted by impact -- high-traffic entities first."""
        gaps = self.detect_gaps()
        if not gaps:
            return []

        # Load analytics for entity hit counts
        analytics_path = Path(__file__).resolve().parent / "data" / "analytics.json"
        entity_hits = {}
        if analytics_path.exists():
            try:
                with open(analytics_path, encoding="utf-8") as f:
                    analytics = json.load(f)
                entity_hits = analytics.get("entity_hits", {})
            except (json.JSONDecodeError, OSError):
                pass

        # Priority scoring
        gap_type_weights = {
            "missing_field": 3,
            "thin_description": 4,
            "no_image": 2,
            "stale_data": 3,
            "orphan_entity": 1,
            "empty_area": 5,
            "missing_category": 4,
        }

        for gap in gaps:
            base_weight = gap_type_weights.get(gap["type"], 1)
            eid = gap.get("entity_id", "")
            hits = entity_hits.get(eid, 0)
            # Higher traffic -> higher priority
            traffic_boost = math.log1p(hits)
            gap["priority_score"] = round(base_weight + traffic_boost, 2)

        gaps.sort(key=lambda g: g["priority_score"], reverse=True)
        return gaps

    def get_coverage_score(self) -> float:
        """Overall knowledge completeness 0-100."""
        entities = _content_entities()
        if not entities:
            return 0.0

        total = len(entities)
        scores = []

        coverage = SchemaAnalyzer().get_field_coverage()
        # Field coverage average (weighted)
        important_fields = ["summary", "placeId", "season", "source", "confidence", "updatedAt"]
        field_scores = []
        for f in important_fields:
            field_scores.append(coverage.get(f, 0.0))
        if field_scores:
            scores.append(sum(field_scores) / len(field_scores))

        # Description quality
        good_desc = sum(1 for e in entities.values() if len(e.get("summary", "")) >= 50)
        scores.append(good_desc / total if total else 0)

        # Confidence coverage
        has_confidence = sum(1 for e in entities.values() if e.get("confidence", 0) > 0)
        scores.append(has_confidence / total if total else 0)

        # Freshness (entities updated in last 180 days)
        fresh = 0
        for e in entities.values():
            updated = e.get("updatedAt")
            if updated and _days_since(updated) <= 180:
                fresh += 1
        scores.append(fresh / total if total else 0)

        # Relation coverage
        rels = _get_relationships()
        related_ids = set()
        for r in rels:
            related_ids.add(r.get("from"))
            related_ids.add(r.get("to"))
        connected = sum(1 for eid in entities if eid in related_ids)
        scores.append(connected / total if total else 0)

        # Type diversity
        type_dist = SchemaAnalyzer().get_type_distribution()
        represented = sum(1 for t in CARD_TYPES if type_dist.get(t, 0) >= 5)
        scores.append(represented / len(CARD_TYPES) if CARD_TYPES else 0)

        return round((sum(scores) / len(scores)) * 100, 1) if scores else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  4. EvolutionTracker
# ══════════════════════════════════════════════════════════════════════════════


class EvolutionTracker:
    """Track knowledge changes over time with drift detection."""

    def __init__(self):
        self._lock = Lock()
        self._changelog: list[dict] = []
        self._load()

    def _load(self):
        data = _load_json(CHANGELOG_FILE, default=[])
        if isinstance(data, list):
            self._changelog = data
        elif isinstance(data, dict):
            self._changelog = data.get("changelog", [])
        else:
            self._changelog = []

    def _save(self):
        # Trim to max entries
        if len(self._changelog) > MAX_CHANGELOG:
            self._changelog = self._changelog[-MAX_CHANGELOG:]
        _atomic_write(CHANGELOG_FILE, self._changelog)

    def record_change(
        self,
        entity_id: str,
        field: str,
        old_value,
        new_value,
        source: str,
    ):
        """Track a change to an entity field."""
        with self._lock:
            entry = {
                "entity_id": entity_id,
                "field": field,
                "old_value": _serialize(old_value),
                "new_value": _serialize(new_value),
                "source": source,
                "timestamp": _now_iso(),
            }
            self._changelog.append(entry)
            self._save()
            logger.info(
                "Change recorded: %s.%s by %s", entity_id, field, source,
            )

    def get_changelog(
        self,
        entity_id: str = None,
        days: int = 30,
    ) -> list[dict]:
        """Recent changes, optionally filtered by entity and time window."""
        with self._lock:
            cutoff_ts = time.time() - (days * 86400)
            results = []
            for entry in reversed(self._changelog):
                # Filter by entity
                if entity_id and entry.get("entity_id") != entity_id:
                    continue
                # Filter by time
                ts_str = entry.get("timestamp", "")
                try:
                    entry_days = _days_since(ts_str)
                    if entry_days > days:
                        continue
                except Exception:
                    pass
                results.append(entry)
            return results

    def get_growth_metrics(self) -> dict:
        """Entities added/modified over time -- bucketed by week."""
        with self._lock:
            weekly: dict[str, dict] = defaultdict(lambda: {"added": 0, "modified": 0})
            for entry in self._changelog:
                ts = entry.get("timestamp", "")[:10]
                if not ts:
                    continue
                # Compute ISO week key
                try:
                    parts = ts.split("-")
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    import calendar
                    # Simple week key: year-week_number
                    day_of_year = sum(
                        calendar.monthrange(y, mi)[1] for mi in range(1, m)
                    ) + d
                    week_num = (day_of_year - 1) // 7 + 1
                    week_key = f"{y}-W{week_num:02d}"
                except Exception:
                    week_key = "unknown"

                if entry.get("field") == "__created__":
                    weekly[week_key]["added"] += 1
                else:
                    weekly[week_key]["modified"] += 1

            return {
                "weeks": dict(weekly),
                "total_changes": len(self._changelog),
                "unique_entities": len({e["entity_id"] for e in self._changelog}),
            }

    def detect_drift(self) -> list[dict]:
        """Schema changes that may indicate data quality issues."""
        with self._lock:
            drifts = []

            # Detect fields that changed type
            field_type_changes: dict[str, list] = defaultdict(list)
            for entry in self._changelog:
                old_t = _value_type_name(entry.get("old_value"))
                new_t = _value_type_name(entry.get("new_value"))
                if old_t and new_t and old_t != new_t:
                    field_type_changes[entry["field"]].append({
                        "entity_id": entry["entity_id"],
                        "old_type": old_t,
                        "new_type": new_t,
                        "timestamp": entry.get("timestamp"),
                    })

            for field_name, changes in field_type_changes.items():
                drifts.append({
                    "type": "type_drift",
                    "field": field_name,
                    "occurrences": len(changes),
                    "examples": changes[:3],
                    "severity": "high" if len(changes) > 5 else "medium",
                })

            # Detect rapid changes to same field (possible instability)
            recent_changes: dict[str, list] = defaultdict(list)
            for entry in self._changelog:
                key = f"{entry['entity_id']}:{entry['field']}"
                recent_changes[key].append(entry.get("timestamp", ""))

            for key, timestamps in recent_changes.items():
                if len(timestamps) >= 5:
                    eid, field_name = key.split(":", 1)
                    drifts.append({
                        "type": "frequent_changes",
                        "entity_id": eid,
                        "field": field_name,
                        "change_count": len(timestamps),
                        "severity": "medium",
                        "detail": f"Field changed {len(timestamps)} times",
                    })

            # Detect bulk changes from same source (possible bad import)
            source_counts: Counter = Counter()
            for entry in self._changelog[-200:]:
                src = entry.get("source", "unknown")
                source_counts[src] += 1

            for src, count in source_counts.items():
                if count > 50:
                    drifts.append({
                        "type": "bulk_change",
                        "source": src,
                        "change_count": count,
                        "severity": "low",
                        "detail": f"Source '{src}' made {count} changes recently",
                    })

            drifts.sort(
                key=lambda d: {"high": 0, "medium": 1, "low": 2}.get(d["severity"], 3),
            )
            return drifts


def _serialize(value) -> str:
    """Serialize a value for changelog storage."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _value_type_name(value) -> str:
    """Return a human-friendly type name for a serialized value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        # Check if it's a serialized JSON
        if value.startswith(("{", "[")):
            return "json"
        return "str"
    return type(value).__name__


# ══════════════════════════════════════════════════════════════════════════════
#  5. AutoEnricher
# ══════════════════════════════════════════════════════════════════════════════


class AutoEnricher:
    """Suggest and apply enrichments based on similar entities."""

    def __init__(self):
        self._lock = Lock()
        self._log: list[dict] = []
        self._load()

    def _load(self):
        data = _load_json(ENRICHMENT_LOG_FILE, default=[])
        if isinstance(data, list):
            self._log = data
        elif isinstance(data, dict):
            self._log = data.get("log", [])
        else:
            self._log = []

    def _save(self):
        if len(self._log) > MAX_ENRICHMENT_LOG:
            self._log = self._log[-MAX_ENRICHMENT_LOG:]
        _atomic_write(ENRICHMENT_LOG_FILE, self._log)

    @staticmethod
    def _persist_to_kb(entity_id: str, field: str, value):
        """Write an enrichment through to web/data.json so it survives reload."""
        try:
            data_json = Path(__file__).resolve().parent.parent / "web" / "data.json"
            if not data_json.exists():
                return
            data = json.loads(data_json.read_text(encoding="utf-8"))
            for e in data.get("entities", []):
                if e.get("id") == entity_id:
                    e[field] = value
                    tmp = data_json.with_suffix(".enrich.tmp")
                    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    tmp.replace(data_json)
                    return
        except Exception as exc:
            logger.warning("AutoEnricher persist failed: %s", exc)

    def suggest_enrichments(self, entity_id: str) -> list[dict]:
        """What data could be added to this entity, based on similar entities."""
        entities = _content_entities()
        target = entities.get(entity_id)
        if not target:
            return []

        target_type = target.get("type")
        target_fields = set(target.keys())

        # Find entities of the same type
        same_type = [
            e for e in entities.values()
            if e.get("type") == target_type and e["id"] != entity_id
        ]
        if not same_type:
            return []

        # Count which fields the similar entities have that this one lacks
        field_values: dict[str, list] = defaultdict(list)
        field_counts: Counter = Counter()
        for e in same_type:
            for k, v in e.items():
                if k not in target_fields and k not in ("id", "name"):
                    field_counts[k] += 1
                    if v is not None:
                        field_values[k].append(v)

        total_similar = len(same_type)
        suggestions = []

        for field_name, count in field_counts.most_common():
            if count < 2:
                continue
            prevalence = count / total_similar
            if prevalence < 0.3:
                continue

            # Pick a representative example value
            examples = field_values.get(field_name, [])
            example = examples[0] if examples else None

            suggestions.append({
                "field": field_name,
                "reason": f"{count}/{total_similar} similar '{target_type}' entities have this field",
                "prevalence": round(prevalence, 2),
                "example_value": _serialize(example),
                "priority": "high" if prevalence >= 0.7 else "medium" if prevalence >= 0.5 else "low",
            })

        suggestions.sort(key=lambda s: s["prevalence"], reverse=True)
        return suggestions

    def apply_enrichment(
        self,
        entity_id: str,
        field: str,
        value,
        source: str = "auto",
    ):
        """Add data to an entity and log the enrichment."""
        with self._lock:
            entities = _get_entities()
            entity = entities.get(entity_id)
            if not entity:
                logger.warning("AutoEnricher: entity %s not found", entity_id)
                return

            old_value = entity.get(field)
            entity[field] = value

            # Persist the change to web/data.json (previously the mutation was
            # in-memory only and lost on the next reload — a real bug). Best-effort.
            self._persist_to_kb(entity_id, field, value)

            log_entry = {
                "entity_id": entity_id,
                "field": field,
                "old_value": _serialize(old_value),
                "new_value": _serialize(value),
                "source": source,
                "timestamp": _now_iso(),
            }
            self._log.append(log_entry)
            self._save()

            # Also record in evolution tracker
            evolution_tracker.record_change(
                entity_id, field, old_value, value, source=f"enrichment:{source}",
            )

            logger.info(
                "Enrichment applied: %s.%s = %s (source: %s)",
                entity_id, field, repr(value)[:60], source,
            )

    def get_enrichment_stats(self) -> dict:
        """How many enrichments have been applied, grouped by source and field."""
        with self._lock:
            by_source: Counter = Counter()
            by_field: Counter = Counter()
            for entry in self._log:
                by_source[entry.get("source", "unknown")] += 1
                by_field[entry.get("field", "unknown")] += 1

            return {
                "total": len(self._log),
                "by_source": dict(by_source.most_common()),
                "by_field": dict(by_field.most_common()),
                "recent": self._log[-10:] if self._log else [],
            }


# ══════════════════════════════════════════════════════════════════════════════
#  6. Convenience functions
# ══════════════════════════════════════════════════════════════════════════════


def analyze_knowledge() -> dict:
    """Full analysis: schema + gaps + relations + coverage."""
    _ensure()
    schema = schema_analyzer.analyze_schema()
    gaps = gap_detector.detect_gaps()
    relations = relation_inferrer.infer_relations()
    coverage_score = gap_detector.get_coverage_score()

    gap_summary: Counter = Counter()
    for g in gaps:
        gap_summary[g["type"]] += 1

    return {
        "schema": schema,
        "gaps": {
            "total": len(gaps),
            "by_type": dict(gap_summary.most_common()),
            "top_priority": gap_detector.get_gap_priority()[:20],
        },
        "relations": {
            "new_inferred": len(relations),
            "types": relation_inferrer.get_relation_types(),
        },
        "coverage_score": coverage_score,
        "timestamp": _now_iso(),
    }


def get_evolution_report() -> dict:
    """Report for /system/knowledge-evolution endpoint."""
    _ensure()
    schema = schema_analyzer.analyze_schema()
    type_dist = schema_analyzer.get_type_distribution()
    gaps = gap_detector.detect_gaps()
    coverage = gap_detector.get_coverage_score()
    growth = evolution_tracker.get_growth_metrics()
    drift = evolution_tracker.detect_drift()
    enrichment_stats = auto_enricher.get_enrichment_stats()
    inconsistencies = schema_analyzer.detect_inconsistencies()

    gap_summary: Counter = Counter()
    for g in gaps:
        gap_summary[g["type"]] += 1

    return {
        "overview": {
            "total_entities": schema.get("total", 0),
            "type_distribution": type_dist,
            "coverage_score": coverage,
            "total_gaps": len(gaps),
        },
        "schema": {
            "field_coverage": schema_analyzer.get_field_coverage(),
            "suggestions": schema_analyzer.suggest_schema_additions()[:10],
            "inconsistencies": inconsistencies[:10],
        },
        "gaps": {
            "by_type": dict(gap_summary.most_common()),
            "top_priority": gap_detector.get_gap_priority()[:15],
        },
        "evolution": {
            "growth": growth,
            "drift": drift,
            "recent_changes": evolution_tracker.get_changelog(days=7),
        },
        "enrichments": enrichment_stats,
        "relations": {
            "types": relation_inferrer.get_relation_types(),
            "total": len(relation_inferrer._relations),
        },
        "timestamp": _now_iso(),
    }


def get_knowledge_score() -> dict:
    """Overall health score with breakdown."""
    _ensure()
    entities = _content_entities()
    total = len(entities)
    if total == 0:
        return {"overall": 0, "breakdown": {}, "grade": "F"}

    # Sub-scores (all 0-100)
    coverage = gap_detector.get_coverage_score()

    # Completeness: % of entities with all important fields
    important = ["summary", "placeId", "type"]
    complete = 0
    for e in entities.values():
        if all(e.get(f) for f in important):
            complete += 1
    completeness = round((complete / total) * 100, 1)

    # Freshness: % updated in last 180 days
    fresh = 0
    for e in entities.values():
        updated = e.get("updatedAt")
        if updated and _days_since(updated) <= 180:
            fresh += 1
    freshness = round((fresh / total) * 100, 1)

    # Richness: average description length score
    desc_scores = []
    for e in entities.values():
        s = e.get("summary", "")
        desc_scores.append(min(100, len(s) * 2))  # 50 chars = 100
    richness = round(sum(desc_scores) / len(desc_scores), 1) if desc_scores else 0

    # Connectivity: % of entities with relations
    rels = _get_relationships()
    related_ids = set()
    for r in rels:
        related_ids.add(r.get("from"))
        related_ids.add(r.get("to"))
    connected = sum(1 for eid in entities if eid in related_ids)
    connectivity = round((connected / total) * 100, 1) if total else 0

    # Confidence: average confidence score
    conf_vals = [e.get("confidence", 0) for e in entities.values() if e.get("confidence")]
    confidence = round((sum(conf_vals) / len(conf_vals)) * 100, 1) if conf_vals else 0

    # Diversity: how many types are well-represented (>= 5)
    type_dist = SchemaAnalyzer().get_type_distribution()
    well_represented = sum(1 for t in CARD_TYPES if type_dist.get(t, 0) >= 5)
    diversity = round((well_represented / len(CARD_TYPES)) * 100, 1) if CARD_TYPES else 0

    # Overall weighted average
    weights = {
        "coverage": 0.20,
        "completeness": 0.20,
        "freshness": 0.15,
        "richness": 0.15,
        "connectivity": 0.10,
        "confidence": 0.10,
        "diversity": 0.10,
    }
    breakdown = {
        "coverage": coverage,
        "completeness": completeness,
        "freshness": freshness,
        "richness": richness,
        "connectivity": connectivity,
        "confidence": confidence,
        "diversity": diversity,
    }

    overall = sum(breakdown[k] * w for k, w in weights.items())
    overall = round(overall, 1)

    # Grade
    if overall >= 90:
        grade = "A"
    elif overall >= 75:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "overall": overall,
        "breakdown": breakdown,
        "weights": weights,
        "grade": grade,
        "total_entities": total,
        "timestamp": _now_iso(),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Module singletons
# ══════════════════════════════════════════════════════════════════════════════

schema_analyzer = SchemaAnalyzer()
relation_inferrer = RelationInferrer()
gap_detector = KnowledgeGapDetector()
evolution_tracker = EvolutionTracker()
auto_enricher = AutoEnricher()
