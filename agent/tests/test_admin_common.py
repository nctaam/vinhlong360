"""Hợp đồng của hạ tầng ADMIN dùng chung (`agent/admin_common.py`).

Tách khỏi `admin.py` 2026-08-28 (bước 2a): `_sync_kb`(12 nơi gọi),
`_log_mod_action`(20), `_mask`(6) bị KẸT GIỮA miền entity-admin sắp bóc và phần
còn lại. Vì cả hai bên dùng, đổi hành vi ở đây là đổi cho cả hai.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import admin_common  # noqa: E402


def test_mask_che_so_giua_giu_dau_cuoi():
    """Che số là RÀO RIÊNG TƯ — claims list từng là nơi DUY NHẤT trả số thô."""
    ra = admin_common._mask("0912345678")
    assert ra != "0912345678"
    assert "1234" not in ra, "phần giữa của số vẫn lộ"


def test_mask_khong_no_voi_input_ngan():
    for xau in ("", "09", "abc"):
        admin_common._mask(xau)  # không được ném


def test_registry_cache_la_mot_object_voi_admin():
    """`admin.py` tái xuất registry; nếu hai bên giữ HAI list khác nhau thì
    `_invalidate_admin_caches` xoá một nửa số cache — im lặng."""
    import admin

    assert admin._admin_volatile_caches is admin_common._admin_volatile_caches
    assert admin._sync_kb is admin_common._sync_kb


def test_invalidate_xoa_du_lieu_moi_cache_da_dang_ky():
    cache = {"ts": 1.0, "data": ["x"]}
    admin_common._admin_volatile_caches.append(cache)
    try:
        admin_common._invalidate_admin_caches()
        assert cache["data"] is None
    finally:
        admin_common._admin_volatile_caches.remove(cache)


def test_sync_kb_lam_tuoi_kb_va_xoa_cache_llm():
    """B2 của rào cũ: sửa entity xong phải làm tươi KB *và* xoá cache LLM —
    thiếu vế sau là chat trả lời bằng dữ liệu đã sửa-mất."""
    import ast

    src = Path(admin_common.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_sync_kb")
    called = {n.func.attr for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "invalidate_all" in called
