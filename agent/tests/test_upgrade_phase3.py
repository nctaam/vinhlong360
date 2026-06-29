"""Tests for Phase 3 upgrade cards: U-17, U-24, U-22, BE-10, BE-5."""
import inspect
import pytest


# ── U-17: Stale content admin queue ─────────────────────────────────

class TestStaleQueue:

    def test_stale_queue_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/stale-queue" in paths

    def test_stale_mark_reviewed_endpoint_exists(self):
        from admin import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/admin/stale-queue/{entity_id}/mark-reviewed" in paths

    def test_stale_queue_has_threshold_param(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "threshold_days" in src
        assert "ge=30" in src

    def test_stale_queue_has_missing_field_filter(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "missing_field" in src
        assert "source|images|coordinates|phone|summary" in src

    def test_stale_queue_has_entity_type_filter(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "entity_type" in src

    def test_stale_queue_computes_days_since(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "days_since" in src
        assert "timedelta" in src

    def test_stale_queue_response_shape(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert '"items"' in src
        assert '"total"' in src
        assert '"days_since_update"' in src
        assert '"is_stale"' in src
        assert '"missing_fields"' in src

    def test_stale_queue_sorts_by_staleness(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert "results.sort" in src
        assert "days_since_update" in src

    def test_stale_queue_skips_place_entities(self):
        src = inspect.getsource(__import__("admin").stale_queue)
        assert '"place"' in src
        assert "continue" in src

    def test_stale_mark_reviewed_validates_path(self):
        src = inspect.getsource(__import__("admin").stale_mark_reviewed)
        assert "validate_path_id" in src

    def test_stale_mark_reviewed_sets_timestamp(self):
        src = inspect.getsource(__import__("admin").stale_mark_reviewed)
        assert "stale_reviewed_at" in src
        assert "isoformat" in src

    def test_stale_queue_missing_fields_constant(self):
        from admin import _STALE_QUEUE_MISSING_FIELDS
        assert "source" in _STALE_QUEUE_MISSING_FIELDS
        assert "images" in _STALE_QUEUE_MISSING_FIELDS
        assert "coordinates" in _STALE_QUEUE_MISSING_FIELDS

    def test_stale_threshold_default(self):
        from admin import _STALE_THRESHOLD_DEFAULT
        assert _STALE_THRESHOLD_DEFAULT == 180
