from __future__ import annotations

import sys
from pathlib import Path

from scripts import generate_data_verification_report as report_generator


ARTIFACT_NAMES = {
    "data-verification-report.md",
    "data-verification-matrix.csv",
    "data-verification-claims.csv",
    "data-verification-web-log.csv",
    "data-verification-sources.csv",
    "data-verification-fixes.sql",
}
COMPANION_NAMES = ARTIFACT_NAMES - {"data-verification-report.md"}


def _fixture_data() -> dict[str, object]:
    return {
        "entities": [
            {
                "id": "cho-noi-cai-be-test-fixture",
                "type": "attraction",
                "name": "Chợ nổi Cái Bè test fixture",
                "summary": "Điểm tham quan ven sông dùng cho kiểm thử báo cáo.",
                "description": "Một fixture có hình dạng giống entity thật nhưng không chứa claim bên ngoài.",
                "area": "vinh-long",
                "coordinates": [10.25, 106.0],
                "attributes": {"coords_approximate": True},
                "source": [
                    {
                        "title": "Nguồn kiểm thử cục bộ",
                        "url": "https://vinhlong.gov.vn/fixture",
                    }
                ],
                "images": [],
                "status": "published",
                "verified": 1,
            }
        ],
        "relationships": [],
        "itineraries": [],
    }


def _snapshot(path: Path) -> tuple[bool, bytes | None]:
    return path.exists(), path.read_bytes() if path.exists() else None


def _assert_exact_artifacts(output_dir: Path) -> None:
    assert output_dir.is_dir()
    assert {path.name for path in output_dir.iterdir()} == ARTIFACT_NAMES


def test_generate_report_routes_every_artifact_to_requested_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "forensic-output"
    assert report_generator.ROOT not in output_dir.parents

    protected_paths = [
        report_generator.ROOT / "docs" / name for name in ARTIFACT_NAMES
    ] + [report_generator.ROOT / "docs" / "archive" / "data-verification-report.md"]
    before = {path: _snapshot(path) for path in protected_paths}

    report_generator.generate_report(_fixture_data(), [], output_dir=output_dir)

    _assert_exact_artifacts(output_dir)
    report_body = (output_dir / "data-verification-report.md").read_text(encoding="utf-8")
    for name in COMPANION_NAMES:
        assert str(output_dir / name) in report_body
    assert {path: _snapshot(path) for path in protected_paths} == before


def test_generate_report_uses_monkeypatched_default_output_boundary(
    monkeypatch, tmp_path: Path
) -> None:
    default_output = tmp_path / "default-output"
    unexpected_output = tmp_path / "legacy-output"
    unexpected_output.mkdir()
    monkeypatch.setattr(report_generator, "DEFAULT_OUTPUT_DIR", default_output, raising=False)
    monkeypatch.setattr(report_generator, "ROOT", tmp_path)
    for attribute, name in {
        "REPORT_PATH": "data-verification-report.md",
        "MATRIX_CSV": "data-verification-matrix.csv",
        "CLAIMS_CSV": "data-verification-claims.csv",
        "WEB_LOG_CSV": "data-verification-web-log.csv",
        "SOURCE_AUDIT_CSV": "data-verification-sources.csv",
        "FIX_SQL": "data-verification-fixes.sql",
    }.items():
        monkeypatch.setattr(report_generator, attribute, unexpected_output / name, raising=False)

    report_generator.generate_report(_fixture_data(), [])

    _assert_exact_artifacts(default_output)
    assert not any(unexpected_output.iterdir())


def test_cli_output_dir_controls_artifacts_and_wrote_messages(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    output_dir = tmp_path / "cli-output"
    monkeypatch.setattr(report_generator, "read_json", lambda _path: _fixture_data())
    monkeypatch.setattr(report_generator, "load_or_create_web_log", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(sys, "argv", ["generate_data_verification_report.py", "--output-dir", str(output_dir)])

    assert report_generator.main() == 0

    _assert_exact_artifacts(output_dir)
    assert capsys.readouterr().out.splitlines() == [
        f"Wrote {output_dir / name}"
        for name in (
            "data-verification-report.md",
            "data-verification-matrix.csv",
            "data-verification-claims.csv",
            "data-verification-web-log.csv",
            "data-verification-sources.csv",
            "data-verification-fixes.sql",
        )
    ]
