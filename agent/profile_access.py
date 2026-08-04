from dataclasses import dataclass
from typing import Literal

from database import db


AccessStatus = Literal["ok", "hidden", "not_found"]


@dataclass(frozen=True)
class ProfileAccessDecision:
    status: AccessStatus
    target_id: str | None = None
    is_self: bool = False
    can_view_activity: bool = False


def can_view_profile_audience(
    visibility: str, is_self: bool, is_follower: bool
) -> bool:
    if is_self or visibility == "public":
        return True
    return visibility in {"followers", "followers_only", "private"} and is_follower


def resolve_profile_access(
    conn,
    target_id: str,
    viewer_id: str | None,
    *,
    require_activity: bool,
) -> ProfileAccessDecision:
    ph = db._ph
    row = db._fetchone(conn, f"""
        SELECT u.id, pv.profile_visibility, pv.show_activity
        FROM users u
        LEFT JOIN user_privacy pv ON pv.user_id = u.id
        WHERE u.id::text = {ph} AND u.is_active = TRUE AND u.deleted_at IS NULL
    """, (target_id,))
    if not row:
        return ProfileAccessDecision("not_found")
    target = db._row_to_dict(row)
    resolved_id = str(target["id"])
    is_self = viewer_id == resolved_id
    if is_self:
        return ProfileAccessDecision("ok", resolved_id, True, True)
    if viewer_id:
        blocked = db._fetchone(conn, f"""
            SELECT 1 FROM blocks
            WHERE (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
               OR (blocker_id = {ph}::uuid AND blocked_id = {ph}::uuid)
        """, (viewer_id, resolved_id, resolved_id, viewer_id))
        if blocked:
            return ProfileAccessDecision("hidden", resolved_id)
    visibility = target.get("profile_visibility") or "followers_only"
    is_follower = False
    if viewer_id and visibility != "public":
        is_follower = db._fetchone(conn, f"""
            SELECT 1 FROM follows
            WHERE follower_id = {ph}::uuid AND target_type = 'user' AND target_id = {ph}
        """, (viewer_id, resolved_id)) is not None
    if not can_view_profile_audience(visibility, False, is_follower):
        return ProfileAccessDecision("hidden", resolved_id)
    can_view_activity = target.get("show_activity") is True
    if require_activity and not can_view_activity:
        return ProfileAccessDecision("hidden", resolved_id)
    return ProfileAccessDecision("ok", resolved_id, False, can_view_activity)
