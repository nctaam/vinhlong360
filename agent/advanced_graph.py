"""
vinhlong360 -- Advanced Graph Analytics.

Mo rong memory_graph.py voi cac phan tich nang cao:
  - Community Detection (Label Propagation)
  - Link Prediction (Common Neighbors / Jaccard / Adamic-Adar)
  - Anomaly Detection (isolated clusters, hubs, dead-ends, weight spikes)
  - Temporal Evolution (snapshots, growth rate, trending entities)
  - Facade GraphAnalytics (full analysis, recommendations, health report)

Kien truc:
  Dependencies: stdlib only (json, math, collections, dataclasses, threading, random, time, pathlib, logging)
  Persistence: agent/data/graph/snapshots.json
  Thread-safe: threading.Lock
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────

GRAPH_DATA_DIR = Path(__file__).resolve().parent / "data" / "graph"
GRAPH_DATA_DIR.mkdir(parents=True, exist_ok=True)

SNAPSHOTS_FILE = GRAPH_DATA_DIR / "snapshots.json"

# Max snapshots retained (roughly 1 per day for 90 days)
MAX_SNAPSHOTS = 90


# ══════════════════════════════════════════════════
#  Helper Functions
# ══════════════════════════════════════════════════

def _build_adjacency_list(edges: list) -> dict[str, set]:
    """
    Build an undirected adjacency list from a list of edge dicts.

    Each edge dict must have "source" and "target" keys.
    Returns {node_id: {neighbor_id, ...}}.
    """
    adj: dict[str, set] = defaultdict(set)
    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        if src and tgt:
            adj[src].add(tgt)
            adj[tgt].add(src)
    return dict(adj)


def _bfs_components(adj_list: dict[str, set]) -> list[set]:
    """
    Find all connected components via BFS.

    Returns a list of sets, each set containing the node IDs of one component.
    """
    visited: set[str] = set()
    components: list[set] = []

    all_nodes = set(adj_list.keys())
    for start in all_nodes:
        if start in visited:
            continue
        component: set[str] = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adj_list.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        if component:
            components.append(component)

    return components


def _estimate_diameter(adj_list: dict[str, set], samples: int = 5) -> int:
    """
    Estimate graph diameter by running BFS from a small number of random nodes
    and returning the maximum shortest-path length found.

    Returns 0 for empty or disconnected graphs (estimates on largest component only).
    """
    if not adj_list:
        return 0

    nodes = list(adj_list.keys())
    if len(nodes) <= 1:
        return 0

    # Work on the largest connected component
    components = _bfs_components(adj_list)
    if not components:
        return 0
    largest = max(components, key=len)
    component_nodes = list(largest)

    if len(component_nodes) <= 1:
        return 0

    sample_count = min(samples, len(component_nodes))
    sample_nodes = random.sample(component_nodes, sample_count)

    max_distance = 0
    for start in sample_nodes:
        # BFS from start, track distances
        dist: dict[str, int] = {start: 0}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in adj_list.get(node, set()):
                if neighbor not in dist and neighbor in largest:
                    dist[neighbor] = dist[node] + 1
                    queue.append(neighbor)
        if dist:
            farthest = max(dist.values())
            if farthest > max_distance:
                max_distance = farthest

    return max_distance


# ══════════════════════════════════════════════════
#  CommunityDetector
# ══════════════════════════════════════════════════

class CommunityDetector:
    """
    Detect communities in the memory graph using Label Propagation.

    Results are cached and re-computed when the graph changes significantly
    (>10% new nodes since last detection).
    """

    def __init__(self):
        self._lock = Lock()
        self._communities: list[set] = []
        self._label_map: dict[str, int] = {}  # node_id -> community_id
        self._last_node_count: int = 0

    def _label_propagation(
        self,
        adj_list: dict[str, set],
        max_iterations: int = 50,
    ) -> dict[str, int]:
        """
        Label Propagation algorithm for community detection.

        Each node starts with a unique label. On each iteration, every node
        adopts the most frequent label among its neighbors. Ties are broken
        randomly. Converges when no node changes its label.

        Returns {node_id: community_id}.
        """
        nodes = list(adj_list.keys())
        if not nodes:
            return {}

        # Initialize: each node gets its own label
        labels: dict[str, int] = {node: i for i, node in enumerate(nodes)}

        for _iteration in range(max_iterations):
            changed = False
            # Shuffle to avoid ordering bias
            order = list(nodes)
            random.shuffle(order)

            for node in order:
                neighbors = adj_list.get(node, set())
                if not neighbors:
                    continue

                # Count neighbor labels
                label_counts: dict[int, int] = defaultdict(int)
                for nbr in neighbors:
                    if nbr in labels:
                        label_counts[labels[nbr]] += 1

                if not label_counts:
                    continue

                # Find the maximum count
                max_count = max(label_counts.values())
                # Collect all labels with max count (for tie-breaking)
                best_labels = [
                    lbl for lbl, cnt in label_counts.items() if cnt == max_count
                ]
                chosen = random.choice(best_labels)

                if labels[node] != chosen:
                    labels[node] = chosen
                    changed = True

            if not changed:
                logger.debug(
                    "Label propagation converged at iteration %d", _iteration + 1
                )
                break

        return labels

    def detect_communities(
        self,
        nodes: dict,
        edges: list,
    ) -> list[set]:
        """
        Run community detection on the given graph.

        Parameters
        ----------
        nodes : dict
            {node_id: node_dict} or {node_id: MemoryNode} -- keys are used.
        edges : list
            List of edge dicts with "source" and "target" keys.

        Returns
        -------
        list[set]
            Each set contains the node IDs belonging to one community.
        """
        with self._lock:
            node_count = len(nodes)
            adj_list = _build_adjacency_list(edges)

            # Include isolated nodes (no edges) in the adjacency list
            for nid in nodes:
                if nid not in adj_list:
                    adj_list[nid] = set()

            # Check if we should re-run (first time or >10% growth)
            should_rerun = (
                not self._communities
                or self._last_node_count == 0
                or (node_count - self._last_node_count) / max(self._last_node_count, 1) > 0.10
            )

            if not should_rerun:
                return list(self._communities)

            label_map = self._label_propagation(adj_list)

            # Group nodes by label
            community_map: dict[int, set] = defaultdict(set)
            for nid, label in label_map.items():
                community_map[label].add(nid)

            self._communities = list(community_map.values())
            self._label_map = label_map
            self._last_node_count = node_count

            logger.info(
                "Detected %d communities across %d nodes",
                len(self._communities),
                node_count,
            )

            return list(self._communities)

    def get_community_for(self, node_id: str) -> set | None:
        """Return the community set that contains *node_id*, or None."""
        with self._lock:
            label = self._label_map.get(node_id)
            if label is None:
                return None
            for community in self._communities:
                if node_id in community:
                    return set(community)
            return None

    def get_community_summary(self) -> list[dict]:
        """
        Return a summary of each detected community.

        Each entry: {community_id, size, top_nodes, theme}.
        'theme' is inferred from the most common node-type prefix.
        """
        with self._lock:
            summaries = []
            for idx, community in enumerate(self._communities):
                top_nodes = sorted(community)[:5]
                # Simple theme: most common prefix before first '-'
                prefixes: dict[str, int] = defaultdict(int)
                for nid in community:
                    prefix = nid.split("-")[0] if "-" in nid else nid
                    prefixes[prefix] += 1
                theme = max(prefixes, key=prefixes.get) if prefixes else "mixed"

                summaries.append({
                    "community_id": idx,
                    "size": len(community),
                    "top_nodes": top_nodes,
                    "theme": theme,
                })
            return summaries


# ══════════════════════════════════════════════════
#  LinkPredictor
# ══════════════════════════════════════════════════

class LinkPredictor:
    """
    Predict likely new connections between nodes using topological features.

    Methods: Common Neighbors, Jaccard Coefficient, Adamic-Adar index.
    Scores are combined with a weighted average.
    """

    def __init__(
        self,
        weight_common: float = 0.3,
        weight_jaccard: float = 0.3,
        weight_adamic_adar: float = 0.4,
    ):
        self._lock = Lock()
        self._w_common = weight_common
        self._w_jaccard = weight_jaccard
        self._w_adamic_adar = weight_adamic_adar

    @staticmethod
    def _common_neighbors(
        adj: dict[str, set], u: str, v: str
    ) -> float:
        """Return |N(u) ∩ N(v)|."""
        return float(len(adj.get(u, set()) & adj.get(v, set())))

    @staticmethod
    def _jaccard_coefficient(
        adj: dict[str, set], u: str, v: str
    ) -> float:
        """Return |N(u) ∩ N(v)| / |N(u) ∪ N(v)|.  0 if union is empty."""
        nu = adj.get(u, set())
        nv = adj.get(v, set())
        union = nu | nv
        if not union:
            return 0.0
        return len(nu & nv) / len(union)

    @staticmethod
    def _adamic_adar(
        adj: dict[str, set], u: str, v: str
    ) -> float:
        """Return Σ 1/log(|N(w)|) for w in N(u) ∩ N(v)."""
        common = adj.get(u, set()) & adj.get(v, set())
        score = 0.0
        for w in common:
            degree_w = len(adj.get(w, set()))
            if degree_w > 1:
                score += 1.0 / math.log(degree_w)
        return score

    def predict_links(
        self,
        nodes: dict,
        edges: list,
        top_k: int = 10,
    ) -> list[tuple[str, str, float]]:
        """
        Predict likely new connections between unconnected node pairs.

        Returns up to *top_k* tuples of (node_a, node_b, combined_score),
        sorted by score descending.
        """
        with self._lock:
            adj = _build_adjacency_list(edges)

            # Build set of existing edges for quick lookup
            existing: set[frozenset] = set()
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                if src and tgt:
                    existing.add(frozenset((src, tgt)))

            node_ids = list(nodes.keys())
            candidates: list[tuple[str, str, float]] = []

            # Only evaluate pairs that share at least one common neighbor
            # (optimization: skip pairs with zero common neighbors)
            for i, u in enumerate(node_ids):
                neighbors_u = adj.get(u, set())
                # Collect 2-hop neighbors
                two_hop: set[str] = set()
                for nbr in neighbors_u:
                    two_hop.update(adj.get(nbr, set()))
                two_hop.discard(u)
                two_hop -= neighbors_u  # exclude direct neighbors

                for v in two_hop:
                    if frozenset((u, v)) in existing:
                        continue
                    # Ensure canonical order to avoid duplicates
                    if u > v:
                        continue

                    cn = self._common_neighbors(adj, u, v)
                    jc = self._jaccard_coefficient(adj, u, v)
                    aa = self._adamic_adar(adj, u, v)

                    # Normalize common neighbors by max possible
                    max_cn = max(len(neighbors_u), 1)
                    cn_norm = cn / max_cn

                    combined = (
                        self._w_common * cn_norm
                        + self._w_jaccard * jc
                        + self._w_adamic_adar * aa
                    )

                    if combined > 0:
                        candidates.append((u, v, round(combined, 4)))

            candidates.sort(key=lambda x: x[2], reverse=True)
            return candidates[:top_k]

    def suggest_exploration(
        self,
        user_id: str,
        nodes: dict | None = None,
        edges: list | None = None,
    ) -> list[str]:
        """
        Suggest entities the user hasn't visited but is predicted to connect with.

        Loads data from memory_graph if *nodes* / *edges* are not provided.
        Returns a list of entity IDs.
        """
        if nodes is None or edges is None:
            nodes, edges = _load_graph_data()

        adj = _build_adjacency_list(edges)
        user_neighbors = adj.get(user_id, set())

        # Already connected entities
        connected = set(user_neighbors)
        connected.add(user_id)

        # Predict links from this user to all others
        existing: set[frozenset] = set()
        for e in edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            if src and tgt:
                existing.add(frozenset((src, tgt)))

        scored: list[tuple[str, float]] = []
        for nid in nodes:
            if nid in connected:
                continue
            node_data = nodes[nid]
            # Only suggest entity-type nodes
            ntype = node_data.get("type", "") if isinstance(node_data, dict) else getattr(node_data, "type", "")
            if ntype != "entity":
                continue
            if frozenset((user_id, nid)) in existing:
                continue

            cn = self._common_neighbors(adj, user_id, nid)
            jc = self._jaccard_coefficient(adj, user_id, nid)
            aa = self._adamic_adar(adj, user_id, nid)
            max_cn = max(len(user_neighbors), 1)
            combined = (
                self._w_common * (cn / max_cn)
                + self._w_jaccard * jc
                + self._w_adamic_adar * aa
            )
            if combined > 0:
                scored.append((nid, combined))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in scored[:10]]


# ══════════════════════════════════════════════════
#  AnomalyDetector
# ══════════════════════════════════════════════════

class AnomalyDetector:
    """
    Detect unusual patterns in the memory graph.

    Anomaly types:
      - isolated_cluster: community with <3 nodes disconnected from main graph
      - hub_node: node whose degree exceeds 3x the mean degree
      - dead_end_entity: entity node with zero queries (mention_count == 0)
      - sudden_weight_change: edge weight changed >50% within 24 hours
    """

    def __init__(self):
        self._lock = Lock()

    def detect_anomalies(
        self,
        nodes: dict,
        edges: list,
    ) -> list[dict]:
        """
        Run all anomaly detectors and return a combined list.

        Each anomaly: {type, severity (0-1), nodes, description}.
        """
        with self._lock:
            anomalies: list[dict] = []
            adj = _build_adjacency_list(edges)

            anomalies.extend(self._detect_isolated_clusters(adj))
            anomalies.extend(self._detect_hub_nodes(adj))
            anomalies.extend(self._detect_dead_ends(nodes, adj))
            anomalies.extend(self._detect_weight_spikes(edges))

            # Sort by severity descending
            anomalies.sort(key=lambda a: a["severity"], reverse=True)
            return anomalies

    @staticmethod
    def _detect_isolated_clusters(adj: dict[str, set]) -> list[dict]:
        """Find communities with <3 nodes that are disconnected from the main graph."""
        components = _bfs_components(adj)
        if len(components) <= 1:
            return []

        # Largest component is the "main graph"
        largest_size = max(len(c) for c in components)
        anomalies = []
        for comp in components:
            if len(comp) < 3 and len(comp) < largest_size:
                severity = min(1.0, 0.3 + (3 - len(comp)) * 0.2)
                anomalies.append({
                    "type": "isolated_cluster",
                    "severity": round(severity, 2),
                    "nodes": sorted(comp),
                    "description": (
                        f"Isolated cluster of {len(comp)} node(s) disconnected "
                        f"from the main graph: {', '.join(sorted(comp))}"
                    ),
                })
        return anomalies

    @staticmethod
    def _detect_hub_nodes(adj: dict[str, set]) -> list[dict]:
        """Find nodes whose degree exceeds 3x the mean degree."""
        if not adj:
            return []

        degrees = {nid: len(nbrs) for nid, nbrs in adj.items()}
        total_degree = sum(degrees.values())
        mean_degree = total_degree / max(len(degrees), 1)
        threshold = mean_degree * 3

        if threshold < 1:
            return []

        anomalies = []
        for nid, deg in degrees.items():
            if deg > threshold:
                severity = min(1.0, 0.4 + (deg / threshold - 1) * 0.3)
                anomalies.append({
                    "type": "hub_node",
                    "severity": round(severity, 2),
                    "nodes": [nid],
                    "description": (
                        f"Hub node '{nid}' has degree {deg}, "
                        f"which is {deg / mean_degree:.1f}x the mean ({mean_degree:.1f})"
                    ),
                })
        return anomalies

    @staticmethod
    def _detect_dead_ends(nodes: dict, adj: dict[str, set]) -> list[dict]:
        """Find entity nodes that exist in knowledge but were never queried."""
        anomalies = []
        for nid, node_data in nodes.items():
            # Extract type and mention_count from dict or object
            if isinstance(node_data, dict):
                ntype = node_data.get("type", "")
                props = node_data.get("properties", {})
                mention_count = props.get("mention_count", 0)
            else:
                ntype = getattr(node_data, "type", "")
                props = getattr(node_data, "properties", {})
                mention_count = props.get("mention_count", 0)

            if ntype != "entity":
                continue

            # Dead-end: entity type, no mentions, and no edges (or only 1)
            degree = len(adj.get(nid, set()))
            if mention_count == 0 and degree <= 1:
                severity = 0.2 if degree == 1 else 0.4
                anomalies.append({
                    "type": "dead_end_entity",
                    "severity": round(severity, 2),
                    "nodes": [nid],
                    "description": (
                        f"Entity '{nid}' has never been queried "
                        f"(mention_count=0, degree={degree})"
                    ),
                })
        return anomalies

    @staticmethod
    def _detect_weight_spikes(edges: list) -> list[dict]:
        """
        Find edges with sudden weight changes (>50% in 24 hours).

        Detects by examining timestamp intervals: if recent timestamps
        contributed more than 50% of the total weight, flag it.
        """
        anomalies = []
        cutoff_24h = time.time() - 86400

        for e in edges:
            timestamps = e.get("timestamps", [])
            weight = e.get("weight", 1.0)

            if weight <= 1 or len(timestamps) < 2:
                continue

            recent_count = sum(1 for ts in timestamps if ts >= cutoff_24h)
            total_count = len(timestamps)

            if total_count == 0:
                continue

            # If more than 50% of all reinforcements happened in last 24h
            recent_ratio = recent_count / total_count
            if recent_ratio > 0.5 and recent_count >= 2:
                severity = min(1.0, 0.3 + recent_ratio * 0.5)
                src = e.get("source", "?")
                tgt = e.get("target", "?")
                anomalies.append({
                    "type": "sudden_weight_change",
                    "severity": round(severity, 2),
                    "nodes": [src, tgt],
                    "description": (
                        f"Edge '{src}' -> '{tgt}' had {recent_count}/{total_count} "
                        f"reinforcements in the last 24h "
                        f"(weight={weight:.1f}, ratio={recent_ratio:.0%})"
                    ),
                })
        return anomalies


# ══════════════════════════════════════════════════
#  TemporalEvolution
# ══════════════════════════════════════════════════

class TemporalEvolution:
    """
    Track how the memory graph evolves over time.

    Persists snapshots to agent/data/graph/snapshots.json (max 90 entries).
    """

    def __init__(self, snapshots_path: Path | str | None = None):
        self._lock = Lock()
        self._path = Path(snapshots_path) if snapshots_path else SNAPSHOTS_FILE
        self._snapshots: list[dict] = []
        self._load()

    def _load(self):
        """Load snapshots from disk."""
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._snapshots = data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("Failed to load snapshots: %s", exc)
            self._snapshots = []

    def _save(self):
        """Persist snapshots to disk with atomic write."""
        try:
            content = json.dumps(self._snapshots, ensure_ascii=False, indent=2)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(content, encoding="utf-8")
            if self._path.exists():
                self._path.unlink()
            tmp.rename(self._path)
        except Exception as exc:
            logger.warning("Failed to save snapshots: %s", exc)

    def record_snapshot(
        self,
        nodes: dict | None = None,
        edges: list | None = None,
    ):
        """
        Save current graph state as a snapshot.

        Auto-loads from memory_graph if *nodes*/*edges* not provided.
        Trims to MAX_SNAPSHOTS.
        """
        if nodes is None or edges is None:
            nodes, edges = _load_graph_data()

        with self._lock:
            adj = _build_adjacency_list(edges)
            node_count = len(nodes)
            edge_count = len(edges)

            # Density: 2*|E| / (|V| * (|V|-1)) for undirected graph
            if node_count > 1:
                density = (2 * edge_count) / (node_count * (node_count - 1))
            else:
                density = 0.0

            components = _bfs_components(adj)

            snapshot = {
                "timestamp": time.time(),
                "node_count": node_count,
                "edge_count": edge_count,
                "density": round(density, 6),
                "component_count": len(components),
                "largest_component_size": max(
                    (len(c) for c in components), default=0
                ),
            }

            self._snapshots.append(snapshot)

            # Trim oldest snapshots beyond the limit
            if len(self._snapshots) > MAX_SNAPSHOTS:
                self._snapshots = self._snapshots[-MAX_SNAPSHOTS:]

            self._save()

            logger.info(
                "Recorded snapshot: %d nodes, %d edges, density=%.4f",
                node_count, edge_count, density,
            )

    def get_evolution(self, days: int = 30) -> list[dict]:
        """Return snapshots from the last *days* days."""
        cutoff = time.time() - (days * 86400)
        with self._lock:
            return [s for s in self._snapshots if s["timestamp"] >= cutoff]

    def get_growth_rate(self) -> dict:
        """
        Calculate growth rates: nodes/day, edges/day, density trend.

        Uses the first and last snapshots to compute averages.
        """
        with self._lock:
            if len(self._snapshots) < 2:
                return {
                    "nodes_per_day": 0.0,
                    "edges_per_day": 0.0,
                    "density_trend": 0.0,
                    "snapshot_count": len(self._snapshots),
                }

            first = self._snapshots[0]
            last = self._snapshots[-1]
            elapsed_days = max(
                (last["timestamp"] - first["timestamp"]) / 86400, 0.001
            )

            node_delta = last["node_count"] - first["node_count"]
            edge_delta = last["edge_count"] - first["edge_count"]
            density_delta = last["density"] - first["density"]

            return {
                "nodes_per_day": round(node_delta / elapsed_days, 2),
                "edges_per_day": round(edge_delta / elapsed_days, 2),
                "density_trend": round(density_delta / elapsed_days, 6),
                "snapshot_count": len(self._snapshots),
            }

    def get_trending_entities(
        self,
        window_hours: int = 24,
        edges: list | None = None,
    ) -> list[dict]:
        """
        Find entities with the most new edges in the given time window.

        Returns list of {entity_id, new_edge_count, total_degree} sorted
        by new_edge_count descending.
        """
        if edges is None:
            _, edges = _load_graph_data()

        cutoff = time.time() - (window_hours * 3600)
        entity_new_edges: dict[str, int] = defaultdict(int)

        for e in edges:
            timestamps = e.get("timestamps", [])
            recent = [ts for ts in timestamps if ts >= cutoff]
            if recent:
                count = len(recent)
                entity_new_edges[e.get("source", "")] += count
                entity_new_edges[e.get("target", "")] += count

        if not entity_new_edges:
            return []

        # Build adjacency for total degree
        adj = _build_adjacency_list(edges)

        trending = []
        for eid, new_count in entity_new_edges.items():
            if not eid:
                continue
            trending.append({
                "entity_id": eid,
                "new_edge_count": new_count,
                "total_degree": len(adj.get(eid, set())),
            })

        trending.sort(key=lambda x: x["new_edge_count"], reverse=True)
        return trending[:20]


# ══════════════════════════════════════════════════
#  GraphAnalytics (Facade)
# ══════════════════════════════════════════════════

class GraphAnalytics:
    """
    Facade that combines all advanced graph analytics.

    Lazy-loads data from memory_graph when needed.
    """

    def __init__(
        self,
        detector: CommunityDetector | None = None,
        predictor: LinkPredictor | None = None,
        anomaly: AnomalyDetector | None = None,
        temporal: TemporalEvolution | None = None,
    ):
        self._community = detector or CommunityDetector()
        self._predictor = predictor or LinkPredictor()
        self._anomaly = anomaly or AnomalyDetector()
        self._temporal = temporal or TemporalEvolution()
        self._lock = Lock()

    def full_analysis(self) -> dict:
        """
        Run all analytics and return a combined report.

        Returns dict with keys: communities, predictions, anomalies,
        evolution, health.
        """
        nodes, edges = _load_graph_data()

        communities = self._community.detect_communities(nodes, edges)
        community_summary = self._community.get_community_summary()
        predictions = self._predictor.predict_links(nodes, edges)
        anomalies = self._anomaly.detect_anomalies(nodes, edges)
        evolution = self._temporal.get_evolution(days=30)
        growth = self._temporal.get_growth_rate()
        health = self._compute_health(nodes, edges)

        return {
            "communities": {
                "count": len(communities),
                "summary": community_summary,
            },
            "predictions": {
                "count": len(predictions),
                "top_links": [
                    {"source": s, "target": t, "score": sc}
                    for s, t, sc in predictions[:5]
                ],
            },
            "anomalies": {
                "count": len(anomalies),
                "items": anomalies[:10],
            },
            "evolution": {
                "snapshots": len(evolution),
                "growth_rate": growth,
            },
            "health": health,
        }

    def get_recommendations(self, user_id: str) -> list[dict]:
        """
        Combine link prediction, community context, and trending entities
        to produce recommendations for a user.

        Returns list of {entity_id, reason, score}.
        """
        nodes, edges = _load_graph_data()

        recommendations: dict[str, dict] = {}

        # 1. Link prediction suggestions
        exploration = self._predictor.suggest_exploration(
            user_id, nodes=nodes, edges=edges
        )
        for eid in exploration[:5]:
            recommendations[eid] = {
                "entity_id": eid,
                "reason": "predicted_connection",
                "score": 0.7,
            }

        # 2. Community-based: find entities in the same community
        communities = self._community.detect_communities(nodes, edges)
        user_community = self._community.get_community_for(user_id)
        if user_community:
            adj = _build_adjacency_list(edges)
            user_neighbors = adj.get(user_id, set())
            for nid in user_community:
                if nid == user_id or nid in user_neighbors:
                    continue
                node_data = nodes.get(nid)
                if node_data:
                    ntype = (
                        node_data.get("type", "")
                        if isinstance(node_data, dict)
                        else getattr(node_data, "type", "")
                    )
                    if ntype == "entity" and nid not in recommendations:
                        recommendations[nid] = {
                            "entity_id": nid,
                            "reason": "same_community",
                            "score": 0.5,
                        }

        # 3. Trending entities
        trending = self._temporal.get_trending_entities(
            window_hours=24, edges=edges
        )
        for t in trending[:5]:
            eid = t["entity_id"]
            if eid not in recommendations and eid != user_id:
                recommendations[eid] = {
                    "entity_id": eid,
                    "reason": "trending",
                    "score": 0.3,
                }

        result = list(recommendations.values())
        result.sort(key=lambda r: r["score"], reverse=True)
        return result[:10]

    def get_health_report(self) -> dict:
        """
        Return graph health metrics.

        Includes: density, avg_degree, diameter_estimate, component_count,
        node_count, edge_count.
        """
        nodes, edges = _load_graph_data()
        return self._compute_health(nodes, edges)

    @staticmethod
    def _compute_health(nodes: dict, edges: list) -> dict:
        """Internal: compute health metrics for a given graph."""
        adj = _build_adjacency_list(edges)
        node_count = len(nodes)
        edge_count = len(edges)

        # Density
        if node_count > 1:
            density = (2 * edge_count) / (node_count * (node_count - 1))
        else:
            density = 0.0

        # Average degree
        if adj:
            degrees = [len(nbrs) for nbrs in adj.values()]
            avg_degree = sum(degrees) / len(degrees)
        else:
            avg_degree = 0.0

        # Components
        components = _bfs_components(adj)

        # Diameter estimate
        diameter = _estimate_diameter(adj, samples=5)

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": round(density, 6),
            "avg_degree": round(avg_degree, 2),
            "diameter_estimate": diameter,
            "component_count": len(components),
        }


# ══════════════════════════════════════════════════
#  Graph Data Loader (lazy bridge to memory_graph)
# ══════════════════════════════════════════════════

def _load_graph_data() -> tuple[dict, list]:
    """
    Load nodes and edges from the memory_graph singleton.

    Returns (nodes_dict, edges_list) where:
      - nodes_dict: {node_id: {"id":..., "type":..., "properties":...}}
      - edges_list: [{"source":..., "target":..., "relation":..., "weight":..., "timestamps":...}]

    Falls back to empty dicts/lists if memory_graph is unavailable.
    """
    try:
        from memory_graph import memory_graph
    except ImportError:
        try:
            from agent.memory_graph import memory_graph
        except ImportError:
            logger.warning("Could not import memory_graph; returning empty data")
            return {}, []

    # Access internal storage under lock
    with memory_graph._lock:
        nodes_dict = {}
        for nid, node in memory_graph._nodes.items():
            nodes_dict[nid] = node.to_dict()

        edges_list = []
        for edge in memory_graph._edges.values():
            edges_list.append(edge.to_dict())

    return nodes_dict, edges_list


# ══════════════════════════════════════════════════
#  Module Singletons
# ══════════════════════════════════════════════════

community_detector = CommunityDetector()
link_predictor = LinkPredictor()
anomaly_detector = AnomalyDetector()
temporal_evolution = TemporalEvolution()
graph_analytics = GraphAnalytics(
    detector=community_detector,
    predictor=link_predictor,
    anomaly=anomaly_detector,
    temporal=temporal_evolution,
)


# ══════════════════════════════════════════════════
#  CLI Test
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== vinhlong360 Advanced Graph Analytics -- Demo ===\n")

    # Build sample data (same shape as memory_graph exports)
    sample_nodes = {
        "user_A": {"id": "user_A", "type": "user", "properties": {"name": "User A", "mention_count": 5}},
        "cu-lao-an-binh": {"id": "cu-lao-an-binh", "type": "entity", "properties": {"name": "Cu Lao An Binh", "mention_count": 10}},
        "homestay-ut-trinh": {"id": "homestay-ut-trinh", "type": "entity", "properties": {"name": "Homestay Ut Trinh", "mention_count": 4}},
        "bun-nuoc-leo": {"id": "bun-nuoc-leo", "type": "entity", "properties": {"name": "Bun nuoc leo", "mention_count": 3}},
        "cho-noi-cai-be": {"id": "cho-noi-cai-be", "type": "entity", "properties": {"name": "Cho noi Cai Be", "mention_count": 0}},
        "vuon-trai-cay": {"id": "vuon-trai-cay", "type": "entity", "properties": {"name": "Vuon trai cay", "mention_count": 2}},
        "nha-co-long-ho": {"id": "nha-co-long-ho", "type": "entity", "properties": {"name": "Nha co Long Ho", "mention_count": 0}},
        "user_B": {"id": "user_B", "type": "user", "properties": {"name": "User B", "mention_count": 3}},
    }

    now = time.time()
    sample_edges = [
        {"source": "user_A", "target": "cu-lao-an-binh", "relation": "discussed", "weight": 3.0, "timestamps": [now - 3600, now - 1800, now]},
        {"source": "user_A", "target": "homestay-ut-trinh", "relation": "discussed", "weight": 2.0, "timestamps": [now - 3600, now]},
        {"source": "user_A", "target": "bun-nuoc-leo", "relation": "discussed", "weight": 1.0, "timestamps": [now - 7200]},
        {"source": "cu-lao-an-binh", "target": "homestay-ut-trinh", "relation": "co_mentioned", "weight": 4.0, "timestamps": [now - 3600, now - 1800, now - 900, now]},
        {"source": "cu-lao-an-binh", "target": "bun-nuoc-leo", "relation": "co_mentioned", "weight": 2.0, "timestamps": [now - 7200, now]},
        {"source": "cu-lao-an-binh", "target": "cho-noi-cai-be", "relation": "co_mentioned", "weight": 1.0, "timestamps": [now - 86400]},
        {"source": "homestay-ut-trinh", "target": "bun-nuoc-leo", "relation": "co_mentioned", "weight": 1.0, "timestamps": [now - 7200]},
        {"source": "user_B", "target": "cu-lao-an-binh", "relation": "discussed", "weight": 2.0, "timestamps": [now - 1800, now]},
        {"source": "user_B", "target": "vuon-trai-cay", "relation": "discussed", "weight": 1.0, "timestamps": [now - 3600]},
        {"source": "vuon-trai-cay", "target": "cu-lao-an-binh", "relation": "co_mentioned", "weight": 1.0, "timestamps": [now - 3600]},
    ]

    # ── Community Detection ──────────────────────
    print("1. Community Detection (Label Propagation)")
    communities = community_detector.detect_communities(sample_nodes, sample_edges)
    for i, comm in enumerate(communities):
        print(f"   Community {i}: {sorted(comm)}")
    print(f"   Summary: {community_detector.get_community_summary()}")

    user_comm = community_detector.get_community_for("user_A")
    print(f"   User A community: {sorted(user_comm) if user_comm else 'None'}")

    # ── Link Prediction ──────────────────────────
    print("\n2. Link Prediction")
    predictions = link_predictor.predict_links(sample_nodes, sample_edges, top_k=5)
    for src, tgt, score in predictions:
        print(f"   {src} <-> {tgt} (score={score})")

    exploration = link_predictor.suggest_exploration("user_A", sample_nodes, sample_edges)
    print(f"   Suggested for User A: {exploration}")

    # ── Anomaly Detection ────────────────────────
    print("\n3. Anomaly Detection")
    anomalies = anomaly_detector.detect_anomalies(sample_nodes, sample_edges)
    for a in anomalies:
        print(f"   [{a['type']}] severity={a['severity']} -- {a['description']}")
    if not anomalies:
        print("   No anomalies detected")

    # ── Temporal Evolution ───────────────────────
    print("\n4. Temporal Evolution")
    te = TemporalEvolution(snapshots_path=GRAPH_DATA_DIR / "snapshots_test.json")
    te.record_snapshot(nodes=sample_nodes, edges=sample_edges)
    print(f"   Snapshot recorded. Growth rate: {te.get_growth_rate()}")
    trending = te.get_trending_entities(window_hours=24, edges=sample_edges)
    print(f"   Trending entities (24h): {[(t['entity_id'], t['new_edge_count']) for t in trending[:5]]}")

    # Cleanup test snapshots
    test_snap = GRAPH_DATA_DIR / "snapshots_test.json"
    if test_snap.exists():
        test_snap.unlink()

    # ── Health Report ────────────────────────────
    print("\n5. Health Report")
    health = GraphAnalytics._compute_health(sample_nodes, sample_edges)
    for k, v in health.items():
        print(f"   {k}: {v}")

    # ── Helper Functions ─────────────────────────
    print("\n6. Helper Functions")
    adj = _build_adjacency_list(sample_edges)
    components = _bfs_components(adj)
    diameter = _estimate_diameter(adj)
    print(f"   Components: {len(components)}")
    print(f"   Diameter estimate: {diameter}")

    print("\n=== Demo complete ===")
