#!/usr/bin/env python3
"""Sinh ảnh AI cover cho entities thiếu ảnh.

Dùng gen_image.py internally (import hàm generate).
Lưu ảnh vào web-nuxt/public/img/entities/{entity_id}.jpg
Cập nhật entity.images trong DB.

Usage:
  python scripts/gen_entity_images.py --type dish --limit 10 --dry-run
  python scripts/gen_entity_images.py --type dish --limit 10
  python scripts/gen_entity_images.py --id banh-trang-phoi-suong

Flags:
  --type          Filter entity type (dish, experience, product, ...)
  --limit         Max entities to process (default 10)
  --dry-run       Chỉ in prompt, không gọi API
  --id            Sinh cho 1 entity cụ thể
  --skip-existing Bỏ qua entity đã có images (default True)

QUAN TRỌNG:
  - Mỗi ảnh tốn 1 API call → chạy manual với --limit
  - Cần env: IMAGE_API_KEY, IMAGE_API_BASE, IMAGE_MODEL
  - Prompt KHÔNG chứa text/watermark
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
IMG_DIR = ROOT / "web-nuxt" / "public" / "img" / "entities"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(ROOT / "scripts"))

PROMPT_TEMPLATES = {
    "dish": (
        "Vietnamese food photography, {name}, Mekong Delta cuisine, "
        "natural lighting, overhead angle, no text, no watermark"
    ),
    "experience": (
        "Travel photography, {name}, Vinh Long Vietnam, "
        "golden hour, candid style, no text, no watermark"
    ),
    "product": (
        "Product photography, {name}, Vietnamese OCOP product, "
        "clean white background, no text, no watermark"
    ),
    "accommodation": (
        "Hotel or homestay exterior, {name}, Mekong Delta Vietnam, "
        "warm lighting, no text, no watermark"
    ),
    "nature": (
        "Landscape photography, {name}, Mekong Delta Vietnam, "
        "aerial perspective, lush green, no text, no watermark"
    ),
    "history": (
        "Vietnamese heritage site, {name}, architectural photography, "
        "warm tones, no text, no watermark"
    ),
    "attraction": (
        "Vietnamese heritage site, {name}, architectural photography, "
        "warm tones, no text, no watermark"
    ),
    "craft_village": (
        "Vietnamese artisan workshop, {name}, traditional craft, "
        "warm documentary style, no text, no watermark"
    ),
    "event": (
        "Vietnamese festival, {name}, Mekong Delta celebration, "
        "vibrant colors, documentary style, no text, no watermark"
    ),
    "facility": (
        "Vietnamese public building, {name}, clean exterior photography, "
        "daytime, no text, no watermark"
    ),
    "organization": (
        "Vietnamese cooperative or business, {name}, professional photography, "
        "daytime exterior, no text, no watermark"
    ),
    "cafe": (
        "Vietnamese cafe interior, {name}, Mekong Delta, cozy ambiance, "
        "warm lighting, no text, no watermark"
    ),
    "restaurant": (
        "Vietnamese restaurant, {name}, Mekong Delta, appetizing food display, "
        "warm lighting, no text, no watermark"
    ),
}

DEFAULT_PROMPT = (
    "Photography of {name}, Vietnam, Mekong Delta region, "
    "natural lighting, no text, no watermark"
)


def build_prompt(entity: dict) -> str:
    etype = entity.get("type", "")
    name = entity.get("name", entity.get("id", "unknown"))
    template = PROMPT_TEMPLATES.get(etype, DEFAULT_PROMPT)
    prompt = template.format(name=name)
    area = entity.get("area", "")
    if area and area not in prompt.lower():
        area_label = {"vinh-long": "Vinh Long", "ben-tre": "Ben Tre",
                      "tra-vinh": "Tra Vinh"}.get(area, area)
        prompt += f", {area_label} province"
    return prompt


def load_entities(entity_type=None, entity_id=None, skip_existing=True):
    try:
        from database import db
        entities = db.all_entities()
    except Exception as e:
        print(f"[WARN] Cannot import database: {e}")
        print("[WARN] Falling back to web/data.json")
        data_path = ROOT / "web" / "data.json"
        if not data_path.exists():
            sys.exit(f"ERROR: {data_path} not found")
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        entities = data.get("entities", [])

    if entity_id:
        entities = [e for e in entities if e.get("id") == entity_id]
        if not entities:
            sys.exit(f"ERROR: entity '{entity_id}' not found")
        return entities

    if entity_type:
        entities = [e for e in entities if e.get("type") == entity_type]

    # Exclude place-type entities
    entities = [e for e in entities if e.get("type") != "place"]

    if skip_existing:
        entities = [e for e in entities
                    if not e.get("images") or len(e.get("images", [])) == 0]

    return entities


def update_entity_image(entity_id: str, image_path: str):
    rel_path = f"/img/entities/{entity_id}.jpg"
    try:
        from database import db
        entity = db.get_entity(entity_id)
        if not entity:
            print(f"  [WARN] Entity {entity_id} not found in DB, skip DB update")
            return
        images = entity.get("images") or []
        if rel_path not in images:
            images.insert(0, rel_path)
        entity["images"] = images
        db.upsert_entity(entity)
        print(f"  [DB] Updated {entity_id}: images={images[:3]}")
    except Exception as e:
        print(f"  [WARN] DB update failed: {e}")
        print(f"  [INFO] Image saved at {image_path}, update DB manually")


def main():
    ap = argparse.ArgumentParser(description="Sinh ảnh AI cover cho entities thiếu ảnh")
    ap.add_argument("--type", dest="entity_type", help="Filter entity type")
    ap.add_argument("--limit", type=int, default=10, help="Max entities (default 10)")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ in prompt, không gọi API")
    ap.add_argument("--id", dest="entity_id", help="Sinh cho 1 entity cụ thể")
    ap.add_argument("--skip-existing", action="store_true", default=True,
                    help="Bỏ qua entity đã có images (default True)")
    ap.add_argument("--no-skip-existing", action="store_false", dest="skip_existing",
                    help="Bao gồm entity đã có images")
    args = ap.parse_args()

    entities = load_entities(args.entity_type, args.entity_id, args.skip_existing)

    if not entities:
        print("[INFO] Không có entity nào cần sinh ảnh.")
        return

    total = min(len(entities), args.limit) if not args.entity_id else len(entities)
    entities = entities[:total]

    print(f"[INFO] {total} entities to process (dry_run={args.dry_run})")
    print(f"[INFO] Output dir: {IMG_DIR}")
    if not args.dry_run:
        IMG_DIR.mkdir(parents=True, exist_ok=True)

    success, fail = 0, 0
    for i, entity in enumerate(entities, 1):
        eid = entity.get("id", "unknown")
        name = entity.get("name", eid)
        etype = entity.get("type", "?")
        prompt = build_prompt(entity)
        out_path = IMG_DIR / f"{eid}.jpg"

        print(f"\n[{i}/{total}] {eid} ({etype})")
        print(f"  Name: {name}")
        print(f"  Prompt: {prompt}")
        print(f"  Output: {out_path}")

        if args.dry_run:
            print("  [DRY-RUN] Skipped")
            success += 1
            continue

        try:
            from gen_image import generate
            generate(prompt, str(out_path))
            update_entity_image(eid, str(out_path))
            success += 1
        except SystemExit as e:
            print(f"  [FAIL] {e}")
            fail += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            fail += 1

    print(f"\n[DONE] Success: {success}, Failed: {fail}, Total: {total}")


if __name__ == "__main__":
    main()
