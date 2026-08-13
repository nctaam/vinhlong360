import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cases.domain import (
    CaseActivity, CasePhase, CaseSnapshot, CorrectionItem, DispositionFamily,
    EvidenceLevel, PromiseHealth, PublicationState, RiskClass, ServiceKind,
    WaitingContext,
)
from cases.policy import load_case_policy

NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def snapshot(**changes):
    item = CaseSnapshot(
        "case-1", ServiceKind.CORRECTION, "listing", CasePhase.INVESTIGATION,
        CaseActivity.ACTIVE, DispositionFamily.UNDETERMINED, None,
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
    older_ready = replace(base, ready_at=NOW - timedelta(hours=1),
                          received_at=NOW - timedelta(days=1))
    older_received = replace(base, received_at=NOW - timedelta(days=1))
    assert sorted((base, older_received, older_ready, high_risk, breached, emergency), key=priority_key) == [
        emergency, breached, high_risk, older_ready, older_received, base,
    ]


@pytest.mark.parametrize("invalid", [
    None,
    object(),
    {"emergency": False},
])
def test_priority_key_rejects_non_work_item_containers_with_stable_code(invalid):
    from cases.queue_policy import QueuePolicyRejected, priority_key

    with pytest.raises(QueuePolicyRejected, match="^invalid_work_item$"):
        priority_key(invalid)


def test_priority_key_rejects_work_item_subclasses():
    from cases.queue_policy import QueuePolicyRejected, WorkItemDraft, priority_key

    class WorkItemSubclass(WorkItemDraft):
        pass

    invalid = WorkItemSubclass("case", "decision", "decision_maker", RiskClass.R0,
                               NOW, NOW, PromiseHealth.ON_TRACK)
    with pytest.raises(QueuePolicyRejected, match="^invalid_work_item$"):
        priority_key(invalid)


@pytest.mark.parametrize("field,value", [
    ("emergency", 1),
    ("promise_health", "breached"),
    ("risk_class", "R3"),
    ("ready_at", NOW.replace(tzinfo=None)),
    ("received_at", NOW.replace(tzinfo=None)),
    ("received_at", NOW + timedelta(seconds=1)),
])
def test_priority_key_rejects_malformed_consumed_fields_with_stable_code(field, value):
    from cases.queue_policy import QueuePolicyRejected, WorkItemDraft, priority_key

    draft = WorkItemDraft("case", "decision", "decision_maker", RiskClass.R0, NOW, NOW,
                          PromiseHealth.ON_TRACK)
    with pytest.raises(QueuePolicyRejected, match="^invalid_work_item$"):
        priority_key(replace(draft, **{field: value}))


def test_priority_sort_rejects_mixed_naive_and_aware_dates_with_stable_code():
    from cases.queue_policy import QueuePolicyRejected, WorkItemDraft, priority_key

    valid = WorkItemDraft("case", "decision", "decision_maker", RiskClass.R0, NOW, NOW,
                          PromiseHealth.ON_TRACK)
    invalid = replace(valid, ready_at=NOW.replace(tzinfo=None))
    with pytest.raises(QueuePolicyRejected, match="^invalid_work_item$"):
        sorted((valid, invalid), key=priority_key)


def test_priority_key_accepts_future_ready_work_and_preserves_received_before_ready_order():
    from cases.queue_policy import WorkItemDraft, priority_key

    future = WorkItemDraft(
        "case", "decision", "decision_maker", RiskClass.R0,
        NOW + timedelta(hours=1), NOW, PromiseHealth.ON_TRACK,
    )
    assert priority_key(future)[-2:] == (NOW + timedelta(hours=1), NOW)


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


@pytest.mark.parametrize("bad_snapshot,bad_items,bad_policy,bad_now", [
    (None, (), None, NOW), (object(), (), load_case_policy(), NOW),
    (snapshot(owner_ref="owner-1", promise_clocks=(object(),)), (), load_case_policy(), NOW),
    (snapshot(owner_ref="owner-1"), ({"item_id": "item"},), load_case_policy(), NOW),
    (snapshot(owner_ref="owner-1"), (), {"risk_registry": {}}, NOW),
    (snapshot(owner_ref="owner-1"), (), load_case_policy(), NOW.replace(tzinfo=None)),
])
def test_queue_malformed_inputs_raise_stable_policy_error(bad_snapshot, bad_items, bad_policy, bad_now):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    with pytest.raises(QueuePolicyRejected, match="invalid_case_contract|invalid_case_policy|invalid_case_time"):
        derive_work_items(bad_snapshot, bad_items, bad_policy, now=bad_now)


def test_work_identity_uses_safe_case_and_item_identifiers():
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    with pytest.raises(QueuePolicyRejected, match="invalid_case_contract"):
        derive_work_items(snapshot(case_id="case:ambiguous", owner_ref="owner-1"),
                          (CorrectionItem("item:ambiguous", RiskClass.R1, EvidenceLevel.E1),),
                          load_case_policy(), now=NOW)


def _waiting(**changes):
    context = WaitingContext(
        "Confirm phone.", "Confirm phone.", "requester-1", "interaction-1",
        NOW + timedelta(hours=1), NOW - timedelta(hours=2),
    )
    return replace(context, **changes)


@pytest.mark.parametrize("activity,waiting", [
    (CaseActivity.WAITING_ON_REQUESTER, None),
    (CaseActivity.WAITING_ON_REQUESTER, object()),
    (CaseActivity.WAITING_ON_REQUESTER, _waiting(next_review_at=NOW)),
    (CaseActivity.WAITING_ON_REQUESTER, _waiting(started_at=NOW.replace(tzinfo=None))),
    (CaseActivity.WAITING_ON_REQUESTER, _waiting(next_review_at=(NOW + timedelta(hours=1)).replace(tzinfo=None))),
    (CaseActivity.WAITING_ON_REQUESTER, _waiting(requester_request=" ")),
    (CaseActivity.ACTIVE, _waiting()),
])
def test_queue_rejects_malformed_or_incoherent_waiting_snapshots(activity, waiting):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    invalid = snapshot(owner_ref="owner-1", activity=activity, waiting=waiting)
    with pytest.raises(QueuePolicyRejected, match="invalid_case_contract|invalid_case_time"):
        derive_work_items(invalid, (), load_case_policy(), now=NOW)


def test_queue_rejects_closed_snapshot_with_requester_waiting_activity():
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    invalid = snapshot(
        owner_ref="owner-1", phase=CasePhase.CLOSED,
        activity=CaseActivity.WAITING_ON_REQUESTER, waiting=_waiting(), closed_at=NOW,
        updated_at=NOW - timedelta(hours=1),
    )
    with pytest.raises(QueuePolicyRejected, match="^invalid_case_contract$"):
        derive_work_items(invalid, (), load_case_policy(), now=NOW)


@pytest.mark.parametrize("revision", [True, "3"])
def test_queue_rejects_non_exact_snapshot_revisions(revision):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    with pytest.raises(QueuePolicyRejected, match="^invalid_case_contract$"):
        derive_work_items(snapshot(owner_ref="owner-1", current_revision=revision), (),
                          load_case_policy(), now=NOW)


@pytest.mark.parametrize("revision", [None, "", " "])
def test_queue_rejects_blank_or_non_string_policy_revisions(revision):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    with pytest.raises(QueuePolicyRejected, match="^invalid_case_policy$"):
        derive_work_items(snapshot(owner_ref="owner-1"), (),
                          replace(load_case_policy(), revision=revision), now=NOW)


@pytest.mark.parametrize("supplier", [[], {}, " ", "supplier ref", "supplier:ref"])
def test_queue_rejects_unsafe_or_unhashable_evidence_suppliers(supplier):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    item = CorrectionItem("item-1", RiskClass.R3, EvidenceLevel.E2,
                          evidence_supplier_ref=supplier)
    with pytest.raises(QueuePolicyRejected, match="^invalid_case_contract$"):
        derive_work_items(snapshot(owner_ref="owner-1"), (item,), load_case_policy(), now=NOW)


@pytest.mark.parametrize("changes", [
    {"service_kind": "correction"},
    {"promise_health": "on_track"},
])
def test_queue_rejects_snapshot_enums_deserialized_as_strings(changes):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    with pytest.raises(QueuePolicyRejected, match="^invalid_case_contract$"):
        derive_work_items(snapshot(owner_ref="owner-1", **changes), (),
                          load_case_policy(), now=NOW)


@pytest.mark.parametrize("changes", [
    {"risk_class": "R1"},
    {"evidence_level": "E2"},
    {"publication_state": "pending"},
    {"accepted": 1},
    {"requires_public_change": 0},
    {"base_entity_revision": True},
    {"field_path": " "},
    {"evidence_refs": ["evidence-1"]},
])
def test_queue_rejects_malformed_nested_correction_item_fields(changes):
    from cases.queue_policy import QueuePolicyRejected, derive_work_items

    item = replace(
        CorrectionItem("item-1", RiskClass.R1, EvidenceLevel.E2,
                       publication_state=PublicationState.PENDING),
        **changes,
    )
    with pytest.raises(QueuePolicyRejected, match="^invalid_case_contract$"):
        derive_work_items(snapshot(owner_ref="owner-1"), (item,), load_case_policy(), now=NOW)


def test_multi_item_r0_to_r3_work_identities_are_unique_and_review_refs_close():
    from cases.queue_policy import derive_work_items

    items = (
        CorrectionItem("item-r0", RiskClass.R0, EvidenceLevel.E1, validated=True),
        CorrectionItem("item-r1", RiskClass.R1, EvidenceLevel.E2),
        CorrectionItem("item-r2", RiskClass.R2, EvidenceLevel.E2),
        CorrectionItem("item-r3", RiskClass.R3, EvidenceLevel.E2),
    )
    work = derive_work_items(snapshot(owner_ref="owner-1"), items, load_case_policy(), now=NOW)
    identities = {draft.work_identity for draft in work}
    referenced = {ref for draft in work for ref in draft.independent_of_work_refs}
    assert len(identities) == len(work)
    assert referenced <= identities
