# -*- coding: utf-8 -*-
"""Sinh phụ lục "bản đồ route" cho docs/api-contract.md từ AST của agent/.

R20.5b (thêm 2026-08-05) đo được 275/367 route trong `agent/` chưa hề được hợp
đồng nhắc tới. Viết tay từng cái vừa tốn vừa dễ sai; tệ hơn, mô tả do người
(hoặc LLM) đoán ra sẽ trôi khỏi code ngay lần refactor sau.

Phụ lục này lấy MỌI thông tin từ chính mã nguồn — method, path đã ghép prefix
router, tên handler, và dòng đầu docstring nếu có. Không có chỗ nào để bịa: cái
gì code không nói thì phụ lục để trống.

Chạy:
    python scripts/gen_route_appendix.py --dry-run
    python scripts/gen_route_appendix.py            # ghi vào docs/api-contract.md
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from checks.check_api_contract import (  # noqa: E402
    CONTRACT,
    CONTRACT_PATH_RE,
    HTTP_METHODS,
    ApiContractCheck,
    _matches_any_route,
)

ROOT = Path(__file__).resolve().parents[1]
MARKER_START = "<!-- ROUTE-APPENDIX:START — sinh bởi scripts/gen_route_appendix.py, đừng sửa tay -->"
MARKER_END = "<!-- ROUTE-APPENDIX:END -->"


def _first_docline(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    doc = ast.get_docstring(node) or ""
    line = doc.strip().splitlines()[0].strip() if doc.strip() else ""
    return line.replace("|", "\\|")


def _parse_route_file(path: Path) -> ast.Module | None:
    """Chỉ parse file thực sự khai route; trả None nếu không đọc/parse được."""
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    if "@router." not in source and "@app." not in source:
        return None
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _handler_routes(node, check, prefixes, consts) -> list[tuple[str, str, str, str]]:
    """Route khai bằng decorator trên MỘT handler."""
    found = []
    for deco in node.decorator_list:
        if not isinstance(deco, ast.Call) or not deco.args:
            continue
        func = deco.func
        if not isinstance(func, ast.Attribute) or func.attr not in HTTP_METHODS:
            continue
        route = check._decorator_path(deco, consts)
        if route is None:
            continue
        prefix = prefixes.get(getattr(func.value, "id", ""), "")
        found.append((func.attr.upper(), f"{prefix}{route}", node.name, _first_docline(node)))
    return found


def _routes_in_file(path: Path) -> list[tuple[str, str, str, str]]:
    """[(method, path, tên handler, dòng docstring đầu)] cho một file."""
    tree = _parse_route_file(path)
    if tree is None:
        return []

    check = ApiContractCheck(root=ROOT)
    prefixes = check._router_prefixes(tree)
    consts = check._module_constants(tree)

    found: list[tuple[str, str, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.extend(_handler_routes(node, check, prefixes, consts))
    return found


def collect() -> dict[str, list[tuple[str, str, str, str]]]:
    by_file: dict[str, list[tuple[str, str, str, str]]] = {}
    for path in sorted((ROOT / "agent").rglob("*.py")):
        if "/tests/" in path.as_posix() or "\\tests\\" in str(path):
            continue
        routes = _routes_in_file(path)
        if routes:
            by_file[path.relative_to(ROOT).as_posix()] = sorted(routes, key=lambda r: (r[1], r[0]))
    return by_file


def render(by_file: dict[str, list[tuple[str, str, str, str]]], documented: set[str]) -> str:
    total = sum(len(v) for v in by_file.values())
    lines = [
        MARKER_START,
        "",
        "## Phụ lục — bản đồ route đầy đủ",
        "",
        f"Sinh tự động từ AST của `agent/` bằng `scripts/gen_route_appendix.py` "
        f"({total} route trong {len(by_file)} module). Mọi thông tin dưới đây lấy trực tiếp "
        "từ mã nguồn: method, path đã ghép prefix của `APIRouter`, tên handler, và dòng đầu "
        "docstring nếu handler có. Ô mô tả trống nghĩa là **code chưa có docstring** — đó là "
        "chỗ đáng viết tiếp, không phải chỗ để đoán.",
        "",
        "Các mục ở phần trên tài liệu mới là hợp đồng có ràng buộc (shape dữ liệu, quy tắc, "
        "ví dụ). Phụ lục này chỉ bảo đảm **không route nào tồn tại mà tài liệu không biết** — "
        "đó là điều R20.5b đo.",
        "",
    ]
    for rel, routes in sorted(by_file.items()):
        new_count = sum(
            1 for _, path, _, _ in routes
            if not any(_matches_any_route(entry, {path}) for entry in documented)
        )
        suffix = f" · {new_count} chưa từng được nhắc" if new_count else ""
        lines.append(f"### `{rel}` ({len(routes)} route{suffix})")
        lines.append("")
        lines.append("| Method | Path | Handler | Mô tả (docstring) |")
        lines.append("|---|---|---|---|")
        for method, path, handler, doc in routes:
            lines.append(f"| {method} | `{path}` | `{handler}` | {doc} |")
        lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    by_file = collect()
    contract_path = ROOT / CONTRACT
    contract = contract_path.read_text(encoding="utf-8")
    documented = set(CONTRACT_PATH_RE.findall(contract))

    appendix = render(by_file, documented)
    total = sum(len(v) for v in by_file.values())
    missing = sum(
        1
        for routes in by_file.values()
        for _, path, _, _ in routes
        if not any(_matches_any_route(entry, {path}) for entry in documented)
    )
    print(f"{total} route trong {len(by_file)} module · {missing} chưa được hợp đồng nhắc")

    if MARKER_START in contract:
        head, _, rest = contract.partition(MARKER_START)
        _, _, tail = rest.partition(MARKER_END)
        updated = f"{head}{appendix}{tail}"
    else:
        updated = f"{contract.rstrip()}\n\n---\n\n{appendix}\n"

    if args.dry_run:
        print(f"[DRY] sẽ ghi {len(appendix.splitlines())} dòng phụ lục vào {CONTRACT}")
        return 0

    contract_path.write_text(updated, encoding="utf-8")
    print(f"[OK] đã ghi phụ lục vào {CONTRACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
