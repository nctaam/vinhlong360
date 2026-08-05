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
# `<...>` chỉ miễn khi là PLACEHOLDER (`<YOUR_API_KEY>`, `<TOKEN>`), không phải
# thẻ HTML. Pattern cũ `<.*>` miễn mọi dòng có một cặp ngoặc nhọn — trong SFC Vue
# gần như dòng template nào cũng có, nên một secret đặt giữa `<div>…</div>` lọt
# sạch (đã đo 2026-08-05: cùng chuỗi đó trong .py bị chặn, trong .vue thì không).
_ALLOW_LINE = re.compile(r"(example|placeholder|xxx+|your[_-]|<[A-Z][A-Z0-9_ -]{1,30}>|\bos\.environ|getenv|env\(|process\.env|import\.meta|b64|base64|alphabet|charset|ABCDEFGHIJKLMNOPQRSTUVWXYZ)")
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

    def _candidates(self, files: list[str] | None) -> list[str]:
        return (
            [f.replace("\\", "/") for f in files]
            if files is not None
            else iter_text_files(self.root, _GLOBS, _ROOTS, _EXCLUDE)
        )

    def _scan_line(self, rel: str, i: int, line: str) -> dict | None:
        if _ALLOW_LINE.search(line):
            return None
        m = KEY_PATTERN.search(line)
        if m:
            return {"file": rel, "line": i, "rule": self.rule,
                    "msg": f"nghi hardcode secret ({m.group(1)}=...)"}
        sm = _STRING_32.search(line)
        if sm and _entropy(sm.group(1)) > 4.5:
            return {"file": rel, "line": i, "rule": self.rule,
                    "msg": "chuỗi entropy cao ≥32 ký tự — nghi secret"}
        return None

    def _scan_file(self, rel: str, p: Path) -> list[dict]:
        found = []
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            v = self._scan_line(rel, i, line)
            if v is not None:
                found.append(v)
        return found

    @staticmethod
    def _is_secret_env_file(rel: str) -> bool:
        """`.env` VÀ mọi biến thể `.env.<gì đó>`, trừ các bản mẫu.

        Điều kiện cũ chỉ khớp đúng `.env`, nên `.env.production` / `.env.local`
        — đúng những file mang secret PROD — vừa thoát chặn tuyệt đối, vừa rớt
        khỏi bộ lọc đuôi file bên dưới, tức không được quét lấy một dòng.
        """
        name = Path(rel).name
        if name in {".env.example", ".env.sample", ".env.template", ".env.dist"}:
            return False
        return name == ".env" or name.startswith(".env.")

    def _file_violations(self, rel: str) -> list[dict]:
        # .env thật bị stage = chặn tuyệt đối
        if self._is_secret_env_file(rel):
            return [{"file": rel, "line": 0, "rule": self.rule,
                     "msg": f"CẤM stage file {Path(rel).name} (secret thật)"}]
        if any(rel.startswith(e) or e in rel for e in _EXCLUDE):
            return []
        if not any(rel.endswith(g.lstrip("*")) for g in _GLOBS):
            return []
        p = self.root / rel
        if not p.exists():
            return []
        return self._scan_file(rel, p)

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        for rel in self._candidates(files):
            violations.extend(self._file_violations(rel))
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [SecretsCheck()]
