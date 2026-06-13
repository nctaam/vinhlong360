from __future__ import annotations

import data_quality as dq


def test_entity_quality_reports_source_location_and_missing_fields() -> None:
    quality = dq.entity_quality({
        "id": "e1",
        "type": "product",
        "source": {"title": "Source", "url": "https://example.com/source"},
        "coordinates": [10.1, 106.1],
    })

    assert quality["has_source"] is True
    assert quality["has_location"] is True
    assert quality["has_place"] is False
    assert quality["missing"] == ["placeId"]
    assert quality["source_url"] == "https://example.com/source"


def test_filter_candidates_by_kind_and_bucket() -> None:
    queue = {
        "auto_apply": [
            {"entity_id": "e1", "field": "source", "confidence": 0.95},
            {"entity_id": "e2", "field": "coordinates", "confidence": 0.95},
        ],
        "needs_review": [{"entity_id": "e3", "field": "placeId", "confidence": 0.8}],
        "reject": [{"entity_id": "e4", "field": "entity_accuracy", "confidence": 0.2}],
    }

    result = dq.filter_candidates(queue, kind="source", bucket="auto_apply")

    assert result["total"] == 1
    assert result["candidates"][0]["entity_id"] == "e1"
    assert result["candidates"][0]["kind"] == "source"
    assert result["candidates"][0]["candidate_id"]


def test_apply_candidates_dry_run_only_evidence_auto_apply(monkeypatch) -> None:
    queue = {
        "auto_apply": [
            {
                "entity_id": "e1",
                "field": "source",
                "suggested_value": {"title": "Verified", "url": "https://example.com/verified"},
                "confidence": 0.95,
                "evidence_urls": ["https://example.com/verified"],
                "url_verified": True,
                "apply_policy": "auto_apply",
            },
            {
                "entity_id": "e2",
                "field": "coordinates",
                "suggested_value": [10.2, 106.2],
                "confidence": 0.95,
                "evidence_urls": [],
                "geocode_verified": True,
                "apply_policy": "auto_apply",
            },
            {
                "entity_id": "e3",
                "field": "placeId",
                "suggested_value": "xa-an-binh",
                "confidence": 0.95,
                "apply_policy": "auto_apply",
            },
        ]
    }
    data = {"entities": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}], "relationships": [], "itineraries": []}

    monkeypatch.setattr(dq, "load_candidate_queue", lambda refresh=True: queue)
    monkeypatch.setattr(dq, "load_data", lambda: data)

    result = dq.apply_candidates(dry_run=True)

    assert result["applied_count"] == 2
    assert result["backup"] is None
    assert {item["field"] for item in result["applied"]} == {"source", "coordinates"}
    assert "source" not in data["entities"][0]
    assert "coordinates" not in data["entities"][1]
