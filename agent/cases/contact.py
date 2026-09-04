"""Optional phone verification for a correction case.

A verified phone is a reply address and nothing else. It never becomes account
authority, never grants listing authority, and never widens what the reporter
can read: the only thing it unlocks is being notified about their own case.

Authority comes from the case access session the caller already holds. The
request body never names a case, so a verified phone cannot be attached to
somebody else's case.
"""
from __future__ import annotations

import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from .outbox import delivery_key
from .rate_limit import check_case_rate_limit, rate_subject_digest
from .security import CaseSecurityError

CHALLENGE_TTL_SECONDS = 600
VERIFY_ATTEMPT_LIMIT = 5
VERIFY_ATTEMPT_WINDOW = 900
_PUBLIC_ERROR = "invalid_case_credential"
_DIGITS = re.compile(r"[^0-9]")
_MESSAGE = "vinhlong360: ma xac nhan {code}. Ma het han sau 10 phut. Khong chia se ma nay."

_DATABASE = None
_CRYPTO = None
_PROVIDER = None
_CODE_SOURCE = None


class ContactDeliveryUnavailable(RuntimeError):
    """The OTP provider did not accept the message; never mint a success claim."""

    def __init__(self, code: str = "contact_verification_unavailable") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ContactChallenge:
    challenge_id: str
    case_id: str
    expires_at: datetime
    delivery_key: str


@dataclass(frozen=True)
class VerifiedContact:
    case_id: str
    contact_digest: str
    verified_at: datetime


def configure_case_contact(*, database=None, crypto=None, provider=None, code_source=None) -> None:
    global _DATABASE, _CRYPTO, _PROVIDER, _CODE_SOURCE
    _DATABASE = database
    _CRYPTO = crypto
    _PROVIDER = provider
    _CODE_SOURCE = code_source


def _database():
    if _DATABASE is not None:
        return _DATABASE
    from database import db

    return db


def _crypto():
    if _CRYPTO is None:
        raise RuntimeError("case_contact_not_configured")
    return _CRYPTO


def normalize_phone(raw: object) -> str:
    """One national form, so the same number always digests the same way."""
    if type(raw) is not str:
        raise ValueError("invalid_contact_phone")
    digits = _DIGITS.sub("", raw)
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if not digits.startswith("0") or not 9 <= len(digits) <= 11:
        raise ValueError("invalid_contact_phone")
    return digits


def contact_digest(phone: str, *, crypto) -> str:
    """Keyed, so a stolen table cannot be reversed with a rainbow table."""
    return crypto.digest_capability(f"case-contact:{normalize_phone(phone)}")


def _open_withdrawal_receipt(receipt: str, digest: str, crypto, *, now: datetime) -> str:
    try:
        payload = crypto.open_contact_receipt(receipt, now=now)
        challenge_id = str(uuid.UUID(str(payload["challenge_id"])))
        if not hmac.compare_digest(str(payload["contact_digest"]), digest):
            raise ValueError
    except (CaseSecurityError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise CaseSecurityError(_PUBLIC_ERROR) from exc
    return challenge_id


def _enforce_contact_rate_limit(
    bucket: str,
    subject: str,
    *,
    database,
    now: datetime,
) -> None:
    if not check_case_rate_limit(
        bucket,
        subject,
        limit=VERIFY_ATTEMPT_LIMIT,
        window=VERIFY_ATTEMPT_WINDOW,
        now=now,
        database=database,
    ):
        raise CaseSecurityError(_PUBLIC_ERROR)


def _challenge_digest(code: str, *, crypto, case_id: str) -> str:
    return crypto.digest_capability(f"case-otp:{case_id}:{code}")


def _new_code() -> str:
    if _CODE_SOURCE is not None:
        return _CODE_SOURCE()
    return f"{secrets.randbelow(1_000_000):06d}"


def request_contact_verification(access, phone: str, consent: bool, *, now: datetime) -> ContactChallenge:
    """Replace any pending challenge for this case and send a fresh code."""
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_contact_clock")
    database = _database()
    if not database._use_pg:
        raise RuntimeError("case_postgresql_required")
    crypto = _crypto()
    case_id = access.case_id
    number = normalize_phone(phone)

    # Ngân sách theo SỐ ĐÍCH, kiểm trước ngân sách theo hồ sơ. Hai cái kia đều
    # khoá theo case_id, mà mở một hồ sơ mới thì gần như miễn phí — nên chúng
    # không hề chặn việc dựng N hồ sơ rồi bắn 5N tin nhắn vào CÙNG MỘT số. Tiền
    # tin nhắn và brandname vinhlong360 đều là của dự án (CLAUDE.md B8), còn
    # người hứng là một người thứ ba không liên quan.
    #
    # Đánh đổi có ý thức: kẻ tấn công đốt được ngân sách của một số, nên chủ số
    # đó phải chờ hết cửa sổ mới xác thực được. Chờ 15 phút là cái giá nhỏ hơn
    # nhiều so với bị dội tin không giới hạn.
    subject_key = crypto.digest_capability("case-contact-subject")
    _enforce_contact_rate_limit(
        "contact_otp_dest",
        rate_subject_digest(f"dest:{number}", master_key=subject_key),
        database=database,
        now=now,
    )
    _enforce_contact_rate_limit(
        "contact_otp",
        rate_subject_digest(f"request:{case_id}", master_key=subject_key),
        database=database,
        now=now,
    )

    code = _new_code()
    expires_at = now + timedelta(seconds=CHALLENGE_TTL_SECONDS)
    with database._conn(commit_on_success=False) as conn:
        # Withdrawing consent simply leaves no live challenge and no verified
        # contact, so the dispatcher finds nothing to notify.
        database._execute(conn, "DELETE FROM case_contact_challenges WHERE case_id = %s", (case_id,))
        if not consent:
            conn.commit()
            return ContactChallenge(
                challenge_id="", case_id=case_id, expires_at=now, delivery_key=""
            )
        row = database._fetchone(
            conn,
            """
            INSERT INTO case_contact_challenges (
                case_id, contact_digest, challenge_digest, channel, expires_at, created_at
            ) VALUES (%s, %s, %s, 'phone', %s, %s)
            RETURNING challenge_id
            """,
            (
                case_id,
                contact_digest(number, crypto=crypto),
                _challenge_digest(code, crypto=crypto, case_id=case_id),
                expires_at,
                now,
            ),
        )
        challenge_id = str(database._row_to_dict(row)["challenge_id"])
        # The number itself lives encrypted on the case interaction, never here.
        database._execute(
            conn,
            """
            INSERT INTO case_interactions (
                case_id, channel, actor_ref, direction, consent_ref,
                identity_assurance, payload_enc, created_at
            ) VALUES (%s, 'phone', 'anonymous', 'outbound', 'notify:granted:v1', 'none', %s, %s)
            """,
            (case_id, crypto.encrypt_private_payload({"contact": number}), now),
        )
        conn.commit()

    key = delivery_key(challenge_id)
    result = _PROVIDER.send(number, _MESSAGE.format(code=code), delivery_key=key)
    if not bool(getattr(result, "delivered", False)):
        with database._conn(commit_on_success=False) as conn:
            database._execute(conn, "DELETE FROM case_contact_challenges WHERE challenge_id = %s", (challenge_id,))
            conn.commit()
        raise ContactDeliveryUnavailable(str(getattr(result, "error_code", None) or "contact_verification_unavailable"))
    return ContactChallenge(
        challenge_id=challenge_id, case_id=case_id, expires_at=expires_at, delivery_key=key
    )


def request_pre_case_contact_verification(
    phone: str, consent: bool, *, now: datetime, requester_subject: str | None = None,
    receipt: str | None = None,
) -> ContactChallenge:
    """Send a durable, opaque proof receipt before a case access session exists."""
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_contact_clock")
    database = _database()
    if not database._use_pg:
        raise RuntimeError("case_postgresql_required")
    crypto = _crypto()
    number = normalize_phone(phone)
    digest = contact_digest(number, crypto=crypto)
    if not consent:
        if not receipt:
            raise CaseSecurityError(_PUBLIC_ERROR)
        challenge_id = _open_withdrawal_receipt(receipt, digest, crypto, now=now)
        withdraw_subject = rate_subject_digest(
            f"withdraw:{challenge_id}",
            master_key=crypto.digest_capability("case-contact-subject"),
        )
        _enforce_contact_rate_limit(
            "contact_otp_withdraw", withdraw_subject, database=database, now=now,
        )
        with database._conn(commit_on_success=False) as conn:
            database._execute(
                conn,
                "DELETE FROM case_pre_contact_challenges "
                "WHERE challenge_id = %s AND contact_digest = %s AND used_at IS NULL",
                (challenge_id, digest),
            )
            conn.commit()
        return ContactChallenge(challenge_id="", case_id="", expires_at=now, delivery_key="")
    destination = rate_subject_digest(
        f"dest:{number}",
        master_key=crypto.digest_capability("case-contact-subject"),
    )
    _enforce_contact_rate_limit(
        "contact_otp", destination, database=database, now=now,
    )
    if requester_subject:
        requester = rate_subject_digest(
            f"requester:{requester_subject}",
            master_key=crypto.digest_capability("case-contact-subject"),
        )
        _enforce_contact_rate_limit(
            "contact_otp_requester", requester, database=database, now=now,
        )
    code = _new_code()
    expires_at = now + timedelta(seconds=CHALLENGE_TTL_SECONDS)
    challenge_digest = crypto.digest_capability(f"case-pre-otp:{digest}:{code}")
    with database._conn(commit_on_success=False) as conn:
        # One current receipt per destination. The row is also the durable,
        # single-use authority consumed atomically when a case is created.
        row = database._fetchone(
            conn,
            """
            INSERT INTO case_pre_contact_challenges (
                challenge_id, contact_digest, challenge_digest, expires_at, created_at
            ) VALUES (uuid_generate_v4(), %s, %s, %s, %s)
            ON CONFLICT (contact_digest) WHERE used_at IS NULL DO UPDATE SET
                challenge_id = EXCLUDED.challenge_id,
                challenge_digest = EXCLUDED.challenge_digest,
                expires_at = EXCLUDED.expires_at,
                created_at = EXCLUDED.created_at,
                verified_at = NULL,
                used_at = NULL
            RETURNING challenge_id
            """,
            (digest, challenge_digest, expires_at, now),
        )
        challenge_id = str(database._row_to_dict(row)["challenge_id"])
        receipt = crypto.issue_contact_receipt(
            contact_digest=digest,
            challenge_digest=challenge_digest,
            challenge_id=challenge_id,
            expires_at=expires_at,
            now=now,
        )
        conn.commit()
    key = delivery_key(challenge_id)
    result = _PROVIDER.send(number, _MESSAGE.format(code=code), delivery_key=key)
    if not bool(getattr(result, "delivered", False)):
        with database._conn(commit_on_success=False) as conn:
            database._execute(conn, "DELETE FROM case_pre_contact_challenges WHERE challenge_id = %s", (challenge_id,))
            conn.commit()
        raise ContactDeliveryUnavailable(str(getattr(result, "error_code", None) or "contact_verification_unavailable"))
    return ContactChallenge(
        challenge_id=receipt, case_id="", expires_at=expires_at, delivery_key=key
    )


def verify_pre_case_contact(receipt: str, code: str, *, now: datetime) -> tuple[VerifiedContact, str]:
    """Verify a restart-safe pre-case receipt without creating a case."""
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_contact_clock")
    database = _database()
    if not database._use_pg:
        raise RuntimeError("case_postgresql_required")
    crypto = _crypto()
    payload = crypto.open_contact_receipt(receipt, now=now)
    try:
        challenge_id = str(uuid.UUID(str(payload["challenge_id"])))
    except (ValueError, TypeError, AttributeError) as exc:
        raise CaseSecurityError(_PUBLIC_ERROR) from exc
    verify_subject = rate_subject_digest(
        f"pre-verify:{challenge_id}",
        master_key=crypto.digest_capability("case-contact-subject"),
    )
    if not check_case_rate_limit(
        "contact_otp_verify", verify_subject, limit=VERIFY_ATTEMPT_LIMIT,
        window=VERIFY_ATTEMPT_WINDOW, now=now, database=database,
    ):
        raise CaseSecurityError(_PUBLIC_ERROR)
    with database._conn(commit_on_success=False) as conn:
        row = database._fetchone(
            conn,
            """
            SELECT contact_digest, challenge_digest, expires_at
            FROM case_pre_contact_challenges
            WHERE challenge_id = %s AND verified_at IS NULL AND used_at IS NULL AND expires_at > %s
            FOR UPDATE
            """,
            (challenge_id, now),
        )
        if row is None:
            raise CaseSecurityError(_PUBLIC_ERROR)
        item = database._row_to_dict(row)
        if not hmac.compare_digest(str(payload.get("contact_digest", "")), str(item["contact_digest"])):
            raise CaseSecurityError(_PUBLIC_ERROR)
        if not hmac.compare_digest(str(payload.get("challenge_digest", "")), str(item["challenge_digest"])):
            raise CaseSecurityError(_PUBLIC_ERROR)
        expected = crypto.digest_capability(
            f"case-pre-otp:{item['contact_digest']}:{code}"
        ) if type(code) is str else ""
        if not hmac.compare_digest(str(item["challenge_digest"]), expected):
            raise CaseSecurityError(_PUBLIC_ERROR)
        database._execute(
            conn,
            "UPDATE case_pre_contact_challenges SET verified_at = %s WHERE challenge_id = %s",
            (now, challenge_id),
        )
        conn.commit()
    return VerifiedContact(case_id="", contact_digest=str(item["contact_digest"]), verified_at=now), crypto.issue_contact_receipt(
        contact_digest=str(item["contact_digest"]),
        challenge_digest=str(item["challenge_digest"]),
        challenge_id=challenge_id,
        expires_at=item["expires_at"],
        now=now,
        verified=True,
    )


def verify_contact(access, code: str, *, now: datetime, receipt: str | None = None) -> VerifiedContact:
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_contact_clock")
    database = _database()
    if not database._use_pg:
        raise RuntimeError("case_postgresql_required")
    crypto = _crypto()
    case_id = access.case_id

    if not check_case_rate_limit(
        "contact_otp",
        rate_subject_digest(f"verify:{case_id}", master_key=crypto.digest_capability("case-contact-subject")),
        limit=VERIFY_ATTEMPT_LIMIT, window=VERIFY_ATTEMPT_WINDOW, now=now, database=database,
    ):
        raise CaseSecurityError(_PUBLIC_ERROR)

    expected = _challenge_digest(code, crypto=crypto, case_id=case_id) if type(code) is str else ""
    with database._conn(commit_on_success=False) as conn:
        row = database._fetchone(
            conn,
            """
            SELECT challenge_id, contact_digest, challenge_digest
            FROM case_contact_challenges
            WHERE case_id = %s AND verified_at IS NULL AND expires_at > %s
              AND (%s IS NULL OR challenge_id = %s)
            ORDER BY created_at DESC LIMIT 1
            FOR UPDATE
            """,
            (case_id, now, receipt, receipt),
        )
        if row is None:
            raise CaseSecurityError(_PUBLIC_ERROR)
        item = database._row_to_dict(row)
        if not expected or not hmac.compare_digest(str(item["challenge_digest"]), expected):
            raise CaseSecurityError(_PUBLIC_ERROR)
        database._execute(
            conn,
            "UPDATE case_contact_challenges SET verified_at = %s WHERE challenge_id = %s",
            (now, item["challenge_id"]),
        )
        conn.commit()
    return VerifiedContact(
        case_id=case_id, contact_digest=str(item["contact_digest"]), verified_at=now
    )


def verified_contact_for(case_id: str, *, now: datetime) -> str | None:
    """Delivery-time authority: the digest of a still-verified contact, or None."""
    database = _database()
    with database._conn(commit_on_success=False) as conn:
        row = database._fetchone(
            conn,
            """
            SELECT contact_digest FROM case_contact_challenges
            WHERE case_id = %s AND verified_at IS NOT NULL
            ORDER BY verified_at DESC LIMIT 1
            """,
            (case_id,),
        )
    return None if row is None else str(database._row_to_dict(row)["contact_digest"])


def deliverable_contact_for(case_id: str, *, now: datetime, crypto=None) -> str | None:
    """Delivery-time authority: the phone to notify, or None.

    Returns a number only when a verified challenge still exists AND the stored
    ciphertext still digests to that challenge's contact. Consent withdrawn,
    challenge deleted, or the number changed since verification all read as None,
    so the dispatcher suppresses instead of messaging the wrong person.
    """
    database = _database()
    crypto = crypto or _crypto()
    expected = verified_contact_for(case_id, now=now)
    if expected is None:
        return None
    with database._conn(commit_on_success=False) as conn:
        row = database._fetchone(
            conn,
            """
            SELECT payload_enc FROM case_interactions
            WHERE case_id = %s AND payload_enc IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (case_id,),
        )
    if row is None:
        return None
    try:
        payload = crypto.decrypt_private_payload(
            str(database._row_to_dict(row)["payload_enc"])
        )
    except CaseSecurityError:
        return None
    number = payload.get("contact")
    if type(number) is not str or not number:
        return None
    if not hmac.compare_digest(contact_digest(number, crypto=crypto), expected):
        return None
    return number
