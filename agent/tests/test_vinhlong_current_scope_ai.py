import json


def _tool_by_name(tools, name):
    return next(tool for tool in tools if tool["function"]["name"] == name)


def test_current_ai_tools_expose_only_vinh_long_as_selectable_area():
    from tools import TOOLS

    current_tools = {
        "search",
        "list_itineraries",
        "places_in_area",
        "ocop_products",
        "accommodation_search",
        "generate_itinerary",
        "weather",
    }
    for name in current_tools:
        tool = _tool_by_name(TOOLS, name)
        properties = tool["function"]["parameters"]["properties"]
        field = "areas" if name == "generate_itinerary" else "area"
        schema = properties[field]
        if field == "areas":
            schema = schema["items"]
        assert schema["enum"] == ["vinh-long"]


def test_agentic_area_detection_maps_legacy_names_to_current_province():
    from agentic_rag import _detect_areas

    assert _detect_areas("du lịch Bến Tre") == ["vinh-long"]
    assert _detect_areas("khám phá Trà Vinh") == ["vinh-long"]
    assert _detect_areas("đi Vĩnh Long") == ["vinh-long"]


def test_legacy_tool_area_arguments_normalize_to_current_scope():
    import knowledge

    assert knowledge.normalize_current_area("ben-tre") == "vinh-long"
    assert knowledge.normalize_current_area("tra-vinh") == "vinh-long"
    assert knowledge.normalize_current_areas(["ben-tre", "vinh-long", "tra-vinh"]) == ["vinh-long"]


def test_chat_area_match_current_scope_includes_legacy_subregions(monkeypatch):
    import chat.api as chat_api

    places = {
        "entity-bt": {"id": "place-bt", "area": "ben-tre", "parentId": "vinh-long", "level": "xa"},
        "entity-tv": {"id": "place-tv", "area": "tra-vinh", "parentId": "vinh-long", "level": "phuong"},
    }
    monkeypatch.setattr(chat_api.knowledge, "_ensure", lambda: None)
    monkeypatch.setattr(chat_api.knowledge, "get_place", lambda entity_id: places.get(entity_id))

    assert chat_api._area_matches({"id": "entity-bt"}, {}, "vinh-long") is True
    assert chat_api._area_matches({"id": "entity-tv"}, {}, "vinh-long") is True


def test_itinerary_generator_defaults_to_current_province(monkeypatch):
    from itineraries import itinerary_gen

    captured = {}

    monkeypatch.setattr(itinerary_gen.knowledge, "_ensure", lambda: None)
    def _collect(interests, areas, month, budget):
        captured["collect"] = areas
        return []

    monkeypatch.setattr(itinerary_gen, "_collect_candidates", _collect)
    monkeypatch.setattr(itinerary_gen, "_select_diverse", lambda *args: [])
    monkeypatch.setattr(itinerary_gen, "_build_joint_day_plans", lambda *args: [])
    monkeypatch.setattr(itinerary_gen, "_gen_tips", lambda interests, areas, month, budget: [])
    monkeypatch.setattr(itinerary_gen, "_build_title", lambda days, interests, areas: "test")

    result = itinerary_gen.generate_itinerary()

    assert captured["collect"] == ["vinh-long"]
    assert result["areas"] == ["vinh-long"]


def test_places_tool_returns_all_124_current_children(monkeypatch):
    import chat.api as chat_api

    children = [
        {"id": f"place-{i}", "name": f"Đơn vị {i}", "level": "phuong" if i < 35 else "xa", "legacyArea": ""}
        for i in range(124)
    ]
    monkeypatch.setattr(chat_api.knowledge, "current_places", lambda: children)
    monkeypatch.setattr(chat_api.knowledge, "_entities", {})

    result = json.loads(chat_api._tool_places_in_area({"area": "vinh-long"}))

    assert len(result) == 124
    assert sum(item["level"] == "phuong" for item in result) == 35
    assert sum(item["level"] == "xa" for item in result) == 89
