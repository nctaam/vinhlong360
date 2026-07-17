from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

if __package__:
    from .launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence
    from .public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES
else:
    from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence
    from public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES


PUBLIC_STATUSES = frozenset({"published", "verified"})
ENTITY_REASON_ORDER = (
    "entity-type-missing",
    "entity-type-not-allowlisted",
    "public-status-missing",
    "public-status-not-allowlisted",
    "public-verification-missing",
    "public-explicitly-unverified",
    "public-private-content",
    "public-unpublished-content",
    "description-below-130-words",
)
WARD_REASON_ORDER = (
    "ward-type-not-place",
    "public-status-missing",
    "public-status-not-allowlisted",
    "public-verification-missing",
    "public-explicitly-unverified",
    "public-private-content",
    "public-unpublished-content",
    "ward-below-child-and-summary-threshold",
)
ITINERARY_REASON_ORDER = (
    "itinerary-fixed-noindex",
    "shared-plan-fixed-noindex",
)

_REASON_ORDERS = {
    "entity": ENTITY_REASON_ORDER,
    "ward": WARD_REASON_ORDER,
    "itinerary": ITINERARY_REASON_ORDER,
}

_ENTITY_FIELDS = (
    "type",
    "status",
    "verified",
    "is_private",
    "visibility",
    "is_public",
    "published",
    "summary",
    "description",
)
_MISSING = object()
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UNICODE_WORD = re.compile(r"\b\w+\b", flags=re.UNICODE)


@dataclass(frozen=True)
class IndexPolicyDecision:
    kind: str
    indexable: bool
    reasons: tuple[str, ...]
    policy_fingerprint: str
    policy_revision: str

    def __post_init__(self) -> None:
        _validate_decision_fields(self)
        _validate_decision_reasons(self)
        _validate_decision_evidence(self)


def _validate_decision_fields(decision: IndexPolicyDecision) -> None:
    if type(decision.kind) is not str or decision.kind not in _REASON_ORDERS:
        raise ValueError("decision kind must be entity, ward, or itinerary")
    if type(decision.indexable) is not bool:
        raise TypeError("indexable must be a boolean")
    if type(decision.reasons) is not tuple:
        raise TypeError("reasons must be a tuple")
    if any(type(reason) is not str for reason in decision.reasons):
        raise TypeError("decision reasons must be strings")


def _validate_decision_reasons(decision: IndexPolicyDecision) -> None:
    if len(set(decision.reasons)) != len(decision.reasons):
        raise ValueError("decision reasons must be unique")
    reason_order = _REASON_ORDERS[decision.kind]
    try:
        positions = tuple(reason_order.index(reason) for reason in decision.reasons)
    except ValueError as exc:
        raise ValueError("decision contains an unknown reason") from exc
    if positions != tuple(sorted(positions)):
        raise ValueError("decision reasons are not in canonical order")
    if decision.kind == "itinerary" and (
        decision.indexable or len(decision.reasons) != 1
    ):
        raise ValueError(
            "itinerary decision requires exactly one fixed noindex reason"
        )
    if decision.indexable is bool(decision.reasons):
        raise ValueError("indexable does not match decision reasons")


def _validate_decision_evidence(decision: IndexPolicyDecision) -> None:
    if (
        type(decision.policy_fingerprint) is not str
        or _SHA256.fullmatch(decision.policy_fingerprint) is None
    ):
        raise ValueError("decision policy fingerprint is invalid")
    if (
        type(decision.policy_revision) is not str
        or decision.policy_revision != INDEX_POLICY_REVISION
    ):
        raise ValueError("decision policy revision is not current")


def _snapshot(entity: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(entity, Mapping):
        raise TypeError("entity must be a mapping")
    return {field: entity.get(field, _MISSING) for field in _ENTITY_FIELDS}


def _is_supported_verified(value: object) -> bool:
    return value is True or (type(value) is int and value == 1)


def _entity_type_reasons(snapshot: Mapping[str, object]) -> tuple[str, ...]:
    entity_type = snapshot["type"]
    if entity_type is _MISSING or entity_type is None:
        return ("entity-type-missing",)
    if type(entity_type) is not str:
        return ("entity-type-not-allowlisted",)
    if not entity_type:
        return ("entity-type-missing",)
    if entity_type not in REVIEWED_NON_PLACE_ENTITY_TYPES:
        return ("entity-type-not-allowlisted",)
    return ()


def _status_reason(snapshot: Mapping[str, object]) -> str | None:
    status = snapshot["status"]
    if status is _MISSING or status is None:
        return "public-status-missing"
    if type(status) is not str or status not in PUBLIC_STATUSES:
        return "public-status-not-allowlisted"
    return None


def _verification_reason(snapshot: Mapping[str, object]) -> str | None:
    verified = snapshot["verified"]
    if verified is _MISSING or verified is None:
        return "public-verification-missing"
    if not _is_supported_verified(verified):
        return "public-explicitly-unverified"
    return None


def _has_private_marker(snapshot: Mapping[str, object]) -> bool:
    is_private = snapshot["is_private"]
    private_flag = is_private is not _MISSING and (
        type(is_private) is not bool or is_private is True
    )
    visibility = snapshot["visibility"]
    private_visibility = visibility is not _MISSING and (
        type(visibility) is not str or visibility != "public"
    )
    return private_flag or private_visibility


def _has_unpublished_marker(snapshot: Mapping[str, object]) -> bool:
    for field in ("is_public", "published"):
        value = snapshot[field]
        if value is not _MISSING and (type(value) is not bool or value is False):
            return True
    return False


def _public_eligibility_reasons(snapshot: Mapping[str, object]) -> tuple[str, ...]:
    reasons: list[str] = []
    status_reason = _status_reason(snapshot)
    if status_reason is not None:
        reasons.append(status_reason)
    verification_reason = _verification_reason(snapshot)
    if verification_reason is not None:
        reasons.append(verification_reason)
    if _has_private_marker(snapshot):
        reasons.append("public-private-content")
    if _has_unpublished_marker(snapshot):
        reasons.append("public-unpublished-content")

    return tuple(reasons)


def public_eligibility_reasons(entity: Mapping[str, object]) -> tuple[str, ...]:
    return _public_eligibility_reasons(_snapshot(entity))


def is_publicly_eligible(entity: Mapping[str, object]) -> bool:
    return not public_eligibility_reasons(entity)


def _ward_child_identity(child: Mapping[str, object]) -> tuple[str, str] | None:
    child_id = child.get("id")
    place_id = child.get("placeId")
    child_type = child.get("type")
    if type(child_id) is not str or not child_id.strip():
        return None
    if type(place_id) is not str or not place_id.strip():
        return None
    if type(child_type) is not str or not child_type.strip():
        return None
    if child_type == "place" or child_id == place_id:
        return None
    return place_id, child_id


def public_ward_child_counts(entities: Iterable[object]) -> dict[str, int]:
    """Count unique, strictly identified public non-place children by ward."""
    child_ids_by_ward: dict[str, set[str]] = {}
    for child in entities:
        if not isinstance(child, Mapping):
            continue
        identity = _ward_child_identity(child)
        if identity is None:
            continue
        if not is_publicly_eligible(child):
            continue
        place_id, child_id = identity
        child_ids_by_ward.setdefault(place_id, set()).add(child_id)
    return {
        ward_id: len(child_ids)
        for ward_id, child_ids in child_ids_by_ward.items()
    }


def _unicode_word_count(value: object) -> int:
    if type(value) is not str:
        return 0
    normalized = unicodedata.normalize("NFC", value).strip()
    return sum(
        any(character.isalpha() for character in token)
        for token in _UNICODE_WORD.findall(normalized)
    )


def _descriptive_word_count(snapshot: Mapping[str, object]) -> int:
    summary_value = snapshot["summary"]
    description_value = snapshot["description"]
    summary = (
        unicodedata.normalize("NFC", summary_value).strip()
        if type(summary_value) is str
        else ""
    )
    description = (
        unicodedata.normalize("NFC", description_value).strip()
        if type(description_value) is str
        else ""
    )
    parts = [summary]
    if description.casefold() != summary.casefold():
        parts.append(description)
    return _unicode_word_count(" ".join(parts))


def _require_evidence(evidence: PolicyEvidence) -> None:
    if type(evidence) is not PolicyEvidence:
        raise TypeError("evidence must be PolicyEvidence")


def decide_entity(
    entity: Mapping[str, object], evidence: PolicyEvidence
) -> IndexPolicyDecision:
    _require_evidence(evidence)
    snapshot = _snapshot(entity)
    if type(snapshot["type"]) is str and snapshot["type"] == "place":
        raise ValueError("decide_entity accepts non-place entities only")
    reasons = list(_entity_type_reasons(snapshot))
    reasons.extend(_public_eligibility_reasons(snapshot))
    if _descriptive_word_count(snapshot) < 130:
        reasons.append("description-below-130-words")
    return IndexPolicyDecision(
        kind="entity",
        indexable=not reasons,
        reasons=tuple(reasons),
        policy_fingerprint=evidence.policy_fingerprint,
        policy_revision=evidence.backend_policy_revision,
    )


def decide_ward(
    ward: Mapping[str, object],
    *,
    public_child_count: int,
    evidence: PolicyEvidence,
) -> IndexPolicyDecision:
    _require_evidence(evidence)
    if type(public_child_count) is not int:
        raise TypeError("public_child_count must be an integer")
    if public_child_count < 0:
        raise ValueError("public_child_count must be nonnegative")
    snapshot = _snapshot(ward)
    reasons: list[str] = []
    if type(snapshot["type"]) is not str or snapshot["type"] != "place":
        reasons.append("ward-type-not-place")
    reasons.extend(_public_eligibility_reasons(snapshot))
    if public_child_count <= 1 and _unicode_word_count(snapshot["summary"]) < 60:
        reasons.append("ward-below-child-and-summary-threshold")
    return IndexPolicyDecision(
        kind="ward",
        indexable=not reasons,
        reasons=tuple(reasons),
        policy_fingerprint=evidence.policy_fingerprint,
        policy_revision=evidence.backend_policy_revision,
    )


def decide_itinerary(
    *, shared_plan: bool, evidence: PolicyEvidence
) -> IndexPolicyDecision:
    _require_evidence(evidence)
    if type(shared_plan) is not bool:
        raise TypeError("shared_plan must be a boolean")
    reason = (
        "shared-plan-fixed-noindex"
        if shared_plan
        else "itinerary-fixed-noindex"
    )
    return IndexPolicyDecision(
        kind="itinerary",
        indexable=False,
        reasons=(reason,),
        policy_fingerprint=evidence.policy_fingerprint,
        policy_revision=evidence.backend_policy_revision,
    )
