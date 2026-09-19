# -*- coding: utf-8 -*-
"""Remediate Phase 4: Systemic normalization of 373 legacy district addresses to 2-tier administrative format."""
import json
from pathlib import Path

DATA_PATH = Path("web/data.json")
LEDGER_PATH = Path("outputs/data_remediation_ledger.json")

def _apply_address_remediation(ent: dict, proposed: str, rem: dict, changes: list) -> None:
    attrs = ent.setdefault("attributes", {})
    old_addr = attrs.get("address") or ent.get("address")
    attrs["address"] = proposed
    if "address" in ent:
        ent["address"] = proposed
    changes.append({
        "entity_id": rem["entity_id"],
        "field": "address",
        "old": old_addr,
        "new": proposed,
        "rule": rem.get("rule", "RULE_2TIER_CANONICAL_ADDRESS_SYNTAX"),
        "reason": rem.get("rationale", "Remap from legacy district to canonical 2-tier format")
    })

def remediate_phase4():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    entity_map = {e["id"]: e for e in data.get("entities", [])}
    changes = []

    err_districts = [
        x for x in ledger.get("remediations", [])
        if x.get("category") == "Spatial"
        and x.get("error_code") == "ERR_OLD_ADMIN_DISTRICT"
        and x.get("field") == "address"
    ]

    for rem in err_districts:
        eid = rem["entity_id"]
        if eid in entity_map:
            _apply_address_remediation(entity_map[eid], rem["proposed_value"], rem, changes)

    log_path = Path("outputs/remediation_phase4_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    remediate_phase4()
