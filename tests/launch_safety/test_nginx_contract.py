from __future__ import annotations

import json
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
            if not buffer:
                buffer_start = index
            quote = character
            index += 1
            while index < len(source) and source[index] != quote:
                if source[index] == "\\" and index + 1 < len(source):
                    buffer.extend((source[index], source[index + 1]))
                    index += 2
                    continue
                buffer.append(source[index])
                index += 1
            if index >= len(source):
                raise AssertionError("unterminated quoted Nginx token")
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
            if argument == ord("\\"):
                return prefixes, False
            pieces = {chr(argument)}
            complete = True
        elif operation == re._constants.IN:
            if any(
                item_operation != re._constants.LITERAL
                for item_operation, _value in argument
            ):
                return prefixes, False
            pieces = {
                chr(value)
                for item_operation, value in argument
                if item_operation == re._constants.LITERAL
            }
            complete = True
        elif operation == re._constants.SUBPATTERN:
            if argument[1] & re.IGNORECASE:
                return prefixes, False
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
    if "[:" in location.pattern:
        return False
    try:
        parsed_pattern = re._parser.parse(location.pattern, 0)
    except re.error:
        return False
    # Inline PCRE case-folding is accepted only when we can prove the path prefix
    # is outside the protected namespace; unfamiliar parser forms fail closed.
    if parsed_pattern.state.flags & re.IGNORECASE:
        return False
    parsed = list(parsed_pattern)
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
    if location.modifier in {"=", "", "^~"} and "\\" in location.pattern:
        return True
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


def _server_scope_includes(body: tuple[Statement, ...]) -> list[tuple[str, ...]]:
    includes: list[tuple[str, ...]] = []
    for statement in body:
        if not statement.parts or statement.parts[0] == "location":
            continue
        if statement.parts[0] == "include":
            includes.append(statement.parts[1:])
        if statement.children is not None:
            includes.extend(_server_scope_includes(statement.children))
    return includes


def _assert_internal_boundary(server: Statement) -> None:
    assert server.children is not None
    server_directives = _server_scope_directive_names(server.children)
    assert not server_directives & {"error_page", "rewrite"}
    assert all(
        include == ("/etc/nginx/vl360-maintenance/active-server.conf",)
        for include in _server_scope_includes(server.children)
    )

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


def test_parser_concatenates_adjacent_quoted_and_unquoted_fragments():
    source = r'''
ser"ver" {
    server_na"me" vinhlong360.vn;
    loca"tion" = /_inter"nal"/new-secret {
        add_header X-Literal "quoted # value";
        proxy_pass http://vl360_agent;
    }
}
'''

    servers = _public_servers_from_source(source)

    assert len(servers) == 1
    locations = _locations(servers[0])
    assert [(item.modifier, item.pattern) for item in locations] == [
        ("=", "/_internal/new-secret")
    ]
    assert _active_directives(locations[0].body) == [
        "add_header X-Literal quoted # value",
        "proxy_pass http://vl360_agent",
    ]


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
        'location = /_inter"nal"/new-secret { proxy_pass http://vl360_agent; }',
        r"location = /\_internal/new-secret { proxy_pass http://vl360_agent; }",
        r"location /\_internal/new-secret { proxy_pass http://vl360_agent; }",
        r"location ^~ /\_internal/new-secret { proxy_pass http://vl360_agent; }",
        r"location ~ ^/_internal/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/_inte[r]nal/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/[xA-z]internal/ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/[x\D]internal/ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/[^xy]internal/ { proxy_pass http://vl360_agent; }",
        r'location ~ "^/\\\\x5finternal/new-secret$" { proxy_pass http://vl360_agent; }',
        r"location ~ ^/[[:punct:]]internal/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/.*$ { proxy_pass http://vl360_agent; }",
        r"location ~ (?i)^/_INTERNAL/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~ ^/(?i:_INTERNAL)/new-secret$ { proxy_pass http://vl360_agent; }",
        r"location ~* ^/_INTERNAL/new-secret$ { proxy_pass http://vl360_agent; }",
    ],
)
def test_internal_boundary_rejects_every_overlapping_location_selector(selector: str):
    server = _public_server_with(selector)

    with pytest.raises(AssertionError):
        _assert_internal_boundary(server)


@pytest.mark.parametrize(
    "selector",
    [
        r"location ~ ^/api[x\D] { proxy_pass http://vl360_agent; }",
        r"location ~* ^/api(?:/|$) { proxy_pass http://vl360_agent; }",
    ],
)
def test_internal_boundary_allows_regex_after_disjoint_literal_prefix(selector: str):
    server = _public_server_with(selector)

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


ROOT_SEO_PATHS = (
    "/robots.txt",
    "/sitemap.xml",
    "/sitemap-media.xml",
    "/sitemap-index.xml",
)


def _directive(body: tuple[Statement, ...], name: str) -> list[Statement]:
    return [statement for statement in body if statement.parts[:1] == (name,)]


def _location_for(server: Statement, modifier: str, pattern: str) -> Location:
    matches = [
        location
        for location in _locations(server)
        if location.modifier == modifier and location.pattern == pattern
    ]
    assert len(matches) == 1, (modifier, pattern, matches)
    return matches[0]


@pytest.mark.parametrize("filename", ["nginx.conf", "nginx-ssl.conf"])
def test_root_seo_is_nuxt_owned_and_uncached(filename: str):
    servers = [
        server
        for server in _public_servers(ROOT / filename)
        if any(
            location.modifier == ""
            and location.pattern == "/"
            and any(
                statement.parts[:2] == ("proxy_pass", "http://vl360_nuxt")
                for statement in _directive(location.body, "proxy_pass")
            )
            for location in _locations(server)
        )
    ]
    assert servers
    for server in servers:
        locations = _locations(server)
        for path in ROOT_SEO_PATHS:
            location = _location_for(server, "=", path)
            proxy_pass = _directive(location.body, "proxy_pass")
            assert len(proxy_pass) == 1
            assert proxy_pass[0].parts[1] in {
                "http://vl360_nuxt",
                "$nuxt_upstream$request_uri",
            }
            assert not _directive(location.body, "proxy_cache_valid")
            assert not _directive(location.body, "proxy_cache") or all(
                statement.parts == ("proxy_cache", "off")
                for statement in _directive(location.body, "proxy_cache")
            )
            assert _resolve_location(locations, path) == location


@pytest.mark.parametrize("filename", ["nginx.conf", "nginx-ssl.conf"])
def test_backend_prefixes_use_segment_boundaries(filename: str):
    servers = [
        server
        for server in _public_servers(ROOT / filename)
        if any(
            location.modifier == ""
            and location.pattern == "/"
            and _directive(location.body, "proxy_pass")
            for location in _locations(server)
        )
    ]
    for server in servers:
        locations = _locations(server)
        backend_locations = [
            location
            for location in locations
            if _directive(location.body, "proxy_pass")
            and any(
                "vl360_agent" in statement.parts[1]
                or "vl360_bots" in statement.parts[1]
                or "$agent_upstream" in statement.parts[1]
                or "$bot_upstream" in statement.parts[1]
                for statement in _directive(location.body, "proxy_pass")
            )
        ]
        for path in ("/system", "/system/x", "/api", "/api/x", "/webhook"):
            assert any(_resolve_location([location], path) == location for location in backend_locations), path
        for path in ("/systematic", "/apiary", "/webhooks"):
            assert not any(_resolve_location([location], path) == location for location in backend_locations), path


def test_route_refactor_preserves_maintenance_includes_exactly_once():
    for filename in ("nginx.conf", "nginx-ssl.conf"):
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert source.count("include /etc/nginx/vl360-maintenance/http-context.conf;") == 1
        for server in _public_servers_from_source(source):
            assert sum(
                statement.parts == ("include", "/etc/nginx/vl360-maintenance/active-server.conf")
                for statement in server.children or ()
            ) == 1


def test_compose_optional_upstreams_use_request_time_resolution():
    source = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    assert "resolver 127.0.0.11 valid=5s ipv6=off;" in source
    assert "set $agent_upstream http://agent:8360;" in source
    assert "set $bot_upstream http://bot-gateway:8361;" in source
    assert "$agent_upstream$request_uri" in source
    assert "$bot_upstream$request_uri" in source


def test_systemd_renderer_emits_loopback_targets_without_compose_dns(tmp_path: Path):
    from scripts.ops.render_nginx_config import render_config

    source = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    rendered = render_config(source, topology="systemd")
    assert "127.0.0.1:8360" in rendered
    assert "127.0.0.1:8361" in rendered
    assert "127.0.0.1:3000" in rendered
    assert "agent:8360" not in rendered
    assert "bot-gateway:8361" not in rendered
    assert "nuxt:3000" not in rendered


def test_systemd_renderer_uses_uri_less_literal_upstreams_and_keeps_admin_rewrite():
    from scripts.ops.render_nginx_config import render_config

    source = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    rendered = render_config(source, topology="systemd")
    servers = _public_servers_from_source(rendered)
    assert len(servers) == 1

    proxy_targets = [
        statement.parts[1]
        for location in _locations(servers[0])
        for statement in _directive(location.body, "proxy_pass")
    ]
    assert "http://127.0.0.1:8360" in proxy_targets
    assert "http://127.0.0.1:8361" in proxy_targets
    assert all("$request_uri" not in target for target in proxy_targets)
    assert all("$uri" not in target for target in proxy_targets)
    assert all("$is_args" not in target for target in proxy_targets)
    assert all("$args" not in target for target in proxy_targets)

    exact_admin = _location_for(servers[0], "=", "/admin-api")
    prefix_admin = _location_for(servers[0], "^~", "/admin-api/")
    assert _directive(exact_admin.body, "rewrite")[0].parts == (
        "rewrite",
        "^",
        "/admin",
        "break",
    )
    assert _directive(prefix_admin.body, "rewrite")[0].parts[-2:] == (
        "/admin$admin_rest",
        "break",
    )
    assert _directive(exact_admin.body, "proxy_pass")[0].parts == (
        "proxy_pass",
        "http://127.0.0.1:8360",
    )
    assert _directive(prefix_admin.body, "proxy_pass")[0].parts == (
        "proxy_pass",
        "http://127.0.0.1:8360",
    )


def _backend_upstream(location: Location) -> str | None:
    targets = _directive(location.body, "proxy_pass")
    if not targets:
        return None
    assert len(targets) == 1
    target = targets[0].parts[1]
    if "$agent_upstream" in target or "vl360_agent" in target:
        return "agent"
    if "$bot_upstream" in target or "vl360_bots" in target:
        return "bot-gateway"
    return None


def _regex_backend_aliases(pattern: str) -> set[str]:
    single = re.fullmatch(r"\^/([a-z0-9-]+)\(\?:/\|\$\)", pattern)
    if single:
        return {f"/{single.group(1)}"}
    grouped = re.fullmatch(r"\^/\(([a-z0-9|-]+)\)\(\?:/\|\$\)", pattern)
    if grouped:
        names = grouped.group(1).split("|")
        assert all(names) and len(names) == len(set(names))
        return {f"/{name}" for name in names}
    raise AssertionError(f"backend regex lacks reviewed segment-boundary form: {pattern}")


def _backend_ingress_inventory(
    source: str,
) -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    inventory: dict[tuple[str, str], tuple[str, frozenset[str]]] = {}
    for server in _public_servers_from_source(source):
        for location in _locations(server):
            upstream = _backend_upstream(location)
            if upstream is None:
                continue
            if location.modifier in {"~", "~*"}:
                aliases = frozenset(_regex_backend_aliases(location.pattern))
            elif location.modifier in {"=", "", "^~"}:
                prefix = location.pattern.rstrip("/") or "/"
                aliases = frozenset({prefix})
            else:
                raise AssertionError(
                    f"unsupported backend location modifier: {location.modifier}"
                )
            selector = (location.modifier, location.pattern)
            ingress = (upstream, aliases)
            previous = inventory.setdefault(selector, ingress)
            assert previous == ingress, (selector, previous, ingress)
    return inventory


def _assert_backend_ingress_matches_policy(
    source: str,
    policy: dict[str, object],
) -> dict[tuple[str, str], tuple[str, frozenset[str]]]:
    inventory = _backend_ingress_inventory(source)
    sensitive = {
        item["prefix"]
        for item in policy["sensitive_prefixes"]
        if isinstance(item, dict)
    }
    exceptions = {
        item["prefix"]: item
        for item in policy["backend_ingress_exceptions"]
        if isinstance(item, dict)
    }
    reviewed_aliases: set[str] = set()
    for upstream, aliases in inventory.values():
        for prefix in aliases:
            reviewed_aliases.add(prefix)
            if prefix in sensitive:
                continue
            exception = exceptions.get(prefix)
            assert exception is not None, f"unreviewed backend ingress alias: {prefix}"
            assert exception.get("upstream") == upstream
            assert isinstance(exception.get("review_reason"), str)
            assert exception["review_reason"].strip()
    assert set(exceptions) <= reviewed_aliases, "stale backend ingress exception"
    return inventory


def test_backend_ingress_aliases_match_policy_and_http_https_parity():
    policy = json.loads(
        (ROOT / "config" / "launch-indexing-policy.json").read_text(encoding="utf-8")
    )
    http_aliases = _assert_backend_ingress_matches_policy(
        (ROOT / "nginx.conf").read_text(encoding="utf-8"), policy
    )
    https_aliases = _assert_backend_ingress_matches_policy(
        (ROOT / "nginx-ssl.conf").read_text(encoding="utf-8"), policy
    )
    assert http_aliases == https_aliases


def _remove_location_block(source: str, header: str) -> str:
    pattern = re.compile(
        rf"^    {re.escape(header)} \{{\r?\n.*?^    \}}\r?\n",
        flags=re.MULTILINE | re.DOTALL,
    )
    mutated, count = pattern.subn("", source, count=1)
    assert count == 1, header
    return mutated


@pytest.mark.parametrize(
    "header",
    (
        "location = /admin-api",
        "location ^~ /admin-api/",
    ),
)
def test_backend_ingress_parity_rejects_missing_admin_selector(header: str):
    policy = json.loads(
        (ROOT / "config" / "launch-indexing-policy.json").read_text(encoding="utf-8")
    )
    http_inventory = _assert_backend_ingress_matches_policy(
        (ROOT / "nginx.conf").read_text(encoding="utf-8"), policy
    )
    https_source = _remove_location_block(
        (ROOT / "nginx-ssl.conf").read_text(encoding="utf-8"), header
    )
    https_inventory = _assert_backend_ingress_matches_policy(https_source, policy)

    with pytest.raises(AssertionError):
        assert http_inventory == https_inventory


def test_backend_ingress_policy_rejects_rogue_route():
    policy = json.loads(
        (ROOT / "config" / "launch-indexing-policy.json").read_text(encoding="utf-8")
    )
    source = (ROOT / "nginx.conf").read_text(encoding="utf-8").replace(
        "location ~ ^/api(?:/|$) {",
        "location ~ ^/rogue(?:/|$) {",
        1,
    )
    with pytest.raises(AssertionError, match="unreviewed backend ingress alias: /rogue"):
        _assert_backend_ingress_matches_policy(source, policy)
