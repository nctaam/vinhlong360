from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest

import chat_identity
import feedback_policy


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
USER_ID = "00000000-0000-0000-0000-000000000001"
USER_OWNER = f"user:{USER_ID}"
ANON_DIGEST = "a" * 64
ANON_OWNER = f"anon:{ANON_DIGEST}"
TURN_DIGEST = "b" * 64


class FakeStore:
    def __init__(self):
        self.rows = []
        self.consume_calls = []
        self.cleanup_calls = []
        self.purge_calls = []
        self.absent_calls = []
        self.issue_error = None
        self.consume_error = None

    def issue(self, record):
        if self.issue_error:
            raise self.issue_error
        self.rows.append(record)

    def consume(self, **kwargs):
        if self.consume_error:
            raise self.consume_error
        self.consume_calls.append(kwargs)
        return feedback_policy.FeedbackConsumeResult(rating=kwargs["rating"], idempotent=False)

    def cleanup(self, *, now, limit):
        self.cleanup_calls.append((now, limit))
        return 3

    def purge(self, *, owner_binding):
        self.purge_calls.append(owner_binding)
        return 2

    def owner_absent(self, *, owner_binding):
        self.absent_calls.append(owner_binding)
        return True


@pytest.fixture
def fake_store(monkeypatch):
    store = FakeStore()
    monkeypatch.setattr(feedback_policy, "_store", store)
    return store


def test_owner_binding_digest_is_deterministic_and_domain_separated():
    first = chat_identity.owner_binding_digest(USER_OWNER)
    assert len(first) == 64
    assert first == chat_identity.owner_binding_digest(USER_OWNER)
    assert first != chat_identity.owner_binding_digest(ANON_OWNER)
    assert first != chat_identity._sign_visitor_id(USER_OWNER)


def test_receipt_token_is_high_entropy_and_only_digest_is_persisted(fake_store):
    receipt = feedback_policy.issue_feedback_receipt(
        USER_OWNER,
        assistant_turn_digest=TURN_DIGEST,
        model_variant="cx/gpt-5.4",
        tool_bucket="search",
        now=NOW,
    )

    assert receipt is not None
    assert len(receipt.token) >= 43
    assert receipt.token not in repr(fake_store.rows)
    assert receipt.expires_at == NOW + timedelta(hours=24)
    row = fake_store.rows[0]
    assert row.user_id == USER_ID
    assert row.anonymous_owner_digest is None
    assert row.owner_kind == "authenticated"
    assert row.model_variant == "cx-gpt-5-4"
    assert row.tool_bucket == "search"
    assert row.assistant_turn_digest == TURN_DIGEST
    assert len(row.token_digest) == 64
    assert len(row.owner_binding_digest) == 64


def test_anonymous_receipt_uses_bounded_dimensions(fake_store):
    receipt = feedback_policy.issue_feedback_receipt(
        ANON_OWNER,
        assistant_turn_digest=TURN_DIGEST,
        model_variant="raw-model-user@example.com",
        tool_bucket="raw-tool-user@example.com",
        now=NOW,
    )

    assert receipt is not None
    row = fake_store.rows[0]
    assert row.user_id is None
    assert row.anonymous_owner_digest == ANON_DIGEST
    assert row.owner_kind == "anonymous"
    assert row.model_variant == "other"
    assert row.tool_bucket == "mixed"
    assert "raw-model-user@example.com" not in repr(row)
    assert "raw-tool-user@example.com" not in repr(row)


@pytest.mark.parametrize(
    ("owner_key", "turn_digest"),
    [
        ("anonymous", TURN_DIGEST),
        ("user:not-a-uuid", TURN_DIGEST),
        ("anon:not-a-digest", TURN_DIGEST),
        (USER_OWNER, "short"),
    ],
)
def test_issue_rejects_invalid_owner_or_turn_digest(owner_key, turn_digest, fake_store):
    with pytest.raises(feedback_policy.FeedbackRejected):
        feedback_policy.issue_feedback_receipt(
            owner_key,
            assistant_turn_digest=turn_digest,
            model_variant="cx-gpt-5-4",
            tool_bucket="none",
            now=NOW,
        )
    assert fake_store.rows == []


def test_issue_store_failure_returns_none_without_raw_exception(
    fake_store, caplog
):
    fake_store.issue_error = RuntimeError("database leaked db-user@example.com")

    with caplog.at_level(logging.WARNING, logger="feedback_policy"):
        receipt = feedback_policy.issue_feedback_receipt(
            USER_OWNER,
            assistant_turn_digest=TURN_DIGEST,
            model_variant="cx-gpt-5-4",
            tool_bucket="none",
            now=NOW,
        )

    assert receipt is None
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "FEEDBACK_RECEIPT_ISSUE_UNAVAILABLE" in output
    assert "db-user@example.com" not in output


@pytest.mark.parametrize(
    ("token", "rating"),
    [("short", 1), ("a" * 43, 2), ("a" * 43, True)],
)
def test_consume_validates_shape_before_store(token, rating, fake_store):
    with pytest.raises(feedback_policy.FeedbackRejected):
        feedback_policy.consume_feedback_receipt(
            token,
            USER_OWNER,
            rating,
            now=NOW,
        )
    assert fake_store.consume_calls == []


def test_consume_passes_only_digests_and_bounded_owner_fields(fake_store):
    token = "A" * 43
    result = feedback_policy.consume_feedback_receipt(
        token,
        USER_OWNER,
        1,
        now=NOW,
    )

    assert result == feedback_policy.FeedbackConsumeResult(rating=1, idempotent=False)
    call = fake_store.consume_calls[0]
    assert token not in repr(call)
    assert call["owner_kind"] == "authenticated"
    assert call["user_id"] == USER_ID
    assert call["anonymous_owner_digest"] is None
    assert len(call["token_digest"]) == 64
    assert len(call["owner_binding"]) == 64


def test_consume_store_failure_has_one_unavailable_class(fake_store, caplog):
    fake_store.consume_error = RuntimeError("db oracle secret@example.com")

    with caplog.at_level(logging.WARNING, logger="feedback_policy"):
        with pytest.raises(feedback_policy.FeedbackUnavailable) as exc_info:
            feedback_policy.consume_feedback_receipt(
                "A" * 43,
                USER_OWNER,
                1,
                now=NOW,
            )

    assert str(exc_info.value) == "FEEDBACK_UNAVAILABLE"
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "FEEDBACK_RECEIPT_CONSUME_UNAVAILABLE" in output
    assert "secret@example.com" not in output


def test_cleanup_and_lifecycle_hooks_use_owner_binding(fake_store):
    assert feedback_policy.cleanup_expired_feedback_receipts(now=NOW, limit=7) == 3
    assert fake_store.cleanup_calls == [(NOW, 7)]

    expected_binding = chat_identity.owner_binding_digest(USER_OWNER)
    assert feedback_policy.purge_feedback_owner(USER_OWNER) == 2
    assert feedback_policy.verify_feedback_owner_absent(USER_OWNER) is True
    assert fake_store.purge_calls == [expected_binding]
    assert fake_store.absent_calls == [expected_binding]


@pytest.mark.parametrize("limit", [0, -1, 501, True])
def test_cleanup_rejects_unbounded_limits(limit, fake_store):
    with pytest.raises(feedback_policy.FeedbackRejected):
        feedback_policy.cleanup_expired_feedback_receipts(now=NOW, limit=limit)
    assert fake_store.cleanup_calls == []
