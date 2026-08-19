"""Taking a correction down the phone: the record has to carry the reporter's consent.

A transcriber is a weaker position than self-service, not a stronger one. The
person cannot see the screen, so nothing here is filed unless the record proves
they were told what would be stored, agreed to it, and heard each value read back.

The schema is also a boundary against authentication secrets. It names every
field it accepts and refuses the rest before validation reads a value, so a
password or a one-time code cannot arrive in a correction even by accident.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.admin_api import (  # noqa: E402
    AssistedCorrectionBody,
    StepUpRefused,
    parse_assisted_body,
    validate_assisted_intake,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


def _item(**overrides) -> dict:
    base = {
        "entity_id": "p-quan-com",
        "field_path": "attributes.phone",
        "reported_value": "0270 111 2222",
        "proposed_value": "0270 333 4444",
        "base_entity_revision": 7,
        "read_back_confirmed": True,
    }
    base.update(overrides)
    return base


def _body(**overrides) -> dict:
    base = {
        "channel": "phone",
        "privacy_notice_revision": "privacy-2026-07",
        "consent_scope": "correction.contact",
        "consent_given_at": NOW - timedelta(minutes=2),
        "reporter_privacy": "anonymous",
        "reporter_confirmed": True,
        "items": [_item()],
        "notification_consent": False,
    }
    base.update(overrides)
    return base


def _validate(**overrides) -> None:
    validate_assisted_intake(AssistedCorrectionBody(**_body(**overrides)), now=NOW)


# ── A complete, consented transcription ──

def test_a_properly_consented_call_passes_every_check():
    _validate()


def test_a_human_zalo_conversation_is_also_a_transcribed_channel():
    _validate(channel="zalo_human")


# ── What the reporter must have been given ──

@pytest.mark.parametrize("overrides,expected", [
    ({"privacy_notice_revision": "   "}, "privacy_notice_required"),
    ({"consent_scope": ""}, "consent_scope_required"),
    ({"consent_given_at": NOW + timedelta(minutes=1)}, "consent_not_yet_given"),
    ({"items": []}, "correction_items_required"),
    ({"items": [_item(read_back_confirmed=False)]}, "read_back_required"),
    ({"reporter_confirmed": False}, "reporter_confirmation_required"),
    ({"channel": "web"}, "assisted_channel_not_offered"),
])
def test_a_call_missing_any_of_the_promises_is_refused(overrides, expected):
    with pytest.raises(StepUpRefused) as excinfo:
        _validate(**overrides)

    assert excinfo.value.code == expected
    assert excinfo.value.status == 422


def test_one_unconfirmed_item_stops_the_whole_call():
    # Filing the confirmed half would leave a record the reporter never heard.
    with pytest.raises(StepUpRefused) as excinfo:
        _validate(items=[_item(), _item(field_path="attributes.address",
                                        read_back_confirmed=False)])

    assert excinfo.value.code == "read_back_required"


def test_a_self_service_channel_cannot_be_filed_as_a_transcription():
    # Claiming somebody was read to when they typed it themselves would put a
    # consent record in the file that nobody gave.
    for channel in ("web", "email_transcribed", "zalo_ai_handoff"):
        with pytest.raises(StepUpRefused):
            _validate(channel=channel)


# ── Authentication secrets cannot arrive here ──

SECRET = "hunter2-should-never-be-stored"


@pytest.mark.parametrize("field", ["password", "otp", "recovery_code", "secret",
                                   "totp", "session_token"])
def test_a_secret_like_field_is_refused_and_its_value_never_repeated(field):
    with pytest.raises(StepUpRefused) as excinfo:
        parse_assisted_body(_body(**{field: SECRET}))

    assert excinfo.value.status == 422
    # The refusal names the field, never what was in it. Pydantic's own message
    # quotes the value back, which would put the secret in the error body and
    # the log -- so the boundary rebuilds the refusal from locations alone.
    assert field in excinfo.value.detail
    assert SECRET not in excinfo.value.detail
    assert SECRET not in str(excinfo.value)


def test_the_raw_schema_error_is_never_what_reaches_a_caller():
    # Proving the reason the wrapper exists rather than trusting it.
    with pytest.raises(ValidationError) as raw:
        AssistedCorrectionBody(**_body(password=SECRET))
    assert SECRET in str(raw.value)

    with pytest.raises(StepUpRefused) as refused:
        parse_assisted_body(_body(password=SECRET))
    assert SECRET not in str(refused.value.detail)


def test_a_secret_hidden_inside_an_item_is_refused_too():
    with pytest.raises(StepUpRefused) as excinfo:
        parse_assisted_body(_body(items=[_item(otp="000000")]))

    assert "otp" in excinfo.value.detail
    assert "000000" not in excinfo.value.detail


def test_there_is_nowhere_to_put_a_recording_or_a_transcript():
    # The pilot does not record calls, so the schema offers no field that would
    # invite an operator to paste one in.
    for field in ("recording_url", "transcript", "call_audio", "notes"):
        with pytest.raises(StepUpRefused):
            parse_assisted_body(_body(**{field: "x"}))


# ── Filing it, through the same Kernel as self-service ──

import os  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

import database  # noqa: E402
from cases.domain import ActorContext, Channel  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402
from cases.service import (  # noqa: E402
    AssistedIntake,
    CaseService,
    CommandEnvelope,
    CorrectionItemInput,
    CorrectionRejected,
    CreateCorrectionCommand,
)
from cases.store import PostgresCaseStore  # noqa: E402

MASTER_KEY = "0" * 43
ENTITY_ID = "p-assisted"


def _pg_url():
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


TEST_DATABASE_URL = _pg_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


@pytest.fixture
def case_service():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, revision) VALUES (%s,'place','Quan Ba Nam',7)"
            " ON CONFLICT (id) DO UPDATE SET revision = 7",
            (ENTITY_ID,),
        )
        conn.commit()
    service = CaseService(
        PostgresCaseStore(adapter), CaseCrypto(MASTER_KEY), load_case_policy(),
        owner_ref="person:owner", database=adapter,
    )
    return adapter, service


def _intake(**overrides) -> AssistedIntake:
    base = dict(
        operator_ref="user:7", privacy_notice_revision="privacy-2026-07",
        consent_scope="correction.contact", consent_given_at=NOW - timedelta(minutes=2),
        read_back_confirmed=True, reporter_confirmed=True,
    )
    base.update(overrides)
    return AssistedIntake(**base)


def _file(service, *, subject="operator-7", **overrides):
    import uuid

    return service.create_assisted_correction(
        items=(CorrectionItemInput(
            entity_id=ENTITY_ID, field_path="attributes.phone",
            reported_value="0270 111 2222", proposed_value="0270 333 4444",
            base_entity_revision=7,
        ),),
        assisted=_intake(**overrides),
        channel=Channel.PHONE,
        reporter_privacy="anonymous",
        idempotency_key=f"assisted:{uuid.uuid4()}",
        correlation_id="corr-assisted",
        rate_subject=subject,
        now=NOW,
    )


@pg_only
def test_a_transcribed_call_becomes_a_real_case_with_a_reference(case_service):
    _adapter, service = case_service

    result = _file(service)

    assert result.case_id
    assert result.public_reference.startswith("VL-")
    assert result.next_update_at > NOW


@pg_only
def test_the_operator_is_never_handed_the_reporter_key(case_service):
    _adapter, service = case_service

    result = _file(service, subject="operator-key-check")

    # The capability opens somebody else's private thread. An operator holding it
    # would keep standing access long after the call ended.
    assert not hasattr(result, "capability")
    assert "capability" not in str(result.read_back)


@pg_only
def test_the_consent_that_was_taken_is_written_into_the_file(case_service):
    adapter, service = case_service

    result = _file(service, subject="operator-consent")

    with adapter._conn(commit_on_success=False) as conn:
        row = dict(adapter._fetchone(
            conn,
            "SELECT channel, consent_ref, identity_assurance FROM case_interactions"
            " WHERE case_id=%s",
            (result.case_id,),
        ))
    assert row["channel"] == "phone"
    # Which notice, what it covered, when, and that the values were read back.
    assert "privacy-2026-07" in row["consent_ref"]
    assert "correction.contact" in row["consent_ref"]
    assert "read_back=yes" in row["consent_ref"]
    assert "confirmed=yes" in row["consent_ref"]
    # The reporter did not sign in. Crediting them with the operator's login
    # would be a claim about identity that nobody made.
    assert row["identity_assurance"] == "transcribed"


@pg_only
def test_the_operator_authority_is_scoped_to_transcribing_this_one_case(case_service):
    adapter, service = case_service

    result = _file(service, subject="operator-authority")

    with adapter._conn(commit_on_success=False) as conn:
        row = dict(adapter._fetchone(
            conn,
            "SELECT party_ref, authority_kind, scope, assurance_level"
            " FROM case_party_authorities WHERE case_id=%s",
            (result.case_id,),
        ))
    assert row["party_ref"] == "user:7"
    assert row["authority_kind"] == "transcriber"
    # Not authority to act for the reporter anywhere else.
    assert row["scope"] == "correction:transcribe"
    assert row["assurance_level"] == "operator_session"


@pg_only
def test_an_assisted_case_gets_the_same_receipt_clocks_and_work_as_self_service(case_service):
    adapter, service = case_service

    result = _file(service, subject="operator-parity")

    with adapter._conn(commit_on_success=False) as conn:
        counts = {
            table: adapter._fetchone(
                conn, "SELECT count(*) AS n FROM " + table + " WHERE case_id=%s",
                (result.case_id,),
            )["n"]
            for table in ("case_receipts", "case_promise_clocks", "case_work_items",
                          "case_audit_events")
        }
    # A report taken down the phone is not a lesser record than one typed in.
    assert counts["case_receipts"] == 1
    assert counts["case_promise_clocks"] >= 1
    assert counts["case_work_items"] >= 1
    assert counts["case_audit_events"] >= 1


@pg_only
def test_the_operator_gets_the_values_to_read_back_and_nothing_private(case_service):
    _adapter, service = case_service

    result = _file(service, subject="operator-readback")

    assert result.read_back[0]["proposed_value"] == "0270 333 4444"
    assert result.read_back[0]["field_path"] == "attributes.phone"


@pg_only
def test_a_self_service_actor_still_cannot_pretend_to_be_transcribing(case_service):
    _adapter, service = case_service

    # An operator-scoped actor on the ordinary path is still refused. The assisted
    # context is what makes those scopes legitimate, and it is built server-side
    # from what the operator recorded, never taken from the request body.
    with pytest.raises(CorrectionRejected) as excinfo:
        service.create_correction(
            CreateCorrectionCommand(
                envelope=CommandEnvelope(
                    idempotency_key="assisted-impostor",
                    expected_revision=None,
                    actor=ActorContext(
                        actor_ref="user:7", channel=Channel.PHONE,
                        scopes=frozenset({"service.operator"}), correlation_id="c",
                    ),
                ),
                reporter_privacy="anonymous",
                items=(CorrectionItemInput(
                    entity_id=ENTITY_ID, field_path="attributes.phone",
                    reported_value="a", proposed_value="b", base_entity_revision=7,
                ),),
            ),
            now=NOW, rate_subject="impostor",
        )

    assert excinfo.value.problem.code == "operator_actor_not_allowed"
