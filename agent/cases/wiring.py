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
from dataclasses import dataclass

logger = logging.getLogger("cases.wiring")


@dataclass(frozen=True)
class CaseDependencies:
    """Immutable dependency bundle assembled before touching module globals."""

    database: object
    crypto: object
    policy: object
    projection_fetcher: object
    sms_provider: object


def site_origin(settings) -> str | None:
    """The one public origin this deployment answers on.

    `cors_origins_list` is a @property. Calling it raised TypeError inside
    wire_case_kernel's try block, which logged and left the kernel dormant — so
    the composition root added to fix "nothing wires the kernel" wired nothing
    itself. The unit test missed it because its fake settings object supplied a
    callable, matching the mistake rather than the real object.
    """
    configured = list(settings.cors_origins_list)
    secure = [origin for origin in configured if origin.startswith("https://")]
    if secure:
        return secure[0]
    return configured[0] if configured else None


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


def build_case_dependencies(database, settings) -> CaseDependencies:
    """Build and validate the complete case bundle without mutating globals."""
    if database is None:
        raise ValueError("case_database_required")
    from .policy import load_case_policy
    from .security import CaseCrypto

    crypto = CaseCrypto(settings.CASE_KERNEL_ENCRYPTION_KEY)
    policy = load_case_policy()
    projection_fetcher = build_projection_fetcher(settings)
    sms_provider = _sms_provider(settings)
    owner_ref = getattr(settings, "CASE_SERVICE_OWNER_REF", "")
    if not owner_ref:
        raise ValueError("case_owner_ref_required")
    bundle = CaseDependencies(
        database=database,
        crypto=crypto,
        policy=policy,
        projection_fetcher=projection_fetcher,
        sms_provider=sms_provider,
    )
    object.__setattr__(bundle, "owner_ref", owner_ref)
    if any(getattr(bundle, name, None) is None for name in (
        "database", "crypto", "policy", "sms_provider"
    )):
        raise ValueError("incomplete_case_dependencies")
    return bundle


def commit_case_dependencies(bundle: CaseDependencies) -> None:
    """Publish a validated bundle to every case module in one guarded step."""
    if not isinstance(bundle, CaseDependencies):
        raise TypeError("invalid_case_dependencies")
    if any(getattr(bundle, name, None) is None for name in (
        "database", "crypto", "policy", "sms_provider"
    )):
        raise ValueError("incomplete_case_dependencies")
    from .admin_api import configure_case_admin_api
    from .contact import configure_case_contact
    from .correction import configure_case_correction
    from .metrics import configure_case_metrics
    from .outbox import configure_case_outbox
    from .public_api import configure_case_public_api
    from .publication import configure_case_publication
    from .service import CaseService
    from .store import PostgresCaseStore
    from .work_control import configure_case_work_control

    try:
        service = CaseService(
            PostgresCaseStore(bundle.database), bundle.crypto, bundle.policy,
            owner_ref=getattr(bundle, "owner_ref", "person:case-owner"),
            database=bundle.database,
        )
        settings = getattr(bundle, "settings", None)
        configure_case_public_api(
            service=service,
            settings=settings,
            allowed_origin=getattr(bundle, "allowed_origin", None),
        )
        configure_case_correction(database=bundle.database, crypto=bundle.crypto,
                                  policy=bundle.policy)
        configure_case_publication(database=bundle.database, crypto=bundle.crypto,
                                   policy=bundle.policy)
        configure_case_work_control(database=bundle.database, policy=bundle.policy)
        configure_case_admin_api(
            database=bundle.database, crypto=bundle.crypto,
            projection_fetcher=bundle.projection_fetcher, service=service,
        )
        configure_case_contact(database=bundle.database, crypto=bundle.crypto,
                               provider=bundle.sms_provider)
        configure_case_outbox(database=bundle.database, crypto=bundle.crypto,
                              provider=bundle.sms_provider)
        configure_case_metrics(database=bundle.database)
    except Exception:
        reset_case_dependencies()
        raise


def reset_case_dependencies() -> None:
    """Return every case module to its dormant, fail-closed state."""
    from . import admin_api, contact, correction, metrics, outbox, public_api, publication, work_control

    # Assign the module slots directly so reset remains reliable even when a
    # failing configure hook was injected by a startup proof test.
    for module, names in (
        (public_api, ("_SERVICE", "_SETTINGS", "_ALLOWED_ORIGIN")),
        (correction, ("_DATABASE", "_CRYPTO", "_POLICY")),
        (publication, ("_DATABASE", "_CRYPTO", "_POLICY")),
        (work_control, ("_DATABASE", "_POLICY")),
        (admin_api, ("_DATABASE", "_CRYPTO", "_PROJECTION_FETCHER", "_SERVICE")),
        (contact, ("_DATABASE", "_CRYPTO", "_PROVIDER", "_CODE_SOURCE")),
        (outbox, ("_DATABASE", "_CRYPTO", "_PROVIDER", "_CONTACT_LOOKUP")),
        (metrics, ("_DATABASE",)),
    ):
        for name in names:
            setattr(module, name, None)



def wire_case_kernel(database, settings) -> bool:
    """Configure every case module against the live database, or nothing at all.

    Returns True when the kernel was wired. All-or-nothing on purpose: a
    half-wired kernel (service up, publication unconfigured) would take intake
    and then fail the promise, so any failure here leaves everything dormant
    and logs why.
    """
    if not getattr(settings, "CASE_KERNEL_ENABLED", False):
        reset_case_dependencies()
        return False
    try:
        bundle = build_case_dependencies(database, settings)
        object.__setattr__(bundle, "settings", settings)
        object.__setattr__(bundle, "allowed_origin", site_origin(settings))
        commit_case_dependencies(bundle)
        logger.info("case kernel wired (owner=%s)", settings.CASE_SERVICE_OWNER_REF)
        return True
    except Exception:
        # Dormant beats half-alive: leave every module unconfigured so the
        # routes fail closed, and make the reason loud.
        reset_case_dependencies()
        logger.exception("CASE_KERNEL_WIRING_FAILED — kernel stays dormant")
        return False
