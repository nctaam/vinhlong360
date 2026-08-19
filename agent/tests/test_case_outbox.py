"""At-least-once notification dispatch: one logical delivery, safe copy, no rollback."""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.outbox import (  # noqa: E402
    DeliveryResult,
    DispatchSummary,
    configure_case_outbox,
    dispatch_case_outbox,
    notification_message,
)
from cases.security import CaseCrypto  # noqa: E402
from cases.store import OutboxDraft, PostgresCaseStore  # noqa: E402

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


class _FakeProvider:
    """Never a real network call in a case test."""

    def __init__(self, script=None) -> None:
        self.script = list(script or [])
        self.sent = []

    def send(self, phone, message, *, delivery_key):
        self.sent.append((phone, message, delivery_key))
        outcome = self.script.pop(0) if self.script else DeliveryResult(True, None, False)
        return outcome


@pytest.fixture
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
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM case_outbox", ())
        conn.commit()
    return adapter


def _reference(case_id: str) -> str:
    digits = hashlib.sha256(case_id.encode()).hexdigest().upper()
    body = "".join(c for c in digits if c in "0123456789ABCDEFGHJKMNPQRSTVWXYZ")[:13]
    return f"VL-COR-{body}"


def _case(adapter, *, phase="intake") -> str:
    with adapter._conn(commit_on_success=False) as conn:
        row = adapter._fetchone(
            conn,
            """
            INSERT INTO cases (service_kind, category, phase, activity, disposition_family,
                               reporter_privacy, owner_ref, current_revision, promise_policy_ref)
            VALUES ('correction','correction',%s,'active','undetermined','anonymous',
                    'person:owner',1,'correction-pilot-v1')
            RETURNING case_id
            """,
            (phase,),
        )
        case_id = str(row["case_id"])
        # A live receipt is what supplies the public reference the message quotes.
        adapter._execute(
            conn,
            """
            INSERT INTO case_receipts (case_id, public_reference, capability_digest,
                                       capability_key_version, receipt_revision,
                                       expires_at, created_at)
            VALUES (%s, %s, %s, 'v1', 1, NOW() + interval '365 days', NOW())
            """,
            (case_id, _reference(case_id), hashlib.sha256(case_id.encode()).hexdigest()),
        )
        conn.commit()
    return case_id


def _enqueue(adapter, case_id, *, key, available_at=NOW) -> None:
    store = PostgresCaseStore(adapter)
    with store.transaction() as transaction:
        transaction.enqueue_outbox(
            OutboxDraft(
                case_id=case_id,
                idempotency_key=key,
                topic="correction.received",
                descriptor={"reason": "received", "policy_revision": "correction-pilot-v1"},
                available_at=available_at,
            )
        )


def _row(adapter, key) -> dict:
    with adapter._conn(commit_on_success=False) as conn:
        return dict(
            adapter._fetchone(
                conn,
                "SELECT status, attempts, last_error_code, available_at"
                " FROM case_outbox WHERE idempotency_key=%s",
                (key,),
            )
        )


# ── Message safety: pure, no database ──

def test_the_message_carries_only_a_reference_and_generic_copy():
    message = notification_message(
        public_reference="VL-COR-ABCDEFGHJKMN0", topic="correction.received"
    )

    assert "VL-COR-ABCDEFGHJKMN0" in message
    for forbidden in (
        "0270", "0901234567", "capability", "evidence", "proposed",
        "person:owner", "triage",
    ):
        assert forbidden not in message
    assert len(message) <= 320


def test_an_unknown_topic_never_invents_copy():
    with pytest.raises(ValueError, match="unknown_outbox_topic"):
        notification_message(public_reference="VL-COR-X", topic="correction.secret_leak")


# ── Dispatch ──

@pg_only
def test_a_transient_failure_retries_and_then_delivers_once(pg_database):
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:retry:1")
    provider = _FakeProvider([
        DeliveryResult(False, "provider_timeout", True),
        DeliveryResult(True, None, False),
    ])
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    first = dispatch_case_outbox(now=NOW)
    after_first = _row(pg_database, "notify:retry:1")
    second = dispatch_case_outbox(now=NOW + timedelta(minutes=30))

    assert type(first) is DispatchSummary
    assert first.retried == 1 and first.sent == 0
    assert after_first["status"] == "pending"
    assert after_first["attempts"] == 1
    assert after_first["available_at"] > NOW           # backed off, not hammered
    assert second.sent == 1
    assert _row(pg_database, "notify:retry:1")["status"] == "sent"
    # One logical delivery even though the provider was called twice.
    assert len({key for _, _, key in provider.sent}) == 1


@pg_only
def test_a_permanent_failure_dead_letters_without_touching_the_case(pg_database):
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:dead:1")
    provider = _FakeProvider([DeliveryResult(False, "provider_rejected", False)])
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    summary = dispatch_case_outbox(now=NOW)

    row = _row(pg_database, "notify:dead:1")
    assert summary.dead_lettered == 1
    assert row["status"] == "failed"
    assert row["last_error_code"] == "provider_rejected"
    with pg_database._conn(commit_on_success=False) as conn:
        still_there = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM cases WHERE case_id=%s", (case_id,)
        )["n"]
    assert still_there == 1


@pg_only
def test_consent_withdrawn_after_enqueue_suppresses_the_delivery(pg_database):
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:muted:1")
    provider = _FakeProvider()
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: None,   # consent gone by delivery time
    )

    summary = dispatch_case_outbox(now=NOW)

    row = _row(pg_database, "notify:muted:1")
    assert summary.suppressed == 1
    assert provider.sent == []
    assert row["status"] == "failed"
    assert row["last_error_code"] == "suppressed_at_delivery"


@pg_only
def test_an_item_that_is_not_due_yet_is_left_alone(pg_database):
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:later:1", available_at=NOW + timedelta(hours=2))
    provider = _FakeProvider()
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    summary = dispatch_case_outbox(now=NOW)

    assert summary.claimed == 0
    assert provider.sent == []


@pg_only
def test_the_claim_uses_skip_locked_so_two_workers_never_double_send(pg_database):
    import inspect

    from cases import outbox

    source = inspect.getsource(outbox.dispatch_case_outbox) + inspect.getsource(outbox._claim)
    assert "FOR UPDATE SKIP LOCKED" in source


@pg_only
def test_the_delivery_key_is_deterministic_for_one_item(pg_database):
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:key:1")
    provider = _FakeProvider([DeliveryResult(False, "provider_timeout", True),
                              DeliveryResult(True, None, False)])
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    dispatch_case_outbox(now=NOW)
    dispatch_case_outbox(now=NOW + timedelta(minutes=30))

    keys = [key for _, _, key in provider.sent]
    assert len(keys) == 2 and keys[0] == keys[1]


@pg_only
def test_provider_failures_are_observed_as_capacity_events(pg_database, monkeypatch):
    events = []
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append((kind, kw.get("channel"))) or True)
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:observe:1")
    provider = _FakeProvider([DeliveryResult(False, "provider_rejected", False)])
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    dispatch_case_outbox(now=NOW)

    # The failure demand ledger sees what the reporter felt: the provider broke.
    assert ("provider_failure", "sms") in events


@pg_only
def test_a_delivered_notification_is_the_reporter_being_updated(pg_database, monkeypatch):
    events = []
    monkeypatch.setattr("cases.metrics.observe",
                        lambda kind, **kw: events.append(kind) or True)
    case_id = _case(pg_database)
    _enqueue(pg_database, case_id, key="notify:updated:1")
    provider = _FakeProvider([DeliveryResult(True, None, False)])
    configure_case_outbox(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=provider,
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    dispatch_case_outbox(now=NOW)

    # Updated means the word reached them, not that we queued the word.
    assert events == ["updated"]
