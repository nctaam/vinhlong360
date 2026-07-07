# -*- coding: utf-8 -*-
"""R20.7 — agent/*.py đổi mà không có test nào staged cùng (SOFT-RATCHET per-commit).

Baseline = 0 → mọi commit vi phạm bị chặn; thoát hiểm hợp lệ = SKIP_CHECKS (soft, có log).
"""
from __future__ import annotations

from pathlib import Path


class TestPairingCheck:
    __test__ = False  # không phải pytest test-class
    name, level, rule = "test_pairing", "soft-ratchet", "R20.7"

    def __init__(self, root: Path | None = None):
        self._root = root

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        if files:  # chỉ có nghĩa ở chế độ staged
            norm = [f.replace("\\", "/") for f in files]
            agent_py = [f for f in norm if f.startswith("agent/") and f.endswith(".py") and "/tests/" not in f]
            has_tests = any(f.startswith("tests/") or "/tests/" in f for f in norm)
            if agent_py and not has_tests:
                violations.append({"file": agent_py[0], "line": 0, "rule": self.rule,
                                   "msg": f"{len(agent_py)} file agent/ đổi nhưng không test nào staged (R20.7/B3)"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [TestPairingCheck()]
