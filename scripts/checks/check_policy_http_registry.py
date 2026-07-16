"""Fail closed when policy-bearing FastAPI routes drift from the exact registry."""

from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = ROOT / "agent"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(AGENT_ROOT))

from checks.common import repo_root  # noqa: E402
from policy_http import POLICY_ENDPOINTS, PolicyEndpoint  # noqa: E402


HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head"})
DECLARED_FUTURE_ROUTE_NAMES = frozenset(
    {"launch_policy_attestation", "launch_sitemap_document"}
)
SERIALIZED_POLICY_KEYS = frozenset(
    {
        "index_policy",
        "policy_fingerprint",
        "policy_revision",
        "route_manifest_revision",
        "backend_policy_revision",
        "x-launch-indexing-policy",
        "x-launch-route-manifest-revision",
        "x-launch-backend-policy-revision",
        "x-launch-sitemap-batch-revision",
        "x-launch-sitemap-requested-batch",
    }
)
_AUTHORITATIVE_APP_MODULE = "server"
_AUTHORITATIVE_APP_MODULES = frozenset({_AUTHORITATIVE_APP_MODULE, "agent.server"})
_AUTHORITATIVE_APP_VARIABLE = "app"


@dataclass(frozen=True)
class Finding:
    code: str
    file: str
    line: int
    message: str


@dataclass(frozen=True)
class _RouterDef:
    module: str
    variable: str
    prefix: str
    is_app: bool


@dataclass(frozen=True)
class _Route:
    method: str
    path: str
    route_name: str
    file: str
    line: int
    policy_bearing: bool
    mounted: bool

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.method, self.path, self.route_name


@dataclass
class _ModuleInfo:
    path: Path
    key: str
    tree: ast.Module
    routers: dict[str, _RouterDef]
    imported_symbols: dict[str, tuple[str, str]]
    imported_modules: dict[str, str]
    constants: dict[str, str]
    scan_errors: list[Finding]


def agent_source_files(agent_root: Path) -> list[Path]:
    return sorted(
        path
        for path in agent_root.rglob("*.py")
        if "tests" not in path.relative_to(agent_root).parts
        and "__pycache__" not in path.parts
    )


def _literal_string(node: ast.AST | None, constants: dict[str, str] | None = None) -> str | None:
    if isinstance(node, ast.Name) and constants is not None:
        return constants.get(node.id)
    return node.value if isinstance(node, ast.Constant) and type(node.value) is str else None


def _keyword_string(call: ast.Call, name: str, constants: dict[str, str] | None = None) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return _literal_string(keyword.value, constants)
    return None


def _normalise_path(*parts: str) -> str:
    raw_parts = [part for part in parts if part is not None]
    trailing = bool(raw_parts and raw_parts[-1].endswith("/"))
    segments = [part.strip("/") for part in raw_parts if part and part != "/"]
    path = "/" + "/".join(segment for segment in segments if segment)
    if trailing and path != "/":
        path += "/"
    return path


def _common_source_root(paths: Sequence[Path]) -> Path:
    if len(paths) == 1:
        return paths[0].parent
    return Path(os.path.commonpath([str(path.parent) for path in paths]))


def _module_key(path: Path, source_root: Path) -> str:
    try:
        relative = path.relative_to(source_root).with_suffix("")
    except ValueError:
        return path.stem
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or path.stem


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _assignment_name_value(node: ast.AST) -> tuple[str | None, ast.AST | None]:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id, node.value
    return None, None


def _string_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        name, value_node = _assignment_name_value(node)
        value = _literal_string(value_node)
        if name is not None and value is not None:
            constants[name] = value
    return constants


def _proven_fastapi_constructor(
    value: ast.Call,
    imported_symbols: dict[str, tuple[str, str]],
    imported_modules: dict[str, str],
) -> str | None:
    if isinstance(value.func, ast.Name):
        imported = imported_symbols.get(value.func.id)
        if imported is not None and imported[0] == "fastapi":
            return imported[1]
    elif isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name):
        if imported_modules.get(value.func.value.id) == "fastapi":
            return value.func.attr
    return None


def _router_definition(
    node: ast.AST,
    module_key: str,
    constants: dict[str, str],
    imported_symbols: dict[str, tuple[str, str]],
    imported_modules: dict[str, str],
    path: Path,
    scan_errors: list[Finding],
) -> _RouterDef | None:
    name, value = _assignment_name_value(node)
    if name is None or not isinstance(value, ast.Call):
        return None
    constructor_name = _call_name(value)
    constructor = _proven_fastapi_constructor(value, imported_symbols, imported_modules)
    if constructor not in {"APIRouter", "FastAPI"}:
        if constructor_name in {"APIRouter", "FastAPI"}:
            scan_errors.append(
                Finding(
                    "POLICY_ROUTE_SCAN_ERROR",
                    str(path),
                    node.lineno,
                    "router constructor is not proven to originate from fastapi",
                )
            )
        return None
    prefix_node = next((keyword.value for keyword in value.keywords if keyword.arg == "prefix"), None)
    prefix = _literal_string(prefix_node, constants) if prefix_node is not None else ""
    if prefix_node is not None and prefix is None:
        scan_errors.append(
            Finding("POLICY_ROUTE_SCAN_ERROR", str(path), node.lineno, "router prefix is not a simple string")
        )
    return _RouterDef(module_key, name, prefix or "", constructor == "FastAPI")


def _record_imports(
    node: ast.AST,
    imported_symbols: dict[str, tuple[str, str]],
    imported_modules: dict[str, str],
) -> None:
    if isinstance(node, ast.ImportFrom):
        module = ("." * node.level) + (node.module or "")
        for name in node.names:
            imported_symbols[name.asname or name.name] = (module, name.name)
    elif isinstance(node, ast.Import):
        for name in node.names:
            imported_modules[name.asname or name.name.split(".")[0]] = name.name


class _RebindingVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.names.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        self.names.update(name.asname or name.name.split(".")[0] for name in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.names.update(name.asname or name.name for name in node.names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Delete(self, node: ast.Delete) -> None:
        self.names.update(
            child.id
            for target in node.targets
            for child in ast.walk(target)
            if isinstance(child, ast.Name)
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return None


def _clear_rebound_imports(
    node: ast.AST,
    imported_symbols: dict[str, tuple[str, str]],
    imported_modules: dict[str, str],
) -> None:
    visitor = _RebindingVisitor()
    visitor.visit(node)
    for name in visitor.names:
        imported_symbols.pop(name, None)
        imported_modules.pop(name, None)


def _parse_module(path: Path, source_root: Path) -> _ModuleInfo:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    key = _module_key(path, source_root)
    routers: dict[str, _RouterDef] = {}
    imported_symbols: dict[str, tuple[str, str]] = {}
    imported_modules: dict[str, str] = {}
    constants = _string_constants(tree)
    scan_errors: list[Finding] = []

    for node in tree.body:
        _clear_rebound_imports(node, imported_symbols, imported_modules)
        router = _router_definition(
            node,
            key,
            constants,
            imported_symbols,
            imported_modules,
            path,
            scan_errors,
        )
        if router is not None:
            routers[router.variable] = router
        _record_imports(node, imported_symbols, imported_modules)

    return _ModuleInfo(path, key, tree, routers, imported_symbols, imported_modules, constants, scan_errors)


def _module_matches(left: str, right: str) -> bool:
    return left == right or left.endswith(f".{right}") or right.endswith(f".{left}")


def _resolve_router_reference(
    expression: ast.AST,
    module: _ModuleInfo,
    router_defs: dict[tuple[str, str], _RouterDef],
) -> _RouterDef | None:
    candidates: list[tuple[str, str]] = []
    if isinstance(expression, ast.Name):
        if expression.id in module.routers:
            return module.routers[expression.id]
        imported = module.imported_symbols.get(expression.id)
        if imported:
            candidates.append(imported)
    elif isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name):
        imported_module = module.imported_modules.get(expression.value.id)
        if imported_module:
            candidates.append((imported_module, expression.attr))

    for candidate_module, variable in candidates:
        for (defined_module, defined_variable), router in router_defs.items():
            if defined_variable == variable and _module_matches(defined_module, candidate_module):
                return router
    return None


def _decorator_path(
    decorator: ast.Call,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    constants: dict[str, str],
    scan_errors: list[Finding],
) -> str | None:
    path_node = decorator.args[0] if decorator.args else next(
        (keyword.value for keyword in decorator.keywords if keyword.arg == "path"),
        None,
    )
    path = _literal_string(path_node, constants)
    if path is None:
        scan_errors.append(Finding("POLICY_ROUTE_SCAN_ERROR", "", node.lineno, "route path is not a simple string"))
    return path


def _decorator_name(
    decorator: ast.Call,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    constants: dict[str, str],
    scan_errors: list[Finding],
) -> str:
    name_node = next((keyword.value for keyword in decorator.keywords if keyword.arg == "name"), None)
    route_name = _literal_string(name_node, constants) if name_node is not None else node.name
    if route_name is None:
        scan_errors.append(Finding("POLICY_ROUTE_SCAN_ERROR", "", node.lineno, "route name is not a simple string"))
        return node.name
    return route_name


def _decorator_methods(
    decorator: ast.Call,
    method: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    constants: dict[str, str],
    scan_errors: list[Finding],
) -> list[str]:
    if method != "api_route":
        return [method.upper()]
    methods_node = next((keyword.value for keyword in decorator.keywords if keyword.arg == "methods"), None)
    if methods_node is None:
        return ["GET"]
    if not isinstance(methods_node, (ast.List, ast.Tuple, ast.Set)):
        scan_errors.append(Finding("POLICY_ROUTE_SCAN_ERROR", "", node.lineno, "api_route methods are not literal"))
        return []
    methods = [_literal_string(item, constants) for item in methods_node.elts]
    if any(value is None or value.casefold() not in HTTP_METHODS for value in methods):
        scan_errors.append(Finding("POLICY_ROUTE_SCAN_ERROR", "", node.lineno, "api_route method is not supported"))
        return []
    return [value.upper() for value in methods if value is not None]


def _route_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    constants: dict[str, str],
    scan_errors: list[Finding],
):
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        method = decorator.func.attr.lower()
        if method not in HTTP_METHODS and method != "api_route":
            continue
        path = _decorator_path(decorator, node, constants, scan_errors)
        if path is None:
            continue
        route_name = _decorator_name(decorator, node, constants, scan_errors)
        for route_method in _decorator_methods(decorator, method, node, constants, scan_errors):
            yield decorator.func.value, route_method, path, route_name


def _contains_serialized_key(node: ast.AST, constants: dict[str, str] | None = None) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Dict):
            continue
        for key in child.keys:
            value = _literal_string(key, constants)
            if value is not None and value.casefold() in SERIALIZED_POLICY_KEYS:
                return True
    return False


def _subscript_key(target: ast.AST, constants: dict[str, str] | None = None) -> str | None:
    if not isinstance(target, ast.Subscript):
        return None
    return _literal_string(target.slice, constants)


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _contains_name(node: ast.AST | None, name: str) -> bool:
    return node is not None and any(
        isinstance(child, ast.Name) and child.id == name
        for child in ast.walk(node)
    )


_POLICY_CALLS = frozenset(
    {"IndexPolicyDecision", "decide_entity", "decide_ward", "decide_itinerary"}
)
_POLICY_EVIDENCE_CALLS = frozenset({"PolicyEvidence", "current_policy_evidence"})


def _assignment_parts(node: ast.AST) -> tuple[list[ast.AST], ast.AST | None, ast.AST | None]:
    if isinstance(node, ast.Assign):
        return list(node.targets), node.value, None
    if isinstance(node, ast.AnnAssign):
        return [node.target], node.value, node.annotation
    return [], None, None


def _assigned_names(targets: Iterable[ast.AST]) -> set[str]:
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _names_in(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _returned_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {
        name
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
        for name in _names_in(child.value)
    }


def _policy_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        targets, value, annotation = _assignment_parts(child)
        policy_call = isinstance(value, ast.Call) and _call_name(value) in _POLICY_CALLS
        if policy_call or _contains_name(annotation, "IndexPolicyDecision"):
            names.update(_assigned_names(targets))
    return names


def _policy_evidence_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        targets, value, annotation = _assignment_parts(child)
        evidence_call = isinstance(value, ast.Call) and _call_name(value) in _POLICY_EVIDENCE_CALLS
        if evidence_call or _contains_name(annotation, "PolicyEvidence"):
            names.update(_assigned_names(targets))
    return names


def _directly_derived_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    initial: set[str],
) -> set[str]:
    derived = set(initial)
    for child in ast.walk(node):
        targets, value, _annotation = _assignment_parts(child)
        if value is not None and (
            bool(_names_in(value) & initial)
            or any(
                _call_name(call) in _POLICY_EVIDENCE_CALLS
                for call in ast.walk(value)
                if isinstance(call, ast.Call)
            )
        ):
            derived.update(_assigned_names(targets))
    return derived


def _tainted_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    initial: set[str],
    constants: dict[str, str] | None,
) -> set[str]:
    tainted = set(initial)
    for _ in range(2):
        for child in ast.walk(node):
            targets, value, _annotation = _assignment_parts(child)
            value_is_policy = value is not None and (
                _contains_serialized_key(value, constants) or bool(_names_in(value) & tainted)
            )
            if value_is_policy:
                tainted.update(_assigned_names(targets))
    return tainted


def _return_serializes_policy(
    node: ast.Return,
    policy_names: set[str],
    tainted_names: set[str],
    evidence_names: set[str],
    constants: dict[str, str] | None,
) -> bool:
    value = node.value
    if value is None:
        return False
    if _contains_serialized_key(value, constants) or bool(
        _names_in(value) & (tainted_names | evidence_names)
    ):
        return True
    for call in (child for child in ast.walk(value) if isinstance(child, ast.Call)):
        if _call_name(call) == "asdict" and bool(
            _names_in(call) & (policy_names | evidence_names)
        ):
            return True
        if _call_name(call) in (_POLICY_CALLS | _POLICY_EVIDENCE_CALLS):
            return True
    return False


def _function_parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    return {argument.arg for argument in arguments}


def _subscript_serializes_policy(
    target: ast.AST,
    returned_names: set[str],
    parameter_names: set[str],
    constants: dict[str, str] | None,
) -> bool:
    key = _subscript_key(target, constants)
    if key is None or key.casefold() not in SERIALIZED_POLICY_KEYS:
        return False
    root_name = _root_name(target)
    return root_name in returned_names or (
        key.casefold().startswith("x-launch-") and root_name in parameter_names
    )


def _assignment_serializes_policy(
    node: ast.AST,
    returned_names: set[str],
    parameter_names: set[str],
    constants: dict[str, str] | None,
) -> bool:
    targets, _value, _annotation = _assignment_parts(node)
    return any(
        _subscript_serializes_policy(target, returned_names, parameter_names, constants)
        for target in targets
    )


def _call_serializes_policy(
    call: ast.Call,
    constants: dict[str, str] | None,
    tainted_names: set[str],
    returned_names: set[str],
) -> bool:
    if not (_contains_serialized_key(call, constants) or bool(_names_in(call) & tainted_names)):
        return False
    if _call_name(call) in {"Response", "JSONResponse"}:
        return True
    function = call.func
    if not isinstance(function, ast.Attribute) or function.attr != "update":
        return False
    if isinstance(function.value, ast.Attribute) and function.value.attr == "headers":
        return True
    return _root_name(function.value) in returned_names


def _serializes_policy(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    constants: dict[str, str] | None = None,
) -> bool:
    returned = _returned_names(node)
    policy = _policy_names(node)
    tainted = _tainted_names(node, policy, constants)
    evidence = _directly_derived_names(node, _policy_evidence_names(node))
    parameters = _function_parameter_names(node)
    return any(
        _return_serializes_policy(child, policy, tainted, evidence, constants)
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
    ) or any(
        _assignment_serializes_policy(child, returned, parameters, constants)
        for child in ast.walk(node)
        if isinstance(child, (ast.Assign, ast.AnnAssign))
    ) or any(
        _call_serializes_policy(child, constants, tainted, returned)
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
    )


def _router_definitions(modules: Sequence[_ModuleInfo]) -> dict[tuple[str, str], _RouterDef]:
    return {
        (router.module, router.variable): router
        for module in modules
        for router in module.routers.values()
    }


def _include_prefix(call: ast.Call, module: _ModuleInfo) -> str | None:
    prefix_node = next((keyword.value for keyword in call.keywords if keyword.arg == "prefix"), None)
    prefix = _literal_string(prefix_node, module.constants) if prefix_node is not None else ""
    if prefix_node is not None and prefix is None:
        module.scan_errors.append(
            Finding("POLICY_ROUTE_SCAN_ERROR", str(module.path), call.lineno, "include_router prefix is not a simple string")
        )
        return None
    return prefix or ""


def _include_edge(
    call: ast.Call,
    module: _ModuleInfo,
    router_defs: dict[tuple[str, str], _RouterDef],
) -> tuple[tuple[str, str], tuple[str, str], str] | None:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "include_router" or not call.args:
        return None
    parent = _resolve_router_reference(call.func.value, module, router_defs)
    child = _resolve_router_reference(call.args[0], module, router_defs)
    if parent is None or child is None:
        return None
    prefix = _include_prefix(call, module)
    if prefix is None:
        return None
    parent_key = (parent.module, parent.variable)
    edge_prefix = _normalise_path(parent.prefix, prefix)
    return parent_key, (child.module, child.variable), edge_prefix


def _mount_edges(
    modules: Sequence[_ModuleInfo],
    router_defs: dict[tuple[str, str], _RouterDef],
) -> dict[tuple[str, str], list[tuple[tuple[str, str], str]]]:
    edges: dict[tuple[str, str], list[tuple[tuple[str, str], str]]] = {}
    for module in modules:
        for statement in module.tree.body:
            call = statement.value if isinstance(statement, ast.Expr) else None
            if not isinstance(call, ast.Call):
                continue
            edge = _include_edge(call, module, router_defs)
            if edge is not None:
                parent_key, child_key, prefix = edge
                edges.setdefault(parent_key, []).append((child_key, prefix))
    return edges


def _mounted_prefixes(
    modules: Sequence[_ModuleInfo],
    edges: dict[tuple[str, str], list[tuple[tuple[str, str], str]]],
) -> dict[tuple[str, str], set[str]]:
    mounted = {
        (router.module, router.variable): {""}
        for module in modules
        for router in module.routers.values()
        if router.is_app
        and router.variable == _AUTHORITATIVE_APP_VARIABLE
        and module.path.name == f"{_AUTHORITATIVE_APP_MODULE}.py"
        and module.key in _AUTHORITATIVE_APP_MODULES
    }
    changed = True
    while changed:
        changed = False
        for parent_key, children in edges.items():
            for child_key, prefix in children:
                additions = {
                    _normalise_path(parent_prefix, prefix)
                    for parent_prefix in mounted.get(parent_key, set())
                } - mounted.setdefault(child_key, set())
                if additions:
                    mounted[child_key].update(additions)
                    changed = True
    return mounted


def _route_row(
    module: _ModuleInfo,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    router: _RouterDef,
    method: str,
    decorator_path: str,
    route_name: str,
    include_prefix: str,
    mounted: bool,
) -> _Route:
    return _Route(
        method=method,
        path=_normalise_path(include_prefix, router.prefix, decorator_path),
        route_name=route_name,
        file=str(module.path),
        line=function.lineno,
        policy_bearing=_serializes_policy(function, module.constants),
        mounted=mounted,
    )


def _module_routes(
    module: _ModuleInfo,
    router_defs: dict[tuple[str, str], _RouterDef],
    mounted_prefixes: dict[tuple[str, str], set[str]],
) -> list[_Route]:
    routes: list[_Route] = []
    functions = (
        node for node in ast.walk(module.tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    for function in functions:
        for router_expression, method, path, name in _route_decorator(
            function, module.constants, module.scan_errors
        ):
            router = _resolve_router_reference(router_expression, module, router_defs)
            if router is None:
                if _serializes_policy(function, module.constants):
                    module.scan_errors.append(
                        Finding(
                            "POLICY_ROUTE_SCAN_ERROR",
                            str(module.path),
                            function.lineno,
                            "policy-bearing route uses an unresolved router constructor",
                        )
                    )
                continue
            prefixes = mounted_prefixes.get((router.module, router.variable), set())
            for prefix in prefixes or {""}:
                routes.append(
                    _route_row(module, function, router, method, path, name, prefix, bool(prefixes))
                )
    return routes


def _module_scan_errors(modules: Sequence[_ModuleInfo]) -> list[Finding]:
    return [
        error if error.file else Finding(error.code, str(module.path), error.line, error.message)
        for module in modules
        for error in module.scan_errors
    ]


def _discover_routes(modules: Sequence[_ModuleInfo]) -> tuple[list[_Route], list[Finding]]:
    router_defs = _router_definitions(modules)
    mounted = _mounted_prefixes(modules, _mount_edges(modules, router_defs))
    routes = [route for module in modules for route in _module_routes(module, router_defs, mounted)]
    return routes, _module_scan_errors(modules)


def _future_allowance_state(
    allowed: set[str],
    registry_names: set[str],
    routes: Sequence[_Route],
) -> tuple[list[Finding], set[str]]:
    permitted = DECLARED_FUTURE_ROUTE_NAMES & registry_names
    invalid = allowed - permitted
    requested = allowed & permitted
    observed = {route.route_name for route in routes}
    findings = [
        Finding("INVALID_FUTURE_ALLOWANCE", "<registry>", 0, f"unsupported future route name {name!r}")
        for name in sorted(invalid)
    ]
    findings.extend(
        Finding("INVALID_FUTURE_ALLOWANCE", "<registry>", 0, f"future route {name!r} already exists")
        for name in sorted(requested & observed)
    )
    return findings, requested - observed


def _route_contract_result(
    route: _Route,
    registry_by_identity: dict[tuple[str, str, str], PolicyEndpoint],
    registry_names: set[str],
    registry_method_paths: set[tuple[str, str]],
) -> tuple[Finding | None, bool]:
    exact = registry_by_identity.get(route.identity)
    if exact is not None and route.mounted and route.policy_bearing:
        return None, True
    if exact is not None:
        reason = "route is not mounted" if not route.mounted else "registered route no longer serializes policy evidence"
        return Finding(
            "POLICY_ROUTE_CONTRACT_MISMATCH",
            route.file,
            route.line,
            f"{route.method} {route.path} ({route.route_name}) {reason}",
        ), False
    if not route.policy_bearing:
        return None, False
    related = route.route_name in registry_names or (route.method, route.path) in registry_method_paths
    code = "POLICY_ROUTE_CONTRACT_MISMATCH" if related else "UNREGISTERED_POLICY_ROUTE"
    message = (
        f"{route.method} {route.path} ({route.route_name}) does not match the registered identity"
        if related
        else f"{route.method} {route.path} ({route.route_name}) serializes policy evidence without a registry row"
    )
    return Finding(code, route.file, route.line, message), False


def _route_contract_state(
    routes: Sequence[_Route],
    registry_by_identity: dict[tuple[str, str, str], PolicyEndpoint],
    registry_names: set[str],
    registry_method_paths: set[tuple[str, str]],
) -> tuple[list[Finding], set[tuple[str, str, str]]]:
    results = [
        (route, _route_contract_result(route, registry_by_identity, registry_names, registry_method_paths))
        for route in routes
    ]
    findings = [result[0] for _route, result in results if result[0] is not None]
    exact = {route.identity for route, result in results if result[1]}
    return findings, exact


def _stale_registry_findings(
    registry: Sequence[PolicyEndpoint],
    exact_mounted: set[tuple[str, str, str]],
    valid_future: set[str],
) -> list[Finding]:
    return [
        Finding(
            "STALE_POLICY_REGISTRY_ENTRY",
            "agent/policy_http.py",
            0,
            f"{endpoint.method} {endpoint.path} ({endpoint.route_name}) has no exact mounted policy route",
        )
        for endpoint in registry
        if (endpoint.method, endpoint.path, endpoint.route_name) not in exact_mounted
        and endpoint.route_name not in valid_future
    ]


def scan_policy_routes(
    source_files: Iterable[Path],
    endpoints: Iterable[PolicyEndpoint],
    *,
    allowed_future: set[str] | None = None,
) -> list[Finding]:
    paths = [Path(path).resolve() for path in source_files]
    registry = tuple(endpoints)
    allowed = set(allowed_future or set())
    if not paths:
        return []
    source_root = _common_source_root(paths)
    modules = [_parse_module(path, source_root) for path in paths]
    routes, scan_errors = _discover_routes(modules)
    registry_by_identity = {
        (row.method, row.path, row.route_name): row
        for row in registry
    }
    registry_names = {row.route_name for row in registry}
    registry_method_paths = {(row.method, row.path) for row in registry}

    future_findings, valid_future = _future_allowance_state(allowed, registry_names, routes)
    route_findings, exact_mounted = _route_contract_state(
        routes, registry_by_identity, registry_names, registry_method_paths
    )
    return [
        *scan_errors,
        *future_findings,
        *route_findings,
        *_stale_registry_findings(registry, exact_mounted, valid_future),
    ]


class PolicyHttpRegistryCheck:
    name, level, rule = "policy_http_registry", "hard", "R20.9"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        if files is not None and not any(
            file.replace("\\", "/").startswith("agent/")
            or file.replace("\\", "/") == "scripts/checks/check_policy_http_registry.py"
            for file in files
        ):
            return self._result([])
        findings = scan_policy_routes(
            agent_source_files(self.root / "agent"),
            POLICY_ENDPOINTS,
            allowed_future={"launch_policy_attestation", "launch_sitemap_document"},
        )
        violations = [
            {
                "file": finding.file,
                "line": finding.line,
                "rule": self.rule,
                "msg": f"{finding.code}: {finding.message}",
            }
            for finding in findings
        ]
        return self._result(violations)

    def _result(self, violations: list[dict]) -> dict:
        return {
            "check": self.name,
            "level": self.level,
            "rule": self.rule,
            "count": len(violations),
            "violations": violations,
        }


CHECKS = [PolicyHttpRegistryCheck()]


def _validate_allow_future(values: list[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    known = DECLARED_FUTURE_ROUTE_NAMES
    for value in values:
        if value in seen:
            errors.append(f"duplicate future route name {value!r}")
        elif value not in known:
            errors.append(f"unknown future route name {value!r}")
        seen.add(value)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-future", action="append", default=[])
    args = parser.parse_args()
    allowance_errors = _validate_allow_future(args.allow_future)
    if allowance_errors:
        for error in allowance_errors:
            print(f"INVALID_FUTURE_ALLOWANCE: {error}", file=sys.stderr)
        return 2
    root = repo_root()
    findings = scan_policy_routes(
        agent_source_files(root / "agent"),
        POLICY_ENDPOINTS,
        allowed_future=set(args.allow_future),
    )
    if findings:
        for finding in findings:
            print(f"{finding.code} {finding.file}:{finding.line} - {finding.message}")
        return 1
    print("policy HTTP registry: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
