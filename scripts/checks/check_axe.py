# -*- coding: utf-8 -*-
"""R30.6 — axe accessibility (SP4). Đọc axe-report.json (sinh bởi CI axe-core scan
14 trang), đếm violation impact serious+critical, đích 0.

Vắng axe-report.json (chưa scan / không có browser local) → count 0 (graceful-skip,
không chặn hook staged). Enforce ở CI nơi axe-report.json sinh trước. Format nhận:
- object đơn {violations:[{impact,...}]}
- list [{url, violations:[...]}] (14-trang sweep)
- {results:[...]} bọc ngoài
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import repo_root

REPORT = "axe-report.json"
SEVERE = {"serious", "critical"}


def _iter_violations(data) -> list:
    """Trích mọi violation từ các format axe report thường gặp."""
    if isinstance(data, dict):
        if "violations" in data:
            return data["violations"] or []
        if "results" in data:
            return _iter_violations(data["results"])
        return []
    if isinstance(data, list):
        out = []
        for item in data:
            out.extend(_iter_violations(item))
        return out
    return []


class AxeCheck:
    name, level, rule = "axe", "hard-ratchet", "R30.6"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        p = self.root / REPORT
        if not p.exists():
            return self._result([])  # chưa scan → skip
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._result([])
        violations = []
        for v in _iter_violations(data):
            if isinstance(v, dict) and str(v.get("impact", "")).lower() in SEVERE:
                violations.append({
                    "file": REPORT, "line": 0, "rule": self.rule,
                    "msg": f"axe {v.get('impact')}: {v.get('id', v.get('help', '?'))}"
                           f" ({len(v.get('nodes', []))} node)",
                })
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [AxeCheck()]


def main() -> int:
    """Chạy riêng R30.6 ở nơi ĐÃ có axe-report.json — job frontend của CI.

    `run_hard --all` chạy ở job Python, nơi không ai quét axe, nên ở đó R30.6
    luôn graceful-skip về 0. Entry này fail-closed khi thiếu report:
        PYTHONPATH=scripts python3 -m checks.check_axe
    """
    check = CHECKS[0]
    report = check.root / REPORT
    if not report.exists():
        print(f"✖ R30.6: không thấy {REPORT} — phải chạy `node scripts/axe_scan.mjs` trước")
        return 2
    result = check.run(None)
    for violation in result["violations"]:
        print(f"✖ R30.6 {violation['msg']}")
    baseline = 0  # 8 serious+ ban đầu đã sửa hết 2026-08-05; cổng nay đòi sạch tuyệt đối
    if result["count"] > baseline:
        print(f"axe: {result['count']} violation serious+ > baseline {baseline}")
        return 1
    print(f"✓ R30.6 axe: {result['count']}/{baseline} violation serious+ (không tăng)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
