from __future__ import annotations

import pytest
from pydantic import ValidationError

from notifications import ReportRequest, NotifPrefsUpdate, _NOTIF_TYPE_TO_PREF


def test_report_request_allows_entity_reports() -> None:
    report = ReportRequest(target_type="entity", target_id="ao-ba-om", reason="Sai toa do hien thi")

    assert report.target_type == "entity"
    assert report.target_id == "ao-ba-om"


def test_report_request_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        ReportRequest(target_type="placeid", target_id="x", reason="Ly do hop le")


# -- Notification preferences --


def test_notif_prefs_update_partial() -> None:
    body = NotifPrefsUpdate(pref_like=False)
    dump = body.model_dump()
    assert dump["pref_like"] is False
    assert dump["pref_comment"] is None


def test_notif_prefs_update_all_fields() -> None:
    body = NotifPrefsUpdate(
        pref_like=False, pref_comment=True, pref_mention=False,
        pref_follow=True, pref_system=False,
    )
    dump = {k: v for k, v in body.model_dump().items() if v is not None}
    assert len(dump) == 5
    assert dump["pref_like"] is False
    assert dump["pref_system"] is False


def test_notif_type_to_pref_mapping() -> None:
    assert _NOTIF_TYPE_TO_PREF["like"] == "pref_like"
    assert _NOTIF_TYPE_TO_PREF["comment"] == "pref_comment"
    assert _NOTIF_TYPE_TO_PREF["mention"] == "pref_mention"
    assert _NOTIF_TYPE_TO_PREF["follow"] == "pref_follow"
    assert "repost" not in _NOTIF_TYPE_TO_PREF
    assert "entity_post" not in _NOTIF_TYPE_TO_PREF
