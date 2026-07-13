# Account and Control-Plane Security Design

> STATUS: implemented and verified

## Goal

Close the immediate account/control-plane findings `REVIEW-01-005`,
`REVIEW-01-006`, and `REVIEW-08-001` without changing the public admin or
authentication response shapes, adding a database migration, or weakening the
existing request audit trail.

The resulting invariants are:

- an administrative actor may change account availability only for a target
  whose role is strictly lower than the actor's role;
- the server-side admin key remains the explicit root authority;
- a rejected single or bulk hierarchy operation performs no target account,
  target session, or moderation-log mutation;
- password recovery atomically changes the password and revokes existing
  sessions and pending second-factor challenges; and
- authentication work authorized against the pre-reset password state cannot
  create a session after the reset boundary.

## Findings

### Higher-role single ban

`POST /admin/users/{user_id}/ban` checks only self-targeting and existence. An
`admin` can therefore deactivate a `superadmin` and delete all of the target's
sessions.

### Higher-role bulk ban

`POST /admin/users/bulk-ban` repeats the missing hierarchy check for every
target. One request can deactivate multiple superior recovery accounts. The
current loop can also mutate earlier targets before discovering a later
problem if a hierarchy check is added naively inside the mutation loop.

### Post-reset session resurrection

`POST /auth/reset-password-otp` changes the password and deletes
`user_sessions`, but leaves `pending_2fa` rows usable. A challenge issued under
the old password state can later reach `_finish_login` and create a new
session.

Deleting `pending_2fa` alone closes the sequential reproduction but not both
concurrent variants:

1. primary-factor verification can finish before reset and insert its challenge
   after the reset-side delete; and
2. a verifier can consume a challenge immediately before reset, then insert its
   session immediately after the reset-side session delete.

## Considered Approaches

### 1. Endpoint-local checks and pending-row deletion

Add role checks directly to the two ban handlers and add one
`DELETE FROM pending_2fa` statement to password reset.

This is the smallest patch, but it duplicates hierarchy policy, risks partial
bulk mutation, and leaves the two concurrency windows described above.

### 2. Shared transactional guards and credential snapshots (selected)

Centralize role comparison, lock target account rows before hierarchy checks,
validate a complete bulk request before mutation, and serialize password-state
changes against challenge/session creation by comparing the password hash
snapshot used for primary authentication.

This closes the validated findings and their immediate races without a schema
change. It follows the existing connection/transaction model and keeps rollback
simple.

### 3. Persistent authentication generation

Add an `auth_version` column to users, pending challenges, and sessions, then
increment it during password recovery and validate it at every authentication
boundary.

This is a useful future architecture if more credential types are added, but it
requires a migration, compatibility handling, and broader session middleware
changes that are disproportionate to Workstream 4.

## Administrative Role Boundary

### Canonical rank policy

`agent/admin.py` owns one explicit role-rank mapping:

| Role | Rank |
| --- | ---: |
| `user` | 0 |
| `moderator` | 1 |
| `admin` | 2 |
| `superadmin` | 3 |

An authenticated user actor may manage a target only when the actor rank is
strictly greater than the target rank. Consequently:

- `admin` may ban `moderator` and `user`, but not another `admin` or a
  `superadmin`;
- `superadmin` may ban `admin`, `moderator`, and `user`, but not another
  `superadmin`;
- self-targeting remains a `400` error even if a future role definition would
  otherwise pass; and
- the admin key, represented by `request.state.admin_user is None` after
  successful key authentication, bypasses rank comparison as the root actor.

Missing, empty, or unknown actor/target roles fail closed with `403`. The helper
does not infer rank from arbitrary scopes because a custom scope must not
silently grant account-control authority equivalent to a higher role.

### Shared guard

A focused helper accepts the request-scoped actor and a locked target row. It
normalizes roles, applies the root-key exception, and raises the existing
FastAPI `HTTPException` shape on denial.

Handlers use `request.state.admin_user`, which was established by
`require_admin`, rather than performing a second current-user lookup. This
keeps the actor identity and scopes consistent with the dependency that
authorized the request.

## Single-Ban Transaction

The single-ban handler performs these steps:

1. require PostgreSQL and validate the target identifier;
2. reject self-targeting before entering the mutation path;
3. select `id`, `role`, and `is_active` for the target with `FOR UPDATE`;
4. return `404` when the target does not exist;
5. run the shared actor-target hierarchy guard;
6. only after the guard passes, deactivate the target and delete its sessions
   on the same connection; and
7. write the moderation action log only after the transaction succeeds.

The row lock prevents a concurrent role change from moving the target above the
actor between authorization and mutation. Existing idempotent behavior for an
already inactive target remains unchanged.

## Bulk-Ban Transaction

Bulk ban is all-or-nothing for every existing target in the request:

1. validate every identifier and reject self-targeting before database writes;
2. deduplicate identifiers while preserving first-occurrence response order;
3. lock existing target rows in deterministic identifier order;
4. preserve the current compatibility behavior of skipping missing targets;
5. apply the shared hierarchy guard to every locked existing target;
6. if any target is forbidden, raise `403` before any account or session
   mutation; and
7. otherwise deactivate eligible targets and delete their sessions in the same
   transaction, then emit moderation logs after commit.

Deterministic locking reduces deadlock risk for overlapping bulk requests.
Separating the validation pass from the mutation pass makes zero partial target
mutation explicit rather than depending only on exception rollback.

## Password-Reset Boundary

### Atomic reset

`reset_password_otp` keeps OTP consumption, user lookup, password update,
session revocation, and challenge revocation on one connection. The user row is
selected with `FOR UPDATE` before credential mutation.

After OTP validation succeeds, the transaction:

1. locks and loads the active user by normalized phone;
2. hashes the new password;
3. updates `users.password_hash`;
4. deletes every `user_sessions` row for the user; and
5. deletes every `pending_2fa` row for the user.

The response and post-reset login-history/streak/achievement behavior remain
unchanged. Trusted-device rows are not pending authentication challenges and
remain out of scope; they still require a valid primary factor after reset.

### Credential snapshot at challenge creation

Both OTP and password login already load a user record before deciding whether
to issue a 2FA challenge. `_create_pending_2fa` receives that record's
`password_hash` as the expected credential snapshot.

Before inserting a challenge, it locks the user row and compares the current
password hash with the expected snapshot using constant-time comparison for
non-null strings. If password recovery changed the credential state in between,
the helper inserts nothing and the login returns `401` instructing the caller
to authenticate again.

If a legacy-password rehash occurs during password login, the in-memory user
snapshot is updated to the newly stored hash before challenge creation.

This gives two safe serial orders:

- challenge creation commits first, then reset locks the user and deletes the
  challenge; or
- reset commits first, then challenge creation observes a snapshot mismatch and
  refuses the insert.

### Credential snapshot at session creation

`_finish_login` passes the loaded user's password-hash snapshot to
`_create_session_atomic`. Session creation locks the user row and verifies that
the account is active, not deleted, and still has the expected credential
snapshot before inserting `user_sessions` and enforcing the concurrent-session
cap.

This serializes every direct or post-2FA session insertion against password
reset:

- session creation commits first, then reset deletes that session; or
- reset commits first, then session creation detects the stale snapshot and
  inserts no session.

For a pre-reset 2FA verifier, the user snapshot is loaded before the challenge
is atomically consumed. Even if consumption wins just before reset, the stale
snapshot prevents a post-reset session from being created.

## Error and Audit Semantics

- Self-ban remains `400`.
- Missing single-ban targets remain `404`.
- Unknown or same/higher role targets return `403` without revealing a more
  detailed hierarchy oracle.
- A mixed bulk request containing any forbidden existing target returns `403`
  and mutates none of its targets.
- Missing bulk targets continue to be skipped for compatibility.
- Stale credential snapshots return `401`; clients must restart login.
- Request-level admin security auditing performed by `require_admin` remains
  intact, including for rejected mutations.
- A rejected hierarchy operation does not update `users`, delete
  `user_sessions`, or write `_log_mod_action`. The request audit event is an
  intentional security record, not a target-account mutation.
- No raw password hash, challenge token, session token, phone number, or TOTP
  value is added to logs or response payloads.

## Verification Strategy

### Role-policy tests

- cover every canonical actor-target rank combination;
- prove equal-rank and higher-rank targets are denied;
- prove unknown roles fail closed; and
- prove the admin-key root path remains allowed.

### Single-ban tests

- admin-to-superadmin and admin-to-admin return `403`;
- denied operations execute no account update, session delete, or moderation
  log;
- superadmin-to-admin and admin-key-to-superadmin retain successful behavior;
- target role is read under `FOR UPDATE`; and
- existing self-ban, missing-target, session-revocation, and audit tests remain
  green.

### Bulk-ban tests

- a mixed lower-role/superadmin request fails atomically with zero target
  writes;
- a mixed lower-role/peer-admin request also fails atomically;
- successful requests skip missing IDs and return unique existing targets in
  first-occurrence order;
- every existing target is validated before the first mutation; and
- row locking is deterministic.

### Password-reset and concurrency tests

- reset deletes `user_sessions` and `pending_2fa` in the password-update
  transaction;
- challenge creation rejects a stale expected password hash and performs no
  insert;
- session creation rejects a stale expected password hash and performs no
  insert;
- challenge-before-reset is deleted;
- reset-before-challenge causes snapshot rejection;
- session-before-reset is deleted;
- reset-before-session causes snapshot rejection; and
- the existing atomic challenge-consumption, OTP, login, session-cap, and
  trusted-device tests remain green.

Tests use deterministic fake database boundaries for RED/GREEN behavior and SQL
ordering. PostgreSQL-only integration tests run when the repository's test
database is available and otherwise remain explicitly skipped under the
existing project convention.

## Completion Gates

- focused Workstream 4 tests pass;
- owning admin/auth regression suites pass;
- full backend pytest passes with no new failure or flake;
- Ruff, `py_compile`, and `git diff --check` pass;
- denied hierarchy paths show zero target account/session/moderation-log side
  effects;
- stale pre-reset authentication work cannot create a post-reset session; and
- independent spec and code-quality review report no open Important finding.

## Rollback

Revert the Workstream 4 code commits together while retaining the new
regression tests for review. No migration or stored-data rewrite is introduced.
Rollback restores the earlier endpoint behavior but must not be presented as a
security-compatible long-term state because it reopens the three validated
findings.

## Non-Goals

- No redesign of role assignment, unban, account deletion, or arbitrary custom
  scope policy.
- No persistent `auth_version` migration in this workstream.
- No forced deletion of trusted devices or disabling of the user's configured
  2FA secret during password reset.
- No frontend redesign; existing error handling consumes the standard FastAPI
  error shape.
- No merge, push, deployment, secret rotation, or production data operation.

## Implementation Evidence

The verified implementation and test HEAD before this closure-only documentation
update is `389eccfc01d524fdf85c53566851476f2788d2ce` on branch
`codex/account-control-plane`.

Production correctness was implemented by these commits:

- `ea323d0` centralizes the account role hierarchy;
- `c8ba17b` enforces hierarchy before single-user ban mutation;
- `4ceff8c` makes bulk bans validation-first, atomic, and deterministically
  locked;
- `6c316c2` binds pending challenges and sessions to credential snapshots;
- `eb062f7` closes the legacy-password rehash/reset compare-and-swap race;
- `b43b3d5` keeps trusted-device touch failure best-effort and ordered after the
  credential boundary; and
- `c91cb6f` makes OTP consumption, password change, session revocation, and
  pending-challenge revocation one transaction.

Regression and verification coverage was completed by `8b33266`, `8c4972a`,
`3b405e2`, `7a77d06`, and the test-only PostgreSQL commit `389eccf`. The final
PostgreSQL commit does not change production behavior; it proves the existing
transaction design against real PostgreSQL MVCC, row locks, predicate rechecks,
deadlock behavior, and rollback.

Fresh verification evidence:

- the pre-PostgreSQL focused Workstream set passed with `1358 passed, 5 skipped,
  1 warning`;
- the pre-PostgreSQL full backend passed with `6168 passed, 39 skipped, 78
  deselected, 1 xfailed, 1 warning`;
- with the opt-in PostgreSQL URL absent, the final focused control-plane run
  passed with `66 passed, 8 skipped`;
- the final full backend run passed with `6168 passed, 47 skipped, 78 deselected,
  1 xfailed, 1 warning`; the eight additional skips are exactly the opt-in
  PostgreSQL module;
- a fresh disposable PostgreSQL 16.4 cluster, bound only to localhost with the
  database `account_control_plane_test`, passed all eight PostgreSQL race and
  rollback tests in `9.10s` and was stopped and removed afterward;
- `ACCOUNT_CONTROL_PLANE_TEST_DATABASE_URL` is required, unsafe database names
  are rejected unless the explicit second opt-in is set, and event/future plus
  server-side timeouts bound lock and failure waits; and
- Ruff, `py_compile`, and `git diff --check` passed across every Python file
  touched by the Workstream 4 commits.

The final specification review reported `✅ Final spec compliant`. The final
quality re-review found no Critical or Important issue and approved closure
documentation. These reviews and the real PostgreSQL tests support the
production correctness claims above; the opt-in integration module is
additional verification coverage, not the source of the fixes.

## Verified Residuals

- Bulk ban performs at most 50 individual `id::text` row-lock queries. This is
  correctness-safe, bounded by the request model, and avoids deadlock through
  sorted lock order, but a future one-query locking optimization would reduce
  round trips.
- The real PostgreSQL suite is opt-in and is not yet wired into continuous
  integration. Run it serially in a dedicated CI or scheduled job with a
  disposable database.
- A small set of regressions intentionally inspects AST/source ordering. That
  coupling is maintenance debt and can be replaced opportunistically with
  behavior-level seams without weakening current coverage.
- The existing Starlette/httpx deprecation warning remains unchanged and is not
  introduced by this workstream.

Rollback remains commit-based: revert the production Workstream 4 commits
together while retaining the regression tests for diagnosis. No migration,
stored-data rewrite, merge, push, deployment, or production data operation is
part of this closure.
