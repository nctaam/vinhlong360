import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_KEYS = frozenset({'revision', 'owner_ref_env', 'receipt_target_seconds', 'triage_target_seconds', 'update_target_seconds', 'resolution_target_seconds_by_risk', 'lease_duration_seconds', 'risk_registry', 'maker_checker_rules', 'retention', 'notification_channel', 'assisted_coverage', 'public_resolution_sla_enabled'})
_RISK_KEYS = frozenset({'R0', 'R1', 'R2', 'R3'})
_COVERAGE_KEYS = frozenset({'timezone', 'weekdays', 'hours', 'duty_roster', 'fallback_copy'})

@dataclass(frozen=True)
class CasePolicy:
    revision: str; owner_ref_env: str; receipt_target_seconds: int; triage_target_seconds: int; update_target_seconds: int; resolution_target_seconds_by_risk: dict[str, int]; lease_duration_seconds: int; risk_registry: dict[str, dict[str, Any]]; maker_checker_rules: dict[str, bool]; retention: dict[str, int]; notification_channel: str; assisted_coverage: dict[str, Any]; public_resolution_sla_enabled: bool

def _positive(value: Any, label: str) -> None:
    if type(value) is not int or value <= 0: raise ValueError(f'{label} must be a positive integer')

def _risk_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _RISK_KEYS: raise ValueError(f'{label} must contain exactly R0-R3')
    return value

def _high_risk_rules(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict) or set(value) != {'R2', 'R3'}: raise ValueError('maker-checker rules must contain exactly R2 and R3')
    if any(type(rule) is not bool for rule in value.values()): raise ValueError('maker-checker rules must be boolean')
    return value

def _validate_coverage(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _COVERAGE_KEYS: raise ValueError('assisted coverage keys are invalid')
    if not isinstance(value['timezone'], str) or not value['timezone'].strip(): raise ValueError('assisted coverage timezone is invalid')
    if not isinstance(value['weekdays'], list) or not value['weekdays'] or not all(isinstance(day, str) and day.strip() for day in value['weekdays']): raise ValueError('assisted coverage weekdays are invalid')
    if any(not isinstance(value[key], str) or not value[key].strip() for key in ('hours', 'duty_roster', 'fallback_copy')): raise ValueError('assisted coverage is incomplete')
    return value

def load_case_policy(path: Path | None = None) -> CasePolicy:
    path = path or Path(__file__).resolve().parents[2] / 'config' / 'case-service-policy.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != _KEYS: raise ValueError('policy requires exact top-level keys')
    if data['revision'] != 'correction-pilot-v1' or data['owner_ref_env'] != 'CASE_SERVICE_OWNER_REF': raise ValueError('invalid policy authority')
    for key in ('receipt_target_seconds', 'triage_target_seconds', 'update_target_seconds', 'lease_duration_seconds'): _positive(data[key], key)
    resolution = _risk_mapping(data['resolution_target_seconds_by_risk'], 'resolution targets')
    for value in resolution.values(): _positive(value, 'resolution clock')
    registry = _risk_mapping(data['risk_registry'], 'risk registry')
    if any(not isinstance(config, dict) or set(config) != {'independent_review'} or type(config['independent_review']) is not bool for config in registry.values()): raise ValueError('risk registry independence must be boolean')
    rules = _high_risk_rules(data['maker_checker_rules'])
    if any(registry[risk].get('independent_review') is not True or rules[risk] is not True for risk in ('R2', 'R3')): raise ValueError('R2/R3 require independent review')
    retention = data['retention']
    if not isinstance(retention, dict) or set(retention) != {'case_days', 'receipt_days'}: raise ValueError('retention keys are invalid')
    for value in retention.values(): _positive(value, 'retention')
    if not isinstance(data['notification_channel'], str) or data['notification_channel'] != 'outbox': raise ValueError('notification channel is invalid')
    _validate_coverage(data['assisted_coverage'])
    if data['public_resolution_sla_enabled'] is not False: raise ValueError('public resolution SLA is disabled')
    return CasePolicy(**data)
