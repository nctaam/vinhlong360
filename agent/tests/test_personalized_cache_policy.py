import asyncio

import pytest
from fastapi import Request, Response

import auth_middleware
import server


USER_ID = "11111111-1111-1111-1111-111111111111"


def _request(path="/api/search", headers=None):
    raw_headers = [
        (key.lower().encode("ascii"), value.encode("latin-1"))
        for key, value in (headers or [])
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode("ascii"),
            "headers": raw_headers,
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
    )


def _vary_parts(response):
    return {part.strip().lower() for part in response.headers["Vary"].split(",")}


def test_authenticated_engagement_response_overrides_public_cache():
    request = _request(f"/api/users/{USER_ID}/engagement")
    request.state.authenticated_user_id = USER_ID
    response = Response(
        headers={
            "Cache-Control": "public, max-age=60, stale-while-revalidate=120",
            "Vary": "Accept-Encoding",
        }
    )

    server._apply_final_cache_policy(request, response)

    assert response.headers["Cache-Control"] == "private, no-store"
    assert _vary_parts(response) == {
        "accept-encoding",
        "authorization",
        "cookie",
        "accept",
    }


def test_anonymous_engagement_cache_ttl_survives():
    request = _request(f"/api/users/{USER_ID}/engagement")
    response = Response(
        headers={
            "Cache-Control": "public, max-age=60, stale-while-revalidate=120",
            "Vary": "Accept-Encoding",
        }
    )

    server._apply_final_cache_policy(request, response)

    assert response.headers["Cache-Control"] == (
        "public, max-age=60, stale-while-revalidate=120"
    )
    assert _vary_parts(response) == {
        "accept-encoding",
        "authorization",
        "cookie",
        "accept",
    }


def test_existing_private_and_no_store_cache_values_survive():
    for cache_control in ("private, max-age=30", "no-store"):
        request = _request("/api/search")
        response = Response(headers={"Cache-Control": cache_control})

        server._apply_final_cache_policy(request, response)

        assert response.headers["Cache-Control"] == cache_control


def test_vary_members_are_case_insensitive_and_deduplicated():
    request = _request("/admin/users")
    response = Response(
        headers={
            "Vary": "Accept-Encoding, authorization, Cookie, accept, Authorization, ACCEPT"
        }
    )

    server._apply_final_cache_policy(request, response)

    assert _vary_parts(response) == {
        "accept-encoding",
        "authorization",
        "cookie",
        "accept",
    }


def test_auth_response_merges_auth_vary_members():
    request = _request("/auth/login")
    response = Response(headers={"Vary": "Accept-Encoding"})

    server._apply_final_cache_policy(request, response)

    assert _vary_parts(response) == {
        "accept-encoding",
        "authorization",
        "cookie",
        "accept",
    }


@pytest.mark.parametrize(
    "headers",
    [[], [("Authorization", "Bearer invalid")], [("Cookie", "vl360_token=invalid")]],
)
def test_invalid_or_missing_credentials_do_not_mark_request(monkeypatch, headers):
    async def no_user(_request):
        return None

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", no_user)
    request = _request("/api/search", headers)

    assert asyncio.run(auth_middleware.get_current_user(request)) is None
    assert getattr(request.state, "authenticated_user_id", None) is None


def test_valid_get_current_user_marks_request(monkeypatch):
    async def current_user(_request):
        return {"id": USER_ID, "role": "user"}

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    request = _request("/api/search")

    assert asyncio.run(auth_middleware.get_current_user(request)) == {
        "id": USER_ID,
        "role": "user",
    }
    assert request.state.authenticated_user_id == USER_ID


def test_invalid_resolution_clears_stale_auth_marker(monkeypatch):
    async def no_user(_request):
        return None

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", no_user)
    request = _request("/api/search")
    request.state.authenticated_user_id = USER_ID

    assert asyncio.run(auth_middleware.get_current_user(request)) is None
    assert getattr(request.state, "authenticated_user_id", None) is None


def test_valid_require_user_marks_request(monkeypatch):
    async def current_user(_request):
        return {"id": USER_ID, "role": "user"}

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    request = _request("/api/me")

    assert asyncio.run(auth_middleware.require_user(request))["id"] == USER_ID
    assert request.state.authenticated_user_id == USER_ID


def test_valid_require_role_marks_request(monkeypatch):
    async def current_user(_request):
        return {"id": USER_ID, "role": "admin"}

    monkeypatch.setattr(auth_middleware, "_get_current_user_or_none", current_user)
    request = _request("/admin/users")

    dependency = auth_middleware.require_role("admin")
    assert asyncio.run(dependency(request))["id"] == USER_ID
    assert request.state.authenticated_user_id == USER_ID


def test_security_headers_applies_final_policy_after_endpoint():
    request = _request("/api/search")
    response = Response(
        headers={"Cache-Control": "public, max-age=30", "Vary": "Accept-Encoding"}
    )
    request.state.authenticated_user_id = USER_ID

    async def call_next(_request):
        return response

    result = asyncio.run(server.security_headers(request, call_next))

    assert result.headers["Cache-Control"] == "private, no-store"
    assert _vary_parts(result) == {
        "accept-encoding",
        "authorization",
        "cookie",
        "accept",
    }
