# -*- coding: utf-8 -*-
"""Rào cho `scripts/install_hooks.py` — lệnh cài cổng tiêu chuẩn ở CLAUDE.md §5.

Vì sao cần rào: script in tiếng Việt ("CÀI XONG…", "OK: hook đã cài", "Hook cũ →").
Console Windows mặc định cp1252 không mã hoá được chữ "đ" (U+0111) → `print` ném
UnicodeEncodeError SAU KHI hook đã ghi xong, script thoát 1. Người làm theo §5 thấy
mã lỗi sẽ tưởng cổng tiêu chuẩn chưa cài và có thể bỏ qua nó — đúng thứ mà cổng
sinh ra để chặn. Bản vá `_utf8_output()` từng bị bỏ quên trên một nhánh khác suốt
12 ngày vì không có test nào giữ nó; đây là cái rào đó.

Test chạy script trong MỘT REPO GIT TẠM (không phải repo thật) nên không đụng
`.git/hooks/pre-commit` của máy.
"""
from __future__ import annotations

import ast
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

try:  # import cấp module để R20.7 ghép được test ↔ script (AST thấy import)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import install_hooks
except Exception:  # pragma: no cover - script không import được thì test dưới tự đỏ
    install_hooks = None

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_hooks.py"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    return repo


def _run(repo: Path, encoding: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = encoding
    env.pop("PYTHONUTF8", None)  # đừng để -X utf8 của phiên cha che mất lỗi
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, env=env,
                          capture_output=True, text=True, errors="replace")


@pytest.mark.parametrize("encoding", ["cp1252", "ascii", "utf-8"])
def test_cai_moi_thoat_0_du_console_khong_ma_hoa_duoc_tieng_viet(temp_repo, encoding):
    """Nhánh in thứ nhất: cài mới ("CÀI XONG")."""
    res = _run(temp_repo, encoding)
    hook = temp_repo / ".git" / "hooks" / "pre-commit"
    assert res.returncode == 0, f"console {encoding} làm script thoát {res.returncode}: {res.stderr[-400:]}"
    assert hook.exists()
    assert install_hooks.MARKER in hook.read_text(encoding="utf-8")


@pytest.mark.parametrize("encoding", ["cp1252", "ascii"])
def test_chay_lai_lan_hai_van_thoat_0(temp_repo, encoding):
    """Nhánh in thứ hai: idempotent ("OK: hook đã cài") — chữ 'đã' là chỗ vỡ."""
    assert _run(temp_repo, encoding).returncode == 0
    res = _run(temp_repo, encoding)
    assert res.returncode == 0, f"lần chạy lại thoát {res.returncode}: {res.stderr[-400:]}"


@pytest.mark.parametrize("encoding", ["cp1252", "ascii"])
def test_co_hook_cu_thi_sao_luu_va_van_thoat_0(temp_repo, encoding):
    """Nhánh in thứ ba: hook lạ có sẵn ("Hook cũ →") — cả 'ũ' lẫn '→' đều vỡ."""
    hook = temp_repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\necho hook-cu-cua-nguoi-khac\n", encoding="utf-8")

    res = _run(temp_repo, encoding)

    assert res.returncode == 0, f"nhánh sao lưu thoát {res.returncode}: {res.stderr[-400:]}"
    backup = hook.with_suffix(".backup")
    assert backup.exists(), "hook cũ phải được giữ lại, không được đè mất"
    assert "hook-cu-cua-nguoi-khac" in backup.read_text(encoding="utf-8")
    assert install_hooks.MARKER in hook.read_text(encoding="utf-8")


def test_utf8_output_la_viec_dau_tien_trong_main():
    """Neo theo Ý ĐỊNH, không theo dòng: mọi `print` phải nằm SAU khi đã đổi encoding.

    Nếu ai đó chèn một `print` chẩn đoán lên trước `_utf8_output()`, lỗi cũ quay lại
    y nguyên mà ba test trên vẫn có thể xanh (chúng chỉ đo mã thoát cuối cùng).
    """
    tree = ast.parse(inspect.getsource(install_hooks.main))
    body = tree.body[0].body
    first = next(st for st in body if not isinstance(st, ast.Expr)
                 or not isinstance(st.value, ast.Constant))  # bỏ qua docstring
    assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Call), (
        "câu lệnh đầu tiên của main() phải là một lời gọi"
    )
    assert getattr(first.value.func, "id", None) == "_utf8_output", (
        "main() phải gọi _utf8_output() TRƯỚC mọi thứ khác"
    )
