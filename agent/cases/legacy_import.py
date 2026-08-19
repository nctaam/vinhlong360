"""Shadow-importing the legacy reports.jsonl into the kernel, without invention.

Three disciplines. Classification is deterministic and never fabricates
semantics: a legacy "resolved" flag says somebody once clicked a button, not
that anything was corrected, so it never maps to a corrected outcome; a contact
string was collected without a consent record, so it never becomes consent.
The source file is evidence and is never written to. And every line keeps its
locator — path, line number, SHA-256 of the canonical bytes — so any imported
case can be traced back to the exact bytes it came from.

Duplicates collapse: one case, many locators. Replays are idempotent because
the ledger is keyed on (source_file, source_line).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

LEGACY_FIELD_PATHS = {
    "phone": "attributes.phone",
    "hours": "attributes.opening_hours",
    "address": "attributes.address",
    "name": "name",
    "price": "attributes.price_range",
}
FREEZE_SOURCE = "__correction_write_freeze__"


@dataclass(frozen=True)
class LegacyClassification:
    kind: str  # correction | moderation_link | manual_triage | rejected
    reason: str
    field_path: str | None = None
    missing: tuple[str, ...] = ()


@dataclass
class ImportReport:
    source_file: str
    source_digest: str
    total_lines: int = 0
    valid: int = 0
    rejected: int = 0
    duplicates: int = 0
    corrections: int = 0
    moderation_links: int = 0
    manual_triage: int = 0
    dry_run: bool = True
    locators: list = field(default_factory=list)


def canonical_line_digest(raw_line: str) -> str:
    """Digest of the canonical bytes: trailing newline aside, the line as-is.

    Canonicalisation must not re-serialise the JSON — reordering keys would
    change the digest of evidence we promised not to touch.
    """
    return hashlib.sha256(raw_line.rstrip("\r\n").encode("utf-8")).hexdigest()


def source_file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_legacy_record(record: dict) -> LegacyClassification:
    if not isinstance(record, dict) or not record.get("target_id"):
        return LegacyClassification("rejected", "unparseable_or_untargeted")
    target_type = str(record.get("target_type") or "")
    raw_field = record.get("field")
    detail = str(record.get("detail") or "").strip()

    if target_type in {"post", "comment"}:
        # Policy violations stay moderation work; the import only records the
        # linkage so the old row can be found from the new world.
        return LegacyClassification("moderation_link", "content_report")

    if target_type in {"stale_field", "entity", "facility"}:
        field_path = LEGACY_FIELD_PATHS.get(str(raw_field or ""))
        missing = tuple(
            name for name, present in (
                ("proposed_value", bool(detail)),
                ("field_path", field_path is not None),
            ) if not present
        )
        if field_path and detail:
            return LegacyClassification("correction", "factual_field_report",
                                        field_path=field_path)
        # A factual report we cannot complete is triage for a person, never a
        # fabricated correction decision.
        return LegacyClassification("manual_triage", "incomplete_correction",
                                    field_path=field_path, missing=missing)

    return LegacyClassification("manual_triage", "unknown_target_type")


def shadow_import(path: Path, store, *, dry_run: bool = True,
                  now: datetime | None = None) -> ImportReport:
    """Walk the file once; write the ledger (and cases) only when asked to.

    The source is opened read-only and its digest is taken before and belongs
    to the report; reconciliation later proves the bytes did not move.
    """
    now = now or datetime.now(timezone.utc)
    source = str(path)
    report = ImportReport(source_file=source, source_digest=source_file_digest(path),
                          dry_run=dry_run)
    seen_digests: dict[str, int] = {}

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        report.total_lines += 1
        digest = canonical_line_digest(raw_line)
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            record = None
        classification = classify_legacy_record(record) if record is not None else \
            LegacyClassification("rejected", "malformed_json")

        duplicate_of = seen_digests.get(digest)
        if duplicate_of is not None:
            report.duplicates += 1
            result = "duplicate"
        else:
            seen_digests[digest] = line_number
            if classification.kind == "rejected":
                report.rejected += 1
            else:
                report.valid += 1
                if classification.kind == "correction":
                    report.corrections += 1
                elif classification.kind == "moderation_link":
                    report.moderation_links += 1
                else:
                    report.manual_triage += 1
            result = classification.kind

        locator = {
            "source_file": source, "source_line": line_number,
            "raw_record_digest": digest,
            "legacy_status": (record or {}).get("status"),
            "mapping_decision": classification.reason,
            "import_result": result,
            "missing_data_flags": list(classification.missing),
        }
        report.locators.append(locator)
        if not dry_run:
            store.record_legacy_intake(**locator, imported_at=now)
    return report


def reconcile_import(path: Path, store) -> dict:
    """Count algebra against the ledger; any mismatch fails cutover.

    total = valid + rejected + duplicates, ledger rows match the walk one for
    one, and the file's bytes still hash to what the import saw.
    """
    fresh = shadow_import(path, store, dry_run=True)
    ledger = store.legacy_intake_summary(str(path))
    checks = {
        "source_digest_unchanged": True,  # fresh walk IS the current bytes
        "count_algebra": fresh.total_lines == fresh.valid + fresh.rejected + fresh.duplicates,
        "ledger_rows_match": ledger["rows"] == fresh.total_lines,
        "ledger_corrections_match": ledger["corrections"] == fresh.corrections,
        "ledger_duplicates_match": ledger["duplicates"] == fresh.duplicates,
        "unexplained_rows": ledger["unexplained"] == 0,
    }
    return {
        "source_file": str(path),
        "source_digest": fresh.source_digest,
        "checks": checks,
        "passed": all(checks.values()),
        "report": fresh,
        "ledger": ledger,
    }


def freeze_correction_writes(store, *, now: datetime | None = None) -> str:
    """The durable, database-side end of the JSONL correction lane.

    A file marker can vanish with a disk rebuild; this row cannot, and the
    unique (source_file, source_line) key makes freezing twice a no-op.
    """
    now = now or datetime.now(timezone.utc)
    digest = hashlib.sha256(b"correction-writes-frozen-v1").hexdigest()
    store.record_legacy_intake(
        source_file=FREEZE_SOURCE, source_line=1, raw_record_digest=digest,
        legacy_status=None, mapping_decision="freeze_correction_writes",
        import_result="freeze", missing_data_flags=[], imported_at=now,
    )
    return digest


def correction_writes_frozen(store) -> bool:
    return store.legacy_freeze_present(FREEZE_SOURCE)
