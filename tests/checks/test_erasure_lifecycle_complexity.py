from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from checks.check_complexity import ComplexityCheck  # noqa: E402

if TYPE_CHECKING:
    import data_lifecycle
    import memory_graph
    import prompt_compiler


TARGET_FILES = (
    "agent/data_lifecycle.py",
    "agent/memory_graph.py",
    "agent/prompt_compiler.py",
)


def test_erasure_lifecycle_helpers_do_not_increase_complexity_debt():
    result = ComplexityCheck(root=ROOT).run(files=list(TARGET_FILES))

    assert result["violations"] == []
