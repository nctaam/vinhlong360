"""Task 5 lifecycle registry and proof contracts."""

from pathlib import Path
import json

import pytest

from control_plane.lifecycle import (
    export_subject,
    load_lifecycle_registry,
)
import storage


def _reset_media_receipts() -> None:
    """Keep durable receipt tests isolated from the ignored local DB file."""
    storage._MEDIA_RECEIPTS.clear()
    try:
        database = storage._receipt_database()
        database.initialize()
        with database._conn() as conn:
            database._execute(conn, "DELETE FROM media_delete_receipts", ())
    except Exception:
        pass


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
    _reset_media_receipts()
    calls = []
    monkeypatch.setattr(storage.storage, "delete", lambda key: calls.append(key))
    first = storage.delete_media_with_receipt("subject", "objects/a.webp", "7")
    second = storage.delete_media_with_receipt("subject", "objects/a.webp", "7")
    assert first["status"] == "failed"
    assert second["status"] == "failed"
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
    _reset_media_receipts()
    calls = []
    def fail_once(key):
        calls.append(key)
        if len(calls) == 1:
            raise RuntimeError("temporary")
    monkeypatch.setattr(storage.storage, "delete", fail_once)
    first = storage.delete_media_with_receipt("subject-retry", "objects/retry.webp", cdn_purge=lambda key: None)
    second = storage.delete_media_with_receipt("subject-retry", "objects/retry.webp", cdn_purge=lambda key: None)
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
    _reset_media_receipts()
    import storage
    calls = []
    monkeypatch.setattr(storage.storage, "delete", lambda key: (_ for _ in ()).throw(RuntimeError("object")))
    result = storage.delete_media_with_receipt("u-cdn", "k", cdn_purge=lambda key: calls.append(key))
    assert result["status"] == "failed" and result["cdn_status"] == "deleted" and calls == ["k"]


def test_browser_inventory_includes_journey_thread():
    from control_plane.lifecycle import issue_browser_clear_instruction
    assert "vl360:journey-thread:v1" in issue_browser_clear_instruction("u")["keys"]


def test_media_without_cdn_adapter_is_not_verified(monkeypatch):
    import storage
    _reset_media_receipts()
    monkeypatch.setattr(storage.storage, "delete", lambda key: None)
    receipt = storage.delete_media_with_receipt("u-no-cdn", "k")
    assert receipt["cdn_status"] == "unavailable"
    assert receipt["status"] == "failed"


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


def test_legacy_orderings_include_ties_for_posts_blocks_and_mutes():
    from identity import api
    source = __import__("inspect").getsource(api.export_user_data)
    assert "p.created_at DESC, p.id DESC" in source
    assert "created_at DESC, blocked_id DESC" in source
    assert "created_at DESC, muted_id DESC" in source


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


def test_collection_items_export_uses_collection_owner_and_stable_page(monkeypatch):
    import control_plane.lifecycle as lifecycle

    class FakeDB:
        _use_pg = True
        _ph = "%s"

        def _conn(self):
            from contextlib import nullcontext
            return nullcontext(object())

        def _fetchall(self, _conn, sql, _params):
            assert "JOIN user_collections uc" in sql
            assert "ORDER BY ci.added_at DESC, ci.id DESC" in sql
            return [
                {"id": "2", "collection_id": "c", "post_id": "p2", "added_at": "2026-01-02"},
                {"id": "1", "collection_id": "c", "post_id": "p1", "added_at": "2026-01-01"},
            ]

        _row_to_dict = staticmethod(lambda row: row)

    monkeypatch.setattr(lifecycle, "db", FakeDB())
    rows, next_cursor, truncated, error = lifecycle._rows_for_table("collection_items", "u", None, 1)
    assert rows == [{"id": "2", "collection_id": "c", "post_id": "p2", "added_at": "2026-01-02"}]
    assert truncated is True and error is None
    assert lifecycle._decode_cursor(next_cursor)["sink"] == "collection_items"


def test_external_export_cursor_pages_local_adapter(monkeypatch):
    import sys
    import control_plane.lifecycle as lifecycle

    class Analytics:
        @staticmethod
        def export_owner_records(owner):
            assert owner == "user:u"
            return [{"id": "1"}, {"id": "2"}, {"id": "3"}]

    monkeypatch.setitem(sys.modules, "analytics", Analytics)
    rows, next_cursor, truncated, error, adapter = lifecycle._external_export("analytics-jsonl", "u", 1, "1")
    assert rows == [{"id": "2"}]
    assert lifecycle._decode_cursor(next_cursor) == 2
    assert truncated is True and error is None and adapter == "analytics"


def test_legacy_export_cursor_decodes_per_dataset():
    from identity.api import _legacy_cursor_offsets
    import control_plane.lifecycle as lifecycle
    token = lifecycle._encode_cursor('{"sink":"posts","offset":3}')
    assert _legacy_cursor_offsets(token, "posts") == 3
    assert _legacy_cursor_offsets(token, "comments") == 0


def test_legacy_manifest_counts_page_rows_and_signs_next_cursor(monkeypatch):
    from identity import api

    monkeypatch.setattr(api, "_EXPORT_CURSOR_SECRET", b"test-export-secret")
    raw = {"posts": [{"id": str(i)} for i in range(3)], "comments": []}
    manifest = api._build_legacy_manifest(raw, None, 2, "user-1")
    assert manifest["posts"]["count"] == 2
    assert manifest["posts"]["truncated"] is True
    signed = manifest["posts"]["next_cursor"]
    inner = api._verify_export_cursor(signed, "user-1")
    assert inner is not None
    assert api._legacy_cursor_offsets(inner, "posts") == 2


def test_export_cursor_provenance_rejects_forged_tokens():
    from identity.api import _verify_export_cursor, _sign_export_cursor
    signed = _sign_export_cursor("inner", "subject-1")
    assert _verify_export_cursor(signed, "subject-1") == "inner"
    assert _verify_export_cursor(signed, "subject-2") is None
    assert _verify_export_cursor("ZmFrZQ", "subject-1") is None


def test_export_inventory_declares_user_owned_secondary_sinks():
    import control_plane.lifecycle as lifecycle

    expected = {
        "event_rsvp", "notification_preferences", "comment_likes",
        "user_hidden_posts", "user_achievements", "profile_views",
        "user_preferences", "user_preference_consents",
        "user_personalization_events", "personalization_legacy_purge_queue",
    }
    assert expected <= set(lifecycle._TABLES)
    assert expected <= set(lifecycle._POSTGRES_EXTRA_OWNERS) | {"profile_views"}


def test_external_analytics_adapters_use_canonical_user_owner(monkeypatch):
    import control_plane.lifecycle as lifecycle
    observed = []

    class Analytics:
        @staticmethod
        def export_owner_records(owner):
            observed.append(("export", owner))
            return []

        @staticmethod
        def purge_owner_records(owner):
            observed.append(("erase", owner))
            return 0

    import sys
    monkeypatch.setitem(sys.modules, "analytics", Analytics)
    lifecycle._external_export("analytics-jsonl", "abc", 1)
    lifecycle._external_erase("analytics-jsonl", "abc", dry_run=False)
    assert observed == [("export", "user:abc"), ("erase", "user:abc")]


def test_browser_clear_issuance_has_unique_nonce_and_survives_fresh_lookup(
    isolated_sqlite_db, monkeypatch
):
    import control_plane.lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "db", isolated_sqlite_db)
    first = lifecycle.issue_browser_clear_instruction("user-1")
    second = lifecycle.issue_browser_clear_instruction("user-1")
    assert first["issuance_id"] != second["issuance_id"]
    lifecycle._BROWSER_PROOFS.clear()
    proof = lifecycle.get_browser_clear_instruction(first["issuance_id"])
    assert proof["subject_hash"] == first["subject_hash"]
    assert proof["issuance_id"] == first["issuance_id"]


def test_media_receipt_is_durable_after_process_cache_loss(isolated_sqlite_db, monkeypatch):
    import storage as storage_module

    monkeypatch.setattr(storage_module, "db", isolated_sqlite_db)
    isolated_sqlite_db.initialize()
    storage_module._MEDIA_RECEIPTS.clear()
    calls = []
    monkeypatch.setattr(storage_module.storage, "delete", lambda key: calls.append(key))
    first = storage_module.delete_media_with_receipt(
        "subject-durable", "objects/durable.webp", cdn_purge=lambda key: None
    )
    storage_module._MEDIA_RECEIPTS.clear()
    second = storage_module.delete_media_with_receipt(
        "subject-durable", "objects/durable.webp", cdn_purge=lambda key: None
    )
    assert first["status"] == "deleted"
    assert second["status"] == "deleted"
    assert calls == ["objects/durable.webp"]
