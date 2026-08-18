# Task 9 Report: Policy-Derived Queue, Leases, Takeover, Recusal, And Escalation

## Status: COMPLETE

`agent/cases/work_control.py` provides the derived queue and every lease command.
`agent/cases/store.py` was not modified: the work-item reads and compare-and-set
writes are specific to this service, and threading them through the generic
transaction adapter would have added indirection without a second caller.

## The queue is a query, not a status

Order is computed from the work row, the case's promise clocks and the risk
class, never from a stored rank. That is what the review gate means by
transparent priority: nobody can move their own items up by writing a field, and
there is no throughput counter to game because none is stored. Ordering is
emergency first, then promise health (breached above at-risk above on track),
then risk class descending, then the oldest ready item. A test seeds one of each
and asserts the exact sequence.

An item leaves the queue while a live lease holds it and returns the moment that
lease expires, so an operator who walks away cannot strand work.

## One assignee, always bounded

Every lease command is a single compare-and-set on the work item's revision.
Claim requires the caller's expected revision and only succeeds when the row is
unassigned, its lease has expired, or it is not claimed — expressed in one
`UPDATE ... WHERE ... RETURNING`, so two racing operators cannot both believe
they own it. The concurrency suite races two claims through a barrier and asserts
exactly one winner, one rejection, and a revision that moved exactly once; it
also races a reclaim after expiry, and checks the loser cannot heartbeat the
winner's lease.

Heartbeat extends only a live lease owned by the same actor, so it can never
revive an expired one. Lease duration comes from policy
(`lease_duration_seconds`), not from a constant in this module.

## Authority

Claiming needs `cases:work`. R2 and R3 additionally need `cases:high_risk`.
Takeover needs `case.supervisor` and a stated reason, and — deliberately — the
risk check still runs afterwards: seniority reassigns work, it does not grant
clearance the risk rules withhold. A test pins that a supervisor without high-risk
clearance is refused an R3 takeover, which is exactly the "no supervisor bypass"
the review gate asks for.

Recusal cancels the item, opens a replacement for somebody else, and records the
recused actor in the audit event; that actor is then refused the replacement.
Completion requires a live lease held by the caller and a result reference.

## Schema honoured, no new columns

Migration 080 stays locked. `case_work_items` has no result, completion or
recusal column, so the result reference and the recused actor are recorded in the
audit event that the transition is proved by, and recusal is expressed as
`cancelled` plus a fresh `ready` row rather than an invented state.

## Escalation only ever adds work

A breached clock on an open case raises exactly one escalation work item. The
scan is idempotent — a case that already carries an open escalation is skipped —
and it never edits the case it escalates: a test snapshots phase, activity and
revision before the scan and asserts they are byte-identical afterwards.

## Verification

Plan Step 5 command: `133 passed`. The two new suites pass twice in a row, so the
durable rows they create do not leak between runs. Case regression across public
API, outbox, contact, create, service, store and database: `377 passed,
1 xfailed`. Ruff clean; `git diff --check` exit 0.

Not independently reviewed.
