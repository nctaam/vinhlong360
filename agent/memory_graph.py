"""
vinhlong360 -- Graph-Based Relationship Memory.

Mo rong he thong nho (memory.py) bang do thi quan he giua entities,
cho phep "knowledge compounding" qua nhieu phien hoi thoai.

Lay cam hung tu Mem0 graph memory:
  - Theo doi entity nao user da kham pha
  - Lien ket entities thuong duoc de cap cung nhau (co-mention)
  - Goi y dia diem chua kham pha dua tren so thich da biet
  - Phat hien xu huong: combo dia diem pho bien

Kien truc:
  Nodes: user | entity | concept | preference
  Edges: discussed | interested_in | visited | compared_with | co_mentioned | recommended

Persistence: agent/data/memory/graph.json (atomic writes)
Thread-safe: threading.Lock
Dependencies: stdlib only (json, threading, time, pathlib, collections)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)


# ── Paths ────────────────────────────────────────

MEMORY_DIR = Path(__file__).resolve().parent / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_FILE = MEMORY_DIR / "graph.json"

# Valid relation types
VALID_RELATIONS = frozenset({
    "discussed", "interested_in", "visited",
    "compared_with", "co_mentioned", "recommended",
})

# Valid node types
VALID_NODE_TYPES = frozenset({
    "entity", "user", "concept", "preference",
})


# ══════════════════════════════════════════════════
#  Data Classes
# ══════════════════════════════════════════════════

@dataclass
class MemoryNode:
    """A node in the memory graph -- an entity, user, concept, or preference."""

    id: str
    type: str  # "entity" | "user" | "concept" | "preference"
    properties: dict = field(default_factory=dict)

    def __post_init__(self):
        now = time.time()
        self.properties.setdefault("first_seen", now)
        self.properties.setdefault("last_seen", now)
        self.properties.setdefault("mention_count", 0)

    def touch(self):
        """Update last_seen and increment mention_count."""
        self.properties["last_seen"] = time.time()
        self.properties["mention_count"] = self.properties.get("mention_count", 0) + 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryNode:
        return cls(
            id=data["id"],
            type=data["type"],
            properties=data.get("properties", {}),
        )


@dataclass
class MemoryEdge:
    """A weighted, timestamped edge between two nodes."""

    source: str
    target: str
    relation: str  # "discussed" | "interested_in" | "visited" | ...
    weight: float = 1.0
    timestamps: list[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamps:
            self.timestamps = [time.time()]

    _MAX_TIMESTAMPS = 100

    def reinforce(self, amount: float = 1.0):
        """Strengthen the edge and record the timestamp."""
        self.weight += amount
        self.timestamps.append(time.time())
        if len(self.timestamps) > self._MAX_TIMESTAMPS:
            self.timestamps = self.timestamps[-self._MAX_TIMESTAMPS:]

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryEdge:
        return cls(
            source=data["source"],
            target=data["target"],
            relation=data["relation"],
            weight=data.get("weight", 1.0),
            timestamps=data.get("timestamps", []),
        )


# ══════════════════════════════════════════════════
#  MemoryGraph
# ══════════════════════════════════════════════════

class MemoryGraph:
    """
    Dict-based adjacency-list graph for tracking entity relationships.

    Thread-safe, auto-persists after every N mutations.
    """

    def __init__(self, graph_path: Path | str | None = None, auto_save_every: int = 5):
        self._path = Path(graph_path) if graph_path else GRAPH_FILE
        self._lock = Lock()

        # Core storage
        self._nodes: dict[str, MemoryNode] = {}
        # Adjacency: node_id -> list of edge keys
        # Edge key = (source, target, relation)
        self._edges: dict[tuple[str, str, str], MemoryEdge] = {}
        self._adjacency: dict[str, set[tuple[str, str, str]]] = defaultdict(set)

        # Auto-save bookkeeping
        self._auto_save_every = auto_save_every
        self._mutations_since_save = 0

        # Load existing graph
        self._load()

    # ── Persistence ──────────────────────────────

    def _load(self):
        """Load graph from JSON file."""
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)

            for nd in data.get("nodes", []):
                node = MemoryNode.from_dict(nd)
                self._nodes[node.id] = node

            for ed in data.get("edges", []):
                edge = MemoryEdge.from_dict(ed)
                key = (edge.source, edge.target, edge.relation)
                self._edges[key] = edge
                self._adjacency[edge.source].add(key)
                self._adjacency[edge.target].add(key)

        except Exception as e:
            logger.warning("Failed to load graph: %s", e)

    def save(self):
        """Persist graph to disk with atomic write (write .tmp then rename)."""
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self):
        """Internal save -- caller must hold self._lock."""
        try:
            data = {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for e in self._edges.values()],
                "saved_at": time.time(),
            }
            content = json.dumps(data, ensure_ascii=False, indent=2)

            tmp_path = self._path.with_suffix(".tmp")
            tmp_path.write_text(content, encoding="utf-8")
            # Atomic rename (on Windows, need to remove target first)
            if self._path.exists():
                self._path.unlink()
            tmp_path.rename(self._path)

            self._mutations_since_save = 0
        except Exception as e:
            logger.warning("Failed to save graph: %s", e)

    def _maybe_auto_save(self):
        """Auto-save if we've hit the mutation threshold. Caller must hold lock."""
        self._mutations_since_save += 1
        if self._mutations_since_save >= self._auto_save_every:
            self._save_unlocked()

    # ── Core Operations ──────────────────────────

    def add_node(self, id: str, type: str = "entity",
                 properties: dict | None = None) -> MemoryNode:
        """Add a node or update an existing one. Returns the node."""
        with self._lock:
            if id in self._nodes:
                node = self._nodes[id]
                node.touch()
                if properties:
                    node.properties.update(properties)
            else:
                props = dict(properties) if properties else {}
                node = MemoryNode(id=id, type=type, properties=props)
                self._nodes[id] = node

            self._maybe_auto_save()
            return node

    def add_edge(self, source: str, target: str, relation: str,
                 weight: float = 1.0) -> MemoryEdge:
        """Add a new edge or strengthen an existing one. Returns the edge."""
        key = (source, target, relation)

        with self._lock:
            # Ensure both nodes exist
            if source not in self._nodes:
                self._nodes[source] = MemoryNode(id=source, type="entity")
            if target not in self._nodes:
                self._nodes[target] = MemoryNode(id=target, type="entity")

            if key in self._edges:
                edge = self._edges[key]
                edge.reinforce(weight)
            else:
                edge = MemoryEdge(source=source, target=target,
                                  relation=relation, weight=weight)
                self._edges[key] = edge
                self._adjacency[source].add(key)
                self._adjacency[target].add(key)

            self._maybe_auto_save()
            return edge

    def get_node(self, node_id: str) -> MemoryNode | None:
        """Get a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str, relation: str | None = None,
                      min_weight: float = 0) -> list[dict]:
        """
        Get all neighbors of a node, optionally filtered by relation and weight.

        Returns list of {node_id, relation, weight, direction} dicts.
        """
        with self._lock:
            results = []
            for key in self._adjacency.get(node_id, set()):
                edge = self._edges.get(key)
                if edge is None:
                    continue
                if relation and edge.relation != relation:
                    continue
                if edge.weight < min_weight:
                    continue

                # Determine the "other" node
                if edge.source == node_id:
                    other_id = edge.target
                    direction = "outgoing"
                else:
                    other_id = edge.source
                    direction = "incoming"

                other_node = self._nodes.get(other_id)
                results.append({
                    "node_id": other_id,
                    "node_type": other_node.type if other_node else "unknown",
                    "node_name": other_node.properties.get("name", other_id) if other_node else other_id,
                    "relation": edge.relation,
                    "weight": edge.weight,
                    "direction": direction,
                })
            # Sort by weight descending
            results.sort(key=lambda x: x["weight"], reverse=True)
            return results

    def get_path(self, source: str, target: str,
                 max_hops: int = 3) -> list[str] | None:
        """
        BFS shortest path between two nodes. Returns list of node IDs or None.
        """
        with self._lock:
            if source not in self._nodes or target not in self._nodes:
                return None
            if source == target:
                return [source]

            visited = {source}
            queue = deque([(source, [source])])

            while queue:
                current, path = queue.popleft()
                if len(path) > max_hops + 1:
                    break

                for key in self._adjacency.get(current, set()):
                    edge = self._edges.get(key)
                    if edge is None:
                        continue
                    neighbor = edge.target if edge.source == current else edge.source
                    if neighbor in visited:
                        continue

                    new_path = path + [neighbor]
                    if neighbor == target:
                        return new_path

                    visited.add(neighbor)
                    queue.append((neighbor, new_path))

            return None  # No path found

    def get_subgraph(self, node_id: str,
                     hops: int = 2) -> dict:
        """
        Get the local neighborhood around a node up to N hops.

        Returns {nodes: [...], edges: [...]}.
        """
        with self._lock:
            if node_id not in self._nodes:
                return {"nodes": [], "edges": []}

            collected_nodes: set[str] = {node_id}
            collected_edges: set[tuple[str, str, str]] = set()
            frontier = {node_id}

            for _ in range(hops):
                next_frontier = set()
                for nid in frontier:
                    for key in self._adjacency.get(nid, set()):
                        edge = self._edges.get(key)
                        if edge is None:
                            continue
                        collected_edges.add(key)
                        neighbor = edge.target if edge.source == nid else edge.source
                        if neighbor not in collected_nodes:
                            collected_nodes.add(neighbor)
                            next_frontier.add(neighbor)
                frontier = next_frontier

            nodes_out = [
                self._nodes[nid].to_dict()
                for nid in collected_nodes if nid in self._nodes
            ]
            edges_out = [
                self._edges[key].to_dict()
                for key in collected_edges if key in self._edges
            ]
            return {"nodes": nodes_out, "edges": edges_out}

    # ── Memory-Specific Operations ───────────────

    def record_interaction(self, user_id: str,
                           entities_discussed: list[str],
                           query: str = ""):
        """
        Record that a user discussed certain entities.

        Creates/strengthens:
          - user -> entity ("discussed") edges
          - entity <-> entity ("co_mentioned") edges for all pairs
        """
        # Ensure user node exists
        self.add_node(user_id, type="user", properties={"name": user_id})

        # User -> entity edges
        for eid in entities_discussed:
            self.add_node(eid, type="entity", properties={"name": eid})
            self.add_edge(user_id, eid, "discussed")

        # Co-mention edges between all entity pairs
        for i, a in enumerate(entities_discussed):
            for b in entities_discussed[i + 1:]:
                # Always store in alphabetical order for consistency
                if a > b:
                    a, b = b, a
                self.add_edge(a, b, "co_mentioned")

    def record_preference(self, user_id: str, entity_id: str,
                          score: float = 1.0):
        """Record user interest in an entity. Score is used as edge weight."""
        self.add_node(user_id, type="user", properties={"name": user_id})
        self.add_node(entity_id, type="entity", properties={"name": entity_id})
        self.add_edge(user_id, entity_id, "interested_in", weight=score)

    def record_comparison(self, user_id: str, entity_a: str, entity_b: str):
        """Record that a user compared two entities."""
        self.add_node(user_id, type="user", properties={"name": user_id})
        self.add_node(entity_a, type="entity", properties={"name": entity_a})
        self.add_node(entity_b, type="entity", properties={"name": entity_b})

        # User discussed both
        self.add_edge(user_id, entity_a, "discussed")
        self.add_edge(user_id, entity_b, "discussed")

        # The two entities are compared
        if entity_a > entity_b:
            entity_a, entity_b = entity_b, entity_a
        self.add_edge(entity_a, entity_b, "compared_with")

    def get_user_knowledge_map(self, user_id: str) -> dict:
        """
        Full subgraph of everything a user has explored.

        Returns {nodes, edges} of the user's neighborhood (2 hops).
        """
        return self.get_subgraph(user_id, hops=2)

    def suggest_unexplored(self, user_id: str, limit: int = 5) -> list[dict]:
        """
        Find entities connected to the user's interests but not yet discussed.

        Strategy:
          1. Get entities the user HAS discussed (1 hop, relation="discussed")
          2. Get neighbors of those entities (via co_mentioned, near, etc.)
          3. Filter out entities the user already discussed
          4. Rank by connection weight and return top N
        """
        with self._lock:
            if user_id not in self._nodes:
                return []

            # Step 1: entities user has discussed
            discussed_ids: set[str] = set()
            for key in self._adjacency.get(user_id, set()):
                edge = self._edges.get(key)
                if edge and edge.relation in ("discussed", "interested_in", "visited"):
                    other = edge.target if edge.source == user_id else edge.source
                    discussed_ids.add(other)

            if not discussed_ids:
                return []

            # Step 2: neighbors of discussed entities
            candidates: dict[str, float] = {}  # entity_id -> score
            for did in discussed_ids:
                for key in self._adjacency.get(did, set()):
                    edge = self._edges.get(key)
                    if edge is None:
                        continue
                    neighbor = edge.target if edge.source == did else edge.source
                    # Skip user nodes and already-discussed
                    node = self._nodes.get(neighbor)
                    if not node or node.type == "user":
                        continue
                    if neighbor in discussed_ids or neighbor == user_id:
                        continue
                    candidates[neighbor] = candidates.get(neighbor, 0) + edge.weight

            # Step 3: sort by score and return top N
            ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
            results = []
            for eid, score in ranked[:limit]:
                node = self._nodes.get(eid)
                results.append({
                    "entity_id": eid,
                    "name": node.properties.get("name", eid) if node else eid,
                    "type": node.type if node else "entity",
                    "relevance_score": round(score, 2),
                })
            return results

    def find_common_interests(self, user_a: str, user_b: str) -> list[dict]:
        """
        Find entities that both users have discussed or shown interest in.
        """
        with self._lock:
            def _get_entity_set(uid: str) -> set[str]:
                entities = set()
                for key in self._adjacency.get(uid, set()):
                    edge = self._edges.get(key)
                    if edge and edge.relation in ("discussed", "interested_in"):
                        other = edge.target if edge.source == uid else edge.source
                        node = self._nodes.get(other)
                        if node and node.type != "user":
                            entities.add(other)
                return entities

            set_a = _get_entity_set(user_a)
            set_b = _get_entity_set(user_b)
            common = set_a & set_b

            results = []
            for eid in common:
                node = self._nodes.get(eid)
                results.append({
                    "entity_id": eid,
                    "name": node.properties.get("name", eid) if node else eid,
                    "type": node.type if node else "entity",
                })
            return results

    # ── Knowledge Compounding ────────────────────

    def get_emerging_patterns(self, min_weight: float = 3.0) -> list[dict]:
        """
        Find frequently co-mentioned entity pairs (popular combinations).

        Returns list of {entity_a, entity_b, relation, weight} sorted by weight.
        """
        with self._lock:
            patterns = []
            for key, edge in self._edges.items():
                if edge.relation == "co_mentioned" and edge.weight >= min_weight:
                    node_a = self._nodes.get(edge.source)
                    node_b = self._nodes.get(edge.target)
                    patterns.append({
                        "entity_a": edge.source,
                        "name_a": node_a.properties.get("name", edge.source) if node_a else edge.source,
                        "entity_b": edge.target,
                        "name_b": node_b.properties.get("name", edge.target) if node_b else edge.target,
                        "relation": edge.relation,
                        "weight": edge.weight,
                    })
            patterns.sort(key=lambda x: x["weight"], reverse=True)
            return patterns

    def get_trending_paths(self, days: int = 7) -> list[dict]:
        """
        Find most recently active entity connections.

        Returns edges that have been reinforced in the last N days,
        sorted by most recent activity.
        """
        cutoff = time.time() - (days * 86400)

        with self._lock:
            trending = []
            for key, edge in self._edges.items():
                recent_ts = [t for t in edge.timestamps if t >= cutoff]
                if recent_ts:
                    node_a = self._nodes.get(edge.source)
                    node_b = self._nodes.get(edge.target)
                    trending.append({
                        "source": edge.source,
                        "name_source": node_a.properties.get("name", edge.source) if node_a else edge.source,
                        "target": edge.target,
                        "name_target": node_b.properties.get("name", edge.target) if node_b else edge.target,
                        "relation": edge.relation,
                        "weight": edge.weight,
                        "recent_count": len(recent_ts),
                        "last_active": max(recent_ts),
                    })
            trending.sort(key=lambda x: x["last_active"], reverse=True)
            return trending

    def decay_weights(self, factor: float = 0.95):
        """
        Apply time decay to all edge weights to keep the graph fresh.

        Edges that drop below 0.1 weight are removed.
        """
        with self._lock:
            to_remove = []
            for key, edge in self._edges.items():
                edge.weight *= factor
                if edge.weight < 0.1:
                    to_remove.append(key)

            for key in to_remove:
                edge = self._edges.pop(key, None)
                if edge:
                    self._adjacency[edge.source].discard(key)
                    self._adjacency[edge.target].discard(key)

            if to_remove:
                self._maybe_auto_save()
            else:
                self._save_unlocked()

    def health_check(self) -> dict:
        """Quick readiness probe for the memory graph."""
        with self._lock:
            return {
                "status": "ok" if self._nodes else "empty",
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "file_exists": self._path.exists(),
            }

    # ── LLM-Based Fact Extraction (optional) ─────

    def extract_facts(self, message: str, reply: str) -> list[tuple[str, str, str]]:
        """
        Extract (subject, relation, object) triples from a conversation turn.

        §B8: LLM-based extraction là LLM-call TỰ ĐỘNG (mỗi chat turn) → CHỈ chạy khi
        agent nền được opt-in (AUTONOMOUS_AGENT_ENABLED) VÀ còn trong cap/ngày. Mặc định
        OFF → dùng heuristic keyword, KHÔNG gọi LLM tự động (tránh rò chi phí 24/7).
        Returns list of (subject, relation, object) tuples.
        """
        try:
            from autonomous_budget import enabled as _ab_enabled, try_consume as _ab_consume
            if _ab_enabled() and _ab_consume(1):
                return self._extract_facts_llm(message, reply)
        except Exception as exc:
            logger.warning("LLM fact extraction failed, using keywords: %s", exc)
        return self._extract_facts_keywords(message, reply)

    def _extract_facts_llm(self, message: str, reply: str) -> list[tuple[str, str, str]]:
        """
        Use LLM to extract factual relationships from conversation.

        Uses the project's OpenAI-compatible endpoint (see .env).
        """
        from openai import OpenAI
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        api_key = os.environ.get("LLM_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL")
        if not api_key or not base_url:
            raise RuntimeError("LLM credentials not configured")

        client = OpenAI(api_key=api_key, base_url=base_url)
        model = os.environ.get("LLM_MODEL", "cx/gpt-5.4-mini")

        prompt = (
            "Extract factual relationships from this conversation about "
            "Vinh Long tourism. Return ONLY a JSON array of triples: "
            '[[subject, relation, object], ...]\n'
            "Relations should be one of: discussed, interested_in, visited, "
            "compared_with, co_mentioned, recommended, located_in, "
            "famous_for, near.\n"
            "Keep subjects and objects as concise entity names (Vietnamese OK).\n\n"
            f"User: {message}\n"
            f"Assistant: {reply}\n\n"
            "JSON array:"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            timeout=8,
        )

        text = response.choices[0].message.content.strip()
        # Parse JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        try:
            triples_raw = json.loads(text)
            return [(t[0], t[1], t[2]) for t in triples_raw if len(t) >= 3]
        except (json.JSONDecodeError, TypeError, IndexError) as exc:
            logger.warning("LLM triple extraction parse failed: %s, raw=%s", exc, text[:200])
            return []

    def _extract_facts_keywords(self, message: str,
                                reply: str) -> list[tuple[str, str, str]]:
        """
        Fallback: extract entity mentions using keyword matching.

        Simple heuristic approach -- looks for known Vietnamese tourism terms.
        """
        combined = f"{message} {reply}".lower()

        # Normalize Vietnamese
        def _norm(text: str) -> str:
            s = unicodedata.normalize("NFD", text.lower())
            s = re.sub(r"[̀-ͯ]", "", s)
            return s.replace("đ", "d").replace("Đ", "D")

        combined_norm = _norm(combined)

        # Common Vinh Long tourism entities for keyword extraction
        known_entities = {
            "cu lao an binh": "Cu Lao An Binh",
            "homestay ut trinh": "Homestay Ut Trinh",
            "bun nuoc leo": "Bun nuoc leo",
            "cho noi cai be": "Cho noi Cai Be",
            "vinh long": "Vinh Long",
            "ben tre": "Ben Tre",
            "tra vinh": "Tra Vinh",
            "nha co": "Nha co",
            "vuon trai cay": "Vuon trai cay",
            "banh trang": "Banh trang",
            "hu tieu": "Hu tieu",
            "chua": "Chua",
            "cho": "Cho",
        }

        found = []
        for key, name in known_entities.items():
            if key in combined_norm:
                found.append(name)

        # Generate triples from found entities
        triples = []
        for i, entity in enumerate(found):
            triples.append((entity, "discussed", "conversation"))
            for other in found[i + 1:]:
                triples.append((entity, "co_mentioned", other))

        return triples

    # ── Integration Helpers ──────────────────────

    def build_graph_context(self, user_id: str) -> str:
        """
        Build a formatted context string for the system prompt,
        summarizing what the user has explored and what's nearby.

        Example output:
          "User da kham pha: Cu Lao An Binh -> Homestay Ut Trinh -> Bun nuoc leo.
           Chua kham pha: Cho noi Cai Be (gan Cu Lao An Binh)."
        """
        with self._lock:
            if user_id not in self._nodes:
                return ""

            # Entities the user has discussed/visited (deduplicate by id,
            # keeping the highest-weight edge per entity)
            discussed_map: dict[str, dict] = {}
            for key in self._adjacency.get(user_id, set()):
                edge = self._edges.get(key)
                if not edge:
                    continue
                if edge.relation in ("discussed", "visited", "interested_in"):
                    other = edge.target if edge.source == user_id else edge.source
                    node = self._nodes.get(other)
                    if node and node.type != "user":
                        existing = discussed_map.get(other)
                        if not existing or edge.weight > existing["weight"]:
                            discussed_map[other] = {
                                "id": other,
                                "name": node.properties.get("name", other),
                                "weight": edge.weight,
                                "relation": edge.relation,
                            }
            discussed = list(discussed_map.values())

            if not discussed:
                return ""

            # Sort by weight (most discussed first)
            discussed.sort(key=lambda x: x["weight"], reverse=True)

        # Build explored string
        explored_names = [d["name"] for d in discussed[:8]]
        parts = []
        parts.append("User da kham pha: " + " -> ".join(explored_names))

        # Suggest unexplored (release lock, then call suggest_unexplored)
        suggestions = self.suggest_unexplored(user_id, limit=3)
        if suggestions:
            suggestion_parts = []
            for s in suggestions:
                # Find what it's connected to
                neighbors = self.get_neighbors(s["entity_id"], relation="co_mentioned")
                if neighbors:
                    closest = neighbors[0]["node_name"]
                    suggestion_parts.append(f"{s['name']} (gan {closest})")
                else:
                    suggestion_parts.append(s["name"])
            parts.append("Chua kham pha: " + ", ".join(suggestion_parts))

        # Emerging patterns relevant to user
        patterns = self.get_emerging_patterns(min_weight=2.0)
        if patterns:
            top = patterns[0]
            parts.append(
                f"Combo pho bien: {top['name_a']} + {top['name_b']} "
                f"(duoc {int(top['weight'])} nguoi de cap cung)"
            )

        return ". ".join(parts) + "."

    def on_chat_complete(self, user_id: str, message: str, reply: str,
                         entities_mentioned: list[str]):
        """
        Hook to call after each chat turn completes.

        1. Records the interaction (user <-> entities)
        2. Extracts facts from the conversation
        3. Applies extracted facts to the graph
        """
        # Record direct entity interactions
        if entities_mentioned:
            self.record_interaction(user_id, entities_mentioned, query=message)

        # Try to extract additional facts
        try:
            facts = self.extract_facts(message, reply)
            for subj, rel, obj in facts:
                # Normalize relation to valid types
                normalized_rel = rel if rel in VALID_RELATIONS else "co_mentioned"
                self.add_node(subj, type="entity", properties={"name": subj})
                self.add_node(obj, type="entity", properties={"name": obj})
                self.add_edge(subj, obj, normalized_rel)
        except Exception:
            logger.debug("Fact extraction failed (best-effort)", exc_info=True)

        # Final save
        self.save()

    # ── Stats & Debug ────────────────────────────

    def stats(self) -> dict:
        """Return summary statistics about the graph."""
        with self._lock:
            type_counts = defaultdict(int)
            for n in self._nodes.values():
                type_counts[n.type] += 1

            rel_counts = defaultdict(int)
            for e in self._edges.values():
                rel_counts[e.relation] += 1

            return {
                "total_nodes": len(self._nodes),
                "total_edges": len(self._edges),
                "node_types": dict(type_counts),
                "relation_types": dict(rel_counts),
            }

    def __repr__(self) -> str:
        s = self.stats()
        return (
            f"<MemoryGraph nodes={s['total_nodes']} edges={s['total_edges']} "
            f"types={s['node_types']}>"
        )


# ══════════════════════════════════════════════════
#  Module Singleton
# ══════════════════════════════════════════════════

memory_graph = MemoryGraph()


# ══════════════════════════════════════════════════
#  CLI Test
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== vinhlong360 Memory Graph -- Demo ===\n")

    g = MemoryGraph(graph_path=MEMORY_DIR / "graph_test.json")

    # ── Simulate user interactions ────────────────

    print("1. User A explores Cu Lao An Binh and homestays...")
    g.record_interaction("user_A", [
        "cu-lao-an-binh", "homestay-ut-trinh", "bun-nuoc-leo"
    ], query="Toi muon di Cu Lao An Binh, o homestay nao tot?")

    # Add names to entities
    g.add_node("cu-lao-an-binh", "entity", {"name": "Cu Lao An Binh"})
    g.add_node("homestay-ut-trinh", "entity", {"name": "Homestay Ut Trinh"})
    g.add_node("bun-nuoc-leo", "entity", {"name": "Bun nuoc leo"})
    g.add_node("cho-noi-cai-be", "entity", {"name": "Cho noi Cai Be"})
    g.add_node("vuon-trai-cay-vinh-long", "entity", {"name": "Vuon trai cay Vinh Long"})
    g.add_node("nha-co-long-ho", "entity", {"name": "Nha co Long Ho"})

    print("2. User A asks about food...")
    g.record_interaction("user_A", [
        "bun-nuoc-leo", "hu-tieu-my-tho"
    ], query="Dac san Vinh Long an gi ngon?")
    g.add_node("hu-tieu-my-tho", "entity", {"name": "Hu tieu My Tho"})

    print("3. User A compares two destinations...")
    g.record_comparison("user_A", "cu-lao-an-binh", "cho-noi-cai-be")

    print("4. User A marks preference...")
    g.record_preference("user_A", "cu-lao-an-binh", score=2.0)

    print("5. User B explores some overlapping entities...")
    g.record_interaction("user_B", [
        "cu-lao-an-binh", "vuon-trai-cay-vinh-long", "nha-co-long-ho"
    ], query="Vinh Long co gi tham quan?")

    # Add a co_mention link to simulate popular combo
    g.add_edge("cu-lao-an-binh", "cho-noi-cai-be", "co_mentioned", weight=2.0)

    # ── Query the graph ──────────────────────────

    print("\n--- Graph Stats ---")
    print(f"  {g}")
    stats = g.stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n--- User A's neighbors ---")
    neighbors = g.get_neighbors("user_A")
    for n in neighbors:
        print(f"  -> {n['node_name']} ({n['relation']}, weight={n['weight']:.1f})")

    print("\n--- Path from User A to Nha co Long Ho ---")
    path = g.get_path("user_A", "nha-co-long-ho")
    if path:
        print(f"  {' -> '.join(path)}")
    else:
        print("  No path found")

    print("\n--- Suggest unexplored for User A ---")
    suggestions = g.suggest_unexplored("user_A", limit=5)
    for s in suggestions:
        print(f"  * {s['name']} (relevance: {s['relevance_score']})")

    print("\n--- Common interests: User A & User B ---")
    common = g.find_common_interests("user_A", "user_B")
    for c in common:
        print(f"  * {c['name']}")

    print("\n--- Emerging patterns (min_weight=2) ---")
    patterns = g.get_emerging_patterns(min_weight=2.0)
    for p in patterns:
        print(f"  {p['name_a']} + {p['name_b']} (weight: {p['weight']:.1f})")

    print("\n--- Trending paths (last 7 days) ---")
    trending = g.get_trending_paths(days=7)
    for t in trending[:5]:
        print(f"  {t['name_source']} -> {t['name_target']} ({t['relation']}, "
              f"recent: {t['recent_count']}x)")

    print("\n--- Graph context for User A ---")
    ctx = g.build_graph_context("user_A")
    print(f"  {ctx}")

    print("\n--- User A knowledge map ---")
    kmap = g.get_user_knowledge_map("user_A")
    print(f"  Nodes: {len(kmap['nodes'])}, Edges: {len(kmap['edges'])}")
    for n in kmap["nodes"]:
        print(f"    [{n['type']}] {n['properties'].get('name', n['id'])}")

    # Save and cleanup
    g.save()

    # Remove test file
    test_file = MEMORY_DIR / "graph_test.json"
    if test_file.exists():
        test_file.unlink()

    print("\n=== Demo complete (test file cleaned up) ===")
