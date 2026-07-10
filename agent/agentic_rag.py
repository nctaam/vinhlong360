"""
vinhlong360 — Agentic RAG (Adaptive + Corrective + Graph-Enhanced).

Kiến trúc 2026 — 3 tầng:

  TẦNG 1: ADAPTIVE ROUTING
    Phân loại độ phức tạp query → chọn chiến lược:
    - Simple: direct KB lookup (1 tool call)
    - Moderate: multi-tool search + season check
    - Complex: multi-hop reasoning + web search + LLM synthesis

  TẦNG 2: CORRECTIVE RAG
    Sau khi retrieve → đánh giá relevance:
    - Nếu relevant: sinh câu trả lời
    - Nếu irrelevant: reformulate query → re-search
    - Nếu ambiguous: ask clarification hoặc web search

  TẦNG 3: GRAPH-ENHANCED REASONING
    Dùng relationship graph để multi-hop:
    - Entity A → related_to → Entity B → near → Entity C
    - Expand context qua graph traversal
    - Cung cấp richer context cho LLM

Tham khảo: Agentic RAG Survey 2026 (arXiv:2501.09136v4)
"""

import heapq
import logging
import re
import unicodedata
from collections import deque
from typing import Literal

import knowledge

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════
#  TẦNG 1: ADAPTIVE QUERY ROUTER
# ══════════════════════════════════════════════════

QueryComplexity = Literal["simple", "moderate", "complex"]


def classify_query(query: str) -> dict:
    """
    Phân loại query theo độ phức tạp.

    Returns: {
        complexity: "simple" | "moderate" | "complex",
        intent: str,
        suggested_tools: [str],
        entities_detected: [str],
        areas_detected: [str],
    }
    """
    q = query.lower().strip()

    # Detect entities, areas, intents
    entities = _detect_entities(q)
    areas = _detect_areas(q)
    intent = _detect_intent(q)

    # ── Classify complexity ──

    # SIMPLE: direct lookup, single entity/fact
    if intent in ("entity_detail", "simple_fact") and entities:
        return {
            "complexity": "simple",
            "intent": intent,
            "suggested_tools": ["entity_detail"] if len(entities) == 1 else ["search"],
            "entities_detected": entities,
            "areas_detected": areas,
        }

    # COMPLEX: comparison, itinerary planning, multi-hop, opinion
    if intent in ("comparison", "itinerary", "multi_hop", "open_ended"):
        tools = []
        if intent == "comparison":
            tools = ["compare_areas", "search", "search"]
        elif intent == "itinerary":
            tools = ["seasonal_now", "generate_itinerary", "suggest_followups"]
        elif intent == "multi_hop":
            tools = ["search", "entity_detail", "nearby_entities"]
        else:
            tools = ["search", "web_search", "suggest_followups"]

        return {
            "complexity": "complex",
            "intent": intent,
            "suggested_tools": tools,
            "entities_detected": entities,
            "areas_detected": areas,
        }

    # MODERATE: search with filters, seasonal, area-based
    tools = ["search"]
    if areas:
        tools.append("places_in_area")
    if _is_seasonal_query(q):
        tools.append("seasonal_now")
    tools.append("suggest_followups")

    return {
        "complexity": "moderate",
        "intent": intent,
        "suggested_tools": tools,
        "entities_detected": entities,
        "areas_detected": areas,
    }


def get_routing_prompt(classification: dict) -> str:
    """Tạo routing instruction cho agent dựa trên classification."""
    c = classification["complexity"]
    intent = classification["intent"]
    tools = classification["suggested_tools"]

    prompt_parts = [f"[Query Analysis]: Complexity={c}, Intent={intent}"]

    if c == "simple":
        prompt_parts.append("→ Tra cứu trực tiếp, trả lời ngắn gọn chính xác.")
        if classification["entities_detected"]:
            prompt_parts.append(f"Entity IDs thử: {', '.join(classification['entities_detected'][:3])}")

    elif c == "moderate":
        prompt_parts.append("→ Search knowledge base, kết hợp nhiều nguồn nếu cần.")
        if classification["areas_detected"]:
            prompt_parts.append(f"Areas: {', '.join(classification['areas_detected'])}")

    elif c == "complex":
        prompt_parts.append("→ Multi-step reasoning. Dùng nhiều tools, tổng hợp thông tin.")
        if intent == "comparison":
            prompt_parts.append("Dùng compare_areas hoặc search cả 2 bên rồi so sánh.")
        elif intent == "itinerary":
            prompt_parts.append("Kiểm tra seasonal_now trước, rồi generate_itinerary hoặc list_itineraries.")
        elif intent == "multi_hop":
            prompt_parts.append("Dùng entity_detail → nearby_entities để mở rộng context.")

    prompt_parts.append(f"Suggested tools: {' → '.join(tools)}")

    return "\n".join(prompt_parts)


# ══════════════════════════════════════════════════
#  TẦNG 2: CORRECTIVE RAG
# ══════════════════════════════════════════════════

def evaluate_retrieval_relevance(query: str, results: list[dict]) -> dict:
    """
    Đánh giá relevance của kết quả search.

    Returns: {
        status: "relevant" | "partially_relevant" | "irrelevant",
        confidence: float,
        suggestion: str,
    }
    """
    if not results:
        return {
            "status": "irrelevant",
            "confidence": 0,
            "suggestion": "Không tìm thấy kết quả. Thử web_search hoặc reformulate query.",
            "reformulated_query": _reformulate_query(query),
        }

    # Check keyword overlap between query and results
    q_words = set(_normalize(query).split())
    total_overlap = 0

    for r in results[:5]:
        r_text = _normalize(r.get("name", "") + " " + r.get("summary", ""))
        r_words = set(r_text.split())
        overlap = len(q_words & r_words)
        total_overlap += overlap

    avg_overlap = total_overlap / max(len(results[:5]), 1)

    if avg_overlap >= 2:
        return {
            "status": "relevant",
            "confidence": min(avg_overlap / 3, 1.0),
            "suggestion": "Kết quả phù hợp. Tiếp tục tổng hợp.",
        }
    elif avg_overlap >= 1:
        return {
            "status": "partially_relevant",
            "confidence": 0.4,
            "suggestion": "Kết quả chưa chắc chắn. Thử search thêm với từ khóa khác.",
            "reformulated_query": _reformulate_query(query),
        }
    else:
        return {
            "status": "irrelevant",
            "confidence": 0.1,
            "suggestion": "Kết quả không liên quan. Thử web_search.",
            "reformulated_query": _reformulate_query(query),
        }


def _reformulate_query(query: str) -> str:
    """Reformulate query để tìm kiếm lại."""
    # Remove question words
    q = re.sub(r"^(cho tôi biết|hãy|xin|vui lòng|bạn có thể)\s+", "", query, flags=re.IGNORECASE)
    q = re.sub(r"\?+$", "", q).strip()

    # Add location context if missing
    if not any(a in q.lower() for a in ["vĩnh long", "bến tre", "trà vinh"]):
        q += " Vĩnh Long"

    return q


# ══════════════════════════════════════════════════
#  TẦNG 3: GRAPH-ENHANCED REASONING
# ══════════════════════════════════════════════════

# Relationship type scores — higher = explore first (priority queue)
_REL_SCORES: dict[str, float] = {
    "near": 1.0,
    "Gần": 1.0,
    "cùng xã/phường": 0.9,
    "cùng khu vực": 0.85,
    "related_to": 0.8,
    "belongs_to": 0.7,
    "Tổ chức": 0.7,
    "Diễn ra tại": 0.7,
    "Đặt qua": 0.6,
    "Cung cấp": 0.6,
    "Sản xuất bởi": 0.6,
    "Sản phẩm": 0.6,
    "Sản xuất tại": 0.6,
    "Đặc sản": 0.6,
    "Nguồn cung": 0.5,
    "Cung ứng cho": 0.5,
}

# Diversity bonus when crossing to a different entity type
_DIVERSITY_BONUS = 0.15


def _rel_score(label: str) -> float:
    """Score a relationship label for priority ordering."""
    return _REL_SCORES.get(label, 0.5)


def _expand_rels(eid, hop, path, counter, visited, visited_types, edges, pq):
    """Xử lý relationships của 1 node trong graph_expand. Trả về counter mới."""
    rels = knowledge.related(eid)
    for r in rels:
        other_id = r["id"]
        label = r["label"]
        edges.append({
            "from": eid,
            "to": other_id,
            "label": label,
        })
        if other_id not in visited:
            other_e = knowledge.get_entity(other_id)
            # Calculate priority
            score = _rel_score(label)
            # Diversity bonus: prefer different types
            if other_e and other_e["type"] not in visited_types:
                score += _DIVERSITY_BONUS
            counter += 1
            new_path = path + [f"—{label}→", other_id]
            heapq.heappush(pq, (-score, counter, other_id, hop + 1, new_path))
    return counter


def _expand_nearby(eid, hop, path, counter, visited, visited_types, edges, pq):
    """Xử lý nearby entities của 1 node trong graph_expand. Trả về counter mới."""
    nearby = knowledge.nearby_entities(eid, limit=5)
    for n in nearby:
        if n["id"] not in visited:
            prox = n.get("proximity", "near")
            edges.append({
                "from": eid,
                "to": n["id"],
                "label": prox,
            })
            score = _rel_score(prox)
            other_e = knowledge.get_entity(n["id"])
            if other_e and other_e["type"] not in visited_types:
                score += _DIVERSITY_BONUS
            counter += 1
            new_path = path + [f"—{prox}→", n["id"]]
            heapq.heappush(pq, (-score, counter, n["id"], hop + 1, new_path))
    return counter


def _visit_graph_node(eid, hop, path, nodes, visited_types):
    """Xử lý 1 node đã pop: ghi vào nodes. Trả về entity dict, hoặc None nếu bỏ qua."""
    e = knowledge.get_entity(eid)
    if not e:
        return None

    visited_types.add(e["type"])

    nodes.append({
        "id": eid,
        "name": e["name"],
        "type": e["type"],
        "summary": e.get("summary", "")[:100],
        "hop": hop,
        "path": path,
    })
    return e


def graph_expand(entity_id: str, max_hops: int = 3, max_nodes: int = 25) -> dict:
    """
    Multi-hop graph traversal từ 1 entity (lên tới 3+ hops).

    Features:
      - Path tracking: mỗi node ghi lại chuỗi dẫn tới nó
      - Relationship scoring: ưu tiên khám phá quan hệ có score cao
      - Cross-type discovery: ưu tiên node có type khác để tăng tính đa dạng

    Trả về subgraph với entities + relationships trong N hops.
    Giúp LLM có richer context để trả lời.
    """
    knowledge._ensure()

    visited: set[str] = set()
    visited_types: set[str] = set()
    nodes: list[dict] = []
    edges: list[dict] = []

    # Priority queue: (-priority, counter, entity_id, hop, path)
    # Negative priority because heapq is a min-heap.
    counter = 0
    pq: list[tuple[float, int, str, int, list[str]]] = []
    heapq.heappush(pq, (0.0, counter, entity_id, 0, [entity_id]))

    while pq and len(nodes) < max_nodes:
        neg_pri, _cnt, eid, hop, path = heapq.heappop(pq)
        if eid in visited or hop > max_hops:
            continue
        visited.add(eid)

        e = _visit_graph_node(eid, hop, path, nodes, visited_types)
        if not e:
            continue

        if hop >= max_hops:
            continue

        # Get relationships
        counter = _expand_rels(eid, hop, path, counter, visited, visited_types, edges, pq)

        # Also check nearby (same placeId) — expanded to hops 0 and 1
        if hop <= 1:
            counter = _expand_nearby(eid, hop, path, counter, visited, visited_types, edges, pq)

    return {
        "root": entity_id,
        "nodes": nodes,
        "edges": edges,
        "hops": max_hops,
    }


def _format_path_segment(segment: str) -> str:
    """Format 1 segment của path: label (—...→) giữ nguyên chữ; entity id → tên."""
    if segment.startswith("—") and segment.endswith("→"):
        # Relationship label
        return segment[1:-1]  # strip — and →
    # Entity id — resolve to name
    ent = knowledge.get_entity(segment)
    return ent["name"] if ent else segment


def _format_cross_paths(graph_nodes: list[dict]) -> list[str]:
    """Dựng danh sách chuỗi liên kết cross-domain từ path của các node ≥2 hop."""
    cross_paths = []
    for n in graph_nodes:
        if n["hop"] >= 2 and n.get("path") and len(n["path"]) >= 5:
            # Format path: entity → rel → entity → rel → entity
            path_parts = [_format_path_segment(segment) for segment in n["path"]]
            cross_paths.append(" → ".join(path_parts))
    return cross_paths


def graph_context_prompt(entity_id: str) -> str:
    """
    Tạo context prompt từ graph expansion (lên tới 3 hops).
    Inject vào system message để LLM có multi-hop context.
    Bao gồm path information và cross-domain connections.
    """
    graph = graph_expand(entity_id, max_hops=3, max_nodes=15)

    if len(graph["nodes"]) <= 1:
        return ""

    root_name = graph["nodes"][0]["name"]
    lines = [f"[Graph context cho {root_name}]:"]

    # Group by hop
    hop_labels = {1: "Liên quan trực tiếp", 2: "Liên quan gián tiếp (2 hops)", 3: "Liên quan xa (3 hops)"}
    for hop in range(1, 4):
        hop_nodes = [n for n in graph["nodes"] if n["hop"] == hop]
        if hop_nodes:
            items = ", ".join(f"{n['name']} ({n['type']})" for n in hop_nodes[:5])
            lines.append(f"  {hop_labels.get(hop, f'Hop {hop}')}: {items}")

    # Show cross-domain paths (nodes that cross entity types)
    cross_paths = _format_cross_paths(graph["nodes"])

    if cross_paths:
        lines.append("  Chuỗi liên kết:")
        for cp in cross_paths[:5]:
            lines.append(f"    • {cp}")

    # Key edges
    unique_labels = set(e["label"] for e in graph["edges"])
    if unique_labels:
        lines.append(f"  Quan hệ: {', '.join(unique_labels)}")

    return "\n".join(lines)


def _collect_neighbors(current: str) -> list[tuple[str, str]]:
    """Gom neighbors của 1 node: relationships + nearby entities (khử trùng theo id)."""
    # Get neighbors via relationships
    rels = knowledge.related(current)
    neighbors: list[tuple[str, str]] = [(r["id"], r["label"]) for r in rels]

    # Also get nearby entities
    nearby = knowledge.nearby_entities(current, limit=5)
    for n in nearby:
        nid = n["id"]
        if nid not in {nb[0] for nb in neighbors}:
            neighbors.append((nid, n.get("proximity", "near")))
    return neighbors


def _should_explore_path(neighbor_id, new_path, visited_at_depth) -> bool:
    """Quyết định có enqueue path mới không; cập nhật visited_at_depth như logic gốc."""
    new_depth = len(new_path) - 1
    # Only explore if we haven't visited at a shallower depth, or allow up to +1
    prev_depth = visited_at_depth.get(neighbor_id)
    if prev_depth is not None and new_depth > prev_depth + 1:
        return False
    visited_at_depth[neighbor_id] = min(new_depth, prev_depth or new_depth)
    return True


def find_paths(entity_a: str, entity_b: str, max_hops: int = 4) -> list[list[tuple[str, str]]]:
    """
    BFS để tìm tất cả paths giữa 2 entities (tối đa max_hops).

    Returns: list of paths, mỗi path = list of (entity_id, relationship_label) tuples.
    Giới hạn tối đa 5 paths.
    """
    knowledge._ensure()

    if entity_a == entity_b:
        return [[(entity_a, "")]]

    # BFS with path tracking
    # Queue item: (current_entity_id, path_so_far)
    # path_so_far = [(entity_id, rel_label), ...]
    queue: deque[tuple[str, list[tuple[str, str]]]] = deque()
    queue.append((entity_a, [(entity_a, "start")]))

    found_paths: list[list[tuple[str, str]]] = []
    visited_at_depth: dict[str, int] = {entity_a: 0}

    while queue and len(found_paths) < 5:
        current, path = queue.popleft()
        current_depth = len(path) - 1

        if current_depth >= max_hops:
            continue

        neighbors = _collect_neighbors(current)

        for neighbor_id, label in neighbors:
            # Skip if we already visited this node at a shallower or equal depth
            # (allow revisiting at deeper depth for finding alternative paths)
            if neighbor_id in {p[0] for p in path}:
                continue  # Avoid cycles within the same path

            new_path = path + [(neighbor_id, label)]

            if neighbor_id == entity_b:
                found_paths.append(new_path)
                if len(found_paths) >= 5:
                    break
                continue

            if _should_explore_path(neighbor_id, new_path, visited_at_depth):
                queue.append((neighbor_id, new_path))

    return found_paths


# Concept keyword map cho cross_domain_query (có dấu + không dấu).
_CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "person": [
        "đầu bếp", "nghệ nhân", "người", "chủ", "bà", "ông", "anh", "chị",
        "dau bep", "nghe nhan", "nguoi", "chu",
    ],
    "dish": [
        "món", "ẩm thực", "đặc sản", "nấu", "chế biến", "bánh", "bún",
        "mon", "am thuc", "dac san", "nau", "che bien", "banh", "bun",
    ],
    "attraction": [
        "nhà hàng", "quán", "homestay", "du lịch", "điểm", "nơi", "chỗ",
        "nha hang", "quan", "du lich", "diem", "noi", "cho",
    ],
    "product": [
        "sản phẩm", "trái cây", "hàng", "ocop",
        "san pham", "trai cay", "hang",
    ],
    "experience": [
        "trải nghiệm", "tour", "tham quan", "hoạt động",
        "trai nghiem", "tham quan", "hoat dong",
    ],
    "craft_village": [
        "làng nghề", "nghề", "thủ công",
        "lang nghe", "nghe", "thu cong",
    ],
}


def _concept_entities(concept_type: str, matched_kw: list[str]) -> list[str]:
    """Tìm entity ids đại diện cho 1 concept: theo type + keyword search (khử trùng)."""
    # Find entities of this type
    entities = knowledge.search_entities(entity_type=concept_type, limit=10)
    # Also try keyword search
    for kw in matched_kw[:2]:
        kw_results = knowledge.search_entities(q=kw, limit=5)
        for r in kw_results:
            if r["id"] not in {e["id"] for e in entities}:
                entities.append(r)

    return [e["id"] for e in entities[:8]]


def _detect_concepts_by_keyword(q_lower: str, q_norm: str) -> list[dict]:
    """Dò concept theo keyword map — trả list {keyword,type,entities}."""
    detected_concepts: list[dict] = []
    for concept_type, keywords in _CONCEPT_KEYWORDS.items():
        matched_kw = [kw for kw in keywords if kw in q_lower or kw in q_norm]
        if matched_kw:
            detected_concepts.append({
                "keyword": matched_kw[0],
                "type": concept_type,
                "entities": _concept_entities(concept_type, matched_kw),
            })
    return detected_concepts


def _add_named_entity_concepts(query: str, detected_concepts: list[dict]) -> None:
    """Bổ sung concept từ entity gọi thẳng tên trong query (nếu chưa có)."""
    named_entities = _detect_entities(query)
    for neid in named_entities:
        ent = knowledge.get_entity(neid)
        if ent:
            already = any(neid in c["entities"] for c in detected_concepts)
            if not already:
                detected_concepts.append({
                    "keyword": ent["name"],
                    "type": ent["type"],
                    "entities": [neid],
                })


def _readable_path(p: list[tuple[str, str]]) -> list[str]:
    """Chuyển 1 path (entity_id,label) thành chuỗi readable resolve tên entity."""
    path_readable = []
    for entity_id, label in p:
        ent = knowledge.get_entity(entity_id)
        ent_name = ent["name"] if ent else entity_id
        if label and label != "start":
            path_readable.append(f"—{label}→ {ent_name}")
        else:
            path_readable.append(ent_name)
    return path_readable


def _connect_pair(c_from: dict, c_to: dict, max_hops: int, connections: list[dict]) -> None:
    """Tìm connections giữa 2 concept, append vào `connections` chung.

    GIỮ NGUYÊN semantics gốc: guard `if connections:` đọc list TÍCH LŨY toàn cục —
    nên một khi đã có bất kỳ connection nào (từ cặp trước), vòng lặp cặp này
    short-circuit sau find_paths đầu tiên. Không đổi thứ tự tác dụng phụ.
    """
    for eid_a in c_from["entities"][:3]:
        for eid_b in c_to["entities"][:3]:
            paths = find_paths(eid_a, eid_b, max_hops=max_hops)
            for p in paths[:2]:
                connections.append({
                    "from": eid_a,
                    "to": eid_b,
                    "path": _readable_path(p),
                    "from_type": c_from["type"],
                    "to_type": c_to["type"],
                })
            if connections:
                break
        if connections:
            break


def _find_concept_connections(detected_concepts: list[dict], max_hops: int) -> list[dict]:
    """Duyệt mọi cặp concept, gom connections (accumulator chung như logic gốc)."""
    connections: list[dict] = []
    if len(detected_concepts) >= 2:
        for i in range(len(detected_concepts)):
            for j in range(i + 1, len(detected_concepts)):
                _connect_pair(detected_concepts[i], detected_concepts[j], max_hops, connections)
    return connections


def _build_cross_domain_context(detected_concepts: list[dict], connections: list[dict]) -> str:
    """Dựng context string cho cross_domain_query từ concepts + connections."""
    ctx_parts = []
    if detected_concepts:
        concept_summary = ", ".join(
            f"{c['type']}({c['keyword']})" for c in detected_concepts
        )
        ctx_parts.append(f"[Cross-domain]: Concepts detected: {concept_summary}")

    if connections:
        ctx_parts.append("Connecting paths:")
        for conn in connections[:5]:
            ctx_parts.append(f"  • {' '.join(conn['path'])}")

    return "\n".join(ctx_parts)


def cross_domain_query(query: str, max_hops: int = 3) -> dict:
    """
    Cross-domain reasoning: parse query để tìm nhiều concepts,
    tìm entities khớp mỗi concept, rồi dùng graph traversal
    để tìm connecting paths giữa chúng.

    Ví dụ: "đầu bếp nấu món gì ở nhà hàng nào"
           → person + dish + attraction

    Returns: {
        "concepts": [{"keyword": str, "type": str, "entities": [str]}],
        "connections": [{"from": str, "to": str, "path": [...]}],
        "context": str,
    }
    """
    knowledge._ensure()

    # ── Parse query to identify concept types ──
    q_lower = query.lower()
    q_norm = _normalize(q_lower)

    detected_concepts = _detect_concepts_by_keyword(q_lower, q_norm)

    # Also detect specific entities mentioned by name in the query
    _add_named_entity_concepts(query, detected_concepts)

    # ── Find connecting paths between concepts ──
    connections = _find_concept_connections(detected_concepts, max_hops)

    # ── Build context string ──
    return {
        "concepts": detected_concepts,
        "connections": connections,
        "context": _build_cross_domain_context(detected_concepts, connections),
    }


# ══════════════════════════════════════════════════
#  UNIFIED RAG PIPELINE
# ══════════════════════════════════════════════════

def build_rag_context(query: str, session_context: str = "") -> str:
    """
    Unified Agentic RAG pipeline.
    Gọi 1 lần, trả về toàn bộ context bổ sung cho LLM.

    Bao gồm:
      - Query classification + routing
      - Graph context nếu entity được detect
      - Cross-domain reasoning cho complex queries
      - Proactive suggestions
    """
    classification = classify_query(query)
    parts = []

    # 1. Query routing
    routing = get_routing_prompt(classification)
    parts.append(routing)

    # 2. Graph context for detected entities
    for eid in classification["entities_detected"][:2]:
        gc = graph_context_prompt(eid)
        if gc:
            parts.append(gc)

    # 3. Cross-domain reasoning for complex / multi-hop queries
    if classification["complexity"] in ("complex", "moderate"):
        cdq = cross_domain_query(query, max_hops=3)
        if cdq["context"]:
            parts.append(cdq["context"])
        # Enrich with cross-domain paths for connections found
        if cdq["connections"]:
            path_lines = ["[Cross-domain paths]:"]
            for conn in cdq["connections"][:3]:
                path_lines.append(f"  {' '.join(conn['path'])}")
            parts.append("\n".join(path_lines))

    # 4. Session context
    if session_context:
        parts.append(session_context)

    return "\n\n".join(parts)


# ══════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════

def _normalize(text: str) -> str:
    s = unicodedata.normalize("NFD", text.lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    return s.replace("đ", "d")


def _detect_entities(query: str) -> list[str]:
    """Phát hiện entity IDs có thể có trong query."""
    knowledge._ensure()

    detected = []
    q_lower = query.lower()
    q_norm = _normalize(query)

    for eid, e in knowledge._entities.items():
        if e["type"] == "place":
            continue
        name_lower = e["name"].lower()
        name_norm = _normalize(e["name"])

        # Exact or near-exact match
        if name_lower in q_lower or name_norm in q_norm:
            detected.append(eid)
            if len(detected) >= 5:
                break

    return detected


def _detect_areas(query: str) -> list[str]:
    """Phát hiện areas trong query (có dấu + không dấu)."""
    q = query.lower()
    q_norm = _normalize(q)
    areas = []
    if "vĩnh long" in q or "vinh long" in q_norm:
        areas.append("vinh-long")
    if "bến tre" in q or "ben tre" in q_norm:
        areas.append("ben-tre")
    if "trà vinh" in q or "tra vinh" in q_norm:
        areas.append("tra-vinh")
    return areas


# Intent rules: (intent, có-dấu keywords, không-dấu keywords).
# Thứ tự PHẢI giữ nguyên — trả về intent đầu tiên khớp (như chuỗi if cũ).
_INTENT_RULES: list[tuple[str, list[str], list[str]]] = [
    ("comparison",
     ["so sánh", "khác nhau", "hay hơn", "nên chọn"],
     ["so sanh", "khac nhau", "hay hon", "nen chon"]),
    ("itinerary",
     ["lịch trình", "đi đâu", "kế hoạch", "mấy ngày", "plan"],
     ["lich trinh", "di dau", "ke hoach", "may ngay"]),
    ("multi_hop",
     ["gần", "quanh đây", "xung quanh", "kế bên"],
     ["gan", "quanh day", "xung quanh", "ke ben"]),
    ("entity_detail",
     ["là gì", "chi tiết", "thông tin"],
     ["la gi", "chi tiet", "thong tin"]),
    ("simple_fact",
     ["mấy", "bao nhiêu", "khi nào", "ở đâu"],
     ["may", "bao nhieu", "khi nao", "o dau"]),
    ("open_ended",
     ["tại sao", "vì sao", "như thế nào", "giải thích"],
     ["tai sao", "vi sao", "nhu the nao", "giai thich"]),
]


def _match_kw(q: str, q_norm: str, kw: list[str], kw_norm: list[str]) -> bool:
    """True nếu q chứa 1 keyword có-dấu HOẶC q_norm chứa 1 keyword không-dấu."""
    return any(w in q for w in kw) or any(w in q_norm for w in kw_norm)


def _detect_intent(query: str) -> str:
    """Phát hiện intent từ query (hỗ trợ cả có dấu và không dấu)."""
    q = query.lower()
    q_norm = _normalize(q)

    # Check cả có dấu và không dấu — trả về intent đầu tiên khớp
    for intent, kw, kw_norm in _INTENT_RULES:
        if _match_kw(q, q_norm, kw, kw_norm):
            return intent

    return "search"


def _is_seasonal_query(query: str) -> bool:
    q = query.lower()
    q_norm = _normalize(q)
    return any(w in q for w in [
        "mùa", "tháng", "bây giờ", "hiện tại", "hôm nay",
        "nên đi", "thời điểm", "khi nào",
    ]) or any(w in q_norm for w in [
        "mua", "thang", "bay gio", "hien tai", "hom nay",
        "nen di", "thoi diem", "khi nao",
    ])
