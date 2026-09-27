"""Canonical provenance URL, license, and sourced-photo evidence validators."""
from __future__ import annotations
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import urlparse
DOCUMENTARY_IMAGE_TYPES = frozenset({"documentary", "journalistic", "official", "press"})
_PLACEHOLDER_SUFFIXES = frozenset({"example", "example.test", "example.com", "example.net", "example.org", "localhost", "local", "localdomain", "invalid", "test", "home.arpa", "corp", "internal", "intranet", "lan"})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_CONCRETE_LICENSE_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (r"\bcc0\s+1\.0\b", r"\bcc\s*by\s+4\.0\b", r"\bcc\s*by[-\s]sa\s+4\.0\b", r"\bcc\s*by[-\s]nc[-\s]nd\s+4\.0\b", r"\bpublic\s+domain\s+mark\s+1\.0\b"))
_AFFIRMATIVE_GRANT_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (r"\b(?:permitted|allowed)\s+(?:to\s+|for\s+)?(?:re-?host(?:ing)?|reuse|republish)\b", r"\bpermission\s+granted\s+(?:to\s+|for\s+)?(?:re-?host(?:ing)?|reuse|republish)\b", r"\b(?:re-?host(?:ing)?|reuse|republish)\s+(?:is\s+)?(?:permitted|allowed)\b", r"\b(?:được\s+phép|cho\s+phép)\s+(?:re-?host|tái\s+(?:sử\s+dụng|lưu\s+trữ|đăng\s+lại|đăng\s+tải))\b"))
_DENIAL_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (r"\ball\s+rights\s+reserved\b", r"\b(?:not|no|never|prohibited|forbidden|denied|unavailable|cannot)\b", r"\bwithout\s+(?:permission|rights?|authorization)\b", r"\bkhông\s+(?:được\s+phép|cho\s+phép)\b"))
def _normalized_statement(value: object) -> str | None:
    if not isinstance(value, str): return None
    value = " ".join(value.strip().split()); return value or None
def has_license_denial(value: object) -> bool:
    value = _normalized_statement(value); return value is not None and any(p.search(value) for p in _DENIAL_PATTERNS)
def is_affirmative_license_scope(value: object) -> bool:
    value = _normalized_statement(value); return bool(value and not has_license_denial(value) and any(p.search(value) for p in _CONCRETE_LICENSE_PATTERNS + _AFFIRMATIVE_GRANT_PATTERNS))
def select_affirmative_license_scope(values: Iterable[object]) -> str | None:
    normalized = [value for raw in values if (value := _normalized_statement(raw)) is not None]
    if any(has_license_denial(value) for value in normalized): return None
    return next((value for value in normalized if is_affirmative_license_scope(value)), None)
def _normalized_public_hostname(hostname: object) -> str | None:
    if not isinstance(hostname, str) or not hostname.strip(): return None
    host = hostname.strip().rstrip(".").lower()
    try: address = ipaddress.ip_address(host)
    except ValueError: address = None
    if address is not None: return _public_ip(host, address)
    try: ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError: return None
    return ascii_host if _valid_public_hostname(ascii_host) else None

def _public_ip(host: str, address: object) -> str | None:
    return host if address.is_global else None

def _valid_public_hostname(host: str) -> bool:
    labels = host.split(".")
    return (len(labels) >= 2 and all(_HOST_LABEL.fullmatch(label) for label in labels)
            and not all(label.isdigit() for label in labels)
            and not any(host == suffix or host.endswith(f".{suffix}") for suffix in _PLACEHOLDER_SUFFIXES))
def is_public_provenance_url(value: object, *, require_path: bool = True) -> bool:
    if not isinstance(value, str) or not value.strip(): return False
    try: parsed = urlparse(value.strip()); hostname = parsed.hostname
    except ValueError: return False
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc and _normalized_public_hostname(hostname) and (not require_path or parsed.path not in {"", "/"}))
def is_placeholder_hostname(hostname: object) -> bool:
    return isinstance(hostname, str) and bool(hostname.strip()) and _normalized_public_hostname(hostname) is None
@dataclass(frozen=True)
class SourcedPhotoEvidence:
    image_type: str
    author: str
    source: str
    source_url: str
    license_scope: str
    permission_evidence: str
    credit: str
def sourced_photo_evidence(attributes: object) -> SourcedPhotoEvidence | None:
    if not isinstance(attributes, Mapping): return None
    image_type = (_normalized_statement(attributes.get("image_type")) or "").lower()
    author, source = _normalized_statement(attributes.get("image_author")), _normalized_statement(attributes.get("image_source"))
    source_url, permission = _normalized_statement(attributes.get("image_source_url")), _normalized_statement(attributes.get("permission_evidence"))
    license_scope = select_affirmative_license_scope([attributes.get("image_license"), attributes.get("license_scope")])
    if image_type not in DOCUMENTARY_IMAGE_TYPES or attributes.get("is_verified_photo") is not True or not author or not source or not source_url or not is_public_provenance_url(source_url) or not license_scope or not permission: return None
    return SourcedPhotoEvidence(image_type, author, source, source_url, license_scope, permission, f"{author} · {source}")
