"""Integration coverage for privacy-safe personalization event persistence."""

from __future__ import annotations

import os
import json
import multiprocessing
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
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

_LOCATION_PREFERENCE_CONSTRAINTS = (
    "ck_user_preferences_revision_json_safe",
    "ck_user_preferences_region_text_safe_v2",
    "ck_user_preferences_region_tuple_v2",
    "ck_user_preferences_reconfirm_state_v1",
)


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS schema_version (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    migration TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
    location_reconfirm_required BOOLEAN NOT NULL DEFAULT FALSE,
    location_provenance_version VARCHAR(32),
    revision BIGINT NOT NULL DEFAULT 0,
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
    migration_dir = Path(__file__).resolve().parent.parent / "migrations"
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS personalization_legacy_purge_queue")
            cursor.execute(SCHEMA_SQL)
            cursor.execute(
                (migration_dir / "072_personalization_legacy_purge_queue.sql").read_text(
                    encoding="utf-8"
                )
            )
            for constraint in _LOCATION_PREFERENCE_CONSTRAINTS:
                cursor.execute(
                    f"ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS {constraint}"
                )
            cursor.execute(
                (migration_dir / "073_location_preference_remediation.sql").read_text(
                    encoding="utf-8"
                )
            )
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
    monkeypatch.setattr(
        public_api,
        "settings",
        SimpleNamespace(
            PREFERENCE_PROFILE_V1=True,
            LOCATION_RESOLVER_V1=True,
            RECOMMENDATION_EXPLANATIONS_V1=True,
            TRUST_DRAWER_V1=True,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        personalization_events,
        "settings",
        SimpleNamespace(
            PERSONALIZATION_EVENTS_PG=True,
            LEGACY_EVENT_READ_UNTIL="",
        ),
    )
    with adapter._conn() as conn:
        adapter._execute(
            conn,
            "TRUNCATE personalization_legacy_purge_queue, "
            "user_personalization_events, user_preference_consents, "
            "user_preferences, saved_entities, user_visits, posts, comments, likes, "
            "bookmarks, follows, post_reactions, user_collections, blocks, user_mutes, "
            "user_sessions, otp_sessions, login_history, notifications, entities, users CASCADE",
        )
    yield adapter
    with adapter._conn() as conn:
        adapter._execute(
            conn,
            "TRUNCATE personalization_legacy_purge_queue, "
            "user_personalization_events, user_preference_consents, "
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


def _public_score_paths(value, path="$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            folded = str(key).casefold()
            if "score" in folded or "weight" in folded:
                found.append(child)
            found.extend(_public_score_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_public_score_paths(item, f"{path}[{index}]"))
    return found


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


@pytest.fixture
def canonical_event_entities(pg_db):
    entities = {
        "entity-1": ("dish", "province-vl"),
        "craft_village_x": ("economy", "ward-economy"),
        "0901234567": ("dish", "ward-numeric"),
        "2024-01-02-01": ("product", "ward-four-part"),
    }
    for entity_id, (entity_type, place_id) in entities.items():
        _seed_entity(
            pg_db,
            entity_id,
            name=f"Canonical {entity_id}",
            entity_type=entity_type,
            area=f"Label {place_id}",
            place_id=place_id,
        )
    return entities


@pytest.mark.parametrize(
    "payload",
    [
        {
            "region_id": "203.0.113.8",
            "region_label": "203.0.113.8",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
        },
        {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_source": "gps",
            "location_accuracy": "province",
            "location_enabled": True,
        },
        {
            "region_id": "client-invented-region",
            "region_label": "Client invented region",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
        },
    ],
)
def test_postgres_preference_route_rejects_forged_region_without_writing(
    logged_in_client, pg_db, payload
):
    response = logged_in_client.client.patch(
        "/api/me/preferences",
        json={"revision": 0, **payload},
        headers=logged_in_client.csrf_headers,
    )

    assert response.status_code == 422
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM user_preferences WHERE user_id = %s::uuid",
            (logged_in_client.owner,),
        )
    assert int(pg_db._row_to_dict(row)["count"]) == 0


def test_postgres_preference_route_persists_valid_manual_and_token_regions_only(
    logged_in_client, pg_db
):
    logged_in_client.client.app.dependency_overrides[
        public_api.get_reverse_geocoder
    ] = lambda: (
        lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    resolution = logged_in_client.client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_client.csrf_headers,
    )
    assert resolution.status_code == 200
    token = resolution.json()["confirmation_token"]

    confirmed = logged_in_client.client.patch(
        "/api/me/preferences",
        json={
            "revision": 0,
            "location_confirmation_token": token,
            "location_consent_state": "granted",
            "location_enabled": True,
        },
        headers=logged_in_client.csrf_headers,
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["region_id"] == "province-vl"
    assert confirmed.json()["location_source"] == "gps"

    manual = logged_in_client.client.patch(
        "/api/me/preferences",
        json={
            "revision": 1,
            "region_id": "province-bt",
            "region_label": "Bến Tre",
            "region_scope": "province",
            "location_source": "manual",
            "location_accuracy": "province",
        },
        headers=logged_in_client.csrf_headers,
    )
    assert manual.status_code == 200
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT region_id, region_label, location_source, revision "
            "FROM user_preferences WHERE user_id = %s::uuid",
            (logged_in_client.owner,),
        )
        columns = pg_db._fetchall(
            conn,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'user_preferences'",
            (),
        )
    stored = pg_db._row_to_dict(row)
    assert stored == {
        "region_id": "province-bt",
        "region_label": "Bến Tre",
        "location_source": "manual",
        "revision": 2,
    }
    assert "confirmation_token" not in {
        pg_db._row_to_dict(column)["column_name"] for column in columns
    }


def test_postgres_confirmation_token_has_one_atomic_winner(auth_client):
    auth_client.client.app.dependency_overrides[public_api.get_reverse_geocoder] = (
        lambda: lambda *_: {
            "region_id": "province-vl",
            "region_label": "Vĩnh Long",
            "region_scope": "province",
            "location_accuracy": "province",
        }
    )
    resolution = auth_client.client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=auth_client.csrf_headers,
    )
    assert resolution.status_code == 200, resolution.text
    assert resolution.headers["Cache-Control"] == "no-store"
    token = resolution.json()["confirmation_token"]
    barrier = threading.Barrier(2)

    def confirm_once():
        barrier.wait(timeout=5)
        return auth_client.client.patch(
            "/api/me/preferences",
            json={
                "revision": 0,
                "location_confirmation_token": token,
                "location_consent_state": "granted",
                "location_enabled": True,
            },
            headers=auth_client.csrf_headers,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: confirm_once(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    assert all(response.headers["Cache-Control"] == "no-store" for response in responses)
    assert {response.json()["revision"] for response in responses} == {1}
    current_response = auth_client.client.get(
        "/api/me/preferences",
        headers=auth_client.headers,
    )
    assert current_response.status_code == 200, current_response.text
    assert current_response.headers["Cache-Control"] == "no-store"
    current = current_response.json()
    assert current["revision"] == 1
    assert current["location_source"] == "gps"


def test_contextual_response_recursively_omits_internal_scores(
    logged_in_client, pg_db, monkeypatch
):
    _set_preferences(
        pg_db,
        logged_in_client.owner,
        personalization_enabled=True,
        explicit_interests=["food"],
    )
    candidate = {
        "id": "public-context-card",
        "name": "Bánh dân gian",
        "type": "dish",
        "summary": "Món bánh truyền thống",
        "placeId": None,
        "area": "province-vl",
        "attributes": {"rating": 4.5, "review_count": 12},
        "source": {
            "title": "Cổng thông tin tỉnh",
            "url": "https://example.gov.vn/banh-dan-gian",
        },
        "images": [],
        "coordinates": None,
        "status": "published",
        "verified": 1,
        "updatedAt": "2026-07-28T00:00:00Z",
    }
    monkeypatch.setattr(
        public_api,
        "_gather_recommendation_candidates",
        lambda *_: {candidate["id"]: candidate},
    )

    internal = public_api._build_user_interest_profile(logged_in_client.owner)
    response = logged_in_client.client.get(
        "/api/me/recommendations/contextual?context=home&limit=3",
        headers=logged_in_client.headers,
    )

    assert internal["interests"][0]["score"] > 0
    assert response.status_code == 200
    assert response.json()["profile"]["interests"][0]["key"] == "food"
    assert _public_score_paths(response.json()) == []


def test_insights_response_recursively_omits_internal_scores(
    logged_in_client, pg_db
):
    _set_preferences(
        pg_db,
        logged_in_client.owner,
        personalization_enabled=True,
        explicit_interests=["culture"],
    )

    internal = public_api._build_user_interest_profile(logged_in_client.owner)
    response = logged_in_client.client.get(
        "/api/me/insights", headers=logged_in_client.headers
    )

    assert internal["interest_scores"]["culture"] > 0
    assert response.status_code == 200
    assert response.json()["interests"][0]["key"] == "culture"
    assert _public_score_paths(response.json()) == []


def test_event_writer_drops_sensitive_and_arbitrary_fields(
    pg_db, users, canonical_event_entities
):
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
        "interest_keys": ["food"],
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
    ("event_type", "context", "entity_id", "interest_keys"),
)
@pytest.mark.parametrize("smuggled", _SMUGGLED_VALUES)
def test_direct_writer_rejects_sensitive_text_in_every_validated_carrier(
    pg_db, users, canonical_event_entities, carrier, smuggled
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
        ("interest_keys", "so dien thoai rieng tu"),
    ),
)
def test_event_route_rejects_smuggling_without_storage_export_or_scoring(
    auth_client, pg_db, canonical_event_entities, carrier, smuggled
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
    _seed_entity(
        pg_db,
        entity_id,
        name=f"Canonical {entity_id}",
        entity_type="dish",
        area="Vinh Long",
        place_id="province-vl",
    )

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


def test_direct_writer_rejects_oversized_entity_id_instead_of_truncating(
    pg_db, users
):
    owner, _ = users
    event = {
        "event_type": "entity_view",
        "context": "entity",
        "entity_id": "a" * 201,
        "entity_type": "dish",
        "area_id": "province-vl",
        "interest_keys": ["food"],
    }

    with pytest.raises(personalization_events.PersonalizationEventError):
        write_personalization_event(owner, event)

    assert read_personalization_events(owner, cutoff=None) == []


_NON_MEMBER_IDENTIFIERS = (
    "090-123-4567",
    "phone-0901234567",
    "ip-203-0-113-8",
    "gps-10-2500-105-9700",
    "safe-looking-slug",
)


@pytest.mark.parametrize("entity_id", _NON_MEMBER_IDENTIFIERS)
def test_direct_writer_rejects_every_non_member_entity_identifier(
    pg_db, users, entity_id
):
    owner, _ = users

    with pytest.raises(personalization_events.PersonalizationEventError):
        write_personalization_event(
            owner,
            {
                "event_type": "entity_view",
                "context": "entity",
                "entity_id": entity_id,
                "entity_type": "dish",
                "area_id": "client-area",
                "interest_keys": ["food"],
            },
        )

    assert read_personalization_events(owner, cutoff=None) == []


@pytest.mark.parametrize("entity_id", _NON_MEMBER_IDENTIFIERS)
def test_event_route_rejects_every_non_member_identifier_without_use(
    auth_client, pg_db, entity_id
):
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)
    payload = {
        "event_type": "entity_view",
        "context": "entity",
        "entity_id": entity_id,
        "entity_type": "dish",
        "area_id": "client-area",
        "interest_keys": ["food"],
    }

    response = auth_client.client.post(
        "/api/me/events", json=payload, headers=auth_client.csrf_headers
    )
    exported = auth_client.client.get(
        "/auth/export-data", headers=auth_client.headers
    )
    profile = public_api._build_user_interest_profile(auth_client.owner)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid personalization event"}
    assert entity_id not in response.text
    assert exported.status_code == 200
    assert exported.json()["personalization"]["events"] == []
    assert profile["signal_count"] == 0
    assert profile["recent_entity_ids"] == []
    assert profile["areas"] == []
    assert profile["types"] == []


@pytest.mark.parametrize(
    ("entity_id", "canonical_type", "canonical_area"),
    (
        ("craft_village_x", "economy", "ward-economy"),
        ("0901234567", "dish", "ward-numeric"),
        ("2024-01-02-01", "product", "ward-four-part"),
    ),
)
def test_direct_writer_derives_fields_from_canonical_entity_membership(
    pg_db,
    users,
    canonical_event_entities,
    entity_id,
    canonical_type,
    canonical_area,
):
    owner, _ = users
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": entity_id,
            "entity_type": "person",
            "area_id": "spoofed-client-area",
            "interest_keys": ["food"],
        },
    )

    row = read_personalization_events(owner, cutoff=None)[0]
    assert row["entity_id"] == entity_id
    assert row["entity_type"] == canonical_type
    assert row["area_id"] == canonical_area


@pytest.mark.parametrize(
    ("entity_id", "canonical_type", "canonical_area"),
    (
        ("craft_village_x", "economy", "ward-economy"),
        ("0901234567", "dish", "ward-numeric"),
        ("2024-01-02-01", "product", "ward-four-part"),
    ),
)
def test_event_route_derives_fields_from_canonical_entity_membership(
    auth_client,
    canonical_event_entities,
    entity_id,
    canonical_type,
    canonical_area,
):
    response = auth_client.client.post(
        "/api/me/events",
        json={
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": entity_id,
            "entity_type": "person",
            "area_id": "spoofed-client-area",
            "entity_name": "Spoofed client name",
            "metadata": {},
        },
        headers=auth_client.csrf_headers,
    )

    assert response.status_code == 202, response.text
    assert response.headers["Cache-Control"] == "no-store"
    row = read_personalization_events(auth_client.owner, cutoff=None)[0]
    assert row["entity_id"] == entity_id
    assert row["entity_type"] == canonical_type
    assert row["area_id"] == canonical_area


_ENTITY_REQUIRED_EVENTS = (
    ("entity_view", "entity"),
    ("save_add", "saved"),
    ("save_remove", "saved"),
    ("visit_mark", "entity"),
    ("map_focus", "map"),
    ("itinerary_view", "itinerary"),
)


@pytest.mark.parametrize(("event_type", "context"), _ENTITY_REQUIRED_EVENTS)
def test_direct_writer_rejects_entity_bound_event_without_entity_id(
    pg_db, users, event_type, context
):
    owner, _ = users

    with pytest.raises(personalization_events.PersonalizationEventError):
        write_personalization_event(
            owner,
            {
                "event_type": event_type,
                "context": context,
                "entity_type": "dish",
                "area_id": "client-area",
                "interest_keys": ["food"],
            },
        )

    assert read_personalization_events(owner, cutoff=None) == []


@pytest.mark.parametrize(("event_type", "context"), _ENTITY_REQUIRED_EVENTS)
def test_event_route_rejects_entity_bound_event_without_entity_id_or_signals(
    auth_client, pg_db, event_type, context
):
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)

    response = auth_client.client.post(
        "/api/me/events",
        json={
            "event_type": event_type,
            "context": context,
            "entity_type": "dish",
            "area_id": "client-area",
            "interest_keys": ["food"],
        },
        headers=auth_client.csrf_headers,
    )
    exported = auth_client.client.get(
        "/auth/export-data", headers=auth_client.headers
    )
    profile = public_api._build_user_interest_profile(auth_client.owner)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid personalization event"}
    assert exported.status_code == 200
    assert exported.json()["personalization"]["events"] == []
    assert profile["signal_count"] == 0
    assert profile["interests"] == []
    assert profile["areas"] == []
    assert profile["types"] == []


_NON_PUBLIC_ENTITY_CASES = (
    ("provisional", "provisional", 1),
    ("verified-false", "published", False),
    ("verified-zero", "published", 0),
)


@pytest.mark.parametrize(
    ("case_name", "status", "verified"), _NON_PUBLIC_ENTITY_CASES
)
def test_direct_writer_rejects_non_public_canonical_entity(
    pg_db, users, case_name, status, verified
):
    owner, _ = users
    entity_id = f"non-public-{case_name}"
    _seed_entity(
        pg_db,
        entity_id,
        name="Bun nuoc leo private",
        entity_type="dish",
        area="Private area",
        place_id="private-area",
        status=status,
        verified=verified,
    )

    with pytest.raises(personalization_events.PersonalizationEventError):
        write_personalization_event(
            owner,
            {
                "event_type": "entity_view",
                "context": "entity",
                "entity_id": entity_id,
                "interest_keys": ["food"],
            },
        )

    assert read_personalization_events(owner, cutoff=None) == []


@pytest.mark.parametrize(
    ("case_name", "status", "verified"), _NON_PUBLIC_ENTITY_CASES
)
def test_event_route_rejects_non_public_canonical_entity_without_signals(
    auth_client, pg_db, case_name, status, verified
):
    entity_id = f"non-public-{case_name}"
    _seed_entity(
        pg_db,
        entity_id,
        name="Bun nuoc leo private",
        entity_type="dish",
        area="Private area",
        place_id="private-area",
        status=status,
        verified=verified,
    )
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)

    response = auth_client.client.post(
        "/api/me/events",
        json={
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": entity_id,
            "entity_type": "person",
            "area_id": "client-area",
            "interest_keys": ["culture"],
        },
        headers=auth_client.csrf_headers,
    )
    exported = auth_client.client.get(
        "/auth/export-data", headers=auth_client.headers
    )
    profile = public_api._build_user_interest_profile(auth_client.owner)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid personalization event"}
    assert entity_id not in response.text
    assert exported.status_code == 200
    assert exported.json()["personalization"]["events"] == []
    assert profile["signal_count"] == 0
    assert profile["interests"] == []
    assert profile["areas"] == []
    assert profile["types"] == []


@pytest.mark.parametrize(("case_name", "verified"), (("verified", 1), ("verified-null", None)))
def test_direct_writer_derives_all_fields_from_public_canonical_entity(
    pg_db, users, case_name, verified
):
    owner, _ = users
    entity_id = f"public-{case_name}"
    _seed_entity(
        pg_db,
        entity_id,
        name="Bun nuoc leo canonical",
        entity_type="dish",
        area="Canonical area",
        place_id="canonical-area",
        verified=verified,
    )

    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": entity_id,
            "entity_type": "person",
            "area_id": "client-area",
            "interest_keys": ["culture"],
        },
    )

    row = read_personalization_events(owner, cutoff=None)[0]
    assert row["entity_id"] == entity_id
    assert row["entity_type"] == "dish"
    assert row["area_id"] == "canonical-area"
    assert row["interest_keys"] == ["food"]


@pytest.mark.parametrize(("case_name", "verified"), (("verified", 1), ("verified-null", None)))
def test_event_route_derives_all_fields_from_public_canonical_entity(
    auth_client, pg_db, case_name, verified
):
    entity_id = f"public-{case_name}"
    _seed_entity(
        pg_db,
        entity_id,
        name="Bun nuoc leo canonical",
        entity_type="dish",
        area="Canonical area",
        place_id="canonical-area",
        verified=verified,
    )

    response = auth_client.client.post(
        "/api/me/events",
        json={
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": entity_id,
            "entity_type": "person",
            "area_id": "client-area",
            "interest_keys": ["culture"],
        },
        headers=auth_client.csrf_headers,
    )

    assert response.status_code == 202, response.text
    row = read_personalization_events(auth_client.owner, cutoff=None)[0]
    assert row["entity_id"] == entity_id
    assert row["entity_type"] == "dish"
    assert row["area_id"] == "canonical-area"
    assert row["interest_keys"] == ["food"]


_AGGREGATE_EVENTS = (
    ("search", "search_submit"),
    ("community_view", "community"),
    ("post_view", "community"),
)


@pytest.mark.parametrize(("event_type", "context"), _AGGREGATE_EVENTS)
def test_direct_writer_accepts_aggregate_event_without_entity_and_discards_client_signals(
    pg_db, users, event_type, context
):
    owner, _ = users

    write_personalization_event(
        owner,
        {
            "event_type": event_type,
            "context": context,
            "entity_type": "dish",
            "area_id": "client-area",
            "interest_keys": ["food"],
        },
    )

    row = read_personalization_events(owner, cutoff=None)[0]
    assert row["entity_id"] is None
    assert row["entity_type"] is None
    assert row["area_id"] is None
    assert row["interest_keys"] == []


@pytest.mark.parametrize(("event_type", "context"), _AGGREGATE_EVENTS)
def test_event_route_accepts_aggregate_event_without_entity_and_discards_client_signals(
    auth_client, pg_db, event_type, context
):
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)

    response = auth_client.client.post(
        "/api/me/events",
        json={
            "event_type": event_type,
            "context": context,
            "entity_type": "dish",
            "area_id": "client-area",
            "interest_keys": ["food"],
        },
        headers=auth_client.csrf_headers,
    )
    exported = auth_client.client.get(
        "/auth/export-data", headers=auth_client.headers
    )
    profile = public_api._build_user_interest_profile(auth_client.owner)

    assert response.status_code == 202, response.text
    row = exported.json()["personalization"]["events"][0]
    assert row["entity_id"] is None
    assert row["entity_type"] is None
    assert row["area_id"] is None
    assert row["interest_keys"] == []
    assert profile["signal_count"] == 1
    assert profile["interests"] == []
    assert profile["areas"] == []
    assert profile["types"] == []


@pytest.mark.parametrize("context", ("search_trending", "search_submit"))
def test_search_route_accepts_without_entity_and_drops_client_entity_fields(
    auth_client, context
):
    response = auth_client.client.post(
        "/api/me/events",
        json={
            "event_type": "search",
            "context": context,
            "query": "bun nuoc leo",
            "entity_type": "economy",
            "area_id": "090-123-4567",
            "metadata": {},
        },
        headers=auth_client.csrf_headers,
    )

    assert response.status_code == 202, response.text
    row = read_personalization_events(auth_client.owner, cutoff=None)[0]
    assert row["context"] == context
    assert row["entity_id"] is None
    assert row["entity_type"] is None
    assert row["area_id"] is None


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
                "event_type": "search",
                "context": "search",
                "occurred_at": occurred_at,
                "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
            },
        )
    write_personalization_event(
        owner,
        {
            "event_type": "search",
            "context": "search",
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
                "event_type": "search",
                "context": "search",
                "expires_at": expires_at,
            },
        )

    assert purge_personalization_events(before=now) == 1
    assert len(read_personalization_events(owner, cutoff=None)) == 1
    assert purge_personalization_events(user_id=owner) == 1
    assert read_personalization_events(owner, cutoff=None) == []
    assert len(read_personalization_events(other, cutoff=None)) == 1


def test_migration_072_queue_contract_survives_schema_073_fixture(pg_db):
    with pg_db._conn(commit_on_success=False) as conn:
        columns = pg_db._fetchall(
            conn,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'personalization_legacy_purge_queue'",
        )
        foreign_keys = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM information_schema.table_constraints "
            "WHERE table_schema = 'public' "
            "AND table_name = 'personalization_legacy_purge_queue' "
            "AND constraint_type = 'FOREIGN KEY'",
        )
        indexes = pg_db._fetchall(
            conn,
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
            "AND tablename = 'personalization_legacy_purge_queue'",
        )
        version = pg_db._fetchone(
            conn,
            "SELECT version, migration FROM schema_version "
            "WHERE component = 'agent'",
        )

    assert {row["column_name"] for row in columns} == {
        "user_id",
        "created_at",
        "attempt_count",
        "next_attempt_at",
        "last_error",
    }
    assert int(foreign_keys["count"]) == 0
    assert {
        "personalization_legacy_purge_queue_pkey",
        "idx_personalization_legacy_purge_queue_due",
    } <= {row["indexname"] for row in indexes}
    assert version["version"] == 73
    assert version["migration"] == "073_location_preference_remediation.sql"


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


def test_legacy_reader_uses_exact_rollout_deadline_setting(
    tmp_path, monkeypatch, users
):
    owner, _ = users
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    personalization_events.settings.LEGACY_EVENT_READ_UNTIL = (
        "2026-08-01T00:00:00Z"
    )

    before = read_legacy_events_if_allowed(
        owner,
        cutoff=None,
        now=datetime(2026, 7, 31, 23, 59, 59, tzinfo=timezone.utc),
    )
    after = read_legacy_events_if_allowed(
        owner,
        cutoff=None,
        now=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    assert [event["entity_id"] for event in before] == ["entity-0"]
    assert after == []


def test_legacy_reader_disables_reads_at_exact_cutover_deadline(
    tmp_path, monkeypatch, users
):
    owner, _ = users
    deadline = datetime(2026, 8, 1, tzinfo=timezone.utc)
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events, "legacy_cutover_deadline", lambda: deadline
    )

    assert read_legacy_events_if_allowed(owner, cutoff=None, now=deadline) == []


def test_legacy_reader_ignores_retired_deadline_name_and_fails_closed(
    tmp_path, monkeypatch, users
):
    owner, _ = users
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "settings",
        SimpleNamespace(
            LEGACY_EVENT_READ_UNTIL="",
            PERSONALIZATION_LEGACY_READ_DEADLINE="2026-08-30T00:00:00Z",
        ),
    )
    monkeypatch.setenv(
        "PERSONALIZATION_LEGACY_READ_DEADLINE", "2026-08-30T00:00:00Z"
    )
    monkeypatch.delenv("LEGACY_EVENT_READ_UNTIL", raising=False)

    assert personalization_events.legacy_cutover_deadline() is None
    assert read_legacy_events_if_allowed(
        owner,
        cutoff=None,
        now=datetime(2026, 7, 29, tzinfo=timezone.utc),
    ) == []


def test_preference_profile_flag_uses_public_context_without_private_reads(
    pg_db, users, monkeypatch
):
    owner, _ = users
    monkeypatch.setattr(
        public_api,
        "settings",
        SimpleNamespace(PREFERENCE_PROFILE_V1=False),
    )
    monkeypatch.setattr(
        public_api,
        "load_preferences",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("disabled profile loaded preferences")
        ),
    )
    monkeypatch.setattr(
        public_api,
        "read_personalization_events",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("disabled profile loaded events")
        ),
    )

    profile = public_api._build_user_interest_profile(
        owner,
        query="am thuc",
        context_entity={"type": "dish", "name": "Banh xeo"},
    )

    assert profile["personalization_enabled"] is False
    assert profile["preference_snapshot"] is None
    assert profile["recent_entity_ids"] == []


def test_personalization_pg_flag_prevents_new_storage_writes(pg_db, users):
    owner, _ = users
    personalization_events.settings.PERSONALIZATION_EVENTS_PG = False

    write_personalization_event(
        owner,
        {"event_type": "search", "context": "search"},
    )

    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM user_personalization_events",
        )
    assert pg_db._row_to_dict(row)["count"] == 0


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


def test_concurrent_first_recommendation_resets_are_atomic_on_postgres(
    pg_db, users, monkeypatch
):
    owner, _ = users
    original_loader_select = user_preferences._select_preferences
    original_reset_select = personalization_events._select_preferences
    loader_barrier = threading.Barrier(2)
    reset_barrier = threading.Barrier(2)

    def synchronized_loader_select(conn, user_id, *, for_update=False):
        row = original_loader_select(conn, user_id, for_update=for_update)
        if for_update and row is None:
            loader_barrier.wait(timeout=10)
        return row

    def synchronized_reset_select(conn, user_id, *, for_update=False):
        row = original_reset_select(conn, user_id, for_update=for_update)
        if for_update and row is None:
            reset_barrier.wait(timeout=10)
        return row

    monkeypatch.setattr(
        user_preferences, "_select_preferences", synchronized_loader_select
    )
    monkeypatch.setattr(
        personalization_events, "_select_preferences", synchronized_reset_select
    )
    results = []

    def reset_in_thread(index):
        try:
            snapshot = personalization_events.record_recommendation_reset(owner)
            results.append((index, "ok", snapshot["revision"]))
        except Exception as exc:  # pragma: no cover - asserted below
            results.append((index, type(exc).__name__, str(exc)))

    threads = [
        threading.Thread(target=reset_in_thread, args=(index,))
        for index in (1, 2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted((status, revision) for _, status, revision in results) == [
        ("ok", 1),
        ("ok", 2),
    ]
    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT revision FROM user_preferences WHERE user_id = %s::uuid",
            (owner,),
        )
    assert pg_db._row_to_dict(row)["revision"] == 2


@contextmanager
def _unsafe_preference(pg_db, user_id: str, *, recommendation_reset_at=None):
    migration = (
        Path(__file__).resolve().parent.parent
        / "migrations"
        / "073_location_preference_remediation.sql"
    ).read_text(encoding="utf-8")
    with pg_db._conn() as conn:
        for constraint in _LOCATION_PREFERENCE_CONSTRAINTS:
            pg_db._execute(
                conn,
                f"ALTER TABLE user_preferences DROP CONSTRAINT {constraint}",
            )
        pg_db._execute(
            conn,
            """
            INSERT INTO user_preferences
                (user_id, region_id, region_label, region_scope, location_source,
                 location_accuracy, location_consent_state, location_enabled,
                 personalization_enabled, explicit_interests,
                 recommendation_reset_at, consent_version,
                 location_reconfirm_required, location_provenance_version, revision)
            VALUES (%s::uuid, %s, %s, 'province', 'manual', 'province', 'granted', TRUE,
                    TRUE, %s::jsonb, %s, 'privacy-v1', FALSE, NULL, 7)
            """,
            (
                user_id,
                "203.0.113.9",
                "10.25,105.97",
                json.dumps(["food"]),
                recommendation_reset_at,
            ),
        )
    try:
        yield
    finally:
        with pg_db._conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(migration)


def test_recommendation_reset_quarantines_unsafe_preference_and_returns_public_state(
    logged_in_client, pg_db
):
    with _unsafe_preference(pg_db, logged_in_client.owner):
        response = logged_in_client.client.post(
            "/api/me/recommendations/reset",
            headers=logged_in_client.csrf_headers,
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["region_id"] is None
        assert payload["region_label"] is None
        assert payload["location_source"] == "default"
        assert payload["location_consent_state"] == "off"
        assert payload["location_reconfirm_required"] is True
        assert payload["personalization_enabled"] is True
        assert payload["explicit_interests"] == ["food"]
        assert payload["revision"] == 8
        assert payload["recommendation_reset_at"] is not None
        assert "location_provenance_version" not in payload
        assert "203.0.113.9" not in response.text
        assert "10.25,105.97" not in response.text

        with pg_db._conn(commit_on_success=False) as conn:
            row = pg_db._fetchone(
                conn,
                """
                SELECT region_id, region_label, location_source,
                       location_consent_state, location_reconfirm_required,
                       location_provenance_version, explicit_interests, revision
                FROM user_preferences WHERE user_id = %s::uuid
                """,
                (logged_in_client.owner,),
            )
        persisted = pg_db._row_to_dict(row)
        assert persisted["region_id"] is None
        assert persisted["region_label"] is None
        assert persisted["location_source"] == "default"
        assert persisted["location_consent_state"] == "off"
        assert persisted["location_reconfirm_required"] is True
        assert persisted["location_provenance_version"] is None
        assert persisted["revision"] == 8


def test_recommendation_reset_honors_json_safe_revision_ceiling(pg_db, users):
    owner, _ = users
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO user_preferences (user_id, revision) "
            "VALUES (%s::uuid, %s)",
            (owner, 9_007_199_254_740_991),
        )

    with pytest.raises(user_preferences.PreferenceValidationError, match="revision limit"):
        personalization_events.record_recommendation_reset(owner)

    with pg_db._conn(commit_on_success=False) as conn:
        row = pg_db._fetchone(
            conn,
            "SELECT recommendation_reset_at, revision "
            "FROM user_preferences WHERE user_id = %s::uuid",
            (owner,),
        )
    persisted = pg_db._row_to_dict(row)
    assert persisted["recommendation_reset_at"] is None
    assert persisted["revision"] == 9_007_199_254_740_991


def test_event_route_persists_safe_owner_event_without_legacy_jsonl(
    logged_in_client, users, canonical_event_entities, tmp_path, monkeypatch
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
        "location_reconfirm_required": False,
        "location_provenance_version": None,
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
                 recommendation_reset_at, location_reconfirm_required,
                 location_provenance_version, revision)
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                    %s, %s, %s, %s)
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
                location_reconfirm_required = EXCLUDED.location_reconfirm_required,
                location_provenance_version = EXCLUDED.location_provenance_version,
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
                defaults["location_reconfirm_required"],
                defaults["location_provenance_version"],
                defaults["revision"],
            ),
        )


def _seed_entity(
    pg_db,
    entity_id: str,
    *,
    name: str,
    entity_type: str,
    area: str,
    place_id: str | None = None,
    status: str | None = "published",
    verified: bool | int | None = 1,
):
    stored_verified = int(verified) if isinstance(verified, bool) else verified
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO entities "
            "(id, type, name, summary, area, \"placeId\", status, verified) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                entity_id,
                entity_type,
                name,
                name,
                area,
                place_id,
                status,
                stored_verified,
            ),
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
    _seed_entity(
        pg_db,
        "old-event-culture",
        name="Di tich van hoa",
        entity_type="attraction",
        area="",
    )
    _seed_entity(
        pg_db,
        "new-event-food",
        name="Bun nuoc leo",
        entity_type="dish",
        area="",
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
            "entity_id": "old-event-culture",
            "interest_keys": ["culture"],
            "occurred_at": cutoff - timedelta(minutes=1),
        },
    )
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": "new-event-food",
            "interest_keys": ["food"],
            "occurred_at": cutoff + timedelta(minutes=1),
        },
    )

    profile = public_api._build_user_interest_profile(owner)

    assert [item["key"] for item in profile["interests"]] == ["food"]
    assert profile["areas"] == []
    assert profile["types"] == [{"key": "dish", "score": 2.2}]
    assert profile["signal_count"] == 2


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
    _seed_entity(
        pg_db,
        "ignored-food-event",
        name="Bun nuoc leo",
        entity_type="dish",
        area="ignored-area",
    )
    _set_preferences(
        pg_db,
        owner,
        region_id="province-vl",
        region_label="Vĩnh Long",
        region_scope="province",
        location_source="manual",
        location_accuracy="province",
        location_enabled=False,
        personalization_enabled=False,
        explicit_interests=["culture"],
    )
    write_personalization_event(
        owner,
        {
            "event_type": "entity_view",
            "context": "entity",
            "entity_id": "ignored-food-event",
            "interest_keys": ["food"],
        },
    )

    manual = public_api._build_user_interest_profile(
        owner, query="food", context_entity={"type": "dish", "area": "query-area"}
    )
    _set_preferences(
        pg_db,
        owner,
        region_id=None,
        region_label=None,
        region_scope="unknown",
        location_source="default",
        location_accuracy="unknown",
        location_consent_state="off",
        location_enabled=False,
        location_provenance_version=None,
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
    with _unsafe_preference(
        pg_db, auth_client.owner, recommendation_reset_at=cutoff
    ):
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
    exported_preferences = exported["preferences"]
    assert exported_preferences["explicit_interests"] == ["food"]
    assert exported_preferences["region_id"] is None
    assert exported_preferences["location_source"] == "default"
    assert exported_preferences["location_consent_state"] == "off"
    assert exported_preferences["location_reconfirm_required"] is True
    assert exported_preferences["personalization_enabled"] is True
    assert exported_preferences["revision"] == 8
    assert exported_preferences["recommendation_reset_at"] == cutoff.isoformat()
    assert "location_provenance_version" not in exported_preferences
    serialized_preferences = json.dumps(exported_preferences, ensure_ascii=False)
    assert "203.0.113.9" not in serialized_preferences
    assert "10.25,105.97" not in serialized_preferences
    assert "confirmation_token" not in serialized_preferences
    assert [(row["consent_type"], row["state"]) for row in exported["consents"]] == [
        ("personalization", "granted")
    ]
    assert exported["events"][0]["interest_keys"] == []
    assert len(exported["legacy_events"]) == 1
    serialized = json.dumps(exported, ensure_ascii=True)
    assert "private-new-query" not in serialized
    assert "private-query" not in serialized
    assert "203.0.113.9" not in serialized
    assert "10.25,105.97" not in serialized
    assert "confirmation_token" not in serialized
    assert "metadata" not in serialized


def test_scheduling_delete_only_inactivates_and_keeps_personalization(
    auth_client, pg_db, tmp_path, monkeypatch
):
    _set_preferences(pg_db, auth_client.owner, personalization_enabled=True)
    write_personalization_event(
        auth_client.owner,
        {"event_type": "search", "context": "search"},
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
            user_id, {"event_type": "search", "context": "search"}
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
            "event_type": "search",
            "context": "search",
            "expires_at": now - timedelta(seconds=1),
        },
    )
    write_personalization_event(
        other,
        {
            "event_type": "search",
            "context": "search",
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


def test_scheduler_logs_only_aggregate_location_quarantine(monkeypatch, caplog, pg_db):
    monkeypatch.setattr(
        user_preferences,
        "quarantine_invalid_preferences_batch",
        lambda limit=100: {"raw_shape": 2, "provenance": 1},
    )
    with caplog.at_level("INFO", logger="scheduler"):
        scheduler.task_personalization_cleanup()
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "3" in output
    assert "203.0.113" not in output
    assert "province-vl" not in output


def test_scheduler_worker_failure_preserves_legacy_cleanup_and_retry_signal(
    pg_db, users, tmp_path, monkeypatch, caplog
):
    owner, _ = users
    deadline = datetime(2026, 8, 1, tzinfo=timezone.utc)
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )
    monkeypatch.setattr(
        personalization_events, "legacy_cutover_deadline", lambda: deadline
    )

    class AtCutoverDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return deadline

    monkeypatch.setattr(scheduler, "datetime", AtCutoverDateTime)
    sensitive_error = (
        f"user={owner} region=203.0.113.9 token=location-confirmation-secret"
    )

    def fail_location_quarantine(limit=100):
        raise RuntimeError(sensitive_error)

    monkeypatch.setattr(
        user_preferences,
        "quarantine_invalid_preferences_batch",
        fail_location_quarantine,
    )
    scheduled = scheduler.ScheduledTask(
        "personalization-cleanup-failure-test",
        scheduler.task_personalization_cleanup,
        interval_seconds=3600,
    )

    with caplog.at_level("INFO", logger="scheduler"):
        scheduled.run()

    output = "\n".join(record.getMessage() for record in caplog.records)
    assert read_all_legacy_events(path) == []
    assert scheduled.run_count == 0
    assert scheduled.last_error == "Location preference self-healing failed"
    assert scheduled._consecutive_failures == 1
    assert scheduled.next_run_after > time.time()
    assert "Location preference self-healing failed" in output
    assert owner not in output
    assert "203.0.113.9" not in output
    assert "location-confirmation-secret" not in output


def test_scheduler_purges_recognized_legacy_rows_only_after_cutover(
    pg_db, users, tmp_path, monkeypatch
):
    owner, other = users
    path = tmp_path / "legacy-events.jsonl"
    lock_path = tmp_path / ".legacy-events.publication.lock"
    seed_legacy_events(path, [owner, other])
    workspace_row = {
        "record_type": "workspace_state",
        "workspace_id": "keep-this-workspace",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(workspace_row) + "\n")
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_LOCK_PATH", lock_path)
    personalization_events.settings.LEGACY_EVENT_READ_UNTIL = (
        "2026-08-01T00:00:00Z"
    )

    class BeforeCutoverDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 7, 31, tzinfo=timezone.utc)

    class AfterCutoverDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 8, 2, tzinfo=timezone.utc)

    monkeypatch.setattr(scheduler, "datetime", BeforeCutoverDateTime)
    scheduler.task_personalization_cleanup()
    assert len(read_all_legacy_events(path)) == 3

    monkeypatch.setattr(scheduler, "datetime", AfterCutoverDateTime)
    scheduler.task_personalization_cleanup()

    assert read_all_legacy_events(path) == [workspace_row]


def test_scheduler_purges_legacy_rows_at_exact_cutover_deadline(
    pg_db, users, tmp_path, monkeypatch
):
    owner, _ = users
    deadline = datetime(2026, 8, 1, tzinfo=timezone.utc)
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [owner])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )
    monkeypatch.setattr(
        personalization_events, "legacy_cutover_deadline", lambda: deadline
    )

    class AtCutoverDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return deadline

    monkeypatch.setattr(scheduler, "datetime", AtCutoverDateTime)

    scheduler.task_personalization_cleanup()

    assert read_all_legacy_events(path) == []


def test_final_account_purge_waits_for_configured_grace_period(
    pg_db, users, tmp_path, monkeypatch
):
    stale, active = users
    monkeypatch.setattr(scheduler, "ACCOUNT_DELETE_GRACE_DAYS", 45, raising=False)
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
            user_id, {"event_type": "search", "context": "search"}
        )
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [stale, active])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )

    scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        counts = pg_db._fetchone(
            conn,
            "SELECT "
            "(SELECT COUNT(*) FROM users) AS users, "
            "(SELECT COUNT(*) FROM user_preferences) AS preferences, "
            "(SELECT COUNT(*) FROM user_preference_consents) AS consents, "
            "(SELECT COUNT(*) FROM user_personalization_events) AS events",
        )
    assert pg_db._row_to_dict(counts) == {
        "users": 2,
        "preferences": 2,
        "consents": 2,
        "events": 2,
    }
    assert [row["user_id"] for row in read_all_legacy_events(path)] == [
        stale,
        active,
    ]


def test_cleanup_skips_account_locked_by_concurrent_reactivation(
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
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [stale, active])
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )
    purge_started = threading.Event()
    real_purge = personalization_events.purge_legacy_events

    def observed_purge(**kwargs):
        result = real_purge(**kwargs)
        purge_started.set()
        return result

    monkeypatch.setattr(personalization_events, "purge_legacy_events", observed_purge)
    reactivation_conn = psycopg2.connect(TEST_DATABASE_URL)
    cleanup_thread = threading.Thread(target=scheduler.task_session_cleanup)
    try:
        with reactivation_conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET deleted_at = NULL, is_active = TRUE "
                "WHERE id = %s::uuid",
                (stale,),
            )
        cleanup_thread.start()
        cleanup_thread.join(timeout=1)
        if cleanup_thread.is_alive():
            assert purge_started.wait(5)
        reactivation_conn.commit()
        cleanup_thread.join(timeout=10)
    finally:
        reactivation_conn.rollback()
        reactivation_conn.close()

    assert not cleanup_thread.is_alive()
    with pg_db._conn(commit_on_success=False) as conn:
        survivor = pg_db._fetchone(
            conn,
            "SELECT is_active, deleted_at FROM users WHERE id = %s::uuid",
            (stale,),
        )
    assert pg_db._row_to_dict(survivor) == {
        "is_active": True,
        "deleted_at": None,
    }
    assert [row["user_id"] for row in read_all_legacy_events(path)] == [
        stale,
        active,
    ]


def test_legacy_purge_queue_preserves_committed_deletes_and_retries_failure(
    pg_db, users, tmp_path, monkeypatch
):
    stale_one, stale_two = users
    active = str(uuid4())
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO users (id, phone) VALUES (%s::uuid, %s)",
            (active, f"test-{active}"),
        )
        pg_db._execute(
            conn,
            "UPDATE users SET deleted_at = NOW() - INTERVAL '31 days', "
            "is_active = FALSE WHERE id IN (%s::uuid, %s::uuid)",
            (stale_one, stale_two),
        )
    for user_id in (stale_one, stale_two, active):
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
            user_id, {"event_type": "search", "context": "search"}
        )
    path = tmp_path / "legacy-events.jsonl"
    seed_legacy_events(path, [stale_one, stale_two, active])
    workspace_row = {"workspace": "keep", "payload": {"owner": active}}
    path.write_text(
        path.read_text(encoding="utf-8")
        + json.dumps(workspace_row, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(personalization_events, "LEGACY_EVENTS_PATH", path)
    monkeypatch.setattr(
        personalization_events,
        "LEGACY_EVENTS_LOCK_PATH",
        tmp_path / ".legacy-events.publication.lock",
    )
    real_purge = personalization_events.purge_legacy_events
    purge_calls = []

    def fail_second_purge(**kwargs):
        purge_calls.append(kwargs["user_id"])
        if len(purge_calls) == 2:
            raise OSError("legacy purge failed")
        return real_purge(**kwargs)

    with monkeypatch.context() as failure_patch:
        failure_patch.setattr(
            personalization_events, "purge_legacy_events", fail_second_purge
        )
        scheduler.task_session_cleanup()

    assert len(purge_calls) == 2
    succeeded_user, failed_user = purge_calls
    with pg_db._conn(commit_on_success=False) as conn:
        failed_counts = pg_db._fetchone(
            conn,
            "SELECT "
            "(SELECT COUNT(*) FROM users) AS users, "
            "(SELECT COUNT(*) FROM user_preferences) AS preferences, "
            "(SELECT COUNT(*) FROM user_preference_consents) AS consents, "
            "(SELECT COUNT(*) FROM user_personalization_events) AS events",
        )
        jobs = pg_db._fetchall(
            conn,
            "SELECT user_id, attempt_count, last_error "
            "FROM personalization_legacy_purge_queue ORDER BY user_id",
        )
    assert pg_db._row_to_dict(failed_counts) == {
        "users": 1,
        "preferences": 1,
        "consents": 1,
        "events": 1,
    }
    assert [str(row["user_id"]) for row in jobs] == [failed_user]
    assert int(jobs[0]["attempt_count"]) == 1
    assert "legacy purge failed" in jobs[0]["last_error"]
    remaining_rows = read_all_legacy_events(path)
    assert succeeded_user not in {row.get("user_id") for row in remaining_rows}
    assert failed_user in {row.get("user_id") for row in remaining_rows}
    assert active in {row.get("user_id") for row in remaining_rows}
    assert workspace_row in remaining_rows

    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "UPDATE personalization_legacy_purge_queue SET next_attempt_at = NOW()",
        )
    scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        queue_count = pg_db._fetchone(
            conn,
            "SELECT COUNT(*) AS count FROM personalization_legacy_purge_queue",
        )
    assert int(queue_count["count"]) == 0
    assert read_all_legacy_events(path) == [
        next(row for row in remaining_rows if row.get("user_id") == active),
        workspace_row,
    ]


def test_scheduler_drains_existing_backlog_plus_max_enqueue_but_keeps_future_jobs(
    pg_db, users, monkeypatch
):
    del users
    now = datetime.now(timezone.utc)
    due_ids = [str(uuid4()) for _ in range(600)]
    future_id = str(uuid4())
    with pg_db._conn() as conn:
        cursor = conn.cursor()
        psycopg2.extras.execute_values(
            cursor,
            "INSERT INTO personalization_legacy_purge_queue "
            "(user_id, next_attempt_at) VALUES %s",
            [(user_id, now - timedelta(minutes=1)) for user_id in due_ids]
            + [(future_id, now + timedelta(days=1))],
        )
    purge_calls = []
    monkeypatch.setattr(
        personalization_events,
        "purge_legacy_events",
        lambda *, user_id: purge_calls.append(user_id),
    )

    scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        remaining = pg_db._fetchall(
            conn,
            "SELECT user_id, attempt_count, next_attempt_at "
            "FROM personalization_legacy_purge_queue ORDER BY user_id",
        )
    assert set(purge_calls) == set(due_ids)
    assert future_id not in purge_calls
    assert [str(row["user_id"]) for row in remaining] == [future_id]
    assert int(remaining[0]["attempt_count"]) == 0
    assert remaining[0]["next_attempt_at"] > now


def test_due_purge_jobs_run_when_hard_delete_transaction_fails(
    pg_db, users, monkeypatch, caplog
):
    due_id = str(uuid4())
    future_id = str(uuid4())
    now = datetime.now(timezone.utc)
    with pg_db._conn() as conn:
        pg_db._execute(
            conn,
            "INSERT INTO personalization_legacy_purge_queue "
            "(user_id, next_attempt_at) VALUES "
            "(%s::uuid, %s), (%s::uuid, %s)",
            (
                due_id,
                now - timedelta(minutes=1),
                future_id,
                now + timedelta(days=1),
            ),
        )
    real_fetchall = pg_db._fetchall

    def fail_candidate_query(conn, sql, params=None):
        if "SELECT id FROM users" in sql:
            raise RuntimeError("injected candidate query failure")
        return real_fetchall(conn, sql, params)

    purge_calls = []
    monkeypatch.setattr(pg_db, "_fetchall", fail_candidate_query)
    monkeypatch.setattr(
        personalization_events,
        "purge_legacy_events",
        lambda *, user_id: purge_calls.append(user_id),
    )

    with caplog.at_level("ERROR", logger="scheduler"):
        scheduler.task_session_cleanup()

    with pg_db._conn(commit_on_success=False) as conn:
        remaining = pg_db._fetchall(
            conn,
            "SELECT user_id FROM personalization_legacy_purge_queue ORDER BY user_id",
        )
        user_count = pg_db._fetchone(conn, "SELECT COUNT(*) AS count FROM users")
    assert purge_calls == [due_id]
    assert [str(row["user_id"]) for row in remaining] == [future_id]
    assert int(user_count["count"]) == 2
    assert "injected candidate query failure" in caplog.text


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
            user_id, {"event_type": "search", "context": "search"}
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
