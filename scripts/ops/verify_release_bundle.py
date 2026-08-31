#!/usr/bin/env python3
"""Verify a versioned release evidence bundle without mutating it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.control_plane.evidence import verify_bundle  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args(argv)
    result = verify_bundle(args.bundle)
    print(
        json.dumps(
            {
                "verdict": result.verdict,
                "reasons": list(result.reasons),
                "checked_sha256": result.checked_sha256,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return {"PASS": 0, "BLOCKED": 2, "UNCLASSIFIED": 3}[result.verdict]


if __name__ == "__main__":
    raise SystemExit(main())

