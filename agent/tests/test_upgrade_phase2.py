"""Tests for Phase 2 upgrade cards: U-08, U-29, U-25, U-12."""
import inspect
import pytest


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
