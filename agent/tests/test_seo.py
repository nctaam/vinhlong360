"""Tests for SEO data reload and sitemap caching."""

import json
import os
import time

import seo


def _write_data(path, entity_id, name):
    payload = {
        "entities": [
            # summary is rich enough to clear the P0-1 index-eligibility gate so the
            # entity reaches the sitemap; this test asserts cache invalidation, not
            # index-worthiness.
            {"id": entity_id, "name": name, "type": "product", "updatedAt": "2026-06-12",
             "summary": " ".join(["từ"] * 220)},
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


# ── P0-1: cổng chất lượng trước index (is_index_worthy) ──────────────────────

def _text(n: int) -> str:
    """A descriptive string of exactly ``n`` whitespace-separated words."""
    return " ".join(["từ"] * n)


def _entity(**over):
    e = {"id": "e1", "name": "Test", "type": "attraction", "updatedAt": "2026-06-12"}
    e.update(over)
    return e


def _reset_seo(monkeypatch, data_path):
    monkeypatch.setattr(seo, "DATA_PATH", data_path)
    for attr in ("_data", "_data_mtime_ns", "_by_id_cache", "_sitemap_cache"):
        monkeypatch.setattr(seo, attr, None)


def test_is_index_worthy_rich_text_no_image():
    # ≥200 descriptive words carries enough unique value on its own.
    assert seo.is_index_worthy(_entity(summary=_text(220))) is True


def test_is_index_worthy_medium_text_with_real_image():
    assert seo.is_index_worthy(
        _entity(summary=_text(120), images=["https://ex.com/p.jpg"])
    ) is True


def test_is_index_worthy_medium_text_without_image_excluded():
    # 100–199 words needs a real image to be index-worthy.
    assert seo.is_index_worthy(_entity(summary=_text(120))) is False


def test_is_index_worthy_thin_text_with_image_excluded():
    # Below the floor, a real image does not rescue a thin page.
    assert seo.is_index_worthy(
        _entity(summary=_text(30), images=["https://ex.com/p.jpg"])
    ) is False


def test_is_index_worthy_provisional_excluded_even_if_rich():
    assert seo.is_index_worthy(
        _entity(summary=_text(300), status="provisional")
    ) is False


def test_page_word_count_sums_distinct_lead_and_body():
    # The detail page renders the summary lead AND the description body.
    entity = _entity(summary=" ".join(["dan"] * 120), description=" ".join(["than"] * 90))
    assert seo._page_word_count(entity) == 210


def test_page_word_count_dedups_verbatim_body():
    # A description copied verbatim from the summary adds no content, so it is
    # counted once, not twice.
    text = _text(150)
    assert seo._page_word_count(_entity(summary=text, description=text)) == 150


def test_is_index_worthy_counts_summary_plus_description():
    # A page clears the bar on the sum of its two distinct blocks even when
    # neither block alone is long enough.
    n = seo.INDEX_RICH_WORDS - 10  # each block alone stays under the bar
    lead = " ".join(["dan"] * n)
    body = " ".join(["than"] * n)
    assert seo.is_index_worthy(_entity(summary=lead, description=body)) is True


def test_sitemap_excludes_thin_entity_pages(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "rich-entity", "name": "Rich", "type": "attraction",
             "summary": _text(220), "updatedAt": "2026-06-12"},
            {"id": "thin-entity", "name": "Thin", "type": "attraction",
             "summary": _text(20), "updatedAt": "2026-06-12"},
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)

    body = seo.sitemap().body
    assert b"rich-entity" in body
    assert b"thin-entity" not in body


def test_sitemap_changefreq_by_type_and_no_lastmod(tmp_path, monkeypatch):
    import re
    payload = {
        "entities": [
            {"id": "hist-1", "name": "H", "type": "history", "summary": _text(200), "updatedAt": "2026-06-12"},
            {"id": "ev-1", "name": "E", "type": "event", "summary": _text(200), "updatedAt": "2026-06-12"},
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)
    xml = seo.sitemap().body.decode()
    hist_block = re.search(r"<url>(?:(?!</url>).)*hist-1(?:(?!</url>).)*</url>", xml, re.S).group()
    assert "<changefreq>yearly</changefreq>" in hist_block   # P1-4: static heritage type
    ev_block = re.search(r"<url>(?:(?!</url>).)*ev-1(?:(?!</url>).)*</url>", xml, re.S).group()
    assert "<changefreq>weekly</changefreq>" in ev_block     # P1-4: events change often
    assert "<lastmod>" not in xml                            # P1-4: no misleading import-date lastmod


def test_sitemap_thin_ward_excluded(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "thin-ward", "name": "TW", "type": "place", "summary": _text(20)},
            {"id": "rich-ward", "name": "RW", "type": "place", "summary": _text(80)},
            {"id": "hub-ward", "name": "HW", "type": "place", "summary": _text(10)},
            {"id": "child-1", "name": "C1", "type": "dish", "placeId": "hub-ward", "summary": _text(200)},
            {"id": "child-2", "name": "C2", "type": "dish", "placeId": "hub-ward", "summary": _text(200)},
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)
    body = seo.sitemap().body
    assert b"/xa-phuong/thin-ward" not in body   # thin summary + no children → out (P1-5)
    assert b"/xa-phuong/rich-ward" in body        # rich summary → in
    assert b"/xa-phuong/hub-ward" in body         # thin summary but a hub (2 children) → in


def test_sitemap_place_loop_skips_provisional(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "prov-place", "name": "P", "type": "place",
             "status": "provisional", "updatedAt": "2026-06-12"},
            {"id": "good-place", "name": "G", "type": "place",
             "summary": _text(80), "updatedAt": "2026-06-12"},
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)

    body = seo.sitemap().body
    assert b"prov-place" not in body
    assert b"good-place" in body
