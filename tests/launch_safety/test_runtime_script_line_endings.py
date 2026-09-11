from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_systemd_invoked_shell_scripts_are_lf_only() -> None:
    """Systemd must not receive CRLF shebangs or CR-tainted shell commands."""

    for relative_path in (
        "scripts/ops/backup_db_daily.sh",
        "scripts/ops/watchdog.sh",
    ):
        payload = (ROOT / relative_path).read_bytes()
        assert b"\r" not in payload, relative_path


def test_git_preserves_lf_for_systemd_invoked_shell_scripts() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.sh text eol=lf" in attributes
