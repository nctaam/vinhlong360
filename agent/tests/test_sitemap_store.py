"""Tests for durable immutable sitemap bundle publication."""

import ast
import hashlib
import importlib
import inspect
import json
import os
import stat
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sitemap_store
import versioned_json_store
from sitemap_store import (
    SITEMAP_METADATA_SCHEMA_VERSION,
    SitemapBundleConflict,
    SitemapBundleStore,
    SitemapPublicationStage,
    SitemapStateUnavailable,
    StoredBundle,
)
from versioned_json_store import (
    atomic_write_json,
    fsync_directory,
    publication_lock,
    replace_json,
)


DOCUMENT_NAMES = (
    "metadata.json",
    "sitemap.xml",
    "sitemap-media.xml",
    "sitemap-index.xml",
)
XML_DOCUMENT_NAMES = DOCUMENT_NAMES[1:]


class InjectedPublicationFailure(RuntimeError):
    pass


class Clock:
    def __init__(self):
        self.current = datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc)

    def now(self):
        return self.current

    def advance(self, **kwargs):
        self.current += timedelta(**kwargs)


@pytest.fixture
def clock():
    return Clock()


def make_bundle(revision, marker=b"first", **metadata_evidence):
    documents = {
        "sitemap.xml": b"<urlset>" + marker + b"</urlset>",
        "sitemap-media.xml": b"<urlset>media-" + marker + b"</urlset>",
        "sitemap-index.xml": b"<sitemapindex>" + marker + b"</sitemapindex>",
    }
    evidence = {
        "policy_fingerprint": "f" * 64,
        "route_manifest_revision": "route-1",
        "backend_policy_revision": "policy-1",
        **metadata_evidence,
    }
    if type(revision) is str and sitemap_store._REVISION_PATTERN.fullmatch(revision):
        try:
            revision = sitemap_store.compute_batch_revision(
                fingerprint=evidence["policy_fingerprint"],
                route_revision=evidence["route_manifest_revision"],
                policy_revision=evidence["backend_policy_revision"],
                main=documents["sitemap.xml"],
                media=documents["sitemap-media.xml"],
            )
        except (TypeError, ValueError):
            pass
    metadata = {
        "schema_version": 1,
        "batch_revision": revision,
        "documents": {
            name: hashlib.sha256(document).hexdigest()
            for name, document in documents.items()
        },
        "renderer_evidence": evidence,
    }
    return StoredBundle(revision, metadata, documents)


def canonical_metadata(metadata):
    return json.dumps(
        metadata,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def raise_at_publication_stage(expected, error):
    def inject(actual):
        if actual is expected:
            raise error

    return inject


def read_pointer(root):
    return json.loads((root / "active.json").read_text(encoding="utf-8"))


def test_stored_bundle_and_publication_stage_are_exact_contracts():
    candidate = make_bundle("a" * 64)

    assert [field.name for field in fields(candidate)] == [
        "batch_revision",
        "metadata",
        "documents",
    ]
    with pytest.raises(FrozenInstanceError):
        candidate.batch_revision = "b" * 64
    assert issubclass(SitemapPublicationStage, str)
    assert issubclass(SitemapPublicationStage, Enum)
    assert [(member.name, member.value) for member in SitemapPublicationStage] == [
        ("AFTER_DIRECTORY_RENAME", "after-directory-rename-before-active-pointer"),
        ("BEFORE_ACTIVE_POINTER_REPLACE", "before-active-pointer-replace"),
    ]
    assert SITEMAP_METADATA_SCHEMA_VERSION == 1


def test_first_publication_round_trips_exact_bundle_and_pointer(tmp_path, clock):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path, now=clock.now)

    store.publish(candidate)

    target = tmp_path / candidate.batch_revision
    assert {path.name for path in target.iterdir()} == set(DOCUMENT_NAMES)
    assert (target / "metadata.json").read_bytes() == canonical_metadata(
        candidate.metadata
    )
    assert store.load_active() == candidate
    assert store.load_active_on_startup() == candidate
    assert store.load_batch(candidate.batch_revision) == candidate
    assert store.list_batches() == (candidate.batch_revision,)

    pointer = read_pointer(tmp_path)
    published_at = clock.current.isoformat()
    assert pointer == {
        "batch_revision": candidate.batch_revision,
        "published_at": published_at,
        "published_batches": [
            {
                "batch_revision": candidate.batch_revision,
                "published_at": published_at,
            }
        ],
    }
    parsed = datetime.fromisoformat(pointer["published_at"])
    assert parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def test_first_publish_durably_creates_each_missing_root_component(
    tmp_path, monkeypatch
):
    root = tmp_path / "r" / "a" / "d" / "s"
    missing_components = (
        tmp_path / "r",
        tmp_path / "r" / "a",
        tmp_path / "r" / "a" / "d",
        root,
    )
    events = []
    real_mkdir = Path.mkdir
    real_fsync_directory = sitemap_store.fsync_directory
    real_publication_lock = sitemap_store.publication_lock

    def record_mkdir(path, *args, **kwargs):
        existed = path.exists()
        result = real_mkdir(path, *args, **kwargs)
        if path in missing_components and not existed:
            events.append(("mkdir", path))
        return result

    def record_fsync(directory):
        directory = Path(directory)
        if directory in {component.parent for component in missing_components}:
            events.append(("fsync", directory))
        return real_fsync_directory(directory)

    @contextmanager
    def record_publication_lock(path):
        events.append(("lock", Path(path)))
        with real_publication_lock(path):
            yield

    monkeypatch.setattr(Path, "mkdir", record_mkdir)
    monkeypatch.setattr(sitemap_store, "fsync_directory", record_fsync)
    monkeypatch.setattr(sitemap_store, "publication_lock", record_publication_lock)

    SitemapBundleStore(root).publish(make_bundle("a" * 64))

    expected = []
    for component in missing_components:
        expected.extend((("mkdir", component), ("fsync", component.parent)))
    expected.append(("lock", root / ".publish.lock"))
    assert events[: len(expected)] == expected


def test_publish_with_existing_root_does_not_fsync_unchanged_ancestor(
    tmp_path, monkeypatch
):
    root = tmp_path / "sitemap-bundles"
    root.mkdir()
    fsynced = []
    real_fsync_directory = sitemap_store.fsync_directory

    def record_fsync(directory):
        fsynced.append(Path(directory))
        return real_fsync_directory(directory)

    monkeypatch.setattr(sitemap_store, "fsync_directory", record_fsync)

    SitemapBundleStore(root).publish(make_bundle("a" * 64))

    assert tmp_path not in fsynced


def test_root_creation_tolerates_component_created_by_concurrent_publisher(
    tmp_path, monkeypatch
):
    root = tmp_path / "r" / "a" / "d"
    raced_component = tmp_path / "r"
    real_mkdir = Path.mkdir
    injected = False

    def race_mkdir(path, *args, **kwargs):
        nonlocal injected
        if path == raced_component and not injected:
            injected = True
            real_mkdir(path)
            raise FileExistsError("created concurrently")
        return real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", race_mkdir)

    store = SitemapBundleStore(root)
    store.publish(make_bundle("a" * 64))

    assert injected is True
    assert store.load_active() == make_bundle("a" * 64)


@pytest.mark.parametrize(
    "revision",
    [
        "",
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        "../" + "a" * 61,
        "a" * 63 + "/",
    ],
)
def test_publish_rejects_revision_before_creating_or_addressing_root(
    tmp_path, revision
):
    store = SitemapBundleStore(tmp_path / "not-created")

    with pytest.raises(ValueError, match="batch revision"):
        store.publish(make_bundle(revision))

    assert not store.root.exists()


@pytest.mark.parametrize(
    "candidate",
    [
        lambda bundle: replace(
            bundle,
            documents={
                name: body
                for name, body in bundle.documents.items()
                if name != "sitemap-media.xml"
            },
        ),
        lambda bundle: replace(
            bundle, documents={**bundle.documents, "extra.xml": b"extra"}
        ),
        lambda bundle: replace(
            bundle, documents={**bundle.documents, "sitemap.xml": "not-bytes"}
        ),
        lambda bundle: replace(
            bundle, metadata={key: value for key, value in bundle.metadata.items() if key != "schema_version"}
        ),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "schema_version": True}),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "schema_version": 2}),
        lambda bundle: replace(
            bundle, metadata={**bundle.metadata, "batch_revision": "b" * 64}
        ),
        lambda bundle: replace(
            bundle,
            metadata={
                **bundle.metadata,
                "documents": {**bundle.metadata["documents"], "extra.xml": "0" * 64},
            },
        ),
        lambda bundle: replace(
            bundle,
            metadata={
                **bundle.metadata,
                "documents": {**bundle.metadata["documents"], "sitemap.xml": "0" * 64},
            },
        ),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "published_at": "2026-01-01T00:00:00+00:00"}),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "renderer_evidence": ("not", "json")}),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "renderer_evidence": ["not", "an", "object"]}),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "renderer_evidence": None}),
        lambda bundle: replace(bundle, metadata={**bundle.metadata, "renderer_evidnce": {}}),
        lambda bundle: replace(
            bundle,
            metadata={
                **bundle.metadata,
                "renderer_evidence": {
                    **bundle.metadata["renderer_evidence"],
                    "route_manifest_revision": "ok\r\nInjected: yes",
                },
            },
        ),
    ],
    ids=[
        "missing-document",
        "extra-document",
        "non-bytes-document",
        "missing-schema",
        "boolean-schema",
        "unsupported-schema",
        "wrong-revision",
        "extra-hash",
        "wrong-hash",
        "publication-timestamp",
        "non-json-metadata",
        "non-object-evidence",
        "null-evidence",
        "unknown-root-key",
        "header-injection",
    ],
)
def test_candidate_validation_rejects_incomplete_or_inconsistent_bundle(
    tmp_path, candidate
):
    base = make_bundle("a" * 64)
    root = tmp_path / "not-created"

    with pytest.raises(ValueError):
        SitemapBundleStore(root).publish(candidate(base))

    assert not root.exists()


def test_additional_renderer_metadata_is_rejected_before_root_creation(tmp_path):
    candidate = make_bundle(
        "a" * 64,
        rules={"entity": {"allowed": True, "minimum_images": 1}},
    )

    root = tmp_path / "not-created"
    with pytest.raises(ValueError, match="renderer evidence"):
        SitemapBundleStore(root).publish(candidate)

    assert not root.exists()


def test_renderer_evidence_metadata_is_required(tmp_path):
    candidate = make_bundle("a" * 64)
    metadata = {
        key: value
        for key, value in candidate.metadata.items()
        if key != "renderer_evidence"
    }
    candidate = replace(candidate, metadata=metadata)

    root = tmp_path / "not-created"
    with pytest.raises(ValueError, match="renderer evidence"):
        SitemapBundleStore(root).publish(candidate)

    assert not root.exists()


@pytest.mark.parametrize(
    "renderer_evidence",
    [
        {
            "policy_fingerprint": "F" * 64,
            "route_manifest_revision": "route-1",
            "backend_policy_revision": "policy-1",
        },
        {
            "policy_fingerprint": "f" * 64,
            "route_manifest_revision": "",
            "backend_policy_revision": "policy-1",
        },
        {
            "policy_fingerprint": "f" * 64,
            "route_manifest_revision": "route-1",
            "backend_policy_revision": None,
        },
    ],
)
def test_renderer_evidence_values_are_exact_and_nonempty(tmp_path, renderer_evidence):
    candidate = make_bundle("a" * 64)
    candidate = replace(
        candidate,
        metadata={**candidate.metadata, "renderer_evidence": renderer_evidence},
    )
    with pytest.raises(ValueError, match="renderer evidence"):
        SitemapBundleStore(tmp_path / "not-created").publish(candidate)


def test_batch_revision_binds_renderer_evidence_and_documents(tmp_path):
    candidate = make_bundle("a" * 64)
    forged = replace(
        candidate,
        metadata={
            **candidate.metadata,
            "renderer_evidence": {
                **candidate.metadata["renderer_evidence"],
                "policy_fingerprint": "e" * 64,
            },
        },
    )
    with pytest.raises(ValueError, match="batch revision"):
        SitemapBundleStore(tmp_path / "not-created").publish(forged)
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize(
    "stage",
    [
        SitemapPublicationStage.AFTER_DIRECTORY_RENAME,
        SitemapPublicationStage.BEFORE_ACTIVE_POINTER_REPLACE,
    ],
)
def test_injected_pre_pointer_failures_preserve_previous_active_and_orphan(
    tmp_path, stage
):
    previous = make_bundle("a" * 64)
    candidate = make_bundle("b" * 64, marker=b"second")
    SitemapBundleStore(tmp_path).publish(previous)
    failing = SitemapBundleStore(
        tmp_path,
        failure_injector=raise_at_publication_stage(
            stage, InjectedPublicationFailure(stage.value)
        ),
    )

    with pytest.raises(InjectedPublicationFailure, match=stage.value):
        failing.publish(candidate)

    restarted = SitemapBundleStore(tmp_path)
    assert restarted.load_active() == previous
    assert (tmp_path / candidate.batch_revision).is_dir()
    assert {path.name for path in (tmp_path / candidate.batch_revision).iterdir()} == set(
        DOCUMENT_NAMES
    )
    with pytest.raises(SitemapStateUnavailable):
        restarted.load_batch(candidate.batch_revision)
    assert restarted.list_batches() == (previous.batch_revision,)
    assert not any(path.name.endswith(".staging") for path in tmp_path.iterdir())


def test_retry_reuses_complete_post_rename_orphan_without_rewriting(
    tmp_path, monkeypatch
):
    previous = make_bundle("a" * 64)
    candidate = make_bundle("b" * 64, marker=b"second")
    SitemapBundleStore(tmp_path).publish(previous)
    failing = SitemapBundleStore(
        tmp_path,
        failure_injector=raise_at_publication_stage(
            SitemapPublicationStage.AFTER_DIRECTORY_RENAME,
            InjectedPublicationFailure("post-rename"),
        ),
    )
    with pytest.raises(InjectedPublicationFailure):
        failing.publish(candidate)
    metadata_bytes = (tmp_path / candidate.batch_revision / "metadata.json").read_bytes()

    def unexpected_write(*_args, **_kwargs):
        raise AssertionError("completed orphan must be validated and reused")

    monkeypatch.setattr(sitemap_store, "write_bundle_and_fsync", unexpected_write)
    restarted = SitemapBundleStore(tmp_path)
    restarted.publish(candidate)

    assert restarted.load_active() == candidate
    assert (tmp_path / candidate.batch_revision / "metadata.json").read_bytes() == metadata_bytes
    assert restarted.list_batches() == (
        previous.batch_revision,
        candidate.batch_revision,
    )


def test_first_publication_retry_reuses_only_its_matching_orphan(tmp_path):
    candidate = make_bundle("a" * 64)
    failing = SitemapBundleStore(
        tmp_path,
        failure_injector=raise_at_publication_stage(
            SitemapPublicationStage.AFTER_DIRECTORY_RENAME,
            InjectedPublicationFailure("first orphan"),
        ),
    )
    with pytest.raises(InjectedPublicationFailure):
        failing.publish(candidate)
    assert not (tmp_path / "active.json").exists()

    restarted = SitemapBundleStore(tmp_path)
    restarted.publish(candidate)

    assert restarted.load_active() == candidate


def test_missing_pointer_with_a_different_bundle_directory_fails_closed(tmp_path):
    existing = make_bundle("a" * 64)
    candidate = make_bundle("b" * 64, marker=b"candidate")
    sitemap_store.write_bundle_and_fsync(tmp_path / existing.batch_revision, existing)

    with pytest.raises(SitemapStateUnavailable):
        SitemapBundleStore(tmp_path).publish(candidate)

    assert not (tmp_path / candidate.batch_revision).exists()


def test_publish_uses_canonical_snapshot_when_caller_mutates_input(
    tmp_path, monkeypatch
):
    candidate = make_bundle("a" * 64)
    expected = make_bundle("a" * 64)
    real_lock = sitemap_store.publication_lock

    @contextmanager
    def mutate_before_filesystem_work(path):
        candidate.metadata["renderer_evidence"]["route_manifest_revision"] = "mutated"
        candidate.documents["sitemap.xml"] = b"mutated"
        with real_lock(path):
            yield

    monkeypatch.setattr(sitemap_store, "publication_lock", mutate_before_filesystem_work)

    SitemapBundleStore(tmp_path).publish(candidate)

    assert SitemapBundleStore(tmp_path).load_active() == expected


def test_pre_rename_write_failure_cleans_only_its_staging_directory(
    tmp_path, monkeypatch
):
    previous = make_bundle("a" * 64)
    candidate = make_bundle("b" * 64, marker=b"second")
    store = SitemapBundleStore(tmp_path)
    store.publish(previous)

    def fail_write(directory, _bundle):
        directory.mkdir()
        (directory / "partial").write_bytes(b"partial")
        raise OSError("write failed")

    monkeypatch.setattr(sitemap_store, "write_bundle_and_fsync", fail_write)

    with pytest.raises(OSError, match="write failed"):
        store.publish(candidate)

    assert store.load_active() == previous
    assert not (tmp_path / candidate.batch_revision).exists()
    assert not any(path.name.endswith(".staging") for path in tmp_path.iterdir())


def test_identical_republish_refreshes_and_deduplicates_ledger_without_rewrite(
    tmp_path, clock, monkeypatch
):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(candidate)
    first_pointer = read_pointer(tmp_path)
    first_metadata = (tmp_path / candidate.batch_revision / "metadata.json").read_bytes()
    clock.advance(minutes=1)

    def unexpected_write(*_args, **_kwargs):
        raise AssertionError("identical immutable bundle must not be rewritten")

    monkeypatch.setattr(sitemap_store, "write_bundle_and_fsync", unexpected_write)
    store.publish(candidate)

    second_pointer = read_pointer(tmp_path)
    assert second_pointer["published_at"] != first_pointer["published_at"]
    assert second_pointer["published_batches"] == [
        {
            "batch_revision": candidate.batch_revision,
            "published_at": clock.current.isoformat(),
        }
    ]
    assert (tmp_path / candidate.batch_revision / "metadata.json").read_bytes() == first_metadata
    assert store.load_active() == candidate


def test_publish_samples_timestamp_only_after_acquiring_root_lock(tmp_path):
    root = tmp_path / "bundles"
    root.mkdir()
    now_called = threading.Event()
    published = threading.Event()

    def now():
        now_called.set()
        return datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc)

    def publish():
        SitemapBundleStore(root, now=now).publish(make_bundle("a" * 64))
        published.set()

    with publication_lock(root / ".publish.lock"):
        thread = threading.Thread(target=publish)
        thread.start()
        assert not now_called.wait(0.1)
    thread.join(timeout=10)

    assert now_called.is_set()
    assert published.is_set()


def _mutate_metadata_bytes(target, _tmp_path):
    path = target / "metadata.json"
    path.write_bytes(path.read_bytes() + b" ")


def _mutate_document_bytes(target, _tmp_path):
    path = target / "sitemap.xml"
    path.write_bytes(path.read_bytes() + b"changed")


def _add_extra_entry(target, _tmp_path):
    (target / "extra.txt").write_text("extra", encoding="utf-8")


def _replace_document_with_directory(target, _tmp_path):
    path = target / "sitemap.xml"
    path.unlink()
    path.mkdir()


def _replace_document_with_symlink(target, tmp_path):
    path = target / "sitemap.xml"
    source = tmp_path / "outside.xml"
    source.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(source)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")


@pytest.mark.parametrize(
    "mutate",
    [
        _mutate_metadata_bytes,
        _mutate_document_bytes,
        _add_extra_entry,
        _replace_document_with_directory,
        _replace_document_with_symlink,
    ],
    ids=["metadata-bytes", "document-bytes", "extra-entry", "directory-entry", "symlink-entry"],
)
def test_existing_content_address_conflicts_on_any_byte_or_entry_change(
    tmp_path, mutate
):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path)
    store.publish(candidate)
    pointer_before = (tmp_path / "active.json").read_bytes()
    mutate(tmp_path / candidate.batch_revision, tmp_path)

    with pytest.raises(SitemapBundleConflict):
        store.publish(candidate)

    assert (tmp_path / "active.json").read_bytes() == pointer_before


def test_completed_bundle_validation_rejects_wrong_content_address_name(tmp_path):
    candidate = make_bundle("a" * 64)
    wrong_directory = tmp_path / ("b" * 64)
    sitemap_store.write_bundle_and_fsync(wrong_directory, candidate)

    with pytest.raises(SitemapBundleConflict):
        sitemap_store.validate_completed_bundle_matches(wrong_directory, candidate)


@pytest.mark.parametrize(
    "corrupt",
    [
        _mutate_metadata_bytes,
        _mutate_document_bytes,
        _add_extra_entry,
        _replace_document_with_directory,
        _replace_document_with_symlink,
    ],
    ids=["metadata", "hash", "extra-entry", "non-regular", "symlink"],
)
def test_load_active_fails_closed_for_corrupt_immutable_bundle(tmp_path, corrupt):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path)
    store.publish(candidate)
    corrupt(tmp_path / candidate.batch_revision, tmp_path)

    with pytest.raises(SitemapStateUnavailable):
        store.load_active()
    with pytest.raises(SitemapStateUnavailable):
        store.load_active_on_startup()


@pytest.mark.parametrize(
    "replacement",
    [
        b"{not-json",
        json.dumps({"batch_revision": "a" * 64}).encode(),
        json.dumps(
            {
                "batch_revision": "a" * 64,
                "published_at": "2026-07-17T08:00:00",
                "published_batches": [
                    {
                        "batch_revision": "a" * 64,
                        "published_at": "2026-07-17T08:00:00",
                    }
                ],
            }
        ).encode(),
        json.dumps(
            {
                "batch_revision": "a" * 64,
                "published_at": "2026-07-17T08:00:00+00:00",
                "published_batches": [],
            }
        ).encode(),
        json.dumps(
            {
                "batch_revision": "a" * 64,
                "published_at": "2026-07-17T08:00:00+00:00",
                "published_batches": [
                    {
                        "batch_revision": "a" * 64,
                        "published_at": "2026-07-17T08:00:00+00:00",
                    },
                    {
                        "batch_revision": "a" * 64,
                        "published_at": "2026-07-17T08:00:00+00:00",
                    },
                ],
            }
        ).encode(),
        json.dumps(
            {
                "batch_revision": "a" * 64,
                "published_at": "2026-07-17T08:00:00+00:00",
                "published_batches": [
                    {
                        "batch_revision": "a" * 64,
                        "published_at": "2026-07-17T08:01:00+00:00",
                    }
                ],
            }
        ).encode(),
        json.dumps(
            {
                "batch_revision": "a" * 64,
                "published_at": "2026-07-17T08:00:00+00:00",
                "published_batches": [
                    {
                        "batch_revision": "a" * 64,
                        "published_at": "2026-07-17T08:00:00+00:00",
                        "extra": True,
                    }
                ],
                "extra": True,
            }
        ).encode(),
    ],
    ids=[
        "invalid-json",
        "missing-keys",
        "naive-time",
        "active-not-in-ledger",
        "duplicate-active",
        "timestamp-mismatch",
        "extra-keys",
    ],
)
def test_corrupt_active_pointer_fails_closed(tmp_path, replacement):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path)
    store.publish(candidate)
    (tmp_path / "active.json").write_bytes(replacement)

    with pytest.raises(SitemapStateUnavailable):
        store.load_active()
    with pytest.raises(SitemapStateUnavailable):
        store.list_batches()


def test_active_pointer_symlink_is_rejected_without_following(tmp_path):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path)
    store.publish(candidate)
    outside = tmp_path / "outside-active.json"
    active = tmp_path / "active.json"
    outside.write_bytes(active.read_bytes())
    active.unlink()
    try:
        active.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(SitemapStateUnavailable):
        store.load_active()


def test_store_maps_unusable_publication_lock_to_unavailable_state(tmp_path):
    candidate = make_bundle("a" * 64)
    store = SitemapBundleStore(tmp_path)
    store.publish(candidate)
    lock_path = tmp_path / ".publish.lock"
    outside = tmp_path / "outside.lock"
    outside.write_bytes(lock_path.read_bytes())
    lock_path.unlink()
    try:
        lock_path.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(SitemapStateUnavailable):
        store.load_active()


def test_missing_active_pointer_fails_closed_for_every_read(tmp_path):
    store = SitemapBundleStore(tmp_path)

    with pytest.raises(SitemapStateUnavailable):
        store.load_active()
    with pytest.raises(SitemapStateUnavailable):
        store.load_active_on_startup()
    with pytest.raises(SitemapStateUnavailable):
        store.load_batch("a" * 64)
    with pytest.raises(SitemapStateUnavailable):
        store.list_batches()


def test_publish_does_not_treat_corrupt_existing_pointer_as_first_publish(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "active.json").write_bytes(b"{broken")
    candidate = make_bundle("a" * 64)

    with pytest.raises(SitemapStateUnavailable):
        SitemapBundleStore(tmp_path).publish(candidate)

    assert not (tmp_path / candidate.batch_revision).exists()
    assert (tmp_path / "active.json").read_bytes() == b"{broken"


def test_load_batch_validates_pointer_before_revision_and_refuses_orphan(tmp_path):
    store = SitemapBundleStore(tmp_path)
    with pytest.raises(SitemapStateUnavailable):
        store.load_batch("../malformed")

    active = make_bundle("a" * 64)
    orphan = make_bundle("b" * 64, marker=b"orphan")
    store.publish(active)
    sitemap_store.write_bundle_and_fsync(tmp_path / orphan.batch_revision, orphan)

    with pytest.raises(SitemapStateUnavailable):
        store.load_batch("not-a-revision")
    with pytest.raises(SitemapStateUnavailable):
        store.load_batch(orphan.batch_revision)
    assert store.list_batches() == (active.batch_revision,)


def test_cleanup_keeps_active_previous_and_every_revision_inside_window(
    tmp_path, clock
):
    bundles = [make_bundle(character * 64, marker=character.encode()) for character in "abcd"]
    store = SitemapBundleStore(tmp_path, retention=timedelta(hours=24), now=clock.now)
    store.publish(bundles[0])
    clock.advance(hours=10)
    store.publish(bundles[1])
    clock.advance(hours=15)
    store.publish(bundles[2])
    clock.advance(hours=5)
    store.publish(bundles[3])

    store.cleanup()

    revisions = tuple(bundle.batch_revision for bundle in bundles)
    assert store.list_batches() == tuple(revisions[1:])
    assert not (tmp_path / revisions[0]).exists()
    assert all((tmp_path / revision).is_dir() for revision in revisions[1:])


def test_cleanup_keeps_previous_even_when_it_is_outside_retention(tmp_path, clock):
    previous = make_bundle("a" * 64)
    active = make_bundle("b" * 64, marker=b"active")
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(previous)
    clock.advance(hours=25)
    store.publish(active)

    store.cleanup()

    assert store.list_batches() == (previous.batch_revision, active.batch_revision)


def test_republish_refresh_controls_retention_and_active_is_newest(tmp_path, clock):
    first = make_bundle("a" * 64, marker=b"a")
    expired = make_bundle("b" * 64, marker=b"b")
    previous = make_bundle("c" * 64, marker=b"c")
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(first)
    clock.advance(hours=1)
    store.publish(expired)
    clock.advance(hours=1)
    store.publish(previous)
    clock.advance(hours=25)

    store.publish(first)
    store.cleanup()

    assert store.list_batches() == (previous.batch_revision, first.batch_revision)
    pointer = read_pointer(tmp_path)
    assert pointer["published_batches"][-1] == {
        "batch_revision": first.batch_revision,
        "published_at": clock.current.isoformat(),
    }
    assert not (tmp_path / expired.batch_revision).exists()


def test_cleanup_uses_ledger_order_for_previous_when_clock_moves_backwards(
    tmp_path, clock
):
    first = make_bundle("a" * 64, marker=b"a")
    timestamp_newer_but_not_previous = make_bundle("b" * 64, marker=b"b")
    previous = make_bundle("c" * 64, marker=b"c")
    active = make_bundle("d" * 64, marker=b"d")
    store = SitemapBundleStore(tmp_path, retention=timedelta(hours=24), now=clock.now)
    store.publish(first)
    clock.current += timedelta(hours=100)
    store.publish(timestamp_newer_but_not_previous)
    clock.current -= timedelta(hours=50)
    store.publish(previous)
    clock.current += timedelta(hours=150)
    store.publish(active)

    store.cleanup()

    assert store.list_batches() == (previous.batch_revision, active.batch_revision)
    assert not (tmp_path / first.batch_revision).exists()
    assert not (tmp_path / timestamp_newer_but_not_previous.batch_revision).exists()


def test_cleanup_never_discovers_or_deletes_post_rename_orphans(tmp_path, clock):
    active = make_bundle("a" * 64)
    orphan = make_bundle("b" * 64, marker=b"orphan")
    SitemapBundleStore(tmp_path, now=clock.now).publish(active)
    failing = SitemapBundleStore(
        tmp_path,
        now=clock.now,
        failure_injector=raise_at_publication_stage(
            SitemapPublicationStage.AFTER_DIRECTORY_RENAME,
            InjectedPublicationFailure("orphan"),
        ),
    )
    with pytest.raises(InjectedPublicationFailure):
        failing.publish(orphan)
    clock.advance(hours=48)

    SitemapBundleStore(tmp_path, now=clock.now).cleanup()

    assert (tmp_path / orphan.batch_revision).is_dir()
    assert SitemapBundleStore(tmp_path).list_batches() == (active.batch_revision,)


def test_cleanup_refuses_to_delete_corrupt_ledger_owned_directory(tmp_path, clock):
    expired = make_bundle("a" * 64, marker=b"expired")
    previous = make_bundle("b" * 64, marker=b"previous")
    active = make_bundle("c" * 64, marker=b"active")
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(expired)
    clock.advance(hours=25)
    store.publish(previous)
    store.publish(active)
    pointer_before = (tmp_path / "active.json").read_bytes()
    _mutate_document_bytes(tmp_path / expired.batch_revision, tmp_path)

    with pytest.raises(SitemapStateUnavailable):
        store.cleanup()

    assert (tmp_path / expired.batch_revision).exists()
    assert (tmp_path / "active.json").read_bytes() == pointer_before


def test_cleanup_prevalidates_all_retirees_before_deleting_any(tmp_path, clock):
    first = make_bundle("a" * 64, marker=b"first")
    second = make_bundle("b" * 64, marker=b"second")
    previous = make_bundle("c" * 64, marker=b"previous")
    active = make_bundle("d" * 64, marker=b"active")
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(first)
    store.publish(second)
    clock.advance(hours=25)
    store.publish(previous)
    store.publish(active)
    pointer_before = (tmp_path / "active.json").read_bytes()
    _mutate_document_bytes(tmp_path / second.batch_revision, tmp_path)

    with pytest.raises(SitemapStateUnavailable):
        store.cleanup()

    assert (tmp_path / first.batch_revision).is_dir()
    assert (tmp_path / second.batch_revision).is_dir()
    assert (tmp_path / "active.json").read_bytes() == pointer_before


def test_cleanup_filters_pointer_before_delete_failure_leaves_safe_orphan(
    tmp_path, clock, monkeypatch
):
    expired = make_bundle("a" * 64, marker=b"expired")
    previous = make_bundle("b" * 64, marker=b"previous")
    active = make_bundle("c" * 64, marker=b"active")
    store = SitemapBundleStore(tmp_path, now=clock.now)
    store.publish(expired)
    clock.advance(hours=25)
    store.publish(previous)
    store.publish(active)

    def fail_delete(_root, revision):
        assert revision == expired.batch_revision
        raise OSError("delete failed")

    monkeypatch.setattr(sitemap_store, "_remove_validated_bundle_directory", fail_delete)

    with pytest.raises(OSError, match="delete failed"):
        store.cleanup()

    assert store.list_batches() == (previous.batch_revision, active.batch_revision)
    assert store.load_active() == active
    with pytest.raises(SitemapStateUnavailable):
        store.load_batch(expired.batch_revision)
    assert (tmp_path / expired.batch_revision).is_dir()


def test_no_public_deletion_api_can_remove_active_or_previous():
    assert not hasattr(sitemap_store, "remove_validated_bundle_directory")


def test_same_process_concurrent_publication_is_serialized_and_deduplicated(tmp_path):
    first = make_bundle("a" * 64, marker=b"a")
    second = make_bundle("b" * 64, marker=b"b")
    candidates = [first, second] * 4
    barrier = threading.Barrier(len(candidates))

    def publish(candidate):
        barrier.wait()
        SitemapBundleStore(tmp_path).publish(candidate)

    with ThreadPoolExecutor(max_workers=len(candidates)) as executor:
        futures = [executor.submit(publish, candidate) for candidate in candidates]
        for future in futures:
            future.result(timeout=20)

    store = SitemapBundleStore(tmp_path)
    active = store.load_active()
    assert active in (first, second)
    assert set(store.list_batches()) == {first.batch_revision, second.batch_revision}
    assert len(store.list_batches()) == 2
    assert store.load_batch(first.batch_revision) == first
    assert store.load_batch(second.batch_revision) == second


def test_release_root_defaults_and_no_refresh_surface(tmp_path):
    release_root = tmp_path / "release"
    store = SitemapBundleStore.from_release_root(release_root)

    assert store.root == release_root / "agent" / "data" / "sitemap-bundles"
    assert store.retention == timedelta(hours=24)
    assert not hasattr(store, "refresh")


def test_store_has_no_generation_database_snapshot_or_data_fallback_imports():
    source = inspect.getsource(sitemap_store)
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])

    assert imported.isdisjoint({"database", "sitemap_snapshot", "sitemap_render"})
    assert '"data.json"' not in source and "'data.json'" not in source
    assert '"data.js"' not in source and "'data.js'" not in source
    assert "def refresh" not in source


def test_publication_lock_is_canonical_cross_thread_and_persistent(tmp_path):
    lock_path = tmp_path / ".publish.lock"
    alias_parent = tmp_path / "alias"
    alias_parent.mkdir()
    alias = alias_parent / ".." / ".publish.lock"
    entered = threading.Event()

    def contender():
        with publication_lock(alias):
            entered.set()

    with publication_lock(lock_path):
        thread = threading.Thread(target=contender)
        thread.start()
        assert not entered.wait(0.1)
    thread.join(timeout=5)

    assert entered.is_set()
    assert lock_path.is_file()
    assert not lock_path.is_symlink()


def test_publication_lock_explicitly_rejects_same_thread_recursion(tmp_path):
    lock_path = tmp_path / ".publish.lock"

    with publication_lock(lock_path):
        with pytest.raises(RuntimeError, match="non-reentrant"):
            with publication_lock(lock_path):
                pass


def test_publication_lock_rejects_preexisting_symlink_without_touching_target(
    tmp_path
):
    outside = tmp_path / "outside.lock"
    outside.write_bytes(b"outside")
    root = tmp_path / "root"
    root.mkdir()
    lock_path = root / ".publish.lock"
    try:
        lock_path.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(OSError, match="regular file"):
        with publication_lock(lock_path):
            pass

    assert outside.read_bytes() == b"outside"


def test_atomic_write_json_orders_mode_file_fsync_replace_and_directory_fsync(
    tmp_path, monkeypatch
):
    target = tmp_path / "active.json"
    target.write_text('{"old": true}', encoding="utf-8")
    target.chmod(0o640)
    target_mode = stat.S_IMODE(target.stat().st_mode)
    events = []
    real_chmod = os.chmod
    real_fsync = os.fsync
    real_replace = os.replace
    real_fsync_directory = versioned_json_store.fsync_directory

    def chmod(path, mode):
        events.append(("chmod", Path(path)))
        real_chmod(path, mode)

    def fsync(fd):
        events.append(("fsync", stat.S_ISDIR(os.fstat(fd).st_mode)))
        real_fsync(fd)

    def replace_path(source, destination):
        events.append(("replace", Path(destination)))
        real_replace(source, destination)

    def sync_directory(directory):
        events.append(("directory-fsync", Path(directory)))
        real_fsync_directory(directory)

    monkeypatch.setattr(versioned_json_store.os, "chmod", chmod)
    monkeypatch.setattr(versioned_json_store.os, "fsync", fsync)
    monkeypatch.setattr(versioned_json_store.os, "replace", replace_path)
    monkeypatch.setattr(versioned_json_store, "fsync_directory", sync_directory)

    atomic_write_json(target, {"new": True})

    names = [event[0] for event in events]
    assert names.index("chmod") < names.index("fsync") < names.index("replace")
    assert names.index("replace") < names.index("directory-fsync")
    assert stat.S_IMODE(target.stat().st_mode) == target_mode
    assert json.loads(target.read_text(encoding="utf-8")) == {"new": True}
    assert list(tmp_path.glob(".active.json.*.tmp")) == []


def test_atomic_write_json_propagates_post_replace_directory_fsync_failure(
    tmp_path, monkeypatch
):
    target = tmp_path / "active.json"
    target.write_text('{"old": true}', encoding="utf-8")

    def fail_directory_fsync(_directory):
        raise OSError("directory fsync failed")

    monkeypatch.setattr(versioned_json_store, "fsync_directory", fail_directory_fsync)

    with pytest.raises(OSError, match="directory fsync failed"):
        atomic_write_json(target, {"new": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"new": True}
    assert list(tmp_path.glob(".active.json.*.tmp")) == []


def test_publish_reports_commit_uncertain_when_pointer_replace_precedes_fsync_error(
    tmp_path, monkeypatch
):
    previous = make_bundle("a" * 64)
    candidate = make_bundle("b" * 64, marker=b"candidate")
    store = SitemapBundleStore(tmp_path)
    store.publish(previous)
    real_atomic_write = sitemap_store.atomic_write_json

    def replace_then_fail(path, payload):
        real_atomic_write(path, payload)
        raise OSError("directory fsync failed after replace")

    monkeypatch.setattr(sitemap_store, "atomic_write_json", replace_then_fail)

    with pytest.raises(OSError, match="after replace"):
        store.publish(candidate)

    assert SitemapBundleStore(tmp_path).load_active() == candidate


def test_legacy_replace_json_keeps_best_effort_parent_fsync_behavior(
    tmp_path, monkeypatch
):
    target = tmp_path / "legacy.json"
    target.write_text('{"old": true}', encoding="utf-8")

    def fail_directory_fsync(_directory):
        raise OSError("directory fsync unsupported")

    monkeypatch.setattr(versioned_json_store, "fsync_directory", fail_directory_fsync)

    assert replace_json(target, {"new": True}) is True
    assert json.loads(target.read_text(encoding="utf-8")) == {"new": True}


def test_fsync_directory_propagates_posix_open_failure_and_is_windows_noop(
    tmp_path, monkeypatch
):
    def fail_open(*_args, **_kwargs):
        raise OSError("open directory failed")

    monkeypatch.setattr(versioned_json_store.os, "open", fail_open)

    if os.name == "nt":
        fsync_directory(tmp_path)
    else:
        with pytest.raises(OSError, match="open directory failed"):
            fsync_directory(tmp_path)


def test_store_uses_only_write_active_pointer_for_pointer_replacement(
    tmp_path, monkeypatch
):
    calls = []
    original = SitemapBundleStore._write_active_pointer

    def record(self, payload):
        calls.append(payload)
        return original(self, payload)

    monkeypatch.setattr(SitemapBundleStore, "_write_active_pointer", record)
    store = SitemapBundleStore(tmp_path)
    store.publish(make_bundle("a" * 64))
    store.publish(make_bundle("b" * 64, marker=b"b"))
    store.cleanup()

    assert len(calls) == 3


def test_module_import_and_constructor_have_no_storage_side_effects(tmp_path):
    root = tmp_path / "never-created"

    reloaded = importlib.reload(sitemap_store)
    store = reloaded.SitemapBundleStore(root)

    assert store.root == root
    assert not root.exists()
