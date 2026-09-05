import json
from datetime import datetime, timezone


if False:  # pragma: no cover - staged pairing markers
    from control_plane import lifecycle as lifecycle_contract  # noqa: F401


def test_every_backend_sink_has_export_and_erasure_policy():
    from data_lifecycle import list_lifecycle_sinks

    sinks = {sink.name: sink for sink in list_lifecycle_sinks()}
    expected = {
        "reports",
        "admin_audit",
        "case_outbox",
        "provider_receipts",
        "jsonl_legacy_archive",
        "bot_conversations",
        "browser_storage",
        "object_media",
    }
    assert expected <= sinks.keys()
    assert sinks["reports"].export_mode == "redacted"
    assert sinks["reports"].erasure_mode in {"redact", "delete"}
    assert sinks["jsonl_legacy_archive"].authority == "legacy-read-only"
    assert all(isinstance(sink.retention_days, int) for sink in sinks.values())


def test_invalid_lifecycle_sink_blocks_runtime_drill_validation(tmp_path):
    from scripts.ops.validate_drill_index import validate

    root = tmp_path
    drills = root / "artifacts" / "runtime-drills"
    drills.mkdir(parents=True)
    (drills / "index.json").write_text(
        json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entries": [{
                "id": "empty",
                "status": "UNAVAILABLE",
                "missing": "not run",
            }],
        }),
        encoding="utf-8",
    )
    config = root / "config"
    config.mkdir()
    (config / "lifecycle-registry.json").write_text(
        json.dumps({
            "schema_version": "1",
            "sinks": [],
            "lifecycle_sinks": [{
                "name": "reports",
                "authority": "",
                "contains_personal_data": True,
                "export_mode": "redacted",
                "erasure_mode": "redact",
                "retention_days": None,
                "proof_level": "strong",
            }],
        }),
        encoding="utf-8",
    )

    report = validate(root)

    assert any("lifecycle" in problem.lower() for problem in report["problems"])
