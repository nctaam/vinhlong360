from datetime import datetime, timezone


def test_report_export_is_minimal_and_redacts_personal_detail():
    from reports.models import ReportRecord, ReportStatus, ReportTargetType

    record = ReportRecord(
        report_id="r-1",
        target_id="post-1",
        target_type=ReportTargetType.POST,
        reason="wrong contact",
        status=ReportStatus.PENDING,
        actor_scope="user:private-user",
        detail="Call me at 0901234567 or email user@example.com",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    exported = record.to_export_dict()

    assert set(exported) == {
        "report_id",
        "target",
        "reason",
        "status",
        "created_at",
        "updated_at",
        "actor_pseudonym",
        "detail",
    }
    assert exported["target"] == {"type": "post", "id": "post-1"}
    assert exported["actor_pseudonym"] != "user:private-user"
    assert "0901234567" not in exported["detail"]
    assert "user@example.com" not in exported["detail"]


def test_erasure_result_exposes_row_count_receipt():
    from erasure import ErasureResult

    result = ErasureResult(
        status="completed",
        verified=True,
        run_id="run-1",
        stores=(
            {
                "store_name": "reports",
                "removed_count": 3,
                "residual_count": 0,
                "verified": True,
            },
        ),
    )

    receipt = result.to_dict()["receipt"]

    assert receipt["run_id"] == "run-1"
    assert receipt["stores"] == [{
        "store_name": "reports",
        "rows_before": 3,
        "rows_after": 0,
        "verified": True,
    }]
