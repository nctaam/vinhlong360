"""Ranh giới của `agent/moderation.py` — mục 8 đợt hoàn-thiện-sâu (2026-08-29).

moderation.py là DỊCH VỤ LÁ: không router, được community.api / identity.api /
admin_common gọi vào. File vốn một-miền-một-việc nên không cần đóng gói —
cái thiếu duy nhất là rào đồng phục với 9 gói kia: chiều import phải một
chiều (miền → moderation, không bao giờ ngược), và bộ ký hiệu công khai mà
consumer đang dựa vào phải sống. Hành vi fail-closed đã có suite riêng
(test_moderation_fail_closed.py) — file này chỉ canh CẤU TRÚC.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import moderation  # noqa: E402

SRC = Path(moderation.__file__).resolve()


def test_KHONG_import_nguoc_dich_vu_la():
    """Dịch vụ lá mà import ngược lên tầng route/miền là vòng chờ sẵn."""
    XAU = ("server", "admin", "public_api", "chat", "community", "identity",
           "entities", "llmops", "itineraries", "cases", "notifications")
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [a.name for a in n.names if a.name.split(".")[0] in XAU]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in XAU:
                bad.append(n.module)
    assert not bad, f"moderation.py import ngược: {bad}"


def test_bo_ky_hieu_consumer_dang_dua_vao():
    """Đo 2026-08-29: community.api / identity.api / admin_common import đúng
    ba tên này — đổi tên/xoá là gãy ba miền cùng lúc."""
    for ten in ("moderate_content", "moderate_content_enhanced", "log_moderation"):
        assert callable(getattr(moderation, ten)), ten
