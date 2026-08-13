from dataclasses import dataclass
from datetime import datetime

from .domain import CaseSnapshot, CorrectionItem, EvidenceLevel, PromiseHealth, RiskClass
from .policy import CasePolicy


@dataclass(frozen=True)
class WorkItemDraft:
    case_id: str; kind: str; required_role: str; risk_class: RiskClass
    ready_at: datetime; received_at: datetime; promise_health: PromiseHealth
    emergency: bool = False; recused_actor_refs: frozenset[str] = frozenset()
    escalation_reason: str | None = None


def priority_key(item: WorkItemDraft) -> tuple[int, int, int, datetime, datetime]:
    """Ascending tuple implements the published queue precedence."""
    promise_rank = {
        PromiseHealth.BREACHED: 0, PromiseHealth.AT_RISK: 1,
        PromiseHealth.RECOVERY: 2, PromiseHealth.ON_TRACK: 3,
    }[item.promise_health]
    risk_rank = {RiskClass.R3: 0, RiskClass.R2: 1, RiskClass.R1: 2, RiskClass.R0: 3}[item.risk_class]
    return (0 if item.emergency else 1, promise_rank, risk_rank, item.ready_at, item.received_at)


def _review(item: CorrectionItem, snapshot: CaseSnapshot, kind: str) -> WorkItemDraft:
    recused = frozenset((item.evidence_supplier_ref,)) if item.evidence_supplier_ref else frozenset()
    return WorkItemDraft(snapshot.case_id, kind, 'independent_reviewer', item.risk_class,
                         snapshot.updated_at, snapshot.created_at, snapshot.promise_health,
                         recused_actor_refs=recused)


def _item_work(snapshot: CaseSnapshot, item: CorrectionItem) -> tuple[WorkItemDraft, ...]:
    if item.risk_class is RiskClass.R0 and item.validated:
        return (WorkItemDraft(snapshot.case_id, 'fulfillment', 'fulfillment_operator', item.risk_class,
                              snapshot.updated_at, snapshot.created_at, snapshot.promise_health),)
    if item.risk_class is RiskClass.R2:
        if item.evidence_level in (EvidenceLevel.E3, EvidenceLevel.E4):
            return (WorkItemDraft(snapshot.case_id, 'decision', 'decision_maker', item.risk_class,
                                  snapshot.updated_at, snapshot.created_at, snapshot.promise_health),)
        return (_review(item, snapshot, 'independent_review'),)
    if item.risk_class is RiskClass.R3:
        maker = WorkItemDraft(snapshot.case_id, 'decision', 'decision_maker', item.risk_class,
                              snapshot.updated_at, snapshot.created_at, snapshot.promise_health)
        return (maker, _review(item, snapshot, 'truth_review'), _review(item, snapshot, 'publication_review'))
    return (WorkItemDraft(snapshot.case_id, 'decision', 'decision_maker', item.risk_class,
                          snapshot.updated_at, snapshot.created_at, snapshot.promise_health),)


def _escalations(snapshot: CaseSnapshot, items: tuple[CorrectionItem, ...]) -> tuple[WorkItemDraft, ...]:
    reasons: list[tuple[str, RiskClass]] = []
    if not snapshot.owner_ref:
        reasons.append(('missing_owner', RiskClass.R0))
    if snapshot.promise_health in (PromiseHealth.AT_RISK, PromiseHealth.BREACHED):
        reasons.append((f'promise_{snapshot.promise_health.value}', RiskClass.R0))
    for item in items:
        if item.risk_class in (RiskClass.R2, RiskClass.R3) and item.evidence_conflict:
            reasons.append(('evidence_conflict', item.risk_class))
        if item.publication_failed:
            reasons.append(('publication_failure', item.risk_class))
        if item.rollback_failed:
            reasons.append(('rollback_failure', item.risk_class))
        if item.privacy_security_safety_signal:
            reasons.append(('privacy_security_safety_signal', item.risk_class))
    return tuple(WorkItemDraft(snapshot.case_id, 'escalation', 'supervisor', risk,
                               snapshot.updated_at, snapshot.created_at, snapshot.promise_health,
                               emergency=True, escalation_reason=reason)
                 for reason, risk in reasons)


def derive_work_items(snapshot: CaseSnapshot, correction_items: tuple[CorrectionItem, ...],
                      policy: CasePolicy, *, now: datetime) -> tuple[WorkItemDraft, ...]:
    del policy, now
    return tuple(draft for item in correction_items for draft in _item_work(snapshot, item)) + _escalations(snapshot, correction_items)
