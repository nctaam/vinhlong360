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


def test_every_mapped_module_imports_pinned_http_client() -> None:
    for relative_path in MAPPED_FETCHERS:
        imported = _module_pinned_http_imports(ROOT / relative_path)
        assert "PinnedHTTPClient" in imported, (
            f"{relative_path} does not import PinnedHTTPClient"
        )
