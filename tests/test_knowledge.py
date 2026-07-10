"""Tests for the knowledge layer (agent/knowledge.py)."""
import pytest
import knowledge


@pytest.fixture(autouse=True)
def ensure_loaded():
    """KB thật được nạp trước mỗi test, độc lập thứ tự collection.

    _ensure() là no-op nếu _entities đã set → nếu test khác (thứ tự khác) để
    KB global rỗng/nhỏ thì các test data-thật thấy 0 (flaky). reload() khôi
    phục KB thật từ DB; chỉ reload khi nghi pollution để giữ tốc độ.
    """
    if not knowledge._entities or len(knowledge._entities) < 100:
        knowledge.reload()
    if not knowledge._entities or len(knowledge._entities) < 100:
        # reload() nạp từ DB; dưới Postgres test-DB (CI) chưa seed entity → KB rỗng.
        # Test knowledge-layer cần data THẬT — skip khi không có (SQLite/prod-PG vẫn chạy).
        pytest.skip("KB data không sẵn (DB rỗng — vd Postgres test-DB chưa seed entity)")


def _sample_entity_id() -> str:
    """Return a sample non-place entity ID from the loaded data."""
    for eid, e in knowledge._entities.items():
        if e["type"] != "place":
            return eid
    pytest.skip("No non-place entities in data")


def _sample_entity_with_place() -> str:
    """Return entity ID that has a placeId."""
    for eid, e in knowledge._entities.items():
        if e["type"] != "place" and e.get("placeId"):
            return eid
    pytest.skip("No entity with placeId found")


# ── Loading ──

def test_ensure_loads_data():
    knowledge._ensure()
    assert knowledge._entities is not None
    assert len(knowledge._entities) > 0


# ── search_entities ──

def test_search_entities_basic():
    # "cam" should match entities whose name/summary contain "cam" (case-insensitive)
    results = knowledge.search_entities(q="cam")
    assert isinstance(results, list)
    # Verify we got results
    assert len(results) > 0


def test_search_entities_by_type():
    results = knowledge.search_entities(entity_type="product")
    assert isinstance(results, list)
    for r in results:
        assert r["type"] == "product"


def test_search_entities_by_area():
    results = knowledge.search_entities(area="vinh-long")
    assert isinstance(results, list)
    # Every result should belong to the vinh-long area
    for r in results:
        place = knowledge.get_place(r["id"])
        assert place is not None
        assert place.get("area") == "vinh-long"


# ── get_entity ──

def test_get_entity():
    eid = _sample_entity_id()
    entity = knowledge.get_entity(eid)
    assert entity is not None
    assert "name" in entity
    assert "type" in entity


def test_get_entity_not_found():
    result = knowledge.get_entity("nonexistent-entity-id-12345")
    assert result is None


# ── entity_detail ──

def test_entity_detail():
    eid = _sample_entity_id()
    detail = knowledge.entity_detail(eid)
    assert detail is not None
    assert "related" in detail
    assert "place_name" in detail


# ── places ──

def test_places():
    result = knowledge.places()
    assert isinstance(result, list)
    assert len(result) > 0
    for p in result:
        assert p["type"] == "place"


def test_places_by_area():
    result = knowledge.places("ben-tre")
    assert isinstance(result, list)
    for p in result:
        assert p.get("area") == "ben-tre"


# ── stats ──

def test_stats():
    result = knowledge.stats()
    assert isinstance(result, dict)
    assert "total_content" in result
    assert "by_type" in result
    assert result["total_content"] > 0


# ── compare_areas ──

def test_compare_areas():
    result = knowledge.compare_areas("vinh-long", "ben-tre")
    assert "area_1" in result
    assert "area_2" in result
    assert result["area_1"]["area"] == "vinh-long"
    assert result["area_2"]["area"] == "ben-tre"


# ── nearby_entities ──

def test_nearby_entities():
    eid = _sample_entity_with_place()
    result = knowledge.nearby_entities(eid)
    assert isinstance(result, list)
    # Nearby should return other entities (may be empty for isolated entities)


# ── related ──

def test_related():
    eid = _sample_entity_id()
    result = knowledge.related(eid)
    assert isinstance(result, list)


# ── seasonal_now ──

def test_seasonal_now():
    result = knowledge.seasonal_now(6)
    assert isinstance(result, list)
    # Can be empty if no entity has peak in month 6


# ── _normalize_vn ──

def test_normalize_vn():
    assert knowledge._normalize_vn("Vĩnh Long") == "vinh long"
    assert knowledge._normalize_vn("Bến Tre") == "ben tre"
    assert knowledge._normalize_vn("Đồng bằng") == "dong bang"
