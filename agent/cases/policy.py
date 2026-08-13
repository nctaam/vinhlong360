import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class CasePolicy:
    revision: str; owner_ref_env: str; receipt_target_seconds: int; triage_target_seconds: int; update_target_seconds: int; public_resolution_sla_enabled: bool

def load_case_policy() -> CasePolicy:
    path = Path(__file__).resolve().parents[2] / 'config' / 'case-service-policy.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    required = {'revision','owner_ref_env','receipt_target_seconds','triage_target_seconds','update_target_seconds','public_resolution_sla_enabled'}
    if set(data) - required - {'lease_duration_seconds','risk_registry','maker_checker','retention','notification_channel','assisted_coverage'} or not required <= set(data):
        raise ValueError('invalid case policy keys')
    clocks = [data[k] for k in ('receipt_target_seconds','triage_target_seconds','update_target_seconds')]
    if any(not isinstance(v, int) or v <= 0 for v in clocks): raise ValueError('clock values must be positive')
    if data['public_resolution_sla_enabled']: raise ValueError('public resolution SLA is disabled')
    return CasePolicy(*(data[k] for k in ('revision','owner_ref_env','receipt_target_seconds','triage_target_seconds','update_target_seconds','public_resolution_sla_enabled')))
