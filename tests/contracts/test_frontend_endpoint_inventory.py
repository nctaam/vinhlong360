from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "contracts" / "frontend-endpoints.json"
SOURCE_ROOT = ROOT / "web-nuxt"
IGNORED_PARTS = {"node_modules", ".nuxt", ".output", "dist", "tests", "docs"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# These calls intentionally bypass the product API contract. They are admin
# operations/SEO or health probes owned by the platform and remain documented
# as direct transports until those surfaces get their own contract.
DIRECT_TRANSPORT_EXCEPTIONS = {
    "/admin/cases",
    "/health",
    "/health/internal",
    "/reload",
    "/seo/jsonld/",
}


def frontend_source_text() -> str:
    chunks: list[str] = []
    for path in SOURCE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".vue", ".ts", ".js", ".mjs"}:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def frontend_source_files() -> list[Path]:
    return [
        path
        for path in SOURCE_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in {".vue", ".ts", ".js", ".mjs"}
        and not any(part in IGNORED_PARTS for part in path.parts)
    ]


def _transport_calls() -> list[tuple[str, str]]:
    """Extract literal URL prefixes from frontend transport calls.

    The scanner deliberately works on source text rather than importing Nuxt;
    this keeps the contract gate deterministic and catches a newly-added call
    before it can disappear behind a runtime-only code path.
    """
    call_re = re.compile(
        r"(?P<fn>\$fetch|apiFetch|fetcher|fetch|post)\s*(?:<[^>]*>)?\s*"
        r"\(\s*(?P<quote>['\"`])(?P<url>/[^'\"`]*)"
    )
    event_re = re.compile(r"new\s+EventSource\s*\(\s*(?P<quote>['\"`])(?P<url>/[^'\"`]*)")
    calls: list[tuple[str, str]] = []

    def call_body(source: str, start: int) -> str:
        opening = source.find("(", start)
        if opening < 0:
            return ""
        depth = 0
        quote = ""
        escaped = False
        for index in range(opening, min(len(source), opening + 2000)):
            char = source[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
                continue
            if char in "'\"`":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return source[opening:index]
        return source[opening:opening + 2000]

    for path in frontend_source_files():
        source = path.read_text(encoding="utf-8")
        for match in call_re.finditer(source):
            url = match.group("url")
            if path.name == "apiFetch.ts":
                # This helper receives arbitrary URLs from its callers; the
                # helper's own `$fetch(url)` is not an endpoint declaration.
                continue
            if not url:
                continue
            prefix = url
            if any(prefix.startswith(exception) for exception in DIRECT_TRANSPORT_EXCEPTIONS):
                continue
            body = call_body(source, match.start())
            method_match = re.search(r"\bmethod\s*:\s*['\"](GET|POST|PUT|PATCH|DELETE)", body)
            method = "POST" if match.group("fn") == "post" else (method_match.group(1) if method_match else "GET")
            calls.append((method, prefix))
        for match in event_re.finditer(source):
            prefix = match.group("url")
            if not any(prefix.startswith(exception) for exception in DIRECT_TRANSPORT_EXCEPTIONS):
                calls.append(("GET", prefix))
    return calls


_TRANSPORT_NAME_RE = re.compile(r"\$fetch|apiFetch|fetcher|fetch|post")
_EVENT_SOURCE_RE = re.compile(r"new\s+EventSource")
_QUOTES = {"'", chr(34), chr(96)}


def _skip_quoted(source: str, start: int) -> int:
    quote = source[start]
    escaped = False
    for index in range(start + 1, len(source)):
        char = source[index]
        if escaped:
            escaped = False
        elif char == chr(92):
            escaped = True
        elif char == quote:
            return index + 1
    return len(source)


def _skip_ws_and_comments(source: str, start: int) -> int:
    index = start
    while index < len(source):
        if source[index].isspace():
            index += 1
        elif source.startswith("//", index):
            newline = source.find(chr(10), index + 2)
            index = len(source) if newline < 0 else newline + 1
        elif source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = len(source) if end < 0 else end + 2
        else:
            break
    return index


def _consume_type_arguments(source: str, start: int) -> int | None:
    if start >= len(source) or source[start] != "<":
        return start
    depth = 0
    index = start
    while index < len(source):
        char = source[index]
        if char in _QUOTES:
            index = _skip_quoted(source, index)
            continue
        if source.startswith("//", index) or source.startswith("/*", index):
            index = _skip_ws_and_comments(source, index)
            continue
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None


def _quoted_url(source: str, start: int) -> tuple[str, int] | None:
    if start >= len(source) or source[start] not in _QUOTES:
        return None
    quote = source[start]
    escaped = False
    chars: list[str] = []
    for index in range(start + 1, len(source)):
        char = source[index]
        if escaped:
            chars.append(char)
            escaped = False
        elif char == chr(92):
            escaped = True
        elif char == quote:
            return "".join(chars), index + 1
        else:
            chars.append(char)
    return None


def _balanced_call_body(source: str, opening: int) -> str:
    depth = 0
    quote = ""
    escaped = False
    for index in range(opening, min(len(source), opening + 2000)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == chr(92):
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in _QUOTES:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[opening:index]
    return source[opening:opening + 2000]


def _transport_calls_from_source(source: str, filename: str = "") -> list[tuple[str, str]]:
    """Extract URL literals while balancing nested TypeScript type arguments."""
    calls: list[tuple[str, str]] = []
    index = 0
    while index < len(source):
        if source.startswith("//", index) or source.startswith("/*", index):
            index = _skip_ws_and_comments(source, index)
            continue
        if source[index] in _QUOTES:
            index = _skip_quoted(source, index)
            continue
        match = _TRANSPORT_NAME_RE.match(source, index)
        if not match:
            index += 1
            continue
        before = source[index - 1] if index else ""
        after = source[match.end()] if match.end() < len(source) else ""
        if (before and (before.isalnum() or before in "_$")) or (after and (after.isalnum() or after in "_$")):
            index = match.end()
            continue
        cursor = _skip_ws_and_comments(source, match.end())
        type_end = _consume_type_arguments(source, cursor)
        if type_end is None:
            index = match.end()
            continue
        cursor = _skip_ws_and_comments(source, type_end)
        if cursor >= len(source) or source[cursor] != "(":
            index = match.end()
            continue
        parsed = _quoted_url(source, _skip_ws_and_comments(source, cursor + 1))
        if parsed is None:
            index = match.end()
            continue
        prefix, _ = parsed
        if filename == "apiFetch.ts" or not prefix or any(prefix.startswith(exception) for exception in DIRECT_TRANSPORT_EXCEPTIONS):
            index = match.end()
            continue
        body = _balanced_call_body(source, cursor)
        method = "POST" if match.group(0) == "post" else "GET"
        for candidate in ("POST", "PUT", "PATCH", "DELETE", "GET"):
            if f"method: '{candidate}'" in body or f'method: "{candidate}"' in body:
                method = candidate
                break
        calls.append((method, prefix))
        index = match.end()
    for event in _EVENT_SOURCE_RE.finditer(source):
        cursor = _skip_ws_and_comments(source, event.end())
        if cursor >= len(source) or source[cursor] != "(":
            continue
        parsed = _quoted_url(source, _skip_ws_and_comments(source, cursor + 1))
        if parsed is None:
            continue
        prefix, _ = parsed
        if prefix and not any(prefix.startswith(exception) for exception in DIRECT_TRANSPORT_EXCEPTIONS):
            calls.append(("GET", prefix))
    return calls


def _transport_calls() -> list[tuple[str, str]]:
    return [
        call
        for path in frontend_source_files()
        for call in _transport_calls_from_source(path.read_text(encoding="utf-8"), path.name)
    ]


def _endpoint_pattern(value: str) -> str:
    """Convert a source literal or inventory matcher to a path shape."""
    value = re.sub(r"\$\{[^}]*\}", "{id}", value)
    if value.endswith("/"):
        value = value.rstrip("/") + "/{id}"
    value = value.split("?", 1)[0]
    return re.sub(r"\$\{.*", "", value).rstrip("/") or "/"


def test_frontend_endpoint_inventory_is_valid_and_matches_source() -> None:
    document = json.loads(INVENTORY.read_text(encoding="utf-8"))
    entries = document["entries"]
    assert entries
    assert document["version"] == 1
    exceptions = document.get("direct_transport_exceptions", [])
    assert all(set(item) == {"source_match", "reason"} for item in exceptions)
    assert all(item["source_match"] in frontend_source_text() for item in exceptions)

    source = frontend_source_text()
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        assert set(entry) == {"method", "path", "source_match", "auth", "domain"}
        assert entry["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert entry["path"].startswith("/")
        assert entry["source_match"]
        assert entry["auth"] in {"public", "session", "admin", "case-capability"}
        assert entry["domain"]
        assert entry["source_match"] in source, entry
        identity = (entry["method"], entry["path"])
        assert identity not in seen
        seen.add(identity)


def test_frontend_endpoint_inventory_excludes_internal_operations_routes() -> None:
    entries = json.loads(INVENTORY.read_text(encoding="utf-8"))["entries"]
    paths = [entry["path"] for entry in entries]
    assert not any(path.startswith("/_internal/") for path in paths)
    assert not any(path.startswith("/health") for path in paths)


def test_every_frontend_transport_call_is_documented() -> None:
    """The inventory is bidirectional: source additions must add a contract row."""
    entries = json.loads(INVENTORY.read_text(encoding="utf-8"))["entries"]
    source_matches = {(entry["method"], _endpoint_pattern(entry["source_match"])) for entry in entries}
    undocumented = sorted({
        prefix
        for method, prefix in _transport_calls()
        if (method, _endpoint_pattern(prefix)) not in source_matches
    })
    assert not undocumented, f"frontend transport calls missing from inventory: {undocumented}"


def test_pre_case_contact_routes_are_public() -> None:
    entries = json.loads(INVENTORY.read_text(encoding="utf-8"))["entries"]
    auth_by_route = {
        (entry["method"], entry["path"]): entry["auth"]
        for entry in entries
    }
    assert auth_by_route[("POST", "/api/cases/contact/start")] == "public"
    assert auth_by_route[("POST", "/api/cases/contact/verify")] == "public"


def test_user_owned_frontend_routes_require_a_session() -> None:
    entries = json.loads(INVENTORY.read_text(encoding="utf-8"))["entries"]
    auth_by_route = {
        (entry["method"], entry["path"]): entry["auth"]
        for entry in entries
    }
    expected_session_routes = {
        ("POST", "/api/my-plans"),
        ("PUT", "/api/my-plans/{id}"),
        ("DELETE", "/api/my-plans/{id}"),
        ("POST", "/api/my-plans/merge"),
        ("GET", "/api/scheduled"),
        ("DELETE", "/api/scheduled/{id}"),
        ("POST", "/api/drafts"),
        ("POST", "/api/drafts/{id}/schedule"),
        ("PUT", "/api/notification-preferences"),
        ("POST", "/api/events/{id}/rsvp"),
        ("GET", "/auth/login-history"),
    }
    assert {route for route in expected_session_routes if auth_by_route.get(route) != "session"} == set()
    # The status endpoint is intentionally readable without a session; only
    # the RSVP mutation is user-owned.
    assert auth_by_route[("GET", "/api/events/{id}/rsvp")] == "public"


def test_transport_scanner_handles_nested_types_without_identifier_false_positives() -> None:
    source = """
    const good = apiFetch<Record<string, unknown>>('/api/nested', { method: 'POST' })
    const alsoGood = $fetch<Array<Record<string, unknown>>>('/api/array')
    const decoy = myapiFetch<Record<string, unknown>>('/api/not-a-transport')
    """
    calls = _transport_calls_from_source(source, "fixture.ts")
    assert ("POST", "/api/nested") in calls
    assert ("GET", "/api/array") in calls
    assert all(prefix != "/api/not-a-transport" for _, prefix in calls)
