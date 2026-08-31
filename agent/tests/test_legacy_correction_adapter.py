"""One write authority per report: the Kernel or the old JSONL file, never both.

The legacy endpoints predate the case kernel and append to reports.jsonl. Once
correction intake is switched on, a factual field report filed there would fork
the record: an operator watching the queue would never see it, and the reporter
would hold a "đã ghi nhận" that nothing tracks. So while the switch is off the
old behaviour stands untouched, and while it is on, correction-classified
requests go to the kernel alone and come back with the canonical receipt.

Cutover is one-way. Once a correction has been routed to the kernel, rolling the
flag back must not quietly reopen the JSONL lane for corrections — a fork in the
record is worse than an honest refusal.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("BUILD_SEARCH_INDEXES", "false")
os.environ.setdefault("BACKGROUND_INDEX_BUILD", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from fastapi.testclient import TestClient  # noqa: E402

import public_api  # noqa: E402
from cases.public_api import configure_case_public_api  # noqa: E402
from server import app  # noqa: E402

client = TestClient(app)
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc)


class _KernelDouble:
    def __init__(self) -> None:
        self.filed: list[dict] = []

    def create_correction_from_transport(self, payload, *, idempotency_key,
                                         correlation_id, rate_subject,
                                         session_user_ref=None, now=None):
        item = payload.items[0]
        self.filed.append({
            "entity_id": item.entity_id,
            "field_path": item.field_path,
            "reported_value": item.reported_value,
            "proposed_value": item.proposed_value,
            "base_entity_revision": item.base_entity_revision,
            "rate_subject": rate_subject,
        })
        return SimpleNamespace(
            case_id="case-1",
            public_reference="VL-COR-0000000000042",
            capability="A" * 43,
            received_at=NOW,
            next_update_at=NOW,
            replayed=False,
        )


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    """Flags on, kernel doubled, JSONL redirected to a fresh temp file."""
    from config import settings

    reports = tmp_path / "reports.jsonl"
    monkeypatch.setattr(public_api, "REPORTS_FILE", reports)
    monkeypatch.setattr(public_api.report_limiter, "is_allowed", lambda ip: (True, {}))
    monkeypatch.setattr(
        public_api, "_get_public_entity",
        lambda entity_id: {
            "id": entity_id, "name": "Quán Cơm Bà Tư", "revision": 7,
            "attributes": {"phone": "0270 111 2222"},
        } if entity_id == "p-quan-com" else None,
    )
    monkeypatch.setattr(settings, "CASE_KERNEL_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "CORRECTION_INTAKE_ENABLED", True, raising=False)
    kernel = _KernelDouble()
    configure_case_public_api(service=kernel)
    yield kernel, reports
    configure_case_public_api(service=None)


def _jsonl_lines(reports: Path) -> list[dict]:
    if not reports.exists():
        return []
    return [json.loads(line) for line in reports.read_text(encoding="utf-8").splitlines()]


# ── While the switch is off, nothing changes ──

def test_with_intake_off_a_stale_report_still_goes_to_jsonl(tmp_path, monkeypatch):
    from config import settings

    reports = tmp_path / "reports.jsonl"
    monkeypatch.setattr(public_api, "REPORTS_FILE", reports)
    monkeypatch.setattr(public_api.report_limiter, "is_allowed", lambda ip: (True, {}))
    monkeypatch.setattr(settings, "CORRECTION_INTAKE_ENABLED", False, raising=False)

    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "phone", "detail": "số mới 0270 333 4444"})

    assert response.status_code == 200
    assert len(_jsonl_lines(reports)) == 1


# ── With the switch on, one authority ──

def test_a_stale_field_report_files_a_kernel_case_and_returns_the_receipt(legacy):
    kernel, reports = legacy

    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "phone", "detail": "0270 333 4444"})

    assert response.status_code == 201
    body = response.json()
    assert body["publicReference"] == "VL-COR-0000000000042"
    assert body["capability"] == "A" * 43
    # The kernel got the correction; the JSONL file got nothing. Never both.
    assert kernel.filed[0]["field_path"] == "attributes.phone"
    assert kernel.filed[0]["reported_value"] == "0270 111 2222"
    assert kernel.filed[0]["proposed_value"] == "0270 333 4444"
    assert kernel.filed[0]["base_entity_revision"] == 7
    assert _jsonl_lines(reports) == []


def test_legacy_correction_invokes_the_shared_schema_before_service(legacy, monkeypatch):
    import api_schemas

    calls = []
    original = api_schemas.CorrectionIntakeContract.model_validate

    def spy(cls, value, *args, **kwargs):
        calls.append(value)
        return original(value, *args, **kwargs)

    monkeypatch.setattr(
        api_schemas.CorrectionIntakeContract,
        "model_validate",
        classmethod(spy),
    )

    kernel, reports = legacy
    response = client.post(
        "/api/entities/p-quan-com/report-stale",
        json={"field": "phone", "detail": "0270 333 4444"},
    )

    assert response.status_code == 201
    assert calls == [{
        "reported_value_known": True,
        "reported_value": "0270 111 2222",
    }]
    assert len(kernel.filed) == 1
    assert _jsonl_lines(reports) == []


def test_legacy_invalid_generated_current_value_is_rejected_before_service(legacy, monkeypatch):
    kernel, reports = legacy
    monkeypatch.setattr(
        public_api,
        "_get_public_entity",
        lambda _entity_id: {
            "id": "p-quan-com",
            "revision": 7,
            "attributes": {},
        },
    )

    response = client.post(
        "/api/entities/p-quan-com/report-stale",
        json={"field": "phone", "detail": "0270 333 4444"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_correction_value"
    assert kernel.filed == []
    assert _jsonl_lines(reports) == []


def test_the_reported_value_is_read_from_the_live_entry_not_from_the_reporter(legacy):
    kernel, _reports = legacy

    client.post("/api/entities/p-quan-com/report-stale",
                json={"field": "phone", "detail": "0270 333 4444"})

    # What the page says now is ours to know; the reporter only supplies what it
    # should say. Trusting them for both would let one request forge a diff.
    assert kernel.filed[0]["reported_value"] == "0270 111 2222"


def test_a_field_the_kernel_cannot_hold_stays_on_the_legacy_lane(legacy):
    kernel, reports = legacy

    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "images", "detail": "ảnh không đúng chỗ"})

    assert response.status_code == 200
    assert kernel.filed == []
    assert len(_jsonl_lines(reports)) == 1


def test_a_correction_without_the_correct_value_is_asked_for_it(legacy):
    kernel, reports = legacy

    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "phone", "detail": "   "})

    # A correction is a claim about what the page should say. With nothing
    # proposed there is nothing to decide, and silently downgrading to the old
    # lane would fork the record by the reporter's punctuation.
    assert response.status_code == 422
    assert kernel.filed == []
    assert _jsonl_lines(reports) == []


def test_an_unknown_entity_is_refused_without_reaching_either_lane(legacy):
    kernel, reports = legacy

    response = client.post("/api/entities/p-khong-ton-tai/report-stale",
                           json={"field": "phone", "detail": "0270 333 4444"})

    assert response.status_code == 404
    assert kernel.filed == []
    assert _jsonl_lines(reports) == []


def test_a_generic_entity_report_with_a_mapped_field_also_goes_to_the_kernel(legacy):
    kernel, reports = legacy

    response = client.post("/api/report", json={
        "target_id": "p-quan-com", "target_type": "facility",
        "reason": "sai số điện thoại", "detail": "0270 333 4444", "field": "phone",
    })

    assert response.status_code == 201
    assert kernel.filed[0]["entity_id"] == "p-quan-com"
    assert _jsonl_lines(reports) == []


def test_a_content_report_keeps_its_moderation_lane_untouched(legacy):
    kernel, reports = legacy

    response = client.post("/api/report", json={
        "target_id": "post-99", "target_type": "post",
        "reason": "nội dung xúc phạm", "detail": "bài đăng chửi bới",
    })

    # Policy violations are moderation work, not corrections; the kernel holds
    # promises about public facts, not about people's behaviour.
    assert response.status_code == 200
    assert kernel.filed == []
    assert len(_jsonl_lines(reports)) == 1


# ── Cutover is one-way ──

def test_rolling_the_flag_back_does_not_reopen_the_jsonl_correction_lane(legacy, monkeypatch):
    from config import settings

    kernel, reports = legacy
    client.post("/api/entities/p-quan-com/report-stale",
                json={"field": "phone", "detail": "0270 333 4444"})
    assert len(kernel.filed) == 1

    monkeypatch.setattr(settings, "CORRECTION_INTAKE_ENABLED", False, raising=False)
    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "phone", "detail": "0270 555 6666"})

    # An honest refusal, not a silent fork: the kernel now owns corrections, and
    # a JSONL line written here would be a report nobody is watching.
    assert response.status_code == 503
    assert _jsonl_lines(reports) == []


def test_the_cutover_survives_a_process_restart_because_it_is_a_file(legacy, monkeypatch):
    from config import settings

    _kernel, reports = legacy
    client.post("/api/entities/p-quan-com/report-stale",
                json={"field": "phone", "detail": "0270 333 4444"})

    marker = public_api._correction_cutover_marker()
    assert marker.exists(), "cutover must be durable, not a module global"
    monkeypatch.setattr(settings, "CORRECTION_INTAKE_ENABLED", False, raising=False)

    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "phone", "detail": "0270 555 6666"})
    assert response.status_code == 503


def test_fields_the_kernel_never_took_over_still_work_after_cutover(legacy, monkeypatch):
    from config import settings

    _kernel, reports = legacy
    client.post("/api/entities/p-quan-com/report-stale",
                json={"field": "phone", "detail": "0270 333 4444"})
    monkeypatch.setattr(settings, "CORRECTION_INTAKE_ENABLED", False, raising=False)

    response = client.post("/api/entities/p-quan-com/report-stale",
                           json={"field": "images", "detail": "ảnh không đúng"})

    # The guard is correction-specific. Reports the kernel cannot hold keep
    # their old lane; closing it would leave them nowhere at all.
    assert response.status_code == 200
    assert len(_jsonl_lines(reports)) == 1
