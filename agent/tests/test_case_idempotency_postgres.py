"""Encrypted lost-response replay for correction create, against real PostgreSQL."""
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
from cases.security import CaseCrypto  # noqa: E402
from cases.service import (  # noqa: E402
    CaseService,
    CorrectionItemInput,
    CreateCorrectionCommand,
    IdempotencyConflict,
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
    """Seed the FK target and clear the durable state this module asserts on.

    Replay rows and rate buckets are meant to survive a restart, so a previous
    run at the same fixed clock would make the first create look like a replay.
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


def _service(adapter) -> CaseService:
    return CaseService(
        store=PostgresCaseStore(adapter),
        crypto=CaseCrypto(MASTER_KEY),
        policy=load_case_policy(),
        owner_ref="person:case-owner",
        database=adapter,
    )


def _command(key: str, **overrides) -> CreateCorrectionCommand:
    base = CreateCorrectionCommand(
        envelope=CommandEnvelope(
            idempotency_key=key,
            expected_revision=None,
            actor=ActorContext(
                actor_ref="anonymous",
                channel=Channel.WEB,
                scopes=frozenset(),
                correlation_id="corr-idem",
            ),
        ),
        reporter_privacy="anonymous",
        items=(
            CorrectionItemInput(
                entity_id="p-vinh-long",
                field_path="attributes.phone",
                reported_value="0270 111 2222",
                proposed_value="0270 333 4444",
                base_entity_revision=7,
            ),
        ),
    )
    return replace(base, **overrides) if overrides else base


@pg_only
def test_exact_retry_replays_the_original_receipt_without_a_second_case(pg_database):
    service = _service(pg_database)
    command = _command("idem-replay-1")

    first = service.create_correction(command, now=NOW, rate_subject="192.0.2.21")
    second = service.create_correction(
        command, now=NOW + timedelta(seconds=30), rate_subject="192.0.2.21"
    )

    assert first.replayed is False
    assert second.replayed is True
    assert (second.case_id, second.public_reference, second.capability) == (
        first.case_id, first.public_reference, first.capability
    )
    with pg_database._conn(commit_on_success=False) as conn:
        cases = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM cases WHERE case_id=%s", (first.case_id,)
        )["n"]
        receipts = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM case_receipts WHERE case_id=%s", (first.case_id,)
        )["n"]
    assert (cases, receipts) == (1, 1)


@pg_only
def test_same_key_with_a_different_body_is_a_conflict(pg_database):
    service = _service(pg_database)
    service.create_correction(_command("idem-conflict-1"), now=NOW, rate_subject="192.0.2.22")

    divergent = _command(
        "idem-conflict-1",
        items=(
            CorrectionItemInput(
                entity_id="p-vinh-long",
                field_path="attributes.phone",
                reported_value="0270 111 2222",
                proposed_value="0270 999 0000",
                base_entity_revision=7,
            ),
        ),
    )

    with pytest.raises(IdempotencyConflict) as excinfo:
        service.create_correction(divergent, now=NOW, rate_subject="192.0.2.22")

    assert excinfo.value.problem.code == "idempotency_conflict"
    assert excinfo.value.problem.status == 409


@pg_only
def test_replay_expires_after_twenty_four_hours_without_creating_a_second_case(pg_database):
    service = _service(pg_database)
    command = _command("idem-expiry-1")
    first = service.create_correction(command, now=NOW, rate_subject="192.0.2.23")

    with pytest.raises(IdempotencyConflict) as excinfo:
        service.create_correction(
            command, now=NOW + timedelta(hours=24, seconds=1), rate_subject="192.0.2.23"
        )

    assert excinfo.value.problem.code == "idempotency_expired"
    assert excinfo.value.problem.status == 409
    # No secret recovery channel: the expired reply must not hand the capability back.
    assert first.capability not in str(excinfo.value.problem.detail)
    with pg_database._conn(commit_on_success=False) as conn:
        cases = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM cases WHERE case_id=%s", (first.case_id,)
        )["n"]
    assert cases == 1


@pg_only
def test_replay_is_scoped_to_the_original_actor(pg_database):
    service = _service(pg_database)
    command = _command("idem-actor-1")
    service.create_correction(command, now=NOW, rate_subject="192.0.2.24")

    other_actor = replace(
        command,
        envelope=replace(
            command.envelope,
            actor=replace(command.envelope.actor, actor_ref="user:99"),
        ),
        authenticated_user_ref="user:99",
    )

    with pytest.raises(IdempotencyConflict):
        service.create_correction(
            other_actor, now=NOW, session_user_ref="user:99", rate_subject="192.0.2.24"
        )
