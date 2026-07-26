"""Shared DNS-pinned, redirect-safe synchronous HTTP GET client — destination policy.

This module lays the foundation for a shared outbound HTTP egress boundary:
immutable dataclass contracts, the exception hierarchy, URL parsing/authority
policy, and the public-address resolver (including IPv6 transition-form
rejection). Nothing in the codebase consumes this module yet; the pinned
socket backend and manual redirect client are added in later tasks.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol

import httpx


class PinnedHTTPError(Exception):
    """Base error for the public pinned egress boundary."""


class DestinationPolicyError(PinnedHTTPError):
    """The requested destination cannot be authorized."""


class InvalidDestinationError(DestinationPolicyError):
    pass


class ResolutionError(DestinationPolicyError):
    pass


class BlockedAddressError(DestinationPolicyError):
    pass


class PeerMismatchError(DestinationPolicyError):
    pass


class RedirectPolicyError(PinnedHTTPError):
    pass


class PinnedTransportError(PinnedHTTPError):
    pass


@dataclass(frozen=True)
class ResolvedAddress:
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address
    port: int
    family: int
    socktype: int
    protocol: int
    sockaddr: tuple


@dataclass(frozen=True)
class ResolvedHop:
    url: httpx.URL
    host: str
    port: int
    addresses: tuple[ResolvedAddress, ...]


@dataclass(frozen=True)
class RedirectHop:
    request_url: str
    status_code: int
    location: str
    next_url: str


@dataclass(frozen=True)
class PinnedResponse:
    status_code: int
    url: str
    headers: tuple[tuple[str, str], ...]
    content: bytes
    redirects: tuple[RedirectHop, ...]


class Resolver(Protocol):
    def __call__(self, host: str, port: int) -> tuple[ResolvedAddress, ...]:
        raise NotImplementedError


class TransportFactory(Protocol):
    def __call__(self, hop: ResolvedHop) -> httpx.BaseTransport:
        raise NotImplementedError


_HTTP_PORTS = {"http": 80, "https": 443}
_NAT64_NETWORKS = (
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
)


def _parse_url(url: str) -> httpx.URL:
    try:
        parsed = httpx.URL(url)
    except (TypeError, ValueError, httpx.InvalidURL) as exc:
        raise InvalidDestinationError("invalid URL") from exc
    if parsed.scheme not in _HTTP_PORTS or not parsed.host or not parsed.is_absolute_url:
        raise InvalidDestinationError("only absolute http/https URLs are allowed")
    if parsed.username or parsed.password or "%" in parsed.host:
        raise InvalidDestinationError("credentials and zone identifiers are forbidden")
    try:
        port = parsed.port
    except ValueError as exc:
        raise InvalidDestinationError("invalid port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise InvalidDestinationError("invalid port")
    return parsed.copy_with(fragment=None)


def _is_isatap(address: ipaddress.IPv6Address) -> bool:
    interface_id = int(address) & ((1 << 64) - 1)
    marker = (interface_id >> 32) & 0xFFFFFFFF
    return marker in {0x00005EFE, 0x02005EFE}


def _is_transition_address(address: ipaddress.IPv6Address) -> bool:
    return (
        address.ipv4_mapped is not None
        or address in ipaddress.ip_network("::/96")
        or any(address in network for network in _NAT64_NETWORKS)
        or address.sixtofour is not None
        or address.teredo is not None
        or _is_isatap(address)
    )


def _require_allowed_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if isinstance(address, ipaddress.IPv6Address) and _is_transition_address(address):
        raise BlockedAddressError(f"IPv6 transition address denied: {address}")
    if address.is_multicast or address.is_unspecified or not address.is_global:
        raise BlockedAddressError(f"non-global address denied: {address}")


def _ascii_host(url: httpx.URL) -> str:
    return url.raw_host.decode("ascii").lower()


def _canonical_url_key(url: httpx.URL) -> tuple[str, str, int, bytes]:
    port = url.port or _HTTP_PORTS[url.scheme]
    return (url.scheme.lower(), _ascii_host(url), port, url.raw_path)


def _resolved_address(
    family: int,
    socktype: int,
    protocol: int,
    sockaddr: tuple,
) -> ResolvedAddress:
    try:
        address = ipaddress.ip_address(sockaddr[0])
        resolved_port = int(sockaddr[1])
    except (IndexError, TypeError, ValueError) as exc:
        raise ResolutionError("resolver returned a malformed address") from exc
    _require_allowed_ip(address)
    return ResolvedAddress(
        ip=address,
        port=resolved_port,
        family=family,
        socktype=socktype,
        protocol=protocol,
        sockaddr=sockaddr,
    )


def resolve_public_addresses(host: str, port: int) -> tuple[ResolvedAddress, ...]:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        _require_allowed_ip(literal)
        family = socket.AF_INET6 if literal.version == 6 else socket.AF_INET
        sockaddr = (str(literal), port, 0, 0) if family == socket.AF_INET6 else (str(literal), port)
        return (_resolved_address(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, sockaddr),)

    try:
        answers = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except OSError as exc:
        raise ResolutionError(f"failed to resolve {host}") from exc

    resolved: list[ResolvedAddress] = []
    seen: set[tuple[int, tuple]] = set()
    for family, socktype, protocol, _canonname, sockaddr in answers:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(_resolved_address(family, socktype, protocol, sockaddr))
    if not resolved:
        raise ResolutionError("resolver returned no usable addresses")
    return tuple(resolved)


def validate_public_url(
    url: str,
    *,
    resolver: Resolver = resolve_public_addresses,
) -> None:
    parsed = _parse_url(url)
    port = parsed.port or _HTTP_PORTS[parsed.scheme]
    if not resolver(_ascii_host(parsed), port):
        raise ResolutionError("resolver returned no usable addresses")
