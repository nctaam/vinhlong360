from __future__ import annotations

import copy
import json
import subprocess
import sys
import unicodedata
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

import index_policy
import launch_evidence
from ai_disclosure import load_ai_disclosure
from index_policy import (
    IndexPolicyDecision,
    decide_entity,
    is_publicly_eligible,
    public_eligibility_reasons,
)
from launch_evidence import (
    INDEX_POLICY_REVISION,
    PolicyEvidence,
    build_policy_fingerprint,
    current_policy_evidence,
)
from route_manifest import load_route_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "launch-policy-fingerprint.json"
)
EVIDENCE = PolicyEvidence(
    policy_fingerprint="a" * 64,
    route_manifest_revision="launch-indexing-policy-v1",
    backend_policy_revision=INDEX_POLICY_REVISION,
)


class _NonStringEntityType:
    def __eq__(self, other: object) -> bool:
        raise AssertionError("non-string entity types must not be compared")


@pytest.fixture
def fingerprint_fixture() -> dict[str, object]:
    return json.loads(FINGERPRINT_FIXTURE.read_text(encoding="utf-8"))


def _words(count: int, word: str = "word") -> str:
    return " ".join([word] * count)


def _public_entity(**overrides: object) -> dict[str, object]:
    entity: dict[str, object] = {
        "id": "entity",
        "type": "attraction",
        "status": "published",
        "verified": True,
        "summary": _words(130),
        "description": "",
    }
    entity.update(overrides)
    return entity


def _public_ward(**overrides: object) -> dict[str, object]:
    ward: dict[str, object] = {
        "id": "ward",
        "type": "place",
        "status": "published",
        "verified": True,
        "summary": _words(60, "phường"),
    }
    ward.update(overrides)
    return ward


def test_reviewed_non_place_entity_types_are_exact():
    from public_entity_types import REVIEWED_NON_PLACE_ENTITY_TYPES

    assert REVIEWED_NON_PLACE_ENTITY_TYPES == frozenset(
        {
            "accommodation",
            "attraction",
            "cafe",
            "craft_village",
            "dish",
            "drink",
            "event",
            "experience",
            "facility",
            "history",
            "nature",
            "organization",
            "person",
            "product",
            "restaurant",
        }
    )


def test_entity_requires_public_eligibility_and_exactly_130_words():
    entity = _public_entity(summary=_words(129))
    decision = decide_entity(entity, EVIDENCE)

    assert decision.indexable is False
    assert decision.reasons == ("description-below-130-words",)

    entity["summary"] = _words(130)
    decision = decide_entity(entity, EVIDENCE)

    assert decision.indexable is True
    assert decision.reasons == ()


def test_description_casefold_duplicate_is_counted_once():
    summary = _words(65, "Đồng")
    entity = _public_entity(summary=summary, description=summary.swapcase())

    decision = decide_entity(entity, EVIDENCE)

    assert decision.indexable is False
    assert decision.reasons == ("description-below-130-words",)


def test_nfc_nfd_description_duplicate_is_counted_once():
    summary = _words(65, "café")
    description = unicodedata.normalize("NFD", summary)
    entity = _public_entity(summary=summary, description=description)

    decision = decide_entity(entity, EVIDENCE)

    assert decision.reasons == ("description-below-130-words",)


def test_distinct_summary_and_description_are_counted_together():
    entity = _public_entity(
        summary=_words(65, "vườn"),
        description=_words(65, "dừa"),
    )

    assert decide_entity(entity, EVIDENCE).indexable is True


def test_unicode_words_count_at_the_same_129_130_boundary():
    entity = _public_entity(summary=_words(129, "VĩnhLong"))
    assert decide_entity(entity, EVIDENCE).indexable is False

    entity["summary"] = f"{entity['summary']} miệtvườn"
    assert decide_entity(entity, EVIDENCE).indexable is True


@pytest.mark.parametrize("token", ["___", "123", "--"])
def test_non_letter_tokens_receive_no_word_credit(token: str):
    entity = _public_entity(summary=f"{_words(129)} {token}")

    assert decide_entity(entity, EVIDENCE).reasons == (
        "description-below-130-words",
    )


def test_missing_entity_type_uses_canonical_reason():
    entity = _public_entity()
    del entity["type"]

    assert decide_entity(entity, EVIDENCE).reasons == ("entity-type-missing",)


@pytest.mark.parametrize(
    "entity_type, expected_reason",
    [
        (None, "entity-type-missing"),
        ("", "entity-type-missing"),
        ("itinerary", "entity-type-not-allowlisted"),
        ("unknown", "entity-type-not-allowlisted"),
        (1, "entity-type-not-allowlisted"),
        (True, "entity-type-not-allowlisted"),
    ],
)
def test_entity_type_must_be_reviewed_and_allowlisted(
    entity_type: object,
    expected_reason: str,
):
    entity = _public_entity(type=entity_type)

    assert decide_entity(entity, EVIDENCE).reasons == (expected_reason,)


def test_non_string_entity_type_is_rejected_without_string_comparison():
    entity = _public_entity(type=_NonStringEntityType())

    assert decide_entity(entity, EVIDENCE).reasons == (
        "entity-type-not-allowlisted",
    )


@pytest.mark.parametrize(
    "entity, expected_reason",
    [
        ({}, "public-status-missing"),
        ({"status": "published", "verified": None}, "public-verification-missing"),
        ({"status": "provisional", "verified": True}, "public-status-not-allowlisted"),
        ({"status": "private", "verified": True}, "public-status-not-allowlisted"),
        ({"status": "draft", "verified": True}, "public-status-not-allowlisted"),
        ({"status": "unpublished", "verified": True}, "public-status-not-allowlisted"),
        ({"status": "published", "verified": False}, "public-explicitly-unverified"),
        (
            {"status": "published", "verified": True, "is_private": True},
            "public-private-content",
        ),
        (
            {"status": "published", "verified": True, "visibility": "private"},
            "public-private-content",
        ),
        (
            {"status": "published", "verified": True, "is_public": False},
            "public-unpublished-content",
        ),
        (
            {"status": "published", "verified": True, "published": False},
            "public-unpublished-content",
        ),
    ],
)
def test_missing_private_draft_unpublished_and_unverified_entities_are_ineligible(
    entity: dict[str, object],
    expected_reason: str,
):
    entity.update(type="attraction", summary=_words(130), description="")

    decision = decide_entity(entity, EVIDENCE)

    assert decision.indexable is False
    assert expected_reason in decision.reasons
    assert decision.reasons[0].startswith("public-")


@pytest.mark.parametrize(
    "field, value, expected_reason",
    [
        ("status", True, "public-status-not-allowlisted"),
        ("verified", 1.0, "public-explicitly-unverified"),
        ("verified", "true", "public-explicitly-unverified"),
        ("is_private", 1, "public-private-content"),
        ("is_public", 0, "public-unpublished-content"),
        ("published", 1, "public-unpublished-content"),
        ("visibility", 1, "public-private-content"),
    ],
)
def test_public_flags_do_not_accept_bool_int_or_equality_aliases(
    field: str,
    value: object,
    expected_reason: str,
):
    entity = _public_entity(**{field: value})

    assert public_eligibility_reasons(entity) == (expected_reason,)
    assert is_publicly_eligible(entity) is False


def test_legacy_integer_one_verification_is_explicitly_supported_without_float_alias():
    assert is_publicly_eligible(_public_entity(verified=1)) is True
    assert is_publicly_eligible(_public_entity(verified=1.0)) is False


def test_entity_reason_order_is_stable_unique_and_precedes_public_and_quality():
    entity = {
        "type": "unknown",
        "status": "draft",
        "verified": False,
        "is_private": True,
        "visibility": "private",
        "is_public": False,
        "published": False,
        "summary": _words(10),
    }

    decision = decide_entity(entity, EVIDENCE)

    assert decision.reasons == (
        "entity-type-not-allowlisted",
        "public-status-not-allowlisted",
        "public-explicitly-unverified",
        "public-private-content",
        "public-unpublished-content",
        "description-below-130-words",
    )


def test_ward_quality_boundary_requires_two_public_children_or_60_summary_words():
    ward = _public_ward(summary=_words(59, "phường"))

    one_child = index_policy.decide_ward(
        ward, public_child_count=1, evidence=EVIDENCE
    )
    two_children = index_policy.decide_ward(
        ward, public_child_count=2, evidence=EVIDENCE
    )
    rich_summary = index_policy.decide_ward(
        _public_ward(summary=_words(60, "phường")),
        public_child_count=0,
        evidence=EVIDENCE,
    )

    assert one_child.indexable is False
    assert one_child.reasons == ("ward-below-child-and-summary-threshold",)
    assert two_children.indexable is True
    assert two_children.reasons == ()
    assert rich_summary.indexable is True
    assert rich_summary.reasons == ()


def test_ward_summary_uses_unicode_letter_tokens_and_nfc_normalization():
    accented = unicodedata.normalize("NFD", _words(60, "café"))
    numeric_padding = f"{_words(59, 'xã')} 123 ___ --"

    assert index_policy.decide_ward(
        _public_ward(summary=accented), public_child_count=0, evidence=EVIDENCE
    ).indexable is True
    assert index_policy.decide_ward(
        _public_ward(summary=numeric_padding),
        public_child_count=0,
        evidence=EVIDENCE,
    ).reasons == ("ward-below-child-and-summary-threshold",)


@pytest.mark.parametrize(
    "overrides, expected_reason",
    [
        ({"status": None}, "public-status-missing"),
        ({"status": "draft"}, "public-status-not-allowlisted"),
        ({"status": "unpublished"}, "public-status-not-allowlisted"),
        ({"verified": None}, "public-verification-missing"),
        ({"verified": False}, "public-explicitly-unverified"),
        ({"published": False}, "public-unpublished-content"),
    ],
)
def test_ward_public_eligibility_fails_closed_regardless_of_quality(
    overrides: dict[str, object], expected_reason: str
):
    ward = _public_ward(**overrides)

    decision = index_policy.decide_ward(
        ward, public_child_count=2, evidence=EVIDENCE
    )

    assert decision.indexable is False
    assert decision.reasons == (expected_reason,)


@pytest.mark.parametrize(
    "missing_field, expected_reason",
    [
        ("status", "public-status-missing"),
        ("verified", "public-verification-missing"),
    ],
)
def test_ward_missing_public_fields_fail_closed(
    missing_field: str, expected_reason: str
):
    ward = _public_ward()
    del ward[missing_field]

    decision = index_policy.decide_ward(
        ward, public_child_count=2, evidence=EVIDENCE
    )

    assert decision.reasons == (expected_reason,)


def test_thin_ineligible_ward_orders_public_reasons_before_quality_reason():
    ward = _public_ward(
        status="draft", verified=False, summary=_words(59, "xã")
    )

    decision = index_policy.decide_ward(
        ward, public_child_count=1, evidence=EVIDENCE
    )

    assert decision.reasons == (
        "public-status-not-allowlisted",
        "public-explicitly-unverified",
        "ward-below-child-and-summary-threshold",
    )


def test_decide_ward_does_not_mutate_or_alias_the_caller():
    with pytest.raises(TypeError, match="entity must be a mapping"):
        index_policy.decide_ward(  # type: ignore[arg-type]
            [], public_child_count=0, evidence=EVIDENCE
        )

    ward = _public_ward(summary=_words(59, "xã"))
    original = copy.deepcopy(ward)

    decision = index_policy.decide_ward(
        MappingProxyType(ward), public_child_count=1, evidence=EVIDENCE
    )

    assert ward == original
    ward["summary"] = _words(60, "xã")
    assert decision.reasons == ("ward-below-child-and-summary-threshold",)


@pytest.mark.parametrize("public_child_count", [-1, True, 1.0, "2"])
def test_decide_ward_requires_a_nonnegative_exact_integer_child_count(
    public_child_count: object,
):
    with pytest.raises((TypeError, ValueError)):
        index_policy.decide_ward(
            _public_ward(),
            public_child_count=public_child_count,  # type: ignore[arg-type]
            evidence=EVIDENCE,
        )


def test_itinerary_and_shared_plan_are_fixed_noindex_decisions():
    itinerary = index_policy.decide_itinerary(
        shared_plan=False, evidence=EVIDENCE
    )
    shared_plan = index_policy.decide_itinerary(
        shared_plan=True, evidence=EVIDENCE
    )

    assert itinerary == IndexPolicyDecision(
        kind="itinerary",
        indexable=False,
        reasons=("itinerary-fixed-noindex",),
        policy_fingerprint="a" * 64,
        policy_revision=INDEX_POLICY_REVISION,
    )
    assert shared_plan == IndexPolicyDecision(
        kind="itinerary",
        indexable=False,
        reasons=("shared-plan-fixed-noindex",),
        policy_fingerprint="a" * 64,
        policy_revision=INDEX_POLICY_REVISION,
    )


@pytest.mark.parametrize("shared_plan", [0, 1, None, "true"])
def test_decide_itinerary_requires_an_exact_boolean(shared_plan: object):
    with pytest.raises(TypeError, match="shared_plan must be a boolean"):
        index_policy.decide_itinerary(
            shared_plan=shared_plan,  # type: ignore[arg-type]
            evidence=EVIDENCE,
        )


def test_decide_itinerary_requires_keyword_only_arguments():
    with pytest.raises(TypeError):
        index_policy.decide_itinerary(False, EVIDENCE)  # type: ignore[misc]


def test_new_policy_entry_points_require_exact_policy_evidence():
    with pytest.raises(TypeError, match="evidence must be PolicyEvidence"):
        index_policy.decide_ward(
            _public_ward(), public_child_count=0, evidence=object()  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="evidence must be PolicyEvidence"):
        index_policy.decide_itinerary(
            shared_plan=False, evidence=object()  # type: ignore[arg-type]
        )


def test_decision_validation_uses_exact_per_kind_reason_vocabularies():
    valid_ward = IndexPolicyDecision(
        kind="ward",
        indexable=False,
        reasons=("ward-below-child-and-summary-threshold",),
        policy_fingerprint="a" * 64,
        policy_revision=INDEX_POLICY_REVISION,
    )
    assert valid_ward.kind == "ward"

    invalid_kind_reason_pairs = [
        ("entity", "ward-below-child-and-summary-threshold"),
        ("ward", "description-below-130-words"),
        ("ward", "itinerary-fixed-noindex"),
        ("itinerary", "public-status-missing"),
        ("itinerary", "ward-below-child-and-summary-threshold"),
    ]
    for kind, reason in invalid_kind_reason_pairs:
        with pytest.raises(ValueError, match="unknown reason"):
            IndexPolicyDecision(
                kind=kind,
                indexable=False,
                reasons=(reason,),
                policy_fingerprint="a" * 64,
                policy_revision=INDEX_POLICY_REVISION,
            )


def test_decision_validation_rejects_unknown_kind_and_noncanonical_reasons():
    with pytest.raises(ValueError, match="entity, ward, or itinerary"):
        IndexPolicyDecision(
            kind="place",
            indexable=True,
            reasons=(),
            policy_fingerprint="a" * 64,
            policy_revision=INDEX_POLICY_REVISION,
        )
    with pytest.raises(ValueError, match="canonical order"):
        IndexPolicyDecision(
            kind="ward",
            indexable=False,
            reasons=(
                "ward-below-child-and-summary-threshold",
                "public-status-missing",
            ),
            policy_fingerprint="a" * 64,
            policy_revision=INDEX_POLICY_REVISION,
        )
    with pytest.raises(ValueError, match="unique"):
        IndexPolicyDecision(
            kind="itinerary",
            indexable=False,
            reasons=("itinerary-fixed-noindex", "itinerary-fixed-noindex"),
            policy_fingerprint="a" * 64,
            policy_revision=INDEX_POLICY_REVISION,
        )


@pytest.mark.parametrize(
    "indexable, reasons",
    [
        (True, ()),
        (
            False,
            ("itinerary-fixed-noindex", "shared-plan-fixed-noindex"),
        ),
    ],
)
def test_itinerary_decision_requires_exactly_one_fixed_noindex_reason(
    indexable: bool, reasons: tuple[str, ...]
):
    with pytest.raises(ValueError, match="exactly one fixed noindex reason"):
        IndexPolicyDecision(
            kind="itinerary",
            indexable=indexable,
            reasons=reasons,
            policy_fingerprint="a" * 64,
            policy_revision=INDEX_POLICY_REVISION,
        )


@pytest.mark.parametrize(
    "images",
    [
        ["/img/ai-1.webp", "/img/ai-2.webp"],
        ["https://example.com/entity.jpg"],
        [{"kind": "placeholder", "url": "/img/placeholder.webp"}],
        [{"kind": "ugc", "url": "https://example.com/review.jpg"}],
        [{"url": object()}],
        "https://example.com/not-a-list.jpg",
    ],
)
def test_all_entity_media_shapes_receive_zero_quality_credit(images: object):
    entity = _public_entity(summary=_words(100), images=images)

    assert decide_entity(entity, EVIDENCE).indexable is False


def test_decide_entity_requires_a_mapping_and_does_not_mutate_or_alias_the_caller():
    with pytest.raises(TypeError, match="entity must be a mapping"):
        decide_entity([], EVIDENCE)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-place"):
        decide_entity(_public_entity(type="place"), EVIDENCE)

    entity = _public_entity(summary=_words(10))
    original = copy.deepcopy(entity)
    decision = decide_entity(MappingProxyType(entity), EVIDENCE)

    assert entity == original
    entity["status"] = "published"
    entity["summary"] = _words(130)
    assert decision.reasons == ("description-below-130-words",)


def test_decision_is_frozen_owned_and_runtime_valid():
    decision = decide_entity(_public_entity(), EVIDENCE)

    assert decision == IndexPolicyDecision(
        kind="entity",
        indexable=True,
        reasons=(),
        policy_fingerprint="a" * 64,
        policy_revision=INDEX_POLICY_REVISION,
    )
    with pytest.raises(FrozenInstanceError):
        decision.indexable = False  # type: ignore[misc]
    with pytest.raises(TypeError, match="indexable must be a boolean"):
        IndexPolicyDecision(
            kind="entity",
            indexable=1,  # type: ignore[arg-type]
            reasons=(),
            policy_fingerprint="a" * 64,
            policy_revision=INDEX_POLICY_REVISION,
        )
    with pytest.raises(TypeError, match="reasons must be a tuple"):
        IndexPolicyDecision(
            kind="entity",
            indexable=False,
            reasons=["description-below-130-words"],  # type: ignore[arg-type]
            policy_fingerprint="a" * 64,
            policy_revision=INDEX_POLICY_REVISION,
        )


def test_policy_evidence_is_frozen_and_rejects_invalid_runtime_values():
    with pytest.raises(FrozenInstanceError):
        EVIDENCE.policy_fingerprint = "b" * 64  # type: ignore[misc]

    invalid_values = [
        {"policy_fingerprint": "A" * 64},
        {"policy_fingerprint": "a" * 63},
        {"policy_fingerprint": True},
        {"route_manifest_revision": "launch-indexing-policy-v0"},
        {"backend_policy_revision": "index-policy-v0"},
    ]
    defaults: dict[str, object] = {
        "policy_fingerprint": "a" * 64,
        "route_manifest_revision": "launch-indexing-policy-v1",
        "backend_policy_revision": INDEX_POLICY_REVISION,
    }
    for replacement in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            PolicyEvidence(**(defaults | replacement))  # type: ignore[arg-type]


def test_fingerprint_hashes_exact_fixture_payload(
    fingerprint_fixture: dict[str, object],
):
    inputs = fingerprint_fixture["inputs"]
    assert isinstance(inputs, dict)

    assert build_policy_fingerprint(**inputs) == fingerprint_fixture["expected_sha256"]
    assert fingerprint_fixture["semantic_revisions"] == {
        "index_policy": launch_evidence.INDEX_POLICY_REVISION,
        "response_matrix": launch_evidence.RESPONSE_MATRIX_REVISION,
        "cache_isolation": launch_evidence.CACHE_ISOLATION_REVISION,
        "sitemap_protocol": launch_evidence.SITEMAP_PROTOCOL_REVISION,
    }


def test_fingerprint_is_deterministic_and_every_artifact_field_changes_it(
    fingerprint_fixture: dict[str, object],
):
    inputs = fingerprint_fixture["inputs"]
    assert isinstance(inputs, dict)
    baseline = build_policy_fingerprint(**inputs)
    reversed_order = dict(reversed(list(inputs.items())))
    assert build_policy_fingerprint(**reversed_order) == baseline

    replacements = {
        "route_revision": "launch-indexing-policy-v2",
        "route_digest": "1" * 63 + "2",
        "disclosure_revision": "ai-disclosure-v2",
        "disclosure_digest": "2" * 63 + "3",
    }
    for field, replacement in replacements.items():
        changed = dict(inputs)
        changed[field] = replacement
        assert build_policy_fingerprint(**changed) != baseline


def test_fingerprint_normalizes_equivalent_revision_strings(
    fingerprint_fixture: dict[str, object],
):
    inputs = fingerprint_fixture["inputs"]
    assert isinstance(inputs, dict)
    nfc_revision = "révision-v1"
    nfd_revision = unicodedata.normalize("NFD", nfc_revision)

    nfc_inputs = dict(inputs, route_revision=nfc_revision)
    nfd_inputs = dict(inputs, route_revision=nfd_revision)

    assert build_policy_fingerprint(**nfc_inputs) == build_policy_fingerprint(
        **nfd_inputs
    )


@pytest.mark.parametrize(
    "constant",
    [
        "INDEX_POLICY_REVISION",
        "RESPONSE_MATRIX_REVISION",
        "CACHE_ISOLATION_REVISION",
        "SITEMAP_PROTOCOL_REVISION",
    ],
)
def test_every_semantic_revision_changes_the_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    fingerprint_fixture: dict[str, object],
    constant: str,
):
    inputs = fingerprint_fixture["inputs"]
    assert isinstance(inputs, dict)
    baseline = build_policy_fingerprint(**inputs)
    monkeypatch.setattr(
        launch_evidence, constant, f"{getattr(launch_evidence, constant)}-changed"
    )

    assert build_policy_fingerprint(**inputs) != baseline


@pytest.mark.parametrize(
    "field, value",
    [
        ("route_revision", True),
        ("route_revision", ""),
        ("route_digest", "a" * 63),
        ("route_digest", "A" * 64),
        ("route_digest", 1),
        ("disclosure_revision", None),
        ("disclosure_digest", "not-a-digest"),
    ],
)
def test_fingerprint_rejects_invalid_revision_and_digest_types(
    fingerprint_fixture: dict[str, object],
    field: str,
    value: object,
):
    inputs = fingerprint_fixture["inputs"]
    assert isinstance(inputs, dict)
    candidate = dict(inputs)
    candidate[field] = value

    with pytest.raises((TypeError, ValueError)):
        build_policy_fingerprint(**candidate)  # type: ignore[arg-type]


def test_current_policy_evidence_matches_loaded_artifacts():
    route = load_route_manifest()
    disclosure = load_ai_disclosure()
    evidence = current_policy_evidence()

    assert evidence.route_manifest_revision == route.revision
    assert evidence.backend_policy_revision == INDEX_POLICY_REVISION
    assert evidence.policy_fingerprint == build_policy_fingerprint(
        route_revision=route.revision,
        route_digest=route.artifact.sha256,
        disclosure_revision=disclosure.revision,
        disclosure_digest=disclosure.artifact.sha256,
    )


def test_policy_modules_support_flat_and_repository_package_imports():
    scripts = (
        (
            f"import sys; sys.path.insert(0, {str(REPO_ROOT / 'agent')!r}); "
            "import launch_evidence, index_policy; "
            "assert index_policy.decide_entity"
        ),
        (
            f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); "
            "import agent.launch_evidence, agent.index_policy; "
            "assert agent.index_policy.decide_entity"
        ),
    )
    for script in scripts:
        result = subprocess.run(
            [sys.executable, "-I", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
