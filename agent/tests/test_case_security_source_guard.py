from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {"capability", "receipt_secret", "access_token", "csrf_binding", "case_capability"}
CALL = re.compile(
    r"(?<![\w$])(?:new\s+)?(?P<callee>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\("
)
IDENTIFIER = re.compile(r"\b[A-Za-z_$][\w$]*\b")
FRONTEND_SINK_ROOTS = {
    "$fetch", "analytics", "axios", "console", "document", "history",
    "localStorage", "location", "notification", "notify", "query", "route",
    "router", "sessionStorage", "top", "window",
}
FRONTEND_SINK_METHODS = {
    "append", "appendChild", "assign", "create", "createTextNode", "execute",
    "fetch", "insert", "log", "navigateTo", "open", "persist", "push",
    "pushState", "replace", "replaceChildren", "replaceState", "save", "send",
    "setAttribute", "setItem", "update", "write",
}
PYTHON_SINK_ROOTS = {
    "analytics", "document", "logger", "logging", "notification", "notify",
    "query", "route", "router", "security_logger", "storage",
}
PYTHON_SINK_METHODS = {
    "create", "critical", "debug", "error", "exception", "execute", "fetch",
    "info", "insert", "notify", "parse_qs", "parse_qsl", "persist", "query",
    "save", "send", "update", "warning",
}
FRONTEND_ASSIGNMENT_SINK_ROOTS = {
    "document", "history", "localStorage", "location", "navigator",
    "sessionStorage", "top", "window",
}
FRONTEND_ASSIGNMENT_SINK_PROPERTIES = {
    "action", "cookie", "hash", "href", "innerHTML", "innerText", "name",
    "outerHTML", "pathname", "search", "src", "srcdoc", "textContent",
    "title", "value",
}
ASSIGNMENT = re.compile(
    r"(?P<target>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*|\[[^\]\r\n]{0,80}\])+)"
    r"\s*(?:\+|\|\||\?\?)?=(?!=)"
)


def _strip_literals(value: str) -> str:
    """Drop literal and comment text but keep executable ``${...}`` expressions.

    Removing a whole backtick literal also removed the interpolated expressions
    inside it, so a bearer routed through ```${access_token}``` reached a sink
    unseen. Comments go too, otherwise a warning that merely names a bearer
    reads as a leak. A quote with no partner on its own line is prose (``don't``)
    or part of a regex literal rather than a string, so it is kept verbatim
    instead of swallowing every sink below it. Line count is preserved so
    callers can still locate a violation.
    """
    kept: list[str] = []
    index, length = 0, len(value)
    while index < length:
        char = value[index]
        following = value[index + 1:index + 2]
        if char == "/" and following in {"/", "*"} and (index == 0 or value[index - 1].isspace()):
            if following == "/":
                while index < length and value[index] != "\n":
                    index += 1
                continue
            index += 2
            while index < length and value[index:index + 2] != "*/":
                if value[index] == "\n":
                    kept.append("\n")
                index += 1
            index += 2
            kept.append(" ")
            continue
        if char in "'\"":
            close = index + 1
            while close < length and value[close] not in (char, "\n"):
                close += 2 if value[close] == "\\" else 1
            if close >= length or value[close] != char:
                kept.append(char)
                index += 1
                continue
            kept.append(" ")
            index = close + 1
            continue
        if char != "`":
            kept.append(char)
            index += 1
            continue
        index += 1
        while index < length:
            if value[index] == "\\":
                if value[index + 1:index + 2] == "\n":
                    kept.append("\n")
                index += 2
                continue
            if value[index] == "`":
                index += 1
                break
            if value[index] == "$" and value[index + 1:index + 2] == "{":
                index += 2
                depth, start = 1, index
                while index < length and depth:
                    depth += {"{": 1, "}": -1}.get(value[index], 0)
                    index += 1
                kept.append(f" {value[start:index - 1]} ")
                continue
            if value[index] == "\n":
                kept.append("\n")
            index += 1
        kept.append(" ")
    return "".join(kept)


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


def _callee_parts(node: ast.AST) -> tuple[str, str]:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    parts.reverse()
    return (parts[0], parts[-1]) if parts else ("", "")


def _direct_scope_nodes(scope: ast.AST):
    body = getattr(scope, "body", [])
    stack = [body] if isinstance(body, ast.AST) else list(reversed(body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _python_violations(source: str) -> list[int]:
    tree = ast.parse(source)
    scopes = [tree]
    scopes.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
    )
    violations = []
    for scope in scopes:
        nodes = list(_direct_scope_nodes(scope))
        aliases = set(FORBIDDEN)
        changed = True
        while changed:
            changed = False
            for node in nodes:
                value = None
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
                    value = node.value.id
                    targets = [item for item in node.targets if isinstance(item, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Name):
                    value = node.value.id
                    targets = [node.target] if isinstance(node.target, ast.Name) else []
                else:
                    targets = []
                if value in aliases:
                    for target in targets:
                        if target.id not in aliases:
                            aliases.add(target.id)
                            changed = True
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            root, method = _callee_parts(node.func)
            if root not in PYTHON_SINK_ROOTS and method not in PYTHON_SINK_METHODS:
                continue
            argument_nodes = [*node.args, *(keyword.value for keyword in node.keywords)]
            names = {
                item.id
                for argument in argument_nodes
                for item in ast.walk(argument)
                if isinstance(item, ast.Name)
            }
            if names & aliases:
                violations.append(node.lineno)
    return sorted(set(violations))


def _is_frontend_sink(callee: str) -> bool:
    parts = callee.split(".")
    return (
        callee == "URLSearchParams"
        or parts[0] in FRONTEND_SINK_ROOTS
        or parts[-1] in FRONTEND_SINK_METHODS
    )


def _frontend_aliases(source: str) -> set[str]:
    aliases = set(FORBIDDEN)
    alias_pattern = re.compile(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)"
        r"(?:\s*:\s*[^=;\r\n]+)?\s*=\s*([A-Za-z_$][\w$]*)\b"
    )
    changed = True
    while changed:
        changed = False
        for match in alias_pattern.finditer(source):
            if match.group(2) in aliases and match.group(1) not in aliases:
                aliases.add(match.group(1))
                changed = True
    return aliases


def _assignment_sink_violations(scrubbed: str, aliases: set[str]) -> list[int]:
    """Browser property-assignment sinks: they persist a bearer without a call."""
    violations = []
    for match in ASSIGNMENT.finditer(scrubbed):
        parts = [
            part
            for part in (item.strip() for item in re.split(r"[.\[\]]+", match.group("target")))
            if part
        ]
        if (
            parts[0] not in FRONTEND_ASSIGNMENT_SINK_ROOTS
            and parts[-1] not in FRONTEND_ASSIGNMENT_SINK_PROPERTIES
            # A dataset write persists into a data-* attribute whatever the
            # element variable is called and whatever key the author picks.
            and "dataset" not in parts
        ):
            continue
        tail = scrubbed[match.end():match.end() + 200].lstrip()
        assigned = re.split(r"[;\r\n]", tail, maxsplit=1)[0]
        if set(IDENTIFIER.findall(assigned)) & aliases:
            violations.append(scrubbed.count("\n", 0, match.start()) + 1)
    return violations


def _frontend_violations(source: str) -> list[int]:
    # Both passes read the scrubbed source so a commented-out sink cannot be
    # reported and a bearer named in a comment cannot be mistaken for a value.
    scrubbed = _strip_literals(source)
    aliases = _frontend_aliases(scrubbed)
    violations = []
    for match in CALL.finditer(scrubbed):
        if not _is_frontend_sink(match.group("callee")):
            continue
        args = _call_arguments(scrubbed, match.end())
        if set(IDENTIFIER.findall(args)) & aliases:
            violations.append(scrubbed.count("\n", 0, match.start()) + 1)
    violations.extend(_assignment_sink_violations(scrubbed, aliases))
    return sorted(set(violations))


def case_security_source_violations(paths: tuple[Path, ...]) -> list[str]:
    violations = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            violations.extend(f"{path.name}:{line}" for line in _python_violations(source))
            continue
        else:
            violations.extend(f"{path.name}:{line}" for line in _frontend_violations(source))
    return violations


def test_case_security_production_sources_do_not_handle_bearers_at_unsafe_sinks():
    paths = tuple(path for root in (ROOT / "agent", ROOT / "web-nuxt") for path in root.rglob("*") if path.suffix in {".py", ".js", ".ts", ".vue"} and "tests" not in path.parts and "node_modules" not in path.parts
                  # Build output is minified soup, not a source anybody edits; scanning
                  # it makes the guard fail on whoever last ran `npm run build`.
                  and ".output" not in path.parts and ".nuxt" not in path.parts and "dist" not in path.parts)
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


def test_source_guard_detects_query_parsers_and_typed_logger_aliases(tmp_path):
    python = tmp_path / "typed_alias.py"
    frontend = tmp_path / "typed_alias.ts"
    python.write_text(
        "from urllib.parse import parse_qs\n"
        "parsed = parse_qs(access_token)\n"
        "logger_alias: str = case_capability\n"
        "logger.info(logger_alias)\n",
        encoding="utf-8",
    )
    frontend.write_text(
        "const typedAlias: string = receipt_secret\n"
        "console.log(typedAlias)\n"
        "const params = new URLSearchParams({ access: case_capability })\n",
        encoding="utf-8",
    )

    violations = case_security_source_violations((python, frontend))

    assert violations == ["typed_alias.py:2", "typed_alias.py:4", "typed_alias.ts:2", "typed_alias.ts:3"]


def test_source_guard_covers_route_notification_persistence_dom_and_browser_storage(tmp_path):
    frontend = tmp_path / "sinks.vue"
    frontend.write_text(
        "const bearer: string = access_token\n"
        "router.push({ query: { receipt: bearer } })\n"
        "notification.send({ body: bearer })\n"
        "repository.persist({ capability: bearer })\n"
        "document.createTextNode(bearer)\n"
        "localStorage.setItem('case', bearer)\n"
        "sessionStorage.setItem('case', bearer)\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == [
        "sinks.vue:2",
        "sinks.vue:3",
        "sinks.vue:4",
        "sinks.vue:5",
        "sinks.vue:6",
        "sinks.vue:7",
    ]


def test_source_guard_detects_bearers_inside_executable_template_expressions(tmp_path):
    frontend = tmp_path / "template.ts"
    frontend.write_text(
        "console.log(`case=${access_token}`)\n"
        "localStorage.setItem('case', `${case_capability}`)\n"
        "console.log(`case=${publicReference}`)\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == ["template.ts:1", "template.ts:2"]


def test_source_guard_detects_browser_property_assignment_sinks(tmp_path):
    frontend = tmp_path / "assign.vue"
    frontend.write_text(
        "window.location.href = access_token\n"
        "document.body.textContent = case_capability\n"
        "localStorage.caseToken = receipt_secret\n"
        "sessionStorage['case'] = access_token\n"
        "element.innerHTML = case_capability\n"
        "anchor.href +=\n  case_capability\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == [
        "assign.vue:1", "assign.vue:2", "assign.vue:3",
        "assign.vue:4", "assign.vue:5", "assign.vue:6",
    ]


def test_source_guard_survives_apostrophes_in_comments_and_regex_literals(tmp_path):
    """An unpaired quote is prose or a regex, and must not silence later sinks."""
    frontend = tmp_path / "prose.ts"
    frontend.write_text(
        "// we don't persist bearers here\n"
        "window.location.href = access_token\n"
        "const pattern = /it's/\n"
        "document.body.textContent = case_capability\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == ["prose.ts:2", "prose.ts:4"]


def test_source_guard_ignores_bearer_names_mentioned_only_in_comments(tmp_path):
    frontend = tmp_path / "commented.vue"
    frontend.write_text(
        "document.title = publicReference // never put access_token here\n"
        "/* case_capability must never reach localStorage */\n"
        "localStorage.setItem('case', publicReference)\n"
        "// localStorage.setItem('case', access_token)\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == []


def test_source_guard_covers_navigation_and_history_call_sinks(tmp_path):
    frontend = tmp_path / "nav.ts"
    frontend.write_text(
        "location.assign(access_token)\n"
        "history.pushState({}, '', access_token)\n"
        "history.replaceState({}, '', access_token)\n"
        "window.open(access_token)\n"
        "location.assign(publicReference)\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == [
        "nav.ts:1", "nav.ts:2", "nav.ts:3", "nav.ts:4",
    ]


def test_source_guard_covers_dataset_property_writes(tmp_path):
    frontend = tmp_path / "dataset.vue"
    frontend.write_text(
        "el.dataset.token = access_token\n"
        "row.dataset.caseCapability = case_capability\n"
        "el.dataset.reference = publicReference\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == [
        "dataset.vue:1", "dataset.vue:2",
    ]


def test_source_guard_does_not_flag_comparisons_or_non_bearer_assignment_sinks(tmp_path):
    frontend = tmp_path / "safe.ts"
    frontend.write_text(
        "if (location.href === access_token) { redirect() }\n"
        "const rendered = `case=${publicReference}`\n"
        "document.title = publicReference\n"
        "const capability = LEGACY_PUBLIC_CAPABILITY[key]\n"
        "state.capabilityMode = resolvePublicCapabilityMode(capability, flags)\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == []


def test_source_guard_does_not_join_unrelated_occurrences_across_one_file(tmp_path):
    frontend = tmp_path / "unrelated.ts"
    frontend.write_text(
        "const safeValue: string = publicReference\n"
        "console.log(safeValue)\n"
        "const label = 'access_token is forbidden in URLs'\n"
        "const receipt_secret = issueSecret()\n"
        "renderPublicCopy('receipt_secret')\n",
        encoding="utf-8",
    )

    assert case_security_source_violations((frontend,)) == []


def test_security_module_has_canonical_key_validation_boundary():
    source = (ROOT / "agent" / "cases" / "security.py").read_text(encoding="utf-8")
    assert "validate_case_encryption_key" in source
