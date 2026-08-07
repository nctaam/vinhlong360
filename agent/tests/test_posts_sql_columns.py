"""Every column an endpoint SELECTs from `posts` must exist in the real schema.

Why this test exists: four endpoints queried `p.title`, a column `posts` has
never had.  SQLite-backed local runs never noticed (those code paths are
Postgres-only and short-circuit on `_use_pg`), so the queries only blew up as
`UndefinedColumn` 500s on production Postgres — including on the PUBLIC
endpoint /api/feed/new-since.

There is no local Postgres in the dev loop, so instead of executing the SQL we
*capture the SQL each endpoint actually builds at runtime* (driving it through
the real HTTP stack with the DB layer stubbed into Postgres mode) and check
every `posts` column reference against the schema parsed from the deployment
artefacts CI applies: init.sql + agent/migrations/*.sql.

This is a behaviour test, not a source-string test: it fails only if a running
endpoint emits SQL naming a column Postgres would reject.
"""
import contextlib
import os
import pathlib
import re
import sys

import pytest

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-posts-sql")
os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

AGENT_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = AGENT_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402

client = TestClient(app)
H = {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}

_CONSTRAINT_WORDS = {
    "constraint", "primary", "foreign", "unique", "check", "exclude", "like",
}


def _posts_columns() -> set[str]:
    """Parse the live `posts` schema from init.sql + migrations (same as CI applies)."""
    init_sql = (ROOT / "init.sql").read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS posts\s*\((.*?)\n\);",
        init_sql,
        re.DOTALL | re.IGNORECASE,
    )
    assert match, "Could not locate the CREATE TABLE posts block in init.sql"

    columns: set[str] = set()
    depth = 0
    for raw in match.group(1).splitlines():
        line = raw.strip()
        # only consider lines at paren depth 0 (skips CHECK (...) continuations)
        at_top = depth == 0
        depth += line.count("(") - line.count(")")
        if not at_top or not line or line.startswith("--"):
            continue
        name = line.split()[0].strip('",')
        if name.lower() in _CONSTRAINT_WORDS:
            continue
        columns.add(name.lower())

    for path in sorted((AGENT_DIR / "migrations").glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        for col in re.findall(
            r"ALTER TABLE\s+posts\s+ADD COLUMN\s+(?:IF NOT EXISTS\s+)?(\w+)", sql, re.IGNORECASE
        ):
            columns.add(col.lower())
        for col in re.findall(
            r"ALTER TABLE\s+posts\s+DROP COLUMN\s+(?:IF EXISTS\s+)?(\w+)", sql, re.IGNORECASE
        ):
            columns.discard(col.lower())
    return columns


def _posts_column_refs(sql: str) -> set[str]:
    """Columns this statement reads off the `posts` table, via alias or bare name."""
    flat = " ".join(sql.split())
    aliases = {
        alias.lower()
        for alias in re.findall(
            r"\b(?:FROM|JOIN|UPDATE|INTO)\s+posts\s+(?:AS\s+)?(?!WHERE\b|SET\b|ON\b|USING\b|GROUP\b|ORDER\b|LIMIT\b|RETURNING\b|VALUES\b|SELECT\b|LEFT\b|RIGHT\b|INNER\b|JOIN\b|WHERE\b)([a-z_][a-z0-9_]*)",
            flat,
            re.IGNORECASE,
        )
    }
    if re.search(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+posts\b", flat, re.IGNORECASE):
        aliases.add("posts")

    refs: set[str] = set()
    for alias in aliases:
        refs.update(
            m.lower()
            for m in re.findall(rf"\b{re.escape(alias)}\.([a-z_][a-z0-9_]*)", flat, re.IGNORECASE)
        )
    return refs


class _SQLRecorder:
    """Stands in for the Postgres driver and remembers every statement issued."""

    def __init__(self):
        self.statements: list[str] = []

    def _record(self, sql):
        self.statements.append(" ".join(str(sql).split()))

    def fetchall(self, conn, sql, params=None):
        self._record(sql)
        return []

    def fetchone(self, conn, sql, params=None):
        self._record(sql)
        return None

    def execute(self, conn, sql, params=None):
        self._record(sql)
        return self

    def posts_refs(self) -> dict[str, set[str]]:
        return {sql: _posts_column_refs(sql) for sql in self.statements if _posts_column_refs(sql)}


@pytest.fixture
def pg_sql_recorder(monkeypatch):
    """Force the shared DB adapter into Postgres mode with a recording driver."""
    from database import db

    recorder = _SQLRecorder()

    @contextlib.contextmanager
    def _fake_conn(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(db, "_use_pg", True, raising=False)
    monkeypatch.setattr(db, "_conn", _fake_conn, raising=False)
    monkeypatch.setattr(db, "_fetchall", recorder.fetchall, raising=False)
    monkeypatch.setattr(db, "_fetchone", recorder.fetchone, raising=False)
    monkeypatch.setattr(db, "_execute", recorder.execute, raising=False)
    return recorder


def _assert_columns_exist(recorder: _SQLRecorder, schema: set[str], label: str):
    seen = recorder.posts_refs()
    assert seen, f"{label}: no SQL touching `posts` was captured — the test drove nothing"
    problems = []
    for sql, refs in seen.items():
        unknown = sorted(refs - schema)
        if unknown:
            problems.append(f"{label}: unknown posts column(s) {unknown} in: {sql[:220]}")
    assert problems == [], (
        "Endpoint emits SQL against columns `posts` does not have — this is a 500 on "
        "production Postgres:\n  " + "\n  ".join(problems)
    )


def test_posts_schema_parses_sanely():
    """Sanity-check the schema parser before trusting it to fail other tests."""
    schema = _posts_columns()
    for expected in ("id", "user_id", "content", "post_type", "moderation_status", "deleted_at"):
        assert expected in schema, f"parser lost known column {expected}: {sorted(schema)}"
    # migrations must be picked up too
    assert "best_answer_id" in schema
    assert "is_pinned" in schema
    # the column that caused the outage never existed
    assert "title" not in schema


def test_posts_column_ref_extraction():
    """The extractor must see through aliases, and ignore other tables' aliases."""
    assert _posts_column_refs(
        "SELECT p.id, p.title FROM posts p JOIN users u ON u.id = p.user_id"
    ) == {"id", "title", "user_id"}
    assert _posts_column_refs(
        "SELECT c.id, u.display_name FROM comments c JOIN users u ON u.id = c.user_id"
    ) == set()
    assert "post_title" not in _posts_column_refs(
        "SELECT p.title as post_title FROM comments c JOIN posts p ON p.id = c.post_id"
    )


@pytest.mark.integration
def test_admin_qa_queue_selects_only_real_posts_columns(pg_sql_recorder):
    response = client.get("/admin/qa-queue", headers=H)
    assert response.status_code == 200, response.text
    _assert_columns_exist(pg_sql_recorder, _posts_columns(), "GET /admin/qa-queue")


@pytest.mark.integration
def test_admin_content_search_selects_only_real_posts_columns(pg_sql_recorder):
    response = client.get("/admin/content/search", params={"q": "abc"}, headers=H)
    assert response.status_code == 200, response.text
    _assert_columns_exist(pg_sql_recorder, _posts_columns(), "GET /admin/content/search")


@pytest.mark.integration
def test_admin_comments_selects_only_real_posts_columns(pg_sql_recorder):
    response = client.get("/admin/comments", headers=H)
    assert response.status_code == 200, response.text
    _assert_columns_exist(pg_sql_recorder, _posts_columns(), "GET /admin/comments")


@pytest.mark.integration
def test_public_feed_new_since_selects_only_real_posts_columns(pg_sql_recorder, monkeypatch):
    import knowledge

    # The knowledge cache is only populated at startup; empty it explicitly so the
    # entity half of the response is a no-op and only the posts SQL is exercised.
    monkeypatch.setattr(knowledge, "_entities", {}, raising=False)
    response = client.get("/api/feed/new-since", params={"since": "2026-01-01T00:00:00Z"})
    assert response.status_code == 200, response.text
    _assert_columns_exist(pg_sql_recorder, _posts_columns(), "GET /api/feed/new-since")
