from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_complexity import ComplexityCheck  # noqa: E402


def test_moderation_functions_stay_below_the_complexity_limit():
    result = ComplexityCheck(root=ROOT).run(files=["agent/moderation.py"])

    assert result["violations"] == []
