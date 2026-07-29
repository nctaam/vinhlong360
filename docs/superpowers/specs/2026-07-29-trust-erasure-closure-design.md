# Trust And Erasure Closure Design

> STATUS (2026-07-29): active - Runtime Trust Boundary implementation is complete and locally verified; Verified Erasure Lifecycle remains pending, so the overall design is not complete.

## Goal

Close the highest-value trust and personal-data lifecycle gaps without changing
the existing FastAPI, Nuxt, and PostgreSQL architecture: enforce mandatory PII
boundaries across chat and streaming, make public feedback telemetry-only and
abuse-bounded, and erase or anonymize all user-linked data no later than the
approved 30-day account-deletion lifecycle.

## Validated Current Failures

The design responds to behavior reproduced or confirmed in the current tree:

1. `guardrails.check_input()` returns a PII-masked message, but both `/chat` and
   `/chat/stream` continue using the original request message. Raw input can
   reach providers, history, exact and semantic caches, analytics, cost
   attribution, optimizer records, logs, cold memory, memory graphs, and memory
   extraction.
2. Non-stream output is persisted to memory and analytics before output PII
   masking. Streaming emits raw chunks before the final output check, so a
   complete-response check cannot retract leaked content.
3. Public `/feedback` trusts client-supplied `user_id`, `session_id`, `query`,
   and `entity_id`. It writes cold-memory feedback, converts answer-quality
   votes into favorites or dislikes, and calls a learning path that directly
   changes shared entity confidence in both `web/data.json` and the database.
4. The published privacy copy states 20 days while runtime config, API behavior,
   and scheduler SQL use 30 days. The approved policy is now 30 days from the
   account-deletion request for all user-linked personal or pseudonymous data.
5. Account cleanup deletes all due users in one transaction. A restrictive user
   foreign key, including the current `entity_claims.claimant_id`, can roll back
   the entire batch indefinitely.
6. User-linked data also exists outside PostgreSQL in cold memory, memory graph,
   semantic cache, analytics, feedback, cost, optimizer, and related file-backed
   stores. Current hard deletion does not purge or verify these stores.
7. Multiple audit and actor foreign keys use the default restrictive delete
   action, and several user references are polymorphic text or JSON rather than
   database foreign keys.

## Scope Boundary

This design includes three coupled workstreams:

- runtime privacy boundaries for user input, history, tool output, provider
  output, caches, persistence sinks, and SSE;
- receipt-bound, telemetry-only feedback with replay and abuse controls;
- a verified 30-day account erasure lifecycle covering PostgreSQL and external
  personal-data stores.

The work remains inside the current monolith. It does not add Redis, Kafka, a
new worker service, a paid anti-abuse service, or an external data processor.

Production activation, production data backup, applying the historical scrub,
deploying, pushing, or changing real secrets are separate approval-gated
operations. Codex Security remains deferred and is not part of this design.

## Approved Product And Data Policy

1. Active accounts retain the data required to provide the service. There is no
   rolling 30-day TTL for active-account core data.
2. The 30-day period starts when the user requests account deletion.
3. The account is disabled and credentials are revoked immediately.
4. Recovery is allowed only while `now < erasure_due_at`.
5. By the erasure lifecycle deadline, all personal or pseudonymous data linked
   to the account must be deleted or irreversibly anonymized.
6. Deidentified aggregate statistics may remain when they contain no stable
   subject identifier, raw user text, or unique combination that can reasonably
   be traced to a person.
7. Pending entity claims are deleted. Completed claims retain only the entity,
   decision status, and timestamps. Claimant, reviewer, contact details,
   evidence, and every free-text field are cleared completely.
8. Chat thumbs-up or thumbs-down means response quality only. It never means
   favorite, dislike, visit intent, or permission to change shared knowledge.
9. Personalization remains driven by explicit product actions such as save,
   want-to-visit, visited, or follow.
10. Anonymous and authenticated feedback are both telemetry-only.

## Architecture

### Machine-readable policy authority

Create `config/privacy-policy.json` as the committed policy source shared by the
backend, frontend legal copy, and tests. Its initial contract is:

```json
{
  "accountErasureDeadlineDays": 30,
  "recoveryEnabledDuringGracePeriod": true,
  "feedbackMode": "telemetry_only",
  "feedbackReceiptTtlHours": 24,
  "retainDeidentifiedAggregates": true
}
```

`agent/config.py` exposes the parsed values rather than defining an independent
deletion duration. `web-nuxt/utils/legalContent.ts` renders the same committed
duration. In production, a runtime override that contradicts the committed
public policy causes the readiness check to fail.

### Mandatory privacy boundary

Add `agent/privacy_boundary.py`. This module is required for chat availability;
it is not an optional `HAS_*` enhancement.

Its primary immutable input type is:

```python
@dataclass(frozen=True)
class SafeHistoryItem:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class SafeChatInput:
    message: str
    history: tuple[SafeHistoryItem, ...]
    redaction_types: tuple[str, ...]
```

`prepare_chat_input(message, history)` validates and redacts the current user
message and every supplied history item. `SafeHistoryItem` contains only an
allowlisted conversational role and redacted content; unknown roles and extra
history fields are rejected. Once this boundary returns, route code must not
read `req.message` or the raw request history again. A source-level test enforces
this invariant in both POST and SSE routes.

The boundary classifies data provenance:

- `private_user_data`: always redact;
- `untrusted_external`: always redact before prompt construction or storage;
- `verified_public_contact`: allow only an exact value loaded from a published
  database field and attached to the current response context;
- provider-generated or unmatched contact data: redact.

This permits verified public business contact information while preventing a
model or external tool from inventing a phone number or email address and having
it treated as trusted contact data.

The boundary covers user messages, history, external tool results, web-search
results, provider output, cache entries read from older namespaces, and client
feedback metadata. Sink adapters add defense in depth: provider calls reject
unapproved content, structured logging applies a final redaction processor, and
personal persistence APIs accept only boundary-produced values.

### Streaming redaction

`StreamingPIIRedactor` holds a bounded suffix at least as long as the maximum
supported PII pattern span. It detects email, phone, government ID, bank account,
passport, and supported secret patterns that cross provider chunk boundaries.
Only confirmed-safe content is emitted. The unverified suffix is never flushed
after an exception or cancellation.

Streaming PII redaction is separate from full-response factuality checks. The
streaming boundary protects confidentiality in real time; the assembled safe
response can still undergo the existing final quality and factuality checks.

### Owner write gate

Add a central owner admission boundary:

```python
owner_write_gate.assert_writable(owner_key)
```

Every persistent owner-linked write in memory, graph, personalized cache,
feedback receipt ownership, cost attribution, optimizer data, and similar stores
must pass this gate. A deletion request blocks the owner immediately. Store-level
tests and a source scanner prevent new personal-store write paths from bypassing
the gate.

The gate is backed by durable account state, not only process memory. After a
restart, an account with `deleted_at IS NOT NULL` remains blocked.

### Feedback policy

Add `agent/feedback_policy.py`. Successful non-stream, cached, fallback, and SSE
assistant responses may receive a new opaque feedback receipt. The receipt is a
random high-entropy token; PostgreSQL stores only its digest.

The public feedback request becomes:

```json
{
  "receipt": "opaque-token",
  "rating": 1
}
```

The model uses `extra="forbid"`. Client-supplied `user_id`, `session_id`,
`query`, and `entity_id` are not accepted.

Receipt issuance binds the receipt to the resolved owner and actual assistant
turn. Authenticated receipts may hold a nullable `user_id` foreign key with
`ON DELETE CASCADE`; anonymous receipts hold only a keyed owner digest. Neither
receipt records nor feedback rollups store raw query text, response text, entity
IDs, or raw session identifiers.

Before receipt-table access, the endpoint consumes the in-memory IP budget for
every request, resolves the owner, consumes the owner budget for every attempt,
and then applies cheap token-format validation. Initial limits are 30 feedback
requests per IP per hour and 20 feedback attempts per resolved owner per hour.
Malformed, invalid, expired, wrong-owner, replayed, and accepted attempts all
consume the applicable pre-database budget. The existing chat limiter also
bounds the number of valid receipts an attacker can mint. Anonymous and
authenticated aggregates remain separate; anonymous aggregate data is treated
as untrusted telemetry and never drives an automatic product mutation.

Receipt consumption is transactional. It locks the receipt, validates owner,
expiry, and prior use, updates a daily aggregate with an atomic upsert, records
the rating and use time, clears direct owner columns, and commits. A keyed
one-way owner-binding digest remains only until receipt expiry so a concurrent
replay can still validate ownership: the same rating is idempotent and a
conflicting rating is rejected. Invalid, expired, wrong-owner, and unavailable
receipts use a common public error shape so the endpoint does not become an
ownership oracle. Rate limiting returns `429` with `Retry-After`.

Receipt creation is non-critical. If the receipt store is unavailable, chat
still succeeds without a receipt. Privacy-boundary failure is critical and fails
closed.

The endpoint must not call `memory_manager.feedback()`, `learn_loop`, entity
confidence mutation, `data.json` mutation, or any personalization sink.

### Lifecycle registry

Add a registry of every user-linked store:

```python
DataStorePolicy(
    name="cold-memory",
    classification="personal",
    purge=memory_manager.purge_owner,
    verify=memory_manager.verify_owner_absent,
)
```

Each `personal` or `pseudonymous` store must provide:

- `purge_owner(owner_key) -> PurgeResult`;
- `verify_owner_absent(owner_key) -> VerificationResult`;
- a declared retention classification and erasure action.

Aggregate stores declare why they are not subject-linked and are retained only
if they contain no raw user content or stable owner reference. Registry
completeness is a readiness and CI invariant. Adding a personal store without a
policy adapter fails tests.

### Erasure orchestrator

Add `agent/erasure.py`. Scheduler code invokes the orchestrator and contains no
inline deletion policy SQL.

The lifecycle has three phases:

1. **Immediate quarantine:** disable the account, revoke credentials and active
   challenges, block owner writes, purge hot memory, active personalized cache,
   in-flight semantic leases, and unused feedback receipts.
2. **Recoverable grace:** retain the core profile and UGC required for account
   recovery while keeping the owner disabled and write-blocked.
3. **Verified hard erasure:** purge and verify all external personal stores,
   then anonymize or delete database records and hard-delete the user.

`erase_due_accounts(now, limit)` processes users independently. The scheduler
task is single-flight, runs at startup for catch-up, then every five minutes, and
uses a batch size of 50. One user failure does not roll back successful users or
prevent later users from being attempted.

`erase_account(user_id)` performs external purge before the final database
transaction. If the process crashes before database deletion, the user row
remains due and the idempotent purge repeats. If database deletion commits,
external purge has already been verified.

Recovery and erasure both lock the user row. Recovery is allowed only when
`now < erasure_due_at`. At or after the deadline, recovery fails. The scheduler
rechecks deletion state and deadline while holding the lock before beginning the
owner purge. Once final erasure has begun, the account cannot be resurrected.

Time comparisons use UTC and an injectable clock for deterministic boundary and
race tests.

## Data Flow

### Non-stream chat

1. Parse the bounded request and resolve the authenticated or signed anonymous
   owner.
2. Produce `SafeChatInput` before cache lookup, prompt construction, memory
   hydration, analytics, or provider access.
3. Use only safe message and history for RAG, tools, cache, provider, quality,
   memory, cost, optimizer, and logging.
4. Redact provider output before any persistence sink.
5. Persist and return only the safe reply.
6. Best-effort issue a feedback receipt for the delivered assistant turn.

### Streaming chat

1. Apply the same input boundary before cache or provider access.
2. Redact every provider chunk through the rolling streaming boundary.
3. Emit only confirmed-safe chunks.
4. Persist only the assembled safe output after stream completion.
5. Attach the feedback receipt to the terminal `done` event.
6. On cancellation or redactor failure, discard the unverified suffix and close
   with a generic safe error event.

### Feedback

1. Consume the IP and resolved-owner rate-limit budgets.
2. Validate token shape, then hash the token and lock its receipt row.
3. Validate current owner, 24-hour expiry, and used state.
4. Atomically update the appropriate authenticated or anonymous daily rollup.
5. Record rating and use time and clear direct owner columns.
6. Commit without touching personal memory or shared knowledge.

### Deletion request

In one account transaction, the endpoint sets `deleted_at`, calculates and stores
`erasure_due_at = requested_at + 30 days`, disables the account, and revokes all
sessions and active authentication challenges. After commit, it blocks owner
writes and purges immediate-phase ephemeral stores. The response returns the
exact deadline and `grace_days=30`.

If immediate external quarantine partially fails, the account remains disabled;
the failure is recorded for retry and cannot re-enable credentials.

### Recovery

Recovery locks the account row, verifies the deadline has not arrived, clears
deletion and erasure metadata, and commits before creating a new session. Hot
memory and cache removed during immediate quarantine are not reconstructed.

### Hard erasure

For each due user:

1. lock and recheck the account;
2. run every required personal-store purge adapter;
3. verify every adapter reports no residual owner data;
4. if any adapter fails, record a stable error code and retain the user for
   retry;
5. otherwise run one database transaction for structured cleanup,
   anonymization, and user deletion;
6. verify the user row and unapproved restrictive references are absent;
7. record only deidentified operational metrics.

## Data Model

### User erasure state

Add nullable or bounded metadata to `users`:

```sql
erasure_due_at          TIMESTAMPTZ,
erasure_attempt_count   INTEGER NOT NULL DEFAULT 0,
erasure_last_attempt_at TIMESTAMPTZ,
erasure_last_error_code TEXT
```

`erasure_last_error_code` accepts only stable codes such as
`STORE_UNAVAILABLE`, `RESIDUAL_DATA`, `DB_CONSTRAINT`, and `VERIFY_FAILED`; it
never stores a raw exception or subject content.

### Feedback receipts

Add a small PostgreSQL control table with:

- receipt ID and unique token digest;
- owner kind;
- nullable authenticated user foreign key with `ON DELETE CASCADE`;
- nullable anonymous owner digest;
- keyed one-way owner-binding digest retained only through receipt expiry;
- assistant-turn digest;
- safe model variant and tool bucket dimensions;
- nullable rating;
- creation, expiry, and use timestamps.

Before first use, checks require exactly one direct owner representation
(`user_id` or anonymous owner digest) plus the owner-binding digest. After use,
both direct owner columns may be null only when `used_at IS NOT NULL`; the
binding digest remains solely for owner-validated replay protection. The whole
receipt row, including that digest, is deleted at expiry. Raw query, reply,
session ID, and entity ID are forbidden columns.

Add `feedback_daily_rollups` keyed by day, owner kind, model variant, and bounded
tool bucket. It stores only positive and negative counters and uses atomic
`INSERT ... ON CONFLICT DO UPDATE` increments.

## Retention And Erasure Matrix

| Classification | Examples | Hard-erasure action |
| --- | --- | --- |
| Direct profile | users, privacy settings, consent, 2FA | delete |
| Owned UGC | posts, comments, review responses | delete/cascade |
| Preferences | saves, visits, likes, bookmarks, follows, collections | delete |
| Credentials | sessions, OTP, trusted devices, pending receipts | delete |
| Personal memory | hot/cold memory, semantic facts, graph nodes | purge and verify |
| Personalized cache | exact/semantic owner namespaces | purge and verify |
| Pending workflows | pending claims and pending user appeals | delete |
| Completed claim | claim decision and timestamps | anonymize |
| Audit actor | moderator, reviewer, editor, featured-by | set actor null; retain action |
| Personal telemetry | owner/session-linked cost or optimizer records | delete |
| Deidentified telemetry | daily counters and bounded latency/tool buckets | retain |
| Operational log | request/run ID and stable error code only | retain |
| Legacy raw text | old analytics, cost, feedback, memory files | backup then scrub |

Free-text audit fields retained after actor anonymization pass through PII
redaction. They do not retain phone, email, evidence, or user-authored secrets.
This general audit rule does not apply to completed entity claims, whose
contact, evidence, and free-text fields are cleared completely.

## Database Reference Policy

User-owned foreign keys use `ON DELETE CASCADE`. Actor-only audit foreign keys
use nullable columns with `ON DELETE SET NULL`. Special workflows use explicit
orchestrator policy.

Initial special handling includes:

- pending entity claim: delete;
- completed entity claim: null claimant and reviewer; clear phone, email,
  evidence, rejection reason, reviewer notes, and every other free-text field;
  retain only entity, status, and created/reviewed timestamps;
- pending moderation appeal owned by the user: delete;
- completed audit decision: retain decision and timestamp, null reviewer;
- review response owned by the user: delete/cascade;
- edit/moderation/featured/announcement/collection/admin-note actor reference:
  set null while retaining the non-personal action record.

A PostgreSQL integration test introspects `pg_constraint` and rejects any new
foreign key to `users` whose action is not registered as cascade, set-null, or a
named special policy.

Polymorphic and JSON references are also registered. Initial coverage includes:

- `follows.target_type='user'` plus text `target_id`;
- `reports.target_type='user'` plus text `target_id`;
- notification and audit `ref_type`/`ref_id` pairs;
- post and comment structured mention arrays;
- memory graph nodes and file-backed owner indexes.

Cleanup targets structured fields exactly. It does not blindly replace UUID-like
text throughout arbitrary user content.

## Error Handling And Availability

- Privacy input or streaming redaction failure fails closed with a generic safe
  response and never logs the raw content.
- Provider, cache, memory, analytics, and cost sinks receive no raw fallback.
- Receipt issuance failure does not fail chat; feedback is omitted for that
  response.
- Receipt consumption failure rolls back both use state and aggregate update.
- Invalid, expired, unavailable, and wrong-owner receipts use a common public
  unavailable response. Rate limits remain explicit `429` responses.
- Immediate account quarantine cannot fail open. Credential revocation and
  account disablement commit before best-effort external ephemeral purge.
- Hard erasure never deletes the database subject while a required external
  store reports residual data.
- Per-user failures increment bounded attempt metadata and do not stop the batch.
- A user past `erasure_due_at` but not fully erased increments an overdue metric.

## Observability

Add deidentified metrics:

- `privacy_redactions_total{source,type}`;
- `privacy_boundary_failures_total{stage}`;
- `feedback_receipts_issued_total`;
- `feedback_rejections_total{reason}`;
- `feedback_rollup_total{owner_kind,rating}`;
- `erasure_due_total`;
- `erasure_completed_total`;
- `erasure_failed_total{code}`;
- `erasure_overdue_total`.

Logs may include request ID, erasure run ID, store name, and stable error code.
They must not include user ID, owner key, query, reply, receipt token, or raw
exception text that may contain PII.

Readiness requires the privacy policy, mandatory privacy boundary, lifecycle
registry completeness, and expected schema version. Feedback-store outage is a
degraded capability rather than a backend readiness failure. Missing privacy or
erasure policy is fail-closed.

## Testing

All production behavior changes follow strict red-green-refactor TDD. Tests must
observe the intended failure before implementation.

### Runtime trust boundary

- current message and every history item redact phone and email sentinels;
- untrusted tool output is redacted before prompt construction;
- an exact verified database contact may pass while an invented provider contact
  is redacted;
- PII split across multiple SSE chunks never appears on the transport;
- cancellation or redactor failure never flushes the unverified suffix;
- provider arguments, cache, cold memory, graph, analytics, optimizer, cost,
  feedback, and logs contain no sentinel PII;
- output is redacted before every persistence sink;
- POST, cached POST, fallback, and SSE responses receive receipts when the store
  is available;
- receipt-store failure preserves successful chat without a receipt.

Critical POST and SSE assertions run through real ASGI transport, not only helper
calls.

### Feedback policy

- valid receipt consumption updates exactly one aggregate;
- malformed, fake, expired, wrong-owner, and unavailable receipts are rejected;
- concurrent same-rating replay is idempotent and counted once;
- conflicting replay is rejected;
- IP and owner limits count invalid as well as accepted attempts and return the
  correct bounded behavior;
- anonymous and authenticated rollups remain separate;
- no feedback request calls memory, personalization, learning-loop, entity
  confidence, or `data.json` mutation;
- receipt rows and rollups contain no raw query, response, entity, or session
  content.

### Erasure lifecycle

- deletion request stores an exact 30-day deadline and revokes every credential;
- persistent owner writes fail immediately after deletion request;
- ephemeral personal stores purge during immediate quarantine;
- recovery before the deadline succeeds; recovery at or after the deadline
  fails;
- concurrent recovery and erasure produce one linearizable result;
- partial external purge remains retryable and idempotent;
- a residual store prevents database deletion;
- two due users are isolated when one user fails;
- pending claims delete and completed claims anonymize the exact approved fields;
- audit action survives with a null actor;
- structured text/JSON user references no longer contain a sentinel UUID;
- PostgreSQL introspection finds no unapproved restrictive user foreign key;
- every registered personal store reports zero residual data after success;
- deidentified aggregate data remains unchanged.

Schema, locking, concurrency, and delete-action claims require real PostgreSQL
tests. SQLite is not acceptable evidence for production UGC erasure behavior.

### Final verification

Each implementation task runs focused tests. The final gate includes affected
backend suites, PostgreSQL integration tests, frontend tests for legal copy and
feedback contract, Nuxt typecheck/build, repository hard checks, and the full
baseline with documented handling for any pre-existing timeout or known debt.

## Rollout

### Phase 1: additive schema

Add policy data, tables, nullable columns, indexes, and reviewed foreign-key
changes. Hard erasure remains disabled. Run schema replay and constraint
introspection before proceeding.

### Phase 2: runtime boundary and feedback

Enable the mandatory privacy boundary, update POST/SSE response contracts, and
update the embedded legacy feedback caller. The old client-controlled feedback
identity contract is rejected rather than retained as a state-changing fallback.

### Phase 3: erasure audit-only

Run startup and scheduled preflight in audit-only mode. Report due users,
external-store readiness, existing soft-deleted accounts, and the effect of
backfilling `erasure_due_at`. Do not delete production data.

### Phase 4: controlled activation

Activation requires a separate instruction and backup gate:

1. run `python scripts/backup_data.py`;
2. create the PostgreSQL backup required by the runbook;
3. run one due account with `limit=1`;
4. verify PostgreSQL and every external store;
5. only then enable normal batches.

### Phase 5: legacy scrub

The scrub tool defaults to dry-run, lists stores and affected records, requires
backup evidence, and needs an explicit `--apply`. It writes a before/after digest
manifest and re-runs PII scanning. Applying the scrub is not authorized by
approving this design.

## Compatibility

- The chat reply remains available when feedback receipt issuance fails.
- Chat JSON and SSE terminal events add an optional `feedback_receipt` field.
- The public feedback payload intentionally breaks the unsafe client identity
  contract and accepts only receipt plus rating.
- Existing explicit save, visit, follow, and related personalization behavior is
  unchanged.
- Account deletion continues to support OTP recovery during the approved grace
  period, now with a stored exact deadline.
- No external service or paid dependency is added.

## Implementation Plan Split

After final written-spec approval, create two independently executable plans:

1. **Runtime Trust Boundary:** shared policy, privacy envelope, source-aware
   redaction, sink defenses, streaming redactor, feedback receipts, abuse
   controls, aggregate-only telemetry, API/frontend contract tests.
2. **Verified Erasure Lifecycle:** account schema, owner write gate, lifecycle
   registry, external purge adapters, foreign-key and structured-reference
   policy, recovery/erasure locking, scheduler integration, audit-only rollout,
   and legacy scrub tooling.

Each plan uses strict TDD, small commits, a fresh implementation subagent per
task, and an independent review before the next task.

## Acceptance Criteria

1. Sentinel personal data never appears in provider inputs, emitted SSE, cache,
   memory, graph, analytics, optimizer, cost, feedback telemetry, or logs.
2. No public feedback can mutate a profile, favorites, dislikes, shared entity
   confidence, `data.json`, or the knowledge database.
3. Anonymous replay and spam are bounded by valid one-time receipts, chat limits,
   IP/owner limits, and separate untrusted aggregates.
4. The committed policy, API, scheduler, privacy copy, and tests agree on 30
   days from the account-deletion request.
5. Immediate quarantine blocks new personal writes and removes ephemeral owner
   data without preventing recovery of retained core data.
6. Successful hard erasure deletes or anonymizes all registered personal and
   pseudonymous data and preserves only approved deidentified aggregates.
7. A failed user cannot poison the remaining erasure batch.
8. Recovery and erasure are linearizable at the exact deadline.
9. PostgreSQL schema introspection and sentinel structured-reference tests prove
   no unapproved user dependency remains.
10. No production deletion, scrub, deploy, push, or secret change occurs without
    a separate explicit instruction.

## Non-Goals And Residual Risks

- This design does not make anonymous identity Sybil-proof. It contains the
  blast radius by requiring real response receipts, bounding issuance and
  consumption, separating anonymous aggregates, and prohibiting automatic
  product mutation.
- Verified public contact pass-through depends on the correctness of the
  database publication state. It does not authorize provider-generated contact
  data.
- Historical raw data remains a residual until the separately approved backup
  and scrub operation completes.
- A prolonged service or required-store outage can cause a policy breach by
  delaying deletion past `erasure_due_at`; it never extends or resets the
  deadline. Startup catch-up, five-minute single-flight scheduling, overdue
  metrics, and operational alerting reduce the risk and make any breach visible,
  but cannot guarantee execution while required infrastructure is unavailable.
- The design does not repair unrelated self-evolution, scheduler-wide task
  overlap, admin route decorator, Telegram delivery, cache stampede, or analytics
  lost-update findings except where this erasure task needs isolated single-
  flight behavior.
- The design does not add a new personalized "not interested" product action.
  Such an action requires its own UX and behavioral design.
