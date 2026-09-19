# -*- coding: utf-8 -*-
"""Remediate Phase 11: Connect amenity-isolated attractions and cleanup graph topology."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
REGISTER_PATH = Path("outputs/factual_errors_register.json")
LOG_PATH = Path("outputs/remediation_phase11_log.json")
MAX_DIST_KM = 15.0

def _add_amenity_links(amenities: list, entities: dict, existing: set, new_edges: list) -> None:
    for a in amenities:
        eid = a.get("current_value", {}).get("entity_id")
        if eid not in entities:
            continue
        cv = a.get("correct_value", {})
        food_links = cv.get("recommended_food_links", [])
        lodging_links = cv.get("recommended_lodging_links", [])
        _link_group(eid, food_links[:2], entities, existing, new_edges)
        _link_group(eid, lodging_links[:2], entities, existing, new_edges)

def _link_group(eid: str, candidates: list, entities: dict, existing: set, new_edges: list) -> None:
    for item in candidates:
        tid = item.get("id")
        dist = item.get("distance_km", 0)
        if tid in entities and dist <= MAX_DIST_KM:
            if (eid, tid, "near") not in existing:
                new_edges.append({"from": eid, "to": tid, "type": "near"})
                existing.add((eid, tid, "near"))
            if (tid, eid, "near") not in existing:
                new_edges.append({"from": tid, "to": eid, "type": "near"})
                existing.add((tid, eid, "near"))

EXPIRED_OCOP_IDS = [
    "nuoc-mam-ruoi-long-vinh", "cu-cai-muoi-chit-sa", "gao-huu-co-long-hoa-hoa-minh-ocop-4-sao",
    "lap-xuong-ngoc-huong", "ruou-quach-cau-ngang", "san-pham-ocop-cau-ngang",
    "nem-chua-sau-xe", "keo-dau-phong-du-tan-loi", "vung-trong-cam-sapota-huu-thanh",
    "hop-tac-xa-cam-phuong-thuy", "thanh-long-vang-thanh-duc-ocop-3-sao",
    "buoi-da-xanh-cho-lach", "keo-dua-sap-vicosap", "mam-tep-du-du-thuy-nguyen",
    "banh-phong-mi-giong-trom"
]

def _heal_entity_metadata(entities: dict) -> list:
    updates = []
    om = entities.get("chua-ong-met-botum-vong-sa-som-rong")
    if om:
        om.setdefault("attributes", {})["architecture_style"] = "Kiến trúc Phật giáo Nam tông Khmer cổ truyền"
        updates.append("chua-ong-met-botum-vong-sa-som-rong:architecture_style")

    bx = entities.get("ben-xe-mien-tay-hcm")
    if bx:
        bx.setdefault("attributes", {})["external_gateway"] = True
        updates.append("ben-xe-mien-tay-hcm:external_gateway")

    for eid in EXPIRED_OCOP_IDS:
        ent = entities.get(eid)
        if ent:
            ent.setdefault("attributes", {})["recognition_status"] = "EXPIRED"
            updates.append(f"{eid}:recognition_status=EXPIRED")
    return updates

def remediate_phase11():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        reg = json.load(f)

    entities = {e["id"]: e for e in data.get("entities", [])}
    rels = data.get("relationships", [])

    # Filter self loops
    clean_rels = [r for r in rels if r.get("from") != r.get("to")]
    existing_edges = {(r.get("from"), r.get("to"), r.get("type")) for r in clean_rels}

    amenities = [e for e in reg if e.get("field") == "relationships.amenity_connectivity"]
    new_edges = []
    _add_amenity_links(amenities, entities, existing_edges, new_edges)

    clean_rels.extend(new_edges)
    data["relationships"] = clean_rels

    meta_updates = _heal_entity_metadata(entities)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    log_data = {
        "new_amenity_edges": len(new_edges),
        "total_relationships": len(clean_rels),
        "metadata_updates": meta_updates
    }
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"Phase 11 complete: Added {len(new_edges)} amenity edges. Total rels: {len(clean_rels)}.")

if __name__ == "__main__":
    remediate_phase11()
