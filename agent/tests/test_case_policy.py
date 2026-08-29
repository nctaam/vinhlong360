import sys
from pathlib import Path

import pytest
from dataclasses import fields

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


def test_policy_requires_complete_exact_schema_and_independent_high_risk_review(tmp_path):
    from cases.policy import load_case_policy
    import json
    source = Path(__file__).parents[2] / 'config' / 'case-service-policy.json'
    policy = json.loads(source.read_text())
    policy.pop('retention')
    target = tmp_path / 'policy.json'
    target.write_text(json.dumps(policy))
    with pytest.raises(ValueError, match='exact'):
        load_case_policy(target)
    policy = json.loads(source.read_text())
    policy['risk_registry']['R2']['independent_review'] = False
    target.write_text(json.dumps(policy))
    with pytest.raises(ValueError, match='independent'):
        load_case_policy(target)


def test_policy_keeps_operational_structures_and_validates_assisted_coverage():
    from cases.policy import load_case_policy
    policy = load_case_policy()
    assert policy.maker_checker_rules['R2'] is True
    assert policy.assisted_coverage['timezone'] == 'Asia/Ho_Chi_Minh'


@pytest.mark.parametrize('field,value', [
    ('resolution_target_seconds_by_risk', {'R0': 1, 'R1': 1, 'R2': 1, 'R3': 1, 'RX': 1}),
    ('risk_registry', {'R0': {}, 'R1': {}, 'R2': {'independent_review': True}, 'R3': {'independent_review': True}, 'RX': {}}),
    ('maker_checker_rules', {'R2': True, 'R3': True, 'RX': False}),
    ('retention', {'case_days': 1, 'receipt_days': 1, 'extra': 1}),
    ('notification_channel', {'name': 'outbox'}),
    ('assisted_coverage', {'timezone': 'x', 'weekdays': [], 'hours': 'x', 'duty_roster': 'x', 'fallback_copy': 'x'}),
    # Đắp thêm nhánh reject của coverage (lát 9 R20.8): timezone trắng,
    # weekday sai kiểu/trắng, hours trắng.
    ('assisted_coverage', {'timezone': '   ', 'weekdays': ['mon'], 'hours': 'x', 'duty_roster': 'x', 'fallback_copy': 'x'}),
    ('assisted_coverage', {'timezone': 'x', 'weekdays': ['mon', 2], 'hours': 'x', 'duty_roster': 'x', 'fallback_copy': 'x'}),
    ('assisted_coverage', {'timezone': 'x', 'weekdays': ['  '], 'hours': 'x', 'duty_roster': 'x', 'fallback_copy': 'x'}),
    ('assisted_coverage', {'timezone': 'x', 'weekdays': ['mon'], 'hours': '', 'duty_roster': 'x', 'fallback_copy': 'x'}),
])
def test_policy_rejects_malformed_nested_structure(tmp_path, field, value):
    from cases.policy import load_case_policy
    import json
    source = Path(__file__).parents[2] / 'config' / 'case-service-policy.json'
    data = json.loads(source.read_text())
    data[field] = value
    target = tmp_path / 'policy.json'
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError):
            load_case_policy(target)


def test_policy_rejects_non_boolean_low_risk_independence(tmp_path):
    from cases.policy import load_case_policy
    import json
    source = Path(__file__).parents[2] / 'config' / 'case-service-policy.json'
    data = json.loads(source.read_text())
    data['risk_registry']['R0'] = {'independent_review': 'yes'}
    target = tmp_path / 'policy.json'
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='boolean'):
        load_case_policy(target)


@pytest.mark.parametrize('owner,key', [('x', 'sufficient-key-material'), ('person:alice', '   ')])
def test_enabled_flags_reject_inadequate_owner_or_encryption(owner, key):
    from config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL='postgresql://db', CASE_KERNEL_ENABLED=True,
                 CASE_SERVICE_OWNER_REF=owner, CASE_KERNEL_ENCRYPTION_KEY=key)


def test_case_dataclasses_expose_locked_projection_contract():
    from cases.domain import ActorContext, CaseProblem, CaseSnapshot, Channel, PublicCaseStatus
    assert ActorContext.__annotations__['channel'] is Channel
    assert {field.name for field in fields(PublicCaseStatus)} == {
        'public_reference', 'received_at', 'current_step', 'waiting_for', 'next_action',
        'next_update_at', 'promise_health', 'item_decisions', 'item_publication_states', 'review_path',
    }
    assert 'current_revision' in {field.name for field in fields(CaseSnapshot)}
    assert getattr(CaseProblem.__dataclass_params__, 'frozen')


@pytest.mark.parametrize('flag', ['CASE_KERNEL_ENABLED', 'CORRECTION_INTAKE_ENABLED', 'CORRECTION_ADMIN_ENABLED', 'CORRECTION_ASSISTED_ENABLED', 'CORRECTION_PUBLICATION_ENABLED'])
def test_each_enabled_case_flag_requires_postgresql(flag):
    from config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match='case_postgresql_required'):
        Settings(DATABASE_URL='sqlite:///case.db', **{flag: True})


def test_valid_nonproduction_case_activation_has_structural_credentials():
    from config import Settings
    configured = Settings(DATABASE_URL='postgresql://db', CASE_KERNEL_ENABLED=True,
                          CASE_SERVICE_OWNER_REF='person:alice',
                          CASE_KERNEL_ENCRYPTION_KEY='sufficient-key-material')
    assert configured.CASE_KERNEL_ENABLED
