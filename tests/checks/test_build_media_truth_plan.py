from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.checks import apply_data_reconciliation as apply_module
from scripts.checks.build_media_truth_plan import PRESS_FIELDS, PlanError, build_plan, render_plan, sqlite_logical_digest


ROOT = Path(__file__).resolve().parents[2]


def test_plan_has_exact_phase_1_scope():
    plan = build_plan(ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "docs/standards/batch-21-media-truth.json")
    assert plan["status"] == "review_required"
    assert plan["mutationAllowed"] is False
    assert plan["verification"]["mode"] == "targeted-media-v1"
    assert plan["summary"] == {"batch21Records": 40, "deletedEntities": 1, "retainedPlaceholders": 37, "retainedAi": 2, "jsonRelationshipsDeleted": 6, "sqliteRelationshipsDeleted": 0}
    assert len(plan["verification"]["entityIds"]) == 40


def test_plan_is_byte_deterministic():
    args = (ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "docs/standards/batch-21-media-truth.json")
    assert render_plan(build_plan(*args)) == render_plan(build_plan(*args))
    assert len(sqlite_logical_digest(args[1])) == 64


def test_plan_only_adds_generation_fields_to_ai_ids_and_preserves_verified_at():
    plan = build_plan(ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "docs/standards/batch-21-media-truth.json")
    generation_mutations = [
        item
        for item in plan["mutations"]
        if item["field"] in {"attributes.image_generation_model", "attributes.image_generation_reference"}
    ]
    assert {item["recordId"] for item in generation_mutations} == {"cua-com-duyen-hai", "tep-rang-dua"}
    assert {item["store"] for item in generation_mutations} == {"json", "sqlite"}
    assert all("verifiedAt" not in item["field"] for item in plan["mutations"])

    press_fields = {f"attributes.{field}" for field in PRESS_FIELDS}
    press_mutations = [item for item in plan["mutations"] if item["field"] in press_fields]
    assert press_mutations
    assert all(item["operation"] == "remove" and item["after"] is None for item in press_mutations)


def test_generated_plan_passes_shared_mutation_validator():
    plan = build_plan(ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "docs/standards/batch-21-media-truth.json")
    mutations, json_mutations, sqlite_mutations = apply_module._validated_mutations(plan)
    assert len(mutations) == len(plan["mutations"])
    assert len(json_mutations) + len(sqlite_mutations) == len(mutations)


def test_asset_paths_are_root_relative_and_stable():
    plan = build_plan(ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", ROOT / "docs/standards/batch-21-media-truth.json")
    paths = {item["path"] for item in plan["affectedAssets"].values()}
    assert paths == {f"web-nuxt/public/img/entities/{record_id}.webp" for record_id in plan["affectedAssets"]}
    assert all(not Path(path).is_absolute() for path in paths)


def test_sqlite_logical_digest_ignores_relationship_row_order(tmp_path):
    import sqlite3

    paths = [tmp_path / "a.db", tmp_path / "b.db"]
    for path, relationships in zip(paths, [[("a", "b", "near"), ("b", "c", "far")], [("b", "c", "far"), ("a", "b", "near")]]):
        with sqlite3.connect(path) as conn:
            conn.executescript("CREATE TABLE entities (id TEXT, attributes TEXT); CREATE TABLE relationships (from_id TEXT, to_id TEXT, type TEXT);")
            conn.executemany("INSERT INTO entities VALUES (?, ?)", [("a", "{}"), ("b", "{}"), ("c", "{}")])
            conn.executemany("INSERT INTO relationships VALUES (?, ?, ?)", relationships)
    assert sqlite_logical_digest(paths[0]) == sqlite_logical_digest(paths[1])


def test_builder_rejects_wrong_truth_manifest(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(PlanError):
        build_plan(ROOT, ROOT / "agent/data/vinhlong360.db", ROOT / "web/data.json", bad)
