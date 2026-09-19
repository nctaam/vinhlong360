# -*- coding: utf-8 -*-
"""Remediate Phase 6: Systemic normalization of 491 legacy province/town addresses to 2-tier administrative format."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LEDGER_PATH = Path("outputs/data_remediation_ledger.json")

def _clean_address_text(proposed: str) -> str:
    # Remove remaining old administrative prefixes in specific descriptions
    res = proposed.replace("thị trấn Duyên Hải", "Duyên Hải")
    res = res.replace("thị trấn ", "")
    return res

def _apply_address_p2(ent: dict, proposed: str, rem: dict, changes: list) -> None:
    cleaned = _clean_address_text(proposed)
    attrs = ent.setdefault("attributes", {})
    old_addr = attrs.get("address") or ent.get("address")
    attrs["address"] = cleaned
    if "address" in ent:
        ent["address"] = cleaned
    changes.append({
        "entity_id": rem["entity_id"],
        "field": "address",
        "old": old_addr,
        "new": cleaned,
        "rule": rem.get("rule", "RULE_2TIER_CANONICAL_ADDRESS_SYNTAX"),
        "reason": rem.get("rationale", "Remap from legacy province/town to canonical 2-tier format")
    })

def remediate_phase6():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    entity_map = {e["id"]: e for e in data.get("entities", [])}
    changes = []

    old_prov_rems = [
        x for x in ledger.get("remediations", [])
        if x.get("category") == "Spatial"
        and x.get("error_code") == "ERR_OLD_PROVINCE_REF"
        and x.get("field") == "address"
    ]

    for rem in old_prov_rems:
        eid = rem["entity_id"]
        if eid in entity_map:
            _apply_address_p2(entity_map[eid], rem["proposed_value"], rem, changes)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    log_path = Path("outputs/remediation_phase6_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    remediate_phase6()
