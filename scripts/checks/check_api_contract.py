# -*- coding: utf-8 -*-
"""R20.5 — đổi route agent/ mà không cập nhật docs/api-contract.md cùng commit (tầng HARD)."""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from .common import repo_root

ROUTE_RE = re.compile(
    r"""^([+-])\s*@(?:router|app)\.(get|post|put|delete|patch)\(\s*["']([^"']+)["']""")
CONTRACT = "docs/api-contract.md"


DECORATOR_RE = re.compile(r"@(?:router|app)\.(?:get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']")
CONTRACT_PATH_RE = re.compile(r"`(/[A-Za-z0-9_\-/{}.]*)`")
HTTP_METHODS = {"get", "post", "put", "delete", "patch"}

# Mục trong hợp đồng chỉ là tên nhóm/prefix, không phải route cụ thể; và vài tài
# nguyên do frontend Nitro phục vụ chứ không phải agent/.
CONTRACT_NON_ROUTE_ENTRIES = {
    "/", "/api", "/admin", "/auth", "/_internal/", "/chat",
    "/robots.txt", "/sitemap.xml", "/sitemap-index.xml", "/sitemap-media.xml",
}


def _route_changes(diff: str) -> tuple[set[str], set[str]]:
    """Route THÊM và XOÁ thật (net) từ staged diff. Extract-method chỉ DỜI vị trí
    decorator → route xuất hiện ở CẢ dòng `-` lẫn `+` với path y hệt → triệt tiêu.
    Chỉ còn add/xoá path thật hoặc đổi method."""
    added: set[str] = set()
    removed: set[str] = set()
    for ln in diff.splitlines():
        m = ROUTE_RE.match(ln)
        if not m:
            continue
        sign, method, path = m.group(1), m.group(2), m.group(3)
        key = f"{method.upper()} {path}"
        (added if sign == "+" else removed).add(key)
    net = added ^ removed
    return added & net, removed & net


def _matches_any_route(documented: str, code_paths: set[str]) -> bool:
    """Hợp đồng ghi path đã gắn prefix router (vd `/api/posts/{id}`), decorator thì
    không. So bằng đuôi path, và coi mọi placeholder `{...}` là tương đương."""
    def norm(p: str) -> str:
        return re.sub(r"\{[^}]*\}", "{}", p.rstrip("/")) or "/"

    target = norm(documented)
    for path in code_paths:
        candidate = norm(path)
        if target == candidate or target.endswith(candidate) and candidate != "/":
            return True
    return False


class ApiContractCheck:
    name, level, rule = "api_contract", "hard", "R20.5"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _contract_text(self) -> str:
        path = self.root / CONTRACT
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _router_prefixes(tree: ast.Module) -> dict[str, str]:
        """Tên biến router -> prefix khai trong APIRouter(prefix=...)."""
        prefixes: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            if getattr(func, "id", None) != "APIRouter" and getattr(func, "attr", None) != "APIRouter":
                continue
            prefix = next((str(kw.value.value) for kw in node.value.keywords
                           if kw.arg == "prefix" and isinstance(kw.value, ast.Constant)), "")
            prefixes.update({t.id: prefix for t in node.targets if isinstance(t, ast.Name)})
        return prefixes

    @staticmethod
    def _module_constants(tree: ast.Module) -> dict[str, str]:
        """Hằng chuỗi khai ở cấp module: `PATH = "/an-danh"`.

        Không có bảng này thì `@router.get(PATH)` vô hình với cổng — decorator
        chỉ được nhận khi tham số là literal.
        """
        consts: dict[str, str] = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                continue
            if not isinstance(node.value.value, str):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    consts[target.id] = node.value.value
        return consts

    @staticmethod
    def _decorator_path(deco: ast.Call, consts: dict[str, str]) -> str | None:
        arg = deco.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        if isinstance(arg, ast.Name):
            return consts.get(arg.id)
        return None

    @classmethod
    def _decorated_paths(cls, tree: ast.Module, prefixes: dict[str, str]) -> set[str]:
        consts = cls._module_constants(tree)
        paths: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or not deco.args:
                    continue
                func = deco.func
                if not isinstance(func, ast.Attribute) or func.attr not in HTTP_METHODS:
                    continue
                path = cls._decorator_path(deco, consts)
                if path is None:
                    continue
                paths.add(f"{prefixes.get(getattr(func.value, 'id', ''), '')}{path}")
        return paths

    def _paths_in_file(self, file: Path) -> set[str]:
        try:
            source = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return set()
        # Bỏ sớm file không khai route: pre-commit chạy cổng này mỗi lần, parse
        # AST toàn bộ agent/ tốn vài giây không cần thiết.
        if "@router." not in source and "@app." not in source:
            return set()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return set(DECORATOR_RE.findall(source))
        return self._decorated_paths(tree, self._router_prefixes(tree))

    def _code_route_paths(self) -> set[str]:
        """Mọi path route hiện có trong agent/, đã ghép prefix của APIRouter.

        Decorator viết `@router.get("/me/activity")` nhưng router khai
        `APIRouter(prefix="/api")`, nên nếu chỉ đọc decorator thì mọi path trong
        hợp đồng đều trượt và cổng báo oan hàng loạt.
        """
        paths: set[str] = set()
        for file in (self.root / "agent").rglob("*.py"):
            if "/tests/" in file.as_posix() or "\\tests\\" in str(file):
                continue
            paths |= self._paths_in_file(file)
        return paths

    def _stale_contract_entries(self, contract: str) -> list[dict]:
        """--all: hợp đồng mô tả route đã biến mất khỏi code.

        Trước đây nhánh này trả rỗng, nên cổng hạng HARD thực chất vô hiệu ngoài
        lúc commit.
        """
        code_paths = self._code_route_paths()
        return [
            {"file": CONTRACT, "line": 0, "rule": self.rule,
             "msg": f"hợp đồng mô tả `{documented}` nhưng không route nào trong agent/ khớp"}
            for documented in sorted(set(CONTRACT_PATH_RE.findall(contract)))
            if documented not in CONTRACT_NON_ROUTE_ENTRIES
            and not _matches_any_route(documented, code_paths)
        ]

    def _staged_violations(self, path: str, contract: str) -> list[dict]:
        # encoding tường minh: Windows text=True decode cp1252 → chết reader-thread
        # trên diff UTF-8 tiếng Việt (stdout thành None)
        diff = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--", path],
            capture_output=True, encoding="utf-8", errors="replace", cwd=str(self.root),
        ).stdout or ""
        added, removed = _route_changes(diff)

        # Staged file hợp đồng là điều kiện cần, không phải điều kiện đủ: phải
        # thật sự mô tả route mới và bỏ mô tả route đã xoá.
        cases = [
            (sorted(k for k in added if k.split(" ", 1)[1] not in contract),
             "route thêm", f"nhưng {CONTRACT} không mô tả path đó"),
            (sorted(k for k in removed if k.split(" ", 1)[1] in contract),
             "route bị xoá", f"nhưng {CONTRACT} vẫn còn mô tả"),
        ]
        return [
            {"file": path, "line": 0, "rule": self.rule,
             "msg": f"{len(keys)} {label} ({', '.join(keys)}) {tail}"}
            for keys, label, tail in cases if keys
        ]

    def run(self, files: list[str] | None = None) -> dict:
        contract = self._contract_text()
        if files is None:
            return self._result(self._stale_contract_entries(contract))

        violations = []
        for path in (f.replace("\\", "/") for f in files):
            if path.startswith("agent/") and path.endswith(".py"):
                violations.extend(self._staged_violations(path, contract))
        return self._result(violations)

    def _result(self, violations: list) -> dict:
        return {"check": self.name, "level": self.level, "rule": self.rule,
                "count": len(violations), "violations": violations}


class ApiContractCoverageCheck(ApiContractCheck):
    """R20.5b — route CÓ trong code mà hợp đồng không mô tả (chiều ngược).

    R20.5 chỉ đi một chiều: hợp đồng → code. Route mới thêm vào `agent/` mà
    không ai viết vào `docs/api-contract.md` thì `--all` không thấy gì, và ở
    chế độ staged chỉ cần chuỗi path xuất hiện đâu đó trong file hợp đồng là
    qua. Nghĩa là bề mặt API có thể phình ra mà tài liệu đứng yên.

    Tầng `hard-ratchet` chứ không phải `hard`: đo 2026-08-05 có 367 route đọc
    được từ `agent/`, trong đó 297 chưa được hợp đồng nhắc tới. Bắt trả hết nợ
    đó ngay là không thực tế; ratchet giữ đúng tinh thần bộ chuẩn — nợ cũ đứng
    yên, route MỚI bắt buộc có mô tả.
    """

    name, level, rule = "api_contract_coverage", "hard-ratchet", "R20.5b"

    def _undocumented(self, contract: str) -> list[dict]:
        documented = set(CONTRACT_PATH_RE.findall(contract))
        missing = sorted(
            path for path in self._code_route_paths()
            if not any(_matches_any_route(entry, {path}) for entry in documented)
        )
        return [
            {"file": CONTRACT, "line": 0, "rule": self.rule,
             "msg": f"route {path} có trong agent/ nhưng {CONTRACT} không mô tả"}
            for path in missing
        ]

    def run(self, files: list[str] | None = None) -> dict:
        # Chỉ có nghĩa toàn cục: ở chế độ staged, R20.5 đã lo cặp route↔hợp đồng
        # cho đúng file đang commit.
        if files is not None:
            return self._result([])
        return self._result(self._undocumented(self._contract_text()))


CHECKS = [ApiContractCheck(), ApiContractCoverageCheck()]
