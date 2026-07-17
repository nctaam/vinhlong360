from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

if __package__:
    from .launch_evidence import current_policy_evidence
else:
    from launch_evidence import current_policy_evidence


router = APIRouter(prefix="/_internal", include_in_schema=False)


@router.get("/launch-policy-attestation")
def launch_policy_attestation() -> JSONResponse:
    try:
        evidence = current_policy_evidence()
        payload = {
            "policy_fingerprint": evidence.policy_fingerprint,
            "route_manifest_revision": evidence.route_manifest_revision,
            "backend_policy_revision": evidence.backend_policy_revision,
        }
        return JSONResponse(content=payload)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Launch policy evidence unavailable",
        ) from exc
