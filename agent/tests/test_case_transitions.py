import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases.domain import (
    ActorContext, CaseActivity, CasePhase, CaseSnapshot, Channel,
    CorrectionItem, CorrectionOutcome, DispositionFamily, EvidenceLevel,
    PublicationState, RiskClass, ServiceKind,
)
from cases.policy import load_case_policy

NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def case(**changes):
    snapshot = CaseSnapshot(
        case_id="case-1", service_kind=ServiceKind.CORRECTION, category="listing",
        phase=CasePhase.FULFILLMENT, activity=CaseActivity.ACTIVE,
        disposition_family=DispositionFamily.ACTION_TAKEN, domain_outcome=None,
        severity=None, reporter_privacy="anonymous", owner_ref="owner-1",
        current_revision=4, promise_policy_ref="correction-pilot-v1",
        created_at=NOW - timedelta(days=1), updated_at=NOW - timedelta(hours=1),
        closed_at=None,
    )
    return replace(snapshot, **changes)


def command(**changes):
    from cases.transitions import CaseTransitionCommand

    default = CaseTransitionCommand(
        phase=CasePhase.FULFILLMENT, activity=CaseActivity.ACTIVE,
        disposition_family=DispositionFamily.UNDETERMINED, domain_outcome=None,
        actor=ActorContext("operator-1", Channel.WEB, frozenset(), "corr-1"),
        reason_code="investigate", expected_revision=4,
    )
    return replace(default, **changes)


def test_closed_case_never_reopens():
    from cases.transitions import TransitionRejected, transition_case

    closed = case(phase=CasePhase.CLOSED, closed_at=NOW)
    with pytest.raises(TransitionRejected, match="closed_case_immutable"):
        transition_case(closed, command(phase=CasePhase.INVESTIGATION), load_case_policy(), now=NOW)


def test_waiting_on_requester_needs_concrete_safe_request_evidence_and_review_time():
    from cases.transitions import TransitionRejected, transition_case

    waiting = command(activity=CaseActivity.WAITING_ON_REQUESTER)
    with pytest.raises(TransitionRejected, match="waiting_request_incomplete"):
        transition_case(case(), waiting, load_case_policy(), now=NOW)
    result = transition_case(
        case(),
        replace(
            waiting, requester_request="Please confirm the listed phone number.",
            safe_message="Please confirm the listed phone number.",
            waiting_on_ref="requester-1", waiting_evidence_ref="interaction-1",
            next_review_at=NOW + timedelta(days=1),
        ),
        load_case_policy(), now=NOW,
    )
    assert result.snapshot.activity is CaseActivity.WAITING_ON_REQUESTER
    assert result.snapshot.current_revision == 5


def test_corrected_close_requires_every_accepted_public_change_to_be_verified():
    from cases.transitions import TransitionRejected, transition_case

    item = CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2, accepted=True,
                          requires_public_change=True, publication_state=PublicationState.APPLIED)
    close = command(
        phase=CasePhase.CLOSED, domain_outcome=CorrectionOutcome.CORRECTED,
        disposition_family=DispositionFamily.ACTION_TAKEN, reason_code="public_change_verified",
    )
    with pytest.raises(TransitionRejected, match="publication_not_verified"):
        transition_case(case(), close, load_case_policy(), now=NOW, correction_items=(item,))
    result = transition_case(
        case(), close, load_case_policy(), now=NOW,
        correction_items=(replace(item, publication_state=PublicationState.VERIFIED),),
    )
    assert result.snapshot.phase is CasePhase.CLOSED
    assert result.snapshot.closed_at == NOW


def test_corrected_close_requires_fulfillment_phase():
    from cases.transitions import TransitionRejected, transition_case

    item = CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2, accepted=True,
                          requires_public_change=True, publication_state=PublicationState.VERIFIED)
    close = command(
        phase=CasePhase.CLOSED, domain_outcome=CorrectionOutcome.CORRECTED,
        disposition_family=DispositionFamily.ACTION_TAKEN, reason_code="public_change_verified",
    )
    with pytest.raises(TransitionRejected, match="corrected_requires_fulfillment"):
        transition_case(case(phase=CasePhase.DECISION), close, load_case_policy(), now=NOW,
                        correction_items=(item,))


def test_transition_audit_carries_actor_reason_policy_and_correlation():
    from cases.transitions import transition_case

    result = transition_case(case(), command(), load_case_policy(), now=NOW)
    assert result.transition.actor_ref == "operator-1"
    assert result.transition.reason_code == "investigate"
    assert result.transition.policy_revision == "correction-pilot-v1"
    assert result.transition.correlation_id == "corr-1"


def test_requester_waiting_persists_resumption_metadata_in_snapshot_and_transition():
    from cases.transitions import transition_case

    result = transition_case(
        case(),
        command(
            activity=CaseActivity.WAITING_ON_REQUESTER,
            requester_request="Confirm phone.", safe_message="Confirm phone.",
            waiting_on_ref="requester-1", waiting_evidence_ref="interaction-1",
            next_review_at=NOW + timedelta(days=1),
        ),
        load_case_policy(), now=NOW,
    )
    assert result.snapshot.waiting.requester_request == "Confirm phone."
    assert result.transition.waiting.next_review_at == NOW + timedelta(days=1)


@pytest.mark.parametrize("outcome", [CorrectionOutcome.CONFIRMED_CURRENT, CorrectionOutcome.OUT_OF_SCOPE])
def test_terminal_outcome_cannot_bypass_unresolved_publication_recovery(outcome):
    from cases.transitions import TransitionRejected, transition_case

    item = CorrectionItem("item-1", RiskClass.R2, EvidenceLevel.E3, accepted=True,
                          requires_public_change=True, publication_failed=True)
    with pytest.raises(TransitionRejected, match="publication_recovery_required"):
        transition_case(
            case(), command(phase=CasePhase.CLOSED, domain_outcome=outcome,
                            disposition_family=DispositionFamily.NO_ACTION),
            load_case_policy(), now=NOW, correction_items=(item,),
        )


@pytest.mark.parametrize("field,value", [("phase", "closed"), ("activity", "active"),
                                            ("domain_outcome", "corrected")])
def test_runtime_strings_fail_closed_instead_of_bypassing_enum_guards(field, value):
    from cases.transitions import TransitionRejected, transition_case

    with pytest.raises(TransitionRejected, match="invalid_case_contract"):
        transition_case(replace(case(), **{field: value}), command(), load_case_policy(), now=NOW)


def test_runtime_string_on_correction_item_publication_state_fails_closed():
    from cases.transitions import TransitionRejected, transition_case

    invalid = CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2, publication_state="verified")
    with pytest.raises(TransitionRejected, match="invalid_case_contract"):
        transition_case(case(), command(), load_case_policy(), now=NOW, correction_items=(invalid,))


@pytest.mark.parametrize("source,target", [
    (CasePhase.INTAKE, CasePhase.INVESTIGATION), (CasePhase.DECISION, CasePhase.TRIAGE),
    (CasePhase.FULFILLMENT, CasePhase.INVESTIGATION), (CasePhase.INVESTIGATION, CasePhase.CLOSED),
])
def test_illegal_phase_moves_are_rejected(source, target):
    from cases.transitions import TransitionRejected, transition_case

    with pytest.raises(TransitionRejected, match="illegal_phase_transition"):
        transition_case(case(phase=source), command(phase=target), load_case_policy(), now=NOW)
