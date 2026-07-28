import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth_middleware
import location_resolver
import middleware
import public_api
import user_preferences
from auth_middleware import generate_csrf_token
from database import Database
from location_resolver import (
    LocationInputError,
    LocationProviderError,
    configured_ip_geocoder,
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
    client, logged_in_user, monkeypatch
):
    provider_calls = []
    monkeypatch.delenv("LOCATION_REVERSE_GEOCODER_URL", raising=False)
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda latitude, longitude: provider_calls.append((latitude, longitude))
        or {"ambiguous": True, "region_id": "ward-1"}
    )

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert response.json()["location_accuracy"] == "unknown"
    assert provider_calls == [(10.25, 105.97)]
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


def test_location_csrf_failure_does_not_retain_raw_ip(
    client, logged_in_user, monkeypatch
):
    raw_ip = "198.51.100.24"
    monkeypatch.setattr(middleware, "get_client_ip", lambda _request: raw_ip)

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 10.25, "longitude": 105.97},
        headers=logged_in_user.headers,
    )

    event = middleware.security_logger.recent(event_type="csrf_failure")[-1]
    assert response.status_code == 403
    assert event["endpoint"] == "/api/me/location/resolve"
    assert raw_ip not in repr(event)


def test_malformed_json_is_authenticated_before_validation(client, logged_in_user):
    anonymous = client.post(
        "/api/me/location/resolve",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    missing_csrf = client.post(
        "/api/me/location/resolve",
        content="{",
        headers={**logged_in_user.headers, "Content-Type": "application/json"},
    )

    assert anonymous.status_code == 401
    assert missing_csrf.status_code == 403


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


def test_location_rate_limit_runs_before_malformed_json_validation(
    client, logged_in_user, monkeypatch
):
    monkeypatch.setattr(public_api, "LOCATION_RESOLVE_RATE_LIMIT", 1)
    headers = {**logged_in_user.csrf_headers, "Content-Type": "application/json"}

    first = client.post("/api/me/location/resolve", content="{", headers=headers)
    blocked = client.post("/api/me/location/resolve", content="{", headers=headers)

    assert first.status_code == 422
    assert first.json() == {"detail": "Invalid location input"}
    assert blocked.status_code == 429


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


def test_location_resolution_rejects_huge_integer_without_echoing_it(
    client, logged_in_user
):
    huge_coordinate = 10**400
    with TestClient(client.app, raise_server_exceptions=False) as response_client:
        response = response_client.post(
            "/api/me/location/resolve",
            json={
                "mode": "gps",
                "latitude": huge_coordinate,
                "longitude": 105.97,
            },
            headers=logged_in_user.csrf_headers,
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid location input"}
    assert str(huge_coordinate) not in response.text


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


def test_provider_cannot_echo_alternate_gps_representation():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": "near 1.025e1 and 1.0597e2",
        },
    )

    assert "1.025e1" not in repr(result)
    assert "1.0597e2" not in repr(result)


def test_provider_cannot_echo_dms_gps_representation():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": "10°15′0″N, 105°58′12″E",
        },
    )

    assert "10°15′0″N" not in repr(result)
    assert "105°58′12″E" not in repr(result)


def test_provider_cannot_echo_decimal_minute_gps_representation():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": "10°15'N, 105°58.2'E",
        },
    )

    assert "10°15'N" not in repr(result)
    assert "105°58.2'E" not in repr(result)


def test_numeric_region_label_without_coordinates_is_preserved():
    result = resolve_gps(
        10.25,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": "Phuong 1",
        },
    )

    assert result.region_label == "Phuong 1"


def test_numeric_region_label_matching_coordinate_is_preserved():
    result = resolve_gps(
        1.0,
        105.97,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": "Phuong 1",
        },
    )

    assert result.region_label == "Phuong 1"


def test_provider_cannot_echo_integer_gps_pair_in_result():
    echoed_coordinates = "near 1 and 106"
    result = resolve_gps(
        1.0,
        106.0,
        reverse_geocoder=lambda *_: {
            "region_id": "ward-1",
            "region_label": echoed_coordinates,
        },
    )

    assert echoed_coordinates not in repr(result)


def test_provider_cannot_echo_integer_gps_pair_in_route_response(
    client, logged_in_user
):
    echoed_coordinates = "near 1 and 106"
    client.app.dependency_overrides[public_api.get_reverse_geocoder] = lambda: (
        lambda *_: {
            "region_id": "ward-1",
            "region_label": echoed_coordinates,
        }
    )

    response = client.post(
        "/api/me/location/resolve",
        json={"mode": "gps", "latitude": 1, "longitude": 106},
        headers=logged_in_user.csrf_headers,
    )

    assert response.status_code == 200
    assert echoed_coordinates not in response.text
    assert {"latitude", "longitude"}.isdisjoint(response.json())


def test_provider_cannot_echo_expanded_ipv6_representation():
    expanded_ip = "2001:0db8:0000:0000:0000:0000:0000:0001"
    result = resolve_ip(
        "2001:db8::1",
        ip_geocoder=lambda _value: {
            "region_id": "province-vl",
            "region_label": f"lookup for {expanded_ip}",
        },
    )

    assert expanded_ip not in repr(result)


def test_provider_cannot_echo_ipv4_mapped_ipv6_representation():
    mapped_ip = "::ffff:203.0.113.8"
    result = resolve_ip(
        "203.0.113.8",
        ip_geocoder=lambda _value: {
            "region_id": "province-vl",
            "region_label": f"lookup for {mapped_ip}",
        },
    )

    assert mapped_ip not in repr(result)


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


@pytest.mark.parametrize(
    ("environment_name", "resolver_call", "raw_value"),
    [
        (
            "LOCATION_REVERSE_GEOCODER_URL",
            lambda: configured_reverse_geocoder(10.25, 105.97),
            "10.25",
        ),
        (
            "LOCATION_IP_GEOCODER_URL",
            lambda: configured_ip_geocoder("203.0.113.8"),
            "203.0.113.8",
        ),
    ],
)
def test_configured_location_providers_reject_plaintext_http_before_egress(
    monkeypatch, environment_name, resolver_call, raw_value
):
    calls = []

    class FakePinnedClient:
        def get(self, url, *, user_agent, policy):
            calls.append(url)
            raise AssertionError("plaintext provider must not be called")

    monkeypatch.setenv(environment_name, "http://geo.example/resolve")
    monkeypatch.setattr(location_resolver, "_PINNED_HTTP", FakePinnedClient())

    with pytest.raises(LocationProviderError) as error:
        resolver_call()

    assert str(error.value) == "Location provider unavailable"
    assert raw_value not in repr(error.value)
    assert calls == []
