from __future__ import annotations

from datetime import datetime, timezone

import pytest


def test_publication_generation_bump_is_transactional_and_notifies_after_commit(monkeypatch):
    import cases.publication as publication
    from control_plane.snapshot import SnapshotRef

    calls: list[tuple] = []

    class Transaction:
        _conn = object()

        def __init__(self):
            self.callbacks = []

        def on_commit(self, callback):
            self.callbacks.append(callback)

    transaction = Transaction()
    ref = SnapshotRef("entity-1", 4, datetime(2026, 9, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(
        publication,
        "bump_generation",
        lambda conn, entity_id, reason, correlation_id: calls.append(
            ("bump", conn, entity_id, reason, correlation_id)
        ) or ref,
    )
    monkeypatch.setattr(
        publication,
        "invalidate_entity",
        lambda entity_id, **kwargs: calls.append(("invalidate", entity_id, kwargs)),
    )

    result = publication._advance_entity_generation(
        transaction, "entity-1", reason="correction-apply", correlation_id="corr-1"
    )

    assert result == ref
    assert calls == [("bump", transaction._conn, "entity-1", "correction-apply", "corr-1")]
    assert len(transaction.callbacks) == 1

    transaction.callbacks[0]()
    assert calls[-1] == ("invalidate", "entity-1", {"reason": "correction-apply", "generation": 4})


def test_case_transaction_patch_bumps_once_and_defers_invalidation(monkeypatch):
    import cases.store as store
    from entity_write import EntityWriteResult
    from control_plane.snapshot import SnapshotRef

    calls: list[tuple] = []
    ref = SnapshotRef("entity-1", 5, datetime(2026, 9, 1, tzinfo=timezone.utc))

    class Writer:
        def __init__(self, _database):
            pass

        def apply_patch(self, *args, **kwargs):
            return EntityWriteResult(
                entity_id="entity-1", revision=8, changed_fields=("summary",),
                before={"summary": "old"}, after={"summary": "new"},
            )

        def write_change_audit(self, *args, **kwargs):
            pass

    monkeypatch.setattr(store._entity_write, "EntityWriteService", Writer)
    monkeypatch.setattr(
        store, "bump_generation",
        lambda conn, entity_id, reason, correlation_id: calls.append(
            ("bump", conn, entity_id, reason, correlation_id)
        ) or ref,
    )
    monkeypatch.setattr(
        store, "invalidate_entity",
        lambda entity_id, **kwargs: calls.append(("invalidate", entity_id, kwargs)),
    )

    tx = store.CaseTransaction(object(), object())
    result = tx.apply_entity_patch(
        "entity-1", {"summary": "new"}, expected_revision=7,
        actor="person:publisher", provenance="correction-apply",
    )

    assert result.changed_fields == ("summary",)
    assert calls == [("bump", tx._conn, "entity-1", "correction-apply", "person:publisher")]
    assert tx._after_commit
    tx._run_after_commit()
    assert calls[-1] == ("invalidate", "entity-1", {"reason": "correction-apply", "generation": 5})
    tx._run_after_commit()
    assert calls.count(("invalidate", "entity-1", {"reason": "correction-apply", "generation": 5})) == 1


def test_case_transaction_noop_patch_does_not_bump_generation(monkeypatch):
    import cases.store as store
    from entity_write import EntityWriteResult

    calls: list[tuple] = []

    class Writer:
        def __init__(self, _database):
            pass

        def apply_patch(self, *args, **kwargs):
            return EntityWriteResult(
                entity_id="entity-1", revision=7, changed_fields=(),
                before={"summary": "same"}, after={"summary": "same"},
            )

        def write_change_audit(self, *args, **kwargs):
            pass

    monkeypatch.setattr(store._entity_write, "EntityWriteService", Writer)
    monkeypatch.setattr(store, "bump_generation", lambda *args: calls.append("bump"))
    tx = store.CaseTransaction(object(), object())
    tx.apply_entity_patch(
        "entity-1", {"summary": "same"}, expected_revision=7,
        actor="person:publisher", provenance="correction-apply",
    )
    assert calls == []
    assert tx._after_commit == []


def test_case_transaction_discards_callbacks_when_commit_fails():
    import cases.store as store
    from contextlib import contextmanager

    seen: list[str] = []

    class Connection:
        def commit(self):
            raise RuntimeError("commit failed")

    class FakeDatabase:
        _use_pg = True

        @contextmanager
        def _conn(self, **_kwargs):
            yield Connection()

    with pytest.raises(RuntimeError, match="commit failed"):
        with store.PostgresCaseStore(FakeDatabase()).transaction() as transaction:
            transaction.on_commit(lambda: seen.append("ran"))
            retained = transaction

    assert seen == []
    assert retained._after_commit == []
