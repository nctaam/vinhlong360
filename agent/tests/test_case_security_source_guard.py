from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("capability", "receipt_secret", "access_token", "csrf_binding")
SINKS = ("logger", "logging", "analytics", "notification", "parse_qs", "localstorage", "sessionstorage", "persist")
BEARER = re.compile(r"\b(?:receipt_secret|access_token|csrf_binding|case_capability)\b")


def case_security_source_violations(paths: tuple[Path, ...]) -> list[str]:
    violations = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            tree = ast.parse(source)
            lines = [ast.get_source_segment(source, node) or "" for node in ast.walk(tree) if isinstance(node, ast.Call)]
        else:
            lines = [source]
        for number, line in enumerate(lines, 1):
            normalized = line.lower().replace("-", "_")
            if BEARER.search(normalized) and any(sink in normalized for sink in SINKS):
                violations.append(f"{path.name}:{number}")
    return violations


def test_case_security_production_sources_do_not_handle_bearers_at_unsafe_sinks():
    paths = tuple(path for root in (ROOT / "agent", ROOT / "web-nuxt") for path in root.rglob("*") if path.suffix in {".py", ".js", ".ts", ".vue"} and "tests" not in path.parts and "node_modules" not in path.parts)
    assert case_security_source_violations(paths) == []


def test_source_guard_detects_multiline_frontend_and_python_sinks(tmp_path):
    python = tmp_path / "route.py"
    frontend = tmp_path / "page.vue"
    python.write_text("logger.info(\n    access_token\n)\n", encoding="utf-8")
    frontend.write_text("localStorage.setItem(\n  'case', case_capability\n)\n", encoding="utf-8")
    assert len(case_security_source_violations((python, frontend))) == 2
