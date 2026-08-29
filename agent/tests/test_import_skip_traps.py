"""Chống lớp lỗi "rào mất răng thì không kêu" — dạng ÊM NHẤT: skip im lặng.

Sáu chỗ trong bộ test bọc một import module DỰ ÁN trong `try/except` rồi
`pytest.skip(...)`. Ý định ban đầu hợp lý (đừng nổ khi thiếu phụ thuộc), nhưng
hệ quả là: ký hiệu bị DỜI CHỖ → import hỏng → test **bỏ qua im lặng**. Không
đỏ, không cảnh báo — chỉ một con số nhích lên trong dòng tổng kết.

Đã xảy ra thật 2026-08-27 khi bóc `agent/llmops/`: `GuardrailCheckRequest` và
`DynamicAgentCreateRequest` sang gói mới, và BẢY bài kiểm định Pydantic model
tắt lặng lẽ. Chỉ lộ ra vì có người hỏi "vì sao skipped tăng 510 → 517?".

Bộ này biến im lặng đó thành tiếng động: import THẲNG, không bọc. Ký hiệu nào
dời chỗ thì bài dưới đây ĐỎ ngay, kèm tên cụ thể.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.mark.parametrize(
    ("mo_ta", "module", "ten"),
    [
        ("test_server_models.py bọc", "server", "ChatRequest"),
        # FeedbackRequest về nhà thật chat.api 2026-08-29 (lát 9) — trỏ nhà
        # thật để khỏi nói dối; server.FeedbackRequest chỉ còn là tái xuất.
        ("test_server_models.py bọc", "chat.api", "FeedbackRequest"),
        ("test_server_models.py bọc (tái xuất)", "server", "FeedbackRequest"),
        ("test_server_models.py bọc", "llmops.api", "GuardrailCheckRequest"),
        ("test_server_models.py bọc", "llmops.api", "DynamicAgentCreateRequest"),
        ("test_admin.py + test_entity_schemas.py bọc", "admin", "EntityCreate"),
        ("test_admin.py bọc", "admin", "_sanitize"),
    ],
)
def test_ky_hieu_bi_boc_try_except_van_import_duoc(mo_ta, module, ten):
    mod = __import__(module, fromlist=[ten])
    assert hasattr(mod, ten), (
        f"{module}.{ten} không import được — {mo_ta} nó trong try/except rồi "
        f"pytest.skip, nên bài đó ĐANG TẮT LẶNG LẼ. Trỏ import sang nơi ký hiệu "
        f"thật sự sống, đừng để skip nuốt mất."
    )
