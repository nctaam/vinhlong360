from __future__ import annotations

import sys
import importlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases import wiring  # noqa: E402
from cases.correction import (  # noqa: E402
    AddEvidenceCommand,
    CorrectionRejected,
    DecideItemCommand,
    EvidenceRecord,
    add_evidence,
    validate_decision,
)
from cases.domain import ActorContext, Channel, CorrectionOutcome, EvidenceLevel, RiskClass  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)


class _Settings(SimpleNamespace):
    @property
    def cors_origins_list(self):
        return list(self._origins)


def _settings(**overrides):
    values = dict(
        CASE_KERNEL_ENABLED=True,
        CASE_KERNEL_ENCRYPTION_KEY="0" * 43,
        CASE_SERVICE_OWNER_REF="person:owner",
        _origins=["https://vinhlong360.vn"],
    )
    values.update(overrides)
    return _Settings(**values)


def _actor():
    return ActorContext(
        actor_ref="person:maker",
        channel=Channel.WEB,
        scopes=frozenset(("cases:work", "cases:decide")),
        correlation_id="corr-proof",
    )


def _record(**overrides):
    values = dict(
        evidence_id="e-1",
        case_id="case-1",
        item_id="item-1",
        level=EvidenceLevel.E3,
        source_scope="place.contact",
        author_ref="person:source",
        observed_at=NOW - timedelta(minutes=5),
        effective_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        source_ref="source:a",
    )
    values.update(overrides)
    return EvidenceRecord(**values)


def test_case_dependencies_are_frozen_and_commit_is_all_or_nothing(monkeypatch):
    bundle = wiring.build_case_dependencies(object(), _settings())
    with pytest.raises(FrozenInstanceError):
        bundle.database = object()

    import cases.public_api as public_api

    assert public_api._SERVICE is None
    assert wiring.commit_case_dependencies(bundle) is None
    assert public_api._SERVICE is not None
    wiring.reset_case_dependencies()
    assert public_api._SERVICE is None


def _dependency_slots():
    from cases import admin_api, contact, correction, metrics, outbox, public_api, publication, work_control

    return (
        (public_api, ("_SERVICE", "_SETTINGS", "_ALLOWED_ORIGIN")),
        (correction, ("_DATABASE", "_CRYPTO", "_POLICY")),
        (publication, ("_DATABASE", "_CRYPTO", "_POLICY")),
        (work_control, ("_DATABASE", "_POLICY")),
        (admin_api, ("_DATABASE", "_CRYPTO", "_PROJECTION_FETCHER", "_SERVICE")),
        (contact, ("_DATABASE", "_CRYPTO", "_PROVIDER", "_CODE_SOURCE")),
        (outbox, ("_DATABASE", "_CRYPTO", "_PROVIDER", "_CONTACT_LOOKUP")),
        (metrics, ("_DATABASE",)),
    )


@pytest.mark.parametrize(
    "module_name, configure_name",
    (
        ("cases.public_api", "configure_case_public_api"),
        ("cases.correction", "configure_case_correction"),
        ("cases.publication", "configure_case_publication"),
        ("cases.work_control", "configure_case_work_control"),
        ("cases.admin_api", "configure_case_admin_api"),
        ("cases.contact", "configure_case_contact"),
        ("cases.outbox", "configure_case_outbox"),
        ("cases.metrics", "configure_case_metrics"),
    ),
)
def test_failed_dependency_commit_resets_every_module_global(
    monkeypatch, module_name, configure_name
):
    bundle = wiring.build_case_dependencies(object(), _settings())
    module = importlib.import_module(module_name)

    def fail(**kwargs):
        raise RuntimeError("injected commit failure")

    monkeypatch.setattr(module, configure_name, fail)
    with pytest.raises(RuntimeError, match="injected commit failure"):
        wiring.commit_case_dependencies(bundle)
    assert all(
        getattr(dependency_module, name) is None
        for dependency_module, names in _dependency_slots()
        for name in names
    )


@pytest.mark.parametrize(
    "field, value, code",
    [
        ("observed_at", datetime(2026, 8, 31, 8, 0), "evidence_timestamp_timezone_required"),
        ("effective_at", NOW + timedelta(seconds=1), "evidence_effective_at_future"),
        ("expires_at", NOW - timedelta(seconds=1), "evidence_expired"),
    ],
)
def test_add_evidence_rejects_unsafe_time_bounds_before_opening_transaction(field, value, code):
    command = AddEvidenceCommand(
        case_id="case-1",
        item_id="item-1",
        level=EvidenceLevel.E3,
        source_scope="place.contact",
        source_ref="source:a",
        descriptor={},
        content=None,
        actor=_actor(),
        observed_at=NOW - timedelta(minutes=5),
        effective_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
    )
    command = command.__class__(**{**command.__dict__, field: value})
    with pytest.raises(CorrectionRejected) as excinfo:
        add_evidence(command, now=NOW)
    assert getattr(excinfo.value, "problem", None).code == code


def test_validate_decision_uses_only_evidence_in_required_scope_and_time_window():
    valid = _record()
    stale = _record(evidence_id="e-stale", expires_at=NOW - timedelta(seconds=1))
    wrong_scope = _record(evidence_id="e-wrong", source_scope="place.opening_hours")
    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(valid, stale, wrong_scope),
        risk_class=RiskClass.R1,
        actor=_actor(),
    )
    decision = validate_decision(command, now=NOW, required_scope="place.contact")
    assert decision.evidence_refs == ("e-1",)


def test_validate_decision_never_infers_required_scope_from_the_first_record():
    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(_record(source_scope="place.opening_hours"),),
        risk_class=RiskClass.R1,
        actor=_actor(),
    )

    with pytest.raises(CorrectionRejected) as excinfo:
        validate_decision(command, now=NOW)

    assert excinfo.value.problem.code == "evidence_scope_required"


def test_wrong_scope_evidence_is_rejected_as_not_usable():
    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(_record(source_scope="place.opening_hours"),),
        risk_class=RiskClass.R1,
        actor=_actor(),
        required_scope="place.contact",
    )

    with pytest.raises(Exception) as excinfo:
        validate_decision(command, now=NOW)

    assert excinfo.value.problem.code == "evidence_not_usable"


def test_audit_and_outbox_fallback_uses_case_transaction_compatible_methods():
    from control_plane.audit import AuditEvent, write_audit_and_outbox

    class Tx:
        def __init__(self):
            self.audit = None
            self.outbox = None

        def append_audit(self, draft):
            self.audit = draft

        def enqueue_outbox(self, draft):
            self.outbox = draft

    tx = Tx()
    event = AuditEvent(
        event_id="event-1",
        actor_id="person:maker",
        action="case.decided",
        resource_type="case",
        resource_id="case-1",
        reason="source_confirms_change",
        before={"case_id": "case-1", "current_revision": 1},
        after={"case_id": "case-1", "current_revision": 2},
        correlation_id="corr-proof",
        revision=2,
        occurred_at=NOW,
        actor_scopes=("cases:decide", "cases:work"),
        channel=Channel.WEB,
        policy_revision="policy-proof-v2",
    )
    write_audit_and_outbox(tx, event, {"topic": "correction.updated", "generation": "g-2"})
    assert tx.audit.event_id == tx.outbox.descriptor["event_id"] == "event-1"
    assert tx.audit.resource_id == tx.outbox.descriptor["resource_id"] == "case-1"
    assert tx.audit.revision == tx.outbox.descriptor["revision"] == 2
    assert tx.audit.generation == tx.outbox.descriptor["generation"] == "g-2"
    assert tx.audit.correlation_id == tx.outbox.descriptor["correlation_id"] == "corr-proof"
    assert tx.audit.actor_scopes == ("cases:decide", "cases:work")
    assert tx.audit.channel is Channel.WEB
    assert tx.audit.policy_revision == "policy-proof-v2"


def test_delayed_outbox_keeps_the_audit_at_the_actual_occurrence_time(monkeypatch):
    from cases.domain import (
        CaseActivity,
        CasePhase,
        CaseSnapshot,
        DispositionFamily,
        PromiseHealth,
        ServiceKind,
    )
    from cases.publication import VerifyProjectionCommand, _write_audit_outbox

    class Tx:
        def __init__(self):
            self.audit = None
            self.outbox = None

        def append_audit(self, draft):
            self.audit = draft

        def enqueue_outbox(self, draft):
            self.outbox = draft

    snapshot = CaseSnapshot(
        case_id="case-1",
        service_kind=ServiceKind.CORRECTION,
        category="correction",
        phase=CasePhase.FULFILLMENT,
        activity=CaseActivity.ACTIVE,
        disposition_family=DispositionFamily.UNDETERMINED,
        domain_outcome=None,
        severity=None,
        reporter_privacy="anonymous",
        owner_ref="person:owner",
        current_revision=3,
        promise_policy_ref="policy-proof-v2",
        created_at=NOW - timedelta(days=2),
        updated_at=NOW,
        closed_at=None,
        promise_health=PromiseHealth.RECOVERY,
    )
    command = VerifyProjectionCommand("case-1", "change-1", _actor())
    available_at = NOW + timedelta(hours=24)
    tx = Tx()

    _write_audit_outbox(
        tx,
        command,
        snapshot,
        snapshot,
        _actor().actor_ref,
        reason_code="projection_verification_failed",
        event_id="notify:change-1:verification_failed",
        topic="correction.updated",
        now=NOW,
        available_at=available_at,
    )

    assert tx.audit.occurred_at == NOW
    assert tx.outbox.available_at == available_at
