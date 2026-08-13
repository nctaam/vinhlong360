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
