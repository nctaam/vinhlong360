"""Task 5 lifecycle registry and proof contracts."""

from pathlib import Path

import pytest

from control_plane.lifecycle import (
    export_subject,
    load_lifecycle_registry,
)
import storage


def test_registry_covers_every_known_sink():
    registry = load_lifecycle_registry(Path("config/lifecycle-registry.json"))
    assert {
        "postgres",
        "reports-jsonl",
        "analytics-jsonl",
        "bot-memory",
        "browser-storage",
        "object-store",
        "cdn",
    } <= registry.names


def test_registry_rejects_missing_proof_metadata(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version":"1","sinks":[{"name":"x"}]}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_lifecycle_registry(path)


def test_export_manifest_declares_cursor_and_checksums(monkeypatch):
    class EmptyDB:
        _use_pg = False

    import control_plane.lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "db", EmptyDB())
    bundle = export_subject("user-1", limit=1)
    assert bundle.manifest["schema_version"] == "1"
    assert bundle.manifest["truncated"] is False
    assert "checksums" in bundle.manifest
    assert "excluded_secrets" in bundle.manifest


def test_media_delete_receipt_is_keyed_and_idempotent(monkeypatch):
    calls = []
    monkeypatch.setattr(storage.storage, "delete", lambda key: calls.append(key))
    first = storage.delete_media_with_receipt("subject", "objects/a.webp", "7")
    second = storage.delete_media_with_receipt("subject", "objects/a.webp", "7")
    assert first["status"] == "deleted"
    assert second["status"] == "already_absent"
    assert calls == ["objects/a.webp"]
