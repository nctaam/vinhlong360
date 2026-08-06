# -*- coding: utf-8 -*-
"""Khoá tính khả chuyển cho MỌI script vận hành, không riêng installer.

Đợt 2026-08-06 có bảy bug sản phẩm chỉ hỏng trên Linux, và bốn trong số đó là
cùng một lớp: script viết trên máy Windows, chạy thật lần đầu trên môi trường
đích rồi mới lộ giả định nền tảng.

    scripts/ops/install_closed_release.sh   `env --argv0` đòi coreutils >= 9.1
    scripts/run_entity_status_stage_b.ps1   StartsWith("$root\") — nối cứng '\'
    scripts/release_gate.ps1                ghim cứng "powershell"
    tests/.../test_deploy_migration_prerequisite.py  ghim cứng đường Git Bash

`test_installer_portability.py` khoá từng ca riêng cho installer. File này quét
DIỆN RỘNG để một script ops MỚI không lặp lại đúng những cái bẫy đó. Test tĩnh,
không marker, nên chạy trong lệnh pytest mặc định — khác với nhóm
`subprocess_heavy` vốn bị `addopts` loại và chỉ tố giác ở CI sau ~28 phút.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _code_lines(path: Path) -> list[str]:
    """Bỏ dòng comment, và gộp dòng nối.

    Chú thích CÓ quyền nhắc tên cái bẫy để giải thích vì sao tránh nó — soi cả
    comment thì lời giải thích tự làm test đỏ.

    PowerShell nối dòng bằng backtick cuối dòng, bash bằng backslash. Không gộp
    thì một phép kiểm trải hai dòng bị đọc thành hai mảnh rời và báo nhầm — đúng
    cái đã xảy ra với bản vá separator ở run_entity_status_stage_b.ps1.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = raw.replace("`\n", " ").replace("\\\n", " ")
    out = []
    for line in raw.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("<#"):
            continue
        out.append(line)
    return out


def _ops_scripts(suffix: str) -> list[Path]:
    found = sorted(ROOT.joinpath("scripts").rglob(f"*{suffix}"))
    return [p for p in found if "node_modules" not in p.parts]


@pytest.mark.parametrize("script", _ops_scripts(".sh"), ids=lambda p: p.name)
def test_shell_script_khong_dung_co_coreutils_moi(script: Path):
    """`--argv0` chỉ có từ GNU coreutils 9.1 (2022).

    Ubuntu 22.04 dùng 8.32 và `env` từ chối thẳng, thoát 125. Dùng `builtin exec -a`
    của bash thay thế — xem install_closed_release.sh.
    """
    joined = "\n".join(_code_lines(script))
    assert "--argv0" not in joined, (
        f"{script.name}: `env --argv0` đòi coreutils >= 9.1; dùng `builtin exec -a`"
    )


@pytest.mark.parametrize("script", _ops_scripts(".ps1"), ids=lambda p: p.name)
def test_powershell_script_khong_ghim_cung_lenh_powershell(script: Path):
    """`powershell` chỉ có trên Windows; pwsh mới là bản cross-platform.

    Ghim cứng làm script chết trên Linux với "The term 'powershell' is not
    recognized". Cách đúng: `Get-Command pwsh, powershell | Select-Object -First 1`.
    """
    for line in _code_lines(script):
        if "Get-Command" in line:  # đã tra động → hợp lệ
            continue
        assert '"powershell"' not in line and "'powershell'" not in line, (
            f"{script.name}: ghim cứng 'powershell'; tra qua `Get-Command pwsh, powershell`"
        )


@pytest.mark.parametrize("script", _ops_scripts(".ps1"), ids=lambda p: p.name)
def test_powershell_script_khong_noi_cung_dau_phan_cach(script: Path):
    r"""So khớp đường dẫn phải nhận cả '/' — pwsh cũng chạy trên Linux.

    `StartsWith("$root\")` làm mọi đường dẫn con trượt trên Linux và script
    fail-closed. Nếu có nhánh '\' thì phải có nhánh '/' đi kèm.
    """
    for line in _code_lines(script):
        if "StartsWith(" not in line or "\\\"" not in line:
            continue
        assert '/"' in line, (
            f"{script.name}: StartsWith nối cứng '\\'; phải nhận cả '/' "
            f"(pwsh chạy trên Linux ở CI)"
        )


@pytest.mark.parametrize("script", _ops_scripts(".sh") + _ops_scripts(".ps1"),
                         ids=lambda p: p.name)
def test_script_ops_khong_ghim_duong_dan_windows(script: Path):
    """Đường dẫn ổ đĩa Windows trong script vận hành = chết trên VPS.

    Cho phép trong nhánh dò-nhiều-ứng-viên (có `Test-Path`/`-f `/`exists`), vì đó
    là fallback hợp lệ cho máy dev; cấm khi nó là giá trị dùng thẳng.
    """
    for line in _code_lines(script):
        if "C:\\" not in line and "C:/" not in line:
            continue
        if any(tok in line for tok in ("Test-Path", "exists", "-f ", "which", "Get-Command")):
            continue
        pytest.fail(f"{script.name}: ghim đường dẫn Windows ngoài nhánh dò ứng viên: {line.strip()[:80]}")
