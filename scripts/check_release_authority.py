#!/usr/bin/env python3
"""Check release authority, freshness and audit durability for a checkout."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.control_plane.authority import check_authority  # noqa: E402


def _head_sha(root: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = check_authority(root, datetime.now(tz=UTC), _head_sha(root))
    print(f"{report.status} tracked={len(report.tracked_artifacts)} stale={len(report.expired_documents)} mismatches={len(report.mismatches)}")
    for reason in report.mismatches:
        print(f"- {reason}", file=sys.stderr)
    for path in report.expired_documents:
        print(f"- expired document: {path}", file=sys.stderr)
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
