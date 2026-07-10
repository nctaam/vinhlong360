from __future__ import annotations

from pathlib import Path

import gpt55_quality_burst as q


def sample_data() -> dict:
    return {
        "entities": [
            {"id": "p-vl", "type": "place", "name": "Phuong Vinh Long", "area": "vinh-long", "coordinates": [10.1, 106.0]},
            {"id": "p-bt", "type": "place", "name": "Phuong Ben Tre", "area": "ben-tre", "coordinates": [10.2, 106.3]},
            {"id": "e-source", "type": "product", "name": "Dac san A", "area": "vinh-long", "summary": "Summary", "placeId": "p-vl", "coordinates": [10.1, 106.0]},
            {"id": "e-placeid", "type": "dish", "name": "Mon B", "area": "vinh-long", "summary": "Gan Phuong Vinh Long", "source": {"title": "s", "url": "https://example.com"}, "coordinates": [10.1, 106.0]},
            {"id": "e-location", "type": "attraction", "name": "Diem C", "area": "tra-vinh", "summary": "Summary", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-vl"},
            {"id": "e-eval", "type": "attraction", "name": "Diem D", "area": "vinh-long", "summary": "Summary", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-vl", "coordinates": [10.12, 106.01]},
            {"id": "e-prod", "type": "product", "name": "San pham E", "area": "ben-tre", "summary": "OCOP", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-bt", "coordinates": [10.2, 106.3]},
            {"id": "e-acc", "type": "accommodation", "name": "Luu tru F", "area": "tra-vinh", "summary": "Hotel", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-bt", "coordinates": [9.9, 106.2]},
            {"id": "e-dish", "type": "dish", "name": "Mon G", "area": "tra-vinh", "summary": "Khmer food", "source": {"title": "s", "url": "https://example.com"}, "placeId": "p-bt", "coordinates": [9.92, 106.22]},
        ],
        "relationships": [
            {"from": "e-eval", "to": "e-prod", "type": "related_to"},
            {"from": "e-location", "to": "e-dish", "type": "near"},
        ],
        "itineraries": [],
    }


def test_candidate_schema_and_policy_require_source_url() -> None:
    assert q.classify_apply_policy(0.95, [], verified=True, requires_url=True) == "needs_review"
    assert q.classify_apply_policy(0.95, ["https://example.com"], verified=True, requires_url=True) == "auto_apply"

    record = q.make_candidate_record(
        entity_id="",
        field="source",
        current_value=None,
        suggested_value=None,
        confidence=1.2,
        evidence_urls=["not-a-url"],
        reason="bad",
        apply_policy="auto_apply",
        stream="source",
    )
    assert record["apply_policy"] == "reject"
    assert "schema_errors" in record


def test_enforce_apply_policy_requires_verified_source_and_geocoder() -> None:
    source = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "source",
        "confidence": 0.95,
        "evidence_urls": ["https://example.com"],
        "url_verified": False,
        "apply_policy": "auto_apply",
    })
    assert source["apply_policy"] == "needs_review"

    location = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "coordinates",
        "confidence": 0.95,
        "suggested_value": [10.1, 106.1],
        "geocode_verified": False,
        "apply_policy": "auto_apply",
    })
    assert location["apply_policy"] == "needs_review"

    place_id = q.enforce_apply_policy({
        "entity_id": "e1",
        "field": "placeId",
        "confidence": 0.95,
        "suggested_value": "xa-an-binh",
        "apply_policy": "auto_apply",
    })
    assert place_id["apply_policy"] == "needs_review"

def test_manifest_shards_prioritize_non_place_sources() -> None:
    manifest = q.build_manifest(sample_data(), chunk_size=1, relationship_chunk_size=1)
    counts = manifest["counts"]
    assert counts["missing_source"] == 3
    assert counts["missing_source_non_place"] == 1
    assert counts["missing_source_place"] == 2
    assert counts["missing_place_id"] == 1
    source_shards = manifest["streams"]["source"]
    assert source_shards[0]["priority"] == "non_place_first"
    assert source_shards[-1]["priority"] == "place_second"
    assert manifest["streams"]["relationship"]


def test_placeid_area_conflict_rejects_candidate() -> None:
    data = sample_data()
    place_by_id = {e["id"]: e for e in data["entities"] if e["type"] == "place"}
    entity = next(e for e in data["entities"] if e["id"] == "e-placeid")
    record = q.placeid_candidate_from_decision(entity, {"candidate_place_id": "p-bt", "confidence": 0.96, "evidence": "looks close"}, place_by_id)
    assert record["apply_policy"] == "reject"
    assert record["area_conflict"] is True


def test_location_ignores_llm_coordinates_and_uses_geocoder() -> None:
    entity = {"id": "e-location", "type": "attraction", "name": "Diem C", "area": "tra-vinh"}
    decision = {"geocode_query": "Diem C, Tra Vinh", "coordinates": [1, 2], "confidence": 0.95, "reason": "query"}

    no_hit = q.location_candidate_from_decision(entity, decision, geocode_fn=lambda *_args: None)
    assert no_hit["suggested_value"] is None
    assert no_hit["apply_policy"] == "reject"
    assert no_hit["llm_supplied_coordinates_ignored"] is True

    hit = q.location_candidate_from_decision(entity, decision, geocode_fn=lambda *_args: [9.9, 106.2])
    assert hit["suggested_value"] == [9.9, 106.2]
    assert hit["apply_policy"] == "auto_apply"


def test_merge_outputs_dedupes_highest_confidence(tmp_path: Path) -> None:
    low = q.make_candidate_record(
        entity_id="e1", field="source", current_value=None, suggested_value={"url": "https://example.com/a"},
        confidence=0.72, evidence_urls=["https://example.com/a"], reason="low", apply_policy="needs_review", stream="source",
    )
    high = q.make_candidate_record(
        entity_id="e1", field="source", current_value=None, suggested_value={"url": "https://example.com/a"},
        confidence=0.91, evidence_urls=["https://example.com/a"], reason="high", apply_policy="auto_apply", stream="source",
        extra={"url_verified": True},
    )
    q.write_jsonl(tmp_path / q.STREAM_FILES["source"], [low, high])
    queue = q.merge_outputs(tmp_path)
    assert queue["counts"]["raw_records"] == 2
    assert queue["counts"]["deduped_records"] == 1
    assert queue["auto_apply"][0]["reason"] == "high"
    assert (tmp_path / q.REVIEW_QUEUE_FILE).exists()
    assert (tmp_path / q.SUMMARY_FILE).exists()


def test_generated_eval_cases_have_valid_shape() -> None:
    data = sample_data()
    cases = q.generate_heuristic_eval_cases(data, case_target=5)
    entity_ids = {e["id"] for e in data["entities"]}
    assert cases
    assert all(q.valid_eval_case(case, entity_ids) for case in cases)


def test_relationship_low_confidence_rejects_even_with_risk() -> None:
    item = {"index": 1, "source_id": "a", "target_id": "b", "rel_type": "hosts", "heuristic_reasons": ["missing proof"]}
    record = q.relationship_record_from_status(item, "needs_review", 0.35, "missing proof")
    assert record["risk"] == "high"
    assert record["apply_policy"] == "reject"


def test_merge_enforces_low_confidence_reject(tmp_path: Path) -> None:
    bad_policy = q.make_candidate_record(
        entity_id="e2", field="relationship", current_value={}, suggested_value={"risk": "medium"},
        confidence=0.35, evidence_urls=[], reason="weak", apply_policy="needs_review", stream="relationship",
    )
    q.write_jsonl(tmp_path / q.STREAM_FILES["relationship"], [bad_policy])
    queue = q.merge_outputs(tmp_path)
    assert queue["counts"]["needs_review"] == 0
    assert queue["counts"]["reject"] == 1
