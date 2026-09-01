from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))

from control_plane.snapshot import current_generation
from database import Database


def test_entity_mutation_exposes_one_shared_generation_to_read_consumers(tmp_path):
    db = Database(str(tmp_path / "proof.db"))
    entity_id = "proof-entity"
    db.upsert_entity({"id": entity_id, "type": "dish", "name": "Before"})
    first = current_generation(entity_id)
    assert first == 1

    db.upsert_entity({"id": entity_id, "type": "dish", "name": "After"})
    second = current_generation(entity_id)
    assert second == first + 1
    assert db.get_entity(entity_id)["name"] == "After"
