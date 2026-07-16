"""Tests for SEO data reload and sitemap caching."""

import json
import os
import time
from types import SimpleNamespace

import seo
from launch_evidence import PolicyEvidence


def _write_data(path, entity_id, name):
    payload = {
        "entities": [
            # summary is rich enough to clear the P0-1 index-eligibility gate so the
            # entity reaches the sitemap; this test asserts cache invalidation, not
            # index-worthiness.
            {"id": entity_id, "name": name, "type": "product", "updatedAt": "2026-06-12",
             "status": "published", "verified": True,
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


def test_sitemap_cache_invalidates_with_policy_fingerprint(tmp_path, monkeypatch):
    data_path = tmp_path / "data.json"
    _write_data(data_path, "entity-one", "Entity One")
    monkeypatch.setattr(seo, "DATA_PATH", data_path)
    monkeypatch.setattr(seo, "_data", None)
    monkeypatch.setattr(seo, "_data_mtime_ns", None)
    monkeypatch.setattr(seo, "_by_id_cache", None)
    monkeypatch.setattr(seo, "_sitemap_cache", None)

    evidence = [
        PolicyEvidence("a" * 64, "launch-indexing-policy-v1", "index-policy-v1")
    ]
    calls: list[str] = []
    real_decide_entity = seo.decide_entity

    def recording_decision(entity, current_evidence):
        calls.append(current_evidence.policy_fingerprint)
        return real_decide_entity(entity, current_evidence)

    monkeypatch.setattr(seo, "current_policy_evidence", lambda: evidence[0])
    monkeypatch.setattr(seo, "decide_entity", recording_decision)

    seo.sitemap()
    seo.sitemap()
    assert calls == ["a" * 64]

    evidence[0] = PolicyEvidence(
        "b" * 64, "launch-indexing-policy-v1", "index-policy-v1"
    )
    seo.sitemap()
    assert calls == ["a" * 64, "b" * 64]


# ── Entity sitemap delegates to index_policy ─────────────────────────────────

def _text(n: int) -> str:
    """A descriptive string of exactly ``n`` whitespace-separated words."""
    return " ".join(["từ"] * n)


def _entity(**over):
    e = {"id": "e1", "name": "Test", "type": "attraction", "updatedAt": "2026-06-12",
         "status": "published", "verified": True}
    e.update(over)
    return e


def _reset_seo(monkeypatch, data_path):
    monkeypatch.setattr(seo, "DATA_PATH", data_path)
    for attr in ("_data", "_data_mtime_ns", "_by_id_cache", "_sitemap_cache"):
        monkeypatch.setattr(seo, attr, None)


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


def test_sitemap_does_not_credit_an_image_below_130_words(tmp_path, monkeypatch):
    payload = {
        "entities": [
            _entity(id="ai-only", summary=_text(100), images=["https://ex.com/p.jpg"]),
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)

    assert b"ai-only" not in seo.sitemap().body


def test_sitemap_excludes_thin_entity_pages(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "rich-entity", "name": "Rich", "type": "attraction",
             "status": "published", "verified": True,
             "summary": _text(220), "updatedAt": "2026-06-12"},
            {"id": "thin-entity", "name": "Thin", "type": "attraction",
             "status": "published", "verified": True,
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
            {"id": "hist-1", "name": "H", "type": "history", "status": "published", "verified": True,
             "summary": _text(200), "updatedAt": "2026-06-12"},
            {"id": "ev-1", "name": "E", "type": "event", "status": "published", "verified": True,
             "summary": _text(200), "updatedAt": "2026-06-12"},
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


def test_sitemap_ward_outer_compatibility_and_strict_child_count(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "thin-ward", "name": "TW", "type": "place", "status": "published",
             "verified": True, "summary": _text(20)},
            {"id": "rich-ward", "name": "RW", "type": "place", "status": "published",
             "verified": True, "summary": _text(80)},
            {"id": "hub-ward", "name": "HW", "type": "place", "status": "published",
             "verified": True, "summary": _text(10)},
            {"id": "single-child-ward", "name": "SW", "type": "place", "status": "published",
             "verified": True, "summary": _text(10)},
            {"id": "child-1", "name": "C1", "type": "dish", "status": "published", "verified": True,
             "placeId": "hub-ward", "summary": _text(200)},
            {"id": "child-2", "name": "C2", "type": "dish", "status": "published", "verified": True,
             "placeId": "hub-ward", "summary": _text(200)},
            {"id": "eligible-child", "name": "EC", "type": "dish", "status": "published", "verified": True,
             "placeId": "single-child-ward", "summary": _text(200)},
            {"id": "legacy-child", "name": "LC", "type": "dish",
             "placeId": "single-child-ward", "summary": _text(200)},
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)
    body = seo.sitemap().body
    assert b"/xa-phuong/thin-ward" not in body   # thin summary + no children → out (P1-5)
    assert b"/xa-phuong/rich-ward" in body        # public ward with 60+ Unicode words → in
    assert b"/xa-phuong/hub-ward" in body         # thin summary but a hub (2 eligible children) → in
    assert b"/xa-phuong/single-child-ward" not in body  # ineligible child receives no hub credit


def test_sitemap_ward_child_count_ignores_self_references(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "self-plus-one", "type": "place", "status": "published",
             "verified": True, "placeId": "self-plus-one", "summary": _text(10)},
            {"id": "one-real-child", "type": "dish", "status": "published",
             "verified": True, "placeId": "self-plus-one", "summary": _text(200)},
            {"id": "self-plus-two", "type": "place", "status": "published",
             "verified": True, "placeId": "self-plus-two", "summary": _text(10)},
            {"id": "first-real-child", "type": "dish", "status": "published",
             "verified": True, "placeId": "self-plus-two", "summary": _text(200)},
            {"id": "second-real-child", "type": "dish", "status": "published",
             "verified": True, "placeId": "self-plus-two", "summary": _text(200)},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)

    body = seo.sitemap().body

    assert b"/xa-phuong/self-plus-one" not in body
    assert b"/xa-phuong/self-plus-two" in body


def test_sitemap_place_children_counts_only_publicly_eligible_children():
    data = {
        "entities": [
            {"id": "eligible", "type": "dish", "status": "published", "verified": True,
             "placeId": "ward"},
            {"id": "missing-status", "type": "dish", "verified": True, "placeId": "ward"},
            {"id": "draft", "type": "dish", "status": "draft", "verified": True, "placeId": "ward"},
        ]
    }

    assert seo._sitemap_place_children(data) == {"ward": 1}


def test_sitemap_static_urls_exclude_fixed_itinerary_routes():
    xml = "\n".join(seo._sitemap_static_urls())

    assert f"<loc>{seo.SITE}/lich-trinh</loc>" not in xml
    assert f"<loc>{seo.SITE}/tao-lich-trinh</loc>" not in xml


def test_sitemap_place_children_skips_malformed_id_and_place_id_values():
    data = {
        "entities": [
            {"id": "valid-child", "type": "dish", "status": "published",
             "verified": True, "placeId": "ward"},
            {"type": "dish", "status": "published", "verified": True,
             "placeId": "ward"},
            {"id": 7, "type": "dish", "status": "published", "verified": True,
             "placeId": "ward"},
            {"id": "blank-child", "type": "dish", "status": "published", "verified": True,
             "placeId": "  "},
            {"id": "  ", "type": "dish", "status": "published", "verified": True,
             "placeId": "ward"},
            {"id": "", "type": "dish", "status": "published", "verified": True,
             "placeId": "ward"},
            {"id": "non-string-place", "type": "dish", "status": "published", "verified": True,
             "placeId": 7},
            {"id": "empty-place", "type": "dish", "status": "published", "verified": True,
             "placeId": ""},
            {"id": "self", "type": "dish", "status": "published", "verified": True,
             "placeId": "self"},
        ]
    }

    assert seo._sitemap_place_children(data) == {"ward": 1}


def test_sitemap_place_urls_skip_non_string_or_blank_ward_ids(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "valid-ward", "name": "Valid", "type": "place",
             "status": "published", "verified": True, "summary": _text(80)},
            {"id": 7, "name": "Numeric", "type": "place",
             "status": "published", "verified": True, "summary": _text(80)},
            {"id": "  ", "name": "Blank", "type": "place",
             "status": "published", "verified": True, "summary": _text(80)},
            {"id": "", "name": "Empty", "type": "place",
             "status": "published", "verified": True, "summary": _text(80)},
            {"name": "Missing", "type": "place",
             "status": "published", "verified": True, "summary": _text(80)},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)

    body = seo.sitemap().body

    assert b"/xa-phuong/valid-ward" in body
    assert b"/xa-phuong/7" not in body
    assert b"/xa-phuong/%20%20" not in body


def test_sitemap_place_loop_skips_provisional(tmp_path, monkeypatch):
    payload = {
        "entities": [
            {"id": "prov-place", "name": "P", "type": "place",
             "status": "provisional", "verified": True, "updatedAt": "2026-06-12"},
            {"id": "good-place", "name": "G", "type": "place",
             "status": "published", "verified": True,
             "summary": _text(80), "updatedAt": "2026-06-12"},
            {"id": "missing-status", "name": "M", "type": "place",
             "verified": True, "summary": _text(80)},
        ],
        "relationships": [], "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)

    body = seo.sitemap().body
    assert b"prov-place" not in body
    assert b"good-place" in body
    assert b"missing-status" not in body


def test_sitemap_ward_delegates_to_index_policy_with_request_evidence(
    tmp_path, monkeypatch
):
    payload = {
        "entities": [
            {"id": "policy-ward", "type": "place", "status": "published",
             "verified": True, "summary": _text(60)},
        ],
        "relationships": [],
        "itineraries": [],
    }
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _reset_seo(monkeypatch, data_path)
    current_evidence = PolicyEvidence(
        "c" * 64, "launch-indexing-policy-v1", "index-policy-v1"
    )
    calls = []

    def recording_decision(ward, *, public_child_count, evidence):
        calls.append((ward["id"], public_child_count, evidence))
        return SimpleNamespace(indexable=True)

    monkeypatch.setattr(seo, "current_policy_evidence", lambda: current_evidence)
    monkeypatch.setattr(seo, "decide_ward", recording_decision)
    monkeypatch.setattr(
        seo,
        "_is_listing_visible",
        lambda entity: (_ for _ in ()).throw(
            AssertionError("ward sitemap must not use legacy visibility authority")
        ),
    )

    body = seo.sitemap().body

    assert b"/xa-phuong/policy-ward" in body
    assert calls == [("policy-ward", 0, current_evidence)]
