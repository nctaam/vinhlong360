"""Guard: an HTTP route decorator must stay attached to its REAL handler.

Bug class this locks down ("extract-method làm lạc decorator"):

    @router.post("/entities/bulk-place", ...)
    def _bulk_assign_entities(ids, pid, place):   # <-- helper slid in underneath
        ...

    async def bulk_assign_place(body: BulkAssignPlaceRequest):   # <-- real handler,
        ...                                                      #     now unreachable

The decorator binds to whatever `def` follows it, so the helper becomes the
endpoint.  FastAPI then turns the helper's plain positional args into REQUIRED
QUERY PARAMS: a body-only POST returns 422 forever, a GET 422s or 500s, and the
real handler is never called.  Nothing in the source *looks* wrong, so this
survived review three separate times (/admin/entities/bulk-place,
/admin/system-health, /admin/moderation/batch).

Both tests below assert on the ASSEMBLED application / parsed AST — i.e. what
FastAPI actually decided a route is — not on source text.
"""
import ast
import os
import pathlib
import sys
import typing

import pytest

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-decorator-binding")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

AGENT_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_DIR))

# Decorator attributes that register an HTTP route.
_ROUTE_VERBS = {
    "get", "post", "put", "patch", "delete", "head", "options",
    "api_route", "websocket",
}
# Objects those decorators hang off of (APIRouter / FastAPI instances).
_ROUTER_NAMES = {"router", "app", "admin_router", "public_router"}

# A parameter with no annotation is fine *if* its default is one of these
# FastAPI markers — the marker, not the annotation, tells FastAPI where the
# value comes from.  `user = Depends(get_current_user)` is idiomatic and
# appears ~120 times in this codebase; it must not trip the check.
_PARAM_MARKERS = {
    "Depends", "Security", "Query", "Path", "Body", "Header",
    "Cookie", "Form", "File", "Request",
}


def _iter_agent_sources():
    for path in sorted(AGENT_DIR.rglob("*.py")):
        parts = path.parts
        if "tests" in parts or "__pycache__" in parts:
            continue
        yield path


def _is_route_decorated(node: ast.AST) -> bool:
    for dec in node.decorator_list:
        call = dec.func if isinstance(dec, ast.Call) else dec
        if not isinstance(call, ast.Attribute) or call.attr not in _ROUTE_VERBS:
            continue
        base = call.value
        name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
        if name in _ROUTER_NAMES or name.endswith("router") or name.endswith("app"):
            return True
    return False


def _marker_name(default: ast.AST | None) -> str | None:
    if not isinstance(default, ast.Call):
        return None
    func = default.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _unmarked_unannotated_params(node) -> list[str]:
    """Params FastAPI would silently turn into query params."""
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    # line up defaults with the tail of the positional list
    pos_defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    pairs = list(zip(positional, pos_defaults))
    pairs += list(zip(args.kwonlyargs, args.kw_defaults))

    offenders = []
    for arg, default in pairs:
        if arg.arg in ("self", "cls"):
            continue
        if arg.annotation is not None:
            continue
        if _marker_name(default) in _PARAM_MARKERS:
            continue
        offenders.append(arg.arg)
    return offenders


def test_no_route_decorator_lands_on_a_private_helper():
    """A name starting with `_` is a helper. A helper is never an endpoint.

    This is the cheapest possible tripwire for a drifted decorator, and it
    works on modules whose router is never mounted into `server.app`.
    """
    offenders = []
    for path in _iter_agent_sources():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - parse failures are their own bug
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if _is_route_decorated(node) and node.name.startswith("_"):
                offenders.append(f"{path.relative_to(AGENT_DIR.parent)}:{node.lineno} {node.name}")

    assert offenders == [], (
        "Route decorator is attached to a private helper — it almost certainly "
        "drifted off the real handler during an extract-method refactor. "
        "Move the decorator down onto the handler:\n  " + "\n  ".join(offenders)
    )


def test_route_params_are_annotated_or_dependency_marked():
    """Every route handler param needs an annotation or a FastAPI marker default.

    A bare `def handler(rows, status, reason)` is the fingerprint of a helper
    that got decorated by accident.
    """
    offenders = []
    for path in _iter_agent_sources():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _is_route_decorated(node):
                continue
            bad = _unmarked_unannotated_params(node)
            if bad:
                offenders.append(
                    f"{path.relative_to(AGENT_DIR.parent)}:{node.lineno} "
                    f"{node.name}({', '.join(bad)})"
                )

    assert offenders == [], (
        "Route handler params without an annotation or a Depends/Query/Body "
        "default become REQUIRED QUERY PARAMS — the endpoint will 422 forever:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.integration
def test_assembled_app_has_no_any_typed_query_params():
    """Runtime truth: ask the built app what it thinks each route's params are.

    `field_info.annotation is Any` is exactly what FastAPI records for a
    positional arg it could not type — i.e. the drifted-helper signature.
    """
    from server import app  # noqa: E402 — env flags must be set first

    offenders = []
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        for field in dependant.query_params:
            if getattr(field.field_info, "annotation", None) is typing.Any:
                offenders.append(
                    f"{sorted(route.methods)} {route.path} -> "
                    f"{route.endpoint.__name__}(query param '{field.name}')"
                )

    assert offenders == [], (
        "These routes demand untyped query params, so any normal call 422s:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.integration
def test_assembled_app_binds_no_route_to_a_private_helper():
    from server import app  # noqa: E402

    offenders = [
        f"{sorted(route.methods)} {route.path} -> {route.endpoint.__name__}"
        for route in app.routes
        if getattr(route, "dependant", None) is not None
        and route.endpoint.__name__.startswith("_")
    ]
    assert offenders == [], (
        "Endpoint bound to a private helper (decorator drifted):\n  " + "\n  ".join(offenders)
    )
