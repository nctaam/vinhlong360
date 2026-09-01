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


def test_decision_command_normalization_is_the_digest_and_replay_evidence_set():
    from cases.correction import _normalize_decision_command

    stale = _record(evidence_id="e-stale", expires_at=NOW - timedelta(seconds=1))
    valid = _record(evidence_id="e-valid")
    normalized = _normalize_decision_command(
        DecideItemCommand(
            case_id="case-1",
            item_id="item-1",
            outcome_code=CorrectionOutcome.CORRECTED,
            reason_code="source_confirms_change",
            evidence=(stale, valid),
            risk_class=RiskClass.R1,
            actor=_actor(),
            required_scope="place.contact",
        ),
        now=NOW,
    )
    assert tuple(record.evidence_id for record in normalized.evidence) == ("e-valid",)


def test_decision_retry_replays_the_same_normalized_evidence_receipt(monkeypatch):
    from cases import correction
    from cases.correction import decide_item

    class Tx:
        receipt = None
        inserts = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def load_case(self, *_args, **_kwargs):
            return SimpleNamespace(current_revision=7)

        def load_outbox_by_idempotency_key(self, _key):
            return self.receipt

        def actor_holds_lease(self, *_args, **_kwargs):
            return True

        def insert_decision(self, **kwargs):
            self.inserts.append(kwargs)

        def append_audit_event(self, _event):
            return None

        def enqueue_outbox_event(self, payload):
            self.receipt = {"payload": dict(payload)}

    class Store:
        tx = Tx()

        def transaction(self):
            return self.tx

    monkeypatch.setattr(correction, "_store", lambda: Store())
    monkeypatch.setattr(correction, "safe_case_projection", lambda _snapshot: {})
    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(
            _record(evidence_id="e-reporter", level=EvidenceLevel.E0,
                    expires_at=NOW - timedelta(seconds=1)),
            _record(evidence_id="e-valid", source_ref="source:valid"),
        ),
        risk_class=RiskClass.R1,
        actor=_actor(),
        required_scope="place.contact",
    )

    first = decide_item(command, now=NOW)
    second = decide_item(command, now=NOW + timedelta(minutes=1))

    assert second == first
    assert first.evidence_refs == ("e-valid",)
    assert len(Store.tx.inserts) == 1


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
    assert tx.audit.reason_code == "source_confirms_change"
    assert tx.outbox.descriptor["reason"] == "source_confirms_change"
    assert tx.outbox.descriptor["resource_type"] == "case"


@pytest.mark.parametrize("channel", [None, "web", object()])
def test_audit_event_rejects_invalid_channel_instead_of_defaulting_to_web(channel):
    from control_plane.audit import AuditEvent

    with pytest.raises(ValueError, match="invalid_audit_event"):
        AuditEvent(
            event_id="event-invalid-channel",
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
            actor_scopes=("cases:decide",),
            channel=channel,
            policy_revision="policy-proof-v2",
        )


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


def test_decision_replay_rejects_a_receipt_without_a_ruling(monkeypatch):
    from cases import correction
    from cases.correction import _decision_command_digest, decide_item

    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(_record(),),
        risk_class=RiskClass.R1,
        actor=_actor(),
        required_scope="place.contact",
    )
    payload = {"decision_digest": _decision_command_digest(command)}

    class Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def load_case(self, *_args, **_kwargs):
            return SimpleNamespace(current_revision=7)

        def load_outbox_by_idempotency_key(self, _key):
            return {"payload": payload}

    class Store:
        def transaction(self):
            return Tx()

    monkeypatch.setattr(correction, "_store", lambda: Store())
    with pytest.raises(correction.CorrectionRejected) as excinfo:
        decide_item(command, now=NOW)
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_decision_replay_rejects_malformed_receipt_types(monkeypatch):
    from cases import correction
    from cases.correction import _decision_command_digest, decide_item

    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(_record(),),
        risk_class=RiskClass.R1,
        actor=_actor(),
        required_scope="place.contact",
    )
    payload = {
        "event_id": "decision:case-1:item-1",
        "case_id": "case-1",
        "revision": "7",
        "generation": "7",
        "correlation_id": "corr-proof",
        "decision_digest": _decision_command_digest(command),
        "ruling": {
            "case_id": "case-1",
            "item_id": "item-1",
            "outcome_code": "corrected",
            "reason_code": "source_confirms_change",
            "refs": ["e-1"],
            "decision_maker_ref": "person:maker",
            "reviewer_ref": None,
            "duplicate_of": None,
        },
    }

    class Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def load_case(self, *_args, **_kwargs):
            return SimpleNamespace(current_revision=7)

        def load_outbox_by_idempotency_key(self, _key):
            return {"payload": payload}

    class Store:
        def transaction(self):
            return Tx()

    monkeypatch.setattr(correction, "_store", lambda: Store())
    with pytest.raises(correction.CorrectionRejected) as excinfo:
        decide_item(command, now=NOW)
    assert excinfo.value.problem.code == "publication_receipt_invalid"


@pytest.mark.parametrize("refs", [None, [], ["e-1"], ["e-2", "e-1"]])
def test_decision_replay_requires_exact_nonempty_evidence_identity(refs, monkeypatch):
    from cases import correction
    from cases.correction import _decision_command_digest, decide_item

    command = DecideItemCommand(
        case_id="case-1",
        item_id="item-1",
        outcome_code=CorrectionOutcome.CORRECTED,
        reason_code="source_confirms_change",
        evidence=(_record(), _record(evidence_id="e-2", source_ref="source:b")),
        risk_class=RiskClass.R1,
        actor=_actor(),
        required_scope="place.contact",
    )
    ruling = {
        "case_id": "case-1",
        "item_id": "item-1",
        "outcome_code": "corrected",
        "reason_code": "source_confirms_change",
        "decision_maker_ref": "person:maker",
        "reviewer_ref": None,
        "duplicate_of": None,
    }
    if refs is not None:
        ruling["refs"] = refs
    payload = {
        "event_id": "decision:case-1:item-1",
        "case_id": "case-1",
        "revision": 7,
        "generation": "7",
        "correlation_id": "corr-proof",
        "decision_digest": _decision_command_digest(command),
        "ruling": ruling,
    }

    class Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def load_case(self, *_args, **_kwargs):
            return SimpleNamespace(current_revision=7)

        def load_outbox_by_idempotency_key(self, _key):
            return {"payload": payload}

    class Store:
        def transaction(self):
            return Tx()

    monkeypatch.setattr(correction, "_store", lambda: Store())
    with pytest.raises(correction.CorrectionRejected) as excinfo:
        decide_item(command, now=NOW)
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_non_evidence_decision_filters_unusable_evidence_before_persisting():
    stale = _record(evidence_id="e-stale", expires_at=NOW - timedelta(seconds=1))
    wrong_scope = _record(evidence_id="e-wrong", source_scope="place.opening_hours")
    decision = validate_decision(
        DecideItemCommand(
            case_id="case-1",
            item_id="item-1",
            outcome_code=CorrectionOutcome.INSUFFICIENT_EVIDENCE,
            reason_code="no_independent_source",
            evidence=(stale, wrong_scope),
            risk_class=RiskClass.R1,
            actor=_actor(),
            required_scope="place.contact",
        ),
        now=NOW,
    )
    assert decision.evidence_refs == ()


def test_change_set_replay_rejects_a_missing_receipt(monkeypatch):
    from cases import correction
    from cases.correction import _replay_existing_change_set

    existing = {
        "change_set_id": "cs-1",
        "apply_status": "pending",
        "base_entity_revision": 7,
        "before_patch": {"attributes.phone": "old"},
        "after_patch": {"attributes.phone": "new"},
        "risk_class": "R1",
        "decision_maker_ref": "person:maker",
        "evidence_refs": ["e-1"],
        "reviewer_ref": None,
    }

    class Tx:
        def load_change_set_for_items(self, *_args, **_kwargs):
            return existing

        def load_outbox_by_idempotency_key(self, _key):
            return None

    with pytest.raises(correction.CorrectionRejected) as excinfo:
        _replay_existing_change_set(
            Tx(), "case-1", ("item-1",), _actor(), 7, ("e-1",),
            SimpleNamespace(current_revision=8),
        )
    assert excinfo.value.problem.code == "publication_receipt_missing"


def test_change_set_replay_rejects_an_incomplete_receipt():
    from cases import correction
    from cases.correction import _build_command_digest, _replay_existing_change_set

    existing = {
        "change_set_id": "cs-1",
        "apply_status": "pending",
        "base_entity_revision": 7,
        "before_patch": {"attributes.phone": "old"},
        "after_patch": {"attributes.phone": "new"},
        "risk_class": "R1",
        "decision_maker_ref": "person:maker",
        "evidence_refs": ["e-1"],
        "reviewer_ref": None,
    }
    digest = _build_command_digest("case-1", ("item-1",), _actor(), 7, ("e-1",))

    class Tx:
        def load_change_set_for_items(self, *_args, **_kwargs):
            return existing

        def load_outbox_by_idempotency_key(self, _key):
            return {"payload": {"build_digest": digest}}

    with pytest.raises(correction.CorrectionRejected) as excinfo:
        _replay_existing_change_set(
            Tx(), "case-1", ("item-1",), _actor(), 7, ("e-1",),
            SimpleNamespace(current_revision=8),
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_change_set_replay_rejects_malformed_receipt_types():
    from cases import correction
    from cases.correction import _build_command_digest, _replay_existing_change_set

    existing = {
        "change_set_id": "cs-1",
        "apply_status": "pending",
        "base_entity_revision": 7,
        "before_patch": {"attributes.phone": "old"},
        "after_patch": {"attributes.phone": "new"},
        "risk_class": "R1",
        "decision_maker_ref": "person:maker",
        "evidence_refs": ["e-1"],
        "reviewer_ref": None,
    }
    digest = _build_command_digest("case-1", ("item-1",), _actor(), 7, ("e-1",))
    payload = {
        "event_id": "notify:cs-1:decided",
        "case_id": "case-1",
        "revision": "8",
        "generation": "8",
        "correlation_id": "corr-proof",
        "change_set_id": "cs-1",
        "item_ids": ["item-1"],
        "build_digest": digest,
    }

    class Tx:
        def load_change_set_for_items(self, *_args, **_kwargs):
            return existing

        def load_outbox_by_idempotency_key(self, _key):
            return {"payload": payload}

    with pytest.raises(correction.CorrectionRejected) as excinfo:
        _replay_existing_change_set(
            Tx(), "case-1", ("item-1",), _actor(), 7, ("e-1",),
            SimpleNamespace(current_revision=8),
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_verification_replay_requires_an_immutable_recovery_deadline():
    from cases.publication import (
        PublicationRejected,
        VerifyProjectionCommand,
        _replay_verification_failure,
    )

    existing = {
        "idempotency_key": "notify:change-1:verification_failed",
        "available_at": NOW + timedelta(hours=1),
        "payload": {
            "event_id": "notify:change-1:verification_failed",
            "case_id": "case-1",
            "generation": "4",
            "correlation_id": "corr-proof",
            "revision": 4,
            "mismatched": ["revision"],
        },
    }
    with pytest.raises(PublicationRejected) as excinfo:
        _replay_verification_failure(
            SimpleNamespace(),
            VerifyProjectionCommand("case-1", "change-1", _actor()),
            SimpleNamespace(),
            existing,
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_replay_receipt_validators_accept_mapping_rows_from_postgres():
    from collections import UserDict

    from cases.correction import _replay_receipt_payload
    from cases.publication import _replay_payload

    correction_payload = UserDict({"event_id": "decision:case-1:item-1"})
    correction_row = UserDict({"payload": correction_payload})
    assert _replay_receipt_payload(
        correction_row,
        "decision:case-1:item-1",
        required=("event_id",),
    ) == {"event_id": "decision:case-1:item-1"}

    publication_event = "notify:change-1:applied"
    publication_payload = UserDict({
        "event_id": publication_event,
        "case_id": "case-1",
        "generation": "4",
        "correlation_id": "corr-proof",
        "revision": 4,
    })
    publication_row = UserDict({
        "idempotency_key": publication_event,
        "payload": publication_payload,
    })
    assert _replay_payload(
        publication_row, publication_event, required=("revision",),
    ) == dict(publication_payload)


def test_apply_replay_rejects_an_empty_applied_fields_receipt():
    from cases.publication import ApplyChangeSetCommand, PublicationRejected, _replay_apply

    event_id = "notify:change-1:applied"
    existing = {
        "idempotency_key": event_id,
        "payload": {
            "event_id": event_id,
            "case_id": "case-1",
            "generation": "4",
            "correlation_id": "corr-proof",
            "revision": 4,
            "entity_revision": 8,
            "applied_fields": [],
        },
    }

    class Tx:
        def load_outbox_by_idempotency_key(self, _key):
            return existing

        def load_change_set_target(self, _change_set_id):
            return "entity-1", ("item-1",)

    with pytest.raises(PublicationRejected) as excinfo:
        _replay_apply(
            Tx(),
            ApplyChangeSetCommand("case-1", "change-1", _actor(), 3, 7),
            {"case_id": "case-1"},
            SimpleNamespace(),
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_verification_failure_replay_rejects_empty_mismatched_receipt():
    from cases.publication import (
        PublicationRejected,
        VerifyProjectionCommand,
        _replay_verification_failure,
    )

    event_id = "notify:change-1:verification_failed"
    deadline = NOW + timedelta(hours=1)
    existing = {
        "idempotency_key": event_id,
        "payload": {
            "event_id": event_id,
            "case_id": "case-1",
            "generation": "4",
            "correlation_id": "corr-proof",
            "revision": 4,
            "mismatched": [],
            "next_update_at": deadline.isoformat(),
        },
    }

    with pytest.raises(PublicationRejected) as excinfo:
        _replay_verification_failure(
            SimpleNamespace(),
            VerifyProjectionCommand("case-1", "change-1", _actor()),
            SimpleNamespace(),
            existing,
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_change_set_replay_rejects_persisted_evidence_refs_that_disagree_with_command():
    from cases import correction
    from cases.correction import _build_command_digest, _replay_existing_change_set

    event_id = "notify:cs-1:decided"
    existing = {
        "change_set_id": "cs-1",
        "case_id": "case-1",
        "apply_status": "pending",
        "base_entity_revision": 7,
        "before_patch": {"attributes.phone": "old"},
        "after_patch": {"attributes.phone": "new"},
        "risk_class": "R1",
        "decision_maker_ref": "person:maker",
        "evidence_refs": ["e-tampered"],
        "reviewer_ref": None,
    }
    digest = _build_command_digest("case-1", ("item-1",), _actor(), 7, ("e-1",))
    payload = {
        "event_id": event_id,
        "case_id": "case-1",
        "revision": 8,
        "generation": "8",
        "correlation_id": "corr-proof",
        "change_set_id": "cs-1",
        "item_ids": ["item-1"],
        "build_digest": digest,
        "risk_class": "R1",
    }

    class Tx:
        def load_change_set_for_items(self, *_args, **_kwargs):
            return existing

        def load_outbox_by_idempotency_key(self, _key):
            return {"idempotency_key": event_id, "payload": payload}

        def load_change_set_target(self, _change_set_id):
            return "entity-1", ("item-1",)

        def load_correction_item_payloads(self, _case_id, _item_ids):
            return ({
                "item_id": "item-1",
                "field_path": "attributes.phone",
                "risk_class": "R1",
            },)

    with pytest.raises(correction.CorrectionRejected) as excinfo:
        _replay_existing_change_set(
            Tx(), "case-1", ("item-1",), _actor(), 7, ("e-1",),
            SimpleNamespace(current_revision=8),
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_change_set_replay_rejects_a_risk_class_outside_the_domain():
    from cases import correction
    from cases.correction import _build_command_digest, _replay_existing_change_set

    event_id = "notify:cs-1:decided"
    existing = {
        "change_set_id": "cs-1",
        "case_id": "case-1",
        "apply_status": "pending",
        "base_entity_revision": 7,
        "before_patch": {"attributes.phone": "old"},
        "after_patch": {"attributes.phone": "new"},
        "risk_class": "not-a-risk",
        "decision_maker_ref": "person:maker",
        "evidence_refs": ["e-1"],
        "reviewer_ref": None,
    }
    digest = _build_command_digest("case-1", ("item-1",), _actor(), 7, ("e-1",))
    payload = {
        "event_id": event_id,
        "case_id": "case-1",
        "revision": 8,
        "generation": "8",
        "correlation_id": "corr-proof",
        "change_set_id": "cs-1",
        "item_ids": ["item-1"],
        "build_digest": digest,
        "risk_class": "not-a-risk",
    }

    class Tx:
        def load_change_set_for_items(self, *_args, **_kwargs):
            return existing

        def load_outbox_by_idempotency_key(self, _key):
            return {"idempotency_key": event_id, "payload": payload}

    with pytest.raises(correction.CorrectionRejected) as excinfo:
        _replay_existing_change_set(
            Tx(), "case-1", ("item-1",), _actor(), 7, ("e-1",),
            SimpleNamespace(current_revision=8),
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_change_set_replay_rejects_risk_class_not_bound_to_persisted_item():
    from cases import correction
    from cases.correction import _build_command_digest, _replay_existing_change_set

    event_id = "notify:cs-1:decided"
    existing = {
        "change_set_id": "cs-1",
        "case_id": "case-1",
        "apply_status": "pending",
        "base_entity_revision": 7,
        "before_patch": {"attributes.phone": "old"},
        "after_patch": {"attributes.phone": "new"},
        "risk_class": "R1",
        "decision_maker_ref": "person:maker",
        "evidence_refs": ["e-1"],
        "reviewer_ref": None,
    }
    digest = _build_command_digest("case-1", ("item-1",), _actor(), 7, ("e-1",))
    payload = {
        "event_id": event_id,
        "case_id": "case-1",
        "revision": 8,
        "generation": "8",
        "correlation_id": "corr-proof",
        "change_set_id": "cs-1",
        "item_ids": ["item-1"],
        "build_digest": digest,
        "risk_class": "R1",
    }

    class Tx:
        def load_change_set_for_items(self, *_args, **_kwargs):
            return existing

        def load_outbox_by_idempotency_key(self, _key):
            return {"idempotency_key": event_id, "payload": payload}

        def load_change_set_target(self, _change_set_id):
            return "entity-1", ("item-1",)

        def load_correction_item_payloads(self, _case_id, _item_ids):
            return ({
                "item_id": "item-1",
                "field_path": "attributes.phone",
                "risk_class": "R3",
            },)

    with pytest.raises(correction.CorrectionRejected) as excinfo:
        _replay_existing_change_set(
            Tx(), "case-1", ("item-1",), _actor(), 7, ("e-1",),
            SimpleNamespace(current_revision=8),
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"


def test_verification_replay_rejects_bad_failure_receipt_before_post_deadline_mutation(monkeypatch):
    from cases import publication
    from cases.publication import PublicationRejected, VerifyProjectionCommand, verify_public_projection

    event_id = "notify:change-1:verification_failed"
    existing = {
        "idempotency_key": event_id,
        "payload": {
            "event_id": event_id,
            "case_id": "another-case",
            "generation": "4",
            "correlation_id": "corr-proof",
            "revision": 4,
            "mismatched": [],
            "next_update_at": (NOW - timedelta(hours=1)).isoformat(),
        },
    }
    calls = []

    class Tx:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def load_change_set(self, _change_set_id, *, for_update=False):
            return {
                "case_id": "case-1",
                "apply_status": "applied",
                "public_projection_verified_at": None,
            }

        def load_case(self, _case_id, *, for_update=False):
            return SimpleNamespace(current_revision=3)

        def load_outbox_by_idempotency_key(self, _key):
            return existing

        def actor_holds_lease(self, *_args, **_kwargs):
            calls.append("lease")
            raise AssertionError("malformed receipt must fail before lease acquisition")

    class Store:
        def transaction(self):
            return Tx()

    monkeypatch.setattr(publication, "_store", lambda: Store())
    monkeypatch.setattr(publication, "_require_enabled", lambda: None)
    monkeypatch.setattr(publication, "_require_scope", lambda *_args, **_kwargs: None)

    with pytest.raises(PublicationRejected) as excinfo:
        verify_public_projection(
            VerifyProjectionCommand("case-1", "change-1", _actor()),
            lambda _entity_id: (_ for _ in ()).throw(AssertionError("must not fetch")),
            now=NOW,
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"
    assert calls == []


@pytest.mark.parametrize("deadline", ["not-a-date", "2026-09-01T10:00:00"])
def test_verification_replay_rejects_a_malformed_recovery_deadline(deadline):
    from cases.publication import (
        PublicationRejected,
        VerifyProjectionCommand,
        _replay_verification_failure,
    )

    existing = {
        "idempotency_key": "notify:change-1:verification_failed",
        "payload": {
            "event_id": "notify:change-1:verification_failed",
            "case_id": "case-1",
            "generation": "4",
            "correlation_id": "corr-proof",
            "revision": 4,
            "mismatched": ["revision"],
            "next_update_at": deadline,
        },
    }
    with pytest.raises(PublicationRejected) as excinfo:
        _replay_verification_failure(
            SimpleNamespace(),
            VerifyProjectionCommand("case-1", "change-1", _actor()),
            SimpleNamespace(),
            existing,
        )
    assert excinfo.value.problem.code == "publication_receipt_invalid"
