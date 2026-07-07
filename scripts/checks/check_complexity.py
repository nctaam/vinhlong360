# -*- coding: utf-8 -*-
"""R20.8 complexity >12 (SOFT-RATCHET) + R20.3 bare-except (SOFT-RATCHET) cho agent/ + scripts/."""
from __future__ import annotations

import ast
from pathlib import Path

from .common import iter_text_files, repo_root

LIMIT = 12
_ROOTS = ["agent", "scripts"]
_EXCLUDE = ["agent/tests", "scripts/checks/__pycache__"]


def _complexity(node: ast.AST) -> int:
    score = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With,
                          ast.Assert, ast.comprehension, ast.IfExp)):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
    return score


class ComplexityCheck:
    name, level, rule = "complexity", "soft-ratchet", "R20.8"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _candidates(self, files):
        if files is None:
            return iter_text_files(self.root, ["*.py"], _ROOTS, _EXCLUDE)
        return [f.replace("\\", "/") for f in files
                if f.endswith(".py") and any(f.replace("\\", "/").startswith(r + "/") for r in _ROOTS)]

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        for rel in self._candidates(files):
            p = self.root / rel
            if not p.exists():
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    c = _complexity(node)
                    if c > LIMIT:
                        violations.append({"file": rel, "line": node.lineno, "rule": self.rule,
                                           "msg": f"hàm {node.name}() complexity {c} > {LIMIT}"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


class BareExceptCheck:
    name, level, rule = "bare_except", "soft-ratchet", "R20.3"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        helper = ComplexityCheck(root=self._root)
        for rel in helper._candidates(files):
            p = self.root / rel
            if not p.exists():
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    violations.append({"file": rel, "line": node.lineno, "rule": self.rule,
                                       "msg": "bare except: — bắt Exception cụ thể (R20.3)"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [ComplexityCheck(), BareExceptCheck()]
