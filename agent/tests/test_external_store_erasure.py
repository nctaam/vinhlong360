"""Exact-owner purge and verification behavior for external stores."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from threading import Event, Thread

import ab_testing
import analytics
import cache as exact_cache
import cost_tracker
import data_lifecycle
import experience_memory
import feedback_policy
import guardrails
import memory
import memory_graph
import prompt_compiler
import self_optimizer
import semantic_cache


OWNER = "user:alice"
OTHER = "user:bob"


def test_hot_and_cold_memory_purge_exact_owner_idempotently(tmp_path):
    manager = memory.MemoryManager()
    manager.cold._profiles_file = tmp_path / "profiles.json"
    manager.cold._profiles.clear()

    alice_session = manager.create_session(OWNER)
    manager.create_session(OTHER)
    manager.on_message(OWNER, alice_session.session_id, "user", "private")
    manager.cold.get_profile(OWNER)
    manager.cold.get_profile(OTHER)
    manager.cold._save_all()

    assert manager.purge_owner(OWNER) == 1
    assert manager.purge_owner(OWNER) == 0
    assert manager.verify_owner_absent(OWNER) is True
    assert manager.require_session(OTHER, next(
        session_id for owner, session_id in manager._sessions if owner == OTHER
    ))

    assert manager.cold.purge_owner(OWNER) == 1
    assert manager.cold.purge_owner(OWNER) == 0
    assert manager.cold.verify_owner_absent(OWNER) is True
    assert manager.cold.find_profile(OTHER) is not None


def test_memory_graph_purge_removes_only_exact_owner_node_and_edges(tmp_path):
    graph = memory_graph.MemoryGraph(
        graph_path=tmp_path / "graph.json",
        auto_save_every=100,
    )
    graph.record_interaction(OWNER, ["entity-a"])
    graph.record_interaction(OTHER, ["entity-a"])
    graph.save()

    assert graph.purge_owner(OWNER) == 2
    assert graph.purge_owner(OWNER) == 0
    assert graph.verify_owner_absent(OWNER) is True
    assert graph.get_node(OTHER) is not None
    assert graph.get_node("entity-a") is not None


def test_semantic_cache_and_lease_purge_are_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_cache, "ENTRIES_FILE", tmp_path / "entries.json")
    matcher = semantic_cache.SemanticMatcher()
    cache = semantic_cache.MultiTierCache(matcher=matcher)
    cache.put("same query", {"owner": "alice"}, owner_key=OWNER)
    cache.put("same query", {"owner": "bob"}, owner_key=OTHER)

    assert cache.purge_owner(OWNER) == 1
    assert cache.purge_owner(OWNER) == 0
    assert cache.verify_owner_absent(OWNER) is True
    assert cache.get("same query", owner_key=OTHER) == {"owner": "bob"}

    leases = semantic_cache.RequestDeduplicator()
    leases.acquire("same query", owner_key=OWNER)
    leases.acquire("same query", owner_key=OTHER)
    assert leases.purge_owner(OWNER) == 1
    assert leases.purge_owner(OWNER) == 0
    assert leases.verify_owner_absent(OWNER) is True
    assert leases.verify_owner_absent(OTHER) is False


def test_lease_purge_wakes_sync_and_async_waiters():
    leases = semantic_cache.RequestDeduplicator()
    _, sync_key = leases.acquire("sync query", owner_key=OWNER)
    started = Event()
    result = {}

    def wait_sync():
        started.set()
        result["sync"] = leases.wait_for(sync_key, timeout=5)

    thread = Thread(target=wait_sync)
    thread.start()
    assert started.wait(timeout=1)
    assert leases.purge_owner(OWNER) == 1
    thread.join(timeout=1)

    assert thread.is_alive() is False
    assert result["sync"] is None

    async def wait_async():
        _, async_key = leases.acquire("async query", owner_key=OWNER)
        waiter = asyncio.create_task(leases.wait_for_async(async_key, timeout=5))
        await asyncio.sleep(0)
        assert leases.purge_owner(OWNER) == 1
        return await asyncio.wait_for(waiter, timeout=1)

    assert asyncio.run(wait_async()) is None


def test_exact_cache_registry_adapter_matches_hashed_owner_namespace(monkeypatch):
    monkeypatch.setattr(exact_cache, "_redis_initialized", True)
    monkeypatch.setattr(exact_cache, "_use_redis", False)
    exact_cache._cache.clear()
    exact_cache.put("same query", {"owner": "alice"}, owner_key=OWNER)
    exact_cache.put("same query", {"owner": "bob"}, owner_key=OTHER)
    policy = data_lifecycle.lifecycle_registry.get("exact_cache")

    first = policy.purge_owner(OWNER)
    second = policy.purge_owner(OWNER)

    assert first.removed_count == 1
    assert second.removed_count == 0
    assert policy.verify_owner_absent(OWNER).verified is True
    assert exact_cache.get("same query", owner_key=OTHER) == {"owner": "bob"}


def test_analytics_and_conversation_history_purge_exact_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics, "ANALYTICS_FILE", tmp_path / "analytics.json")
    conversations = tmp_path / "conversations"
    conversations.mkdir()
    monkeypatch.setattr(analytics, "CONVERSATIONS_DIR", conversations)

    analytics.track_query("alice", [], "long enough alice answer", owner_key=OWNER)
    analytics.track_query("bob", [], "long enough bob answer", owner_key=OTHER)
    analytics.save_conversation("alice-session", [], owner_key=OWNER)
    analytics.save_conversation("bob-session", [], owner_key=OTHER)

    assert analytics.purge_owner(OWNER) == 2
    assert analytics.purge_owner(OWNER) == 0
    assert analytics.verify_owner_absent(OWNER) is True
    assert analytics.verify_owner_absent(OTHER) is False
    assert (conversations / "bob-session.json").exists()


def test_cost_and_optimizer_records_purge_exact_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(cost_tracker, "COSTS_FILE", tmp_path / "costs.json")
    costs = cost_tracker.CostAttribution()
    tokens = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
    costs.record(OWNER, "q", "agent", None, "model", tokens, 0.1)
    costs.record(OTHER, "q", "agent", None, "model", tokens, 0.1)

    assert costs.purge_owner(OWNER) == 1
    assert costs.purge_owner(OWNER) == 0
    assert costs.verify_owner_absent(OWNER) is True
    assert costs.verify_owner_absent(OTHER) is False

    monkeypatch.setattr(
        self_optimizer,
        "PERFORMANCE_FILE",
        tmp_path / "performance.json",
    )
    optimizer = self_optimizer.PerformanceCollector()
    optimizer.record("s1", "q", "agent", [], 8, 1.0, 10, owner_key=OWNER)
    optimizer.record("s2", "q", "agent", [], 8, 1.0, 10, owner_key=OTHER)

    assert optimizer.purge_owner(OWNER) == 1
    assert optimizer.purge_owner(OWNER) == 0
    assert optimizer.verify_owner_absent(OWNER) is True
    assert optimizer.verify_owner_absent(OTHER) is False


def test_guardrail_budget_purges_exact_owner_and_blocks_new_writes(
    tmp_path, monkeypatch
):
    manager = guardrails.SessionBudgetManager(default_limit=1000)
    manager._persistence_file = tmp_path / "guardrails_budget.json"
    manager._sessions.clear()
    manager.record_usage(OWNER, 10)
    manager.record_usage(OTHER, 20)

    assert manager.purge_owner(OWNER) == 1
    assert manager.purge_owner(OWNER) == 0
    assert manager.verify_owner_absent(OWNER) is True
    assert manager.verify_owner_absent(OTHER) is False

    class BlockedGate:
        @staticmethod
        def assert_writable(_owner_key):
            raise RuntimeError("blocked")

    monkeypatch.setattr(guardrails, "owner_write_gate", BlockedGate())

    try:
        manager.record_usage(OWNER, 1)
    except RuntimeError as exc:
        assert str(exc) == "blocked"
    else:
        raise AssertionError("blocked owner write unexpectedly succeeded")
    assert manager.verify_owner_absent(OWNER) is True


def test_experience_and_prompt_artifacts_remove_owner_from_all_files(
    tmp_path, monkeypatch
):
    bank = tmp_path / "experience.json"
    raw = tmp_path / "demo_pool.json"
    compiled = tmp_path / "compiled.json"
    monkeypatch.setattr(experience_memory, "BANK_FILE", bank)
    monkeypatch.setattr(prompt_compiler, "RAW_FILE", raw)
    monkeypatch.setattr(prompt_compiler, "COMPILED_FILE", compiled)

    experience_memory._save([
        {"id": "a", "owner_key": OWNER},
        {"id": "b", "owner_key": OTHER},
    ])
    prompt_compiler._save(raw, [
        {"intent": "factual", "owner_key": OWNER},
        {"intent": "factual", "owner_key": OTHER},
    ])
    prompt_compiler._save(compiled, {"demos": {"factual": [
        {"owner_key": OWNER},
        {"owner_key": OTHER},
    ]}})

    assert experience_memory.purge_owner(OWNER) == 1
    assert experience_memory.purge_owner(OWNER) == 0
    assert experience_memory.verify_owner_absent(OWNER) is True
    assert experience_memory.verify_owner_absent(OTHER) is False

    assert prompt_compiler.purge_owner(OWNER) == 2
    assert prompt_compiler.purge_owner(OWNER) == 0
    assert prompt_compiler.verify_owner_absent(OWNER) is True
    assert prompt_compiler.verify_owner_absent(OTHER) is False


def test_ab_outcomes_purge_owner_attribution_and_linked_assignment(tmp_path):
    manager = ab_testing.ABTestManager(filepath=tmp_path / "ab.json")
    manager.create_experiment(
        "exp",
        [
            {"id": "a", "config": {}, "weight": 0.5},
            {"id": "b", "config": {}, "weight": 0.5},
        ],
        "score",
    )
    manager.record_outcome("exp", "alice-session", 1.0, owner_key=OWNER)
    manager.record_outcome("exp", "bob-session", 0.0, owner_key=OTHER)

    assert manager.purge_owner(OWNER) == 1
    assert manager.purge_owner(OWNER) == 0
    assert manager.verify_owner_absent(OWNER) is True
    assert manager.verify_owner_absent(OTHER) is False
    assert "alice-session" not in manager._assignments["exp"]
    assert "bob-session" in manager._assignments["exp"]


class _FakeFeedbackStore:
    def __init__(self):
        self.pending = set()
        self.all_rows = set()

    def purge_pending(self, *, owner_binding):
        removed = int(owner_binding in self.pending)
        self.pending.discard(owner_binding)
        return removed

    def pending_owner_absent(self, *, owner_binding):
        return owner_binding not in self.pending

    def purge(self, *, owner_binding):
        removed = int(owner_binding in self.all_rows)
        self.pending.discard(owner_binding)
        self.all_rows.discard(owner_binding)
        return removed

    def owner_absent(self, *, owner_binding):
        return owner_binding not in self.all_rows


def test_feedback_pending_and_full_purge_have_separate_phases(monkeypatch):
    fake = _FakeFeedbackStore()
    feedback_owner = "user:11111111-1111-4111-8111-111111111111"
    binding = feedback_policy._owner_ref(feedback_owner).owner_binding
    fake.pending.add(binding)
    fake.all_rows.add(binding)
    monkeypatch.setattr(feedback_policy, "_store", fake)

    assert feedback_policy.purge_pending_feedback_owner(feedback_owner) == 1
    assert feedback_policy.purge_pending_feedback_owner(feedback_owner) == 0
    assert feedback_policy.verify_pending_feedback_owner_absent(feedback_owner) is True
    assert feedback_policy.verify_feedback_owner_absent(feedback_owner) is False
    assert feedback_policy.purge_feedback_owner(feedback_owner) == 1
    assert feedback_policy.verify_feedback_owner_absent(feedback_owner) is True


def test_purge_results_never_serialize_owner_or_paths():
    policy = data_lifecycle.DataStorePolicy(
        name="fake",
        classification="personal",
        purge=lambda _owner: 2,
        verify=lambda _owner: True,
        description="fake store",
    )

    purge = policy.purge_owner(OWNER)
    verify = policy.verify_owner_absent(OWNER)
    encoded = json.dumps([purge.to_dict(), verify.to_dict()], sort_keys=True)

    assert OWNER not in encoded
    assert str(Path.cwd()) not in encoded
    assert purge.to_dict() == {
        "store_name": "fake",
        "removed_count": 2,
        "complete": True,
        "error_code": None,
    }
