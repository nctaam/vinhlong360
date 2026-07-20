"""Strict image normalization and disclosure-backed entity descriptors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import ipaddress
import re

if __package__:
    from .ai_disclosure import LoadedAiDisclosure
else:
    from ai_disclosure import LoadedAiDisclosure


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


_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_PUNYCODE_PAYLOAD = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,57}[A-Za-z0-9])?\Z")
_IMAGE_DESCRIPTOR_KEYS = frozenset(
    {
        "alt",
        "credit",
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
    for label in labels:
        if not _DNS_LABEL.fullmatch(label):
            return False
        if label.lower().startswith("xn--") and not _PUNYCODE_PAYLOAD.fullmatch(
            label[4:]
        ):
            return False
    if all(label.isascii() and label.isdigit() for label in labels):
        if len(labels) != 4:
            return False
        return all(
            (label == "0" or not label.startswith("0")) and int(label) <= 255
            for label in labels
        )
    return True


def _valid_https_authority(authority: str) -> bool:
    if not authority or any(marker in authority for marker in ("@", "%")):
        return False

    if authority.startswith("["):
        closing = authority.find("]")
        if (
            closing <= 1
            or authority.count("[") != 1
            or authority.count("]") != 1
        ):
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

    if "[" in authority or "]" in authority or authority.count(":") > 1:
        return False
    if ":" in authority:
        host, port = authority.split(":", 1)
        if not _valid_port(port):
            return False
    else:
        host = authority
    return _valid_dns_host(host)


def normalize_renderable_image_url(raw: object) -> str | None:
    """Return an approved local or absolute HTTPS image URL."""
    if type(raw) is not str:
        return None
    normalized = raw.strip()
    if (
        not normalized
        or any(
            ord(character) <= 0x20 or ord(character) == 0x7F
            for character in normalized
        )
        or "\\" in normalized
        or "#" in normalized
        or normalized.startswith("//")
    ):
        return None

    if normalized.startswith("/"):
        return normalized

    if not normalized[:8].lower() == "https://":
        return None
    remainder = normalized[8:]
    authority_end = len(remainder)
    for delimiter in ("/", "?"):
        position = remainder.find(delimiter)
        if position >= 0:
            authority_end = min(authority_end, position)
    authority = remainder[:authority_end]
    if not _valid_https_authority(authority):
        return None
    return normalized


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


def _parse_supplied_entity_descriptor(
    raw: object,
    *,
    disclosure: LoadedAiDisclosure,
) -> ImageDescriptor | None:
    if type(raw) is not dict or set(raw) != _IMAGE_DESCRIPTOR_KEYS:
        return None
    url = normalize_renderable_image_url(raw.get("url"))
    alt = raw.get("alt")
    source_class = raw.get("source_class")
    source_kind = raw.get("source_kind")
    disclosure_key = raw.get("disclosure_key")
    short_label = raw.get("short_label")
    full_disclosure = raw.get("full_disclosure")
    credit = raw.get("credit")
    width = raw.get("width")
    height = raw.get("height")
    if url is None or type(alt) is not str or not alt.strip():
        return None
    if (source_class, source_kind, disclosure_key) != (
        "ai-generated",
        "entity-editorial",
        "entity-ai",
    ):
        return None
    if short_label != disclosure.entity_ai.short_label:
        return None
    if full_disclosure != disclosure.entity_ai.full_disclosure:
        return None
    if credit is not None or not _valid_descriptor_dimensions(width, height):
        return None
    return ImageDescriptor(
        url=url,
        alt=alt,
        source_class=source_class,
        source_kind=source_kind,
        disclosure_key=disclosure_key,
        short_label=short_label,
        full_disclosure=full_disclosure,
        credit=None,
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


def describe_entity_images(
    entity: object,
    *,
    disclosure: object,
) -> tuple[ImageDescriptor, ...]:
    """Return descriptors only for a well-formed entity image collection."""
    loaded_disclosure = _require_disclosure(disclosure)
    if not isinstance(entity, Mapping):
        return ()
    entity_name = entity.get("name")
    if type(entity_name) is not str or not entity_name.strip():
        return ()

    if "image_descriptors" in entity or "image_descriptor" in entity:
        return _supplied_entity_descriptors(entity, disclosure=loaded_disclosure)

    images = entity.get("images")
    if type(images) not in {list, tuple}:
        return ()

    descriptors: list[ImageDescriptor] = []
    for index, raw in enumerate(images):
        descriptor = describe_entity_image(
            raw,
            entity_name=entity_name,
            index=index,
            disclosure=loaded_disclosure,
        )
        if descriptor is not None:
            descriptors.append(descriptor)
    return tuple(descriptors)
