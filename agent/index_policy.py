from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

if __package__:
    from .launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence
else:
    from launch_evidence import INDEX_POLICY_REVISION, PolicyEvidence


PUBLIC_STATUSES = frozenset({"published", "verified"})
ENTITY_REASON_ORDER = (
    "public-status-missing",
    "public-status-not-allowlisted",
    "public-verification-missing",
    "public-explicitly-unverified",
    "public-private-content",
    "public-unpublished-content",
    "description-below-130-words",
)

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
        if type(self.kind) is not str or self.kind != "entity":
            raise ValueError("decision kind must be entity")
        if type(self.indexable) is not bool:
            raise TypeError("indexable must be a boolean")
        if type(self.reasons) is not tuple:
            raise TypeError("reasons must be a tuple")
        if any(type(reason) is not str for reason in self.reasons):
            raise TypeError("decision reasons must be strings")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("decision reasons must be unique")
        try:
            positions = tuple(
                ENTITY_REASON_ORDER.index(reason) for reason in self.reasons
            )
        except ValueError as exc:
            raise ValueError("decision contains an unknown reason") from exc
        if positions != tuple(sorted(positions)):
            raise ValueError("decision reasons are not in canonical order")
        if self.indexable is bool(self.reasons):
            raise ValueError("indexable does not match decision reasons")
        if (
            type(self.policy_fingerprint) is not str
            or _SHA256.fullmatch(self.policy_fingerprint) is None
        ):
            raise ValueError("decision policy fingerprint is invalid")
        if (
            type(self.policy_revision) is not str
            or self.policy_revision != INDEX_POLICY_REVISION
        ):
            raise ValueError("decision policy revision is not current")


def _snapshot(entity: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(entity, Mapping):
        raise TypeError("entity must be a mapping")
    return {field: entity.get(field, _MISSING) for field in _ENTITY_FIELDS}


def _append_once(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _is_supported_verified(value: object) -> bool:
    return value is True or (type(value) is int and value == 1)


def _public_eligibility_reasons(snapshot: Mapping[str, object]) -> tuple[str, ...]:
    reasons: list[str] = []

    status = snapshot["status"]
    if status is _MISSING or status is None:
        reasons.append("public-status-missing")
    elif type(status) is not str or status not in PUBLIC_STATUSES:
        reasons.append("public-status-not-allowlisted")

    verified = snapshot["verified"]
    if verified is _MISSING or verified is None:
        reasons.append("public-verification-missing")
    elif not _is_supported_verified(verified):
        reasons.append("public-explicitly-unverified")

    is_private = snapshot["is_private"]
    if is_private is not _MISSING and (
        type(is_private) is not bool or is_private is True
    ):
        _append_once(reasons, "public-private-content")

    visibility = snapshot["visibility"]
    if visibility is not _MISSING and (
        type(visibility) is not str or visibility != "public"
    ):
        _append_once(reasons, "public-private-content")

    for field in ("is_public", "published"):
        value = snapshot[field]
        if value is not _MISSING and (type(value) is not bool or value is False):
            _append_once(reasons, "public-unpublished-content")

    return tuple(reasons)


def public_eligibility_reasons(entity: Mapping[str, object]) -> tuple[str, ...]:
    return _public_eligibility_reasons(_snapshot(entity))


def is_publicly_eligible(entity: Mapping[str, object]) -> bool:
    return not public_eligibility_reasons(entity)


def _descriptive_word_count(snapshot: Mapping[str, object]) -> int:
    summary_value = snapshot["summary"]
    description_value = snapshot["description"]
    summary = summary_value.strip() if type(summary_value) is str else ""
    description = description_value.strip() if type(description_value) is str else ""
    parts = [summary]
    if description.casefold() != summary.casefold():
        parts.append(description)
    return len(_UNICODE_WORD.findall(" ".join(parts)))


def decide_entity(
    entity: Mapping[str, object], evidence: PolicyEvidence
) -> IndexPolicyDecision:
    if type(evidence) is not PolicyEvidence:
        raise TypeError("evidence must be PolicyEvidence")
    snapshot = _snapshot(entity)
    if snapshot["type"] == "place":
        raise ValueError("decide_entity accepts non-place entities only")
    reasons = list(_public_eligibility_reasons(snapshot))
    if _descriptive_word_count(snapshot) < 130:
        reasons.append("description-below-130-words")
    return IndexPolicyDecision(
        kind="entity",
        indexable=not reasons,
        reasons=tuple(reasons),
        policy_fingerprint=evidence.policy_fingerprint,
        policy_revision=evidence.backend_policy_revision,
    )
