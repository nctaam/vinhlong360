import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases.domain import (
    ActorContext, CaseActivity, CasePhase, CaseSnapshot, Channel,
    CorrectionOutcome, DispositionFamily, PromiseClock, PromiseHealth, ServiceKind,
)
from cases.policy import load_case_policy

NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def snapshot(revision):
    return CaseSnapshot(
        "case-1", ServiceKind.CORRECTION, "listing", CasePhase.TRIAGE,
        CaseActivity.ACTIVE, DispositionFamily.UNDETERMINED, None, None,
        "anonymous", "owner-1", revision, "correction-pilot-v1",
        NOW - timedelta(days=1), NOW - timedelta(hours=1), None,
    )


@pytest.mark.parametrize("revision", [1, 4, 99])
def test_accepted_transition_increments_revision_exactly_once(revision):
    from cases.transitions import CaseTransitionCommand, transition_case

    command = CaseTransitionCommand(
        phase=CasePhase.INVESTIGATION, activity=CaseActivity.ACTIVE,
        disposition_family=DispositionFamily.UNDETERMINED, domain_outcome=None,
        actor=ActorContext("operator-1", Channel.WEB, frozenset(), "corr-1"),
        reason_code="investigate", expected_revision=revision,
    )
    result = transition_case(snapshot(revision), command, load_case_policy(), now=NOW)
    assert result.snapshot.current_revision == revision + 1


def test_promise_health_uses_the_original_due_timestamp_without_waiting_pause():
    from cases.transitions import promise_health

    clock = PromiseClock(
        kind="update", started_at=NOW - timedelta(days=3), due_at=NOW - timedelta(hours=1),
        risk_at=NOW - timedelta(hours=2), observed_at=NOW - timedelta(days=1),
    )
    assert promise_health(clock, now=NOW) is PromiseHealth.BREACHED
    assert clock.due_at == NOW - timedelta(hours=1)


def test_review_relation_is_derived_from_linked_review_cases():
    from cases.domain import ReviewCaseLink, ReviewCaseStatus, review_relation

    assert review_relation(()) == "none"
    assert review_relation((ReviewCaseLink("review-1", ReviewCaseStatus.REQUESTED),)) == "review_requested"
    assert review_relation((ReviewCaseLink("review-1", ReviewCaseStatus.IN_PROGRESS),)) == "under_review"
    assert review_relation((ReviewCaseLink("review-1", ReviewCaseStatus.COMPLETED),)) == "review_completed"


def test_domain_correction_item_keeps_publication_state_separate_from_decision():
    from cases.domain import CorrectionItem, EvidenceLevel, PublicationState, RiskClass

    item = CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2, accepted=True)
    assert item.publication_state is PublicationState.NOT_REQUIRED


def test_every_legal_phase_pair_and_same_phase_activity_update_is_accepted():
    from cases.transitions import CaseTransitionCommand, transition_case

    pairs = ((CasePhase.INTAKE, CasePhase.TRIAGE), (CasePhase.TRIAGE, CasePhase.INVESTIGATION),
             (CasePhase.INVESTIGATION, CasePhase.DECISION), (CasePhase.DECISION, CasePhase.FULFILLMENT),
             (CasePhase.FULFILLMENT, CasePhase.CLOSED), (CasePhase.TRIAGE, CasePhase.TRIAGE))
    for source, target in pairs:
        command = CaseTransitionCommand(target, CaseActivity.ACTIVE, DispositionFamily.UNDETERMINED,
                                        CorrectionOutcome.CONFIRMED_CURRENT if target is CasePhase.CLOSED else None,
                                        ActorContext("operator-1", Channel.WEB, frozenset(), "corr-1"),
                                        "move", 4)
        assert transition_case(replace(snapshot(4), phase=source), command, load_case_policy(), now=NOW)


@pytest.mark.parametrize("revision", range(1, 101))
def test_generated_accepted_transitions_advance_revision_exactly_once(revision):
    from cases.transitions import CaseTransitionCommand, transition_case

    command = CaseTransitionCommand(CasePhase.INVESTIGATION, CaseActivity.ACTIVE,
                                    DispositionFamily.UNDETERMINED, None,
                                    ActorContext("operator-1", Channel.WEB, frozenset(), "corr-1"),
                                    "investigate", revision)
    result = transition_case(replace(snapshot(revision), phase=CasePhase.TRIAGE), command,
                             load_case_policy(), now=NOW)
    assert result.snapshot.current_revision == revision + 1


@pytest.mark.parametrize("source", list(CasePhase))
@pytest.mark.parametrize("target", list(CasePhase))
def test_generated_phase_pairs_match_the_explicit_transition_graph(source, target):
    from cases.transitions import CaseTransitionCommand, TransitionRejected, transition_case

    allowed = {
        CasePhase.INTAKE: {CasePhase.INTAKE, CasePhase.TRIAGE},
        CasePhase.TRIAGE: {CasePhase.TRIAGE, CasePhase.INVESTIGATION},
        CasePhase.INVESTIGATION: {CasePhase.INVESTIGATION, CasePhase.DECISION},
        CasePhase.DECISION: {CasePhase.DECISION, CasePhase.FULFILLMENT},
        CasePhase.FULFILLMENT: {CasePhase.FULFILLMENT, CasePhase.CLOSED},
    }
    outcome = CorrectionOutcome.CONFIRMED_CURRENT if target is CasePhase.CLOSED else None
    command = CaseTransitionCommand(target, CaseActivity.ACTIVE, DispositionFamily.UNDETERMINED,
                                    outcome, ActorContext("operator-1", Channel.WEB, frozenset(), "corr-1"),
                                    "move", 4)
    if source is CasePhase.CLOSED:
        with pytest.raises(TransitionRejected, match="closed_case_immutable"):
            transition_case(replace(snapshot(4), phase=source, closed_at=NOW), command,
                            load_case_policy(), now=NOW)
        return
    if target in allowed[source]:
        assert transition_case(replace(snapshot(4), phase=source), command, load_case_policy(), now=NOW)
    else:
        with pytest.raises(TransitionRejected, match="illegal_phase_transition"):
            transition_case(replace(snapshot(4), phase=source), command, load_case_policy(), now=NOW)


@pytest.mark.parametrize("target", list(CasePhase))
def test_generated_closed_cases_are_immutable_for_every_target(target):
    from cases.transitions import CaseTransitionCommand, TransitionRejected, transition_case

    command = CaseTransitionCommand(target, CaseActivity.ACTIVE, DispositionFamily.UNDETERMINED,
                                    None, ActorContext("operator-1", Channel.WEB, frozenset(), "corr-1"),
                                    "move", 4)
    with pytest.raises(TransitionRejected, match="closed_case_immutable"):
        transition_case(replace(snapshot(4), phase=CasePhase.CLOSED, closed_at=NOW), command,
                        load_case_policy(), now=NOW)
