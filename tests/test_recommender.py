"""Paired unit tests for agent/recommender.py (Haversine geo + MMR diversity)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

import recommender  # noqa: E402


def _make_entities():
    return {
        "p-vl": {"id": "p-vl", "type": "place", "name": "Long Hồ", "area": "vinh-long"},
        "src": {
            "id": "src",
            "type": "attraction",
            "name": "Chùa Tiên Châu",
            "placeId": "p-vl",
            "tags": ["chua", "di-tich", "song-nuoc"],
            "coordinates": {"lat": 10.265, "lng": 105.975},
            "confidence": 0.9,
        },
        # Very close entity (~0.8 km)
        "near-dish": {
            "id": "near-dish",
            "type": "dish",
            "name": "Bánh xèo An Bình",
            "placeId": "p-vl",
            "tags": ["song-nuoc", "am-thuc"],
            "coordinates": {"lat": 10.270, "lng": 105.980},
            "confidence": 0.85,
        },
        # Duplicate attraction clones (identical type + same tags -> MMR should demote second clone)
        "clone-1": {
            "id": "clone-1",
            "type": "attraction",
            "name": "Chùa cổ A",
            "placeId": "p-vl",
            "tags": ["chua", "di-tich", "song-nuoc"],
            "coordinates": {"lat": 10.268, "lng": 105.976},
            "confidence": 0.88,
        },
        "clone-2": {
            "id": "clone-2",
            "type": "attraction",
            "name": "Chùa cổ B",
            "placeId": "p-vl",
            "tags": ["chua", "di-tich", "song-nuoc"],
            "coordinates": {"lat": 10.269, "lng": 105.977},
            "confidence": 0.87,
        },
        # Farther away (> 60 km) with same type/tag should lose geo bonus vs near entity
        "far-attr": {
            "id": "far-attr",
            "type": "attraction",
            "name": "Điểm xa",
            "placeId": "p-vl",
            "tags": ["chua"],
            "coordinates": {"lat": 9.65, "lng": 106.45},
            "confidence": 0.85,
        },
    }


def test_haversine_geo_proximity_boosts_nearby_entity():
    entities = _make_entities()
    recs = recommender.recommend_by_entity("src", entities, relationships=[], limit=5)
    by_id = {r["id"]: r for r in recs}
    assert "nearby_geo" in by_id["near-dish"]["reason"]
    assert "nearby_geo" not in by_id["far-attr"]["reason"]
    assert by_id["clone-1"]["score"] > by_id["far-attr"]["score"]


def test_mmr_diversifies_redundant_type_clones():
    entities = _make_entities()
    recs = recommender.recommend_by_entity("src", entities, relationships=[], limit=2)
    ids = [r["id"] for r in recs]
    assert ids[0] == "clone-1"
    # Second pick must diversify away from clone-2 (which is redundant with clone-1)
    assert ids[1] == "near-dish"


def test_recommend_without_coordinates_stays_stable():
    entities = {
        "p-1": {"id": "p-1", "type": "place", "name": "Phường 1", "area": "vinh-long"},
        "a": {"id": "a", "type": "dish", "name": "Bánh ít", "placeId": "p-1", "tags": ["banh"]},
        "b": {"id": "b", "type": "dish", "name": "Bánh tét", "placeId": "p-1", "tags": ["banh"]},
    }
    recs = recommender.recommend_by_entity("a", entities, relationships=[], limit=5)
    assert [r["id"] for r in recs] == ["b"]
