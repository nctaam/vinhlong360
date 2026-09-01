"""Task 5 lifecycle registry and proof contracts."""

from pathlib import Path
import json

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


def test_registry_rejects_unknown_keys_and_strategy_enums(tmp_path):
    base = {"name": "x", "owner_key": "id", "classification": "personal",
            "export_strategy": "row-keyset", "erase_strategy": "delete",
            "retention_days": None, "proof_level": "strong"}
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps({"schema_version": "1", "sinks": [{**base, "extra": 1}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        load_lifecycle_registry(unknown)
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"schema_version": "1", "sinks": [{**base, "export_strategy": "bogus"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="export_strategy"):
        load_lifecycle_registry(invalid)


def test_browser_instruction_lists_shipped_keys():
    from control_plane.lifecycle import issue_browser_clear_instruction
    instruction = issue_browser_clear_instruction("user-1")
    assert {"vl360_favorites", "vl360_recent", "vl360_post_draft", "vl360_recent_searches",
            "vinhlong360:public-search-entries:v2", "chat_sid"} <= set(instruction["keys"])


def test_failed_media_receipt_can_retry(monkeypatch):
    calls = []
    def fail_once(key):
        calls.append(key)
        if len(calls) == 1:
            raise RuntimeError("temporary")
    monkeypatch.setattr(storage.storage, "delete", fail_once)
    first = storage.delete_media_with_receipt("subject-retry", "objects/retry.webp")
    second = storage.delete_media_with_receipt("subject-retry", "objects/retry.webp")
    assert first["status"] == "failed"
    assert second["status"] == "deleted"
    assert len(calls) == 2


def test_manifest_marks_degraded_when_external_adapter_unavailable(monkeypatch):
    import control_plane.lifecycle as lifecycle
    class EmptyDB: _use_pg = False
    monkeypatch.setattr(lifecycle, "db", EmptyDB())
    bundle = lifecycle.export_subject("u", limit=1)
    assert bundle.manifest["degraded"] is True


def test_media_object_failure_still_runs_cdn_and_retries(monkeypatch):
    import storage
    calls = []
    monkeypatch.setattr(storage.storage, "delete", lambda key: (_ for _ in ()).throw(RuntimeError("object")))
    result = storage.delete_media_with_receipt("u-cdn", "k", cdn_purge=lambda key: calls.append(key))
    assert result["status"] == "failed" and result["cdn_status"] == "deleted" and calls == ["k"]


def test_export_keyset_cursor_includes_tie_breaker(monkeypatch):
    import control_plane.lifecycle as lifecycle
    class FakeDB:
        _use_pg = True; _ph = "%s"
        def _conn(self):
            from contextlib import nullcontext
            return nullcontext(object())
        def _fetchall(self, _conn, sql, _params):
            assert "ORDER BY created_at DESC, id DESC" in sql
            return []
        _row_to_dict = staticmethod(lambda row: row)
    monkeypatch.setattr(lifecycle, "db", FakeDB())
    lifecycle._rows_for_table("posts", "u", None, 1)


def test_export_cursor_offset_is_scoped_to_its_sink(monkeypatch):
    import control_plane.lifecycle as lifecycle
    class FakeDB:
        _use_pg = True; _ph = "%s"
        def _conn(self):
            from contextlib import nullcontext
            return nullcontext(object())
        def _fetchall(self, _conn, sql, _params):
            if "FROM posts" in sql:
                assert _params[-1] == 2
            if "FROM comments" in sql:
                assert _params[-1] == 0
            return []
        _row_to_dict = staticmethod(lambda row: row)
    monkeypatch.setattr(lifecycle, "db", FakeDB())
    cursor = lifecycle._encode_cursor('{"sink":"posts","offset":2}')
    decoded = lifecycle._decode_cursor(cursor)
    lifecycle._rows_for_table("posts", "u", decoded, 1)
    lifecycle._rows_for_table("comments", "u", decoded, 1)


def test_legacy_export_cursor_decodes_per_dataset():
    from identity.api import _legacy_cursor_offsets
    import control_plane.lifecycle as lifecycle
    token = lifecycle._encode_cursor('{"sink":"posts","offset":3}')
    assert _legacy_cursor_offsets(token, "posts") == 3
    assert _legacy_cursor_offsets(token, "comments") == 0
