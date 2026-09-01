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


class _Settings(SimpleNamespace):
    """A stand-in that keeps the real object's SHAPE, not a convenient one.

    cors_origins_list is a @property on the real Settings. The first version of
    this fake made it a callable, which matched the production code's mistake
    instead of the production object — so a TypeError that killed the entire
    composition root passed every test here.
    """

    @property
    def cors_origins_list(self):
        return list(self._origins)


def _settings(**overrides):
    origins = overrides.pop(
        "origins", ["http://localhost:3000", "https://vinhlong360.vn"],
    )
    base = dict(
        CASE_KERNEL_ENABLED=True,
        CASE_KERNEL_ENCRYPTION_KEY=MASTER_KEY,
        CASE_SERVICE_OWNER_REF="person:owner",
        _origins=origins,
    )
    base.update(overrides)
    return _Settings(**base)


@pytest.fixture(autouse=True)
def _unwire():
    yield
    # Leave no configured global behind for the rest of the suite.
    from cases.admin_api import configure_case_admin_api
    from cases.contact import configure_case_contact
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
    configure_case_contact(database=None, crypto=None, provider=None)
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
    # Contact belongs to the same all-or-nothing wiring: unconfigured, every
    # notification the reporter consented to would 500 at the moment it mattered.
    from cases import contact

    assert contact._DATABASE is not None and contact._PROVIDER is not None


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
        _settings(origins=["http://localhost:3000"])
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


def test_the_real_settings_object_survives_the_composition_root():
    """The shape check no fake can give you.

    site_origin reads settings.cors_origins_list. On the real object that is a
    @property; the version of this file that preceded this test handed the code
    a callable and so agreed with the bug. Read the production object.
    """
    from config import settings

    origin = wiring.site_origin(settings)

    assert origin is None or isinstance(origin, str)
    assert not callable(type(settings).cors_origins_list.__get__(settings))


def test_failed_commit_cannot_be_reactivated_by_public_configuration(monkeypatch):
    """A failed commit keeps every HTTP surface dormant despite enabled flags."""
    from cases import admin_api, public_api

    bundle = wiring.build_case_dependencies(object(), _settings())

    def fail(**kwargs):
        raise RuntimeError("injected commit failure")

    monkeypatch.setattr(admin_api, "configure_case_admin_api", fail)
    with pytest.raises(RuntimeError, match="injected commit failure"):
        wiring.commit_case_dependencies(bundle)

    public_api.configure_case_public_api(
        service=object(), settings=_settings(CASE_KERNEL_ENABLED=True),
        allowed_origin="https://vinhlong360.vn",
    )

    assert wiring.case_kernel_ready() is False
    assert public_api._kernel_ready() is False

    from fastapi import HTTPException
    from config import settings

    monkeypatch.setattr(settings, "CASE_KERNEL_ENABLED", True, raising=False)
    with pytest.raises(HTTPException) as excinfo:
        admin_api._require_kernel()
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail["code"] == "capability_unavailable"
