# -*- coding: utf-8 -*-
"""R20.5 — đổi route agent/ mà không cập nhật docs/api-contract.md cùng commit (tầng HARD)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .common import repo_root

ROUTE_RE = re.compile(r"^[+-]\s*@(router|app)\.(get|post|put|delete|patch)\(")
CONTRACT = "docs/api-contract.md"


class ApiContractCheck:
    name, level, rule = "api_contract", "hard", "R20.5"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        if files is None:
            # --all: không có khái niệm diff — check này chỉ có nghĩa ở chế độ staged
            return self._result([])
        files = [f.replace("\\", "/") for f in files]
        agent_py = [f for f in files if f.startswith("agent/") and f.endswith(".py")]
        if agent_py and CONTRACT not in files:
            for f in agent_py:
                # encoding tường minh: Windows text=True decode cp1252 → chết
                # reader-thread trên diff UTF-8 tiếng Việt (stdout thành None)
                diff = subprocess.run(
                    ["git", "diff", "--cached", "-U0", "--", f],
                    capture_output=True, encoding="utf-8", errors="replace", cwd=str(self.root),
                ).stdout or ""
                changed_routes = [ln for ln in diff.splitlines() if ROUTE_RE.match(ln)]
                if changed_routes:
                    violations.append({
                        "file": f, "line": 0, "rule": self.rule,
                        "msg": f"{len(changed_routes)} route thêm/xoá nhưng {CONTRACT} không staged cùng commit",
                    })
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [ApiContractCheck()]
