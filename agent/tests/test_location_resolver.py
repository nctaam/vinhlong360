import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth_middleware
import location_resolver
import public_api
import user_preferences
from auth_middleware import generate_csrf_token
from database import Database
from location_resolver import (
    LocationInputError,
    configured_reverse_geocoder,
    resolve_gps,
    resolve_ip,
)
from pinned_http import EgressPolicy, PinnedResponse
from user_preferences import load_preferences


@pytest.fixture
def preference_database(tmp_path, monkeypatch):
    database = Database(str(tmp_path / "location-preferences.db"))
    database._use_pg = False
    database._dsn = None
    with database._conn() as conn:
        conn.executescript(
            """
            CREATE TABLE user_preferences (
                user_id TEXT PRIMARY KEY,
                region_id TEXT,
                region_label TEXT,
                region_scope TEXT NOT NULL DEFAULT 'unknown',
                location_source TEXT NOT NULL DEFAULT 'default',
                location_accuracy TEXT NOT NULL DEFAULT 'unknown',
                location_consent_state TEXT NOT NULL DEFAULT 'unknown',
                location_enabled INTEGER NOT NULL DEFAULT 0,
                personalization_enabled INTEGER NOT NULL DEFAULT 0,
                explicit_interests TEXT NOT NULL DEFAULT '[]',
                recommendation_reset_at TEXT,
                consent_version TEXT,
                revision INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    monkeypatch.setattr(user_preferences, "db", database)
    return database


@pytest.fixture
def logged_in_user(monkeypatch):
    session_token = "location-route-session"
    user = {"id": "user-1", "display_name": "Location owner"}

    async def current_user(request):
        bearer = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return user if bearer == session_token else None

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    headers = {"Authorization": f"Bearer {session_token}"}
    return SimpleNamespace(
        user_id=user["id"],
        headers=headers,
        csrf_headers={
            **headers,
            "X-CSRF-Token": generate_csrf_token(session_token),
        },
    )


@pytest.fixture
def client(preference_database, logged_in_user):
    app = FastAPI()
    app.include_router(public_api.router)
    with TestClient(app) as test_client:
        yield test_client


def test_gps_resolution_returns_normalized_region_without_coordinates():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {"region_id": "ward-1"},
    )

    assert result.region_id == "ward-1"
    assert not hasattr(result, "latitude")
    assert not hasattr(result, "longitude")


def test_gps_out_of_bounds_is_rejected():
    with pytest.raises(LocationInputError):
        resolve_gps(91.0, 105.97, reverse_geocoder=lambda *_: {})


def test_ip_resolver_does_not_return_raw_ip():
    result = resolve_ip(
        "203.0.113.8",
        ip_geocoder=lambda value: {"region_id": "province-vl"},
    )

    assert result.region_id == "province-vl"
    assert "203.0.113.8" not in repr(result)


def test_ambiguous_resolution_requires_confirmation_without_persisting(
    client, logged_in_user
):
    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["location_accuracy"] == "unknown"
    assert load_preferences(logged_in_user.user_id)["region_id"] is None


def test_location_resolution_requires_auth_before_csrf_or_provider(client):
    provider_calls = []
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: provider_calls.append(True) or {"region_id": "ward-1"}
    )

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
    )

    assert response.status_code == 401
    assert provider_calls == []


def test_location_resolution_requires_csrf_before_provider(client, logged_in_user):
    provider_calls = []
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: provider_calls.append(True) or {"region_id": "ward-1"}
    )

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.headers,
    )

    assert response.status_code == 403
    assert provider_calls == []


def test_location_resolution_is_rate_limited_before_provider_egress(
    client, logged_in_user, monkeypatch
):
    provider_calls = []
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: provider_calls.append(True) or {"region_id": "ward-1"}
    )
    monkeypatch.setattr(public_api, "LOCATION_RESOLVE_RATE_LIMIT", 1)

    first = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )
    blocked = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert provider_calls == [True]


def test_location_resolution_rejects_user_id_and_never_persists(
    client, logged_in_user
):
    response = client.post(
        "/api/me/location/resolve",
        json={
            "mode": "gps",
            "latitude": 10.25,
            "longitude": 105.97,
            "user_id": "user-2",
        },
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid location input"}
    assert load_preferences(logged_in_user.user_id)["revision"] == 0
    assert load_preferences("user-2")["revision"] == 0


def test_location_resolution_rejects_boolean_coordinates_without_echoing_them(
    client, logged_in_user
):
    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": True, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid location input"}


def test_provider_failure_returns_unknown_without_input_or_error_disclosure(
    client, logged_in_user, caplog
):
    def unavailable(latitude, longitude):
        raise RuntimeError(f"provider failed for {latitude},{longitude}")

    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: unavailable

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "region_id": None,
        "region_label": None,
        "region_scope": "unknown",
        "location_source": "gps",
        "location_accuracy": "unknown",
    }
    assert "10.25" not in response.text
    assert "105.97" not in response.text
    assert "10.25" not in caplog.text
    assert "105.97" not in caplog.text
    assert load_preferences(logged_in_user.user_id)["revision"] == 0


def test_malformed_provider_payload_normalizes_to_unknown():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_scope": ["ward"],
        },
    )

    assert result.region_id is None
    assert result.location_accuracy == "unknown"


def test_provider_cannot_echo_raw_gps_into_result():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": "near 10.25 and 105.97",
            "latitude": 10.25,
            "longitude": 105.97,
        },
    )

    assert "10.25" not in repr(result)
    assert "105.97" not in repr(result)


def test_ip_route_never_returns_or_persists_raw_client_ip(
    client, logged_in_user, monkeypatch
):
    raw_ip = "203.0.113.8"
    monkeypatch.setattr(public_api, "get_client_ip", lambda _request: raw_ip)
    client.app.dependency_overrides[public_api.get_ip_geocoder] = lambda: (
        lambda value: {
            "region_id": "province-vl",
            "region_label": f"lookup for {value}",
            "ip": value,
        }
    )

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "ip"},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert raw_ip not in response.text
    assert load_preferences(logged_in_user.user_id)["revision"] == 0


def test_configured_reverse_geocoder_uses_pinned_http_boundary(
    monkeypatch,
):
    calls = []

    class FakePinnedClient:
        def get(self, url, *, user_agent, policy):
            calls.append((url, user_agent, policy))
            return PinnedResponse(
                status_code=200,
                url=url,
                headers=(),
                content=b'{"region_id":"ward-1","location_accuracy":"ward"}',
                redirects=(),
            )

    monkeypatch.setenv("LOCATION_REVERSE_GEOCODER_URL", "https://geo.example/resolve")
    monkeypatch.setattr(location_resolver, "_PINNED_HTTP", FakePinnedClient())

    result = configured_reverse_geocoder(10.25, 105.97)

    assert result == {"region_id": "ward-1", "location_accuracy": "ward"}
    assert len(calls) == 1
    assert calls[0][0].startswith("https://geo.example/resolve?")
    assert isinstance(calls[0][2], EgressPolicy)
