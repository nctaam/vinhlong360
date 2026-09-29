from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_llms_txt import generate_llms


def _candidate_json(tmp_path: Path) -> Path:
    path = tmp_path / "candidate.json"
    payload = {
        "entities": [
            {
                "id": "press-1",
                "type": "attraction",
                "name": "Press item",
                "summary": "A reviewed item",
                "attributes": {
                    "image_type": "press",
                    "is_verified_photo": True,
                    "image_author": "A. Reporter",
                    "image_source": "Local paper",
                    "image_source_url": "https://publisher.example/item",
                    "image_license": "Permission granted",
                    "permission_evidence": "owner-record:press-1",
                },
            },
            {
                "id": "ai-1",
                "type": "attraction",
                "name": "AI item",
                "attributes": {"image_type": "ai-generated", "is_verified_photo": False},
            },
            {
                "id": "placeholder-1",
                "type": "attraction",
                "name": "Placeholder item",
                "attributes": {"image_type": "generated-placeholder", "is_verified_photo": False},
            },
            {
                "id": "incomplete-press",
                "type": "attraction",
                "name": "Incomplete press item",
                "attributes": {"image_type": "press", "is_verified_photo": True, "image_author": "Unknown"},
            },
            {"id": "prov-1", "type": "place", "name": "Tombstone", "attributes": {}},
        ],
        "relationships": [],
        "itineraries": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_llms_output_does_not_invent_press_credits(tmp_path: Path) -> None:
    candidate_json = _candidate_json(tmp_path)
    outputs = generate_llms(candidate_json, tmp_path / "out")
    for key in ("llms", "llms_full"):
        content = outputs[key].read_text(encoding="utf-8")
        assert "prov-1" not in content
        assert "100% ảnh WebP nội bộ" not in content
        assert "Google Images" not in content
        assert "Google Images" not in content
    full = outputs["llms_full"].read_text(encoding="utf-8")
    assert "Minh họa AI" in full
    assert "Minh họa đồ họa" in full
    assert "Chưa có ảnh đã xác minh nguồn gốc" in full
    assert "Incomplete press item" in full
    assert "Unknown" not in full


def test_llms_cli_requires_explicit_paths_and_help_is_read_only(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/generate_llms_txt.py"
    refused = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert refused.returncode != 0
    output = tmp_path / "help-output.txt"
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    help_run = subprocess.run([sys.executable, str(script), "--help"], cwd=tmp_path, capture_output=True, text=True, env=env)
    assert help_run.returncode == 0
    assert not output.exists()
