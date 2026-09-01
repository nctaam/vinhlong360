"""Correction intake: validation, safety routing, and the canonical create command."""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.domain import ActorContext, Channel, CommandEnvelope  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.rate_limit import check_case_rate_limit, rate_subject_digest  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402
from cases.service import (  # noqa: E402
    CaseService,
    CorrectionItemInput,
    CorrectionRejected,
    CreateCorrectionCommand,
    CreateCorrectionResult,
    SafetyRoutingRequired,
    ZaloHandoff,
)
from cases.store import PostgresCaseStore  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
MASTER_KEY = "0" * 43


def _validated_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _validated_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


@pytest.fixture(scope="module")
def pg_database():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter


@pytest.fixture(scope="module", autouse=True)
def seeded_entity(request):
    """Seed the FK target and clear the durable buckets this module fills.

    The rate buckets are deliberately durable, so a previous run at the same
    fixed clock would otherwise leave this module blocked before it starts.
    """
    if TEST_DATABASE_URL is None:
        return None
    adapter = request.getfixturevalue("pg_database")
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, revision) VALUES (%s,'place','Vĩnh Long',1)"
            " ON CONFLICT (id) DO NOTHING",
            ("p-vinh-long",),
        )
        adapter._execute(conn, "DELETE FROM shared_rate_limits WHERE key LIKE %s", ("case:%",))
        adapter._execute(
            conn, "DELETE FROM case_idempotency WHERE idempotency_key LIKE %s", ("create:%",)
        )
        conn.commit()
    return "p-vinh-long"


def _service(adapter=None) -> CaseService:
    return CaseService(
        store=PostgresCaseStore(adapter) if adapter is not None else None,
        crypto=CaseCrypto(MASTER_KEY),
        policy=load_case_policy(),
        owner_ref="person:case-owner",
        database=adapter,
    )


def _actor(scopes=(), channel=Channel.WEB) -> ActorContext:
    return ActorContext(
        actor_ref="anonymous",
        channel=channel,
        scopes=frozenset(scopes),
        correlation_id="corr-create-1",
    )


def _envelope(key: str = "idem-create-1", scopes=(), channel=Channel.WEB) -> CommandEnvelope:
    return CommandEnvelope(
        idempotency_key=key,
        expected_revision=None,
        actor=_actor(scopes, channel),
    )


def _item(field_path: str = "attributes.phone", **overrides) -> CorrectionItemInput:
    base = CorrectionItemInput(
        entity_id="p-vinh-long",
        field_path=field_path,
        reported_value="0270 111 2222",
        proposed_value="0270 333 4444",
        base_entity_revision=7,
    )
    return replace(base, **overrides) if overrides else base


def _command(**overrides) -> CreateCorrectionCommand:
    base = CreateCorrectionCommand(
        envelope=_envelope(),
        reporter_privacy="anonymous",
        items=(_item(),),
    )
    return replace(base, **overrides) if overrides else base


# ── Validation and routing: these must fail before any transaction opens ──

def test_public_create_rejects_an_operator_actor():
    command = _command(envelope=_envelope(scopes=("cases:operate",)))

    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(command, now=NOW, rate_subject="test")

    assert excinfo.value.problem.code == "operator_actor_not_allowed"
    assert excinfo.value.problem.status == 403


def test_create_rejects_a_client_supplied_user_reference():
    """The linkage may only come from the server-side session, never the body."""
    command = _command(authenticated_user_ref="user:attacker")

    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(command, now=NOW, rate_subject="test", session_user_ref=None)

    assert excinfo.value.problem.code == "authenticated_ref_not_server_derived"


def test_create_rejects_a_user_reference_that_contradicts_the_session():
    command = _command(authenticated_user_ref="user:attacker")

    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(command, now=NOW, rate_subject="test", session_user_ref="user:real")

    assert excinfo.value.problem.code == "authenticated_ref_not_server_derived"


@pytest.mark.parametrize(
    ("items", "code"),
    [
        ((), "correction_items_required"),
        (tuple(_item() for _ in range(11)), "too_many_correction_items"),
        ((_item(field_path="attributes.__proto__"),), "field_path_not_correctable"),
        ((_item(field_path="verifiedAt"),), "field_path_not_correctable"),
        ((_item(proposed_value="x" * 2001),), "correction_value_too_long"),
        ((_item(proposed_value="0270 111 2222"),), "correction_value_unchanged"),
        ((_item(base_entity_revision=0),), "invalid_base_entity_revision"),
        ((_item(), _item()), "duplicate_correction_field"),
        # Thứ tự reject là hợp đồng (lát 11 R20.8): field_path hỏng thắng
        # entity_id hỏng; entity_id hỏng thắng value hỏng.
        ((_item(field_path="verifiedAt", entity_id=""),), "field_path_not_correctable"),
        ((_item(entity_id="", proposed_value=""),), "invalid_correction_entity"),
        ((_item(proposed_value="", base_entity_revision=0),), "invalid_correction_value"),
    ],
)
def test_create_enforces_bounded_multi_item_fields(items, code):
    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(_command(items=items), now=NOW, rate_subject="test")

    assert excinfo.value.problem.code == code


@pytest.mark.parametrize(
    "reported",
    ["Có người dọa giết chủ quán", "this is an emergency, someone is dying"],
)
def test_emergency_language_routes_to_the_safety_lane_without_creating_a_case(reported):
    command = _command(items=(_item(reported_value=reported),))

    with pytest.raises(SafetyRoutingRequired) as excinfo:
        _service().create_correction(command, now=NOW, rate_subject="test")

    problem = excinfo.value.problem
    assert problem.code == "correction_safety_routing"
    assert problem.status == 409
    # Must hand over to the real emergency services, never claim to be one.
    assert "113" in excinfo.value.safe_message
    assert "vinhlong360" not in excinfo.value.safe_message.lower()


def test_zalo_handoff_requires_explicit_confirmation_and_carries_no_transcript():
    unconfirmed = _command(
        envelope=_envelope(channel=Channel.ZALO_AI_HANDOFF),
        handoff=ZaloHandoff(conversation_digest="d" * 64, user_confirmed=False),
    )

    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(unconfirmed, now=NOW, rate_subject="test")

    assert excinfo.value.problem.code == "handoff_confirmation_required"

    with pytest.raises(ValueError):
        ZaloHandoff(conversation_digest="d" * 64, user_confirmed=True, transcript="raw chat")


def test_optional_phone_is_never_treated_as_identity():
    command = _command(optional_phone="0901234567", notification_consent=True)
    service = _service()

    assert service.identity_assurance_for(command) == "none"
    assert service.reporter_privacy_for(command) == "anonymous"
    assert service.party_authority_draft_for(command, case_id="c-1", now=NOW) is None


# ── Durable rate limiting ──

@pg_only
def test_rate_limit_is_shared_across_service_instances(pg_database):
    subject = rate_subject_digest("203.0.113.7", master_key=MASTER_KEY)
    bucket = "correction_create_test"
    for _ in range(3):
        check_case_rate_limit(
            bucket, subject, limit=3, window=60, now=NOW, database=pg_database
        )

    # A fresh process would build a new service object; the bucket must survive it.
    allowed = check_case_rate_limit(
        bucket, subject, limit=3, window=60, now=NOW, database=pg_database
    )

    assert allowed is False
    assert check_case_rate_limit(
        bucket, subject, limit=3, window=60, now=NOW + timedelta(seconds=61),
        database=pg_database,
    ) is True


@pg_only
def test_create_is_rate_limited_per_subject(pg_database):
    service = _service(pg_database)
    for index in range(service.create_rate_limit):
        service.create_correction(
            _command(envelope=_envelope(key=f"rl-{index}")),
            now=NOW,
            rate_subject="198.51.100.9",
        )

    with pytest.raises(CorrectionRejected) as excinfo:
        service.create_correction(
            _command(envelope=_envelope(key="rl-over")), now=NOW, rate_subject="198.51.100.9"
        )

    assert excinfo.value.problem.code == "case_rate_limited"
    assert excinfo.value.problem.status == 429


# ── Canonical create ──

@pg_only
def test_anonymous_create_commits_the_whole_case_atomically(pg_database):
    service = _service(pg_database)

    result = service.create_correction(
        _command(envelope=_envelope(key="anon-create-1")),
        now=NOW,
        rate_subject="192.0.2.11",
    )

    assert type(result) is CreateCorrectionResult
    assert result.replayed is False
    assert result.public_reference.startswith("VL-COR-")
    assert len(result.capability) == 43
    assert result.received_at == NOW
    assert result.next_update_at == NOW + timedelta(seconds=259200)
    assert result.revision == 1
    assert result.outbox_event_id == f"notify:{result.case_id}:received"

    with pg_database._conn(commit_on_success=False) as conn:
        counts = {
            table: pg_database._fetchone(
                conn, f"SELECT count(*) AS n FROM {table} WHERE case_id=%s", (result.case_id,)
            )["n"]
            for table in (
                "case_interactions", "correction_items", "correction_evidence",
                "case_promise_clocks", "case_work_items", "case_transitions",
                "case_audit_events", "case_receipts", "case_outbox",
            )
        }
    assert counts["case_interactions"] == 1
    assert counts["correction_items"] == 1
    assert counts["correction_evidence"] == 1
    assert counts["case_promise_clocks"] == 4
    assert counts["case_work_items"] == 1
    assert counts["case_transitions"] == 1
    assert counts["case_audit_events"] == 1
    assert counts["case_receipts"] == 1
    assert counts["case_outbox"] == 1


@pg_only
def test_create_rejects_an_unknown_entity_without_a_driver_error(pg_database):
    service = _service(pg_database)

    with pytest.raises(CorrectionRejected) as excinfo:
        service.create_correction(
            _command(
                envelope=_envelope(key="unknown-entity-1"),
                items=(_item(entity_id="p-does-not-exist"),),
            ),
            now=NOW,
            rate_subject="192.0.2.15",
        )

    assert excinfo.value.problem.code == "correction_entity_unknown"
    assert excinfo.value.problem.status == 404


@pg_only
def test_create_persists_no_plaintext_reported_value(pg_database):
    service = _service(pg_database)
    secret = "0270 555 6666"

    result = service.create_correction(
        _command(envelope=_envelope(key="enc-create-1"), items=(_item(proposed_value=secret),)),
        now=NOW,
        rate_subject="192.0.2.12",
    )

    with pg_database._conn(commit_on_success=False) as conn:
        row = pg_database._fetchone(
            conn,
            "SELECT reported_value_enc, proposed_value_enc FROM correction_items WHERE case_id=%s",
            (result.case_id,),
        )
        outbox = pg_database._fetchone(
            conn, "SELECT payload::text AS payload FROM case_outbox WHERE case_id=%s", (result.case_id,)
        )
    assert secret not in str(row["reported_value_enc"]) + str(row["proposed_value_enc"])
    assert secret not in str(outbox["payload"])
    assert result.capability not in str(outbox["payload"])


@pg_only
def test_authenticated_create_links_the_session_user(pg_database):
    service = _service(pg_database)

    result = service.create_correction(
        _command(
            envelope=_envelope(key="auth-create-1"),
            reporter_privacy="attributed",
            authenticated_user_ref="user:42",
        ),
        now=NOW,
        session_user_ref="user:42",
        rate_subject="192.0.2.13",
    )

    with pg_database._conn(commit_on_success=False) as conn:
        authority = pg_database._fetchone(
            conn,
            "SELECT party_ref, authority_kind FROM case_party_authorities WHERE case_id=%s",
            (result.case_id,),
        )
        receipt = pg_database._fetchone(
            conn, "SELECT subject_user_id FROM case_receipts WHERE case_id=%s", (result.case_id,)
        )
    assert authority["party_ref"] == "user:42"
    assert authority["authority_kind"] == "account_owner"
    assert str(receipt["subject_user_id"]) == "user:42"


@pg_only
def test_receipt_failure_rolls_the_whole_case_back(pg_database):
    service = _service(pg_database)

    class ExplodingCrypto(CaseCrypto):
        def issue_capability(self) -> str:
            raise RuntimeError("receipt_unavailable")

    service._crypto = ExplodingCrypto(MASTER_KEY)
    with pg_database._conn(commit_on_success=False) as conn:
        before = pg_database._fetchone(conn, "SELECT count(*) AS n FROM cases")["n"]

    with pytest.raises(RuntimeError):
        service.create_correction(
            _command(envelope=_envelope(key="rollback-1")), now=NOW, rate_subject="192.0.2.14"
        )

    with pg_database._conn(commit_on_success=False) as conn:
        after = pg_database._fetchone(conn, "SELECT count(*) AS n FROM cases")["n"]
    assert after == before


@pg_only
def test_a_signed_in_reporter_filing_anonymously_keeps_an_unbound_receipt(pg_database):
    """bug_002: binding the receipt to the session locks them out after logout."""
    service = _service(pg_database)

    result = service.create_correction(
        _command(envelope=_envelope(key="anon-while-signed-in-1")),
        now=NOW,
        session_user_ref="user:77",          # signed in ...
        rate_subject="192.0.2.41",
    )                                         # ... but authenticated_user_ref stays None

    with pg_database._conn(commit_on_success=False) as conn:
        receipt = pg_database._fetchone(
            conn, "SELECT subject_user_id FROM case_receipts WHERE case_id=%s", (result.case_id,)
        )
        case = pg_database._fetchone(
            conn, "SELECT reporter_privacy FROM cases WHERE case_id=%s", (result.case_id,)
        )
        authority = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM case_party_authorities WHERE case_id=%s",
            (result.case_id,),
        )
    assert receipt["subject_user_id"] is None
    assert case["reporter_privacy"] == "anonymous"
    assert authority["n"] == 0
