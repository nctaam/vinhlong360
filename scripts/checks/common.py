# -*- coding: utf-8 -*-
"""Nền dùng chung cho bộ check tiêu chuẩn (SP1).

Interface chuẩn:
- CheckResult: {"check", "level", "rule", "count", "violations": [{"file","line","rule","msg"}]}
- level ∈ {"hard", "hard-ratchet", "soft-ratchet", "soft"}
- RegexCheck: check khai báo bằng pattern — 8/12 module chỉ là config trên class này.
- Ratchet: so count với docs/standards/baseline.json (COMMITTED) — tăng là chặn.
"""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from pathlib import Path

# Dòng mang ngữ cảnh phủ định/cảnh báo — không tính là vi phạm
NEG_DEFAULT = re.compile(
    r"(KHÔNG|KHONG|CẤM|không dùng|đừng|OVERRIDE|ARCHIVED|đã bỏ|đã xoá|đã dừng|banned|deprecated|ngoại lệ|whitelist|từ.khoá|blacklist|filler|\bno\b|Supersedes)",
    re.I,
)

_SKIP_DIRS = {".git", "node_modules", ".nuxt", ".output", "dist", "__pycache__", ".venv", "venv"}


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def staged_files(root: Path | None = None) -> list[str]:
    """File đã stage (Added/Copied/Modified/Renamed) — đường dẫn repo-relative, forward-slash."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, cwd=str(root) if root else None, check=True,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def _norm(rel: str) -> str:
    return rel.replace("\\", "/")


def iter_text_files(root: Path, globs: list[str], roots: list[str], exclude_paths: list[str]) -> list[str]:
    """Liệt kê file repo-relative khớp globs dưới roots, bỏ exclude + thư mục hệ thống."""
    found: list[str] = []
    for base in roots:
        base_dir = root / base
        if not base_dir.exists():
            continue
        for p in base_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.parts):
                continue
            rel = _norm(str(p.relative_to(root)))
            if any(rel.startswith(_norm(e)) for e in exclude_paths):
                continue
            if any(fnmatch.fnmatch(p.name, g) for g in globs):
                found.append(rel)
    return found


class RegexCheck:
    """Check khai báo: quét dòng khớp patterns (bỏ dòng khớp neg_context)."""

    def __init__(
        self,
        name: str,
        level: str,
        rule: str,
        patterns: list[str],
        globs: list[str],
        roots: list[str],
        exclude_paths: list[str] | None = None,
        neg_context: re.Pattern | None = NEG_DEFAULT,
        msg: str = "",
        root: Path | None = None,
        count_matches: bool = False,  # True: đếm TỪNG match (file 1-dòng lớn như data.json); neg_context bị bỏ qua
    ):
        assert level in {"hard", "hard-ratchet", "soft-ratchet", "soft"}
        self.name, self.level, self.rule = name, level, rule
        self.patterns = [re.compile(p) for p in patterns]
        self.globs, self.roots = globs, roots
        self.exclude_paths = exclude_paths or []
        self.neg_context = neg_context
        self.msg = msg or f"vi phạm {rule}"
        self._root = root
        self.count_matches = count_matches

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _candidates(self, files: list[str] | None) -> list[str]:
        if files is None:
            return iter_text_files(self.root, self.globs, self.roots, self.exclude_paths)
        picked = []
        for f in files:
            rel = _norm(f)
            if any(rel.startswith(_norm(e)) for e in self.exclude_paths):
                continue
            if not any(rel == _norm(b) or rel.startswith(_norm(b) + "/") for b in self.roots):
                continue
            if any(fnmatch.fnmatch(Path(rel).name, g) for g in self.globs):
                picked.append(rel)
        return picked

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        for rel in self._candidates(files):
            path = self.root / rel
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if self.count_matches:
                for p in self.patterns:
                    for _ in p.finditer(text):
                        violations.append({"file": rel, "line": 0, "rule": self.rule, "msg": self.msg})
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if self.neg_context is not None and self.neg_context.search(line):
                    continue
                if any(p.search(line) for p in self.patterns):
                    violations.append({"file": rel, "line": i, "rule": self.rule, "msg": self.msg})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


# ---------------- baseline / ratchet ----------------

def _baseline_path(root: Path) -> Path:
    return root / "docs" / "standards" / "baseline.json"


def load_baseline(root: Path | None = None) -> dict:
    p = _baseline_path(root or repo_root())
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_baseline(baseline: dict, root: Path | None = None) -> None:
    p = _baseline_path(root or repo_root())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(baseline.items())), ensure_ascii=False, indent=1), encoding="utf-8")


def ratchet_violations(results: list[dict], baseline: dict) -> tuple[list[str], list[str]]:
    """(blockers, suggestions): tăng so baseline = chặn; giảm = đề nghị hạ baseline.

    Chỉ áp cho level *-ratchet. hard thuần do runner xử (count>0 = chặn); soft thuần chỉ report.
    """
    blockers, suggestions = [], []
    for r in results:
        if not r["level"].endswith("-ratchet"):
            continue
        base = baseline.get(r["rule"], 0)
        if r["count"] > base:
            blockers.append(
                f'{r["rule"]} ({r["check"]}): {r["count"]} vi phạm > baseline {base} — RATCHET: nợ chuẩn không được tăng.'
            )
        elif r["count"] < base:
            suggestions.append(
                f'{r["rule"]} ({r["check"]}): {r["count"]} < baseline {base} — chạy baseline_tool --write để ghi nhận tiến bộ.'
            )
    return blockers, suggestions
