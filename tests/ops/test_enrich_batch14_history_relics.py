# -*- coding: utf-8 -*-
"""Unit tests for Batch 14 historical relics & architectural monuments enrichment."""
import pytest
from scripts.ops.enrich_batch14_history_relics import BATCH14_DATA, apply_batch14_enrichment


def test_batch14_data_structure():
    """Verify Batch 14 contains 25 items with valid schema fields."""
    assert len(BATCH14_DATA) == 25
    for eid, payload in BATCH14_DATA.items():
        assert "key_facts" in payload, f"{eid} missing key_facts"
        assert len(payload["key_facts"]) == 3, f"{eid} key_facts count != 3"
        for fact in payload["key_facts"]:
            assert isinstance(fact, str) and len(fact) >= 20, f"{eid} invalid fact"
        assert "hours" in payload, f"{eid} missing hours"
        assert "admission" in payload, f"{eid} missing admission"
        assert "travel_tip" in payload, f"{eid} missing travel_tip"
        assert "source_citations" in payload, f"{eid} missing source_citations"
        assert len(payload["source_citations"]) >= 1, f"{eid} empty source_citations"
        assert "image_caption" in payload, f"{eid} missing image_caption"
        assert "image_alt" in payload, f"{eid} missing image_alt"
        assert len(payload["image_alt"]) >= 10, f"{eid} image_alt too short"


def test_apply_batch14_enrichment():
    """Verify enrichment modifies entities in-place and sets verifiedAt."""
    mock_entities = [
        {"id": "chua-tuyen-linh-mo-cay-bac", "name": "Chùa Tuyên Linh", "attributes": {}},
        {"id": "unrelated-entity-999", "name": "Unrelated", "attributes": {}},
    ]
    count, logs = apply_batch14_enrichment(mock_entities)
    assert count == 1
    assert len(logs) == 1
    target = mock_entities[0]["attributes"]
    assert target["verified"] is True
    assert target["verifiedAt"] == "2026-09-19"
    assert "key_facts" in target
    assert "image_alt" in target
    assert "image_caption" in target
