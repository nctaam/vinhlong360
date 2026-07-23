"""Canonical AI-only media provenance policy shared by API boundaries."""

from __future__ import annotations

from collections.abc import Mapping
import re


ENTITY_AI_SOURCE = ("ai-generated", "entity-editorial", "entity-ai")
ENTITY_PLACEHOLDER_SOURCE = (
    "placeholder",
    "generated-placeholder",
    "entity-placeholder",
)
REVIEW_UGC_SOURCE = ("user-uploaded", "review-ugc", "ugc-photo")
POST_UGC_SOURCE = ("user-uploaded", "post-ugc", "ugc-photo")

RENDERABLE_ENTITY_SOURCES = frozenset(
    {ENTITY_AI_SOURCE, ENTITY_PLACEHOLDER_SOURCE}
)

AI_ONLY_MEDIA_DETAIL = {
    "code": "ai_only_media",
    "message": "Only canonical AI-generated entity media is accepted.",
}

_CANONICAL_LEGACY_ENTITY_IMAGE = re.compile(
    r"/img/entities/[a-z0-9]+(?:-[a-z0-9]+)*\.webp\Z"
)


def is_canonical_legacy_entity_image(value: object) -> bool:
    """Return whether a legacy string is a canonical AI entity image path."""
    return type(value) is str and bool(_CANONICAL_LEGACY_ENTITY_IMAGE.fullmatch(value))


def descriptor_source(value: object) -> tuple[object, object, object] | None:
    if not isinstance(value, Mapping):
        return None
    return (
        value.get("source_class"),
        value.get("source_kind"),
        value.get("disclosure_key"),
    )


def is_renderable_entity_descriptor(value: object) -> bool:
    """Allow explicit entity media only for canonical AI or placeholder sources."""
    return descriptor_source(value) in RENDERABLE_ENTITY_SOURCES


def entity_images_are_ai_only(values: object) -> bool:
    """Validate non-empty raw entity image collections without rewriting them."""
    return type(values) is list and all(
        is_canonical_legacy_entity_image(value) for value in values
    )
