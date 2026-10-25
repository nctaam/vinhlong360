"""Entity snapshot generations and one invalidation registry.

The process-local adapter keeps SQLite/tests useful while the SQL path uses an
atomic PostgreSQL ``UPDATE ... RETURNING`` against ``entity_snapshot_generation``.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .clock import system_clock


@dataclass(frozen=True)
class SnapshotRef:
    entity_id: str
    generation: int
    issued_at: datetime


class InvalidationRegistry:
    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[[str, int], object]] = {}
        self._lock = threading.RLock()

    def register(self, name: str, callback: Callable[[str, int], object]) -> None:
        with self._lock:
            self._callbacks[name] = callback

    def unregister(self, name: str) -> None:
        with self._lock:
            self._callbacks.pop(name, None)

    def invalidate(self, entity_id: str, generation: int) -> None:
        with self._lock:
            callbacks = list(self._callbacks.values())
        for callback in callbacks:
            try:
                callback(entity_id, generation)
            except TypeError:
                # Compatibility with zero-argument cache clear callbacks.
                callback()

    @property
    def names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._callbacks)


registry = InvalidationRegistry()
_generations: dict[str, int] = {}
_lock = threading.RLock()


def register_invalidator(name: str, callback: Callable[[str, int], object]) -> None:
    registry.register(name, callback)


def _query_durable_generation(eid: str) -> int | None:
    try:
        from database import db
        db.initialize()
        with db._conn(commit_on_success=False) as conn:
            row = db._fetchone(
                conn,
                f"SELECT generation FROM entity_snapshot_generation WHERE entity_id = {db._ph}",
                (eid,),
            )
        if row is not None:
            return int(row["generation"] if isinstance(row, dict) else row[0])
        return 0
    except Exception:
        return None


def current_generation(entity_id: str) -> int:
    eid = str(entity_id)
    with _lock:
        if eid in _generations:
            return int(_generations[eid])
    # Recover the durable generation after process restart when the DB adapter
    # is available; failures remain safe for lightweight local/test adapters.
    value = _query_durable_generation(eid)
    if value is not None:
        with _lock:
            return int(_generations.setdefault(eid, value))
    return 0


def _postgres_backend(transaction) -> tuple[bool, str]:
    """Resolve PG-ness and placeholder style through adapters, not module names."""
    candidates = [transaction]
    connection = getattr(transaction, "_conn", None)
    if connection is not None:
        candidates.append(connection)
    database = getattr(transaction, "_db", None)
    if database is not None:
        candidates.append(database)
    for candidate in candidates:
        if candidate is None:
            continue
        if getattr(candidate, "_use_pg", False):
            return True, str(getattr(candidate, "_ph", "%s"))
        ph = getattr(candidate, "_ph", None)
        if ph in {"%s", "%(name)s"}:
            return True, str(ph)
        module = str(getattr(candidate.__class__, "__module__", ""))
        if module.startswith(("psycopg2", "psycopg")):
            return True, "%s"
        paramstyle = str(getattr(candidate, "paramstyle", ""))
        if paramstyle in {"pyformat", "format"}:
            return True, "%s"
    return False, "?"


def _sql_bump(transaction, entity_id: str):
    """Try the shared SQL adapter; return ``(generation, issued_at)`` or None."""
    use_pg, ph = _postgres_backend(transaction)
    now = system_clock.now_utc()
    stored_now = now.isoformat()
    try:
        cursor = transaction
        if not hasattr(cursor, "execute") and hasattr(transaction, "cursor"):
            cursor = transaction.cursor()
        cursor.execute(
            f"INSERT INTO entity_snapshot_generation (entity_id, generation, issued_at) "
            f"VALUES ({ph}, 0, {ph}) ON CONFLICT (entity_id) DO NOTHING",
            (str(entity_id), stored_now),
        )
        cursor.execute(
            f"UPDATE entity_snapshot_generation SET generation = generation + 1, issued_at = {ph} "
            f"WHERE entity_id = {ph} RETURNING generation, issued_at",
            (stored_now, str(entity_id)),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            generation, issued_at = row["generation"], row.get("issued_at")
        else:
            generation, issued_at = row[0], row[1]
        return int(generation), issued_at or now
    except Exception:
        if use_pg:
            raise
        return None


def bump_generation(transaction, entity_id: str, reason: str, correlation_id: str) -> SnapshotRef:
    """Atomically advance an entity generation and return its immutable ref."""
    del reason, correlation_id  # metadata is carried by the caller's audit row
    eid = str(entity_id)
    sql_result = _sql_bump(transaction, eid) if transaction is not None else None
    if sql_result is None:
        with _lock:
            generation = _generations.get(eid, 0) + 1
            _generations[eid] = generation
        issued_at = system_clock.now_utc()
    else:
        generation, issued_at = sql_result
        with _lock:
            _generations[eid] = generation
        if not isinstance(issued_at, datetime):
            issued_at = system_clock.now_utc()
        elif issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        else:
            issued_at = issued_at.astimezone(timezone.utc)
    return SnapshotRef(eid, generation, issued_at)


def invalidate_entity(entity_id: str, *, reason: str, generation: int | None = None) -> SnapshotRef:
    """Advance (or adopt) a generation and notify every registered consumer."""
    eid = str(entity_id)
    if generation is None:
        ref = bump_generation(None, eid, reason, str(uuid.uuid4()))
    else:
        with _lock:
            _generations[eid] = max(int(generation), _generations.get(eid, 0))
        ref = SnapshotRef(eid, int(generation), system_clock.now_utc())
    registry.invalidate(ref.entity_id, ref.generation)
    return ref


def invalidate_all(*, reason: str = "global") -> None:
    """Notify consumers for every known entity without burning generations."""
    del reason
    with _lock:
        items = tuple(_generations.items())
    for entity_id, generation in items:
        registry.invalidate(entity_id, generation)


def _clear_knowledge(entity_id: str, _generation: int) -> None:
    try:
        import knowledge
        knowledge.sync_entity(entity_id)
    except Exception:
        pass


def _clear_seo(_entity_id: str, _generation: int) -> None:
    try:
        import seo
        seo.invalidate_db_snapshot()
    except Exception:
        pass


def _clear_l1(_entity_id: str, _generation: int) -> None:
    try:
        import cache
        cache.invalidate_all()
    except Exception:
        pass


def _clear_redis(_entity_id: str, _generation: int) -> None:
    # Covered by _clear_l1's cache.invalidate_all(); kept registered for
    # consumer-name contract compatibility without double-flushing Redis.
    return None


def _clear_l2(entity_id: str, _generation: int) -> None:
    try:
        import semantic_cache
        semantic_cache.multi_tier_cache.invalidate_entity(entity_id)
    except Exception:
        pass


def _clear_review(entity_id: str, _generation: int) -> None:
    try:
        from entities import api
        api._REVIEW_STATS_CACHE.pop(entity_id, None)
    except Exception:
        pass


def _clear_similar(entity_id: str, _generation: int) -> None:
    try:
        from entities import api
        prefix = f"{entity_id}:"
        for key in tuple(api._similar_cache):
            if str(key).startswith(prefix):
                api._similar_cache.pop(key, None)
    except Exception:
        pass


def _clear_kb(_entity_id: str, _generation: int) -> None:
    try:
        import kb_context
        kb_context.invalidate()
    except Exception:
        pass


def _clear_place(_entity_id: str, _generation: int) -> None:
    try:
        import entity_read
        entity_read.invalidate_place_cache()
    except Exception:
        pass


def _clear_homepage(_entity_id: str, _generation: int) -> None:
    try:
        import public_api
        public_api._homepage_cache.update(month=None, data=None, ts=0.0)
    except Exception:
        pass


_DEFAULT_CONSUMERS: tuple[tuple[str, Callable[[str, int], object]], ...] = (
    ("l1", _clear_l1),
    ("l2", _clear_l2),
    ("redis", _clear_redis),
    ("review_stats", _clear_review),
    ("similar", _clear_similar),
    ("kb_context", _clear_kb),
    ("place", _clear_place),
    ("homepage", _clear_homepage),
    ("knowledge", _clear_knowledge),
    ("seo", _clear_seo),
)


def _register_default_consumers() -> None:
    """Register cache consumers without importing their heavyweight modules."""
    for name, callback in _DEFAULT_CONSUMERS:
        register_invalidator(name, callback)


_register_default_consumers()
