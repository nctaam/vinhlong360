"""Strict image normalization and disclosure-backed entity descriptors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

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

    try:
        parsed = urlsplit(normalized)
    except ValueError:
        return None

    if normalized.startswith("/"):
        if parsed.scheme or parsed.netloc:
            return None
        return normalized

    if parsed.scheme.lower() != "https" or not parsed.netloc:
        return None
    try:
        hostname = parsed.hostname
        port = parsed.port
        username = parsed.username
        password = parsed.password
    except ValueError:
        return None
    if (
        hostname is None
        or username is not None
        or password is not None
        or parsed.netloc.endswith(":")
    ):
        return None
    del port
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
        or index < 1
    ):
        return None
    url = normalize_renderable_image_url(raw)
    if url is None:
        return None
    copy = loaded_disclosure.entity_ai
    return ImageDescriptor(
        url=url,
        alt=f"{entity_name} — ảnh minh họa {index}",
        source_class="ai-generated",
        source_kind="entity-editorial",
        disclosure_key="entity-ai",
        short_label=copy.short_label,
        full_disclosure=copy.full_disclosure,
        credit=None,
        width=None,
        height=None,
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
    images = entity.get("images")
    if (
        type(entity_name) is not str
        or not entity_name.strip()
        or type(images) not in {list, tuple}
    ):
        return ()

    descriptors: list[ImageDescriptor] = []
    for index, raw in enumerate(images, start=1):
        descriptor = describe_entity_image(
            raw,
            entity_name=entity_name,
            index=index,
            disclosure=loaded_disclosure,
        )
        if descriptor is not None:
            descriptors.append(descriptor)
    return tuple(descriptors)
