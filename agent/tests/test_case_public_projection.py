"""The public status projection: safe copy only, no backstage state."""
from __future__ import annotations

import sys
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.domain import (  # noqa: E402
    CaseActivity,
    CasePhase,
    CaseSnapshot,
    CorrectionItem,
    CorrectionOutcome,
    DispositionFamily,
    EvidenceLevel,
    PromiseClock,
    PromiseHealth,
    PublicCaseStatus,
    PublicationState,
    RiskClass,
    ServiceKind,
    WaitingContext,
)
from cases.service import project_public_status  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _clocks() -> tuple[PromiseClock, ...]:
    return (
        PromiseClock(kind="receipt", started_at=NOW, due_at=NOW + timedelta(seconds=5),
                     observed_at=NOW, policy_revision="correction-pilot-v1"),
        PromiseClock(kind="triage", started_at=NOW, due_at=NOW + timedelta(days=1),
                     observed_at=NOW, policy_revision="correction-pilot-v1"),
        PromiseClock(kind="update", started_at=NOW, due_at=NOW + timedelta(days=3),
                     observed_at=NOW, policy_revision="correction-pilot-v1"),
        PromiseClock(kind="resolution", started_at=NOW, due_at=NOW + timedelta(days=7),
                     observed_at=NOW, policy_revision="correction-pilot-v1"),
    )


def _case(**overrides) -> CaseSnapshot:
    base = dict(
        case_id="11111111-1111-1111-1111-111111111111",
        service_kind=ServiceKind.CORRECTION,
        category="correction",
        phase=CasePhase.TRIAGE,
        activity=CaseActivity.ACTIVE,
        disposition_family=DispositionFamily.UNDETERMINED,
        domain_outcome=None,
        severity=None,
        reporter_privacy="anonymous",
        owner_ref="person:internal-owner",
        current_revision=2,
        promise_policy_ref="correction-pilot-v1",
        created_at=NOW,
        updated_at=NOW,
        closed_at=None,
        promise_health=PromiseHealth.ON_TRACK,
        promise_clocks=_clocks(),
    )
    base.update(overrides)
    return CaseSnapshot(**base)


def _item(**overrides) -> CorrectionItem:
    base = dict(
        item_id="item-1",
        risk_class=RiskClass.R1,
        evidence_level=EvidenceLevel.E0,
    )
    base.update(overrides)
    return CorrectionItem(**base)


def test_projection_returns_only_the_locked_public_fields():
    status = project_public_status(
        _case(), (_item(),), review_relation="none", public_reference="VL-COR-ABCDEFGHJKMN0"
    )

    assert type(status) is PublicCaseStatus
    assert {field.name for field in fields(PublicCaseStatus)} == {
        "public_reference", "received_at", "current_step", "waiting_for", "next_action",
        "next_update_at", "promise_health", "item_decisions", "item_publication_states",
        "review_path",
        # Thêm 2026-08-30. KHÔNG phải nới khoá: khoá này cấm từ vựng HẬU TRƯỜNG
        # rò ra (case id, owner, severity, risk class, evidence, phase/activity
        # thô, capability digest, audit) — mỗi cái đều có rào riêng ngay dưới.
        # `current_revision` là số phiên bản hồ sơ CỦA CHÍNH NGƯỜI BÁO, và hợp
        # đồng vốn ĐÃ đòi họ gửi lại đúng nó ở `expectedRevision` khi xin xét
        # lại — chỉ là chưa từng phát ra, nên nút đó 422 mọi lượt.
        "current_revision",
    }
    # Rào chống nới nhầm: con số phải là số phiên bản THẬT của hồ sơ, không phải
    # hằng trang trí ai đó nhét vào cho test xanh.
    assert status.current_revision == _case().current_revision


@pytest.mark.parametrize(
    ("phase", "activity", "expected_step"),
    [
        (CasePhase.INTAKE, CaseActivity.ACTIVE, "received"),
        (CasePhase.TRIAGE, CaseActivity.ACTIVE, "checking"),
        (CasePhase.INVESTIGATION, CaseActivity.ACTIVE, "checking"),
        (CasePhase.DECISION, CaseActivity.ACTIVE, "deciding"),
        (CasePhase.FULFILLMENT, CaseActivity.ACTIVE, "updating"),
        (CasePhase.CLOSED, CaseActivity.ACTIVE, "closed"),
    ],
)
def test_backstage_phase_never_leaks_through_the_current_step(phase, activity, expected_step):
    status = project_public_status(
        _case(phase=phase, activity=activity,
              closed_at=NOW if phase is CasePhase.CLOSED else None),
        (_item(),), review_relation="none", public_reference="VL-COR-ABCDEFGHJKMN0",
    )

    assert status.current_step == expected_step
    assert status.current_step != phase.value or phase.value == expected_step


def test_waiting_on_the_requester_is_named_without_quoting_private_notes():
    waiting = WaitingContext(
        requester_request="Gửi ảnh chụp biển hiệu",
        safe_message="Chúng tôi cần thêm một ảnh chụp biển hiệu.",
        waiting_on_ref="party:requester",
        evidence_ref="evidence-1",
        next_review_at=NOW + timedelta(days=2),
        started_at=NOW,
    )
    status = project_public_status(
        _case(activity=CaseActivity.WAITING_ON_REQUESTER, waiting=waiting),
        (_item(),), review_relation="none", public_reference="VL-COR-ABCDEFGHJKMN0",
    )

    assert status.waiting_for == "requester"
    # The catalog supplies the copy; a private operator note must never be echoed.
    assert "Gửi ảnh chụp biển hiệu" not in status.next_action
    assert status.next_action


def test_accepted_is_never_rendered_as_published():
    accepted_not_yet_public = _item(
        accepted=True,
        requires_public_change=True,
        publication_state=PublicationState.PENDING,
    )

    status = project_public_status(
        _case(phase=CasePhase.FULFILLMENT), (accepted_not_yet_public,),
        review_relation="none", public_reference="VL-COR-ABCDEFGHJKMN0",
    )

    publication = {entry.item_id: entry.state for entry in status.item_publication_states}
    assert publication["item-1"] is PublicationState.PENDING
    assert "cập nhật công khai" not in status.next_action.lower()


def test_no_backstage_value_appears_anywhere_in_the_projection():
    case = _case(
        owner_ref="person:secret-operator",
        severity="internal-high",
        domain_outcome=CorrectionOutcome.CORRECTED,
        phase=CasePhase.CLOSED,
        closed_at=NOW,
    )

    status = project_public_status(
        case, (_item(accepted=True),), review_relation="none",
        public_reference="VL-COR-ABCDEFGHJKMN0",
    )

    rendered = repr(status)
    for forbidden in (
        "person:secret-operator", "internal-high", case.case_id,
        "R1", "E0", "person:internal-owner",
    ):
        assert forbidden not in rendered


def test_review_relation_is_surfaced_as_a_path_not_as_a_case_identifier():
    status = project_public_status(
        _case(phase=CasePhase.CLOSED, closed_at=NOW), (_item(),),
        review_relation="under_review", public_reference="VL-COR-ABCDEFGHJKMN0",
    )

    assert status.review_path == "under_review"


def test_the_next_update_promise_comes_from_the_update_clock():
    status = project_public_status(
        _case(), (_item(),), review_relation="none", public_reference="VL-COR-ABCDEFGHJKMN0"
    )

    assert status.next_update_at == NOW + timedelta(days=3)
    assert status.received_at == NOW


def test_a_resolution_due_date_is_never_published_as_a_promise():
    """Policy keeps public_resolution_sla_enabled false; the clock stays internal."""
    status = project_public_status(
        _case(), (_item(),), review_relation="none", public_reference="VL-COR-ABCDEFGHJKMN0"
    )

    resolution = next(clock for clock in _clocks() if clock.kind == "resolution")
    assert status.next_update_at != resolution.due_at
    assert resolution.due_at.isoformat() not in repr(status)
