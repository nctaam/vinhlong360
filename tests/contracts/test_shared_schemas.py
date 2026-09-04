from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "contracts" / "schemas"


def _load_schema(name: str) -> dict:
    path = SCHEMA_ROOT / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_error_schema_is_draft_2020_12_and_requires_shared_fields() -> None:
    schema = _load_schema("error-envelope.schema.json")

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    valid = {
        "type": "https://example.test/problems/invalid-request",
        "title": "Invalid request",
        "status": 400,
        "code": "INVALID_REQUEST",
        "detail": "The request could not be processed.",
        "requestId": "req-123",
    }

    assert list(validator.iter_errors(valid)) == []


def test_error_schema_rejects_missing_required_field_and_unknown_property() -> None:
    schema = _load_schema("error-envelope.schema.json")
    validator = Draft202012Validator(schema)
    invalid = {
        "type": "about:blank",
        "title": "Bad request",
        "status": 400,
        "code": "BAD_REQUEST",
        "requestId": "req-123",
        "unexpected": True,
    }

    errors = list(validator.iter_errors(invalid))

    assert any(error.validator == "required" for error in errors)
    assert any(error.validator == "additionalProperties" for error in errors)


def test_error_schema_rejects_invalid_status() -> None:
    schema = _load_schema("error-envelope.schema.json")
    validator = Draft202012Validator(schema)

    invalid = {
        "type": "about:blank",
        "title": "Invalid status",
        "status": 99,
        "code": "INVALID_STATUS",
        "detail": "Status is outside the HTTP range.",
    }

    errors = list(validator.iter_errors(invalid))

    assert any(list(error.path) == ["status"] for error in errors)


def test_pagination_schema_accepts_offset_and_cursor_examples() -> None:
    schema = _load_schema("pagination.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    examples = [
        {},
        {"limit": 20, "offset": 0, "nextCursor": "eyJvZmZzZXQiOjIwfQ", "hasMore": True},
        {"limit": 20, "offset": 20, "nextCursor": None, "hasMore": False},
    ]

    for example in examples:
        assert list(validator.iter_errors(example)) == []


def test_pagination_schema_rejects_invalid_metadata_and_unknown_property() -> None:
    schema = _load_schema("pagination.schema.json")
    validator = Draft202012Validator(schema)
    invalid = {
        "limit": 0,
        "offset": -1,
        "nextCursor": 123,
        "hasMore": "yes",
        "total": 100,
    }

    errors = list(validator.iter_errors(invalid))

    assert any(error.validator == "minimum" for error in errors)
    assert any(error.validator == "type" for error in errors)
    assert any(error.validator == "additionalProperties" for error in errors)
