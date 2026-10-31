"""Tests for Phase-B Ground-Truth Data & Terroir Readiness Validator (QW-47 / QW-49 / QW-52)."""

from __future__ import annotations

from scripts.checks.verify_phase_b_readiness import (
    DATA_JSON_PATH,
    PhaseBReadinessCheck,
    _sha256,
    verify_phase_b_readiness,
)


def test_phase_b_ground_truth_in_memory_readiness_and_hash_preservation():
    before_hash = _sha256(DATA_JSON_PATH)
    report = verify_phase_b_readiness()
    after_hash = _sha256(DATA_JSON_PATH)

    assert report["ok"] is True, f"Readiness errors: {report['errors']}"
    assert report["schemaVersion"] == 3
    assert report["appliedDossiers"] == 34
    assert report["appliedRuralCorrections"] == 126
    assert report["appliedMistypedFixes"] == 21
    assert report["appliedTruncatedSummaries"] == 20
    assert report["appliedPlaceSelfFixes"] == 37
    assert report["duplicateClustersCatalogued"] == 16
    assert report["totalEntitiesValidated"] == 1772
    assert report["dataJsonSha256Preserved"] is True
    assert before_hash == after_hash


def test_phase_b_readiness_hard_check_gate():
    check = PhaseBReadinessCheck()
    result = check.run()
    assert result["rule"] == "R10.12"
    assert result["level"] == "hard"
    assert result["count"] == 0
    assert result["violations"] == []
