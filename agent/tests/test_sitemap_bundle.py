from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


AGENT = Path(__file__).resolve().parent.parent
ROOT = AGENT.parent
sys.path.insert(0, str(AGENT))

import launch_policy_api  # noqa: E402
import sitemap_bundle  # noqa: E402


def _run_cli(tmp_path: Path, *args: str, module: bool) -> subprocess.CompletedProcess[str]:
    release_root = tmp_path / "release"
    env = os.environ.copy()
    env["SITEMAP_BUNDLE_RELEASE_ROOT"] = str(release_root)
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
    with pytest.raises(
        sitemap_bundle.SitemapRefreshUnavailable,
        match=sitemap_bundle.REFRESH_UNAVAILABLE_ERROR,
    ):
        sitemap_bundle.refresh()


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
