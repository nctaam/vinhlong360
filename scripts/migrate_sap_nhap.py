#!/usr/bin/env python3
"""Migrate sáp nhập: upgrade 16 xã → phường across 3 provinces.

Changes:
1. Rename xa-* entities to p-* (id, name prefix, level)
2. Reassign children (placeId) and relationships from xa-* to p-*
3. Create p-vung-liem (no existing xa-vung-liem)
4. Update data.json to match

Run backup_data.py BEFORE this script!
"""
import json, sqlite3, sys, shutil
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "agent" / "data" / "vinhlong360.db"
JSON_PATH = PROJECT / "web" / "data.json"

UPGRADES = {
    "vinh-long": ["long-ho", "tam-binh", "tan-quoi", "tra-on", "vung-liem"],
    "ben-tre": ["ba-tri", "binh-dai", "mo-cay", "phu-tuc", "tien-thuy", "tan-thuy"],
    "tra-vinh": ["cang-long", "hung-hoa", "tan-hoa", "tieu-can", "tap-ngai"],
}

# Parent districts for each upgraded phuong
PARENT_IDS = {
    "long-ho": "huyen-long-ho-vinh-long",
    "tam-binh": "huyen-tam-binh-vinh-long",
    "tan-quoi": "huyen-binh-minh-vinh-long",
    "tra-on": "huyen-tra-on-vinh-long",
    "vung-liem": "huyen-vung-liem-vinh-long",
    "ba-tri": "huyen-ba-tri-ben-tre",
    "binh-dai": "huyen-binh-dai-ben-tre",
    "mo-cay": "huyen-mo-cay-ben-tre",
    "phu-tuc": "huyen-chau-thanh-ben-tre",
    "tien-thuy": "huyen-chau-thanh-ben-tre",
    "tan-thuy": "huyen-ba-tri-ben-tre",
    "cang-long": "huyen-cang-long-tra-vinh",
    "hung-hoa": "huyen-tieu-can-tra-vinh",
    "tan-hoa": "huyen-tieu-can-tra-vinh",
    "tieu-can": "huyen-tieu-can-tra-vinh",
    "tap-ngai": "huyen-duyen-hai-tra-vinh",
}


def migrate_db():
    """Migrate SQLite DB."""
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    stats = {"renamed": 0, "children_moved": 0, "rels_moved": 0, "created": 0, "skipped": 0}

    for area, slugs in UPGRADES.items():
        for slug in slugs:
            xa_id = f"xa-{slug}"
            p_id = f"p-{slug}"

            xa_row = db.execute("SELECT * FROM entities WHERE id=?", (xa_id,)).fetchone()

            if xa_row:
                # Entity exists as xa-*, need to rename
                cols = [desc[1] for desc in db.execute("PRAGMA table_info(entities)").fetchall()]
                vals = {col: xa_row[col] for col in cols}

                # Delete old entry
                db.execute("DELETE FROM entities WHERE id=?", (xa_id,))

                # Insert new entry with updated id, name, level
                old_name = vals["name"]
                new_name = old_name.replace("Xã ", "Phường ", 1)
                vals["id"] = p_id
                vals["name"] = new_name
                vals["level"] = "phuong"
                vals["updatedAt"] = datetime.utcnow().isoformat() + "Z"

                placeholders = ", ".join(["?" for _ in cols])
                col_names = ", ".join(cols)
                db.execute(
                    f"INSERT INTO entities ({col_names}) VALUES ({placeholders})",
                    [vals[c] for c in cols],
                )
                print(f"  RENAMED: {xa_id} -> {p_id} ({old_name} -> {new_name})")
                stats["renamed"] += 1

                # Update children
                children = db.execute(
                    "UPDATE entities SET placeId=? WHERE placeId=?", (p_id, xa_id)
                ).rowcount
                if children:
                    print(f"    Children reassigned: {children}")
                    stats["children_moved"] += children

                # Update relationships
                r1 = db.execute(
                    "UPDATE relationships SET from_id=? WHERE from_id=?", (p_id, xa_id)
                ).rowcount
                r2 = db.execute(
                    "UPDATE relationships SET to_id=? WHERE to_id=?", (p_id, xa_id)
                ).rowcount
                if r1 + r2:
                    print(f"    Relationships updated: {r1 + r2}")
                    stats["rels_moved"] += r1 + r2

            elif not db.execute("SELECT id FROM entities WHERE id=?", (p_id,)).fetchone():
                # Neither xa-* nor p-* exists — create new phường entry
                parent_id = PARENT_IDS.get(slug)
                # Find area from UPGRADES
                phuong_name = slug.replace("-", " ").title()
                # Fix Vietnamese capitalization
                name_map = {
                    "vung-liem": "Vũng Liêm",
                    "long-ho": "Long Hồ",
                    "tam-binh": "Tam Bình",
                    "tan-quoi": "Tân Quới",
                    "tra-on": "Trà Ôn",
                    "ba-tri": "Ba Tri",
                    "binh-dai": "Bình Đại",
                    "mo-cay": "Mỏ Cày",
                    "phu-tuc": "Phú Túc",
                    "tien-thuy": "Tiên Thủy",
                    "tan-thuy": "Tân Thủy",
                    "cang-long": "Càng Long",
                    "hung-hoa": "Hùng Hòa",
                    "tan-hoa": "Tân Hòa",
                    "tieu-can": "Tiểu Cần",
                    "tap-ngai": "Tập Ngãi",
                }
                proper_name = name_map.get(slug, phuong_name)
                full_name = f"Phường {proper_name}"

                db.execute(
                    "INSERT INTO entities (id, type, name, level, area, parentId, confidence, updatedAt, created_at) "
                    "VALUES (?, 'place', ?, 'phuong', ?, ?, 0.9, ?, ?)",
                    (p_id, full_name, area, parent_id,
                     datetime.utcnow().isoformat() + "Z",
                     datetime.utcnow().isoformat() + "Z"),
                )
                print(f"  CREATED: {p_id} ({full_name}) parent={parent_id}")
                stats["created"] += 1
            else:
                print(f"  SKIPPED: {slug} (p-* already exists)")
                stats["skipped"] += 1

    db.commit()
    db.close()
    return stats


def migrate_json():
    """Update data.json to match DB changes."""
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    entities = data["entities"]
    rels = data["relationships"]
    by_id = {e["id"]: i for i, e in enumerate(entities)}

    stats = {"renamed": 0, "children_moved": 0, "rels_moved": 0, "created": 0}

    for area, slugs in UPGRADES.items():
        for slug in slugs:
            xa_id = f"xa-{slug}"
            p_id = f"p-{slug}"

            idx = by_id.get(xa_id)
            if idx is not None:
                e = entities[idx]
                old_name = e["name"]
                e["id"] = p_id
                e["name"] = old_name.replace("Xã ", "Phường ", 1)
                e["level"] = "phuong"
                stats["renamed"] += 1

                # Update children
                for other in entities:
                    if other.get("placeId") == xa_id:
                        other["placeId"] = p_id
                        stats["children_moved"] += 1

                # Update relationships
                for r in rels:
                    if r.get("from_id") == xa_id:
                        r["from_id"] = p_id
                        stats["rels_moved"] += 1
                    if r.get("to_id") == xa_id:
                        r["to_id"] = p_id
                        stats["rels_moved"] += 1
            elif p_id not in by_id:
                # Create new entry
                name_map = {
                    "vung-liem": "Vũng Liêm",
                }
                proper_name = name_map.get(slug, slug.replace("-", " ").title())
                entities.append({
                    "id": p_id,
                    "type": "place",
                    "name": f"Phường {proper_name}",
                    "level": "phuong",
                    "area": area,
                    "parentId": PARENT_IDS.get(slug),
                    "confidence": 0.9,
                })
                stats["created"] += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return stats


def verify():
    """Verify migration results."""
    db = sqlite3.connect(str(DB_PATH))

    total_phuong = db.execute("SELECT count(*) FROM entities WHERE level='phuong'").fetchone()[0]
    total_xa = db.execute("SELECT count(*) FROM entities WHERE level='xa'").fetchone()[0]

    # Check all 16 exist
    missing = []
    for area, slugs in UPGRADES.items():
        for slug in slugs:
            p_id = f"p-{slug}"
            row = db.execute("SELECT id, name, level FROM entities WHERE id=?", (p_id,)).fetchone()
            if not row:
                missing.append(p_id)
            elif row[2] != "phuong":
                missing.append(f"{p_id} (level={row[2]})")

    # Check no old xa-* remain
    old_remaining = []
    for area, slugs in UPGRADES.items():
        for slug in slugs:
            xa_id = f"xa-{slug}"
            if db.execute("SELECT id FROM entities WHERE id=?", (xa_id,)).fetchone():
                old_remaining.append(xa_id)

    # Orphaned children check
    orphaned = db.execute(
        "SELECT count(*) FROM entities WHERE placeId LIKE 'xa-%' AND placeId IN (" +
        ",".join(f"'xa-{s}'" for slugs in UPGRADES.values() for s in slugs) + ")"
    ).fetchone()[0]

    db.close()

    print(f"\n=== VERIFICATION ===")
    print(f"  Total phường: {total_phuong}")
    print(f"  Total xã: {total_xa}")
    print(f"  Missing new phường: {missing or 'NONE'}")
    print(f"  Old xã still present: {old_remaining or 'NONE'}")
    print(f"  Orphaned children: {orphaned}")

    return len(missing) == 0 and len(old_remaining) == 0 and orphaned == 0


if __name__ == "__main__":
    print("=== Migrating SQLite DB ===")
    db_stats = migrate_db()
    print(f"\nDB stats: {db_stats}")

    print("\n=== Migrating data.json ===")
    json_stats = migrate_json()
    print(f"\nJSON stats: {json_stats}")

    ok = verify()
    print(f"\nMigration {'PASSED' if ok else 'FAILED'}")
    sys.exit(0 if ok else 1)
