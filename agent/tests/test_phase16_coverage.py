"""
Phase 16-17+ test coverage: tools.py schema validation, seo.py helpers,
moderation auto-escalation, cross-module consistency, path validation,
rate limiting, SELECT * removal, query param constraints.
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


# ═══════════════════════════════════════════════════════════════════════
#  SELECT * removal — explicit column lists in UGC/auth queries
# ═══════════════════════════════════════════════════════════════════════

class TestSelectStarRemoval:
    """Verify SELECT * is not used in UGC/auth Postgres queries."""

    def test_auth_no_select_star_otp(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "SELECT * FROM otp_sessions" not in src

    def test_auth_no_select_star_privacy(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "SELECT * FROM user_privacy" not in src

    def test_notifications_no_select_star(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        assert "SELECT * FROM notifications" not in src

    def test_notifications_explicit_columns(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        assert "SELECT id, type, title, body, ref_type, ref_id, is_read, created_at" in src


# ═══════════════════════════════════════════════════════════════════════
#  Rate limiting on mutation endpoints
# ═══════════════════════════════════════════════════════════════════════

class TestRateLimitMutationEndpoints:
    """All mutation endpoints must have rate limiting."""

    def test_saved_add_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        idx = src.find("def add_saved")
        assert "check_rate" in src[idx:idx+300]

    def test_saved_remove_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        idx = src.find("def remove_saved")
        assert "check_rate" in src[idx:idx+300]

    def test_saved_merge_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        idx = src.find("def merge_saved")
        assert "check_rate" in src[idx:idx+300]

    def test_visits_set_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "visits.py").read_text(encoding="utf-8")
        idx = src.find("def set_visit")
        assert "check_rate" in src[idx:idx+300]

    def test_visits_remove_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "visits.py").read_text(encoding="utf-8")
        idx = src.find("def remove_visit")
        assert "check_rate" in src[idx:idx+300]

    def test_plans_add_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def add_plan")
        assert "check_rate" in src[idx:idx+300]

    def test_plans_remove_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def remove_plan")
        assert "check_rate" in src[idx:idx+300]

    def test_plans_merge_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def merge_plans")
        assert "check_rate" in src[idx:idx+300]

    def test_plans_publish_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def publish_plan")
        assert "check_rate" in src[idx:idx+300]

    def test_follow_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("def toggle_follow")
        assert "check_rate" in src[idx:idx+300]

    def test_block_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("def toggle_block")
        assert "check_rate" in src[idx:idx+300]

    def test_rsvp_has_rate_limit(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("def toggle_rsvp")
        assert "check_rate" in src[idx:idx+300]


class TestBareExceptFixes:
    """Bare except blocks should log errors instead of silently swallowing."""

    def test_session_binding_logs_on_error(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        idx = src.find("_check_session_binding_safe")
        block = src[idx:idx+300]
        assert "exc_info=True" in block or "logging" in block

    def test_sse_cleanup_uses_lock(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        assert "_sse_lock" in src, "SSE cleanup must use asyncio.Lock instead of bare try/except"


# ═══════════════════════════════════════════════════════════════════════
#  Input validation — Pydantic model field constraints
# ═══════════════════════════════════════════════════════════════════════

class TestPydanticFieldValidation:
    """Body models must have field length constraints."""

    def test_saved_item_id_max_length(self):
        from saved import SavedItem
        with pytest.raises(Exception):
            SavedItem(id="x" * 201)

    def test_saved_item_accepts_valid(self):
        from saved import SavedItem
        item = SavedItem(id="ben-tre-coconut")
        assert item.id == "ben-tre-coconut"

    def test_visit_body_entity_id_max_length(self):
        from visits import VisitBody
        with pytest.raises(Exception):
            VisitBody(entity_id="x" * 201, status="want")

    def test_visit_body_valid(self):
        from visits import VisitBody
        v = VisitBody(entity_id="chua-vinh-trang", status="visited")
        assert v.status == "visited"

    def test_plan_stops_limit(self):
        from plans import PlanBody
        with pytest.raises(Exception):
            PlanBody(title="Test", stops=[{"id": str(i)} for i in range(51)])


# ═══════════════════════════════════════════════════════════════════════
#  Query parameter length constraints
# ═══════════════════════════════════════════════════════════════════════

class TestQueryParamConstraints:
    """Query parameters must have max_length to prevent abuse."""

    def test_entities_list_params_constrained(self):
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("def list_entities")
        block = src[idx:idx+400]
        assert "max_length" in block

    def test_map_pins_params_constrained(self):
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("def get_map_pins")
        block = src[idx:idx+300]
        assert "max_length" in block

    def test_feed_params_constrained(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("def get_feed")
        block = src[idx:idx+400]
        assert "max_length" in block

    def test_sse_token_constrained(self):
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("def notification_stream")
        block = src[idx:idx+200]
        assert "max_length" in block

    def test_admin_reports_explicit_columns(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert "SELECT r.*" not in src

    def test_social_no_select_star_posts(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "p.*" not in src

    def test_social_no_select_star_comments(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "c.*" not in src

    def test_social_uses_post_cols_constant(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_POST_COLS" in src
        assert "_COMMENT_COLS" in src


# ═══════════════════════════════════════════════════════════════════════
#  Comprehensive security posture verification
# ═══════════════════════════════════════════════════════════════════════

class TestSecurityPosture:
    """Verify overall security hardening across the backend."""

    def test_no_user_input_in_admin_errors(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert "f\"Entity '{entity_id}'" not in src

    def test_csrf_on_all_saved_mutations(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        for fn in ("add_saved", "remove_saved", "merge_saved"):
            idx = src.find(f"def {fn}")
            assert idx != -1
            block = src[idx:idx+200]
            assert "require_csrf" in block, f"{fn} missing CSRF"

    def test_csrf_on_all_visit_mutations(self):
        src = (Path(__file__).resolve().parent.parent / "visits.py").read_text(encoding="utf-8")
        for fn in ("set_visit", "remove_visit"):
            idx = src.find(f"def {fn}")
            block = src[idx:idx+200]
            assert "require_csrf" in block, f"{fn} missing CSRF"

    def test_csrf_on_all_plan_mutations(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        for fn in ("add_plan", "remove_plan", "merge_plans", "publish_plan"):
            idx = src.find(f"def {fn}")
            block = src[idx:idx+200]
            assert "require_csrf" in block, f"{fn} missing CSRF"

    def test_require_pg_on_ugc_routers(self):
        for module in ("saved", "visits", "plans", "notifications", "social"):
            src = (Path(__file__).resolve().parent.parent / f"{module}.py").read_text(encoding="utf-8")
            assert "_require_pg" in src, f"{module}.py missing _require_pg"

    def test_validate_path_id_coverage(self):
        for module, fns in [
            ("saved", ["remove_saved"]),
            ("visits", ["check_visit", "remove_visit"]),
            ("plans", ["remove_plan", "publish_plan", "get_shared"]),
        ]:
            src = (Path(__file__).resolve().parent.parent / f"{module}.py").read_text(encoding="utf-8")
            for fn in fns:
                idx = src.find(f"def {fn}")
                block = src[idx:idx+300]
                assert "validate_path_id" in block, f"{module}.{fn} missing validate_path_id"

    def test_no_select_star_in_ugc_files(self):
        for module in ("social", "auth", "notifications"):
            src = (Path(__file__).resolve().parent.parent / f"{module}.py").read_text(encoding="utf-8")
            assert "SELECT *" not in src, f"{module}.py still has SELECT *"

    def test_no_error_dict_returns_in_server(self):
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        assert 'return {"error":' not in src, "server.py still returns error dicts instead of HTTPException"

    def test_no_error_dict_returns_in_bot_gateway(self):
        src = (Path(__file__).resolve().parent.parent / "bot_gateway.py").read_text(encoding="utf-8")
        assert 'return {"error":' not in src, "bot_gateway.py still returns error dicts instead of HTTPException"

    def test_httpexception_imported_in_server(self):
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        imports = src[:src.find("\napp =") if "\napp =" in src else 500]
        assert "HTTPException" in imports, "server.py missing HTTPException import"

    def test_httpexception_imported_in_bot_gateway(self):
        src = (Path(__file__).resolve().parent.parent / "bot_gateway.py").read_text(encoding="utf-8")
        imports = src[:2000]
        assert "HTTPException" in imports, "bot_gateway.py missing HTTPException import"

    def test_query_param_bounds_in_server(self):
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        unvalidated = []
        for line_no, line in enumerate(src.split("\n"), 1):
            if "limit: int = " in line and "Query(" not in line and "def " in line:
                fn = line.strip().split("(")[0].replace("async def ", "").replace("def ", "")
                unvalidated.append(f"{fn}:{line_no}")
        assert not unvalidated, f"server.py has unvalidated limit params: {unvalidated}"

    def test_query_param_bounds_in_auth(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        for line in src.split("\n"):
            if "limit: int = " in line and "def " in line:
                assert "Query(" in line, f"auth.py unvalidated limit: {line.strip()}"

    def test_query_param_bounds_in_plans(self):
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        for line in src.split("\n"):
            if "limit: int = " in line and "def " in line:
                assert "Query(" in line, f"plans.py unvalidated limit: {line.strip()}"

    def test_offset_params_have_upper_bound(self):
        for module in ("admin", "notifications", "public_api", "social"):
            src = (Path(__file__).resolve().parent.parent / f"{module}.py").read_text(encoding="utf-8")
            for line_no, line in enumerate(src.split("\n"), 1):
                if "offset: int = Query(" in line:
                    assert "le=" in line, f"{module}.py:{line_no} offset without upper bound"

    def test_phone_masking_in_auth_logs(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "def _mask_phone" in src
        assert "_mask_phone(phone)" in src
        assert "logger.error(" in src or "logger.warning(" in src

    def test_no_otp_code_in_logs(self):
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        for line in src.split("\n"):
            if "logger" in line and "OTP" in line:
                assert ", code)" not in line, "OTP code leaked in log"

    def test_list_fields_have_max_length(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert "candidate_ids: list[str] | None = Field(None, max_length=" in src
        assert 'images: list[str] = Field(default=[], max_length=' in src

    def test_login_timing_oracle_protection(self):
        """Login must run PBKDF2 even when user not found (constant-time rejection)."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_DUMMY_HASH" in src, "Missing dummy hash for timing oracle protection"
        idx = src.find("def login_password")
        assert idx > 0
        block = src[idx:idx + 1200]
        assert "_verify_password(body.password, _DUMMY_HASH)" in block, \
            "login_password must call _verify_password with dummy hash for non-existent users"

    def test_idempotency_key_scoped_to_user(self):
        """Idempotency keys must be scoped per-user to prevent cross-user collisions."""
        src = (Path(__file__).resolve().parent.parent / "auth_middleware.py").read_text(encoding="utf-8")
        idx = src.find("async def require_idempotency")
        assert idx > 0
        block = src[idx:idx + 500]
        assert "_get_current_user_or_none" in block, \
            "require_idempotency must scope key to user"
        assert 'f"{user[\'id\']}:{key}"' in block or "user['id']" in block, \
            "require_idempotency must prefix key with user id"

    def test_auth_mutations_rate_limited(self):
        """All auth mutation endpoints must have rate limiting."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        for endpoint in ("set_password", "deactivate_account", "delete_account", "update_profile"):
            idx = src.find(f"def {endpoint}")
            assert idx > 0, f"Missing endpoint {endpoint}"
            block = src[idx:idx + 500]
            assert "check_rate(" in block, f"{endpoint} missing rate limiting"

    def test_page_params_have_upper_bound(self):
        """All page query params must have le= upper bound to prevent DoS via large OFFSET."""
        for module in ("social", "admin"):
            src = (Path(__file__).resolve().parent.parent / f"{module}.py").read_text(encoding="utf-8")
            for line_no, line in enumerate(src.split("\n"), 1):
                if "page: int = Query(" in line:
                    assert "le=" in line, f"{module}.py:{line_no} page without upper bound: {line.strip()}"

    def test_ssrf_protection_on_entity_image_url(self):
        """add_entity_image_url must call _assert_public_url for external URLs."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def add_entity_image_url")
        assert idx > 0
        block = src[idx:idx + 500]
        assert "_assert_public_url" in block, "add_entity_image_url missing SSRF validation"

    def test_social_cache_invalidation_on_mutations(self):
        """Post create/update/delete must invalidate trending + leaderboard caches."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "def _invalidate_social_caches" in src
        for fn in ("create_post", "update_post", "delete_post"):
            idx = src.find(f"def {fn}")
            assert idx > 0
            end = src.find("\nasync def ", idx + 1)
            if end < 0:
                end = len(src)
            block = src[idx:end]
            assert "_invalidate_social_caches()" in block, f"{fn} missing cache invalidation"

    def test_validate_path_id_has_param_name(self):
        """All validate_path_id calls must include the param_name argument."""
        import re
        for module in ("social", "admin", "notifications", "public_api", "saved", "visits", "plans"):
            path = Path(__file__).resolve().parent.parent / f"{module}.py"
            if not path.exists():
                continue
            src = path.read_text(encoding="utf-8")
            bare = re.findall(r'validate_path_id\(\w+\)(?!,)', src)
            assert not bare, f"{module}.py has validate_path_id without param_name: {bare}"

    def test_no_bare_404_without_detail(self):
        """All HTTPException(404) should include a detail message."""
        for module in ("social", "admin", "notifications", "public_api"):
            src = (Path(__file__).resolve().parent.parent / f"{module}.py").read_text(encoding="utf-8")
            for line_no, line in enumerate(src.split("\n"), 1):
                if "raise HTTPException(404)" in line and "404," not in line:
                    assert False, f"{module}.py:{line_no} bare HTTPException(404) without detail"

    def test_admin_silent_passes_have_logging(self):
        """Dashboard/stats silent except blocks should log for debuggability."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        lines = src.split("\n")
        bare_passes = 0
        for i, line in enumerate(lines):
            if line.strip() == "except Exception:":
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if next_line == "pass":
                    bare_passes += 1
        assert bare_passes <= 15, f"admin.py has {bare_passes} silent except:pass blocks (expected <=15 after adding logging)"

    def test_pydantic_field_constraints_on_string_inputs(self):
        """All user-facing Pydantic str fields should have Field(max_length=...) to prevent oversized payloads."""
        from pydantic import Field as PydanticField
        import inspect

        # Models that accept user/admin string input
        from auth import OTPRequest, OTPVerify, PasswordLogin, SetPassword, CheckPhone, ProfileUpdate, PrivacyUpdate
        from social import CreatePost, CreateComment, BestAnswerBody
        from notifications import ReportRequest
        from admin import _EntityImageURL, RejectBody, BatchModerationBody

        models = [
            OTPRequest, OTPVerify, PasswordLogin, SetPassword, CheckPhone,
            ProfileUpdate, PrivacyUpdate,
            CreatePost, CreateComment, BestAnswerBody,
            ReportRequest,
            _EntityImageURL, RejectBody, BatchModerationBody,
        ]

        # Fields with field_validator enforcing length (skip — validator handles it)
        has_validator = {
            "CreatePost.content", "CreateComment.content",
        }

        unconstrained = []
        for model in models:
            for name, field_info in model.model_fields.items():
                if field_info.annotation is bool or field_info.annotation == bool:
                    continue
                anno = str(field_info.annotation or "")
                if "str" not in anno:
                    continue
                key = f"{model.__name__}.{name}"
                if key in has_validator:
                    continue
                has_max = any(hasattr(m, "max_length") for m in (field_info.metadata or []))
                if has_max:
                    continue
                unconstrained.append(key)
        assert not unconstrained, f"String fields without max_length: {unconstrained}"

    def test_all_write_endpoints_have_rate_limits(self):
        """Every POST/PUT/PATCH/DELETE endpoint in social.py and notifications.py should have check_rate."""
        for module_name in ("social", "notifications"):
            src = (Path(__file__).resolve().parent.parent / f"{module_name}.py").read_text(encoding="utf-8")
            lines = src.split("\n")
            for i, line in enumerate(lines):
                if "@router.post(" in line or "@router.put(" in line or "@router.patch(" in line or "@router.delete(" in line:
                    func_block = "\n".join(lines[i:i+8])
                    if "check_rate(" not in func_block and "require_admin" not in func_block:
                        assert False, f"{module_name}.py:{i+1} write endpoint without rate limit: {line.strip()}"

    def test_query_params_have_max_length(self):
        """All string Query() params should have max_length to prevent oversized queries."""
        import re
        for module_name in ("public_api", "admin", "notifications", "visits"):
            src = (Path(__file__).resolve().parent.parent / f"{module_name}.py").read_text(encoding="utf-8")
            for line_no, line in enumerate(src.split("\n"), 1):
                if re.search(r'Query\(None\s*\)', line) and "str" in line:
                    assert False, f"{module_name}.py:{line_no} Query(None) without max_length: {line.strip()}"

    def test_creation_endpoints_return_201(self):
        """POST endpoints that create resources should return 201."""
        for module_name, fn_names in [("social", ["create_post", "create_comment"]), ("admin", ["create_entity", "create_itinerary"])]:
            src = (Path(__file__).resolve().parent.parent / f"{module_name}.py").read_text(encoding="utf-8")
            for fn in fn_names:
                pattern = f"async def {fn}("
                idx = src.find(pattern)
                assert idx != -1, f"{fn} not found in {module_name}.py"
                before = src[max(0, idx-100):idx]
                assert "status_code=201" in before, f"{module_name}.py {fn} missing status_code=201"

    def test_privacy_visibility_enum_validation(self):
        """PrivacyUpdate model should validate profile_visibility enum at schema level."""
        from auth import PrivacyUpdate
        import pytest as pt
        PrivacyUpdate(profile_visibility="public")
        PrivacyUpdate(profile_visibility="private")
        PrivacyUpdate(profile_visibility="followers")
        with pt.raises(Exception):
            PrivacyUpdate(profile_visibility="invalid_value")

    def test_admin_router_has_csrf_dependency(self):
        """Admin router must enforce CSRF on all mutation endpoints."""
        from admin import router as admin_router
        dep_names = []
        for dep in admin_router.dependencies:
            if hasattr(dep, "dependency"):
                dep_names.append(dep.dependency.__name__)
        assert "require_csrf" in dep_names, "Admin router missing require_csrf dependency"

    def test_all_mutation_routers_have_csrf(self):
        """All routers with POST/PUT/DELETE must have CSRF on individual endpoints or router-level."""
        from pathlib import Path
        import re
        for module_name in ("social", "auth", "notifications"):
            src = (Path(__file__).resolve().parent.parent / f"{module_name}.py").read_text(encoding="utf-8")
            lines = src.split("\n")
            for i, line in enumerate(lines):
                if re.search(r'@router\.(post|put|delete|patch)\(', line):
                    func_block = "\n".join(lines[i:i+5])
                    if "csrf" not in func_block.lower() and "require_admin" not in func_block:
                        if "request_otp" in func_block or "verify_otp" in func_block or "login" in func_block or "check_phone" in func_block or "check_username" in func_block:
                            continue
                        assert False, f"{module_name}.py:{i+1} mutation endpoint without CSRF: {line.strip()}"

    def test_timezone_aware_datetime(self):
        """Production modules must use datetime.now(timezone.utc), not naive datetime.now()."""
        import re
        from pathlib import Path
        critical_modules = ["admin", "auth", "middleware", "server", "database", "analytics", "cost_tracker", "social", "public_api", "proactive", "realtime", "mcp_server", "scheduler"]
        for mod in critical_modules:
            src = (Path(__file__).resolve().parent.parent / f"{mod}.py").read_text(encoding="utf-8")
            for line_no, line in enumerate(src.split("\n"), 1):
                if "datetime.now()" in line and "#" not in line.split("datetime.now()")[0]:
                    assert False, f"{mod}.py:{line_no} uses naive datetime.now() — use datetime.now(timezone.utc)"

    def test_storage_path_traversal_protection(self):
        """Storage module must validate paths stay within LOCAL_MEDIA_DIR."""
        from storage import Storage
        src = (Path(__file__).resolve().parent.parent / "storage.py").read_text(encoding="utf-8")
        assert "is_relative_to" in src, "storage.py must use is_relative_to() for path traversal protection"
        assert src.count("is_relative_to") >= 2, "Both _put and delete must check is_relative_to"

    def test_comments_endpoint_has_offset(self):
        """Comments endpoint must support offset pagination."""
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def get_comments(")
        assert idx != -1
        func_block = src[idx:idx+1500]
        assert "offset" in func_block, "get_comments must accept offset parameter"
        assert "OFFSET" in func_block, "get_comments SQL must use OFFSET"

    def test_rate_limit_gc_threshold(self):
        """Rate limit GC must trigger at a reasonable threshold, not wait for 2000+ keys."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "_RATE_GC_THRESHOLD = 500" in src, "Rate limit GC threshold should be 500"
        assert "_RATE_MAX_KEYS" not in src, "Old _RATE_MAX_KEYS constant should be removed"

    def test_cors_env_check_case_insensitive(self):
        """CORS production check must match case-insensitive environment values."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        assert ".lower()" in src.split("CORS")[0].split("_env_name")[-1] or \
               "_env_name" in src and ".strip().lower()" in src, \
               "CORS environment check must be case-insensitive"
        assert '"prod"' in src or "'prod'" in src, "CORS must match 'prod' variant"
        assert '"prd"' in src or "'prd'" in src, "CORS must match 'prd' variant"

    def test_memory_sessions_max_size(self):
        """MemoryManager must cap sessions to prevent unbounded memory growth."""
        src = (Path(__file__).resolve().parent.parent / "memory.py").read_text(encoding="utf-8")
        assert "_MAX_SESSIONS" in src, "MemoryManager must define _MAX_SESSIONS"
        idx = src.find("def get_session")
        assert idx > 0
        block = src[idx:idx+500]
        assert "_MAX_SESSIONS" in block, "get_session must enforce max sessions"

    def test_skill_store_max_size(self):
        """SkillDocumentStore must cap skills to prevent unbounded list growth."""
        src = (Path(__file__).resolve().parent.parent / "memory.py").read_text(encoding="utf-8")
        assert "_MAX_SKILLS" in src, "SkillDocumentStore must define _MAX_SKILLS"
        idx = src.find("def add_skill")
        assert idx > 0
        block = src[idx:idx+800]
        assert "_MAX_SKILLS" in block, "add_skill must enforce max skills"

    def test_area_regex_no_unbounded_capture(self):
        """_AREA_PATTERNS regex must not use (.+?) which risks ReDoS on long input."""
        src = (Path(__file__).resolve().parent.parent / "memory.py").read_text(encoding="utf-8")
        idx = src.find("_AREA_PATTERNS")
        assert idx > 0
        block = src[idx:idx+300]
        assert "(.+?)" not in block, "_AREA_PATTERNS must use bounded capture group, not (.+?)"

    def test_storage_upload_uses_to_thread(self):
        """storage.upload_image must use asyncio.to_thread to avoid blocking event loop."""
        src = (Path(__file__).resolve().parent.parent / "storage.py").read_text(encoding="utf-8")
        idx = src.find("async def upload_image")
        assert idx > 0
        block = src[idx:idx+800]
        assert "to_thread" in block, "upload_image must use asyncio.to_thread for sync I/O"

    def test_sse_subscribers_has_lock(self):
        """SSE subscriber dict must be protected by asyncio.Lock."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        assert "_sse_lock" in src, "notifications.py must define _sse_lock for SSE subscribers"
        assert "async with _sse_lock" in src, "SSE subscriber mutations must use async with _sse_lock"
        assert src.count("async with _sse_lock") >= 2, "Both subscribe and unsubscribe must use lock"

    def test_get_post_has_block_check(self):
        """get_post must filter blocked users when viewing by direct URL."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def get_post(")
        assert idx > 0
        block = src[idx:idx+800]
        assert "_block_sql" in block, "get_post must call _block_sql to enforce block rules"

    def test_delete_post_cleans_reposts(self):
        """delete_post must nullify repost_of references to prevent orphan data."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def delete_post(")
        assert idx > 0
        block = src[idx:idx+1500]
        assert "repost_of" in block, "delete_post must handle repost_of references"

    def test_notification_dedup(self):
        """create_notification must deduplicate within 5-minute window."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("def create_notification(")
        assert idx > 0
        block = src[idx:idx+1500]
        assert "INTERVAL '5 minutes'" in block or "5 minutes" in block, \
            "create_notification must deduplicate recent notifications"

    def test_otp_verify_per_phone_rate_limit(self):
        """OTP verification must have per-phone rate limiting (not just per-IP)."""
        src = (Path(__file__).resolve().parent.parent / "auth.py").read_text(encoding="utf-8")
        assert "OTP_VERIFY_PHONE_LIMIT" in src, "Missing per-phone OTP rate limit"
        idx = src.find("async def verify_otp(")
        assert idx > 0
        block = src[idx:idx+800]
        assert "_otp_verify_phone_rate" in block, "verify_otp must check per-phone rate limit"

    def test_health_check_includes_llm_status(self):
        """Health core must include LLM status in overall assessment."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        idx = src.find("def _health_core(")
        assert idx > 0, "_health_core function must exist"
        block = src[idx:idx+500]
        assert "llm_ok" in block or "llm_status" in block, \
            "Health core must factor LLM status into overall assessment"

    def test_streaming_uses_list_join(self):
        """Chat streaming must use list+join, not string concatenation."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        assert '_chunks: list[str]' in src or '_chunks = []' in src, \
            "Streaming must use list to collect chunks (not string concatenation)"
        assert '"".join(_chunks)' in src, "Streaming must join chunks at end"

    def test_entity_delete_invalidates_cache(self):
        """Entity delete must invalidate entity cache, not just place cache."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def delete_entity(")
        assert idx > 0
        block = src[idx:idx+600]
        assert "invalidate_entity_cache" in block, "delete_entity must call invalidate_entity_cache"


# ═══════════════════════════════════════════════════════════════════════
#  MEDIUM-priority deep-scan fixes — batch 2
# ═══════════════════════════════════════════════════════════════════════

class TestMediumFixesBatch2:

    def test_plan_delete_returns_404_if_not_found(self):
        """DELETE /my-plans/{id} must check existence before deleting."""
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("async def remove_plan(")
        assert idx > 0
        block = src[idx:idx+800]
        assert "404" in block, "remove_plan must return 404 for non-existent plan"
        assert "SELECT 1" in block or "fetchone" in block.lower(), \
            "remove_plan must check existence before deleting"

    def test_homepage_cache_has_lock(self):
        """Homepage cache rebuild must use asyncio.Lock to prevent stampede."""
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        assert "_homepage_lock" in src, "public_api must define _homepage_lock"
        assert "asyncio.Lock()" in src, "Must use asyncio.Lock for homepage cache"

    def test_sitemap_50k_limit(self):
        """Sitemap must truncate URLs to Google's 50,000 limit."""
        src = (Path(__file__).resolve().parent.parent / "seo.py").read_text(encoding="utf-8")
        assert "50000" in src, "Sitemap must enforce 50,000 URL limit"
        assert "urls[:50000]" in src or "urls = urls[:50000]" in src, \
            "Sitemap must truncate to 50k"

    def test_bot_gateway_rejects_without_secret(self):
        """Zalo webhook must reject requests when ZALO_OA_SECRET is not configured."""
        src = (Path(__file__).resolve().parent.parent / "bot_gateway.py").read_text(encoding="utf-8")
        idx = src.find("async def zalo_webhook(")
        assert idx > 0
        block = src[idx:idx+600]
        assert "not ZALO_OA_SECRET" in block, \
            "Webhook must check for missing ZALO_OA_SECRET"
        assert "503" in block, "Must return 503 when secret not configured"

    def test_scheduler_has_retry_with_backoff(self):
        """Scheduler tasks must retry on failure with exponential backoff."""
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "_MAX_RETRIES" in src, "Scheduler must define _MAX_RETRIES"
        assert "_RETRY_BACKOFF_BASE" in src, "Scheduler must define _RETRY_BACKOFF_BASE"
        assert "_consecutive_failures" in src, "Tasks must track consecutive failures"

    def test_scheduler_retry_logic(self):
        """Scheduler retry: success resets counter, failure increments with backoff."""
        import time as _time
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scheduler import ScheduledTask, _MAX_RETRIES, _RETRY_BACKOFF_BASE

        call_count = 0
        def _failing_task():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("test failure")

        task = ScheduledTask("test_retry", _failing_task, 3600, timeout=5)
        assert task._consecutive_failures == 0

        task.run()
        assert task._consecutive_failures == 1
        assert task.next_run_after > _time.time()
        assert task.last_error == "test failure"

        task.next_run_after = 0
        task.run()
        assert task._consecutive_failures == 2

        def _ok_task():
            return "ok"
        task.func = _ok_task
        task.next_run_after = 0
        task.run()
        assert task._consecutive_failures == 0
        assert task.last_error is None

    def test_create_comment_block_check(self):
        """create_comment must check blocks between commenter and post author."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def create_comment(")
        assert idx > 0
        block = src[idx:idx+1500]
        assert "blocks" in block.lower(), "create_comment must check blocks table"
        assert "403" in block, "create_comment must return 403 if blocked"

    def test_audit_log_thread_lock(self):
        """Audit log write+rotate must be protected by threading.Lock."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert "_audit_lock" in src, "admin.py must define _audit_lock"
        assert "threading.Lock()" in src, "Must use threading.Lock for audit log"
        idx = src.find("def _log_admin_audit(")
        assert idx > 0
        block = src[idx:idx+400]
        assert "_audit_lock" in block, "_log_admin_audit must use _audit_lock"

    def test_update_post_optional_content(self):
        """update_post must handle None content (rating-only update)."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def update_post(")
        assert idx > 0
        block = src[idx:idx+3500]
        assert "new_content is None" in block, \
            "update_post must handle None content for rating-only updates"
        assert "elif set_rating" in block, \
            "update_post must have separate SQL branch for rating-only update"

    def test_trusted_proxies_whitespace_strip(self):
        """TRUSTED_PROXIES must strip whitespace from entries."""
        src = (Path(__file__).resolve().parent.parent / "middleware.py").read_text(encoding="utf-8")
        assert ".strip()" in src.split("TRUSTED_PROXIES")[1][:200], \
            "TRUSTED_PROXIES must strip whitespace from entries"

    def test_db_conn_putconn_safety(self):
        """DB _conn() must catch putconn exceptions to prevent pool leak."""
        src = (Path(__file__).resolve().parent.parent / "database.py").read_text(encoding="utf-8")
        idx = src.find("def _conn(self)")
        assert idx > 0
        block = src[idx:idx+900]
        assert "putconn" in block, "_conn must use putconn"
        after_putconn = block.split("putconn")[1][:200]
        assert "except" in after_putconn or "conn.close()" in after_putconn, \
            "_conn must wrap putconn in try/except to prevent pool leak"

    def test_nearby_entities_early_break(self):
        """nearby_entities first loop must break when limit reached."""
        src = (Path(__file__).resolve().parent.parent / "knowledge.py").read_text(encoding="utf-8")
        idx = src.find("# 1. Cùng placeId")
        assert idx > 0
        block = src[idx:idx+400]
        assert "len(nearby) >= limit" in block, \
            "First nearby loop must have early break at limit"

    def test_saved_max_limit(self):
        """saved.py must enforce a per-user save limit."""
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        assert "MAX_SAVED" in src, "saved.py must define MAX_SAVED"
        idx = src.find("async def add_saved(")
        assert idx > 0
        block = src[idx:idx+800]
        assert "MAX_SAVED" in block, "add_saved must check MAX_SAVED"

    def test_sse_eviction_sends_sentinel(self):
        """SSE subscriber eviction must send None sentinel to signal old generator."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("notification_stream")
        assert idx > 0
        block = src[idx:idx+2500]
        assert "put_nowait(None)" in block, \
            "SSE eviction must send None sentinel to old queue"

    def test_sse_generator_handles_none_sentinel(self):
        """SSE event generator must break on None sentinel."""
        src = (Path(__file__).resolve().parent.parent / "notifications.py").read_text(encoding="utf-8")
        idx = src.find("async def event_generator()")
        assert idx > 0
        block = src[idx:idx+800]
        assert "data is None" in block, \
            "Event generator must break on None sentinel from eviction"

    def test_favicon_endpoint_exists(self):
        """favicon.ico endpoint must return 204 to prevent 404 noise."""
        src = (Path(__file__).resolve().parent.parent / "seo.py").read_text(encoding="utf-8")
        assert "favicon.ico" in src, "seo.py must have /favicon.ico endpoint"
        assert "204" in src, "favicon must return 204"

    def test_site_settings_value_size_limit(self):
        """site_settings upsert must limit value size."""
        src = (Path(__file__).resolve().parent.parent / "site_settings.py").read_text(encoding="utf-8")
        assert "_MAX_VALUE_SIZE" in src, "site_settings must define _MAX_VALUE_SIZE"
        idx = src.find("def upsert(")
        assert idx > 0
        block = src[idx:idx+400]
        assert "_MAX_VALUE_SIZE" in block, "upsert must check _MAX_VALUE_SIZE"

    def test_smart_rank_get_popularity_holds_lock(self):
        """get_popularity must return inside the lock to prevent race condition."""
        src = (Path(__file__).resolve().parent.parent / "smart_rank.py").read_text(encoding="utf-8")
        idx = src.find("def get_popularity(")
        assert idx > 0
        block = src[idx:idx+300]
        lines = block.split("\n")
        return_line = None
        lock_indent = None
        for line in lines:
            if "with _lock:" in line:
                lock_indent = len(line) - len(line.lstrip())
            if "return _popularity" in line and lock_indent is not None:
                return_indent = len(line) - len(line.lstrip())
                assert return_indent > lock_indent, \
                    "return must be INSIDE the with _lock block (indented deeper)"
                return_line = line
                break
        assert return_line, "get_popularity must return _popularity.get inside lock"

    def test_data_quality_apply_safe_get(self):
        """data_quality apply_candidates must use .get() to avoid KeyError on deleted entities."""
        src = (Path(__file__).resolve().parent.parent / "data_quality.py").read_text(encoding="utf-8")
        idx = src.find("changed_ids")
        assert idx > 0
        block = src[idx:idx+200]
        assert "by_id.get(" in block, "Must use by_id.get() not by_id[] to avoid KeyError"


class TestDeepScanBatch3:
    """Tests for deep scan round 3: ratelimit + analytics hardening."""

    def test_penalty_box_race_safe(self):
        """is_in_penalty_box must use .get() to avoid KeyError on concurrent access."""
        src = (Path(__file__).resolve().parent.parent / "ratelimit.py").read_text(encoding="utf-8")
        idx = src.find("def is_in_penalty_box(")
        assert idx > 0
        block = src[idx:idx+400]
        assert "_penalty_box.get(" in block, "Must use .get() not [] to avoid race condition KeyError"
        assert "_penalty_box.pop(" in block, "Must use .pop() not del for thread-safe removal"
        assert "del _penalty_box[" not in block, "del _penalty_box[] is not thread-safe"

    def test_penalty_violations_gc_cleanup(self):
        """gc_all must clean up _penalty_violations for IPs no longer in penalty box."""
        src = (Path(__file__).resolve().parent.parent / "ratelimit.py").read_text(encoding="utf-8")
        idx = src.find("_penalty_violations.items()")
        assert idx > 0
        block = src[max(0, idx - 50):idx + 120]
        assert "_penalty_box" in block, "gc_all must check _penalty_box membership when cleaning violations"

    def test_entity_hits_capped(self):
        """entity_hits must be capped to prevent unbounded growth."""
        src = (Path(__file__).resolve().parent.parent / "analytics.py").read_text(encoding="utf-8")
        assert "_MAX_ENTITY_HITS" in src, "analytics must define _MAX_ENTITY_HITS"
        idx = src.find("def track_entity_hit(")
        assert idx > 0
        block = src[idx:idx+400]
        assert "_MAX_ENTITY_HITS" in block, "track_entity_hit must enforce cap"

    def test_save_conversation_error_handling(self):
        """save_conversation must catch OSError to prevent crashes."""
        src = (Path(__file__).resolve().parent.parent / "analytics.py").read_text(encoding="utf-8")
        idx = src.find("def save_conversation(")
        assert idx > 0
        block = src[idx:idx+600]
        assert "except OSError" in block or "except (OSError" in block, \
            "save_conversation must handle OSError"

    def test_db_pool_retry_flag_inside_lock(self):
        """Pool retry flag must be reset inside the lock to prevent race."""
        src = (Path(__file__).resolve().parent.parent / "database.py").read_text(encoding="utf-8")
        idx = src.find("def _get_pg_pool(")
        assert idx > 0
        block = src[idx:idx+500]
        lock_idx = block.find("with self._lock:")
        reset_idx = block.find("self._pg_pool_failed = False")
        assert lock_idx > 0 and reset_idx > 0, "Pool must have lock and reset"
        assert reset_idx > lock_idx, "Reset must happen INSIDE the lock, not before it"

    def test_publish_plan_verifies_rowcount(self):
        """publish_plan must check rowcount to detect missing/unauthorized plans."""
        src = (Path(__file__).resolve().parent.parent / "plans.py").read_text(encoding="utf-8")
        idx = src.find("def _query():")
        # Find the publish_plan context
        pub_idx = src.find("publish_plan")
        assert pub_idx > 0
        block = src[pub_idx:pub_idx+700]
        assert "rowcount" in block, "publish_plan must check cursor.rowcount"
        assert "404" in block, "publish_plan must raise 404 on zero rows"

    def test_ip_reputation_per_ip_cap(self):
        """IP reputation tracker must cap per-IP entries to prevent memory growth."""
        src = (Path(__file__).resolve().parent.parent / "middleware.py").read_text(encoding="utf-8")
        idx = src.find("def record(self, ip: str, event_type: str)")
        assert idx > 0
        block = src[idx:idx+400]
        assert "500" in block or "_decay" in block, \
            "record() must cap per-IP entries or prune within decay window"

    def test_moderation_history_gc(self):
        """_user_moderation_history must have GC to prevent unbounded growth."""
        src = (Path(__file__).resolve().parent.parent / "moderation.py").read_text(encoding="utf-8")
        idx = src.find("def record_moderation_outcome(")
        assert idx > 0
        block = src[idx:idx+500]
        assert "50_000" in block or "50000" in block, \
            "record_moderation_outcome must have GC cap (50k)"

    def test_storage_delete_toctou_safe(self):
        """storage.delete must use try/except not exists() check."""
        src = (Path(__file__).resolve().parent.parent / "storage.py").read_text(encoding="utf-8")
        idx = src.find("def delete(")
        assert idx > 0
        block = src[idx:idx+900]
        assert "FileNotFoundError" in block, \
            "delete must catch FileNotFoundError instead of TOCTOU exists() check"


class TestDeepScanBatch4:
    """Tests for deep scan round 4: streaming disconnect + cross-cutting."""

    def test_stream_producer_cancellation(self):
        """Streaming producer must check cancellation flag to stop when client disconnects."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        idx = src.find("def _produce_stream():")
        assert idx > 0
        block = src[idx:idx+500]
        assert "_cancelled" in block, \
            "Producer must check cancellation flag between chunks"
        assert "_cancelled.is_set()" in block, \
            "Producer must call _cancelled.is_set() to detect client disconnect"

    def test_stream_consumer_cancellation_handler(self):
        """Streaming consumer must handle CancelledError to signal producer."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        idx = src.find("_cancelled = threading.Event()")
        assert idx > 0
        block = src[idx:idx+2000]
        assert "CancelledError" in block or "GeneratorExit" in block, \
            "Consumer must catch disconnect exceptions to signal producer"
        assert "_cancelled.set()" in block, \
            "Consumer must set cancellation flag on disconnect"

    def test_image_upload_size_check(self):
        """Multipart image upload must check file size before processing."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        idx = src.find("image_recognize")
        assert idx > 0
        block = src[idx:idx+1200]
        assert "413" in block, "Must return 413 for oversized uploads"
        assert "10" in block, "Must enforce ~10MB limit"

    def test_review_stats_content_limit(self):
        """Review stats must LIMIT content rows to prevent unbounded fetch."""
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("review_stats")
        assert idx > 0
        block = src[idx:idx+1500]
        parts = block.split("content_rows")
        assert len(parts) >= 2
        after_content = parts[1]
        assert "LIMIT" in after_content, "Content query must have LIMIT"

    def test_list_places_has_limit(self):
        """Public list_places must have LIMIT to prevent unbounded results."""
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("list_places")
        assert idx > 0
        block = src[idx:idx+900]
        assert "LIMIT" in block, "list_places query must have LIMIT"

    def test_admin_rollback_no_exc_leak(self):
        """Admin rollback must not leak exception details in error response."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("rollback_apply")
        assert idx > 0
        block = src[idx:idx+300]
        assert "str(exc)" not in block, "Must not expose str(exc) in HTTP response"


class TestDeepScanBatch5:
    """Tests for deep scan round 5: budget enforcement, module scanning."""

    def test_budget_ram_fallback_on_disk_failure(self):
        """autonomous_budget must maintain in-memory counter when disk write fails."""
        src = (Path(__file__).resolve().parent.parent / "autonomous_budget.py").read_text(encoding="utf-8")
        assert "_ram_count" in src, \
            "Must have in-memory counter for budget enforcement fallback"
        idx = src.find("def try_consume")
        assert idx > 0
        block = src[idx:idx+800]
        assert "ram_count" in block, \
            "try_consume must use RAM counter alongside disk counter"
        assert "max(disk_count, ram_count)" in block or "max(disk_count," in block, \
            "Must use max of disk and RAM counts to prevent budget bypass"

    def test_budget_status_uses_ram_fallback(self):
        """Budget status must also use RAM counter for accurate reporting."""
        src = (Path(__file__).resolve().parent.parent / "autonomous_budget.py").read_text(encoding="utf-8")
        idx = src.find("def status()")
        assert idx > 0
        block = src[idx:idx+400]
        assert "ram_count" in block, \
            "status() must use RAM counter for accurate budget reporting"

    def test_budget_ram_counter_date_reset(self):
        """RAM counter must check date to reset on new day."""
        src = (Path(__file__).resolve().parent.parent / "autonomous_budget.py").read_text(encoding="utf-8")
        idx = src.find("def try_consume")
        assert idx > 0
        block = src[idx:idx+800]
        assert '_ram_count["date"]' in block or "_ram_count['date']" in block, \
            "Must update RAM counter date to detect day rollover"

    def test_entity_followers_notification_has_limit(self):
        """Entity follower notification query must have LIMIT to prevent unbounded fetch."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("_notify_entity_followers")
        assert idx > 0
        block = src[idx:idx+600]
        assert "LIMIT" in block, "Entity followers query must have LIMIT"

    def test_community_leaderboard_has_limit(self):
        """Community leaderboard SQL must have LIMIT to cap result set."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("community_leaderboard")
        assert idx > 0
        block = src[idx:idx+3000]
        assert "LIMIT 500" in block or "LIMIT 200" in block or "LIMIT 100" in block, \
            "Leaderboard query must have LIMIT to prevent unbounded results"

    def test_audit_rotation_atomic_write(self):
        """Audit log rotation must use atomic temp-rename for main file."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def _maybe_rotate_audit")
        assert idx > 0
        block = src[idx:idx+800]
        assert ".tmp" in block, "Rotation must use temp file for atomic write"
        assert ".replace(" in block, "Rotation must use replace() for atomic swap"

    def test_jsonl_rotation_atomic_write(self):
        """JSONL rotation must use atomic temp-rename for main file."""
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("_maybe_rotate_jsonl")
        assert idx > 0
        block = src[idx:idx+600]
        assert ".tmp" in block, "JSONL rotation must use temp file for atomic write"
        assert ".replace(" in block, "JSONL rotation must use replace() for atomic swap"

    def test_database_has_feed_index(self):
        """Database must have composite index for feed query performance."""
        src = (Path(__file__).resolve().parent.parent / "database.py").read_text(encoding="utf-8")
        assert "idx_posts_feed" in src, \
            "Must have composite index on posts(moderation_status, created_at) for feed performance"

    def test_database_has_notification_index(self):
        """Database must have index on notifications for user query performance."""
        src = (Path(__file__).resolve().parent.parent / "database.py").read_text(encoding="utf-8")
        assert "idx_notifications_user" in src, \
            "Must have index on notifications(user_id, created_at) for notification queries"


class TestEndpointAuthGuards:
    """Verify all internal endpoints have admin auth guards."""

    def _server_src(self):
        return (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")

    def test_health_public_is_minimal(self):
        """Public /health must NOT expose model, cache stats, or DB backend."""
        src = self._server_src()
        idx = src.find("async def health(")
        assert idx > 0
        block = src[idx:idx+300]
        for field in ["model", "cache", "rate_limits", "errors", "backend"]:
            assert field not in block, f"Public /health must not expose '{field}'"

    def test_health_detail_behind_admin(self):
        """/health/details must call require_admin."""
        src = self._server_src()
        idx = src.find("async def health_details(")
        assert idx > 0
        block = src[idx:idx+200]
        assert "require_admin" in block

    def test_health_deep_behind_admin(self):
        """/health/deep must call require_admin."""
        src = self._server_src()
        idx = src.find("async def deep_health(")
        assert idx > 0
        block = src[idx:idx+200]
        assert "require_admin" in block

    def test_health_slo_behind_admin(self):
        """/health/slo must call require_admin."""
        src = self._server_src()
        idx = src.find("async def slo_metrics(")
        assert idx > 0
        block = src[idx:idx+200]
        assert "require_admin" in block

    def test_metrics_behind_admin(self):
        """/metrics must call require_admin."""
        src = self._server_src()
        idx = src.find("async def metrics_endpoint(")
        assert idx > 0
        block = src[idx:idx+200]
        assert "require_admin" in block

    def test_system_endpoints_behind_admin(self):
        """All /system/* endpoints must call require_admin or verify_admin_key."""
        src = self._server_src()
        system_fns = [
            "system_logs", "system_errors", "system_response_times",
            "system_scheduler", "system_learning", "system_self_evolution",
            "system_memory", "system_traces", "system_handoffs",
            "system_memory_graph", "system_quality",
            "circuit_breaker_stats", "guardrails_status",
            "cost_tracker_report", "cost_budget_status",
            "eval_latest", "optimizer_report",
            "semantic_cache_status", "judge_report",
            "dynamic_agents_report",
        ]
        for fn in system_fns:
            idx = src.find(f"async def {fn}(")
            assert idx > 0, f"Function {fn} must exist"
            block = src[idx:idx+300]
            assert "require_admin" in block or "verify_admin_key" in block, \
                f"{fn} must have admin auth guard"

    def test_analytics_behind_admin(self):
        """All /analytics/* endpoints must call require_admin."""
        src = self._server_src()
        for fn in ["analytics_summary", "analytics_popular", "analytics_gaps",
                    "analytics_daily", "analytics_top_entities"]:
            idx = src.find(f"async def {fn}(")
            assert idx > 0, f"Function {fn} must exist"
            block = src[idx:idx+200]
            assert "require_admin" in block, f"{fn} must have admin auth guard"

    def test_checkpoint_endpoints_behind_admin(self):
        """Checkpoint/confirmation endpoints must call require_admin."""
        src = self._server_src()
        for fn in ["list_checkpoints", "save_checkpoint", "resume_checkpoint",
                    "pending_confirmations", "confirm_action", "reject_action"]:
            idx = src.find(f"async def {fn}(")
            assert idx > 0, f"Function {fn} must exist"
            block = src[idx:idx+300]
            assert "require_admin" in block, f"{fn} must have admin auth guard"

    def test_middleware_gates_internal_paths(self):
        """Middleware must gate /system, /analytics, /checkpoints, /confirm, /reject in prod."""
        src = self._server_src()
        idx = src.find("gate_internal_endpoints")
        assert idx > 0
        block = src[idx:idx+1200]
        for path in ["/system", "/analytics", "/checkpoints", "/confirm/", "/reject/", "/freshness"]:
            assert path in block, f"Middleware must gate {path} in production"

    def test_suggested_follows_has_limit(self):
        """Suggested-follows SQL query must have LIMIT to prevent full table scan."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def suggested_follows(")
        assert idx > 0
        block = src[idx:idx+2000]
        assert "LIMIT" in block, "suggested_follows SQL must have LIMIT clause"


# ═══════════════════════════════════════════════════════════════════════
#  LLM Config — runtime-configurable AI settings
# ═══════════════════════════════════════════════════════════════════════

class TestLLMConfig:
    """Verify llm_config module structure and server.py wiring."""

    def test_llm_config_module_exports(self):
        """llm_config must export get_client, get_model, get_model_mini, get_status, update_config, reset_to_env."""
        import llm_config
        for fn_name in ["get_client", "get_model", "get_model_mini",
                        "get_status", "update_config", "reset_to_env"]:
            assert callable(getattr(llm_config, fn_name, None)), f"{fn_name} must be callable"

    def test_get_model_returns_string(self):
        import llm_config
        model = llm_config.get_model()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_model_mini_returns_string(self):
        import llm_config
        model = llm_config.get_model_mini()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_status_shape(self):
        import llm_config
        status = llm_config.get_status()
        assert "source" in status
        assert "base_url" in status
        assert "api_key_set" in status
        assert "api_key_preview" in status
        assert "model" in status
        assert "model_mini" in status
        assert status["source"] in ("env", "database")

    def test_get_client_returns_openai_instance(self):
        import os
        from openai import OpenAI
        old_key = os.environ.get("LLM_API_KEY")
        old_url = os.environ.get("LLM_BASE_URL")
        try:
            os.environ.setdefault("LLM_API_KEY", "test-key")
            os.environ.setdefault("LLM_BASE_URL", "http://localhost:1234")
            import llm_config
            llm_config._client = None
            llm_config._config = {}
            llm_config._ENV_DEFAULTS["api_key"] = os.environ["LLM_API_KEY"]
            llm_config._ENV_DEFAULTS["base_url"] = os.environ["LLM_BASE_URL"]
            c = llm_config.get_client()
            assert isinstance(c, OpenAI)
        finally:
            if old_key is None:
                os.environ.pop("LLM_API_KEY", None)
            if old_url is None:
                os.environ.pop("LLM_BASE_URL", None)

    def test_server_uses_llm_config_getters(self):
        """server.py must use get_client()/get_model()/get_model_mini() instead of static globals."""
        src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
        assert "from llm_config import get_client, get_model, get_model_mini" in src
        assert "client = OpenAI(" not in src, "Must not have static OpenAI client"
        assert "\nMODEL = " not in src, "Must not have static MODEL global"
        assert "\nMODEL_MINI = " not in src, "Must not have static MODEL_MINI global"

    def test_admin_llm_config_endpoints_exist(self):
        """admin.py must have GET/PUT /admin/llm-config and POST /admin/llm-config/reset."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert 'async def admin_get_llm_config(' in src
        assert 'async def admin_update_llm_config(' in src
        assert 'async def admin_reset_llm_config(' in src

    def test_no_server_import_client_in_admin(self):
        """admin.py must not import client from server (should use llm_config)."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        assert "from server import client" not in src

    def test_no_server_import_client_in_scheduler(self):
        """scheduler.py must not import client from server (should use llm_config)."""
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "from server import client" not in src


class TestCacheInvalidationOnEntityCRUD:
    """B2: LLM cache must be invalidated when entities are modified via _sync_kb."""

    def test_sync_kb_invalidates_cache(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        sync_fn = src[src.index("def _sync_kb():"):]
        sync_fn = sync_fn[:sync_fn.index("\ndef _safe(")]
        assert "cache.invalidate_all()" in sync_fn

    def test_update_entity_calls_sync_kb(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        update_fn = src[src.index("async def update_entity("):]
        update_fn = update_fn[:update_fn.index("\n@router.")]
        assert "_sync_kb()" in update_fn

    def test_delete_entity_calls_sync_kb(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        delete_fn = src[src.index("async def delete_entity("):]
        delete_fn = delete_fn[:delete_fn.index("\n\n\nclass")]
        assert "_sync_kb()" in delete_fn

    def test_bulk_delete_calls_sync_kb(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        bulk_fn = src[src.index("async def bulk_delete("):]
        bulk_fn = bulk_fn[:bulk_fn.index("\n@router.")]
        assert "_sync_kb()" in bulk_fn


class TestImageURLLengthValidation:
    """A3: Image URLs in CreatePost must have per-URL length limit."""

    def test_image_url_length_validated(self):
        from social import CreatePost
        # Valid short URLs should pass
        post = CreatePost(content="Test content for post", images=["https://example.com/img.jpg"])
        assert len(post.images) == 1

    def test_image_url_too_long_rejected(self):
        from social import CreatePost
        long_url = "https://example.com/" + "a" * 2100
        with pytest.raises(Exception):
            CreatePost(content="Test content for post", images=[long_url])


class TestPostDeletionCleanup:
    """B3: Post deletion uses soft delete (deleted_at), not hard DELETE."""

    def test_delete_post_uses_soft_delete(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        delete_fn = src[src.index("async def delete_post("):]
        delete_fn = delete_fn[:delete_fn.index("\n@router.")]
        assert "SET deleted_at" in delete_fn
        assert "DELETE FROM posts" not in delete_fn

    def test_feeds_filter_deleted_posts(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert src.count("deleted_at IS NULL") >= 30

    def test_public_api_filters_deleted_posts(self):
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        assert src.count("deleted_at IS NULL") >= 10


class TestInfoReportsLockShared:
    """Info reports file must be protected by a shared lock across public_api and admin."""

    def test_admin_uses_shared_jsonl_lock(self):
        import admin as admin_mod
        import public_api
        assert admin_mod._info_reports_lock is public_api._jsonl_lock, \
            "admin._info_reports_lock must be the SAME object as public_api._jsonl_lock"

    def test_info_report_action_uses_lock(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def info_report_action")
        assert idx > 0
        block = src[idx:idx+500]
        assert "_info_reports_lock" in block, \
            "info_report_action must use _info_reports_lock for thread safety"

    def test_trending_cache_has_asyncio_lock(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        assert "_trending_lock = asyncio.Lock()" in src
        assert "_leaderboard_lock = asyncio.Lock()" in src
        idx = src.find("async def trending_tags(")
        block = src[idx:idx+800]
        assert "_trending_lock" in block
        idx2 = src.find("async def community_leaderboard(")
        block2 = src[idx2:idx2+800]
        assert "_leaderboard_lock" in block2


class TestModerationNotifications:
    """Admin moderation actions must notify the post author."""

    def test_admin_imports_create_notification(self):
        import admin as admin_mod
        assert hasattr(admin_mod, "create_notification")

    def test_approve_post_calls_notification(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def approve_post(")
        assert idx > 0
        block = src[idx:idx+800]
        assert "create_notification(" in block, \
            "approve_post must call create_notification to inform the author"
        assert "RETURNING user_id" in block, \
            "approve_post must fetch user_id via RETURNING to identify the author"

    def test_reject_post_calls_notification(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def reject_post(")
        assert idx > 0
        block = src[idx:idx+800]
        assert "create_notification(" in block, \
            "reject_post must call create_notification to inform the author"
        assert "RETURNING user_id" in block, \
            "reject_post must fetch user_id via RETURNING to identify the author"

    def test_reject_notification_includes_reason(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def reject_post(")
        block = src[idx:idx+800]
        assert "Lý do:" in block, \
            "reject_post notification must include the rejection reason"

    def test_batch_moderation_calls_notification(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def batch_moderation(")
        assert idx > 0
        block = src[idx:idx+1600]
        assert "create_notification(" in block, \
            "batch_moderation must call create_notification for each affected post"
        assert "RETURNING id, user_id" in block, \
            "batch_moderation must fetch user_ids via RETURNING"


class TestDeleteRowcountChecks:
    """DELETE endpoints must check rowcount to avoid silent 200 on missing resources."""

    def test_delete_itinerary_checks_rowcount(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def delete_itinerary(")
        assert idx > 0
        block = src[idx:idx+400]
        assert "rowcount" in block, \
            "delete_itinerary must check rowcount to return 404 on missing itinerary"

    def test_delete_relationship_checks_rowcount(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def delete_relationship(")
        assert idx > 0
        block = src[idx:idx+500]
        assert "rowcount" in block, \
            "delete_relationship must check rowcount to return 404 on missing relationship"

    def test_approve_post_checks_existence(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def approve_post(")
        block = src[idx:idx+600]
        assert "if not row" in block or "rowcount" in block, \
            "approve_post must verify the post exists"

    def test_reject_post_checks_existence(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("async def reject_post(")
        block = src[idx:idx+600]
        assert "if not row" in block or "rowcount" in block, \
            "reject_post must verify the post exists"


class TestCommentParentValidation:
    """Comment parent_id must belong to the same post."""

    def test_create_comment_validates_parent_post(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def create_comment(")
        assert idx > 0
        block = src[idx:idx+2500]
        assert "post_id::text" in block and "parent_id" in block, \
            "create_comment must validate parent_id belongs to the same post_id"

    def test_parent_check_before_insert(self):
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def create_comment(")
        block = src[idx:idx+2500]
        parent_check_idx = block.find("Bình luận gốc không thuộc bài viết này")
        insert_idx = block.find("INSERT INTO comments")
        assert parent_check_idx > 0, "Must have parent-post validation error message"
        assert parent_check_idx < insert_idx, \
            "Parent validation must happen BEFORE the INSERT"


class TestSchedulerOverlapGuard:
    """Scheduler tasks must prevent overlapping execution."""

    def test_scheduled_task_has_is_running_flag(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        assert "_is_running" in src, \
            "ScheduledTask must have _is_running flag to prevent overlapping execution"

    def test_should_run_checks_is_running(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        idx = src.find("def should_run(self)")
        block = src[idx:idx+300]
        assert "_is_running" in block, \
            "should_run must check _is_running to prevent concurrent execution"

    def test_run_sets_and_clears_flag(self):
        src = (Path(__file__).resolve().parent.parent / "scheduler.py").read_text(encoding="utf-8")
        idx = src.find("def run(self)")
        block = src[idx:idx+3000]
        assert "self._is_running = True" in block, \
            "run() must set _is_running = True at start"
        assert "self._is_running = False" in block, \
            "run() must clear _is_running in finally block"
        assert "finally:" in block, \
            "run() must use finally to guarantee _is_running is cleared"


class TestSavedMergeCap:
    """Verify merge_saved enforces MAX_SAVED cap."""

    def test_merge_has_max_saved_enforcement(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        idx = src.find("def merge_saved")
        assert idx != -1, "merge_saved function must exist"
        block = src[idx:idx+800]
        assert "MAX_SAVED" in block, \
            "merge_saved must reference MAX_SAVED to enforce limit"
        assert "DELETE" in block, \
            "merge_saved must trim excess items after upsert"

    def test_merge_trims_oldest(self):
        src = (Path(__file__).resolve().parent.parent / "saved.py").read_text(encoding="utf-8")
        idx = src.find("def merge_saved")
        block = src[idx:idx+1200]
        assert "ORDER BY created_at ASC" in block, \
            "merge_saved must delete OLDEST items when trimming"


class TestBotMessageTruncation:
    """Verify bot gateway truncates incoming message text."""

    def test_telegram_text_truncated(self):
        src = (Path(__file__).resolve().parent.parent / "bot_gateway.py").read_text(encoding="utf-8")
        idx = src.find("async def _tg_message")
        assert idx != -1
        block = src[idx:idx+500]
        assert "[:5000]" in block, \
            "Telegram message text must be truncated to 5000 chars"

    def test_zalo_text_truncated(self):
        src = (Path(__file__).resolve().parent.parent / "bot_gateway.py").read_text(encoding="utf-8")
        idx = src.find("handle_zalo_event")
        assert idx != -1
        block = src[idx:idx+800]
        assert "[:5000]" in block, \
            "Zalo message text must be truncated to 5000 chars"


class TestReportIpPseudonymization:
    """Verify report/contact-view logs pseudonymize IPs."""

    def test_report_uses_ip_hash(self):
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("def submit_report")
        assert idx != -1
        block = src[idx:idx+1200]
        assert "ip_hash" in block, \
            "submit_report must store ip_hash, not raw ip"
        assert '"ip": ip' not in block, \
            "submit_report must NOT store raw ip"

    def test_contact_view_uses_ip_hash(self):
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("def track_contact_view")
        assert idx != -1
        block = src[idx:idx+500]
        assert "ip_hash" in block, \
            "track_contact_view must store ip_hash, not raw ip"


class TestAdminBugFixes:
    """Verify admin.py bug fixes: row_to_dict, search pagination, image delete."""

    def test_stats_uses_row_to_dict_for_counts(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def admin_stats")
        assert idx != -1
        block = src[idx:idx+6000]
        assert 'rel_count["c"]' not in block, \
            "admin_stats must use db._row_to_dict(rel_count) not raw row access"
        assert 'itin_count["c"]' not in block, \
            "admin_stats must use db._row_to_dict(itin_count) not raw row access"
        assert "_row_to_dict(rel_count)" in block or "row_to_dict(rel_count)" in block
        assert "_row_to_dict(itin_count)" in block or "row_to_dict(itin_count)" in block

    def test_moderation_queue_uses_row_to_dict(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def moderation_queue")
        assert idx != -1
        block = src[idx:idx+1500]
        assert 'total["c"]' not in block, \
            "moderation_queue total must use _row_to_dict"

    def test_search_pagination_correct_total(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def list_entities")
        assert idx != -1
        block = src[idx:idx+2000]
        assert "limit=10000" in block or "limit=5000" in block or "limit=2000" in block, \
            "search path must fetch matches with bounded cap for correct total count"
        assert "all_matches" in block, \
            "search path should use all_matches for correct total"

    def test_remove_image_rejects_invalid_index(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def remove_entity_image")
        assert idx != -1
        block = src[idx:idx+600]
        assert "HTTPException" in block and "400" in block, \
            "remove_entity_image must raise 400 on invalid index"

    def test_audit_cache_invalidated_on_write(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def _log_admin_audit")
        assert idx != -1
        block = src[idx:idx+900]
        assert '_audit_cache["mtime"]' in block and "= 0" in block, \
            "_log_admin_audit must invalidate audit cache after write"

    def test_media_gallery_stats_computed_before_filter(self):
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def media_gallery")
        assert idx != -1
        block = src[idx:idx+2500]
        total_idx = block.find("total_images = len(media_items)")
        filter_idx = block.find('if filter == "missing_credit"')
        assert total_idx != -1, "media_gallery must compute total_images before filtering"
        assert filter_idx != -1
        assert total_idx < filter_idx, \
            "total_images must be computed BEFORE filter is applied"

    def test_entity_list_pagination_uses_count(self):
        """Non-search entity list must use count_entities_filtered for total, not len(results)."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def list_entities")
        assert idx != -1
        block = src[idx:idx+2500]
        assert "count_entities_filtered" in block, \
            "Non-search path must use count_entities_filtered for accurate pagination total"

    def test_include_places_queries_places_directly(self):
        """include_places must query places from DB, not list_entities (which excludes places)."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def list_entities")
        assert idx != -1
        block = src[idx:idx+2500]
        assert "type = 'place'" in block, \
            "include_places should query entities WHERE type = 'place' directly"

    def test_user_search_like_escaped(self):
        """Admin user search must escape LIKE wildcards in search term."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def list_users")
        assert idx != -1
        block = src[idx:idx+1500]
        assert "_escape_like" in block or "escape_like" in block, \
            "list_users search must escape LIKE wildcards"
        assert "ESCAPE" in block, \
            "list_users LIKE clause must have ESCAPE"

    def test_unban_user_uses_row_to_dict(self):
        """unban_user must use _row_to_dict before dict-style access."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def unban_user")
        assert idx != -1
        block = src[idx:idx+800]
        assert "_row_to_dict" in block, \
            "unban_user must convert fetchone result with _row_to_dict"

    def test_set_user_role_uses_row_to_dict(self):
        """set_user_role must use _row_to_dict before dict-style access."""
        src = (Path(__file__).resolve().parent.parent / "admin.py").read_text(encoding="utf-8")
        idx = src.find("def set_user_role")
        assert idx != -1
        block = src[idx:idx+800]
        assert "_row_to_dict" in block, \
            "set_user_role must convert fetchone result with _row_to_dict"

    def test_search_api_strips_html_from_q(self):
        """Search API must strip HTML tags from returned q (XSS defense-in-depth)."""
        src = (Path(__file__).resolve().parent.parent / "public_api.py").read_text(encoding="utf-8")
        idx = src.find("async def search(")
        assert idx != -1
        block = src[idx:idx+800]
        assert "re.sub" in block or "_strip_html" in block or "html.escape" in block, \
            "Search endpoint must sanitize q before returning"

    def test_social_search_strips_html_from_q(self):
        """Social search endpoints must strip HTML tags from returned q."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        for fn in ["async def search_posts", "async def search_users"]:
            idx = src.find(fn)
            assert idx != -1, f"{fn} not found"
            end_idx = src.find("\n@router.", idx + 1)
            if end_idx == -1:
                end_idx = idx + 3000
            block = src[idx:end_idx]
            assert "_strip_html_tags(q)" in block, \
                f"{fn} must pass q through _strip_html_tags before returning"

    def test_following_followers_block_enforcement(self):
        """following/followers endpoints must apply _block_sql filter."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        for fn in ["async def list_following_users", "async def list_followers"]:
            idx = src.find(fn)
            assert idx != -1, f"{fn} not found"
            end_idx = src.find("\n@router.", idx + 1)
            block = src[idx:end_idx]
            assert "_block_sql" in block, f"{fn} must use _block_sql for block enforcement"
            assert "{bc}" in block, f"{fn} must include {{bc}} in SQL WHERE clause"

    def test_related_posts_block_enforcement(self):
        """related_posts endpoint must apply _block_sql filter."""
        src = (Path(__file__).resolve().parent.parent / "social.py").read_text(encoding="utf-8")
        idx = src.find("async def related_posts")
        assert idx != -1
        end_idx = src.find("\n@router.", idx + 1)
        block = src[idx:end_idx]
        assert "_block_sql" in block, "related_posts must use _block_sql"
        assert "get_current_user" in block, "related_posts must accept optional user for block filtering"
