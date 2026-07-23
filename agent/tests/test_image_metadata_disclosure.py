from __future__ import annotations

import asyncio
import inspect

import pytest
from fastapi import Request, Response

import public_api
import seo
import social
from ai_disclosure import load_ai_disclosure
from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence
from route_manifest import EXPECTED_REVISION as ROUTE_MANIFEST_REVISION
from sitemap_render import render_media_sitemap
from route_manifest import load_route_manifest
from sitemap_snapshot import SitemapSnapshot


DISCLOSURE = load_ai_disclosure()
RAW_MEDIA_KEYS = {"image", "images", "image_url", "image_urls"}


def _entity(**overrides):
    entity = {
        "id": "ai-place",
        "name": "Điểm đến AI",
        "type": "attraction",
        "status": "published",
        "verified": True,
        "summary": " ".join(["word"] * 130),
        "images": ["https://cdn.example/ai.webp"],
        "attributes": {},
    }
    entity.update(overrides)
    return entity


EVIDENCE = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision=ROUTE_MANIFEST_REVISION,
    backend_policy_revision=INDEX_POLICY_REVISION,
)


def test_entity_jsonld_uses_classified_ai_descriptor_and_omits_raw_or_forbidden_metadata():
    entity = _entity(
        images=[
            "/img/entities/ai.webp",
            {"url": "https://evil.example/raw.webp", "photographer": "Injected"},
            "javascript:alert(1)",
        ],
        photographer="Injected",
        exif={"GPSLatitude": 10},
        capture_location="Invented",
    )

    ld = seo.build_entity_jsonld(entity, {entity["id"]: entity})

    image = ld["image"][0]
    assert image["@type"] == "ImageObject"
    expected_url = f"{seo.SITE}/img/entities/ai.webp"
    assert image["url"] == expected_url
    assert image["contentUrl"] == expected_url
    assert image["caption"] == DISCLOSURE.entity_ai.full_disclosure
    assert image["description"].endswith(DISCLOSURE.entity_ai.full_disclosure)
    for forbidden in ("photographer", "exifData", "captureLocation", "contentLocation"):
        assert forbidden not in image
    assert "evil.example" not in str(ld)
    assert "Injected" not in str(ld)


def test_entity_jsonld_absolutizes_legacy_local_image_descriptor_metadata():
    entity = _entity(images=["/img/entities/local.webp"])

    ld = seo.build_entity_jsonld(entity, {entity["id"]: entity})

    image = ld["image"][0]
    expected_url = "https://vinhlong360.vn/img/entities/local.webp"
    assert image["url"] == expected_url
    assert image["contentUrl"] == expected_url
    assert image["caption"] == DISCLOSURE.entity_ai.full_disclosure


def test_entity_jsonld_omits_placeholder_or_missing_images():
    for images in ([], [None, {"url": "https://evil.example/raw.webp"}]):
        ld = seo.build_entity_jsonld(_entity(images=images), {})
        assert "image" not in ld


def test_entity_jsonld_emits_structured_ai_descriptor_without_legacy_images():
    descriptor = {
        "url": "https://cdn.example/structured.webp",
        "alt": "Điểm đến AI — ảnh minh họa 1",
        "source_class": "ai-generated",
        "source_kind": "entity-editorial",
        "disclosure_key": "entity-ai",
        "short_label": DISCLOSURE.entity_ai.short_label,
        "full_disclosure": DISCLOSURE.entity_ai.full_disclosure,
        "credit": None,
        "width": None,
        "height": None,
    }
    local_descriptor = {**descriptor, "url": "/media/structured-local.webp"}
    entities = [
        (
            _entity(images=[], image_descriptor=local_descriptor),
            f"{seo.SITE}{local_descriptor['url']}",
        ),
        (_entity(image_descriptors=[descriptor]), descriptor["url"]),
    ]
    entities[1][0].pop("images")
    for entity, expected_url in entities:
        ld = seo.build_entity_jsonld(entity, {})
        image = ld["image"][0]
        assert image["@type"] == "ImageObject"
        assert image["contentUrl"] == expected_url
        assert image["caption"] == DISCLOSURE.entity_ai.full_disclosure
        assert image["description"] == (
            f"{descriptor['alt']} — {DISCLOSURE.entity_ai.full_disclosure}"
        )


def test_media_sitemap_caption_matches_classified_descriptor_copy():
    entity = _entity(images=["/img/entities/ai.webp"])
    xml = render_media_sitemap(
        SitemapSnapshot(entities=(entity,), relationships=(), wards=()),
        load_route_manifest(),
        EVIDENCE,
        DISCLOSURE,
    )

    assert DISCLOSURE.entity_ai.full_disclosure.encode() in xml
    assert b"/img/entities/ai.webp" in xml


def test_public_entity_projection_removes_raw_media_and_keeps_only_ai_descriptors():
    entity = _entity(
        images=[
            "/img/entities/editorial.webp",
            "https://cdn.example/unknown.webp",
        ],
    )

    projector = getattr(public_api, "_project_public_entity_media", None)
    assert callable(projector)
    projected = projector(entity)

    assert "images" not in projected
    assert "image" not in projected
    assert "image_urls" not in projected
    assert [item["source_class"] for item in projected["image_descriptors"]] == [
        "ai-generated",
    ]


def test_public_entity_projection_suppresses_explicit_ugc_without_legacy_fallback():
    entity = _entity(
        images=["/img/entities/fallback.webp"],
        image_descriptors=[{
            "url": "/media/review.webp",
            "alt": "Ảnh đánh giá",
            "source_class": "user-uploaded",
            "source_kind": "review-ugc",
            "disclosure_key": "ugc-photo",
            "short_label": DISCLOSURE.ugc_photo.short_label,
            "full_disclosure": DISCLOSURE.ugc_photo.full_disclosure,
            "credit": "Lan",
            "width": None,
            "height": None,
        }],
    )

    projector = getattr(public_api, "_project_public_entity_media", None)
    assert callable(projector)
    projected = projector(entity)

    assert projected["image_descriptors"] == []
    assert "images" not in projected


def test_public_gallery_handler_does_not_append_review_rows():
    source = inspect.getsource(public_api.get_entity_gallery)

    assert "_append_review_gallery_images" not in source


def _assert_no_raw_media(value):
    if isinstance(value, dict):
        assert RAW_MEDIA_KEYS.isdisjoint(value)
        for nested in value.values():
            _assert_no_raw_media(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_raw_media(nested)


def test_public_post_serializer_suppresses_stored_media_without_mutating_storage_row():
    row = {
        "id": "post-1",
        "user_id": "user-1",
        "content": "Bài viết công khai",
        "images": '["/media/post.webp"]',
        "repost_snapshot": {
            "id": "post-0",
            "content": "Bài gốc",
            "images": ["/media/repost.webp"],
        },
    }

    projected = social._format_post(row)

    _assert_no_raw_media(projected)
    assert row["images"] == '["/media/post.webp"]'
    assert row["repost_snapshot"]["images"] == ["/media/repost.webp"]


def test_public_review_serializer_suppresses_stored_media_without_mutating_storage_row():
    row = {
        "id": "review-1",
        "user_id": "user-1",
        "content": "Đánh giá công khai",
        "images": '["/media/review.webp"]',
    }

    projected = public_api._shape_review_row(row)

    _assert_no_raw_media(projected)
    assert row["images"] == '["/media/review.webp"]'


@pytest.mark.parametrize(
    "builder_name",
    [
        "get_featured_entities",
        "_build_homepage_payload",
        "_map_search_shape",
        "entities_trending",
        "compare_entities",
        "_shape_popular_entity",
        "entity_search",
        "_entity_card_shape",
        "_candidate_card",
        "search",
        "place_overview",
        "get_collection_by_slug",
    ],
)
def test_every_public_entity_discovery_builder_uses_descriptor_only_projection(builder_name):
    builder = getattr(public_api, builder_name)

    assert "_project_public_entity_media" in inspect.getsource(builder)


@pytest.mark.parametrize(
    ("builder_name", "args"),
    [
        ("_map_search_shape", ([10.0, 106.0],)),
        ("_shape_popular_entity", ()),
        ("_entity_card_shape", ()),
        ("_candidate_card", (["Phù hợp"],)),
    ],
)
def test_public_entity_shape_helpers_never_emit_raw_media(builder_name, args):
    entity = _entity(images=["/img/entities/editorial.webp"])
    projected = getattr(public_api, builder_name)(entity, *args)

    _assert_no_raw_media(projected)
    assert projected["image_descriptors"][0]["source_class"] == "ai-generated"


def test_unified_search_projects_entity_media_without_mutating_rank_input(monkeypatch):
    entity = _entity(images=["/img/entities/search.webp"])
    monkeypatch.setattr(public_api.db, "search_entities", lambda **_kwargs: [entity])
    monkeypatch.setattr(public_api.db, "count_entities_filtered", lambda **_kwargs: 1)
    monkeypatch.setattr(public_api, "_enrich_place", lambda _items: None)
    monkeypatch.setattr(public_api, "_search_posts_for_contract", lambda *_args: ([], 0))
    monkeypatch.setattr(public_api, "_search_users_for_contract", lambda *_args: ([], 0))
    monkeypatch.setattr(public_api, "_log_search_query", lambda *_args: None)
    monkeypatch.setattr("ratelimit.check_rate", lambda *_args: None)
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/api/search",
        "headers": [],
        "query_string": b"q=ai",
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
        "scheme": "http",
    })

    result = asyncio.run(public_api.search(
        request,
        Response(),
        q="ai",
        type=None,
        area=None,
        limit=20,
        user=None,
    ))

    _assert_no_raw_media(result["entities"])
    assert result["entities"][0]["image_descriptors"][0]["source_class"] == "ai-generated"
    assert entity["images"] == ["/img/entities/search.webp"]


def test_place_overview_projects_grouped_entities_without_mutating_rows(monkeypatch):
    child = _entity(images=["/img/entities/ward-child.webp"])
    place = _entity(id="ward", type="place", images=[])
    monkeypatch.setattr(public_api, "_get_public_entity", lambda _entity_id: place)
    monkeypatch.setattr(public_api, "_public_entities_by_place", lambda _place_id: [child])
    monkeypatch.setattr(public_api, "_public_facilities_by_place", lambda _place_id: [])

    result = asyncio.run(public_api.place_overview("ward", Response()))

    _assert_no_raw_media(result["tourism"])
    assert result["tourism"][0]["image_descriptors"][0]["source_class"] == "ai-generated"
    assert child["images"] == ["/img/entities/ward-child.webp"]


@pytest.mark.parametrize(
    "entity",
    [
        None,
        _entity(images=[]),
        _entity(images=["https://cdn.example/unknown.webp"]),
        _entity(
            images=[],
            image_descriptor={
                "url": None,
                "alt": "Điểm đến AI — chưa có ảnh riêng",
                "source_class": "placeholder",
                "source_kind": "generated-placeholder",
                "disclosure_key": "entity-placeholder",
                "short_label": DISCLOSURE.placeholder.short_label,
                "full_disclosure": DISCLOSURE.placeholder.full_disclosure,
                "credit": None,
                "width": None,
                "height": None,
            },
        ),
    ],
)
def test_og_meta_omits_image_keys_without_a_renderable_ai_descriptor(entity):
    meta = seo.build_og_meta(entity)

    assert "og:image" not in meta
    assert "twitter:image" not in meta


def test_og_meta_keeps_only_a_classified_ai_descriptor_url():
    meta = seo.build_og_meta(_entity(images=["/img/entities/og.webp"]))

    assert meta["og:image"] == f"{seo.SITE}/img/entities/og.webp"
    assert meta["twitter:image"] == meta["og:image"]
