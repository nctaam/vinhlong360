from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from publication_status import (
    PUBLICATION_POLICY_REVISION,
    PUBLICATION_REASON_ORDER,
    PUBLISHED_V1_EXCLUSIONS,
    PublicationDecision,
    decide_publication_candidate,
)


def _candidate(**overrides: object) -> dict[str, object]:
    entity: dict[str, object] = {
        "id": "candidate",
        "type": "dish",
        "status": None,
        "verified": True,
        "attributes": {},
        "source": [{"url": "https://example.org/source"}],
    }
    entity.update(overrides)
    return entity


def test_policy_constants_are_exact():
    assert PUBLICATION_POLICY_REVISION == "published-v1"
    assert PUBLISHED_V1_EXCLUSIONS == frozenset(
        {
            "prov-1",
            "test-mutation-create",
            "test-mutation-update",
            "cu-lao-dai-song-co-chien-vung-liem",
        }
    )
    assert PUBLICATION_REASON_ORDER == (
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


def test_valid_candidate_is_eligible():
    assert decide_publication_candidate(_candidate()) == PublicationDecision(
        eligible=True,
        reasons=(),
    )


@pytest.mark.parametrize("verified", [False, 0, None, "true", 1.0])
def test_verified_requires_exact_true_or_legacy_integer_one(verified: object):
    assert decide_publication_candidate(_candidate(verified=verified)) == (
        PublicationDecision(eligible=False, reasons=("verified-not-true",))
    )


def test_legacy_integer_one_verification_is_accepted():
    assert decide_publication_candidate(_candidate(verified=1)).eligible is True


@pytest.mark.parametrize("status", ["", "draft", "private", "published", "verified"])
def test_every_non_null_status_is_rejected(status: object):
    assert decide_publication_candidate(_candidate(status=status)) == (
        PublicationDecision(eligible=False, reasons=("status-not-null",))
    )


def test_missing_status_is_distinct_from_non_null_status():
    candidate = _candidate()
    del candidate["status"]

    assert decide_publication_candidate(candidate) == PublicationDecision(
        eligible=False,
        reasons=("status-missing",),
    )


@pytest.mark.parametrize(
    "entity_type, expected_reason",
    [
        ("place", "entity-type-not-allowlisted"),
        ("itinerary", "entity-type-not-allowlisted"),
        ("unknown", "entity-type-not-allowlisted"),
        (None, "entity-type-missing"),
        (1, "entity-type-not-allowlisted"),
    ],
)
def test_entity_type_must_be_in_the_shared_reviewed_allowlist(
    entity_type: object,
    expected_reason: str,
):
    assert decide_publication_candidate(_candidate(type=entity_type)) == (
        PublicationDecision(eligible=False, reasons=(expected_reason,))
    )


@pytest.mark.parametrize("entity_type", [None, ""])
def test_missing_or_empty_entity_type_uses_missing_reason(entity_type: object):
    candidate = _candidate(type=entity_type)
    assert decide_publication_candidate(candidate).reasons == (
        "entity-type-missing",
    )


def test_absent_entity_type_uses_missing_reason():
    candidate = _candidate()
    del candidate["type"]

    assert decide_publication_candidate(candidate).reasons == (
        "entity-type-missing",
    )


@pytest.mark.parametrize(
    "source",
    [
        [],
        {"title": "Manual review"},
        "/relative/source",
        "http://localhost:8000/source",
        "http://127.0.0.1/source",
        "https://www.vinhlong360.vn/source",
        "manual",
        "http://224.0.0.1/source",
        "https://foo.test/source",
    ],
)
def test_source_must_contain_an_external_public_http_url(source: object):
    assert decide_publication_candidate(_candidate(source=source)) == (
        PublicationDecision(eligible=False, reasons=("external-source-missing",))
    )


@pytest.mark.parametrize(
    "source",
    [
        "https://example.org/source",
        {"url": "https://example.org/source"},
        [{"href": "https://example.org/source"}],
    ],
)
def test_supported_external_source_shapes_are_eligible(source: object):
    assert decide_publication_candidate(_candidate(source=source)) == (
        PublicationDecision(eligible=True, reasons=())
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("is_private", True),
        ("private", True),
        ("is_draft", True),
        ("draft", True),
        ("provisional", True),
        ("unpublished", True),
        ("is_public", False),
        ("published", False),
        ("visibility", "private"),
    ],
)
@pytest.mark.parametrize("location", ["top-level", "attributes"])
def test_non_public_flags_fail_closed_in_both_supported_locations(
    field: str,
    value: object,
    location: str,
):
    candidate = _candidate()
    if location == "top-level":
        candidate[field] = value
    else:
        candidate["attributes"] = {field: value}

    assert decide_publication_candidate(candidate) == PublicationDecision(
        eligible=False,
        reasons=("non-public-flag",),
    )


@pytest.mark.parametrize(
    "field, value",
    [
        ("is_private", 0),
        ("private", "false"),
        ("is_draft", 1),
        ("draft", None),
        ("provisional", "yes"),
        ("unpublished", []),
        ("is_public", 1),
        ("published", "true"),
        ("visibility", True),
    ],
)
@pytest.mark.parametrize("location", ["top-level", "attributes"])
def test_non_boolean_flag_values_do_not_alias_valid_boolean_values(
    field: str,
    value: object,
    location: str,
):
    candidate = _candidate()
    if location == "top-level":
        candidate[field] = value
    else:
        candidate["attributes"] = {field: value}

    assert decide_publication_candidate(candidate).reasons == (
        "non-public-flag",
    )


@pytest.mark.parametrize("attributes", [[], 1])
def test_malformed_attributes_fail_closed(attributes: object):
    assert decide_publication_candidate(_candidate(attributes=attributes)) == (
        PublicationDecision(eligible=False, reasons=("attributes-invalid",))
    )


@pytest.mark.parametrize("attributes", [None, pytest.param({}, id="mapping")])
def test_null_or_mapping_attributes_are_supported(attributes: object):
    assert decide_publication_candidate(_candidate(attributes=attributes)).eligible is True


def test_absent_attributes_default_to_an_empty_mapping():
    candidate = _candidate()
    del candidate["attributes"]

    assert decide_publication_candidate(candidate).eligible is True


def test_reviewed_exclusion_is_the_only_reason_for_an_otherwise_valid_row():
    assert decide_publication_candidate(_candidate(id="prov-1")) == (
        PublicationDecision(eligible=False, reasons=("reviewed-exclusion",))
    )


@pytest.mark.parametrize("entity_id", [None, 1, True, ["prov-1"]])
def test_non_string_ids_do_not_match_or_crash(entity_id: object):
    assert decide_publication_candidate(_candidate(id=entity_id)).eligible is True


def test_custom_reviewed_exclusions_are_honored():
    assert decide_publication_candidate(
        _candidate(),
        reviewed_exclusions=frozenset({"candidate"}),
    ).reasons == ("reviewed-exclusion",)


def test_combined_failures_are_unique_and_in_canonical_order():
    candidate = _candidate(
        id="prov-1",
        type="unknown",
        status="draft",
        verified=False,
        attributes={"draft": True, "unpublished": True},
        is_private=True,
        source="manual",
    )

    assert decide_publication_candidate(candidate) == PublicationDecision(
        eligible=False,
        reasons=(
            "status-not-null",
            "verified-not-true",
            "entity-type-not-allowlisted",
            "non-public-flag",
            "external-source-missing",
            "reviewed-exclusion",
        ),
    )


def test_predicate_requires_a_mapping_and_does_not_mutate_or_alias_input():
    with pytest.raises(TypeError, match="entity must be a mapping"):
        decide_publication_candidate([])  # type: ignore[arg-type]

    candidate = _candidate(attributes={"visibility": "private"})
    original = copy.deepcopy(candidate)
    decision = decide_publication_candidate(MappingProxyType(candidate))

    assert candidate == original
    candidate["attributes"]["visibility"] = "public"  # type: ignore[index]
    assert decision == PublicationDecision(
        eligible=False,
        reasons=("non-public-flag",),
    )


def test_decision_is_frozen_and_runtime_validated():
    decision = PublicationDecision(eligible=True, reasons=())
    with pytest.raises(FrozenInstanceError):
        decision.eligible = False  # type: ignore[misc]

    with pytest.raises(TypeError, match="eligible must be a boolean"):
        PublicationDecision(eligible=1, reasons=())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="reasons must be a tuple"):
        PublicationDecision(eligible=False, reasons=["status-missing"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="decision reasons must be strings"):
        PublicationDecision(eligible=False, reasons=(1,))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="decision reasons must be unique"):
        PublicationDecision(
            eligible=False,
            reasons=("status-missing", "status-missing"),
        )
    with pytest.raises(ValueError, match="unknown reason"):
        PublicationDecision(eligible=False, reasons=("unknown",))
    with pytest.raises(ValueError, match="canonical order"):
        PublicationDecision(
            eligible=False,
            reasons=("verified-not-true", "status-missing"),
        )


@pytest.mark.parametrize(
    "eligible, reasons",
    [
        (True, ("status-missing",)),
        (False, ()),
    ],
)
def test_decision_eligibility_must_match_reasons(
    eligible: bool,
    reasons: tuple[str, ...],
):
    with pytest.raises(ValueError, match="eligible does not match decision reasons"):
        PublicationDecision(eligible=eligible, reasons=reasons)
