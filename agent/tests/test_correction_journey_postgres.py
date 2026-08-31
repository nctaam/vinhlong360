"""The whole road, walked on a real database — and the fences between cases.

One journey end to end: an anonymous report becomes a case, is decided, built,
applied to the live entry, verified against the public projection, and the
reporter's own status page finally says corrected-and-visible. Then the fences:
user A's credentials, cookie and account link open user A's case and nothing
else, and every wrong key fails the same neutral way.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.domain import ActorContext, Channel  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402
from cases.service import (  # noqa: E402
    CaseService,
    CommandEnvelope,
    CorrectionItemInput,
    CorrectionRejected,
    CreateCorrectionCommand,
)
from cases.security import CaseSecurityError  # noqa: E402
from cases.store import PostgresCaseStore  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
MASTER_KEY = "0" * 43
ENTITY_ID = "p-journey"




# One loopback-only rule for every suite that opens the disposable database.
from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402


@pytest.fixture
def journey(monkeypatch):
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    from cases.correction import configure_case_correction
    from cases.publication import configure_case_publication
    from config import settings

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        # This suite reports at a frozen NOW, so its rate-limit hits never age
        # out of the window: run it twice against the same disposable database
        # and the second run is throttled by the first. Start from clean.
        adapter._execute(conn, "DELETE FROM shared_rate_limits WHERE key LIKE %s", ("case:%",))
        adapter._execute(conn, "DELETE FROM entity_changes WHERE entity_id=%s", (ENTITY_ID,))
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, attributes, revision)"
            " VALUES (%s,'place','Bến Đò Cổ Chiên',%s,3)"
            " ON CONFLICT (id) DO UPDATE SET revision=3, attributes=EXCLUDED.attributes",
            (ENTITY_ID, '{"phone": "0270 111 2222"}'),
        )
        conn.commit()
    crypto = CaseCrypto(MASTER_KEY)
    policy = load_case_policy()
    service = CaseService(PostgresCaseStore(adapter), crypto, policy,
                          owner_ref="person:owner", database=adapter)
    configure_case_correction(database=adapter, crypto=crypto, policy=policy)
    configure_case_publication(database=adapter, crypto=crypto, policy=policy)
    monkeypatch.setattr(settings, "CORRECTION_PUBLICATION_ENABLED", True, raising=False)
    yield adapter, service
    configure_case_correction(database=None, crypto=None, policy=None)
    configure_case_publication(database=None, crypto=None, policy=None)


def _report(service, *, subject: str, user_ref: str | None = None):
    return service.create_correction(
        CreateCorrectionCommand(
            envelope=CommandEnvelope(
                idempotency_key=f"journey:{uuid.uuid4()}",
                expected_revision=None,
                actor=ActorContext(actor_ref=user_ref or "anonymous", channel=Channel.WEB,
                                   scopes=frozenset(), correlation_id="journey"),
            ),
            reporter_privacy="anonymous",
            items=(CorrectionItemInput(
                entity_id=ENTITY_ID, field_path="attributes.phone",
                reported_value="0270 111 2222", proposed_value="0270 333 4444",
                base_entity_revision=3,
            ),),
            authenticated_user_ref=user_ref,
        ),
        now=NOW, rate_subject=subject, session_user_ref=user_ref,
    )


def _drive_to_verified(adapter, case_id: str) -> None:
    """Decide, build, apply and verify — the operator half of the journey."""
    from cases.correction import build_change_set
    from cases.publication import (
        ApplyChangeSetCommand,
        VerifyProjectionCommand,
        apply_change_set,
        verify_public_projection,
    )

    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class,"
            " status, assignee_ref, lease_expires_at, ready_at, priority)"
            " VALUES (%s,'decide','case_operator','R1','claimed',%s,%s,%s,0)",
            (case_id, "person:maker", NOW + timedelta(hours=2), NOW),
        )
        conn.commit()

    class _Maker:
        actor_ref = "person:maker"
        reviewer_ref = None
        scopes = ("cases:work", "cases:decide")
        channel = Channel.WEB
        correlation_id = "journey"

    with adapter._conn(commit_on_success=False) as conn:
        item_id = str(adapter._fetchone(
            conn, "SELECT item_id FROM correction_items WHERE case_id=%s", (case_id,)
        )["item_id"])
        revision = int(adapter._fetchone(
            conn, "SELECT current_revision FROM cases WHERE case_id=%s", (case_id,)
        )["current_revision"])

    # The ruling itself, on real evidence — the step a shortcut would skip, and
    # the one the reporter's status page reads its answer from.
    from cases.correction import AddEvidenceCommand, add_evidence, decide_item
    from cases.correction import DecideItemCommand, load_evidence_records
    from cases.domain import CorrectionOutcome, EvidenceLevel, RiskClass

    add_evidence(
        AddEvidenceCommand(
            case_id=case_id, item_id=item_id, level=EvidenceLevel.E3,
            source_scope="place.contact", source_ref="https://a.example",
            descriptor={}, content=None, actor=_Maker(),
            observed_at=NOW - timedelta(days=1), effective_at=NOW - timedelta(days=1),
            expires_at=NOW + timedelta(days=30), asserted_value="0270 333 4444",
        ),
        now=NOW,
    )
    decide_item(
        DecideItemCommand(
            case_id=case_id, item_id=item_id,
            outcome_code=CorrectionOutcome.CORRECTED,
            reason_code="source_confirms_change",
            evidence=load_evidence_records(case_id, item_id),
            risk_class=RiskClass.R1, actor=_Maker(),
            required_scope="place.contact",
        ),
        now=NOW,
    )
    build_change_set(case_id, (item_id,), _Maker(), expected_revision=revision,
                     evidence_refs=("e-1",), now=NOW)

    with adapter._conn(commit_on_success=False) as conn:
        change_set_id = str(adapter._fetchone(
            conn, "SELECT change_set_id FROM correction_change_sets WHERE case_id=%s",
            (case_id,),
        )["change_set_id"])
        adapter._execute(
            conn,
            "UPDATE case_work_items SET status='claimed', assignee_ref=%s,"
            " lease_expires_at=%s WHERE case_id=%s AND kind='publication'",
            ("person:publisher", NOW + timedelta(hours=2), case_id),
        )
        revision = int(adapter._fetchone(
            conn, "SELECT current_revision FROM cases WHERE case_id=%s", (case_id,)
        )["current_revision"])
        conn.commit()

    publisher = ActorContext(
        actor_ref="person:publisher", channel=Channel.WEB,
        scopes=frozenset({"cases:work", "publication.apply", "publication.verify"}),
        correlation_id="journey",
    )
    apply_change_set(
        ApplyChangeSetCommand(case_id=case_id, change_set_id=change_set_id,
                              actor=publisher, expected_case_revision=revision,
                              expected_entity_revision=3),
        now=NOW,
    )
    verify_public_projection(
        VerifyProjectionCommand(case_id=case_id, change_set_id=change_set_id,
                                actor=publisher),
        lambda entity_id: {
            "id": ENTITY_ID, "revision": 4,
            "attributes": {"phone": "0270 333 4444"},
            "source": {"name": "Ban biên tập vinhlong360"},
        },
        now=NOW + timedelta(minutes=5),
    )


# ── The whole road ──

@pg_only
def test_an_anonymous_report_travels_to_corrected_and_visible(journey):
    adapter, service = journey
    receipt = _report(service, subject="journey-happy")

    _drive_to_verified(adapter, receipt.case_id)

    grant = service.exchange_receipt(
        public_reference=receipt.public_reference, capability=receipt.capability,
        rate_subject="journey-happy", now=NOW + timedelta(minutes=10),
    )
    status = service.public_status(access_token=grant.access_token,
                                   now=NOW + timedelta(minutes=11))

    # The reporter's own page says both facts: decided, and visibly published.
    assert status.public_reference == receipt.public_reference
    assert [str(d.disposition_family) for d in status.item_decisions] == ["action_taken"]
    assert [str(p.state) for p in status.item_publication_states] == ["verified"]

    with adapter._conn(commit_on_success=False) as conn:
        live = adapter._fetchone(
            conn, "SELECT attributes::text AS a, revision FROM entities WHERE id=%s",
            (ENTITY_ID,),
        )
    assert "0270 333 4444" in live["a"] and live["revision"] == 4


# ── The fences ──

@pg_only
def test_a_capability_opens_its_own_case_and_no_other(journey):
    adapter, service = journey
    case_a = _report(service, subject="fence-a")
    case_b = _report(service, subject="fence-b")

    with pytest.raises((CorrectionRejected, CaseSecurityError)):
        # A's key against B's reference: the pairing is the credential.
        service.exchange_receipt(
            public_reference=case_b.public_reference, capability=case_a.capability,
            rate_subject="fence-a", now=NOW + timedelta(minutes=1),
        )


@pg_only
def test_one_cookie_reads_one_case_and_nothing_leaks_across(journey):
    adapter, service = journey
    case_a = _report(service, subject="cookie-a")
    case_b = _report(service, subject="cookie-b")

    grant_a = service.exchange_receipt(
        public_reference=case_a.public_reference, capability=case_a.capability,
        rate_subject="cookie-a", now=NOW + timedelta(minutes=1),
    )
    status = service.public_status(access_token=grant_a.access_token,
                                   now=NOW + timedelta(minutes=2))

    assert status.public_reference == case_a.public_reference
    assert status.public_reference != case_b.public_reference


@pg_only
def test_an_account_bound_case_refuses_a_different_signed_in_user(journey):
    adapter, service = journey
    case_a = _report(service, subject="account-a", user_ref="user:1001")

    # User B, signed in, holding A's stolen pair: the account binding refuses.
    with pytest.raises((CorrectionRejected, CaseSecurityError)):
        service.exchange_receipt(
            public_reference=case_a.public_reference, capability=case_a.capability,
            rate_subject="account-b", session_user_ref="user:2002",
            now=NOW + timedelta(minutes=1),
        )


@pg_only
def test_every_wrong_key_fails_the_same_neutral_way(journey):
    adapter, service = journey
    case_a = _report(service, subject="neutral-a")

    seen = []
    for capability in ("A" * 43, "B" * 43):
        try:
            service.exchange_receipt(
                public_reference=case_a.public_reference, capability=capability,
                rate_subject="neutral-a", now=NOW + timedelta(minutes=1),
            )
        except Exception as error:  # noqa: BLE001 - the shape is the assertion
            seen.append(type(error).__name__)
    # Wrong and differently-wrong read identically: nothing confirms a near miss.
    assert len(seen) == 2 and len(set(seen)) == 1


@pg_only
def test_coming_back_for_the_same_case_is_counted_as_failure_demand(journey, monkeypatch):
    adapter, service = journey
    events = []
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append(kind) or True)
    receipt = _report(service, subject="repeat-a")
    grant = service.exchange_receipt(
        public_reference=receipt.public_reference, capability=receipt.capability,
        rate_subject="repeat-a", now=NOW + timedelta(minutes=1),
    )
    assert "repeated_contact" not in events, "the first visit is the service working"

    rotated = service.rotate_receipt(
        access_token=grant.access_token, rate_subject="repeat-a",
        now=NOW + timedelta(minutes=2),
    )
    service.exchange_receipt(
        public_reference=rotated.public_reference, capability=rotated.capability,
        rate_subject="repeat-a", now=NOW + timedelta(minutes=3),
    )

    # The second successful opening of the same case is the reporter having to
    # come back: the first answer did not settle it.
    assert events.count("repeated_contact") == 1
