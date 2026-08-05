# -*- coding: utf-8 -*-
"""Ratchet docstring cho route công khai.

64 docstring được viết ngày 2026-08-06 đưa phụ lục `docs/api-contract.md` từ
39% lên 55% route có mô tả. Không có chốt chặn thì con số đó tụt dần: người thêm
route mới hiếm khi quay lại viết docstring, và phụ lục sinh tự động sẽ âm thầm
loãng đi.

Test này KHÔNG đòi 100% — nó chỉ giữ mức đã đạt cho 5 module công khai, đúng
tinh thần ratchet của bộ chuẩn: nợ cũ đứng yên, cái mới phải sạch.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys

import pytest

AGENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT_DIR))

# Import để R20.7 ghép được cặp file-đổi ↔ test (check_test_pairing đọc AST import).
import notifications  # noqa: E402,F401
import public_api  # noqa: E402,F401
import saved  # noqa: E402,F401
import seo  # noqa: E402,F401
import visits  # noqa: E402,F401

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# Số handler CÓ docstring tối thiểu, đo ngày 2026-08-06. Tăng được thì tăng;
# giảm là hồi quy.
FLOORS = {
    "public_api.py": 47,
    "notifications.py": 20,
    "seo.py": 8,
    "visits.py": 6,
    "saved.py": 4,
}


def _route_handlers(path: Path) -> list[tuple[str, bool]]:
    """[(tên handler, có docstring)] cho mọi hàm mang decorator HTTP."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    found: list[tuple[str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            func = deco.func
            if isinstance(func, ast.Attribute) and func.attr in HTTP_METHODS:
                found.append((node.name, ast.get_docstring(node) is not None))
                break
    return found


@pytest.mark.parametrize("filename,floor", sorted(FLOORS.items()))
def test_route_cong_khai_giu_muc_docstring_da_dat(filename, floor):
    handlers = _route_handlers(AGENT_DIR / filename)
    documented = [name for name, has_doc in handlers if has_doc]

    assert len(documented) >= floor, (
        f"{filename}: {len(documented)}/{len(handlers)} handler có docstring, "
        f"tụt dưới mức đã đạt ({floor}). Route mới phải có docstring — nó chảy "
        f"thẳng vào phụ lục docs/api-contract.md."
    )


def test_docstring_dong_dau_tu_dung_duoc_khi_tach_ngu_canh():
    """Dòng đầu bị `gen_route_appendix.py` rút vào bảng — không được rỗng hay quá dài."""
    qua_dai: list[str] = []
    for filename in FLOORS:
        tree = ast.parse((AGENT_DIR / filename).read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc = ast.get_docstring(node)
            if not doc or not any(
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr in HTTP_METHODS
                for d in node.decorator_list
            ):
                continue
            first = doc.strip().splitlines()[0].strip()
            assert first, f"{filename}::{node.name} có docstring nhưng dòng đầu rỗng"
            if len(first) > 160:
                qua_dai.append(f"{filename}::{node.name} ({len(first)} ký tự)")

    assert not qua_dai, "dòng đầu quá dài cho một ô bảng: " + ", ".join(qua_dai)
