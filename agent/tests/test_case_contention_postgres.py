"""Two actors at the same instant, against a real database.

Everything this branch claims about contention — FOR UPDATE SKIP LOCKED,
compare-and-set revisions, a lease that only one worker can hold — has until now
been asserted by reading the SQL text. A string containing "SKIP LOCKED" is not
evidence that two workers cannot both send the same message; it is evidence that
somebody typed it.

These start real threads on real connections behind a barrier, then assert the
durable invariant rather than a scheduling accident: exactly one message and
exactly one write. A separate lock test deliberately holds one transaction open
so the ``change_set_busy`` branch is exercised under genuine overlap; a caller
that arrives after commit is an ordinary idempotent replay and is allowed to
receive the committed result.
"""
from __future__ import annotations

import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pg_test_database import TEST_DATABASE_URL, pg_only  # noqa: E402

MASTER_KEY = "0" * 43
UTC = timezone.utc
RACERS = 8


def _now():
    return datetime.now(UTC)


@pg_only
def test_community_cas_and_due_lease_have_one_winner(pg):
    """Real PG proof for the community state primitives (not a SQL-text check)."""
    from control_plane.concurrency import StateConflict, cas_transition, claim_due

    with pg._conn() as conn:
        user = pg._fetchone(conn, "INSERT INTO users(phone,password_hash,username,role,is_active) VALUES (%s,%s,%s,'user',true) RETURNING id", ("090" + uuid.uuid4().hex[:8], "x", "cas-" + uuid.uuid4().hex[:8]))
        post = pg._fetchone(conn, "INSERT INTO posts(user_id,content,post_type,moderation_status,scheduled_at) VALUES (%s,%s,'share','pending',%s) RETURNING id", (str(user["id"]), "community CAS proof", _now() - timedelta(minutes=1)))
        post_id = str(post["id"])

    class Tx:
        _db = pg
        def __init__(self, conn): self._conn = conn

    barrier = threading.Barrier(2)
    leases = []
    def claim(index):
        with pg._conn(commit_on_success=False) as conn:
            barrier.wait()
            leases.append(claim_due(Tx(conn), "posts", due_before=_now(), worker_id=f"community-{index}", lease_seconds=30))
            conn.commit()
    threads = [threading.Thread(target=claim, args=(i,)) for i in range(2)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=30)
    assert sum(lease is not None for lease in leases) == 1

    with pg._conn() as conn:
        pg._execute(conn, "UPDATE posts SET claim_expires_at=NULL, claimed_by=NULL WHERE id=%s", (post_id,))
    outcomes = []
    def decide(index):
        with pg._conn(commit_on_success=False) as conn:
            try:
                outcomes.append(cas_transition(Tx(conn), "posts", post_id, expected_status="pending", new_status="approved", actor_id=f"mod-{index}", reason="proof", correlation_id=f"proof-{index}"))
            except StateConflict as exc:
                outcomes.append(exc)
            conn.commit()
    threads = [threading.Thread(target=decide, args=(i,)) for i in range(2)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=30)
    assert sum(not isinstance(item, Exception) for item in outcomes) == 1
    assert sum(isinstance(item, StateConflict) and item.status_code == 409 for item in outcomes) == 1
    with pg._conn() as conn:
        pg._execute(conn, "DELETE FROM posts WHERE id=%s", (post_id,))
        pg._execute(conn, "DELETE FROM users WHERE id=%s", (str(user["id"]),))


@pytest.fixture
def pg():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    import database

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter


def race(work, count: int = RACERS):
    """Run `work(index)` on `count` threads that all start at the same instant.

    The barrier is the point. Without it the first thread finishes before the
    second begins and the test proves only that the code runs twice.
    """
    barrier = threading.Barrier(count)
    results: list = [None] * count
    errors: list = [None] * count

    def run(index):
        barrier.wait(timeout=30)
        try:
            results[index] = work(index)
        except BaseException as error:  # noqa: BLE001 - the refusal is the data
            errors[index] = error

    threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert not any(thread.is_alive() for thread in threads), "a racer never finished"
    return results, errors


def _case(adapter) -> str:
    with adapter._conn(commit_on_success=False) as conn:
        case_id = str(adapter._fetchone(
            conn,
            "INSERT INTO cases (service_kind, category, phase, activity,"
            " disposition_family, reporter_privacy, owner_ref, current_revision,"
            " promise_policy_ref) VALUES ('correction','correction','decision','active',"
            "'undetermined','anonymous','person:owner',1,'correction-pilot-v1')"
            " RETURNING case_id",
            (),
        )["case_id"])
        conn.commit()
    return case_id


def test_the_barrier_actually_overlaps_the_racers():
    """The harness, guarded: a race that serialises proves nothing."""
    inside = []
    peak = [0]
    lock = threading.Lock()

    def work(_index):
        with lock:
            inside.append(1)
            peak[0] = max(peak[0], len(inside))
        threading.Event().wait(0.05)
        with lock:
            inside.pop()
        return True

    results, errors = race(work, count=4)

    assert peak[0] >= 2, "the threads never overlapped, so no test here races anything"
    assert all(results) and not any(errors)


@pg_only
def test_only_one_operator_can_hold_one_work_item(pg):
    from cases.policy import load_case_policy
    from cases.work_control import claim_work_item, configure_case_work_control

    configure_case_work_control(database=pg, policy=load_case_policy())
    case_id = _case(pg)
    with pg._conn(commit_on_success=False) as conn:
        work_id = str(pg._fetchone(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class,"
            " status, ready_at, priority) VALUES (%s,'decide','case_operator','R1',"
            "'ready',%s,0) RETURNING work_item_id",
            (case_id, _now()),
        )["work_item_id"])
        conn.commit()

    from cases.domain import ActorContext, Channel

    def work(index):
        actor = ActorContext(actor_ref=f"person:{index}", channel=Channel.WEB,
                             scopes=frozenset({"service.operator"}),
                             correlation_id=f"race-{index}")
        return claim_work_item(work_id, actor, expected_revision=1, now=_now())

    results, errors = race(work)

    winners = [item for item in results if item is not None]
    # Two operators believing they hold the same item is how two rulings get
    # written on one report, each unaware of the other.
    assert len(winners) == 1, f"{len(winners)} operators think they hold it"
    assert len([e for e in errors if e is not None]) == RACERS - 1
    with pg._conn(commit_on_success=False) as conn:
        row = dict(pg._row_to_dict(pg._fetchone(
            conn,
            "SELECT status, assignee_ref, revision FROM case_work_items"
            " WHERE work_item_id=%s",
            (work_id,),
        )))
    assert row["status"] == "claimed"
    assert row["assignee_ref"] == winners[0].assignee_ref
    # One claim, one revision bump: a lost update would leave this at 1.
    assert int(row["revision"]) == 2


@pg_only
def test_change_set_lock_rejects_a_transaction_that_is_still_in_flight(pg):
    """The busy response is proven while the first transaction is open.

    A later call after commit is intentionally a replay, so the thread race
    tests below cannot use response count as their concurrency invariant.
    """
    from cases.store import PostgresCaseStore

    change_set_id = f"lock-race-{uuid.uuid4()}"
    store = PostgresCaseStore(pg)
    with store.transaction() as first:
        assert first.try_change_set_lock(change_set_id)
        with store.transaction() as second:
            assert not second.try_change_set_lock(change_set_id)


@pg_only
def test_racing_dispatchers_never_send_one_notification_twice(pg):
    from cases.outbox import configure_case_outbox, dispatch_case_outbox
    from cases.security import CaseCrypto
    from cases.store import OutboxDraft, PostgresCaseStore

    case_id = _case(pg)
    with pg._conn(commit_on_success=False) as conn:
        pg._execute(
            conn,
            "INSERT INTO case_receipts (case_id, public_reference, capability_digest,"
            " capability_key_version, receipt_revision, expires_at)"
            " VALUES (%s,%s,%s,'v1',1,%s)",
            (case_id, f"VL-COR-{uuid.uuid4().hex[:13]}", uuid.uuid4().hex * 2,
             _now() + timedelta(days=30)),
        )
        conn.commit()
    store = PostgresCaseStore(pg)
    key = f"race:{uuid.uuid4()}"
    with store.transaction() as transaction:
        transaction.enqueue_outbox(OutboxDraft(
            case_id=case_id, idempotency_key=key,
            topic="correction.received",
            descriptor={"reason": "received", "policy_revision": "correction-pilot-v1"},
            available_at=_now() - timedelta(minutes=1),
        ))
    with pg._conn(commit_on_success=False) as conn:
        mine = str(pg._fetchone(
            conn, "SELECT outbox_id FROM case_outbox WHERE idempotency_key=%s", (key,),
        )["outbox_id"])

    sent = []
    lock = threading.Lock()

    class _Provider:
        def send(self, phone, message, *, delivery_key=""):
            from sms_provider import SmsDeliveryResult

            with lock:
                sent.append(delivery_key)
            return SmsDeliveryResult(True, None, False)

    configure_case_outbox(
        database=pg, crypto=CaseCrypto(MASTER_KEY), provider=_Provider(),
        contact_lookup=lambda case_id, **_: "0901234567",
    )

    results, errors = race(lambda index: dispatch_case_outbox(now=_now(), limit=50))

    # Counted for THIS row, not for the database. The disposable database
    # carries queued rows from every other suite, so a total would be a number
    # about the fixture rather than about the lease — the first version of this
    # assertion said 34 and meant nothing.
    from cases.outbox import delivery_key

    mine_sent = [entry for entry in sent if entry == delivery_key(mine)]
    # Every message here goes to somebody's phone. Sending one twice is not a
    # performance problem, it is two texts to a person who reported one thing.
    assert len(mine_sent) == 1, f"the same notification went out {len(mine_sent)} times"
    assert not [e for e in errors if e is not None]
    with pg._conn(commit_on_success=False) as conn:
        row = dict(pg._row_to_dict(pg._fetchone(
            conn,
            "SELECT status, attempts FROM case_outbox WHERE outbox_id=%s", (mine,),
        )))
    # One send, one attempt: two dispatchers both settling it would show here.
    assert row["status"] == "sent"
    assert int(row["attempts"]) == 1


@pg_only
def test_racing_applies_write_the_entry_once(pg):
    from cases.correction import build_change_set, configure_case_correction
    from cases.domain import Channel
    from cases.policy import load_case_policy
    from cases.publication import (
        ApplyChangeSetCommand,
        apply_change_set,
        configure_case_publication,
    )
    from cases.security import CaseCrypto
    from config import settings

    crypto = CaseCrypto(MASTER_KEY)
    policy = load_case_policy()
    configure_case_correction(database=pg, crypto=crypto, policy=policy)
    configure_case_publication(database=pg, crypto=crypto, policy=policy)
    original = settings.CORRECTION_PUBLICATION_ENABLED
    settings.CORRECTION_PUBLICATION_ENABLED = True
    entity_id = f"p-race-{uuid.uuid4().hex[:8]}"
    try:
        case_id = _case(pg)
        now = _now()
        with pg._conn(commit_on_success=False) as conn:
            pg._execute(
                conn,
                "INSERT INTO entities (id, type, name, attributes, revision)"
                " VALUES (%s,'place','Bến Đò',%s,3)",
                (entity_id, '{"phone": "0270 111 2222"}'),
            )
            item_id = str(pg._fetchone(
                conn,
                "INSERT INTO correction_items (case_id, entity_id, field_path,"
                " reported_value_enc, proposed_value_enc, base_entity_revision,"
                " risk_class, evidence_level) VALUES (%s,%s,'attributes.phone',%s,%s,3,"
                "'R1','E3') RETURNING item_id",
                (case_id, entity_id,
                 crypto.encrypt_private_payload({"value": "0270 111 2222"}),
                 crypto.encrypt_private_payload({"value": "0270 333 4444"})),
            )["item_id"])
            pg._execute(
                conn,
                "INSERT INTO case_work_items (case_id, kind, required_role, risk_class,"
                " status, assignee_ref, lease_expires_at, ready_at, priority)"
                " VALUES (%s,'decide','case_operator','R1','claimed','person:maker',%s,%s,0)",
                (case_id, now + timedelta(hours=2), now),
            )
            pg._execute(
                conn,
                "INSERT INTO case_decisions (case_id, item_id, outcome_code, reason_code,"
                " evidence_refs, decision_maker_ref, policy_revision, decided_at)"
                " VALUES (%s,%s,'corrected','source_confirms_change','[\"e-1\"]'::jsonb,"
                " 'person:maker','correction-pilot-v1',%s)",
                (case_id, item_id, now),
            )
            conn.commit()

        class _Maker:
            actor_ref = "person:maker"
            reviewer_ref = None
            scopes = ("cases:work", "cases:decide", "publication.apply")
            channel = Channel.WEB
            correlation_id = "race"

        build_change_set(case_id, (item_id,), _Maker(), expected_revision=1,
                         evidence_refs=("e-1",), now=now)
        with pg._conn(commit_on_success=False) as conn:
            change_set_id = str(pg._fetchone(
                conn,
                "SELECT change_set_id FROM correction_change_sets WHERE case_id=%s",
                (case_id,),
            )["change_set_id"])
            revision = int(pg._fetchone(
                conn, "SELECT current_revision FROM cases WHERE case_id=%s", (case_id,),
            )["current_revision"])
            pg._execute(
                conn,
                "UPDATE case_work_items SET status='claimed', assignee_ref='person:maker',"
                " lease_expires_at=%s WHERE case_id=%s",
                (now + timedelta(hours=2), case_id),
            )
            conn.commit()

        def work(_index):
            return apply_change_set(
                ApplyChangeSetCommand(
                    case_id=case_id, change_set_id=change_set_id,
                    expected_case_revision=revision, expected_entity_revision=3,
                    actor=_Maker(),
                ),
                now=_now(),
            )

        results, errors = race(work, count=4)

        applied = [item for item in results if item is not None]
        # A caller that reaches the transaction after commit may replay the
        # durable receipt. The invariant is one mutation, not one response.
        assert 1 <= len(applied) <= 4
        assert all(item == applied[0] for item in applied)
        assert all(
            getattr(getattr(error, "problem", None), "code", None) == "change_set_busy"
            for error in errors if error is not None
        )
        with pg._conn(commit_on_success=False) as conn:
            live = dict(pg._row_to_dict(pg._fetchone(
                conn, "SELECT attributes, revision FROM entities WHERE id=%s", (entity_id,),
            )))
            changes = int(pg._fetchone(
                conn,
                "SELECT count(*) AS n FROM entity_changes WHERE entity_id=%s", (entity_id,),
            )["n"])
        assert "0270 333 4444" in str(live["attributes"])
        # Exactly one revision past the base, and exactly one change row.
        assert int(live["revision"]) == 4
        assert changes == 1
    finally:
        settings.CORRECTION_PUBLICATION_ENABLED = original
        configure_case_correction(database=None, crypto=None, policy=None)
        configure_case_publication(database=None, crypto=None, policy=None)


@pg_only
def test_racing_rollbacks_undo_the_entry_once(pg):
    """Two operators both reaching for undo on a correction that went live.

    Rollback is the other writer to the public page, and the one somebody
    reaches for in a hurry — a complaint, a retracted source, a wrong call. Two
    of them landing would replay the inverse patch twice and leave two audit
    rows each claiming to be the moment the page was put back.
    """
    from cases.correction import configure_case_correction
    from cases.domain import Channel
    from cases.policy import load_case_policy
    from cases.publication import (
        ApplyChangeSetCommand,
        RollbackChangeSetCommand,
        apply_change_set,
        configure_case_publication,
        rollback_change_set,
    )
    from cases.security import CaseCrypto
    from config import settings

    crypto = CaseCrypto(MASTER_KEY)
    policy = load_case_policy()
    configure_case_correction(database=pg, crypto=crypto, policy=policy)
    configure_case_publication(database=pg, crypto=crypto, policy=policy)
    original = settings.CORRECTION_PUBLICATION_ENABLED
    settings.CORRECTION_PUBLICATION_ENABLED = True
    entity_id = f"p-undo-{uuid.uuid4().hex[:8]}"
    try:
        case_id, change_set_id, revision = _decided_change_set(pg, crypto, entity_id)

        class _Maker:
            actor_ref = "person:maker"
            reviewer_ref = None
            scopes = ("cases:work", "cases:decide", "publication.apply")
            channel = Channel.WEB
            correlation_id = "race-undo"

        apply_change_set(
            ApplyChangeSetCommand(
                case_id=case_id, change_set_id=change_set_id,
                expected_case_revision=revision, expected_entity_revision=3,
                actor=_Maker(),
            ),
            now=_now(),
        )
        with pg._conn(commit_on_success=False) as conn:
            # Rollback carries no expected revision: it is a compare-and-set on
            # the change set's own apply_status, which is what makes racing
            # undos safe without the caller having to hold a revision.
            pg._execute(
                conn,
                "UPDATE case_work_items SET status='claimed', assignee_ref='person:maker',"
                " lease_expires_at=%s WHERE case_id=%s",
                (_now() + timedelta(hours=2), case_id),
            )
            conn.commit()

        def work(_index):
            return rollback_change_set(
                RollbackChangeSetCommand(
                    case_id=case_id, change_set_id=change_set_id,
                    actor=_Maker(), reason_code="source_withdrawn",
                ),
                now=_now(),
            )

        results, errors = race(work, count=4)

        undone = [item for item in results if item is not None]
        # As with apply, post-commit callers may receive the idempotent
        # rollback receipt; only the durable inverse write must happen once.
        assert 1 <= len(undone) <= 4
        assert all(item == undone[0] for item in undone)
        assert all(
            getattr(getattr(error, "problem", None), "code", None) == "change_set_busy"
            for error in errors if error is not None
        )
        with pg._conn(commit_on_success=False) as conn:
            live = dict(pg._row_to_dict(pg._fetchone(
                conn, "SELECT attributes, revision FROM entities WHERE id=%s", (entity_id,),
            )))
            changes = int(pg._fetchone(
                conn,
                "SELECT count(*) AS n FROM entity_changes WHERE entity_id=%s", (entity_id,),
            )["n"])
        assert "0270 111 2222" in str(live["attributes"])
        # Base 3, applied 4, undone 5 — forward only, and two writes total.
        assert int(live["revision"]) == 5
        assert changes == 2
    finally:
        settings.CORRECTION_PUBLICATION_ENABLED = original
        configure_case_correction(database=None, crypto=None, policy=None)
        configure_case_publication(database=None, crypto=None, policy=None)


def _decided_change_set(pg, crypto, entity_id: str):
    """A case decided and built, ready to publish — the state before apply."""
    from cases.correction import build_change_set
    from cases.domain import Channel

    case_id = _case(pg)
    now = _now()
    with pg._conn(commit_on_success=False) as conn:
        pg._execute(
            conn,
            "INSERT INTO entities (id, type, name, attributes, revision)"
            " VALUES (%s,'place','Bến Đò',%s,3)",
            (entity_id, '{"phone": "0270 111 2222"}'),
        )
        item_id = str(pg._fetchone(
            conn,
            "INSERT INTO correction_items (case_id, entity_id, field_path,"
            " reported_value_enc, proposed_value_enc, base_entity_revision,"
            " risk_class, evidence_level) VALUES (%s,%s,'attributes.phone',%s,%s,3,"
            "'R1','E3') RETURNING item_id",
            (case_id, entity_id,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"})),
        )["item_id"])
        pg._execute(
            conn,
            "INSERT INTO case_work_items (case_id, kind, required_role, risk_class,"
            " status, assignee_ref, lease_expires_at, ready_at, priority)"
            " VALUES (%s,'decide','case_operator','R1','claimed','person:maker',%s,%s,0)",
            (case_id, now + timedelta(hours=2), now),
        )
        pg._execute(
            conn,
            "INSERT INTO case_decisions (case_id, item_id, outcome_code, reason_code,"
            " evidence_refs, decision_maker_ref, policy_revision, decided_at)"
            " VALUES (%s,%s,'corrected','source_confirms_change','[\"e-1\"]'::jsonb,"
            " 'person:maker','correction-pilot-v1',%s)",
            (case_id, item_id, now),
        )
        conn.commit()

    class _Maker:
        actor_ref = "person:maker"
        reviewer_ref = None
        scopes = ("cases:work", "cases:decide", "publication.apply")
        channel = Channel.WEB
        correlation_id = "race-setup"

    build_change_set(case_id, (item_id,), _Maker(), expected_revision=1,
                     evidence_refs=("e-1",), now=now)
    with pg._conn(commit_on_success=False) as conn:
        change_set_id = str(pg._fetchone(
            conn,
            "SELECT change_set_id FROM correction_change_sets WHERE case_id=%s",
            (case_id,),
        )["change_set_id"])
        revision = int(pg._fetchone(
            conn, "SELECT current_revision FROM cases WHERE case_id=%s", (case_id,),
        )["current_revision"])
        pg._execute(
            conn,
            "UPDATE case_work_items SET status='claimed', assignee_ref='person:maker',"
            " lease_expires_at=%s WHERE case_id=%s",
            (now + timedelta(hours=2), case_id),
        )
        conn.commit()
    return case_id, change_set_id, revision
