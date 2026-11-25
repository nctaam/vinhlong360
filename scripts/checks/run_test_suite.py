# -*- coding: utf-8 -*-
"""Run decoupled Core Platform tests vs Province Data tests."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _build_commands(suite: str, scope: str, passthrough: list[str]) -> list[tuple[list[str], Path]]:
    commands: list[tuple[list[str], Path]] = []
    if scope in ("backend", "all"):
        if suite == "core":
            marker_expr = (
                "not province_data and not slow and not integration "
                "and not entity_status_postgres and not subprocess_heavy"
            )
        else:
            marker_expr = "province_data"
        commands.append(
            ([sys.executable, "-m", "pytest", "-q", "-m", marker_expr, *passthrough], ROOT)
        )

    if scope in ("frontend", "all"):
        npm_cmd = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        script_name = "test:core" if suite == "core" else "test:province"
        fe_cmd = [npm_cmd, "run", script_name]
        if passthrough:
            fe_cmd.extend(["--", *passthrough])
        commands.append((fe_cmd, ROOT / "web-nuxt"))
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run core or province test suites.")
    parser.add_argument("--suite", choices=("core", "province"), required=True)
    parser.add_argument("--scope", choices=("backend", "frontend", "all"), default="all")
    parser.add_argument("--dry-run", action="store_true")
    args, passthrough = parser.parse_known_args(argv)

    commands = _build_commands(args.suite, args.scope, passthrough)
    for cmd, cwd in commands:
        rel_cwd = cwd.relative_to(ROOT).as_posix() if cwd != ROOT else "."
        print(f"[{rel_cwd}] {' '.join(cmd)}")
        if not args.dry_run:
            result = subprocess.run(cmd, cwd=cwd)
            if result.returncode != 0:
                return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
