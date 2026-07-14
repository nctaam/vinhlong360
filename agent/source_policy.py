from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit


_SELF_DOMAIN = "vinhlong360.vn"
_SPECIAL_USE_DOMAINS = frozenset({"test", "invalid", "example", "home.arpa"})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_NUMERIC_HOST_LABEL = re.compile(r"(?:0x[0-9a-f]+|[0-9]+)")


def _http_host(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").rstrip(".").lower()
        parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not host:
        return None
    return host


def _canonical_domain(host: str) -> str | None:
    try:
        return host.encode("idna").decode("ascii").rstrip(".").lower()
    except UnicodeError:
        return None


def _is_special_use_domain(host: str) -> bool:
    return any(
        host == suffix or host.endswith(f".{suffix}")
        for suffix in _SPECIAL_USE_DOMAINS
    )


def _is_blocked_domain(host: str) -> bool:
    return (
        host == _SELF_DOMAIN
        or host.endswith(f".{_SELF_DOMAIN}")
        or host == "localhost"
        or host.endswith(".localhost")
        or host.endswith(".local")
        or _is_special_use_domain(host)
    )


def _is_external_domain(host: str) -> bool:
    ascii_host = _canonical_domain(host)
    if ascii_host is None or _is_blocked_domain(ascii_host):
        return False
    labels = ascii_host.split(".")
    if all(_NUMERIC_HOST_LABEL.fullmatch(label) for label in labels):
        return False
    return len(labels) > 1 and all(_HOST_LABEL.fullmatch(label) for label in labels)


def _is_public_unicast(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    return (
        address.is_global
        and not address.is_private
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
        and not address.is_loopback
        and not address.is_link_local
        and not getattr(address, "is_site_local", False)
    )


def _is_external_host(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return _is_external_domain(host)
    return _is_public_unicast(address)


def _is_external_http_url(value: object) -> bool:
    host = _http_host(value)
    return host is not None and _is_external_host(host)


def has_external_source_url(source: object) -> bool:
    if isinstance(source, str):
        return _is_external_http_url(source)
    if isinstance(source, Mapping):
        return any(_is_external_http_url(source.get(field)) for field in ("url", "href"))
    if isinstance(source, Sequence) and not isinstance(source, (bytes, bytearray)):
        return any(has_external_source_url(item) for item in source)
    return False
