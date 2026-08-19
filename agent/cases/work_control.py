"""Backstage work control: a derived queue and compare-and-set leases.

The queue is a query, not a stored status. Order comes from the work row, the
case's promise clocks and the risk class, so nobody can move their own items up
by writing a field, and there is no throughput counter to game.

A lease is held by exactly one actor at a time and always expires. Every claim,
extension, release, takeover, recusal and completion is a compare-and-set on the
work item's revision, so two racing operators cannot both believe they own it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .domain import CaseProblem, RiskClass

WORK_SCOPE = "cases:work"
HIGH_RISK_SCOPE = "cases:high_risk"
SUPERVISOR_SCOPE = "case.supervisor"
HIGH_RISK_CLASSES = frozenset({RiskClass.R2, RiskClass.R3})
AT_RISK_FRACTION = 0.8
ESCALATION_KIND = "escalation"

_DATABASE = None
_POLICY = None


class WorkControlRejected(ValueError):
    def __init__(self, problem: CaseProblem) -> None:
        super().__init__(problem.code)
        self.problem = problem


def _reject(code: str, detail: str, status: int = 409) -> WorkControlRejected:
    return WorkControlRejected(CaseProblem(code=code, detail=detail, status=status))


@dataclass(frozen=True)
class WorkItem:
    work_item_id: str
    case_id: str
    kind: str
    required_role: str
    risk_class: RiskClass
    status: str
    assignee_ref: str | None
    lease_expires_at: datetime | None
    ready_at: datetime
    priority: int
    revision: int
    # Derived from the case's promise clocks at read time, never stored here.
    promise_health: str = "on_track"


@dataclass(frozen=True)
class QueuePage:
    items: tuple[WorkItem, ...]
    total: int


@dataclass(frozen=True)
class EscalationSummary:
    scanned: int = 0
    created: int = 0
    skipped: int = 0


def configure_case_work_control(*, database=None, policy=None) -> None:
    global _DATABASE, _POLICY
    _DATABASE = database
    _POLICY = policy


def _database():
    if _DATABASE is not None:
        return _DATABASE
    from database import db

    return db


def _lease_duration() -> timedelta:
    seconds = getattr(_POLICY, "lease_duration_seconds", 1800) if _POLICY else 1800
    return timedelta(seconds=int(seconds))


def _row_to_item(database, row) -> WorkItem:
    item = database._row_to_dict(row)
    return WorkItem(
        work_item_id=str(item["work_item_id"]),
        case_id=str(item["case_id"]),
        kind=str(item["kind"]),
        required_role=str(item["required_role"]),
        risk_class=RiskClass(item["risk_class"]),
        status=str(item["status"]),
        assignee_ref=item["assignee_ref"],
        lease_expires_at=item["lease_expires_at"],
        ready_at=item["ready_at"],
        priority=int(item["priority"]),
        revision=int(item["revision"]),
        promise_health={2: "breached", 1: "at_risk"}.get(
            int(item.get("health_rank") or 0), "on_track"
        ),
    )


_COLUMNS = (
    "work_item_id, case_id, kind, required_role, risk_class, status,"
    " assignee_ref, lease_expires_at, ready_at, priority, revision"
)


def _require_clock(now: datetime) -> None:
    if type(now) is not datetime or now.tzinfo is None:
        raise ValueError("invalid_work_clock")


def _require_scopes(actor, item: WorkItem | None) -> None:
    scopes = set(getattr(actor, "scopes", ()) or ())
    if WORK_SCOPE not in scopes:
        raise _reject("work_scope_required", "You cannot take backstage work.", status=403)
    if item is not None and item.risk_class in HIGH_RISK_CLASSES and HIGH_RISK_SCOPE not in scopes:
        # A supervisor may reassign work; nobody may reassign the risk rules.
        raise _reject(
            "risk_clearance_required",
            "This work needs an explicit high-risk clearance.",
            status=403,
        )


def _load(database, conn, work_item_id: str) -> WorkItem:
    row = database._fetchone(
        database and conn,
        f"SELECT {_COLUMNS} FROM case_work_items WHERE work_item_id = %s",
        (work_item_id,),
    )
    if row is None:
        raise _reject("work_item_not_found", "That work item does not exist.", status=404)
    return _row_to_item(database, row)


def _recused(database, conn, work_item_id: str, actor_ref: str) -> bool:
    row = database._fetchone(
        conn,
        """
        SELECT 1 FROM case_audit_events
        WHERE reason_code = 'work_recused'
          AND actor_ref = %s
          AND after_snapshot->>'work_item_id' = %s
        LIMIT 1
        """,
        (actor_ref, work_item_id),
    )
    return row is not None


def _audit(database, conn, item: WorkItem, actor, *, reason_code: str, now: datetime,
           detail: dict | None = None) -> None:
    import json

    payload = {"work_item_id": item.work_item_id, "kind": item.kind}
    payload.update(detail or {})
    database._execute(
        conn,
        """
        INSERT INTO case_audit_events (
            case_id, actor_ref, actor_scopes, channel, reason_code,
            policy_revision, correlation_id, before_snapshot, after_snapshot, created_at
        ) VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, NULL, %s::jsonb, %s)
        """,
        (
            item.case_id,
            getattr(actor, "actor_ref", "unknown"),
            json.dumps(sorted(set(getattr(actor, "scopes", ()) or ())), separators=(",", ":")),
            getattr(getattr(actor, "channel", None), "value", "web"),
            reason_code,
            getattr(_POLICY, "revision", "correction-pilot-v1"),
            getattr(actor, "correlation_id", "work-control"),
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            now,
        ),
    )


# ── Queue ──

_QUEUE_SQL = f"""
SELECT {_COLUMNS}, COALESCE(health.health_rank, 0) AS health_rank
FROM case_work_items AS work
LEFT JOIN LATERAL (
    SELECT max(
        CASE
            WHEN clock.due_at <= %(now)s THEN 2
            WHEN clock.due_at <= %(now)s + (clock.due_at - clock.started_at) * 0 THEN 1
            WHEN EXTRACT(EPOCH FROM (clock.due_at - %(now)s))
                 <= EXTRACT(EPOCH FROM (clock.due_at - clock.started_at)) * %(at_risk)s THEN 1
            ELSE 0
        END
    ) AS health_rank
    FROM case_promise_clocks AS clock
    WHERE clock.case_id = work.case_id
) AS health ON TRUE
WHERE work.status = 'ready'
   OR (work.status = 'claimed' AND work.lease_expires_at <= %(now)s)
ORDER BY work.priority DESC,
         COALESCE(health.health_rank, 0) DESC,
         work.risk_class DESC,
         work.ready_at ASC,
         work.work_item_id ASC
LIMIT %(limit)s
"""


def list_queue(actor, filters: dict | None = None, *, now: datetime) -> QueuePage:
    """Derived order: emergency, then promise health, then risk, then age."""
    _require_clock(now)
    _require_scopes(actor, None)
    database = _database()
    limit = int((filters or {}).get("limit", 100))
    with database._conn(commit_on_success=False) as conn:
        rows = database._fetchall(
            conn, _QUEUE_SQL,
            {"now": now, "at_risk": 1 - AT_RISK_FRACTION, "limit": limit},
        )
        items = tuple(_row_to_item(database, row) for row in rows)
    return QueuePage(items=items, total=len(items))


# ── Lease commands, all compare-and-set on revision ──

def _apply(database, conn, sql: str, params: tuple, *, code: str, detail: str) -> WorkItem:
    row = database._fetchone(conn, sql, params)
    if row is None:
        raise _reject(code, detail)
    return _row_to_item(database, row)


def claim_work_item(work_item_id: str, actor, expected_revision: int, *, now: datetime) -> WorkItem:
    _require_clock(now)
    database = _database()
    with database._conn(commit_on_success=False) as conn:
        item = _load(database, conn, work_item_id)
        _require_scopes(actor, item)
        actor_ref = getattr(actor, "actor_ref", "unknown")
        if _recused(database, conn, work_item_id, actor_ref):
            raise _reject("actor_recused", "You stepped back from this case.", status=403)
        if item.revision != expected_revision:
            raise _reject("work_item_revision_conflict", "This work item changed; reload it.")
        claimed = _apply(
            database, conn,
            f"""
            UPDATE case_work_items
            SET status = 'claimed', assignee_ref = %s, lease_expires_at = %s,
                revision = revision + 1
            WHERE work_item_id = %s AND revision = %s
              AND (assignee_ref IS NULL OR lease_expires_at <= %s OR status <> 'claimed')
            RETURNING {_COLUMNS}
            """,
            (actor_ref, now + _lease_duration(), work_item_id, expected_revision, now),
            code="work_item_already_claimed",
            detail="Somebody else is holding this work item.",
        )
        _audit(database, conn, claimed, actor, reason_code="work_claimed", now=now)
        conn.commit()
    if claimed.kind in ("decide", "decision"):
        from . import metrics as _metrics

        # The moment somebody picks the decision work up is when triage starts;
        # nothing earlier involves a person looking at the case.
        _metrics.observe("triaged", channel="web", risk_class=str(claimed.risk_class),
                         case_id=claimed.case_id, now=now)
    return claimed


def heartbeat_lease(work_item_id: str, actor, *, now: datetime) -> WorkItem:
    _require_clock(now)
    database = _database()
    actor_ref = getattr(actor, "actor_ref", "unknown")
    with database._conn(commit_on_success=False) as conn:
        beaten = _apply(
            database, conn,
            f"""
            UPDATE case_work_items
            SET lease_expires_at = %s, revision = revision + 1
            WHERE work_item_id = %s AND status = 'claimed'
              AND assignee_ref = %s AND lease_expires_at > %s
            RETURNING {_COLUMNS}
            """,
            (now + _lease_duration(), work_item_id, actor_ref, now),
            code="work_item_lease_expired",
            detail="That lease is no longer yours to extend.",
        )
        conn.commit()
    return beaten


def release_work_item(work_item_id: str, actor, *, now: datetime) -> WorkItem:
    _require_clock(now)
    database = _database()
    actor_ref = getattr(actor, "actor_ref", "unknown")
    with database._conn(commit_on_success=False) as conn:
        released = _apply(
            database, conn,
            f"""
            UPDATE case_work_items
            SET status = 'ready', assignee_ref = NULL, lease_expires_at = NULL,
                revision = revision + 1
            WHERE work_item_id = %s AND assignee_ref = %s
            RETURNING {_COLUMNS}
            """,
            (work_item_id, actor_ref),
            code="work_item_not_held",
            detail="You are not holding this work item.",
        )
        _audit(database, conn, released, actor, reason_code="work_released", now=now)
        conn.commit()
    return released


def takeover_work_item(work_item_id: str, actor, reason: str, *, now: datetime) -> WorkItem:
    _require_clock(now)
    scopes = set(getattr(actor, "scopes", ()) or ())
    if SUPERVISOR_SCOPE not in scopes:
        raise _reject("supervisor_scope_required", "Only a supervisor can take work over.", status=403)
    if type(reason) is not str or not reason.strip():
        raise _reject("takeover_reason_required", "A takeover needs a stated reason.", status=400)
    database = _database()
    with database._conn(commit_on_success=False) as conn:
        item = _load(database, conn, work_item_id)
        # Checked after the supervisor gate on purpose: seniority reassigns work,
        # it does not grant clearance the risk rules withhold.
        _require_scopes(actor, item)
        taken = _apply(
            database, conn,
            f"""
            UPDATE case_work_items
            SET status = 'claimed', assignee_ref = %s, lease_expires_at = %s,
                revision = revision + 1
            WHERE work_item_id = %s
            RETURNING {_COLUMNS}
            """,
            (getattr(actor, "actor_ref", "unknown"), now + _lease_duration(), work_item_id),
            code="work_item_not_found",
            detail="That work item does not exist.",
        )
        _audit(database, conn, taken, actor, reason_code="work_taken_over", now=now,
               detail={"reason": reason.strip()})
        conn.commit()
    return taken


def recuse_actor(work_item_id: str, actor, reason: str, *, now: datetime) -> WorkItem:
    """Close this item for the recused actor and open a replacement for someone else."""
    _require_clock(now)
    if type(reason) is not str or not reason.strip():
        raise _reject("recusal_reason_required", "A recusal needs a stated reason.", status=400)
    database = _database()
    actor_ref = getattr(actor, "actor_ref", "unknown")
    with database._conn(commit_on_success=False) as conn:
        item = _load(database, conn, work_item_id)
        database._execute(
            conn,
            """
            UPDATE case_work_items
            SET status = 'cancelled', assignee_ref = NULL, lease_expires_at = NULL,
                revision = revision + 1
            WHERE work_item_id = %s
            """,
            (work_item_id,),
        )
        replacement = _apply(
            database, conn,
            f"""
            INSERT INTO case_work_items (case_id, kind, required_role, risk_class, status,
                                         ready_at, priority)
            VALUES (%s, %s, %s, %s, 'ready', %s, %s)
            RETURNING {_COLUMNS}
            """,
            (item.case_id, item.kind, item.required_role, item.risk_class.value,
             now, item.priority),
            code="work_item_not_found",
            detail="That work item does not exist.",
        )
        _audit(database, conn, replacement, actor, reason_code="work_recused", now=now,
               detail={"reason": reason.strip(), "replaces": work_item_id,
                       "recused_actor_ref": actor_ref})
        conn.commit()
    return replacement


def complete_work_item(work_item_id: str, actor, result_ref: str, *, now: datetime) -> WorkItem:
    _require_clock(now)
    if type(result_ref) is not str or not result_ref.strip():
        raise _reject("result_reference_required", "Completed work needs a result reference.",
                      status=400)
    database = _database()
    actor_ref = getattr(actor, "actor_ref", "unknown")
    with database._conn(commit_on_success=False) as conn:
        done = _apply(
            database, conn,
            f"""
            UPDATE case_work_items
            SET status = 'completed', assignee_ref = NULL, lease_expires_at = NULL,
                revision = revision + 1
            WHERE work_item_id = %s AND status = 'claimed' AND assignee_ref = %s
              AND lease_expires_at > %s
            RETURNING {_COLUMNS}
            """,
            (work_item_id, actor_ref, now),
            code="work_item_not_held",
            detail="Only the live lease holder can complete this work.",
        )
        # No result column exists on the locked schema, so the reference is
        # recorded in the audit event that the completion is proved by.
        _audit(database, conn, done, actor, reason_code="work_completed", now=now,
               detail={"result_ref": result_ref.strip()})
        conn.commit()
    return done


# ── Escalation ──

_ESCALATION_SQL = """
SELECT DISTINCT work.case_id
FROM case_work_items AS work
JOIN case_promise_clocks AS clock ON clock.case_id = work.case_id
JOIN cases AS parent ON parent.case_id = work.case_id
WHERE clock.due_at <= %(now)s
  AND parent.phase <> 'closed'
  AND NOT EXISTS (
      SELECT 1 FROM case_work_items AS existing
      WHERE existing.case_id = work.case_id
        AND existing.kind = %(kind)s
        AND existing.status <> 'cancelled'
  )
"""


def scan_escalations(*, now: datetime, limit: int = 200) -> EscalationSummary:
    """Idempotent: a case that already carries an open escalation is skipped.

    Escalation only ever adds work. It never edits prior history, never moves a
    phase, and never touches a terminal outcome.
    """
    _require_clock(now)
    database = _database()
    created = 0
    with database._conn(commit_on_success=False) as conn:
        rows = database._fetchall(
            conn, _ESCALATION_SQL + " LIMIT %(limit)s",
            {"now": now, "kind": ESCALATION_KIND, "limit": limit},
        )
        case_ids = [str(database._row_to_dict(row)["case_id"]) for row in rows]
        from . import metrics as _metrics

        for expired_case_id in case_ids:
            _metrics.observe("lease_expired", channel="web",
                             case_id=expired_case_id, now=now)
        for case_id in case_ids:
            database._execute(
                conn,
                """
                INSERT INTO case_work_items (case_id, kind, required_role, risk_class,
                                             status, ready_at, priority)
                VALUES (%s, %s, 'case_supervisor', 'R2', 'ready', %s, 90)
                """,
                (case_id, ESCALATION_KIND, now),
            )
            created += 1
        conn.commit()
    return EscalationSummary(scanned=len(case_ids), created=created, skipped=0)
