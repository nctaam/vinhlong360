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


def test_duong_cu_auth_da_chet_han():
    """Gỡ shim 2026-08-29 (lệnh "làm luôn"): `import auth` phẳng phải nổ —
    không shim, không file rơi rớt, không bản-sao-globals nào còn tồn tại."""
    import importlib
    import sys

    assert "auth" not in sys.modules or sys.modules["auth"].__name__ == "identity.api"
    try:
        importlib.import_module("auth")
    except ModuleNotFoundError:
        return
    raise AssertionError("đường phẳng `import auth` vẫn sống — còn file cũ/shim")


def test_nam_ky_hieu_duong_cu_van_song():
    """5 ký hiệu công khai của miền (đo 2026-08-28) phải import được từ nhà
    thật — sau khi gỡ shim, identity.api LÀ đường duy nhất."""
    from identity.api import (  # noqa: F401
        CONSENT_VERSION,
        _extract_token,
        _get_current_user_or_none,
        _hash_token,
        router,
    )


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
