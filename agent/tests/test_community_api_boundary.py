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


def test_shim_va_module_that_dung_CUNG_mot_router():
    """72 chỗ test soi `social.router`; server mount qua social. Hai object
    router khác nhau = hai bảng route trôi khác nhau."""
    import social

    assert social.router is community_api.router


def test_shim_chi_con_tai_xuat_khong_con_dinh_nghia():
    import social

    tree = ast.parse(Path(social.__file__).resolve().read_text(encoding="utf-8"))
    ten = [n.name for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    assert ten == [], f"shim vẫn còn định nghĩa: {ten[:5]} — hai nguồn sự thật"


def test_hai_helper_sql_van_import_duoc_qua_duong_cu():
    """2 nơi ngoài import `_block_sql`/`_mute_sql` từ social — đường cũ phải sống."""
    from social import _block_sql, _mute_sql  # noqa: F401

    assert callable(getattr(community_api, "_block_sql"))
    assert social_is_same()


def social_is_same():
    import social

    return social._block_sql is community_api._block_sql


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
