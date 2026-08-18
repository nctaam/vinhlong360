"""Evidence registry: a level is a claim about provenance, not a verdict."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))

from cases.correction import (  # noqa: E402
    EvidenceRecord,
    CorrectionRuling,
    conflicting_sources,
    supports_risk,
    usable_evidence,
)
from cases.domain import EvidenceLevel, RiskClass  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)


def _evidence(**overrides) -> EvidenceRecord:
    base = dict(
        evidence_id="e-1",
        case_id="c-1",
        item_id="i-1",
        level=EvidenceLevel.E2,
        source_scope="place.contact",
        author_ref="person:operator",
        observed_at=NOW - timedelta(days=1),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=30),
        source_ref="https://example.gov.vn/a",
    )
    base.update(overrides)
    return EvidenceRecord(**base)


# ── Usability is separate from level ──

def test_every_level_is_accepted_as_a_record_without_deciding_anything():
    for level in (EvidenceLevel.E0, EvidenceLevel.E1, EvidenceLevel.E2,
                  EvidenceLevel.E3, EvidenceLevel.E4):
        record = _evidence(level=level)
        assert record.level is level
        # Recording it does not accept it.
        assert usable_evidence((record,), now=NOW, required_scope="place.contact") == (record,)


def test_expired_evidence_is_not_usable():
    stale = _evidence(expires_at=NOW - timedelta(seconds=1))

    assert usable_evidence((stale,), now=NOW, required_scope="place.contact") == ()


def test_evidence_from_another_scope_is_not_usable():
    other = _evidence(source_scope="place.opening_hours")

    assert usable_evidence((other,), now=NOW, required_scope="place.contact") == ()


def test_evidence_observed_after_the_decision_clock_is_not_usable():
    future = _evidence(observed_at=NOW + timedelta(days=1))

    assert usable_evidence((future,), now=NOW, required_scope="place.contact") == ()


# ── Risk rules: a high level alone never carries a high-risk decision ──

def test_r0_and_r1_accept_an_ordinary_contextual_artifact():
    contextual = (_evidence(level=EvidenceLevel.E1),)

    assert supports_risk(contextual, RiskClass.R0, decision_maker_ref="person:other") is True
    assert supports_risk(contextual, RiskClass.R1, decision_maker_ref="person:other") is True


def test_r2_needs_an_authoritative_source_or_two_independent_ones():
    single_public = (_evidence(level=EvidenceLevel.E2, evidence_id="e-1"),)
    assert supports_risk(single_public, RiskClass.R2, decision_maker_ref="person:other") is False

    two_independent = (
        _evidence(level=EvidenceLevel.E2, evidence_id="e-1", source_ref="https://a.example"),
        _evidence(level=EvidenceLevel.E2, evidence_id="e-2", source_ref="https://b.example"),
    )
    assert supports_risk(two_independent, RiskClass.R2, decision_maker_ref="person:other") is True

    authoritative = (_evidence(level=EvidenceLevel.E3),)
    assert supports_risk(authoritative, RiskClass.R2, decision_maker_ref="person:other") is True


def test_two_pieces_from_the_same_source_are_not_two_independent_sources():
    same_source = (
        _evidence(evidence_id="e-1", source_ref="https://same.example/x"),
        _evidence(evidence_id="e-2", source_ref="https://same.example/x"),
    )

    assert supports_risk(same_source, RiskClass.R2, decision_maker_ref="person:other") is False


def test_a_reporter_assertion_alone_never_supports_a_high_risk_decision():
    reporter_only = (_evidence(level=EvidenceLevel.E0, author_ref="anonymous"),)

    for risk in (RiskClass.R2, RiskClass.R3):
        assert supports_risk(reporter_only, risk, decision_maker_ref="person:other") is False


def test_the_decision_maker_cannot_lean_only_on_evidence_they_authored():
    """Author recusal: somebody else must have put at least one piece on the record."""
    own = (
        _evidence(evidence_id="e-1", level=EvidenceLevel.E3, author_ref="person:me"),
    )

    assert supports_risk(own, RiskClass.R2, decision_maker_ref="person:me") is False
    with_other = own + (
        _evidence(evidence_id="e-2", level=EvidenceLevel.E3, author_ref="person:someone",
                  source_ref="https://b.example"),
    )
    assert supports_risk(with_other, RiskClass.R2, decision_maker_ref="person:me") is True


# ── Conflict ──

def test_sources_that_disagree_are_reported_rather_than_silently_ranked():
    disagreeing = (
        _evidence(evidence_id="e-1", source_ref="https://a.example", asserted_value="0270 111"),
        _evidence(evidence_id="e-2", source_ref="https://b.example", asserted_value="0270 222"),
    )

    conflict = conflicting_sources(disagreeing)

    assert conflict is True
    # A conflict blocks acceptance; it does not pick a winner by level.
    assert supports_risk(disagreeing, RiskClass.R2, decision_maker_ref="person:other") is False


def test_agreeing_sources_are_not_a_conflict():
    agreeing = (
        _evidence(evidence_id="e-1", source_ref="https://a.example", asserted_value="0270 111"),
        _evidence(evidence_id="e-2", source_ref="https://b.example", asserted_value="0270 111"),
    )

    assert conflicting_sources(agreeing) is False


def test_a_ruling_states_why_it_refused():
    ruling = CorrectionRuling.for_risk(
        (_evidence(level=EvidenceLevel.E0),), RiskClass.R3, decision_maker_ref="person:me"
    )

    assert ruling.supported is False
    assert ruling.reason_code in {
        "insufficient_evidence_level", "independent_source_required",
        "author_recusal_required", "evidence_conflict",
    }


# ── Persistence, against real PostgreSQL ──

import os  # noqa: E402
from urllib.parse import parse_qs, urlparse  # noqa: E402

import pytest  # noqa: E402

import database  # noqa: E402
from cases.domain import ActorContext, Channel  # noqa: E402
from cases.policy import load_case_policy  # noqa: E402
from cases.security import CaseCrypto  # noqa: E402


def _pg_url():
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


TEST_DATABASE_URL = _pg_url()
pg_only = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database",
)
MASTER_KEY = "0" * 43


@pytest.fixture
def pg_database():
    if TEST_DATABASE_URL is None:
        pytest.skip("set VL360_TEST_DATABASE_URL to a disposable loopback PostgreSQL database")
    import psycopg2
    import psycopg2.extras

    from cases.correction import configure_case_correction

    database.psycopg2 = psycopg2
    database.psycopg2.extras = psycopg2.extras
    adapter = database.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    with adapter._conn(commit_on_success=False) as conn:
        adapter._execute(
            conn,
            "INSERT INTO entities (id, type, name, revision) VALUES (%s,'place','Vinh Long',7)"
            " ON CONFLICT (id) DO UPDATE SET revision = 7",
            ("p-cs",),
        )
        conn.commit()
    configure_case_correction(
        database=adapter, crypto=CaseCrypto(MASTER_KEY), policy=load_case_policy()
    )
    yield adapter
    configure_case_correction(database=None, crypto=None, policy=None)


def _decider(ref="person:maker", scopes=("cases:work", "cases:decide")):
    return ActorContext(actor_ref=ref, channel=Channel.WEB, scopes=frozenset(scopes),
                        correlation_id="corr-persist")


def _seed_case_with_item(adapter, *, entity_id="p-cs", field_path="attributes.phone",
                         risk="R1", holder="person:maker"):
    from cases.security import CaseCrypto as _Crypto

    crypto = _Crypto(MASTER_KEY)
    with adapter._conn(commit_on_success=False) as conn:
        case_id = str(adapter._fetchone(
            conn,
            """
            INSERT INTO cases (service_kind, category, phase, activity, disposition_family,
                               reporter_privacy, owner_ref, current_revision, promise_policy_ref)
            VALUES ('correction','correction','decision','active','undetermined','anonymous',
                    'person:owner',1,'correction-pilot-v1')
            RETURNING case_id
            """,
            (),
        )["case_id"])
        item_id = str(adapter._fetchone(
            conn,
            """
            INSERT INTO correction_items (case_id, entity_id, field_path, reported_value_enc,
                                          proposed_value_enc, base_entity_revision,
                                          risk_class, evidence_level)
            VALUES (%s,%s,%s,%s,%s,7,%s,'E0') RETURNING item_id
            """,
            (case_id, entity_id, field_path,
             crypto.encrypt_private_payload({"value": "0270 111 2222"}),
             crypto.encrypt_private_payload({"value": "0270 333 4444"}), risk),
        )["item_id"])
        if holder:
            adapter._execute(
                conn,
                """
                INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,
                                             assignee_ref, lease_expires_at, ready_at, priority)
                VALUES (%s,'decide','case_operator',%s,'claimed',%s,%s,%s,0)
                """,
                (case_id, risk, holder, NOW + timedelta(hours=1), NOW),
            )
        conn.commit()
    return case_id, item_id


@pg_only
def test_add_evidence_stores_the_payload_encrypted_and_needs_a_live_lease(pg_database):
    from cases.correction import AddEvidenceCommand, CorrectionRejected, add_evidence

    case_id, item_id = _seed_case_with_item(pg_database)
    command = AddEvidenceCommand(
        case_id=case_id, item_id=item_id, level=EvidenceLevel.E3,
        source_scope="place.contact", source_ref="https://a.example",
        descriptor={"kind": "authoritative_source"},
        content="scan of the licence", actor=_decider(),
        observed_at=NOW - timedelta(days=1), effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=30), asserted_value="0270 333 4444",
    )

    record = add_evidence(command, now=NOW)

    assert record.evidence_id
    with pg_database._conn(commit_on_success=False) as conn:
        row = dict(pg_database._fetchone(
            conn,
            "SELECT evidence_level, source_ref, content_enc, created_by_ref"
            " FROM correction_evidence WHERE evidence_id=%s",
            (record.evidence_id,),
        ))
    assert row["evidence_level"] == "E3"
    assert "scan of the licence" not in str(row["content_enc"])
    assert row["created_by_ref"] == "person:maker"

    # Somebody without the lease cannot put evidence on this case.
    with pytest.raises(CorrectionRejected) as excinfo:
        add_evidence(
            AddEvidenceCommand(**{**command.__dict__, "actor": _decider("person:stranger")}),
            now=NOW,
        )
    assert excinfo.value.problem.code == "active_lease_required"
