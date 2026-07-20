#!/usr/bin/env python3
"""Probe the safe-closed public launch boundary.

Task 31 intentionally has only two modes: an operator-source maintenance probe
and the post-reopen closed probe.  This command never prints response bodies or
URLs; its evidence is a small, atomic JSON record containing only stable
surface names, booleans, and reason codes.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET


DEFAULT_BASE_URL = "https://vinhlong360.vn"
MAX_BODY_BYTES = 1_048_576
LAUNCH_EVIDENCE_HEADERS = frozenset(
    {
        "x-launch-policy-fingerprint",
        "x-launch-route-manifest-revision",
        "x-launch-backend-policy-revision",
        "x-launch-sitemap-batch-revision",
        "x-launch-sitemap-requested-batch",
    }
)

_LAUNCH_MATRIX_POLICY_FINGERPRINT = (
    "ef12661b898905bd8b31804475aca64accd4c8b2df32b5252c3b2f61eeeca44c"
)
_LAUNCH_MATRIX_ROUTE_MANIFEST_REVISION = "launch-indexing-policy-v1"
_LAUNCH_MATRIX_BACKEND_POLICY_REVISION = "index-policy-v1"
_LAUNCH_MATRIX_SITEMAP_BATCH_REVISION = "b" * 64
_READINESS_CHECK_NAMES = frozenset(
    {
        "manifest-schema",
        "artifact-evidence",
        "compiled-cache-rules",
        "public-prerender",
        "service-worker-cache-purge",
    }
)


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(value))


def load_launch_matrix_contract() -> Mapping[str, Mapping[str, object]]:
    """Return the immutable seven-case launch response contract.

    The contract deliberately stores only stable response facts.  Runtime
    probes and integration tests use the same mapping so policy cases cannot
    drift between their assertions.
    """

    page_evidence = _freeze_mapping(
        {
            "x-launch-policy-fingerprint": _LAUNCH_MATRIX_POLICY_FINGERPRINT,
            "x-launch-route-manifest-revision": _LAUNCH_MATRIX_ROUTE_MANIFEST_REVISION,
            "x-launch-backend-policy-revision": _LAUNCH_MATRIX_BACKEND_POLICY_REVISION,
        }
    )
    pinned_evidence = _freeze_mapping(
        {
            **page_evidence,
            "x-launch-sitemap-batch-revision": _LAUNCH_MATRIX_SITEMAP_BATCH_REVISION,
        }
    )

    cases: dict[str, Mapping[str, object]] = {
        "closed": _freeze_mapping(
            {
                "policy": "closed",
                "robots": "noindex, follow",
                "evidence_headers": _freeze_mapping({}),
                "sitemap_discovery": False,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "closed-with-backend-sentinel",
                "surface": "/",
            }
        ),
        "selective-static": _freeze_mapping(
            {
                "policy": "selective-open",
                "robots": "index, follow",
                "evidence_headers": page_evidence,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "matching-backend",
                "surface": "/du-lich",
            }
        ),
        "selective-entity-positive": _freeze_mapping(
            {
                "policy": "selective-open",
                "robots": "index, follow",
                "evidence_headers": page_evidence,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "matching-indexable-entity",
                "surface": "/dia-diem/launch-matrix-positive",
            }
        ),
        "selective-entity-negative": _freeze_mapping(
            {
                "policy": "selective-open",
                "robots": "noindex, follow",
                "evidence_headers": page_evidence,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "matching-noindex-entity",
                "surface": "/dia-diem/launch-matrix-negative",
            }
        ),
        "entity-request-failed-open": _freeze_mapping(
            {
                "policy": "failed-open",
                "robots": "noindex, follow",
                "evidence_headers": _freeze_mapping({}),
                "sitemap_discovery": False,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "failed-entity-request",
                "surface": "/dia-diem/launch-matrix-failed",
            }
        ),
        "sitemap-pinned": _freeze_mapping(
            {
                "policy": "selective-open",
                "robots": None,
                "evidence_headers": pinned_evidence,
                "sitemap_discovery": True,
                "sitemap_status": 200,
                "requires_matching_batch_revision": True,
                "fixture": "matching-pinned-sitemap",
                "surface": "/sitemap.xml",
            }
        ),
        "agent-absent-closed": _freeze_mapping(
            {
                "policy": "closed",
                "robots": "noindex, follow",
                "evidence_headers": _freeze_mapping({}),
                "sitemap_discovery": False,
                "sitemap_status": 200,
                "requires_matching_batch_revision": False,
                "fixture": "agent-absent",
                "surface": "/",
            }
        ),
    }
    return MappingProxyType(cases)

EMPTY_URLSET = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
)
EMPTY_MEDIA_URLSET = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"></urlset>'
)
EMPTY_SITEMAP_INDEX = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'
)
SITEMAP_BODIES = {
    "/sitemap.xml": EMPTY_URLSET.encode("utf-8"),
    "/sitemap-media.xml": EMPTY_MEDIA_URLSET.encode("utf-8"),
    "/sitemap-index.xml": EMPTY_SITEMAP_INDEX.encode("utf-8"),
}
SURFACES = ("/", "/robots.txt", *SITEMAP_BODIES)


@dataclass
class HttpResponse:
    """Minimal response shape used by the probe and deterministic tests."""

    path: str
    status: int
    headers: dict[str, tuple[str, ...]]
    body: bytes


class _ProbeRequestError(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any):  # noqa: ANN401
        return None


def _read_limited(stream: Any) -> bytes:  # noqa: ANN401
    data = stream.read(MAX_BODY_BYTES + 1)
    if len(data) > MAX_BODY_BYTES:
        raise _ProbeRequestError("response-too-large")
    return data


def _normalise_headers(headers: Any) -> dict[str, tuple[str, ...]]:  # noqa: ANN401
    result: dict[str, list[str]] = {}
    for key in headers.keys():
        lowered = str(key).lower()
        result.setdefault(lowered, []).extend(str(value) for value in headers.get_all(key) or ())
    return {key: tuple(values) for key, values in result.items()}


def _make_requester(
    base_url: str,
    *,
    host_header: str | None = None,
) -> Callable[[str, float], HttpResponse]:
    split = urlsplit(base_url)
    base = urlunsplit((split.scheme, split.netloc, split.path.rstrip("/"), "", ""))
    opener = build_opener(_NoRedirect)

    def request_path(path: str, timeout_seconds: float) -> HttpResponse:
        url = f"{base}{path}"
        headers = {
            "Accept": "text/html, text/plain, application/xml;q=0.9, */*;q=0.1",
            "User-Agent": "vl360-launch-boundary-probe/1",
        }
        if host_header is not None:
            headers["Host"] = host_header
        request = Request(url, headers=headers, method="GET")
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                return HttpResponse(
                    path=path,
                    status=int(response.status),
                    headers=_normalise_headers(response.headers),
                    body=_read_limited(response),
                )
        except HTTPError as error:
            try:
                body = _read_limited(error)
            except Exception as exc:  # noqa: BLE001 - sanitize every transport failure.
                raise _ProbeRequestError("http-request-failed") from exc
            return HttpResponse(
                path=path,
                status=int(error.code),
                headers=_normalise_headers(error.headers),
                body=body,
            )
        except Exception as exc:  # noqa: BLE001 - never expose network details.
            raise _ProbeRequestError("http-request-failed") from exc

    return request_path


def _request_absolute_url(url: str, timeout_seconds: float) -> HttpResponse:
    split = urlsplit(url)
    base = urlunsplit((split.scheme, split.netloc, "", "", ""))
    path = urlunsplit(("", "", split.path or "/", split.query, ""))
    return _make_requester(base)(path, timeout_seconds)


class _HtmlContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.robots_meta: list[str] = []
        self.sitemap_links = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): (value or "") for name, value in attrs}
        if tag.lower() == "meta" and values.get("name", "").lower() == "robots":
            self.robots_meta.append(values.get("content", ""))
        if tag.lower() == "link":
            rel = set(values.get("rel", "").lower().split())
            if "sitemap" in rel and values.get("href") == "/sitemap-index.xml":
                self.sitemap_links += 1


def _single_header(response: HttpResponse, name: str) -> str | None:
    values = response.headers.get(name.lower(), ())
    return values[0].strip() if len(values) == 1 else None


def _observation(
    *,
    request_completed: bool,
    reasons: Sequence[str],
) -> dict[str, object]:
    return {
        "contract_passed": request_completed and not reasons,
        "reasons": sorted(set(reasons)),
        "request_completed": request_completed,
    }


def _common_errors(response: HttpResponse, *, surface: str, html: bool) -> list[str]:
    errors: list[str] = []
    prefix = "html" if html else "root"
    if response.status != 200:
        errors.append(f"{prefix}-status-invalid")
    if _single_header(response, "cache-control") != "no-store":
        errors.append(f"{prefix}-cache-control-invalid")
    if _single_header(response, "x-launch-indexing-policy") != "closed":
        errors.append("launch-indexing-policy-invalid")
    if any(name in response.headers for name in LAUNCH_EVIDENCE_HEADERS):
        errors.append("launch-evidence-present")
    if any(name in response.headers for name in ("etag", "last-modified")):
        errors.append("launch-validator-present")
    content_type = _single_header(response, "content-type")
    if html and (content_type is None or not content_type.lower().startswith("text/html")):
        errors.append("html-content-type-invalid")
    if not html and surface == "/robots.txt":
        if content_type is None or not content_type.lower().startswith("text/plain"):
            errors.append("robots-content-type-invalid")
    if not html and surface in SITEMAP_BODIES:
        if content_type is None or not content_type.lower().startswith("application/xml"):
            errors.append("sitemap-content-type-invalid")
    return errors


def _html_errors(response: HttpResponse) -> list[str]:
    errors = _common_errors(response, surface=response.path, html=True)
    x_robots = _single_header(response, "x-robots-tag")
    if x_robots != "noindex, follow":
        errors.append("html-x-robots-tag-invalid")

    parser = _HtmlContractParser()
    try:
        parser.feed(response.body.decode("utf-8", "replace"))
        parser.close()
    except Exception:  # noqa: BLE001 - malformed HTML is a failed probe, not a traceback.
        errors.append("html-parse-failed")
        return sorted(set(errors))

    if parser.robots_meta != ["noindex, follow"]:
        errors.append("html-robots-meta-invalid")
    if parser.sitemap_links:
        errors.append("html-sitemap-discovery-present")
    return sorted(set(errors))


def _sitemap_errors(response: HttpResponse) -> list[str]:
    errors = _common_errors(response, surface=response.path, html=False)
    expected = SITEMAP_BODIES[response.path]
    if response.body == expected:
        return sorted(set(errors))

    try:
        root = ET.fromstring(response.body)
    except ET.ParseError:
        stem = response.path.rsplit("/", 1)[-1].removesuffix(".xml")
        errors.append(f"{stem}-shape-invalid")
        return sorted(set(errors))

    local_name = root.tag.rsplit("}", 1)[-1]
    expected_name = "sitemapindex" if response.path == "/sitemap-index.xml" else "urlset"
    if local_name != expected_name:
        stem = response.path.rsplit("/", 1)[-1].removesuffix(".xml")
        errors.append(f"{stem}-shape-invalid")
    elif list(root):
        stem = response.path.rsplit("/", 1)[-1].removesuffix(".xml")
        errors.append("sitemap-root-not-empty" if stem == "sitemap" else f"sitemap-{stem}-not-empty")
    else:
        stem = response.path.rsplit("/", 1)[-1].removesuffix(".xml")
        errors.append(f"{stem}-shape-invalid")
    return sorted(set(errors))


def probe_closed_matrix(
    *,
    requester: Callable[[str, float], HttpResponse],
    timeout_seconds: float,
) -> tuple[list[str], dict[str, dict[str, object]]]:
    errors: set[str] = set()
    observations: dict[str, dict[str, object]] = {}
    for path in SURFACES:
        try:
            response = requester(path, timeout_seconds)
            if not isinstance(response, HttpResponse):
                raise _ProbeRequestError("http-request-failed")
        except Exception:  # noqa: BLE001 - evidence must never contain exception text.
            reasons = ["http-request-failed"]
            observations[path] = _observation(request_completed=False, reasons=reasons)
            errors.update(reasons)
            continue
        surface_errors: list[str]
        if path == "/":
            surface_errors = _html_errors(response)
        elif path == "/robots.txt":
            surface_errors = _common_errors(response, surface=path, html=False)
            content = response.body.decode("utf-8", "replace")
            if any(line.lstrip().lower().startswith("sitemap:") for line in content.splitlines()):
                surface_errors.append("robots-sitemap-discovery-present")
        else:
            surface_errors = _sitemap_errors(response)
        observations[path] = _observation(request_completed=True, reasons=surface_errors)
        errors.update(surface_errors)
    return sorted(errors), observations


def probe_process_local_readiness(
    *,
    requester: Callable[[str, float], HttpResponse],
    readiness_url: str,
    timeout_seconds: float,
    expected_state: str,
    require_complete_check_set: bool,
) -> tuple[list[str], dict[str, dict[str, object]]]:
    errors: list[str] = []
    try:
        response = requester(readiness_url, timeout_seconds)
        if not isinstance(response, HttpResponse):
            raise _ProbeRequestError("http-request-failed")
    except Exception:  # noqa: BLE001 - evidence must never contain exception text.
        errors.append("http-request-failed")
        return errors, {
            "process-local-readiness": _observation(
                request_completed=False,
                reasons=errors,
            )
        }

    if response.status != 200:
        errors.append("readiness-status-invalid")
    if _single_header(response, "cache-control") != "no-store":
        errors.append("readiness-cache-control-invalid")
    content_type = _single_header(response, "content-type")
    if content_type is None or not content_type.lower().startswith("application/json"):
        errors.append("readiness-content-type-invalid")

    payload: object | None = None
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        errors.append("readiness-json-invalid")

    if not isinstance(payload, Mapping):
        errors.append("readiness-body-invalid")
    else:
        if payload.get("ok") is not True:
            errors.append("readiness-ok-invalid")
        if payload.get("state") != expected_state:
            errors.append("readiness-state-invalid")
        if require_complete_check_set:
            checks = payload.get("checks")
            if not isinstance(checks, list):
                errors.append("readiness-check-set-incomplete")
            else:
                names = {
                    item.get("name")
                    for item in checks
                    if isinstance(item, Mapping)
                }
                if names != _READINESS_CHECK_NAMES or any(
                    not isinstance(item, Mapping) or item.get("ok") is not True
                    for item in checks
                ):
                    errors.append("readiness-check-set-incomplete")

    observations = {
        "process-local-readiness": _observation(
            request_completed=True,
            reasons=errors,
        )
    }
    return sorted(set(errors)), observations


def _write_evidence(path: Path, payload: Mapping[str, object]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        return False
    encoded = (json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            return False
        os.replace(temporary, path)
        temporary = None
        return True
    except OSError:
        return False
    finally:
        if descriptor != -1:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _timeout(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be numeric") from exc
    if not 0.1 <= parsed <= 60:
        raise argparse.ArgumentTypeError("timeout is outside the safe range")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe the closed launch boundary.")
    parser.add_argument("--expect", choices=("maintenance", "closed"))
    parser.add_argument("--operator-source", action="store_true")
    parser.add_argument("--require-public-post-reopen-matrix", action="store_true")
    parser.add_argument(
        "--maintenance-probe",
        action="store_true",
        help="Compatibility alias for the operator-source closed maintenance probe.",
    )
    parser.add_argument("--process-local-readiness", metavar="URL")
    parser.add_argument("--require-complete-check-set", action="store_true")
    for flag in (
        "--require-rich-html",
        "--require-thin-html",
        "--require-meta-robots",
        "--require-rich-thin-html",
        "--require-meta-header-noindex",
        "--require-no-sitemap",
        "--require-three-empty-sitemaps",
        "--require-robots-without-sitemap",
        "--require-three-empty-sitemap-shapes",
        "--require-no-store",
        "--require-no-evidence",
        "--require-no-discovery",
        "--require-public-internal-404",
        "--require-direct-bypass-denied",
    ):
        parser.add_argument(flag, action="store_true")
    parser.add_argument("--base-url", default=os.environ.get("VL360_LAUNCH_PUBLIC_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout-seconds", type=_timeout, default=8.0)
    parser.add_argument("--evidence", type=Path)
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    compatibility_flags = (
        args.maintenance_probe
        or args.process_local_readiness is not None
        or args.require_complete_check_set
        or args.require_rich_html
        or args.require_thin_html
        or args.require_meta_robots
        or args.require_rich_thin_html
        or args.require_meta_header_noindex
        or args.require_no_sitemap
        or args.require_three_empty_sitemaps
        or args.require_robots_without_sitemap
        or args.require_three_empty_sitemap_shapes
        or args.require_no_store
        or args.require_no_evidence
        or args.require_no_discovery
        or args.require_public_internal_404
        or args.require_direct_bypass_denied
    )
    if args.expect is None:
        if not compatibility_flags:
            parser.error("one of --expect or --maintenance-probe is required")
        if args.process_local_readiness is not None:
            args.expect = "closed"
        else:
            args.expect = "maintenance"
            args.operator_source = True
    elif compatibility_flags and args.expect == "maintenance":
        # Task44 callers may provide --expect maintenance with the richer
        # assertion vocabulary; preserve the old explicit mode as-is.
        args.operator_source = True

    if args.process_local_readiness is not None:
        split = urlsplit(args.process_local_readiness)
        if split.scheme not in {"http", "https"} or not split.netloc or split.fragment:
            parser.error("process-local-readiness must be an absolute HTTP(S) URL")
        if args.expect != "closed" or args.operator_source or args.require_public_post_reopen_matrix:
            parser.error("process-local-readiness requires closed mode without public-source flags")
        if not args.require_complete_check_set:
            parser.error("process-local-readiness requires complete check set")
    elif args.expect == "maintenance":
        if not args.operator_source or args.require_public_post_reopen_matrix:
            parser.error("maintenance mode requires operator-source")
    elif args.maintenance_probe:
        if not args.operator_source or args.require_public_post_reopen_matrix:
            parser.error("maintenance probe requires operator-source")
    elif not args.require_public_post_reopen_matrix or args.operator_source:
        parser.error("closed mode requires public post-reopen matrix")

    if args.base_url != DEFAULT_BASE_URL:
        parser.error(f"base URL must be exactly {DEFAULT_BASE_URL}")


def main(
    argv: Sequence[str] | None = None,
    *,
    requester: Callable[[str, float], HttpResponse] | None = None,
) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    if args.process_local_readiness is not None:
        errors, observations = probe_process_local_readiness(
            requester=requester or _request_absolute_url,
            readiness_url=args.process_local_readiness,
            timeout_seconds=args.timeout_seconds,
            expected_state=args.expect,
            require_complete_check_set=args.require_complete_check_set,
        )
    else:
        request = requester or _make_requester(args.base_url.rstrip("/"))
        errors, observations = probe_closed_matrix(
            requester=request,
            timeout_seconds=args.timeout_seconds,
        )
    payload: dict[str, object] = {
        "errors": errors,
        "expect": args.expect,
        "observations": observations,
        "schema_version": 1,
        "verdict": "pass" if not errors else "fail",
    }
    if args.evidence is not None and not _write_evidence(args.evidence, payload):
        print("evidence-write-failed", file=os.sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error, file=os.sys.stderr)
        return 2 if errors == ["http-request-failed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
