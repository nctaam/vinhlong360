"""Deterministic rendering for the immutable main sitemap document."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote
from xml.etree.ElementTree import Element, SubElement, tostring

if __package__:
    from .index_policy import (
        decide_entity,
        decide_ward,
        public_ward_child_counts as _index_policy_ward_child_counts,
    )
    from .launch_evidence import PolicyEvidence
    from .route_manifest import (
        LoadedRouteManifest,
        extract_static_sitemap_paths,
        load_route_manifest,
    )
else:
    from index_policy import (
        decide_entity,
        decide_ward,
        public_ward_child_counts as _index_policy_ward_child_counts,
    )
    from launch_evidence import PolicyEvidence
    from route_manifest import (
        LoadedRouteManifest,
        extract_static_sitemap_paths,
        load_route_manifest,
    )


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
MAX_SITEMAP_URLS = 50_000


def public_ward_child_counts(snapshot) -> dict[str, int]:
    """Expose ward counts through the immutable sitemap snapshot contract."""
    return _index_policy_ward_child_counts(snapshot.entities)


def canonical_detail_url(
    entity: Mapping[str, object],
    canonical_origin: str,
) -> str | None:
    """Return one canonical detail URL, or None for malformed identifiers."""
    if not isinstance(entity, Mapping) or type(canonical_origin) is not str:
        return None
    entity_id = entity.get("id")
    if (
        type(entity_id) is not str
        or not entity_id
        or entity_id.strip() != entity_id
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in entity_id)
    ):
        return None
    prefix = "xa-phuong" if entity.get("type") == "place" else "dia-diem"
    return f"{canonical_origin}/{prefix}/{quote(entity_id, safe='')}"


def _indexable_detail_url(
    entity: object,
    *,
    child_counts: Mapping[str, int],
    canonical_origin: str,
    evidence,
) -> str | None:
    if not isinstance(entity, Mapping):
        return None
    if entity.get("type") == "place":
        ward_id = entity.get("id")
        public_child_count = (
            child_counts.get(ward_id, 0) if type(ward_id) is str else 0
        )
        decision = decide_ward(
            entity,
            public_child_count=public_child_count,
            evidence=evidence,
        )
    else:
        decision = decide_entity(entity, evidence)
    if not decision.indexable:
        return None
    return canonical_detail_url(entity, canonical_origin)


def _serialize_urlset(urls: list[str]) -> bytes:
    root = Element("urlset", {"xmlns": SITEMAP_NAMESPACE})
    for location in urls:
        node = SubElement(root, "url")
        SubElement(node, "loc").text = location
    return tostring(root, encoding="utf-8", xml_declaration=True)


def render_main_sitemap(
    snapshot,
    manifest: LoadedRouteManifest | None,
    evidence,
) -> bytes:
    """Render sorted, deduplicated loc-only XML from one immutable snapshot."""
    if type(evidence) is not PolicyEvidence:
        raise TypeError("evidence must be PolicyEvidence")
    manifest = manifest if manifest is not None else load_route_manifest()
    canonical_origin = manifest.data["canonical_origin"]
    entities = tuple(snapshot.entities)
    child_counts = public_ward_child_counts(snapshot)
    urls = {
        f"{canonical_origin}{path}"
        for path in extract_static_sitemap_paths(manifest)
    }
    for entity in entities:
        location = _indexable_detail_url(
            entity,
            child_counts=child_counts,
            canonical_origin=canonical_origin,
            evidence=evidence,
        )
        if location is not None:
            urls.add(location)
    return _serialize_urlset(sorted(urls)[:MAX_SITEMAP_URLS])
