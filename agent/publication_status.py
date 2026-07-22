from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

if __package__:
    from .public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES
    from .source_policy import has_external_source_url
else:
    from public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES
    from source_policy import has_external_source_url


PUBLICATION_POLICY_REVISION = "published-v1"
PUBLISHED_V1_EXCLUSIONS = frozenset(
    {
        "prov-1",
        "test-mutation-create",
        "test-mutation-update",
        "cu-lao-dai-song-co-chien-vung-liem",
    }
)
PUBLICATION_REASON_ORDER = (
    "status-missing",
    "status-not-null",
    "verified-not-true",
    "entity-type-missing",
    "entity-type-not-allowlisted",
    "attributes-invalid",
    "non-public-flag",
    "external-source-missing",
    "reviewed-exclusion",
)

_MISSING = object()
_NON_PUBLIC_FLAGS = (
    "is_private",
    "private",
    "is_draft",
    "draft",
    "provisional",
    "unpublished",
)
_PUBLIC_FLAGS = ("is_public", "published")


@dataclass(frozen=True)
class PublicationDecision:
    eligible: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.eligible) is not bool:
            raise TypeError("eligible must be a boolean")
        if type(self.reasons) is not tuple:
            raise TypeError("reasons must be a tuple")
        if any(type(reason) is not str for reason in self.reasons):
            raise TypeError("decision reasons must be strings")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("decision reasons must be unique")
        try:
            positions = tuple(
                PUBLICATION_REASON_ORDER.index(reason) for reason in self.reasons
            )
        except ValueError as exc:
            raise ValueError("decision contains an unknown reason") from exc
        if positions != tuple(sorted(positions)):
            raise ValueError("decision reasons are not in canonical order")
        if self.eligible is bool(self.reasons):
            raise ValueError("eligible does not match decision reasons")


def _has_non_public_flag(container: Mapping[str, object]) -> bool:
    for field in _NON_PUBLIC_FLAGS:
        value = container.get(field, _MISSING)
        if value is not _MISSING and (type(value) is not bool or value is True):
            return True
    for field in _PUBLIC_FLAGS:
        value = container.get(field, _MISSING)
        if value is not _MISSING and (type(value) is not bool or value is not True):
            return True
    visibility = container.get("visibility", _MISSING)
    if visibility is not _MISSING and (
        type(visibility) is not str or visibility != "public"
    ):
        return True
    return False


def _validate_reviewed_exclusions(reviewed_exclusions: object) -> None:
    if type(reviewed_exclusions) is not frozenset:
        raise TypeError("reviewed_exclusions must be a frozenset")
    for exclusion in reviewed_exclusions:
        if type(exclusion) is not str:
            raise TypeError("reviewed_exclusions must contain strings")
        if not exclusion:
            raise ValueError("reviewed_exclusions cannot contain empty strings")


def decide_publication_candidate(
    entity: Mapping[str, object],
    *,
    reviewed_exclusions: frozenset[str] = PUBLISHED_V1_EXCLUSIONS,
) -> PublicationDecision:
    _validate_reviewed_exclusions(reviewed_exclusions)
    if not isinstance(entity, Mapping):
        raise TypeError("entity must be a mapping")
    reasons = _publication_reasons(entity, reviewed_exclusions)
    return PublicationDecision(eligible=not reasons, reasons=tuple(reasons))


def _publication_reasons(
    entity: Mapping[str, object], reviewed_exclusions: frozenset[str]
) -> list[str]:
    reasons: list[str] = []
    _append_status_reasons(reasons, entity.get("status", _MISSING))
    if not _verified_value(entity.get("verified", _MISSING)):
        reasons.append("verified-not-true")
    _append_type_reasons(reasons, entity.get("type", _MISSING))
    attributes = _attributes_or_empty(reasons, entity.get("attributes", _MISSING))
    if _has_non_public_flag(entity) or _has_non_public_flag(attributes):
        reasons.append("non-public-flag")
    if not has_external_source_url(entity.get("source")):
        reasons.append("external-source-missing")
    entity_id = entity.get("id", _MISSING)
    if type(entity_id) is str and entity_id in reviewed_exclusions:
        reasons.append("reviewed-exclusion")
    return reasons


def _append_status_reasons(reasons: list[str], status: object) -> None:
    if status is _MISSING:
        reasons.append("status-missing")
    elif status is not None:
        reasons.append("status-not-null")


def _verified_value(value: object) -> bool:
    return value is True or (type(value) is int and value == 1)


def _append_type_reasons(reasons: list[str], entity_type: object) -> None:
    missing = entity_type is _MISSING or entity_type is None or (
        type(entity_type) is str and not entity_type
    )
    if missing:
        reasons.append("entity-type-missing")
    elif type(entity_type) is not str or entity_type not in REVIEWED_NON_PLACE_ENTITY_TYPES:
        reasons.append("entity-type-not-allowlisted")


def _attributes_or_empty(reasons: list[str], attributes: object) -> Mapping[str, object]:
    if attributes is _MISSING or attributes is None:
        return {}
    if isinstance(attributes, Mapping):
        return attributes
    reasons.append("attributes-invalid")
    return {}
