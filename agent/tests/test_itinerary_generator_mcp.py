import json
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_server


def test_generate_itinerary_documents_empty_meal_anchors_disable_insertion():
    source = inspect.getsource(mcp_server.generate_itinerary)
    assert "[]" in source
    assert "disable" in source.lower() or "tắt" in source.lower()


def test_generate_itinerary_forwards_anchor_arguments(monkeypatch):
    forwarded = {}

    def fake_generate_itinerary(**kwargs):
        forwarded.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(mcp_server, "_ensure_knowledge", lambda: None)
    monkeypatch.setattr(mcp_server, "_generate_itinerary", fake_generate_itinerary)
    monkeypatch.setattr(mcp_server, "HAS_ITINERARY_GEN", True)

    payload = json.loads(mcp_server.generate_itinerary(
        days=2,
        interests=["tham_quan"],
        areas=["vinh-long"],
        month=7,
        budget="thap",
        meal_anchors=["12:00"],
        rest_anchors=["15:00"],
    ))

    assert forwarded == {
        "days": 2,
        "interests": ["tham_quan"],
        "areas": ["vinh-long"],
        "month": 7,
        "budget": "thap",
        "meal_anchors": ["12:00"],
        "rest_anchors": ["15:00"],
    }
    assert payload == {"ok": True}
