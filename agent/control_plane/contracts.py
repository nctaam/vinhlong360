"""Small, explicit registry for contracts shared by the case transports.

The registry is intentionally boring: a version is part of the lookup key and
validation fails closed.  Callers can translate the resulting violation into
an RFC 9457-style problem document without losing the field that was wrong.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ContractSpec:
    name: str
    version: str
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...] = ()
    error_codes: tuple[str, ...] = ()


class ContractViolation(ValueError):
    code = "CONTRACT_INVALID"

    def __init__(self, detail: str, *, field: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.field = field


_REGISTRY: dict[tuple[str, str], ContractSpec] = {}
CORRECTION_INTAKE_CONTRACT_VERSION = "1"


def register_contract(spec: ContractSpec) -> None:
    if not isinstance(spec, ContractSpec) or not spec.name or not spec.version:
        raise ContractViolation("invalid contract specification")
    key = (spec.name, spec.version)
    if key in _REGISTRY:
        raise ContractViolation(f"contract already registered: {spec.name}@{spec.version}")
    _REGISTRY[key] = spec


def get_contract(name: str, version: str = CORRECTION_INTAKE_CONTRACT_VERSION) -> ContractSpec:
    try:
        return _REGISTRY[(name, version)]
    except KeyError as exc:
        raise ContractViolation(f"unknown contract version: {name}@{version}") from exc


def validate_payload(
    name: str,
    payload: Mapping[str, object],
    version: str = CORRECTION_INTAKE_CONTRACT_VERSION,
) -> None:
    """Validate required contract discriminators and reject ambiguous values."""
    if not isinstance(payload, Mapping):
        raise ContractViolation("payload must be an object")
    spec = get_contract(name, version)
    missing = [field for field in spec.request_fields if field not in payload]
    if missing:
        raise ContractViolation(
            f"missing required contract field: {missing[0]}", field=missing[0]
        )
    if name == "correction-intake":
        known = payload["reported_value_known"]
        if type(known) is not bool:
            raise ContractViolation(
                "reported_value_known must be a boolean",
                field="reported_value_known",
            )
        value = payload["reported_value"]
        if not known and value is not None:
            raise ContractViolation(
                "reported_value must be null when current value is unknown",
                field="reported_value",
            )


def problem_detail(
    code: str,
    detail: str,
    status: int,
    *,
    field: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, object]:
    """Build the stable problem envelope consumed by FE and operators."""
    result: dict[str, object] = {
        "type": f"https://vinhlong360.vn/problems/{code}",
        "title": code.replace("_", " "),
        "status": status,
        "detail": detail,
        "code": code,
    }
    if field is not None:
        result["field"] = field
    if correlation_id is not None:
        result["correlation_id"] = correlation_id
    return result


register_contract(
    ContractSpec(
        name="correction-intake",
        version=CORRECTION_INTAKE_CONTRACT_VERSION,
        request_fields=("reported_value_known", "reported_value"),
        response_fields=("public_reference", "received_at", "next_update_at"),
        error_codes=("CONTRACT_INVALID", "invalid_request"),
    )
)


__all__ = [
    "ContractSpec",
    "ContractViolation",
    "CORRECTION_INTAKE_CONTRACT_VERSION",
    "get_contract",
    "problem_detail",
    "register_contract",
    "validate_payload",
]
