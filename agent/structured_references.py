"""Registered PostgreSQL delete actions and exact user-reference cleanup."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Mapping


_DELETE_ACTIONS = {"cascade", "set_null"}
_ACTOR_POLICIES = {"set_null"}


@dataclass(frozen=True)
class DeleteActionPolicy:
    table: str
    column: str
    action: str
    special_policy: str | None = None

    def __post_init__(self) -> None:
        if self.action not in _DELETE_ACTIONS:
            raise ValueError(f"unsupported delete action: {self.action}")
        if not self.table or not self.column:
            raise ValueError("delete-action table and column are required")


@dataclass(frozen=True)
class ScrubSummary:
    deleted_rows: int
    updated_rows: int
    mentions_removed: int
    claims_deleted: int
    claims_scrubbed: int
    actor_references_cleared: int

    def to_dict(self) -> dict[str, int]:
        return {
            "deleted_rows": self.deleted_rows,
            "updated_rows": self.updated_rows,
            "mentions_removed": self.mentions_removed,
            "claims_deleted": self.claims_deleted,
            "claims_scrubbed": self.claims_scrubbed,
            "actor_references_cleared": self.actor_references_cleared,
        }


class UnregisteredDeleteActionError(RuntimeError):
    """Raised when the live PostgreSQL catalog diverges from the registry."""


_REGISTERED_DELETE_ACTIONS = (
    DeleteActionPolicy("admin_user_notes", "admin_id", "set_null", "actor_reference"),
    DeleteActionPolicy("admin_user_notes", "user_id", "cascade"),
    DeleteActionPolicy("announcements", "created_by", "set_null", "actor_reference"),
    DeleteActionPolicy("blocks", "blocked_id", "cascade"),
    DeleteActionPolicy("blocks", "blocker_id", "cascade"),
    DeleteActionPolicy("bookmarks", "user_id", "cascade"),
    DeleteActionPolicy("collections", "created_by", "set_null", "actor_reference"),
    DeleteActionPolicy("comment_likes", "user_id", "cascade"),
    DeleteActionPolicy("comments", "user_id", "cascade"),
    DeleteActionPolicy("consent_log", "user_id", "cascade"),
    DeleteActionPolicy(
        "entity_claims", "claimant_id", "set_null", "completed_claim_scrub"
    ),
    DeleteActionPolicy("entity_claims", "reviewer_id", "set_null", "actor_reference"),
    DeleteActionPolicy("event_rsvp", "user_id", "cascade"),
    DeleteActionPolicy("featured_entities", "added_by", "set_null", "actor_reference"),
    DeleteActionPolicy("feedback_receipts", "user_id", "cascade"),
    DeleteActionPolicy("follows", "follower_id", "cascade"),
    DeleteActionPolicy("likes", "user_id", "cascade"),
    DeleteActionPolicy("login_history", "user_id", "cascade"),
    DeleteActionPolicy(
        "moderation_appeals", "reviewer_id", "set_null", "actor_reference"
    ),
    DeleteActionPolicy(
        "moderation_appeals", "user_id", "set_null", "completed_appeal_scrub"
    ),
    DeleteActionPolicy("moderation_log", "moderator_id", "set_null", "actor_reference"),
    DeleteActionPolicy("notification_preferences", "user_id", "cascade"),
    DeleteActionPolicy("notifications", "user_id", "cascade"),
    DeleteActionPolicy("pending_2fa", "user_id", "cascade"),
    DeleteActionPolicy("post_edit_history", "editor_id", "set_null", "actor_reference"),
    DeleteActionPolicy("post_reactions", "user_id", "cascade"),
    DeleteActionPolicy("posts", "featured_by", "set_null", "actor_reference"),
    DeleteActionPolicy("posts", "user_id", "cascade"),
    DeleteActionPolicy("profile_views", "viewed_id", "cascade"),
    DeleteActionPolicy("profile_views", "viewer_id", "cascade"),
    DeleteActionPolicy("reports", "reporter_id", "cascade"),
    DeleteActionPolicy("review_responses", "responder_id", "cascade"),
    DeleteActionPolicy("saved_entities", "user_id", "cascade"),
    DeleteActionPolicy("trusted_devices", "user_id", "cascade"),
    DeleteActionPolicy("user_2fa", "user_id", "cascade"),
    DeleteActionPolicy("user_2fa_recovery_codes", "user_id", "cascade"),
    DeleteActionPolicy("user_achievements", "user_id", "cascade"),
    DeleteActionPolicy("user_collections", "user_id", "cascade"),
    DeleteActionPolicy("user_hidden_posts", "user_id", "cascade"),
    DeleteActionPolicy("user_mutes", "muted_id", "cascade"),
    DeleteActionPolicy("user_mutes", "user_id", "cascade"),
    # NP-1 (migration 076): cả ba đều FK tới users ON DELETE CASCADE. Thiếu ở đây
    # thì xoá tài khoản bỏ sót tuỳ chọn/consent/hành vi của người đó —
    # test_erasure_constraints_postgres.py::test_registry_matches_every_source_fk_to_users
    # tồn tại đúng để bắt việc này, và nó đã đỏ khi hợp nhánh vào.
    DeleteActionPolicy("user_personalization_events", "user_id", "cascade"),
    DeleteActionPolicy("user_plans", "user_id", "cascade"),
    DeleteActionPolicy("user_preference_consents", "user_id", "cascade"),
    DeleteActionPolicy("user_preferences", "user_id", "cascade"),
    DeleteActionPolicy("user_privacy", "user_id", "cascade"),
    DeleteActionPolicy("user_sessions", "user_id", "cascade"),
    DeleteActionPolicy("user_visits", "user_id", "cascade"),
)


def registered_delete_actions() -> tuple[DeleteActionPolicy, ...]:
    return _REGISTERED_DELETE_ACTIONS


def _catalog_value(row, index: int, key: str):
    if isinstance(row, Mapping):
        return row[key]
    return row[index]


def _normalize_catalog_action(action: str) -> str:
    normalized = str(action).strip().upper().replace("_", " ")
    aliases = {
        "C": "cascade",
        "CASCADE": "cascade",
        "N": "set_null",
        "SET NULL": "set_null",
        "A": "no_action",
        "NO ACTION": "no_action",
        "R": "restrict",
        "RESTRICT": "restrict",
        "D": "set_default",
        "SET DEFAULT": "set_default",
    }
    return aliases.get(normalized, normalized.lower().replace(" ", "_"))


def validate_user_fk_actions(conn) -> tuple[DeleteActionPolicy, ...]:
    """Validate every FK to the current schema's users table against the registry."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT child.relname AS table_name,
                   attribute.attname AS column_name,
                   CASE constraint_row.confdeltype
                       WHEN 'c' THEN 'CASCADE'
                       WHEN 'n' THEN 'SET NULL'
                       WHEN 'r' THEN 'RESTRICT'
                       WHEN 'd' THEN 'SET DEFAULT'
                       ELSE 'NO ACTION'
                   END AS delete_action,
                   constraint_row.conname AS constraint_name
            FROM pg_constraint AS constraint_row
            JOIN pg_class AS child
              ON child.oid = constraint_row.conrelid
            JOIN pg_namespace AS child_namespace
              ON child_namespace.oid = child.relnamespace
            JOIN pg_class AS parent
              ON parent.oid = constraint_row.confrelid
            JOIN pg_namespace AS parent_namespace
              ON parent_namespace.oid = parent.relnamespace
            JOIN LATERAL unnest(constraint_row.conkey) AS key(attnum)
              ON TRUE
            JOIN pg_attribute AS attribute
              ON attribute.attrelid = child.oid
             AND attribute.attnum = key.attnum
            WHERE constraint_row.contype = 'f'
              AND parent.relname = 'users'
              AND child_namespace.nspname = current_schema()
              AND parent_namespace.nspname = current_schema()
            ORDER BY child.relname, attribute.attname, constraint_row.conname
            """
        )
        rows = cursor.fetchall()

    registry = {
        (policy.table, policy.column): policy
        for policy in registered_delete_actions()
    }
    observed: list[DeleteActionPolicy] = []
    violations: list[str] = []
    for row in rows:
        table = str(_catalog_value(row, 0, "table_name"))
        column = str(_catalog_value(row, 1, "column_name"))
        actual = _normalize_catalog_action(
            _catalog_value(row, 2, "delete_action")
        )
        policy = registry.get((table, column))
        if policy is None:
            violations.append(f"{table}.{column}: unregistered {actual}")
            continue
        if policy.action != actual:
            violations.append(
                f"{table}.{column}: catalog={actual}, registered={policy.action}"
            )
            continue
        observed.append(policy)

    if violations:
        raise UnregisteredDeleteActionError("; ".join(sorted(violations)))
    return tuple(observed)


def _execute_count(cursor, sql: str, params: tuple) -> int:
    cursor.execute(sql, params)
    return max(int(getattr(cursor, "rowcount", 0) or 0), 0)


def _row_pair(row) -> tuple[object, object]:
    if isinstance(row, Mapping):
        return row["id"], row["mentions"]
    return row[0], row[1]


def _decode_mentions(value) -> list:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
    return list(value) if isinstance(value, list) else []


def _scrub_mentions(cursor, table: str, user_id: str) -> tuple[int, int]:
    sentinel = json.dumps([{"type": "user", "id": user_id}], separators=(",", ":"))
    cursor.execute(
        f"""
        SELECT id, mentions FROM {table}
        WHERE jsonb_typeof(mentions) = 'array'
          AND mentions @> %s::jsonb
        FOR UPDATE
        """,
        (sentinel,),
    )
    updated_rows = 0
    removed_mentions = 0
    for row in cursor.fetchall():
        row_id, stored_mentions = _row_pair(row)
        mentions = _decode_mentions(stored_mentions)
        kept = [
            mention
            for mention in mentions
            if not (
                isinstance(mention, Mapping)
                and mention.get("type") == "user"
                and str(mention.get("id")) == user_id
            )
        ]
        removed = len(mentions) - len(kept)
        if not removed:
            continue
        updated_rows += _execute_count(
            cursor,
            f"UPDATE {table} SET mentions = %s::jsonb WHERE id = %s",
            (json.dumps(kept, ensure_ascii=False, separators=(",", ":")), row_id),
        )
        removed_mentions += removed
    return updated_rows, removed_mentions


def scrub_user_references(conn, user_id, *, actor_policy) -> ScrubSummary:
    """Remove exact non-FK references while preserving unrelated UUID-like text."""
    if actor_policy not in _ACTOR_POLICIES:
        raise ValueError("actor_policy must be 'set_null'")
    try:
        canonical_user_id = str(uuid.UUID(str(user_id)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("user_id must be a UUID") from exc
    owner_key = f"user:{canonical_user_id}"

    deleted_rows = 0
    updated_rows = 0
    mentions_removed = 0
    claims_deleted = 0
    claims_scrubbed = 0
    actor_references_cleared = 0

    with conn.cursor() as cursor:
        deleted_rows += _execute_count(
            cursor,
            "DELETE FROM feedback WHERE user_id = %s OR user_id = %s",
            (canonical_user_id, owner_key),
        )
        deleted_rows += _execute_count(
            cursor,
            """
            DELETE FROM follows
            WHERE follower_id::text = %s
               OR (target_type = 'user' AND target_id = %s)
            """,
            (canonical_user_id, canonical_user_id),
        )
        updated_rows += _execute_count(
            cursor,
            """
            UPDATE notifications SET ref_type = NULL, ref_id = NULL
            WHERE ref_type = 'user' AND ref_id = %s
            """,
            (canonical_user_id,),
        )
        deleted_rows += _execute_count(
            cursor,
            """
            DELETE FROM reports
            WHERE reporter_id::text = %s
               OR (target_type = 'user' AND target_id = %s)
            """,
            (canonical_user_id, canonical_user_id),
        )
        updated_rows += _execute_count(
            cursor,
            """
            UPDATE moderation_log
            SET target_id = NULL, reason = NULL, scores = NULL
            WHERE target_type = 'user' AND target_id = %s
            """,
            (canonical_user_id,),
        )

        for table in ("posts", "comments"):
            row_updates, removed = _scrub_mentions(cursor, table, canonical_user_id)
            updated_rows += row_updates
            mentions_removed += removed

        claim_pending = _execute_count(
            cursor,
            """
            DELETE FROM entity_claims WHERE status = 'pending'
              AND claimant_id::text = %s
            """,
            (canonical_user_id,),
        )
        claim_completed = _execute_count(
            cursor,
            """
            UPDATE entity_claims SET claimant_id = NULL, reviewer_id = NULL,
                business_name = NULL, contact_phone = NULL, contact_email = NULL,
                evidence = NULL, rejection_reason = NULL, reviewer_note = NULL
            WHERE status IN ('approved', 'rejected')
              AND claimant_id::text = %s
            """,
            (canonical_user_id,),
        )
        claim_reviewer = _execute_count(
            cursor,
            """
            UPDATE entity_claims SET reviewer_id = NULL,
                reviewer_note = NULL, rejection_reason = NULL
            WHERE reviewer_id::text = %s
            """,
            (canonical_user_id,),
        )
        claims_deleted += claim_pending
        claims_scrubbed += claim_completed + claim_reviewer
        deleted_rows += claim_pending
        updated_rows += claim_completed + claim_reviewer

        appeal_pending = _execute_count(
            cursor,
            """
            DELETE FROM moderation_appeals WHERE status = 'pending'
              AND user_id::text = %s
            """,
            (canonical_user_id,),
        )
        appeal_completed = _execute_count(
            cursor,
            """
            UPDATE moderation_appeals SET user_id = NULL, reviewer_id = NULL,
                reason = NULL, reviewer_note = NULL
            WHERE status IN ('approved', 'rejected')
              AND user_id::text = %s
            """,
            (canonical_user_id,),
        )
        appeal_reviewer = _execute_count(
            cursor,
            """
            UPDATE moderation_appeals SET reviewer_id = NULL, reviewer_note = NULL
            WHERE reviewer_id::text = %s
            """,
            (canonical_user_id,),
        )
        deleted_rows += appeal_pending
        updated_rows += appeal_completed + appeal_reviewer

        actor_counts = (
            _execute_count(
                cursor,
                """
                UPDATE admin_audit_events SET actor = NULL, actor_role = NULL,
                    actor_scopes = ARRAY[]::TEXT[], ip = NULL, reason = NULL,
                    before_json = NULL, after_json = NULL, meta = '{}'::jsonb
                WHERE actor = %s OR actor = %s
                """,
                (canonical_user_id, owner_key),
            ),
            _execute_count(
                cursor,
                "UPDATE entity_changes SET actor = NULL WHERE actor = %s OR actor = %s",
                (canonical_user_id, owner_key),
            ),
            _execute_count(
                cursor,
                "UPDATE site_settings_history SET actor = NULL WHERE actor = %s OR actor = %s",
                (canonical_user_id, owner_key),
            ),
        )
        actor_references_cleared += sum(actor_counts)
        updated_rows += sum(actor_counts)

    return ScrubSummary(
        deleted_rows=deleted_rows,
        updated_rows=updated_rows,
        mentions_removed=mentions_removed,
        claims_deleted=claims_deleted,
        claims_scrubbed=claims_scrubbed,
        actor_references_cleared=actor_references_cleared,
    )
