"""Hợp đồng của POST /reload: nạp lại trong bộ nhớ, KHÔNG xuất file.

/reload từng gọi thêm một bộ xuất để sinh `web/data.js`. File đó đã gỡ
(2026-08-22, `8afdbfb0` — không còn ai đọc), nên handler giờ chỉ nạp lại tri thức,
dọn cache và dựng lại index.

Hai lời hứa dưới đây từng LỆCH nhau mà không test nào bắt: docstring module vẫn
quảng cáo "data sync" sau khi lời gọi sync đã bị gỡ. Người vận hành đọc docstring
sẽ trông đợi một tác dụng phụ không còn tồn tại. Tài liệu sai kiểu đó nguy hơn mã
sai, vì mã sai thì test đỏ còn tài liệu sai thì người ta làm theo.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server


def test_reload_khong_con_ghi_file_nao():
    """Hành vi: handler chỉ nạp/dọn cache, không có đường ghi ra đĩa."""
    source = inspect.getsource(server.reload_data)
    dead_export = "sync_data_json" + "_to_js"
    for forbidden in (dead_export, "export_data", "write_text", "open(", ".write("):
        assert forbidden not in source, (
            f"/reload không được ghi file, nhưng thân hàm có {forbidden!r}"
        )


def test_docstring_module_khong_con_hua_data_sync_cho_reload():
    """Tài liệu phải khớp hành vi: bỏ lời gọi sync thì bỏ luôn lời hứa sync."""
    doc = server.__doc__ or ""
    lines = [line for line in doc.splitlines() if "/reload" in line]
    assert lines, "docstring module phải còn liệt kê /reload"
    for line in lines:
        assert "sync" not in line.lower(), (
            f"docstring còn hứa sync cho /reload ({line.strip()!r}), nhưng lời gọi "
            "sync đã gỡ 2026-08-22. Sửa docstring hoặc trả lại hành vi — đừng để lệch."
        )
