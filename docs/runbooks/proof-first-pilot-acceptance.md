# Proof-first closed-pilot acceptance

Authority: config/release-authority.json

> STATUS: active — updated 2026-09-02. Documents the `--postgres-proof` flag, the
> four attestation roles, the independent countersigner, and the honest limits of
> a signature held on the same machine as the editor.

## Purpose and boundary

This runbook produces local, reproducible evidence for the correction-case
closed pilot. It is a release-control artifact, not a public-launch approval.
The gate can return `GO_CONDITIONAL` only after every P1 finding has complete
layered evidence and an owner sign-off. `NO_GO` is the expected result while a
required environment or decision gate is unavailable.

No production/provider calls, secrets, or raw personal data are allowed.

## Run

From the repository root:

```powershell
# The DSN is read from the environment, never from argv.
$env:VL360_TEST_DATABASE_URL = 'postgresql://vl360:vl360@127.0.0.1:55432/<db>'
python scripts/ops/run_pilot_acceptance.py `
  --root . `
  --database-target disposable-postgres `
  --postgres-proof `
  --external-sandbox
```

`--postgres-proof` (`scripts/ops/run_pilot_acceptance.py:1254`) is what turns the
PostgreSQL layer from a declared gap into a real capture. Without it every
section records the named gap `postgres-proof-not-requested`
(`scripts/ops/run_pilot_acceptance.py:1129`).

**The DSN never appears in argv.** `_loopback_pg_dsn()`
(`scripts/ops/run_pilot_acceptance.py:935-955`) reads only the environment
variable `VL360_TEST_DATABASE_URL`, and refuses anything whose host is not
`127.0.0.1`, `::1`, or `localhost`, and anything carrying `hostaddr`. There is no
`--dsn` flag on purpose: a credential in argv reaches the recorded command
string, the process table, and the shell history. The bundle records the source
as the literal string `pytest:VL360_TEST_DATABASE_URL`
(`scripts/ops/run_pilot_acceptance.py:994`), never the value.

The command writes `artifacts/pilot-acceptance.json` locally and prints the
P1 count, layer list, and gate decision. A non-zero exit is intentional for a
`NO_GO` result. Verify the artifact without mutating it:

```powershell
python scripts/ops/verify_release_bundle.py `
  --bundle artifacts/pilot-acceptance.json
```

## Evidence contract

The bundle has one section for each of the 28 P1 findings:
`F-01` through `F-17`, `F-32`, `F-34`, `F-38`, `F-40`, `F-41`, `F-42`,
`F-44`, `F-47`, `F-49`, `F-53`, and `F-69`. Each section records all five
layers: `unit`, `postgres`, `multi_process`, `browser`, and
`external_side_effect`.

Every layer records the exact command, sanitized environment, nodeids,
native return code, SHA-256 checksum, owner, outcome, and rollback note.
Disk free space before/after, Python/platform versions, and the repository HEAD
are recorded in the envelope. Evidence is stale after 24 hours or when its
artifact identity/revision cannot be established.

Unavailable infrastructure is recorded as an explicit `UNCLASSIFIED` gap,
for example `docker-cli-unavailable`, `browser-base-url-not-supplied`, or
`external-sandbox-not-enabled`. It must never be replaced with a synthetic
pass receipt.

`docker info` is an availability probe only. It may document that a disposable
target can be provisioned, but it is not PostgreSQL acceptance proof. A passing
PostgreSQL layer must run the repository-local integration/drill command against
the explicitly named disposable target and capture its native result.

## Gate rules

`evaluate_pilot_gate()` returns `NO_GO` when any P1 is missing, a section or
layer is stale, an outcome is `UNCLASSIFIED`/failed, cross-boundary proof is
missing, a required layer field is absent, or a `decisionRequired` item lacks
approval. It also rejects artifacts older than the configured 24-hour window.

`GO_CONDITIONAL` means closed pilot only: all P1 sections and layers pass,
cross-boundary proof is present, all decision-required items are approved, and
the service owner has signed off. It never means public-launch readiness;
public launch remains `NO_GO` until the separate legal, provider, staging,
backup, monitoring, and rollout decisions are closed.

The future drill command must create only hashed fixture identifiers and prove
the same case revision/generation at API, database, worker, projection, cache,
search, chat, review, and homepage boundaries. It must include stale/wrong-scope
evidence rejection, cross-user cache denial, a local object/provider failure
with retry/compensation, subject export, and dry-run erasure. Until that command
is captured, the relevant P1 layer remains `UNCLASSIFIED`.

## Attestations — four roles

`agent/control_plane/attestation.py:46` fixes the role tuple and
`config/release-authority.json` declares one key identity per role:

| Role | Key id | Custody | Question it answers |
|---|---|---|---|
| `runner` | `runner-local` | `environment:PILOT_ATTEST_RUNNER_KEY` | Which process emitted this bundle |
| `owner` | `owner-offline` | `offline-owner:/etc/vinhlong360/pilot-owner-signing.key` | Which human accepted it — never mintable by an agent |
| `countersign` | `countersign-local` | `environment:PILOT_ATTEST_COUNTERSIGN_KEY` | An independent re-execution saw the same outcomes |
| `ci` | `ci-hosted` | `ci-secret:PILOT_ATTEST_CI_KEY` | It was produced on hardware the local editor does not control |

All four must verify, no two roles may share a `key_id`, and `owner`/`ci` must
sit in independent custody (`agent/control_plane/attestation.py:257-278`;
independent custody classes are `ci-secret` and `offline-owner`, `:47-48`).
A role reached without its key is recorded as `scheme="unsigned"` with an empty
signature rather than silently skipped (`:156-162`). A missing key therefore
produces `NO_GO`, which is the intended behaviour, not a defect to route around.

**Status on this machine (2026-09-02): the keys are deliberately absent.** That
is the project owner's explicit choice, and it is why the gate stays `NO_GO`.
Do not create them to make a gate pass.

## Independent countersigner

```powershell
python scripts/ops/countersign_pilot_acceptance.py `
  --bundle artifacts/pilot-acceptance.json `
  --root .
```

`scripts/ops/countersign_pilot_acceptance.py` re-runs the tests that each `PASS`
record names and compares parsed outcomes — verdict, counts, node ids — with what
the record claims. Two properties matter and are deliberate
(`scripts/ops/countersign_pilot_acceptance.py:11-19`):

- The command string stored in the bundle is **never executed**. The tool rebuilds
  its own invocation from the record's `nodeids`, so a forged bundle cannot steer
  the countersigner at a command of its choosing.
- Byte equality is not required, because pytest prints durations; only the parsed
  outcome must match.

The receipt is written to `artifacts/pilot-countersignature.json` as a separate
artifact — a bundle is never edited in place. Exit code is `0` only when the
receipt is complete *and* carries a real signature; otherwise `2`
(`scripts/ops/countersign_pilot_acceptance.py:193`).

## Current reality (2026-09-02)

- Real disposable-PostgreSQL evidence exists for **3 of 28 P1 findings**: `F-42`,
  `F-49`, `F-53`, via `agent/tests/test_case_contention_postgres.py`
  (`scripts/ops/run_pilot_acceptance.py:381-396`). The other 25 carry the named
  gap `no-postgres-proof-mapped-for-finding` (`:1137`).
- Countersigner result: `complete=true`, `confirmed=3`, `expected=3`, covering
  `F-42/postgres`, `F-49/postgres`, `F-53/postgres` — but **unsigned**, because
  `PILOT_ATTEST_COUNTERSIGN_KEY` is absent.
- `unit`, `multi_process`, `browser`, and `external_side_effect` are
  `UNCLASSIFIED` for all 28 findings. **`unit` included.** An earlier run of this
  layer did not finish at all (`return_code: 124`, `captured_output` ending in
  `TIMEOUT`) because the drill inherited a 120-second default while the
  cross-boundary suite had grown past two minutes; that is fixed — the drill now
  gets 1800 seconds and the capture completes (`return_code: 0`, `95 passed`).
  It stays `UNCLASSIFIED` for the *correct* reason: one aggregate capture is not
  per-finding proof, so `_bind_evidence` downgrades it. The consequence is
  unchanged and must not be softened: **25 of 28 findings have zero passing
  layers**, and the other 3 have exactly one (`postgres`).
  There is also no evidence for HA/failover, backup →
  offsite → restore → checksum, staging rollout → smoke → rollback, or a real
  alert receiver. None of the infrastructure classes can be produced on a single
  laptop; record them as unavailable and never as a synthetic pass.
- Gate: **NO_GO**. Release verifier: **BLOCKED**. Correct, and it must stay that
  way until the missing evidence and decisions actually exist.
- `scripts/ops/run_pilot_acceptance.py`, `artifacts/pilot-acceptance.json` and
  this runbook are **untracked at HEAD** `7bd85e772843ac5ab3c7db656a1b0766aed8ede3`;
  the `pilot_acceptance` block in `config/release-authority.json` is an
  uncommitted diff. Nothing here is under CI custody yet.

## Honest limits — what these controls do not prove

Stated here because it must not be lost between the module docstring
(`agent/control_plane/attestation.py:22-28`) and this runbook:

- **HMAC is symmetric: verify capability equals forge capability.** A key readable
  on the same machine as the text editor that could rewrite the bundle raises the
  bar and records intent. It is **not a trust anchor against that editor**.
- Only two things reach further: **independent re-execution** (`countersign` —
  it carries re-observed fingerprints as data, so it tests the claim rather than
  the claimant) and **custody elsewhere** (`ci` — hardware the local editor does
  not control). This is why custody is recorded per key and why independence is
  reported rather than assumed.
- A checksum chain inside a bundle proves only internal consistency: every digest
  is a keyless function of text the author typed, so anyone holding the checkout
  can recompute all of it. Re-parsing `captured_output` at gate time
  (`scripts/ops/run_pilot_acceptance.py:138-186`, used at `:734-743`) removes the
  easiest forgery, not the whole class.
- A single-laptop run can never evidence multi-node behaviour, provider
  side-effects, or production topology, no matter how many local layers pass.

## Recovery and rollback

- Stop at the first `NO_GO`; keep the bundle for local diagnosis.
- Do not retry a provider or production operation from this runner.
- Destroy only explicitly disposable PostgreSQL/browser/sandbox targets after
  preserving their checksums and return codes.
- Correct the missing evidence or owner decision, rerun the complete command,
  and use the new artifact ID/revision. Never edit a bundle in place.
