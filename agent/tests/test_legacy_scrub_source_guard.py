"""Source-level safety contracts for legacy scrub tooling."""

from pathlib import Path


def test_legacy_scrub_uses_declared_store_inventory_and_no_broad_deletion():
    source = Path(__file__).parents[1].joinpath("legacy_scrub.py").read_text(encoding="utf-8")

    assert "DECLARED_STORES" in source
    assert "rglob(\"*\")" not in source
    assert "shutil.rmtree" not in source
    assert "os.walk" not in source
    assert "replace(\"" not in source
    assert "redact_log_value" in source


def test_scrub_script_defaults_to_dry_run_and_has_explicit_apply_gate():
    source = Path(__file__).parents[2].joinpath("scripts", "scrub_legacy_personal_data.py").read_text(encoding="utf-8")

    assert "--apply" in source
    assert "--backup-evidence" in source
    assert "apply_scrub_plan" in source
    assert "dry-run" in source
