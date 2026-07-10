# -*- coding: utf-8 -*-
"""R30.7 — bundle budget (SP4). Parse web-nuxt/.output/public/_nuxt, đo gz size
tổng + chunk lớn nhất, so ngưỡng docs/standards/bundle-budget.json (ratchet: chỉ
GIẢM, không tăng). Đích chuẩn: entry ≤200kB gz — chunk lớn nhất hiện 276kB là nợ,
giảm dần qua ratchet.

Vắng .output (chưa build) → count 0 (graceful-skip, không chặn hook staged). Chạy
sau `npm run build`.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from .common import repo_root

NUXT_DIR = "web-nuxt/.output/public/_nuxt"
BUDGET = "docs/standards/bundle-budget.json"
DEFAULTS = {"total_gz_kb": 800, "max_chunk_gz_kb": 280, "entry_target_gz_kb": 200}


def _gz_kb(p: Path) -> int:
    return len(gzip.compress(p.read_bytes())) // 1024


class BundleCheck:
    name, level, rule = "bundle", "soft-ratchet", "R30.7"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _budget(self) -> dict:
        p = self.root / BUDGET
        if p.exists():
            try:
                return {**DEFAULTS, **json.loads(p.read_text(encoding="utf-8"))}
            except (OSError, json.JSONDecodeError):
                pass
        return dict(DEFAULTS)

    def run(self, files: list[str] | None = None) -> dict:
        nuxt = self.root / NUXT_DIR
        js = list(nuxt.glob("*.js")) if nuxt.exists() else []
        if not js:
            return self._result([])  # chưa build → skip
        budget = self._budget()
        sizes = [(_gz_kb(f), f.name) for f in js]
        total = sum(s for s, _ in sizes)
        max_chunk, max_name = max(sizes)
        violations = []
        if total > budget["total_gz_kb"]:
            violations.append({"file": NUXT_DIR, "line": 0, "rule": self.rule,
                               "msg": f"bundle total {total}kB gz > {budget['total_gz_kb']}kB"})
        if max_chunk > budget["max_chunk_gz_kb"]:
            violations.append({"file": f"{NUXT_DIR}/{max_name}", "line": 0, "rule": self.rule,
                               "msg": f"chunk lớn nhất {max_chunk}kB gz > {budget['max_chunk_gz_kb']}kB "
                                      f"(đích entry {budget['entry_target_gz_kb']}kB)"})
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [BundleCheck()]
