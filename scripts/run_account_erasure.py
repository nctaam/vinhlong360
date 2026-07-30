#!/usr/bin/env python3
"""Run account erasure in audit-only mode unless all activation gates are explicit."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from erasure import erase_due_accounts  # noqa: E402


UTC = timezone.utc


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _backup_evidence(path: str | None) -> bool:
    return bool(path) and Path(path).is_file()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--backup-evidence", help="path to a completed backup manifest")
    parser.add_argument("--limit", type=int, help="required explicit mutation batch size (1..50)")
    args = parser.parse_args(argv)

    if args.activate:
        if not _backup_evidence(args.backup_evidence):
            print("[erasure] --activate requires --backup-evidence pointing to a file", file=sys.stderr)
            return 2
        if args.limit is None or not 1 <= args.limit <= 50:
            print("[erasure] --activate requires --limit between 1 and 50", file=sys.stderr)
            return 2
        audit_only = False
        limit = args.limit
    else:
        audit_only = True
        limit = 50 if args.limit is None else args.limit
        if not 1 <= limit <= 50:
            print("[erasure] --limit must be between 1 and 50", file=sys.stderr)
            return 2

    result = erase_due_accounts(now=_utc_now(), limit=limit, audit_only=audit_only)
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
