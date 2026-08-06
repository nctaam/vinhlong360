# -*- coding: utf-8 -*-
"""Khoá tính khả chuyển của `install_closed_release.sh` trên Linux đời cũ.

Bối cảnh: script này chạy trên VPS prod, nơi ta không chọn được phiên bản
coreutils. Ngày 2026-08-06 nó dùng `/usr/bin/env --argv0=…` — cờ CHỈ có từ GNU
coreutils 9.1 (2022). Trên coreutils 8.32 (Ubuntu 22.04, và cả Git Bash của máy
dev) `env` từ chối thẳng:

    /usr/bin/env: unrecognized option '--argv0=…'

`env` thoát 125, guard runtime bắt được và dịch thành
`python-executor-runtime-incompatible`, làm 183 test đỏ — và, nghiêm trọng hơn,
sẽ khiến installer KHÔNG BAO GIỜ chạy được trên VPS nào có coreutils cũ.

Chỗ này không tự lộ ở local: Windows đi nhánh `else` của `invoke_python`, không
chạm dòng Linux. Nên phải khoá bằng test tĩnh chứ không trông vào lần chạy thật.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "ops" / "install_closed_release.sh"


def _source() -> str:
    return INSTALLER.read_text(encoding="utf-8")


def _code_only() -> str:
    """Bỏ dòng comment trước khi soi.

    Chú thích trong script CÓ nhắc tên cờ để giải thích vì sao không dùng nó —
    soi cả comment thì lời giải thích tự làm test đỏ, và áp lực sẽ đổ sang việc
    xoá chú thích thay vì giữ code đúng.
    """
    return "\n".join(
        line for line in _source().splitlines() if not line.lstrip().startswith("#")
    )


def test_installer_khong_dung_co_env_chi_co_o_coreutils_moi():
    """`--argv0` đòi coreutils ≥ 9.1; VPS có thể chạy bản cũ hơn."""
    assert "--argv0" not in _code_only(), (
        "`env --argv0` chỉ có từ coreutils 9.1 — dùng `exec -a` (builtin bash) "
        "để chạy được trên Ubuntu 22.04 và các bản cũ hơn"
    )


def test_invoke_python_dat_argv0_bang_exec_a():
    """Vẫn phải đặt argv[0] — bỏ hẳn sẽ làm Python suy sai sys.prefix.

    Executor được ghim qua `/proc/<pid>/fd/<n>`; nếu argv[0] cũng là đường dẫn
    /proc đó thì Python mất manh mối để tìm prefix. `exec -a <logical>` giữ đúng
    ý định ban đầu mà không cần cờ mới của coreutils.
    """
    source = _source()
    assert 'exec -a "$PYTHON_EXECUTOR_LOGICAL" "$PYTHON_EXECUTOR"' in source, (
        "invoke_python phải đặt argv[0] về đường dẫn logical qua `exec -a`"
    )


def test_exec_a_nam_trong_subshell():
    """`exec` trần sẽ thay thế chính shell installer và giết phần còn lại."""
    source = _source()
    line = next(
        (ln for ln in source.splitlines() if "exec -a" in ln and "PYTHON_EXECUTOR" in ln),
        "",
    )
    stripped = line.strip()
    assert stripped.startswith("(") and stripped.endswith(")"), (
        f"dòng `exec -a` phải nằm trong subshell, thấy: {stripped!r}"
    )
