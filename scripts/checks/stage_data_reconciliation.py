"""Stage a reviewed media-truth plan into an owned candidate bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.checks import apply_data_reconciliation as apply_module
    from scripts.checks.build_media_truth_plan import _json_render, _sha, sqlite_logical_digest
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.checks import apply_data_reconciliation as apply_module
    from scripts.checks.build_media_truth_plan import _json_render, _sha, sqlite_logical_digest


class StageError(ValueError):
    """Raised when staging would leave the owned-copy boundary."""


@dataclass(frozen=True)
class StageResult:
    output_dir: Path
    plan_bytes: bytes
    json_bytes: bytes
    logical_sqlite_digest: str
    stage_result: dict[str, Any]


def _asset_digest(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append((path.relative_to(root).as_posix(), _sha(path)))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def _asset_inventory(root: Path) -> list[dict[str, str]]:
    inventory = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        inventory.append({"id": path.stem, "path": relative, "sha256": _sha(path)})
    return inventory


def _protected(root: Path) -> set[Path]:
    return {(root / "agent/data/vinhlong360.db").resolve(), (root / "web/data.json").resolve(), (root / "web-nuxt/public/img/entities").resolve()}


def _ensure_no_sidecars(sqlite_path: Path) -> None:
    sidecars = tuple(Path(str(sqlite_path) + suffix) for suffix in ("-wal", "-shm", "-journal"))
    if any(path.exists() for path in sidecars):
        raise StageError(f"SQLite sidecar present: {sqlite_path}")


def _refuses_protected(output_dir: Path, root: Path) -> None:
    output_dir = output_dir.resolve()
    for protected in _protected(root):
        if output_dir == protected or protected in output_dir.parents or output_dir in protected.parents:
            raise StageError(f"protected output path refused: {output_dir}")


_EXPECTED_SUMMARY = {
    "batch21Records": 40,
    "deletedEntities": 1,
    "retainedPlaceholders": 37,
    "retainedAi": 2,
    "jsonRelationshipsDeleted": 6,
    "sqliteRelationshipsDeleted": 0,
}


def _validate_stage_request(
    plan: dict[str, Any], sqlite_input: Path, json_input: Path, asset_root: Path,
) -> list[dict[str, Any]]:
    _validate_stage_flags(plan)
    _ensure_no_sidecars(sqlite_input)
    if _sha(sqlite_input) != plan.get("inputs", {}).get("sqlite", {}).get("sha256") or _sha(json_input) != plan.get("inputs", {}).get("json", {}).get("sha256"):
        raise StageError("staging input hash mismatch")
    if not asset_root.is_dir():
        raise StageError(f"missing asset root: {asset_root}")
    return _validated_mutations(plan)


def _validate_stage_flags(plan: dict[str, Any]) -> None:
    if plan.get("status") != "review_required" or plan.get("mutationAllowed") is not False:
        raise StageError("staging requires review_required and mutationAllowed=false")
    if (plan.get("verification") or {}).get("mode") != "targeted-media-v1":
        raise StageError("staging requires targeted-media-v1 verification")
    if plan.get("summary") != _EXPECTED_SUMMARY:
        raise StageError("staging scope counts do not match Batch 21")


def _validated_mutations(plan: dict[str, Any]) -> list[dict[str, Any]]:
    mutations = plan.get("mutations")
    if not isinstance(mutations, list):
        raise StageError("plan mutations must be a list")
    deleted_asset_ids = sorted({
        mutation.get("recordId")
        for mutation in mutations
        if mutation.get("recordType") == "entity" and mutation.get("operation") == "delete"
    })
    if deleted_asset_ids != ["prov-1"]:
        raise StageError("reviewed asset deletion must contain only prov-1")
    return mutations


def _apply_candidate_stores(
    mutations: list[dict[str, Any]], sqlite_input: Path, candidate_db: Path,
    candidate_json: Path, json_input: Path,
) -> None:
    shutil.copy2(sqlite_input, candidate_db)
    payload = json.loads(json_input.read_text(encoding="utf-8"))
    conn = sqlite3.connect(candidate_db)
    try:
        for mutation in mutations:
            if mutation.get("store") == "sqlite":
                apply_module._sqlite_mutation(conn, mutation)
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    apply_module._apply_json_mutations(payload, [item for item in mutations if item.get("store") == "json"])
    candidate_json.write_bytes(_json_render(payload))


def _stage_assets(
    asset_root: Path, candidate_assets: Path, plan: dict[str, Any], mutations: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    source_asset_digest = _asset_digest(asset_root)
    source_assets = _asset_inventory(asset_root)
    shutil.copytree(asset_root, candidate_assets, dirs_exist_ok=True)
    deleted_asset_ids = ["prov-1"]
    removed_assets = [_remove_reviewed_asset(candidate_assets, plan, record_id) for record_id in deleted_asset_ids]
    _validate_reviewed_assets(candidate_assets, plan, deleted_asset_ids)
    retained_assets = _asset_inventory(candidate_assets)
    if retained_assets != [item for item in source_assets if item["id"] not in deleted_asset_ids]:
        raise StageError("candidate asset tree differs from the reviewed source tree")
    return retained_assets, removed_assets, source_asset_digest


def _remove_reviewed_asset(candidate_assets: Path, plan: dict[str, Any], record_id: str) -> dict[str, str]:
    path = candidate_assets / f"{record_id}.webp"
    if not path.is_file():
        raise StageError(f"reviewed asset is missing: {record_id}")
    source = (plan.get("affectedAssets") or {}).get(record_id) or {}
    digest = _sha(path)
    if digest != source.get("sha256"):
        raise StageError(f"reviewed asset hash mismatch: {record_id}")
    path.unlink()
    return {"id": record_id, "path": path.name, "sha256": digest}


def _validate_reviewed_assets(candidate_assets: Path, plan: dict[str, Any], deleted_asset_ids: list[str]) -> None:
    for record_id, metadata in sorted((plan.get("affectedAssets") or {}).items()):
        if record_id in deleted_asset_ids:
            continue
        path = candidate_assets / f"{record_id}.webp"
        if not path.is_file() or _sha(path) != metadata.get("sha256"):
            raise StageError(f"retained asset hash mismatch: {record_id}")


def stage_plan(plan: dict[str, Any], sqlite_input: Path, json_input: Path, asset_root: Path, output_dir: Path) -> StageResult:
    sqlite_input, json_input, asset_root, output_dir = map(Path, (sqlite_input, json_input, asset_root, output_dir))
    root = Path(__file__).resolve().parents[2]
    _refuses_protected(output_dir, root)
    mutations = _validate_stage_request(plan, sqlite_input, json_input, asset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / "candidate"
    candidate.mkdir(parents=True, exist_ok=True)
    candidate_db = candidate / "vinhlong360.db"
    candidate_json = candidate / "data.json"
    candidate_assets = candidate / "public/img/entities"
    _apply_candidate_stores(mutations, sqlite_input, candidate_db, candidate_json, json_input)
    json_bytes = candidate_json.read_bytes()
    retained_assets, removed_assets, source_asset_digest = _stage_assets(asset_root, candidate_assets, plan, mutations)
    target_result = apply_module.verify_plan_result(plan, candidate_db, candidate_json)
    expected = plan.get("expectedOutputs") or {}
    if _sha(candidate_json) != expected.get("jsonSha256"):
        raise StageError("candidate JSON hash does not match the reviewed plan")
    if sqlite_logical_digest(candidate_db) != expected.get("sqliteLogicalDigest"):
        raise StageError("candidate SQLite digest does not match the reviewed plan")
    expected_assets = expected.get("assetSha256") or {}
    for record_id, source in (plan.get("affectedAssets") or {}).items():
        if not isinstance(source, dict) or expected_assets.get(record_id) != source.get("sha256"):
            raise StageError(f"asset hash missing from reviewed plan: {record_id}")
    protected_after = {"sqlite": _sha(sqlite_input), "json": _sha(json_input)}
    stage_result = {
        "schemaVersion": 1,
        "status": "review_required",
        "mutationAllowed": False,
        "verificationMode": "targeted-media-v1",
        "inputs": {
            "sqliteSha256": plan["inputs"]["sqlite"]["sha256"],
            "jsonSha256": plan["inputs"]["json"]["sha256"],
            "truthManifestSha256": plan["inputs"]["truthManifest"]["sha256"],
            "assetRootDigest": source_asset_digest,
        },
        "candidate": {
            "jsonSha256": _sha(candidate_json),
            "sqliteLogicalDigest": sqlite_logical_digest(candidate_db),
            "assetRootDigest": _asset_digest(candidate_assets),
        },
        "targetVerification": target_result,
        "counts": plan.get("summary", {}),
        "assets": {"retained": retained_assets, "removed": removed_assets},
        "protectedStoreAfterHashes": protected_after,
    }
    stage_bytes = (json.dumps(stage_result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    (candidate / "stage-result.json").write_bytes(stage_bytes)
    plan_bytes = (json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    return StageResult(output_dir.resolve(), plan_bytes, json_bytes, stage_result["candidate"]["sqliteLogicalDigest"], stage_result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--sqlite", type=Path, default=Path("agent/data/vinhlong360.db"))
    parser.add_argument("--json", dest="json_path", type=Path, default=Path("web/data.json"))
    parser.add_argument("--assets", type=Path, default=Path("web-nuxt/public/img/entities"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    def rooted(path: Path) -> Path:
        return path if path.is_absolute() else root / path
    try:
        plan = json.loads(rooted(args.plan).read_text(encoding="utf-8"))
        stage_plan(plan, rooted(args.sqlite), rooted(args.json_path), rooted(args.assets), rooted(args.output_dir))
    except (StageError, OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        print(f"media truth staging refused: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
