import json
import subprocess
import sys
from pathlib import Path

from agent.media_truth_manifest import load_batch_21_truth

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs/batch_culinary_restaurants_photos.json"


def test_batch_21_generator_emits_manifest_partition() -> None:
    subprocess.run([sys.executable, "scripts/ops/generate_batch_21.py"], cwd=ROOT, check=True)
    rows = json.loads(OUTPUT.read_text(encoding="utf-8"))
    truth = load_batch_21_truth()
    assert len(rows) == 39
    assert {row["entity_id"] for row in rows} == {
        *truth.ai_generated,
        *truth.generated_placeholder,
    }
    assert all(row["image"] == f"web-nuxt/public/img/entities/{row['entity_id']}.webp" for row in rows)
    assert all(row["is_verified_photo"] is False for row in rows)
    assert sum(row["image_type"] == "generated-placeholder" for row in rows) == 37
    assert sum(row["image_type"] == "ai-generated" for row in rows) == 2
    assert all("author" not in row and "license" not in row and "source" not in row for row in rows)
    assert all(
        row["image_generation_model"] == "cx/gpt-5.5-image"
        and row["image_generation_reference"] == "git:30a3fae9"
        for row in rows
        if row["image_type"] == "ai-generated"
    )


def test_batch_21_generator_is_byte_deterministic() -> None:
    subprocess.run([sys.executable, "scripts/ops/generate_batch_21.py"], cwd=ROOT, check=True)
    first = OUTPUT.read_bytes()
    subprocess.run([sys.executable, "scripts/ops/generate_batch_21.py"], cwd=ROOT, check=True)
    assert OUTPUT.read_bytes() == first
