"""Canonical public search contract.

The database remains the source of truth for filtering, while this module owns
the text normalization, complete-catalog ranking, and page metadata shared by
the public search and autocomplete surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import re
import unicodedata
from typing import Any


RANKING_VERSION = "search-v1"


def coerce_query_int(value: Any, default: int) -> int:
    """Coerce FastAPI ``Query`` defaults for direct Python endpoint calls."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    raw = getattr(value, "default", value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def normalize_search_text(value: str | Any) -> str:
    """Return one accent-insensitive, case-folded, whitespace-stable string."""
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class SearchFilters:
    entity_type: str | None = None
    area: str | None = None
    entity_types: tuple[str, ...] = ()
    month: int | None = None
    public_only: bool = True


@dataclass(frozen=True)
class SearchPage:
    items: list[dict[str, Any]]
    total: int
    offset: int
    limit: int
    truncated: bool = False
    ranking_version: str = RANKING_VERSION


def _source_text(entity: Mapping[str, Any]) -> str:
    source = entity.get("source")
    values: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, Mapping):
            for key in ("title", "name", "url"):
                if value.get(key):
                    values.append(str(value[key]))
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect(item)
        elif value:
            values.append(str(value))

    collect(source)
    return normalize_search_text(" ".join(values))


def _contains_all_terms(text: str, terms: tuple[str, ...]) -> bool:
    return bool(terms) and all(term in text for term in terms)


def _matches_text(query: str, text: str, terms: tuple[str, ...]) -> bool:
    return query in text or _contains_all_terms(text, terms)


def _rank(entity: Mapping[str, Any], query: str) -> tuple[float, str] | None:
    qn = normalize_search_text(query)
    if not qn:
        return float(entity.get("confidence") or 0), "catalog"
    terms = tuple(part for part in qn.split(" ") if part)
    name = normalize_search_text(entity.get("name", ""))
    summary = normalize_search_text(entity.get("summary", ""))
    source = _source_text(entity)

    if name == qn:
        return 1000.0, "exact_name"
    if name.startswith(qn):
        return 900.0, "name_prefix"
    if qn in name:
        return 800.0, "name_contains"
    if _contains_all_terms(name, terms):
        return 750.0, "name_terms"
    if _matches_text(qn, summary, terms):
        return 500.0, "summary"
    if _matches_text(qn, source, terms):
        return 300.0, "source"
    return None


def _db_filters(filters: SearchFilters) -> dict[str, Any]:
    values: dict[str, Any] = {
        "entity_type": filters.entity_type,
        "area": filters.area,
        "month": filters.month,
        "public_only": filters.public_only,
    }
    if filters.entity_types:
        values["entity_types"] = list(filters.entity_types)
    return {key: value for key, value in values.items() if value is not None}


def search_public_entities(
    query: str,
    *,
    offset: int,
    limit: int,
    filters: SearchFilters,
    database: Any | None = None,
    bounded: bool = False,
) -> SearchPage:
    """Search the complete filtered relation, rank it, then slice one page.

    ``database`` is injectable for tests and alternate read replicas. Production
    callers use the database singleton lazily to avoid import cycles.
    """
    if database is None:
        from database import db as database
    offset = max(int(offset or 0), 0)
    limit = max(int(limit or 1), 1)
    matched, truncated = rank_public_entity_catalog(
        query, filters=filters, database=database, bounded=bounded,
        fetch_limit=(offset + limit) if bounded else None,
    )
    return SearchPage(
        items=matched[offset:offset + limit],
        total=len(matched),
        offset=offset,
        limit=limit,
        truncated=truncated,
    )


def _catalog_rows(database: Any, query: str | None, db_kwargs: dict[str, Any], *, bounded: bool,
                  fetch_limit: int | None) -> tuple[list[dict[str, Any]], int]:
    try:
        relation_total = int(database.count_entities_filtered(q=query or None, **db_kwargs))
    except (AttributeError, TypeError):
        relation_total = 0
    fetch_size = max(relation_total, 1)
    if bounded:
        fetch_size = min(fetch_size, max(fetch_limit or 1, 1))
    if hasattr(database, "search_entities"):
        rows = database.search_entities(q=query or None, limit=fetch_size, offset=0, **db_kwargs)
    else:
        rows = database.list_entities(limit=fetch_size, offset=0, **db_kwargs)
    return list(rows), relation_total


def _rank_catalog_rows(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    ranked: list[tuple[float, str, int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        score = _rank(row, query)
        if score is None:
            continue
        numeric, reason = score
        item = dict(row)
        item["_search_meta"] = {
            "score": round(numeric + float(row.get("confidence") or 0) * 0.01, 4),
            "reason": reason,
            "ranking_version": RANKING_VERSION,
        }
        ranked.append((numeric, str(item.get("id") or ""), index, item))
    ranked.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
    return [entry[3] for entry in ranked]


def rank_public_entity_catalog(
    query: str,
    *,
    filters: SearchFilters,
    database: Any | None = None,
    bounded: bool = False,
    fetch_limit: int | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Return the complete ranked public catalog before page slicing.

    Advanced consumers that apply a second predicate (for example media
    presence or a non-relevance sort) must use this relation-level result;
    slicing first would make later pages and totals dishonest.
    """
    if database is None:
        from database import db as database
    db_kwargs = _db_filters(filters)
    count_query = query or None
    rows, relation_total = _catalog_rows(
        database, count_query, db_kwargs, bounded=bounded, fetch_limit=fetch_limit,
    )
    matched = _rank_catalog_rows(rows, query)
    return matched, bounded and len(rows) < relation_total
