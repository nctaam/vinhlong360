"""Ranh giới của gói `agent/identity/` — lát thứ năm, CUỐI (2026-08-28).

Cùng khuôn community/: đổi-nhà một-một (auth.py đã là miền-đơn, chỉ 5 ký hiệu
bị ngoài import), không cắt bao đóng. Rủi ro không phải "cắt sót" mà là "shim
giả vờ là module thật" — bộ này khoá đúng các chỗ đó. Riêng lát này còn thêm
trục 4 gấp tám (23 fixture vá `auth.db`): phần đó khoá bằng đếm DB thật ở ba
mốc trong quy trình nghiệm thu, không khoá được bằng unit test.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from identity import api as identity_api  # noqa: E402

SRC = Path(identity_api.__file__).resolve()


def test_shim_va_module_that_dung_CUNG_mot_router():
    """server mount qua `auth.router`; test cũ soi cùng tên. Hai object router
    khác nhau = hai bảng route trôi khác nhau."""
    import auth

    assert auth.router is identity_api.router


def test_shim_chi_con_tai_xuat_khong_con_dinh_nghia():
    import auth

    tree = ast.parse(Path(auth.__file__).resolve().read_text(encoding="utf-8"))
    ten = [n.name for n in tree.body
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    assert ten == [], f"shim vẫn còn định nghĩa: {ten[:5]} — hai nguồn sự thật"


def test_nam_ky_hieu_duong_cu_van_song():
    """5 nơi ngoài import từ `auth` (đo 2026-08-28): chat_identity, notifications
    (2 chỗ), server, user_preferences. Đường cũ phải sống và CÙNG object."""
    from auth import (  # noqa: F401
        CONSENT_VERSION,
        _extract_token,
        _get_current_user_or_none,
        _hash_token,
        router,
    )
    import auth

    for ten in ("_extract_token", "_get_current_user_or_none", "_hash_token"):
        assert getattr(auth, ten) is getattr(identity_api, ten), ten


def test_KHONG_import_nguoc():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    XAU = ("server", "auth", "social", "community", "admin", "chat", "llmops",
           "entities")
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [a.name for a in n.names if a.name.split(".")[0] in XAU]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in XAU:
                bad.append(n.module)
    assert not bad, f"identity/api.py import xấu: {bad}"


def test_route_len_app_nguyen_ven():
    import server

    app_paths = {r.path for r in server.app.routes}
    thieu = [r.path for r in identity_api.router.routes if r.path not in app_paths]
    assert not thieu, f"route định danh không lên app: {thieu[:5]}"
