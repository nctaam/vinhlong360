"""The production composition root for the case kernel.

Every `configure_case_*` in this package existed, and until this module nothing
outside the tests ever called them. Flags on would have meant a mounted router
answering 500 `case_service_not_configured` on the first request — a capability
advertised and then dropped, which is worse than 404.

`wire_case_kernel(database, settings)` is called once at server startup. With
the kernel flag off it deliberately configures nothing: dormant stays dormant,
and every case route keeps answering 404.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger("cases.wiring")


def site_origin(settings) -> str | None:
    """The one public origin this deployment answers on."""
    origins = [o for o in settings.cors_origins_list() if o.startswith("https://")]
    if origins:
        return origins[0]
    fallback = settings.cors_origins_list()
    return fallback[0] if fallback else None


def build_projection_fetcher(settings):
    """A bounded, same-origin reader of the public entity projection.

    Verification exists to see what a reader is served, so it goes through the
    pinned HTTP client against our own public origin — caches and all. If the
    origin cannot be pinned (dev without TLS), the fetcher is None and the
    verify route answers 503 honestly instead of pretending it looked.
    """
    origin = site_origin(settings)
    if not origin or not origin.startswith("https://"):
        return None

    from pinned_http import EgressPolicy, PinnedHTTPClient

    policy = EgressPolicy(
        max_encoded_bytes=512 * 1024,
        max_decoded_bytes=1024 * 1024,
        accepted_encodings=("gzip", "identity"),
        inactivity_timeout_seconds=10.0,
        total_timeout_seconds=20.0,
        max_redirects=0,
        allowed_origins=(origin,),
    )
    client = PinnedHTTPClient()

    def fetch(entity_id: str) -> dict:
        response = client.get(
            f"{origin}/api/entities/{entity_id}",
            user_agent="vinhlong360-projection-verify/1",
            policy=policy,
            audit_context="projection_verify",
        )
        return json.loads(response.content.decode("utf-8"))

    return fetch


def _sms_provider(settings):
    """The one eSMS transport, built the same way the scheduler builds it."""
    from sms_provider import EsmsProvider

    return EsmsProvider(
        api_key=getattr(settings, "ESMS_API_KEY", ""),
        secret=getattr(settings, "ESMS_SECRET", ""),
        brandname=getattr(settings, "ESMS_BRANDNAME", ""),
    )


def wire_case_kernel(database, settings) -> bool:
    """Configure every case module against the live database, or nothing at all.

    Returns True when the kernel was wired. All-or-nothing on purpose: a
    half-wired kernel (service up, publication unconfigured) would take intake
    and then fail the promise, so any failure here leaves everything dormant
    and logs why.
    """
    if not getattr(settings, "CASE_KERNEL_ENABLED", False):
        return False
    try:
        from .admin_api import configure_case_admin_api
        from .correction import configure_case_correction
        from .metrics import configure_case_metrics
        from .policy import load_case_policy
        from .public_api import configure_case_public_api
        from .publication import configure_case_publication
        from .security import CaseCrypto
        from .service import CaseService
        from .store import PostgresCaseStore
        from .work_control import configure_case_work_control

        crypto = CaseCrypto(settings.CASE_KERNEL_ENCRYPTION_KEY)
        policy = load_case_policy()
        store = PostgresCaseStore(database)
        service = CaseService(
            store, crypto, policy,
            owner_ref=settings.CASE_SERVICE_OWNER_REF, database=database,
        )

        configure_case_public_api(
            service=service, settings=settings, allowed_origin=site_origin(settings),
        )
        configure_case_correction(database=database, crypto=crypto, policy=policy)
        configure_case_publication(database=database, crypto=crypto, policy=policy)
        configure_case_work_control(database=database, policy=policy)
        configure_case_admin_api(
            database=database, crypto=crypto,
            projection_fetcher=build_projection_fetcher(settings),
            service=service,
        )
        # The optional-phone promise is part of intake, so its module is part of
        # the same all-or-nothing wiring: unconfigured, every notification the
        # reporter consented to would 500 at the moment it mattered.
        from .contact import configure_case_contact

        configure_case_contact(database=database, crypto=crypto,
                               provider=_sms_provider(settings))
        configure_case_metrics(database=database)
        logger.info("case kernel wired (owner=%s)", settings.CASE_SERVICE_OWNER_REF)
        return True
    except Exception:
        # Dormant beats half-alive: leave every module unconfigured so the
        # routes fail closed, and make the reason loud.
        logger.exception("CASE_KERNEL_WIRING_FAILED — kernel stays dormant")
        return False
