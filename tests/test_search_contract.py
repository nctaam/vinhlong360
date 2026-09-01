"""Task 9 red/green contract tests for canonical search and data quality."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from database import normalize_entity
from search_contract import SearchFilters, normalize_search_text, search_public_entities
from semantic_cache import SemanticMatcher


@dataclass
class _Catalog:
    rows: list[dict]

    def list_entities(self, **kwargs):
        self.list_kwargs = kwargs
        return list(self.rows)

    def count_entities_filtered(self, **kwargs):
        return len(self.rows)


def test_normalize_search_text_folds_accents_case_and_whitespace():
    assert normalize_search_text("  DỪA\u00a0   Sáp ") == "dua sap"


def test_search_ranks_exact_name_before_summary_and_source_matches():
    catalog = _Catalog([
        {"id": "summary", "type": "product", "name": "Món miền Tây", "summary": "dừa sáp ngon", "confidence": 1.0},
        {"id": "source", "type": "product", "name": "Đặc sản", "summary": "", "source": [{"title": "Dừa sáp"}], "confidence": 1.0},
        {"id": "exact", "type": "product", "name": "Dừa Sáp", "summary": "", "confidence": 0.1},
    ])

    page = search_public_entities("dua sap", offset=0, limit=10, filters=SearchFilters(), database=catalog)

    assert page.items[0]["id"] == "exact"
    assert page.ranking_version
    assert page.total == 3
    assert page.truncated is False


def test_full_catalog_offset_is_not_capped_at_500():
    rows = [
        {"id": f"entity-{i:04d}", "type": "product", "name": f"Sản phẩm {i}", "summary": ""}
        for i in range(501)
    ]
    catalog = _Catalog(rows)

    page = search_public_entities("", offset=500, limit=50, filters=SearchFilters(), database=catalog)

    assert page.items[0]["id"] == "entity-0500"
    assert page.total == 501
    assert page.offset == 500
    assert page.limit == 50
    assert page.truncated is False
    assert catalog.list_kwargs["limit"] >= 501


def test_verified_at_round_trip_uses_nested_canonical_field():
    row = normalize_entity({"verifiedAt": "2026-08-31T00:00:00Z", "attributes": {"verifiedAt": None}})

    assert row["attributes"]["verifiedAt"] == "2026-08-31T00:00:00Z"
    assert "verifiedAt" not in row


def test_zero_denominator_quality_is_not_applicable():
    from scripts.validate_data import coverage_metric

    assert coverage_metric(0, 0) == {"value": None, "status": "not_applicable"}
    assert coverage_metric(3, 4) == {"value": 75.0, "status": "measured"}


def test_replacing_semantic_cache_document_does_not_inflate_document_frequency():
    matcher = SemanticMatcher()

    matcher.add("same-key", "dua sap")
    matcher.add("same-key", "cam sanh")

    assert matcher._doc_count == 1
    assert matcher._df["dua"] == 0
    assert matcher._df["cam"] == 1
    assert matcher.replacements == 1
