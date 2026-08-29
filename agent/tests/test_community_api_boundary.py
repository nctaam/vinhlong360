"""Ranh giới của gói `agent/community/` — lát thứ tư (2026-08-28).

Lát này KHÁC ba lát trước: đổi-nhà một-một (social.py đã là miền-đơn, chỉ 3 ký
hiệu bị ngoài import), không cắt bao đóng. Rủi ro vì thế cũng khác — không phải
"cắt sót" mà là "shim giả vờ là module thật". Bộ này khoá đúng các chỗ đó.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from community import api as community_api  # noqa: E402

SRC = Path(community_api.__file__).resolve()


def test_duong_cu_social_da_chet_han():
    """Gỡ shim 2026-08-29 (lệnh "làm luôn"): `import social` phẳng phải nổ —
    không shim, không file rơi rớt, không bản-sao-globals nào còn tồn tại."""
    import importlib
    import sys

    assert "social" not in sys.modules or sys.modules["social"].__name__ == "community.api"
    try:
        importlib.import_module("social")
    except ModuleNotFoundError:
        return
    raise AssertionError("đường phẳng `import social` vẫn sống — còn file cũ/shim")


def test_hai_helper_sql_import_duoc_tu_nha_that():
    """2 nơi ngoài từng import `_block_sql`/`_mute_sql` — sau gỡ shim,
    community.api là đường duy nhất và phải giữ hai ký hiệu này."""
    from community.api import _block_sql, _mute_sql  # noqa: F401

    assert callable(_block_sql) and callable(_mute_sql)


def test_KHONG_import_nguoc():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    # `public_api` KHÔNG nằm trong danh sách cấm: social.py cũ vốn import nó
    # (chiều social→public_api, không vòng — public_api không import social).
    # Đây là phụ thuộc CÓ SẴN đi theo cú đổi-nhà nguyên văn; siết nó là việc
    # tách tầng tương lai, không phải điều kiện của lát này.
    XAU = ("server", "social", "admin", "chat", "llmops", "entities")
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [a.name for a in n.names if a.name.split(".")[0] in XAU]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in XAU:
                bad.append(n.module)
    assert not bad, f"community/api.py import xấu: {bad}"


def test_route_len_app_nguyen_ven():
    import server

    app_paths = {r.path for r in server.app.routes}
    thieu = [r.path for r in community_api.router.routes if r.path not in app_paths]
    assert not thieu, f"route cộng đồng không lên app: {thieu[:5]}"
