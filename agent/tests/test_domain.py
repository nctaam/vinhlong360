from cases import Channel, ItemDecision, ItemPublication
from cases.domain import CaseActivity, CasePhase, DispositionFamily, ServiceKind, PublicCaseStatus


def test_only_correction_is_the_pilot_service_vocabulary():
    assert ServiceKind.CORRECTION.value == 'correction'


def test_case_state_fabric_uses_orthogonal_vocabulary():
    assert {item.value for item in CasePhase} == {'intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed'}
    assert {item.value for item in CaseActivity} == {'active', 'waiting_on_requester', 'waiting_on_external'}
    assert {item.value for item in DispositionFamily} == {'undetermined', 'action_taken', 'no_action', 'transferred', 'withdrawn', 'duplicate'}


def test_channel_and_projection_records_are_exported_and_typed():
    assert Channel.WEB.value == 'web'
    assert PublicCaseStatus.__annotations__['item_decisions'] == tuple[ItemDecision, ...]
    assert PublicCaseStatus.__annotations__['item_publication_states'] == tuple[ItemPublication, ...]
