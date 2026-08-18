"""Decisions: bounded outcomes, stated reasons, lineage, and maker-checker."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.correction import (  # noqa: E402
    TERMINAL_OUTCOMES,
    CorrectionRejected,
    DecideItemCommand,
    EvidenceRecord,
    validate_decision,
)
from cases.domain import ActorContext, Channel, CorrectionOutcome, EvidenceLevel, RiskClass  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _actor(ref="person:maker", scopes=("cases:work", "cases:decide")) -> ActorContext:
    return ActorContext(actor_ref=ref, channel=Channel.WEB, scopes=frozenset(scopes),
                        correlation_id="corr-decide")


def _evidence(**overrides) -> EvidenceRecord:
    base = dict(
        evidence_id="e-1", case_id="c-1", item_id="i-1", level=EvidenceLevel.E3,
        source_scope="place.contact", author_ref="person:someone",
        observed_at=NOW - timedelta(days=1), effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=30), source_ref="https://a.example",
    )
    base.update(overrides)
    return EvidenceRecord(**base)


def _command(**overrides) -> DecideItemCommand:
    base = dict(
        case_id="c-1", item_id="i-1", outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change", evidence=(_evidence(),),
        risk_class=RiskClass.R1, actor=_actor(), reviewer_ref=None,
    )
    base.update(overrides)
    return DecideItemCommand(**base)


def test_the_terminal_outcome_set_is_exactly_the_locked_seven():
    assert TERMINAL_OUTCOMES == {
        CorrectionOutcome.CORRECTED, CorrectionOutcome.CONFIRMED_CURRENT,
        CorrectionOutcome.INSUFFICIENT_EVIDENCE, CorrectionOutcome.OUT_OF_SCOPE,
        CorrectionOutcome.DUPLICATE_LINKED, CorrectionOutcome.UNABLE_TO_VERIFY,
        CorrectionOutcome.WITHDRAWN_BY_REQUESTER,
    }
    # No generic terminal outcome is permitted.
    for banned in ("resolved", "dismissed", "da_xu_ly"):
        assert banned not in {outcome.value for outcome in TERMINAL_OUTCOMES}


def test_a_decision_needs_the_decide_scope():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(_command(actor=_actor(scopes=("cases:work",))), now=NOW)

    assert excinfo.value.problem.code == "decide_scope_required"


def test_a_decision_needs_a_bounded_reason():
    for reason in ("", "   ", "x" * 201):
        with pytest.raises(CorrectionRejected) as excinfo:
            validate_decision(_command(reason_code=reason), now=NOW)
        assert excinfo.value.problem.code == "decision_reason_required"


def test_a_correction_needs_evidence_lineage():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(_command(evidence=()), now=NOW)

    assert excinfo.value.problem.code == "evidence_lineage_required"


def test_r3_requires_a_second_person():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(_command(risk_class=RiskClass.R3, reviewer_ref=None), now=NOW)
    assert excinfo.value.problem.code == "maker_checker_required"

    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(
            _command(risk_class=RiskClass.R3, reviewer_ref="person:maker"), now=NOW
        )
    assert excinfo.value.problem.code == "maker_checker_required"

    decided = validate_decision(
        _command(risk_class=RiskClass.R3, reviewer_ref="person:checker"), now=NOW
    )
    assert decided.reviewer_ref == "person:checker"


def test_r2_requires_authoritative_or_independent_evidence():
    weak = _evidence(level=EvidenceLevel.E2)

    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(_command(risk_class=RiskClass.R2, evidence=(weak,)), now=NOW)

    assert excinfo.value.problem.code in {
        "independent_source_required", "insufficient_evidence_level",
    }


def test_an_unsupported_correction_must_be_recorded_as_such_not_forced_through():
    """The way out of thin evidence is a truthful outcome, not a stronger claim."""
    thin = _evidence(level=EvidenceLevel.E0, author_ref="anonymous")

    honest = validate_decision(
        _command(
            outcome_code=CorrectionOutcome.INSUFFICIENT_EVIDENCE,
            reason_code="no_independent_source",
            evidence=(thin,),
            risk_class=RiskClass.R2,
        ),
        now=NOW,
    )

    assert honest.outcome_code is CorrectionOutcome.INSUFFICIENT_EVIDENCE


def test_a_duplicate_must_name_the_case_it_duplicates():
    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(
            _command(outcome_code=CorrectionOutcome.DUPLICATE_LINKED, duplicate_of=None),
            now=NOW,
        )
    assert excinfo.value.problem.code == "duplicate_link_required"

    linked = validate_decision(
        _command(outcome_code=CorrectionOutcome.DUPLICATE_LINKED, duplicate_of="c-2"),
        now=NOW,
    )
    assert linked.duplicate_of == "c-2"


def test_accepted_is_an_item_decision_not_a_case_terminal_state():
    from cases.correction import requires_public_change

    corrected = validate_decision(_command(), now=NOW)

    assert requires_public_change(corrected) is True
    # Nothing about this decision closes the case or publishes anything.
    assert not hasattr(corrected, "case_phase")
    assert not hasattr(corrected, "published")
