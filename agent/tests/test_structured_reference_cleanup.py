"""Contracts for exact PostgreSQL reference cleanup."""

from __future__ import annotations

import json

import pytest

try:
    from structured_references import scrub_user_references
except ImportError:  # RED phase: the production module is not present yet.
    scrub_user_references = None


USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_ID = "00000000-0000-0000-0000-000000000002"


class ScriptedCursor:
    def __init__(self, *, rows_by_query=None, rowcount_by_query=None):
        self.rows_by_query = rows_by_query or {}
        self.rowcount_by_query = rowcount_by_query or {}
        self.statements: list[tuple[str, tuple | None]] = []
        self.rowcount = 0
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.statements.append((normalized, params))
        self._rows = self.rows_by_query.get(normalized, [])
        self.rowcount = self.rowcount_by_query.get(normalized, 0)
        for fragment, rows in self.rows_by_query.items():
            if fragment in normalized:
                self._rows = rows
        for fragment, count in self.rowcount_by_query.items():
            if fragment in normalized:
                self.rowcount = count

    def fetchall(self):
        return list(self._rows)


class ScriptedConnection:
    def __init__(self, **kwargs):
        self.cursor_obj = ScriptedCursor(**kwargs)

    def cursor(self):
        return self.cursor_obj


def _find_statement(conn, fragment: str):
    return next(item for item in conn.cursor_obj.statements if fragment in item[0])


def test_scrub_removes_only_exact_structured_references_and_claim_pii():
    assert callable(scrub_user_references), "structured_references.py is not implemented"
    post_id = "post-1"
    comment_id = "comment-1"
    conn = ScriptedConnection(
        rows_by_query={
            "SELECT id, mentions FROM posts": [
                (
                    post_id,
                    [
                        {"type": "user", "id": USER_ID, "label": "owner"},
                        {"type": "user", "id": OTHER_ID, "label": "keep"},
                    ],
                )
            ],
            "SELECT id, mentions FROM comments": [
                (
                    comment_id,
                    [
                        {"type": "entity", "id": USER_ID},
                        {"type": "user", "id": USER_ID},
                    ],
                )
            ],
        },
        rowcount_by_query={
            "UPDATE posts SET mentions": 1,
            "UPDATE comments SET mentions": 1,
            "DELETE FROM feedback": 2,
            "DELETE FROM follows": 1,
            "UPDATE notifications SET ref_type": 1,
            "DELETE FROM reports": 1,
            "UPDATE moderation_log SET target_id": 1,
            "DELETE FROM entity_claims WHERE status = 'pending'": 1,
            "UPDATE entity_claims SET claimant_id": 1,
            "DELETE FROM moderation_appeals WHERE status = 'pending'": 1,
            "UPDATE moderation_appeals SET user_id": 1,
            "UPDATE admin_audit_events SET actor": 1,
            "UPDATE entity_changes SET actor": 1,
            "UPDATE site_settings_history SET actor": 1,
        },
    )

    summary = scrub_user_references(conn, USER_ID, actor_policy="set_null")

    assert summary.deleted_rows >= 5
    assert summary.updated_rows >= 7
    post_update = _find_statement(conn, "UPDATE posts SET mentions")
    comment_update = _find_statement(conn, "UPDATE comments SET mentions")
    assert json.loads(post_update[1][0]) == [
        {"type": "user", "id": OTHER_ID, "label": "keep"}
    ]
    assert json.loads(comment_update[1][0]) == [{"type": "entity", "id": USER_ID}]

    follows = _find_statement(conn, "DELETE FROM follows")
    assert follows[1] == (USER_ID, USER_ID)
    notifications = _find_statement(conn, "UPDATE notifications SET ref_type")
    assert notifications[1] == (USER_ID,)
    reports = _find_statement(conn, "DELETE FROM reports")
    assert reports[1] == (USER_ID, USER_ID)

    all_sql = "\n".join(sql for sql, _params in conn.cursor_obj.statements)
    assert "REPLACE(" not in all_sql.upper()
    assert "LIKE" not in all_sql.upper()
    assert "REGEXP" not in all_sql.upper()


def test_scrub_rejects_unknown_actor_policy_before_mutating():
    assert callable(scrub_user_references), "structured_references.py is not implemented"
    conn = ScriptedConnection()

    with pytest.raises(ValueError, match="actor_policy"):
        scrub_user_references(conn, USER_ID, actor_policy="replace-everything")

    assert conn.cursor_obj.statements == []
