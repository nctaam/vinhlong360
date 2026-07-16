"""Exact HTTP cache contract for policy-bearing FastAPI endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_EXPOSURES = frozenset({"public", "internal"})
_CACHE_CONTRACT = "no-store-no-validator"
_REMOVED_HEADERS = frozenset({b"cache-control", b"etag", b"last-modified", b"expires"})


@dataclass(frozen=True)
class PolicyEndpoint:
    method: str
    path: str
    route_name: str
    exposure: str
    cache_contract: str = _CACHE_CONTRACT

    def __post_init__(self) -> None:
        if type(self.method) is not str or not self.method or self.method != self.method.upper():
            raise ValueError("policy endpoint method must be a non-empty uppercase string")
        if type(self.path) is not str or not self.path.startswith("/"):
            raise ValueError("policy endpoint path must start with '/'")
        if type(self.route_name) is not str or not self.route_name.strip():
            raise ValueError("policy endpoint route_name must be a non-empty string")
        if self.exposure not in _EXPOSURES:
            raise ValueError(f"unsupported policy endpoint exposure: {self.exposure!r}")
        if self.cache_contract != _CACHE_CONTRACT:
            raise ValueError(f"unsupported policy endpoint cache contract: {self.cache_contract!r}")


POLICY_ENDPOINTS = (
    PolicyEndpoint("GET", "/api/entities/{entity_id}", "get_entity", "public"),
    PolicyEndpoint(
        "GET",
        "/_internal/launch-policy-attestation",
        "launch_policy_attestation",
        "internal",
    ),
    PolicyEndpoint(
        "GET",
        "/_internal/launch-sitemaps/{document}",
        "launch_sitemap_document",
        "internal",
    ),
)


def validate_policy_endpoints(endpoints: Iterable[PolicyEndpoint]) -> tuple[PolicyEndpoint, ...]:
    rows = tuple(endpoints)
    identities: set[tuple[str, str, str]] = set()
    method_paths: set[tuple[str, str]] = set()
    route_names: set[str] = set()
    for endpoint in rows:
        if type(endpoint) is not PolicyEndpoint:
            raise TypeError("policy endpoint registry accepts PolicyEndpoint rows only")
        identity = (endpoint.method, endpoint.path, endpoint.route_name)
        method_path = (endpoint.method, endpoint.path)
        if identity in identities or method_path in method_paths or endpoint.route_name in route_names:
            raise ValueError(f"duplicate policy endpoint registry row: {identity!r}")
        identities.add(identity)
        method_paths.add(method_path)
        route_names.add(endpoint.route_name)
    return rows


POLICY_ENDPOINTS = validate_policy_endpoints(POLICY_ENDPOINTS)


class PolicyHttpContractError(RuntimeError):
    """Raised before headers are sent when a registered route attempts HTTP 304."""


class PolicyHttpMiddleware:
    """Apply the registry contract at ASGI response start after route resolution."""

    def __init__(self, app, endpoints: Iterable[PolicyEndpoint] = POLICY_ENDPOINTS) -> None:
        self.app = app
        self._identities = frozenset(
            (row.method, row.path, row.route_name)
            for row in validate_policy_endpoints(endpoints)
        )

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def enforce_at_response_start(message) -> None:
            if message.get("type") == "http.response.start" and self._is_registered(scope):
                status = message.get("status")
                if status == 304:
                    route = scope.get("route")
                    raise PolicyHttpContractError(
                        f"registered policy route {getattr(route, 'name', '<unknown>')!r} attempted HTTP 304"
                    )
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() not in _REMOVED_HEADERS
                ]
                headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, enforce_at_response_start)

    def _is_registered(self, scope) -> bool:
        route = scope.get("route")
        if route is None:
            return False
        identity = (
            str(scope.get("method", "")).upper(),
            getattr(route, "path", None),
            getattr(route, "name", None),
        )
        return identity in self._identities
