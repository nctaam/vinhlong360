#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cài pre-commit hook chạy bộ check tiêu chuẩn (SP1). Idempotent.

  python scripts/install_hooks.py
"""
import stat
import subprocess
import sys
from pathlib import Path

MARKER = "# vl360-hooks v1"
HOOK = f"""#!/bin/sh
{MARKER}
python scripts/checks/run_hard.py --staged || exit 1
"""


def main() -> int:
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True, check=True).stdout.strip())
    hook_path = root / ".git" / "hooks" / "pre-commit"
    if hook_path.exists() and MARKER in hook_path.read_text(encoding="utf-8", errors="replace"):
        print(f"OK: hook đã cài ({hook_path})")
        return 0
    if hook_path.exists():
        backup = hook_path.with_suffix(".backup")
        hook_path.replace(backup)
        print(f"Hook cũ → {backup}")
    hook_path.write_text(HOOK, encoding="utf-8", newline="\n")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
    print(f"CÀI XONG: {hook_path} — mọi commit sẽ qua run_hard --staged (<5s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
