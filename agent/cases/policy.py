import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_KEYS = frozenset({'revision', 'owner_ref_env', 'receipt_target_seconds', 'triage_target_seconds', 'update_target_seconds', 'resolution_target_seconds_by_risk', 'lease_duration_seconds', 'risk_registry', 'maker_checker_rules', 'retention', 'notification_channel', 'assisted_coverage', 'public_resolution_sla_enabled'})

@dataclass(frozen=True)
class CasePolicy:
    revision: str; owner_ref_env: str; receipt_target_seconds: int; triage_target_seconds: int; update_target_seconds: int; resolution_target_seconds_by_risk: dict[str, int]; lease_duration_seconds: int; risk_registry: dict[str, dict[str, Any]]; maker_checker_rules: dict[str, bool]; retention: dict[str, int]; notification_channel: str; assisted_coverage: dict[str, Any]; public_resolution_sla_enabled: bool

def _positive(value: Any, label: str) -> None:
    if not isinstance(value, int) or value <= 0: raise ValueError(f'{label} must be positive')

def _validate_coverage(coverage: dict[str, Any]) -> None:
    if not isinstance(coverage, dict) or not all(coverage.get(key) for key in ('timezone', 'weekdays', 'hours', 'duty_roster', 'fallback_copy')): raise ValueError('assisted coverage is incomplete')

def load_case_policy(path: Path | None = None) -> CasePolicy:
    path = path or Path(__file__).resolve().parents[2] / 'config' / 'case-service-policy.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data) != _KEYS: raise ValueError('policy requires exact top-level keys')
    if data['revision'] != 'correction-pilot-v1' or data['owner_ref_env'] != 'CASE_SERVICE_OWNER_REF': raise ValueError('invalid policy authority')
    for key in ('receipt_target_seconds', 'triage_target_seconds', 'update_target_seconds', 'lease_duration_seconds'): _positive(data[key], key)
    for value in data['resolution_target_seconds_by_risk'].values(): _positive(value, 'resolution clock')
    for value in data['retention'].values(): _positive(value, 'retention')
    if data['public_resolution_sla_enabled']: raise ValueError('public resolution SLA is disabled')
    if any(not data['risk_registry'].get(risk, {}).get('independent_review') or not data['maker_checker_rules'].get(risk) for risk in ('R2', 'R3')): raise ValueError('R2/R3 require independent review')
    _validate_coverage(data['assisted_coverage'])
    return CasePolicy(**data)
