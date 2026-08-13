# Correction Case Pilot Implementation Plan

> STATUS: approved implementation plan; implementation has not started. Approval of this plan does not enable any runtime flag, mutate production data, publish an SLA, or authorize claim, account-recovery, or full safety workflow implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a production-shaped, flag-closed correction pilot that gives every valid intake a durable secure receipt, exposes a safe public status, supports assisted intake and policy-derived backstage work, and closes `corrected` only after an atomic entity change and verified public projection.

**Architecture:** Add a focused `agent/cases/` modular-monolith slice around the approved Canonical Case Kernel. PostgreSQL owns current snapshots, immutable transition/audit records, receipt capabilities, work leases, correction evidence/decisions/change sets, idempotency replay, and a transactional outbox. FastAPI exposes separate public and action-scoped AdminCP routers; Nuxt consumes one typed case contract. Live entity publication is isolated behind its own kill switch and a transaction-aware entity writer so entity mutation, provenance, case fulfillment, audit, and outbox commit together.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, PostgreSQL, psycopg2, cryptography/Fernet/HKDF, pytest, Hypothesis, Nuxt 3, Vue 3, TypeScript, Vitest, and the existing browser/accessibility gate scripts.

## Global Constraints

- The approved authority is `docs/superpowers/specs/2026-08-12-service-ownership-assisted-channels-design.md` under `docs/superpowers/specs/2026-08-11-nocturne-civic-whole-service-constitution-design.md`; implementation must not silently weaken either contract.
- Implement correction only. Claim, account recovery, and full safety workflows remain out of scope; `/lien-he` may route to their existing safe lanes but must not fabricate unavailable capability.
- PostgreSQL is required for Case Kernel runtime. Domain-policy tests remain database-independent; SQLite must fail closed with a stable `case_postgresql_required` problem detail when a case flag is enabled.
- All five runtime controls default to false: `CASE_KERNEL_ENABLED`, `CORRECTION_INTAKE_ENABLED`, `CORRECTION_ADMIN_ENABLED`, `CORRECTION_ASSISTED_ENABLED`, and `CORRECTION_PUBLICATION_ENABLED`.
- `config/case-service-policy.json` is the only pilot policy-structure authority. Its initial revision is `correction-pilot-v1`, requires the deploy-specific `CASE_SERVICE_OWNER_REF` to resolve to one individual actor record, sets non-public receipt/triage/update targets, and explicitly sets `public_resolution_sla_enabled` to false. The repository contains no alias/mailbox fallback owner.
- Initial internal targets are receipt commit within 5 seconds, triage within 24 hours, and a user-visible update at least every 72 hours. They are operational guardrails, not a public resolution promise.
- Every case still starts all four `PromiseClock` kinds: receipt, triage, update, and resolution. Resolution uses a risk-specific internal target from policy for operations/capacity measurement, but its due date/target is never rendered as a public SLA until a separately approved 28-day eligibility decision.
- In operating copy and tests these are explicitly the receipt clock, triage clock, update clock, and resolution clock; backlog/waiting never resets any clock lineage.
- Human reference uses `VL-COR-` plus 12 random Crockford Base32 symbols and one check symbol; it is non-secret and non-sequential. Receipt capability uses 32 random bytes encoded as 43 URL-safe characters and expires after 365 days unless rotated/revoked earlier. Only an HMAC-SHA-256 digest is durable. Access sessions expire after 15 minutes; encrypted idempotency replay expires after 24 hours.
- A dedicated `CASE_KERNEL_ENCRYPTION_KEY` is mandatory before any case flag may be enabled in production. No development fallback may pass production validation.
- `public_reference` is non-secret. Capability secrets never enter a URL/query string, server log, analytics event, notification body, referrer, localStorage, sessionStorage, or persisted DOM state.
- Case access uses a `Secure`, `HttpOnly`, `SameSite=Lax` cookie scoped to `/api/cases`; invalid, expired, revoked, and unknown credentials return the same non-enumerating problem detail.
- Every public case mutation that relies on the case-access cookie requires same-origin enforcement plus a double-submit `X-Case-CSRF` token bound to the access-session digest. Create and receipt exchange are credential POSTs without an existing case cookie; they require JSON content type, exact Origin/Sec-Fetch-Site policy, and rate limiting.
- Receipt commit precedes notification. Notification is an at-least-once outbox side effect whose consumer re-checks consent, contact verification, revocation, and privilege immediately before delivery.
- Current case state is a transactional snapshot plus immutable transition ledger, not event sourcing. Every mutation requires `expected_revision`; closed cases never reopen, and review creates a linked `ReviewCase`.
- `accepted` is a decision; `published` is a public projection state. No API or UI copy may render accepted as publicly updated.
- Correction uses field-level `CorrectionItem`, evidence E0-E4, risk R0-R3, immutable `CorrectionChangeSet`, maker-checker for R2/R3, inverse-patch rollback, and fail-closed revision conflict handling.
- `updatedAt` changes only when entity content changes. `verifiedAt` changes only after authorized verification activity.
- No generic terminal `resolved`, `dismissed`, or `Da xu ly` outcome is permitted. Correction terminal outcomes are exactly `corrected`, `confirmed_current`, `insufficient_evidence`, `out_of_scope`, `duplicate_linked`, `unable_to_verify`, and `withdrawn_by_requester`.
- No call recording in the pilot. Assisted correction stores scoped consent, read-back confirmation, channel, operator, and authority audit; operators never request or enter passwords, OTPs, recovery codes, or equivalent secrets.
- `CORRECTION_ASSISTED_ENABLED` may be true only when policy defines timezone, staffed weekdays/hours, responsible duty roster, and fallback copy. Public pages render those configured hours exactly and never imply 24/7 coverage.
- Generic email is never a case source of truth. During transition, an operator may transcribe it as a source interaction under the same consent/read-back rules; claim/recovery links continue to their separately governed secure-continuation paths and are not implemented by this pilot.
- Zalo AI is a separate trust boundary. The pilot accepts only an explicit handoff marker, a minimal conversation digest/reference, editable structured fields, and final user confirmation; it never imports a raw transcript as evidence or instruction.
- Legacy migration is additive and evidence-preserving. It records source file/line, raw digest, missing-data flags, mapping decision, import result, and reconciliation; it never invents consent, verification, evidence, risk, decision, or publication.
- Each intake surface has one write authority at a time. Compatibility adapters may read or route, but never dual-write Case Kernel and JSONL.
- After a live canonical case exists, rollback does not restore correction JSONL writes. Intake/status can enter degraded mode while the Kernel remains authority; publication has an independent kill switch.
- Use strict RED-GREEN-REFACTOR TDD. Each numbered task receives an independent implementation review and spec-compliance review before the next task begins, and commits only its scoped files.
- Preserve user-owned worktree changes, especially `web-nuxt/pages/xa-phuong/[id].vue`; inspect and reconcile its live diff before implementation, and never reset or overwrite unrelated edits.

## Locked File And Interface Map

| Unit | Responsibility |
|---|---|
| `agent/cases/domain.py` | Frozen vocabulary, command/result dataclasses, transition guards, public projection types |
| `agent/cases/policy.py` | Load and validate named-owner, risk, promise, retention, queue, and maker-checker policy |
| `agent/cases/store.py` | PostgreSQL transaction boundary and all Case Kernel persistence primitives |
| `agent/cases/security.py` | Receipt generation/digest, encrypted replay, access sessions, rotation/revocation, cookie policy |
| `agent/cases/service.py` | Create/access/status/review orchestration and idempotency |
| `agent/cases/public_api.py` | `/api/cases/**` transport and RFC 9457-style problem details |
| `agent/cases/contact.py` | Optional phone verification and notification-consent state |
| `agent/cases/outbox.py` | At-least-once notification dispatcher, retry, revocation re-check, incident signal |
| `agent/cases/work_control.py` | Derived queue, leases, heartbeat, takeover, recusal, priority, escalation |
| `agent/cases/correction.py` | Evidence, risk, decision, maker-checker, immutable change-set construction |
| `agent/cases/publication.py` | Atomic apply, public projection verification, recovery, inverse-patch rollback |
| `agent/cases/admin_api.py` | Action-scoped queue/workbench/assisted endpoints under `/admin/cases` |
| `agent/cases/legacy_import.py` | Deterministic JSONL classification, shadow import, duplicate linkage, reconciliation |
| `agent/cases/metrics.py` | Capacity events, 28-day window, promise health, privacy-safe internal metrics |
| `web-nuxt/types/cases.ts` | Exact public/admin TypeScript contract matching Pydantic projections |
| `web-nuxt/composables/useCorrectionCases.ts` | Secret-safe create/access/status/rotate/review client with no persistent bearer storage |
| `web-nuxt/components/cases/**` | Intake, receipt, status, decision/publication, and assisted-workbench presentation |
| `web-nuxt/pages/yeu-cau/**` | Canonical public correction intake, lookup, and status journeys |

Locked cross-task signatures:

```python
@dataclass(frozen=True)
class ActorContext:
    actor_ref: str
    channel: Channel
    scopes: frozenset[str]
    correlation_id: str

@dataclass(frozen=True)
class CommandEnvelope:
    idempotency_key: str
    expected_revision: int | None
    actor: ActorContext

class CaseService:
    def create_correction(self, command: CreateCorrectionCommand, *, now: datetime) -> CreateCorrectionResult: ...
    def exchange_receipt(self, command: ExchangeReceiptCommand, *, now: datetime) -> AccessGrant: ...
    def public_status(self, access_token: str, *, now: datetime) -> PublicCaseStatus: ...
    def rotate_receipt(self, command: RotateReceiptCommand, *, now: datetime) -> ReceiptGrant: ...
    def request_review(self, command: RequestReviewCommand, *, now: datetime) -> PublicCaseStatus: ...
```

```typescript
export interface PublicCaseStatus {
  // Nuxt-facing types are camelCase; Pydantic uses explicit aliases for these
  // names while PostgreSQL/domain fields remain snake_case.
  publicReference: string
  receivedAt: string
  currentStep: CasePublicStep
  waitingFor: 'service' | 'requester' | 'external' | null
  nextAction: string
  nextUpdateAt: string
  promiseHealth: 'on_track' | 'at_risk' | 'breached' | 'recovery'
  itemDecisions: PublicItemDecision[]
  itemPublicationStates: PublicItemPublication[]
  reviewPath: 'none' | 'review_requested' | 'under_review' | 'review_completed'
}
```

---

### Task 1: Domain Vocabulary, Policy Authority, Permissions, And Kill Switches

**Files:**
- Create: `config/case-service-policy.json`
- Create: `agent/cases/__init__.py`
- Create: `agent/cases/domain.py`
- Create: `agent/cases/policy.py`
- Modify: `agent/config.py`
- Modify: `agent/admin_permissions.py`
- Modify: `web-nuxt/utils/adminAccess.ts`
- Test: `agent/tests/test_case_policy.py`
- Test: `agent/tests/test_case_permissions.py`
- Test: `web-nuxt/tests/admin-case-access.test.ts`

**Interfaces:**
- Produces enums `ServiceKind`, `CasePhase`, `CaseActivity`, `DispositionFamily`, `PromiseHealth`, `RiskClass`, `EvidenceLevel`, `CorrectionOutcome`, and `PublicationState` with the exact values in Global Constraints.
- Produces frozen `ActorContext`, `CommandEnvelope`, `CaseSnapshot`, `PublicCaseStatus`, `CaseProblem`, and `load_case_policy() -> CasePolicy`.
- Produces action scopes `service.operator`, `correction.decide`, `truth.review`, `publication.apply`, and `case.supervisor` in backend and frontend permission registries.

- [ ] **Step 1: Write failing vocabulary, policy, and permission tests**

```python
def test_policy_names_owner_and_refuses_public_resolution_sla():
    policy = load_case_policy()
    assert policy.revision == "correction-pilot-v1"
    assert policy.owner_ref_env == "CASE_SERVICE_OWNER_REF"
    assert policy.public_resolution_sla_enabled is False
    assert policy.receipt_target_seconds == 5
    assert policy.triage_target_seconds == 86_400
    assert policy.update_target_seconds == 259_200

def test_correction_outcomes_have_no_generic_terminal_state():
    assert {item.value for item in CorrectionOutcome} == {
        "corrected", "confirmed_current", "insufficient_evidence",
        "out_of_scope", "duplicate_linked", "unable_to_verify",
        "withdrawn_by_requester",
    }
```

Frontend test asserts `/admin/yeu-cau` requires `service.operator`, each new scope is normalized, and an unknown scope is still denied.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_policy.py agent/tests/test_case_permissions.py
Set-Location web-nuxt; npm test -- --run tests/admin-case-access.test.ts; Set-Location ..
```

Expected: missing `agent.cases`, missing policy file, and frontend rejects the new scopes.

- [ ] **Step 3: Implement the frozen contract and strict policy loader**

The JSON policy must contain exact keys for `owner_ref_env`, revision, clocks, lease duration, risk registry, maker-checker rules, retention, notification channel, assisted coverage, and `public_resolution_sla_enabled: false`; `owner_ref_env` is exactly `CASE_SERVICE_OWNER_REF`. Reject unknown/missing keys, a missing deploy-specific owner value when a case flag is enabled, team/mailbox-like owner values, non-positive clock values, an enabled public resolution SLA, R2/R3 policy without independent review, or enabled assisted service without timezone/hours/duty roster/fallback copy. Add all five `Settings` flags with false defaults plus `CASE_KERNEL_ENCRYPTION_KEY` and `CASE_SERVICE_OWNER_REF`. Production validation fails when any case flag is true without PostgreSQL, one named individual owner, and the dedicated encryption key.

- [ ] **Step 4: Add action-scoped RBAC without collapsing roles**

Give existing `admin` and `superadmin` roles the new scopes; do not grant decision, truth, publication, or supervisor authority to `moderator`. Allow explicit per-user scope grants. Add `/admin/yeu-cau` route ownership and make `service.operator` the minimal AdminCP entry scope for that page.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_policy.py agent/tests/test_case_permissions.py agent/tests/test_admin_permissions.py
Set-Location web-nuxt; npm test -- --run tests/admin-case-access.test.ts tests/admin-access.test.ts; Set-Location ..
git add config/case-service-policy.json agent/cases/__init__.py agent/cases/domain.py agent/cases/policy.py agent/config.py agent/admin_permissions.py web-nuxt/utils/adminAccess.ts agent/tests/test_case_policy.py agent/tests/test_case_permissions.py web-nuxt/tests/admin-case-access.test.ts
git commit -m "feat: define correction case contracts"
```

Review gate: verify exact vocabulary, false-by-default controls, named individual owner, no public resolution SLA, and no broad role string replacing action/risk authority.

---

### Task 2: Migration 080, Fresh-Schema Parity, And Readiness

**Files:**
- Create: `agent/migrations/080_correction_case_kernel.sql`
- Modify: `init.sql`
- Modify: `agent/database.py`
- Modify: `agent/server.py`
- Modify: `agent/tests/test_migration_chain.py`
- Modify: `agent/tests/test_migration_apply.py`
- Create: `agent/tests/test_case_schema_postgres.py`

**Interfaces:**
- Produces PostgreSQL tables `cases`, `case_interactions`, `case_party_authorities`, `case_work_items`, `case_decisions`, `case_promise_clocks`, `case_receipts`, `case_access_sessions`, `case_admin_access_sessions`, `case_transitions`, `case_audit_events`, `case_outbox`, `case_idempotency`, `case_contact_challenges`, `correction_items`, `correction_evidence`, `correction_change_sets`, `legacy_intake_records` (the durable `LegacyIntakeRecord` model), and `case_capacity_events`, plus additive `entities.revision INTEGER NOT NULL DEFAULT 1`.
- Raises `PG_REQUIRED_SCHEMA_VERSION` from 79 to 80 and registers every runtime-required table/column in readiness.

- [ ] **Step 1: Write failing schema-chain and real-PostgreSQL tests**

Assert UUID primary keys, foreign keys, revision/check constraints, immutable linkage, unique active work lease, receipt digest shape, no plaintext capability/contact/evidence column, outbox uniqueness, idempotency expiry, change-set base revision, `entities.revision >= 1`, legacy locator uniqueness, and schema-version registration. Real PostgreSQL tests must inspect constraints and owners, not only grep SQL.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_migration_chain.py agent/tests/test_case_schema_postgres.py agent/tests/test_migration_apply.py
```

Expected: migration 080 and tables are absent; readiness still accepts schema version 79.

- [ ] **Step 3: Implement one additive replay-safe migration and `init.sql` parity**

Use bounded text checks for all enumerations, `JSONB` only for versioned structured projections/patches, `BYTEA/TEXT` ciphertext fields named `*_enc`, and partial/covering indexes for queue priority, due promises, outbox retry, access expiry, and legacy reconciliation. Add `entities.revision INTEGER NOT NULL DEFAULT 1` with a positive check and no content-changing backfill; every entity mutation increments it through Task 11. Store `review_of_case_id` on `cases`; enforce that a review case references a closed case and cannot share the same ID in service guards. Add `VALUES ('agent', 80, '080_correction_case_kernel.sql', NOW())` with monotonic upsert.

- [ ] **Step 4: Register readiness and PostgreSQL-only runtime behavior**

Add required table/column sets and version 80. Wire `case_kernel_schema` and `case_policy` into `/health/ready`: when all case flags are false, unavailable case capability is reported as dormant and does not block unrelated runtime readiness; when any case flag is true, PostgreSQL schema/policy/owner/key failures block readiness with stable codes and no DSN/schema contents. Do not build SQLite shadow tables for the Kernel.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_migration_chain.py agent/tests/test_case_schema_postgres.py agent/tests/test_migration_apply.py agent/tests/test_migration_readiness_postgres.py
git add agent/migrations/080_correction_case_kernel.sql init.sql agent/database.py agent/server.py agent/tests/test_migration_chain.py agent/tests/test_migration_apply.py agent/tests/test_case_schema_postgres.py
git commit -m "feat: add correction case schema"
```

Review gate: compare migration and fresh schema column-for-column; verify no destructive DDL, plaintext secret/contact/evidence storage, fabricated backfill, or SQLite runtime path.

---

### Task 3: Pure Case State, Promise, Risk, And Work-Derivation Policy

**Files:**
- Modify: `agent/cases/domain.py`
- Create: `agent/cases/transitions.py`
- Create: `agent/cases/queue_policy.py`
- Test: `agent/tests/test_case_transitions.py`
- Test: `agent/tests/test_case_properties.py`
- Test: `agent/tests/test_case_queue_policy.py`

**Interfaces:**
- Produces `transition_case(snapshot, command, policy, *, now) -> TransitionResult`.
- Produces `derive_work_items(snapshot, correction_items, policy, *, now) -> tuple[WorkItemDraft, ...]`.
- Produces `priority_key(item) -> tuple[int, int, int, datetime, datetime]` ordered emergency, promise health, risk, oldest ready, oldest received.

- [ ] **Step 1: Write failing example and property tests**

```python
def test_closed_case_never_reopens():
    with pytest.raises(TransitionRejected, match="closed_case_immutable"):
        transition_case(closed_case(), command(phase=CasePhase.INVESTIGATION), policy(), now=NOW)

@given(case_snapshots(), transition_commands())
def test_revision_never_decreases(snapshot, command):
    try:
        result = transition_case(snapshot, command, policy(), now=NOW)
    except TransitionRejected:
        return
    assert result.snapshot.current_revision == snapshot.current_revision + 1
```

Cover waiting actor/reason/next-review requirements, no backlog clock pause, review relation derivation, `corrected` publication guard, R2/R3 independence, and deterministic priority.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py
```

Expected: transition and queue modules do not exist.

- [ ] **Step 3: Implement pure deterministic policy functions**

Return new frozen snapshots and immutable transition/work drafts; never perform I/O or read wall clock internally. `waiting_on_requester` requires requester-facing safe copy and `next_review_at`. Clock health derives from original due time and observation time; waiting segments remain separately reportable. `fulfillment -> closed/corrected` requires `publication_state=verified` for every accepted public-change item.

- [ ] **Step 4: Add maker-checker and recusal derivation**

R0 may create direct fulfillment work after validation, R1 may require one decision role per policy, R2 requires authoritative evidence or an independent reviewer, and R3 always creates separate truth-review and publication-review work. An actor who supplied evidence cannot satisfy an independence-required review.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py
git add agent/cases/domain.py agent/cases/transitions.py agent/cases/queue_policy.py agent/tests/test_case_transitions.py agent/tests/test_case_properties.py agent/tests/test_case_queue_policy.py
git commit -m "feat: enforce correction case policy"
```

Review gate: inspect every terminal transition, orthogonal dimension, clock lineage, review relation, and R2/R3 independence rule against spec sections 6, 9, 11, and 12.

---

### Task 4: PostgreSQL Case Store And Transactional Create Boundary

**Files:**
- Create: `agent/cases/store.py`
- Create: `agent/cases/audit.py`
- Test: `agent/tests/test_case_store.py`
- Test: `agent/tests/test_case_transaction_postgres.py`

**Interfaces:**
- Produces `PostgresCaseStore.transaction() -> CaseTransaction` with commit-on-success and rollback-on-error.
- Produces transaction methods `insert_case`, `insert_interaction`, `insert_party_authority`, `insert_correction_items`, `insert_promise_clocks`, `insert_work_items`, `append_transition`, `append_audit`, `enqueue_outbox`, `load_case(for_update=False)`, and `update_case(expected_revision, snapshot)`.
- Produces `RevisionConflict(current: CaseSnapshot)` and `CaseNotFound`.

- [ ] **Step 1: Write failing atomicity, CAS, and immutable-ledger tests**

Seed a valid create bundle and prove all rows commit. Inject failure after interaction, audit, and outbox insertion and prove the whole transaction rolls back. Race two updates against revision 1 and require one success plus one `RevisionConflict` carrying revision 2. Reject updates/deletes to transition and audit rows at the repository boundary.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_store.py agent/tests/test_case_transaction_postgres.py
```

Expected: no store or transaction boundary exists.

- [ ] **Step 3: Implement a focused transaction adapter**

Use `db._conn(commit_on_success=False)` and explicit commit/rollback exactly once per unit of work. Map rows at the boundary; domain code receives typed snapshots, not psycopg rows. Lock mutations with `SELECT ... FOR UPDATE` where policy requires serialized authority and use `UPDATE ... WHERE current_revision = %s RETURNING` for CAS.

- [ ] **Step 4: Make audit and outbox first-class transaction participants**

Audit rows contain actor ref, scopes, channel, reason code, policy revision, correlation ID, before/after safe snapshots, and timestamp. They must not use the existing best-effort JSONL admin audit as canonical case audit. Outbox insertion requires a deterministic idempotency key and generic payload descriptor, not evidence/contact/plaintext secret.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_store.py agent/tests/test_case_transaction_postgres.py agent/tests/test_database.py
git add agent/cases/store.py agent/cases/audit.py agent/tests/test_case_store.py agent/tests/test_case_transaction_postgres.py
git commit -m "feat: persist correction cases atomically"
```

Review gate: verify one connection/transaction owns business row, audit, and outbox; no implicit nested connection; CAS conflict returns current safe snapshot; immutable rows have no mutation path.

---

### Task 5: Secure Receipt, Encrypted Replay, Access Session, Rotation, And Revocation

**Files:**
- Create: `agent/cases/security.py`
- Modify: `agent/cases/store.py`
- Test: `agent/tests/test_case_receipts.py`
- Test: `agent/tests/test_case_access_security.py`
- Test: `agent/tests/test_case_security_source_guard.py`

**Interfaces:**
- Produces `issue_receipt(case_id, *, now) -> ReceiptGrant`, `digest_capability(secret) -> str`, `encrypt_replay(payload) -> str`, and `decrypt_replay(ciphertext) -> dict`.
- Produces `exchange_receipt(public_reference, capability, *, now) -> AccessGrant`, `rotate_receipt(access_token, *, now) -> ReceiptGrant`, `revoke_access(case_id, *, now)`, and `validate_access(token, *, now) -> CaseAccess`.
- Produces `issue_case_csrf(access: CaseAccess) -> str` and `validate_case_csrf(access, presented_token) -> None`; the token is HMAC-bound to the access-session digest and never grants case access by itself.
- `ReceiptGrant.capability` is returned once and is never accepted through GET/query parameters.

- [ ] **Step 1: Write failing cryptographic and lifecycle tests**

Assert a `VL-COR-` reference with 12 random Crockford symbols plus a valid check symbol, a 43-character URL-safe capability generated from 32 random bytes, a 64-hex HMAC digest, 365-day capability expiry, constant-time comparison, 15-minute access expiry, 24-hour replay expiry, old-grant revocation on rotation, revocation precedence over an unexpired session, and indistinguishable errors. Inspect persisted rows and captured logs to prove the raw secret is absent.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py
```

Expected: security module is missing.

- [ ] **Step 3: Implement dedicated-key encryption and digest-only capabilities**

Derive separate Fernet/HMAC subkeys from `CASE_KERNEL_ENCRYPTION_KEY` with HKDF salts `vl360-case-replay-v1` and `vl360-case-capability-v1`. Store only digest, key version, expiry/revocation, and encrypted replay. Reject missing/weak keys whenever a case flag is enabled; tests inject a valid key.

- [ ] **Step 4: Implement short-lived access and secure cookie contract**

Access tokens are random, digest-only, bound to one receipt revision, and invalidated by receipt rotation/revocation. Authenticated cases also bind authority to the current server-side user ID; access validation requires both the matching logged-in user and the case grant, so another user cannot use a copied cookie. Export one cookie helper with `httponly=True`, production `secure=True`, `samesite='lax'`, `path='/api/cases'`, and `max_age=900`. Issue a readable 15-minute `vl360_case_csrf` cookie scoped to `/api/cases`; mutations validate exact Origin/Sec-Fetch-Site and constant-time equality with `X-Case-CSRF`, then validate the token's HMAC binding to the current access digest. Add source guards rejecting `capability`, `receipt_secret`, access token, or CSRF binding material in logging/analytics/query parsing and frontend persistent-storage calls.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py agent/tests/test_privacy_logging.py
git add agent/cases/security.py agent/cases/store.py agent/tests/test_case_receipts.py agent/tests/test_case_access_security.py agent/tests/test_case_security_source_guard.py
git commit -m "feat: secure correction case receipts"
```

Review gate: manually trace lost response, retry, exchange, expiry, rotation, revocation, and cache behavior; verify no bearer material can appear in URI, log, telemetry, notification, or durable plaintext.

---

### Task 6: Correction Create Command And Idempotency

**Files:**
- Create: `agent/cases/service.py`
- Create: `agent/cases/rate_limit.py`
- Modify: `agent/cases/store.py`
- Test: `agent/tests/test_correction_create.py`
- Test: `agent/tests/test_case_idempotency_postgres.py`

**Interfaces:**
- Produces `CreateCorrectionCommand(envelope, reporter_privacy, items, optional_phone, notification_consent, authenticated_user_ref, handoff)` and `CreateCorrectionResult(case_id, public_reference, capability, received_at, next_update_at, replayed)`.
- `CaseService.create_correction(...)` commits case, interaction, party authority when present, E0 evidence, items, clocks, initial work, transition, audit, receipt, encrypted replay, and notification outbox intent in one transaction.
- Produces PostgreSQL-backed `check_case_rate_limit(bucket, subject_digest, *, limit, window, now)` for create, receipt exchange, contact OTP, review, and rotation; local memory is not authoritative.

- [ ] **Step 1: Write failing anonymous/contact/handoff/idempotency tests**

Test anonymous create, optional-phone create without treating contact verification as identity, authenticated linkage derived only from the current authenticated session rather than client JSON, operator actor rejection on public command, multi-item field validation, emergency/safety language rejection with safe urgent-routing copy, shared rate limits surviving a new service instance, and Zalo AI handoff requiring explicit confirmation plus digest but no transcript. Submit the same `Idempotency-Key` twice and require the same case/reference/capability replay; submit a different body under the same key and require `409 idempotency_conflict`.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py
```

Expected: create command/service is missing.

- [ ] **Step 3: Implement validation and canonical create orchestration**

Normalize only bounded field paths from policy, preserve reported/proposed values as encrypted private payload references, capture base entity revision, classify initial risk, and create E0 reporter assertion. A bounded pre-intake safety classifier may route explicit imminent-harm/emergency language to the existing safety lane and appropriate emergency-contact guidance; it must not create a correction case or describe vinhlong360 as an emergency authority. When an authenticated session exists, create a scoped `PartyAuthority`/account linkage from the server-side user ID; never trust a submitted user ID. Enforce shared PostgreSQL rate buckets using privacy-safe IP/actor/contact digests so process restart or multi-worker deployment cannot reset abuse controls. Generate public reference and capability before entering the transaction; persist only digest/ciphertext. Receipt failure rolls back the case. Notification enqueue failure inside the transaction also rolls back the intent insertion, but later provider delivery never rolls back the case.

- [ ] **Step 4: Implement encrypted lost-response replay**

Scope idempotency by normalized actor/channel plus key and canonical request digest. A duplicate exact request decrypts and returns the original one-time response for 24 hours with `replayed=True`; after expiry it returns a stable conflict without creating a second case or promising secret recovery.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py agent/tests/test_case_transaction_postgres.py
git add agent/cases/service.py agent/cases/rate_limit.py agent/cases/store.py agent/tests/test_correction_create.py agent/tests/test_case_idempotency_postgres.py
git commit -m "feat: create correction cases idempotently"
```

Review gate: verify one case/interaction per logical request, no contact-as-identity, no transcript import, durable receipt in the same transaction, and exact duplicate versus conflicting duplicate behavior.

---

### Task 7: Public Case API, Status Projection, Receipt Rotation, And ReviewCase

**Files:**
- Create: `agent/cases/public_api.py`
- Modify: `agent/cases/service.py`
- Modify: `agent/server.py`
- Test: `agent/tests/test_case_public_api.py`
- Test: `agent/tests/test_case_public_projection.py`

**Interfaces:**
- Produces routes `POST /api/cases/corrections`, `POST /api/cases/access`, `GET /api/cases/status`, `POST /api/cases/receipts/rotate`, `DELETE /api/cases/access`, `POST /api/cases/review`, `POST /api/cases/contact/request`, and `POST /api/cases/contact/verify`.
- Produces `project_public_status(case, items, review_relation, clocks) -> PublicCaseStatus` with only the fields locked in the header.

- [ ] **Step 1: Write failing ASGI transport and disclosure tests**

Assert flags return `404 capability_unavailable` while off; enabled create returns `201`, `Cache-Control: no-store`, reference and one-time capability; access accepts POST JSON only and sets the scoped HttpOnly access cookie plus readable CSRF cookie; GET status works only with access cookie; logout clears both. Assert rotate, review, logout, and contact mutations reject missing/invalid Origin or `X-Case-CSRF`. Assert status serialization excludes evidence, private notes, operator identity, IP/contact, internal owner, raw phase/activity, capability digest, and audit. Review on a closed case creates a new linked case and leaves the original immutable.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_public_api.py agent/tests/test_case_public_projection.py
```

Expected: router/routes are absent.

- [ ] **Step 3: Implement strict Pydantic transport and problem details**

Use `extra='forbid'`, bounded strings/lists, explicit field-path allowlist, `Idempotency-Key` header, and correlation ID. Pydantic models keep snake_case internally and use explicit camelCase response aliases matching `web-nuxt/types/cases.ts`; request models accept only the documented JSON names. Create/access enforce JSON content type, exact allowed Origin/Sec-Fetch-Site, and their dedicated rate limits. Cookie-authenticated mutations also require `X-Case-CSRF` validated by Task 5. Return RFC 9457-style `{type,title,status,detail,code,request_id}` without echoing secrets. Mount the router after `public_router`; add `Idempotency-Key` and `X-Case-CSRF` to CORS allow-headers and include `/api/cases` in private/no-store cache classification.

- [ ] **Step 4: Implement safe status and review semantics**

Map backstage state through a policy-versioned safe-copy catalog keyed by current step, waiting actor, outcome, publication state, and promise health; reject free-form private notes as `nextAction`. Keep accepted decision and publication state separate. `POST /review` requires a closed case, reason, and expected terminal revision; it creates a new `service_kind=correction`, `category=review`, `review_of_case_id=<closed>` case with its own receipt/work/audit, never reopens the original.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_public_api.py agent/tests/test_case_public_projection.py agent/tests/test_case_access_security.py agent/tests/test_server_models.py agent/tests/test_policy_http.py
git add agent/cases/public_api.py agent/cases/service.py agent/server.py agent/tests/test_case_public_api.py agent/tests/test_case_public_projection.py
git commit -m "feat: expose secure correction case status"
```

Review gate: inspect every response/cache header and verify no raw backstage or credential data; verify review graph semantics and generic credential errors prevent enumeration.

---

### Task 8: Optional Phone Verification And At-Least-Once Notification Outbox

**Files:**
- Create: `agent/cases/contact.py`
- Create: `agent/cases/outbox.py`
- Create: `agent/sms_provider.py`
- Modify: `agent/pinned_http.py`
- Modify: `agent/auth.py`
- Modify: `agent/scheduler.py`
- Test: `agent/tests/test_case_contact.py`
- Test: `agent/tests/test_case_outbox.py`
- Test: `agent/tests/test_sms_provider.py`
- Modify: `tests/test_pinned_http_consumers.py`

**Interfaces:**
- Produces `request_contact_verification(access: CaseAccess, phone, consent, *, now) -> ContactChallenge` and `verify_contact(access: CaseAccess, code, *, now) -> VerifiedContact`; public transport is owned by the two contact routes introduced in Task 7.
- Produces `dispatch_case_outbox(*, now, limit=100) -> DispatchSummary` with `FOR UPDATE SKIP LOCKED`, deterministic delivery key, bounded exponential retry, and dead-letter incident state.
- Produces reusable `SmsProvider.send(phone, message, *, delivery_key) -> DeliveryResult`; `auth.py` OTP and case notifications consume it.

- [ ] **Step 1: Write failing verification, consent, outage, and retry tests**

Prove OTP verification grants notification authority only, not listing/account authority. Revoke consent after enqueue and require dispatcher skip delivery. Simulate provider timeout then success and require one logical delivery with retry count. Simulate permanent failure and require incident signal without case rollback. Assert message contains only reference, generic update copy, and safe status instructions--never evidence, proposed value, phone echo, or bearer secret.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_contact.py agent/tests/test_case_outbox.py agent/tests/test_sms_provider.py
```

Expected: contact/outbox/provider abstractions are absent and SMS remains embedded in `auth.py`.

- [ ] **Step 3: Extract the existing eSMS transport without behavioral regression**

Extend `PinnedHTTPClient` with a bounded `post_json` operation that reuses exact-origin resolution, approved-socket dialing, peer verification, total/inactivity deadlines, encoded/decoded body caps, and zero cross-origin redirects. Move eSMS timeout, exact origin, payload, retry, and response mapping into `sms_provider.py`; register both auth OTP and case notification consumers in `tests/test_pinned_http_consumers.py`. Keep authentication OTP semantics unchanged. Never log full phone/message/provider credentials. Use a fake provider in all case tests.

- [ ] **Step 4: Implement verification and dispatcher authorization re-check**

Hash OTPs, bound attempts and expiry, encrypt phone at rest, store normalized contact digest for deduplication, and record consent revision. Require a valid case access session plus Task 5 CSRF binding; the request body never accepts `case_id` as authority. Before every side effect, reload receipt/contact/consent/case authority; revoked, muted, expired, or insufficient privilege marks the outbox item suppressed. Scheduler invokes dispatcher single-flight; dispatcher failure never stops unrelated jobs.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_contact.py agent/tests/test_case_outbox.py agent/tests/test_sms_provider.py agent/tests/test_auth_security_hardening.py tests/test_auth_behavior.py agent/tests/test_security_advanced.py tests/test_pinned_http_consumers.py
git add agent/cases/contact.py agent/cases/outbox.py agent/sms_provider.py agent/pinned_http.py agent/auth.py agent/scheduler.py agent/tests/test_case_contact.py agent/tests/test_case_outbox.py agent/tests/test_sms_provider.py tests/test_pinned_http_consumers.py
git commit -m "feat: notify correction cases safely"
```

Review gate: verify verification is action-specific, consent/revocation is checked at delivery time, provider retries are idempotent, and notification outage cannot invalidate a committed receipt.

---

### Task 9: Policy-Derived Queue, Leases, Takeover, Recusal, And Escalation

**Files:**
- Create: `agent/cases/work_control.py`
- Modify: `agent/cases/store.py`
- Test: `agent/tests/test_case_work_control.py`
- Test: `agent/tests/test_case_work_concurrency_postgres.py`

**Interfaces:**
- Produces `list_queue(actor, filters, *, now) -> QueuePage`, `claim_work_item(work_item_id, actor, expected_revision, *, now) -> WorkItem`, `heartbeat_lease(...)`, `release_work_item(...)`, `takeover_work_item(...)`, `recuse_actor(...)`, and `scan_escalations(*, now) -> EscalationSummary`.
- Lease duration comes from policy; one work item has at most one active assignee.

- [ ] **Step 1: Write failing priority, authorization, and concurrency tests**

Seed emergency, breached, at-risk, R3, and old ready items and assert exact ordering. Race two claims and require one winner. Assert expired lease can be reclaimed, heartbeat cannot revive an expired lease, takeover requires `case.supervisor` and reason, actor cannot claim work lacking scope/risk clearance, recusal creates replacement work, and completed work requires evidence/result reference.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_work_control.py agent/tests/test_case_work_concurrency_postgres.py
```

Expected: work-control service is missing.

- [ ] **Step 3: Implement queue query and CAS lease commands**

Derive queue rows from work/case/promise/risk data; do not store a mutable generic queue status. Claim uses a single `UPDATE ... WHERE revision = %s AND (assignee_ref IS NULL OR lease_expires_at <= %s) RETURNING`. Heartbeat extends only a live lease owned by the same actor. Every assignment/delegation/takeover/recusal is audited in the same transaction.

- [ ] **Step 4: Implement escalation scanner**

Create idempotent escalation work for missing owner, at-risk/breached clock, R2/R3 evidence conflict, publication/rollback failure, privacy/security signal, repeated lease expiry, or abandoned case. Escalation never edits prior history or terminal outcome.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_work_control.py agent/tests/test_case_work_concurrency_postgres.py agent/tests/test_case_queue_policy.py
git add agent/cases/work_control.py agent/cases/store.py agent/tests/test_case_work_control.py agent/tests/test_case_work_concurrency_postgres.py
git commit -m "feat: control correction case work"
```

Review gate: verify transparent priority, no throughput-gaming fields, one active assignee, bounded leases, independent reviewer rules, and no supervisor bypass of risk guards.

---

### Task 10: Evidence Registry, Risk Decisions, Domain Outcomes, And Immutable Change Sets

**Files:**
- Create: `agent/cases/correction.py`
- Modify: `agent/cases/store.py`
- Test: `agent/tests/test_correction_evidence.py`
- Test: `agent/tests/test_correction_decisions.py`
- Test: `agent/tests/test_correction_changesets.py`

**Interfaces:**
- Produces `add_evidence(command) -> EvidenceRecord`, `decide_item(command) -> DecisionOutcome`, and `build_change_set(case_id, accepted_item_ids, actor, expected_revision, *, now) -> CorrectionChangeSet`.
- Evidence records carry level, source scope, provenance, observed/effective/expiry time, geography revision, encrypted payload reference, and author ref.
- Change set contains immutable before/after JSON Patch, inverse patch, base/current entity revision, evidence refs, policy revision, maker/reviewer refs, and `apply_status=pending`.

- [ ] **Step 1: Write failing evidence/risk/maker-checker/outcome tests**

Test E0 reporter assertions, E1 contextual artifacts, E2 independent public sources, E3 authoritative sources, and E4 field/independent verification without automatic acceptance; also test expired/wrong-scope/conflicting evidence, R2 authoritative-or-independent requirement, R3 maker-checker, author recusal, exact terminal reason codes, duplicate linkage, and acceptance producing a change set without changing the live entity. Reject a change set when proposed before-state does not match the captured entity revision.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_correction_evidence.py agent/tests/test_correction_decisions.py agent/tests/test_correction_changesets.py
```

Expected: correction decision service is missing.

- [ ] **Step 3: Implement evidence and decision commands under expected revision**

Require action scope and active work lease. Store evidence content encrypted; public/source-safe descriptors remain structured. A decision records item outcome, bounded reason, evidence lineage, decision maker, reviewer when required, policy revision, and time. `accepted` is represented by an item decision requiring a public change; it is not a case terminal outcome.

- [ ] **Step 4: Build immutable patch and inverse patch**

Allow only policy-approved entity field paths. Capture normalized before/after values and entity revision; reject no-op patches and cross-entity item bundles. Insert the change set, item linkage, transition to fulfillment, new publication work, audit, and outbox intent in one transaction; do not call the entity writer.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_correction_evidence.py agent/tests/test_correction_decisions.py agent/tests/test_correction_changesets.py agent/tests/test_case_transaction_postgres.py
git add agent/cases/correction.py agent/cases/store.py agent/tests/test_correction_evidence.py agent/tests/test_correction_decisions.py agent/tests/test_correction_changesets.py
git commit -m "feat: decide correction evidence"
```

Review gate: verify evidence does not become truth by level alone, accepted does not mutate/publish, all decisions have lineage/reason, and immutable patches are bounded to one entity revision.

---

### Task 11: Transaction-Aware Entity Write And Provenance Boundary

**Files:**
- Modify: `agent/database.py`
- Create: `agent/entity_write.py`
- Modify: `agent/admin.py`
- Test: `agent/tests/test_entity_write_transaction.py`
- Test: `agent/tests/test_entity_write_compatibility.py`

**Interfaces:**
- Produces `EntityWriteService.load_for_update(conn, entity_id) -> EntitySnapshot`.
- Produces `EntityWriteService.apply_patch(conn, entity_id, patch, *, expected_revision, actor, provenance) -> EntityWriteResult` and `write_change_audit(conn, result, actor, provenance)` using the caller-owned connection.
- Existing `db.upsert_entity(entity)` remains a compatibility wrapper that opens one transaction then delegates to the new service.

- [ ] **Step 1: Write failing same-transaction and compatibility tests**

Inject failure after entity row write but before entity-change audit and prove no entity change commits. Prove successful write updates entity row, CTI detail row/cache mutation descriptor, and `entity_changes` under one caller transaction. Verify existing admin upsert behavior and public parsing remain compatible. Test expected revision conflict and no-op patch preserving `updatedAt`.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_entity_write_transaction.py agent/tests/test_entity_write_compatibility.py agent/tests/test_entity_details_sync.py
```

Expected: `upsert_entity()` and `log_entity_changes()` own separate connections and cannot satisfy rollback assertion.

- [ ] **Step 3: Extract a caller-owned entity writer**

Move normalization and `_write_entity_row` reuse behind `EntityWriteService`; keep all SQL behavior and CTI synchronization. Return deferred cache mutations and apply them only after outer transaction commit. Consume the `entities.revision` column added by migration 080. Every actual entity content change increments it exactly once; a no-op does not. `attributes.verifiedAt` remains the canonical verification timestamp and changes only through an authorized verification command, never through ordinary correction apply or admin edit.

- [ ] **Step 4: Route legacy admin mutation through the same boundary**

Update admin entity mutations to call one transaction-aware operation for entity plus change audit. Preserve API response/caches and add provenance source `admin-editor`. Remove only the separate connection behavior; do not broadly restructure `admin.py`.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_entity_write_transaction.py agent/tests/test_entity_write_compatibility.py agent/tests/test_entity_details_sync.py agent/tests/test_admin_mutations.py tests/test_entity_write_guard.py
git add agent/database.py agent/entity_write.py agent/admin.py agent/tests/test_entity_write_transaction.py agent/tests/test_entity_write_compatibility.py
git commit -m "refactor: make entity writes transactional"
```

Review gate: inspect for every nested `_conn()` call; verify cache mutation happens after commit, old admin behavior remains, revision/no-op semantics are correct, and no case code bypasses this boundary.

---

### Task 12: Atomic Publication Apply, Projection Verification, Recovery, And Rollback

**Files:**
- Create: `agent/cases/publication.py`
- Modify: `agent/cases/store.py`
- Modify: `agent/public_api.py`
- Test: `agent/tests/test_correction_publication.py`
- Test: `agent/tests/test_correction_publication_failure.py`
- Test: `agent/tests/test_correction_rollback.py`

**Interfaces:**
- Produces `apply_change_set(command, *, now) -> PublicationResult`, `verify_public_projection(command, fetcher, *, now) -> VerificationResult`, and `rollback_change_set(command, *, now) -> RollbackResult`.
- Apply requires `publication.apply`; R3 also requires a prior independent `truth.review` result. Verification is a separate command and work result.

- [ ] **Step 1: Write failing atomicity, conflict, verification, and rollback tests**

Prove apply atomically commits entity row/revision, entity provenance/audit, change-set state, correction item publication state, case fulfillment transition, case audit, and outbox. Inject failure at each participant and require total rollback. Test base-revision drift, public endpoint cache/fetch failure, wrong rendered value/source/time, verified projection closure, inverse-patch rollback, and rollback refusal when entity drifted after apply.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_rollback.py
```

Expected: publication service is absent.

- [ ] **Step 3: Implement atomic apply behind the publication kill switch**

Lock case, change set, and entity; validate expected case/entity/change-set revisions and authority; call `EntityWriteService` on the same connection. Mark `applied`, not `verified`, after commit. Set `updatedAt` and increment `entities.revision` only for a content diff; preserve `attributes.verifiedAt` until the separate authorized verification command. Apply deferred entity cache mutation only after commit.

- [ ] **Step 4: Implement external public projection verification and recovery**

Use an injected fetcher in tests and a bounded same-origin public API fetch in runtime. Compare entity ID, field value, source descriptor/time, and entity revision. Success marks the projection verified and, when the actor holds the required verification authority, updates canonical `attributes.verifiedAt`; it then completes work and permits `closed/corrected`. Failure keeps fulfillment/recovery, marks promise health, creates escalation and next update, and never emits terminal success. Rollback locks current entity and applies inverse patch only if the applied revision still matches; otherwise fail closed and escalate.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_rollback.py agent/tests/test_public_api.py
git add agent/cases/publication.py agent/cases/store.py agent/public_api.py agent/tests/test_correction_publication.py agent/tests/test_correction_publication_failure.py agent/tests/test_correction_rollback.py
git commit -m "feat: publish verified corrections atomically"
```

Review gate: verify accepted/applied/verified are distinct, every failure remains non-terminal, rollback is inverse and revision-safe, and the publication kill switch cannot disable intake/receipt/audit.

---

### Task 13: Action-Scoped Admin API And Guided Assisted Intake

**Files:**
- Create: `agent/cases/admin_api.py`
- Modify: `agent/server.py`
- Modify: `agent/admin.py`
- Modify: `agent/admin_permissions.py`
- Test: `agent/tests/test_case_admin_api.py`
- Test: `agent/tests/test_assisted_correction.py`
- Test: `agent/tests/test_case_admin_scope_matrix.py`

**Interfaces:**
- Produces `GET /admin/cases`, `GET /admin/cases/{case_id}`, work-item claim/heartbeat/release/takeover/recuse routes, evidence/decision routes, change-set build/apply/verify/rollback routes, and `POST /admin/cases/assisted/corrections`.
- Produces `POST /admin/cases/access/step-up` and `DELETE /admin/cases/access/step-up`; a successful operator reauthentication creates a 15-minute digest-only `case_admin_access_sessions` grant bound to admin user, current login session, allowed private-data scope, and optional case/work item.
- Assisted body requires `channel`, privacy notice revision, consent scope/time, target/field/value read-back, reporter confirmation, operator actor, and optional notification consent; `extra='forbid'` rejects secret-like fields.

- [ ] **Step 1: Write failing route/scope/read-back/secret-boundary tests**

Create a scope matrix proving operator can view/transcribe but not decide, decision maker cannot publish, truth reviewer cannot self-review, publication actor cannot supervise, and supervisor takeover still cannot bypass R2/R3 guards. Assert queue/safe summary works without step-up, while raw evidence/private notes require a live case-admin access grant and fail generically after expiry/revocation/logout. Assert assisted intake fails without privacy notice, scoped consent, read-back, or final confirmation. Send `password`, `otp`, `recovery_code`, and `secret` fields to assisted intake and require 422 without logging values.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_admin_api.py agent/tests/test_assisted_correction.py agent/tests/test_case_admin_scope_matrix.py
```

Expected: admin case router is absent.

- [ ] **Step 3: Implement explicit route-level action guards**

Mount a separate `/admin/cases` router using existing admin authentication, CSRF, and rate limiting, but call action-specific scope guards per command. Do not rely on one prefix scope for all actions. Step-up reauthenticates the logged-in operator using the account's configured password or OTP flow without exposing the credential to case code; admin API-key actors may operate safe queue/deploy endpoints but cannot receive private-evidence grants. Return safe workbench projections; private evidence requires corresponding active work/clearance plus the short-lived grant and is never included in queue list responses.

- [ ] **Step 4: Implement guided transcriber transaction**

Create an `Interaction` with phone/Zalo-human channel, scoped `PartyAuthority`, consent and read-back audit, canonical correction case, receipt, clocks, initial work, and outbox in the same create transaction. Return human reference and operator-safe read-back; never return capability secret to the operator unless the user is physically controlling the self-service response. No recording/transcript field exists.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_admin_api.py agent/tests/test_assisted_correction.py agent/tests/test_case_admin_scope_matrix.py agent/tests/test_admin_permissions.py
git add agent/cases/admin_api.py agent/server.py agent/admin.py agent/admin_permissions.py agent/tests/test_case_admin_api.py agent/tests/test_assisted_correction.py agent/tests/test_case_admin_scope_matrix.py
git commit -m "feat: add assisted correction operations"
```

Review gate: verify no prefix-wide overgrant, operator cannot touch authentication secrets or final publication, assisted and self-service use the same Kernel, and phone-only status remains public-safe.

---

### Task 14: Public Nuxt Contract, Intake, One-Time Receipt, Lookup, And Status

**Files:**
- Create: `web-nuxt/types/cases.ts`
- Create: `web-nuxt/composables/useCorrectionCases.ts`
- Create: `web-nuxt/components/cases/CorrectionIntakeForm.vue`
- Create: `web-nuxt/components/cases/CaseReceiptCard.vue`
- Create: `web-nuxt/components/cases/CaseStatusTimeline.vue`
- Create: `web-nuxt/components/cases/DecisionPublicationState.vue`
- Create: `web-nuxt/pages/yeu-cau/sua-thong-tin.vue`
- Create: `web-nuxt/pages/yeu-cau/tra-cuu.vue`
- Create: `web-nuxt/pages/yeu-cau/trang-thai.vue`
- Test: `web-nuxt/tests/correction-case-contract.test.ts`
- Test: `web-nuxt/tests/correction-case-security.test.ts`
- Test: `web-nuxt/tests/correction-case-pages.test.ts`

**Interfaces:**
- Produces `useCorrectionCases()` methods `createCorrection`, `exchangeReceipt`, `loadStatus`, `rotateReceipt`, `clearAccess`, `requestContactVerification`, `verifyContact`, and `requestReview` using `apiFetch` and cookie-based access.
- Component events contain structured non-secret fields only; the composable never writes capability/access values to persistent storage or telemetry.

- [ ] **Step 1: Write failing type/copy/security/page tests**

Assert exact backend projection names, `Idempotency-Key` header use, `X-Case-CSRF` on cookie-authenticated mutations, no GET/query capability, no local/session storage, no capability in route state, no generic `Da xu ly`, and distinct copy for `accepted` versus `published/verified`. Page tests require progressive field-level form, optional phone consent and verification, explicit Zalo AI handoff confirmation, one-time receipt warning, printable human reference, review action only on terminal status, and no unsupported 24-48 hour resolution promise.

- [ ] **Step 2: Run tests and verify RED**

```powershell
Set-Location web-nuxt
npm test -- --run tests/correction-case-contract.test.ts tests/correction-case-security.test.ts tests/correction-case-pages.test.ts
Set-Location ..
```

Expected: types/composable/pages/components are absent.

- [ ] **Step 3: Implement secret-safe client state and transport**

Keep the one-time capability in a function-local/ref value only until rendered/copied; clear it on navigation/unmount and never include it in Nuxt payload serialization. After create/access, status uses the HttpOnly cookie. Read the non-secret CSRF cookie only immediately before a mutation and send it as `X-Case-CSRF`; never persist it or mix it with receipt capability state. Errors map invalid/expired/unknown to one neutral recovery message. Generate a cryptographically random UUID idempotency key per logical submit and retain it only for the active retry lifecycle.

- [ ] **Step 4: Build the Nocturne Heritage service journey**

Use the existing shell/tokens with a focused editorial header, compact trust notice, field-by-field cards, configured assisted-hours disclosure when available, urgent-safety routing copy that does not imply emergency authority, and a stable action region. At 320px width/200% text, all content reflows in one column; at short height, submit/receipt controls remain reachable without overlaying the bottom nav. Motion is limited to staged section reveal and status progression, disabled under reduced motion. Use semantic headings, fieldset/legend, error summary with focus transfer, live region for submission/status, and print styles for the receipt.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
Set-Location web-nuxt
npm test -- --run tests/correction-case-contract.test.ts tests/correction-case-security.test.ts tests/correction-case-pages.test.ts tests/nocturne-theme-contract.test.ts tests/ui-foundation-shell.test.ts
npm run typecheck
Set-Location ..
git add web-nuxt/types/cases.ts web-nuxt/composables/useCorrectionCases.ts web-nuxt/components/cases/CorrectionIntakeForm.vue web-nuxt/components/cases/CaseReceiptCard.vue web-nuxt/components/cases/CaseStatusTimeline.vue web-nuxt/components/cases/DecisionPublicationState.vue web-nuxt/pages/yeu-cau/sua-thong-tin.vue web-nuxt/pages/yeu-cau/tra-cuu.vue web-nuxt/pages/yeu-cau/trang-thai.vue web-nuxt/tests/correction-case-contract.test.ts web-nuxt/tests/correction-case-security.test.ts web-nuxt/tests/correction-case-pages.test.ts
git commit -m "feat: add public correction case journey"
```

Review gate: inspect SSR payload, DOM, route, browser storage, telemetry, copy, keyboard order, 200% zoom, 320x256, 320x180, and accepted/publication distinction.

---

### Task 15: Integrate Directory, Detail, Ward, Contact Router, And Legacy Entry Routes

**Files:**
- Modify: `web-nuxt/pages/danh-ba.vue`
- Modify: `web-nuxt/pages/dia-diem/[id].vue`
- Modify: `web-nuxt/pages/xa-phuong/[id].vue`
- Modify: `web-nuxt/pages/lien-he.vue`
- Modify: `agent/public_api.py`
- Test: `web-nuxt/tests/correction-entrypoints.test.ts`
- Test: `web-nuxt/tests/contact-service-router.test.ts`
- Test: `agent/tests/test_legacy_correction_adapter.py`

**Interfaces:**
- Entry links pass only non-secret target context: `entity`, `field`, and `source`; canonical form re-fetches entity state and base revision.
- Legacy correction adapter classifies `stale_field` and factual entity/facility intent into `CaseService.create_correction`; policy-violation content stays in its existing moderation lane. It never writes both Kernel and JSONL.

- [ ] **Step 1: Inspect dirty files and write failing integration tests**

Before editing, run `git diff -- web-nuxt/pages/xa-phuong/[id].vue` and preserve all user-owned hunks. Tests require correction CTAs from directory/detail/ward to canonical intake with safe context, detail trust CTA no longer becoming a community search, and `/lien-he` routing by job. Assert contact copy contains no `24-48 gio` resolution promise and unavailable claim/recovery/safety capability is described honestly.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_legacy_correction_adapter.py
Set-Location web-nuxt; npm test -- --run tests/correction-entrypoints.test.ts tests/contact-service-router.test.ts; Set-Location ..
```

Expected: old CTAs point at JSONL/community/generic contact and adapter is missing.

- [ ] **Step 3: Wire public surfaces to one canonical correction journey**

Use one shared link builder and accessible CTA copy. Query context is a convenience hint, not trusted submission data; the form reloads target name, revision, allowed fields, and disclosure. Keep route layout/shell stable and avoid adding a second navigation system or bottom-nav destination.

- [ ] **Step 4: Make legacy routing single-authority and reversible**

While `CORRECTION_INTAKE_ENABLED` is false, current legacy behavior remains. When true, correction-classified `/api/report` and `/api/entities/{id}/report-stale` requests route only to the Kernel and return the canonical receipt envelope; they do not append JSONL. Mixed policy-violation reports continue through the existing moderation path until its separate spec. After cutover, a correction-specific archive guard prevents re-enabling JSONL correction writes even if the public UI flag is rolled back.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_legacy_correction_adapter.py agent/tests/test_public_api.py
Set-Location web-nuxt
npm test -- --run tests/correction-entrypoints.test.ts tests/contact-service-router.test.ts tests/detail-surface-states.test.ts tests/ui-foundation-shell.test.ts
npm run typecheck
Set-Location ..
git add web-nuxt/pages/danh-ba.vue web-nuxt/pages/dia-diem/[id].vue web-nuxt/pages/xa-phuong/[id].vue web-nuxt/pages/lien-he.vue agent/public_api.py web-nuxt/tests/correction-entrypoints.test.ts web-nuxt/tests/contact-service-router.test.ts agent/tests/test_legacy_correction_adapter.py
git commit -m "feat: route public corrections to case kernel"
```

Review gate: compare the pre-edit dirty diff, verify one write authority per surface, no secret context in URLs, no unsupported capability/SLA copy, and no regression to shell or mobile bottom nav.

---

### Task 16: AdminCP Queue And Correction Workbench

**Files:**
- Create: `web-nuxt/pages/admin/yeu-cau.vue`
- Create: `web-nuxt/components/admin/cases/CaseQueue.vue`
- Create: `web-nuxt/components/admin/cases/CaseWorkbench.vue`
- Create: `web-nuxt/components/admin/cases/EvidencePanel.vue`
- Create: `web-nuxt/components/admin/cases/ChangeSetDiff.vue`
- Create: `web-nuxt/components/admin/cases/AssistedCorrectionForm.vue`
- Create: `web-nuxt/composables/useAdminCases.ts`
- Modify: `web-nuxt/utils/adminNavigation.ts`
- Modify: `web-nuxt/utils/adminAccess.ts`
- Modify: `web-nuxt/pages/admin/bao-cao.vue`
- Test: `web-nuxt/tests/admin-case-workbench.test.ts`
- Test: `web-nuxt/tests/admin-case-scope-ui.test.ts`

**Interfaces:**
- Produces queue grammar `Queue -> Promise health -> Owner -> Next action` and action visibility derived from server-returned grants plus local route scope.
- Admin UI sends `expectedRevision` on every command and handles 409 by reloading/rebasing, never blind retrying.

- [ ] **Step 1: Write failing workbench and scope-visibility tests**

Require priority reason, promise health, owner, next action, target/field risk, evidence level/provenance, before/after diff, bounded decision reasons, publication verification, interaction timeline, safe-message preview, lease countdown, step-up prompt/expiry state for private evidence, and assisted form. Assert no generic resolve/dismiss button; hidden UI never substitutes for backend authorization; revision conflict shows current snapshot and requires user re-apply.

- [ ] **Step 2: Run tests and verify RED**

```powershell
Set-Location web-nuxt
npm test -- --run tests/admin-case-workbench.test.ts tests/admin-case-scope-ui.test.ts
Set-Location ..
```

Expected: page/components/composable/navigation entry are absent.

- [ ] **Step 3: Implement density-aware queue and workbench**

Desktop uses a resizable queue/workbench split; tablet collapses to queue then case; mobile AdminCP uses a single stacked task view. Preserve Nocturne typography/color tokens but prioritize operational density, explicit state, and legible diffs. Do not encode risk only by color. Lease state, promise breach, and publication recovery require text/icon labels and live-region updates.

- [ ] **Step 4: Replace correction use of the legacy reports page**

Keep moderation reports on `/admin/bao-cao`; add a clear route to canonical correction work and stop offering `resolved/dismissed` controls for imported/canonical correction rows. Legacy archive rows are read-only with import/reconciliation linkage.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
Set-Location web-nuxt
npm test -- --run tests/admin-case-workbench.test.ts tests/admin-case-scope-ui.test.ts tests/admin-access.test.ts tests/admin-provisional-review.test.ts
npm run typecheck
Set-Location ..
git add web-nuxt/pages/admin/yeu-cau.vue web-nuxt/components/admin/cases/CaseQueue.vue web-nuxt/components/admin/cases/CaseWorkbench.vue web-nuxt/components/admin/cases/EvidencePanel.vue web-nuxt/components/admin/cases/ChangeSetDiff.vue web-nuxt/components/admin/cases/AssistedCorrectionForm.vue web-nuxt/composables/useAdminCases.ts web-nuxt/utils/adminNavigation.ts web-nuxt/utils/adminAccess.ts web-nuxt/pages/admin/bao-cao.vue web-nuxt/tests/admin-case-workbench.test.ts web-nuxt/tests/admin-case-scope-ui.test.ts
git commit -m "feat: add correction case workbench"
```

Review gate: test each scope independently, lease expiry/revision conflict, keyboard-only operation, diff comprehension without color, mobile density, and absence of generic terminal actions.

---

### Task 17: Legacy JSONL Shadow Import, Reconciliation, Cutover, And Rollback Controls

**Files:**
- Create: `agent/cases/legacy_import.py`
- Create: `scripts/migrate_info_reports_to_cases.py`
- Modify: `agent/cases/store.py`
- Modify: `agent/config.py`
- Test: `agent/tests/test_case_legacy_import.py`
- Test: `agent/tests/test_case_legacy_reconciliation_postgres.py`
- Test: `tests/test_case_migration_cli.py`

**Interfaces:**
- Produces `classify_legacy_record(record) -> LegacyClassification`, `shadow_import(path, store, *, dry_run=True) -> ImportReport`, and `reconcile_import(run_id) -> ReconciliationReport`.
- CLI supports only `scan`, `shadow-import`, `reconcile`, and `freeze-correction-writes`; mutation commands require explicit disposable/target confirmation, immutable input digest, and pre-existing backup evidence.

- [ ] **Step 1: Write failing deterministic classification and replay tests**

Fixtures cover stale field/factual entity correction, post/comment policy violation linkage, ambiguous manual triage, duplicate lines, malformed lines, legacy `resolved`, contact without consent, and missing evidence. Assert `resolved` never maps to `corrected`, contact never maps to verified consent, duplicates create one case plus multiple locators, replay is idempotent, raw digest/line locator are retained, and source JSONL bytes are unchanged.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_legacy_import.py agent/tests/test_case_legacy_reconciliation_postgres.py tests/test_case_migration_cli.py
```

Expected: importer/CLI is missing.

- [ ] **Step 3: Implement dry-run-first shadow import and reject ledger**

Canonicalize each raw line for SHA-256 while preserving original line number/path. Classification is explicit and deterministic; ambiguous/safety-moderation rows create linkage/manual-triage records but no fabricated correction decision. Imported correction cases use `channel=legacy_import`, `reporter_privacy=legacy_unknown`, missing-data flags, no receipt capability delivered, no notification consent, and policy-derived manual triage.

- [ ] **Step 4: Implement reconciliation and irreversible correction-write freeze**

Reconcile source count, valid/rejected/duplicate/linkage totals, imported case/item totals, checksums, and unexplained status count; any mismatch fails cutover. Freeze stores a durable cutover marker in PostgreSQL and makes correction adapters refuse JSONL writes even if environment flags drift. Rollback may hide entrypoints or disable publication, but the Kernel remains write authority for already-cut-over corrections.

- [ ] **Step 5: Run GREEN gates and commit**

```powershell
python -m pytest -q agent/tests/test_case_legacy_import.py agent/tests/test_case_legacy_reconciliation_postgres.py tests/test_case_migration_cli.py agent/tests/test_legacy_correction_adapter.py
git add agent/cases/legacy_import.py scripts/migrate_info_reports_to_cases.py agent/cases/store.py agent/config.py agent/tests/test_case_legacy_import.py agent/tests/test_case_legacy_reconciliation_postgres.py tests/test_case_migration_cli.py
git commit -m "feat: migrate legacy correction intake safely"
```

Review gate: independently recompute checksums/count algebra, verify no source mutation or invented semantics, test duplicate replay, and prove correction JSONL writes cannot return after freeze.

---

### Task 18: Capacity Evidence, Retention, End-To-End Journeys, Accessibility, Privacy, And Operating Docs

**Files:**
- Create: `agent/cases/metrics.py`
- Create: `agent/cases/lifecycle.py`
- Modify: `agent/cases/public_api.py`
- Modify: `agent/cases/admin_api.py`
- Modify: `agent/cases/outbox.py`
- Modify: `agent/cases/work_control.py`
- Modify: `agent/cases/publication.py`
- Modify: `agent/scheduler.py`
- Modify: `agent/data_lifecycle.py`
- Create: `agent/tests/test_case_metrics.py`
- Create: `agent/tests/test_case_lifecycle.py`
- Create: `agent/tests/test_correction_journey_postgres.py`
- Create: `web-nuxt/tests/correction-accessibility-gate.test.mjs`
- Modify: `web-nuxt/scripts/check-public-accessibility.mjs`
- Modify: `scripts/smoke_e2e_chrome.mjs`
- Create: `docs/runbooks/correction-case-pilot.md`
- Create: `docs/runbooks/correction-case-incident.md`
- Create: `docs/runbooks/correction-case-cutover.md`
- Create: `docs/superpowers/results/2026-08-12-correction-case-pilot.md`

**Interfaces:**
- Produces privacy-safe `record_capacity_event`, `capacity_window(now) -> CapacityWindow`, `public_sla_eligible(window) -> False|EligibilityEvidence`, and `cleanup_case_data(*, now) -> CleanupSummary`.
- Metrics separate risk/channel and measure arrival/completion, backlog/ready/wait/touch time, rework, overturn, publication failure, WIP, coverage, breach, failure demand, repeated contact, and completion path; they contain no bearer/contact/evidence values.

- [ ] **Step 1: Write failing metrics, retention, journey, and accessibility gates**

Backend journey tests cover anonymous corrected projection, optional-phone consent and provider outage, authenticated link, phone-assisted reference/status, explicit Zalo AI handoff, R2/R3 maker-checker, confirmed current, insufficient evidence, ReviewCase, publication failure/recovery, legacy migration/reconciliation, and explicit user A/user B cross-case access denial for receipt, cookie, account link, evidence, and private note paths. Metrics tests require a continuous 28-day denominator that does not reset on deploy/restart and refuses public SLA eligibility at 27 days or with missing coverage. Lifecycle tests enforce policy retention and revocation cleanup without deleting immutable minimal audit/outcome evidence early.

- [ ] **Step 2: Run tests and verify RED**

```powershell
python -m pytest -q agent/tests/test_case_metrics.py agent/tests/test_case_lifecycle.py agent/tests/test_correction_journey_postgres.py
Set-Location web-nuxt; npm test -- --run tests/correction-accessibility-gate.test.mjs; Set-Location ..
```

Expected: metrics/lifecycle/journey gates and runbooks are absent.

- [ ] **Step 3: Implement capacity evidence and bounded lifecycle jobs**

Persist append-only operational events with case/risk/channel pseudonymous grouping and derived daily aggregates. Instrument the public/admin transports and service transitions at receipt, triage, waiting, update, decision, apply, verify, completion, repeated contact, provider failure, lease expiry, and recovery boundaries; do not infer touch/wait time from request logs. Eligibility requires 28 complete consecutive UTC days, named coverage, non-zero arrival/completion denominators, and no missing-day gaps; it only emits an internal evidence object and never flips public SLA automatically. Cleanup expires access/idempotency/challenges promptly, removes optional contact 90 days after terminal closure, removes encrypted private evidence/payload after 365 days unless legal/security hold is explicitly audited, retains minimal case/decision/publication/audit lineage for 730 days, then deidentifies capacity linkage. Register subject-linked case stores with purge/verify adapters while preserving legally required bounded audit records under explicit retained fields.

- [ ] **Step 4: Add browser, accessibility, privacy, and operational proof**

Extend browser smoke to execute create -> copy receipt -> exchange -> status using a disposable backend and fake provider; never print the capability in evidence. Accessibility gate covers keyboard, screen reader names/status, focus/error summary, 200% text, 320x256, 320x180, reduced motion, and no bottom-nav/action overlap. Runbooks name owner/duty coverage, queue/lease policy, provider outage, lost receipt limits, privacy/security escalation, publication rollback, flag sequencing, backup/shadow import/reconcile/freeze, degraded mode, and evidence artifact locations.

- [ ] **Step 5: Run GREEN full-pilot gates, record result, and commit**

```powershell
python -m pytest -q agent/tests/test_case_policy.py agent/tests/test_case_schema_postgres.py agent/tests/test_case_properties.py agent/tests/test_case_transaction_postgres.py agent/tests/test_case_access_security.py agent/tests/test_case_idempotency_postgres.py agent/tests/test_case_public_api.py agent/tests/test_case_outbox.py agent/tests/test_case_work_concurrency_postgres.py agent/tests/test_correction_changesets.py agent/tests/test_entity_write_transaction.py agent/tests/test_correction_publication.py agent/tests/test_assisted_correction.py agent/tests/test_case_legacy_reconciliation_postgres.py agent/tests/test_case_metrics.py agent/tests/test_case_lifecycle.py agent/tests/test_correction_journey_postgres.py
python -m ruff check agent/cases agent/entity_write.py agent/sms_provider.py
Set-Location web-nuxt
npm test -- --run tests/correction-case-contract.test.ts tests/correction-case-security.test.ts tests/correction-case-pages.test.ts tests/correction-entrypoints.test.ts tests/contact-service-router.test.ts tests/admin-case-workbench.test.ts tests/admin-case-scope-ui.test.ts tests/correction-accessibility-gate.test.mjs
npm run typecheck
npm run build
Set-Location ..
python scripts/checks/run_hard.py --all
```

Record exact commands, exit codes, PostgreSQL target identity class, skipped evidence, browser artifact paths, flag state, reconciliation counts, unresolved risks, and Definition Ladder level in the result document. Do not claim `production-proven`; flags remain false until separate owner-approved release admission.

```powershell
git add agent/cases/metrics.py agent/cases/lifecycle.py agent/cases/public_api.py agent/cases/admin_api.py agent/cases/outbox.py agent/cases/work_control.py agent/cases/publication.py agent/scheduler.py agent/data_lifecycle.py agent/tests/test_case_metrics.py agent/tests/test_case_lifecycle.py agent/tests/test_correction_journey_postgres.py web-nuxt/tests/correction-accessibility-gate.test.mjs web-nuxt/scripts/check-public-accessibility.mjs scripts/smoke_e2e_chrome.mjs docs/runbooks/correction-case-pilot.md docs/runbooks/correction-case-incident.md docs/runbooks/correction-case-cutover.md docs/superpowers/results/2026-08-12-correction-case-pilot.md
git commit -m "test: prove correction case pilot"
```

Review gate: map every acceptance item in spec section 14 and every pilot exit criterion in section 15 to a passing artifact or an explicit blocked gate; verify no public SLA, production-proof, claim/recovery/safety, or activation claim exceeds evidence.

---

## Execution Order And Review Protocol

1. Execute Tasks 1-10 in order; Task 3 policy may be reviewed independently, but persistence work must consume the locked vocabulary from Task 1 and schema from Task 2.
2. Task 11 is a mandatory publication prerequisite. Do not begin Task 12 until the transaction-aware entity writer passes both focused and compatibility suites.
3. Tasks 13-16 consume stable backend transport. Do not mock away authorization, receipt, decision/publication separation, or revision conflicts in UI tests.
4. Task 17 runs shadow/dry-run only during implementation. No real production import, freeze, or write-authority cutover is authorized by this plan.
5. Task 18 is the integrated evidence gate. All flags stay false after tests; activation belongs to a separate release-admission decision with named owner and capacity evidence.
6. For each task, the implementation worker commits, then a spec-compliance reviewer checks required behavior, then a code-quality reviewer checks correctness, security, maintainability, and test evidence. Fix findings before dispatching the next task.

## Completion Definition

The implementation plan is complete only when the correction vertical slice can demonstrate, against disposable PostgreSQL and browser evidence, one canonical path from every enabled self-service/assisted trigger through durable receipt, safe status, triage/work, evidence/decision, atomic publication, verified public projection, review, notification failure recovery, migration reconciliation, privacy lifecycle, and metrics--with no cross-case disclosure, lost receipt on committed intake, blind overwrite, generic terminal outcome, unsupported SLA, secret-bearing URI/storage/log/notification, or JSONL dual write.
