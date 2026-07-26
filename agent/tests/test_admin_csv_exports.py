import asyncio
import csv
import io

import pytest

import admin


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_row_neutralizes_spreadsheet_formula_prefixes(prefix):
    payload = f"{prefix}SUM(1,1)"

    parsed = next(csv.reader([admin._csv_row([payload])]))

    assert parsed == [f"'{payload}"]


def test_csv_row_preserves_unicode_quotes_commas_and_columns():
    parsed = next(csv.reader([admin._csv_row(['Bình "An", Trà Vinh', None, 7])]))

    assert parsed == ['Bình "An", Trà Vinh', '', '7']


async def _response_text(response) -> str:
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


def test_contact_funnel_csv_uses_safe_cells(tmp_path, monkeypatch):
    log = tmp_path / "contact_views.jsonl"
    log.write_text(
        '{"ts":"2999-01-01T00:00:00+00:00","entity_id":"=entity","action":"phone"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(admin, "CONTACT_VIEWS_FILE", log)
    monkeypatch.setattr(admin.knowledge, "_entities", {"=entity": {"name": '+Cơ sở, "Mới"'}})

    async def export_csv():
        response = await admin.contact_funnel_export(days=30)
        return await _response_text(response)

    rows = list(csv.reader(io.StringIO(asyncio.run(export_csv()))))

    assert rows[0] == ["entity_id", "name", "zalo", "phone", "website", "map", "total"]
    assert rows[1] == ["'=entity", '\'+Cơ sở, "Mới"', "0", "1", "0", "0", "1"]


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakeDb:
    _ph = "%s"

    def __init__(self, rows):
        self.rows = rows

    def _conn(self):
        return _Connection()

    def _fetchall(self, _conn, _sql, _params=()):
        return self.rows

    @staticmethod
    def _row_to_dict(row):
        return row


def test_users_csv_preserves_schema_and_neutralizes_user_name(monkeypatch):
    monkeypatch.setattr(admin, "require_pg", lambda: None)
    monkeypatch.setattr(admin, "db", _FakeDb([{
        "id": "user-1",
        "phone": "0901234567",
        "display_name": '=SUM(1,1) — Bình "An", Trà Vinh',
        "role": "user",
        "is_active": True,
        "reputation": 7,
        "created_at": "2026-07-26",
        "post_count": 2,
        "follower_count": 3,
    }]))

    async def export_csv():
        response = await admin.export_users_csv()
        return await _response_text(response)

    rows = list(csv.reader(io.StringIO(asyncio.run(export_csv()))))

    assert rows[0] == ["id", "phone", "display_name", "role", "is_active", "reputation", "created_at", "post_count", "follower_count"]
    assert rows[1][2] == '\'=SUM(1,1) — Bình "An", Trà Vinh'
    assert len(rows[1]) == len(rows[0])


def test_posts_csv_preserves_schema_and_neutralizes_user_name(monkeypatch):
    monkeypatch.setattr(admin, "require_pg", lambda: None)
    monkeypatch.setattr(admin, "db", _FakeDb([{
        "id": "post-1",
        "user_id": "user-1",
        "author_name": "@Nguyễn, \"An\"",
        "post_type": "review",
        "rating": 5,
        "like_count": 2,
        "comment_count": 1,
        "share_count": 0,
        "moderation_status": "approved",
        "entity_id": "entity-1",
        "created_at": "2026-07-26",
    }]))

    async def export_csv():
        response = await admin.export_posts_csv()
        return await _response_text(response)

    rows = list(csv.reader(io.StringIO(asyncio.run(export_csv()))))

    assert rows[0] == ["id", "user_id", "author_name", "post_type", "rating", "like_count", "comment_count", "share_count", "status", "entity_id", "created_at"]
    assert rows[1][2] == '\'@Nguyễn, "An"'
    assert len(rows[1]) == len(rows[0])
