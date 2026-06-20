"""U1.3 — Assign placeId to entities missing it by matching coordinates to nearest ward.

Uses haversine distance to find the nearest ward/commune entity.
Run backup_data.py BEFORE this script (B1).
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_coords(entity):
    c = entity.get("coordinates")
    if not c:
        return None
    if isinstance(c, dict):
        lat, lon = c.get("lat"), c.get("lng") or c.get("lon")
    elif isinstance(c, list) and len(c) >= 2:
        lat, lon = c[0], c[1]
    else:
        return None
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def main():
    from agent.database import Database
    db = Database()
    db.initialize()
    entities = db.all_entities()

    wards = [e for e in entities if e.get("type") == "place" and e.get("level") in ("xa", "phuong")]
    ward_coords = []
    for w in wards:
        c = get_coords(w)
        if c:
            ward_coords.append((w["id"], w["name"], c[0], c[1]))

    print(f"Wards with coords: {len(ward_coords)}")

    fixable = [e for e in entities if not e.get("placeId") and get_coords(e)]
    print(f"Entities to fix: {len(fixable)}")

    updated = 0
    max_dist_km = 15  # max distance to assign (prevent wildly wrong matches)

    for e in fixable:
        ec = get_coords(e)
        if not ec:
            continue
        best_id, best_name, best_dist = None, None, float('inf')
        for wid, wname, wlat, wlon in ward_coords:
            d = haversine(ec[0], ec[1], wlat, wlon)
            if d < best_dist:
                best_dist = d
                best_id = wid
                best_name = wname

        if best_dist <= max_dist_km:
            e["placeId"] = best_id
            db.upsert_entity(e)
            updated += 1
            print(f"  [{e['id']}] {e['name']} -> {best_name} ({best_dist:.1f}km)")
        else:
            print(f"  SKIP [{e['id']}] {e['name']} (nearest: {best_name} {best_dist:.1f}km > {max_dist_km}km)")

    print(f"\nAssigned placeId to {updated} entities")

    # Export data.json
    print("Exporting data.json...")
    entities = db.all_entities()
    relationships = db.all_relationships()
    itineraries = db.all_itineraries()
    data = {"entities": entities, "relationships": relationships, "itineraries": itineraries}
    with open("web/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(entities)} entities")


if __name__ == "__main__":
    main()
