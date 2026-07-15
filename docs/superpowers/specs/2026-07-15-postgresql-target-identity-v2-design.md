# PostgreSQL Target Identity v2 Design

> STATUS: owner-approved design; written spec awaiting review; implementation planning not yet authorized; Stage B must be regenerated; Stage C remains unauthorized

## 1. Goal

Make the PostgreSQL publication-migration target fingerprint identify the exact
database inside the exact PostgreSQL cluster, even when the connection reaches
production through an SSH tunnel whose visible server address is loopback.

The same work must ensure that Stage B artifacts are private before sensitive
database bytes are written and that the completed Stage B package contains
durable, credential-free evidence for live global noindex and operational
cleanup. No part of this design authorizes `apply`, rollback, export, indexing
activation, or application-data mutation.

## 2. Fixed Owner Decisions

1. Use PostgreSQL identity v2 rather than an SSH-host-only attestation.
2. Identity v2 includes the cluster `system_identifier` and current database
   OID in addition to the existing database/server fields.
3. Legacy identity v1 artifacts are rejected; there is no silent fallback.
4. A Stage B artifact root is ACL-protected before `pg_dump` or plan output is
   written.
5. Stage B writes a canonical evidence attestation after the temporary role is
   deleted and the SSH tunnel is closed.
6. Production remains globally `noindex, follow` throughout the work.
7. A temporary PostgreSQL role may be created only for one Stage B run, with
   read-only privileges, a short expiry, and mandatory cleanup.
8. Stage C still requires separate owner authorization naming the exact v2
   target fingerprint and newly generated artifact hashes.

## 3. Current Failure Mode

Identity v1 hashes this tuple:

```text
database
server_addr
server_port
server_version_num
```

Through the approved SSH tunnel, production reports
`127.0.0.1/32:5432`. Another PostgreSQL 16 cluster containing a database named
`vinhlong360` can produce the same tuple. The resulting fingerprint therefore
does not prove that a later apply command has reached the reviewed production
cluster.

The first Stage B artifact also inherited read access for the local
`CodexSandboxUsers` principal. The ACL has since been restricted without
changing artifact bytes, but security must be established before future dump
creation rather than repaired afterward.

Finally, live noindex and temporary-role cleanup were verified during the run
but were not persisted beside the immutable plan and backup. A later reviewer
must not depend on transient terminal output to reconstruct those gates.

## 4. PostgreSQL Identity v2 Contract

### 4.1 Canonical identity

`scripts/postgres_target.py` defines one exact identity revision:

```text
identity_revision = postgres-cluster-v2
database
database_oid
system_identifier
server_addr
server_port
server_version_num
```

`database_oid` is the OID of `current_database()` from `pg_database`.
`system_identifier` is the decimal text value returned by
`pg_control_system()`. Both values are serialized as strings or integers in one
documented form and never depend on locale or display formatting.

The target fingerprint is SHA-256 over canonical JSON containing exactly the
ordered v2 identity fields. Credentials, SSH hostnames, temporary role names,
and passwords are excluded.

### 4.2 Read query

`read_target_identity()` performs one read-only query that obtains the current
database name and OID, cluster system identifier, server address and port, and
server version. Missing rows, NULL fields, unexpected types, lack of permission
to call `pg_control_system()`, or an unsupported identity revision are fatal.

The temporary Stage B role receives only the additional EXECUTE privilege
needed for `pg_control_system()`. It remains transaction-read-only and retains
no write, DDL, ownership, bypass-RLS, replication, database-creation, or
role-creation capability.

### 4.3 Legacy rejection

Backup manifests, plans, apply reports, and rollback reports must contain
`identity_revision = postgres-cluster-v2`, `database_oid`, and
`system_identifier`. Validators reject identity v1 artifacts with an explicit
target-identity-revision error before comparing confirmation hashes or entering
an apply transaction.

Existing v1 Stage B artifacts remain immutable evidence but are marked
superseded and are never eligible for Stage C.

## 5. ACL-First Artifact Boundary

Before creating a backup directory, dump, manifest, plan, pending hardlink, or
attestation, the Stage B runner creates a new root with a protected Windows
DACL. The only allowed principals are:

```text
the identity returned by WindowsIdentity.GetCurrent().Name
NT AUTHORITY\SYSTEM
BUILTIN\Administrators
```

Each allowed principal receives FullControl. The root is protected before any
sensitive write. New descendants may initially inherit only these safe root
rules; after Stage B writes complete, the ACL normalizer converts every
descendant to a protected DACL with the same three explicit principals.

The runner verifies the root immediately after creation and verifies every
descendant after Stage B. During creation, an inherited ACE is accepted only
when it comes from the protected Stage B root and names an allowed principal.
Final attestation requires every object to be protected with explicit rules.
Any unexpected principal, inherited rule from outside the root, reparse point,
alternate data stream, unreadable artifact, or ACL application failure stops
the run before apply and preserves evidence for inspection.

The existing `write_exclusive()` pending paths remain intentional hardlinks.
They must stay inside the protected root and match their canonical published
file by file identity, size, and SHA-256.

## 6. Canonical Stage B Attestation

After backup and plan succeed and after cleanup is verified, a tracked helper
writes `stage-b-attestation.json` with canonical UTF-8 JSON bytes. It contains:

- schema and attestation revision;
- source HEAD and clean-worktree result;
- plan, manifest, dump, and restore-list SHA-256 values;
- v2 target identity and fingerprint;
- live noindex URL, UTC timestamp, HTTP status, exact header value, robots-meta
  count/value, and response-body SHA-256;
- temporary role name, expiry, and a fresh `role_absent = true` check timestamp;
- local tunnel endpoint, PID used during Stage B, and fresh evidence that the
  process and listener are absent;
- ACL verification summary and allowed-principal inventory;
- `apply_run = false`, `rollback_run = false`, `export_run = false`, and
  `deploy_run = false`.

The attestation contains no password, connection URL, password hash, session
token, OTP, private key data, or raw database row. Its own SHA-256 is recorded
when Stage B is handed to the owner.

The writer refuses to create an attestation if cleanup, live noindex, artifact
hashes, ACL checks, source revision, target identity, or freshness checks fail.

## 7. Temporary Role and Tunnel Lifecycle

The tracked PowerShell runner `scripts/run_entity_status_stage_b.ps1` delegates
ACL operations to `scripts/secure_stage_b_artifacts.ps1` and canonical evidence
writing to `scripts/stage_b_attestation.py`. It performs this sequence:

1. Verify source guardrails and live global noindex.
2. Create and verify the protected artifact root.
3. Open a loopback-only SSH tunnel.
4. Create a random, expiring PostgreSQL role with `pg_read_all_data`, database
   CONNECT, and only the EXECUTE privilege required for identity v2.
5. Set `default_transaction_read_only = on`, `statement_timeout = 5min`, a
   two-hour expiry, and connection limit 2.
6. Verify v2 identity and read-only mode through the tunnel.
7. Run exactly one PostgreSQL backup.
8. Run exactly one `published-v1` plan if backup succeeds.
9. Revoke privileges, drop the role, close the tunnel, and verify both absent.
10. Write and validate the canonical Stage B attestation.

The password exists only in process memory. It is not written to disk, printed,
passed in a process argument, stored in User/Machine environment scope, or
included in an artifact.

Cleanup runs in a mandatory finally path. A cleanup verification failure is a
blocking incident even if backup and plan succeeded.

## 8. Artifact and Validation Flow

The backup manifest and migration plan both embed the same v2
`database_identity` and `target_fingerprint`. Apply later recomputes v2 identity
from its own connection and refuses any mismatch before acquiring write locks.

Stage B review validates:

- canonical JSON bytes and raw/canonical hashes;
- custom-format dump size, SHA-256, `pg_restore --list`, and required tables;
- v2 identity equality across manifest, plan, and attestation;
- schema fingerprint and exact column inventory;
- sorted unique candidate IDs, count, and candidate hash;
- before/after status accounting and every exclusion reason;
- backup and plan age limits;
- source revision and live global noindex;
- protected ACLs, role deletion, tunnel closure, and `apply_run = false`.

Any mismatch marks the package unusable. Review never repairs plan, manifest, or
dump bytes in place.

## 9. Failure Handling

- Identity permission or query failure stops before backup.
- ACL failure stops before sensitive output is written.
- Backup failure prevents plan creation.
- Plan failure preserves the validated backup but does not retry automatically.
- Cleanup always runs; cleanup failure blocks attestation and Stage B approval.
- Attestation failure leaves backup and plan unapproved and ineligible for
  Stage C.
- Identity v1 artifacts produce an explicit superseded/legacy error.
- No failure path calls apply, rollback, export, deploy, or indexing activation.

## 10. Test Strategy

Required RED/GREEN coverage includes:

- exact v2 identity query shape and type normalization;
- fingerprint changes for system identifier or database OID changes;
- credential-independent deterministic fingerprints;
- explicit rejection of every identity v1 artifact consumer path;
- backup/plan/apply/rollback agreement on identity v2;
- PostgreSQL integration using a disposable cluster and a restricted role;
- permission-denied behavior for `pg_control_system()`;
- protected-root creation and recursive ACL verification on Windows;
- refusal of inherited sandbox/user principals and reparse points;
- canonical attestation writing and secret-field rejection;
- live noindex, role-absence, and tunnel-closure attestation failures;
- unchanged pending-hardlink integrity and dump restore-list validation;
- proof that no Stage B path invokes apply or mutates application rows.

## 11. Rollout and Supersession

Implementation is committed and reviewed before touching production again.
The corrected Stage B run uses a fresh artifact root, fresh temporary role, and
fresh SSH tunnel. It does not reuse the current v1 plan, manifest, dump, target
fingerprint, or confirmation values.

After the v2 package passes spec and quality review, a protected canonical
supersession marker is added beside the v1 package. The marker names the v1
artifact hashes, reason `target-identity-v1-not-unique`, and the replacement v2
artifact root/hash. It does not modify the v1 plan, manifest, or dump.

Stage C remains a separate decision. Its future authorization must name the v2
target fingerprint, plan SHA-256, backup-manifest SHA-256, dump SHA-256,
attestation SHA-256, candidate count, and candidate-ID hash.

## 12. Non-Goals

- no production apply, rollback, export, deploy, or data-row mutation;
- no reading or copying the existing production `DATABASE_URL` or password;
- no public PostgreSQL port or persistent tunnel;
- no SSH-host-only target identity;
- no support for identity v1 in Stage C;
- no deletion of existing Stage B evidence;
- no indexing activation or legal-gate inference.

## 13. Acceptance Criteria

The design is satisfied only when:

- every target-bearing artifact and runtime check uses identity v2;
- system identifier and database OID changes alter the fingerprint;
- identity v1 is explicitly rejected before apply logic;
- the Stage B root is private before the dump is created;
- backup, plan, and attestation are canonical, fresh, hash-consistent, and
  restorable/listable;
- source and live global noindex evidence agree;
- the temporary role and tunnel are independently verified absent;
- no credential is present in command lines, logs, environment persistence, or
  artifacts;
- spec and quality review approve the regenerated Stage B package;
- `APPLY_NOT_RUN` remains true.
