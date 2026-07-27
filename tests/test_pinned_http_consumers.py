from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPED_FETCHERS = {
    "agent/admin.py": {"_approve_fetch_image_data"},
    "agent/auto_learn.py": {"fetch_url"},
    "agent/gpt55_quality_burst.py": {"fetch_url_text"},
}


def _calls_in_function(path: Path, function_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    calls: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if isinstance(node.func.value, ast.Name):
            calls.add(f"{node.func.value.id}.{node.func.attr}")
    return calls


def test_mapped_fetchers_have_no_direct_general_http_calls() -> None:
    for relative_path, functions in MAPPED_FETCHERS.items():
        path = ROOT / relative_path
        for function_name in functions:
            calls = _calls_in_function(path, function_name)
            assert "httpx.get" not in calls
            assert "requests.get" not in calls


def _module_pinned_http_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "pinned_http":
            imported.update(alias.name for alias in node.names)
    return imported


def test_mapped_fetcher_registry_scope_is_exact() -> None:
    assert MAPPED_FETCHERS == {
        "agent/admin.py": {"_approve_fetch_image_data"},
        "agent/auto_learn.py": {"fetch_url"},
        "agent/gpt55_quality_burst.py": {"fetch_url_text"},
    }


def test_every_mapped_module_imports_pinned_http_client_and_policy() -> None:
    for relative_path in MAPPED_FETCHERS:
        imported = _module_pinned_http_imports(ROOT / relative_path)
        for name in ("PinnedHTTPClient", "EgressPolicy"):
            assert name in imported, f"{relative_path} does not import {name}"


# Every function in agent/ that still reaches the network through a
# general-purpose HTTP client, deliberately enumerated. Migrating these is
# residual egress debt, explicitly out of scope for the P1 pinned tranche --
# but the surface must not grow silently.
KNOWN_UNPINNED_FETCHERS = {
    # Outbound GETs that a future tranche can route through PinnedHTTPClient.
    ("agent/crawler.py", "fetch_page"),
    ("agent/geocode.py", "_query_nominatim"),
    ("agent/realtime.py", "get_weather"),
    # Outbound POSTs to the Telegram bot API. PinnedHTTPClient is GET-only by
    # design, so these cannot migrate without widening that contract.
    ("agent/scheduler.py", "_digest_send"),
    ("agent/scheduler.py", "_send_telegram_admins"),
}

_GENERAL_HTTP_CALLS = {
    ("httpx", "get"),
    ("httpx", "post"),
    ("httpx", "stream"),
    ("httpx", "request"),
    ("httpx", "Client"),
    ("requests", "get"),
    ("requests", "post"),
    ("requests", "request"),
    ("requests", "Session"),
}


def _functions_making_general_http_calls(path: Path) -> set[str]:
    """Names of functions in `path` that call a general-purpose HTTP client.

    Only `name.attr(...)` forms count, so an attribute chain such as
    `self._requests.get(...)` (a dict lookup in agent/bot_gateway.py) is not
    mistaken for an outbound request.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call) or not isinstance(sub.func, ast.Attribute):
                continue
            value = sub.func.value
            if isinstance(value, ast.Name) and (value.id, sub.func.attr) in _GENERAL_HTTP_CALLS:
                offenders.add(node.name)
    return offenders


def test_unpinned_egress_surface_matches_the_documented_set() -> None:
    """Gives the registry teeth: a NEW unpinned fetcher fails this test.

    `test_mapped_fetcher_registry_scope_is_exact` only compares the registry
    literal to itself, so it cannot notice a fourth outbound caller appearing.
    This walks every non-test module under agent/ instead, so both adding an
    unpinned fetcher and pinning an existing one force a deliberate update here.
    """
    found: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "agent").glob("*.py")):
        if path.name == "pinned_http.py":
            continue
        relative = f"agent/{path.name}"
        for function_name in _functions_making_general_http_calls(path):
            found.add((relative, function_name))

    assert found == KNOWN_UNPINNED_FETCHERS, (
        "outbound egress surface changed; pin it or update "
        f"KNOWN_UNPINNED_FETCHERS deliberately.\n"
        f"  newly unpinned: {sorted(found - KNOWN_UNPINNED_FETCHERS)}\n"
        f"  no longer present: {sorted(KNOWN_UNPINNED_FETCHERS - found)}"
    )


def test_mapped_fetchers_are_not_listed_as_unpinned() -> None:
    mapped = {
        (relative_path, function_name)
        for relative_path, functions in MAPPED_FETCHERS.items()
        for function_name in functions
    }
    assert not (mapped & KNOWN_UNPINNED_FETCHERS)
