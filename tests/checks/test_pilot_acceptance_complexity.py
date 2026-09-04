from __future__ import annotations

from pathlib import Path

from scripts.checks.check_complexity import ComplexityCheck


def test_pilot_acceptance_binding_helpers_stay_within_complexity_limit() -> None:
    """R20.8 helpers remain small while the gate evaluator keeps its own seam."""

    target_names = {
        "_execution_receipt",
        "_canonical_evidence_payload",
        "_authority_contract",
        "_bind_evidence",
    }
    result = ComplexityCheck(root=Path(__file__).resolve().parents[2]).run(
        ["scripts/ops/run_pilot_acceptance.py"]
    )

    violations = [
        violation
        for violation in result["violations"]
        if any(f"{name}()" in violation["msg"] for name in target_names)
    ]
    assert violations == []
