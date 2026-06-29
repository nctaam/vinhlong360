"""Tests for Phase 1 upgrade cards: U-02, U-07, U-04, U-09."""
import inspect
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
