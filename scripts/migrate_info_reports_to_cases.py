"""Migrate legacy reports.jsonl into the case kernel — dry-run first, always.

Four commands, nothing else:

  scan                     read-only walk; prints the classification report
  shadow-import            writes the ledger (and later, cases); gated
  reconcile                count algebra + checksum against the ledger
  freeze-correction-writes durable PostgreSQL end of the JSONL correction lane

Every mutating command demands three proofs before it touches anything: the
operator names the target database on purpose (--confirm-target), states the
digest of the exact input file they reviewed (--input-digest), and points at a
backup that already exists (--backup-evidence). A wrong or missing proof is a
refusal, not a prompt.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

MUTATING = {"shadow-import", "reconcile", "freeze-correction-writes"}
# reconcile only reads, but it reads the DATABASE, so it still names its target.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="migrate_info_reports_to_cases")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="read-only classification report")
    scan.add_argument("--source", type=Path, required=True)

    for name in ("shadow-import", "reconcile"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--source", type=Path, required=True)
        _mutation_gates(cmd)
    _mutation_gates(sub.add_parser("freeze-correction-writes"))
    return parser


def _mutation_gates(cmd: argparse.ArgumentParser) -> None:
    cmd.add_argument("--confirm-target", required=True,
                     help="the database you mean, spelled out (e.g. 'disposable-5433')")
    cmd.add_argument("--input-digest", required=True,
                     help="sha256 of the reviewed input file (or 'none' for freeze)")
    cmd.add_argument("--backup-evidence", type=Path, required=True,
                     help="path to a backup that already exists")


def _require_gates(args, *, source: Path | None) -> None:
    from cases.legacy_import import source_file_digest

    if not args.backup_evidence.exists():
        raise SystemExit("refused: --backup-evidence does not exist; back up first (B1)")
    if source is not None:
        actual = source_file_digest(source)
        if args.input_digest != actual:
            # The operator reviewed some file; this proves it was this one.
            raise SystemExit(
                f"refused: --input-digest does not match the file ({actual})"
            )
    if not args.confirm_target.strip():
        raise SystemExit("refused: --confirm-target must name the database")


def _store():
    from cases.store import PostgresCaseStore

    return PostgresCaseStore()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from cases import legacy_import as li

    if args.command == "scan":
        report = li.shadow_import(args.source, store=None, dry_run=True)
        print(json.dumps({
            "source_file": report.source_file, "source_digest": report.source_digest,
            "total": report.total_lines, "valid": report.valid,
            "rejected": report.rejected, "duplicates": report.duplicates,
            "corrections": report.corrections,
            "moderation_links": report.moderation_links,
            "manual_triage": report.manual_triage,
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "shadow-import":
        _require_gates(args, source=args.source)
        store = _store()
        with store.transaction() as transaction:
            report = li.shadow_import(args.source, transaction, dry_run=False)
        print(f"imported ledger rows for {report.total_lines} lines"
              f" ({report.corrections} corrections, {report.duplicates} duplicates)")
        return 0

    if args.command == "reconcile":
        _require_gates(args, source=args.source)
        store = _store()
        with store.transaction() as transaction:
            outcome = li.reconcile_import(args.source, transaction)
        print(json.dumps({"passed": outcome["passed"], "checks": outcome["checks"]},
                         indent=2))
        return 0 if outcome["passed"] else 1

    if args.command == "freeze-correction-writes":
        _require_gates(args, source=None)
        store = _store()
        with store.transaction() as transaction:
            digest = li.freeze_correction_writes(transaction)
        # Both ends: the database row is the durable truth, the file marker is
        # what the public adapter consults on every request. Writing only one
        # would leave a lane the other end believes is closed.
        import public_api

        marker = public_api._correction_cutover_marker()
        if not marker.exists():
            marker.parent.mkdir(exist_ok=True)
            marker.write_text(digest, encoding="utf-8")
        print(f"correction JSONL lane frozen (marker {digest[:12]}…)")
        return 0

    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
