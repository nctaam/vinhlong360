"""Opt-in PostgreSQL isolation tests for immutable sitemap bundles."""

import hashlib
import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from psycopg2.extensions import make_dsn
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database as database_module
import sitemap_snapshot
from sitemap_store import (
    SITEMAP_METADATA_SCHEMA_VERSION,
    SitemapBundleStore,
    SitemapPublicationStage,
    SitemapStateUnavailable,
    StoredBundle,
)


THREAD_TIMEOUT = 10
WAIT_TIMEOUT = 5
DOCUMENT_NAMES = (
    "sitemap.xml",
    "sitemap-media.xml",
    "sitemap-index.xml",
)
ENTITIES_SQL = "SELECT * FROM entities"
RELATIONSHIPS_SQL = (
    "SELECT from_id AS source_id, to_id AS target_id, type FROM relationships"
)


def _test_database_url() -> str | None:
    url = os.environ.get("SITEMAP_BUNDLE_TEST_DATABASE_URL")
    if not url:
        return None

    parsed = urlparse(url)
    database_name = unquote(parsed.path.lstrip("/"))
    if parsed.scheme not in {"postgres", "postgresql"} or not database_name:
        raise pytest.UsageError(
            "SITEMAP_BUNDLE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    if "launch_test" not in database_name.lower():
        raise pytest.UsageError(
            "sitemap bundle PostgreSQL tests require a database name containing "
            "'launch_test'"
        )
    try:
        port = parsed.port
    except ValueError as error:
        raise pytest.UsageError(
            "SITEMAP_BUNDLE_TEST_DATABASE_URL must use a valid PostgreSQL port"
        ) from error
    if port != 55432:
        raise pytest.UsageError(
            "sitemap bundle PostgreSQL tests require disposable port 55432"
        )
    if (
        parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        and os.environ.get("ALLOW_REMOTE_DISPOSABLE_PG") != "true"
    ):
        raise pytest.UsageError(
            "non-loopback sitemap PostgreSQL tests require "
            "ALLOW_REMOTE_DISPOSABLE_PG=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        TEST_DATABASE_URL is None,
        reason="set SITEMAP_BUNDLE_TEST_DATABASE_URL to a disposable PostgreSQL DB",
    ),
]


@dataclass(frozen=True)
class DisposablePostgres:
    adapter: database_module.Database
    dsn: str
    schema: str


@pytest.fixture
def disposable_pg():
    assert TEST_DATABASE_URL is not None
    schema = f"sitemap_bundle_{uuid.uuid4().hex}"
    schema_created = False
    try:
        with psycopg2.connect(TEST_DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
                )
                schema_created = True

        schema_dsn = make_dsn(
            TEST_DATABASE_URL,
            options=f"-csearch_path={schema}",
        )
        with psycopg2.connect(schema_dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW search_path")
                search_path = cursor.fetchone()[0].split(",", 1)[0].strip().strip('"')
                assert search_path == schema
                cursor.execute(
                    """
                    CREATE TABLE entities (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        images JSONB NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE relationships (
                        from_id TEXT NOT NULL,
                        to_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        PRIMARY KEY (from_id, to_id, type)
                    )
                    """
                )

        database_module.psycopg2 = psycopg2
        database_module.psycopg2.extras = psycopg2.extras
        adapter = database_module.Database()
        adapter._use_pg = True
        adapter._dsn = schema_dsn
        yield DisposablePostgres(adapter=adapter, dsn=schema_dsn, schema=schema)
    finally:
        if schema_created:
            with psycopg2.connect(TEST_DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("DROP SCHEMA {} CASCADE").format(
                            sql.Identifier(schema)
                        )
                    )


class InjectedPublicationFailure(RuntimeError):
    pass


def _normalized(sql_text: str) -> str:
    return " ".join(sql_text.split())


def _seed_original_snapshot(database: DisposablePostgres) -> None:
    with psycopg2.connect(database.dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO entities (id, type, name, summary, images)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    "entity-1",
                    "place",
                    "Original Entity",
                    "original-summary",
                    json.dumps(["original.webp"]),
                ),
            )
            cursor.execute(
                """
                INSERT INTO relationships (from_id, to_id, type)
                VALUES (%s, %s, %s)
                """,
                ("entity-1", "original-snapshot", "snapshot-marker"),
            )


def _mutate_snapshot_source(database: DisposablePostgres) -> None:
    with psycopg2.connect(database.dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE entities
                SET summary = %s, images = %s::jsonb
                WHERE id = %s
                """,
                (
                    "changed-summary",
                    json.dumps(["changed.webp"]),
                    "entity-1",
                ),
            )
            cursor.execute(
                """
                UPDATE relationships
                SET to_id = %s, type = %s
                WHERE from_id = %s
                """,
                ("changed-snapshot", "changed-marker", "entity-1"),
            )


def _build_snapshot_probe_documents(snapshot) -> dict[str, bytes]:
    entity = next(row for row in snapshot.entities if row["id"] == "entity-1")
    relationship = next(
        row for row in snapshot.relationships if row["source_id"] == "entity-1"
    )
    return {
        "sitemap.xml": f"main-summary:{entity['summary']}".encode(),
        "sitemap-media.xml": (
            "media-images:"
            + json.dumps(entity["images"], sort_keys=True, separators=(",", ":"))
        ).encode(),
        "sitemap-index.xml": (
            f"relationship:{relationship['target_id']}:{relationship['type']}"
        ).encode(),
    }


def _complete_probe_bundle(revision: str, label: str) -> StoredBundle:
    marker = label.encode()
    documents = {
        "sitemap.xml": b"main:" + marker,
        "sitemap-media.xml": b"media:" + marker,
        "sitemap-index.xml": b"index:" + marker,
    }
    metadata = {
        "schema_version": SITEMAP_METADATA_SCHEMA_VERSION,
        "batch_revision": revision,
        "documents": {
            name: hashlib.sha256(body).hexdigest()
            for name, body in documents.items()
        },
    }
    return StoredBundle(revision, metadata, documents)


def _raise_at_publication_stage(expected, error):
    def inject(actual):
        if actual is expected:
            raise error

    return inject


def _directory_signature(directory: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(directory.iterdir())
    }


def test_all_three_documents_use_the_original_repeatable_read_snapshot(
    disposable_pg,
    monkeypatch,
):
    _seed_original_snapshot(disposable_pg)
    open_snapshot = getattr(sitemap_snapshot, "open_sitemap_snapshot", None)
    assert open_snapshot is not None, (
        "sitemap_snapshot.open_sitemap_snapshot must hold the materialized snapshot "
        "transaction open"
    )

    entity_read = threading.Event()
    release_relationship_read = threading.Event()
    original_execute = disposable_pg.adapter._execute

    def execute_with_snapshot_barrier(conn, sql_text, params=None):
        statement = _normalized(sql_text)
        if statement == RELATIONSHIPS_SQL:
            if not release_relationship_read.wait(WAIT_TIMEOUT):
                raise AssertionError("timed out waiting to read relationships")
        cursor = original_execute(conn, sql_text, params)
        if statement == ENTITIES_SQL:
            entity_read.set()
        return cursor

    monkeypatch.setattr(
        disposable_pg.adapter,
        "_execute",
        execute_with_snapshot_barrier,
    )

    def load_probe_documents():
        with open_snapshot(disposable_pg.adapter) as snapshot:
            return _build_snapshot_probe_documents(snapshot)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(load_probe_documents)
        try:
            assert entity_read.wait(WAIT_TIMEOUT), (
                "snapshot worker did not complete its first PostgreSQL read"
            )
            _mutate_snapshot_source(disposable_pg)
        finally:
            release_relationship_read.set()
        documents = future.result(timeout=THREAD_TIMEOUT)

    assert b"original-summary" in documents["sitemap.xml"]
    assert b"original.webp" in documents["sitemap-media.xml"]
    assert b"original-snapshot" in documents["sitemap-index.xml"]
    assert b"snapshot-marker" in documents["sitemap-index.xml"]
    assert all(b"changed" not in body for body in documents.values())


def test_concurrent_publication_exposes_only_complete_bundles(
    disposable_pg,
    tmp_path,
):
    previous = _complete_probe_bundle("a" * 64, "previous")
    candidates = (
        _complete_probe_bundle("b" * 64, "candidate-one"),
        _complete_probe_bundle("c" * 64, "candidate-two"),
    )
    SitemapBundleStore(tmp_path).publish(previous)
    start = threading.Barrier(len(candidates))

    def publish(candidate):
        start.wait(timeout=WAIT_TIMEOUT)
        SitemapBundleStore(tmp_path).publish(candidate)

    observations = [SitemapBundleStore(tmp_path).load_active()]
    with ThreadPoolExecutor(max_workers=len(candidates)) as executor:
        futures = [executor.submit(publish, candidate) for candidate in candidates]
        deadline = time.monotonic() + THREAD_TIMEOUT
        while not all(future.done() for future in futures):
            assert time.monotonic() < deadline, "concurrent publication timed out"
            observations.append(SitemapBundleStore(tmp_path).load_active())
        for future in futures:
            future.result(timeout=THREAD_TIMEOUT)

    store = SitemapBundleStore(tmp_path)
    observations.append(store.load_active())
    complete_bundles = (previous, *candidates)
    assert all(observation in complete_bundles for observation in observations)
    assert store.load_active() in candidates

    revisions = store.list_batches()
    assert set(revisions) == {bundle.batch_revision for bundle in complete_bundles}
    for revision in revisions:
        bundle = store.load_batch(revision)
        assert set(bundle.documents) == set(DOCUMENT_NAMES)
        assert bundle in complete_bundles
    assert not list(tmp_path.glob(".*.staging"))
    assert {
        path.name for path in tmp_path.iterdir() if path.is_dir()
    } == set(revisions)


@pytest.mark.parametrize(
    ("stage", "error"),
    [
        (
            SitemapPublicationStage.AFTER_DIRECTORY_RENAME,
            InjectedPublicationFailure("after-directory-rename"),
        ),
        (
            SitemapPublicationStage.BEFORE_ACTIVE_POINTER_REPLACE,
            InjectedPublicationFailure("before-active-pointer-replace"),
        ),
    ],
    ids=("after-directory-rename", "before-active-pointer-replace"),
)
def test_failed_publication_preserves_previous_and_retry_reuses_candidate(
    disposable_pg,
    tmp_path,
    stage,
    error,
):
    previous = _complete_probe_bundle("d" * 64, "previous")
    candidate = _complete_probe_bundle("e" * 64, "candidate")
    SitemapBundleStore(tmp_path).publish(previous)
    failing = SitemapBundleStore(
        tmp_path,
        failure_injector=_raise_at_publication_stage(stage, error),
    )

    with pytest.raises(InjectedPublicationFailure, match=str(error)):
        failing.publish(candidate)

    restarted = SitemapBundleStore(tmp_path)
    active = restarted.load_active_on_startup()
    assert active == previous
    assert active.documents == previous.documents
    assert set(active.documents) == set(DOCUMENT_NAMES)

    candidate_directory = tmp_path / candidate.batch_revision
    assert candidate_directory.is_dir()
    before_retry = _directory_signature(candidate_directory)
    with pytest.raises(SitemapStateUnavailable):
        restarted.load_batch(candidate.batch_revision)
    assert restarted.list_batches() == (previous.batch_revision,)
    assert not list(tmp_path.glob(".*.staging"))

    SitemapBundleStore(tmp_path).publish(candidate)

    after_retry = _directory_signature(candidate_directory)
    activated = SitemapBundleStore(tmp_path)
    assert after_retry == before_retry
    assert activated.load_active() == candidate
    assert activated.load_batch(candidate.batch_revision) == candidate
    assert set(activated.load_active().documents) == set(DOCUMENT_NAMES)
    assert not list(tmp_path.glob(".*.staging"))
