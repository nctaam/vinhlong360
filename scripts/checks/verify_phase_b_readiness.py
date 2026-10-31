"""Phase-B Ground-Truth Data & Terroir Readiness Validator (QW-47 / QW-49 / QW-52).

Simulates applying `outputs/ground-truth-9router-verification-2026-10-21.json`
(schemaVersion 3: 34 multi-source factual dossiers + 126 post-merger placeId
corrections + 21 mistyped entity fixes + 19 truncated summary fixes + 37 place
self-placeId fixes + 16 duplicate cluster checks) against an in-memory clone of
`web/data.json` without mutating `web/data.json` on disk (preserving R10.hash
lock until the owner-approved Phase-1 apply gate).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_REL = "web/data.json"
GROUND_TRUTH_REL = "outputs/ground-truth-9router-verification-2026-10-21.json"
DATA_JSON_PATH = ROOT / DATA_REL
GROUND_TRUTH_PATH = ROOT / GROUND_TRUTH_REL
EXTERNAL_GATEWAYS = {"gateway-hcm"}
TRUNCATED_SUFFIXES = ("TP.", "(H.", "+ H.")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_dossier_sources(eid: str, sources: list[dict[str, Any]]) -> list[str]:
    if not sources:
        return [f"Dossier {eid} has empty sources list"]
    errs: list[str] = []
    for src in sources:
        if not src.get("url", "").startswith("http") or not src.get("domain"):
            errs.append(f"Dossier {eid} has invalid source entry: {src}")
    return errs


def _apply_single_dossier(
    item: dict[str, Any],
    entities_by_id: dict[str, dict[str, Any]],
    places_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    eid = item.get("entityId", "<missing>")
    if eid not in entities_by_id:
        return [f"Dossier entityId not found in data.json: {eid}"]
    truth = item.get("verifiedGroundTruth") or {}
    target_place = truth.get("placeId")
    if target_place and target_place not in places_by_id:
        return [f"Dossier {eid} references unknown placeId: {target_place}"]
    source_errs = _validate_dossier_sources(eid, truth.get("sources") or [])
    if source_errs:
        return source_errs

    entity = entities_by_id[eid]
    for field in ("address", "summary", "phone", "hours"):
        if truth.get(field):
            entity[field] = truth[field]
    if target_place:
        entity["placeId"] = target_place
    return []


def _apply_rural_correction(
    corr: dict[str, Any],
    orig_by_id: dict[str, dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
    places_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    eid = corr.get("entityId", "<missing>")
    current_pid = corr.get("currentPlaceId")
    verified_pid = corr.get("verifiedPlaceId")
    if eid not in entities_by_id:
        return [f"Rural correction entityId not found: {eid}"]
    if verified_pid not in places_by_id:
        return [f"Rural correction {eid} target placeId not in places: {verified_pid}"]
    orig_pid = orig_by_id[eid].get("placeId")
    if orig_pid != current_pid:
        return [f"Rural correction {eid} currentPlaceId mismatch: expected {current_pid}, got {orig_pid}"]
    entities_by_id[eid]["placeId"] = verified_pid
    return []


def _apply_mistyped_entity(
    item: dict[str, Any],
    orig_by_id: dict[str, dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    eid = item.get("entityId", "<missing>")
    if eid not in entities_by_id:
        return [f"Mistyped entityId not found: {eid}"]
    if orig_by_id[eid].get("type") != item.get("currentType"):
        return [f"Mistyped entity {eid} currentType mismatch"]
    entities_by_id[eid]["type"] = item.get("verifiedType")
    return []


def _apply_truncated_summary(
    item: dict[str, Any],
    orig_by_id: dict[str, dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    eid = item.get("entityId", "<missing>")
    if eid not in entities_by_id:
        return [f"Truncated summary entityId not found: {eid}"]
    if orig_by_id[eid].get("summary") != item.get("currentSummary"):
        return [f"Truncated summary {eid} currentSummary mismatch"]
    verified_summary = str(item.get("verifiedSummary") or "").strip()
    if not verified_summary:
        return [f"Truncated summary {eid} verifiedSummary is empty"]
    entities_by_id[eid]["summary"] = verified_summary
    return []


def _apply_place_self_id(
    item: dict[str, Any],
    orig_by_id: dict[str, dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    eid = item.get("entityId", "<missing>")
    if eid not in entities_by_id:
        return [f"Place self-ID entityId not found: {eid}"]
    if orig_by_id[eid].get("placeId") != item.get("currentPlaceId"):
        return [f"Place self-ID {eid} currentPlaceId mismatch"]
    verified_pid = item.get("verifiedPlaceId")
    if verified_pid != eid:
        return [f"Place self-ID {eid} verifiedPlaceId must equal entityId, got {verified_pid}"]
    entities_by_id[eid]["placeId"] = verified_pid
    return []


def _validate_entity_summary(eid: str, summary: str) -> list[str]:
    errs: list[str] = []
    if summary.count("(") != summary.count(")"):
        errs.append(f"Post-patch entity {eid} has unbalanced parentheses in summary")
    if summary.endswith(TRUNCATED_SUFFIXES):
        errs.append(f"Post-patch entity {eid} has truncated summary: {summary}")
    return errs


def _validate_post_patch_entity(
    e: dict[str, Any],
    places_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    eid = e.get("id", "<missing>")
    pid = e.get("placeId")
    errs: list[str] = []
    if e.get("type") == "place":
        if pid != eid:
            errs.append(f"Post-patch place {eid} has non-self placeId: {pid}")
    elif pid == "vinh-long":
        errs.append(f"Post-patch entity {eid} still uses province root placeId 'vinh-long'")
    elif pid is not None and pid not in places_by_id and pid not in EXTERNAL_GATEWAYS:
        errs.append(f"Post-patch entity {eid} has invalid placeId: {pid}")
    if not str(e.get("name") or "").strip():
        errs.append(f"Post-patch entity {eid} has empty name")
    errs.extend(_validate_entity_summary(eid, str(e.get("summary") or "").strip()))
    return errs


def _run_batch_patches(
    gt: dict[str, Any],
    orig_by_id: dict[str, dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
    places_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, int], list[str]]:
    errors: list[str] = []
    counts = {
        "dossiers": 0,
        "rural": 0,
        "types": 0,
        "summaries": 0,
        "place_self": 0,
    }
    for item in gt.get("verifiedDossiers", []):
        d_errs = _apply_single_dossier(item, entities_by_id, places_by_id)
        errors.extend(d_errs)
        counts["dossiers"] += int(not d_errs)

    for corr in gt.get("ruralPlaceIdCorrections", []):
        r_errs = _apply_rural_correction(corr, orig_by_id, entities_by_id, places_by_id)
        errors.extend(r_errs)
        counts["rural"] += int(not r_errs)

    for mt in gt.get("mistypedEntities", []):
        m_errs = _apply_mistyped_entity(mt, orig_by_id, entities_by_id)
        errors.extend(m_errs)
        counts["types"] += int(not m_errs)

    for ts in gt.get("truncatedSummaryFixes", []):
        s_errs = _apply_truncated_summary(ts, orig_by_id, entities_by_id)
        errors.extend(s_errs)
        counts["summaries"] += int(not s_errs)

    for ps in gt.get("placeSelfIdFixes", []):
        p_errs = _apply_place_self_id(ps, orig_by_id, entities_by_id)
        errors.extend(p_errs)
        counts["place_self"] += int(not p_errs)

    return counts, errors


def verify_phase_b_readiness(
    data_path: Path = DATA_JSON_PATH,
    ground_truth_path: Path = GROUND_TRUTH_PATH,
) -> dict[str, Any]:
    """Validate Phase-B ground-truth patch against an in-memory clone of data.json."""
    hash_before = _sha256(data_path)
    raw_data = json.loads(data_path.read_text(encoding="utf-8"))
    gt = json.loads(ground_truth_path.read_text(encoding="utf-8"))

    cloned = copy.deepcopy(raw_data)
    orig_by_id = {e["id"]: e for e in raw_data.get("entities", []) if "id" in e}
    entities_by_id = {e["id"]: e for e in cloned.get("entities", []) if "id" in e}
    places_by_id = {eid: e for eid, e in entities_by_id.items() if e.get("type") == "place"}

    counts, errors = _run_batch_patches(gt, orig_by_id, entities_by_id, places_by_id)
    for e in cloned.get("entities", []):
        errors.extend(_validate_post_patch_entity(e, places_by_id))

    hash_after = _sha256(data_path)
    if hash_before != hash_after:
        errors.append("R10.hash violation: data.json was modified on disk")

    return {
        "ok": len(errors) == 0,
        "schemaVersion": gt.get("schemaVersion", 1),
        "appliedDossiers": counts["dossiers"],
        "appliedRuralCorrections": counts["rural"],
        "appliedMistypedFixes": counts["types"],
        "appliedTruncatedSummaries": counts["summaries"],
        "appliedPlaceSelfFixes": counts["place_self"],
        "duplicateClustersCatalogued": len(gt.get("duplicateEntityClusters", [])),
        "totalEntitiesValidated": len(cloned.get("entities", [])),
        "dataJsonSha256Preserved": hash_before == hash_after,
        "errors": errors,
    }


class PhaseBReadinessCheck:
    """R10.12 — Hard quality gate validating Phase-B ground-truth ledger readiness."""

    name, level, rule = "phase_b_ground_truth_readiness", "hard", "R10.12"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or ROOT

    def run(self, files: list[str] | None = None) -> dict[str, Any]:
        data_path = self.root / DATA_REL
        gt_path = self.root / GROUND_TRUTH_REL
        if not data_path.exists() or not gt_path.exists():
            if self.root.resolve() != ROOT.resolve():
                return {
                    "check": self.name,
                    "level": self.level,
                    "rule": self.rule,
                    "count": 0,
                    "violations": [],
                }
            missing = DATA_REL if not data_path.exists() else GROUND_TRUTH_REL
            return {
                "check": self.name,
                "level": self.level,
                "rule": self.rule,
                "count": 1,
                "violations": [
                    {
                        "file": missing,
                        "line": 0,
                        "rule": self.rule,
                        "msg": f"Missing required Phase-B readiness artifact: {missing}",
                    }
                ],
            }
        report = verify_phase_b_readiness(data_path=data_path, ground_truth_path=gt_path)
        violations = [
            {"file": GROUND_TRUTH_REL, "line": 0, "rule": self.rule, "msg": err}
            for err in report["errors"]
        ]
        return {
            "check": self.name,
            "level": self.level,
            "rule": self.rule,
            "count": len(violations),
            "violations": violations,
        }


CHECKS = [PhaseBReadinessCheck()]


if __name__ == "__main__":
    report = verify_phase_b_readiness()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)
