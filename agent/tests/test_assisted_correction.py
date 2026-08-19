"""Taking a correction down the phone: the record has to carry the reporter's consent.

A transcriber is a weaker position than self-service, not a stronger one. The
person cannot see the screen, so nothing here is filed unless the record proves
they were told what would be stored, agreed to it, and heard each value read back.

The schema is also a boundary against authentication secrets. It names every
field it accepts and refuses the rest before validation reads a value, so a
password or a one-time code cannot arrive in a correction even by accident.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.admin_api import (  # noqa: E402
    AssistedCorrectionBody,
    StepUpRefused,
    parse_assisted_body,
    validate_assisted_intake,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)


def _item(**overrides) -> dict:
    base = {
        "entity_id": "p-quan-com",
        "field_path": "attributes.phone",
        "reported_value": "0270 111 2222",
        "proposed_value": "0270 333 4444",
        "base_entity_revision": 7,
        "read_back_confirmed": True,
    }
    base.update(overrides)
    return base


def _body(**overrides) -> dict:
    base = {
        "channel": "phone",
        "privacy_notice_revision": "privacy-2026-07",
        "consent_scope": "correction.contact",
        "consent_given_at": NOW - timedelta(minutes=2),
        "reporter_privacy": "anonymous",
        "reporter_confirmed": True,
        "items": [_item()],
        "notification_consent": False,
    }
    base.update(overrides)
    return base


def _validate(**overrides) -> None:
    validate_assisted_intake(AssistedCorrectionBody(**_body(**overrides)), now=NOW)


# ── A complete, consented transcription ──

def test_a_properly_consented_call_passes_every_check():
    _validate()


def test_a_human_zalo_conversation_is_also_a_transcribed_channel():
    _validate(channel="zalo_human")


# ── What the reporter must have been given ──

@pytest.mark.parametrize("overrides,expected", [
    ({"privacy_notice_revision": "   "}, "privacy_notice_required"),
    ({"consent_scope": ""}, "consent_scope_required"),
    ({"consent_given_at": NOW + timedelta(minutes=1)}, "consent_not_yet_given"),
    ({"items": []}, "correction_items_required"),
    ({"items": [_item(read_back_confirmed=False)]}, "read_back_required"),
    ({"reporter_confirmed": False}, "reporter_confirmation_required"),
    ({"channel": "web"}, "assisted_channel_not_offered"),
])
def test_a_call_missing_any_of_the_promises_is_refused(overrides, expected):
    with pytest.raises(StepUpRefused) as excinfo:
        _validate(**overrides)

    assert excinfo.value.code == expected
    assert excinfo.value.status == 422


def test_one_unconfirmed_item_stops_the_whole_call():
    # Filing the confirmed half would leave a record the reporter never heard.
    with pytest.raises(StepUpRefused) as excinfo:
        _validate(items=[_item(), _item(field_path="attributes.address",
                                        read_back_confirmed=False)])

    assert excinfo.value.code == "read_back_required"


def test_a_self_service_channel_cannot_be_filed_as_a_transcription():
    # Claiming somebody was read to when they typed it themselves would put a
    # consent record in the file that nobody gave.
    for channel in ("web", "email_transcribed", "zalo_ai_handoff"):
        with pytest.raises(StepUpRefused):
            _validate(channel=channel)


# ── Authentication secrets cannot arrive here ──

SECRET = "hunter2-should-never-be-stored"


@pytest.mark.parametrize("field", ["password", "otp", "recovery_code", "secret",
                                   "totp", "session_token"])
def test_a_secret_like_field_is_refused_and_its_value_never_repeated(field):
    with pytest.raises(StepUpRefused) as excinfo:
        parse_assisted_body(_body(**{field: SECRET}))

    assert excinfo.value.status == 422
    # The refusal names the field, never what was in it. Pydantic's own message
    # quotes the value back, which would put the secret in the error body and
    # the log -- so the boundary rebuilds the refusal from locations alone.
    assert field in excinfo.value.detail
    assert SECRET not in excinfo.value.detail
    assert SECRET not in str(excinfo.value)


def test_the_raw_schema_error_is_never_what_reaches_a_caller():
    # Proving the reason the wrapper exists rather than trusting it.
    with pytest.raises(ValidationError) as raw:
        AssistedCorrectionBody(**_body(password=SECRET))
    assert SECRET in str(raw.value)

    with pytest.raises(StepUpRefused) as refused:
        parse_assisted_body(_body(password=SECRET))
    assert SECRET not in str(refused.value.detail)


def test_a_secret_hidden_inside_an_item_is_refused_too():
    with pytest.raises(StepUpRefused) as excinfo:
        parse_assisted_body(_body(items=[_item(otp="000000")]))

    assert "otp" in excinfo.value.detail
    assert "000000" not in excinfo.value.detail


def test_there_is_nowhere_to_put_a_recording_or_a_transcript():
    # The pilot does not record calls, so the schema offers no field that would
    # invite an operator to paste one in.
    for field in ("recording_url", "transcript", "call_audio", "notes"):
        with pytest.raises(StepUpRefused):
            parse_assisted_body(_body(**{field: "x"}))
