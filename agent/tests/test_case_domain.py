import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_correction_item_preserves_the_field_level_contract():
    from cases.domain import CorrectionItem, EvidenceLevel, PublicationState, RiskClass

    item = CorrectionItem(
        "item-1", RiskClass.R2, EvidenceLevel.E3, entity_id="entity-1",
        field_path="contact.phone", base_entity_revision=4,
        evidence_refs=("evidence-1",), publication_state=PublicationState.PENDING,
    )
    assert (item.entity_id, item.field_path, item.base_entity_revision) == (
        "entity-1", "contact.phone", 4,
    )
    assert item.publication_state is PublicationState.PENDING


def test_case_snapshot_keeps_waiting_and_original_promise_lineage_immutable():
    from datetime import datetime, timezone
    from cases.domain import (
        CaseActivity, CasePhase, CaseSnapshot, DispositionFamily, PromiseClock,
        PromiseHealth, ServiceKind, WaitingContext,
    )

    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    waiting = WaitingContext("Confirm phone.", "Confirm phone.", "requester-1", "interaction-1", now, now)
    snapshot = CaseSnapshot("case-1", ServiceKind.CORRECTION, "listing", CasePhase.TRIAGE,
                            CaseActivity.WAITING_ON_REQUESTER, DispositionFamily.UNDETERMINED,
                            None, None, "anonymous", "owner-1", 1, "policy", now, now, None,
                            PromiseHealth.ON_TRACK, waiting, (PromiseClock("update", now, now),))
    assert snapshot.waiting == waiting
    assert snapshot.promise_clocks[0].due_at == now

def test_no_recordable_ruling_falls_through_to_still_deciding():
    from cases.domain import CorrectionOutcome, DispositionFamily, disposition_for

    # The whole vocabulary, held against the map. A new outcome added without a
    # family would silently tell that reporter their case is still open.
    for outcome in CorrectionOutcome:
        assert disposition_for(outcome.value) is not DispositionFamily.UNDETERMINED

    assert disposition_for(None) is DispositionFamily.UNDETERMINED
    assert disposition_for("") is DispositionFamily.UNDETERMINED
    # An unknown code is a bug, and "no settled family" is the honest answer to
    # it — claiming the case is still under review would not be.
    assert disposition_for("invented_by_nobody") is DispositionFamily.UNDETERMINED


def test_refusals_and_acceptance_do_not_read_the_same():
    from cases.domain import DispositionFamily, disposition_for

    assert disposition_for("corrected") is DispositionFamily.ACTION_TAKEN
    for refusal in ("confirmed_current", "insufficient_evidence",
                    "out_of_scope", "unable_to_verify"):
        assert disposition_for(refusal) is DispositionFamily.NO_ACTION
    assert disposition_for("duplicate_linked") is DispositionFamily.DUPLICATE
    assert disposition_for("withdrawn_by_requester") is DispositionFamily.WITHDRAWN


def test_the_guards_accept_the_scopes_a_real_session_carries():
    from admin_permissions import ADMIN_ROLE_SCOPES
    from cases.domain import holds_authority

    admin = ADMIN_ROLE_SCOPES["admin"]

    # The bug this replaced: the domain asked for cases:work / cases:decide /
    # cases:high_risk, the registry issued none of them, so every operator who
    # reached these guards was refused work they were entitled to do.
    assert holds_authority(admin, "cases:work")
    assert holds_authority(admin, "cases:decide")
    assert holds_authority(admin, "cases:high_risk")
    assert holds_authority(admin, "case.supervisor")


def test_a_superadmin_wildcard_satisfies_every_authority():
    from cases.domain import holds_authority

    # A plain `in` test failed the wildcard, so the one account that holds
    # everything held nothing here.
    for authority in ("cases:work", "cases:decide", "cases:high_risk", "case.supervisor"):
        assert holds_authority({"*"}, authority)


def test_the_mapping_is_not_a_widening():
    from cases.domain import holds_authority

    # Nobody gets work authority from nothing, and — the distinction an existing
    # work-control test defends — supervising is not clearance for R2/R3.
    assert not holds_authority(set(), "cases:work")
    assert not holds_authority({"content.editor"}, "cases:work")
    assert not holds_authority({"case.supervisor"}, "cases:high_risk")
    assert not holds_authority({"service.operator"}, "cases:decide")
    assert not holds_authority({"service.operator"}, "case.supervisor")
