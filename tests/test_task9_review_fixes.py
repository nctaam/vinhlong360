"""Regression tests for the independent Task 9 review findings."""

from __future__ import annotations

import asyncio
import json
import sys



def test_completeness_overview_marks_zero_denominator_not_applicable(monkeypatch):
    from entities import admin_api

    monkeypatch.setattr(admin_api.knowledge, "_entities", {})
    result = asyncio.run(admin_api.completeness_overview())

    assert result["total_entities"] == 0
    for field in ("source", "images", "place_id", "summary"):
        assert result[field]["pct"] is None
        assert result[field]["status"] == "not_applicable"
    assert result["overall_pct"] is None
    assert result["overall_status"] == "not_applicable"


def test_completeness_overview_overall_percentage_is_bounded(monkeypatch):
    from entities import admin_api

    entities = {
        f"entity-{i}": {
            "type": "attraction",
            "source": [{"url": "https://example.com/source"}],
            "images": ["/img.webp"],
            "placeId": "place-1",
            "summary": "A useful summary",
            "attributes": {},
        }
        for i in range(2)
    }
    monkeypatch.setattr(admin_api.knowledge, "_entities", entities)
    result = asyncio.run(admin_api.completeness_overview())

    assert result["overall_pct"] == 100.0
    assert result["overall_status"] == "measured"
    assert 0 <= result["overall_pct"] <= 100


def test_sqlite_search_matches_source_only_entity(tmp_path, monkeypatch):
    import database

    monkeypatch.setattr(database, "USE_PG", False)
    monkeypatch.setattr(database, "DATABASE_URL", "")
    db = database.Database(str(tmp_path / "source-search.db"))
    db.upsert_entity({
        "id": "source-only",
        "type": "attraction",
        "name": "Unrelated name",
        "summary": "",
        "source": [{"title": "Dua Sap Guide", "url": "https://example.com/dua-sap"}],
    })

    rows = db.search_entities(q="dua sap", limit=10)

    assert [row["id"] for row in rows] == ["source-only"]


def test_postgres_source_search_casts_jsonb_to_text():
    import database

    conditions: list[str] = []
    params: list[str] = []
    database._append_q_filter(conditions, params, "%s", True, "dua sap")

    clause = conditions[0]
    assert "CAST(e.source AS TEXT)" in clause
    assert "lower(CAST(e.source AS TEXT))" in clause


def test_semantic_cache_refreshes_worker_loaded_before_manifest_exists(tmp_path, monkeypatch):
    import semantic_cache as cache_module

    manifest = tmp_path / "entries.json"
    monkeypatch.setattr(cache_module, "ENTRIES_FILE", manifest)
    first = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    second = cache_module.MultiTierCache(cache_module.SemanticMatcher())

    assert second.get("written later") is None
    first.put("written later", {"worker": 1})

    assert second.get("written later") == {"worker": 1}


def test_semantic_cache_external_invalidate_evicts_stale_l1(tmp_path, monkeypatch):
    import semantic_cache as cache_module

    manifest = tmp_path / "entries.json"
    monkeypatch.setattr(cache_module, "ENTRIES_FILE", manifest)
    first = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    second = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    first.put("cross worker delete", {"version": 1})
    assert first.get("cross worker delete") == {"version": 1}
    second.invalidate("cross worker delete")

    assert first.get("cross worker delete") is None


def test_semantic_cache_invalidate_after_missing_manifest_load_wins_over_remote_put(
    tmp_path, monkeypatch
):
    import semantic_cache as cache_module

    manifest = tmp_path / "entries.json"
    monkeypatch.setattr(cache_module, "ENTRIES_FILE", manifest)
    first = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    second = cache_module.MultiTierCache(cache_module.SemanticMatcher())

    # Worker B snapshots an empty manifest before worker A creates the file.
    assert second.get("missing manifest race") is None
    first.put("missing manifest race", {"worker": "a"})

    second.invalidate("missing manifest race")

    assert first.get("missing manifest race") is None
    key = cache_module._make_key("missing manifest race")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    assert records[key]["deleted"] is True


def test_semantic_cache_stale_put_cannot_resurrect_tombstone(tmp_path, monkeypatch):
    import semantic_cache as cache_module

    manifest = tmp_path / "entries.json"
    monkeypatch.setattr(cache_module, "ENTRIES_FILE", manifest)
    first = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    second = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    first.put("tombstone race", {"version": 1})
    second.get("tombstone race")
    second.invalidate("tombstone race")
    first.put("tombstone race", {"version": "stale"})

    assert second.get("tombstone race") is None
    assert first.get("tombstone race") is None


def test_semantic_cache_stale_same_key_put_preserves_newer_worker_value(tmp_path, monkeypatch):
    import semantic_cache as cache_module

    manifest = tmp_path / "entries.json"
    monkeypatch.setattr(cache_module, "ENTRIES_FILE", manifest)
    first = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    second = cache_module.MultiTierCache(cache_module.SemanticMatcher())
    first.put("same key race", {"version": 1})
    second.get("same key race")
    second.put("same key race", {"version": 2})
    first.put("same key race", {"version": "stale"})

    assert first.get("same key race") == {"version": 2}
    assert second.get("same key race") == {"version": 2}


def test_geocode_cache_refreshes_after_external_worker_write(tmp_path, monkeypatch):
    import geocode

    cache_file = tmp_path / "geocode.json"
    monkeypatch.setattr(geocode, "CACHE_FILE", cache_file)
    monkeypatch.setattr(geocode, "_cache", None)
    monkeypatch.setattr(geocode, "_cache_mtime_ns", None, raising=False)
    monkeypatch.setattr(geocode, "_cache_stats", {
        "cache_hits": 0,
        "duplicate_writes": 0,
        "lost_update_prevented": 0,
        "cache_refreshes": 0,
    })

    assert geocode._load_cache() == {}
    cache_file.write_text(json.dumps({"external-key": [10.1, 106.1]}), encoding="utf-8")

    assert geocode._load_cache()["external-key"] == [10.1, 106.1]
    assert geocode.stats()["cache_refreshes"] >= 1


def test_geocode_save_does_not_overwrite_external_same_key_write(tmp_path, monkeypatch):
    import geocode

    cache_file = tmp_path / "geocode.json"
    monkeypatch.setattr(geocode, "CACHE_FILE", cache_file)
    monkeypatch.setattr(geocode, "_cache", None)
    monkeypatch.setattr(geocode, "_cache_mtime_ns", None, raising=False)
    monkeypatch.setattr(geocode, "_cache_snapshot", None, raising=False)
    monkeypatch.setattr(geocode, "_cache_stats", {
        "cache_hits": 0,
        "duplicate_writes": 0,
        "lost_update_prevented": 0,
        "cache_refreshes": 0,
    })

    geocode._load_cache()["same-place"] = [10.1, 106.1]
    geocode._save_cache()
    geocode._load_cache()["same-place"] = [10.2, 106.2]
    cache_file.write_text(json.dumps({"same-place": [10.3, 106.3]}), encoding="utf-8")
    geocode._save_cache()

    assert json.loads(cache_file.read_text(encoding="utf-8"))["same-place"] == [10.3, 106.3]
    assert geocode.stats()["lost_update_prevented"] >= 1


def test_vector_search_namespace_aliases_share_module_identity():
    import features
    import semantic_cache

    top_level = sys.modules.get("vector_search")
    package_level = sys.modules.get("agent.vector_search")

    assert top_level is not None
    assert package_level is not None
    assert top_level is package_level
    assert features.embedding_store.__class__.__module__ == package_level.__name__
    assert semantic_cache._tokenize is package_level.tokenize


def test_stale_queue_mark_reviewed_uses_canonical_upsert_writer(monkeypatch):
    from entities import admin_api

    calls: list[tuple[str, dict]] = []
    entity = {"id": "stale-1", "type": "attraction", "attributes": {}}

    class FakeDB:
        def get_entity(self, entity_id):
            assert entity_id == "stale-1"
            return dict(entity)

        def upsert_entity(self, value, **kwargs):
            calls.append(("upsert_entity", value))

    monkeypatch.setattr(admin_api, "db", FakeDB())
    result = asyncio.run(admin_api.stale_mark_reviewed("stale-1"))

    assert result["ok"] is True
    assert calls and calls[0][0] == "upsert_entity"
    assert calls[0][1]["attributes"]["stale_reviewed_at"]
