from __future__ import annotations

import ast
from pathlib import Path

import server


SERVER_PATH = Path(server.__file__).resolve()
SERVER_SOURCE = SERVER_PATH.read_text(encoding="utf-8")
SERVER_TREE = ast.parse(SERVER_SOURCE)

USAGE_SINKS = (
    "settle_usage()",
    "usage_accumulator.settle(",
)
CONTENT_SINKS = (
    "_record_cached_exchange(",
    "memory_manager.on_message(",
    "memory_graph.on_chat_complete(",
    "memory_manager.on_chat_complete(",
    "memory_manager.on_good_answer(",
    "quality_tracker.record(",
    "experience_memory.record(",
    "prompt_compiler.record_demo(",
    "record_outcome(",
    "ab_manager.record_outcome(",
    "analytics.track_query(",
    "cache.put(",
    "semantic_put(",
)
PERSISTENCE_SINKS = USAGE_SINKS + CONTENT_SINKS
FORBIDDEN_FEEDBACK_TOKENS = (
    "memory_manager.feedback(",
    "record_feedback(",
    "save_feedback(",
    "_adjust_entity_confidence(",
    "sync_data_json_to_js(",
    "data.json",
)
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}
LIFECYCLE_LOG_SCOPES = (
    ("auth.py", "delete_account"),
    ("erasure.py", "_observe_failure"),
    ("scheduler.py", "task_account_erasure"),
    ("scheduler.py", "task_quarantine_retry"),
)
SENSITIVE_LOG_NAMES = {
    "e",
    "exc",
    "exception",
    "owner_key",
    "phone",
    "query",
    "receipt",
    "reply",
    "uid",
    "user_id",
}


def _handler_source(name: str) -> str:
    node = next(
        item
        for item in SERVER_TREE.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    lines = SERVER_SOURCE.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1:node.end_lineno])


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _module_function(relative_path: str, function_name: str):
    path = SERVER_PATH.parent / relative_path
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item
        for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == function_name
    )
    return source, node


def _log_call_contains_subject(call: ast.Call) -> bool:
    for node in ast.walk(call):
        if isinstance(node, ast.Name) and node.id in SENSITIVE_LOG_NAMES:
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "user"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "id"
        ):
            return True
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "user"
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "id"
        ):
            return True
    return False


def _content_sink_names() -> set[str]:
    return {sink.removesuffix("(") for sink in CONTENT_SINKS}


def _statement_sink_calls(statement: ast.stmt) -> list[tuple[str, int]]:
    calls = []
    for node in ast.walk(statement):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in _content_sink_names():
                calls.append((name, node.lineno))
    return calls


def _undominated_content_sinks(source: str) -> list[str]:
    route = ast.parse(source).body[0]
    violations = []

    def scan_block(statements: list[ast.stmt], boundary_seen: bool, scope: str) -> None:
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scan_block(statement.body, False, f"{scope}.{statement.name}")
                continue
            if isinstance(statement, ast.If):
                scan_block(statement.body, boundary_seen, scope)
                scan_block(statement.orelse, boundary_seen, scope)
                continue
            if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                scan_block(statement.body, boundary_seen, scope)
                scan_block(statement.orelse, boundary_seen, scope)
                continue
            if isinstance(statement, ast.Try):
                scan_block(statement.body, boundary_seen, scope)
                for handler in statement.handlers:
                    scan_block(handler.body, boundary_seen, scope)
                scan_block(statement.orelse, boundary_seen, scope)
                scan_block(statement.finalbody, boundary_seen, scope)
                continue
            if isinstance(statement, (ast.With, ast.AsyncWith)):
                scan_block(statement.body, boundary_seen, scope)
                continue
            if isinstance(statement, ast.Match):
                for case in statement.cases:
                    scan_block(case.body, boundary_seen, scope)
                continue

            for sink, line in _statement_sink_calls(statement):
                if not boundary_seen:
                    violations.append(f"{scope}:{line}: {sink}")
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = (
                    statement.targets
                    if isinstance(statement, ast.Assign)
                    else [statement.target]
                )
                if any(
                    isinstance(target, ast.Name)
                    and target.id == "_privacy_output_boundary_marker"
                    for target in targets
                ):
                    boundary_seen = True

    scan_block(route.body, False, route.name)
    return violations


def test_chat_route_tails_never_read_raw_request_content():
    for route_name in ("chat", "chat_stream"):
        source = _handler_source(route_name)
        marker = source.index("_privacy_input_boundary_marker = True")
        tail = source[marker:]
        assert "req.message" not in tail, route_name
        assert "req.history" not in tail, route_name


def test_chat_persistence_sinks_follow_an_output_boundary_marker():
    covered_sinks = set()
    for route_name in ("chat", "chat_stream"):
        source = _handler_source(route_name)
        input_marker = source.index("_privacy_input_boundary_marker = True")
        for sink in PERSISTENCE_SINKS:
            if sink in source:
                covered_sinks.add(sink)
        # Usage settlement persists only safe input plus aggregate token counts and
        # must remain available on cancellation before a delivered output exists.
        for sink in USAGE_SINKS:
            sink_index = source.find(sink)
            if sink_index >= 0:
                assert input_marker < sink_index, route_name
        assert not _undominated_content_sinks(source), route_name
    assert covered_sinks == set(PERSISTENCE_SINKS), (
        "source guard is not exercising sinks: "
        f"{sorted(set(PERSISTENCE_SINKS) - covered_sinks)}"
    )


def test_output_boundary_scanner_rejects_sink_in_unmarked_sibling_path():
    source = """
async def route():
    if cached:
        _privacy_output_boundary_marker = True
        cache.put('safe')
        return
    analytics.track_query('unsafe')
"""
    assert _undominated_content_sinks(source) == [
        "route:7: analytics.track_query"
    ]


def test_feedback_handler_contains_no_personalization_or_data_mutation_tokens():
    source = _handler_source("user_feedback")
    for token in FORBIDDEN_FEEDBACK_TOKENS:
        assert token not in source, token


def test_feedback_request_has_only_receipt_and_rating_fields():
    assert set(server.FeedbackRequest.model_fields) == {"receipt", "rating"}
    assert server.FeedbackRequest.model_config["extra"] == "forbid"


def test_readiness_uses_mandatory_privacy_boundary_health_function():
    source = _handler_source("readiness_probe")
    assert '"privacy_boundary": privacy_boundary_readiness()' in source
    assert '"privacy_boundary": True' not in source


def test_erasure_lifecycle_logs_use_bounded_subject_free_diagnostics():
    violations = []
    for relative_path, function_name in LIFECYCLE_LOG_SCOPES:
        source, function = _module_function(relative_path, function_name)
        for node in ast.walk(function):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node.func).rsplit(".", 1)[-1] not in LOG_METHODS:
                continue
            if _log_call_contains_subject(node):
                segment = ast.get_source_segment(source, node) or "logging call"
                violations.append(f"{relative_path}:{node.lineno}: {segment}")

    assert violations == []
