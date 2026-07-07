# -*- coding: utf-8 -*-
"""R20.1 — ruff lint (tầng HARD-RATCHET): đếm vi phạm dưới config pyproject.toml.

Config (select E/F/W, ignore style cố ý E402/E701/E702/E501/E741) sống ở
pyproject.toml — ruff tự nạp. Gate CHỈ đếm + ratchet (nợ không tăng); nhóm
style repo giữ nguyên đã bị ignore nên không tính.

Định vị ruff robust: PATH → C:/Python314/Scripts/ruff.exe → python -m ruff.
KHÔNG có ruff (máy khác) → count 0 (graceful skip, không chặn).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from .common import _norm, repo_root

ROOTS = ("agent", "scripts")


def find_ruff() -> list[str] | None:
    exe = shutil.which("ruff")
    if exe:
        return [exe]
    for cand in (r"C:/Python314/Scripts/ruff.exe", r"C:\Python314\Scripts\ruff.exe"):
        if Path(cand).exists():
            return [cand]
    # fallback: python -m ruff (chỉ dùng được nếu ruff cài trong env này)
    try:
        r = subprocess.run([sys.executable, "-m", "ruff", "--version"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return [sys.executable, "-m", "ruff"]
    except OSError:
        pass
    return None


def run_ruff(root: Path, targets: list[str], select: str | None = None) -> list[dict]:
    """Trả list violation (dict ruff json) — [] nếu không target hoặc không có ruff.

    select=None → dùng config pyproject.toml; select="ASYNC" → chỉ nhóm đó.
    """
    if not targets:
        return []
    ruff = find_ruff()
    if not ruff:
        return []
    extra = ["--select", select] if select else []
    proc = subprocess.run(
        ruff + ["check", *targets, *extra, "--output-format", "json", "--quiet"],
        capture_output=True, encoding="utf-8", errors="replace", cwd=str(root),
    )
    out = (proc.stdout or "").strip()
    if not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


class RuffCheck:
    name, level, rule = "ruff_lint", "hard-ratchet", "R20.1"
    select: str | None = None  # None = config pyproject.toml

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _targets(self, files: list[str] | None) -> list[str]:
        if files is None:
            return [r for r in ROOTS if (self.root / r).exists()]
        picked = []
        for f in files:
            rel = _norm(f)
            if rel.endswith(".py") and any(rel == r or rel.startswith(r + "/") for r in ROOTS):
                picked.append(rel)
        return picked

    def run(self, files: list[str] | None = None) -> dict:
        targets = self._targets(files)
        violations = run_ruff(self.root, targets, select=self.select)
        out = [{"file": _norm(str(v.get("filename", ""))), "line": (v.get("location") or {}).get("row", 0),
                "rule": self.rule, "msg": f'{v.get("code")}: {v.get("message", "")[:80]}'}
               for v in violations]
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(out), "violations": out}


class RuffAsyncCheck(RuffCheck):
    """R20.2 — blocking-sync trong async (ruff ASYNC). Baseline 0 (đã đạt); ratchet
    riêng để 1 blocking-async mới KHÔNG bị 'bù trừ' trong tổng R20.1."""
    name, level, rule = "ruff_async", "hard-ratchet", "R20.2"
    select = "ASYNC"


CHECKS = [RuffCheck(), RuffAsyncCheck()]
