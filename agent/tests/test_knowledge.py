"""
Tests for knowledge.py — the core knowledge base layer.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure agent/ on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import knowledge


class TestNormalizeVn:
    """Test Vietnamese text normalization."""

    def test_basic_normalization(self):
        assert knowledge._normalize_vn("Vĩnh Long") == "vinh long"

    def test_d_stroke(self):
        assert knowledge._normalize_vn("Đồng bằng") == "dong bang"

    def test_accents(self):
        assert knowledge._normalize_vn("Trà Vinh") == "tra vinh"

    def test_empty_string(self):
        assert knowledge._normalize_vn("") == ""

    def test_already_ascii(self):
        assert knowledge._normalize_vn("hello world") == "hello world"

    def test_mixed_case(self):
        assert knowledge._normalize_vn("CẦU MỸ THUẬN") == "cau my thuan"


class TestSeasonText:
    """Test season description generation."""

    def test_no_season(self):
        assert knowledge.season_text({}) == "quanh năm"

    def test_no_months(self):
        assert knowledge.season_text({"season": {}}) == "quanh năm"

    def test_with_months(self):
        result = knowledge.season_text({"season": {"months": [11, 12, 1]}})
        assert "tháng 11" in result
        assert "tháng 12" in result
        assert "tháng 1" in result

    def test_with_peak(self):
        result = knowledge.season_text({"season": {"months": [10, 11, 12], "peak": [11]}})
        assert "cao điểm" in result
        assert "tháng 11" in result


class TestSearchEntities:
    """Test entity search function with various filters."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        """Load sample data into knowledge module."""
        entities = {e["id"]: e for e in sample_data["entities"]}
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_search_by_text(self):
        results = knowledge.search_entities(q="cam sành")
        assert len(results) >= 1
        assert any(e["id"] == "cam-sanh-vinh-long" for e in results)

    def test_search_by_type(self):
        results = knowledge.search_entities(entity_type="dish")
        assert all(e["type"] == "dish" for e in results)

    def test_search_by_area(self):
        results = knowledge.search_entities(area="vinh-long")
        assert len(results) >= 1

    def test_search_ocop_only(self):
        results = knowledge.search_entities(ocop_only=True)
        for e in results:
            assert e.get("attributes", {}).get("ocop") is True

    def test_search_by_month(self):
        results = knowledge.search_entities(month=11)
        # cam-sanh has month 11 in season, bun-mam has no season (passes)
        assert len(results) >= 1

    def test_search_limit(self):
        results = knowledge.search_entities(limit=1)
        assert len(results) <= 1

    def test_search_no_results(self):
        results = knowledge.search_entities(q="xyz_nonexistent_12345")
        assert results == []


class TestEntityLookup:
    """Test entity retrieval functions."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        entities = {e["id"]: e for e in sample_data["entities"]}
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_get_entity(self):
        e = knowledge.get_entity("cam-sanh-vinh-long")
        assert e is not None
        assert e["name"] == "Cam sành Vĩnh Long"

    def test_get_entity_not_found(self):
        assert knowledge.get_entity("nonexistent") is None

    def test_get_place(self):
        p = knowledge.get_place("cam-sanh-vinh-long")
        assert p is not None
        assert p["type"] == "place"
        assert p["area"] == "vinh-long"

    def test_area_of(self):
        assert knowledge.area_of("cam-sanh-vinh-long") == "vinh-long"

    def test_places(self):
        ps = knowledge.places()
        # Only places with parentId are returned (xa-binh-hoa-phuoc has parentId)
        assert len(ps) >= 1
        assert all(p["type"] == "place" for p in ps)

    def test_places_filter_area(self):
        ps = knowledge.places(area="vinh-long")
        assert all(p.get("area") == "vinh-long" for p in ps)


class TestRelated:
    """Test relationship lookups."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        entities = {e["id"]: e for e in sample_data["entities"]}
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_related_forward(self):
        rels = knowledge.related("cam-sanh-vinh-long")
        assert len(rels) >= 1
        assert any(r["id"] == "xa-binh-hoa-phuoc" for r in rels)

    def test_related_backward(self):
        rels = knowledge.related("xa-binh-hoa-phuoc")
        assert len(rels) >= 1
        assert any(r["id"] == "cam-sanh-vinh-long" for r in rels)

    def test_related_none(self):
        assert knowledge.related("bun-mam") == []

    def test_related_nonexistent(self):
        assert knowledge.related("doesnt-exist") == []


class TestItineraries:
    """Test itinerary functions."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        entities = {e["id"]: e for e in sample_data["entities"]}
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_get_itinerary(self):
        it = knowledge.get_itinerary("1-ngay-vinh-long")
        assert it is not None
        assert it["days"] == 1

    def test_get_itinerary_not_found(self):
        assert knowledge.get_itinerary("nonexistent") is None

    def test_list_itineraries(self):
        its = knowledge.list_itineraries()
        assert len(its) == 1

    def test_list_itineraries_by_area(self):
        its = knowledge.list_itineraries(area="vinh-long")
        assert len(its) == 1
        its = knowledge.list_itineraries(area="ben-tre")
        assert len(its) == 0


class TestStats:
    """Test stats aggregation."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        entities = {e["id"]: e for e in sample_data["entities"]}
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_stats_structure(self):
        s = knowledge.stats()
        assert "total_content" in s
        assert "by_type" in s
        assert "places" in s
        assert "itineraries" in s
        assert s["total_content"] == 2  # product + dish
        assert s["itineraries"] == 1


class TestCompareAreas:
    """Test area comparison."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        entities = {e["id"]: e for e in sample_data["entities"]}
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_compare(self):
        result = knowledge.compare_areas("vinh-long", "tra-vinh")
        assert "area_1" in result
        assert "area_2" in result
        assert result["area_1"]["area"] == "vinh-long"
        assert result["area_2"]["area"] == "tra-vinh"
        assert result["area_1"]["total_content"] >= 1


def test_is_searchable_includes_nonadmin_place():
    """GĐ4.5: quán/nhà hàng bị gán type=place (level phi-hành-chính) phải tìm được;
    đơn vị hành chính (phuong/xa/tinh) thì không."""
    assert knowledge._is_searchable({"type": "dish"}) is True
    assert knowledge._is_searchable({"type": "place", "level": None}) is True   # quán/doanh nghiệp
    assert knowledge._is_searchable({"type": "place", "level": "phuong"}) is False
    assert knowledge._is_searchable({"type": "place", "level": "xa"}) is False


def test_is_searchable_includes_facility():
    """GĐ13: cơ quan nhà nước (facility) phải vào tìm kiếm."""
    assert knowledge._is_searchable({"type": "facility"}) is True


class TestReload:
    """GĐ11.4: reload() swap state nhất quán + làm tươi adjacency. Hợp đồng hành vi
    (giữ qua refactor background/atomic-swap)."""

    def _fake_load(self, entities, rels, itins):
        return lambda: ({e["id"]: e for e in entities}, rels, {it["id"]: it for it in itins})

    def test_reload_rebuilds_globals_from_load(self, monkeypatch):
        ents = [{"id": "x", "name": "X", "type": "dish"}]
        monkeypatch.setattr(knowledge, "_load", self._fake_load(ents, [], []))
        res = knowledge.reload()
        assert res["status"] == "ok"
        assert res["entities"] == 1
        assert knowledge.get_entity("x")["name"] == "X"

    def test_reload_refreshes_adjacency(self, monkeypatch):
        # Lần 1: A -> B
        ents = [{"id": "a", "name": "A", "type": "dish"},
                {"id": "b", "name": "B", "type": "dish"},
                {"id": "c", "name": "C", "type": "dish"}]
        monkeypatch.setattr(knowledge, "_load",
                            self._fake_load(ents, [{"from": "a", "to": "b", "type": "near"}], []))
        knowledge.reload()
        assert any(r["id"] == "b" for r in knowledge.related("a"))

        # Lần 2: A -> C (adjacency phải phản ánh cạnh mới, bỏ cạnh cũ)
        monkeypatch.setattr(knowledge, "_load",
                            self._fake_load(ents, [{"from": "a", "to": "c", "type": "near"}], []))
        knowledge.reload()
        ids = {r["id"] for r in knowledge.related("a")}
        assert "c" in ids and "b" not in ids

    def test_reload_uses_lock_and_resets_adjacency(self, monkeypatch):
        # GĐ11.4: tồn tại _reload_lock; reload vô hiệu adjacency (đặt None) để dựng lại.
        assert isinstance(knowledge._reload_lock, type(__import__("threading").Lock()))
        ents = [{"id": "a", "name": "A", "type": "dish"}, {"id": "b", "name": "B", "type": "dish"}]
        monkeypatch.setattr(knowledge, "_load",
                            self._fake_load(ents, [{"from": "a", "to": "b", "type": "near"}], []))
        knowledge.reload()
        knowledge.related("a")                       # dựng adjacency
        assert knowledge._adjacency is not None
        knowledge.reload()                           # reload phải reset adjacency
        assert knowledge._adjacency is None

    def test_concurrent_reloads_no_corruption(self, monkeypatch):
        # Nhiều reload song song không làm hỏng state (khoá tuần-tự-hoá). Kết thúc: state hợp lệ.
        import threading as _t
        ents = [{"id": f"e{i}", "name": f"E{i}", "type": "dish"} for i in range(20)]
        rels = [{"from": "e0", "to": f"e{i}", "type": "near"} for i in range(1, 20)]
        monkeypatch.setattr(knowledge, "_load", self._fake_load(ents, rels, []))
        errors = []

        def worker():
            try:
                for _ in range(5):
                    knowledge.reload()
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [_t.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(knowledge._entities) == 20
        assert len(knowledge.related("e0")) == 19


class TestDirectorySearch:
    """GĐ13: tra danh bạ cơ quan hành chính (facility) theo tên hoặc tên xã/phường."""

    @pytest.fixture(autouse=True)
    def setup_kb(self, sample_data):
        entities = {e["id"]: e for e in sample_data["entities"]}
        # Thêm 1 facility thật để test (dữ liệu mẫu, không phải dữ liệu sản xuất)
        entities["ubnd-xa-binh-hoa-phuoc"] = {
            "id": "ubnd-xa-binh-hoa-phuoc",
            "name": "UBND xã Bình Hòa Phước",
            "type": "facility",
            "placeId": "xa-binh-hoa-phuoc",
            "attributes": {
                "office_kind": "ubnd",
                "address": "Ấp Bình Thuận, xã Bình Hòa Phước",
                "phone": "0270 1234 567",
                "hours": "7:30-17:00",
            },
            "source": {"url": "https://vinhlong.gov.vn"},
            "updatedAt": "2026-06-13",
        }
        rels = sample_data["relationships"]
        itins = {it["id"]: it for it in sample_data["itineraries"]}
        with patch.object(knowledge, '_entities', entities), \
             patch.object(knowledge, '_relationships', rels), \
             patch.object(knowledge, '_itineraries', itins):
            yield

    def test_search_by_office_name(self):
        results = knowledge.directory_search("UBND")
        assert len(results) == 1
        r = results[0]
        assert r["name"] == "UBND xã Bình Hòa Phước"
        assert r["office_kind"] == "ubnd"
        assert r["phone"] == "0270 1234 567"
        assert r["address"]
        assert r["ward"] == "Bình Hòa Phước"
        assert r["source"] == "https://vinhlong.gov.vn"

    def test_search_by_ward_name(self):
        # Tra theo tên xã (có dấu) vẫn ra cơ quan trong xã đó
        results = knowledge.directory_search("Bình Hòa Phước")
        assert any(r["name"] == "UBND xã Bình Hòa Phước" for r in results)

    def test_empty_query_returns_all_facilities(self):
        results = knowledge.directory_search("")
        assert len(results) == 1

    def test_no_match_returns_empty(self):
        assert knowledge.directory_search("công an thành phố XYZ") == []

    def test_only_facilities_returned(self):
        # dish/product/place không bao giờ lọt vào danh bạ
        results = knowledge.directory_search("")
        assert all("office_kind" in r for r in results)
