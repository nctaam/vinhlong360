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


def _validate_entry_identity(entry: dict[str, Any], entry_id: str) -> list[str]:
    problems: list[str] = []
    if not entry.get("id"):
        problems.append("entry has no id")
    status = entry.get("status")
    if not status:
        problems.append(f"{entry_id}: no status")
    elif status not in ALLOWED_STATUSES:
        problems.append(
            f"{entry_id}: status {status!r} is not one of {sorted(ALLOWED_STATUSES)}"
        )
    return problems


def _validate_entry_scope(entry: dict[str, Any], entry_id: str) -> list[str]:
    if entry.get("status") == STATUS_WITHOUT_EVIDENCE:
        return []
    scope = entry.get("scope")
    if not scope:
        return [f"{entry_id}: executed entry has no scope"]
    upper = str(scope).upper()
    problems = [
        f"{entry_id}: scope {scope!r} claims {token} reach; drill evidence here is local-only"
        for token in FORBIDDEN_SCOPE_TOKENS
        if token in upper
    ]
    if not upper.startswith("LOCAL"):
        problems.append(f"{entry_id}: scope {scope!r} does not start with LOCAL")
    return problems


def _validate_entry_evidence(entry: dict[str, Any], entry_id: str, root: Path) -> list[str]:
    evidence = entry.get("evidence") or []
    problems: list[str] = []
    if entry.get("status") != STATUS_WITHOUT_EVIDENCE and not evidence:
        problems.append(f"{entry_id}: executed entry lists no evidence path")
    seen: dict[tuple[str, str], str] = {}
    for rel in evidence:
        path = root / rel
        if not path.is_file():
            problems.append(f"{entry_id}: evidence path does not exist: {rel}")
            continue
        key = (path.name, _sha256(path))
        if key in seen:
            problems.append(
                f"{entry_id}: evidence {rel} is the same document as {seen[key]} — "
                "the entry lists more documents than it has"
            )
        else:
            seen[key] = rel
    return problems


def _validate_entry(entry: dict[str, Any], root: Path) -> list[str]:
    entry_id = entry.get("id") or "<no id>"
    problems = _validate_entry_identity(entry, entry_id)
    problems.extend(_validate_entry_scope(entry, entry_id))

    # Every entry must carry a stated limit, whatever its shape.
    if not any(entry.get(field) for field in ("limitations", "missing", "reason")):
        problems.append(
            f"{entry_id}: carries none of limitations/missing/reason — "
            "an entry must state what it does not prove"
        )

    problems.extend(_validate_entry_evidence(entry, entry_id, root))
    return problems


def _validate_entries(entries: list[dict[str, Any]], root: Path) -> list[str]:
    problems: list[str] = []
    seen_ids: set[str] = set()
    for entry in entries:
        entry_id = entry.get("id")
        if entry_id in seen_ids:
            problems.append(f"duplicate entry id: {entry_id}")
        seen_ids.add(entry_id)
        problems.extend(_validate_entry(entry, root))
    return problems


def _validate_evidence_freshness(entries: list[dict[str, Any]], root: Path,
                                 generated_at: datetime | None, raw_generated: str) -> list[str]:
    if generated_at is None:
        return ["generated_at is missing or not an ISO-8601 timestamp"]
    problems: list[str] = []
    for entry in entries:
        for rel in entry.get("evidence") or []:
            path = root / rel
            if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) > generated_at:
                problems.append(
                    f"{entry.get('id')}: evidence {rel} is newer than the index generated_at ({raw_generated})"
                )
    return problems


def _orphan_drills(entries: list[dict[str, Any]], drills: Path) -> tuple[list[str], list[str]]:
    referenced = {
        Path(rel).parts[2]
        for entry in entries
        for rel in entry.get("evidence") or []
        if len(Path(rel).parts) >= 3
    }
    orphans = sorted(child.name for child in drills.iterdir() if child.is_dir() and child.name not in referenced)
    return orphans, [f"drill directory referenced by no entry: {name}" for name in orphans]


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
    entries = index.get("entries") or []
    drills = root / "artifacts" / "runtime-drills"
    problems = (["index declares no entries"] if not entries else [])
    problems.extend(_validate_entries(entries, root))
    raw_generated = str(index.get("generated_at", ""))
    problems.extend(_validate_evidence_freshness(entries, root, _iso(raw_generated), raw_generated))
    orphans, orphan_problems = _orphan_drills(entries, drills)
    problems.extend(orphan_problems)

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
