"""
Phase 16-17 test coverage: tools.py schema validation, seo.py helpers,
moderation auto-escalation, and cross-module consistency.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════
#  tools.py — Schema validation
# ═══════════════════════════════════════════════════════════════════════

class TestToolsSchema:
    """Validate that tools.py TOOLS list has correct OpenAI function-call format."""

    def test_tools_is_list(self):
        from tools import TOOLS
        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 5

    def test_each_tool_has_required_fields(self):
        from tools import TOOLS
        for tool in TOOLS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_tool_names_unique(self):
        from tools import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert len(names) == len(set(names)), f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"

    def test_search_tool_has_entity_type_enum(self):
        from tools import TOOLS
        search = next(t for t in TOOLS if t["function"]["name"] == "search")
        props = search["function"]["parameters"]["properties"]
        assert "entity_type" in props
        enum = props["entity_type"]["enum"]
        assert "experience" in enum
        assert "product" in enum
        assert "dish" in enum

    def test_search_tool_has_area_enum(self):
        from tools import TOOLS
        search = next(t for t in TOOLS if t["function"]["name"] == "search")
        props = search["function"]["parameters"]["properties"]
        assert "area" in props
        enum = props["area"]["enum"]
        assert "vinh-long" in enum
        assert "ben-tre" in enum
        assert "tra-vinh" in enum

    def test_generate_itinerary_tool_exists(self):
        from tools import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert "generate_itinerary" in names

    def test_system_prompt_not_empty(self):
        from tools import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 200

    def test_system_prompt_mentions_vinh_long(self):
        from tools import SYSTEM_PROMPT
        assert "Vĩnh Long" in SYSTEM_PROMPT

    def test_system_prompt_anti_fabrication_rule(self):
        from tools import SYSTEM_PROMPT
        assert "bịa" in SYSTEM_PROMPT.lower() or "TUYỆT ĐỐI" in SYSTEM_PROMPT

    def test_tool_descriptions_are_vietnamese(self):
        from tools import TOOLS
        for tool in TOOLS:
            desc = tool["function"]["description"]
            has_vn = any(c in desc for c in "áàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ")
            assert has_vn, f"Tool '{tool['function']['name']}' description not Vietnamese"

    def test_ocop_products_tool_exists(self):
        from tools import TOOLS
        names = [t["function"]["name"] for t in TOOLS]
        assert "ocop_products" in names

    def test_entity_detail_requires_entity_id(self):
        from tools import TOOLS
        detail = next(t for t in TOOLS if t["function"]["name"] == "entity_detail")
        required = detail["function"]["parameters"].get("required", [])
        assert "entity_id" in required


# ═══════════════════════════════════════════════════════════════════════
#  seo.py — Pure helper functions
# ═══════════════════════════════════════════════════════════════════════

class TestSeoHelpers:
    """Test seo.py pure functions that don't need data.json."""

    def test_is_valid_url_good(self):
        from seo import _is_valid_url
        assert _is_valid_url("https://example.com")
        assert _is_valid_url("http://localhost:3000")
        assert _is_valid_url("https://maps.google.com/place?q=test")

    def test_is_valid_url_bad(self):
        from seo import _is_valid_url
        assert not _is_valid_url("")
        assert not _is_valid_url(None)
        assert not _is_valid_url("not-a-url")
        assert not _is_valid_url("ftp://file.com")
        assert not _is_valid_url(123)

    def test_is_external_url(self):
        from seo import _is_external_url
        assert _is_external_url("https://google.com")
        assert not _is_external_url("https://vinhlong360.vn/path")
        assert not _is_external_url("https://www.vinhlong360.vn/path")
        assert not _is_external_url("")

    def test_parse_coordinates_list(self):
        from seo import parse_coordinates
        assert parse_coordinates([10.25, 106.37]) == (10.25, 106.37)

    def test_parse_coordinates_dict(self):
        from seo import parse_coordinates
        assert parse_coordinates({"lat": 10.25, "lng": 106.37}) == (10.25, 106.37)

    def test_parse_coordinates_dict_longitude_key(self):
        from seo import parse_coordinates
        assert parse_coordinates({"latitude": 10.25, "longitude": 106.37}) == (10.25, 106.37)

    def test_parse_coordinates_json_string(self):
        from seo import parse_coordinates
        result = parse_coordinates('[10.25, 106.37]')
        assert result == (10.25, 106.37)

    def test_parse_coordinates_invalid(self):
        from seo import parse_coordinates
        assert parse_coordinates(None) is None
        assert parse_coordinates("not-coords") is None
        assert parse_coordinates([999, 999]) is None

    def test_parse_coordinates_swapped(self):
        from seo import parse_coordinates
        result = parse_coordinates([106.37, 10.25])
        assert result == (10.25, 106.37)

    def test_safe_date_iso(self):
        from seo import _safe_date
        assert _safe_date("2024-06-15") == "2024-06-15"

    def test_safe_date_datetime(self):
        from seo import _safe_date
        assert _safe_date("2024-06-15T12:30:00Z") == "2024-06-15"

    def test_safe_date_invalid(self):
        from seo import _safe_date
        assert _safe_date("not-a-date") is None
        assert _safe_date(None) is None
        assert _safe_date("", "2024-01-01") == "2024-01-01"

    def test_parse_duration_days(self):
        from seo import _parse_duration
        assert _parse_duration("2 ngày 1 đêm") == "P2D"
        assert _parse_duration("3 ngày") == "P3D"

    def test_parse_duration_hours(self):
        from seo import _parse_duration
        assert _parse_duration("2 giờ") == "PT2H"
        assert _parse_duration("2 giờ 30 phút") == "PT2H30M"

    def test_parse_duration_minutes(self):
        from seo import _parse_duration
        assert _parse_duration("45 phút") == "PT45M"

    def test_parse_duration_nights(self):
        from seo import _parse_duration
        assert _parse_duration("2 đêm") == "P3D"

    def test_parse_duration_invalid(self):
        from seo import _parse_duration
        assert _parse_duration(None) is None
        assert _parse_duration("random text") is None
        assert _parse_duration(123) is None

    def test_source_info_string(self):
        from seo import _source_info
        name, url = _source_info({"source": "https://google.com"})
        assert url == "https://google.com"

    def test_source_info_dict(self):
        from seo import _source_info
        name, url = _source_info({"source": {"title": "Test", "url": "https://example.com"}})
        assert name == "Test"
        assert url == "https://example.com"

    def test_source_info_self_url(self):
        from seo import _source_info
        name, url = _source_info({"source": {"url": "https://vinhlong360.vn/x"}})
        assert url is None

    def test_source_info_list(self):
        from seo import _source_info
        name, url = _source_info({"source": [{"title": "A", "url": "https://ext.com"}]})
        assert name == "A"
        assert url == "https://ext.com"

    def test_source_info_empty(self):
        from seo import _source_info
        name, url = _source_info({})
        assert name is None and url is None

    def test_type_schema_mapping(self):
        from seo import TYPE_SCHEMA
        assert TYPE_SCHEMA["accommodation"] == "LodgingBusiness"
        assert TYPE_SCHEMA["dish"] == "Recipe"
        assert TYPE_SCHEMA["attraction"] == "TouristAttraction"

    def test_area_names(self):
        from seo import AREA_NAMES
        assert AREA_NAMES["vinh-long"] == "Vĩnh Long"
        assert AREA_NAMES["ben-tre"] == "Bến Tre"
        assert AREA_NAMES["tra-vinh"] == "Trà Vinh"

    def test_build_og_meta_default(self):
        from seo import build_og_meta
        meta = build_og_meta()
        assert "og:title" in meta
        assert "og:type" in meta
        assert meta["og:type"] == "website"


# ═══════════════════════════════════════════════════════════════════════
#  Phase 17: Moderation auto-escalation
# ═══════════════════════════════════════════════════════════════════════

class TestPhase17ModerationAutoEscalation:
    """Phase 17: Stale pending posts auto-approved after 48h."""

    def test_scheduler_has_moderation_escalation_task(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "moderation-escalation" in src
        assert "task_moderation_auto_escalation" in src

    def test_escalation_interval_reasonable(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        idx = src.find("moderation-escalation")
        block = src[idx:idx+200]
        assert "6 * 3600" in block

    def test_escalation_uses_48h_threshold(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "48 hours" in src

    def test_escalation_only_pending_status(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        idx = src.find("task_moderation_auto_escalation")
        block = src[idx:idx+500]
        assert "pending" in block
        assert "approved" in block


class TestPhase17AccountHardDelete:
    """Phase 17: Hard-delete accounts past grace period."""

    def test_session_cleanup_hard_deletes_accounts(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        idx = src.find("task_session_cleanup")
        block = src[idx:idx+1000]
        assert "DELETE FROM users" in block
        assert "deleted_at" in block
        assert "30 days" in block

    def test_grace_period_configurable(self):
        from config import settings
        assert settings.ACCOUNT_DELETE_GRACE_DAYS == 30


class TestPhase17SecurityChecks:
    """Phase 17: Verify security best practices across modules."""

    def test_admin_key_timing_safe(self):
        """Admin key verification must use timing-safe comparison."""
        src = (Path(__file__).resolve().parent.parent / "middleware.py").read_text(encoding="utf-8")
        assert "hmac.compare_digest" in src

    def test_password_hash_uses_pbkdf2(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "pbkdf2_hmac" in src

    def test_password_validation_min_length(self):
        from auth import SetPassword
        import pytest as pt
        with pt.raises(Exception):
            SetPassword(password="short1")

    def test_password_validation_needs_digit(self):
        from auth import SetPassword
        import pytest as pt
        with pt.raises(Exception):
            SetPassword(password="onlyletters")

    def test_password_validation_needs_letter(self):
        from auth import SetPassword
        import pytest as pt
        with pt.raises(Exception):
            SetPassword(password="12345678")

    def test_esms_uses_https(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "https://rest.esms.vn/" in src

    def test_token_hashing_uses_sha256(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "sha256" in src

    def test_session_cleanup_purges_expired(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "DELETE FROM user_sessions WHERE expires_at < NOW()" in src
        assert "DELETE FROM otp_sessions WHERE expires_at < NOW()" in src


# ═══════════════════════════════════════════════════════════════════════
#  Cross-module consistency checks
# ═══════════════════════════════════════════════════════════════════════

class TestCrossModuleConsistency:
    """Verify cross-module contracts and consistency."""

    def test_all_routers_importable(self):
        """All modules with routers should be importable without errors."""
        import social
        import auth
        import notifications
        import visits
        import saved
        import plans
        assert hasattr(social, "router")
        assert hasattr(auth, "router")
        assert hasattr(notifications, "router")
        assert hasattr(visits, "router")
        assert hasattr(saved, "router")
        assert hasattr(plans, "router")

    def test_config_settings_importable(self):
        from config import settings
        assert hasattr(settings, "LLM_API_KEY")
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "MAX_COMMENTS_PER_POST")

    def test_ratelimit_functions_importable(self):
        from ratelimit import check_rate, check_rate_ip, gc_all, is_rate_limited, _reset
        assert callable(check_rate)
        assert callable(gc_all)
        assert callable(_reset)

    def test_auth_middleware_dependencies_importable(self):
        from auth_middleware import (
            get_current_user, require_user, require_csrf,
            require_idempotency, validate_path_id,
        )
        import inspect
        assert inspect.iscoroutinefunction(require_idempotency)

    def test_moderation_functions_importable(self):
        from moderation import moderate_content, moderate_content_enhanced
        import inspect
        assert inspect.iscoroutinefunction(moderate_content)
        assert inspect.iscoroutinefunction(moderate_content_enhanced)

    def test_scheduler_tasks_all_callable(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        import re
        task_names = re.findall(r'ScheduledTask\("([^"]+)"', src)
        assert len(task_names) >= 10
        fn_names = re.findall(r'ScheduledTask\("[^"]+",\s*(\w+)', src)
        for fn in fn_names:
            assert f"def {fn}" in src, f"Task function {fn} not defined"


# ═══════════════════════════════════════════════════════════════════════
#  Path parameter validation — visits.py + saved.py
# ═══════════════════════════════════════════════════════════════════════

class TestPathValidationVisits:
    """visits.py path parameters must call validate_path_id."""

    def test_check_visit_validates_entity_id(self):
        src = (Path(__file__).resolve().parent.parent / "visits.py").read_text(encoding="utf-8")
        idx = src.find("def check_visit")
        block = src[idx:idx+300]
        assert "validate_path_id" in block

    def test_remove_visit_validates_entity_id(self):
        src = (Path(__file__).resolve().parent.parent / "visits.py").read_text(encoding="utf-8")
        idx = src.find("def remove_visit")
        block = src[idx:idx+300]
        assert "validate_path_id" in block

    def test_visits_imports_validate_path_id(self):
        src = (Path(__file__).resolve().parent.parent / "visits.py").read_text(encoding="utf-8")
        import_section = src[:src.find("\nrouter")]
        assert "validate_path_id" in import_section


class TestPathValidationSaved:
    """saved.py path parameters must call validate_path_id."""

    def test_remove_saved_validates_entity_id(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        idx = src.find("def remove_saved")
        block = src[idx:idx+300]
        assert "validate_path_id" in block

    def test_saved_imports_validate_path_id(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        import_section = src[:src.find("\nrouter")]
        assert "validate_path_id" in import_section


class TestPathValidationPlans:
    """plans.py path parameters must call validate_path_id."""

    def test_remove_plan_validates_plan_id(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def remove_plan")
        block = src[idx:idx+300]
        assert "validate_path_id" in block

    def test_publish_plan_validates_plan_id(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def publish_plan")
        block = src[idx:idx+300]
        assert "validate_path_id" in block

    def test_get_shared_validates_plan_id(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def get_shared")
        block = src[idx:idx+300]
        assert "validate_path_id" in block

    def test_plans_imports_validate_path_id(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        import_section = src[:src.find("\nrouter")]
        assert "validate_path_id" in import_section
