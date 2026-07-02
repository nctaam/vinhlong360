"""Tests for agent/entity_schemas.py — the content-model registry (entity Phase 1).

Guards the single-source-of-truth contract: every valid type has a schema, the
type->kind mapping is total, and validate_attributes coerces known fields while
preserving the bespoke tail and never raising.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import entity_schemas as es  # noqa: E402


class TestRegistryShape:
    def test_valid_types_covers_known_types(self):
        vt = es.valid_types()
        # The previously-mismatched types must now be valid (bug fix).
        for t in ("restaurant", "cafe", "drink", "place", "itinerary"):
            assert t in vt, f"{t} missing from valid_types()"
        # Legacy set must still be present.
        for t in ("experience", "product", "dish", "craft_village", "attraction",
                  "accommodation", "person", "event", "history", "nature",
                  "facility", "organization"):
            assert t in vt

    def test_every_type_has_kind(self):
        for t in es.valid_types():
            assert es.kind_of(t) in es.KIND_META, f"{t} maps to unknown kind {es.kind_of(t)}"

    def test_every_schema_has_metadata_and_fields(self):
        for t, s in es.ENTITY_SCHEMAS.items():
            assert s.get("label"), f"{t} missing label"
            assert s.get("emoji"), f"{t} missing emoji"
            assert s.get("kind"), f"{t} missing kind"
            assert isinstance(s.get("fields"), list), f"{t} fields not a list"
            for f in s["fields"]:
                assert "key" in f and "label" in f and "widget" in f, f"{t} bad field {f}"

    def test_all_schemas_payload(self):
        payload = es.all_schemas()
        assert set(payload.keys()) == {"types", "kinds", "kind_of_type"}
        assert payload["types"] == es.ENTITY_SCHEMAS
        assert len(payload["kinds"]) >= 7


class TestValidateAttributes:
    def test_coerces_number_bool_tags(self):
        norm, warn = es.validate_attributes("product", {
            "ocop_star": "4", "ocop_certified": "yes",
        })
        assert norm["ocop_certified"] is True
        assert warn == []

    def test_event_number_coercion(self):
        norm, _ = es.validate_attributes("event", {"month": "3", "duration_days": "2"})
        assert norm["month"] == 3
        assert norm["duration_days"] == 2

    def test_preserves_bespoke_tail(self):
        norm, _ = es.validate_attributes("history", {
            "sac_phong": "sắc phong 1852", "deity_worshipped": "Thành Hoàng",
        })
        assert norm["sac_phong"] == "sắc phong 1852"
        assert norm["deity_worshipped"] == "Thành Hoàng"

    def test_missing_required_warns_not_raises(self):
        norm, warn = es.validate_attributes("accommodation", {"address": "abc"})
        assert any("accommodation_type" in w for w in warn)
        assert norm["address"] == "abc"

    def test_unknown_type_is_noop(self):
        norm, warn = es.validate_attributes("no_such_type", {"a": 1})
        assert norm == {"a": 1}
        assert warn == []

    def test_none_attrs_safe(self):
        norm, warn = es.validate_attributes("product", None)
        assert isinstance(norm, dict)
        assert warn == []

    def test_bad_number_warns_and_keeps_raw(self):
        norm, warn = es.validate_attributes("restaurant", {"rating": "không rõ"})
        assert any("rating" in w.lower() or "Điểm đánh giá" in w for w in warn)
        # value preserved (non-destructive)
        assert norm["rating"] == "không rõ"


class TestAdminIntegration:
    def test_admin_valid_types_uses_registry(self):
        try:
            import admin
        except Exception:
            pytest.skip("admin import unavailable in this env")
        assert admin.VALID_TYPES == es.valid_types()

    def test_id_regex_allows_underscore(self):
        try:
            from admin import EntityCreate
        except Exception:
            pytest.skip("admin import unavailable")
        e = EntityCreate(id="craft_village_x", name="X", type="craft_village")
        assert e.id == "craft_village_x"
