# -*- coding: utf-8 -*-
"""R20.4 — coverage gate (SP3 Backend). Đọc coverage.json (sinh bởi
`pytest --cov=agent --cov-report=json`), so ngưỡng agent-total + core-4 module.

Gate KHÔNG chạy pytest (chậm/nặng) — chỉ đọc coverage.json có sẵn; vắng file →
count 0 (graceful skip, không chặn hook staged). Enforce ở pre_merge/CI nơi
coverage.json được sinh trước.

Ngưỡng ratchet đọc từ docs/standards/coverage-thresholds.json (nâng dần, không tụt):
  {"agent": 60, "core": {"database.py": 80, "auth.py": 80, "social.py": 80, "server.py": 80}}
count = số ngưỡng CHƯA đạt (0 = pass). level soft-ratchet để nợ giảm dần theo đợt.
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import repo_root

COV_JSON = "coverage.json"
THRESHOLDS = "docs/standards/coverage-thresholds.json"
CORE = ("database.py", "auth.py", "social.py", "server.py")


def _pct(files: dict, suffix: str) -> float | None:
    """% covered cho core-module theo basename CHÍNH XÁC (agent/server.py).
    Phải khớp đúng tên file, KHÔNG endswith lỏng — nếu không `mcp_server.py`
    (basename khác) sẽ che `server.py` và trả nhầm 0%."""
    for name, data in files.items():
        n = name.replace("\\", "/")
        if n.rsplit("/", 1)[-1] == suffix:
            return (data.get("summary") or {}).get("percent_covered", 0.0)
    return None


class CoverageCheck:
    name, level, rule = "coverage", "soft-ratchet", "R20.4"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _load(self, rel: str) -> dict | None:
        p = self.root / rel
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def run(self, files: list[str] | None = None) -> dict:
        cov = self._load(COV_JSON)
        if cov is None:
            return self._result([])  # vắng coverage.json → skip
        thr = self._load(THRESHOLDS) or {"agent": 60, "core": {c: 80 for c in CORE}}
        cfiles = cov.get("files", {})
        violations = []
        agent_total = (cov.get("totals") or {}).get("percent_covered")
        if agent_total is not None and agent_total < thr.get("agent", 60):
            violations.append({"file": "agent/", "line": 0, "rule": self.rule,
                               "msg": f"agent coverage {agent_total:.1f}% < {thr.get('agent', 60)}%"})
        for mod, floor in (thr.get("core") or {}).items():
            pct = _pct(cfiles, mod)
            if pct is not None and pct < floor:
                violations.append({"file": f"agent/{mod}", "line": 0, "rule": self.rule,
                                   "msg": f"{mod} coverage {pct:.1f}% < {floor}%"})
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [CoverageCheck()]
