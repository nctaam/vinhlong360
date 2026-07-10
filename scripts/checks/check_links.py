# -*- coding: utf-8 -*-
"""R60.4 — broken internal link trong docs-active (HARD-RATCHET).

Link markdown [text](target): target tương-đối được thử theo (a) thư mục file,
(b) repo root. http(s)/mailto/# bỏ qua; fragment sau # cắt bỏ trước khi thử.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from .common import iter_text_files, repo_root

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")  # bỏ code-span: `[..](path)` mô tả rule ≠ link thật
EXCLUDE = ["docs/archive", "docs/research"]


def _select_candidates(root: Path, files: list[str] | None) -> list[str]:
    if files is None:
        return iter_text_files(root, ["*.md"], ["docs"], EXCLUDE)
    return [
        f.replace("\\", "/") for f in files
        if f.replace("\\", "/").startswith("docs/") and f.endswith(".md")
        and not any(f.replace("\\", "/").startswith(e) for e in EXCLUDE)
    ]


def _scan_line(rel: str, i: int, line: str, p: Path, root: Path, violations: list) -> None:
    for m in LINK_RE.finditer(INLINE_CODE_RE.sub("", line)):  # bỏ inline-code trước khi match
        target = unquote(m.group(1).split("#")[0].strip())
        if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        cand_a = (p.parent / target)
        cand_b = (root / target)
        if not cand_a.exists() and not cand_b.exists():
            violations.append({"file": rel, "line": i, "rule": LinksCheck.rule,
                               "msg": f"link chết: ({m.group(1)})"})


def _scan_file(rel: str, p: Path, root: Path, violations: list) -> None:
    in_fence = False
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):  # fenced-code block → bỏ qua
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        _scan_line(rel, i, line, p, root, violations)


class LinksCheck:
    name, level, rule = "links", "hard-ratchet", "R60.4"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        candidates = _select_candidates(self.root, files)
        for rel in candidates:
            p = self.root / rel
            if not p.exists():
                continue
            _scan_file(rel, p, self.root, violations)
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [LinksCheck()]
