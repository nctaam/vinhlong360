"""Tests for Phase 1 upgrade cards: U-02, U-07, U-04, U-09."""
import inspect
import sys
import pytest


# ── U-02: Source freshness metadata ──────────────────────────────────

class TestSourceFreshness:

    def test_build_source_freshness_fresh(self):
        from datetime import datetime, timezone, timedelta
        from public_api import _build_source_freshness
        entity = {
            "updatedAt": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "source": {"title": "Test", "url": "https://example.com"},
        }
        result = _build_source_freshness(entity)
        assert result["freshness_status"] == "fresh"
        assert result["days_since_update"] is not None
        assert result["days_since_update"] <= 31
        assert result["source_title"] == "Test"
        assert result["source_url"] == "https://example.com"

    def test_build_source_freshness_aging(self):
        from datetime import datetime, timezone, timedelta
        from public_api import _build_source_freshness
        entity = {"updatedAt": (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()}
        result = _build_source_freshness(entity)
        assert result["freshness_status"] == "aging"

    def test_build_source_freshness_stale(self):
        from datetime import datetime, timezone, timedelta
        from public_api import _build_source_freshness
        entity = {"updatedAt": (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()}
        result = _build_source_freshness(entity)
        assert result["freshness_status"] == "stale"
        assert result["days_since_update"] >= 200

    def test_build_source_freshness_unknown(self):
        from public_api import _build_source_freshness
        result = _build_source_freshness({})
        assert result["freshness_status"] == "unknown"
        assert result["days_since_update"] is None

    def test_build_source_freshness_bad_date(self):
        from public_api import _build_source_freshness
        result = _build_source_freshness({"updatedAt": "not-a-date"})
        assert result["freshness_status"] == "unknown"

    def test_entity_detail_includes_source_freshness(self):
        src = inspect.getsource(__import__("public_api").get_entity)
        assert "source_freshness" in src
        assert "_build_source_freshness" in src

    def test_source_freshness_keys_complete(self):
        from public_api import _build_source_freshness
        result = _build_source_freshness({"updatedAt": "2025-01-01"})
        expected_keys = {"source_title", "source_url", "updated_at", "days_since_update", "freshness_status"}
        assert set(result.keys()) == expected_keys


class TestReportStale:

    def test_report_stale_endpoint_exists(self):
        from public_api import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/entities/{entity_id}/report-stale" in paths

    def test_report_stale_model_validation(self):
        from public_api import ReportStaleIn
        m = ReportStaleIn(field="phone", detail="Số này không còn hoạt động")
        assert m.field == "phone"
        assert m.detail == "Số này không còn hoạt động"

    def test_report_stale_model_rejects_empty_field(self):
        from public_api import ReportStaleIn
        with pytest.raises(Exception):
            ReportStaleIn(field="", detail="test")

    def test_report_stale_valid_fields(self):
        from public_api import _STALE_FIELDS
        assert "phone" in _STALE_FIELDS
        assert "hours" in _STALE_FIELDS
        assert "address" in _STALE_FIELDS
        assert "source" in _STALE_FIELDS
        assert "images" in _STALE_FIELDS

    def test_report_stale_uses_rate_limiter(self):
        src = inspect.getsource(__import__("public_api").report_stale_field)
        assert "report_limiter" in src

    def test_report_stale_writes_jsonl(self):
        src = inspect.getsource(__import__("public_api").report_stale_field)
        assert "_jsonl_lock" in src
        assert "REPORTS_FILE" in src
        assert "stale_field" in src

    def test_report_stale_validates_path_id(self):
        src = inspect.getsource(__import__("public_api").report_stale_field)
        assert "validate_path_id" in src


# ── U-07: Practical facts struct ─────────────────────────────────────

class TestPracticalFacts:

    def test_build_practical_facts_empty_attrs(self):
        from public_api import _build_practical_facts
        result = _build_practical_facts({})
        assert "hours" in result
        assert "phone" in result
        assert "address" in result
        assert "website" in result
        assert "zalo" in result
        assert "parking" in result
        assert "best_time" in result
        assert result["hours"] is None

    def test_build_practical_facts_with_data(self):
        from public_api import _build_practical_facts
        entity = {"attributes": {
            "hours": "7:00-17:00",
            "phone": "0270 123 456",
            "parking": "Miễn phí",
        }}
        result = _build_practical_facts(entity)
        assert result["hours"] == "7:00-17:00"
        assert result["phone"] == "0270 123 456"
        assert result["parking"] == "Miễn phí"
        assert result["address"] is None

    def test_build_practical_facts_alias_open_hours(self):
        from public_api import _build_practical_facts
        entity = {"attributes": {"open_hours": "8:00-16:30"}}
        result = _build_practical_facts(entity)
        assert result["hours"] == "8:00-16:30"

    def test_build_practical_facts_alias_opening_hours(self):
        from public_api import _build_practical_facts
        entity = {"attributes": {"opening_hours": "Hàng ngày 6:00-18:00"}}
        result = _build_practical_facts(entity)
        assert result["hours"] == "Hàng ngày 6:00-18:00"

    def test_build_practical_facts_alias_admission(self):
        from public_api import _build_practical_facts
        entity = {"attributes": {"admission": "50.000đ"}}
        result = _build_practical_facts(entity)
        assert result["admission_fee"] == "50.000đ"

    def test_build_practical_facts_alias_price(self):
        from public_api import _build_practical_facts
        entity = {"attributes": {"price": "30.000-50.000đ"}}
        result = _build_practical_facts(entity)
        assert result["price_range"] == "30.000-50.000đ"

    def test_build_practical_facts_completeness_count(self):
        from public_api import _build_practical_facts
        entity = {"attributes": {"hours": "8-17", "phone": "123", "parking": "Có"}}
        result = _build_practical_facts(entity)
        assert result["_completeness"] >= 3

    def test_entity_detail_includes_practical_facts(self):
        src = inspect.getsource(__import__("public_api").get_entity)
        assert "practical_facts" in src
        assert "_build_practical_facts" in src

    def test_practical_facts_consistent_keys(self):
        from public_api import _build_practical_facts, _PRACTICAL_FACTS_KEYS
        result = _build_practical_facts({"attributes": {"hours": "8-17"}})
        for key in _PRACTICAL_FACTS_KEYS:
            assert key in result


# ── U-04: Review sort/filter/photo-first ─────────────────────────────

class TestEntityFeedSortFilter:

    def test_entity_feed_has_sort_param(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "sort" in src
        assert "default" in src
        assert "newest" in src
        assert "helpful" in src
        assert "photo" in src
        assert "star" in src

    def test_entity_feed_has_min_rating_param(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "min_rating" in src
        assert "p.rating >=" in src

    def test_entity_feed_has_photo_filter(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "has_photo" in src
        assert "jsonb_array_length" in src

    def test_entity_feed_sort_options_defined(self):
        from social import _ENTITY_FEED_SORT_OPTIONS
        assert "default" in _ENTITY_FEED_SORT_OPTIONS
        assert "newest" in _ENTITY_FEED_SORT_OPTIONS
        assert "helpful" in _ENTITY_FEED_SORT_OPTIONS
        assert "photo" in _ENTITY_FEED_SORT_OPTIONS
        assert "star" in _ENTITY_FEED_SORT_OPTIONS

    def test_entity_feed_sort_newest_order(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert '"newest": "p.created_at DESC"' in src

    def test_entity_feed_sort_star_order(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "p.rating DESC NULLS LAST" in src

    def test_entity_feed_invalid_sort_defaults(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert 'sort not in _ENTITY_FEED_SORT_OPTIONS' in src

    def test_entity_feed_total_includes_filters(self):
        src = inspect.getsource(__import__("social").get_entity_feed)
        assert "total_extra" in src
