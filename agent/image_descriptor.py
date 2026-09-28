"""Strict image normalization and disclosure-backed entity descriptors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import ipaddress
import re

if __package__:
    from .ai_disclosure import LoadedAiDisclosure
    from .media_provenance import DOCUMENTARY_IMAGE_TYPES, sourced_photo_evidence
    from .media_policy import (
        ENTITY_AI_SOURCE,
        ENTITY_PLACEHOLDER_SOURCE,
        descriptor_source,
        is_canonical_legacy_entity_image,
        is_renderable_entity_descriptor,
    )
else:
    from ai_disclosure import LoadedAiDisclosure
    from media_provenance import DOCUMENTARY_IMAGE_TYPES, sourced_photo_evidence
    from media_policy import (
        ENTITY_AI_SOURCE,
        ENTITY_PLACEHOLDER_SOURCE,
        descriptor_source,
        is_canonical_legacy_entity_image,
        is_renderable_entity_descriptor,
    )


@dataclass(frozen=True)
class ImageDescriptor:
    url: str | None
    alt: str
    source_class: str
    source_kind: str
    disclosure_key: str
    short_label: str | None
    full_disclosure: str
    credit: str | None
    width: int | None
    height: int | None
    source_url: str | None = None


_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_PUNYCODE_PAYLOAD = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,57}[A-Za-z0-9])?\Z")
_IMAGE_DESCRIPTOR_KEYS = frozenset(
    {
        "alt",
        "credit",
        "source_url",
        "disclosure_key",
        "full_disclosure",
        "height",
        "short_label",
        "source_class",
        "source_kind",
        "url",
        "width",
    }
)


def _valid_port(port: str) -> bool:
    if len(port) > 5 or not re.fullmatch(r"[0-9]+", port):
        return False
    try:
        return 1 <= int(port) <= 65535
    except ValueError:
        return False


def _valid_dns_host(host: str) -> bool:
    if not host or len(host) > 253:
        return False
    labels = host.split(".")
    return _valid_dns_labels(labels)


def _valid_dns_labels(labels: list[str]) -> bool:
    for label in labels:
        if not _valid_dns_label(label):
            return False
    return _valid_ipv4_labels(labels) if all(
        label.isascii() and label.isdigit() for label in labels
    ) else True


def _valid_dns_label(label: str) -> bool:
    if not _DNS_LABEL.fullmatch(label):
        return False
    return not label.lower().startswith("xn--") or bool(
        _PUNYCODE_PAYLOAD.fullmatch(label[4:])
    )


def _valid_ipv4_labels(labels: list[str]) -> bool:
    if len(labels) != 4:
        return False
    return all(
        (label == "0" or not label.startswith("0")) and int(label) <= 255
        for label in labels
    )


def _valid_https_authority(authority: str) -> bool:
    if not authority or any(marker in authority for marker in ("@", "%")):
        return False

    if authority.startswith("["):
        return _valid_bracketed_authority(authority)

    if "[" in authority or "]" in authority or authority.count(":") > 1:
        return False
    host, separator, port = authority.partition(":")
    if separator and not _valid_port(port):
        return False
    return _valid_dns_host(host)


def _valid_bracketed_authority(authority: str) -> bool:
    closing = authority.find("]")
    if closing <= 1 or authority.count("[") != 1 or authority.count("]") != 1:
        return False
    host = authority[1:closing]
    suffix = authority[closing + 1 :]
    if suffix and (not suffix.startswith(":") or not _valid_port(suffix[1:])):
        return False
    try:
        ipaddress.IPv6Address(host)
    except ValueError:
        return False
    return True


def normalize_renderable_image_url(raw: object) -> str | None:
    """Return an approved local or absolute HTTPS image URL."""
    if type(raw) is not str:
        return None
    normalized = raw.strip()
    if _unsafe_image_url(normalized):
        return None

    if normalized.startswith("/"):
        return normalized

    if not normalized[:8].lower() == "https://":
        return None
    authority = _https_authority(normalized[8:])
    if not _valid_https_authority(authority):
        return None
    return normalized


def _unsafe_image_url(normalized: str) -> bool:
    return (
        not normalized
        or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in normalized)
        or "\\" in normalized
        or "#" in normalized
        or normalized.startswith("//")
    )


def _https_authority(remainder: str) -> str:
    authority_end = len(remainder)
    for delimiter in ("/", "?"):
        position = remainder.find(delimiter)
        if position >= 0:
            authority_end = min(authority_end, position)
    return remainder[:authority_end]


def _require_disclosure(disclosure: object) -> LoadedAiDisclosure:
    if type(disclosure) is not LoadedAiDisclosure:
        raise TypeError("disclosure must be LoadedAiDisclosure")
    return disclosure


def describe_entity_image(
    raw: object,
    *,
    entity_name: object,
    index: object,
    disclosure: object,
) -> ImageDescriptor | None:
    """Describe one current editorial entity image as disclosed AI media."""
    loaded_disclosure = _require_disclosure(disclosure)
    if (
        type(entity_name) is not str
        or not entity_name.strip()
        or type(index) is not int
        or index < 0
    ):
        return None
    if not is_canonical_legacy_entity_image(raw):
        return None
    url = normalize_renderable_image_url(raw)
    if url is None:
        return None
    copy = loaded_disclosure.entity_ai
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — ảnh minh họa {index + 1}",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=copy.short_label,
        full_disclosure=copy.full_disclosure,
        credit=None,
        source_url=None,
        width=None,
        height=None,
    )


def describe_review_image(
    raw: object,
    *,
    entity_name: object,
    credit: object,
    disclosure: object,
) -> ImageDescriptor | None:
    """Describe one trusted review photo as user-uploaded media."""
    loaded_disclosure = _require_disclosure(disclosure)
    if type(entity_name) is not str or not entity_name.strip():
        return None
    normalized_credit = (
        credit if type(credit) is str and credit.strip() else None
    )
    url = normalize_renderable_image_url(raw)
    if url is None:
        return None
    copy = loaded_disclosure.ugc_photo
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — ảnh đánh giá",
        source_class="user-uploaded",
        source_kind="review-ugc",
        disclosure_key="ugc-photo",
        short_label=copy.short_label,
        full_disclosure=copy.full_disclosure,
        credit=normalized_credit,
        source_url=None,
        width=None,
        height=None,
    )


def _valid_descriptor_dimensions(width: object, height: object) -> bool:
    if (width is None) != (height is None):
        return False
    if width is None:
        return True
    return (
        type(width) is int
        and width > 0
        and type(height) is int
        and height > 0
    )


def _supplied_entity_descriptor_copy(
    raw: dict,
    source: tuple[object, object, object] | None,
    disclosure: LoadedAiDisclosure,
) -> tuple[str | None, object] | None:
    if source == ENTITY_AI_SOURCE:
        url = normalize_renderable_image_url(raw.get("url"))
        return (url, disclosure.entity_ai) if url is not None else None
    if source == ENTITY_PLACEHOLDER_SOURCE and raw.get("url") is None:
        return None, disclosure.placeholder
    return None


def _parse_supplied_entity_descriptor(
    raw: object,
    *,
    disclosure: LoadedAiDisclosure,
) -> ImageDescriptor | None:
    if type(raw) is not dict or set(raw) != _IMAGE_DESCRIPTOR_KEYS:
        return None
    alt = raw.get("alt")
    source = descriptor_source(raw)
    short_label = raw.get("short_label")
    full_disclosure = raw.get("full_disclosure")
    credit = raw.get("credit")
    source_url = raw.get("source_url")
    width = raw.get("width")
    height = raw.get("height")
    if type(alt) is not str or not alt.strip():
        return None
    if not is_renderable_entity_descriptor(raw):
        return None
    normalized = _supplied_entity_descriptor_copy(raw, source, disclosure)
    if normalized is None:
        return None
    url, copy = normalized
    if short_label != copy.short_label:
        return None
    if full_disclosure != copy.full_disclosure:
        return None
    if credit is not None or source_url is not None:
        return None
    if not _valid_descriptor_dimensions(width, height):
        return None
    source_class, source_kind, disclosure_key = source
    return ImageDescriptor(
        url=url,
        alt=alt,
        source_class=source_class,
        source_kind=source_kind,
        disclosure_key=disclosure_key,
        short_label=short_label,
        full_disclosure=full_disclosure,
        credit=None,
        source_url=None,
        width=width,
        height=height,
    )


def _supplied_entity_descriptors(
    entity: Mapping[str, object],
    *,
    disclosure: LoadedAiDisclosure,
) -> tuple[ImageDescriptor, ...]:
    raw_values: list[object] = []
    if "image_descriptors" in entity:
        if type(entity.get("image_descriptors")) is not list:
            return ()
        raw_values.extend(entity["image_descriptors"])
    if "image_descriptor" in entity:
        raw_values.append(entity.get("image_descriptor"))
    return tuple(
        descriptor
        for raw in raw_values
        if (descriptor := _parse_supplied_entity_descriptor(
            raw,
            disclosure=disclosure,
        ))
        is not None
    )


def _entity_media_class(entity: Mapping[str, object]) -> str | None:
    attributes = entity.get("attributes")
    if not isinstance(attributes, Mapping):
        return None
    value = attributes.get("image_type")
    return value.strip().lower() if type(value) is str and value.strip() else None


def _classified_local_images(
    entity: Mapping[str, object],
) -> tuple[str, tuple[tuple[int, str], ...]] | None:
    entity_name = entity.get("name")
    images = entity.get("images")
    if (
        type(entity_name) is not str
        or not entity_name.strip()
        or type(images) not in {list, tuple}
    ):
        return None
    local_images = tuple(
        (index, url)
        for index, raw in enumerate(images)
        if (url := normalize_renderable_image_url(raw)) is not None
        and url.startswith("/")
    )
    return entity_name, local_images


def _placeholder_entity_descriptor(
    url: str,
    *,
    entity_name: str,
    index: int,
    disclosure: LoadedAiDisclosure,
) -> ImageDescriptor:
    copy = disclosure.placeholder
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — minh họa chưa được xác minh {index + 1}",
        source_class="placeholder",
        source_kind="generated-placeholder",
        disclosure_key="entity-placeholder",
        short_label=copy.short_label,
        full_disclosure=copy.full_disclosure,
        credit=None,
        source_url=None,
        width=None,
        height=None,
    )


def _ai_entity_descriptor(
    url: str,
    *,
    entity_name: str,
    index: int,
    disclosure: LoadedAiDisclosure,
) -> ImageDescriptor:
    copy = disclosure.entity_ai
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — ảnh minh họa {index + 1}",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=copy.short_label,
        full_disclosure=copy.full_disclosure,
        credit=None,
        source_url=None,
        width=None,
        height=None,
    )


def _descriptors_for_classified_entity(
    entity: Mapping[str, object],
    media_class: str,
    disclosure: LoadedAiDisclosure,
) -> tuple[ImageDescriptor, ...]:
    local_media = _classified_local_images(entity)
    if local_media is None:
        return ()
    entity_name, local_images = local_media
    attributes = entity.get("attributes")
    if not isinstance(attributes, Mapping):
        return ()

    evidence = (
        sourced_photo_evidence(attributes)
        if media_class in DOCUMENTARY_IMAGE_TYPES
        else None
    )
    descriptors: list[ImageDescriptor] = []
    for index, url in local_images:
        if evidence is not None:
            copy = disclosure.sourced_photo
            descriptors.append(ImageDescriptor(
                url=url,
                alt=f"{entity_name} — ảnh tư liệu {index + 1}",
                source_class="rights-cleared",
                source_kind=evidence.image_type,
                disclosure_key="entity-sourced-photo",
                short_label=copy.short_label,
                full_disclosure=copy.full_disclosure,
                credit=evidence.credit,
                source_url=evidence.source_url,
                width=None,
                height=None,
            ))
        elif (
            media_class == "ai-generated"
            and attributes.get("is_verified_photo") is False
        ):
            descriptors.append(_ai_entity_descriptor(
                url,
                entity_name=entity_name,
                index=index,
                disclosure=disclosure,
            ))
        else:
            descriptors.append(_placeholder_entity_descriptor(
                url,
                entity_name=entity_name,
                index=index,
                disclosure=disclosure,
            ))
    return tuple(descriptors)


def describe_entity_images(
    entity: object,
    *,
    disclosure: object,
) -> tuple[ImageDescriptor, ...]:
    """Return descriptors from explicit entity media classification and evidence."""
    loaded_disclosure = _require_disclosure(disclosure)
    if not isinstance(entity, Mapping):
        return ()
    supplied = _supplied_entity_descriptors(entity, disclosure=loaded_disclosure)
    if "image_descriptor" in entity or "image_descriptors" in entity:
        return supplied
    media_class = _entity_media_class(entity)
    if media_class not in {
        "generated-placeholder",
        "ai-generated",
        *DOCUMENTARY_IMAGE_TYPES,
    }:
        return ()
    return _descriptors_for_classified_entity(entity, media_class, loaded_disclosure)
