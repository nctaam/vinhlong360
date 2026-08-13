from cases.domain import CaseActivity, CasePhase, DispositionFamily, ServiceKind


def test_only_correction_is_the_pilot_service_vocabulary():
    assert ServiceKind.CORRECTION.value == 'correction'


def test_case_state_fabric_uses_orthogonal_vocabulary():
    assert {item.value for item in CasePhase} == {'intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed'}
    assert {item.value for item in CaseActivity} == {'active', 'waiting_on_requester', 'waiting_on_external'}
    assert {item.value for item in DispositionFamily} == {'undetermined', 'action_taken', 'no_action', 'transferred', 'withdrawn', 'duplicate'}
