"""Classifying the old reports file without inventing anything.

The legacy file records what people clicked, not what happened. "resolved"
means a button was pressed; a contact string was collected without a consent
record. Neither may gain meaning on the way in — and the source file itself is
evidence, so the import may read it and never write it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.legacy_import import (  # noqa: E402
    canonical_line_digest,
    classify_legacy_record,
    freeze_correction_writes,
    shadow_import,
)


def _line(**overrides) -> str:
    base = {"ts": "2026-01-01T00:00:00+00:00", "target_id": "p-quan-com",
            "target_type": "stale_field", "field": "phone",
            "detail": "0270 333 4444", "status": "open"}
    base.update(overrides)
    return json.dumps(base, ensure_ascii=False)


def _source(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "reports.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class _LedgerDouble:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def record_legacy_intake(self, **row) -> None:
        self.rows.append(row)


# ── Classification is deterministic and honest ──

def test_a_complete_factual_field_report_classifies_as_a_correction():
    outcome = classify_legacy_record(json.loads(_line()))

    assert outcome.kind == "correction"
    assert outcome.field_path == "attributes.phone"


def test_a_content_report_becomes_linkage_never_a_correction():
    outcome = classify_legacy_record(json.loads(_line(target_type="post", field=None)))

    assert outcome.kind == "moderation_link"


def test_a_report_missing_its_correct_value_goes_to_a_person():
    outcome = classify_legacy_record(json.loads(_line(detail="   ")))

    # Manual triage, never a fabricated correction decision.
    assert outcome.kind == "manual_triage"
    assert "proposed_value" in outcome.missing


def test_an_unmappable_field_goes_to_a_person_too():
    outcome = classify_legacy_record(json.loads(_line(field="images")))

    assert outcome.kind == "manual_triage"
    assert "field_path" in outcome.missing


def test_a_targetless_record_is_rejected():
    assert classify_legacy_record({"detail": "x"}).kind == "rejected"


def test_legacy_resolved_never_reads_as_corrected():
    outcome = classify_legacy_record(json.loads(_line(status="resolved")))

    # "resolved" says a button was pressed. Nothing here may say "corrected":
    # that word is reserved for a decision somebody can be asked about.
    assert outcome.kind == "correction"
    assert "corrected" not in (outcome.reason, outcome.kind)


def test_a_contact_string_never_becomes_consent():
    outcome = classify_legacy_record(json.loads(_line(contact="0912 345 678")))

    assert "consent" not in outcome.reason
    assert outcome.missing == ()


# ── The walk ──

def test_the_dry_run_counts_every_line_and_writes_nothing(tmp_path):
    source = _source(tmp_path, _line(), _line(target_type="post", field=None),
                     "not json at all", _line())
    ledger = _LedgerDouble()

    report = shadow_import(source, ledger, dry_run=True)

    assert report.total_lines == 4
    assert report.valid == 2
    assert report.rejected == 1
    assert report.duplicates == 1
    assert report.corrections == 1
    assert ledger.rows == []


def test_count_algebra_always_closes(tmp_path):
    source = _source(tmp_path, _line(), _line(), "broken", _line(field="images"))

    report = shadow_import(source, _LedgerDouble(), dry_run=True)

    assert report.total_lines == report.valid + report.rejected + report.duplicates


def test_a_duplicate_line_keeps_its_own_locator(tmp_path):
    source = _source(tmp_path, _line(), _line())

    report = shadow_import(source, _LedgerDouble(), dry_run=True)

    # One case later, but two locators: both places the bytes appeared.
    assert len(report.locators) == 2
    assert report.locators[0]["raw_record_digest"] == report.locators[1]["raw_record_digest"]
    assert report.locators[1]["import_result"] == "duplicate"
    assert [entry["source_line"] for entry in report.locators] == [1, 2]


def test_the_digest_is_of_the_bytes_not_of_a_reserialisation():
    line = '{"b": 1,  "a": 2}'

    # Re-serialising would reorder keys and change the digest of evidence.
    assert canonical_line_digest(line) == canonical_line_digest(line + "\n")
    assert canonical_line_digest(line) != canonical_line_digest('{"a": 2, "b": 1}')


def test_the_source_file_bytes_are_untouched(tmp_path):
    source = _source(tmp_path, _line(), "broken")
    before = source.read_bytes()

    shadow_import(source, _LedgerDouble(), dry_run=False)

    assert source.read_bytes() == before


def test_a_real_import_writes_one_ledger_row_per_line(tmp_path):
    source = _source(tmp_path, _line(), _line(target_type="post", field=None))
    ledger = _LedgerDouble()

    shadow_import(source, ledger, dry_run=False)

    assert [row["source_line"] for row in ledger.rows] == [1, 2]
    assert ledger.rows[0]["import_result"] == "correction"
    assert ledger.rows[0]["legacy_status"] == "open"


def test_freezing_writes_the_durable_marker_row():
    ledger = _LedgerDouble()

    digest = freeze_correction_writes(ledger)

    row = ledger.rows[0]
    assert row["source_file"] == "__correction_write_freeze__"
    assert row["import_result"] == "freeze"
    assert row["raw_record_digest"] == digest and len(digest) == 64
