from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
INTERNAL_PREFIX = "/_internal/"
INTERNAL_PATHS = (
    "/_internal/launch-policy-attestation",
    "/_internal/launch-policy-attestation/child",
    "/_internal/launch-readiness",
    "/_internal/launch-sitemaps/sitemap-index.xml",
    "/_internal/launch-sitemaps/sitemap.xml",
    "/_internal/launch-sitemaps/sitemap-media.xml",
)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int


@dataclass(frozen=True)
class Statement:
    parts: tuple[str, ...]
    children: tuple["Statement", ...] | None
    start: int


@dataclass(frozen=True)
class Location:
    modifier: str
    pattern: str
    body: tuple[Statement, ...]
    start: int


def _tokenize_nginx(source: str) -> list[Token]:
    tokens: list[Token] = []
    buffer: list[str] = []
    buffer_start = 0

    def flush() -> None:
        if buffer:
            tokens.append(Token("word", "".join(buffer), buffer_start))
            buffer.clear()

    index = 0
    while index < len(source):
        character = source[index]
        if character == "\\":
            if not buffer:
                buffer_start = index
            buffer.append(character)
            if index + 1 < len(source):
                index += 1
                buffer.append(source[index])
        elif character.isspace():
            flush()
        elif character == "#":
            flush()
            newline = source.find("\n", index)
            index = len(source) if newline == -1 else newline
            continue
        elif character in {'"', "'"}:
            flush()
            quote = character
            quoted_start = index
            value: list[str] = []
            index += 1
            while index < len(source) and source[index] != quote:
                if source[index] == "\\" and index + 1 < len(source):
                    value.extend((source[index], source[index + 1]))
                    index += 2
                    continue
                value.append(source[index])
                index += 1
            if index >= len(source):
                raise AssertionError("unterminated quoted Nginx token")
            tokens.append(Token("quoted", "".join(value), quoted_start))
        elif character in "{};":
            flush()
            tokens.append(Token("symbol", character, index))
        else:
            if not buffer:
                buffer_start = index
            buffer.append(character)
        index += 1
    flush()
    return tokens


def _parse_statements(
    tokens: list[Token],
    index: int = 0,
    *,
    expect_close: bool = False,
) -> tuple[tuple[Statement, ...], int]:
    statements: list[Statement] = []
    parts: list[Token] = []
    while index < len(tokens):
        token = tokens[index]
        if token.kind in {"word", "quoted"}:
            parts.append(token)
        elif token.value == ";":
            if not parts:
                raise AssertionError("empty Nginx directive")
            statements.append(
                Statement(tuple(part.value for part in parts), None, parts[0].start)
            )
            parts.clear()
        elif token.value == "{":
            if not parts:
                raise AssertionError("Nginx block is missing a header")
            children, index = _parse_statements(tokens, index + 1, expect_close=True)
            statements.append(
                Statement(tuple(part.value for part in parts), children, parts[0].start)
            )
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


def _parse_nginx(source: str) -> tuple[Statement, ...]:
    tokens = _tokenize_nginx(source)
    statements, consumed = _parse_statements(tokens)
    if consumed != len(tokens):
        raise AssertionError("Nginx parser left active tokens unconsumed")
    return statements


def _public_servers_from_source(source: str) -> list[Statement]:
    public_names = {"vinhlong360.vn", "www.vinhlong360.vn"}
    public: list[Statement] = []
    for statement in _parse_nginx(source):
        if statement.parts != ("server",) or statement.children is None:
            continue
        names = {
            name
            for child in statement.children
            if child.children is None and child.parts[:1] == ("server_name",)
            for name in child.parts[1:]
        }
        if names & public_names:
            public.append(statement)
    return public


def _public_servers(path: Path) -> list[Statement]:
    return _public_servers_from_source(path.read_text(encoding="utf-8"))


def _locations(server: Statement) -> list[Location]:
    assert server.children is not None
    locations = []
    for statement in server.children:
        if statement.parts[:1] != ("location",) or statement.children is None:
            continue
        parts = statement.parts[1:]
        if parts and parts[0] in {"=", "~", "~*", "^~"}:
            modifier = parts[0]
            pattern = " ".join(parts[1:])
        else:
            modifier = ""
            pattern = " ".join(parts)
        locations.append(Location(modifier, pattern, statement.children, statement.start))
    return locations


def _resolve_location(locations: list[Location], request_path: str) -> Location | None:
    for location in locations:
        if location.modifier == "=" and request_path == location.pattern:
            return location

    prefixes = [
        location
        for location in locations
        if location.modifier in {"", "^~"} and request_path.startswith(location.pattern)
    ]
    prefix = max(prefixes, key=lambda item: len(item.pattern), default=None)
    if prefix is not None and prefix.modifier == "^~":
        return prefix

    for location in locations:
        if location.modifier in {"~", "~*"}:
            flags = re.IGNORECASE if location.modifier == "~*" else 0
            if re.search(location.pattern, request_path, flags):
                return location
    return prefix


def _active_directives(body: tuple[Statement, ...]) -> list[str]:
    return [
        " ".join(statement.parts) + (" {...}" if statement.children is not None else "")
        for statement in body
    ]


def _literal_prefixes(
    tokens: list[tuple[object, object]],
) -> tuple[set[str], bool]:
    prefixes = {""}
    for operation, argument in tokens:
        if operation == re._constants.LITERAL:
            pieces = {chr(argument)}
            complete = True
        elif operation == re._constants.IN:
            pieces = {
                chr(value)
                for item_operation, value in argument
                if item_operation == re._constants.LITERAL
            }
            complete = len(pieces) == len(argument)
        elif operation == re._constants.SUBPATTERN:
            pieces, complete = _literal_prefixes(list(argument[-1]))
        elif operation == re._constants.BRANCH:
            branch_results = [
                _literal_prefixes(list(branch)) for branch in argument[1]
            ]
            pieces = {
                prefix
                for branch_prefixes, _complete in branch_results
                for prefix in branch_prefixes
            }
            complete = all(result_complete for _prefixes, result_complete in branch_results)
        else:
            return prefixes, False

        prefixes = {
            prefix + piece
            for prefix in prefixes
            for piece in pieces
        }
        if not complete:
            return prefixes, False
    return prefixes, True


def _regex_is_provably_outside_internal(location: Location) -> bool:
    flags = re.IGNORECASE if location.modifier == "~*" else 0
    try:
        parsed = list(re._parser.parse(location.pattern, flags))
    except re.error:
        return False
    if parsed[:2] != [
        (re._constants.AT, re._constants.AT_BEGINNING),
        (re._constants.LITERAL, ord("/")),
    ]:
        return False

    prefixes, _complete = _literal_prefixes(parsed[2:])
    protected = INTERNAL_PREFIX[1:].lower() if flags else INTERNAL_PREFIX[1:]
    candidates = {prefix.lower() for prefix in prefixes} if flags else prefixes
    return bool(candidates) and all(
        prefix
        and not protected.startswith(prefix)
        and not prefix.startswith(protected)
        for prefix in candidates
    )


def _overlaps_internal_namespace(location: Location) -> bool:
    if location.modifier == "=":
        return location.pattern.startswith(INTERNAL_PREFIX)
    if location.modifier in {"", "^~"}:
        return location.pattern == INTERNAL_PREFIX.rstrip("/") or location.pattern.startswith(
            INTERNAL_PREFIX
        )
    return not _regex_is_provably_outside_internal(location)


def _server_scope_directive_names(body: tuple[Statement, ...]) -> set[str]:
    names: set[str] = set()
    for statement in body:
        if not statement.parts or statement.parts[0] == "location":
            continue
        names.add(statement.parts[0])
        if statement.children is not None:
            names.update(_server_scope_directive_names(statement.children))
    return names


def _assert_internal_boundary(server: Statement) -> None:
    assert server.children is not None
    server_directives = _server_scope_directive_names(server.children)
    assert not server_directives & {"error_page", "include", "rewrite"}

    locations = _locations(server)
    denies = [
        location
        for location in locations
        if location.modifier == "^~" and location.pattern == "/_internal/"
    ]

    assert len(denies) == 1
    deny = denies[0]
    assert _active_directives(deny.body) == ["return 404"]
    assert not {
        statement.parts[0]
        for statement in deny.body
        if statement.parts
    } & {"proxy_pass", "rewrite", "try_files", "error_page"}

    overlapping = [
        location
        for location in locations
        if location is not deny and _overlaps_internal_namespace(location)
    ]
    assert overlapping == []

    backend_or_catch_all = [
        location.start
        for location in locations
        if location.modifier in {"~", "~*"}
        or (location.modifier == "" and location.pattern == "/")
    ]
    assert backend_or_catch_all
    assert deny.start < min(backend_or_catch_all)

    for request_path in INTERNAL_PATHS:
        assert _resolve_location(locations, request_path) == deny
    assert _resolve_location(locations, "/_internality") != deny


def _public_server_with(extra: str) -> Statement:
    servers = _public_servers_from_source(
        f"""
server {{
    listen 443 ssl;
    server_name vinhlong360.vn www.vinhlong360.vn;
    location ^~ /_internal/ {{ return 404; }}
    {extra}
    location / {{ proxy_pass http://vl360_nuxt; }}
}}
"""
    )
    assert len(servers) == 1
    return servers[0]


def test_parser_ignores_server_and_location_decoys_inside_comments_and_quotes(tmp_path: Path):
    config = tmp_path / "nginx.conf"
    config.write_text(
        '''
# server { server_name vinhlong360.vn; location ^~ /_internal/ { return 404; } }
map $host $decoy {
    default "quoted value
server { server_name vinhlong360.vn; location ^~ /_internal/ { return 404; } }
still quoted";
}
server {
    listen 80;
    server_name example.test;
    location / { return 200; }
}
''',
        encoding="utf-8",
    )

    assert _public_servers(config) == []


def test_public_server_detection_requires_exact_server_name_token(tmp_path: Path):
    config = tmp_path / "nginx.conf"
    config.write_text(
        '''
server {
    listen 80;
    server_name evilvinhlong360.vn vinhlong360.vn.example.test;
    location / { return 200; }
}
''',
        encoding="utf-8",
    )

    assert _public_servers(config) == []


def test_parser_balances_nested_and_quoted_braces_without_counting_commented_deny():
    source = '''
server {
    server_name vinhlong360.vn;
    # location ^~ /_internal/ { return 404; }
    location / {
        add_header X-Literal "quoted } and { braces";
        if ($request_method = GET) { return 200; }
    }
}
'''
    servers = _public_servers_from_source(source)

    assert len(servers) == 1
    assert [(item.modifier, item.pattern) for item in _locations(servers[0])] == [("", "/")]


@pytest.mark.parametrize(
    "override",
    [
        Location("=", "/_internal/launch-policy-attestation", (), 1),
        Location("", "/_internal/launch-policy-attestation", (), 1),
    ],
)
def test_location_resolution_exposes_exact_or_longer_prefix_overrides(override: Location):
    deny = Location("^~", "/_internal/", (), 2)
    catch_all = Location("", "/", (), 3)

    assert _resolve_location([deny, override, catch_all], INTERNAL_PATHS[0]) == override
    assert _resolve_location([deny, override, catch_all], "/_internality") == catch_all


@pytest.mark.parametrize(
    "selector",
    [
        "location = /_internal/new-secret { proxy_pass http://vl360_agent; }",
        "location ^~ /_internal { proxy_pass http://vl360_agent; }",
        "location /_internal/new-secret { proxy_pass http://vl360_agent; }",
        "location ^~ /_internal/new-secret { proxy_pass http://vl360_agent; }",
        r"location ~ ^/_internal/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/_inte[r]nal/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/.*$ { proxy_pass http://vl360_agent; }",
        r"location ~* ^/_INTERNAL/new-secret$ { proxy_pass http://vl360_agent; }",
    ],
)
def test_internal_boundary_rejects_every_overlapping_location_selector(selector: str):
    server = _public_server_with(selector)

    with pytest.raises(AssertionError):
        _assert_internal_boundary(server)


@pytest.mark.parametrize(
    "directive",
    [
        "error_page 404 = @proxied; location @proxied { proxy_pass http://vl360_agent; }",
        r"rewrite ^/_internal/(.*)$ /$1 last;",
        r"if ($request_uri ~ ^/_internal/) { rewrite ^ /api last; }",
        "include conf.d/public-routes.conf;",
    ],
)
def test_internal_boundary_rejects_server_scope_routing_bypasses(directive: str):
    server = _public_server_with(directive)

    with pytest.raises(AssertionError):
        _assert_internal_boundary(server)


def test_server_scope_guard_ignores_comments_quotes_and_location_body_directives():
    server = _public_server_with(
        r'''
        # error_page 404 = @proxied;
        add_header X-Literal "rewrite ^/_internal/(.*)$ /$1 last; include bypass.conf;";
        location /legacy {
            rewrite ^/legacy$ / permanent;
            include conf.d/location-headers.conf;
            error_page 404 = /legacy;
        }
        '''
    )

    _assert_internal_boundary(server)


@pytest.mark.parametrize(
    ("filename", "expected_public_servers"),
    [("nginx.conf", 1), ("nginx-ssl.conf", 2)],
)
def test_every_public_server_fails_closed_for_internal_routes(
    filename: str,
    expected_public_servers: int,
):
    servers = _public_servers(ROOT / filename)
    assert len(servers) == expected_public_servers

    for server in servers:
        _assert_internal_boundary(server)
