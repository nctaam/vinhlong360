from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest


AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence  # noqa: E402
from route_manifest import extract_static_sitemap_paths, load_route_manifest  # noqa: E402
from sitemap_render import (  # noqa: E402
    canonical_detail_url,
    public_ward_child_counts,
    render_main_sitemap,
)
from sitemap_snapshot import SitemapSnapshot  # noqa: E402


EVIDENCE = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


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
