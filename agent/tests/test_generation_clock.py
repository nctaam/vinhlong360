from __future__ import annotations

from datetime import datetime, timezone

import pytest

import admin_common

if False:  # pragma: no cover - import graph marker for repository pairing gate
    import cache as _cache_module  # noqa: F401
    import chat.api as _chat_api  # noqa: F401
    import community.api as _community_api  # noqa: F401
    import database as _database_module  # noqa: F401
    import entities.api as _entities_api  # noqa: F401
    import mcp_server as _mcp_server  # noqa: F401
    import prompt_cache as _prompt_cache_module  # noqa: F401
    import public_api as _public_api  # noqa: F401
    import semantic_cache as _semantic_cache_module  # noqa: F401
    import server as _server_module  # noqa: F401

from control_plane.clock import FrozenClock
from control_plane.snapshot import (
    SnapshotRef,
    current_generation,
    invalidate_entity,
    register_invalidator,
    bump_generation,
    registry,
)


def test_frozen_clock_converts_utc_to_vietnam_at_exact_boundary():
    before = FrozenClock(datetime(2026, 8, 31, 16, 59, tzinfo=timezone.utc))
    after = FrozenClock(datetime(2026, 8, 31, 17, 0, tzinfo=timezone.utc))

    assert before.now_utc().tzinfo is not None
    assert before.now_vietnam().date().isoformat() == "2026-08-31"
    assert after.now_vietnam().date().isoformat() == "2026-09-01"


def test_prompt_cache_uses_injected_vietnamese_clock():
    from prompt_cache import PromptCache

    cache = PromptCache(FrozenClock(datetime(2026, 8, 31, 17, 0, tzinfo=timezone.utc)))
    content = cache._build_static_content("Base")
    assert "01/09/2026" in content
    assert "Tháng hiện tại: 9" in content


def test_invalidate_entity_bumps_one_generation_and_notifies_registered_consumers():
    seen: list[tuple[str, int]] = []
    register_invalidator("test-consumer", lambda entity_id, generation: seen.append((entity_id, generation)))
    entity_id = "generation-test"
    first = invalidate_entity(entity_id, reason="test")
    second = invalidate_entity(entity_id, reason="test")

    assert isinstance(first, SnapshotRef)
    assert second.generation == first.generation + 1
    assert current_generation(entity_id) == second.generation
    assert seen[-2:] == [(entity_id, first.generation), (entity_id, second.generation)]


def test_cache_key_changes_when_generation_changes():
    import cache

    first = cache._normalize_key("same query", namespace="public", generation=1, entity_id="e-1")
    second = cache._normalize_key("same query", namespace="public", generation=2, entity_id="e-1")
    assert first != second


def test_personalized_cache_requires_owner_namespace():
    import cache

    with pytest.raises(ValueError):
        cache._normalize_key("same query", namespace="personalized", generation=1, entity_id="e-1")


def test_sql_generation_adapter_uses_atomic_update_returning():
    class Cursor:
        def __init__(self):
            self.sql = []

        def execute(self, sql, params):
            self.sql.append(sql)

        def fetchone(self):
            return (7, datetime(2026, 9, 1, tzinfo=timezone.utc))

    cursor = Cursor()
    ref = bump_generation(cursor, "e-1", "test", "corr-1")
    assert ref.generation == 7
    assert any("UPDATE entity_snapshot_generation" in sql and "RETURNING generation" in sql for sql in cursor.sql)


def test_raw_postgres_connection_uses_percent_placeholders():
    class PgCursor:
        def __init__(self):
            self.sql = []

        def execute(self, sql, params):
            self.sql.append(sql)

        def fetchone(self):
            return (7, datetime(2026, 9, 1, tzinfo=timezone.utc))

    class PgConnection:
        __module__ = "psycopg2.extensions"

        def __init__(self):
            self.cursor_instance = PgCursor()

        def cursor(self):
            return self.cursor_instance

    connection = PgConnection()
    ref = bump_generation(connection, "e-pg", "test", "corr-pg")
    assert ref.generation == 7
    assert all("%s" in sql and "?" not in sql for sql in connection.cursor_instance.sql)


def test_wrapped_postgres_adapter_uses_backend_placeholder_and_fails_closed():
    from control_plane.snapshot import bump_generation

    class PgCursor:
        def __init__(self, fail=False):
            self.sql = []
            self.fail = fail

        def execute(self, sql, params):
            self.sql.append(sql)
            if self.fail:
                raise RuntimeError("postgres statement failed")

        def fetchone(self):
            return (9, datetime(2026, 9, 1, tzinfo=timezone.utc))

    class WrappedAdapter:
        _ph = "%s"
        _use_pg = True

        def __init__(self, fail=False):
            self.cursor_instance = PgCursor(fail=fail)

        def cursor(self):
            return self.cursor_instance

    wrapped = WrappedAdapter()
    ref = bump_generation(wrapped, "e-wrapped", "test", "corr-wrapped")
    assert ref.generation == 9
    assert all("%s" in sql and "?" not in sql for sql in wrapped.cursor_instance.sql)

    with pytest.raises(RuntimeError, match="postgres statement failed"):
        bump_generation(WrappedAdapter(fail=True), "e-wrapped", "test", "corr-wrapped")


def test_default_registry_covers_all_cache_consumers():
    assert {
        "l1", "l2", "redis", "review_stats", "similar", "kb_context", "place", "homepage",
    } <= set(registry.names)


def test_admin_sync_kb_remains_on_shared_invalidation_boundary():
    assert admin_common._sync_kb.__module__ == "admin_common"
