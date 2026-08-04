from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_complexity import ComplexityCheck  # noqa: E402


TARGET_FILES = (
    "agent/entity_details.py",
    "agent/itinerary_optimizer.py",
    "scripts/check_entity_write_paths.py",
    "scripts/verify_entity_invariants.py",
)


def test_wave1_backend_helpers_stay_below_the_complexity_limit():
    result = ComplexityCheck(root=ROOT).run(files=list(TARGET_FILES))

    assert result["violations"] == []
