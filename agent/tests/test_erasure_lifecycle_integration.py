"""Deterministic cross-boundary contracts for the erasure lifecycle."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock

import httpx
import pytest

import auth
import data_lifecycle
import erasure
import erasure_state
import quarantine
import ratelimit
import scheduler
import server
from owner_write_gate import OwnerWriteBlocked, OwnerWriteGate, owner_key_for_user


UTC = timezone.utc
REQUESTED_AT = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
DUE_AT = REQUESTED_AT + timedelta(days=30)
USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_ID = "00000000-0000-0000-0000-000000000002"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class LifecycleDatabase:
    _ph = "%s"
    _use_pg = True

    def __init__(self):
        self.users: dict[str, dict] = {}
        self.user_sessions: set[str] = set()
        self.otp_sessions: set[str] = set()
        self.trusted_devices: set[str] = set()
        self.pending_2fa: set[str] = set()
        self._lock = RLock()

    def seed_user(self, user_id: str, phone: str) -> None:
        self.users[user_id] = {
            "id": user_id,
            "phone": phone,
            "is_active": True,
            "deleted_at": None,
            "erasure_due_at": None,
            "erasure_attempt_count": 0,
            "erasure_last_attempt_at": None,
            "erasure_last_error_code": None,
            "password_hash": None,
        }
        self.user_sessions.add(user_id)
        self.otp_sessions.add(phone)
        self.trusted_devices.add(user_id)
        self.pending_2fa.add(user_id)

    def initialize(self):
        return None

    @contextmanager
    def _conn(self, **_kwargs):
        with self._lock:
            yield self

    def _fetchone(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        params = params or ()
        if normalized.startswith("SELECT") and "FROM users" in normalized:
            row = self.users.get(str(params[0]))
            return dict(row) if row else None
        if not normalized.startswith("UPDATE users"):
            raise AssertionError(f"unexpected query: {normalized}")

        if "COALESCE(deleted_at" in normalized:
            requested_at, due_at, user_id = params
            row = self.users[str(user_id)]
            row["deleted_at"] = row["deleted_at"] or requested_at
            row["erasure_due_at"] = row["erasure_due_at"] or due_at
            row["is_active"] = False
            return dict(row)
        if "SET deleted_at = NULL" in normalized:
            user_id = str(params[0])
            row = self.users[user_id]
            row.update(
                deleted_at=None,
                erasure_due_at=None,
                erasure_attempt_count=0,
                erasure_last_attempt_at=None,
                erasure_last_error_code=None,
                is_active=True,
            )
            return dict(row)
        if "erasure_attempt_count = LEAST" in normalized:
            now, error_code, user_id = params
            row = self.users[str(user_id)]
            row["erasure_attempt_count"] += 1
            row["erasure_last_attempt_at"] = now
            row["erasure_last_error_code"] = error_code
            return dict(row)
        if "SET erasure_last_attempt_at" in normalized:
            now, user_id = params
            row = self.users[str(user_id)]
            row["erasure_last_attempt_at"] = now
            if "erasure_last_error_code = NULL" in normalized:
                row["erasure_last_error_code"] = None
            return dict(row)
        raise AssertionError(f"unexpected update: {normalized}")

    def _execute(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        value = str((params or (None,))[0])
        if "DELETE FROM user_sessions" in normalized:
            self.user_sessions.discard(value)
        elif "DELETE FROM otp_sessions" in normalized:
            self.otp_sessions.discard(value)
        elif "DELETE FROM trusted_devices" in normalized:
            self.trusted_devices.discard(value)
        elif "DELETE FROM pending_2fa" in normalized:
            self.pending_2fa.discard(value)
        else:
            raise AssertionError(f"unexpected statement: {normalized}")

    def _fetchall(self, _conn, sql, params=None):
        normalized = " ".join(sql.split())
        now, limit = params
        if "erasure_due_at <=" in normalized:
            rows = [
                row
                for row in self.users.values()
                if row["deleted_at"] is not None
                and row["erasure_due_at"] is not None
                and row["erasure_due_at"] <= now
            ]
            rows.sort(key=lambda row: (row["erasure_due_at"], row["id"]))
            return [
                {"id": row["id"], "erasure_due_at": row["erasure_due_at"]}
                for row in rows[: int(limit)]
            ]
        if "erasure_due_at >" in normalized:
            rows = [
                row
                for row in self.users.values()
                if row["deleted_at"] is not None
                and row["erasure_due_at"] is not None
                and row["erasure_due_at"] > now
                and (
                    row["erasure_last_attempt_at"] is None
                    or row["erasure_last_error_code"] is not None
                )
            ]
            rows.sort(key=lambda row: (row["deleted_at"], row["id"]))
            return [{"id": row["id"]} for row in rows[: int(limit)]]
        raise AssertionError(f"unexpected selection: {normalized}")

    def get_user_by_phone(self, phone: str):
        row = next(
            (row for row in self.users.values() if row["phone"] == phone),
            None,
        )
        return dict(row) if row else None

    def delete_erased_user(self, _conn, user_id: str, now: datetime):
        row = self.users.get(str(user_id))
        if not row or row["deleted_at"] is None or row["erasure_due_at"] > now:
            return None
        return self.users.pop(str(user_id))

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row is not None else None


class StoreWorld:
    def __init__(self):
        self.records = {
            name: {} for name in data_lifecycle.EXPECTED_SUBJECT_STORES
        }
        self.fail_once: set[tuple[str, str]] = set()
        self.residual_once: set[tuple[str, str]] = set()
        self.calls: list[tuple[str, str, str]] = []
        self.aggregates = {
            "deidentified_daily_rollups": {"date": "2026-07-30", "count": 8},
            "public_entity_popularity": {"public_entity_id": "entity-1", "count": 3},
        }
        policies = [self._subject_policy(name) for name in sorted(self.records)]
        policies.extend(
            [
                data_lifecycle.DataStorePolicy(
                    "deidentified_daily_rollups",
                    "aggregate",
                    None,
                    None,
                    "daily aggregate",
                    subject_linked=False,
                    retained_fields=("date", "request_count", "session_count"),
                ),
                data_lifecycle.DataStorePolicy(
                    "public_entity_popularity",
                    "aggregate",
                    None,
                    None,
                    "public aggregate",
                    subject_linked=False,
                    retained_fields=("public_entity_id", "count"),
                ),
                data_lifecycle.DataStorePolicy(
                    "post_boundary_operational_logs",
                    "operational",
                    None,
                    None,
                    "bounded operational events",
                    subject_linked=False,
                    retained_fields=("event_code", "store_name", "run_id", "count"),
                ),
            ]
        )
        self.registry = data_lifecycle.LifecycleRegistry(policies)

    def _subject_policy(self, name: str):
        def purge(owner_key: str):
            self.calls.append(("purge", name, owner_key))
            key = (name, owner_key)
            if key in self.fail_once:
                self.fail_once.remove(key)
                return data_lifecycle.PurgeResult(
                    name,
                    complete=False,
                    error_code="STORE_UNAVAILABLE",
                )
            if key in self.residual_once:
                self.residual_once.remove(key)
                return data_lifecycle.PurgeResult(name, removed_count=0)
            removed = int(self.records[name].pop(owner_key, None) is not None)
            return data_lifecycle.PurgeResult(name, removed_count=removed)

        def verify(owner_key: str):
            self.calls.append(("verify", name, owner_key))
            absent = owner_key not in self.records[name]
            return data_lifecycle.VerificationResult(
                name,
                absent=absent,
                residual_count=0 if absent else 1,
            )

        return data_lifecycle.DataStorePolicy(
            name,
            "personal",
            purge,
            verify,
            name,
            quarantine_on_request=name
            in data_lifecycle.EXPECTED_QUARANTINE_STORES,
        )

    def seed(self, owner_key: str) -> None:
        for name in self.records:
            self.records[name][owner_key] = f"sentinel:{name}"

    def remaining(self, owner_key: str) -> set[str]:
        return {
            name for name, rows in self.records.items() if owner_key in rows
        }


class StructuredWorld:
    def __init__(self, user_ids):
        self.claims = []
        self.audit = []
        self.posts = []
        for user_id in user_ids:
            self.claims.extend(
                [
                    {"status": "pending", "claimant_id": user_id},
                    {
                        "status": "approved",
                        "claimant_id": user_id,
                        "reviewer_id": user_id,
                        "contact_email": "private@example.test",
                        "evidence": "private",
                    },
                ]
            )
            self.audit.append({"actor": user_id, "event_code": "reviewed"})
            self.posts.append(
                {
                    "mentions": [
                        {"type": "user", "id": user_id},
                        {"type": "entity", "id": user_id},
                    ]
                }
            )

    def scrub(self, user_id: str) -> None:
        self.claims = [
            claim
            for claim in self.claims
            if not (
                claim["status"] == "pending"
                and claim.get("claimant_id") == user_id
            )
        ]
        for claim in self.claims:
            if claim.get("claimant_id") == user_id:
                for field in (
                    "claimant_id",
                    "reviewer_id",
                    "contact_email",
                    "evidence",
                ):
                    claim[field] = None
            elif claim.get("reviewer_id") == user_id:
                claim["reviewer_id"] = None
        for event in self.audit:
            if event.get("actor") == user_id:
                event["actor"] = None
        for post in self.posts:
            post["mentions"] = [
                mention
                for mention in post["mentions"]
                if not (
                    mention.get("type") == "user"
                    and mention.get("id") == user_id
                )
            ]

    def assert_absent(self, user_id: str) -> None:
        assert all(
            claim.get("claimant_id") != user_id
            and claim.get("reviewer_id") != user_id
            for claim in self.claims
        )
        assert all(event.get("actor") != user_id for event in self.audit)
        assert all(
            not any(
                mention.get("type") == "user"
                and mention.get("id") == user_id
                for mention in post["mentions"]
            )
            for post in self.posts
        )


class Metric:
    def inc(self, *_args, **_kwargs):
        return None


def _patch_lifecycle(monkeypatch, db, stores, gate, structured):
    monkeypatch.setattr(erasure_state, "db", db)
    monkeypatch.setattr(quarantine, "db", db)
    monkeypatch.setattr(erasure, "db", db)
    monkeypatch.setattr(auth, "db", db)
    monkeypatch.setattr(quarantine, "lifecycle_registry", stores.registry)
    monkeypatch.setattr(erasure, "lifecycle_registry", stores.registry)
    monkeypatch.setattr(quarantine, "owner_write_gate", gate)
    monkeypatch.setattr(auth, "owner_write_gate", gate)
    monkeypatch.setattr(erasure, "validate_user_fk_actions", lambda _conn: ())
    monkeypatch.setattr(
        erasure,
        "scrub_user_references",
        lambda _conn, user_id, **_kwargs: structured.scrub(str(user_id)),
    )
    monkeypatch.setattr(
        erasure,
        "_assert_structured_absent",
        lambda _conn, user_id: structured.assert_absent(str(user_id)),
    )
    for name in (
        "erasure_due_total",
        "erasure_completed_total",
        "erasure_failed_total",
        "erasure_overdue_total",
    ):
        monkeypatch.setattr(erasure.metrics, name, Metric())


def _setup_world(monkeypatch, user_ids=(USER_ID,)):
    db = LifecycleDatabase()
    stores = StoreWorld()
    structured = StructuredWorld(user_ids)
    phones = {}
    for index, user_id in enumerate(user_ids, 1):
        phone = f"090000000{index}"
        phones[user_id] = phone
        db.seed_user(user_id, phone)
        stores.seed(owner_key_for_user(user_id))
    gate = OwnerWriteGate(
        lambda user_id: db.users.get(user_id, {}).get("deleted_at")
    )
    _patch_lifecycle(monkeypatch, db, stores, gate, structured)
    return db, stores, structured, gate, phones


def _override_auth_dependencies():
    async def no_dependency():
        return None

    server.app.dependency_overrides[auth._require_pg] = no_dependency
    server.app.dependency_overrides[auth._require_csrf_lazy] = no_dependency


def _clear_auth_dependencies():
    server.app.dependency_overrides.pop(auth._require_pg, None)
    server.app.dependency_overrides.pop(auth._require_csrf_lazy, None)


@pytest.mark.anyio
async def test_request_quarantine_and_predeadline_recovery_keep_retained_data(
    monkeypatch,
):
    db, stores, _structured, gate, phones = _setup_world(monkeypatch)
    owner_key = owner_key_for_user(USER_ID)
    before_aggregates = deepcopy(stores.aggregates)

    async def current_user(_request):
        return dict(db.users[USER_ID])

    async def binding_ok(_request, _user):
        return True

    monkeypatch.setattr(auth, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth, "_check_session_binding_safe", binding_ok)
    monkeypatch.setattr(auth, "_utc_now", lambda: REQUESTED_AT)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    _override_auth_dependencies()
    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.delete("/auth/account")
    finally:
        _clear_auth_dependencies()

    assert response.status_code == 200
    assert response.json()["erasure_due_at"] == DUE_AT.isoformat()
    assert db.users[USER_ID]["deleted_at"] == REQUESTED_AT
    assert db.users[USER_ID]["erasure_due_at"] == DUE_AT
    assert db.users[USER_ID]["is_active"] is False
    assert USER_ID not in db.user_sessions
    assert phones[USER_ID] not in db.otp_sessions
    assert USER_ID not in db.trusted_devices
    assert USER_ID not in db.pending_2fa
    assert not stores.remaining(owner_key).intersection(
        data_lifecycle.EXPECTED_QUARANTINE_STORES
    )
    assert stores.remaining(owner_key) == (
        set(data_lifecycle.EXPECTED_SUBJECT_STORES)
        - set(data_lifecycle.EXPECTED_QUARANTINE_STORES)
    )
    with pytest.raises(OwnerWriteBlocked):
        gate.assert_writable(owner_key)

    async def finish_login(*_args):
        return {"success": True, "token": "fresh-session"}

    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_finish_login", finish_login)
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: False)
    monkeypatch.setattr(auth, "_hash_otp", lambda code: code)
    monkeypatch.setattr(auth, "_check_shared_auth_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_enforce_local_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_log_consent", lambda *_args: None)
    monkeypatch.setattr(auth, "_utc_now", lambda: DUE_AT - timedelta(microseconds=1))
    _override_auth_dependencies()
    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            recovery = await client.post(
                "/auth/verify-otp",
                json={"phone": phones[USER_ID], "code": "123456"},
            )
    finally:
        _clear_auth_dependencies()

    assert recovery.status_code == 200
    assert db.users[USER_ID]["is_active"] is True
    assert db.users[USER_ID]["deleted_at"] is None
    assert db.users[USER_ID]["erasure_due_at"] is None
    gate.assert_writable(owner_key)
    assert stores.aggregates == before_aggregates
    assert not stores.remaining(owner_key).intersection(
        data_lifecycle.EXPECTED_QUARANTINE_STORES
    )


@pytest.mark.anyio
async def test_recovery_at_exact_deadline_fails_closed(monkeypatch):
    db, _stores, _structured, _gate, phones = _setup_world(monkeypatch)
    erasure_state.request_account_erasure(USER_ID, now=REQUESTED_AT)

    async def finish_login(*_args):
        raise AssertionError("session creation must not run at the deadline")

    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_finish_login", finish_login)
    monkeypatch.setattr(auth, "_2fa_is_enabled", lambda *_args: False)
    monkeypatch.setattr(auth, "_hash_otp", lambda code: code)
    monkeypatch.setattr(auth, "_check_shared_auth_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_enforce_local_rate", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth, "_utc_now", lambda: DUE_AT)
    monkeypatch.setattr(ratelimit, "check_rate", lambda *_args, **_kwargs: None)
    _override_auth_dependencies()
    try:
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/verify-otp",
                json={"phone": phones[USER_ID], "code": "123456"},
            )
    finally:
        _clear_auth_dependencies()

    assert response.status_code == 403
    assert db.users[USER_ID]["is_active"] is False
    assert db.users[USER_ID]["erasure_due_at"] == DUE_AT


def _schedule(db, gate, user_id):
    state = erasure_state.request_account_erasure(user_id, now=REQUESTED_AT)
    gate.block_owner(owner_key_for_user(user_id))
    result = quarantine.quarantine_account(user_id, now=REQUESTED_AT)
    assert result.success is True
    assert state.erasure_due_at == DUE_AT
    return db.users[user_id]


def test_due_batch_isolates_partial_purge_and_retry_preserves_aggregates(
    monkeypatch,
):
    db, stores, structured, gate, _phones = _setup_world(
        monkeypatch, (USER_ID, OTHER_ID)
    )
    for user_id in (USER_ID, OTHER_ID):
        _schedule(db, gate, user_id)
    other_owner = owner_key_for_user(OTHER_ID)
    stores.fail_once.add(("cold_memory", other_owner))
    before_aggregates = deepcopy(stores.aggregates)

    batch = erasure.erase_due_accounts(now=DUE_AT, limit=50)

    assert batch.selected_count == 2
    assert batch.completed_count == 1
    assert batch.failed_count == 1
    assert USER_ID not in db.users
    assert OTHER_ID in db.users
    assert stores.remaining(owner_key_for_user(USER_ID)) == set()
    assert "cold_memory" in stores.remaining(other_owner)
    structured.assert_absent(USER_ID)
    assert stores.aggregates == before_aggregates

    retry = erasure.erase_account(OTHER_ID, now=DUE_AT)

    assert retry.verified is True
    assert OTHER_ID not in db.users
    assert stores.remaining(other_owner) == set()
    structured.assert_absent(OTHER_ID)
    assert stores.aggregates == before_aggregates


def test_residual_store_stops_database_delete_until_verified_retry(monkeypatch):
    db, stores, structured, gate, _phones = _setup_world(monkeypatch)
    _schedule(db, gate, USER_ID)
    owner_key = owner_key_for_user(USER_ID)
    stores.residual_once.add(("memory_graph", owner_key))

    first = erasure.erase_account(USER_ID, now=DUE_AT)

    assert first.status == "failed"
    assert first.error_code == "RESIDUAL_DATA"
    assert USER_ID in db.users
    assert "memory_graph" in stores.remaining(owner_key)

    second = erasure.erase_account(USER_ID, now=DUE_AT)

    assert second.verified is True
    assert USER_ID not in db.users
    structured.assert_absent(USER_ID)


def test_scheduler_audit_only_inventory_does_not_purge_due_account(monkeypatch):
    db, stores, _structured, gate, _phones = _setup_world(monkeypatch)
    _schedule(db, gate, USER_ID)
    owner_key = owner_key_for_user(USER_ID)
    before_stores = stores.remaining(owner_key)
    monkeypatch.setattr(scheduler.settings, "ERASURE_AUDIT_ONLY", True)
    monkeypatch.setattr(scheduler.settings, "ERASURE_ACTIVATION_ENABLED", True)
    monkeypatch.setattr(scheduler, "_utc_now", lambda: DUE_AT)
    monkeypatch.setattr(
        scheduler,
        "_legacy_deadline_impact",
        lambda _now: {
            "legacy_missing_deadline_count": 0,
            "earliest_due_at": None,
            "latest_due_at": None,
        },
    )

    result = scheduler.task_account_erasure()

    assert result["audit_only"] is True
    assert result["due_count"] == 1
    assert USER_ID in db.users
    assert stores.remaining(owner_key) == before_stores
