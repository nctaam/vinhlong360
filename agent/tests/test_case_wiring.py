"""The composition root: flags on means configured, flags off means dormant.

Every configure_case_* existed and nothing in production ever called them, so
raising the flags would have produced a mounted router answering 500
`case_service_not_configured` on its first request. These tests hold the one
function whose job is to make that impossible.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases import wiring  # noqa: E402

MASTER_KEY = "0" * 43


def _settings(**overrides):
    base = dict(
        CASE_KERNEL_ENABLED=True,
        CASE_KERNEL_ENCRYPTION_KEY=MASTER_KEY,
        CASE_SERVICE_OWNER_REF="person:owner",
        cors_origins_list=lambda: ["http://localhost:3000", "https://vinhlong360.vn"],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _unwire():
    yield
    # Leave no configured global behind for the rest of the suite.
    from cases.admin_api import configure_case_admin_api
    from cases.correction import configure_case_correction
    from cases.metrics import configure_case_metrics
    from cases.public_api import configure_case_public_api
    from cases.publication import configure_case_publication
    from cases.work_control import configure_case_work_control

    configure_case_public_api(service=None, settings=None, allowed_origin=None)
    configure_case_correction(database=None, crypto=None, policy=None)
    configure_case_publication(database=None, crypto=None, policy=None)
    configure_case_work_control(database=None, policy=None)
    configure_case_admin_api(database=None, crypto=None, projection_fetcher=None,
                             service=None)
    configure_case_metrics(database=None)


def test_a_sleeping_kernel_wires_nothing():
    from cases import public_api

    wired = wiring.wire_case_kernel(object(), _settings(CASE_KERNEL_ENABLED=False))

    assert wired is False
    with pytest.raises(RuntimeError, match="case_service_not_configured"):
        public_api._service()


def test_raising_the_flag_configures_every_module():
    from cases import admin_api, metrics, public_api

    wired = wiring.wire_case_kernel(object(), _settings())

    # The exact failure this module exists to prevent: a mounted router whose
    # first request answers 500 because nobody built the service.
    assert wired is True
    assert public_api._service() is not None
    assert admin_api._SERVICE is not None and admin_api._CRYPTO is not None
    assert metrics._DATABASE is not None


def test_the_public_origin_is_the_deployment_https_origin():
    assert wiring.site_origin(_settings()) == "https://vinhlong360.vn"


def test_a_broken_key_leaves_the_kernel_dormant_not_half_alive():
    from cases import public_api

    wired = wiring.wire_case_kernel(object(), _settings(CASE_KERNEL_ENCRYPTION_KEY="ngắn"))

    # All or nothing: a service without working crypto would take intake it can
    # never answer for. Failure logs loudly and configures nothing.
    assert wired is False
    with pytest.raises(RuntimeError):
        public_api._service()


def test_without_https_there_is_no_projection_fetcher():
    fetcher = wiring.build_projection_fetcher(
        _settings(cors_origins_list=lambda: ["http://localhost:3000"])
    )

    # Verify then answers 503 honestly instead of pretending it looked.
    assert fetcher is None


def test_the_fetcher_pins_exactly_our_own_origin(monkeypatch):
    import pinned_http

    seen = {}

    def capture(self, url, *, user_agent, policy, audit_context):
        seen.update(url=url, policy=policy, audit_context=audit_context)
        return SimpleNamespace(content=b'{"id": "p-1", "revision": 4}')

    # Captured, never dialled: a unit test that reaches the real internet is a
    # flake factory and an information leak rolled into one.
    monkeypatch.setattr(pinned_http.PinnedHTTPClient, "get", capture)
    fetcher = wiring.build_projection_fetcher(_settings())

    assert fetcher is not None
    assert fetcher("p-1") == {"id": "p-1", "revision": 4}
    assert seen["url"] == "https://vinhlong360.vn/api/entities/p-1"
    # The policy canonicalises origins to include the port.
    assert seen["policy"].allowed_origins == ("https://vinhlong360.vn:443",)
    assert seen["policy"].max_redirects == 0
    assert seen["audit_context"] == "projection_verify"
