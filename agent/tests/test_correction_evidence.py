"""Evidence registry: a level is a claim about provenance, not a verdict."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.correction import (  # noqa: E402
    EvidenceRecord,
    CorrectionRuling,
    conflicting_sources,
    supports_risk,
    usable_evidence,
)
from cases.domain import EvidenceLevel, RiskClass  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _evidence(**overrides) -> EvidenceRecord:
    base = dict(
        evidence_id="e-1",
        case_id="c-1",
        item_id="i-1",
        level=EvidenceLevel.E2,
        source_scope="place.contact",
        author_ref="person:operator",
        observed_at=NOW - timedelta(days=1),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=30),
        source_ref="https://example.gov.vn/a",
    )
    base.update(overrides)
    return EvidenceRecord(**base)


# ── Usability is separate from level ──

def test_every_level_is_accepted_as_a_record_without_deciding_anything():
    for level in (EvidenceLevel.E0, EvidenceLevel.E1, EvidenceLevel.E2,
                  EvidenceLevel.E3, EvidenceLevel.E4):
        record = _evidence(level=level)
        assert record.level is level
        # Recording it does not accept it.
        assert usable_evidence((record,), now=NOW, required_scope="place.contact") == (record,)


def test_expired_evidence_is_not_usable():
    stale = _evidence(expires_at=NOW - timedelta(seconds=1))

    assert usable_evidence((stale,), now=NOW, required_scope="place.contact") == ()


def test_evidence_from_another_scope_is_not_usable():
    other = _evidence(source_scope="place.opening_hours")

    assert usable_evidence((other,), now=NOW, required_scope="place.contact") == ()


def test_evidence_observed_after_the_decision_clock_is_not_usable():
    future = _evidence(observed_at=NOW + timedelta(days=1))

    assert usable_evidence((future,), now=NOW, required_scope="place.contact") == ()


# ── Risk rules: a high level alone never carries a high-risk decision ──

def test_r0_and_r1_accept_an_ordinary_contextual_artifact():
    contextual = (_evidence(level=EvidenceLevel.E1),)

    assert supports_risk(contextual, RiskClass.R0, decision_maker_ref="person:other") is True
    assert supports_risk(contextual, RiskClass.R1, decision_maker_ref="person:other") is True


def test_r2_needs_an_authoritative_source_or_two_independent_ones():
    single_public = (_evidence(level=EvidenceLevel.E2, evidence_id="e-1"),)
    assert supports_risk(single_public, RiskClass.R2, decision_maker_ref="person:other") is False

    two_independent = (
        _evidence(level=EvidenceLevel.E2, evidence_id="e-1", source_ref="https://a.example"),
        _evidence(level=EvidenceLevel.E2, evidence_id="e-2", source_ref="https://b.example"),
    )
    assert supports_risk(two_independent, RiskClass.R2, decision_maker_ref="person:other") is True

    authoritative = (_evidence(level=EvidenceLevel.E3),)
    assert supports_risk(authoritative, RiskClass.R2, decision_maker_ref="person:other") is True


def test_two_pieces_from_the_same_source_are_not_two_independent_sources():
    same_source = (
        _evidence(evidence_id="e-1", source_ref="https://same.example/x"),
        _evidence(evidence_id="e-2", source_ref="https://same.example/x"),
    )

    assert supports_risk(same_source, RiskClass.R2, decision_maker_ref="person:other") is False


def test_a_reporter_assertion_alone_never_supports_a_high_risk_decision():
    reporter_only = (_evidence(level=EvidenceLevel.E0, author_ref="anonymous"),)

    for risk in (RiskClass.R2, RiskClass.R3):
        assert supports_risk(reporter_only, risk, decision_maker_ref="person:other") is False


def test_the_decision_maker_cannot_lean_only_on_evidence_they_authored():
    """Author recusal: somebody else must have put at least one piece on the record."""
    own = (
        _evidence(evidence_id="e-1", level=EvidenceLevel.E3, author_ref="person:me"),
    )

    assert supports_risk(own, RiskClass.R2, decision_maker_ref="person:me") is False
    with_other = own + (
        _evidence(evidence_id="e-2", level=EvidenceLevel.E3, author_ref="person:someone",
                  source_ref="https://b.example"),
    )
    assert supports_risk(with_other, RiskClass.R2, decision_maker_ref="person:me") is True


# ── Conflict ──

def test_sources_that_disagree_are_reported_rather_than_silently_ranked():
    disagreeing = (
        _evidence(evidence_id="e-1", source_ref="https://a.example", asserted_value="0270 111"),
        _evidence(evidence_id="e-2", source_ref="https://b.example", asserted_value="0270 222"),
    )

    conflict = conflicting_sources(disagreeing)

    assert conflict is True
    # A conflict blocks acceptance; it does not pick a winner by level.
    assert supports_risk(disagreeing, RiskClass.R2, decision_maker_ref="person:other") is False


def test_agreeing_sources_are_not_a_conflict():
    agreeing = (
        _evidence(evidence_id="e-1", source_ref="https://a.example", asserted_value="0270 111"),
        _evidence(evidence_id="e-2", source_ref="https://b.example", asserted_value="0270 111"),
    )

    assert conflicting_sources(agreeing) is False


def test_a_ruling_states_why_it_refused():
    ruling = CorrectionRuling.for_risk(
        (_evidence(level=EvidenceLevel.E0),), RiskClass.R3, decision_maker_ref="person:me"
    )

    assert ruling.supported is False
    assert ruling.reason_code in {
        "insufficient_evidence_level", "independent_source_required",
        "author_recusal_required", "evidence_conflict",
    }
