from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from agent.control_plane.authority import _baseline_section, check_authority, load_authority


P1_FIXTURE_IDS = [
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
]


def test_baseline_section_preserves_nested_headings_until_same_level() -> None:
    mismatches: list[str] = []
    markdown = "## Target\nvalue\n### Child\nchild value\n## Next\nnext value\n"

    section = _baseline_section(markdown, "ROADMAP.md#target", mismatches)

    assert section == "## Target\nvalue\n### Child\nchild value"
    assert mismatches == []


def test_baseline_section_resolves_matching_explicit_anchor() -> None:
    mismatches: list[str] = []
    markdown = "<a id=\"target\"></a>\n\n## Target\nvalue\n## Next\nnext value\n"

    section = _baseline_section(markdown, "ROADMAP.md#target", mismatches)

    assert section == "## Target\nvalue"
    assert mismatches == []


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _head_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


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
        "<a id=\"fail-da-biet\"></a>\n## Fail-da-biet\nBaseline hiện tại: 15 fail\nAuthority: config/release-authority.json\n",
        encoding="utf-8",
    )
    (root / "docs/standards").mkdir(parents=True)
    (root / "docs/standards/00-INDEX.md").write_text(
        "\n".join(f"| R{i}.x | rule |" for i in range(1, 39))
        + "\nAuthority: config/release-authority.json\n",
        encoding="utf-8",
    )
    (root / audit_artifact).parent.mkdir(parents=True, exist_ok=True)
    p1_rows = "\n".join(f"| {finding_id} | P1 finding |" for finding_id in P1_FIXTURE_IDS)
    p2_rows = "\n".join(
        f"| F-{i:02d} | P2 finding |" for i in range(1, 74) if f"F-{i:02d}" not in P1_FIXTURE_IDS
    )
    (root / audit_artifact).write_text(
        "### P1 - pilot blockers\n"
        + p1_rows
        + "\n### P2 - follow-up\n"
        + p2_rows
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
        "p1_findings": P1_FIXTURE_IDS,
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
        head_sha=_head_sha(tmp_path),
    )
    assert report.status == "BLOCKED"
    assert "untracked" in " ".join(report.mismatches)


def test_untracked_current_progress_artifact_blocks_authority(tmp_path: Path) -> None:
    path = write_registry(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["progress_artifact"] = ".superpowers/sdd/progress.md"
    path.write_text(json.dumps(payload), encoding="utf-8")
    progress = tmp_path / ".superpowers/sdd/progress.md"
    progress.parent.mkdir(parents=True)
    progress.write_text("current execution ledger\n", encoding="utf-8")

    report = check_authority(
        tmp_path,
        now=datetime(2026, 8, 31, tzinfo=UTC),
        head_sha=_head_sha(tmp_path),
    )

    assert report.status == "BLOCKED"
    assert "untracked progress artifact" in " ".join(report.mismatches)


def test_stale_active_document_cannot_be_release_evidence(tmp_path: Path) -> None:
    write_registry(tmp_path, max_age_hours=24)
    report = check_authority(
        tmp_path,
        now=datetime(2026, 9, 2, tzinfo=UTC),
        head_sha=_head_sha(tmp_path),
    )
    assert report.status == "STALE"
    assert report.expired_documents == ("docs/HANDOFF.md",)


def test_invalid_head_shape_blocks_authority(tmp_path: Path) -> None:
    write_registry(tmp_path)
    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha="not-a-sha")
    assert report.status == "BLOCKED"
    assert "HEAD shape invalid" in report.mismatches


def test_baseline_fragment_must_resolve_to_heading_slug(tmp_path: Path) -> None:
    path = write_registry(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["baseline_source"] = "docs/ROADMAP.md#bogus-anchor"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha=_head_sha(tmp_path))

    assert report.status == "BLOCKED"
    assert any("anchor missing" in mismatch for mismatch in report.mismatches)


def test_baseline_fragment_accepts_github_slug_for_diacritic_heading(tmp_path: Path) -> None:
    path = write_registry(tmp_path)
    (tmp_path / "docs/ROADMAP.md").write_text(
        "## Fail-đã-biết\nBaseline hiện tại: 15 fail\nAuthority: config/release-authority.json\n",
        encoding="utf-8",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["baseline_source"] = "docs/ROADMAP.md#fail-da-biet"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha=_head_sha(tmp_path))

    assert report.status == "PASS"


def test_baseline_count_is_scoped_to_selected_fragment_section(tmp_path: Path) -> None:
    write_registry(tmp_path)
    (tmp_path / "docs/ROADMAP.md").write_text(
        "## Other\n"
        "Baseline hiện tại: 15 fail\n"
        "\n"
        "<a id=\"fail-da-biet\"></a>\n"
        "## Fail-da-biet\n"
        "Baseline hiện tại: 99 fail\n"
        "Authority: config/release-authority.json\n",
        encoding="utf-8",
    )

    report = check_authority(
        tmp_path,
        now=datetime(2026, 8, 31, tzinfo=UTC),
        head_sha=_head_sha(tmp_path),
    )

    assert report.status == "BLOCKED"
    assert any("baseline count mismatch" in mismatch for mismatch in report.mismatches)


def test_baseline_without_fragment_blocks_closed(tmp_path: Path) -> None:
    path = write_registry(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["baseline_source"] = "docs/ROADMAP.md"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = check_authority(
        tmp_path,
        now=datetime(2026, 8, 31, tzinfo=UTC),
        head_sha=_head_sha(tmp_path),
    )

    assert report.status == "BLOCKED"
    assert any("baseline fragment missing" in mismatch for mismatch in report.mismatches)


def test_unreadable_baseline_link_returns_blocked_report(tmp_path: Path) -> None:
    write_registry(tmp_path)
    (tmp_path / "docs/ROADMAP.md").write_bytes(b"## Fail-da-biet\nBaseline: \xff fail\n")

    report = check_authority(
        tmp_path,
        now=datetime(2026, 8, 31, tzinfo=UTC),
        head_sha=_head_sha(tmp_path),
    )

    assert report.status == "BLOCKED"
    assert any("baseline link unreadable" in mismatch for mismatch in report.mismatches)


def test_audit_p1_roster_must_match_registry(tmp_path: Path) -> None:
    write_registry(tmp_path)
    audit_path = tmp_path / "docs/audit.md"
    audit_path.write_text(
        audit_path.read_text(encoding="utf-8").replace("| F-01 | P1 finding |\n", ""),
        encoding="utf-8",
    )

    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha=_head_sha(tmp_path))

    assert report.status == "BLOCKED"
    assert any("P1 roster mismatch" in mismatch for mismatch in report.mismatches)


def test_future_registry_timestamp_blocks_authority(tmp_path: Path) -> None:
    path = write_registry(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["last_verified_at"] = "2099-01-01T00:00:00Z"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha=_head_sha(tmp_path))

    assert report.status == "BLOCKED"
    assert any("future verification timestamp" in mismatch for mismatch in report.mismatches)


def test_future_active_document_timestamp_blocks_authority(tmp_path: Path) -> None:
    write_registry(tmp_path, handoff_verified_at="2099-01-01T00:00:00Z")

    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha=_head_sha(tmp_path))

    assert report.status == "BLOCKED"
    assert any("docs/HANDOFF.md" in mismatch and "future verification timestamp" in mismatch for mismatch in report.mismatches)


def test_supplied_head_must_match_repository_head(tmp_path: Path) -> None:
    write_registry(tmp_path)

    report = check_authority(tmp_path, now=datetime(2026, 8, 31, tzinfo=UTC), head_sha="a" * 40)

    assert report.status == "BLOCKED"
    assert "HEAD does not match repository HEAD" in report.mismatches
