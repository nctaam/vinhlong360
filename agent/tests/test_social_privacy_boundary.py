import asyncio
from contextlib import contextmanager

import social


@contextmanager
def _fake_conn():
    yield object()


def test_friend_saves_enforces_owner_visibility_in_sql(monkeypatch):
    captured = {}
    row = {
        "entity_id": "entity-1",
        "name": "Cho Vinh Long",
        "entity_type": "market",
        "display_name": "Friend",
        "avatar_url": "/avatar.webp",
        "created_at": "2026-07-12T08:30:00+00:00",
    }

    def _fetchall(_conn, sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [row]

    monkeypatch.setattr(social.db, "_conn", _fake_conn)
    monkeypatch.setattr(social.db, "_fetchall", _fetchall)
    monkeypatch.setattr(social.db, "_row_to_dict", lambda value: value)

    result = asyncio.run(social.get_friend_saves(limit=5, user={"id": "viewer-1"}))

    assert (
        "LEFT JOIN user_privacy save_privacy ON save_privacy.user_id = s.user_id"
        in captured["sql"]
    )
    assert "COALESCE(save_privacy.show_saved, TRUE) = TRUE" in captured["sql"]
    assert result == {
        "saves": [
            {
                "entity_id": "entity-1",
                "entity_name": "Cho Vinh Long",
                "entity_type": "market",
                "user": {
                    "display_name": "Friend",
                    "avatar_url": "/avatar.webp",
                },
                "created_at": "2026-07-12T08:30:00+00:00",
            }
        ]
    }
