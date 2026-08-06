# -*- coding: utf-8 -*-
"""Lấy TRỌN thân một hàm từ source, thay cho kiểu cắt cửa sổ ký tự cố định.

Nhiều test structure trong repo viết dạng:

    idx = src.index("def merge_saved")
    fn_src = src[idx:idx + 500]
    assert "pg_advisory_xact_lock" in fn_src

Kiểu này hỏng theo hai chiều, và cả hai đều đã xảy ra thật:

- HỤT: thêm docstring hợp lệ vào đầu hàm đẩy phần cần kiểm ra ngoài khung —
  19 test đỏ cùng lúc ngày 2026-08-06 dù không dòng logic nào đổi. Trước đó
  `test_structured_logger_has_warning_alias` cũng đỏ đúng vì lý do này.
- THỪA: 500 ký tự có thể tràn sang hàm KẾ TIẾP, nên assert vẫn xanh nhờ nội
  dung của hàm khác — âm thầm mất tác dụng bảo vệ.

`function_source` cắt theo ranh giới AST thật nên không hụt cũng không tràn.
"""
from __future__ import annotations

import ast


def function_source(module_src: str, name: str) -> str:
    """Trả nguyên văn thân hàm `name` (kể cả nested/async), gồm cả decorator.

    `name` khớp theo tên hàm, không phải chuỗi "def name" — nên đổi chữ ký hàm
    không làm test vỡ vì lý do sai.
    """
    tree = ast.parse(module_src)
    lines = module_src.splitlines(keepends=True)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != name:
            continue
        start = node.lineno - 1
        if node.decorator_list:
            start = min(start, node.decorator_list[0].lineno - 1)
        return "".join(lines[start:node.end_lineno])

    raise AssertionError(f"không tìm thấy hàm {name!r} trong source")
