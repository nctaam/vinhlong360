"""Cross-task source guards for the verified erasure lifecycle."""

from __future__ import annotations

import ast
from pathlib import Path

import data_lifecycle


ROOT = Path(__file__).resolve().parents[2]
GATE_CALL = "owner_write_gate.assert_writable"
OWNER_GATE_FILES = {
    "hot_memory": "agent/memory.py",
    "cold_memory": "agent/memory.py",
    "memory_graph": "agent/memory_graph.py",
    "exact_cache": "agent/server.py",
    "semantic_cache": "agent/semantic_cache.py",
    "semantic_leases": "agent/semantic_cache.py",
    "pending_feedback_receipts": "agent/feedback_policy.py",
    "feedback_receipts": "agent/feedback_policy.py",
    "owner_analytics": "agent/analytics.py",
    "conversation_history": "agent/analytics.py",
    "guardrail_budget": "agent/guardrails.py",
    "cost_attribution": "agent/cost_tracker.py",
    "optimizer_records": "agent/self_optimizer.py",
    "experience_memory": "agent/experience_memory.py",
    "prompt_demonstrations": "agent/prompt_compiler.py",
    "ab_outcomes": "agent/ab_testing.py",
}
FORBIDDEN_RETAINED_FIELDS = {
    "owner_key",
    "user_id",
    "session_id",
    "query",
    "response",
    "receipt",
}


def _function_source(relative_path: str, function_name: str) -> str:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item
        for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == function_name
    )
    return ast.get_source_segment(source, node) or ""


def test_every_registered_subject_store_has_an_owner_gate_source_contract():
    assert set(OWNER_GATE_FILES) == set(data_lifecycle.EXPECTED_SUBJECT_STORES)
    for store_name, relative_path in OWNER_GATE_FILES.items():
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert GATE_CALL in source, f"{store_name} has no owner write gate"


def test_scheduler_contains_no_account_lifecycle_mutation_sql():
    source = (ROOT / "agent" / "scheduler.py").read_text(encoding="utf-8")
    assert "DELETE FROM users" not in source
    assert "UPDATE users SET deleted_at" not in source
    for function_name in (
        "_legacy_deadline_impact",
        "task_account_erasure",
        "task_quarantine_retry",
    ):
        function_source = _function_source("agent/scheduler.py", function_name)
        assert "timedelta(days=30)" not in function_source
        assert "INTERVAL '30 days'" not in function_source


def test_reactivate_user_delegates_without_direct_deletion_state_reset():
    source = _function_source("agent/auth.py", "_reactivate_user")
    assert "recover_account(" in source
    assert "deleted_at = NULL" not in source
    assert "erasure_due_at = NULL" not in source
    assert "is_active = TRUE" not in source
    assert "db._execute" not in source


def test_retained_aggregate_stores_have_no_subject_linkage_or_fields():
    retained = [
        policy
        for policy in data_lifecycle.lifecycle_registry.policies
        if policy.classification in {"aggregate", "operational"}
    ]
    assert retained
    for policy in retained:
        assert policy.subject_linked is False, policy.name
        assert policy.purge is None, policy.name
        assert policy.verify is None, policy.name
        assert policy.retained_fields, policy.name
        assert not FORBIDDEN_RETAINED_FIELDS.intersection(policy.retained_fields), (
            policy.name
        )
