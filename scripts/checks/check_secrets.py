# -*- coding: utf-8 -*-
"""R70.1 — secrets hardcode + .env bị stage (tầng HARD)."""
from __future__ import annotations

import math
import re
from pathlib import Path

from .common import iter_text_files, repo_root

KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|passwd)\s*[=:]\s*['\"]([A-Za-z0-9+/_\-]{16,})['\"]", re.I
)
_ALLOW_LINE = re.compile(r"(example|placeholder|xxx+|your[_-]|<.*>|\bos\.environ|getenv|env\(|process\.env|import\.meta|b64|base64|alphabet|charset|ABCDEFGHIJKLMNOPQRSTUVWXYZ)")
_STRING_32 = re.compile(r"['\"]([A-Za-z0-9+/=_\-]{32,})['\"]")
_EXCLUDE = ["tests", ".env.example", "package-lock.json", "scripts/checks", "web-nuxt/node_modules"]
_ROOTS = ["agent", "scripts", "web-nuxt"]
_GLOBS = ["*.py", "*.ts", "*.vue", "*.js", "*.json", "*.sh", "*.ps1"]


def _entropy(s: str) -> float:
    freq = {c: s.count(c) for c in set(s)}
    return -sum(n / len(s) * math.log2(n / len(s)) for n in freq.values())


class SecretsCheck:
    name, level, rule = "secrets", "hard", "R70.1"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        candidates = (
            [f.replace("\\", "/") for f in files]
            if files is not None
            else iter_text_files(self.root, _GLOBS, _ROOTS, _EXCLUDE)
        )
        for rel in candidates:
            # .env thật bị stage = chặn tuyệt đối
            if rel == ".env" or rel.endswith("/.env"):
                violations.append({"file": rel, "line": 0, "rule": self.rule,
                                   "msg": "CẤM stage file .env (secret thật)"})
                continue
            if any(rel.startswith(e) or e in rel for e in _EXCLUDE):
                continue
            if not any(rel.endswith(g.lstrip("*")) for g in _GLOBS):
                continue
            p = self.root / rel
            if not p.exists():
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if _ALLOW_LINE.search(line):
                    continue
                m = KEY_PATTERN.search(line)
                if m:
                    violations.append({"file": rel, "line": i, "rule": self.rule,
                                       "msg": f"nghi hardcode secret ({m.group(1)}=...)"})
                    continue
                sm = _STRING_32.search(line)
                if sm and _entropy(sm.group(1)) > 4.5:
                    violations.append({"file": rel, "line": i, "rule": self.rule,
                                       "msg": "chuỗi entropy cao ≥32 ký tự — nghi secret"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [SecretsCheck()]
