"""Integration coverage for privacy-safe personalization event persistence."""

from __future__ import annotations

import os
import json
import multiprocessing
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlparse
from uuid import uuid4

import psycopg2
import psycopg2.extras
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_middleware
import auth
import database as database_module
import personalization_events
import public_api
import scheduler
import user_preferences
from auth_middleware import generate_csrf_token
from personalization_events import (
    purge_legacy_events,
    purge_personalization_events,
    purge_user_personalization,
    read_legacy_events_if_allowed,
    read_personalization_events,
    write_personalization_event,
)
from versioned_json_store import publication_lock


def _test_database_url() -> str | None:
    url = os.environ.get("PERSONALIZATION_EVENTS_TEST_DATABASE_URL")
    if not url:
        return None
    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or "test" not in database_name.lower()
    ):
        raise pytest.UsageError(
            "PERSONALIZATION_EVENTS_TEST_DATABASE_URL must target a loopback "
            "PostgreSQL database whose name contains 'test'"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set PERSONALIZATION_EVENTS_TEST_DATABASE_URL to a disposable PostgreSQL DB",
)


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    region_id TEXT,
    region_label VARCHAR(160),
    region_scope TEXT NOT NULL DEFAULT 'unknown',
    location_source TEXT NOT NULL DEFAULT 'default',
    location_accuracy TEXT NOT NULL DEFAULT 'unknown',
    location_consent_state TEXT NOT NULL DEFAULT 'unknown',
    location_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    personalization_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    explicit_interests JSONB NOT NULL DEFAULT '[]'::JSONB,
    recommendation_reset_at TIMESTAMPTZ,
    consent_version VARCHAR(64),
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_preference_consents (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,
    state TEXT NOT NULL,
    version VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_personalization_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    context VARCHAR(64) NOT NULL,
    entity_id TEXT,
    entity_type VARCHAR(64),
    area_id TEXT,
    interest_keys JSONB NOT NULL DEFAULT '[]'::JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    summary TEXT DEFAULT '',
    description TEXT DEFAULT '',
    "placeId" TEXT,
    confidence REAL DEFAULT 1.0,
    season JSONB,
    attributes JSONB DEFAULT '{}'::jsonb,
    source JSONB DEFAULT '{}'::jsonb,
    images JSONB DEFAULT '[]'::jsonb,
    coordinates JSONB,
    area TEXT,
    level TEXT,
    "parentId" TEXT,
    "legacyArea" TEXT,
    "updatedAt" TEXT,
    status TEXT,
    verified INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_entities (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);

CREATE TABLE IF NOT EXISTS user_visits (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'visited',
    visited_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);

ALTER TABLE user_visits ADD COLUMN IF NOT EXISTS visited_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,
    post_type TEXT,
    rating INTEGER,
    entity_id TEXT,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY,
    post_id UUID,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,
    parent_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS likes (
    post_id UUID,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bookmarks (post_id UUID);
CREATE TABLE IF NOT EXISTS follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type TEXT,
    target_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS post_reactions (
    post_id UUID,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reaction_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_collections (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS blocks (
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_mutes (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    muted_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS otp_sessions (
    id UUID PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS login_history (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ref_type TEXT,
    ref_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


@pytest.fixture(scope="session", autouse=True)
def personalization_schema():
    if TEST_DATABASE_URL is None:
        yield
        return
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(SCHEMA_SQL)
    yield


@pytest.fixture
def pg_db(monkeypatch):
    assert TEST_DATABASE_URL is not None
    database_module.psycopg2 = psycopg2
    database_module.psycopg2.extras = psycopg2.extras
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    adapter._initialized = True
    monkeypatch.setattr(personalization_events, "db", adapter)
    monkeypatch.setattr(user_preferences, "db", adapter)
    monkeypatch.setattr(database_module, "db", adapter)
    monkeypatch.setattr(auth, "db", adapter)
    monkeypatch.setattr(scheduler, "db", adapter, raising=False)
    monkeypatch.setattr(auth_middleware, "db", adapter)
    monkeypatch.setattr(public_api, "db", adapter)
    with adapter._conn() as conn:
        adapter._execute(
            conn,
            "TRUNCATE user_personalization_events, user_preference_consents, "
            "user_preferences, saved_entities, user_visits, posts, comments, likes, "
            "bookmarks, follows, post_reactions, user_collections, blocks, user_mutes, "
            "user_sessions, otp_sessions, login_history, notifications, entities, users CASCADE",
        )
    yield adapter
    with adapter._conn() as conn:
        adapter._execute(
            conn,
            "TRUNCATE user_personalization_events, user_preference_consents, "
            "user_preferences, saved_entities, user_visits, posts, comments, likes, "
            "bookmarks, follows, post_reactions, user_collections, blocks, user_mutes, "
            "user_sessions, otp_sessions, login_history, notifications, entities, users CASCADE",
        )


@pytest.fixture
def users(pg_db):
    owner = str(uuid4())
    other = str(uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO users (id, phone) VALUES (%s::uuid, %s), (%s::uuid, %s)",
            (owner, f"test-{owner}", other, f"test-{other}"),
        )
    return owner, other


def seed_legacy_events(path: Path, user_ids: list[str]) -> None:
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    rows = []
    for index, user_id in enumerate(user_ids):
        rows.append(
            {
                "ts": (base + timedelta(days=index)).isoformat(),
                "user_id": user_id,
                "event_type": "entity_view",
                "context": "entity",
                "entity_id": f"entity-{index}",
                "entity_type": "dish",
                "area": "province-vl",
                "interest_keys": ["food"],
                "query": f"private-query-{index}",
                "ip_hash": f"private-ip-{index}",
                "metadata": {"private": index},
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_all_legacy_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _hold_publication_lock(lock_path: str, ready, release) -> None:
    with publication_lock(Path(lock_path)):
        ready.set()
        release.wait(10)


@pytest.fixture
def logged_in_client(pg_db, users, monkeypatch):
    owner, _ = users
    session_token = "personalization-session"
    user = {"id": owner, "display_name": "Personalization owner", "role": "user"}

    async def current_user(request):
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return user if bearer == session_token else None

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth_middleware, "db", pg_db)
    monkeypatch.setattr(public_api, "db", pg_db)
    app = FastAPI()
    app.include_router(public_api.router)
    headers = {"Authorization": f"Bearer {session_token}"}
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            owner=owner,
            headers=headers,
            csrf_headers={
                **headers,
                "X-CSRF-Token": generate_csrf_token(session_token),
            },
        )


@pytest.fixture
def auth_client(pg_db, users, monkeypatch):
    owner, _ = users
    session_token = "personalization-auth-session"
    user = {
        "id": owner,
        "phone": "0901234567",
        "display_name": "Personalization owner",
        "role": "user",
        "is_active": True,
        "deleted_at": None,
    }

    async def current_user(request):
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return user if bearer == session_token else None

    async def session_binding(_request, _user):
        return True

    monkeypatch.setattr(auth, "_get_current_user_or_none", current_user)
    monkeypatch.setattr(auth, "_check_session_binding_safe", session_binding)
    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(public_api.router)
    headers = {"Authorization": f"Bearer {session_token}"}
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            owner=owner,
            headers=headers,
            csrf_headers={
                **headers,
                "X-CSRF-Token": generate_csrf_token(session_token),
            },
        )


def test_event_writer_drops_sensitive_and_arbitrary_fields(pg_db, users):
    owner, _ = users
    write_personalization_event(
        owner,
        {
            "event_type": " Search_Submit ",
            "context": " Search ",
            "entity_id": "  entity-1  ",
            "entity_type": " Dish ",
            "area_id": " province-vl ",
            "interest_keys": [" food ", "food", "culture"],
            "query": "so dien thoai rieng tu",
            "ip": "203.0.113.8",
            "latitude": 10.25,
            "longitude": 105.97,
            "metadata": {"private": "payload"},
        },
    )

    row = read_personalization_events(owner, cutoff=None, limit=1)[0]

    assert row == {
        "event_type": "search_submit",
        "context": "search",
        "entity_id": "entity-1",
        "entity_type": "dish",
        "area_id": "province-vl",
        "interest_keys": ["food", "culture"],
        "occurred_at": row["occurred_at"],
        "expires_at": row["expires_at"],
    }
    assert row["expires_at"] > row["occurred_at"]


_SMUGGLED_VALUES = (
    "so dien thoai rieng tu",
    "203.0.113.8",
    "2001:db8::1",
    "10.25,105.97",
    '{"metadata":"private"}',
)


@pytest.mark.parametrize(
    "carrier",
    ("event_type", "context", "entity_id", "entity_type", "area_id", "interest_keys"),
)
@pytest.mark.parametrize("smuggled", _SMUGGLED_VALUES)
def test_direct_writer_rejects_sensitive_text_in_every_allowed_carrier(
    pg_db, users, carrier, smuggled
):
    owner, _ = users
    event = {
        "event_type": "entity_view",
        "context": "entity",
        "entity_id": "entity-1",
        "entity_type": "dish",
        "area_id": "province-vl",
        "interest_keys": ["food"],
    }
    event[carrier] = [smuggled] if carrier == "interest_keys" else smuggled

    with pytest.raises(personalization_events.PersonalizationEventError):
        write_personalization_event(owner, event)

    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn, "SELECT COUNT(*) AS count FROM user_personalization_events"
        )
    assert pg_db._row_to_dict(row)["count"] == 0


@pytest.mark.parametrize(
    ("carrier", "smuggled"),
    (
        ("event_type", "so dien thoai rieng tu"),
        ("context", "203.0.113.8"),
        ("entity_id", "2001:db8::1"),
        ("entity_type", "10.25,105.97"),
        ("area_id", '{"metadata":"private"}'),
        ("interest_keys", "so dien thoai rieng tu"),
    ),
)
def test_event_route_rejects_smuggling_without_storage_export_or_scoring(
    auth_client, pg_db, carrier, smuggled
):
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)
    payload = {
        "event_type": "entity_view",
        "context": "entity",
        "entity_id": "entity-1",
        "entity_type": "dish",
        "area_id": "province-vl",
        "interest_keys": ["food"],
    }
    payload[carrier] = [smuggled] if carrier == "interest_keys" else smuggled

    response = auth_client.client.post(
        "/api/me/events", json=payload, headers=auth_client.csrf_headers
    )
    exported = auth_client.client.get(
        "/auth/export-data", headers=auth_client.headers
    )
    profile = public_api._build_user_interest_profile(auth_client.owner)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid personalization event"}
    assert smuggled not in response.text
    assert exported.status_code == 200
    assert exported.json()["personalization"]["events"] == []
    assert profile["interests"] == []
    assert profile["areas"] == []
    assert profile["types"] == []


@pytest.mark.parametrize(
    "entity_id", ("entity-with-many---hyphens", "b63c1f9d-41ca-43b7-9b30-c3910b893af3")
)
def test_direct_writer_accepts_normalized_slug_and_uuid_identifiers(
    pg_db, users, entity_id
):
    owner, _ = users

    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": entity_id,
            "entity_type": "dish",
            "area_id": "province-vl",
            "interest_keys": ["food"],
        },
    )

    assert read_personalization_events(owner, cutoff=None)[0]["entity_id"] == entity_id


@pytest.mark.parametrize("carrier", ("entity_id", "area_id"))
def test_direct_writer_rejects_oversized_identifiers_instead_of_truncating(
    pg_db, users, carrier
):
    owner, _ = users
    event = {
        "event_type": "entity_view",
        "context": "entity",
        "entity_id": "entity-1",
        "entity_type": "dish",
        "area_id": "province-vl",
        "interest_keys": ["food"],
    }
    event[carrier] = "a" * 201

    with pytest.raises(personalization_events.PersonalizationEventError):
        write_personalization_event(owner, event)

    assert read_personalization_events(owner, cutoff=None) == []


def test_event_reader_uses_strict_cutoff_expiry_and_hard_limit(pg_db, users):
    owner, _ = users
    cutoff = datetime(2026, 2, 1, tzinfo=timezone.utc)
    for occurred_at in (
        cutoff - timedelta(seconds=1),
        cutoff,
        cutoff + timedelta(seconds=1),
    ):
        write_personalization_event(
            owner,
            {
                "event_type": "entity_view",
                "context": "entity",
                "occurred_at": occurred_at,
                "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
            },
        )
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "occurred_at": cutoff + timedelta(seconds=2),
            "expires_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
    )
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_personalization_events
                (id, user_id, event_type, context, occurred_at, expires_at)
            SELECT uuid_generate_v4(), %s::uuid, 'entity_view', 'entity',
                   %s::timestamptz + (n || ' milliseconds')::interval,
                   '2027-01-01T00:00:00+00'::timestamptz
            FROM generate_series(1, 305) AS n
            """,
            (owner, cutoff + timedelta(minutes=1)),
        )

    rows = read_personalization_events(owner, cutoff=cutoff, limit=10_000)

    assert len(rows) == 300
    assert all(row["occurred_at"] > cutoff for row in rows)
    assert all(row["expires_at"] > datetime.now(timezone.utc) for row in rows)
    assert rows == sorted(rows, key=lambda row: row["occurred_at"], reverse=True)


def test_event_purge_targets_only_expired_or_matching_user(pg_db, users):
    owner, other = users
    now = datetime.now(timezone.utc)
    for user_id, expires_at in (
        (owner, now - timedelta(seconds=1)),
        (owner, now + timedelta(days=1)),
        (other, now + timedelta(days=1)),
    ):
        write_personalization_event(
            user_id,
            {
                "event_type": "entity_view",
                "context": "entity",
                "expires_at": expires_at,
            },
        )

    assert purge_personalization_events(before=now) == 1
    assert len(read_personalization_events(owner, cutoff=None)) == 1
    assert purge_personalization_events(user_id=owner) == 1
    assert read_personalization_events(owner, cutoff=None) == []
    assert len(read_personalization_events(other, cutoff=None)) == 1


def test_legacy_reader_applies_cutoff_deadline_and_safe_projection(
    tmp_path, monkeypatch, users
):
    owner, other = users
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner, owner, other])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "legacy_cutover_deadline",
        lambda: datetime(2026, 8, 30, tzinfo=timezone.utc),
    )

    rows = read_legacy_events_if_allowed(
        owner,
        cutoff=datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
        now=datetime(2026, 7, 28, tzinfo=timezone.utc),
    )

    assert rows == [
        {
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": "entity-1",
            "entity_type": "dish",
            "area_id": "province-vl",
            "interest_keys": ["food"],
            "occurred_at": datetime(2026, 7, 2, tzinfo=timezone.utc),
        }
    ]
    assert read_legacy_events_if_allowed(
        owner,
        cutoff=None,
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    ) == []


def test_legacy_purge_waits_for_cross_process_lock_and_keeps_other_users(
    tmp_path, monkeypatch, users
):
    owner, other = users
    path = tmp_path / "legacy-events.jsonl"
    lock_path = tmp_path / ".legacy-events.publication.lock"
    seed_legacy_events(path, [owner, other])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_LOCK_PATH", lock_path)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_publication_lock,
        args=(str(lock_path), ready, release),
    )
    process.start()
    assert ready.wait(10)
    result: list[int] = []
    finished = threading.Event()

    def purge():
        result.append(purge_legacy_events(user_id=owner))
        finished.set()

    thread = threading.Thread(target=purge)
    thread.start()
    try:
        assert not finished.wait(0.3)
    finally:
        release.set()
        process.join(10)
        thread.join(10)

    assert process.exitcode == 0
    assert result == [1]
    assert [row["user_id"] for row in read_all_legacy_events(path)] == [other]


def test_legacy_purge_preserves_unrecognized_lines(tmp_path, monkeypatch, users):
    owner, other = users
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner, other])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("unrecognized legacy line\n")
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )

    assert purge_legacy_events(user_id=owner) == 1

    assert "unrecognized legacy line" in path.read_text(encoding="utf-8")
    assert f'"user_id": "{other}"' in path.read_text(encoding="utf-8")


def test_legacy_purge_preserves_valid_unknown_json_objects(
    tmp_path, monkeypatch, users
):
    owner, other = users
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner, other])
    unknown = {
        "user_id": owner,
        "ts": "2026-07-01T00:00:00+00:00",
        "event_type": "entity_view",
        "context": "entity",
        "record_type": "future_workspace_record",
        "payload": {"keep": True},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(unknown) + "\n")
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )

    assert purge_legacy_events(user_id=owner) == 1

    rows = read_all_legacy_events(path)
    assert unknown in rows
    recognized = [row for row in rows if row != unknown]
    assert [row["user_id"] for row in recognized] == [other]


def test_legacy_purge_user_and_before_filters_only_recognized_events(
    tmp_path, monkeypatch, users
):
    owner, other = users
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner, owner, other])
    unknown = {
        "user_id": owner,
        "ts": "2026-07-01T00:00:00+00:00",
        "event_type": "entity_view",
        "context": "entity",
        "record_type": "future_workspace_record",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(unknown) + "\n")
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )

    removed_before = purge_legacy_events(
        before=datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
    )
    removed_owner = purge_legacy_events(user_id=owner)

    assert removed_before == 1
    assert removed_owner == 1
    rows = read_all_legacy_events(path)
    assert unknown in rows
    recognized = [row for row in rows if row != unknown]
    assert [row["user_id"] for row in recognized] == [other]


def test_repeated_reset_route_keeps_one_monotonic_cutoff(logged_in_client, pg_db):
    no_csrf = logged_in_client.client.post(
        "/api/me/recommendations/reset", headers=logged_in_client.headers
    )
    first = logged_in_client.client.post(
        "/api/me/recommendations/reset", headers=logged_in_client.csrf_headers
    )
    second = logged_in_client.client.post(
        "/api/me/recommendations/reset", headers=logged_in_client.csrf_headers
    )

    assert no_csrf.status_code == 403
    assert first.status_code == second.status_code == 200
    assert first.headers["Cache-Control"] == second.headers["Cache-Control"] == "no-store"
    assert (
        datetime.fromisoformat(second.json()["recommendation_reset_at"])
        >= datetime.fromisoformat(first.json()["recommendation_reset_at"])
    )
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count, MAX(revision) AS revision "
            "FROM user_preferences WHERE user_id = %s::uuid",
            (logged_in_client.owner,),
        )
    assert pg_db._row_to_dict(row) == {"count": 1, "revision": 2}


def test_event_route_persists_safe_owner_event_without_legacy_jsonl(
    logged_in_client, users, tmp_path, monkeypatch
):
    owner, other = users
    legacy_path = tmp_path / "new-write-must-not-use-legacy.jsonl"
    monkeypatch.setattr(public_api, "USER_EVENTS_FILE", legacy_path, raising=False)
    payload = {
        "event_type": "entity_view",
        "context": "entity",
        "entity_id": "entity-1",
        "entity_type": "dish",
        "area_id": "province-vl",
        "interest_keys": ["food"],
        "user_id": other,
        "query": "private-route-query",
        "ip": "203.0.113.10",
        "latitude": 10.25,
        "longitude": 105.97,
        "metadata": {"private": "route"},
    }

    unauthenticated = logged_in_client.client.post("/api/me/events", json=payload)
    no_csrf = logged_in_client.client.post(
        "/api/me/events", json=payload, headers=logged_in_client.headers
    )
    response = logged_in_client.client.post(
        "/api/me/events", json=payload, headers=logged_in_client.csrf_headers
    )

    assert unauthenticated.status_code == 401
    assert no_csrf.status_code == 403
    assert response.status_code == 202
    assert response.headers["Cache-Control"] == "no-store"
    assert read_personalization_events(owner, cutoff=None)[0]["interest_keys"] == [
        "food"
    ]
    assert read_personalization_events(other, cutoff=None) == []
    assert not legacy_path.exists()


def _set_preferences(pg_db, user_id: str, **values) -> None:
    defaults = {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "default",
        "location_accuracy": "unknown",
        "location_consent_state": "unknown",
        "location_enabled": False,
        "personalization_enabled": False,
        "explicit_interests": [],
        "recommendation_reset_at": None,
        "revision": 0,
    }
    defaults.update(values)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_preferences
                (user_id, region_id, region_label, region_scope, location_source,
                 location_accuracy, location_consent_state, location_enabled,
                 personalization_enabled, explicit_interests,
                 recommendation_reset_at, revision)
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                region_id = EXCLUDED.region_id,
                region_label = EXCLUDED.region_label,
                region_scope = EXCLUDED.region_scope,
                location_source = EXCLUDED.location_source,
                location_accuracy = EXCLUDED.location_accuracy,
                location_consent_state = EXCLUDED.location_consent_state,
                location_enabled = EXCLUDED.location_enabled,
                personalization_enabled = EXCLUDED.personalization_enabled,
                explicit_interests = EXCLUDED.explicit_interests,
                recommendation_reset_at = EXCLUDED.recommendation_reset_at,
                revision = EXCLUDED.revision
            """,
            (
                user_id,
                defaults["region_id"],
                defaults["region_label"],
                defaults["region_scope"],
                defaults["location_source"],
                defaults["location_accuracy"],
                defaults["location_consent_state"],
                defaults["location_enabled"],
                defaults["personalization_enabled"],
                json.dumps(defaults["explicit_interests"]),
                defaults["recommendation_reset_at"],
                defaults["revision"],
            ),
        )


def _seed_entity(pg_db, entity_id: str, *, name: str, entity_type: str, area: str):
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO entities (id, type, name, summary, area, status, verified) "
            "VALUES (%s, %s, %s, %s, %s, 'published', 1)",
            (entity_id, entity_type, name, name, area),
        )


def test_scoring_reset_excludes_old_events_saved_and_visit_signals(pg_db, users):
    owner, _ = users
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    _set_preferences(
        pg_db,
        owner,
        personalization_enabled=True,
        recommendation_reset_at=cutoff,
    )
    _seed_entity(
        pg_db,
        "old-garden",
        name="Vuon trai cay",
        entity_type="attraction",
        area="old-area",
    )
    _seed_entity(
        pg_db,
        "old-craft",
        name="Lang nghe gom",
        entity_type="craft_village",
        area="old-area",
    )
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO saved_entities (user_id, entity_id, created_at) "
            "VALUES (%s::uuid, 'old-garden', %s)",
            (owner, cutoff - timedelta(hours=2)),
        )
        pg_db._execute(
            conn,
            "INSERT INTO user_visits (user_id, entity_id, created_at) "
            "VALUES (%s::uuid, 'old-craft', %s)",
            (owner, cutoff - timedelta(hours=1)),
        )
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "interest_keys": ["culture"],
            "occurred_at": cutoff - timedelta(minutes=1),
        },
    )
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "interest_keys": ["food"],
            "occurred_at": cutoff + timedelta(minutes=1),
        },
    )

    profile = public_api._build_user_interest_profile(owner)

    assert [item["key"] for item in profile["interests"]] == ["food"]
    assert profile["areas"] == []
    assert profile["types"] == []
    assert profile["signal_count"] == 1


def test_explicit_interests_outrank_inferred_event_interests(pg_db, users):
    owner, _ = users
    _set_preferences(
        pg_db,
        owner,
        personalization_enabled=True,
        explicit_interests=["culture"],
    )
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            """
            INSERT INTO user_personalization_events
                (id, user_id, event_type, context, interest_keys, expires_at)
            SELECT uuid_generate_v4(), %s::uuid, 'entity_view', 'entity',
                   jsonb_build_array('food'), NOW() + INTERVAL '1 day'
            FROM generate_series(1, 300)
            """,
            (owner,),
        )

    profile = public_api._build_user_interest_profile(owner)

    assert profile["interests"][0]["key"] == "culture"
    assert profile["interest_scores"]["culture"] > profile["interest_scores"]["food"]


def test_personalization_off_uses_manual_region_only_and_drops_resolver_region(
    pg_db, users
):
    owner, _ = users
    _set_preferences(
        pg_db,
        owner,
        region_id="province-vl",
        region_label="Vinh Long",
        region_scope="province",
        location_source="manual",
        location_enabled=False,
        personalization_enabled=False,
        explicit_interests=["culture"],
    )
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "interest_keys": ["food"],
        },
    )

    manual = public_api._build_user_interest_profile(
        owner, query="food", context_entity={"type": "dish", "area": "query-area"}
    )
    _set_preferences(
        pg_db,
        owner,
        region_id="gps-region",
        region_label="GPS region",
        region_scope="province",
        location_source="gps",
        location_enabled=False,
        personalization_enabled=False,
    )
    resolver_off = public_api._build_user_interest_profile(owner)

    assert manual["interests"] == []
    assert manual["types"] == []
    assert manual["areas"] == [{"key": "province-vl", "score": 50.0}]
    assert resolver_off["areas"] == []


def test_export_includes_safe_preferences_consents_new_and_filtered_legacy_events(
    auth_client, pg_db, tmp_path, monkeypatch
):
    cutoff = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
    _set_preferences(
        pg_db,
        auth_client.owner,
        personalization_enabled=True,
        explicit_interests=["food"],
        recommendation_reset_at=cutoff,
    )
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO user_preference_consents "
            "(id, user_id, consent_type, state, version) "
            "VALUES (%s, %s::uuid, 'personalization', 'granted', 'privacy-v1')",
            (str(uuid4()), auth_client.owner),
        )
    write_personalization_event(
        auth_client.owner,
        {
            "event_type": "search_submit",
            "context": "search",
            "interest_keys": ["food"],
            "query": "private-new-query",
            "ip": "203.0.113.9",
            "metadata": {"private": "new"},
        },
    )
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [auth_client.owner, auth_client.owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "legacy_cutover_deadline",
        lambda: datetime(2026, 8, 30, tzinfo=timezone.utc),
    )

    response = auth_client.client.get(
        "/auth/export-data", headers=auth_client.headers
    )

    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "no-store"
    exported = response.json()["personalization"]
    assert exported["preferences"]["explicit_interests"] == ["food"]
    assert [(row["consent_type"], row["state"]) for row in exported["consents"]] == [
        ("personalization", "granted")
    ]
    assert exported["events"][0]["interest_keys"] == ["food"]
    assert len(exported["legacy_events"]) == 1
    serialized = json.dumps(exported, ensure_ascii=True)
    assert "private-new-query" not in serialized
    assert "private-query" not in serialized
    assert "203.0.113.9" not in serialized
    assert "metadata" not in serialized


def test_scheduling_delete_only_inactivates_and_keeps_personalization(
    auth_client, pg_db, tmp_path, monkeypatch
):
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)
    write_personalization_event(
        auth_client.owner,
        {"event_type": "entity_view", "context": "entity"},
    )
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [auth_client.owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)

    response = auth_client.client.delete(
        "/auth/account", headers=auth_client.csrf_headers
    )

    assert response.status_code == 200
    with pg_db._conn(commit_on_success=False) as conn:
        user_row = pg_db._fetchone(
            conn,
            "SELECT is_active, deleted_at FROM users WHERE id = %s::uuid",
            (auth_client.owner,),
        )
        preference_count = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM user_preferences WHERE user_id = %s::uuid",
            (auth_client.owner,),
        )
    assert pg_db._row_to_dict(user_row)["is_active"] is False
    assert pg_db._row_to_dict(user_row)["deleted_at"] is not None
    assert pg_db._row_to_dict(preference_count)["count"] == 1
    assert len(read_personalization_events(auth_client.owner, cutoff=None)) == 1
    assert len(read_all_legacy_events(path)) == 1


def test_final_personalization_purge_keeps_user_and_other_users_rows(pg_db, users):
    owner, other = users
    for user_id in (owner, other):
        _set_preferences(pg_db, user_id, personalization_enabled=True)
        with pg_db._conn() as conn:
            pg_db._execute(
                conn,
                "INSERT INTO user_preference_consents "
                "(id, user_id, consent_type, state, version) "
                "VALUES (%s, %s::uuid, 'personalization', 'granted', 'privacy-v1')",
                (str(uuid4()), user_id),
            )
        write_personalization_event(
            user_id, {"event_type": "entity_view", "context": "entity"}
        )

    purge_user_personalization(owner)

    with pg_db._conn(commit_on_success=False) as conn:
        owner_exists = pg_db._fetchone(
            conn, "SELECT 1 AS present FROM users WHERE id = %s::uuid", (owner,)
        )
        counts = pg_db._fetchone(
            conn,
            "SELECT "
            "(SELECT COUNT(*) FROM user_preferences) AS preferences, "
            "(SELECT COUNT(*) FROM user_preference_consents) AS consents, "
            "(SELECT COUNT(*) FROM user_personalization_events) AS events",
        )
    assert pg_db._row_to_dict(owner_exists) == {"present": 1}
    assert pg_db._row_to_dict(counts) == {
        "preferences": 1,
        "consents": 1,
        "events": 1,
    }


def test_scheduler_ttl_cleanup_deletes_only_expired_events(pg_db, users):
    owner, other = users
    now = datetime.now(timezone.utc)
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "expires_at": now - timedelta(seconds=1),
        },
    )
    write_personalization_event(
        other,
        {
            "event_type": "entity_view",
            "context": "entity",
            "expires_at": now + timedelta(days=1),
        },
    )

    scheduler.task_personalization_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        count = pg_db._fetchone(
            conn, "SELECT COUNT(*) AS count FROM user_personalization_events"
        )
    assert pg_db._row_to_dict(count)["count"] == 1
    assert any(task.name == "personalization-cleanup" for task in scheduler.TASKS)


def test_scheduler_legacy_failure_rolls_back_user_and_postgres_purge_for_retry(
    pg_db, users, tmp_path, monkeypatch
):
    stale, active = users
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE users SET deleted_at = NOW() - INTERVAL '31 days', "
            "is_active = FALSE WHERE id = %s::uuid",
            (stale,),
        )
    for user_id in (stale, active):
        _set_preferences(pg_db, user_id, personalization_enabled=True)
        with pg_db._conn() as conn:
            pg_db._execute(
                conn,
                "INSERT INTO user_preference_consents "
                "(id, user_id, consent_type, state, version) "
                "VALUES (%s, %s::uuid, 'personalization', 'granted', 'privacy-v1')",
                (str(uuid4()), user_id),
            )
        write_personalization_event(
            user_id, {"event_type": "entity_view", "context": "entity"}
        )
    path = tmp_path / "legacy-events.jsonl"
    lock_path = tmp_path / ".legacy-events.publication.lock"
    seed_legacy_events(path, [stale, active])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_LOCK_PATH", lock_path)

    with monkeypatch.context() as failure_patch:
        failure_patch.setattr(
            personalization_events,
            "purge_legacy_events",
            lambda **_kwargs: (_ for _ in ()).throw(OSError("legacy purge failed")),
        )
        scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        failed_counts = pg_db._fetchone(
            conn,
            "SELECT "
            "(SELECT COUNT(*) FROM users) AS users, "
            "(SELECT COUNT(*) FROM user_preferences) AS preferences, "
            "(SELECT COUNT(*) FROM user_preference_consents) AS consents, "
            "(SELECT COUNT(*) FROM user_personalization_events) AS events",
        )
    assert pg_db._row_to_dict(failed_counts) == {
        "users": 2,
        "preferences": 2,
        "consents": 2,
        "events": 2,
    }
    assert [row["user_id"] for row in read_all_legacy_events(path)] == [stale, active]

    scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        successful_counts = pg_db._fetchone(
            conn,
            "SELECT "
            "(SELECT COUNT(*) FROM users) AS users, "
            "(SELECT COUNT(*) FROM user_preferences) AS preferences, "
            "(SELECT COUNT(*) FROM user_preference_consents) AS consents, "
            "(SELECT COUNT(*) FROM user_personalization_events) AS events",
        )
    assert pg_db._row_to_dict(successful_counts) == {
        "users": 1,
        "preferences": 1,
        "consents": 1,
        "events": 1,
    }
    assert [row["user_id"] for row in read_all_legacy_events(path)] == [active]


def test_scheduler_final_delete_purges_only_matching_legacy_rows(
    pg_db, users, tmp_path, monkeypatch
):
    stale, active = users
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE users SET deleted_at = NOW() - INTERVAL '31 days', "
            "is_active = FALSE WHERE id = %s::uuid",
            (stale,),
        )
    for user_id in (stale, active):
        _set_preferences(pg_db, user_id, personalization_enabled=True)
        write_personalization_event(
            user_id, {"event_type": "entity_view", "context": "entity"}
        )
    path = tmp_path / "legacy-events.jsonl"
    lock_path = tmp_path / ".legacy-events.publication.lock"
    seed_legacy_events(path, [stale, active])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_LOCK_PATH", lock_path)

    scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        users_left = pg_db._fetchall(conn, "SELECT id FROM users ORDER BY id")
        event_users = pg_db._fetchall(
            conn, "SELECT user_id FROM user_personalization_events ORDER BY user_id"
        )
    assert [str(row["id"]) for row in users_left] == [active]
    assert [str(row["user_id"]) for row in event_users] == [active]
    assert [row["user_id"] for row in read_all_legacy_events(path)] == [active]
