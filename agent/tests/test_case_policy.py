import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_policy_names_owner_and_refuses_public_resolution_sla():
    from cases.policy import load_case_policy
    policy = load_case_policy()
    assert policy.revision == "correction-pilot-v1"
    assert policy.owner_ref_env == "CASE_SERVICE_OWNER_REF"
    assert policy.public_resolution_sla_enabled is False
    assert policy.receipt_target_seconds == 5
    assert policy.triage_target_seconds == 86_400
    assert policy.update_target_seconds == 259_200


def test_correction_outcomes_have_no_generic_terminal_state():
    from cases.domain import CorrectionOutcome
    assert {item.value for item in CorrectionOutcome} == {
        "corrected", "confirmed_current", "insufficient_evidence",
        "out_of_scope", "duplicate_linked", "unable_to_verify",
        "withdrawn_by_requester",
    }


def test_production_case_flags_require_postgresql_owner_and_encryption():
    from config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT='production', DATABASE_URL='sqlite:///case.db', CASE_KERNEL_ENABLED=True)
