from datetime import datetime, timezone

from cases.audit import CaseAuditDraft
from cases.domain import ActorContext, Channel


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
