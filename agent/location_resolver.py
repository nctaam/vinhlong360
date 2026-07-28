"""Transient, privacy-safe location resolution boundary."""

from __future__ import annotations

import ipaddress
import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pinned_http import EgressPolicy, PinnedHTTPClient


MAX_REGION_ID_LENGTH = 128
MAX_REGION_LABEL_LENGTH = 160
REGION_SCOPES = frozenset({"ward", "district", "province", "all", "unknown"})
LOCATION_ACCURACIES = frozenset({"ward", "district", "province", "unknown"})


class LocationInputError(ValueError):
    """Raised when caller-supplied location input is invalid."""


class LocationProviderError(RuntimeError):
    """Raised when a configured provider cannot return a safe response."""


class ReverseGeocoder(Protocol):
    def __call__(self, latitude: float, longitude: float) -> Mapping[str, Any]:
        raise NotImplementedError


class IpGeocoder(Protocol):
    def __call__(self, client_ip: str) -> Mapping[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class LocationResolution:
    region_id: str | None
    region_label: str | None
    region_scope: str
    location_source: str
    location_accuracy: str


_PINNED_HTTP = PinnedHTTPClient()
_LOCATION_EGRESS_POLICY = EgressPolicy(
    max_encoded_bytes=64 * 1024,
    max_decoded_bytes=64 * 1024,
    accepted_encodings=("gzip", "identity"),
    inactivity_timeout_seconds=5.0,
    total_timeout_seconds=5.0,
    max_redirects=2,
)


def _unknown(source: str) -> LocationResolution:
    return LocationResolution(None, None, "unknown", source, "unknown")


def _bounded_text(value: Any, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise LocationProviderError("Location provider unavailable")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise LocationProviderError("Location provider unavailable")
    return normalized


def _normalize_provider_result(value: Any, source: str) -> LocationResolution:
    if not isinstance(value, Mapping):
        return _unknown(source)
    try:
        if value.get("ambiguous") is True:
            return _unknown(source)
        region_id = _bounded_text(value.get("region_id"), MAX_REGION_ID_LENGTH)
        region_label = _bounded_text(value.get("region_label"), MAX_REGION_LABEL_LENGTH)
        region_scope = value.get("region_scope", "unknown")
        accuracy = value.get("location_accuracy", value.get("accuracy", "unknown"))
        if region_scope not in REGION_SCOPES or accuracy not in LOCATION_ACCURACIES:
            return _unknown(source)
    except Exception:
        return _unknown(source)
    if region_id is None:
        return _unknown(source)
    return LocationResolution(
        region_id=region_id,
        region_label=region_label,
        region_scope=region_scope,
        location_source=source,
        location_accuracy=accuracy,
    )


def _redact_echoed_input(
    resolution: LocationResolution,
    source: str,
    sensitive_values: tuple[str, ...],
) -> LocationResolution:
    returned_text = (resolution.region_id or "", resolution.region_label or "")
    if any(value and value in text for value in sensitive_values for text in returned_text):
        return _unknown(source)
    return resolution


def resolve_gps(
    latitude: float,
    longitude: float,
    reverse_geocoder: ReverseGeocoder,
) -> LocationResolution:
    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise LocationInputError("Invalid location input")
    try:
        provider_result = reverse_geocoder(float(latitude), float(longitude))
    except Exception:
        return _unknown("gps")
    resolution = _normalize_provider_result(provider_result, "gps")
    return _redact_echoed_input(
        resolution,
        "gps",
        (str(float(latitude)), str(float(longitude))),
    )


def resolve_ip(client_ip: str, ip_geocoder: IpGeocoder) -> LocationResolution:
    if not isinstance(client_ip, str) or len(client_ip) > 45:
        raise LocationInputError("Invalid location input")
    try:
        normalized_ip = str(ipaddress.ip_address(client_ip.strip()))
    except ValueError:
        raise LocationInputError("Invalid location input") from None
    try:
        provider_result = ip_geocoder(normalized_ip)
    except Exception:
        return _unknown("ip")
    resolution = _normalize_provider_result(provider_result, "ip")
    return _redact_echoed_input(resolution, "ip", (normalized_ip,))


def _provider_url(endpoint: str, parameters: Mapping[str, str]) -> str:
    try:
        parsed = urlsplit(endpoint)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query.extend(parameters.items())
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), "")
        )
    except (TypeError, ValueError):
        raise LocationProviderError("Location provider unavailable") from None


def _fetch_provider_json(
    endpoint: str,
    parameters: Mapping[str, str],
    *,
    http_client: PinnedHTTPClient | None = None,
) -> Mapping[str, Any]:
    try:
        response = (http_client or _PINNED_HTTP).get(
            _provider_url(endpoint, parameters),
            user_agent="vinhlong360-location-resolver/1.0",
            policy=_LOCATION_EGRESS_POLICY,
        )
        if response.status_code != 200:
            raise LocationProviderError("Location provider unavailable")
        payload = json.loads(response.content)
        if not isinstance(payload, Mapping):
            raise LocationProviderError("Location provider unavailable")
        return payload
    except LocationProviderError:
        raise
    except Exception:
        raise LocationProviderError("Location provider unavailable") from None


def configured_reverse_geocoder(latitude: float, longitude: float) -> Mapping[str, Any]:
    endpoint = os.environ.get("LOCATION_REVERSE_GEOCODER_URL", "").strip()
    if not endpoint:
        return {}
    return _fetch_provider_json(
        endpoint,
        {"latitude": str(latitude), "longitude": str(longitude)},
    )


def configured_ip_geocoder(client_ip: str) -> Mapping[str, Any]:
    endpoint = os.environ.get("LOCATION_IP_GEOCODER_URL", "").strip()
    if not endpoint:
        return {}
    return _fetch_provider_json(endpoint, {"ip": client_ip})


def get_reverse_geocoder() -> ReverseGeocoder:
    return configured_reverse_geocoder


def get_ip_geocoder() -> IpGeocoder:
    return configured_ip_geocoder
