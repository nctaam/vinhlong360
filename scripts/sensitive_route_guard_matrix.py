#!/usr/bin/env python3
"""Static guard matrix for internal/sensitive backend routes.

This intentionally avoids importing the FastAPI app. It parses server.py and
checks that the central gate middleware still covers every sensitive route
that release smoke depends on.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "agent" / "server.py"


@dataclass(frozen=True)
class GuardCheck:
    route: str
    reason: str
    path: str
    prefix: bool = False


@dataclass(frozen=True)
class EndpointGuardCheck:
    route: str
    method: str
    function: str
    reason: str
    scope: str


CHECKS = [
    GuardCheck("/metrics", "Prometheus metrics", "/metrics"),
    GuardCheck("/vectors/stats", "Vector internals", "/vectors/stats"),
    GuardCheck("/system/*", "System logs, traces, costs, judges, agents", "/system", True),
    GuardCheck("/analytics/*", "Internal analytics summaries", "/analytics", True),
    GuardCheck("/checkpoints/*", "Checkpoint state", "/checkpoints", True),
    GuardCheck("/confirmations/*", "Confirmation state", "/confirmations", True),
    GuardCheck("/confirm/*", "Write confirmation shortcut", "/confirm/", True),
    GuardCheck("/reject/*", "Write rejection shortcut", "/reject/", True),
    GuardCheck("/ab-testing/*", "Experiment internals", "/ab-testing", True),
    GuardCheck("/prompt-cache/*", "Prompt cache internals", "/prompt-cache", True),
    GuardCheck("/freshness/*", "Freshness scanner internals", "/freshness", True),
]

ENDPOINT_CHECKS = [
    EndpointGuardCheck(
        "/vectors/build",
        "post",
        "build_vectors",
        "Embedding rebuild is compute-heavy and internal",
        "ops.deploy",
    ),
    EndpointGuardCheck(
        "/vectors/search",
        "get",
        "vector_search_endpoint",
        "Raw vector scoring must not be a public discovery API",
        "ops.deploy",
    ),
    EndpointGuardCheck(
        "/image/recognize",
        "post",
        "image_recognize_endpoint",
        "Vision calls can spend LLM budget",
        "ops.deploy",
    ),
]


def _target_contains_name(target: ast.expr, name: str) -> bool:
    if isinstance(target, ast.Name):
        return target.id == name
    if isinstance(target, (ast.List, ast.Tuple)):
        return any(_target_contains_name(item, name) for item in target.elts)
    return False


class _GlobalDeclarationFinder(ast.NodeVisitor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.found = False

    def visit_Global(self, node: ast.Global) -> None:
        if self.name in node.names:
            self.found = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef


def _scope_declares_global(body: list[ast.stmt], name: str) -> bool:
    finder = _GlobalDeclarationFinder(name)
    for statement in body:
        finder.visit(statement)
    return finder.found


class _ModuleAssignmentCollector(ast.NodeVisitor):
    """Collect bindings that can replace a protected module route table."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.nodes: list[ast.AST] = []
        self._module_binding_scope = [True]

    @property
    def _changes_module(self) -> bool:
        return self._module_binding_scope[-1]

    def _record_targets(self, node: ast.AST, targets: list[ast.expr]) -> None:
        if self._changes_module and any(
            _target_contains_name(target, self.name) for target in targets
        ):
            self.nodes.append(node)

    def _visit_outer_scope_fields(self, node: ast.AST) -> None:
        for field, value in ast.iter_fields(node):
            if field == "body":
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)

    def _visit_nested_scope(self, body: list[ast.stmt]) -> None:
        self._module_binding_scope.append(_scope_declares_global(body, self.name))
        for statement in body:
            self.visit(statement)
        self._module_binding_scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_targets(node, node.targets)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_targets(node, [node.target])
        if node.value is not None:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._record_targets(node, [node.target])
        self.visit(node.value)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._record_targets(node, [node.target])
        self.visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self._record_targets(node, [node.target])
        self.visit(node.iter)
        for statement in (*node.body, *node.orelse):
            self.visit(statement)

    visit_AsyncFor = visit_For

    def visit_With(self, node: ast.With) -> None:
        targets = [item.optional_vars for item in node.items if item.optional_vars]
        self._record_targets(node, targets)
        for item in node.items:
            self.visit(item.context_expr)
        for statement in node.body:
            self.visit(statement)

    visit_AsyncWith = visit_With

    def visit_Delete(self, node: ast.Delete) -> None:
        self._record_targets(node, node.targets)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._changes_module and node.name == self.name:
            self.nodes.append(node)
        self._visit_outer_scope_fields(node)
        self._visit_nested_scope(node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._changes_module and node.name == self.name:
            self.nodes.append(node)
        self._visit_outer_scope_fields(node)
        self._visit_nested_scope(node.body)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_outer_scope_fields(node)

    def visit_Import(self, node: ast.Import) -> None:
        bound_names = [alias.asname or alias.name.split(".", 1)[0] for alias in node.names]
        if self._changes_module and self.name in bound_names:
            self.nodes.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        bound_names = [alias.asname or alias.name for alias in node.names]
        if self._changes_module and (self.name in bound_names or "*" in bound_names):
            self.nodes.append(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if self._changes_module and node.name == self.name:
            self.nodes.append(node)
        if node.type is not None:
            self.visit(node.type)
        for statement in node.body:
            self.visit(statement)


def _literal_path_table(
    module: ast.Module, name: str, failures: list[str]
) -> set[str]:
    collector = _ModuleAssignmentCollector(name)
    collector.visit(module)
    assignments = collector.nodes
    if len(assignments) != 1:
        failures.append(f"{name} must have one literal assignment")
        return set()

    assignment = assignments[0]
    if not (
        isinstance(assignment, ast.Assign)
        and len(assignment.targets) == 1
        and isinstance(assignment.targets[0], ast.Name)
        and assignment.targets[0].id == name
        and isinstance(assignment.value, (ast.List, ast.Tuple, ast.Set))
        and all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in assignment.value.elts
        )
    ):
        failures.append(f"{name} must have one literal assignment")
        return set()
    return {item.value for item in assignment.value.elts}


def _top_level_functions(
    module: ast.Module, name: str
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _is_request_path(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "path"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "url"
        and _is_name(node.value.value, "request")
    )


def _matches_exact_membership(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and _is_name(node.left, "path")
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.In)
        and len(node.comparators) == 1
        and _is_name(node.comparators[0], "_GATED_EXACT_PATHS")
    )


def _prefix_generator(node: ast.AST) -> ast.GeneratorExp | None:
    if not isinstance(node, ast.Call):
        return None
    if len(node.args) != 1 or node.keywords:
        return None
    if not all((_is_name(node.func, "any"), isinstance(node.args[0], ast.GeneratorExp))):
        return None
    return node.args[0]


def _matches_prefix_startswith(node: ast.AST, target_name: str | None) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    if len(node.args) != 1 or node.keywords:
        return False
    return all(
        (
            node.func.attr == "startswith",
            _is_name(node.func.value, "path"),
            _is_name(node.args[0], target_name),
        )
    )


def _matches_prefix_comprehension(generator: ast.GeneratorExp) -> bool:
    if len(generator.generators) != 1:
        return False
    comprehension = generator.generators[0]
    target_name = comprehension.target.id if isinstance(comprehension.target, ast.Name) else None
    return target_name is not None and all(
        (
            _is_name(comprehension.iter, "_GATED_PREFIX_PATHS"),
            not comprehension.ifs,
            not comprehension.is_async,
            _matches_prefix_startswith(generator.elt, target_name),
        )
    )


def _matches_prefix_membership(node: ast.AST) -> bool:
    generator = _prefix_generator(node)
    return generator is not None and _matches_prefix_comprehension(generator)


def _matches_gate_helper(function: ast.FunctionDef) -> bool:
    body = list(function.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    value = body[0].value
    if not isinstance(value, ast.BoolOp) or not isinstance(value.op, ast.Or):
        return False
    return len(value.values) == 2 and any(
        _matches_exact_membership(first) and _matches_prefix_membership(second)
        for first, second in (value.values, tuple(reversed(value.values)))
    )


def _matches_app_decorator(node: ast.AST, method: str, route: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
        and _is_name(node.func.value, "app")
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == route
    )


def _matches_gate_condition(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_name(node.func, "_is_gated_path")
        and len(node.args) == 1
        and _is_request_path(node.args[0])
        and not node.keywords
    )


def _matches_admin_rejection(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.Not)
        and isinstance(node.operand, ast.Call)
        and _is_name(node.operand.func, "verify_admin_key")
        and len(node.operand.args) == 1
        and _is_name(node.operand.args[0], "request")
        and not node.operand.keywords
    )


def _returns_status_code(statement: ast.stmt, status_code: int) -> bool:
    if not isinstance(statement, ast.Return) or not isinstance(statement.value, ast.Call):
        return False
    return any(
        keyword.arg == "status_code"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == status_code
        for keyword in statement.value.keywords
    )


def _check_gate_helper(module: ast.Module, failures: list[str]) -> None:
    helpers = _top_level_functions(module, "_is_gated_path")
    if len(helpers) != 1 or not isinstance(helpers[0], ast.FunctionDef):
        failures.append("missing synchronous _is_gated_path helper")
    elif not _matches_gate_helper(helpers[0]):
        failures.append("_is_gated_path must return exact-or-prefix membership")


def _gate_middleware(module: ast.Module) -> ast.AsyncFunctionDef | None:
    gates = _top_level_functions(module, "gate_internal_endpoints")
    if len(gates) != 1 or not isinstance(gates[0], ast.AsyncFunctionDef):
        return None
    return gates[0]


def _has_http_middleware(gate: ast.AsyncFunctionDef) -> bool:
    return any(
        _matches_app_decorator(decorator, "middleware", "http")
        for decorator in gate.decorator_list
    )


def _matching_gate_branches(
    body: list[ast.stmt], predicate: Callable[[ast.AST], bool]
) -> list[ast.If]:
    return [
        statement
        for statement in _reachable_block_prefix(body)
        if isinstance(statement, ast.If) and predicate(statement.test)
    ]


class _FunctionExitFinder(ast.NodeVisitor):
    def __init__(self) -> None:
        self.found = False

    def visit_Return(self, node: ast.Return) -> None:
        self.found = True

    visit_Raise = visit_Return

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef


def _contains_function_exit(statement: ast.stmt) -> bool:
    finder = _FunctionExitFinder()
    finder.visit(statement)
    return finder.found


def _reachable_block_prefix(body: list[ast.stmt]) -> list[ast.stmt]:
    reachable: list[ast.stmt] = []
    for statement in body:
        reachable.append(statement)
        if _contains_function_exit(statement):
            break
    return reachable


def _check_gate_integrity(module: ast.Module, failures: list[str]) -> None:
    _check_gate_helper(module, failures)
    gate = _gate_middleware(module)
    if gate is None:
        failures.append("missing gate_internal_endpoints middleware")
        return
    if not _has_http_middleware(gate):
        failures.append("gate_internal_endpoints must be registered as HTTP middleware")

    gated_branches = _matching_gate_branches(gate.body, _matches_gate_condition)
    if len(gated_branches) != 1:
        failures.append("gate_internal_endpoints must enforce the gated-path 404 branch")
        return

    admin_branches = _matching_gate_branches(
        gated_branches[0].body, _matches_admin_rejection
    )
    if len(admin_branches) != 1:
        failures.append("gate_internal_endpoints must verify the admin key")
        return
    if not any(
        _returns_status_code(statement, 404)
        for statement in _reachable_block_prefix(admin_branches[0].body)
    ):
        failures.append("gate_internal_endpoints must hide sensitive paths with 404")


def _check_prefix_guards(module: ast.Module, failures: list[str]) -> None:
    exact_paths = _literal_path_table(module, "_GATED_EXACT_PATHS", failures)
    prefix_paths = _literal_path_table(module, "_GATED_PREFIX_PATHS", failures)
    for check in CHECKS:
        guarded_paths = prefix_paths if check.prefix else exact_paths
        ok = check.path in guarded_paths
        print(f"{'OK' if ok else 'FAIL'} {check.route:20} {check.reason}")
        if not ok:
            kind = "prefix" if check.prefix else "exact"
            failures.append(f"{check.route} missing {kind} path {check.path}")


def _matches_endpoint_guard(statement: ast.stmt, scope: str) -> bool:
    if not (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Await)
        and isinstance(statement.value.value, ast.Call)
    ):
        return False
    call = statement.value.value
    return (
        _is_name(call.func, "require_admin_scope")
        and len(call.args) == 2
        and _is_name(call.args[0], "request")
        and isinstance(call.args[1], ast.Constant)
        and call.args[1].value == scope
        and not call.keywords
    )


def _check_endpoint_guards(module: ast.Module, failures: list[str]) -> None:
    for check in ENDPOINT_CHECKS:
        functions = _top_level_functions(module, check.function)
        function = functions[0] if len(functions) == 1 else None
        ok = (
            isinstance(function, ast.AsyncFunctionDef)
            and any(
                _matches_app_decorator(decorator, check.method, check.route)
                for decorator in function.decorator_list
            )
            and any(
                _matches_endpoint_guard(statement, check.scope)
                for statement in _reachable_block_prefix(function.body)
            )
        )
        print(f"{'OK' if ok else 'FAIL'} {check.route:20} {check.reason}")
        if not ok:
            failures.append(
                f"{check.route} must be async, decorated with @{check.method}, "
                f"and await require_admin_scope(request, {check.scope!r})"
            )


def _report_failures(failures: list[str]) -> int:
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


def main() -> int:
    source = SERVER.read_text(encoding="utf-8", errors="replace")
    print("Sensitive route guard matrix")
    print("============================")
    try:
        module = ast.parse(source)
    except SyntaxError as error:
        return _report_failures(
            [f"server.py syntax error at line {error.lineno}: {error.msg}"]
        )

    failures: list[str] = []
    _check_gate_integrity(module, failures)
    _check_prefix_guards(module, failures)
    _check_endpoint_guards(module, failures)
    return _report_failures(failures)


if __name__ == "__main__":
    raise SystemExit(main())
