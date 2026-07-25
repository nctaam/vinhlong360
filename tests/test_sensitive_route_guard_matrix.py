from __future__ import annotations

from pathlib import Path

import pytest

from scripts import sensitive_route_guard_matrix as matrix
from scripts.checks.check_complexity import ComplexityCheck


EXACT_PATHS = ("/metrics", "/vectors/stats")
PREFIX_PATHS = (
    "/system",
    "/analytics",
    "/checkpoints",
    "/confirmations",
    "/confirm/",
    "/reject/",
    "/ab-testing",
    "/prompt-cache",
    "/freshness",
)
ENDPOINTS = (
    ("/vectors/build", "post", "build_vectors"),
    ("/vectors/search", "get", "vector_search_endpoint"),
    ("/image/recognize", "post", "image_recognize_endpoint"),
)


def _endpoint_source(route: str, method: str, function: str, mode: str) -> str:
    decorator = f'@app.{method}("{route}")\n'
    declaration = f"async def {function}(request):"
    guard = '    await require_admin_scope(request, "ops.deploy")'
    if mode == "sync":
        declaration = f"def {function}(request):"
        guard = '    require_admin_scope(request, "ops.deploy")'
    elif mode == "unawaited":
        guard = '    require_admin_scope(request, "ops.deploy")'
    elif mode == "missing-guard":
        guard = "    pass"
    elif mode == "guard-after-return":
        guard = (
            "    return public_response()\n"
            '    await require_admin_scope(request, "ops.deploy")'
        )
    elif mode == "missing-decorator":
        decorator = ""
    elif mode == "wrong-route":
        decorator = f'@app.{method}("{route}-public")\n'
    return f"{decorator}{declaration}\n{guard}\n"


def _server_source(
    *,
    exact_paths: tuple[str, ...] = EXACT_PATHS,
    prefix_paths: tuple[str, ...] = PREFIX_PATHS,
    exact_assignment: str | None = None,
    prefix_assignment: str | None = None,
    later_assignment: str = "",
    helper_mode: str = "safe",
    gate_mode: str = "safe",
    endpoint_modes: dict[str, str] | None = None,
) -> str:
    exact_assignment = exact_assignment or f"_GATED_EXACT_PATHS = {exact_paths!r}"
    prefix_assignment = prefix_assignment or f"_GATED_PREFIX_PATHS = {prefix_paths!r}"
    helper_body = (
        "    return path in _GATED_EXACT_PATHS or any(\n"
        "        path.startswith(prefix) for prefix in _GATED_PREFIX_PATHS\n"
        "    )"
    )
    if helper_mode == "dead-decoy":
        helper_body = (
            "    if False:\n"
            "        _GATED_EXACT_PATHS\n"
            "        _GATED_PREFIX_PATHS\n"
            "        path.startswith('/decoy')\n"
            "    return False"
        )

    gate_body = (
        "    if _is_gated_path(request.url.path):\n"
        "        from middleware import verify_admin_key\n"
        "        if not verify_admin_key(request):\n"
        "            return JSONResponse(status_code=404)\n"
        "    return await call_next(request)"
    )
    if gate_mode == "dead-decoy":
        gate_body = (
            "    observed = _is_gated_path(request.url.path)\n"
            "    if False:\n"
            "        from middleware import verify_admin_key\n"
            "        if not verify_admin_key(request):\n"
            "            return JSONResponse(status_code=404)\n"
            "    return await call_next(request)"
        )
    elif gate_mode == "guard-after-return":
        gate_body = (
            "    if _is_gated_path(request.url.path):\n"
            "        return await call_next(request)\n"
            "        from middleware import verify_admin_key\n"
            "        if not verify_admin_key(request):\n"
            "            return JSONResponse(status_code=404)\n"
            "    return await call_next(request)"
        )
    elif gate_mode == "missing-admin":
        gate_body = (
            "    if _is_gated_path(request.url.path):\n"
            "        return JSONResponse(status_code=404)\n"
            "    return await call_next(request)"
        )
    elif gate_mode == "missing-404":
        gate_body = (
            "    if _is_gated_path(request.url.path):\n"
            "        from middleware import verify_admin_key\n"
            "        if not verify_admin_key(request):\n"
            "            return JSONResponse(status_code=403)\n"
            "    return await call_next(request)"
        )

    endpoint_modes = endpoint_modes or {}
    endpoints = "\n".join(
        _endpoint_source(route, method, function, endpoint_modes.get(function, "safe"))
        for route, method, function in ENDPOINTS
    )
    return f"""
{exact_assignment}
{prefix_assignment}
{later_assignment}


def _is_gated_path(path: str) -> bool:
{helper_body}


@app.middleware("http")
async def gate_internal_endpoints(request, call_next):
{gate_body}


{endpoints}
"""


def _run_matrix(monkeypatch, tmp_path: Path, source: str) -> tuple[int, str]:
    server = tmp_path / "server.py"
    server.write_text(source, encoding="utf-8")
    monkeypatch.setattr(matrix, "SERVER", server)
    return matrix.main(), ""


def test_matrix_accepts_centralized_gated_path_tables(
    monkeypatch, tmp_path: Path, capsys
):
    result, _ = _run_matrix(monkeypatch, tmp_path, _server_source())

    assert result == 0, capsys.readouterr().out


@pytest.mark.parametrize(
    ("paths_kind", "source", "expected"),
    (
        (
            "exact",
            _server_source(exact_paths=("/metrics",)),
            "FAIL /vectors/stats",
        ),
        (
            "prefix",
            _server_source(
                prefix_paths=tuple(path for path in PREFIX_PATHS if path != "/freshness")
            ),
            "FAIL /freshness/*",
        ),
    ),
)
def test_matrix_rejects_missing_protected_paths(
    monkeypatch, tmp_path: Path, capsys, paths_kind: str, source: str, expected: str
):
    result, _ = _run_matrix(monkeypatch, tmp_path, source)
    output = capsys.readouterr().out

    assert result == 1, paths_kind
    assert expected in output


def test_matrix_reports_source_syntax_errors(monkeypatch, tmp_path: Path, capsys):
    result, _ = _run_matrix(monkeypatch, tmp_path, "def broken(:\n")
    output = capsys.readouterr().out

    assert result == 1
    assert "server.py syntax error" in output


@pytest.mark.parametrize(
    ("source", "table_name"),
    (
        (
            _server_source(exact_assignment="_GATED_EXACT_PATHS = load_paths()"),
            "_GATED_EXACT_PATHS",
        ),
        (
            _server_source(later_assignment="_GATED_EXACT_PATHS = load_paths()"),
            "_GATED_EXACT_PATHS",
        ),
        (
            _server_source(prefix_assignment="_GATED_PREFIX_PATHS = load_paths()"),
            "_GATED_PREFIX_PATHS",
        ),
        (
            _server_source(later_assignment="_GATED_PREFIX_PATHS = load_paths()"),
            "_GATED_PREFIX_PATHS",
        ),
    ),
)
def test_matrix_rejects_dynamic_or_reassigned_path_tables(
    monkeypatch, tmp_path: Path, capsys, source: str, table_name: str
):
    result, _ = _run_matrix(monkeypatch, tmp_path, source)
    output = capsys.readouterr().out

    assert result == 1
    assert f"{table_name} must have one literal assignment" in output


def test_matrix_rejects_called_global_route_table_rebind(
    monkeypatch, tmp_path: Path, capsys
):
    source = _server_source(
        later_assignment=(
            "def disable_guards():\n"
            "    global _GATED_EXACT_PATHS, _GATED_PREFIX_PATHS\n"
            "    _GATED_EXACT_PATHS = ()\n"
            "    _GATED_PREFIX_PATHS = ()\n\n"
            "disable_guards()"
        )
    )

    result, _ = _run_matrix(monkeypatch, tmp_path, source)
    output = capsys.readouterr().out

    assert result == 1
    assert "_GATED_EXACT_PATHS must have one literal assignment" in output
    assert "_GATED_PREFIX_PATHS must have one literal assignment" in output


@pytest.mark.parametrize(
    ("gate_mode", "expected"),
    (
        ("dead-decoy", "gate_internal_endpoints must enforce the gated-path 404 branch"),
        ("missing-admin", "gate_internal_endpoints must verify the admin key"),
        ("missing-404", "gate_internal_endpoints must hide sensitive paths with 404"),
    ),
)
def test_matrix_rejects_invalid_middleware_control_flow(
    monkeypatch, tmp_path: Path, capsys, gate_mode: str, expected: str
):
    result, _ = _run_matrix(
        monkeypatch,
        tmp_path,
        _server_source(gate_mode=gate_mode),
    )
    output = capsys.readouterr().out

    assert result == 1
    assert expected in output


def test_matrix_rejects_middleware_guard_after_terminal_return(
    monkeypatch, tmp_path: Path, capsys
):
    result, _ = _run_matrix(
        monkeypatch,
        tmp_path,
        _server_source(gate_mode="guard-after-return"),
    )
    output = capsys.readouterr().out

    assert result == 1
    assert "gate_internal_endpoints must verify the admin key" in output


def test_matrix_rejects_dead_helper_decoys(monkeypatch, tmp_path: Path, capsys):
    result, _ = _run_matrix(
        monkeypatch,
        tmp_path,
        _server_source(helper_mode="dead-decoy"),
    )
    output = capsys.readouterr().out

    assert result == 1
    assert "_is_gated_path must return exact-or-prefix membership" in output


@pytest.mark.parametrize("mode", ("sync", "unawaited", "missing-decorator", "wrong-route"))
def test_matrix_rejects_invalid_endpoint_guard_shape(
    monkeypatch, tmp_path: Path, capsys, mode: str
):
    result, _ = _run_matrix(
        monkeypatch,
        tmp_path,
        _server_source(endpoint_modes={"build_vectors": mode}),
    )
    output = capsys.readouterr().out

    assert result == 1
    assert "FAIL /vectors/build" in output


def test_matrix_rejects_endpoint_guard_after_terminal_return(
    monkeypatch, tmp_path: Path, capsys
):
    result, _ = _run_matrix(
        monkeypatch,
        tmp_path,
        _server_source(endpoint_modes={"build_vectors": "guard-after-return"}),
    )
    output = capsys.readouterr().out

    assert result == 1
    assert "FAIL /vectors/build" in output


@pytest.mark.parametrize("route,method,function", ENDPOINTS)
def test_matrix_preserves_each_endpoint_local_guard(
    monkeypatch,
    tmp_path: Path,
    capsys,
    route: str,
    method: str,
    function: str,
):
    result, _ = _run_matrix(
        monkeypatch,
        tmp_path,
        _server_source(endpoint_modes={function: "missing-guard"}),
    )
    output = capsys.readouterr().out

    assert result == 1, (method, function)
    assert f"FAIL {route}" in output


def test_matrix_checker_stays_below_complexity_ratchet():
    result = ComplexityCheck(root=matrix.ROOT).run(
        ["scripts/sensitive_route_guard_matrix.py"]
    )

    assert result["count"] == 0, result["violations"]
