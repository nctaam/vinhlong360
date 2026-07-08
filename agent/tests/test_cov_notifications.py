"""
Coverage tests for agent/notifications.py — REAL behavioral tests.

Strategy:
  - Pure helpers (_group_notifications, _format_notif) are exercised directly
    with real inputs and asserted on real outputs.
  - _notify_sse / _next_event_id operate on module globals + real asyncio
    primitives — tested against real queue side-effects, no mocks of the SUT.
  - create_notification / _user_wants_notif contain the real branch logic
    (block / mute / preference / dedup / SSE dispatch). Only the DB I/O
    boundary (db._conn / db._fetchone) is monkeypatched; the LOGIC around it
    is what is asserted (which SQL fires, whether SSE is dispatched, early
    returns), never the mock's return value itself.
  - Pydantic models validate real business rules.

The FastAPI route handlers (get_notifications, toggle_follow, toggle_block,
toggle_rsvp, …) are thin async I/O wrappers guarded by a Postgres-only router
dependency; their inner logic is either trivial marshalling or is already
covered by the standalone helpers above. They require a live Postgres +
FastAPI dependency graph to run and are listed in pg_or_net_skipped.
"""

import contextlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio  # noqa: E402

import notifications  # noqa: E402
from database import db  # noqa: E402
from pydantic import ValidationError  # noqa: E402


# ── DB boundary helpers ──

@contextlib.contextmanager
def _fake_conn_cm():
    """A stand-in for db._conn() used as `with db._conn() as conn:`."""
    yield "CONN"


@pytest.fixture
def db_boundary(monkeypatch):
    """Patch the DB I/O boundary; monkeypatch auto-restores after each test.

    Returns a small controller so each test declares how fetchone responds
    per-SQL. _row_to_dict is made identity (rows are already dicts here).
    """
    monkeypatch.setattr(db, "_conn", _fake_conn_cm)
    monkeypatch.setattr(db, "_row_to_dict", lambda r: r)

    class Ctl:
        def __init__(self):
            self.responder = lambda sql, params: None
            self.seen_sql = []

        def set(self, fn):
            self.responder = fn

    ctl = Ctl()

    def _fetchone(conn, sql, params=None):
        ctl.seen_sql.append(sql)
        return ctl.responder(sql, params)

    monkeypatch.setattr(db, "_fetchone", _fetchone)
    return ctl


# ═══════════════════════════════════════════════════════════════════════
#  _group_notifications — dedup grouping within a 24h window
# ═══════════════════════════════════════════════════════════════════════

class TestGroupNotifications:
    def test_collapses_same_key_within_24h_and_counts(self):
        notifs = [
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "2026-06-10T10:00:00", "is_read": False},
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "2026-06-10T11:30:00", "is_read": False},
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "2026-06-10T12:00:00", "is_read": False},
        ]
        out = notifications._group_notifications(notifs)
        assert len(out) == 1
        # first (representative) accumulates a group_count for the 2 followers
        assert out[0]["group_count"] == 3

    def test_different_ref_id_not_grouped(self):
        notifs = [
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "2026-06-10T10:00:00"},
            {"type": "like", "ref_type": "post", "ref_id": "p2",
             "created_at": "2026-06-10T10:05:00"},
        ]
        out = notifications._group_notifications(notifs)
        assert len(out) == 2
        assert "group_count" not in out[0]

    def test_same_key_beyond_24h_kept_separate(self):
        notifs = [
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "2026-06-10T10:00:00"},
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "2026-06-12T10:00:00"},  # 48h later
        ]
        out = notifications._group_notifications(notifs)
        assert len(out) == 2

    def test_unparseable_dates_fall_through_to_separate_groups(self):
        # ValueError/TypeError in date parse must NOT crash; both kept.
        notifs = [
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "not-a-date"},
            {"type": "like", "ref_type": "post", "ref_id": "p1",
             "created_at": "also-bad"},
        ]
        out = notifications._group_notifications(notifs)
        assert len(out) == 2

    def test_none_created_at_does_not_crash(self):
        notifs = [
            {"type": "like", "ref_type": "post", "ref_id": "p1", "created_at": None},
            {"type": "like", "ref_type": "post", "ref_id": "p1", "created_at": None},
        ]
        out = notifications._group_notifications(notifs)
        # TypeError branch keeps them separate rather than merging
        assert len(out) == 2

    def test_missing_ref_fields_use_empty_string_key(self):
        # Two notifs with no ref_type/ref_id but same type -> same key -> group.
        notifs = [
            {"type": "system", "created_at": "2026-06-10T10:00:00"},
            {"type": "system", "created_at": "2026-06-10T10:01:00"},
        ]
        out = notifications._group_notifications(notifs)
        assert len(out) == 1
        assert out[0]["group_count"] == 2

    def test_empty_input_returns_empty(self):
        assert notifications._group_notifications([]) == []

    def test_z_suffix_iso_timestamp_parsed(self):
        # 'Z' is normalised to +00:00 so parsing succeeds and grouping applies.
        notifs = [
            {"type": "comment", "ref_type": "post", "ref_id": "p9",
             "created_at": "2026-06-10T10:00:00Z"},
            {"type": "comment", "ref_type": "post", "ref_id": "p9",
             "created_at": "2026-06-10T10:30:00Z"},
        ]
        out = notifications._group_notifications(notifs)
        assert len(out) == 1


# ═══════════════════════════════════════════════════════════════════════
#  _format_notif — row → API dict normalisation
# ═══════════════════════════════════════════════════════════════════════

class TestFormatNotif:
    def test_stringifies_ids_and_defaults(self):
        row = {"id": 123, "type": "like", "title": "T",
               "ref_id": 456, "created_at": "2026-06-10"}
        out = notifications._format_notif(row)
        assert out["id"] == "123"          # int -> str
        assert out["ref_id"] == "456"      # int -> str
        assert out["body"] is None         # missing -> None
        assert out["is_read"] is False     # missing -> default False
        assert out["ref_type"] is None
        assert out["created_at"] == "2026-06-10"

    def test_none_ref_id_stays_none_not_string_none(self):
        row = {"id": 1, "type": "x", "title": "t", "ref_id": None}
        out = notifications._format_notif(row)
        assert out["ref_id"] is None

    def test_missing_created_at_becomes_empty_string(self):
        row = {"id": 1, "type": "x", "title": "t"}
        assert notifications._format_notif(row)["created_at"] == ""

    def test_preserves_provided_body_and_is_read(self):
        row = {"id": 7, "type": "comment", "title": "hi",
               "body": "some body", "is_read": True, "created_at": "2026-01-01"}
        out = notifications._format_notif(row)
        assert out["body"] == "some body"
        assert out["is_read"] is True


# ═══════════════════════════════════════════════════════════════════════
#  _notify_sse — fan-out to per-user subscriber queues (no running loop path)
# ═══════════════════════════════════════════════════════════════════════

class TestNotifySSE:
    @pytest.fixture(autouse=True)
    def _clean_sse(self):
        saved = dict(notifications._sse_subscribers)
        saved_loop = notifications._sse_loop
        notifications._sse_subscribers.clear()
        notifications._sse_loop = None
        yield
        notifications._sse_subscribers.clear()
        notifications._sse_subscribers.update(saved)
        notifications._sse_loop = saved_loop

    def test_delivers_to_subscriber_queue(self):
        q = asyncio.Queue(maxsize=10)
        notifications._sse_subscribers["u1"] = [q]
        notifications._notify_sse("u1", {"id": "n1"})
        assert q.qsize() == 1
        assert q.get_nowait() == {"id": "n1"}

    def test_fans_out_to_multiple_queues(self):
        q1, q2 = asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)
        notifications._sse_subscribers["u2"] = [q1, q2]
        notifications._notify_sse("u2", {"id": "n2"})
        assert q1.qsize() == 1
        assert q2.qsize() == 1

    def test_unknown_user_is_noop(self):
        # No subscribers registered -> must not raise.
        notifications._notify_sse("ghost", {"id": "x"})
        assert "ghost" not in notifications._sse_subscribers

    def test_full_queue_drops_without_raising(self):
        q = asyncio.Queue(maxsize=1)
        notifications._sse_subscribers["u3"] = [q]
        notifications._notify_sse("u3", {"n": 1})  # fills queue
        # Second delivery hits QueueFull; must be swallowed, queue stays at cap.
        notifications._notify_sse("u3", {"n": 2})
        assert q.qsize() == 1

    def test_snapshot_isolation_from_concurrent_mutation(self):
        # _notify_sse copies the subscriber list under the thread lock; a queue
        # removed after the snapshot must still not raise. Here we just verify a
        # normal delivery does not mutate the subscriber registry.
        q = asyncio.Queue(maxsize=5)
        notifications._sse_subscribers["u4"] = [q]
        notifications._notify_sse("u4", {"n": 1})
        assert notifications._sse_subscribers["u4"] == [q]


# ═══════════════════════════════════════════════════════════════════════
#  _next_event_id — monotonic async counter
# ═══════════════════════════════════════════════════════════════════════

class TestNextEventId:
    def test_increments_monotonically(self):
        notifications._sse_event_counter = 0
        a = asyncio.run(notifications._next_event_id())
        b = asyncio.run(notifications._next_event_id())
        c = asyncio.run(notifications._next_event_id())
        assert (a, b, c) == (1, 2, 3)

    def test_continues_from_current_counter_value(self):
        notifications._sse_event_counter = 40
        assert asyncio.run(notifications._next_event_id()) == 41

    def test_concurrent_awaits_are_unique(self):
        notifications._sse_event_counter = 0

        async def _run():
            coros = [notifications._next_event_id() for _ in range(10)]
            return await asyncio.gather(*coros)

        ids = asyncio.run(_run())
        assert sorted(ids) == list(range(1, 11))
        assert len(set(ids)) == 10  # no duplicates under the lock


# ═══════════════════════════════════════════════════════════════════════
#  _user_wants_notif — notif-type → preference-column mapping
# ═══════════════════════════════════════════════════════════════════════

class TestUserWantsNotif:
    def test_unknown_type_defaults_true_without_db_query(self, monkeypatch):
        # No pref column mapped -> short-circuit True, must NOT touch the DB.
        def _boom(*a, **k):
            raise AssertionError("_fetchone must not be called for unmapped type")

        monkeypatch.setattr(db, "_fetchone", _boom)
        assert notifications._user_wants_notif("CONN", "u1", "totally_unknown") is True

    def test_no_pref_row_defaults_true(self, db_boundary):
        db_boundary.set(lambda sql, params: None)
        assert notifications._user_wants_notif("CONN", "u1", "like") is True

    def test_pref_false_suppresses(self, db_boundary):
        db_boundary.set(lambda sql, params: {"pref_like": False})
        assert notifications._user_wants_notif("CONN", "u1", "like") is False

    def test_pref_true_allows(self, db_boundary):
        db_boundary.set(lambda sql, params: {"pref_like": True})
        assert notifications._user_wants_notif("CONN", "u1", "like") is True

    def test_reaction_maps_to_pref_like_column(self, db_boundary):
        captured = {}

        def _resp(sql, params):
            captured["sql"] = sql
            return {"pref_like": True}

        db_boundary.set(_resp)
        assert notifications._user_wants_notif("CONN", "u1", "reaction") is True
        assert "pref_like" in captured["sql"]

    def test_comment_reply_maps_to_pref_comment_column(self, db_boundary):
        captured = {}

        def _resp(sql, params):
            captured["sql"] = sql
            return {"pref_comment": False}

        db_boundary.set(_resp)
        assert notifications._user_wants_notif("CONN", "u1", "comment_reply") is False
        assert "pref_comment" in captured["sql"]

    def test_moderation_maps_to_pref_system_column(self, db_boundary):
        captured = {}

        def _resp(sql, params):
            captured["sql"] = sql
            return {"pref_system": True}

        db_boundary.set(_resp)
        assert notifications._user_wants_notif("CONN", "u1", "moderation") is True
        assert "pref_system" in captured["sql"]

    def test_type_to_pref_map_is_complete_and_valid(self):
        # Every mapped value must be a real pref_* column name.
        valid = {"pref_like", "pref_comment", "pref_mention",
                 "pref_follow", "pref_system"}
        assert set(notifications._NOTIF_TYPE_TO_PREF.values()) <= valid
        assert notifications._NOTIF_TYPE_TO_PREF["mention"] == "pref_mention"
        assert notifications._NOTIF_TYPE_TO_PREF["follow"] == "pref_follow"


# ═══════════════════════════════════════════════════════════════════════
#  create_notification — block / mute / pref / dedup / insert+SSE branches
# ═══════════════════════════════════════════════════════════════════════

class TestCreateNotification:
    @pytest.fixture
    def sse_capture(self, monkeypatch):
        fired = []
        monkeypatch.setattr(notifications, "_notify_sse",
                            lambda uid, data: fired.append((uid, data)))
        return fired

    def test_blocked_actor_suppresses_notification(self, db_boundary, sse_capture):
        def _resp(sql, params):
            if "FROM blocks" in sql:
                return {"exists": 1}
            return None

        db_boundary.set(_resp)
        notifications.create_notification("u1", "like", "T",
                                          actor_id="actor1", ref_id="p1")
        assert sse_capture == []  # early return, no delivery
        # It stopped at the block check — never reached the INSERT.
        assert not any("INSERT INTO notifications" in s for s in db_boundary.seen_sql)

    def test_muted_actor_suppresses_notification(self, db_boundary, sse_capture):
        def _resp(sql, params):
            if "FROM blocks" in sql:
                return None
            if "FROM user_mutes" in sql:
                return {"exists": 1}
            return None

        db_boundary.set(_resp)
        notifications.create_notification("u1", "like", "T",
                                          actor_id="actor1", ref_id="p1")
        assert sse_capture == []
        assert not any("INSERT INTO notifications" in s for s in db_boundary.seen_sql)

    def test_disabled_preference_suppresses(self, db_boundary, sse_capture):
        # No actor -> skip block/mute; pref row disables 'like'.
        def _resp(sql, params):
            if "notification_preferences" in sql:
                return {"pref_like": False}
            return None

        db_boundary.set(_resp)
        notifications.create_notification("u1", "like", "T", ref_id="p1")
        assert sse_capture == []
        assert not any("INSERT INTO notifications" in s for s in db_boundary.seen_sql)

    def test_recent_duplicate_suppresses_notification(self, db_boundary, sse_capture):
        # pref ok (no row = allowed); a dup within 5 min exists.
        def _resp(sql, params):
            if "notification_preferences" in sql:
                return None
            if "FROM notifications" in sql and "INTERVAL" in sql:
                return {"exists": 1}
            return None

        db_boundary.set(_resp)
        notifications.create_notification("u1", "like", "T", ref_id="p1")
        assert sse_capture == []
        assert not any("INSERT INTO notifications" in s for s in db_boundary.seen_sql)

    def test_happy_path_inserts_and_dispatches_sse(self, db_boundary, sse_capture):
        def _resp(sql, params):
            if "INSERT INTO notifications" in sql:
                return {"id": "n-99"}
            return None

        db_boundary.set(_resp)
        notifications.create_notification("u1", "like", "TITLE",
                                          body="B", ref_type="post", ref_id="p1")
        assert len(sse_capture) == 1
        uid, data = sse_capture[0]
        assert uid == "u1"
        assert data["id"] == "n-99"          # id from the INSERT ... RETURNING
        assert data["type"] == "like"
        assert data["title"] == "TITLE"
        assert data["ref_id"] == "p1"
        assert any("INSERT INTO notifications" in s for s in db_boundary.seen_sql)

    def test_no_ref_id_skips_dedup_but_inserts(self, db_boundary, sse_capture):
        def _resp(sql, params):
            if "INSERT INTO notifications" in sql:
                return {"id": "n-1"}
            return None

        db_boundary.set(_resp)
        notifications.create_notification("u1", "like", "T")  # ref_id=None
        # dedup query is guarded by `if ref_id:` — must be skipped entirely.
        assert not any("INTERVAL '5 minutes'" in s and "FROM notifications" in s
                       for s in db_boundary.seen_sql)
        assert len(sse_capture) == 1

    def test_insert_returning_none_yields_none_id(self, db_boundary, sse_capture):
        # If the INSERT returns no row, notif_id is None but SSE still fires.
        db_boundary.set(lambda sql, params: None)
        notifications.create_notification("u1", "like", "T", ref_id="p1")
        assert len(sse_capture) == 1
        assert sse_capture[0][1]["id"] is None

    def test_no_actor_skips_block_and_mute_checks(self, db_boundary, sse_capture):
        db_boundary.set(lambda sql, params: {"id": "x"} if "INSERT" in sql else None)
        notifications.create_notification("u1", "like", "T", ref_id="p1")
        # Without actor_id, block/mute SQL must never be issued.
        assert not any("FROM blocks" in s for s in db_boundary.seen_sql)
        assert not any("FROM user_mutes" in s for s in db_boundary.seen_sql)

    def test_ref_id_coerced_to_string_in_sse_payload(self, db_boundary, sse_capture):
        db_boundary.set(lambda sql, params: {"id": "n"} if "INSERT" in sql else None)
        notifications.create_notification("u1", "like", "T", ref_id=12345)
        assert sse_capture[0][1]["ref_id"] == "12345"  # int coerced to str


# ═══════════════════════════════════════════════════════════════════════
#  ReportRequest — validators
# ═══════════════════════════════════════════════════════════════════════

class TestReportRequestModel:
    def test_valid_report_accepted(self):
        r = notifications.ReportRequest(target_type="post", target_id="p1",
                                        reason="spam content here")
        assert r.target_type == "post"

    def test_reason_is_stripped(self):
        r = notifications.ReportRequest(target_type="user", target_id="u1",
                                        reason="   valid reason   ")
        assert r.reason == "valid reason"

    @pytest.mark.parametrize("t", ["post", "comment", "user", "entity"])
    def test_all_allowed_target_types(self, t):
        r = notifications.ReportRequest(target_type=t, target_id="x",
                                        reason="a real reason")
        assert r.target_type == t

    def test_invalid_target_type_rejected(self):
        with pytest.raises(ValidationError):
            notifications.ReportRequest(target_type="banana", target_id="x",
                                        reason="a real reason")

    def test_reason_too_short_rejected(self):
        with pytest.raises(ValidationError):
            notifications.ReportRequest(target_type="post", target_id="x", reason="ab")

    def test_whitespace_only_reason_rejected(self):
        # strips to empty -> under 5 chars.
        with pytest.raises(ValidationError):
            notifications.ReportRequest(target_type="post", target_id="x",
                                        reason="        ")

    def test_reason_over_max_length_rejected(self):
        with pytest.raises(ValidationError):
            notifications.ReportRequest(target_type="post", target_id="x",
                                        reason="x" * 501)


# ═══════════════════════════════════════════════════════════════════════
#  NotifPrefsUpdate — partial-update model
# ═══════════════════════════════════════════════════════════════════════

class TestNotifPrefsUpdateModel:
    def test_all_none_by_default(self):
        b = notifications.NotifPrefsUpdate()
        assert all(v is None for v in b.model_dump().values())

    # (Đã bỏ 2 test re-implement bộ lọc None: handler update_notification_preferences
    #  là PG-only, 2 test đó chỉ tautology model_dump() — không phủ logic module.)

    def test_accepts_all_five_flags(self):
        b = notifications.NotifPrefsUpdate(
            pref_like=True, pref_comment=False, pref_mention=True,
            pref_follow=False, pref_system=True,
        )
        d = b.model_dump()
        assert set(d) == {"pref_like", "pref_comment", "pref_mention",
                          "pref_follow", "pref_system"}
        assert d["pref_comment"] is False


# ═══════════════════════════════════════════════════════════════════════
#  Router wiring — the community router is Postgres-guarded
# ═══════════════════════════════════════════════════════════════════════

class TestRouterConfig:
    def test_router_prefix_and_pg_dependency(self):
        assert notifications.router.prefix == "/api"
        # The router carries a require_pg dependency so every UGC endpoint is
        # 503-guarded off Postgres (a core project invariant).
        assert len(notifications.router.dependencies) >= 1

    def test_sse_cap_pins_contract(self):
        # Pin giá trị THẬT (không range lỏng): eviction ở notifications.py dùng
        # `len(subs) >= _SSE_MAX_PER_USER` — đổi hằng = đổi hợp đồng, phải đỏ.
        assert notifications._SSE_MAX_PER_USER == 5
