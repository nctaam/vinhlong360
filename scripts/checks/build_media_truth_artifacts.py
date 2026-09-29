#!/usr/bin/env python3
"""Build a deterministic media-truth artifact bundle outside public paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import export_fe_data  # type: ignore[import-not-found]
from scripts import generate_llms_txt  # type: ignore[import-not-found]
from scripts.checks import build_data_review_manifest  # type: ignore[import-not-found]
from scripts.checks import build_image_provenance_review  # type: ignore[import-not-found]


class ArtifactBuildError(ValueError):
    """Raised when candidate artifact inputs are incomplete or unsafe."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_candidate_file(root: Path, candidates: tuple[str, ...], label: str) -> Path:
    for relative in candidates:
        path = root / relative
        if path.is_file():
            return path
    raise ArtifactBuildError(f"missing candidate {label} under {root}")


def _copy_input(path: Path, output_dir: Path, name: str | None = None) -> Path:
    destination = output_dir / (name or path.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    return destination


def _image_path(entity: dict[str, Any], entity_id: str) -> str:
    images = entity.get("images")
    if isinstance(images, list) and images and isinstance(images[0], str):
        return images[0]
    return f"/img/entities/{entity_id}.webp"


def _load_entities(json_path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list):
        raise ArtifactBuildError("candidate JSON must contain an entities list")
    return {
        str(entity["id"]): entity
        for entity in payload["entities"]
        if isinstance(entity, dict) and isinstance(entity.get("id"), str)
    }


def _build_provenance_scope(
    *, root: Path, json_path: Path, sqlite_path: Path, ledger: Path, truth_path: Path, output: Path
) -> Path:
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    ids = sorted({item for key in ("delete", "ai_generated", "generated_placeholder") for item in truth.get(key, [])})
    entities = _load_entities(json_path)
    records: list[dict[str, Any]] = []
    for entity_id in ids:
        image_path = _image_path(entities.get(entity_id, {}), entity_id)
        if entity_id not in entities and entity_id in truth.get("delete", []):
            records.append(build_image_provenance_review._target_absent_packet(entity_id, image_path))
            continue
        if entity_id not in entities:
            raise ArtifactBuildError(f"candidate JSON is missing truth target: {entity_id}")
        packet = build_image_provenance_review.build_packet(
            root,
            entity_id=entity_id,
            image_path=image_path,
            sqlite_path=sqlite_path,
            json_path=json_path,
            photo_ledger=ledger,
        )
        records.append(packet)
    payload = {
        "schemaVersion": 1,
        "mode": "read-only-image-provenance-review-scope",
        "status": "review_required",
        "mutationAllowed": False,
        "truthManifest": {"path": str(truth_path), "sha256": _sha(truth_path)},
        "records": records,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return output


def build_candidate_artifacts(
    candidate_root: Path,
    output_dir: Path,
    *,
    truth_manifest: Path,
    batch_ledger: Path,
    renderer_registry: Path,
) -> dict[str, Path]:
    """Build every public-facing artifact from explicit candidate/review inputs."""
    candidate_root = Path(candidate_root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = _resolve_candidate_file(candidate_root, ("web/data.json", "data.json", "candidate.json"), "JSON")
    sqlite_path = _resolve_candidate_file(candidate_root, ("agent/data/vinhlong360.db", "data/vinhlong360.db", "candidate.db"), "SQLite")

    llms_dir = output_dir / "llms"
    llms = generate_llms_txt.generate_llms(json_path, llms_dir)
    fe = export_fe_data.export_frontend_data(sqlite_path=sqlite_path, json_path=None, output_dir=output_dir / "data")

    review_manifest = output_dir / "data-review-manifest.json"
    build_data_review_manifest.build_manifest(candidate_root, review_manifest)
    provenance = _build_provenance_scope(
        root=candidate_root,
        json_path=json_path,
        sqlite_path=sqlite_path,
        ledger=Path(batch_ledger).resolve(),
        truth_path=Path(truth_manifest).resolve(),
        output=output_dir / "image-provenance-review.json",
    )

    ledger_copy = _copy_input(Path(batch_ledger).resolve(), output_dir, "batch-21-media-truth-ledger.json")
    renderer_copy = _copy_input(Path(renderer_registry).resolve(), output_dir, "entity-image-renderers.json")

    outputs: dict[str, Path] = {
        "entity_index": fe["entity_index"],
        "llms": llms["llms"],
        "llms_full": llms["llms_full"],
        "image_provenance_review": provenance,
        "data_review_manifest": review_manifest,
        "batch_21_ledger": ledger_copy,
        "renderer_registry": renderer_copy,
    }
    manifest_entries = []
    for key, path in sorted(outputs.items()):
        manifest_entries.append({"key": key, "path": path.relative_to(output_dir).as_posix(), "bytes": path.stat().st_size, "sha256": _sha(path)})
    manifest = output_dir / "manifest.json"
    manifest.write_text(json.dumps({"schemaVersion": 1, "artifacts": manifest_entries}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    outputs["manifest"] = manifest
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--batch-ledger", type=Path, required=True)
    parser.add_argument("--renderer-registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        build_candidate_artifacts(
            args.candidate_root,
            args.output_dir,
            truth_manifest=args.truth,
            batch_ledger=args.batch_ledger,
            renderer_registry=args.renderer_registry,
        )
    except (ArtifactBuildError, OSError, ValueError) as exc:
        print(f"media truth artifact build refused: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
