from __future__ import annotations

import ast
import copy
import functools
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from route_manifest import (
    classify_request_target,
    extract_static_sitemap_paths,
    load_route_manifest,
    validate_route_manifest_data,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO_ROOT / "web-nuxt"
MANIFEST_PATH = REPO_ROOT / "config" / "launch-indexing-policy.json"
ADMIN_PATH = REPO_ROOT / "agent" / "admin.py"
ROUTE_CORPUS_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "launch-route-parity-corpus.json"
)
VALIDATOR_CORPUS_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "launch-route-validator-corpus.json"
)
NGINX_PATHS = (REPO_ROOT / "nginx.conf", REPO_ROOT / "nginx-ssl.conf")
TYPESCRIPT_RUNNER_TIMEOUT_SECONDS = 120
TYPESCRIPT_OUTPUT_SENTINEL = "__VL360_ROUTE_PARITY_JSON__:"

ROUTE_CORPUS = json.loads(ROUTE_CORPUS_PATH.read_text(encoding="utf-8"))
VALIDATOR_CORPUS = json.loads(VALIDATOR_CORPUS_PATH.read_text(encoding="utf-8"))
STATIC_SITEMAP_PATHS = (
    "/",
    "/ban-do",
    "/chinh-sach-bao-mat",
    "/danh-ba",
    "/dia-diem",
    "/dieu-khoan-su-dung",
    "/du-lich",
    "/gioi-thieu",
    "/huong-dan",
    "/huong-dan-thanh-vien",
    "/kham-pha/am-thuc",
    "/kham-pha/lang-nghe",
    "/kham-pha/mua-sam",
    "/kham-pha/thien-nhien",
    "/kham-pha/van-hoa",
    "/khu-vuc/ben-tre",
    "/khu-vuc/tra-vinh",
    "/khu-vuc/vinh-long",
    "/le-hoi",
    "/lien-he",
    "/luu-tru",
    "/ocop",
    "/san-pham",
    "/su-kien",
    "/theo-mua",
    "/tuyen-duong",
)
PROXY_TARGET_URL = re.compile(
    r"^http://(?P<upstream>vl360_agent|vl360_bots|vl360_nuxt)(?P<uri>/.*)?$"
)
REVIEWED_VARIABLE_BINDINGS = {
    "$agent_upstream": "http://agent:8360",
    "$bot_upstream": "http://bot-gateway:8361",
    "$nuxt_upstream": "http://nuxt:3000",
}
REVIEWED_PASSTHROUGH_VARIABLE_PROXY_TARGETS = {
    "$agent_upstream$request_uri": ("$agent_upstream", ("vl360_agent", "")),
    "$bot_upstream$request_uri": ("$bot_upstream", ("vl360_bots", "")),
}
REVIEWED_NUXT_VARIABLE_PROXY_TARGET = "$nuxt_upstream$request_uri"
REVIEWED_NUXT_EXACT_SELECTORS = frozenset(
    {
        "= /robots.txt",
        "= /sitemap.xml",
        "= /sitemap-index.xml",
        "= /sitemap-media.xml",
    }
)
REVIEWED_NUXT_CATCHALL_SENSITIVE_PREFIXES = frozenset(
    {"/_internal", "/cai-dat", "/da-luu", "/tai-khoan", "/thong-bao"}
)
REVIEWED_ADMIN_VARIABLE_PROXY_TARGET = "$agent_upstream$uri$is_args$args"
POLICY_BEARING_NGINX_DIRECTIVES = {
    "location",
    "map",
    "proxy_pass",
    "rewrite",
    "server",
    "set",
}
UPSTREAM_OWNERS = {"vl360_agent": "agent", "vl360_bots": "bot-gateway"}
SEO_TRANSITION_LOCATION = (
    r"~ ^/(sitemap.*\.xml|robots\.txt)$",
    "vl360_agent",
    "",
)


@dataclass(frozen=True)
class _NginxArgument:
    value: str
    quoted: bool
    had_escape: bool


@dataclass(frozen=True)
class _NginxStatement:
    parts: tuple[_NginxArgument, ...]
    children: tuple[_NginxStatement, ...] | None


@dataclass(frozen=True)
class _AdminProxyRule:
    selector: str
    rewrite: tuple[_NginxArgument, ...]
    proxy_uri: str


def _manifest_source() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@functools.cache
def _fastapi_admin_prefix() -> str:
    tree = ast.parse(
        ADMIN_PATH.read_text(encoding="utf-8"), filename=str(ADMIN_PATH)
    )
    assignments: list[ast.expr | None] = []
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = (statement.target,)
        else:
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "router"
            for target in targets
        ):
            assignments.append(statement.value)

    if len(assignments) != 1:
        raise AssertionError("FastAPI admin router authority is ambiguous")
    call = assignments[0]
    if (
        not isinstance(call, ast.Call)
        or not isinstance(call.func, ast.Name)
        or call.func.id != "APIRouter"
    ):
        raise AssertionError("FastAPI admin router authority is ambiguous")
    prefix_values = [
        keyword.value for keyword in call.keywords if keyword.arg == "prefix"
    ]
    if (
        len(prefix_values) != 1
        or not isinstance(prefix_values[0], ast.Constant)
        or type(prefix_values[0].value) is not str
    ):
        raise AssertionError("FastAPI admin router prefix is not a literal")
    prefix = prefix_values[0].value
    if re.fullmatch(r"/[a-z0-9-]+", prefix) is None:
        raise AssertionError("FastAPI admin router authority is ambiguous")
    return prefix


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json(child) for child in value]
    return value


def _pointer_parts(pointer: str) -> list[str]:
    assert pointer.startswith("/")
    return [
        part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")
    ]


def _pointer_parent(document: object, pointer: str) -> tuple[object, str]:
    parts = _pointer_parts(pointer)
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def _apply_mutation(document: dict[str, object], mutation: dict[str, object]) -> None:
    parent, key = _pointer_parent(document, str(mutation["pointer"]))
    operation = mutation["operation"]
    if operation == "delete":
        if isinstance(parent, list):
            del parent[int(key)]
        else:
            del parent[key]
    elif operation == "set":
        if isinstance(parent, list):
            parent[int(key)] = copy.deepcopy(mutation["value"])
        else:
            parent[key] = copy.deepcopy(mutation["value"])
    elif operation == "append-copy":
        assert isinstance(parent, list)
        parent.append(copy.deepcopy(parent[int(key)]))
    elif operation == "append":
        target = parent[int(key)] if isinstance(parent, list) else parent[key]
        assert isinstance(target, list)
        target.append(copy.deepcopy(mutation["value"]))
    else:
        raise AssertionError(f"unsupported mutation operation: {operation}")


def _accepted_ingress_manifest() -> dict[str, object]:
    candidate = _manifest_source()
    for mutation in VALIDATOR_CORPUS:
        if (
            str(mutation["name"]).startswith("accepted-ingress-")
            or mutation["name"] == "accepted-nel-ingress-review"
        ):
            _apply_mutation(candidate, mutation)
    return candidate


def _validate_route_mutation_shape(mutation: object) -> None:
    assert isinstance(mutation, dict)
    assert set(mutation) == {"operation", "pointer", "value"}
    assert mutation["operation"] == "append"
    assert mutation["pointer"] in {"/exact_routes", "/dynamic_templates"}
    assert isinstance(mutation["value"], dict)


def _validate_route_variant_shape(variant: object, names: set[str]) -> None:
    assert isinstance(variant, dict)
    required = {"name", "mutations"}
    assert required <= set(variant) <= required | {"static_sitemap_paths"}
    assert isinstance(variant["name"], str) and variant["name"]
    assert variant["name"] not in names
    names.add(variant["name"])
    assert isinstance(variant["mutations"], list) and variant["mutations"]
    for mutation in variant["mutations"]:
        _validate_route_mutation_shape(mutation)
    if "static_sitemap_paths" in variant:
        _validate_static_sitemap_paths_shape(variant["static_sitemap_paths"])


def _validate_static_sitemap_paths_shape(paths: object) -> None:
    assert isinstance(paths, list)
    assert len(paths) == 2
    assert all(type(path) is str for path in paths)


def _validate_route_row_shape(row: object, variant_names: set[str]) -> None:
    required = {"target", "method", "classification", "canonical"}
    assert isinstance(row, dict)
    assert required <= row.keys() <= required | {"variant"}
    assert type(row["target"]) is str
    assert type(row["method"]) is str
    assert type(row["classification"]) is str
    assert row["canonical"] is None or type(row["canonical"]) is str
    if row.get("variant") is not None:
        _validate_route_variant_shape(row["variant"], variant_names)


def _validate_route_corpus_shape() -> None:
    assert isinstance(ROUTE_CORPUS, list)
    variant_names: set[str] = set()
    for row in ROUTE_CORPUS:
        _validate_route_row_shape(row, variant_names)


def _route_manifest_for_row(row: dict[str, object], tmp_path: Path):
    candidate = _manifest_source()
    variant = row.get("variant")
    if variant is None:
        return load_route_manifest()
    for mutation in variant["mutations"]:
        _apply_mutation(candidate, mutation)
    validate_route_manifest_data(candidate)
    fixture = tmp_path / f"{variant['name']}.json"
    fixture.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
    return load_route_manifest(fixture_path=fixture)


def _flush_nginx_word(
    buffer: list[str],
    tokens: list[tuple[str, str, bool]],
    had_escape: bool,
    had_quote: bool,
) -> tuple[bool, bool]:
    if buffer:
        tokens.append(("quoted" if had_quote else "word", "".join(buffer), had_escape))
        buffer.clear()
    return False, False


def _read_nginx_quoted(source: str, start: int) -> tuple[str, int, bool]:
    quote = source[start]
    value: list[str] = []
    had_escape = False
    index = start + 1
    while index < len(source):
        character = source[index]
        if character == "\\" and index + 1 < len(source):
            had_escape = True
            value.append(source[index + 1])
            index += 2
            continue
        if character == quote:
            return "".join(value), index + 1, had_escape
        value.append(character)
        index += 1
    raise AssertionError("unterminated quoted Nginx token")


def _tokenize_nginx(source: str) -> list[tuple[str, str, bool]]:
    tokens: list[tuple[str, str, bool]] = []
    buffer: list[str] = []
    buffer_had_escape = False
    buffer_had_quote = False
    index = 0
    while index < len(source):
        character = source[index]
        if character == "\\":
            buffer_had_escape = True
            if index + 1 < len(source):
                buffer.extend((character, source[index + 1]))
                index += 2
                continue
            buffer.append(character)
        elif character.isspace():
            buffer_had_escape, buffer_had_quote = _flush_nginx_word(
                buffer, tokens, buffer_had_escape, buffer_had_quote
            )
        elif character == "#":
            buffer_had_escape, buffer_had_quote = _flush_nginx_word(
                buffer, tokens, buffer_had_escape, buffer_had_quote
            )
            newline = source.find("\n", index)
            index = len(source) if newline == -1 else newline
            continue
        elif character in {'"', "'"}:
            buffer_had_quote = True
            value, index, had_escape = _read_nginx_quoted(source, index)
            buffer.extend(value)
            buffer_had_escape = buffer_had_escape or had_escape
            continue
        elif character in "{};":
            buffer_had_escape, buffer_had_quote = _flush_nginx_word(
                buffer, tokens, buffer_had_escape, buffer_had_quote
            )
            tokens.append(("symbol", character, False))
        else:
            buffer.append(character)
        index += 1
    _flush_nginx_word(buffer, tokens, buffer_had_escape, buffer_had_quote)
    return tokens


def _parse_nginx_statements(
    tokens: list[tuple[str, str, bool]],
    index: int = 0,
    *,
    expect_close: bool = False,
) -> tuple[tuple[_NginxStatement, ...], int]:
    statements: list[_NginxStatement] = []
    parts: list[_NginxArgument] = []
    while index < len(tokens):
        kind, value, had_escape = tokens[index]
        if kind in {"word", "quoted"}:
            parts.append(_NginxArgument(value, kind == "quoted", had_escape))
        elif value == ";":
            if not parts:
                raise AssertionError("empty Nginx directive")
            statements.append(_NginxStatement(tuple(parts), None))
            parts.clear()
        elif value == "{":
            if not parts:
                raise AssertionError("Nginx block is missing a header")
            children, index = _parse_nginx_statements(
                tokens, index + 1, expect_close=True
            )
            statements.append(_NginxStatement(tuple(parts), children))
            parts.clear()
            continue
        else:
            if not expect_close or parts:
                raise AssertionError("unexpected Nginx closing brace")
            return tuple(statements), index + 1
        index += 1
    if expect_close:
        raise AssertionError("unterminated Nginx block")
    if parts:
        raise AssertionError("unterminated Nginx directive")
    return tuple(statements), index


def _backend_reference(
    parts: tuple[_NginxArgument, ...],
    location: str | None,
    variable_bindings: frozenset[str],
    rewrites: tuple[tuple[_NginxArgument, ...], ...],
    admin_authority: tuple[_AdminProxyRule, ...],
    nuxt_selectors: frozenset[str],
) -> tuple[str, str] | None:
    if not parts or parts[0].value != "proxy_pass":
        return None
    selector = location or "<outside location>"
    if len(parts) != 2:
        raise AssertionError(
            f"unsupported proxy target in {selector}: "
            f"{' '.join(part.value for part in parts[1:])}"
        )
    target = parts[1]
    if target.had_escape:
        raise AssertionError(
            f"escaped proxy target {target.value!r} is unsupported in {selector}"
        )
    if target.value == REVIEWED_ADMIN_VARIABLE_PROXY_TARGET:
        rule = next(
            (rule for rule in admin_authority if rule.selector == selector), None
        )
        if rule is None:
            raise AssertionError(
                f"unsupported proxy target {target.value!r} in {selector}"
            )
        _require_variable_binding(
            "$agent_upstream", variable_bindings, target.value, selector
        )
        return "vl360_agent", _admin_rewrite_proxy_uri(selector, rewrites, rule)
    if target.value in REVIEWED_PASSTHROUGH_VARIABLE_PROXY_TARGETS:
        variable, proxy = REVIEWED_PASSTHROUGH_VARIABLE_PROXY_TARGETS[target.value]
        _require_variable_binding(variable, variable_bindings, target.value, selector)
        return proxy
    if target.value == REVIEWED_NUXT_VARIABLE_PROXY_TARGET:
        _require_variable_binding(
            "$nuxt_upstream", variable_bindings, target.value, selector
        )
        _require_reviewed_nuxt_selector(selector, nuxt_selectors)
        return None
    if "$" in target.value:
        raise AssertionError(f"unsupported proxy target {target.value!r} in {selector}")
    match = PROXY_TARGET_URL.fullmatch(target.value)
    if match is None:
        raise AssertionError(f"unsupported proxy target {target.value!r} in {selector}")
    if match.group("upstream") == "vl360_nuxt":
        if match.group("uri") is not None:
            raise AssertionError(
                f"unsupported proxy target {target.value!r} in {selector}"
            )
        _require_reviewed_nuxt_selector(selector, nuxt_selectors)
        return None
    return match.group("upstream"), match.group("uri") or ""


def _unescape_nginx_word(value: str) -> str:
    unescaped: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            index += 1
        unescaped.append(value[index])
        index += 1
    return "".join(unescaped)


def _validate_nginx_directive_name(parts: tuple[_NginxArgument, ...]) -> None:
    if not parts or not parts[0].had_escape:
        return
    if _unescape_nginx_word(parts[0].value) in POLICY_BEARING_NGINX_DIRECTIVES:
        raise AssertionError(f"escaped Nginx directive {parts[0].value!r}")


def _unsupported_variable_binding(variable: str, detail: str) -> AssertionError:
    return AssertionError(f"unsupported variable binding for {variable}: {detail}")


def _set_variable_binding(
    parts: tuple[_NginxArgument, ...],
) -> str | None:
    if not parts or parts[0].value != "set" or len(parts) < 2:
        return None
    variable = _unescape_nginx_word(parts[1].value)
    if variable not in REVIEWED_VARIABLE_BINDINGS:
        return None
    expected = REVIEWED_VARIABLE_BINDINGS[variable]
    if (
        len(parts) != 3
        or any(part.had_escape for part in parts)
        or parts[1].quoted
        or parts[2].value != expected
    ):
        actual = " ".join(part.value for part in parts[2:]) or "<missing>"
        raise _unsupported_variable_binding(variable, actual)
    return variable


def _map_variable_binding(statement: _NginxStatement) -> str | None:
    parts = statement.parts
    if not parts or parts[0].value != "map" or len(parts) < 3:
        return None
    variable = _unescape_nginx_word(parts[2].value)
    if variable not in REVIEWED_VARIABLE_BINDINGS:
        return None
    expected = REVIEWED_VARIABLE_BINDINGS[variable]
    valid_children = (
        statement.children is not None
        and len(statement.children) == 1
        and statement.children[0].children is None
        and tuple(part.value for part in statement.children[0].parts)
        == ("default", expected)
    )
    if (
        len(parts) != 3
        or any(part.had_escape or part.quoted for part in parts)
        or not valid_children
        or any(
            part.had_escape or part.quoted for part in statement.children[0].parts
        )
    ):
        raise _unsupported_variable_binding(variable, "non-constant map")
    return variable


def _scope_variable_bindings(
    statements: tuple[_NginxStatement, ...],
    inherited: frozenset[str],
) -> frozenset[str]:
    bindings = set(inherited)
    for statement in statements:
        variable = (
            _set_variable_binding(statement.parts)
            if statement.children is None
            else _map_variable_binding(statement)
        )
        if variable is not None:
            bindings.add(variable)
    return frozenset(bindings)


def _require_variable_binding(
    variable: str,
    bindings: frozenset[str],
    target: str,
    selector: str,
) -> None:
    if variable not in bindings:
        raise AssertionError(
            f"unsupported proxy target {target!r} in {selector}: "
            f"missing reviewed variable binding for {variable}"
        )


def _rewrite_proxy_uri(
    selector: str,
    rewrites: tuple[tuple[_NginxArgument, ...], ...],
) -> str:
    if len(rewrites) != 1:
        raise AssertionError(f"unsupported admin rewrite in {selector}")
    rewrite = rewrites[0]
    if (
        len(rewrite) != 4
        or tuple(part.value for part in rewrite[:1]) != ("rewrite",)
        or any(part.had_escape or part.quoted for part in rewrite)
        or rewrite[3].value != "break"
    ):
        raise AssertionError(f"unsupported admin rewrite in {selector}")

    _directive, pattern_part, replacement_part, _flag = rewrite
    pattern = pattern_part.value
    replacement = replacement_part.value
    if selector.startswith("= "):
        if pattern != "^" or "$" in replacement:
            raise AssertionError(f"unsupported admin rewrite in {selector}")
        return replacement

    capture = re.fullmatch(
        r"\^(?P<input_prefix>/[^()]*)\(\?<(?P<name>[A-Za-z_][A-Za-z0-9_]*)>/\.\*\)\$",
        pattern,
    )
    output = re.fullmatch(
        r"(?P<output_prefix>/[^$]*)\$(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
        replacement,
    )
    if (
        capture is None
        or output is None
        or capture.group("name") != output.group("name")
        or selector != f'^~ {capture.group("input_prefix")}/'
    ):
        raise AssertionError(f"unsupported admin rewrite in {selector}")
    return output.group("output_prefix") + "/"


def _subtree_rewrites(
    statements: tuple[_NginxStatement, ...],
) -> tuple[tuple[_NginxArgument, ...], ...]:
    rewrites: list[tuple[_NginxArgument, ...]] = []
    for statement in statements:
        _validate_nginx_directive_name(statement.parts)
        if (
            statement.children is None
            and statement.parts
            and statement.parts[0].value == "rewrite"
        ):
            rewrites.append(statement.parts)
        elif statement.children is not None:
            rewrites.extend(_subtree_rewrites(statement.children))
    return tuple(rewrites)


def _admin_rule_is_route_authorized(rule: _AdminProxyRule) -> bool:
    sensitive = {
        item["prefix"]
        for item in _manifest_source()["sensitive_prefixes"]
        if isinstance(item, dict) and isinstance(item.get("prefix"), str)
    }
    inputs = _selector_prefixes(rule.selector)
    output = rule.proxy_uri.rstrip("/") or "/"
    return (
        bool(inputs)
        and all(prefix in sensitive for prefix in inputs)
        and output == _fastapi_admin_prefix()
    )


def _collect_admin_proxy_rules(
    statements: tuple[_NginxStatement, ...],
    location: str | None = None,
    variable_bindings: frozenset[str] = frozenset(),
    location_rewrites: tuple[tuple[_NginxArgument, ...], ...] = (),
) -> list[_AdminProxyRule]:
    rules: list[_AdminProxyRule] = []
    for statement in statements:
        _validate_nginx_directive_name(statement.parts)
    variable_bindings = _scope_variable_bindings(statements, variable_bindings)
    for statement in statements:
        if statement.children is None:
            parts = statement.parts
            if (
                parts[:1]
                and parts[0].value == "proxy_pass"
                and len(parts) == 2
                and parts[1].value == REVIEWED_ADMIN_VARIABLE_PROXY_TARGET
            ):
                selector = location or "<outside location>"
                if location is None or parts[1].had_escape or parts[1].quoted:
                    raise AssertionError(
                        f"unsupported proxy target {parts[1].value!r} in {selector}"
                    )
                _require_variable_binding(
                    "$agent_upstream",
                    variable_bindings,
                    parts[1].value,
                    selector,
                )
                rule = _AdminProxyRule(
                    selector=selector,
                    rewrite=location_rewrites[0] if len(location_rewrites) == 1 else (),
                    proxy_uri=_rewrite_proxy_uri(selector, location_rewrites),
                )
                if not _admin_rule_is_route_authorized(rule):
                    raise AssertionError(f"unsupported admin rewrite in {selector}")
                rules.append(rule)
            continue

        child_location = location
        child_rewrites = location_rewrites
        if statement.parts[0].value == "location":
            if location is not None or len(statement.parts) < 2:
                raise AssertionError("invalid nested or empty Nginx location")
            child_location = " ".join(part.value for part in statement.parts[1:])
            child_rewrites = _subtree_rewrites(statement.children)
        rules.extend(
            _collect_admin_proxy_rules(
                statement.children,
                child_location,
                variable_bindings,
                child_rewrites,
            )
        )
    return rules


def _admin_proxy_rules_from_source(source: str) -> tuple[_AdminProxyRule, ...]:
    tokens = _tokenize_nginx(source)
    statements, consumed = _parse_nginx_statements(tokens)
    if consumed != len(tokens):
        raise AssertionError("Nginx parser left active tokens unconsumed")
    rules = tuple(
        sorted(_collect_admin_proxy_rules(statements), key=lambda rule: rule.selector)
    )
    if not rules or len({rule.selector for rule in rules}) != len(rules):
        raise AssertionError("reviewed admin proxy authority is ambiguous")
    return rules


def _derive_admin_proxy_authority(
    http_source: str,
    https_source: str,
) -> tuple[_AdminProxyRule, ...]:
    http_rules = _admin_proxy_rules_from_source(http_source)
    https_rules = _admin_proxy_rules_from_source(https_source)
    if http_rules != https_rules:
        raise AssertionError("reviewed admin proxy authority lacks HTTP/HTTPS parity")
    return http_rules


@functools.cache
def _reviewed_admin_proxy_authority() -> tuple[_AdminProxyRule, ...]:
    return _derive_admin_proxy_authority(
        NGINX_PATHS[0].read_text(encoding="utf-8"),
        NGINX_PATHS[1].read_text(encoding="utf-8"),
    )


def _admin_rewrite_proxy_uri(
    selector: str,
    rewrites: tuple[tuple[_NginxArgument, ...], ...],
    rule: _AdminProxyRule,
) -> str:
    if rewrites != (rule.rewrite,):
        raise AssertionError(f"unsupported admin rewrite in {selector}")
    return rule.proxy_uri


def _collect_backend_locations(
    statements: tuple[_NginxStatement, ...],
    location: str | None = None,
    variable_bindings: frozenset[str] = frozenset(),
    location_rewrites: tuple[tuple[_NginxArgument, ...], ...] = (),
    admin_authority: tuple[_AdminProxyRule, ...] = (),
    nuxt_selectors: frozenset[str] = frozenset(),
) -> list[tuple[str, str, str]]:
    locations: list[tuple[str, str, str]] = []
    for statement in statements:
        _validate_nginx_directive_name(statement.parts)
    variable_bindings = _scope_variable_bindings(statements, variable_bindings)
    for statement in statements:
        if statement.children is None:
            proxy = _backend_reference(
                statement.parts,
                location,
                variable_bindings,
                location_rewrites,
                admin_authority,
                nuxt_selectors,
            )
            if proxy is not None:
                if location is None:
                    raise AssertionError("backend proxy outside parsed location")
                locations.append((location, *proxy))
            continue
        child_location = location
        child_rewrites = location_rewrites
        child_nuxt_selectors = nuxt_selectors
        if statement.parts[0].value == "server":
            child_nuxt_selectors = _reviewed_nuxt_ingress_selectors(
                statement.children
            )
        if statement.parts[0].value == "location":
            if location is not None or len(statement.parts) < 2:
                raise AssertionError("invalid nested or empty Nginx location")
            child_location = " ".join(part.value for part in statement.parts[1:])
            child_rewrites = _subtree_rewrites(statement.children)
        locations.extend(
            _collect_backend_locations(
                statement.children,
                child_location,
                variable_bindings,
                child_rewrites,
                admin_authority,
                child_nuxt_selectors,
            )
        )
    return locations


def _backend_locations(
    source: str,
    *,
    admin_authority: tuple[_AdminProxyRule, ...] | None = None,
) -> list[tuple[str, str, str]]:
    tokens = _tokenize_nginx(source)
    statements, consumed = _parse_nginx_statements(tokens)
    if consumed != len(tokens):
        raise AssertionError("Nginx parser left active tokens unconsumed")
    authority = (
        _reviewed_admin_proxy_authority()
        if admin_authority is None
        else admin_authority
    )
    return _collect_backend_locations(
        statements,
        admin_authority=authority,
        nuxt_selectors=_reviewed_nuxt_ingress_selectors(statements),
    )


def _reviewable_backend_locations(
    locations: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    # Root SEO stays on the backend until Task 32 transfers its ingress ownership.
    return [location for location in locations if location != SEO_TRANSITION_LOCATION]


def _assert_backend_ingress_reviewed(
    locations: list[tuple[str, str, str]],
) -> None:
    manifest = load_route_manifest()
    sensitive = {item["prefix"] for item in manifest.data["sensitive_prefixes"]}
    exceptions = {
        (item["prefix"], item["upstream"])
        for item in manifest.data["backend_ingress_exceptions"]
    }
    for selector, nginx_upstream, _proxy_uri in _reviewable_backend_locations(
        locations
    ):
        upstream = UPSTREAM_OWNERS[nginx_upstream]
        for prefix in _selector_prefixes(selector):
            if prefix in sensitive:
                continue
            assert (prefix, upstream) in exceptions, (
                f"unreviewed backend ingress: {prefix} "
                f"upstream ownership -> {upstream} ({selector})"
            )


def _proxy_target(
    location: tuple[str, str, str],
    request_path: str,
) -> tuple[str, str]:
    selector, upstream, proxy_uri = location
    assert _selector_matches(selector, request_path)
    if proxy_uri == "":
        return upstream, request_path
    if selector.startswith("= "):
        return upstream, proxy_uri
    if selector.startswith("^~ "):
        location_prefix = selector[3:]
        return upstream, proxy_uri + request_path[len(location_prefix) :]
    raise AssertionError(f"URI-bearing regex proxy is unsupported: {selector}")


def _selector_matches(selector: str, path: str) -> bool:
    if selector.startswith("~ "):
        return re.search(selector[2:], path) is not None
    if selector.startswith("= "):
        return path == selector[2:]
    if selector.startswith("^~ "):
        return path.startswith(selector[3:])
    raise AssertionError(
        f"backend selector lacks explicit boundary semantics: {selector}"
    )


def _selector_prefixes(selector: str) -> tuple[str, ...]:
    if selector.startswith("= "):
        return (selector[2:],)
    if selector.startswith("^~ "):
        return (selector[3:].rstrip("/"),)

    single = re.fullmatch(r"~ \^/([a-z0-9-]+)\(\?:/\|\$\)", selector)
    if single:
        return (f"/{single.group(1)}",)
    grouped = re.fullmatch(r"~ \^/\(([-a-z0-9|]+)\)\(\?:/\|\$\)", selector)
    if grouped:
        return tuple(f"/{part}" for part in grouped.group(1).split("|"))
    raise AssertionError(f"unsupported backend ingress selector: {selector}")


def _location_selectors(
    statements: tuple[_NginxStatement, ...],
    inside_location: bool = False,
) -> tuple[str, ...]:
    selectors: list[str] = []
    for statement in statements:
        _validate_nginx_directive_name(statement.parts)
        if statement.children is None:
            continue
        child_inside_location = inside_location
        if statement.parts[0].value == "location":
            if inside_location or len(statement.parts) < 2:
                raise AssertionError("invalid nested or empty Nginx location")
            selectors.append(" ".join(part.value for part in statement.parts[1:]))
            child_inside_location = True
        selectors.extend(
            _location_selectors(statement.children, child_inside_location)
        )
    return tuple(selectors)


def _required_direct_ingress_prefixes() -> frozenset[str]:
    manifest = _manifest_source()
    sensitive = {
        item["prefix"]
        for item in manifest["sensitive_prefixes"]
        if isinstance(item, dict) and isinstance(item.get("prefix"), str)
    }
    backend_exceptions = {
        item["prefix"]
        for item in manifest["backend_ingress_exceptions"]
        if isinstance(item, dict) and isinstance(item.get("prefix"), str)
    }
    catchall_frontend = set(REVIEWED_NUXT_CATCHALL_SENSITIVE_PREFIXES)
    catchall_frontend.add(_fastapi_admin_prefix())
    if not catchall_frontend.issubset(sensitive):
        raise AssertionError("reviewed Nuxt catch-all authority is stale")
    return frozenset((sensitive - catchall_frontend) | backend_exceptions)


def _fully_covered_location_prefixes(selectors: tuple[str, ...]) -> frozenset[str]:
    exact = {selector[2:] for selector in selectors if selector.startswith("= ")}
    subtree = {
        selector[3:-1]
        for selector in selectors
        if selector.startswith("^~ /") and selector.endswith("/")
    }
    covered = exact & subtree
    for selector in selectors:
        single = re.fullmatch(r"~ \^/([a-z0-9-]+)\(\?:/\|\$\)", selector)
        if single:
            covered.add(f"/{single.group(1)}")
            continue
        grouped = re.fullmatch(
            r"~ \^/\(([-a-z0-9|]+)\)\(\?:/\|\$\)", selector
        )
        if grouped:
            covered.update(f"/{part}" for part in grouped.group(1).split("|"))
    return frozenset(covered)


def _reviewed_nuxt_ingress_selectors(
    statements: tuple[_NginxStatement, ...],
) -> frozenset[str]:
    selectors = _location_selectors(statements)
    reviewed = set(REVIEWED_NUXT_EXACT_SELECTORS)
    if _required_direct_ingress_prefixes().issubset(
        _fully_covered_location_prefixes(selectors)
    ):
        reviewed.add("/")
    return frozenset(reviewed)


def _require_reviewed_nuxt_selector(
    selector: str,
    reviewed_selectors: frozenset[str],
) -> None:
    if selector not in reviewed_selectors:
        raise AssertionError(f"unsupported Nuxt ingress selector: {selector}")


def _matches_any_selector(selectors: list[str], path: str) -> bool:
    return any(_selector_matches(selector, path) for selector in selectors)


def _subprocess_text(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _typescript_sentinel_payload(stdout: bytes) -> bytes:
    sentinel = TYPESCRIPT_OUTPUT_SENTINEL.encode()
    if stdout.count(sentinel) != 1:
        raise AssertionError(
            "TypeScript parity runner must emit exactly one sentinel payload"
        )

    sentinel_index = stdout.index(sentinel)
    if sentinel_index != 0 and stdout[sentinel_index - 1 : sentinel_index] != b"\n":
        raise AssertionError(
            "TypeScript parity runner sentinel payload must start a line"
        )

    payload_start = sentinel_index + len(sentinel)
    payload_end = stdout.find(b"\n", payload_start)
    if payload_end == -1:
        payload_end = len(stdout)
    payload = stdout[payload_start:payload_end]
    if payload.endswith(b"\r"):
        payload = payload[:-1]

    try:
        json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AssertionError(
            "TypeScript parity runner sentinel payload is not valid JSON"
        ) from error
    return payload


def _run_typescript_parity_runner(runner: Path) -> bytes:
    node = shutil.which("node")
    if node is None:
        raise AssertionError("Node.js is required for cross-runtime route parity")
    command = [
        node,
        str(WEB_ROOT / "node_modules" / "vite-node" / "dist" / "cli.mjs"),
        "--config",
        "vitest.config.ts",
        str(runner),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=WEB_ROOT,
            capture_output=True,
            check=False,
            timeout=TYPESCRIPT_RUNNER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"TypeScript parity runner timed out after "
            f"{TYPESCRIPT_RUNNER_TIMEOUT_SECONDS}s; "
            f"stdout={_subprocess_text(error.output)!r}; "
            f"stderr={_subprocess_text(error.stderr)!r}"
        ) from error
    if result.returncode != 0:
        raise AssertionError(_subprocess_text(result.stderr))
    return _typescript_sentinel_payload(result.stdout)


def test_shared_validator_corpus_accepts_canonical_templates_and_matches_errors():
    parsed = validate_route_manifest_data(_manifest_source())
    assert [item["template"] for item in parsed["dynamic_templates"]] == [
        "/dia-diem/{entity_id}",
        "/xa-phuong/{ward_id}",
        "/bai-viet/{id}",
        "/nguoi-dung/{id}",
        "/lich-trinh/{id}",
        "/lich-trinh-chia-se/{id}",
    ]

    for mutation in VALIDATOR_CORPUS:
        candidate = _manifest_source()
        _apply_mutation(candidate, mutation)
        expected_error = mutation["error"]
        if expected_error is None:
            validate_route_manifest_data(candidate)
        else:
            with pytest.raises(ValueError, match=re.escape(str(expected_error))):
                validate_route_manifest_data(candidate)


def test_shared_route_corpus_has_reviewed_shape():
    _validate_route_corpus_shape()


def test_shared_route_corpus_matches_python_classifier(tmp_path):

    for row in ROUTE_CORPUS:
        manifest = _route_manifest_for_row(row, tmp_path)
        decision = classify_request_target(
            row["target"], manifest, method=row["method"]
        )
        assert decision.classification == row["classification"], row
        assert decision.canonical_path == row["canonical"], row
        expected_sitemap_paths = row.get("variant", {}).get("static_sitemap_paths")
        if expected_sitemap_paths:
            actual = extract_static_sitemap_paths(manifest)
            assert [
                path for path in actual if path in expected_sitemap_paths
            ] == expected_sitemap_paths


def test_static_sitemap_paths_are_exact_manifest_inventory():
    assert extract_static_sitemap_paths(load_route_manifest()) == STATIC_SITEMAP_PATHS


@pytest.mark.parametrize(
    "second_assignment",
    [
        "router = build_admin_router()",
        "router: APIRouter = build_admin_router()",
    ],
)
def test_fastapi_admin_prefix_rejects_any_second_top_level_router_assignment(
    monkeypatch, tmp_path, second_assignment
):
    admin_path = tmp_path / "admin.py"
    admin_path.write_text(
        'router = APIRouter(prefix="/admin")\n' + second_assignment,
        encoding="utf-8",
    )
    monkeypatch.setitem(globals(), "ADMIN_PATH", admin_path)
    _fastapi_admin_prefix.cache_clear()

    try:
        with pytest.raises(AssertionError, match="authority is ambiguous"):
            _fastapi_admin_prefix()
    finally:
        _fastapi_admin_prefix.cache_clear()


def test_typescript_serialization_matches_python_byte_for_byte(tmp_path):
    module_url = (
        WEB_ROOT / "server" / "utils" / "launch" / "launchRouteManifest.ts"
    ).as_uri()
    runner = tmp_path / "route-parity-runner.ts"
    runner.write_text(
        f"""
import {{ readFileSync }} from 'node:fs'
import {{
  classifyRequestTarget,
  extractStaticSitemapPaths,
  parseLaunchRouteManifest,
}} from {json.dumps(module_url)}

const manifestSource = JSON.parse(readFileSync({json.dumps(str(MANIFEST_PATH))}, 'utf8'))
const routeCorpus = JSON.parse(readFileSync({json.dumps(str(ROUTE_CORPUS_PATH))}, 'utf8'))
const validatorCorpus = JSON.parse(readFileSync({json.dumps(str(VALIDATOR_CORPUS_PATH))}, 'utf8'))

function pointerParent(document, pointer) {{
  const parts = pointer.slice(1).split('/').map(part => part.replaceAll('~1', '/').replaceAll('~0', '~'))
  let current = document
  for (const part of parts.slice(0, -1)) current = Array.isArray(current) ? current[Number(part)] : current[part]
  return [current, parts.at(-1)]
}}

function applyMutation(document, mutation) {{
  const [parent, key] = pointerParent(document, mutation.pointer)
  if (mutation.operation === 'append') parent[key].push(structuredClone(mutation.value))
  else throw new Error(`unsupported runner mutation: ${{mutation.operation}}`)
}}

const manifest = parseLaunchRouteManifest(manifestSource)
const ingressCandidate = structuredClone(manifestSource)
for (const mutation of validatorCorpus) {{
  if (mutation.name.startsWith('accepted-ingress-') || mutation.name === 'accepted-nel-ingress-review') {{
    applyMutation(ingressCandidate, mutation)
  }}
}}
const ingressManifest = parseLaunchRouteManifest(ingressCandidate)
const output = {{
  decisions: routeCorpus.map(row => {{
    const candidate = structuredClone(manifestSource)
    for (const mutation of row.variant?.mutations ?? []) applyMutation(candidate, mutation)
    const rowManifest = parseLaunchRouteManifest(candidate)
    const decision = classifyRequestTarget(row.target, rowManifest, row.method)
    return {{
      variant: row.variant?.name ?? null,
      manifest: row.variant ? rowManifest : null,
      static_sitemap_paths: row.variant?.static_sitemap_paths ? extractStaticSitemapPaths(rowManifest) : null,
      ...decision,
    }}
  }}),
  static_sitemap_paths: extractStaticSitemapPaths(manifest),
  ingress_exceptions: ingressManifest.backend_ingress_exceptions,
}}
process.stdout.write({json.dumps(TYPESCRIPT_OUTPUT_SENTINEL)} + JSON.stringify(output) + '\\n')
""".strip(),
        encoding="utf-8",
    )

    typescript_output = _run_typescript_parity_runner(runner)

    manifest = load_route_manifest()
    ingress = validate_route_manifest_data(_accepted_ingress_manifest())
    python_output = {
        "decisions": [
            {
                "variant": row.get("variant", {}).get("name"),
                "manifest": (
                    _plain_json(row_manifest.data) if row.get("variant") else None
                ),
                "static_sitemap_paths": (
                    list(extract_static_sitemap_paths(row_manifest))
                    if row.get("variant", {}).get("static_sitemap_paths")
                    else None
                ),
                "classification": decision.classification,
                "canonical_path": decision.canonical_path,
            }
            for row in ROUTE_CORPUS
            for row_manifest in [_route_manifest_for_row(row, tmp_path)]
            for decision in [
                classify_request_target(
                    row["target"], row_manifest, method=row["method"]
                )
            ]
        ],
        "static_sitemap_paths": list(extract_static_sitemap_paths(manifest)),
        "ingress_exceptions": _plain_json(ingress["backend_ingress_exceptions"]),
    }
    expected = json.dumps(
        python_output,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    if typescript_output != expected:
        actual_json = json.loads(typescript_output)
        for index, (actual_decision, expected_decision) in enumerate(
            zip(actual_json["decisions"], python_output["decisions"], strict=True)
        ):
            assert actual_decision == expected_decision, (
                f"route corpus decision {index} differs: {ROUTE_CORPUS[index]!r}"
            )
        assert actual_json == python_output
    assert typescript_output == expected
    assert python_output["ingress_exceptions"] == [
        {"prefix": "/hook", "upstream": "agent", "review_reason": "reviewed callback"},
        {"prefix": "/nel-hook", "upstream": "bot-gateway", "review_reason": "\u0085"},
    ]


def _nginx_location_pair() -> tuple[
    list[tuple[str, str, str]], list[tuple[str, str, str]]
]:
    http_locations = _backend_locations(NGINX_PATHS[0].read_text(encoding="utf-8"))
    https_locations = _backend_locations(NGINX_PATHS[1].read_text(encoding="utf-8"))
    return http_locations, https_locations


def test_nginx_backend_locations_have_http_https_parity():
    http_locations, https_locations = _nginx_location_pair()

    assert http_locations == https_locations
    assert http_locations


def test_nginx_admin_api_preserves_proxy_uri_rewrite_semantics():
    http_locations, _https_locations = _nginx_location_pair()
    by_selector = {location[0]: location for location in http_locations}
    admin_prefix = _fastapi_admin_prefix()

    assert _proxy_target(by_selector["= /admin-api"], "/admin-api") == (
        "vl360_agent",
        admin_prefix,
    )
    assert _proxy_target(by_selector["^~ /admin-api/"], "/admin-api/users") == (
        "vl360_agent",
        f"{admin_prefix}/users",
    )


def test_nginx_regex_ingress_preserves_original_request_uri():
    http_locations, _https_locations = _nginx_location_pair()
    regex_locations = [
        location for location in http_locations if location[0].startswith("~ ")
    ]

    assert regex_locations
    assert all(proxy_uri == "" for _selector, _upstream, proxy_uri in regex_locations)


def test_nginx_backend_location_parser_detects_proxy_uri_drift():
    source = NGINX_PATHS[0].read_text(encoding="utf-8")
    drifted = source.replace(
        "proxy_pass $agent_upstream$uri$is_args$args;",
        "proxy_pass $agent_upstream$request_uri;",
        1,
    )

    assert _backend_locations(source) != _backend_locations(drifted)


def test_nginx_scanner_concatenates_adjacent_quoted_directive_fragments():
    source = '''
location ~ ^/private(?:/|$) {
    proxy"_pass" http://vl360_agent;
}
'''

    assert _backend_locations(source) == [
        ("~ ^/private(?:/|$)", "vl360_agent", "")
    ]


def test_nginx_scanner_rejects_escaped_reviewed_variable_override():
    source = r'''
server {
    set $agent_upstream http://agent:8360;
    location ~ ^/private(?:/|$) {
        if ($request_method = POST) {
            set $agent\_upstream http://evil.example;
        }
        proxy_pass $agent_upstream$request_uri;
    }
}
'''

    with pytest.raises(AssertionError, match="unsupported variable binding"):
        _backend_locations(source)


@pytest.mark.parametrize("nested_position", ["before", "after"])
def test_nginx_scanner_rejects_nested_admin_rewrite(nested_position):
    nested = "if ($request_method = POST) { rewrite ^ /evil break; }"
    reviewed = f"rewrite ^ {_fastapi_admin_prefix()} break;"
    rewrites = (
        f"{nested}\n        {reviewed}"
        if nested_position == "before"
        else f"{reviewed}\n        {nested}"
    )
    source = f'''
server {{
    set $agent_upstream http://agent:8360;
    location = /admin-api {{
        {rewrites}
        proxy_pass $agent_upstream$uri$is_args$args;
    }}
}}
'''

    with pytest.raises(AssertionError, match="unsupported admin rewrite"):
        _backend_locations(source)


def test_nginx_scanner_uses_immutable_reviewed_admin_authority():
    http_source = NGINX_PATHS[0].read_text(encoding="utf-8")
    https_source = NGINX_PATHS[1].read_text(encoding="utf-8")
    authority = _derive_admin_proxy_authority(http_source, https_source)
    admin_prefix = _fastapi_admin_prefix()
    drifted = http_source.replace(
        f"rewrite ^ {admin_prefix} break;",
        f"rewrite ^ {admin_prefix}-broken break;",
        1,
    )

    assert _backend_locations(http_source, admin_authority=authority)
    with pytest.raises(AssertionError, match="unsupported admin rewrite"):
        _backend_locations(drifted, admin_authority=authority)


def test_nginx_scanner_rejects_synchronized_admin_rewrite_authority_drift():
    http_source = NGINX_PATHS[0].read_text(encoding="utf-8")
    https_source = NGINX_PATHS[1].read_text(encoding="utf-8")
    current_prefix = _fastapi_admin_prefix()

    def drift(source: str) -> str:
        return source.replace(
            f"rewrite ^ {current_prefix} break;",
            "rewrite ^ /auth break;",
            1,
        ).replace(
            f"$ {current_prefix}$admin_rest break;",
            "$ /auth$admin_rest break;",
            1,
        )

    with pytest.raises(AssertionError, match="unsupported admin rewrite"):
        _derive_admin_proxy_authority(drift(http_source), drift(https_source))


@pytest.mark.parametrize(
    ("binding", "selector", "target", "expected"),
    [
        (
            "set $agent_upstream http://agent:8360;",
            "~ ^/private(?:/|$)",
            "$agent_upstream$request_uri",
            [("~ ^/private(?:/|$)", "vl360_agent", "")],
        ),
        (
            "set $bot_upstream http://bot-gateway:8361;",
            "~ ^/private(?:/|$)",
            "$bot_upstream$request_uri",
            [("~ ^/private(?:/|$)", "vl360_bots", "")],
        ),
        (
            "set $nuxt_upstream http://nuxt:3000;",
            "= /robots.txt",
            "$nuxt_upstream$request_uri",
            [],
        ),
    ],
)
def test_nginx_scanner_accepts_only_reviewed_variable_proxy_targets(
    binding, selector, target, expected
):
    source = f"""
server {{
    {binding}
    location {selector} {{
        proxy_pass {target};
    }}
}}
"""

    assert _backend_locations(source) == expected


@pytest.mark.parametrize(
    ("binding", "target"),
    [
        ("", "http://vl360_nuxt"),
        (
            "set $nuxt_upstream http://nuxt:3000;",
            "$nuxt_upstream$request_uri",
        ),
    ],
)
@pytest.mark.parametrize(
    "prefix", ["/api", "/auth", "/chat", _fastapi_admin_prefix()]
)
def test_nginx_scanner_rejects_sensitive_nuxt_ingress(binding, target, prefix):
    source = f"""
server {{
    {binding}
    location = {prefix} {{
        proxy_pass {target};
    }}
}}
"""

    with pytest.raises(AssertionError, match="unsupported Nuxt ingress selector"):
        _backend_locations(source)


def test_nginx_scanner_rejects_unparseable_nuxt_ingress_selector():
    source = r"""
location ~ ^/(api|auth) {
    proxy_pass http://vl360_nuxt;
}
"""

    with pytest.raises(AssertionError, match="unsupported Nuxt ingress selector"):
        _backend_locations(source)


def test_nginx_scanner_rejects_default_nuxt_without_complete_sensitive_ingress():
    source = """
location / {
    proxy_pass http://vl360_nuxt;
}
"""

    with pytest.raises(AssertionError, match="unsupported Nuxt ingress selector"):
        _backend_locations(source)


def test_nginx_scanner_does_not_borrow_nuxt_coverage_from_another_server():
    source = """
server {
    location / {
        proxy_pass http://vl360_nuxt;
    }
}
""" + NGINX_PATHS[0].read_text(encoding="utf-8")

    with pytest.raises(AssertionError, match="unsupported Nuxt ingress selector"):
        _backend_locations(source)


def test_nginx_scanner_exact_locations_do_not_prove_descendant_coverage():
    exact_locations = "\n".join(
        f"location = {prefix} {{ return 404; }}"
        for prefix in sorted(_required_direct_ingress_prefixes())
    )
    source = f"""
server {{
    {exact_locations}
    location / {{
        proxy_pass http://vl360_nuxt;
    }}
}}
"""

    with pytest.raises(AssertionError, match="unsupported Nuxt ingress selector"):
        _backend_locations(source)


def test_nginx_scanner_rejects_reviewed_variable_with_unaudited_binding():
    source = """
server {
    set $agent_upstream http://evil.example;
    location ~ ^/private(?:/|$) {
        proxy_pass $agent_upstream$request_uri;
    }
}
"""

    with pytest.raises(AssertionError, match="unsupported variable binding"):
        _backend_locations(source)


@pytest.mark.parametrize(
    ("selector", "rewrite"),
    [
        (
            "= /admin-api",
            f"rewrite ^ {_fastapi_admin_prefix()}-broken break;",
        ),
        (
            "^~ /admin-api/",
            "rewrite ^/admin-api(?<admin_rest>/.*)$ /broken$admin_rest break;",
        ),
    ],
)
def test_nginx_scanner_rejects_admin_variable_proxy_with_rewrite_drift(
    selector, rewrite
):
    source = f"""
server {{
    set $agent_upstream http://agent:8360;
    location {selector} {{
        {rewrite}
        proxy_pass $agent_upstream$uri$is_args$args;
    }}
}}
"""

    with pytest.raises(AssertionError, match="unsupported admin rewrite"):
        _backend_locations(source)


def test_nginx_scanner_rejects_escaped_policy_directive_name():
    source = r"""
location ~ ^/private(?:/|$) {
    proxy\_pass http://vl360_agent;
}
"""

    with pytest.raises(AssertionError, match="escaped Nginx directive"):
        _backend_locations(source)


@pytest.mark.parametrize(
    "source",
    [
        """
location ~ ^/private(?:/|$) {
    if ($request_method = POST) {
        set $private_request 1;
    }
    proxy_pass http://vl360_agent;
}
""",
        """
location ~ ^/private(?:/|$) {
    # Braces in a comment must not hide this active backend location: {}
    proxy_pass http://vl360_agent;
}
""",
        """
location ~ ^/private(?:/|$) {
    set $quoted "{ # quoted syntax is inert }";
    proxy_pass http://vl360_agent;
}
""",
    ],
)
def test_nginx_scanner_keeps_nested_and_comment_brace_locations(source):
    with pytest.raises(AssertionError, match="unreviewed backend ingress: /private"):
        _assert_backend_ingress_reviewed(_backend_locations(source))


@pytest.mark.parametrize(
    "source",
    [
        """
# location ~ ^/private(?:/|$) {
#     proxy_pass http://vl360_agent;
# }
""",
        """
location /public {
    # proxy_pass http://vl360_agent;
    return 204;
}
""",
    ],
)
def test_nginx_scanner_ignores_commented_backend_directives(source):
    assert _backend_locations(source) == []


def test_nginx_scanner_rejects_backend_proxy_outside_location():
    source = """
server {
    proxy_pass http://vl360_agent;
}
"""

    with pytest.raises(AssertionError, match="backend proxy outside parsed location"):
        _backend_locations(source)


@pytest.mark.parametrize(
    "target",
    [
        "http://$backend",
        "http://unknown_upstream",
        "http://vl360_agent$uri",
        "http://vl360_agent/$uri",
        "$agent_upstream$unknown",
        "$agent_upstream$uri$is_args$args",
        "$nuxt_upstream$request_uri",
    ],
)
def test_nginx_scanner_rejects_unresolved_or_unknown_proxy_target(target):
    source = f"""
location ~ ^/private(?:/|$) {{
    set $backend vl360_agent;
    proxy_pass {target};
}}
"""

    with pytest.raises(
        AssertionError,
        match=rf"unsupported proxy target.*{re.escape(target)}.*private",
    ):
        _backend_locations(source)


@pytest.mark.parametrize(
    "target",
    [
        r"http://vl360_\agent",
        r"http://vl360_\nuxt",
        r"http://vl360_\tagent",
        r"http://vl360_\ragent",
        r"http://vl360_\nagent",
        r"http://vl360_\"agent",
        r"http://vl360_\\agent",
    ],
)
@pytest.mark.parametrize("quoted", [False, True])
def test_nginx_scanner_rejects_escaped_proxy_target(target, quoted):
    proxy_target = f'"{target}"' if quoted else target
    source = f"""
location ~ ^/private(?:/|$) {{
    proxy_pass {proxy_target};
}}
"""

    with pytest.raises(AssertionError, match=r"escaped proxy target.*private"):
        _backend_locations(source)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (
            f"http://vl360_agent{_fastapi_admin_prefix()}",
            [("/", "vl360_agent", _fastapi_admin_prefix())],
        ),
        (
            f'"http://vl360_agent{_fastapi_admin_prefix()}"',
            [("/", "vl360_agent", _fastapi_admin_prefix())],
        ),
        ("http://vl360_bots/hook", [("/", "vl360_bots", "/hook")]),
        ('"http://vl360_bots/hook"', [("/", "vl360_bots", "/hook")]),
    ],
)
def test_nginx_scanner_allows_plain_literal_proxy_targets(target, expected):
    source = f"""
location / {{
    proxy_pass {target};
}}
"""

    assert _backend_locations(source) == expected


@pytest.mark.parametrize("quoted", [False, True])
def test_nginx_scanner_rejects_nuxt_proxy_uri(quoted):
    target = "http://vl360_nuxt/app"
    proxy_target = f'"{target}"' if quoted else target
    source = f"""
location = /robots.txt {{
    proxy_pass {proxy_target};
}}
"""

    with pytest.raises(AssertionError, match="unsupported proxy target"):
        _backend_locations(source)


@pytest.mark.parametrize(
    "exception_upstream, nginx_upstream",
    [("agent", "vl360_bots"), ("bot-gateway", "vl360_agent")],
)
def test_ingress_exception_does_not_approve_wrong_upstream(
    monkeypatch,
    exception_upstream,
    nginx_upstream,
):
    candidate = _manifest_source()
    candidate["backend_ingress_exceptions"] = [
        {
            "prefix": "/hook",
            "upstream": exception_upstream,
            "review_reason": "reviewed ownership",
        }
    ]
    parsed = validate_route_manifest_data(candidate)

    class ManifestStub:
        data = parsed

    monkeypatch.setattr(sys.modules[__name__], "load_route_manifest", ManifestStub)
    locations = [("~ ^/hook(?:/|$)", nginx_upstream, "")]

    with pytest.raises(AssertionError, match="upstream ownership"):
        _assert_backend_ingress_reviewed(locations)
    matching_upstream = next(
        name for name, owner in UPSTREAM_OWNERS.items() if owner == exception_upstream
    )
    _assert_backend_ingress_reviewed([("~ ^/hook(?:/|$)", matching_upstream, "")])


def test_sensitive_ingress_allows_either_reviewed_backend_upstream():
    _assert_backend_ingress_reviewed([("~ ^/api(?:/|$)", "vl360_bots", "")])


def test_typescript_runner_timeout_is_actionable(monkeypatch, tmp_path):
    def expire(*_args, **kwargs):
        assert kwargs["timeout"] == 120
        raise subprocess.TimeoutExpired(
            cmd="vite-node",
            timeout=120,
            output=b"partial stdout",
            stderr=b"partial stderr",
        )

    monkeypatch.setattr(subprocess, "run", expire)

    with pytest.raises(AssertionError, match="timed out after 120s.*partial stderr"):
        _run_typescript_parity_runner(tmp_path / "runner.ts")


def test_typescript_runner_extracts_one_sentinel_payload_after_logs(monkeypatch):
    class Completed:
        returncode = 0
        stdout = (
            b"vite v6 ready\n"
            + TYPESCRIPT_OUTPUT_SENTINEL.encode()
            + b'{"ok":true}\n'
            + b"vite cleanup complete\n"
        )
        stderr = b""

    monkeypatch.setattr(shutil, "which", lambda _name: "node")
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: Completed())

    assert _run_typescript_parity_runner(Path("runner.ts")) == b'{"ok":true}'


def test_typescript_runner_rejects_duplicate_sentinel_payloads(monkeypatch):
    sentinel = TYPESCRIPT_OUTPUT_SENTINEL.encode()

    class Completed:
        returncode = 0
        stdout = sentinel + b"{}\n" + sentinel + b"{}\n"
        stderr = b""

    monkeypatch.setattr(shutil, "which", lambda _name: "node")
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: Completed())

    with pytest.raises(AssertionError, match="exactly one sentinel payload"):
        _run_typescript_parity_runner(Path("runner.ts"))


@pytest.mark.parametrize(
    "stdout",
    [
        b'{"ok":true}',
        b"vite " + TYPESCRIPT_OUTPUT_SENTINEL.encode() + b'{}\n',
        TYPESCRIPT_OUTPUT_SENTINEL.encode() + b"\n",
        TYPESCRIPT_OUTPUT_SENTINEL.encode() + b"not-json\n",
    ],
)
def test_typescript_runner_rejects_missing_or_malformed_sentinel(
    monkeypatch, stdout
):
    class Completed:
        returncode = 0
        stderr = b""

    Completed.stdout = stdout
    monkeypatch.setattr(shutil, "which", lambda _name: "node")
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: Completed())

    with pytest.raises(AssertionError, match="sentinel"):
        _run_typescript_parity_runner(Path("runner.ts"))


def test_nginx_backend_locations_have_explicit_boundaries():
    http_locations, _https_locations = _nginx_location_pair()

    for selector, _upstream, _proxy_uri in http_locations:
        if selector.startswith("~ "):
            assert selector.endswith("(?:/|$)") or selector.endswith("$")
        else:
            assert selector.startswith("= ") or (
                selector.startswith("^~ ") and selector.endswith("/")
            )


def test_nginx_backend_ingress_is_reviewed_by_segment_prefix():
    http_locations, _https_locations = _nginx_location_pair()
    _assert_backend_ingress_reviewed(http_locations)


def test_nginx_private_sitemap_is_not_transition_exempt():
    source = """
location ~ ^/private-sitemap(?:/|$) {
    proxy_pass http://vl360_agent;
}
"""
    locations = _backend_locations(source)

    with pytest.raises(
        AssertionError, match="unreviewed backend ingress: /private-sitemap"
    ):
        _assert_backend_ingress_reviewed(locations)


def test_nginx_backend_boundaries_exclude_lookalike_public_paths():
    http_locations, _https_locations = _nginx_location_pair()
    ingress_locations = _reviewable_backend_locations(http_locations)
    selectors = [selector for selector, _upstream, _proxy_uri in ingress_locations]
    assert _matches_any_selector(selectors, "/api")
    assert _matches_any_selector(selectors, "/api/entities")
    assert not _matches_any_selector(selectors, "/apiary")
    assert _matches_any_selector(selectors, "/webhook")
    assert not _matches_any_selector(selectors, "/webhooks")
