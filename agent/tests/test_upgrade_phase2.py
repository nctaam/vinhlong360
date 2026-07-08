"""Tests for Phase 2 upgrade cards: U-08, U-29, U-25, U-12."""
import inspect


# ── U-08: Field-level report/correction CTA ──────────────────────────

class TestFieldLevelReport:

    def test_report_model_has_field(self):
        from public_api import ReportIn
        m = ReportIn(target_id="entity-1", reason="Sai SĐT", field="phone")
        assert m.field == "phone"

    def test_report_model_field_optional(self):
        from public_api import ReportIn
        m = ReportIn(target_id="entity-1", reason="Nội dung xấu")
        assert m.field is None

    def test_report_field_options_defined(self):
        from public_api import _REPORT_FIELD_OPTIONS
        assert "phone" in _REPORT_FIELD_OPTIONS
        assert "hours" in _REPORT_FIELD_OPTIONS
        assert "address" in _REPORT_FIELD_OPTIONS
        assert "source" in _REPORT_FIELD_OPTIONS
        assert "price" in _REPORT_FIELD_OPTIONS

    def test_submit_report_includes_field_in_record(self):
        src = inspect.getsource(__import__("public_api").submit_report)
        assert '"field"' in src
        assert "report_field" in src

    def test_submit_report_validates_field_options(self):
        src = inspect.getsource(__import__("public_api").submit_report)
        assert "_REPORT_FIELD_OPTIONS" in src

    def test_backward_compat_field_none(self):
        src = inspect.getsource(__import__("public_api").submit_report)
        assert "payload.field" in src


# ── U-29: Rule-based similar recommendations ─────────────────────────

class TestSimilarRecommendations:

    def test_similar_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/similar" in paths

    def test_similar_uses_recommender(self):
        src = inspect.getsource(__import__("public_api").get_similar_entities)
        assert "recommend_by_entity" in src

    def test_similar_has_cache(self):
        from public_api import _similar_cache, _SIMILAR_TTL
        assert _SIMILAR_TTL == 300
        assert isinstance(_similar_cache, dict)

    def test_similar_response_shape(self):
        src = inspect.getsource(__import__("public_api").get_similar_entities)
        assert '"entity_id"' in src
        assert '"similar"' in src

    def test_similar_validates_entity_id(self):
        src = inspect.getsource(__import__("public_api").get_similar_entities)
        assert "validate_path_id" in src

    def test_similar_limit_default(self):
        src = inspect.getsource(__import__("public_api").get_similar_entities)
        assert "limit: int = Query(6" in src


# ── U-25: Ward day plan ─────────────────────────────────────────────

class TestWardDayPlan:

    def test_day_plan_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/places/{place_id}/day-plan" in paths

    def test_day_plan_validates_path_id(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert "validate_path_id" in src

    def test_day_plan_uses_entities_by_place(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert "entities_by_place" in src

    def test_day_plan_type_diversity(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert "seen_types" in src
        assert "if t in seen_types" in src

    def test_day_plan_time_slots_defined(self):
        from public_api import _DAY_PLAN_SLOTS
        assert len(_DAY_PLAN_SLOTS) >= 5
        labels = {s["label"] for s in _DAY_PLAN_SLOTS}
        assert "sáng" in labels
        assert "trưa" in labels
        assert "chiều" in labels
        for slot in _DAY_PLAN_SLOTS:
            assert "start" in slot
            assert "duration_min" in slot
            assert slot["duration_min"] > 0

    def test_day_plan_type_priority_defined(self):
        from public_api import _DAY_PLAN_TYPE_PRIORITY
        assert "attraction" in _DAY_PLAN_TYPE_PRIORITY
        assert "dish" in _DAY_PLAN_TYPE_PRIORITY
        assert "accommodation" in _DAY_PLAN_TYPE_PRIORITY
        assert len(_DAY_PLAN_TYPE_PRIORITY) >= 8

    def test_day_plan_response_shape(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert '"place"' in src
        assert '"stops"' in src
        assert '"total_stops"' in src
        assert '"total_duration_min"' in src

    def test_day_plan_stop_shape(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert '"entity_id"' in src
        assert '"name"' in src
        assert '"type"' in src
        assert '"suggested_time"' in src
        assert '"time_of_day"' in src
        assert '"visit_duration_min"' in src

    def test_day_plan_haversine_helper(self):
        from public_api import _haversine_km
        d = _haversine_km([10.25, 105.97], [10.25, 105.97])
        assert d == 0.0
        d2 = _haversine_km([10.25, 105.97], [10.26, 105.98])
        assert 0 < d2 < 5
        assert _haversine_km(None, [10.0, 105.0]) == 999.0
        assert _haversine_km([10.0, 105.0], None) == 999.0

    def test_day_plan_sorts_by_proximity(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert "_haversine_km" in src
        assert "sorted" in src

    def test_day_plan_404_non_place(self):
        src = inspect.getsource(__import__("public_api").place_day_plan)
        assert '"type") != "place"' in src
        assert "404" in src


# ── U-12: AggregateRating schema gating ─────────────────────────────

class TestAggregateRatingGating:

    def test_min_count_constant_defined(self):
        from seo import AGGREGATE_RATING_MIN_COUNT
        assert AGGREGATE_RATING_MIN_COUNT == 3

    def test_rating_count_below_min_omits_schema(self):
        import seo
        entity = {
            "id": "low-cnt", "name": "Low", "type": "attraction",
            "avg_rating": 4.5, "rating_count": 2,
        }
        ld = seo.build_entity_jsonld(entity, {})
        assert "aggregateRating" not in ld

    def test_rating_count_at_min_emits_schema(self):
        import seo
        entity = {
            "id": "exact-cnt", "name": "Exact", "type": "attraction",
            "avg_rating": 4.0, "rating_count": 3,
        }
        ld = seo.build_entity_jsonld(entity, {})
        assert "aggregateRating" in ld
        assert ld["aggregateRating"]["ratingCount"] == 3

    def test_rating_count_above_min_emits_schema(self):
        import seo
        entity = {
            "id": "high-cnt", "name": "High", "type": "attraction",
            "avg_rating": 4.8, "rating_count": 50,
        }
        ld = seo.build_entity_jsonld(entity, {})
        assert "aggregateRating" in ld
        assert ld["aggregateRating"]["ratingValue"] == 4.8
        assert ld["aggregateRating"]["ratingCount"] == 50

    def test_attrs_rating_below_min_omits(self):
        import seo
        entity = {
            "id": "attr-low", "name": "Low", "type": "restaurant",
            "attributes": {"rating": 4.0, "review_count": 1},
        }
        ld = seo.build_entity_jsonld(entity, {})
        assert "aggregateRating" not in ld

    def test_attrs_rating_at_min_emits(self):
        import seo
        entity = {
            "id": "attr-ok", "name": "OK", "type": "restaurant",
            "attributes": {"rating": 4.2, "review_count": 5},
        }
        ld = seo.build_entity_jsonld(entity, {})
        assert "aggregateRating" in ld
        assert ld["aggregateRating"]["ratingValue"] == 4.2

    def test_gating_uses_constant_in_source(self):
        # Gating aggregateRating dời sang helper _jsonld_rating_primary/_fallback
        # (refactor R20.8 build_entity_jsonld); hằng phải còn được dùng ở đó.
        seo = __import__("seo")
        src = inspect.getsource(seo._jsonld_rating_primary) + inspect.getsource(seo._jsonld_rating_fallback)
        assert "AGGREGATE_RATING_MIN_COUNT" in src
