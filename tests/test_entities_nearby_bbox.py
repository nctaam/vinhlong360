"""Tests for bounding-box + heapq nearby entity selection in agent/entities/api.py."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from entities import api as entities_api  # noqa: E402


class TestEntitiesNearbyBbox(unittest.TestCase):
    def test_select_nearby_matches_naive_haversine_scan(self):
        center = [10.254, 105.972]
        entities = [
            {"id": "self", "name": "Self", "type": "attraction", "coordinates": [10.254, 105.972]},
            {"id": "near-1", "name": "Near 1", "type": "attraction", "coordinates": [10.260, 105.975]},
            {"id": "near-2", "name": "Near 2", "type": "dish", "coordinates": [10.270, 105.980]},
            {"id": "edge", "name": "Edge", "type": "craft_village", "coordinates": [10.295, 105.995]},
            {"id": "far-ben-tre", "name": "Far BT", "type": "attraction", "coordinates": [10.10, 106.40]},
            {"id": "far-tra-vinh", "name": "Far TV", "type": "attraction", "coordinates": [9.93, 106.34]},
            {"id": "no-coords", "name": "Missing", "type": "dish", "coordinates": None},
            {"id": "bad-coords", "name": "Bad", "type": "dish", "coordinates": ["x", None]},
        ]

        radius_km = 6.0
        limit = 2

        fast = entities_api._select_nearby_entities(
            center, entities, exclude_id="self", radius_km=radius_km, limit=limit
        )

        # Reference naive full scan
        naive = []
        for e in entities:
            if e["id"] == "self":
                continue
            coords = e.get("coordinates")
            if not coords or not isinstance(coords, list) or not all(isinstance(v, (int, float)) for v in coords):
                continue
            d = entities_api._haversine_km(center, coords)
            if d <= radius_km:
                naive.append({
                    "id": e["id"],
                    "name": e["name"],
                    "type": e.get("type"),
                    "distance_km": round(d, 2),
                    "coordinates": coords,
                })
        naive.sort(key=lambda item: item["distance_km"])

        self.assertEqual(fast, naive[:limit])

    def test_select_nearby_invalid_center_returns_empty(self):
        self.assertEqual(
            entities_api._select_nearby_entities(
                [None, 105.9],  # type: ignore[list-item]
                [{"id": "e1", "name": "A", "coordinates": [10.2, 105.9]}],
                exclude_id="self",
                radius_km=10.0,
                limit=5,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
