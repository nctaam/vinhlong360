"""Source guard preventing owner-linked stores from bypassing admission."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    # These modules are paired with this source-inspection test for R20.7.
    import ab_testing
    import analytics
    import cost_tracker
    import experience_memory
    import feedback_policy
    import memory
    import memory_graph
    import prompt_compiler
    import self_optimizer
    import semantic_cache
    import server

    _PAIRING_MODULES = (
        ab_testing,
        analytics,
        cost_tracker,
        experience_memory,
        feedback_policy,
        memory,
        memory_graph,
        prompt_compiler,
        self_optimizer,
        semantic_cache,
        server,
    )


ROOT = Path(__file__).resolve().parents[2]
GATE_CALL = "owner_write_gate.assert_writable"


def _scope_source(relative_path: str, qualified_name: str) -> str:
    path = ROOT / relative_path
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    parts = qualified_name.split(".")
    nodes = tree.body
    node = None
    for part in parts:
        node = next(
            item
            for item in nodes
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == part
        )
        nodes = node.body if isinstance(node, ast.ClassDef) else []
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno])


SINKS = [
    ("agent/memory.py", "ColdMemory.get_profile", "self._profiles[user_id] ="),
    ("agent/memory.py", "ColdMemory.update_profile_from_session", "self._save_all()"),
    ("agent/memory.py", "ColdMemory.record_feedback", "self._save_all()"),
    ("agent/memory.py", "ColdMemory.add_semantic_fact", "self._save_all()"),
    ("agent/memory.py", "MemoryExtractor.on_conversation_turn", "cold_memory._save_all()"),
    ("agent/memory.py", "MemoryManager.create_session", "self._sessions[key] ="),
    ("agent/memory.py", "MemoryManager.on_message", "session.add_message"),
    ("agent/memory.py", "MemoryManager.on_entity_discussed", "entities_discussed.append"),
    ("agent/memory.py", "MemoryManager.on_session_end", "update_profile_from_session"),
    ("agent/memory.py", "MemoryManager.on_chat_complete", "on_conversation_turn"),
    ("agent/memory.py", "MemoryManager.feedback", "record_feedback"),
    ("agent/memory_graph.py", "MemoryGraph.record_interaction", "self.add_node"),
    ("agent/memory_graph.py", "MemoryGraph.record_preference", "self.add_node"),
    ("agent/memory_graph.py", "MemoryGraph.record_comparison", "self.add_node"),
    ("agent/memory_graph.py", "MemoryGraph.on_chat_complete", "self.record_interaction"),
    ("agent/semantic_cache.py", "MultiTierCache.put", "self._l1[key] ="),
    ("agent/semantic_cache.py", "RequestDeduplicator.acquire", "self._pending[generation_key] ="),
    ("agent/semantic_cache.py", "RequestDeduplicator.resolve", 'slot["result"] ='),
    ("agent/semantic_cache.py", "RequestDeduplicator.resolve_if_active", 'slot["result"] ='),
    ("agent/semantic_cache.py", "RequestDeduplicator.publish_if_active", "publish_fn()"),
    ("agent/semantic_cache.py", "RequestDeduplicator.publish_active", "publish_fn()"),
    ("agent/semantic_cache.py", "semantic_put", "multi_tier_cache.put"),
    ("agent/analytics.py", "track_query", 'data["queries"].append'),
    ("agent/analytics.py", "save_conversation", "tmp.replace"),
    ("agent/cost_tracker.py", "CostAttribution.record", "self._records.append"),
    ("agent/self_optimizer.py", "PerformanceCollector.record", "self._records.append"),
    ("agent/experience_memory.py", "record", "_save(items)"),
    ("agent/prompt_compiler.py", "record_demo", "_save(RAW_FILE, pool)"),
    ("agent/ab_testing.py", "ABTestManager.record_outcome", "self._save()"),
    ("agent/feedback_policy.py", "PostgresFeedbackStore.issue", "db._execute"),
    ("agent/server.py", "chat", "cache.put"),
    ("agent/server.py", "chat_stream", "cache.put"),
]


@pytest.mark.parametrize(("relative_path", "qualified_name", "write_marker"), SINKS)
def test_owner_linked_sink_checks_gate_before_write(
    relative_path, qualified_name, write_marker
):
    """Removing or moving the gate after persistence must fail this guard."""
    source = _scope_source(relative_path, qualified_name)
    gate_index = source.find(GATE_CALL)
    write_index = source.find(write_marker)
    assert gate_index >= 0, f"{relative_path}:{qualified_name} bypasses owner gate"
    assert write_index >= 0, f"{relative_path}:{qualified_name} marker missing"
    assert gate_index < write_index, (
        f"{relative_path}:{qualified_name} checks owner only after persistence"
    )


def test_aggregate_analytics_writes_remain_outside_owner_gate():
    """Deidentified counters must not become unavailable during account deletion."""
    for function_name in ("track_entity_hit", "track_session"):
        source = _scope_source("agent/analytics.py", function_name)
        assert GATE_CALL not in source
