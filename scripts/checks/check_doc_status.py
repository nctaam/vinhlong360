# -*- coding: utf-8 -*-
"""R60.1 — docs-active thiếu STATUS header (HARD-RATCHET).

docs-active .md phải có dòng chứa 'STATUS' dạng blockquote trong 10 dòng đầu.
File cũ chưa có → nằm trong baseline; file MỚI thiếu STATUS làm counter tăng → chặn.
"""
from __future__ import annotations

import re
from pathlib import Path

from .common import iter_text_files, repo_root

STATUS_RE = re.compile(r"^>\s*\*{0,2}STATUS", re.M)
EXCLUDE = ["docs/archive", "docs/research"]


class DocStatusCheck:
    name, level, rule = "doc_status", "hard-ratchet", "R60.1"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        if files is None:
            candidates = iter_text_files(self.root, ["*.md"], ["docs"], EXCLUDE)
        else:
            candidates = [
                f.replace("\\", "/") for f in files
                if f.replace("\\", "/").startswith("docs/") and f.endswith(".md")
                and not any(f.replace("\\", "/").startswith(e) for e in EXCLUDE)
            ]
        for rel in candidates:
            p = self.root / rel
            if not p.exists() or p.name == "README.md" and rel == "docs/archive/README.md":
                continue
            head = "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:10])
            if not STATUS_RE.search(head):
                violations.append({"file": rel, "line": 1, "rule": self.rule,
                                   "msg": "thiếu '> STATUS (...)' trong 10 dòng đầu (R60.1)"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [DocStatusCheck()]
