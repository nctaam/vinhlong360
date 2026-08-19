"""The migration CLI: four commands, and three proofs before anything mutates.

scan is read-only and needs nothing. Everything else refuses — not prompts,
refuses — without a named target, the digest of the exact file the operator
reviewed, and a backup that already exists. B1 is not a suggestion.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "migrate_info_reports_to_cases.py"


def _load_cli():
    name = "migrate_info_reports_to_cases"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


cli = _load_cli()


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "reports.jsonl"
    path.write_text(json.dumps({
        "target_id": "p-1", "target_type": "stale_field",
        "field": "phone", "detail": "0270 333 4444",
    }) + "\n", encoding="utf-8")
    return path


def test_the_cli_offers_exactly_the_four_commands():
    parser = cli.build_parser()
    sub = next(action for action in parser._actions
               if action.__class__.__name__ == "_SubParsersAction")

    assert set(sub.choices) == {"scan", "shadow-import", "reconcile",
                                "freeze-correction-writes"}


def test_scan_is_read_only_and_needs_no_proofs(tmp_path, capsys):
    source = _source(tmp_path)
    before = source.read_bytes()

    code = cli.main(["scan", "--source", str(source)])

    assert code == 0
    assert source.read_bytes() == before
    report = json.loads(capsys.readouterr().out)
    assert report["total"] == 1
    assert report["corrections"] == 1


@pytest.mark.parametrize("command", ["shadow-import", "reconcile"])
def test_a_mutating_command_refuses_without_the_three_proofs(command, tmp_path):
    source = _source(tmp_path)

    # argparse itself refuses when the gates are not even named.
    with pytest.raises(SystemExit) as excinfo:
        cli.main([command, "--source", str(source)])
    assert excinfo.value.code == 2


def test_a_missing_backup_is_a_refusal_not_a_prompt(tmp_path):
    source = _source(tmp_path)
    from cases.legacy_import import source_file_digest

    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "shadow-import", "--source", str(source),
            "--confirm-target", "disposable-5433",
            "--input-digest", source_file_digest(source),
            "--backup-evidence", str(tmp_path / "khong-ton-tai.dump"),
        ])

    assert "backup" in str(excinfo.value.code)


def test_a_wrong_input_digest_is_a_refusal(tmp_path):
    source = _source(tmp_path)
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"evidence")

    # The operator reviewed SOME file; the digest proves it was this one.
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "shadow-import", "--source", str(source),
            "--confirm-target", "disposable-5433",
            "--input-digest", "0" * 64,
            "--backup-evidence", str(backup),
        ])

    assert "digest" in str(excinfo.value.code)


def test_the_freeze_command_still_demands_its_proofs(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "freeze-correction-writes",
            "--confirm-target", "disposable-5433",
            "--input-digest", "none",
            "--backup-evidence", str(tmp_path / "missing.dump"),
        ])

    assert "backup" in str(excinfo.value.code)
