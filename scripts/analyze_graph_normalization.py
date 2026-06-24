#!/usr/bin/env python3
"""
Phân tích sâu đồ thị quan hệ (relationship graph) trong web/data.json
để phát hiện vấn đề normalization, ngữ nghĩa, duplicate, connectivity.

Chạy: python scripts/analyze_graph_normalization.py
"""

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "web" / "data.json"


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = {e["id"]: e for e in data.get("entities", [])}
    relationships = data.get("relationships", [])
    return entities, relationships


def haversine_km(lat1, lon1, lat2, lon2):
    """Khoảng cách Haversine (km) giữa 2 tọa độ."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_coords(entity):
    """Trả về (lat, lon) hoặc None."""
    coords = entity.get("coordinates")
    if coords and len(coords) == 2:
        lat, lon = coords
        if lat and lon and lat != 0 and lon != 0:
            return (float(lat), float(lon))
    return None


# ═══════════════════════════════════════════════════════════
# PART 1: Relationship type inventory
# ═══════════════════════════════════════════════════════════
def part1_relationship_inventory(entities, relationships):
    print("=" * 80)
    print("PART 1: RELATIONSHIP TYPE INVENTORY")
    print("=" * 80)

    type_count = Counter()
    type_schema = defaultdict(lambda: Counter())  # type -> "from_type→to_type" -> count
    missing_entities = {"from": set(), "to": set()}

    for r in relationships:
        rtype = r["type"]
        type_count[rtype] += 1

        from_e = entities.get(r["from"])
        to_e = entities.get(r["to"])

        from_type = from_e["type"] if from_e else "MISSING"
        to_type = to_e["type"] if to_e else "MISSING"

        if not from_e:
            missing_entities["from"].add(r["from"])
        if not to_e:
            missing_entities["to"].add(r["to"])

        type_schema[rtype][f"{from_type} → {to_type}"] += 1

    print("\n--- Count by relationship type ---")
    for rtype, count in type_count.most_common():
        print(f"  {rtype:20s} {count:6d}")
    print(f"  {'TOTAL':20s} {sum(type_count.values()):6d}")

    print("\n--- Schema per relationship type (from_type → to_type) ---")
    for rtype, count in type_count.most_common():
        print(f"\n  [{rtype}] ({count} total)")
        for schema, cnt in type_schema[rtype].most_common():
            flag = ""
            # Flag unexpected combinations
            from_t, to_t = schema.split(" → ")
            if rtype == "associated_with" and from_t == to_t == "place":
                flag = "  ⚠ place→place associated"
            if "MISSING" in schema:
                flag = "  ⚠ MISSING ENTITY"
            print(f"    {schema:45s} {cnt:5d}{flag}")

    if missing_entities["from"] or missing_entities["to"]:
        all_missing = missing_entities["from"] | missing_entities["to"]
        print(f"\n--- ⚠ Missing entities referenced in relationships: {len(all_missing)} ---")
        for eid in sorted(all_missing)[:20]:
            side = []
            if eid in missing_entities["from"]:
                side.append("from")
            if eid in missing_entities["to"]:
                side.append("to")
            print(f"    {eid}  (appears as: {', '.join(side)})")
        if len(all_missing) > 20:
            print(f"    ... and {len(all_missing) - 20} more")


# ═══════════════════════════════════════════════════════════
# PART 2: Semantic validation of "associated_with"
# ═══════════════════════════════════════════════════════════
def part2_associated_validation(entities, relationships):
    print("\n" + "=" * 80)
    print("PART 2: SEMANTIC VALIDATION OF 'associated_with' RELATIONSHIPS")
    print("=" * 80)

    assoc_rels = [r for r in relationships if r["type"] == "associated_with"]
    print(f"\nTotal associated_with relationships: {len(assoc_rels)}")

    # Group by from_type → to_type
    groups = defaultdict(list)
    for r in assoc_rels:
        from_e = entities.get(r["from"])
        to_e = entities.get(r["to"])
        if not from_e or not to_e:
            continue
        key = f"{from_e['type']} → {to_e['type']}"
        groups[key].append((from_e, to_e))

    print("\n--- Groups by from_type → to_type ---")
    for key in sorted(groups.keys(), key=lambda k: -len(groups[k])):
        items = groups[key]
        print(f"\n  [{key}] — {len(items)} relationships")
        # Show up to 10 samples
        for from_e, to_e in items[:10]:
            print(f"    {from_e['name'][:40]:40s} → {to_e['name'][:40]}")
        if len(items) > 10:
            print(f"    ... ({len(items) - 10} more)")

    # Flag nonsemantic patterns
    print("\n--- ⚠ Nonsemantic pattern flags ---")
    flagged_patterns = {
        "dish → craft_village": "Likely auto-generated. Check if dish matches village product.",
        "craft_village → dish": "Likely auto-generated. Check if dish matches village product.",
        "person → accommodation": "Historical figure linked to modern hotel?",
        "accommodation → person": "Hotel linked to historical figure?",
        "person → dish": "Historical person linked to food?",
        "dish → person": "Food linked to historical person?",
        "accommodation → dish": "Hotel linked to food?",
        "dish → accommodation": "Food linked to hotel?",
        "person → economy": "Historical person linked to economy entity?",
        "person → facility": "Historical person linked to modern facility?",
    }

    any_flagged = False
    for pattern, reason in flagged_patterns.items():
        if pattern in groups:
            any_flagged = True
            items = groups[pattern]
            print(f"\n  ⚠ {pattern} ({len(items)} rels) — {reason}")
            for from_e, to_e in items[:5]:
                print(f"    {from_e['name'][:40]:40s} → {to_e['name'][:40]}")

    if not any_flagged:
        print("  No obviously nonsemantic patterns found.")


# ═══════════════════════════════════════════════════════════
# PART 3: "near" relationship quality
# ═══════════════════════════════════════════════════════════
def part3_near_quality(entities, relationships):
    print("\n" + "=" * 80)
    print("PART 3: 'near' RELATIONSHIP QUALITY (POST-CLEANUP)")
    print("=" * 80)

    near_rels = [r for r in relationships if r["type"] == "near"]
    print(f"\nTotal 'near' relationships: {len(near_rels)}")

    # Check entity types in near rels
    near_type_combos = Counter()
    for r in near_rels:
        from_e = entities.get(r["from"])
        to_e = entities.get(r["to"])
        if from_e and to_e:
            key = f"{from_e['type']} → {to_e['type']}"
            near_type_combos[key] += 1

    print("\n--- Entity type combinations in 'near' rels ---")
    for combo, cnt in near_type_combos.most_common(20):
        print(f"  {combo:45s} {cnt:5d}")

    # Calculate distances
    distances = []
    no_coords = 0
    missing_entity = 0

    for r in near_rels:
        from_e = entities.get(r["from"])
        to_e = entities.get(r["to"])
        if not from_e or not to_e:
            missing_entity += 1
            continue
        c1 = get_coords(from_e)
        c2 = get_coords(to_e)
        if not c1 or not c2:
            no_coords += 1
            continue
        dist = haversine_km(c1[0], c1[1], c2[0], c2[1])
        distances.append((dist, r, from_e, to_e))

    print(f"\n--- Distance statistics ---")
    print(f"  Total near rels: {len(near_rels)}")
    print(f"  Missing entity: {missing_entity}")
    print(f"  No coordinates: {no_coords}")
    print(f"  With distance calculated: {len(distances)}")

    if distances:
        # Distribution
        bins = [
            (0, 1, "0–1 km"),
            (1, 2, "1–2 km"),
            (2, 5, "2–5 km"),
            (5, 10, "5–10 km"),
            (10, 15, "10–15 km"),
            (15, 25, "15–25 km"),
            (25, 50, "25–50 km"),
            (50, 100, "50–100 km"),
            (100, float("inf"), ">100 km"),
        ]

        print("\n--- Distance distribution ---")
        for lo, hi, label in bins:
            count = sum(1 for d, _, _, _ in distances if lo <= d < hi)
            bar = "█" * (count // 10) + ("▌" if count % 10 >= 5 else "")
            print(f"  {label:12s} {count:5d}  {bar}")

        # Average and median
        dvals = sorted(d for d, _, _, _ in distances)
        avg = sum(dvals) / len(dvals)
        median = dvals[len(dvals) // 2]
        print(f"\n  Average distance: {avg:.2f} km")
        print(f"  Median distance:  {median:.2f} km")
        print(f"  Min: {dvals[0]:.2f} km, Max: {dvals[-1]:.2f} km")

        # Flag > 15km
        flagged = [(d, r, fe, te) for d, r, fe, te in distances if d > 15]
        print(f"\n--- ⚠ Near relationships with distance > 15 km: {len(flagged)} ---")
        flagged.sort(key=lambda x: -x[0])
        for d, r, fe, te in flagged[:30]:
            from_area = fe.get("area", "?")
            to_area = te.get("area", "?")
            cross = " ⚠CROSS-AREA" if from_area != to_area else ""
            print(
                f"  {d:7.1f} km  {fe['type']:15s} {fe['name'][:30]:30s} ({from_area}) → "
                f"{te['type']:15s} {te['name'][:30]:30s} ({to_area}){cross}"
            )
        if len(flagged) > 30:
            print(f"  ... and {len(flagged) - 30} more")

        # Also flag person-near that might still exist
        person_near = [
            (d, r, fe, te) for d, r, fe, te in distances
            if fe.get("type") == "person" or te.get("type") == "person"
        ]
        if person_near:
            print(f"\n--- ⚠ Person in 'near' relationships: {len(person_near)} ---")
            for d, r, fe, te in person_near[:10]:
                print(
                    f"  {d:7.1f} km  {fe['type']:12s} {fe['name'][:35]:35s} → "
                    f"{te['type']:12s} {te['name'][:35]}"
                )


# ═══════════════════════════════════════════════════════════
# PART 4: Graph connectivity
# ═══════════════════════════════════════════════════════════
def part4_connectivity(entities, relationships):
    print("\n" + "=" * 80)
    print("PART 4: GRAPH CONNECTIVITY (excluding 'near')")
    print("=" * 80)

    # Build adjacency list (non-near only)
    adj = defaultdict(set)
    degree = Counter()
    non_near = [r for r in relationships if r["type"] != "near"]

    print(f"\nNon-near relationships: {len(non_near)}")

    for r in non_near:
        f, t = r["from"], r["to"]
        adj[f].add(t)
        adj[t].add(f)
        degree[f] += 1
        degree[t] += 1

    all_entity_ids = set(entities.keys())
    nodes_in_graph = set(adj.keys()) & all_entity_ids

    # Find connected components using BFS
    visited = set()
    components = []

    for node in all_entity_ids:
        if node in visited:
            continue
        if node not in adj:
            # Isolated node
            components.append({node})
            visited.add(node)
            continue
        # BFS
        queue = [node]
        component = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adj[current]:
                if neighbor not in visited and neighbor in all_entity_ids:
                    queue.append(neighbor)
        if component:
            components.append(component)

    components.sort(key=len, reverse=True)

    isolated = [c for c in components if len(c) == 1]
    non_isolated = [c for c in components if len(c) > 1]

    print(f"\n--- Component summary ---")
    print(f"  Total entities:          {len(all_entity_ids)}")
    print(f"  Entities in non-near graph: {len(nodes_in_graph)}")
    print(f"  Connected components:    {len(components)}")
    print(f"  Isolated (no non-near rels): {len(isolated)}")
    print(f"  Non-trivial components:  {len(non_isolated)}")
    print(f"  Largest component size:  {len(components[0]) if components else 0}")

    if len(non_isolated) > 1:
        print(f"\n--- Component sizes (top 20) ---")
        for i, c in enumerate(non_isolated[:20]):
            # Sample some names
            sample_names = []
            for eid in list(c)[:3]:
                e = entities.get(eid)
                if e:
                    sample_names.append(f"{e['type']}:{e['name'][:25]}")
            print(f"  Component {i + 1}: {len(c):5d} nodes  (e.g. {', '.join(sample_names)})")

    # Dead-ends (degree 1 in non-near graph)
    dead_ends = []
    for eid in all_entity_ids:
        if degree.get(eid, 0) == 1:
            e = entities.get(eid)
            dead_ends.append(e)

    print(f"\n--- Dead-ends (degree 1, only 1 non-near relationship): {len(dead_ends)} ---")
    # Group by type
    de_by_type = Counter(e["type"] for e in dead_ends if e)
    for t, c in de_by_type.most_common():
        print(f"  {t:20s} {c:5d}")

    # Show some samples
    print("\n  Sample dead-ends:")
    for e in dead_ends[:15]:
        if e:
            # Find the single relationship
            rel_desc = ""
            for r in non_near:
                if r["from"] == e["id"] or r["to"] == e["id"]:
                    other_id = r["to"] if r["from"] == e["id"] else r["from"]
                    other_e = entities.get(other_id)
                    other_name = other_e["name"][:25] if other_e else other_id[:25]
                    rel_desc = f"  --[{r['type']}]--> {other_name}"
                    break
            print(f"    {e['type']:15s} {e['name'][:35]:35s}{rel_desc}")

    # Isolated entity samples
    print(f"\n--- Isolated entity samples (no non-near rels): ---")
    iso_by_type = Counter()
    iso_samples = []
    for c in isolated:
        eid = list(c)[0]
        e = entities.get(eid)
        if e:
            iso_by_type[e["type"]] += 1
            if len(iso_samples) < 15:
                iso_samples.append(e)

    print("  By type:")
    for t, c in iso_by_type.most_common():
        print(f"    {t:20s} {c:5d}")
    print("\n  Samples:")
    for e in iso_samples:
        area = e.get("area", "?")
        print(f"    {e['type']:15s} {e['name'][:40]:40s} ({area})")

    # Bridge detection (simplified: for each node with degree > 1, check if removing it
    # increases component count in its local neighborhood)
    # Full bridge detection via Tarjan's algorithm
    print(f"\n--- Bridge nodes (articulation points) ---")

    # Build proper adjacency for Tarjan's
    graph_nodes = set()
    graph_adj = defaultdict(set)
    for r in non_near:
        f, t = r["from"], r["to"]
        if f in all_entity_ids and t in all_entity_ids:
            graph_nodes.add(f)
            graph_nodes.add(t)
            graph_adj[f].add(t)
            graph_adj[t].add(f)

    # Iterative Tarjan's articulation point algorithm
    disc = {}
    low = {}
    parent = {}
    ap = set()
    timer = [0]

    for start in graph_nodes:
        if start in disc:
            continue
        # Iterative DFS
        stack = [(start, iter(graph_adj[start]), False)]
        disc[start] = low[start] = timer[0]
        timer[0] += 1
        parent[start] = None
        children_count = defaultdict(int)

        while stack:
            node, neighbors, returning = stack[-1]

            if returning:
                stack.pop()
                # Update low for parent
                if stack:
                    parent_node = stack[-1][0]
                    low[parent_node] = min(low[parent_node], low[node])

                    # Check AP condition for non-root
                    if parent.get(parent_node) is not None:
                        if low[node] >= disc[parent_node]:
                            ap.add(parent_node)
                    # Root with 2+ children
                    if parent.get(parent_node) is None:
                        children_count[parent_node] += 1
                        if children_count[parent_node] > 1:
                            ap.add(parent_node)
                continue

            try:
                neighbor = next(neighbors)
                if neighbor not in disc:
                    disc[neighbor] = low[neighbor] = timer[0]
                    timer[0] += 1
                    parent[neighbor] = node
                    # Mark current as returning when we come back
                    stack[-1] = (node, neighbors, False)
                    stack.append((neighbor, iter(graph_adj[neighbor]), False))
                elif neighbor != parent.get(node):
                    low[node] = min(low[node], disc[neighbor])
            except StopIteration:
                # All neighbors visited, mark as returning
                stack[-1] = (node, neighbors, True)

    print(f"  Articulation points found: {len(ap)}")
    if ap:
        # Show top ones by degree
        ap_with_degree = [(eid, degree.get(eid, 0)) for eid in ap]
        ap_with_degree.sort(key=lambda x: -x[1])
        print(f"\n  Top articulation points by degree:")
        for eid, deg in ap_with_degree[:20]:
            e = entities.get(eid)
            name = e["name"][:40] if e else eid[:40]
            etype = e["type"] if e else "?"
            print(f"    {etype:15s} {name:40s} degree={deg}")


# ═══════════════════════════════════════════════════════════
# PART 5: Duplicate relationship detection
# ═══════════════════════════════════════════════════════════
def part5_duplicates(entities, relationships):
    print("\n" + "=" * 80)
    print("PART 5: DUPLICATE RELATIONSHIP DETECTION")
    print("=" * 80)

    # Exact duplicates (same from, to, type)
    seen = Counter()
    for r in relationships:
        key = (r["from"], r["to"], r["type"])
        seen[key] += 1

    exact_dupes = {k: v for k, v in seen.items() if v > 1}
    total_extra = sum(v - 1 for v in exact_dupes.values())

    print(f"\n--- Exact duplicates (same from, to, type) ---")
    print(f"  Unique duplicate tuples: {len(exact_dupes)}")
    print(f"  Total extra (removable): {total_extra}")

    if exact_dupes:
        print(f"\n  Examples:")
        for (f, t, rtype), count in sorted(exact_dupes.items(), key=lambda x: -x[1])[:20]:
            from_e = entities.get(f)
            to_e = entities.get(t)
            fn = from_e["name"][:30] if from_e else f[:30]
            tn = to_e["name"][:30] if to_e else t[:30]
            print(f"    [{rtype:18s}] {fn:30s} → {tn:30s}  x{count}")

    # Bidirectional pairs (A→B and B→A with same type)
    pair_set = set()
    for r in relationships:
        pair_set.add((r["from"], r["to"], r["type"]))

    bidirectional = []
    checked = set()
    for f, t, rtype in pair_set:
        key = tuple(sorted([f, t])) + (rtype,)
        if key in checked:
            continue
        checked.add(key)
        if (t, f, rtype) in pair_set:
            bidirectional.append((f, t, rtype))

    print(f"\n--- Bidirectional pairs (A→B AND B→A, same type) ---")
    print(f"  Total bidirectional pairs: {len(bidirectional)}")

    if bidirectional:
        # Group by type
        bi_by_type = Counter(rtype for _, _, rtype in bidirectional)
        print("\n  By type:")
        for rtype, cnt in bi_by_type.most_common():
            print(f"    {rtype:20s} {cnt:5d}")

        print(f"\n  Examples:")
        for f, t, rtype in bidirectional[:15]:
            from_e = entities.get(f)
            to_e = entities.get(t)
            fn = from_e["name"][:30] if from_e else f[:30]
            tn = to_e["name"][:30] if to_e else t[:30]
            print(f"    [{rtype:18s}] {fn:30s} ↔ {tn:30s}")

    print(f"\n--- Summary ---")
    print(f"  Total relationships:       {len(relationships)}")
    print(f"  Exact duplicates (extra):  {total_extra}")
    print(f"  Bidirectional pairs:       {len(bidirectional)}")
    print(f"  Potentially removable:     {total_extra + len(bidirectional)}")


# ═══════════════════════════════════════════════════════════
# PART 6: Relationship density analysis
# ═══════════════════════════════════════════════════════════
def part6_density(entities, relationships):
    print("\n" + "=" * 80)
    print("PART 6: RELATIONSHIP DENSITY ANALYSIS")
    print("=" * 80)

    non_near = [r for r in relationships if r["type"] != "near"]

    # Count rels per entity
    rel_count = Counter()
    for r in non_near:
        rel_count[r["from"]] += 1
        rel_count[r["to"]] += 1

    print(f"\n--- Top 30 entities by relationship count (non-near) ---")
    for eid, cnt in rel_count.most_common(30):
        e = entities.get(eid)
        if e:
            name = e["name"][:40]
            etype = e["type"]
            area = e.get("area", "?")
        else:
            name = eid[:40]
            etype = "MISSING"
            area = "?"
        print(f"  {cnt:4d} rels  {etype:15s} {name:40s} ({area})")

    # Histogram
    print(f"\n--- Histogram: non-near relationship count per entity ---")
    all_counts = []
    for eid in entities:
        all_counts.append(rel_count.get(eid, 0))

    max_count = max(all_counts) if all_counts else 0

    hist_bins = [
        (0, 0, "0 (isolated)"),
        (1, 1, "1 (dead-end)"),
        (2, 2, "2"),
        (3, 3, "3"),
        (4, 5, "4–5"),
        (6, 10, "6–10"),
        (11, 20, "11–20"),
        (21, 50, "21–50"),
        (51, 100, "51–100"),
        (101, max_count + 1, "101+"),
    ]

    for lo, hi, label in hist_bins:
        count = sum(1 for c in all_counts if lo <= c <= hi)
        bar = "█" * (count // 5) + ("▌" if count % 5 >= 3 else "")
        pct = 100 * count / len(all_counts) if all_counts else 0
        print(f"  {label:15s} {count:5d} ({pct:5.1f}%)  {bar}")

    print(f"\n  Total entities: {len(all_counts)}")
    print(f"  Average rels/entity: {sum(all_counts) / len(all_counts):.1f}")
    print(f"  Median rels/entity: {sorted(all_counts)[len(all_counts) // 2]}")
    print(f"  Max rels/entity: {max_count}")

    # Identify "hubs" — entities with disproportionate connections
    threshold = 20
    hubs = [(eid, cnt) for eid, cnt in rel_count.items() if cnt >= threshold]
    hubs.sort(key=lambda x: -x[1])

    print(f"\n--- Relationship 'hubs' (>= {threshold} non-near rels): {len(hubs)} ---")
    for eid, cnt in hubs:
        e = entities.get(eid)
        if e:
            # Show breakdown by rel type
            type_breakdown = Counter()
            for r in non_near:
                if r["from"] == eid or r["to"] == eid:
                    type_breakdown[r["type"]] += 1
            breakdown_str = ", ".join(f"{t}:{c}" for t, c in type_breakdown.most_common())
            print(
                f"  {cnt:4d}  {e['type']:15s} {e['name'][:35]:35s}  [{breakdown_str}]"
            )

    # Also check near relationship density
    print(f"\n--- Top 20 entities by 'near' relationship count ---")
    near_count = Counter()
    for r in relationships:
        if r["type"] == "near":
            near_count[r["from"]] += 1
            near_count[r["to"]] += 1

    for eid, cnt in near_count.most_common(20):
        e = entities.get(eid)
        name = e["name"][:40] if e else eid[:40]
        etype = e["type"] if e else "?"
        print(f"  {cnt:4d} near  {etype:15s} {name}")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("Loading data from", DATA_PATH)
    entities, relationships = load_data()
    print(f"Loaded {len(entities)} entities, {len(relationships)} relationships\n")

    part1_relationship_inventory(entities, relationships)
    part2_associated_validation(entities, relationships)
    part3_near_quality(entities, relationships)
    part4_connectivity(entities, relationships)
    part5_duplicates(entities, relationships)
    part6_density(entities, relationships)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
