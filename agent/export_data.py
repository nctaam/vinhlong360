"""
vinhlong360 — Export DB data to JSON files.

Exports entities, relationships, and itineraries from the database to:
  1. web/data.js     — frontend static fallback (window.VL_DATA)
  2. web/data.json    — used by Knowledge Agent
  3. web-astro/src/data/data.json — Astro SSG build source

Usage:
  python agent/export_data.py              # Export to all locations
  python agent/export_data.py --web-only   # Export only to web/
  python agent/export_data.py --astro-only # Export only to Astro
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import db


def export_from_db() -> dict:
    db.initialize()
    all_entities = db.list_entities(limit=10000)

    with db._conn() as conn:
        place_rows = db._fetchall(conn, "SELECT * FROM entities WHERE type = 'place'")
        rel_rows = db._fetchall(conn, "SELECT from_id, to_id, type FROM relationships")
        itin_rows = db._fetchall(conn, "SELECT * FROM itineraries")

    places = [db._parse_entity(r) for r in place_rows]
    entities = all_entities + places

    relationships = []
    for r in rel_rows:
        d = db._row_to_dict(r)
        relationships.append({"from": d["from_id"], "to": d["to_id"], "type": d["type"]})

    itineraries = [db._parse_itinerary(r) for r in itin_rows]

    return {
        "entities": entities,
        "relationships": relationships,
        "itineraries": itineraries,
    }


def write_data_js(data: dict, path: Path):
    """Write as JS file with window.VL_DATA."""
    places = json.dumps([e for e in data["entities"] if e.get("type") == "place"],
                        ensure_ascii=False, indent=2)
    items = json.dumps([e for e in data["entities"] if e.get("type") != "place"],
                       ensure_ascii=False, indent=2)
    rels = json.dumps(data["relationships"], ensure_ascii=False, indent=2)
    itins = json.dumps(data["itineraries"], ensure_ascii=False, indent=2)

    js = (
        "(function () {\n"
        f"var places = {places};\n"
        f"var items = {items};\n"
        f"var relationships = {rels};\n"
        f"var itineraries = {itins};\n"
        "window.VL_DATA = {\n"
        "  entities: places.concat(items),\n"
        "  relationships: relationships,\n"
        "  itineraries: itineraries,\n"
        "  ALL_MONTHS: [1,2,3,4,5,6,7,8,9,10,11,12]\n"
        "};\n"
        "})();\n"
    )
    _atomic_write(path, js)
    print(f"  data.js  -> {path}")


def _atomic_write(path: Path, text: str):
    """GĐ-audit: ghi atomic (temp + replace) — crash giữa chừng không làm hỏng file đích."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".export.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_json(data: dict, path: Path):
    """Write as plain JSON (atomic)."""
    _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
    print(f"  data.json -> {path}")


def main():
    # GĐ7: export DB -> web/data.json (+ data.js legacy). web-astro đã bị xoá (gom 1 frontend Nuxt).
    ROOT = Path(__file__).resolve().parent.parent
    web_data_js = ROOT / "web" / "data.js"
    web_data_json = ROOT / "web" / "data.json"

    print("Exporting from database...")
    data = export_from_db()
    print(f"  {len(data['entities'])} entities, {len(data['relationships'])} relationships, {len(data['itineraries'])} itineraries")

    write_data_js(data, web_data_js)
    write_json(data, web_data_json)

    print("Done.")


if __name__ == "__main__":
    main()
