import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from cases.audit import CaseAuditDraft
from cases.domain import ActorContext, CasePhase, Channel, CorrectionOutcome


def test_case_audit_sorts_actor_scopes_deterministically():
    actor = ActorContext(
        actor_ref="person:operator",
        channel=Channel.WEB,
        scopes=frozenset(("case:write", "case:read")),
        correlation_id="correlation-1",
    )
    draft = CaseAuditDraft(
        case_id="11111111-1111-1111-1111-111111111111",
        actor_ref=actor.actor_ref,
        actor_scopes=tuple(sorted(actor.scopes)),
        channel=actor.channel,
        reason_code="case_created",
        policy_revision="correction-pilot-v1",
        correlation_id=actor.correlation_id,
        before_snapshot=None,
        after_snapshot={"phase": "intake", "current_revision": 1},
        occurred_at=datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc),
    )

    assert draft.actor_scopes == ("case:read", "case:write")


@pytest.mark.parametrize(
    "snapshot",
    (
        {"phase": {"contact": "reporter@example.test"}},
        {"severity": {"evidence": "private"}},
        {"promise_policy_ref": {"capability": "secret"}},
        {"phase": object()},
        {"phase": b"intake"},
        {"severity": float("nan")},
        {"severity": float("inf")},
        {"phase": CasePhase.INTAKE},
        {"created_at": datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc)},
    ),
)
def test_direct_audit_rejects_noncanonical_or_nested_safe_fields(snapshot):
    with pytest.raises(ValueError, match="unsafe_case_audit_snapshot"):
        CaseAuditDraft(
            case_id="11111111-1111-1111-1111-111111111111",
            actor_ref="person:operator",
            actor_scopes=("case:read",),
            channel=Channel.WEB,
            reason_code="case_created",
            policy_revision="correction-pilot-v1",
            correlation_id="correlation-1",
            before_snapshot=None,
            after_snapshot=snapshot,
            occurred_at=datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc),
        )


def test_safe_projection_is_canonical_json_before_database_insertion():
    from agent.tests.test_case_store import snapshot
    from cases.audit import safe_case_projection

    projection = safe_case_projection(snapshot())

    assert projection["phase"] == "intake"
    assert projection["created_at"] == "2026-08-12T09:00:00+00:00"
    assert json.loads(json.dumps(projection, allow_nan=False)) == projection


def test_safe_projection_canonicalizes_normal_domain_enum_values():
    from agent.tests.test_case_store import snapshot
    from cases.audit import safe_case_projection

    projection = safe_case_projection(
        replace(snapshot(), domain_outcome=CorrectionOutcome.CORRECTED)
    )

    assert projection["domain_outcome"] == "corrected"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        # Ghim 3 nhóm kiểm-tra sau khi tách (lát 7 R20.8): scope không-sort,
        # scope trùng, scope rỗng, channel sai kiểu, occurred_at naive.
        ("actor_scopes", ("case:write", "case:read")),
        ("actor_scopes", ("case:read", "case:read")),
        ("actor_scopes", ("",)),
        ("channel", "web"),
        ("occurred_at", datetime(2026, 8, 12, 9, 0)),
    ),
)
def test_case_audit_rejects_invalid_identity_label_and_time_fields(field, value):
    valid = dict(
        case_id="11111111-1111-1111-1111-111111111111",
        actor_ref="person:operator",
        actor_scopes=("case:read",),
        channel=Channel.WEB,
        reason_code="case_created",
        policy_revision="correction-pilot-v1",
        correlation_id="correlation-1",
        before_snapshot=None,
        after_snapshot=None,
        occurred_at=datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc),
    )
    valid[field] = value
    with pytest.raises(ValueError, match="invalid_case_audit"):
        CaseAuditDraft(**valid)
