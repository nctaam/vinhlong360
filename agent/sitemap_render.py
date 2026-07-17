"""Deterministic rendering for the immutable main sitemap document."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from re import fullmatch
from urllib.parse import quote, urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

if __package__:
    from .ai_disclosure import LoadedAiDisclosure
    from .image_descriptor import ImageDescriptor, describe_entity_images, normalize_renderable_image_url
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
    from ai_disclosure import LoadedAiDisclosure
    from image_descriptor import ImageDescriptor, describe_entity_images, normalize_renderable_image_url
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
IMAGE_NAMESPACE = "http://www.google.com/schemas/sitemap-image/1.1"
MAX_SITEMAP_URLS = 50_000
_BATCH_REVISION_PATTERN = r"[0-9a-f]{64}"


def compute_batch_revision(
    *,
    fingerprint: str,
    route_revision: str,
    policy_revision: str,
    main: bytes,
    media: bytes,
) -> str:
    """Compute the content address for one completed main/media pair."""
    values: tuple[bytes, ...] = []
    for value in (fingerprint, route_revision, policy_revision):
        if type(value) is not str:
            raise TypeError("sitemap batch text inputs must be exact strings")
        values.append(value.encode("utf-8"))
    for value in (main, media):
        if type(value) is not bytes:
            raise TypeError("sitemap batch document inputs must be exact bytes")
        values.append(value)
    digest = sha256()
    for value in values:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def _validate_sitemap_origin(origin: object) -> str:
    if type(origin) is not str:
        raise TypeError("sitemap origin must be an exact string")
    parsed = urlsplit(origin)
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("sitemap origin has an invalid port") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.netloc != parsed.hostname
        or origin != f"https://{parsed.hostname}"
    ):
        raise ValueError("sitemap origin must be a canonical HTTPS origin")
    return origin


def _validate_batch_revision(batch: object) -> str:
    if type(batch) is not str or fullmatch(_BATCH_REVISION_PATTERN, batch) is None:
        raise ValueError("sitemap batch revision must be lowercase SHA-256")
    return batch


def render_sitemap_index(origin: str, batch: str) -> bytes:
    """Render the exact two-child index for one immutable batch."""
    canonical_origin = _validate_sitemap_origin(origin)
    revision = _validate_batch_revision(batch)
    root = Element("sitemapindex", {"xmlns": SITEMAP_NAMESPACE})
    for path in ("/sitemap.xml", "/sitemap-media.xml"):
        node = SubElement(root, "sitemap")
        SubElement(node, "loc").text = (
            f"{canonical_origin}{path}?batch={revision}"
        )
    return tostring(root, encoding="utf-8", xml_declaration=True)


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


def resolve_sitemap_image_url(
    raw: object,
    manifest: LoadedRouteManifest,
) -> str | None:
    """Resolve a normalized local image path without URL-join semantics."""
    normalized = normalize_renderable_image_url(raw)
    if normalized is None:
        return None
    candidate = (
        f"{manifest.data['canonical_origin']}{normalized}"
        if normalized.startswith("/")
        else normalized
    )
    resolved = normalize_renderable_image_url(candidate)
    if resolved is None or resolved.startswith("/"):
        return None
    return resolved


def serialize_image_urlset(
    pages: Mapping[str, Mapping[str, ImageDescriptor]],
) -> bytes:
    """Serialize sorted page/image groups with only disclosure-safe image tags."""
    root = Element(
        "urlset",
        {
            "xmlns": SITEMAP_NAMESPACE,
            "xmlns:image": IMAGE_NAMESPACE,
        },
    )
    for page_url in sorted(pages)[:MAX_SITEMAP_URLS]:
        descriptors = pages[page_url]
        node = SubElement(root, "url")
        SubElement(node, "loc").text = page_url
        for image_url in sorted(descriptors):
            descriptor = descriptors[image_url]
            if (
                type(descriptor) is not ImageDescriptor
                or descriptor.source_class != "ai-generated"
            ):
                continue
            image = SubElement(node, "image:image")
            SubElement(image, "image:loc").text = image_url
            SubElement(image, "image:caption").text = descriptor.full_disclosure
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


def render_media_sitemap(
    snapshot,
    manifest: LoadedRouteManifest | None,
    evidence,
    disclosure,
) -> bytes:
    """Render disclosed entity editorial images with main-sitemap policy parity."""
    if type(evidence) is not PolicyEvidence:
        raise TypeError("evidence must be PolicyEvidence")
    if type(disclosure) is not LoadedAiDisclosure:
        raise TypeError("disclosure must be LoadedAiDisclosure")
    manifest = manifest if manifest is not None else load_route_manifest()
    canonical_origin = manifest.data["canonical_origin"]
    entities = tuple(snapshot.entities)
    child_counts = public_ward_child_counts(snapshot)
    pages: dict[str, dict[str, ImageDescriptor]] = {}
    for entity in entities:
        page_url = _indexable_detail_url(
            entity,
            child_counts=child_counts,
            canonical_origin=canonical_origin,
            evidence=evidence,
        )
        if page_url is None:
            continue
        for descriptor in describe_entity_images(entity, disclosure=disclosure):
            if descriptor.source_class != "ai-generated":
                continue
            image_url = resolve_sitemap_image_url(descriptor.url, manifest)
            if image_url is not None:
                pages.setdefault(page_url, {}).setdefault(image_url, descriptor)
    return serialize_image_urlset(pages)
