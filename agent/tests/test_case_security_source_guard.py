from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {"capability", "receipt_secret", "access_token", "csrf_binding", "case_capability"}
SINK_CALL = re.compile(
    r"(?:logger|logging|security_logger|analytics|notification|notify|router|route|query|execute|fetch|axios|\$fetch|save|persist|insert|update|create|localStorage|sessionStorage|document)"
    r"(?:\.[A-Za-z_$][\w$]*)?\s*\("
)
IDENTIFIER = re.compile(r"\b[A-Za-z_$][\w$]*\b")


def _strip_literals(value: str) -> str:
    return re.sub(r"(['\"])(?:\\.|(?!\1).)*\1|`(?:\\.|[^`])*`", "", value, flags=re.DOTALL)


def _call_arguments(source: str, start: int) -> str:
    depth = 1
    index = start
    quote = None
    while index < len(source):
        char = source[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start:index]
        index += 1
    return source[start:]


def _frontend_violations(source: str) -> bool:
    aliases = set(FORBIDDEN)
    for match in re.finditer(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\b", source):
        if match.group(2) in aliases:
            aliases.add(match.group(1))
    for match in SINK_CALL.finditer(source):
        args = _strip_literals(_call_arguments(source, match.end()))
        if set(IDENTIFIER.findall(args)) & aliases:
            return True
    return False


def case_security_source_violations(paths: tuple[Path, ...]) -> list[str]:
    violations = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            tree = ast.parse(source)
            aliases = set(FORBIDDEN)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in aliases:
                    aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            lines = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                callee = ast.get_source_segment(source, node.func) or ""
                if not any(token in callee.lower() for token in ("logger", "logging", "notify", "route", "query", "execute", "fetch", "save", "persist", "insert", "update", "create", "storage", "document")):
                    continue
                names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
                if names & aliases:
                    lines.append(node)
            for node in lines:
                violations.append(f"{path.name}:{getattr(node, 'lineno', 1)}")
            continue
        else:
            if _frontend_violations(source):
                violations.append(f"{path.name}:1")
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


def test_source_guard_tracks_exact_capability_aliases_at_sinks_without_filewide_hits(tmp_path):
    python = tmp_path / "alias.py"
    frontend = tmp_path / "alias.vue"
    python.write_text(
        "capability = issue()\n"
        "capability_alias = capability\n"
        "logger.info('capability is a field name')\n"
        "logger.info(capability_alias)\n",
        encoding="utf-8",
    )
    frontend.write_text(
        "const capability = issue()\n"
        "const capabilityAlias = capability\n"
        "console.log('capability')\n"
        "localStorage.setItem('case', capabilityAlias)\n",
        encoding="utf-8",
    )
    violations = case_security_source_violations((python, frontend))
    assert len(violations) == 2


def test_security_module_has_canonical_key_validation_boundary():
    source = (ROOT / "agent" / "cases" / "security.py").read_text(encoding="utf-8")
    assert "validate_case_encryption_key" in source
