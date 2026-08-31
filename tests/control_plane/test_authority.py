from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from agent.control_plane.authority import check_authority, load_authority


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def write_registry(
    root: Path,
    *,
    audit_artifact: str = "docs/audit.md",
    max_age_hours: int = 24,
    handoff_verified_at: str = "2026-08-31T00:00:00Z",
) -> Path:
    (root / "config").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "CLAUDE.md").write_text("Authority: config/release-authority.json\n", encoding="utf-8")
    (root / "docs/HANDOFF.md").write_text("Authority: config/release-authority.json\n", encoding="utf-8")
    (root / "docs/ROADMAP.md").write_text(
        "## Fail-da-biet\nBaseline hiện tại: 15 fail\nAuthority: config/release-authority.json\n",
        encoding="utf-8",
    )
    (root / "docs/standards").mkdir(parents=True)
    (root / "docs/standards/00-INDEX.md").write_text(
        "\n".join(f"| R{i}.x | rule |" for i in range(1, 39))
        + "\nAuthority: config/release-authority.json\n",
        encoding="utf-8",
    )
    (root / audit_artifact).parent.mkdir(parents=True, exist_ok=True)
    (root / audit_artifact).write_text(
        "\n".join(f"| F-{i:02d} | finding |" for i in range(1, 74))
        + "\nAuthority: config/release-authority.json\n",
        encoding="utf-8",
    )
    payload = {
        "schema_version": "1",
        "authority_id": "release-control",
        "owner": "service-owner",
        "branch": "codex/correction-case-pilot",
        "head_source": "git:HEAD",
        "baseline_source": "docs/ROADMAP.md#fail-da-biet",
        "rule_index": "docs/standards/00-INDEX.md",
        "audit_artifact": audit_artifact,
        "max_age_hours": max_age_hours,
        "p1_findings": [
            *[f"F-{i:02d}" for i in range(1, 18)],
            "F-32",
            "F-34",
            "F-38",
            "F-40",
            "F-41",
            "F-42",
            "F-44",
            "F-47",
            "F-49",
            "F-53",
            "F-69",
        ],
        "active_documents": [
            {"path": "docs/HANDOFF.md", "last_verified_at": handoff_verified_at},
        ],
    }
    path = root / "config/release-authority.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Authority Tests")
    _git(
        root,
        "add",
        "config",
        "CLAUDE.md",
        "docs/ROADMAP.md",
        "docs/standards/00-INDEX.md",
        "docs/HANDOFF.md",
        audit_artifact,
    )
    _git(root, "commit", "-qm", "seed")
    _git(root, "branch", "-M", "codex/correction-case-pilot")
    return path


def test_load_authority_reads_machine_registry(tmp_path: Path) -> None:
    path = write_registry(tmp_path)
    registry = load_authority(path)
    assert registry.authority_id == "release-control"
    assert registry.max_age_hours == 24
    assert registry.p1_findings[-1] == "F-69"


def test_untracked_audit_artifact_blocks_authority(tmp_path: Path) -> None:
    write_registry(tmp_path, audit_artifact="docs/audit.md", max_age_hours=24)
    _git(tmp_path, "rm", "--cached", "docs/audit.md", "-q")
    _git(tmp_path, "commit", "-qm", "make audit untracked")
    report = check_authority(
        tmp_path,
        now=datetime(2026, 8, 31, tzinfo=UTC),
        head_sha="a" * 40,
    )
    assert report.status == "BLOCKED"
    assert "untracked" in " ".join(report.mismatches)


def test_stale_active_document_cannot_be_release_evidence(tmp_path: Path) -> None:
    write_registry(tmp_path, max_age_hours=24)
    report = check_authority(
        tmp_path,
        now=datetime(2026, 9, 2, tzinfo=UTC),
        head_sha="b" * 40,
    )
    assert report.status == "STALE"
    assert report.expired_documents == ("docs/HANDOFF.md",)
