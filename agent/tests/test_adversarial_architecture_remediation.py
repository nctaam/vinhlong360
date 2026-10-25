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
import freshness  # noqa: E402
import guardrails  # noqa: E402
import knowledge  # noqa: E402
import memory  # noqa: E402
import memory_graph  # noqa: E402
import middleware  # noqa: E402
import orchestrator  # noqa: E402
import privacy_boundary  # noqa: E402
import pytest  # noqa: E402
import semantic_cache  # noqa: E402
import seo  # noqa: E402
import server  # noqa: E402
import site_settings  # noqa: E402
import twofactor  # noqa: E402
import vector_search  # noqa: E402
from cases import admin_api, correction, public_api, publication, store  # noqa: E402
from chat import api as chat_api  # noqa: E402
from entities import api as entities_api  # noqa: E402
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
    assert hasattr(seo, "_load_seo_data")
    assert hasattr(database, "Database")
    assert hasattr(contextual_retrieval, "enhanced_hybrid_search")
    assert isinstance(config.settings.is_production, bool)


def test_site_settings_get_llm_settings_uses_ttl_cache_and_invalidates(monkeypatch):
    site_settings._invalidate()
    site_settings._llm_cache = {"llm.model": "gpt-4o-mini"}
    site_settings._llm_cache_ts = site_settings.time.time()

    class _ExplodeDB:
        _use_pg = True

        def _conn(self):
            raise AssertionError("DB should not be queried when _llm_cache is warm")

    monkeypatch.setattr(site_settings, "db", _ExplodeDB())
    assert site_settings.get_llm_settings() == {"llm.model": "gpt-4o-mini"}
    site_settings._invalidate()
    assert site_settings._llm_cache is None


def test_cold_memory_evicts_oldest_anonymous_profile_at_erasure_cap(monkeypatch):
    cold = memory.ColdMemory.__new__(memory.ColdMemory)
    cold._profiles = {"anon_1": memory.UserProfile("anon_1"), "user_keep": memory.UserProfile("user_keep")}
    cold._profiles["user_keep"].interaction_count = 10
    cold._lock = memory.RLock()
    monkeypatch.setattr(cold, "_MAX_ERASURE_PROFILES", 2)
    prof = cold.get_profile("user_new")
    assert prof.user_id == "user_new"
    assert len(cold._profiles) == 2
    assert "anon_1" not in cold._profiles
    assert "user_keep" in cold._profiles


def test_freshness_load_data_prefers_db_when_default_path(monkeypatch):
    import knowledge

    monkeypatch.setattr(freshness, "DATA_JSON", freshness.ROOT / "web" / "data.json")
    monkeypatch.setattr(knowledge, "_data_source", "db")
    monkeypatch.setattr(knowledge, "_entities", {"db-ent-1": {"id": "db-ent-1", "type": "dish"}})
    loaded = freshness._load_data()
    assert loaded == {"entities": [{"id": "db-ent-1", "type": "dish"}]}


def test_twofactor_app_secret_raises_in_production_without_secret(monkeypatch):
    monkeypatch.delenv("TOTP_ENC_KEY", raising=False)
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config.settings, "JWT_SECRET", "")
    monkeypatch.setattr(config.settings, "ADMIN_API_KEY", "")
    with pytest.raises(RuntimeError, match="TOTP encryption key missing in production"):
        twofactor._app_secret()


def test_memory_graph_evicts_weakest_items_at_erasure_cap(tmp_path, monkeypatch):
    g = memory_graph.MemoryGraph(graph_path=tmp_path / "graph.json", auto_save_every=999)
    monkeypatch.setattr(g, "_MAX_ERASURE_ITEMS", 3)
    g.add_node("anon_1", type="user")
    g.add_node("e1", type="entity")
    g.add_edge("anon_1", "e1", "discussed", weight=0.2)
    assert len(g._nodes) + len(g._edges) == 3
    g.add_node("e2", type="entity")
    assert len(g._nodes) + len(g._edges) <= 3
    assert "e2" in g._nodes


def test_knowledge_refresh_dependent_caches_invalidates_seo_and_loads_autocorrect(monkeypatch):
    import autocorrect as ac_mod

    seo._db_snapshot = {"entities": [{"id": "stale"}]}
    seo._db_snapshot_ts = 999999999.0
    captured = {}
    monkeypatch.setattr(ac_mod, "load_entity_names", lambda emap: captured.setdefault("emap", emap))
    knowledge._refresh_dependent_caches({"e1": {"id": "e1", "name": "Chùa Tiên Châu", "type": "attraction"}})
    assert seo._db_snapshot is None
    assert "e1" in captured["emap"]


def test_memory_encrypt_raises_in_production_without_fernet(monkeypatch):
    monkeypatch.setattr(memory, "_HAS_FERNET", False)
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="Fernet"):
        memory._encrypt("secret-profile")


@pytest.mark.anyio
async def test_server_limit_request_size_rejects_negative_content_length():
    req = SimpleNamespace(
        headers={"content-length": "-5"},
        url=SimpleNamespace(path="/api/chat"),
    )

    async def _call_next(_r):
        raise AssertionError("call_next must not run on negative Content-Length")

    resp = await server.limit_request_size(req, _call_next)
    assert resp.status_code == 400


def test_entities_fetch_best_answers_by_id_batches_in_single_query(monkeypatch):
    calls = []

    class _FakeDB:
        def _fetchall(self, _conn, sql, params):
            calls.append((sql, params))
            return [
                {
                    "id": "c-1",
                    "content": "Trả lời 1",
                    "created_at": "2026-01-01",
                    "user_id": "u-1",
                    "display_name": "An",
                    "avatar_url": None,
                    "username": "an",
                },
                {
                    "id": "c-2",
                    "content": "Trả lời 2",
                    "created_at": "2026-01-02",
                    "user_id": "u-2",
                    "display_name": "Bình",
                    "avatar_url": None,
                    "username": "binh",
                },
            ]

        def _row_to_dict(self, r):
            return dict(r)

    monkeypatch.setattr(entities_api, "db", _FakeDB())
    rows = [{"best_answer_id": "c-1"}, {"best_answer_id": None}, {"best_answer_id": "c-2"}]
    result = entities_api._fetch_best_answers_by_id(None, rows, "%s")
    assert len(calls) == 1
    assert calls[0][1] == ("c-1", "c-2")
    assert result["c-1"]["content"] == "Trả lời 1"
    assert result["c-2"]["user"]["display_name"] == "Bình"


def test_seo_snapshot_from_knowledge_memory_reuses_db_entities(monkeypatch):
    monkeypatch.setattr(knowledge, "_data_source", "db")
    monkeypatch.setattr(knowledge, "_entities", {"e1": {"id": "e1", "type": "dish"}})
    monkeypatch.setattr(knowledge, "_relationships", [{"from": "e1", "to": "e2"}])
    monkeypatch.setattr(knowledge, "_itineraries", {"i1": {"id": "i1"}})
    snap = seo._snapshot_from_knowledge_memory(database.db)
    assert snap is not None
    assert snap["entities"] == [{"id": "e1", "type": "dish"}]
    assert snap["relationships"] == [{"from": "e1", "to": "e2"}]
    assert snap["itineraries"] == [{"id": "i1"}]


def test_chat_generate_followups_short_circuits_when_breaker_open_and_truncates_huge_tool_output(monkeypatch):
    monkeypatch.setattr(chat_api, "_is_llm_circuit_open", lambda: True)
    assert chat_api.generate_followups("Ngữ cảnh") == []
    huge = "Vĩnh Long cù lao An Bình " * 6000
    safe = chat_api._safe_tool_result(huge, set())
    assert len(safe) < 132_000
    assert safe.endswith("...[truncated]")





