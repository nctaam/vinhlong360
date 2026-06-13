"""Tests for SEO data reload and sitemap caching."""

import json
import os
import time

import seo


def _write_data(path, entity_id, name):
    payload = {
        "entities": [
            {"id": entity_id, "name": name, "type": "product", "updatedAt": "2026-06-12"},
        ],
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
    monkeypatch.setattr(seo, "_sitemap_cache", None)

    assert seo._load()["entities"][0]["id"] == "entity-one"

    time.sleep(0.01)
    _write_data(data_path, "entity-two", "Entity Two")

    assert seo._load()["entities"][0]["id"] == "entity-two"


def test_sitemap_cache_invalidates_with_data_mtime(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    _write_data(data_path, "entity-one", "Entity One")
    monkeypatch.setattr(seo, "DATA_PATH", data_path)
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", None)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    monkeypatch.setattr(seo, "_sitemap_cache", None)

    first = seo.sitemap()
    assert "max-age=300" in first.headers["Cache-Control"]
    assert b"entity-one" in first.body

    time.sleep(0.01)
    _write_data(data_path, "entity-two", "Entity Two")
    second = seo.sitemap()

    assert b"entity-two" in second.body
    assert b"entity-one" not in second.body
