"""
Test discover_province._reload_knowledge_index — nạp lại chỉ mục sau khi ghi provisional.

Hàm này từng gọi `scheduler.sync_data_json_to_js()` TRƯỚC `knowledge.reload()`.
Bản sinh `web/data.js` đã được gỡ (2026-08-22, không còn ai đọc), nên coupling đó
biến mất. Vì cả thân hàm nằm trong một `try/except Exception`, một lời gọi hỏng ở
đầu sẽ **nuốt luôn** phần nạp lại phía sau mà không ai thấy — nên bài test dưới
đây kiểm bằng HÀNH VI (reload có chạy không) chứ không so chuỗi mã nguồn.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discover_province
from discover_province import _reload_knowledge_index


class _FakeKnowledge:
    def __init__(self):
        self.reload_calls = 0

    def reload(self):
        self.reload_calls += 1


class _ExplodingScheduler:
    """Mọi truy cập thuộc tính đều nổ — đứng thế chỗ module scheduler."""

    def __getattr__(self, name):
        raise AssertionError(f"_reload_knowledge_index khong duoc cham scheduler.{name}")


def test_reload_chay_du_scheduler_co_no_hay_khong(monkeypatch):
    """Không còn phụ thuộc scheduler: reload vẫn chạy dù scheduler hỏng hoàn toàn."""
    fake = _FakeKnowledge()
    monkeypatch.setitem(sys.modules, "knowledge", fake)
    monkeypatch.setitem(sys.modules, "scheduler", _ExplodingScheduler())

    _reload_knowledge_index()

    assert fake.reload_calls == 1


def test_loi_khi_reload_khong_lan_ra_ngoai(monkeypatch):
    """Hợp đồng cũ được giữ: lỗi nạp lại chỉ ghi log, không làm hỏng vòng phát hiện."""

    class _Broken:
        def reload(self):
            raise RuntimeError("index hong")

    monkeypatch.setitem(sys.modules, "knowledge", _Broken())

    _reload_knowledge_index()  # không được ném


def test_module_khong_con_tham_chieu_bo_sinh_data_js():
    """Chặn tái nhiễm: cái tên đã gỡ không được quay lại dưới dạng lời gọi."""
    source = Path(discover_province.__file__).read_text(encoding="utf-8")
    dead_call = "sync_data_json" + "_to_js()"
    assert dead_call not in source
