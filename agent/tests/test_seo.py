"""Focused tests for retained SEO data loading and legacy sitemap retirement."""

import json
import os
import time
from pathlib import Path

import seo


def _write_data(path, entity_id, name):
    payload = {
        "entities": [{"id": entity_id, "name": name, "type": "product"}],
        "relationships": [],
        "itineraries": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    now = time.time()
    os.utime(path, (now, now))


def test_load_reloads_when_data_file_changes(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    _write_data(data_path, "entity-one", "Entity One")
    monkeypatch.setattr(seo, "DATA_PATH", data_path)
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", None)
    monkeypatch.setattr(seo, "_by_id_cache", None)

    assert seo._load()["entities"][0]["id"] == "entity-one"

    time.sleep(0.01)
    _write_data(data_path, "entity-two", "Entity Two")

    assert seo._load()["entities"][0]["id"] == "entity-two"


def test_mutable_main_sitemap_ownership_is_retired():
    source = Path(seo.__file__).read_text(encoding="utf-8")

    assert not hasattr(seo, "sitemap")
    assert '@router.get("/sitemap.xml"' not in source
    for retired_name in (
        "_sitemap_cache",
        "_sitemap_static_urls",
        "_sitemap_place_children",
        "_sitemap_place_urls",
        "_sitemap_detail_urls",
        "_sitemap_response",
    ):
        assert not hasattr(seo, retired_name)

    assert hasattr(seo, "sitemap_media")
    assert hasattr(seo, "sitemap_index")


def test_seo_has_no_legacy_entity_indexability_authority():
    for legacy_name in (
        "is_index_worthy",
        "_is_public",
        "_page_word_count",
        "_has_real_image",
        "INDEX_MIN_WORDS",
        "INDEX_RICH_WORDS",
    ):
        assert not hasattr(seo, legacy_name)
