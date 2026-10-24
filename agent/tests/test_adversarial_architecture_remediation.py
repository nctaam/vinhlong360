"""Regression tests for Adversarial System Architecture Audit 2026 (Campaign Alpha)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import config  # noqa: E402
import contextual_retrieval  # noqa: E402
import database  # noqa: E402
import entity_details as _entity_details  # noqa: E402
import guardrails  # noqa: E402
import middleware  # noqa: E402
import orchestrator  # noqa: E402
import privacy_boundary  # noqa: E402
import semantic_cache  # noqa: E402
import seo  # noqa: E402
import vector_search  # noqa: E402
from cases import admin_api, correction, public_api, publication, store  # noqa: E402
from chat import api as chat_api  # noqa: E402
from entity_write import EntitySnapshot, _hydrate_loaded_attributes, _prepare_stored_patch  # noqa: E402
from siteops import admin_api as siteops_admin_api  # noqa: E402


def test_split_typed_maps_opening_hours_alias_to_hours_column():
    uni, _, _ = _entity_details.split_typed("attraction", {"opening_hours": "07:00 - 21:00"})
    assert uni["hours"] == "07:00 - 21:00"


def test_publication_and_correction_handle_opening_hours_alias():
    patch = publication._entity_patch(
        {"attributes.opening_hours": "08:00 - 20:00"},
        {"address": "Số 1"},
    )
    assert patch["attributes"]["opening_hours"] == "08:00 - 20:00"
    assert patch["attributes"]["hours"] == "08:00 - 20:00"
    entity_with_hours_only = {"attributes": {"hours": "06:30 - 18:00"}}
    assert correction.live_value_at(entity_with_hours_only, "attributes.opening_hours") == "06:30 - 18:00"
    assert publication._read_path(entity_with_hours_only, "attributes.opening_hours") == "06:30 - 18:00"


def test_hydrate_loaded_attributes_and_prepare_stored_patch(monkeypatch):
    monkeypatch.setattr(_entity_details, "reads_enabled", lambda: True)
    row = {
        "id": "a-1",
        "type": "attraction",
        "address": "Phường 1, Vĩnh Long",
        "hours": "07:00 - 19:00",
        "attributes": {"custom_note": "ven sông"},
    }
    attrs = _hydrate_loaded_attributes(row)
    assert attrs["address"] == "Phường 1, Vĩnh Long"
    assert attrs["hours"] == "07:00 - 19:00"
    assert attrs["custom_note"] == "ven sông"
    fake_conn = SimpleNamespace(cursor=lambda: None)
    snap = EntitySnapshot(entity_id="a-1", revision=1, values={"type": "attraction"})
    can_sync, etype, stored = _prepare_stored_patch(
        fake_conn,
        snap,
        {"attributes": {"address": "Mới", "hours": "08:00", "custom_note": "giữ"}},
    )
    assert can_sync is True
    assert etype == "attraction"
    assert stored["attributes"] == {"custom_note": "giữ"}


def test_select_forwarded_ip_parses_right_to_left_against_spoofing(monkeypatch):
    monkeypatch.setattr(middleware, "TRUSTED_PROXIES", {"127.0.0.1", "172.18.0.2"})
    spoofed = "1.2.3.4, 198.51.100.77, 172.18.0.2"
    assert middleware._select_forwarded_ip(spoofed) == "198.51.100.77"


def test_vietnamese_d_stroke_normalized_in_guardrails_and_orchestrator():
    variants = guardrails._prompt_variants("Địa điểm")
    assert any("dia diem" in v for v in variants)
    assert "duong di" in orchestrator._strip_diacritics("Đường đi").lower()


def test_vector_search_tokenize_emits_unaccented_vietnamese_tokens():
    tokens = vector_search.tokenize("Bánh xèo hến cù lao Dài")
    assert "banh" in tokens
    assert "xeo" in tokens
    assert "banh_xeo" in tokens
    assert "dai" in tokens


def test_semantic_cache_evict_l2_records_tombstone():
    cache = semantic_cache.MultiTierCache(semantic_cache.SemanticMatcher(), l1_max=2, l2_max=2)
    cache._l2_loaded = True
    cache._l2["k1"] = {"response": "r1", "timestamp": 1000, "ttl": 3600}
    cache._l2["k2"] = {"response": "r2", "timestamp": 1001, "ttl": 3600}
    cache._l2["k3"] = {"response": "r3", "timestamp": 1002, "ttl": 3600}
    cache._evict_l2()
    assert len(cache._l2) == 2
    assert "k1" in cache._tombstones
    assert "k1" in cache._dirty_keys


def test_prepare_chat_output_logs_when_output_guard_flags_reply(monkeypatch, caplog):
    monkeypatch.setattr(
        privacy_boundary,
        "check_output",
        lambda reply, query, entities: {
            "cleaned_reply": reply,
            "valid": False,
            "hallucination_score": 0.85,
            "issues": ["unverified_entity"],
        },
    )
    with caplog.at_level("WARNING", logger="privacy_boundary"):
        safe = privacy_boundary.prepare_chat_output("Chào bạn", query="Hỏi", entities={})
    assert safe.text == "Chào bạn"
    assert any("Output guard flagged chat reply" in rec.message for rec in caplog.records)


def test_paired_remediation_modules_contracts():
    assert hasattr(admin_api, "_load_case_workbench_state")
    assert hasattr(public_api, "_rate_subject")
    assert hasattr(store, "PostgresCaseStore")
    assert hasattr(chat_api, "_resolve_rerank_allowed_ids")
    assert hasattr(siteops_admin_api, "router")
    assert hasattr(seo, "build_sitemap_images_xml")
    assert hasattr(database, "Database")
    assert hasattr(contextual_retrieval, "enhanced_hybrid_search")
    assert isinstance(config.settings.is_production, bool)


