import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases.domain import (
    CaseActivity, CasePhase, CaseSnapshot, CorrectionItem, DispositionFamily,
    EvidenceLevel, PromiseHealth, RiskClass, ServiceKind,
)
from cases.policy import load_case_policy

NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def snapshot(**changes):
    item = CaseSnapshot(
        "case-1", ServiceKind.CORRECTION, "listing", CasePhase.INVESTIGATION,
        CaseActivity.WAITING_ON_REQUESTER, DispositionFamily.UNDETERMINED, None,
        None, "anonymous", "", 3, "correction-pilot-v1",
        NOW - timedelta(days=2), NOW - timedelta(hours=1), None,
    )
    return replace(item, **changes)


def test_r3_creates_separate_truth_and_publication_review_with_evidence_supplier_recused():
    from cases.queue_policy import derive_work_items

    item = CorrectionItem("item-1", RiskClass.R3, EvidenceLevel.E2, evidence_supplier_ref="evidence-maker")
    work = derive_work_items(snapshot(owner_ref="owner-1"), (item,), load_case_policy(), now=NOW)
    kinds = {draft.kind for draft in work}
    assert {"decision", "truth_review", "publication_review"} <= kinds
    assert all("evidence-maker" in draft.recused_actor_refs for draft in work if draft.kind.endswith("review"))


def test_r2_authoritative_evidence_allows_decision_without_independent_review():
    from cases.queue_policy import derive_work_items

    item = CorrectionItem("item-1", RiskClass.R2, EvidenceLevel.E3)
    work = derive_work_items(snapshot(owner_ref="owner-1"), (item,), load_case_policy(), now=NOW)
    assert [draft.kind for draft in work] == ["decision"]


def test_queue_priority_is_deterministic_in_emergency_promise_risk_ready_received_order():
    from cases.queue_policy import WorkItemDraft, priority_key

    base = WorkItemDraft("case", "decision", "decision_maker", RiskClass.R0, NOW, NOW,
                         PromiseHealth.ON_TRACK)
    emergency = replace(base, emergency=True, risk_class=RiskClass.R0)
    breached = replace(base, promise_health=PromiseHealth.BREACHED, risk_class=RiskClass.R0)
    high_risk = replace(base, risk_class=RiskClass.R3)
    older_ready = replace(base, ready_at=NOW - timedelta(hours=1))
    older_received = replace(base, received_at=NOW - timedelta(days=1))
    assert sorted((base, older_received, older_ready, high_risk, breached, emergency), key=priority_key) == [
        emergency, breached, high_risk, older_ready, older_received, base,
    ]


def test_escalations_cover_missing_owner_promise_conflict_and_publication_failure():
    from cases.queue_policy import derive_work_items

    item = CorrectionItem("item-1", RiskClass.R2, EvidenceLevel.E2, evidence_conflict=True,
                          publication_failed=True)
    work = derive_work_items(snapshot(owner_ref="", promise_health=PromiseHealth.AT_RISK), (item,), load_case_policy(), now=NOW)
    reasons = {draft.escalation_reason for draft in work if draft.kind == "escalation"}
    assert {"missing_owner", "promise_at_risk", "evidence_conflict", "publication_failure"} <= reasons


def test_work_derivation_recomputes_breached_health_from_original_clock_without_wait_reset():
    from cases.domain import PromiseClock
    from cases.queue_policy import derive_work_items

    clock = PromiseClock("update", NOW - timedelta(days=3), NOW - timedelta(hours=1))
    work = derive_work_items(snapshot(owner_ref="owner-1", promise_clocks=(clock,)), (), load_case_policy(), now=NOW)
    assert any(draft.escalation_reason == "promise_breached" for draft in work)


def test_r1_policy_can_require_an_independent_reviewer():
    from cases.queue_policy import derive_work_items

    policy = replace(load_case_policy(), risk_registry={
        **load_case_policy().risk_registry, "R1": {"independent_review": True},
    })
    work = derive_work_items(snapshot(owner_ref="owner-1"), (CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2),), policy, now=NOW)
    assert [draft.kind for draft in work] == ["independent_review"]


def test_r1_policy_can_allow_a_decision_maker():
    from cases.queue_policy import derive_work_items

    work = derive_work_items(snapshot(owner_ref="owner-1"),
                             (CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2),),
                             load_case_policy(), now=NOW)
    assert [draft.kind for draft in work] == ["decision"]


def test_r3_review_forbids_the_maker_and_evidence_supplier():
    from cases.queue_policy import derive_work_items

    item = CorrectionItem("item-1", RiskClass.R3, EvidenceLevel.E2, evidence_supplier_ref="supplier")
    work = derive_work_items(snapshot(owner_ref="owner-1"), (item,), load_case_policy(), now=NOW)
    maker = next(draft for draft in work if draft.kind == "decision")
    reviews = [draft for draft in work if draft.kind.endswith("review")]
    assert all(maker.work_identity in draft.independent_of_work_refs for draft in reviews)
    assert maker.recused_actor_refs == frozenset()
    assert all("supplier" in draft.forbidden_actor_refs for draft in reviews)


@pytest.mark.parametrize("risk", list(RiskClass))
@pytest.mark.parametrize("evidence", list(EvidenceLevel))
def test_every_risk_evidence_work_draft_has_a_nonblank_unique_identity(risk, evidence):
    from cases.queue_policy import derive_work_items

    work = derive_work_items(snapshot(owner_ref="owner-1"), (CorrectionItem("item-1", risk, evidence, validated=True),),
                             load_case_policy(), now=NOW)
    identities = [draft.work_identity for draft in work]
    assert identities and all(identities) and len(identities) == len(set(identities))


def test_duplicate_item_ids_are_rejected_fail_closed():
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    items = (CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2),
             CorrectionItem("item-1", RiskClass.R2, EvidenceLevel.E3))
    with pytest.raises(QueuePolicyRejected, match="duplicate_item_id"):
        derive_work_items(snapshot(owner_ref="owner-1"), items, load_case_policy(), now=NOW)
