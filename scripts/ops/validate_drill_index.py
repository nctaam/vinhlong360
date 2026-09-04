#!/usr/bin/env python3
"""Validate the runtime-drill evidence index against its own stated contract.

`artifacts/runtime-drills/index.json` declares `schema_version: 1`, but until
now nothing in the repository read it: no schema, no validator, no producer.
An index nobody checks is exactly where evidence drift hides — a path that no
longer exists, a scope quietly widened toward "staging", two evidence entries
that are the same file counted twice, or a drill directory left on disk with
nothing recording that it failed.

What this validator does NOT do is judge whether a drill's verdict is
*correct*.  It checks that each claim is well-formed, that every artifact it
points at exists, and that the index does not overstate its own reach.  A PASS
here means the bookkeeping is honest, never that the system is ready.

Exit code is 0 only when every entry validates.  Any violation exits 2, so this
can never be mistaken for a release gate that went green.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Statuses an entry may carry.  Closed on purpose: a new status must be added
# here deliberately, not invented at the point of writing an artifact.
ALLOWED_STATUSES = frozenset(
    {
        "PASS_LIMITED",
        "PASS_LOCAL_BUILD",
        "INVALID_MEASUREMENT",
        "FAIL",
        "BLOCKED",
        "UNAVAILABLE",
    }
)

# Every scope token must be local-only.  These substrings are what a scope must
# never claim from a laptop drill.
FORBIDDEN_SCOPE_TOKENS = ("STAGING", "PRODUCTION", "PROD", "LIVE")

# A drill that never ran has nothing to scope and nothing to evidence; it
# carries `missing` instead.  That is an accepted schema variant rather than a
# hole — but only for this status.
STATUS_WITHOUT_EVIDENCE = "UNAVAILABLE"


def _iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_entry(entry: dict[str, Any], root: Path) -> list[str]:
    problems: list[str] = []
    entry_id = entry.get("id") or "<no id>"

    if not entry.get("id"):
        problems.append("entry has no id")

    status = entry.get("status")
    if not status:
        problems.append(f"{entry_id}: no status")
    elif status not in ALLOWED_STATUSES:
        problems.append(
            f"{entry_id}: status {status!r} is not one of {sorted(ALLOWED_STATUSES)}"
        )

    # An executed drill must say how far its claim reaches.  An UNAVAILABLE one
    # never ran, so demanding a scope would only invite an invented string.
    if status != STATUS_WITHOUT_EVIDENCE:
        scope = entry.get("scope")
        if not scope:
            problems.append(f"{entry_id}: executed entry has no scope")
        else:
            upper = str(scope).upper()
            for token in FORBIDDEN_SCOPE_TOKENS:
                if token in upper:
                    problems.append(
                        f"{entry_id}: scope {scope!r} claims {token} reach; "
                        "drill evidence here is local-only"
                    )
            if not upper.startswith("LOCAL"):
                problems.append(
                    f"{entry_id}: scope {scope!r} does not start with LOCAL"
                )

    # Every entry must carry a stated limit, whatever its shape.
    if not any(entry.get(field) for field in ("limitations", "missing", "reason")):
        problems.append(
            f"{entry_id}: carries none of limitations/missing/reason — "
            "an entry must state what it does not prove"
        )

    evidence = entry.get("evidence") or []
    if status != STATUS_WITHOUT_EVIDENCE and not evidence:
        problems.append(f"{entry_id}: executed entry lists no evidence path")

    # Keyed by (basename, digest), not digest alone.  A before/after pair is
    # SUPPOSED to be byte-identical when nothing changed — that is the proof,
    # not a defect.  What inflates apparent breadth is the SAME document reached
    # by two paths, which shows up as an equal basename AND an equal digest.
    seen: dict[tuple[str, str], str] = {}
    for rel in evidence:
        path = root / rel
        if not path.is_file():
            problems.append(f"{entry_id}: evidence path does not exist: {rel}")
            continue
        key = (path.name, _sha256(path))
        if key in seen:
            problems.append(
                f"{entry_id}: evidence {rel} is the same document as "
                f"{seen[key]} — the entry lists more documents than it has"
            )
        else:
            seen[key] = rel

    return problems


def validate(root: Path) -> dict[str, Any]:
    index_path = root / "artifacts" / "runtime-drills" / "index.json"
    if not index_path.is_file():
        return {
            "index": str(index_path),
            "problems": ["index.json does not exist"],
            "entry_count": 0,
            "orphan_directories": [],
        }

    index = json.loads(index_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    entries = index.get("entries") or []
    if not entries:
        problems.append("index declares no entries")

    seen_ids: set[str] = set()
    for entry in entries:
        entry_id = entry.get("id")
        if entry_id in seen_ids:
            problems.append(f"duplicate entry id: {entry_id}")
        seen_ids.add(entry_id)
        problems.extend(_validate_entry(entry, root))

    # The index must not claim to be older than the evidence it cites: a
    # generated_at left behind after a hand edit is how an index silently stops
    # describing the run it names.
    generated_at = _iso(str(index.get("generated_at", "")))
    if generated_at is None:
        problems.append("generated_at is missing or not an ISO-8601 timestamp")
    else:
        for entry in entries:
            for rel in entry.get("evidence") or []:
                path = root / rel
                if not path.is_file():
                    continue
                mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if mtime > generated_at:
                    problems.append(
                        f"{entry.get('id')}: evidence {rel} is newer than the "
                        f"index generated_at ({index.get('generated_at')})"
                    )

    # A drill directory nobody references is an unrecorded run.  Report it —
    # never delete it; those directories are the only trace of earlier attempts.
    drills = root / "artifacts" / "runtime-drills"
    referenced: set[str] = set()
    for entry in entries:
        for rel in entry.get("evidence") or []:
            parts = Path(rel).parts
            if len(parts) >= 3:
                referenced.add(parts[2])
    orphans = sorted(
        child.name
        for child in drills.iterdir()
        if child.is_dir() and child.name not in referenced
    )
    for name in orphans:
        problems.append(f"drill directory referenced by no entry: {name}")

    return {
        "index": str(index_path),
        "entry_count": len(entries),
        "orphan_directories": orphans,
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    report = validate(args.root)
    print(
        json.dumps(
            {
                "index": report["index"],
                "entries": report["entry_count"],
                "orphan_directories": report["orphan_directories"],
                "problem_count": len(report["problems"]),
                "problems": report["problems"],
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not report["problems"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
