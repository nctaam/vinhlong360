from __future__ import annotations

import json
import logging
import sys
from pathlib import Path


AGENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT_DIR))

import metrics  # noqa: E402
import middleware  # noqa: E402
import privacy_boundary  # noqa: E402


def _structured_logger(tmp_path: Path, name: str) -> middleware.StructuredLogger:
    logger = middleware.StructuredLogger(name=name, max_entries=100)
    logger.log_file = tmp_path / f"{name}.jsonl"
    return logger


def test_structured_logger_redacts_nested_jsonl_and_console(tmp_path, caplog):
    logger = _structured_logger(tmp_path, "privacy-log-nested")

    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.log(
            "error",
            "provider failed for a@example.com",
            query="call 0901234567",
            nested={"reply": "mail b@example.com"},
            attempt=2,
        )
        logger.flush()

    persisted = logger.log_file.read_text(encoding="utf-8")
    console = "\n".join(
        record.getMessage() for record in caplog.records if record.name == logger.name
    )
    for raw in ("a@example.com", "0901234567", "b@example.com"):
        assert raw not in persisted
        assert raw not in console
    entry = json.loads(persisted)
    assert entry["attempt"] == 2
    assert entry["nested"]["reply"] == "mail [EMAIL]"


def test_structured_logger_uses_fixed_placeholder_on_redaction_failure(
    tmp_path, caplog, monkeypatch
):
    logger = _structured_logger(tmp_path, "privacy-log-failure")

    def fail_redaction(_value):
        raise RuntimeError("detector leaked secret@example.com")

    monkeypatch.setattr(middleware, "redact_log_value", fail_redaction, raising=False)
    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.error("raw secret@example.com", query="0901234567")
        logger.flush()

    persisted = logger.log_file.read_text(encoding="utf-8")
    console = "\n".join(
        record.getMessage() for record in caplog.records if record.name == logger.name
    )
    assert "[REDACTION_FAILED]" in persisted
    assert "[REDACTION_FAILED]" in console
    for raw in ("secret@example.com", "0901234567", "detector leaked"):
        assert raw not in persisted
        assert raw not in console


def test_stdlib_bridge_uses_the_same_redaction_boundary(tmp_path):
    logger = _structured_logger(tmp_path, "privacy-log-bridge")
    bridge = middleware._StructuredLogBridge(logger)
    record = logging.LogRecord(
        "provider.sdk",
        logging.ERROR,
        __file__,
        1,
        "provider error for bridge@example.com",
        (),
        None,
    )

    bridge.emit(record)
    logger.flush()

    persisted = logger.log_file.read_text(encoding="utf-8")
    assert "bridge@example.com" not in persisted
    assert "[EMAIL]" in persisted


def test_structured_logger_never_stringifies_unknown_objects(tmp_path):
    class RawValue:
        def __str__(self):
            return "object leaked object@example.com"

    logger = _structured_logger(tmp_path, "privacy-log-object")
    logger.error("provider failed", detail=RawValue())
    logger.flush()

    persisted = logger.log_file.read_text(encoding="utf-8")
    assert "object@example.com" not in persisted
    assert "[REDACTION_FAILED]" in persisted


def test_privacy_metrics_collapse_unknown_labels_to_other():
    known_before = metrics.privacy_redactions_total.get(
        {"source": "log", "type": "email"}
    )
    other_before = metrics.privacy_redactions_total.get(
        {"source": "other", "type": "other"}
    )
    failure_before = metrics.privacy_boundary_failures_total.get({"stage": "other"})

    metrics.track_privacy_redaction("log", "email")
    metrics.track_privacy_redaction("raw-user@example.com", "unbounded-type")
    metrics.track_privacy_boundary_failure("raw-stage@example.com")

    assert metrics.privacy_redactions_total.get(
        {"source": "log", "type": "email"}
    ) == known_before + 1
    assert metrics.privacy_redactions_total.get(
        {"source": "other", "type": "other"}
    ) == other_before + 1
    assert metrics.privacy_boundary_failures_total.get(
        {"stage": "other"}
    ) == failure_before + 1
    exposition = metrics.generate_metrics()
    assert "raw-user@example.com" not in exposition
    assert "unbounded-type" not in exposition
    assert "raw-stage@example.com" not in exposition


def test_privacy_boundary_redaction_records_source_and_type_metric():
    before = metrics.privacy_redactions_total.get(
        {"source": "provider_output", "type": "email"}
    )

    safe = privacy_boundary.redact_text(
        "provider returned metric@example.com",
        source="provider_output",
    )

    assert safe.text == "provider returned [EMAIL]"
    assert metrics.privacy_redactions_total.get(
        {"source": "provider_output", "type": "email"}
    ) == before + 1
