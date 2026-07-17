"""Opt-in PostgreSQL isolation tests for immutable sitemap bundles."""

import hashlib
import json
import multiprocessing
import os
import queue
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from psycopg2.extensions import make_dsn, parse_dsn
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
    compute_batch_revision,
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
BOUNDED_PG_OPTIONS = "-cstatement_timeout=5000 -clock_timeout=5000"


def _test_database_url() -> str | None:
    url = os.environ.get("SITEMAP_BUNDLE_TEST_DATABASE_URL")
    if not url:
        return None

    scheme = url.split(":", 1)[0]
    if scheme not in {"postgres", "postgresql"}:
        raise pytest.UsageError(
            "SITEMAP_BUNDLE_TEST_DATABASE_URL must be a PostgreSQL URL"
        )
    try:
        target = parse_dsn(url)
    except (psycopg2.ProgrammingError, TypeError, ValueError) as error:
        raise pytest.UsageError(
            "SITEMAP_BUNDLE_TEST_DATABASE_URL must be a valid PostgreSQL URL"
        ) from error

    database_name = target.get("dbname", "")
    if not database_name:
        raise pytest.UsageError(
            "SITEMAP_BUNDLE_TEST_DATABASE_URL must name a PostgreSQL database"
        )
    if "launch_test" not in database_name.lower():
        raise pytest.UsageError(
            "sitemap bundle PostgreSQL tests require a database name containing "
            "'launch_test'"
        )
    ports = tuple(part.strip() for part in target.get("port", "").split(","))
    if not ports or any(port != "55432" for port in ports):
        raise pytest.UsageError(
            "sitemap bundle PostgreSQL tests require disposable port 55432"
        )

    hosts = tuple(part.strip() for part in target.get("host", "").split(","))
    host_addresses = tuple(
        part.strip() for part in target.get("hostaddr", "").split(",")
    )
    effective_hosts = tuple(
        host for host in (*hosts, *host_addresses) if host
    )
    if not effective_hosts:
        raise pytest.UsageError(
            "SITEMAP_BUNDLE_TEST_DATABASE_URL must name an explicit host"
        )
    if (
        any(
            host not in {"127.0.0.1", "localhost", "::1"}
            for host in effective_hosts
        )
        and os.environ.get("ALLOW_REMOTE_DISPOSABLE_PG") != "true"
    ):
        raise pytest.UsageError(
            "non-loopback sitemap PostgreSQL tests require "
            "ALLOW_REMOTE_DISPOSABLE_PG=true"
        )
    return url


TEST_DATABASE_URL = _test_database_url()


@pytest.mark.parametrize(
    "url",
    [
        (
            "postgresql://task16_admin@127.0.0.1:55432/vl360_launch_test"
            "?host=203.0.113.10"
        ),
        (
            "postgresql://task16_admin@127.0.0.1:55432/vl360_launch_test"
            "?port=5432"
        ),
        (
            "postgresql://task16_admin@127.0.0.1:55432/vl360_launch_test"
            "?dbname=prod"
        ),
        (
            "postgresql://task16_admin@127.0.0.1:55432/vl360_launch_test"
            "?hostaddr=203.0.113.10"
        ),
    ],
    ids=("remote-host", "default-port", "production-dbname", "remote-hostaddr"),
)
def test_database_url_guard_rejects_effective_query_overrides_without_connecting(
    monkeypatch,
    url,
):
    connection_attempts = []

    def reject_connection(*args, **kwargs):
        connection_attempts.append((args, kwargs))
        raise AssertionError("URL validation must finish before any connection attempt")

    monkeypatch.setattr(psycopg2, "connect", reject_connection)
    monkeypatch.setenv("SITEMAP_BUNDLE_TEST_DATABASE_URL", url)
    monkeypatch.delenv("ALLOW_REMOTE_DISPOSABLE_PG", raising=False)

    with pytest.raises(pytest.UsageError):
        _test_database_url()

    assert connection_attempts == []


@pytest.mark.parametrize(
    ("override", "allowed"),
    [("true", True), ("TRUE", False), ("1", False)],
)
def test_database_url_guard_remote_override_is_exact(
    monkeypatch,
    override,
    allowed,
):
    url = "postgresql://task16_admin@203.0.113.10:55432/vl360_launch_test"
    monkeypatch.setenv("SITEMAP_BUNDLE_TEST_DATABASE_URL", url)
    monkeypatch.setenv("ALLOW_REMOTE_DISPOSABLE_PG", override)

    if allowed:
        assert _test_database_url() == url
    else:
        with pytest.raises(pytest.UsageError, match="ALLOW_REMOTE_DISPOSABLE_PG"):
            _test_database_url()


class StubbornProcess:
    def __init__(self):
        self.alive = True
        self.terminate_calls = 0
        self.kill_calls = 0
        self.join_timeouts = []

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminate_calls += 1

    def kill(self):
        self.kill_calls += 1

    def join(self, timeout):
        self.join_timeouts.append(timeout)
        if self.kill_calls and timeout > 0:
            self.alive = False
        elif timeout > 0:
            time.sleep(timeout)


def test_process_cleanup_terminates_then_kills_with_only_bounded_joins():
    process = StubbornProcess()

    remaining = _terminate_processes((process,), timeout=0.01)

    assert remaining == ()
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.join_timeouts
    assert all(timeout is not None and timeout <= 0.01 for timeout in process.join_timeouts)
    assert process.join_timeouts[-1] > 0


def test_schema_admin_dsn_for_create_and_drop_has_bounded_timeouts():
    dsn = _bounded_admin_dsn(
        "postgresql://task16_admin@127.0.0.1:55432/vl360_launch_test"
        "?connect_timeout=0&options=-cstatement_timeout%3D0"
    )

    target = parse_dsn(dsn)

    assert target["connect_timeout"] == "5"
    assert "-cstatement_timeout=5000" in target["options"]
    assert "-clock_timeout=5000" in target["options"]


def _bounded_admin_dsn(url):
    return make_dsn(
        url,
        connect_timeout=5,
        options=BOUNDED_PG_OPTIONS,
    )


def _terminate_processes(processes, *, timeout):
    processes = tuple(processes)
    graceful_deadline = time.monotonic() + timeout
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(max(0.0, graceful_deadline - time.monotonic()))

    alive = tuple(process for process in processes if process.is_alive())
    for process in alive:
        process.kill()
    kill_deadline = time.monotonic() + timeout
    for process in alive:
        process.join(max(0.0, kill_deadline - time.monotonic()))
    return tuple(process for process in processes if process.is_alive())


def _start_bounded_connection_cancellation(connections):
    def cancel(connection):
        try:
            connection.cancel()
        except psycopg2.Error:
            pass

    cancellers = []
    for connection in connections:
        canceller = threading.Thread(
            target=cancel,
            args=(connection,),
            daemon=True,
        )
        canceller.start()
        cancellers.append(canceller)
    return tuple(cancellers)


def _publish_candidate_process(root, candidate, start, results):
    try:
        start.wait(timeout=WAIT_TIMEOUT)
        SitemapBundleStore(Path(root)).publish(candidate)
    except BaseException as error:
        results.put(("error", f"{type(error).__name__}: {error}"))
    else:
        results.put(("published", candidate.batch_revision))


def _put_observation(observations, stop, message):
    while not stop.is_set():
        try:
            observations.put(message, timeout=0.1)
        except queue.Full:
            continue
        return True
    return False


def _observe_active_process(root, stop, ready, observations):
    store = SitemapBundleStore(Path(root))
    while not stop.is_set():
        try:
            active = store.load_active()
        except BaseException as error:
            _put_observation(
                observations,
                stop,
                ("error", f"{type(error).__name__}: {error}"),
            )
            ready.set()
            return
        if _put_observation(observations, stop, ("bundle", active)):
            ready.set()


def _drain_process_queue(messages):
    drained = []
    while True:
        try:
            drained.append(messages.get_nowait())
        except queue.Empty:
            return drained


def _close_process_queue(messages):
    messages.cancel_join_thread()
    messages.close()


@dataclass(frozen=True)
class DisposablePostgres:
    adapter: database_module.Database
    dsn: str
    schema: str


@pytest.fixture
def disposable_pg():
    if TEST_DATABASE_URL is None:
        pytest.skip(
            "set SITEMAP_BUNDLE_TEST_DATABASE_URL to a disposable PostgreSQL DB"
        )
    schema = f"sitemap_bundle_{uuid.uuid4().hex}"
    schema_created = False
    admin_dsn = _bounded_admin_dsn(TEST_DATABASE_URL)
    try:
        with psycopg2.connect(admin_dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
                )
                schema_created = True

        schema_dsn = make_dsn(
            TEST_DATABASE_URL,
            connect_timeout=5,
            options=(
                f"-csearch_path={schema} "
                f"{BOUNDED_PG_OPTIONS}"
            ),
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
            with psycopg2.connect(admin_dsn) as conn:
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
    evidence = {
        "policy_fingerprint": "f" * 64,
        "route_manifest_revision": "launch-indexing-policy-v1",
        "backend_policy_revision": "index-policy-v1",
    }
    revision = compute_batch_revision(
        fingerprint=evidence["policy_fingerprint"],
        route_revision=evidence["route_manifest_revision"],
        policy_revision=evidence["backend_policy_revision"],
        main=documents["sitemap.xml"],
        media=documents["sitemap-media.xml"],
    )
    metadata = {
        "schema_version": SITEMAP_METADATA_SCHEMA_VERSION,
        "batch_revision": revision,
        "documents": {
            name: hashlib.sha256(body).hexdigest()
            for name, body in documents.items()
        },
        "renderer_evidence": evidence,
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


@pytest.mark.integration
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
    active_connections = []
    original_execute = disposable_pg.adapter._execute

    def execute_with_snapshot_barrier(conn, sql_text, params=None):
        if conn not in active_connections:
            active_connections.append(conn)
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
        try:
            with open_snapshot(disposable_pg.adapter) as snapshot:
                documents = _build_snapshot_probe_documents(snapshot)
        except BaseException as error:
            worker_result.put(("error", error))
        else:
            worker_result.put(("documents", documents))

    worker_result = queue.Queue(maxsize=1)
    worker = threading.Thread(target=load_probe_documents, daemon=True)
    worker.start()
    try:
        assert entity_read.wait(WAIT_TIMEOUT), (
            "snapshot worker did not complete its first PostgreSQL read"
        )
        _mutate_snapshot_source(disposable_pg)
    finally:
        release_relationship_read.set()
        worker.join(THREAD_TIMEOUT)
        if worker.is_alive():
            cancellers = _start_bounded_connection_cancellation(active_connections)
            cancellation_deadline = time.monotonic() + WAIT_TIMEOUT
            worker.join(max(0.0, cancellation_deadline - time.monotonic()))
            for canceller in cancellers:
                canceller.join(max(0.0, cancellation_deadline - time.monotonic()))
        assert not worker.is_alive(), "snapshot worker did not stop within its timeout"

    result_type, result = worker_result.get_nowait()
    if result_type == "error":
        raise result
    documents = result

    assert b"original-summary" in documents["sitemap.xml"]
    assert b"original.webp" in documents["sitemap-media.xml"]
    assert b"original-snapshot" in documents["sitemap-index.xml"]
    assert b"snapshot-marker" in documents["sitemap-index.xml"]
    assert all(b"changed" not in body for body in documents.values())


@pytest.mark.integration
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
    context = multiprocessing.get_context("spawn")
    start = context.Barrier(len(candidates))
    writer_results = context.Queue()
    observation_messages = context.Queue(maxsize=64)
    stop_reader = context.Event()
    reader_ready = context.Event()
    reader = context.Process(
        target=_observe_active_process,
        args=(str(tmp_path), stop_reader, reader_ready, observation_messages),
    )
    writers = tuple(
        context.Process(
            target=_publish_candidate_process,
            args=(str(tmp_path), candidate, start, writer_results),
        )
        for candidate in candidates
    )
    started_processes = []
    observations = []
    remaining_processes = ()

    def record_observation(message):
        message_type, payload = message
        assert message_type == "bundle", payload
        observations.append(payload)

    try:
        reader.start()
        started_processes.append(reader)
        assert reader_ready.wait(WAIT_TIMEOUT), "publication reader did not start"
        record_observation(observation_messages.get(timeout=WAIT_TIMEOUT))
        for writer in writers:
            writer.start()
            started_processes.append(writer)

        deadline = time.monotonic() + THREAD_TIMEOUT
        while any(writer.is_alive() for writer in writers):
            assert time.monotonic() < deadline, "concurrent publication timed out"
            for message in _drain_process_queue(observation_messages):
                record_observation(message)
            time.sleep(0.01)

        for writer in writers:
            writer.join(max(0.0, deadline - time.monotonic()))
        for _candidate in candidates:
            result_type, payload = writer_results.get(
                timeout=max(0.01, deadline - time.monotonic())
            )
            assert result_type == "published", payload
        for message in _drain_process_queue(observation_messages):
            record_observation(message)
    finally:
        stop_reader.set()
        remaining_processes = _terminate_processes(
            started_processes,
            timeout=WAIT_TIMEOUT,
        )
        _close_process_queue(writer_results)
        _close_process_queue(observation_messages)

    assert remaining_processes == ()

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


@pytest.mark.integration
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
