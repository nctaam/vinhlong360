"""Database-free contract for the correction service module."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.domain import ActorContext, Channel, CommandEnvelope, RiskClass  # noqa: E402
from cases.service import (  # noqa: E402
    CORRECTABLE_FIELD_PATHS,
    MAX_CORRECTION_ITEMS,
    MAX_CORRECTION_VALUE,
    CaseService,
    CorrectionItemInput,
    CorrectionRejected,
    CreateCorrectionCommand,
    SafetyRoutingRequired,
    ZaloHandoff,
    _looks_urgent,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _command(**overrides) -> CreateCorrectionCommand:
    defaults = {
        "envelope": CommandEnvelope(
            idempotency_key="k-1",
            expected_revision=None,
            actor=ActorContext(
                actor_ref="anonymous",
                channel=Channel.WEB,
                scopes=frozenset(),
                correlation_id="corr-1",
            ),
        ),
        "reporter_privacy": "anonymous",
        "items": (
            CorrectionItemInput(
                entity_id="p-x",
                field_path="attributes.phone",
                reported_value="a",
                proposed_value="b",
                base_entity_revision=1,
            ),
        ),
    }
    defaults.update(overrides)
    return CreateCorrectionCommand(**defaults)


def _service() -> CaseService:
    return CaseService(store=None, crypto=None, policy=None, owner_ref="person:owner")


def test_correctable_paths_are_a_closed_allowlist_of_published_fields():
    assert set(CORRECTABLE_FIELD_PATHS) == {
        "name", "summary", "description", "attributes.phone", "attributes.address",
        "attributes.opening_hours", "attributes.website", "attributes.price_range",
    }
    assert all(type(risk) is RiskClass for risk in CORRECTABLE_FIELD_PATHS.values())
    # Trust markers are never reporter-editable.
    assert "verifiedAt" not in CORRECTABLE_FIELD_PATHS
    assert "updatedAt" not in CORRECTABLE_FIELD_PATHS
    assert "verified" not in CORRECTABLE_FIELD_PATHS


def test_renaming_an_entry_is_the_highest_risk_correctable_field():
    assert CORRECTABLE_FIELD_PATHS["name"] is RiskClass.R2
    assert MAX_CORRECTION_ITEMS == 10
    assert MAX_CORRECTION_VALUE == 2000


@pytest.mark.parametrize(
    "text",
    [
        "Có người dọa giết chủ quán",
        "DOA GIET",
        "chủ quán bị đánh đập",
        "someone is dying here",
        "this is an EMERGENCY",
    ],
)
def test_urgent_language_is_detected_regardless_of_diacritics_or_case(text):
    assert _looks_urgent(text) is True


@pytest.mark.parametrize(
    "text",
    ["Số điện thoại sai", "giờ mở cửa đã đổi", "the address moved to another street"],
)
def test_ordinary_corrections_are_not_treated_as_urgent(text):
    assert _looks_urgent(text) is False


def test_safety_routing_never_presents_this_service_as_an_emergency_authority():
    urgent = _command(
        items=(
            CorrectionItemInput(
                entity_id="p-x",
                field_path="attributes.phone",
                reported_value="có người dọa giết",
                proposed_value="b",
                base_entity_revision=1,
            ),
        )
    )

    with pytest.raises(SafetyRoutingRequired) as excinfo:
        _service().create_correction(urgent, now=NOW)

    message = excinfo.value.safe_message
    assert "113" in message and "115" in message
    assert "vinhlong360" not in message.lower()
    assert "24/7" in message


def test_handoff_rejects_a_transcript_and_a_malformed_digest():
    with pytest.raises(ValueError, match="invalid_case_handoff"):
        ZaloHandoff(conversation_digest="d" * 64, user_confirmed=True, transcript={"turns": []})
    with pytest.raises(ValueError, match="invalid_case_handoff"):
        ZaloHandoff(conversation_digest="not-a-digest", user_confirmed=True)
    assert ZaloHandoff(conversation_digest="a" * 64, user_confirmed=True).transcript is None


def test_a_naive_timestamp_is_refused_before_any_store_call():
    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(_command(), now=datetime(2026, 8, 18, 9, 0))

    assert excinfo.value.problem.code == "invalid_command_clock"


def test_contact_details_never_raise_identity_assurance():
    service = _service()
    with_phone = _command(optional_phone="0901234567", notification_consent=True)

    assert service.identity_assurance_for(with_phone) == "none"
    assert service.reporter_privacy_for(with_phone) == "anonymous"

    signed_in = _command(reporter_privacy="attributed", authenticated_user_ref="user:7")
    assert service.identity_assurance_for(signed_in) == "session"
    assert service.reporter_privacy_for(signed_in) == "attributed"


# ── Review round 1: defects found by the independent cloud review ──

def test_vietnamese_values_survive_the_idempotency_digest():
    """bug_001: this is a Vietnamese-first product; diacritics are the norm."""
    from cases.security import CaseCrypto

    service = CaseService(
        store=None, crypto=CaseCrypto("0" * 43), policy=None, owner_ref="person:owner"
    )
    command = _command(
        items=(
            CorrectionItemInput(
                entity_id="p-x",
                field_path="attributes.address",
                reported_value="Số 1 đường Nguyễn Huệ",
                proposed_value="Ấp Phú Đông, xã Long Hồ",
                base_entity_revision=7,
            ),
        )
    )

    digest = service._request_digest(command)

    assert len(digest) == 64
    # A different Vietnamese value must still change the digest.
    other = _command(
        items=(
            CorrectionItemInput(
                entity_id="p-x",
                field_path="attributes.address",
                reported_value="Số 1 đường Nguyễn Huệ",
                proposed_value="Ấp Phú Tây, xã Long Hồ",
                base_entity_revision=7,
            ),
        )
    )
    assert service._request_digest(other) != digest


@pytest.mark.parametrize(
    "text",
    [
        "cửa hàng mở từ từ 8h đến 22h",
        "tăng giá từ tuần sau",
        "tủ sát tường bên trái",
        "cà phê pha từ từ",
        "mở cửa từ thứ hai",
    ],
)
def test_ordinary_vietnamese_wording_is_not_routed_to_the_emergency_lane(text):
    """bug_002: folding diacritics makes 'từ từ' collide with 'tự tử'."""
    assert _looks_urgent(text) is False


@pytest.mark.parametrize(
    "text",
    [
        "có người dọa giết chủ quán",
        "chủ quán bị đánh đập",
        "nó tự tử",
        "nghi bị hiếp dâm",
        "DOA GIET nhau",
        "this is an emergency",
        "someone is dying",
    ],
)
def test_real_urgent_language_still_routes(text):
    assert _looks_urgent(text) is True


def test_the_contact_value_is_bound_to_the_idempotency_digest():
    """bug_004: a corrected phone under the same key must not silently replay."""
    from cases.security import CaseCrypto

    service = CaseService(
        store=None, crypto=CaseCrypto("0" * 43), policy=None, owner_ref="person:owner"
    )
    first = service._request_digest(_command(optional_phone="0270 111 2222"))
    second = service._request_digest(_command(optional_phone="0270 111 2223"))
    absent = service._request_digest(_command())

    assert len({first, second, absent}) == 3


# ── Review round 2 ──

@pytest.mark.parametrize(
    "text",
    [
        "the students are studying at 8 to 10",
        "Khan Capital Tower, tang 3",
        "emergencyroom is not a word here",
    ],
)
def test_english_words_that_merely_contain_a_marker_are_not_urgent(text):
    """bug_001: the same substring defect as 'từ từ', on the English list."""
    assert _looks_urgent(text) is False


@pytest.mark.parametrize(
    "text",
    ["assault course training gym", "suicide squad film screening"],
)
def test_a_standalone_harm_word_still_routes_even_inside_a_venue_name(text):
    """Deliberate: word boundaries cannot disambiguate a real standalone word.

    Routing a cinema listing to the safety lane costs one rejected correction
    with copy pointing at the emergency services; not routing a real report
    costs far more, so the fail-safe direction wins here.
    """
    assert _looks_urgent(text) is True


@pytest.mark.parametrize(
    "text",
    ["a customer is dying", "this is an emergency", "reports of an assault here"],
)
def test_english_markers_still_route_as_whole_words(text):
    assert _looks_urgent(text) is True


def test_reporter_privacy_is_taken_from_the_command_not_re_derived():
    """bug_003: the field fed the idempotency digest but nothing else."""
    service = _service()

    assert service.reporter_privacy_for(_command(reporter_privacy="anonymous")) == "anonymous"
    assert (
        service.reporter_privacy_for(
            _command(reporter_privacy="attributed", authenticated_user_ref="user:7")
        )
        == "attributed"
    )


@pytest.mark.parametrize(
    ("privacy", "user_ref", "code"),
    [
        ("attributed", None, "attribution_requires_a_session"),
        ("public", None, "invalid_reporter_privacy"),
        ("", None, "invalid_reporter_privacy"),
    ],
)
def test_reporter_privacy_must_agree_with_the_session(privacy, user_ref, code):
    command = _command(reporter_privacy=privacy, authenticated_user_ref=user_ref)

    with pytest.raises(CorrectionRejected) as excinfo:
        _service().create_correction(command, now=NOW, session_user_ref=user_ref)

    assert excinfo.value.problem.code == code


def test_signing_in_does_not_force_attribution():
    """A signed-in reporter may still file anonymously."""
    command = _command(reporter_privacy="anonymous", authenticated_user_ref=None)

    assert _service().reporter_privacy_for(command) == "anonymous"
    assert _service().party_authority_draft_for(command, case_id="c", now=NOW) is None
