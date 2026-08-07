from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest


AGENT = Path(__file__).resolve().parent.parent
ROOT = AGENT.parent
sys.path.insert(0, str(AGENT))

import launch_policy_api  # noqa: E402
import sitemap_bundle  # noqa: E402
from ai_disclosure import load_ai_disclosure  # noqa: E402
from launch_evidence import current_policy_evidence  # noqa: E402
from route_manifest import load_route_manifest  # noqa: E402
from sitemap_snapshot import SitemapSnapshot  # noqa: E402


def _run_cli(tmp_path: Path, *args: str, module: bool) -> subprocess.CompletedProcess[str]:
    release_root = tmp_path / "release"
    env = os.environ.copy()
    env["SITEMAP_BUNDLE_RELEASE_ROOT"] = str(release_root)
    # Hợp đồng đo ở đây là nhánh fail-closed: KHÔNG có Postgres thì refresh phải chết
    # trước mọi tác dụng phụ (sitemap_bundle.py:126 `_require_postgresql`). `USE_PG` là
    # hằng module tính lúc import (database.py:38) nên chỉ chặn được bằng env của tiến
    # trình con. Bỏ dòng này thì ở job test-pg tiến trình con thấy DATABASE_URL, build
    # + publish THẬT (đúng chức năng) và `assert not release_root.exists()` đỏ oan.
    env.pop("DATABASE_URL", None)
    command = (
        [sys.executable, "-m", "agent.sitemap_bundle", *args]
        if module
        else [sys.executable, str(AGENT / "sitemap_bundle.py"), *args]
    )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert not release_root.exists()
    return completed


@pytest.mark.parametrize("module", [False, True])
def test_refresh_cli_fails_closed_before_database_or_store_side_effects(
    tmp_path: Path,
    module: bool,
):
    completed = _run_cli(tmp_path, "refresh", module=module)

    assert completed.returncode != 0
    assert sitemap_bundle.REFRESH_UNAVAILABLE_ERROR in completed.stderr
    assert "Traceback" not in completed.stderr


def test_refresh_function_is_a_stable_fail_closed_skeleton():
    with pytest.raises(sitemap_bundle.SitemapRefreshUnavailable):
        sitemap_bundle.refresh(database=SimpleNamespace(_use_pg=False))


def test_bundle_module_import_does_not_load_database_store_or_snapshot():
    script = (
        "import sys; import agent.sitemap_bundle; "
        "assert 'database' not in sys.modules; "
        "assert 'agent.database' not in sys.modules; "
        "assert 'sitemap_store' not in sys.modules; "
        "assert 'agent.sitemap_store' not in sys.modules; "
        "assert 'sitemap_snapshot' not in sys.modules; "
        "assert 'agent.sitemap_snapshot' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert completed.returncode == 0, completed.stderr


def test_bundle_bootstrap_exposes_agent_and_project_import_roots():
    assert sitemap_bundle.AGENT_DIR == AGENT
    assert sitemap_bundle.PROJECT_DIR == ROOT
    assert str(sitemap_bundle.AGENT_DIR) in sys.path
    assert str(sitemap_bundle.PROJECT_DIR) in sys.path


def test_startup_validation_records_available_pinned_batch_without_refresh():
    class Store:
        def load_active_on_startup(self):
            return SimpleNamespace(batch_revision="a" * 64)

        def load_active(self):
            raise AssertionError("startup must use load_active_on_startup")

        def publish(self, _bundle):
            raise AssertionError("startup must never publish")

    app = SimpleNamespace(state=SimpleNamespace())

    available = launch_policy_api.validate_sitemap_bundle_on_startup(app, Store())

    assert available is True
    assert app.state.launch_sitemaps_available is True
    assert app.state.launch_sitemap_batch_revision == "a" * 64


def test_startup_validation_fails_open_for_closed_backend_without_creating_root(
    tmp_path: Path,
):
    root = tmp_path / "missing" / "sitemap-bundles"

    class Store:
        def load_active_on_startup(self):
            assert not root.exists()
            raise RuntimeError("corrupt secret state")

        def publish(self, _bundle):
            raise AssertionError("startup must never publish")

    app = SimpleNamespace(state=SimpleNamespace())

    available = launch_policy_api.validate_sitemap_bundle_on_startup(app, Store())

    assert available is False
    assert app.state.launch_sitemaps_available is False
    assert app.state.launch_sitemap_batch_revision is None
    assert not root.exists()


def test_server_lifespan_invokes_only_startup_validation_for_sitemaps():
    source = (AGENT / "server.py").read_text(encoding="utf-8")
    lifespan_source = source[source.index("async def lifespan") : source.index("app = FastAPI")]

    assert "validate_sitemap_bundle_on_startup(app)" in lifespan_source
    assert "refresh(" not in lifespan_source
    assert ".publish(" not in lifespan_source


def test_build_bundle_renders_all_documents_from_one_postgres_snapshot(monkeypatch):
    database = SimpleNamespace(_use_pg=True)
    snapshot = SitemapSnapshot(entities=(), relationships=(), wards=())
    calls = []

    @contextmanager
    def one_snapshot(_database):
        calls.append("open")
        yield snapshot
        calls.append("close")

    monkeypatch.setattr(sitemap_bundle, "_open_sitemap_snapshot", one_snapshot)
    bundle = sitemap_bundle.build_bundle(
        database=database,
        manifest=load_route_manifest(),
        evidence=current_policy_evidence(),
        disclosure=load_ai_disclosure(),
    )

    assert calls == ["open", "close"]
    assert set(bundle.documents) == {
        "sitemap.xml",
        "sitemap-media.xml",
        "sitemap-index.xml",
    }
    assert f"batch={bundle.batch_revision}".encode() in bundle.documents["sitemap-index.xml"]
    assert set(bundle.metadata) == {
        "schema_version",
        "batch_revision",
        "documents",
        "renderer_evidence",
    }
    assert set(bundle.metadata["renderer_evidence"]) == {
        "policy_fingerprint",
        "route_manifest_revision",
        "backend_policy_revision",
    }


def test_refresh_publishes_only_after_complete_bundle_render(monkeypatch):
    database = SimpleNamespace(_use_pg=True)
    snapshot = SitemapSnapshot(entities=(), relationships=(), wards=())

    @contextmanager
    def one_snapshot(_database):
        yield snapshot

    class Store:
        def __init__(self):
            self.published = []

        def publish(self, bundle):
            self.published.append(bundle)

    store = Store()
    monkeypatch.setattr(sitemap_bundle, "_open_sitemap_snapshot", one_snapshot)
    result = sitemap_bundle.refresh(
        database=database,
        store=store,
        manifest=load_route_manifest(),
        evidence=current_policy_evidence(),
        disclosure=load_ai_disclosure(),
    )

    assert store.published == [result]


def test_build_bundle_rejects_index_with_wrong_batch_reference(monkeypatch):
    database = SimpleNamespace(_use_pg=True)
    snapshot = SitemapSnapshot(entities=(), relationships=(), wards=())

    @contextmanager
    def one_snapshot(_database):
        yield snapshot

    original_loader = sitemap_bundle._load_render_dependencies

    def dependencies_with_bad_index():
        dependencies = original_loader()
        dependencies["render_sitemap_index"] = lambda _origin, _batch: (
            b"<?xml version='1.0' encoding='utf-8'?>\n"
            b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            b"<sitemap><loc>https://vinhlong360.vn/sitemap.xml?batch="
            + b"b" * 64
            + b"</loc></sitemap><sitemap><loc>https://vinhlong360.vn/sitemap-media.xml?batch="
            + b"b" * 64
            + b"</loc></sitemap></sitemapindex>"
        )
        return dependencies

    monkeypatch.setattr(sitemap_bundle, "_open_sitemap_snapshot", one_snapshot)
    monkeypatch.setattr(
        sitemap_bundle, "_load_render_dependencies", dependencies_with_bad_index
    )
    with pytest.raises(ValueError, match="pinned to the batch"):
        sitemap_bundle.build_bundle(
            database=database,
            manifest=load_route_manifest(),
            evidence=current_policy_evidence(),
            disclosure=load_ai_disclosure(),
        )
