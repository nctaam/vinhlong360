from __future__ import annotations

import pytest
from pydantic import ValidationError

from notifications import ReportRequest


def test_report_request_allows_entity_reports() -> None:
    report = ReportRequest(target_type="entity", target_id="ao-ba-om", reason="Sai toa do hien thi")

    assert report.target_type == "entity"
    assert report.target_id == "ao-ba-om"


def test_report_request_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        ReportRequest(target_type="placeid", target_id="x", reason="Ly do hop le")
