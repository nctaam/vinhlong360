"""Optional phone verification: notification authority only, nothing more."""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

import database  # noqa: E402
from cases.contact import (  # noqa: E402
    VERIFY_ATTEMPT_LIMIT,
    ContactChallenge,
    VerifiedContact,
    configure_case_contact,
    normalize_phone,
    request_contact_verification,
    verified_contact_for,
    verify_contact,
)
from cases.security import CaseCrypto, CaseSecurityError  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
MASTER_KEY = "0" * 43


def _validated_url() -> str | None:
    raw = os.environ.get("VL360_TEST_DATABASE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {
        "localhost", "127.0.0.1", "::1",
    }:
        return None
    if {"host", "hostaddr"} & parse_qs(parsed.query, keep_blank_values=True).keys():
        return None
    return raw


TEST_DATABASE_URL = _validated_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)


class _FakeProvider:
    def __init__(self) -> None:
        self.sent = []

    def send(self, phone, message, *, delivery_key):
        from cases.outbox import DeliveryResult

        self.sent.append((phone, message, delivery_key))
        return DeliveryResult(True, None, False)


class _Access:
    """Only the fields the contact flow is allowed to rely on."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.receipt_id = "r-1"
        self.receipt_revision = 1
        self.session_digest = "s" * 64
        self.current_user_id = None


@pytest.fixture
def pg_database():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(conn, "DELETE FROM case_contact_challenges", ())
        adapter._execute(conn, "DELETE FROM shared_rate_limits WHERE key LIKE %s", ("case:%",))
        conn.commit()
    return adapter


@pytest.fixture
def provider(pg_database):
    fake = _FakeProvider()
    configure_case_contact(
        database=pg_database, crypto=CaseCrypto(MASTER_KEY), provider=fake,
        code_source=lambda: "123456",
    )
    yield fake
    configure_case_contact(database=None, crypto=None, provider=None, code_source=None)


def _case(adapter) -> str:
    with adapter._conn(commit_on_success=False) as conn:
        row = adapter._fetchone(
            conn,
            """
            INSERT INTO cases (service_kind, category, phase, activity, disposition_family,
                               reporter_privacy, owner_ref, current_revision, promise_policy_ref)
            VALUES ('correction','correction','intake','active','undetermined','anonymous',
                    'person:owner',1,'correction-pilot-v1')
            RETURNING case_id
            """,
            (),
        )
        case_id = str(row["case_id"])
        conn.commit()
    return case_id


# ── Normalisation, no database ──

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0901 234 567", "0901234567"),
        ("  0901234567  ", "0901234567"),
        ("+84901234567", "0901234567"),
        ("84901234567", "0901234567"),
    ],
)
def test_a_phone_number_normalises_to_one_national_form(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "abc", "0901", "0" * 20, None])
def test_an_unusable_phone_number_is_refused(raw):
    with pytest.raises(ValueError, match="invalid_contact_phone"):
        normalize_phone(raw)


# ── Verification ──

@pg_only
def test_requesting_verification_stores_only_digests_and_sends_a_code(pg_database, provider):
    case_id = _case(pg_database)

    challenge = request_contact_verification(
        _Access(case_id), "0901 234 567", consent=True, now=NOW
    )

    assert type(challenge) is ContactChallenge
    assert challenge.case_id == case_id
    assert challenge.expires_at > NOW
    with pg_database._conn(commit_on_success=False) as conn:
        row = dict(pg_database._fetchone(
            conn,
            "SELECT contact_digest, challenge_digest, channel, verified_at"
            " FROM case_contact_challenges WHERE case_id=%s",
            (case_id,),
        ))
    assert row["channel"] == "phone"
    assert row["verified_at"] is None
    # Neither the number nor the code is stored in the clear.
    assert "0901234567" not in row["contact_digest"]
    assert "123456" not in row["challenge_digest"]
    assert row["challenge_digest"] != "123456"
    assert len(provider.sent) == 1
    assert provider.sent[0][0] == "0901234567"
    assert "123456" in provider.sent[0][1]


@pg_only
def test_the_right_code_verifies_and_grants_notification_authority_only(pg_database, provider):
    case_id = _case(pg_database)
    request_contact_verification(_Access(case_id), "0901234567", consent=True, now=NOW)

    verified = verify_contact(_Access(case_id), "123456", now=NOW + timedelta(minutes=1))

    assert type(verified) is VerifiedContact
    assert verified.case_id == case_id
    with pg_database._conn(commit_on_success=False) as conn:
        authorities = pg_database._fetchone(
            conn, "SELECT count(*) AS n FROM case_party_authorities WHERE case_id=%s", (case_id,)
        )["n"]
        verified_at = pg_database._fetchone(
            conn, "SELECT verified_at FROM case_contact_challenges WHERE case_id=%s", (case_id,)
        )["verified_at"]
    # A verified phone is a reply address, never account or listing authority.
    assert authorities == 0
    assert verified_at is not None
    assert verified_contact_for(case_id, now=NOW + timedelta(minutes=2)) is not None


@pg_only
def test_a_wrong_code_fails_with_the_same_public_credential_error(pg_database, provider):
    case_id = _case(pg_database)
    request_contact_verification(_Access(case_id), "0901234567", consent=True, now=NOW)

    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        verify_contact(_Access(case_id), "999999", now=NOW + timedelta(minutes=1))

    # An unknown case fails identically, so nothing can be probed.
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        verify_contact(_Access(_case(pg_database)), "123456", now=NOW)


@pg_only
def test_an_expired_code_no_longer_verifies(pg_database, provider):
    case_id = _case(pg_database)
    challenge = request_contact_verification(
        _Access(case_id), "0901234567", consent=True, now=NOW
    )

    with pytest.raises(CaseSecurityError):
        verify_contact(_Access(case_id), "123456", now=challenge.expires_at + timedelta(seconds=1))


@pg_only
def test_attempts_are_bounded_by_the_shared_contact_bucket(pg_database, provider):
    case_id = _case(pg_database)
    request_contact_verification(_Access(case_id), "0901234567", consent=True, now=NOW)

    for _ in range(6):
        try:
            verify_contact(_Access(case_id), "999999", now=NOW + timedelta(minutes=1))
        except Exception as exc:  # noqa: BLE001
            last = exc

    assert "rate" in str(last).lower() or "credential" in str(last).lower()
    with pg_database._conn(commit_on_success=False) as conn:
        buckets = pg_database._fetchone(
            conn,
            "SELECT count(*) AS n FROM shared_rate_limits WHERE key LIKE %s",
            # Mẫu cũ là 'case:contact_otp:%' nên nó KHÔNG nhìn thấy bucket
            # 'case:contact_otp_dest:…' — một dấu hai chấm đủ để đếm hụt một
            # ngân sách và làm test tưởng mọi thứ vẫn như cũ.
            ("case:contact_otp%",),
        )["n"]
    # Ba ngân sách, mỗi cái chặn một kiểu tấn công khác nhau; gộp lại thì kiểu
    # này tiêu mất phần của kiểu kia:
    #   request:{case_id}  — dội mã từ MỘT hồ sơ
    #   verify:{case_id}   — đoán mã
    #   dest:{số}          — dội mã vào MỘT SỐ từ nhiều hồ sơ khác nhau
    assert buckets == 3


@pg_only
def test_many_cases_cannot_gang_up_on_one_phone_number(pg_database, provider):
    """Mở hồ sơ mới gần như miễn phí, nên ngân sách theo hồ sơ không chặn được gì.

    Kịch bản thật: dựng N hồ sơ, mỗi hồ sơ xin 5 mã cho CÙNG một số → 5N tin nhắn
    vào một người thứ ba không liên quan, bằng tiền và brandname của dự án. Ngân
    sách theo SỐ ĐÍCH là thứ duy nhất chặn được, vì nó không phụ thuộc case_id.
    """
    victim = "0901234567"
    sent_before = len(provider.sent)

    delivered = 0
    for _ in range(4):                      # bốn hồ sơ KHÁC NHAU
        case_id = _case(pg_database)
        for _ in range(3):                  # dưới hạn mức theo-hồ-sơ (5)
            try:
                request_contact_verification(
                    _Access(case_id), victim, consent=True, now=NOW
                )
                delivered += 1
            except CaseSecurityError:
                pass

    assert delivered <= VERIFY_ATTEMPT_LIMIT, (
        f"{delivered} tin nhắn tới một số trong một cửa sổ — ngân sách theo số "
        "đích không chặn, nên nhiều hồ sơ vẫn dội được vào cùng một người"
    )
    assert len(provider.sent) - sent_before == delivered


@pg_only
def test_withdrawing_consent_leaves_no_verified_contact_to_notify(pg_database, provider):
    case_id = _case(pg_database)
    request_contact_verification(_Access(case_id), "0901234567", consent=True, now=NOW)
    verify_contact(_Access(case_id), "123456", now=NOW + timedelta(minutes=1))

    request_contact_verification(_Access(case_id), "0901234567", consent=False, now=NOW)

    assert verified_contact_for(case_id, now=NOW + timedelta(minutes=2)) is None


def test_the_contact_digest_is_keyed_and_not_a_bare_hash():
    from cases.contact import contact_digest

    digest = contact_digest("0901234567", crypto=CaseCrypto(MASTER_KEY))

    assert digest != hashlib.sha256(b"0901234567").hexdigest()
    assert len(digest) == 64


def test_the_challenge_key_needs_no_attempt_number():
    from cases.outbox import delivery_key

    # It identifies one logical send, not one attempt at it. The parameter that
    # used to be here was always passed 1 and never reached the hash.
    assert delivery_key("challenge-1") == delivery_key("challenge-1")
    assert delivery_key("challenge-1") != delivery_key("challenge-2")


def test_a_takedown_clears_the_catalogue_the_chat_speaks_from():
    import ast
    from pathlib import Path

    # `_sync_kb` sang agent/admin_common.py (2026-08-28, buoc 2a) — soi nha moi.
    source = (Path(__file__).resolve().parents[1] / "admin_common.py").read_text("utf-8")
    tree = ast.parse(source)
    sync = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "_sync_kb")
    called = {
        node.func.attr for node in ast.walk(sync)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    # kb_context.invalidate has always existed and its docstring has always said
    # "call after KB reload". _sync_kb reloads knowledge at all 12 admin write
    # sites and never called it, so a deleted entity stayed in the chat's
    # catalogue — named to the model as real — for the life of the process.
    assert "reload" in called
    assert "invalidate" in called
