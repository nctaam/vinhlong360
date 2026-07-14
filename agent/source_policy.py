from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit


_SELF_HOSTS = frozenset({"vinhlong360.vn", "www.vinhlong360.vn"})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


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


def _is_external_host(host: str) -> bool:
    if (
        host in _SELF_HOSTS
        or host == "localhost"
        or host.endswith(".localhost")
        or host.endswith(".local")
    ):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError:
            return False
        labels = ascii_host.split(".")
        return len(labels) > 1 and all(_HOST_LABEL.fullmatch(label) for label in labels)


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
