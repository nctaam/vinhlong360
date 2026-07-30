"""Activation-gated erasure CLI contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import scripts.run_account_erasure as cli


UTC = timezone.utc
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def test_cli_defaults_to_read_only_audit(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "_utc_now", lambda: NOW, raising=False)
    monkeypatch.setattr(
        cli,
        "erase_due_accounts",
        lambda **kwargs: calls.append(kwargs) or type("R", (), {"to_dict": lambda self: {"audit_only": True}})(),
        raising=False,
    )

    assert cli.main([]) == 0
    assert calls == [{"now": NOW, "limit": 50, "audit_only": True}]


def test_cli_mutation_requires_activate_backup_and_limit(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "erase_due_accounts", lambda **kwargs: calls.append(kwargs), raising=False)
    backup = tmp_path / "backup.json"
    backup.write_text("{}", encoding="utf-8")

    assert cli.main(["--activate"]) != 0
    assert cli.main(["--activate", "--backup-evidence", str(backup)]) != 0
    assert cli.main(["--activate", "--backup-evidence", str(backup), "--limit", "51"]) != 0
    assert calls == []


def test_cli_mutation_passes_all_explicit_gates(monkeypatch, tmp_path):
    calls = []
    backup = tmp_path / "backup.json"
    backup.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "_utc_now", lambda: NOW, raising=False)
    monkeypatch.setattr(
        cli,
        "erase_due_accounts",
        lambda **kwargs: calls.append(kwargs) or type("R", (), {"to_dict": lambda self: {"audit_only": False}})(),
        raising=False,
    )

    assert cli.main(
        ["--activate", "--backup-evidence", str(backup), "--limit", "1"]
    ) == 0
    assert calls == [{"now": NOW, "limit": 1, "audit_only": False}]
