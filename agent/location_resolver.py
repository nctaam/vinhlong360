"""Transient, privacy-safe location resolution boundary."""

from __future__ import annotations

import ipaddress
import json
import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pinned_http import EgressPolicy, PinnedHTTPClient


MAX_REGION_ID_LENGTH = 128
MAX_REGION_LABEL_LENGTH = 160
REGION_SCOPES = frozenset({"ward", "district", "province", "all", "unknown"})
LOCATION_ACCURACIES = frozenset({"ward", "district", "province", "unknown"})
_REGION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_NUMBER_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_NUMBER_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_NUMBER_PATTERN}(?![A-Za-z0-9_.])"
)
_COORDINATE_PAIR_RE = re.compile(
    rf"(?<![A-Za-z0-9_.])(?P<first>{_NUMBER_PATTERN})(?![A-Za-z0-9_.])"
    rf"\s*(?:,|;|/|\band\b|\bva\b|\bvà\b)\s*"
    rf"(?<![A-Za-z0-9_.])(?P<second>{_NUMBER_PATTERN})(?![A-Za-z0-9_.])",
    re.IGNORECASE,
)
_DMS_RE = re.compile(
    r"(?P<degrees>[+-]?\d{1,3})\s*[°º]\s*"
    r"(?P<minutes>\d{1,2}(?:\.\d+)?)\s*['′]\s*"
    r"(?:(?P<seconds>\d{1,2}(?:\.\d+)?)\s*[\"″]\s*)?"
    r"(?P<hemisphere>[NSEW])?",
    re.IGNORECASE,
)
_HEMISPHERE_COORDINATE_RE = re.compile(
    rf"(?<![A-Za-z0-9_.]){_NUMBER_PATTERN}\s*[NSEW](?![A-Za-z])",
    re.IGNORECASE,
)
_IPV4_LIKE_RE = re.compile(r"(?<![0-9.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9.])")
_IP_CANDIDATE_RE = re.compile(r"[0-9A-Fa-f:.]+")
LOCATION_CONFIRMATION_TTL_SECONDS = 300
_LOCATION_CONFIRMATION_PURPOSE = "location-confirmation-v2"


class LocationInputError(ValueError):
    """Raised when caller-supplied location input is invalid."""


class LocationProviderError(RuntimeError):
    """Raised when a configured provider cannot return a safe response."""


class LocationConfirmationError(ValueError):
    """Raised when a resolver confirmation lacks valid server provenance."""


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


@dataclass(frozen=True)
class VerifiedLocationConfirmation:
    resolution: LocationResolution
    preference_revision: int


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


def _normalized_region_id(value: Any) -> str | None:
    region_id = _bounded_text(value, MAX_REGION_ID_LENGTH)
    if region_id is not None and not _REGION_ID_RE.fullmatch(region_id):
        raise LocationProviderError("Location provider unavailable")
    return region_id


def _normalized_region_label(value: Any) -> str | None:
    return _bounded_text(value, MAX_REGION_LABEL_LENGTH)


def is_normalized_region_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and 0 < len(value) <= MAX_REGION_ID_LENGTH
        and _REGION_ID_RE.fullmatch(value) is not None
    )


def is_normalized_region_label(value: Any) -> bool:
    return value is None or (
        isinstance(value, str)
        and value == value.strip()
        and 0 < len(value) <= MAX_REGION_LABEL_LENGTH
    )


def contains_raw_location_value(value: Any) -> bool:
    """Reject IP/coordinate-shaped text at resolution and persistence boundaries."""
    if not isinstance(value, str):
        return False
    if _IPV4_LIKE_RE.search(value):
        return True
    for match in _IP_CANDIDATE_RE.finditer(value):
        candidate = match.group().strip(".,;()[]{}")
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        return True
    if _DMS_RE.search(value) or _HEMISPHERE_COORDINATE_RE.search(value):
        return True
    pair = _COORDINATE_PAIR_RE.search(value)
    if pair:
        try:
            first = float(pair.group("first"))
            second = float(pair.group("second"))
        except ValueError:
            return True
        if (
            -90 <= first <= 90 and -180 <= second <= 180
        ) or (
            -90 <= second <= 90 and -180 <= first <= 180
        ):
            return True
    for match in _NUMBER_RE.finditer(value):
        token = match.group()
        if not any(marker in token for marker in (".", "e", "E", "+", "-")):
            continue
        try:
            candidate = float(token)
        except ValueError:
            continue
        if math.isfinite(candidate) and -180 <= candidate <= 180:
            return True
    return False


def _normalize_provider_result(value: Any, source: str) -> LocationResolution:
    if not isinstance(value, Mapping):
        return _unknown(source)
    try:
        if value.get("ambiguous") is True:
            return _unknown(source)
        region_id = _normalized_region_id(value.get("region_id"))
        region_label = _normalized_region_label(value.get("region_label"))
        region_scope = value.get("region_scope", "unknown")
        accuracy = value.get("location_accuracy", value.get("accuracy", "unknown"))
        if region_scope not in REGION_SCOPES or accuracy not in LOCATION_ACCURACIES:
            return _unknown(source)
    except Exception:
        return _unknown(source)
    if region_id is None:
        return _unknown(source)
    if contains_raw_location_value(region_id) or contains_raw_location_value(region_label):
        return _unknown(source)
    return LocationResolution(
        region_id=region_id,
        region_label=region_label,
        region_scope=region_scope,
        location_source=source,
        location_accuracy=accuracy,
    )


def _returned_text(resolution: LocationResolution) -> tuple[str, str]:
    return resolution.region_id or "", resolution.region_label or ""


def _matches_coordinate(candidate: float, coordinates: tuple[float, float]) -> bool:
    return any(math.isclose(candidate, value, abs_tol=1e-9) for value in coordinates)


def _matches_coordinate_pair(
    first: float,
    second: float,
    coordinates: tuple[float, float],
) -> bool:
    latitude, longitude = coordinates
    return (
        math.isclose(first, latitude, abs_tol=1e-9)
        and math.isclose(second, longitude, abs_tol=1e-9)
    ) or (
        math.isclose(first, longitude, abs_tol=1e-9)
        and math.isclose(second, latitude, abs_tol=1e-9)
    )


def _coordinate_value(value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LocationInputError("Invalid location input")
    if value < minimum or value > maximum:
        raise LocationInputError("Invalid location input")
    if isinstance(value, float) and not math.isfinite(value):
        raise LocationInputError("Invalid location input")
    return float(value)


def _contains_gps_echo(
    resolution: LocationResolution,
    latitude: float,
    longitude: float,
) -> bool:
    coordinates = (latitude, longitude)
    for text in _returned_text(resolution):
        for match in _COORDINATE_PAIR_RE.finditer(text):
            first = float(match.group("first"))
            second = float(match.group("second"))
            if _matches_coordinate_pair(first, second, coordinates):
                return True
        for match in _DMS_RE.finditer(text):
            degrees = float(match.group("degrees"))
            minutes = float(match.group("minutes"))
            seconds = float(match.group("seconds") or 0)
            if minutes >= 60 or seconds >= 60:
                continue
            candidate = abs(degrees) + minutes / 60 + seconds / 3600
            hemisphere = (match.group("hemisphere") or "").upper()
            if degrees < 0 or hemisphere in {"S", "W"}:
                candidate = -candidate
            if _matches_coordinate(candidate, coordinates):
                return True
        for match in _NUMBER_RE.finditer(text):
            token = match.group()
            if not any(marker in token for marker in (".", "e", "E", "+", "-")):
                continue
            try:
                candidate = float(token)
            except ValueError:
                continue
            if math.isfinite(candidate) and _matches_coordinate(candidate, coordinates):
                return True
    return False


def _contains_ip_echo(resolution: LocationResolution, client_ip: str) -> bool:
    target = ipaddress.ip_address(client_ip)
    if isinstance(target, ipaddress.IPv6Address) and target.ipv4_mapped is not None:
        target = target.ipv4_mapped
    for text in _returned_text(resolution):
        for match in _IP_CANDIDATE_RE.finditer(text):
            candidate = match.group().strip(".,;()[]{}")
            try:
                parsed = ipaddress.ip_address(candidate)
                if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
                    parsed = parsed.ipv4_mapped
                if candidate and parsed == target:
                    return True
            except ValueError:
                continue
    return False


def _redact_gps_echo(
    resolution: LocationResolution,
    latitude: float,
    longitude: float,
) -> LocationResolution:
    if _contains_gps_echo(resolution, latitude, longitude):
        return _unknown("gps")
    return resolution


def _redact_ip_echo(
    resolution: LocationResolution,
    client_ip: str,
) -> LocationResolution:
    if _contains_ip_echo(resolution, client_ip):
        return _unknown("ip")
    return resolution


def resolve_gps(
    latitude: float,
    longitude: float,
    reverse_geocoder: ReverseGeocoder,
) -> LocationResolution:
    normalized_latitude = _coordinate_value(latitude, -90, 90)
    normalized_longitude = _coordinate_value(longitude, -180, 180)
    try:
        provider_result = reverse_geocoder(normalized_latitude, normalized_longitude)
    except Exception:
        return _unknown("gps")
    resolution = _normalize_provider_result(provider_result, "gps")
    return _redact_gps_echo(resolution, normalized_latitude, normalized_longitude)


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
    return _redact_ip_echo(resolution, normalized_ip)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validated_preference_revision(value: Any) -> int:
    if type(value) is not int or value < 0 or value > 9_007_199_254_740_991:
        raise LocationConfirmationError("Invalid location confirmation")
    return value


def issue_location_confirmation(
    resolution: LocationResolution,
    user_id: str,
    preference_revision: int,
) -> str | None:
    from auth_middleware import generate_user_bound_token

    if not resolution.region_id or resolution.location_source not in {"gps", "ip"}:
        return None
    now = _utc_now()
    payload = {
        "issued_at": int(now.timestamp()),
        "preference_revision": _validated_preference_revision(preference_revision),
        "region_id": resolution.region_id,
        "region_label": resolution.region_label,
        "region_scope": resolution.region_scope,
        "location_source": resolution.location_source,
        "location_accuracy": resolution.location_accuracy,
    }
    return generate_user_bound_token(
        _LOCATION_CONFIRMATION_PURPOSE,
        user_id,
        payload,
        expires_at=int(now.timestamp()) + LOCATION_CONFIRMATION_TTL_SECONDS,
    )


def verify_location_confirmation(
    token: str, user_id: str
) -> VerifiedLocationConfirmation:
    from auth_middleware import verify_user_bound_token

    payload = verify_user_bound_token(
        token,
        _LOCATION_CONFIRMATION_PURPOSE,
        user_id,
        now=int(_utc_now().timestamp()),
    )
    if payload is None:
        raise LocationConfirmationError("Invalid location confirmation")
    if type(payload.get("issued_at")) is not int:
        raise LocationConfirmationError("Invalid location confirmation")
    preference_revision = _validated_preference_revision(
        payload.get("preference_revision")
    )
    resolution = _normalize_provider_result(
        payload, str(payload.get("location_source") or "")
    )
    if not resolution.region_id or resolution.location_source not in {"gps", "ip"}:
        raise LocationConfirmationError("Invalid location confirmation")
    return VerifiedLocationConfirmation(
        resolution=resolution,
        preference_revision=preference_revision,
    )


def _provider_url(endpoint: str, parameters: Mapping[str, str]) -> str:
    try:
        parsed = urlsplit(endpoint)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise LocationProviderError("Location provider unavailable")
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query.extend(parameters.items())
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), "")
        )
    except LocationProviderError:
        raise
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
