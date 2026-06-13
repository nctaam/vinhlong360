"""Tests for federation.py -- Level 7 federated memory & deployment."""

import sys
import os
import time
import hashlib
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from federation import (
    NodeInfo,
    NodeRegistry,
    FederatedMemory,
    CacheCoherency,
    CanaryDeployment,
    LoadBalancer,
    FederationManager,
)


class TestNodeInfo(unittest.TestCase):
    """Tests for NodeInfo dataclass."""

    def test_to_dict(self):
        node = NodeInfo(node_id="n1", name="test-node", url="http://localhost:8000")
        d = node.to_dict()
        self.assertEqual(d["node_id"], "n1")
        self.assertEqual(d["name"], "test-node")
        self.assertIn("region", d)
        self.assertIn("role", d)
        self.assertIn("status", d)

    def test_from_dict_roundtrip(self):
        node = NodeInfo(
            node_id="n2", name="roundtrip", url="http://host:9000",
            region="us-east", role="replica", status="active",
            version="2.0.0", capabilities=["search"],
        )
        d = node.to_dict()
        restored = NodeInfo.from_dict(d)
        self.assertEqual(restored.node_id, "n2")
        self.assertEqual(restored.name, "roundtrip")
        self.assertEqual(restored.region, "us-east")
        self.assertEqual(restored.role, "replica")
        self.assertEqual(restored.capabilities, ["search"])

    def test_from_dict_defaults(self):
        d = {"name": "minimal"}
        node = NodeInfo.from_dict(d)
        self.assertEqual(node.name, "minimal")
        self.assertEqual(node.role, "replica")
        self.assertEqual(node.status, "active")


class TestNodeRegistry(unittest.TestCase):
    """Tests for NodeRegistry."""

    def setUp(self):
        self.registry = NodeRegistry()

    def test_auto_registered_local_primary(self):
        """Local node is registered as primary on init."""
        local = self.registry.get_node(self.registry.local_node_id)
        self.assertIsNotNone(local)
        self.assertEqual(local.role, "primary")
        self.assertEqual(local.status, "active")

    def test_register_new_node(self):
        node = NodeInfo(node_id="ext-1", name="external", role="replica")
        self.registry.register(node)
        fetched = self.registry.get_node("ext-1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "external")

    def test_get_active_nodes(self):
        active = self.registry.get_active_nodes()
        self.assertGreater(len(active), 0)
        # All returned nodes should have recent heartbeat
        now = time.time()
        for n in active:
            self.assertLess(now - n.last_heartbeat, NodeRegistry.HEARTBEAT_TIMEOUT)

    def test_heartbeat_updates_time(self):
        node_id = self.registry.local_node_id
        old_hb = self.registry.get_node(node_id).last_heartbeat
        time.sleep(0.01)
        self.registry.heartbeat(node_id)
        new_hb = self.registry.get_node(node_id).last_heartbeat
        self.assertGreater(new_hb, old_hb)

    def test_get_primary(self):
        primary = self.registry.get_primary()
        self.assertIsNotNone(primary)
        self.assertEqual(primary.role, "primary")

    def test_deregister(self):
        node = NodeInfo(node_id="temp-1", name="temporary", role="replica")
        self.registry.register(node)
        self.registry.deregister("temp-1")
        self.assertIsNone(self.registry.get_node("temp-1"))


class TestFederatedMemory(unittest.TestCase):
    """Tests for FederatedMemory."""

    def setUp(self):
        self.mem = FederatedMemory()

    def test_sync_memory(self):
        remote_data = {
            "key1": {"value": "hello", "timestamp": time.time()},
            "key2": {"value": "world", "timestamp": time.time()},
        }
        result = self.mem.sync_memory("node-A", remote_data)
        self.assertIn("keys_received", result)
        self.assertEqual(result["keys_received"], 2)
        self.assertEqual(result["keys_after_merge"], 2)

    def test_merge_memories_last_write_wins(self):
        local = {
            "k": {"value": "old", "timestamp": 100.0},
        }
        remote = {
            "k": {"value": "new", "timestamp": 200.0},
        }
        merged = self.mem.merge_memories(local, remote)
        self.assertEqual(merged["k"]["value"], "new")

    def test_merge_memories_local_wins_when_newer(self):
        local = {
            "k": {"value": "local_val", "timestamp": 300.0},
        }
        remote = {
            "k": {"value": "remote_val", "timestamp": 100.0},
        }
        merged = self.mem.merge_memories(local, remote)
        self.assertEqual(merged["k"]["value"], "local_val")

    def test_merge_memories_adds_new_keys(self):
        local = {"a": {"value": 1, "timestamp": 100.0}}
        remote = {"b": {"value": 2, "timestamp": 100.0}}
        merged = self.mem.merge_memories(local, remote)
        self.assertIn("a", merged)
        self.assertIn("b", merged)

    def test_get_sync_status(self):
        status = self.mem.get_sync_status()
        self.assertIn("last_sync_time", status)
        self.assertIn("pending_changes", status)
        self.assertIn("total_memory_keys", status)


class TestCacheCoherency(unittest.TestCase):
    """Tests for CacheCoherency."""

    def setUp(self):
        self.registry = NodeRegistry()
        self.coherency = CacheCoherency(self.registry)

    def test_invalidate(self):
        self.coherency.invalidate("cache_key_1", "node-X")
        self.assertIn("cache_key_1", self.coherency._invalidated_keys)

    def test_receive_invalidation(self):
        self.coherency.receive_invalidation("key_abc", "node-Y")
        self.assertIn("key_abc", self.coherency._invalidated_keys)
        ts = self.coherency._invalidated_keys["key_abc"]
        self.assertGreater(ts, 0)

    def test_get_coherency_status(self):
        self.coherency.invalidate("k1", "n1")
        status = self.coherency.get_coherency_status()
        self.assertIn("invalidated_keys_count", status)
        self.assertEqual(status["invalidated_keys_count"], 1)


class TestCanaryDeployment(unittest.TestCase):
    """Tests for CanaryDeployment."""

    def setUp(self):
        self.canary = CanaryDeployment()
        self.canary._canary = None  # Reset state

    def test_create_canary(self):
        result = self.canary.create_canary("2.0.0", traffic_pct=10.0)
        self.assertEqual(result["version"], "2.0.0")
        self.assertEqual(result["traffic_pct"], 10.0)
        self.assertEqual(result["status"], "active")

    def test_should_route_to_canary_no_canary(self):
        self.canary._canary = None
        self.assertFalse(self.canary.should_route_to_canary("session-1"))

    def test_should_route_to_canary_consistent_hashing(self):
        """Same session_id should always get same routing decision."""
        self.canary.create_canary("v2", traffic_pct=50.0)
        results = set()
        for _ in range(10):
            results.add(self.canary.should_route_to_canary("fixed-session-id"))
        # Should be consistent -- only one unique value
        self.assertEqual(len(results), 1)

    def test_should_route_to_canary_distribution(self):
        """With 50% traffic, roughly half of random sessions should route to canary."""
        self.canary.create_canary("v2", traffic_pct=50.0)
        canary_count = 0
        total = 200
        for i in range(total):
            if self.canary.should_route_to_canary(f"session-{i}"):
                canary_count += 1
        # Should be roughly 50%, allow wide margin
        self.assertGreater(canary_count, total * 0.2)
        self.assertLess(canary_count, total * 0.8)

    def test_rollback_canary(self):
        self.canary.create_canary("v2", traffic_pct=5.0)
        result = self.canary.rollback_canary()
        self.assertEqual(result["action"], "rolled_back")
        self.assertFalse(self.canary.should_route_to_canary("any-session"))


class TestLoadBalancer(unittest.TestCase):
    """Tests for LoadBalancer."""

    def setUp(self):
        self.registry = NodeRegistry()
        self.lb = LoadBalancer(self.registry)

    def test_select_node_round_robin(self):
        self.lb.set_strategy("round_robin")
        node = self.lb.select_node()
        self.assertIsNotNone(node)
        self.assertIsInstance(node, NodeInfo)

    def test_fallback_to_local(self):
        """When no active nodes, should still return local node."""
        registry = NodeRegistry()
        # Manually expire all nodes
        for n in registry.all_nodes():
            n.last_heartbeat = 0  # very old
            n.status = "down"
        lb = LoadBalancer(registry)
        node = lb.select_node()
        self.assertIsNotNone(node)

    def test_select_node_with_multiple_nodes(self):
        # Add a second node
        node2 = NodeInfo(node_id="node-2", name="replica-1", role="replica")
        self.registry.register(node2)

        self.lb.set_strategy("round_robin")
        selected = set()
        for _ in range(10):
            n = self.lb.select_node()
            selected.add(n.node_id)
        # Should rotate between the two nodes
        self.assertGreater(len(selected), 1)

        # Cleanup
        self.registry.deregister("node-2")


class TestFederationManager(unittest.TestCase):
    """Tests for FederationManager facade."""

    def setUp(self):
        self.registry = NodeRegistry()
        self.memory = FederatedMemory()
        self.coherency = CacheCoherency(self.registry)
        self.canary = CanaryDeployment()
        self.lb = LoadBalancer(self.registry)
        self.manager = FederationManager(
            registry=self.registry,
            memory=self.memory,
            coherency=self.coherency,
            canary=self.canary,
            balancer=self.lb,
        )

    def test_get_status(self):
        status = self.manager.get_status()
        self.assertIn("total_nodes", status)
        self.assertIn("active_nodes", status)
        self.assertIn("local_node_id", status)
        self.assertIn("primary", status)
        self.assertIn("memory_sync", status)
        self.assertIn("cache_coherency", status)
        self.assertIn("canary", status)

    def test_get_status_has_primary(self):
        status = self.manager.get_status()
        self.assertIsNotNone(status["primary"])
        self.assertEqual(status["primary"]["role"], "primary")

    def test_get_topology(self):
        topology = self.manager.get_topology()
        self.assertIn("nodes", topology)
        self.assertIn("connections", topology)
        self.assertIsInstance(topology["nodes"], list)
        self.assertGreater(len(topology["nodes"]), 0)

    def test_health_check(self):
        health = self.manager.health_check()
        self.assertIsInstance(health, dict)
        # Should include local node
        self.assertGreater(len(health), 0)
        for node_id, info in health.items():
            self.assertIn("health", info)
            self.assertIn("name", info)


if __name__ == "__main__":
    unittest.main()
