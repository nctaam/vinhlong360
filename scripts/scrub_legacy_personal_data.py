#!/usr/bin/env python3
"""Plan or explicitly apply the scoped legacy personal-data scrub.

The default is a read-only dry-run. Mutation needs both ``--apply`` and a
non-empty backup evidence file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from legacy_scrub import (  # noqa: E402
    BackupEvidenceRequired,
    ScrubError,
    apply_scrub_plan,
    build_scrub_plan,
    scrub_plan_summary,
    write_scrub_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(ROOT / "agent" / "data"),
        help="legacy data root (defaults to agent/data)",
    )
    parser.add_argument(
        "--owner-id",
        action="append",
        dest="owner_ids",
        required=True,
        help="exact owner key to scrub; repeat for a batch",
    )
    parser.add_argument("--apply", action="store_true", help="mutate after all safety gates pass")
    parser.add_argument("--backup-evidence", help="non-empty backup manifest/evidence file")
    parser.add_argument("--manifest", help="path for the apply manifest")
    args = parser.parse_args(argv)

    if args.apply and args.manifest and Path(args.manifest).exists():
        print("[scrub] manifest already exists; choose a new evidence path", file=sys.stderr)
        return 2

    try:
        plan = build_scrub_plan(args.root, owner_ids=args.owner_ids)
        if not args.apply:
            if args.manifest:
                parser.error("--manifest is only available with --apply")
            print(json.dumps(scrub_plan_summary(plan), sort_keys=True))
            return 0

        manifest = apply_scrub_plan(plan, backup_evidence=args.backup_evidence)
        if args.manifest:
            write_scrub_manifest(manifest, args.manifest)
        print(json.dumps(manifest.to_dict(), sort_keys=True))
        return 0
    except BackupEvidenceRequired as exc:
        print(f"[scrub] {exc}", file=sys.stderr)
        return 2
    except ScrubError as exc:
        print(f"[scrub] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[scrub] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
