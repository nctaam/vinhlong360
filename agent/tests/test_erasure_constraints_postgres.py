"""Contracts for PostgreSQL user-FK action registration."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2 import sql
import pytest

try:
    from structured_references import (
        UnregisteredDeleteActionError,
        registered_delete_actions,
        validate_user_fk_actions,
    )
except ImportError:  # RED phase: the production module is not present yet.
    UnregisteredDeleteActionError = RuntimeError
    registered_delete_actions = None
    validate_user_fk_actions = None


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SQL = (
    ROOT / "agent" / "migrations" / "073_erasure_delete_actions.sql"
).read_text(encoding="utf-8")


class CatalogCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, _params=None):
        self.executed.append(" ".join(sql.split()))

    def fetchall(self):
        return list(self.rows)


class CatalogConnection:
    def __init__(self, rows):
        self.cursor_obj = CatalogCursor(rows)

    def cursor(self):
        return self.cursor_obj


def _row(table, column, action):
    return {
        "table_name": table,
        "column_name": column,
        "delete_action": action,
        "constraint_name": f"{table}_{column}_fkey",
    }


def test_registry_contains_owner_and_actor_inventory():
    assert callable(registered_delete_actions), "structured_references.py is not implemented"
    actions = {
        (item.table, item.column): (item.action, item.special_policy)
        for item in registered_delete_actions()
    }

    assert actions[("posts", "user_id")] == ("cascade", None)
    assert actions[("user_sessions", "user_id")] == ("cascade", None)
    assert actions[("blocks", "blocked_id")] == ("cascade", None)
    assert actions[("review_responses", "responder_id")] == ("cascade", None)
    assert actions[("entity_claims", "claimant_id")] == (
        "set_null",
        "completed_claim_scrub",
    )
    assert actions[("moderation_appeals", "user_id")] == (
        "set_null",
        "completed_appeal_scrub",
    )
    assert actions[("admin_user_notes", "admin_id")] == (
        "set_null",
        "actor_reference",
    )


def test_registry_matches_every_source_fk_to_users():
    assert callable(registered_delete_actions), "structured_references.py is not implemented"
    source_actions = set()
    for path in [ROOT / "init.sql", *sorted((ROOT / "agent" / "migrations").glob("*.sql"))]:
        current_table = None
        for line in path.read_text(encoding="utf-8").splitlines():
            create = re.search(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", line, re.I)
            if create:
                current_table = create.group(1)
            alter = re.search(
                r"ALTER TABLE\s+(\w+)\s+ADD COLUMN IF NOT EXISTS\s+(\w+).*REFERENCES\s+users",
                line,
                re.I,
            )
            if alter:
                source_actions.add((alter.group(1), alter.group(2)))
            if current_table and "REFERENCES users" in line:
                column = re.match(r"\s*(\w+)\s+", line)
                if column:
                    source_actions.add((current_table, column.group(1)))

    registered = {
        (policy.table, policy.column) for policy in registered_delete_actions()
    }
    assert registered == source_actions


def test_migration_inventory_matches_runtime_registry():
    assert callable(registered_delete_actions), "structured_references.py is not implemented"
    migration_actions = {
        (table, column): (
            action.lower().replace(" ", "_"),
            None if special == "NULL" else special.strip("'"),
        )
        for table, column, action, special in re.findall(
            r"\('([^']+)',\s*'([^']+)',\s*'(CASCADE|SET NULL)',\s*(NULL|'[^']+')\)",
            MIGRATION_SQL,
        )
    }
    registered = {
        (policy.table, policy.column): (policy.action, policy.special_policy)
        for policy in registered_delete_actions()
    }
    assert migration_actions == registered


def test_validate_accepts_only_registered_actions():
    assert callable(validate_user_fk_actions), "structured_references.py is not implemented"
    conn = CatalogConnection(
        [
            _row("posts", "user_id", "CASCADE"),
            _row("review_responses", "responder_id", "CASCADE"),
            _row("entity_claims", "claimant_id", "SET NULL"),
        ]
    )

    result = validate_user_fk_actions(conn)

    assert len(result) == 3
    assert any(item.table == "posts" for item in result)
    assert conn.cursor_obj.executed


def test_validate_rejects_unregistered_restrictive_action():
    assert callable(validate_user_fk_actions), "structured_references.py is not implemented"
    conn = CatalogConnection([_row("mystery_table", "user_id", "NO ACTION")])

    with pytest.raises(UnregisteredDeleteActionError, match="mystery_table.user_id"):
        validate_user_fk_actions(conn)


def _test_database_url() -> str | None:
    url = os.environ.get("TRUST_ERASURE_TEST_DATABASE_URL")
    if not url:
        return None
    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    explicitly_allowed = os.environ.get(
        "TRUST_ERASURE_ALLOW_PG_TESTS", ""
    ).lower() in {"1", "true", "yes", "on"}
    if parsed.scheme not in {"postgres", "postgresql"} or not database_name:
        raise pytest.UsageError(
            "TRUST_ERASURE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    if "test" not in database_name.lower() and not explicitly_allowed:
        raise pytest.UsageError(
            "PostgreSQL trust-erasure tests require a database name containing "
            "'test' or TRUST_ERASURE_ALLOW_PG_TESTS=true"
        )
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} and not explicitly_allowed:
        raise pytest.UsageError(
            "Non-loopback PostgreSQL trust-erasure tests require "
            "TRUST_ERASURE_ALLOW_PG_TESTS=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()


@pytest.fixture
def erasure_pg_schema():
    if TEST_DATABASE_URL is None:
        pytest.skip("set TRUST_ERASURE_TEST_DATABASE_URL to a disposable PostgreSQL DB")
    schema = f"erasure_{uuid.uuid4().hex}"
    conn = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{schema}"')
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.execute(
                """
                CREATE TABLE users (id UUID PRIMARY KEY, phone TEXT NOT NULL);
                CREATE TABLE schema_version (
                    component TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    migration TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE feedback (id BIGSERIAL PRIMARY KEY, user_id TEXT, query TEXT);
                CREATE TABLE posts (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id),
                    featured_by UUID REFERENCES users(id),
                    content TEXT NOT NULL,
                    mentions JSONB NOT NULL DEFAULT '[]'::jsonb
                );
                CREATE TABLE comments (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id),
                    content TEXT NOT NULL,
                    mentions JSONB NOT NULL DEFAULT '[]'::jsonb
                );
                CREATE TABLE follows (
                    follower_id UUID NOT NULL REFERENCES users(id),
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL
                );
                CREATE TABLE notifications (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id),
                    ref_type TEXT,
                    ref_id TEXT
                );
                CREATE TABLE reports (
                    id UUID PRIMARY KEY,
                    reporter_id UUID NOT NULL REFERENCES users(id),
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    reason TEXT NOT NULL
                );
                CREATE TABLE moderation_log (
                    id UUID PRIMARY KEY,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    moderator_id UUID REFERENCES users(id),
                    scores JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE entity_claims (
                    id UUID PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    claimant_id UUID NOT NULL REFERENCES users(id),
                    business_name TEXT NOT NULL,
                    contact_phone TEXT NOT NULL,
                    contact_email TEXT,
                    evidence TEXT,
                    status TEXT NOT NULL,
                    reviewer_id UUID REFERENCES users(id),
                    reviewer_note TEXT,
                    rejection_reason TEXT,
                    reviewed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE moderation_appeals (
                    id UUID PRIMARY KEY,
                    post_id UUID NOT NULL,
                    user_id UUID NOT NULL REFERENCES users(id),
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reviewer_id UUID REFERENCES users(id),
                    reviewer_note TEXT,
                    reviewed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE review_responses (
                    id UUID PRIMARY KEY,
                    responder_id UUID NOT NULL REFERENCES users(id),
                    content TEXT NOT NULL
                );
                CREATE TABLE admin_audit_events (
                    id UUID PRIMARY KEY,
                    actor TEXT NOT NULL,
                    actor_role TEXT,
                    actor_scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    ip TEXT,
                    reason TEXT,
                    before_json JSONB,
                    after_json JSONB,
                    meta JSONB DEFAULT '{}'::jsonb
                );
                CREATE TABLE entity_changes (id BIGSERIAL PRIMARY KEY, actor TEXT);
                CREATE TABLE site_settings_history (id TEXT PRIMARY KEY, actor TEXT);
                """
            )
            cursor.execute(MIGRATION_SQL)
        conn.commit()
        yield conn
    finally:
        conn.rollback()
        with conn.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.commit()
        conn.close()


def test_real_postgres_migration_covers_full_registered_fk_catalog():
    if TEST_DATABASE_URL is None:
        pytest.skip("set TRUST_ERASURE_TEST_DATABASE_URL to a disposable PostgreSQL DB")

    schema = f"erasure_catalog_{uuid.uuid4().hex}"
    conn = psycopg2.connect(TEST_DATABASE_URL)
    try:
        policies = registered_delete_actions()
        columns_by_table: dict[str, set[str]] = {}
        for policy in policies:
            columns_by_table.setdefault(policy.table, set()).add(policy.column)

        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            cursor.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(schema))
            )
            cursor.execute(
                """
                CREATE TABLE users (id UUID PRIMARY KEY);
                CREATE TABLE schema_version (
                    component TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    migration TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            required_columns = {
                "entity_claims": {
                    "business_name": "TEXT NOT NULL",
                    "contact_phone": "TEXT NOT NULL",
                },
                "moderation_appeals": {"reason": "TEXT NOT NULL"},
                "moderation_log": {"target_id": "TEXT NOT NULL"},
                "admin_audit_events": {"actor": "TEXT NOT NULL"},
            }
            for table, columns in sorted(columns_by_table.items()):
                definitions = [
                    sql.SQL("{} UUID NOT NULL REFERENCES users(id)").format(
                        sql.Identifier(column)
                    )
                    for column in sorted(columns)
                ]
                definitions.extend(
                    sql.SQL("{} {}").format(
                        sql.Identifier(column), sql.SQL(column_type)
                    )
                    for column, column_type in required_columns.get(table, {}).items()
                    if column not in columns
                )
                cursor.execute(
                    sql.SQL("CREATE TABLE {} ({})").format(
                        sql.Identifier(table), sql.SQL(", ").join(definitions)
                    )
                )

            cursor.execute(MIGRATION_SQL)
        conn.commit()

        observed = validate_user_fk_actions(conn)
        assert {
            (policy.table, policy.column, policy.action) for policy in observed
        } == {
            (policy.table, policy.column, policy.action) for policy in policies
        }
        assert len(observed) == 45
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT version, migration FROM schema_version WHERE component = 'agent'"
            )
            assert cursor.fetchone() == (73, "073_erasure_delete_actions.sql")
    finally:
        conn.rollback()
        with conn.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )
        conn.commit()
        conn.close()


def test_real_postgres_migration_and_exact_sentinel_cleanup(erasure_pg_schema):
    from structured_references import scrub_user_references

    conn = erasure_pg_schema
    user_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    post_id = str(uuid.uuid4())
    comment_id = str(uuid.uuid4())
    preserved_text = f"literal text keeps {user_id}"
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (id, phone) VALUES (%s, 'owner'), (%s, 'other')",
            (user_id, other_id),
        )
        cursor.execute(
            "INSERT INTO posts (id, user_id, content, mentions) VALUES (%s, %s, %s, %s::jsonb)",
            (
                post_id,
                other_id,
                preserved_text,
                json.dumps([
                    {"type": "user", "id": user_id},
                    {"type": "user", "id": other_id},
                ]),
            ),
        )
        cursor.execute(
            "INSERT INTO comments (id, user_id, content, mentions) VALUES (%s, %s, %s, %s::jsonb)",
            (
                comment_id,
                other_id,
                preserved_text,
                json.dumps([
                    {"type": "entity", "id": user_id},
                    {"type": "user", "id": user_id},
                ]),
            ),
        )
        cursor.execute(
            "INSERT INTO follows (follower_id, target_type, target_id) VALUES (%s, 'user', %s)",
            (other_id, user_id),
        )
        cursor.execute(
            "INSERT INTO notifications (id, user_id, ref_type, ref_id) VALUES (%s, %s, 'user', %s)",
            (str(uuid.uuid4()), other_id, user_id),
        )
        cursor.execute(
            "INSERT INTO reports (id, reporter_id, target_type, target_id, reason) VALUES (%s, %s, 'user', %s, 'reason')",
            (str(uuid.uuid4()), other_id, user_id),
        )
        cursor.execute(
            "INSERT INTO moderation_log (id, target_type, target_id, action, moderator_id) VALUES (%s, 'user', %s, 'ban', %s)",
            (str(uuid.uuid4()), user_id, user_id),
        )
        cursor.execute(
            """
            INSERT INTO entity_claims
                (id, entity_id, claimant_id, business_name, contact_phone,
                 contact_email, evidence, status, reviewer_id, reviewer_note)
            VALUES
                (%s, 'pending-entity', %s, 'Pending', '0900', 'p@example.test', 'proof', 'pending', NULL, NULL),
                (%s, 'completed-entity', %s, 'Completed', '0901', 'c@example.test', 'proof', 'approved', %s, 'note'),
                (%s, 'other-entity', %s, 'Other', '0902', 'o@example.test', 'keep-proof', 'approved', %s, 'clear-note')
            """,
            (
                str(uuid.uuid4()), user_id,
                str(uuid.uuid4()), user_id, other_id,
                str(uuid.uuid4()), other_id, user_id,
            ),
        )
        cursor.execute(
            """
            INSERT INTO moderation_appeals
                (id, post_id, user_id, reason, status, reviewer_id, reviewer_note)
            VALUES
                (%s, %s, %s, 'pending reason', 'pending', NULL, NULL),
                (%s, %s, %s, 'completed reason', 'approved', %s, 'note')
            """,
            (
                str(uuid.uuid4()), str(uuid.uuid4()), user_id,
                str(uuid.uuid4()), str(uuid.uuid4()), user_id, other_id,
            ),
        )
        cursor.execute(
            "INSERT INTO review_responses (id, responder_id, content) VALUES (%s, %s, 'owned response')",
            (str(uuid.uuid4()), user_id),
        )
        cursor.execute(
            "INSERT INTO admin_audit_events (id, actor, method, path, reason) VALUES (%s, %s, 'POST', '/admin/x', 'private')",
            (str(uuid.uuid4()), user_id),
        )
        cursor.execute("INSERT INTO entity_changes (actor) VALUES (%s)", (user_id,))
        cursor.execute(
            "INSERT INTO site_settings_history (id, actor) VALUES ('history-1', %s)",
            (user_id,),
        )

    policies = validate_user_fk_actions(conn)
    assert policies
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'moderation_appeals'
              AND column_name = 'reason'
            """
        )
        assert cursor.fetchone() == ("YES",)
    summary = scrub_user_references(conn, user_id, actor_policy="set_null")
    assert summary.mentions_removed == 2

    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        cursor.execute("SELECT content, mentions FROM posts WHERE id = %s", (post_id,))
        content, mentions = cursor.fetchone()
        assert content == preserved_text
        assert mentions == [{"type": "user", "id": other_id}]
        cursor.execute("SELECT content, mentions FROM comments WHERE id = %s", (comment_id,))
        content, mentions = cursor.fetchone()
        assert content == preserved_text
        assert mentions == [{"type": "entity", "id": user_id}]
        cursor.execute("SELECT COUNT(*) FROM follows WHERE target_id = %s", (user_id,))
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT COUNT(*) FROM reports WHERE target_id = %s", (user_id,))
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "SELECT claimant_id, reviewer_id, business_name, contact_phone, contact_email, evidence, reviewer_note FROM entity_claims WHERE entity_id = 'completed-entity'"
        )
        assert cursor.fetchone() == (None, None, None, None, None, None, None)
        cursor.execute(
            "SELECT claimant_id::text, reviewer_id, business_name, evidence, reviewer_note FROM entity_claims WHERE entity_id = 'other-entity'"
        )
        assert cursor.fetchone() == (other_id, None, "Other", "keep-proof", None)
        cursor.execute("SELECT COUNT(*) FROM review_responses")
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT actor, reason FROM admin_audit_events")
        assert cursor.fetchone() == (None, None)
