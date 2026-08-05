# -*- coding: utf-8 -*-
"""R20.7 — mỗi agent/*.py đổi phải có test staged tương ứng.

Baseline = 0 → mọi commit vi phạm bị chặn; thoát hiểm hợp lệ = SKIP_CHECKS (soft, có log).
"""
from __future__ import annotations

import ast
from pathlib import Path
import re


class TestPairingCheck:
    __test__ = False  # không phải pytest test-class
    name, level, rule = "test_pairing", "soft-ratchet", "R20.7"

    def __init__(self, root: Path | None = None):
        self._root = root

    def _test_candidates(self, files: list[str]) -> tuple[dict[str, ast.Module], list[str]]:
        """(ứng viên parse được, file không parse được).

        Đọc bằng `utf-8-sig` để bóc BOM: với `utf-8` thuần, BOM sống sót thành U+FEFF
        và `ast.parse` ném SyntaxError → file rơi khỏi tập ứng viên trong im lặng,
        R20.7 coi như KHÔNG được thực thi cho file đó.

        "Không đọc được" (OSError) ≠ "không phải Python hợp lệ": cái sau là defect,
        phải báo lên chứ không nuốt.
        """
        root = self._root or Path.cwd()
        candidates: dict[str, ast.Module] = {}
        unparseable: list[str] = []
        for relative_path in files:
            path = Path(relative_path)
            in_tests = relative_path.startswith("tests/") or "/tests/" in relative_path
            if not in_tests or not path.name.startswith("test_") or path.suffix != ".py":
                continue
            try:
                source = (root / relative_path).read_text(encoding="utf-8-sig")
            except UnicodeError:  # đọc được nhưng không giải mã được → defect
                unparseable.append(relative_path)
                continue
            except OSError:  # không đọc được (đã xoá/đổi tên/quyền) → không phải defect
                continue
            try:
                candidates[relative_path] = ast.parse(source)
            except (SyntaxError, ValueError):  # ValueError: source chứa null byte
                unparseable.append(relative_path)
        return candidates, unparseable

    @staticmethod
    def _has_tests(tree: ast.Module) -> bool:
        """File test phải chứa ít nhất một hàm test THẬT.

        Không có bước này, một file rỗng tuếch tên `test_social.py` đủ để
        `agent/social.py` qua cổng — tên khớp là điều kiện duy nhất. Đã kiểm
        thực nghiệm 2026-08-05: file 0 byte cho count=0.
        """
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.walk(tree)
        )

    @staticmethod
    def _filename_pairs(module: str, test_path: str) -> bool:
        test_stem = Path(test_path).stem
        return re.search(rf"(?:^|_){re.escape(module)}(?:_|$)", test_stem) is not None

    @staticmethod
    def _ast_pairs(module: str, tree: ast.Module) -> bool:
        import_names = {module, f"agent.{module}"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name in import_names for alias in node.names):
                    return True
            elif isinstance(node, ast.ImportFrom):
                if node.module in import_names:
                    return True
                if node.module == "agent" and any(alias.name == module for alias in node.names):
                    return True
        return False

    def _test_pairs(self, module: str, test_path: str, tree: ast.Module) -> bool:
        return self._filename_pairs(module, test_path) or self._ast_pairs(module, tree)

    def run(self, files: list[str] | None = None) -> dict:
        violations = []
        if files:  # chỉ có nghĩa ở chế độ staged
            norm = [f.replace("\\", "/") for f in files]
            agent_py = [f for f in norm if f.startswith("agent/") and f.endswith(".py") and "/tests/" not in f]
            tests, unparseable = self._test_candidates(norm)
            violations.extend(
                {"file": broken, "line": 0, "rule": self.rule,
                 "msg": "test staged không parse được (encoding/cú pháp) — không đối chiếu được R20.7"}
                for broken in unparseable
            )
            empty = sorted(path for path, tree in tests.items() if not self._has_tests(tree))
            violations.extend(
                {"file": path, "line": 0, "rule": self.rule,
                 "msg": "file test staged không có hàm test_* nào — không tính là test cho R20.7"}
                for path in empty
            )
            tests = {path: tree for path, tree in tests.items() if path not in set(empty)}
            unpaired = [
                source for source in agent_py
                if not any(
                    self._test_pairs(Path(source).stem, test, tree)
                    for test, tree in tests.items()
                )
            ]
            if unpaired:
                violations.append({"file": unpaired[0], "line": 0, "rule": self.rule,
                                   "msg": f"{len(unpaired)} file agent/ đổi nhưng chưa có test staged tương ứng (R20.7/B3)"})
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


CHECKS = [TestPairingCheck()]
