# Entity Published-Status Migration Design

> STATUS: proposed; PostgreSQL-only direction approved; written-spec review required before implementation planning; no data mutation authorized by this document

## 1. Goal

Prepare a fail-closed, auditable PostgreSQL migration that annotates reviewed
legacy entity rows with `status = "published"` without weakening the launch
index policy, changing global `noindex`, or treating a local SQLite/database
export as production truth.

The migration exists to unblock the Task 9 data-readiness gate. It is not an
indexing activation. The index policy continues to decide whether published
content is sufficiently rich, and H1/H2 plus separate owner authorization
remain unresolved launch gates.

## 2. Fixed Owner Decisions

1. The real apply target is PostgreSQL only.
2. Local SQLite files and `web/data.json` are evidence inputs, not write
   authorities for this migration.
3. The only allowed state transition is `NULL -> published`.
4. Existing non-NULL statuses are never rewritten by plan, apply, or rollback.
5. Global `noindex` remains enabled before, during, and after the migration.
6. Production apply requires a separately supplied target context, a fresh
   PostgreSQL backup, the exact reviewed plan hash, and explicit confirmation.
7. The migration does not infer field verification. `verified` remains a
   publication/moderation flag and is not a substitute for `verifiedAt`.

## 3. Current Evidence

The read-only 2026-07-14 audit found:

- tracked `web/data.json`: 1,748 entities;
- continuation SQLite: 1,750 entities;
- main-worktree SQLite: 1,752 entities;
- all local entity rows have `status = NULL` and integer `verified = 1`;
- local SQLite contains persistent test fixtures and source divergence;
- no production PostgreSQL target was available in the process environment;
- the existing backup script does not create or verify a PostgreSQL backup;
- normal entity upsert/import paths do not yet preserve `status` and
  `verified` consistently.

These observations prohibit applying from a local count or copying either
local store over another. Production counts remain unknown until the plan
command reads the explicit PostgreSQL target.

## 4. `published-v1` Candidate Contract

A row is a candidate only when every rule below is true at plan time and again
inside the apply transaction:

1. `status IS NULL`.
2. `verified` is the exact database value representing true/1.
3. `type` is an exact reviewed non-place, non-itinerary type:
   `accommodation`, `attraction`, `cafe`, `craft_village`, `dish`, `drink`,
   `event`, `experience`, `facility`, `history`, `nature`, `organization`,
   `person`, `product`, or `restaurant`.
4. The row is not private, draft, provisional, unpublished, or explicitly
   non-public in top-level columns or structured attributes.
5. `source` contains at least one external HTTP(S) URL with a non-local host.
   A title-only source, empty list, local path, localhost URL, or the canonical
   site itself does not satisfy this rule.
6. The row is not on the reviewed exact exclusion list recorded in the plan
   artifact.

The migration deliberately excludes:

- all `place` rows until Task 10 reviews ward policy and place/self child-count
  semantics;
- all entity rows whose type is `itinerary`, because itinerary/share detail is
  fixed-noindex;
- test fixtures, known duplicates, and any unexplained target-only row until
  it receives explicit review.

The 130-word policy is not duplicated in the migration. Publication annotation
and indexability remain separate decisions; `index_policy.decide_entity()` is
the sole quality authority.

## 5. Architecture

### 5.1 Pure publication predicate

Create one pure Python predicate for the `published-v1` migration contract. It
returns stable exclusion reason codes and is shared by plan generation and
transactional re-evaluation. It does not call sitemap code and does not modify
an input mapping.

Task 9 code hardening is a prerequisite:

- require a reviewed exact non-place entity type;
- normalize descriptive text to NFC before duplicate comparison;
- count only tokens containing at least one Unicode letter;
- keep missing status fail-closed;
- use an explicit UTF-8 fingerprint canonicalization or reject non-ASCII
  semantic revision identifiers;
- report artifact-load failures as structured hard-check violations.

### 5.2 Migration utility

Create `scripts/migrate_entity_status.py` with three subcommands:

```text
plan
  --target pg
  --database-url-env <ENV_NAME>
  --policy published-v1
  --report-out <path>

apply
  --target pg
  --database-url-env <ENV_NAME>
  --plan <path>
  --backup-manifest <path>
  --confirm-target <fingerprint>
  --confirm-plan-sha256 <sha256>

rollback
  --target pg
  --database-url-env <ENV_NAME>
  --apply-report <path>
  --backup-manifest <path>
  --confirm-target <fingerprint>
```

Dry-run planning is the default behavior. No command may fall back to SQLite,
`web/data.json`, a default DSN, or a repository `.env` value.

### 5.3 Immutable plan artifact

The plan command writes canonical JSON containing:

- schema and policy revisions;
- target fingerprint without credentials;
- PostgreSQL server/database identity;
- schema/column fingerprint;
- exact candidate IDs in deterministic order;
- candidate count and SHA-256;
- exclusion counts by stable reason;
- current status groups;
- expected before/after counts;
- exact reviewed exclusions;
- creation timestamp and maximum allowed age;
- tool source revision.

Apply recomputes every field that can drift and refuses a mismatch. Editing the
plan invalidates its SHA-256 confirmation.

## 6. Backup Contract

Before apply, a hardened backup command must create a PostgreSQL custom-format
backup using `pg_dump -Fc` from the exact target. The backup manifest records:

- target fingerprint;
- start/end timestamps;
- command/tool versions;
- artifact path, size, and SHA-256;
- a successful `pg_restore --list` validation;
- required table presence;
- plan policy revision;
- maximum backup age.

Missing tools, incomplete output, wrong target, stale evidence, hash mismatch,
or failed restore-list validation is fatal. The existing JSON/SQLite snapshot
remains available for local work but cannot satisfy the PostgreSQL apply gate.

## 7. Apply Transaction

Apply uses one PostgreSQL `SERIALIZABLE` transaction:

1. acquire a migration-specific advisory lock;
2. verify target, schema, backup, plan hash, policy revision, and candidate hash;
3. `SELECT ... FOR UPDATE` the exact planned IDs;
4. re-run the pure candidate predicate;
5. refuse any count, value, exclusion, or status drift;
6. update only `status IS NULL` rows to `published`;
7. write same-transaction audit records with old/new values and plan hash;
8. verify updated and untouched counts;
9. commit and write an immutable apply report.

A second apply using the same plan must perform zero writes and return an
explicit already-applied result. It must not silently create a new plan.

## 8. Rollback

Rollback consumes the exact apply report and backup manifest. It restores
`published -> NULL` only for IDs whose recorded previous value was NULL and
whose current value is still the value written by this migration. Any manual
or later change causes rollback to refuse that row and abort atomically.

The backup remains the disaster-recovery authority; logical rollback is the
preferred first response when its drift checks pass.

## 9. Persistence and Round-Trip Safety

Before production apply, entity persistence must preserve `status` and
`verified` through:

- PostgreSQL insert/update paths;
- SQLite compatibility insert/update paths without `INSERT OR REPLACE` field
  loss;
- DB export to `web/data.json`;
- reviewed import/round-trip tests.

Generic AdminCP writes must not assign `published` implicitly or bypass the
candidate contract. The one-off migration remains a separate, audited tool.

## 10. Test Strategy

Required tests include:

- pure predicate boundary/type/source/private-status cases;
- exact reason ordering and input immutability;
- plan determinism, canonical JSON, ID/count/hash drift, and target mismatch;
- missing/stale/invalid backup refusal;
- PostgreSQL transaction, advisory lock, idempotency, concurrent drift, audit,
  and rollback using an opt-in disposable database;
- persistence round trips for `status` and `verified`;
- test isolation so repository tests cannot pollute the shared SQLite DB;
- Task 9 word/type/fingerprint/hard-check corrections;
- pre/post `X-Robots-Tag: noindex, follow` evidence;
- regression proving no sitemap/index activation occurs from migration tooling.

Docker/PostgreSQL integration may be skipped locally only with explicit
evidence that the runtime is unavailable. Unit and refusal-path tests remain
mandatory.

## 11. Execution Stages

### Stage A: engineering only

Implement and review the predicate, backup hardening, persistence fixes,
migration tool, tests, and runbooks. Use fake/disposable targets only. No real
environment value or data is changed.

### Stage B: production planning

Requires a separately supplied production target context. Run backup and plan,
then present the immutable candidate report to the owner. This stage performs
no updates.

### Stage C: production apply

Requires separate direct owner authorization for the exact target fingerprint,
plan hash, backup manifest, and candidate count. Apply, verify a zero-write
rerun, export DB to JSON, and record post-apply evidence. This design approval
does not itself authorize Stage C.

## 12. Non-Goals

- no local SQLite or `web/data.json` first-write migration;
- no database replacement or import from `web/data.json`;
- no place or itinerary status migration in `published-v1`;
- no policy relaxation for missing status, source, type, or verification;
- no indexing activation, key change, deployment, or H1/H2 inference;
- no broad AdminCP publication workflow.

## 13. Acceptance Criteria

The engineering work is accepted only when:

- all plan/apply/rollback paths are explicit-target and fail closed;
- PostgreSQL backup evidence is mandatory and validated;
- candidate semantics are implemented once and tested;
- apply is manifest-locked, transactional, audited, and idempotent;
- rollback is drift-safe and atomic;
- persistence cannot erase status/verified;
- local shared-DB test contamination is removed;
- Task 9 code-level findings are closed;
- global noindex evidence remains unchanged;
- no production apply occurs without the separate Stage C authorization.
