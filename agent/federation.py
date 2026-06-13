"""
vinhlong360 — Federated Memory, Distributed Cache Coherency & Deployment.

Cung cap:
  1. NodeInfo / NodeRegistry — dang ky va quan ly cac node trong cluster
  2. FederatedMemory — dong bo memory giua cac node (last-write-wins)
  3. CacheCoherency — invalidate cache cross-node qua HTTP POST
  4. CanaryDeployment — canary release voi hash-based routing & auto-rollback
  5. LoadBalancer — round-robin / least-connections / hash-based node selection
  6. FederationManager — facade tong hop status, topology, health

Mac dinh chay single-node (tu dang ky primary). Khi register them node
thi cac tinh nang federation tu dong bat.

Persistence: agent/data/federation/
Thread-safe: moi class dung threading.Lock rieng.
"""

import hashlib
import http.client
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent / "data" / "federation"
DATA_DIR.mkdir(parents=True, exist_ok=True)

NODES_FILE = DATA_DIR / "nodes.json"
CANARY_FILE = DATA_DIR / "canary.json"

# ── Helpers ──────────────────────────────────────────────────────────────────

def _atomic_write(path: Path, data) -> None:
    """Write JSON atomically: write to .tmp then rename."""
    try:
        content = json.dumps(data, ensure_ascii=False, indent=2)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        if path.exists():
            path.unlink()
        tmp_path.rename(path)
    except Exception as e:
        logger.error("Failed to write %s: %s", path, e)


def _load_json(path: Path, default=None):
    """Load JSON file, return *default* on any failure."""
    if default is None:
        default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
    return default


# ══════════════════════════════════════════════════
#  1. NODE INFO
# ══════════════════════════════════════════════════

@dataclass
class NodeInfo:
    """Describes a single node in the federation."""

    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "local"
    url: str = "http://localhost:8000"
    region: str = "vn-south"
    role: str = "primary"          # primary / replica / canary
    status: str = "active"         # active / degraded / down
    last_heartbeat: float = field(default_factory=time.time)
    version: str = "1.0.0"
    capabilities: list = field(default_factory=lambda: ["knowledge", "search"])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "NodeInfo":
        return cls(
            node_id=data.get("node_id", str(uuid.uuid4())),
            name=data.get("name", "unknown"),
            url=data.get("url", "http://localhost:8000"),
            region=data.get("region", "vn-south"),
            role=data.get("role", "replica"),
            status=data.get("status", "active"),
            last_heartbeat=data.get("last_heartbeat", time.time()),
            version=data.get("version", "1.0.0"),
            capabilities=data.get("capabilities", []),
        )


# ══════════════════════════════════════════════════
#  2. NODE REGISTRY
# ══════════════════════════════════════════════════

class NodeRegistry:
    """
    Thread-safe registry of federation nodes.

    On init, auto-registers the local node as primary.
    Persistence: agent/data/federation/nodes.json
    """

    HEARTBEAT_TIMEOUT = 60.0  # seconds before a node is considered stale

    def __init__(self):
        self._lock = Lock()
        self._nodes: dict[str, NodeInfo] = {}
        self._local_node_id: str = str(uuid.uuid4())

        # Load persisted nodes
        self._load()

        # Auto-register this node as primary
        local = NodeInfo(
            node_id=self._local_node_id,
            name="local-primary",
            role="primary",
            status="active",
            last_heartbeat=time.time(),
        )
        self.register(local)

    # ── persistence ──

    def _load(self) -> None:
        data = _load_json(NODES_FILE, default=[])
        if isinstance(data, list):
            for entry in data:
                try:
                    node = NodeInfo.from_dict(entry)
                    self._nodes[node.node_id] = node
                except Exception:
                    pass

    def _persist(self) -> None:
        data = [n.to_dict() for n in self._nodes.values()]
        _atomic_write(NODES_FILE, data)

    # ── public API ──

    def register(self, node: NodeInfo) -> None:
        """Add or update a node."""
        with self._lock:
            node.last_heartbeat = time.time()
            self._nodes[node.node_id] = node
            self._persist()
            logger.info("Node registered: %s (%s)", node.name, node.node_id[:8])

    def deregister(self, node_id: str) -> None:
        """Remove a node from the registry."""
        with self._lock:
            if node_id in self._nodes:
                name = self._nodes[node_id].name
                del self._nodes[node_id]
                self._persist()
                logger.info("Node deregistered: %s (%s)", name, node_id[:8])

    def get_active_nodes(self) -> list[NodeInfo]:
        """Return nodes whose heartbeat is within HEARTBEAT_TIMEOUT."""
        now = time.time()
        with self._lock:
            return [
                n for n in self._nodes.values()
                if (now - n.last_heartbeat) < self.HEARTBEAT_TIMEOUT
                and n.status != "down"
            ]

    def get_node(self, node_id: str):
        """Return NodeInfo or None."""
        with self._lock:
            return self._nodes.get(node_id)

    def heartbeat(self, node_id: str) -> None:
        """Update last_heartbeat for a node."""
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].last_heartbeat = time.time()
                self._nodes[node_id].status = "active"
                self._persist()

    def get_primary(self):
        """Return the primary node, or None."""
        with self._lock:
            for n in self._nodes.values():
                if n.role == "primary" and n.status != "down":
                    return n
            return None

    @property
    def local_node_id(self) -> str:
        return self._local_node_id

    def all_nodes(self) -> list[NodeInfo]:
        """Return all registered nodes (including stale)."""
        with self._lock:
            return list(self._nodes.values())


# ══════════════════════════════════════════════════
#  3. FEDERATED MEMORY
# ══════════════════════════════════════════════════

class FederatedMemory:
    """
    Synchronise memory across federation nodes.

    Conflict resolution: last-write-wins by timestamp.
    Tracks the last 100 sync events.
    """

    MAX_SYNC_HISTORY = 100

    def __init__(self):
        self._lock = Lock()
        self._local_memory: dict = {}
        self._sync_history: deque = deque(maxlen=self.MAX_SYNC_HISTORY)
        self._last_sync_time: float = 0.0
        self._pending_changes: int = 0
        self._conflicts_resolved: int = 0

    # ── public API ──

    def sync_memory(self, source_node: str, memory_data: dict) -> dict:
        """
        Receive memory from another node and merge it into local memory.

        Returns dict with sync result summary.
        """
        with self._lock:
            merged = self.merge_memories(self._local_memory, memory_data)
            changes = len(merged) - len(self._local_memory)
            self._local_memory = merged
            self._last_sync_time = time.time()
            self._pending_changes = 0

            record = {
                "source_node": source_node,
                "timestamp": self._last_sync_time,
                "keys_received": len(memory_data),
                "keys_after_merge": len(merged),
                "new_keys": max(0, changes),
            }
            self._sync_history.append(record)

            logger.info(
                "Memory synced from %s: %d keys received, %d total after merge",
                source_node[:8], len(memory_data), len(merged),
            )
            return record

    def get_sync_package(self) -> dict:
        """Package local memory for sending to other nodes."""
        with self._lock:
            return {
                "memory": dict(self._local_memory),
                "timestamp": time.time(),
                "node_count": len(self._local_memory),
            }

    def merge_memories(self, local: dict, remote: dict) -> dict:
        """
        Merge two memory dicts using last-write-wins by timestamp.

        Each value is expected to be a dict with a 'timestamp' field.
        If not present, the entry keeps its existing value (local wins).
        """
        merged = dict(local)
        for key, remote_val in remote.items():
            if key not in merged:
                merged[key] = remote_val
            else:
                local_ts = 0.0
                remote_ts = 0.0
                if isinstance(merged[key], dict):
                    local_ts = merged[key].get("timestamp", 0.0)
                if isinstance(remote_val, dict):
                    remote_ts = remote_val.get("timestamp", 0.0)

                if remote_ts > local_ts:
                    merged[key] = remote_val
                    self._conflicts_resolved += 1
        return merged

    def get_sync_status(self) -> dict:
        """Return current synchronisation status."""
        with self._lock:
            return {
                "last_sync_time": self._last_sync_time,
                "pending_changes": self._pending_changes,
                "conflicts_resolved": self._conflicts_resolved,
                "total_memory_keys": len(self._local_memory),
                "sync_history_count": len(self._sync_history),
                "recent_syncs": list(self._sync_history)[-5:],
            }

    def mark_change(self) -> None:
        """Increment pending change counter (called by local memory writes)."""
        with self._lock:
            self._pending_changes += 1


# ══════════════════════════════════════════════════
#  4. CACHE COHERENCY
# ══════════════════════════════════════════════════

class CacheCoherency:
    """
    Distributed cache invalidation via HTTP POST.

    Protocol: POST /federation/invalidate  {key, source_node}
    Queues invalidations for nodes that are down and retries on next heartbeat.
    """

    def __init__(self, registry: NodeRegistry):
        self._lock = Lock()
        self._registry = registry
        self._invalidated_keys: dict[str, float] = {}  # key -> timestamp
        self._pending_queue: dict[str, list[str]] = {}  # node_id -> [keys]
        self._last_broadcast: float = 0.0
        self._broadcast_count: int = 0

    def invalidate(self, key: str, source_node: str) -> None:
        """Mark a cache key as invalidated."""
        with self._lock:
            self._invalidated_keys[key] = time.time()
            logger.debug("Cache key invalidated: %s (from %s)", key, source_node[:8])

    def broadcast_invalidation(self, key: str) -> None:
        """Notify all active nodes about a cache invalidation (best-effort)."""
        local_id = self._registry.local_node_id
        nodes = self._registry.get_active_nodes()

        with self._lock:
            self._last_broadcast = time.time()
            self._broadcast_count += 1

        for node in nodes:
            if node.node_id == local_id:
                continue
            success = self._send_invalidation(node, key)
            if not success:
                # Queue for retry
                with self._lock:
                    if node.node_id not in self._pending_queue:
                        self._pending_queue[node.node_id] = []
                    if key not in self._pending_queue[node.node_id]:
                        self._pending_queue[node.node_id].append(key)

        # Also invalidate locally
        self.invalidate(key, local_id)

    def receive_invalidation(self, key: str, source_node: str) -> None:
        """Handle an incoming invalidation from another node."""
        self.invalidate(key, source_node)
        logger.info("Received cache invalidation for '%s' from %s", key, source_node[:8])

    def get_coherency_status(self) -> dict:
        """Return current coherency status."""
        with self._lock:
            total_pending = sum(len(v) for v in self._pending_queue.values())
            return {
                "invalidated_keys_count": len(self._invalidated_keys),
                "pending_invalidations": total_pending,
                "pending_by_node": {
                    nid[:8]: len(keys)
                    for nid, keys in self._pending_queue.items()
                },
                "last_broadcast": self._last_broadcast,
                "total_broadcasts": self._broadcast_count,
            }

    def flush_pending(self, node_id: str) -> None:
        """
        Retry queued invalidations for a node (call on heartbeat).
        """
        with self._lock:
            keys = list(self._pending_queue.get(node_id, []))
        if not keys:
            return

        node = self._registry.get_node(node_id)
        if node is None:
            return

        succeeded = []
        for key in keys:
            if self._send_invalidation(node, key):
                succeeded.append(key)

        with self._lock:
            remaining = self._pending_queue.get(node_id, [])
            self._pending_queue[node_id] = [k for k in remaining if k not in succeeded]
            if not self._pending_queue[node_id]:
                del self._pending_queue[node_id]

    # ── internal ──

    @staticmethod
    def _send_invalidation(node: NodeInfo, key: str) -> bool:
        """POST invalidation to a remote node. Returns True on success."""
        try:
            parsed = urlparse(node.url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 80
            scheme = parsed.scheme or "http"

            payload = json.dumps({"key": key, "source_node": node.node_id})

            if scheme == "https":
                conn = http.client.HTTPSConnection(host, port, timeout=5)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=5)

            conn.request(
                "POST",
                "/federation/invalidate",
                body=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            conn.close()
            return 200 <= resp.status < 300
        except Exception as e:
            logger.debug("Failed to send invalidation to %s: %s", node.name, e)
            return False


# ══════════════════════════════════════════════════
#  5. CANARY DEPLOYMENT
# ══════════════════════════════════════════════════

class CanaryDeployment:
    """
    Canary release management with hash-based routing and auto-rollback.

    Auto-rollback triggers:
      - Error rate > 5%
      - Quality score drops > 20% compared to stable

    Persistence: agent/data/federation/canary.json
    """

    ERROR_RATE_THRESHOLD = 0.05
    QUALITY_DROP_THRESHOLD = 0.20

    def __init__(self):
        self._lock = Lock()
        self._canary: dict | None = None
        self._stable_metrics: dict = {
            "requests": 0, "successes": 0, "total_latency": 0.0,
            "total_quality": 0.0,
        }
        self._canary_metrics: dict = {
            "requests": 0, "successes": 0, "total_latency": 0.0,
            "total_quality": 0.0,
        }
        self._load()

    # ── persistence ──

    def _load(self) -> None:
        data = _load_json(CANARY_FILE)
        if data and "canary" in data:
            self._canary = data["canary"]
            self._stable_metrics = data.get("stable_metrics", self._stable_metrics)
            self._canary_metrics = data.get("canary_metrics", self._canary_metrics)

    def _persist(self) -> None:
        data = {
            "canary": self._canary,
            "stable_metrics": self._stable_metrics,
            "canary_metrics": self._canary_metrics,
        }
        _atomic_write(CANARY_FILE, data)

    # ── public API ──

    def create_canary(self, version: str, traffic_pct: float = 5.0) -> dict:
        """Create a canary deployment configuration."""
        with self._lock:
            self._canary = {
                "version": version,
                "traffic_pct": traffic_pct,
                "created_at": time.time(),
                "status": "active",
            }
            self._canary_metrics = {
                "requests": 0, "successes": 0,
                "total_latency": 0.0, "total_quality": 0.0,
            }
            self._persist()
            logger.info("Canary created: version=%s, traffic=%.1f%%", version, traffic_pct)
            return dict(self._canary)

    def should_route_to_canary(self, session_id: str) -> bool:
        """
        Determine if a session should hit the canary (hash-based, consistent).

        Returns False when no canary is active.
        """
        with self._lock:
            if not self._canary or self._canary.get("status") != "active":
                return False
            traffic_pct = self._canary.get("traffic_pct", 5.0)

        # Consistent hash: take first 8 hex digits → 0..FFFFFFFF → pct
        digest = hashlib.md5(session_id.encode()).hexdigest()
        hash_value = int(digest[:8], 16)
        bucket = (hash_value % 10000) / 100.0  # 0.00 .. 99.99
        return bucket < traffic_pct

    def update_canary_metrics(
        self, success: bool, latency: float, quality_score: float,
    ) -> None:
        """
        Record a canary request outcome.

        Triggers auto-rollback if thresholds are exceeded.
        """
        with self._lock:
            self._canary_metrics["requests"] += 1
            if success:
                self._canary_metrics["successes"] += 1
            self._canary_metrics["total_latency"] += latency
            self._canary_metrics["total_quality"] += quality_score
            self._persist()

        # Check auto-rollback (need enough data)
        self._check_auto_rollback()

    def update_stable_metrics(
        self, success: bool, latency: float, quality_score: float,
    ) -> None:
        """Record a stable-path request outcome (for comparison)."""
        with self._lock:
            self._stable_metrics["requests"] += 1
            if success:
                self._stable_metrics["successes"] += 1
            self._stable_metrics["total_latency"] += latency
            self._stable_metrics["total_quality"] += quality_score

    def get_canary_status(self) -> dict:
        """Return metrics comparison: canary vs stable."""
        with self._lock:
            canary_stats = self._compute_stats(self._canary_metrics)
            stable_stats = self._compute_stats(self._stable_metrics)
            return {
                "canary": self._canary,
                "canary_metrics": canary_stats,
                "stable_metrics": stable_stats,
                "auto_rollback_thresholds": {
                    "error_rate": self.ERROR_RATE_THRESHOLD,
                    "quality_drop": self.QUALITY_DROP_THRESHOLD,
                },
            }

    def promote_canary(self) -> dict:
        """Promote canary to become the new stable version."""
        with self._lock:
            if not self._canary:
                return {"error": "No active canary"}
            version = self._canary["version"]
            result = {
                "action": "promoted",
                "version": version,
                "timestamp": time.time(),
                "canary_metrics": self._compute_stats(self._canary_metrics),
            }
            # Canary metrics become the new stable baseline
            self._stable_metrics = dict(self._canary_metrics)
            self._canary = None
            self._canary_metrics = {
                "requests": 0, "successes": 0,
                "total_latency": 0.0, "total_quality": 0.0,
            }
            self._persist()
            logger.info("Canary promoted: %s", version)
            return result

    def rollback_canary(self) -> dict:
        """Remove canary deployment, revert to stable."""
        with self._lock:
            if not self._canary:
                return {"error": "No active canary"}
            version = self._canary["version"]
            result = {
                "action": "rolled_back",
                "version": version,
                "timestamp": time.time(),
                "canary_metrics": self._compute_stats(self._canary_metrics),
            }
            self._canary = None
            self._canary_metrics = {
                "requests": 0, "successes": 0,
                "total_latency": 0.0, "total_quality": 0.0,
            }
            self._persist()
            logger.info("Canary rolled back: %s", version)
            return result

    # ── internal ──

    @staticmethod
    def _compute_stats(metrics: dict) -> dict:
        reqs = metrics.get("requests", 0)
        if reqs == 0:
            return {
                "requests": 0, "error_rate": 0.0,
                "avg_latency": 0.0, "avg_quality": 0.0,
            }
        successes = metrics.get("successes", 0)
        return {
            "requests": reqs,
            "error_rate": 1.0 - (successes / reqs),
            "avg_latency": metrics.get("total_latency", 0.0) / reqs,
            "avg_quality": metrics.get("total_quality", 0.0) / reqs,
        }

    def _check_auto_rollback(self) -> None:
        """Auto-rollback if canary error rate or quality drop exceeds thresholds."""
        with self._lock:
            if not self._canary or self._canary.get("status") != "active":
                return
            canary = self._compute_stats(self._canary_metrics)
            stable = self._compute_stats(self._stable_metrics)

            # Need at least 20 canary requests before judging
            if canary["requests"] < 20:
                return

            # Error rate check
            if canary["error_rate"] > self.ERROR_RATE_THRESHOLD:
                logger.warning(
                    "Canary auto-rollback: error rate %.2f%% > %.2f%%",
                    canary["error_rate"] * 100,
                    self.ERROR_RATE_THRESHOLD * 100,
                )
                self._canary["status"] = "rolled_back"
                self._persist()
                return

            # Quality drop check (only if stable has data)
            if stable["requests"] > 0 and stable["avg_quality"] > 0:
                drop = (stable["avg_quality"] - canary["avg_quality"]) / stable["avg_quality"]
                if drop > self.QUALITY_DROP_THRESHOLD:
                    logger.warning(
                        "Canary auto-rollback: quality drop %.1f%% > %.1f%%",
                        drop * 100, self.QUALITY_DROP_THRESHOLD * 100,
                    )
                    self._canary["status"] = "rolled_back"
                    self._persist()


# ══════════════════════════════════════════════════
#  6. LOAD BALANCER
# ══════════════════════════════════════════════════

class LoadBalancer:
    """
    Select the best node for a request.

    Strategies:
      - round_robin: rotate through active nodes
      - least_connections: node with fewest active requests
      - hash_based: consistent hashing for session affinity
    """

    def __init__(self, registry: NodeRegistry):
        self._lock = Lock()
        self._registry = registry
        self._rr_index: int = 0
        self._active_requests: dict[str, int] = {}  # node_id -> count
        self._strategy: str = "round_robin"

    def set_strategy(self, strategy: str) -> None:
        """Set the balancing strategy (round_robin / least_connections / hash_based)."""
        if strategy in ("round_robin", "least_connections", "hash_based"):
            self._strategy = strategy
            logger.info("Load balancer strategy set to: %s", strategy)

    def select_node(self, session_id: str = None) -> NodeInfo:
        """
        Select the best node for a request.

        Falls back to local node if all others are down.
        """
        nodes = self._registry.get_active_nodes()
        if not nodes:
            # Fallback: return local node regardless of heartbeat
            local = self._registry.get_node(self._registry.local_node_id)
            if local:
                return local
            # Last resort: create a minimal local node
            return NodeInfo(node_id=self._registry.local_node_id, name="fallback-local")

        if len(nodes) == 1:
            return nodes[0]

        if self._strategy == "hash_based" and session_id:
            return self._hash_select(nodes, session_id)
        elif self._strategy == "least_connections":
            return self._least_conn_select(nodes)
        else:
            return self._round_robin_select(nodes)

    def record_request(self, node_id: str) -> None:
        """Increment active request count for a node."""
        with self._lock:
            self._active_requests[node_id] = self._active_requests.get(node_id, 0) + 1

    def complete_request(self, node_id: str) -> None:
        """Decrement active request count for a node."""
        with self._lock:
            current = self._active_requests.get(node_id, 0)
            self._active_requests[node_id] = max(0, current - 1)

    # ── strategies ──

    def _round_robin_select(self, nodes: list[NodeInfo]) -> NodeInfo:
        with self._lock:
            idx = self._rr_index % len(nodes)
            self._rr_index = (self._rr_index + 1) % len(nodes)
            return nodes[idx]

    def _least_conn_select(self, nodes: list[NodeInfo]) -> NodeInfo:
        with self._lock:
            best = nodes[0]
            best_count = self._active_requests.get(best.node_id, 0)
            for node in nodes[1:]:
                count = self._active_requests.get(node.node_id, 0)
                if count < best_count:
                    best = node
                    best_count = count
            return best

    @staticmethod
    def _hash_select(nodes: list[NodeInfo], session_id: str) -> NodeInfo:
        digest = hashlib.md5(session_id.encode()).hexdigest()
        idx = int(digest[:8], 16) % len(nodes)
        return nodes[idx]


# ══════════════════════════════════════════════════
#  7. FEDERATION MANAGER (facade)
# ══════════════════════════════════════════════════

class FederationManager:
    """Facade aggregating all federation subsystems."""

    def __init__(
        self,
        registry: NodeRegistry,
        memory: FederatedMemory,
        coherency: CacheCoherency,
        canary: CanaryDeployment,
        balancer: LoadBalancer,
    ):
        self._registry = registry
        self._memory = memory
        self._coherency = coherency
        self._canary = canary
        self._balancer = balancer

    def get_status(self) -> dict:
        """Full federation status."""
        nodes = self._registry.all_nodes()
        active = self._registry.get_active_nodes()
        return {
            "total_nodes": len(nodes),
            "active_nodes": len(active),
            "local_node_id": self._registry.local_node_id,
            "primary": self._registry.get_primary().to_dict() if self._registry.get_primary() else None,
            "memory_sync": self._memory.get_sync_status(),
            "cache_coherency": self._coherency.get_coherency_status(),
            "canary": self._canary.get_canary_status(),
        }

    def get_topology(self) -> dict:
        """Node graph with connections."""
        nodes = self._registry.all_nodes()
        node_list = []
        for n in nodes:
            node_list.append({
                "id": n.node_id,
                "name": n.name,
                "region": n.region,
                "role": n.role,
                "status": n.status,
                "url": n.url,
            })

        # Connections: primary <-> each replica/canary
        primary = self._registry.get_primary()
        connections = []
        if primary:
            for n in nodes:
                if n.node_id != primary.node_id:
                    connections.append({
                        "from": primary.node_id,
                        "to": n.node_id,
                        "type": "replication",
                    })

        return {
            "nodes": node_list,
            "connections": connections,
        }

    def health_check(self) -> dict:
        """Check all nodes and return health status."""
        nodes = self._registry.all_nodes()
        now = time.time()
        results = {}
        for node in nodes:
            age = now - node.last_heartbeat
            if node.status == "down":
                health = "down"
            elif age > NodeRegistry.HEARTBEAT_TIMEOUT:
                health = "stale"
            elif node.status == "degraded":
                health = "degraded"
            else:
                health = "healthy"
            results[node.node_id] = {
                "name": node.name,
                "health": health,
                "heartbeat_age_s": round(age, 1),
                "role": node.role,
                "version": node.version,
            }
        return results

    def get_federation_report(self) -> dict:
        """Comprehensive report for /system/federation endpoint."""
        return {
            "status": self.get_status(),
            "topology": self.get_topology(),
            "health": self.health_check(),
            "timestamp": time.time(),
        }


# ══════════════════════════════════════════════════
#  MODULE SINGLETONS
# ══════════════════════════════════════════════════

node_registry = NodeRegistry()
federated_memory = FederatedMemory()
cache_coherency = CacheCoherency(node_registry)
canary_deployment = CanaryDeployment()
load_balancer = LoadBalancer(node_registry)
federation_manager = FederationManager(
    registry=node_registry,
    memory=federated_memory,
    coherency=cache_coherency,
    canary=canary_deployment,
    balancer=load_balancer,
)

logger.info(
    "Federation module initialised — local node %s (primary)",
    node_registry.local_node_id[:8],
)
