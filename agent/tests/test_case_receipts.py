from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest

from cases.security import (
    CaseCrypto,
    CaseSecurityError,
    decrypt_replay,
    digest_capability,
    encrypt_replay,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
KEY = base64.urlsafe_b64encode(b"k" * 32).decode("ascii")


def _bytes(count: int) -> bytes:
    return bytes(range(count))


def test_reference_capability_digest_and_replay_contract():
    crypto = CaseCrypto(KEY, random_bytes=_bytes)

    reference = crypto.issue_public_reference()
    capability = crypto.issue_capability()
    replay = crypto.encrypt_replay({"case_id": "case-1"}, now=NOW)

    assert reference.startswith("VL-COR-")
    assert crypto.validate_public_reference(reference)
    assert len(reference.removeprefix("VL-COR-")) == 13
    assert len(capability) == 43
    assert crypto.digest_capability(capability).isalnum()
    assert len(crypto.digest_capability(capability)) == 64
    assert crypto.decrypt_replay(replay, now=NOW + timedelta(hours=23))["case_id"] == "case-1"
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        crypto.decrypt_replay(replay, now=NOW + timedelta(hours=25))
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        crypto.decrypt_replay(replay[:-1] + "A", now=NOW)


def test_weak_case_key_fails_closed():
    with pytest.raises(CaseSecurityError, match="case_encryption_key_required"):
        CaseCrypto("short")


def test_stateless_helpers_accept_explicit_key_material():
    replay = encrypt_replay({"case_id": "case-1"}, master_key=KEY, now=NOW)

    assert digest_capability("secret", master_key=KEY) == CaseCrypto(KEY).digest_capability("secret")
    assert decrypt_replay(replay, master_key=KEY, now=NOW)["case_id"] == "case-1"


def test_replay_rejects_future_issue_time_and_bad_boundary_inputs():
    future = encrypt_replay({"case_id": "case-1"}, master_key=KEY, now=NOW + timedelta(minutes=6))
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        decrypt_replay(future, master_key=KEY, now=NOW)
    crypto = CaseCrypto(KEY)
    for value in (None, b"secret", "\ud800"):
        with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
            crypto.digest_capability(value)
