from __future__ import annotations

import seo
from ai_disclosure import load_ai_disclosure
from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence
from route_manifest import EXPECTED_REVISION as ROUTE_MANIFEST_REVISION
from sitemap_render import render_media_sitemap
from route_manifest import load_route_manifest
from sitemap_snapshot import SitemapSnapshot


DISCLOSURE = load_ai_disclosure()


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
            "https://cdn.example/ai.webp",
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
    assert image["url"] == "https://cdn.example/ai.webp"
    assert image["contentUrl"] == "https://cdn.example/ai.webp"
    assert image["caption"] == DISCLOSURE.entity_ai.full_disclosure
    assert image["description"].endswith(DISCLOSURE.entity_ai.full_disclosure)
    for forbidden in ("photographer", "exifData", "captureLocation", "contentLocation"):
        assert forbidden not in image
    assert "evil.example" not in str(ld)
    assert "Injected" not in str(ld)


def test_entity_jsonld_omits_placeholder_or_missing_images():
    for images in ([], [None, {"url": "https://evil.example/raw.webp"}]):
        ld = seo.build_entity_jsonld(_entity(images=images), {})
        assert "image" not in ld


def test_media_sitemap_caption_matches_classified_descriptor_copy():
    entity = _entity(images=["/media/ai.webp"])
    xml = render_media_sitemap(
        SitemapSnapshot(entities=(entity,), relationships=(), wards=()),
        load_route_manifest(),
        EVIDENCE,
        DISCLOSURE,
    )

    assert DISCLOSURE.entity_ai.full_disclosure.encode() in xml
    assert b"/media/ai.webp" in xml
