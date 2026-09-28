"""Regenerate the Batch 21 generated-media ledger from its frozen manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs/batch_culinary_restaurants_photos.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.media_truth_manifest import load_batch_21_truth


def generate() -> list[dict]:
    truth = load_batch_21_truth(ROOT)
    rows: list[dict] = []
    for image_type, entity_ids in (
        ("ai-generated", truth.ai_generated),
        ("generated-placeholder", truth.generated_placeholder),
    ):
        for entity_id in entity_ids:
            row = {
                "entity_id": entity_id,
                "image": f"web-nuxt/public/img/entities/{entity_id}.webp",
                "image_type": image_type,
                "is_verified_photo": False,
            }
            if image_type == "ai-generated":
                row["image_generation_model"] = "cx/gpt-5.5-image"
                row["image_generation_reference"] = "git:30a3fae9"
            rows.append(row)
    return rows


def main() -> None:
    rows = generate()
    rendered = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    if not OUTPUT.exists() or OUTPUT.read_bytes() != rendered.encode("utf-8"):
        OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Generated {OUTPUT.relative_to(ROOT)} with {len(rows)} entries!")


if __name__ == "__main__":
    main()
