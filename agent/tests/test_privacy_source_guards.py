from __future__ import annotations

import ast
from pathlib import Path

import server


SERVER_PATH = Path(server.__file__).resolve()
SERVER_SOURCE = SERVER_PATH.read_text(encoding="utf-8")
SERVER_TREE = ast.parse(SERVER_SOURCE)

PERSISTENCE_SINKS = (
    "settle_usage()",
    "usage_accumulator.settle(",
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
FORBIDDEN_FEEDBACK_TOKENS = (
    "memory_manager.feedback(",
    "record_feedback(query=",
    "data.json",
)


def _handler_source(name: str) -> str:
    node = next(
        item
        for item in SERVER_TREE.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    lines = SERVER_SOURCE.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1:node.end_lineno])


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
        marker = source.index("_privacy_output_boundary_marker = True")
        for sink in PERSISTENCE_SINKS:
            sink_index = source.find(sink)
            if sink_index >= 0:
                covered_sinks.add(sink)
                assert marker < sink_index, f"{route_name}: {sink} precedes output boundary"
    assert covered_sinks == set(PERSISTENCE_SINKS), (
        "source guard is not exercising sinks: "
        f"{sorted(set(PERSISTENCE_SINKS) - covered_sinks)}"
    )


def test_feedback_handler_contains_no_personalization_or_data_mutation_tokens():
    source = _handler_source("user_feedback")
    for token in FORBIDDEN_FEEDBACK_TOKENS:
        assert token not in source, token


def test_readiness_uses_mandatory_privacy_boundary_health_function():
    source = _handler_source("readiness_probe")
    assert '"privacy_boundary": privacy_boundary_readiness()' in source
    assert '"privacy_boundary": True' not in source
