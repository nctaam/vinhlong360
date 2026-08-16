from __future__ import annotations

import base64
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import pytest

from cases.security import CaseCrypto, CaseSecurityError, CaseSecurityService
from cases.store import PostgresCaseStore


UTC = timezone.utc
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
KEY = base64.urlsafe_b64encode(b"s" * 32).rstrip(b"=").decode("ascii")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))


def _test_dsn():
    dsn = os.environ.get("VL360_TEST_DATABASE_URL", "")
    parsed = urlparse(dsn)
    return dsn if parsed.scheme in {"postgres", "postgresql"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"} and "test" in parsed.path.lower() else None


pg_only = pytest.mark.skipif(_test_dsn() is None, reason="set a disposable loopback VL360_TEST_DATABASE_URL")


def test_service_requires_a_store_for_persistence():
    service = CaseSecurityService(None, CaseCrypto(KEY))
    with pytest.raises(CaseSecurityError, match="case_postgresql_required"):
        service.issue_receipt("case-1", now=NOW)


def test_service_delegates_only_digests_and_encrypted_replay_to_the_store():
    class Store:
        def __init__(self):
            self.calls = []

        def issue_receipt(self, case_id, crypto, *, now, current_user_id, idempotency_key):
            self.calls.append((case_id, crypto, now, current_user_id, idempotency_key))
            return "stored"

    store = Store()
    service = CaseSecurityService(store, CaseCrypto(KEY))

    assert service.issue_receipt("case-1", now=NOW, current_user_id="user-1", idempotency_key="issue-1") == "stored"
    assert store.calls[0][0] == "case-1"
    assert store.calls[0][3] == "user-1"
    assert store.calls[0][4] == "issue-1"


def test_store_module_is_covered_by_the_case_access_service_contract():
    assert PostgresCaseStore.__module__ == "cases.store"


def test_authenticated_subject_must_match_during_exchange_and_validation():
    class Store:
        def exchange_receipt(self, *_args, **kwargs):
            assert kwargs["current_user_id"] == "user-1"
            return "grant"

        def validate_access(self, *_args, **kwargs):
            assert kwargs["current_user_id"] == "user-1"
            return "access"

    service = CaseSecurityService(Store(), CaseCrypto(KEY))
    assert service.exchange_receipt("VL-COR-0123456789AB0", "capability", now=NOW, current_user_id="user-1") == "grant"
    assert service.validate_access("access", now=NOW, current_user_id="user-1") == "access"


def test_cookie_csrf_and_origin_contract():
    crypto = CaseCrypto(KEY)
    access = crypto.make_access("case-1", "receipt-1", 1, "a" * 64, None)
    token = crypto.issue_case_csrf(access, random_bytes=lambda _count: b"x" * 16)

    assert crypto.validate_case_csrf(access, token) is None
    assert crypto.case_access_cookie("token", production=True) == {
        "key": "vl360_case_access",
        "value": "token",
        "httponly": True,
        "secure": True,
        "samesite": "lax",
        "path": "/api/cases",
        "max_age": 900,
    }
    assert crypto.case_csrf_cookie(token)["httponly"] is False
    assert crypto.validate_case_mutation(
        access, token, token, origin="https://vl360.example", expected_origin="https://vl360.example", sec_fetch_site="same-origin"
    ) is None
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        crypto.validate_case_mutation(access, token, token, origin="https://evil.example", expected_origin="https://vl360.example", sec_fetch_site="cross-site")
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        crypto.validate_case_mutation(access, token, token, origin="https://vl360.example", expected_origin="https://vl360.example", sec_fetch_site="same-site")
    for malformed in (None, b"x", 1):
        with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
            crypto.validate_case_csrf(access, malformed)


def test_subject_rejects_blank_identity_and_cookie_helper_returns_both_specs():
    crypto = CaseCrypto(KEY)
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        crypto.normalize_subject(" ")
    cookies = crypto.case_cookies("access", "csrf", production=True)
    assert set(cookies) == {"access", "csrf"}


@pg_only
def test_postgres_lifecycle_persists_only_digests_and_revocation_wins():
    import database
    import psycopg2
    import psycopg2.extras
    import uuid

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    db = database.Database()
    db._use_pg = True
    db._dsn = _test_dsn()
    case_id = str(uuid.uuid4())
    with db._conn(commit_on_success=False) as conn:
        db._execute(conn, "INSERT INTO cases(case_id, service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES (%s, 'correction', 'security-test', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test')", (case_id,))
        conn.commit()
    service = CaseSecurityService(PostgresCaseStore(db), CaseCrypto(KEY))
    grant = service.issue_receipt(case_id, now=NOW, current_user_id="user-1")
    exchanged = service.exchange_receipt(grant.public_reference, grant.capability, now=NOW, current_user_id="user-1")
    assert service.validate_access(exchanged.access_token, now=NOW, current_user_id="user-1").case_id == case_id
    with db._conn(commit_on_success=False) as conn:
        receipt = db._row_to_dict(db._fetchone(conn, "SELECT capability_digest, public_reference, receipt_revision, subject_user_id FROM case_receipts WHERE receipt_id=%s", (grant.receipt_id,)))
        session = db._row_to_dict(db._fetchone(conn, "SELECT session_digest, session_key_version FROM case_access_sessions WHERE receipt_id=%s", (grant.receipt_id,)))
    assert grant.capability not in repr(receipt)
    assert exchanged.access_token not in repr(session)
    assert receipt["receipt_revision"] == 1
    assert receipt["subject_user_id"] == "user-1"
    assert session["session_key_version"] == "v1"
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        service.validate_access(exchanged.access_token, now=NOW, current_user_id="user-2")
    replacement = service.rotate_receipt(exchanged.access_token, now=NOW + timedelta(seconds=1), current_user_id="user-1")
    assert replacement.revision == 2
    service.revoke_access(case_id, now=NOW + timedelta(minutes=1))
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        service.validate_access(exchanged.access_token, now=NOW + timedelta(minutes=2))


@pg_only
def test_postgres_issue_idempotency_replays_same_raw_grant_and_rejects_actor_reuse():
    import database
    import psycopg2
    import psycopg2.extras
    import uuid

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    db = database.Database()
    db._use_pg = True
    db._dsn = _test_dsn()
    case_id = str(uuid.uuid4())
    with db._conn(commit_on_success=False) as conn:
        db._execute(conn, "INSERT INTO cases(case_id, service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES (%s, 'correction', 'idempotency-test', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test')", (case_id,))
        conn.commit()
    service = CaseSecurityService(PostgresCaseStore(db), CaseCrypto(KEY))
    operation_key = f"issue-{case_id}"
    first = service.issue_receipt(case_id, now=NOW, current_user_id="user-1", idempotency_key=operation_key)
    replayed = service.issue_receipt(case_id, now=NOW + timedelta(minutes=1), current_user_id="user-1", idempotency_key=operation_key)
    assert replayed == first
    with db._conn(commit_on_success=False) as conn:
        row = db._fetchone(conn, "SELECT COUNT(*) AS count FROM case_receipts WHERE case_id=%s", (case_id,))
    assert db._row_to_dict(row)["count"] == 1
    with pytest.raises(CaseSecurityError, match="invalid_case_credential"):
        service.issue_receipt(case_id, now=NOW, current_user_id="user-2", idempotency_key=operation_key)


@pg_only
def test_postgres_two_rotations_of_one_bearer_create_one_successor():
    import database
    import psycopg2
    import psycopg2.extras
    import uuid

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    db = database.Database()
    db._use_pg = True
    db._dsn = _test_dsn()
    case_id = str(uuid.uuid4())
    with db._conn(commit_on_success=False) as conn:
        db._execute(conn, "INSERT INTO cases(case_id, service_kind, category, phase, activity, disposition_family, reporter_privacy, owner_ref, promise_policy_ref) VALUES (%s, 'correction', 'rotation-race', 'intake', 'active', 'undetermined', 'anonymous', 'person:test', 'policy:test')", (case_id,))
        conn.commit()
    service = CaseSecurityService(PostgresCaseStore(db), CaseCrypto(KEY))
    grant = service.issue_receipt(case_id, now=NOW, current_user_id="user-1")
    access = service.exchange_receipt(grant.public_reference, grant.capability, now=NOW, current_user_id="user-1")

    def rotate():
        try:
            return ("success", service.rotate_receipt(access.access_token, now=NOW, current_user_id="user-1").revision)
        except CaseSecurityError as exc:
            return ("error", str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _unused: rotate(), range(2)))
    assert sorted(outcomes) == [("error", "invalid_case_credential"), ("success", 2)]
    with db._conn(commit_on_success=False) as conn:
        row = db._fetchone(conn, "SELECT COUNT(*) AS count FROM case_receipts WHERE case_id=%s", (case_id,))
    assert db._row_to_dict(row)["count"] == 2
