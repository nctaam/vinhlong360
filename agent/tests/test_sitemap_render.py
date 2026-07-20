from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from xml.etree import ElementTree

import pytest


AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence  # noqa: E402
from ai_disclosure import load_ai_disclosure  # noqa: E402
from image_descriptor import ImageDescriptor  # noqa: E402
from route_manifest import extract_static_sitemap_paths, load_route_manifest  # noqa: E402
import sitemap_render  # noqa: E402
from sitemap_render import (  # noqa: E402
    canonical_detail_url,
    public_ward_child_counts,
    render_media_sitemap,
    render_main_sitemap,
    resolve_sitemap_image_url,
    serialize_image_urlset,
)
from sitemap_snapshot import SitemapSnapshot  # noqa: E402


EVIDENCE = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)
DISCLOSURE = load_ai_disclosure()
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NAMESPACE = "http://www.google.com/schemas/sitemap-image/1.1"
MEDIA_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "sitemap"
    / "expected-sitemap-media.xml"
)


def _words(count: int, word: str = "word") -> str:
    return " ".join([word] * count)


def _entity(entity_id: object = "entity", **overrides: object) -> dict[str, object]:
    entity: dict[str, object] = {
        "id": entity_id,
        "type": "attraction",
        "status": "published",
        "verified": True,
        "summary": _words(130),
    }
    entity.update(overrides)
    return entity


def _ward(ward_id: object = "ward", **overrides: object) -> dict[str, object]:
    ward: dict[str, object] = {
        "id": ward_id,
        "type": "place",
        "status": "published",
        "verified": True,
        "summary": _words(59, "phuong"),
    }
    ward.update(overrides)
    return ward


def _snapshot(*entities: object, relationships: tuple[dict, ...] = ()) -> SitemapSnapshot:
    mappings = tuple(entity for entity in entities if isinstance(entity, dict))
    return SitemapSnapshot(
        entities=tuple(entities),
        relationships=relationships,
        wards=tuple(entity for entity in mappings if entity.get("type") == "place"),
    )


def _locs(xml: bytes) -> list[str]:
    root = ElementTree.fromstring(xml)
    assert root.tag == f"{{{SITEMAP_NAMESPACE}}}urlset"
    assert all([child.tag for child in node] == [f"{{{SITEMAP_NAMESPACE}}}loc"] for node in root)
    return [
        node.findtext(f"{{{SITEMAP_NAMESPACE}}}loc", default="")
        for node in root
    ]


def _media_entries(xml: bytes) -> list[tuple[str, list[tuple[str, str]]]]:
    root = ElementTree.fromstring(xml)
    assert root.tag == f"{{{SITEMAP_NAMESPACE}}}urlset"
    entries: list[tuple[str, list[tuple[str, str]]]] = []
    for page in root:
        assert page.tag == f"{{{SITEMAP_NAMESPACE}}}url"
        assert [child.tag for child in page][:1] == [f"{{{SITEMAP_NAMESPACE}}}loc"]
        images: list[tuple[str, str]] = []
        for image in list(page)[1:]:
            assert image.tag == f"{{{IMAGE_NAMESPACE}}}image"
            assert [child.tag for child in image] == [
                f"{{{IMAGE_NAMESPACE}}}loc",
                f"{{{IMAGE_NAMESPACE}}}caption",
            ]
            images.append(
                (
                    image.findtext(f"{{{IMAGE_NAMESPACE}}}loc", default=""),
                    image.findtext(f"{{{IMAGE_NAMESPACE}}}caption", default=""),
                )
            )
        entries.append(
            (page.findtext(f"{{{SITEMAP_NAMESPACE}}}loc", default=""), images)
        )
    return entries


def test_main_sitemap_is_absolute_sorted_deduplicated_and_permutation_stable():
    manifest = load_route_manifest()
    rich = _entity("z-rich")
    duplicate = dict(rich)
    ward = _ward("a-ward")
    child_a = _entity("child-a", placeId="a-ward")
    child_b = _entity("child-b", placeId="a-ward")
    first = _snapshot(rich, duplicate, ward, child_b, child_a)
    second = _snapshot(child_a, ward, rich, child_b, duplicate)

    first_xml = render_main_sitemap(first, manifest, EVIDENCE)
    second_xml = render_main_sitemap(second, manifest, EVIDENCE)
    locs = _locs(first_xml)

    assert first_xml == second_xml
    assert first_xml.startswith(b"<?xml")
    assert locs == sorted(set(locs))
    assert all(loc.startswith(manifest.data["canonical_origin"]) for loc in locs)
    assert f"{manifest.data['canonical_origin']}/dia-diem/z-rich" in locs
    assert f"{manifest.data['canonical_origin']}/xa-phuong/a-ward" in locs
    assert locs.count(f"{manifest.data['canonical_origin']}/dia-diem/z-rich") == 1


def test_main_sitemap_uses_manifest_static_authority_and_fixed_negative_routes():
    manifest = load_route_manifest()

    locs = _locs(render_main_sitemap(_snapshot(), manifest, EVIDENCE))

    assert locs == [
        f"{manifest.data['canonical_origin']}{path}"
        for path in extract_static_sitemap_paths(manifest)
    ]
    assert not any("/lich-trinh/" in loc for loc in locs)
    assert not any("/chia-se/" in loc for loc in locs)
    assert f"{manifest.data['canonical_origin']}/tim-kiem" not in locs


def test_main_sitemap_delegates_non_places_and_wards_to_index_policy():
    manifest = load_route_manifest()
    thin = _entity("thin", summary=_words(129))
    draft = _entity("draft", status="draft")
    weak_ward = _ward("weak-ward")
    strong_ward = _ward("strong-ward")
    children = (
        _entity("one", placeId="strong-ward"),
        _entity("two", placeId="strong-ward"),
    )

    locs = _locs(
        render_main_sitemap(
            _snapshot(thin, draft, weak_ward, strong_ward, *children),
            manifest,
            EVIDENCE,
        )
    )

    assert not any(loc.endswith("/dia-diem/thin") for loc in locs)
    assert not any(loc.endswith("/dia-diem/draft") for loc in locs)
    assert not any(loc.endswith("/xa-phuong/weak-ward") for loc in locs)
    assert any(loc.endswith("/xa-phuong/strong-ward") for loc in locs)


@pytest.mark.parametrize("invalid_evidence", [None, object()])
def test_invalid_or_missing_evidence_aborts_before_rendering_xml(invalid_evidence):
    with pytest.raises(TypeError, match="evidence must be PolicyEvidence"):
        render_main_sitemap(_snapshot(), load_route_manifest(), invalid_evidence)


def test_policy_contract_exceptions_abort_render(monkeypatch):
    def fail_policy(_entity, _evidence):
        raise ValueError("policy contract failure")

    monkeypatch.setattr(sitemap_render, "decide_entity", fail_policy)

    with pytest.raises(ValueError, match="policy contract failure"):
        render_main_sitemap(
            _snapshot(_entity("rich")),
            load_route_manifest(),
            EVIDENCE,
        )


def test_shared_ward_child_counts_are_exact_unique_and_relationship_independent():
    ward = "ward"
    eligible = _entity("eligible", placeId=ward)
    duplicate = dict(eligible)
    entities: tuple[object, ...] = (
        eligible,
        duplicate,
        _entity("second", placeId=ward),
        _entity("draft", placeId=ward, status="draft"),
        _entity("other", placeId="other-ward"),
        _entity("ward", placeId=ward),
        _ward("nested-place", placeId=ward),
        _entity("blank-id", placeId=" "),
        _entity(" ", placeId=ward),
        _entity(7, placeId=ward),
        _entity("numeric-place", placeId=7),
        object(),
    )

    snapshot = _snapshot(
        _ward(ward),
        *entities,
        relationships=(
            {"source_id": "ghost", "target_id": ward, "type": "located_in"},
        ),
    )
    counts = public_ward_child_counts(snapshot)

    assert counts == {ward: 2, "other-ward": 1}
    locs = _locs(render_main_sitemap(snapshot, load_route_manifest(), EVIDENCE))
    assert any(loc.endswith(f"/xa-phuong/{ward}") for loc in locs)


@pytest.mark.parametrize(
    "bad_id",
    [None, "", "   ", " leading", "trailing ", "control\nid", 0, False, object()],
)
def test_canonical_detail_url_skips_malformed_ids(bad_id: object):
    assert canonical_detail_url(
        _entity(bad_id), "https://vinhlong360.vn"
    ) is None


def test_canonical_detail_url_encodes_exactly_one_segment_and_xml_escapes():
    origin = "https://vinhlong360.vn"
    encoded = canonical_detail_url(_entity("a/b ?#%&<"), origin)

    assert encoded == f"{origin}/dia-diem/a%2Fb%20%3F%23%25%26%3C"
    xml = render_main_sitemap(
        _snapshot(_entity("a&b")), load_route_manifest(), EVIDENCE
    )
    assert b"a%26b" in xml
    assert any(loc.endswith("/dia-diem/a%26b") for loc in _locs(xml))


def test_main_sitemap_sorts_before_enforcing_50000_url_limit():
    manifest = load_route_manifest()
    entities = tuple(_entity(f"entity-{index:05d}") for index in range(50_010, -1, -1))

    locs = _locs(render_main_sitemap(_snapshot(*entities), manifest, EVIDENCE))

    assert len(locs) == 50_000
    assert locs == sorted(locs)
    assert any(loc.endswith("/dia-diem/entity-00000") for loc in locs)
    assert not any(loc.endswith("/dia-diem/entity-50010") for loc in locs)


def test_resolve_sitemap_image_url_prefixes_local_paths_and_preserves_https():
    manifest = load_route_manifest()
    origin = manifest.data["canonical_origin"]

    assert resolve_sitemap_image_url("/media/ảnh.webp?x=1&y=2", manifest) == (
        f"{origin}/media/ảnh.webp?x=1&y=2"
    )
    assert resolve_sitemap_image_url(
        "https://cdn.example/ảnh.webp?x=1&y=2", manifest
    ) == "https://cdn.example/ảnh.webp?x=1&y=2"
    assert resolve_sitemap_image_url("http://cdn.example/image.webp", manifest) is None


def test_media_serializer_matches_utf8_fixture_with_two_disclosed_images():
    manifest = load_route_manifest()
    entity = _entity(
        "two-images",
        name="Two images",
        images=[
            "/media/z-local.webp",
            "https://cdn.example.test/media/a-absolute.webp",
            "http://cdn.example.test/media/rejected.webp",
        ],
    )

    xml = render_media_sitemap(
        _snapshot(entity), manifest, EVIDENCE, DISCLOSURE
    )

    # Normalize checkout line endings so the byte fixture remains portable on Windows.
    expected = MEDIA_FIXTURE.read_bytes().replace(b"\r\n", b"\n").rstrip(b"\r\n")
    assert xml.rstrip(b"\r\n") == expected
    assert xml.startswith(b"<?xml version='1.0' encoding='utf-8'?>\n")
    assert not xml.endswith(b"\n")
    assert b"rejected.webp" not in xml


def test_media_sitemap_uses_structured_entity_descriptor_without_legacy_images():
    descriptor = ImageDescriptor(
        url="/media/structured.webp",
        alt="Structured — ảnh minh họa",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=DISCLOSURE.entity_ai.short_label,
        full_disclosure=DISCLOSURE.entity_ai.full_disclosure,
        credit=None,
        width=None,
        height=None,
    )
    entity = _entity(
        "structured-only",
        name="Structured only",
        images=[],
        image_descriptors=[asdict(descriptor)],
    )
    xml = render_media_sitemap(
        _snapshot(entity), load_route_manifest(), EVIDENCE, DISCLOSURE
    )

    assert b"/media/structured.webp" in xml
    assert DISCLOSURE.entity_ai.full_disclosure.encode() in xml


def test_media_sitemap_is_sorted_deduplicated_and_permutation_stable():
    manifest = load_route_manifest()
    first_entity = _entity(
        "z-entity",
        name="Z entity",
        images=[
            "https://cdn.example/z.webp",
            "/media/a.webp",
            "https://cdn.example/z.webp",
        ],
    )
    duplicate = dict(first_entity)
    duplicate["images"] = list(reversed(first_entity["images"]))
    second_entity = _entity(
        "a-entity",
        name="A entity",
        images=("/media/ứ.webp?x=1&y=2",),
    )

    first_xml = render_media_sitemap(
        _snapshot(first_entity, duplicate, second_entity),
        manifest,
        EVIDENCE,
        DISCLOSURE,
    )
    second_xml = render_media_sitemap(
        _snapshot(second_entity, duplicate, first_entity),
        manifest,
        EVIDENCE,
        DISCLOSURE,
    )
    entries = _media_entries(first_xml)

    assert first_xml == second_xml
    assert [page for page, _images in entries] == sorted(page for page, _images in entries)
    assert [loc for loc, _caption in entries[1][1]] == sorted(
        loc for loc, _caption in entries[1][1]
    )
    assert len(entries[1][1]) == 2
    assert all(
        caption == DISCLOSURE.entity_ai.full_disclosure
        for _page, images in entries
        for _loc, caption in images
    )
    assert b"&amp;" in first_xml
    assert "ứ".encode() in first_xml


def test_media_sitemap_has_exact_main_policy_parity_including_ward_paths():
    manifest = load_route_manifest()
    rich = _entity("rich", name="Rich", images=["/rich.webp"])
    thin = _entity("thin", name="Thin", summary=_words(129), images=["/thin.webp"])
    draft = _entity("draft", name="Draft", status="draft", images=["/draft.webp"])
    unverified = _entity(
        "unverified", name="Unverified", verified=False, images=["/unverified.webp"]
    )
    private = _entity(
        "private", name="Private", is_private=True, images=["/private.webp"]
    )
    ward = _ward("ward", name="Ward", images=["/ward.webp"])
    child_a = _entity("child-a", name="Child A", placeId="ward")
    child_b = _entity("child-b", name="Child B", placeId="ward")

    entries = _media_entries(
        render_media_sitemap(
            _snapshot(
                rich,
                thin,
                draft,
                unverified,
                private,
                ward,
                child_a,
                child_b,
                object(),
            ),
            manifest,
            EVIDENCE,
            DISCLOSURE,
        )
    )
    pages = [page for page, _images in entries]

    assert pages == [
        f"{manifest.data['canonical_origin']}/dia-diem/rich",
        f"{manifest.data['canonical_origin']}/xa-phuong/ward",
    ]


def test_media_sitemap_uses_only_entity_editorial_images_and_minimal_tags():
    entity = _entity(
        "rich",
        name="Rich",
        images=["/editorial.webp"],
        placeholder="PLACEHOLDER-SENTINEL",
        posts=[{"images": ["POST-SENTINEL"]}],
        reviews=[{"images": ["REVIEW-SENTINEL"]}],
        image_title="TITLE-SENTINEL",
        image_credit="CREDIT-SENTINEL",
        image_license="LICENSE-SENTINEL",
        image_geo="GEO-SENTINEL",
        summary="SUMMARY-SENTINEL " + _words(130),
    )

    xml = render_media_sitemap(
        _snapshot(entity), load_route_manifest(), EVIDENCE, DISCLOSURE
    )

    assert b"editorial.webp" in xml
    for forbidden in (
        b"PLACEHOLDER-SENTINEL",
        b"POST-SENTINEL",
        b"REVIEW-SENTINEL",
        b"TITLE-SENTINEL",
        b"CREDIT-SENTINEL",
        b"LICENSE-SENTINEL",
        b"GEO-SENTINEL",
        b"SUMMARY-SENTINEL",
        b"image:title",
        b"image:license",
        b"image:geo_location",
    ):
        assert forbidden not in xml


@pytest.mark.parametrize(
    "descriptor",
    [
        ImageDescriptor(
            url="/ugc.jpg",
            alt="UGC",
            source_class="user-uploaded",
            source_kind="review-ugc",
            disclosure_key="ugc-photo",
            short_label=DISCLOSURE.ugc_photo.short_label,
            full_disclosure=DISCLOSURE.ugc_photo.full_disclosure,
            credit="Lan",
            width=None,
            height=None,
        ),
        ImageDescriptor(
            url="/contradictory.jpg",
            alt="Contradictory",
            source_class="ai-generated",
            source_kind="review-ugc",
            disclosure_key="ugc-photo",
            short_label=DISCLOSURE.ugc_photo.short_label,
            full_disclosure=DISCLOSURE.ugc_photo.full_disclosure,
            credit="Lan",
            width=None,
            height=None,
        ),
        object(),
    ],
)
def test_media_sitemap_requires_exact_ai_editorial_descriptor_before_page_node(
    monkeypatch, descriptor: object
):
    entity = _entity("ugc-only", images=["/ignored.webp"])
    monkeypatch.setattr(
        sitemap_render,
        "describe_entity_images",
        lambda _entity, disclosure: (descriptor,),
    )

    entries = _media_entries(
        render_media_sitemap(
            _snapshot(entity), load_route_manifest(), EVIDENCE, DISCLOSURE
        )
    )

    assert entries == []


@pytest.mark.parametrize(
    "descriptor",
    [
        ImageDescriptor(
            url="/ugc.jpg",
            alt="UGC",
            source_class="user-uploaded",
            source_kind="review-ugc",
            disclosure_key="ugc-photo",
            short_label=DISCLOSURE.ugc_photo.short_label,
            full_disclosure=DISCLOSURE.ugc_photo.full_disclosure,
            credit="Lan",
            width=None,
            height=None,
        ),
        ImageDescriptor(
            url="/contradictory.jpg",
            alt="Contradictory",
            source_class="ai-generated",
            source_kind="review-ugc",
            disclosure_key="ugc-photo",
            short_label=DISCLOSURE.ugc_photo.short_label,
            full_disclosure=DISCLOSURE.ugc_photo.full_disclosure,
            credit="Lan",
            width=None,
            height=None,
        ),
    ],
)
def test_serialize_image_urlset_omits_pages_without_editorial_descriptors(
    descriptor: ImageDescriptor,
):
    xml = serialize_image_urlset(
        {"https://vinhlong360.vn/dia-diem/ugc-only": {descriptor.url or "": descriptor}}
    )

    assert _media_entries(xml) == []


def test_serialize_image_urlset_keeps_page_and_only_editorial_image_for_mixed_group():
    editorial = ImageDescriptor(
        url="/editorial.jpg",
        alt="Editorial",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=DISCLOSURE.entity_ai.short_label,
        full_disclosure=DISCLOSURE.entity_ai.full_disclosure,
        credit=None,
        width=None,
        height=None,
    )
    ugc = ImageDescriptor(
        url="/ugc.jpg",
        alt="UGC",
        source_class="user-uploaded",
        source_kind="review-ugc",
        disclosure_key="ugc-photo",
        short_label=DISCLOSURE.ugc_photo.short_label,
        full_disclosure=DISCLOSURE.ugc_photo.full_disclosure,
        credit="Lan",
        width=None,
        height=None,
    )

    entries = _media_entries(
        serialize_image_urlset(
            {
                "https://vinhlong360.vn/dia-diem/mixed": {
                    editorial.url or "": editorial,
                    ugc.url or "": ugc,
                }
            }
        )
    )

    assert entries == [
        (
            "https://vinhlong360.vn/dia-diem/mixed",
            [("/editorial.jpg", DISCLOSURE.entity_ai.full_disclosure)],
        )
    ]


@pytest.mark.parametrize(
    ("invalid_evidence", "invalid_disclosure", "message"),
    [
        (None, DISCLOSURE, "evidence must be PolicyEvidence"),
        (EVIDENCE, None, "disclosure must be LoadedAiDisclosure"),
        (object(), DISCLOSURE, "evidence must be PolicyEvidence"),
        (EVIDENCE, object(), "disclosure must be LoadedAiDisclosure"),
    ],
)
def test_media_sitemap_validates_policy_and_disclosure_before_empty_snapshot_access(
    invalid_evidence: object,
    invalid_disclosure: object,
    message: str,
):
    class ExplodingSnapshot:
        @property
        def entities(self):
            raise AssertionError("invalid contracts must abort before snapshot access")

    with pytest.raises(TypeError, match=message):
        render_media_sitemap(
            ExplodingSnapshot(),
            load_route_manifest(),
            invalid_evidence,
            invalid_disclosure,
        )


def test_media_policy_contract_exceptions_abort_render(monkeypatch):
    def fail_policy(_entity, _evidence):
        raise ValueError("policy contract failure")

    monkeypatch.setattr(sitemap_render, "decide_entity", fail_policy)

    with pytest.raises(ValueError, match="policy contract failure"):
        render_media_sitemap(
            _snapshot(_entity("rich", name="Rich", images=["/rich.webp"])),
            load_route_manifest(),
            EVIDENCE,
            DISCLOSURE,
        )


def test_media_sitemap_empty_output_is_valid_and_contains_no_static_pages():
    xml = render_media_sitemap(
        _snapshot(), load_route_manifest(), EVIDENCE, DISCLOSURE
    )

    assert _media_entries(xml) == []
    assert xml == serialize_image_urlset({})


def test_media_sitemap_sorts_pages_before_enforcing_shared_limit(monkeypatch):
    monkeypatch.setattr(sitemap_render, "MAX_SITEMAP_URLS", 2)
    entities = tuple(
        _entity(entity_id, name=entity_id, images=[f"/{entity_id}.webp"])
        for entity_id in ("z", "a", "m")
    )

    pages = [
        page
        for page, _images in _media_entries(
            render_media_sitemap(
                _snapshot(*entities),
                load_route_manifest(),
                EVIDENCE,
                DISCLOSURE,
            )
        )
    ]

    assert pages == [
        "https://vinhlong360.vn/dia-diem/a",
        "https://vinhlong360.vn/dia-diem/m",
    ]


def test_batch_revision_is_length_prefixed_and_changes_for_each_input():
    compute = getattr(sitemap_render, "compute_batch_revision", None)
    assert callable(compute), "compute_batch_revision is not implemented"
    base = compute(
        fingerprint="f" * 64,
        route_revision="route-v1",
        policy_revision="policy-v1",
        main=b"main",
        media=b"media",
    )
    assert len(base) == 64
    assert base == compute(
        fingerprint="f" * 64,
        route_revision="route-v1",
        policy_revision="policy-v1",
        main=b"main",
        media=b"media",
    )
    for key, value in (
        ("fingerprint", "e" * 64),
        ("route_revision", "route-v2"),
        ("policy_revision", "policy-v2"),
        ("main", b"main-2"),
        ("media", b"media-2"),
    ):
        values = {
            "fingerprint": "f" * 64,
            "route_revision": "route-v1",
            "policy_revision": "policy-v1",
            "main": b"main",
            "media": b"media",
        }
        values[key] = value
        assert compute(**values) != base


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fingerprint": b"f" * 64},
        {"route_revision": b"route-v1"},
        {"policy_revision": b"policy-v1"},
        {"main": "main"},
        {"media": "media"},
    ],
)
def test_batch_revision_rejects_non_exact_input_types(kwargs):
    values = {
        "fingerprint": "f" * 64,
        "route_revision": "route-v1",
        "policy_revision": "policy-v1",
        "main": b"main",
        "media": b"media",
    }
    values.update(kwargs)
    with pytest.raises(TypeError):
        compute = getattr(sitemap_render, "compute_batch_revision", None)
        assert callable(compute), "compute_batch_revision is not implemented"
        compute(**values)


def test_index_pins_both_children_to_one_batch_without_trailing_newline():
    batch = "a" * 64
    render = getattr(sitemap_render, "render_sitemap_index", None)
    assert callable(render), "render_sitemap_index is not implemented"
    xml = render("https://vinhlong360.vn", batch)
    assert xml == (
        b"<?xml version='1.0' encoding='utf-8'?>\n"
        b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<sitemap><loc>https://vinhlong360.vn/sitemap.xml?batch="
        + batch.encode()
        + b"</loc></sitemap><sitemap><loc>https://vinhlong360.vn/sitemap-media.xml?batch="
        + batch.encode()
        + b"</loc></sitemap></sitemapindex>"
    )
    assert not xml.startswith(b"\xef\xbb\xbf")
    assert not xml.endswith(b"\n")


@pytest.mark.parametrize(
    ("origin", "batch"),
    [
        ("http://vinhlong360.vn", "a" * 64),
        ("https://vinhlong360.vn/", "a" * 64),
        ("https://user:pass@vinhlong360.vn", "a" * 64),
        ("https://vinhlong360.vn?x=1", "a" * 64),
        ("https://vinhlong360.vn\\evil", "a" * 64),
        ("https://vĩnhlong360.vn", "a" * 64),
        ("https://vinhlong360.v\u200bn", "a" * 64),
        ("https://vinhlong360.vn\x00", "a" * 64),
        ("https://vinhlong360.vn", "A" * 64),
        ("https://vinhlong360.vn", "a" * 63),
    ],
)
def test_index_rejects_noncanonical_origin_or_batch(origin, batch):
    render = getattr(sitemap_render, "render_sitemap_index", None)
    assert callable(render), "render_sitemap_index is not implemented"
    with pytest.raises((TypeError, ValueError)):
        render(origin, batch)
