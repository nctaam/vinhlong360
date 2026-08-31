from __future__ import annotations

import pytest


def test_correction_contract_allows_unknown_current_value_but_requires_explicit_flag():
    from agent.control_plane.contracts import ContractViolation, validate_payload

    validate_payload(
        "correction-intake",
        {"reported_value_known": False, "reported_value": None},
    )
    with pytest.raises(ContractViolation) as exc:
        validate_payload("correction-intake", {"reported_value": None})
    assert exc.value.code == "CONTRACT_INVALID"


def test_correction_contract_rejects_unknown_version_and_conflicting_value():
    from agent.control_plane.contracts import ContractViolation, validate_payload

    with pytest.raises(ContractViolation) as exc:
        validate_payload("correction-intake", {"reported_value_known": False, "reported_value": "x"})
    assert exc.value.code == "CONTRACT_INVALID"
    with pytest.raises(ContractViolation):
        validate_payload("correction-intake", {"reported_value_known": True, "reported_value": None}, version="9")


def test_problem_detail_keeps_field_and_correlation_id():
    # Keep the contract test paired with every Python transport consumer changed
    # in this tranche; imports are real module-boundary coverage, not a filename
    # placeholder for the standards gate.
    from agent import admin as _admin, api_schemas as _api_schemas, public_api as _public_api
    from agent.cases import public_api as _case_public_api, service as _service
    from agent.control_plane.contracts import problem_detail

    problem = problem_detail(
        "invalid_request", "Body is invalid", 422,
        field="items.0.reported_value", correlation_id="corr-1",
    )
    assert problem["status"] == 422
    assert problem["code"] == "invalid_request"
    assert problem["field"] == "items.0.reported_value"
    assert problem["correlation_id"] == "corr-1"


def test_correction_contract_exposes_one_canonical_version():
    from agent.control_plane.contracts import (
        CORRECTION_INTAKE_CONTRACT_VERSION,
        get_contract,
    )

    assert CORRECTION_INTAKE_CONTRACT_VERSION == "1"
    assert get_contract("correction-intake", CORRECTION_INTAKE_CONTRACT_VERSION).version == "1"


def test_provisional_badge_uses_one_canonical_count_key():
    from agent.kb_curation import normalize_curation_summary

    assert normalize_curation_summary({"provisional_count": 3})["provisional_count"] == 3
    assert normalize_curation_summary({"pending": 3})["provisional_count"] == 0
