# Hardening Closure: verifiedAt, Release Scanner, and Bounded Egress

> STATUS: active - initial design and four optimization amendments approved by the project owner on 2026-07-27; awaiting final spec review before implementation planning. Source changes are not yet authorized.

## Decision

Close the three remaining hardening gaps in this order:

1. stop false field-verification claims derived from legacy top-level `verifiedAt`;
2. make repository and release-package scanners inspect the correct input domains;
3. complete the pinned outbound HTTP boundary with bounded bodies, bounded decompression, one end-to-end deadline, and real-httpcore transport tests.

The work remains one coordinated hardening tranche because all three changes are
required before the branch can claim a trustworthy green baseline. Each workstream
has an isolated contract, focused tests, and its own implementation commit. No data
migration, production mutation, push, or deployment is part of this design.

Planning is deliberately split after this umbrella decision: Plan A closes the
trust and scanner contracts, while Plan B completes egress and final truth-sync.
This keeps the small correctness fixes reviewable without placing the complete
transport change into the same execution context.

## Evidence Basis

The design is based on the current branch at revision `407c7a13` and direct
inspection or execution, not only on the previous plan text.

- `agent/pinned_http.py` calls `response.read()` for the final hop and applies the
  caller timeout again for every redirect hop.
- Installed HTTPX 0.28.1 joins decoded chunks in `Response.read()`. Its gzip decoder
  can expand one raw input chunk before application code can inspect the decoded
  size.
- A local reproducer expanded 32,636 encoded bytes into one 32 MiB decoded chunk,
  with about 81.15 MiB peak traced allocation. Reading the same response through
  `iter_raw()` yielded one bounded 32,636-byte encoded chunk.
- A real `httpcore.ConnectionPool` was exercised through a scripted socket pair and
  emitted a valid `GET / HTTP/1.1` request without live DNS or network access.
- `socket.getaddrinfo()` has no timeout parameter, so an HTTPX timeout alone cannot
  bound DNS wall-clock time.
- The local knowledge DB contains 1,751 entities and no
  `attributes.verifiedAt`. `web/data.json` contains 1,746 entities, all with a
  top-level `verifiedAt`, none with `attributes.verifiedAt`, and 1,702 values equal
  to `updatedAt`.
- The product claim is rendered from top-level `entity.verifiedAt` in
  `web-nuxt/pages/dia-diem/[id].vue`. The API freshness helper also trusts that
  top-level field.
- The duplicate-artifact scanner walks the ambient repository tree with `rglob()`.
  Nested `.claude/worktrees` therefore appear as duplicate release artifacts even
  though they are neither tracked repository members nor immutable package members.
- The official bounded backend regression passed at the inspected revision:
  Phase A reported `8534 passed, 58 skipped, 111 deselected, 1 xfailed`; Phase B
  reported `284 passed, 19 skipped`.

Durable baseline receipts from the research pass:

- stdout SHA-256: `6f280e611c190126369da41fdfdd25e7e76d9e408ff00b0a4910028958b3dae6`
- stderr SHA-256: `7d5273f65cba5bc8da849bd1562494e0d200ac2b512eb68a16a82e5ae49ce54`

## Goals

- Make `attributes.verifiedAt` the only field-verification authority everywhere in
  the public product.
- Prevent legacy or adversarial top-level `verifiedAt` values from creating a
  public field-verification claim.
- Make repository hygiene depend on tracked paths and package integrity depend on
  the immutable package snapshot, rather than ambient filesystem contents.
- Bound encoded response bytes, decoded response bytes, DNS concurrency, and total
  elapsed time for every call through the shared pinned GET client.
- Preserve the existing DNS and peer-pinning security boundary.
- Exercise the production `httpcore` composition seam through deterministic local
  scripted sockets.
- Finish with focused tests, Nuxt verification, hard checks, and a fresh official
  bounded backend regression.

## Non-Goals

- Do not rewrite the local DB or `web/data.json`; they are divergent sources and
  must not overwrite one another.
- Do not infer field verification from `updatedAt`, `createdAt`, `verified`, publish
  status, source presence, or data freshness.
- Do not add cookie-jar support for consent redirect gates.
- Do not add Brotli or deflate support in this tranche.
- Do not migrate crawler, geocode, realtime, scheduler, moderation, bot, OpenAI, or
  other outbound clients into `PinnedHTTPClient`.
- Do not add async egress, POST support, proxy support, arbitrary caller headers,
  authentication, HTTP/2, retries, or an external egress service.
- Do not add paid monitoring or external telemetry.
- Do not push, deploy, change secrets, enable indexing, or mutate production data.

## Workstream 1: Canonical Field-Verification Contract

### Authority

One focused accessor will define field-verification truth:

```python
def canonical_verified_at(entity: Mapping[str, object]) -> str | None:
    ...
```

The accessor reads only `entity["attributes"]["verifiedAt"]`. It returns a
normalized ISO value when the attribute is a supported date string and returns
`None` for missing, blank, malformed, or non-string values. It never reads the
top-level `verifiedAt` field and never falls back to another timestamp.

The accessor belongs beside the existing timestamp normalization contract in
`agent/database.py`, so internal serializers and the public API share one meaning.
The stale `_normalize_entity_timestamps()` documentation that says verified time
defaults to updated time must be corrected. Timestamp normalization stops creating
top-level `verifiedAt`, including when a genuine attribute exists, and removes a
legacy top-level value from normalized output. The attribute remains unchanged as
the single stored representation.

Future DB exports therefore carry field verification only inside `attributes`.
This tranche does not rewrite the already-divergent `web/data.json`; its legacy
top-level values remain historical input that all new code must ignore.

### Public API

`_build_source_freshness()` derives `verified_at`, `days_since_verified`, and
`freshness_status` only from `canonical_verified_at(entity)`.

The owned public projection removes top-level `verifiedAt` before returning an
entity. This is a defense-in-depth boundary: even if legacy input or an internal
caller contains a stale top-level value, public clients cannot accidentally adopt
it as a second verification contract.

`updated_at` remains a separate content/source update signal. It may affect an
"updated" label, but it cannot affect field-verification status or wording.

### Frontend

The entity-detail byline reads only `entity.source_freshness.verified_at`.

- A genuine value renders `Biên tập & kiểm chứng thực địa` with its formatted date.
- A missing or invalid value renders the existing truthful fallback
  `Tổng hợp & biên tập từ nguồn công khai - chưa kiểm chứng thực địa`.

The public TypeScript entity type removes the top-level `verifiedAt` member. The
`EntitySourceFreshness` type remains the only public carrier of `verified_at`.

### Adversarial Cases

Tests must prove all of the following:

- top-level `verifiedAt` plus no attribute yields `verified_at = None` and status
  `unknown`;
- conflicting top-level and attribute values use the attribute;
- recent `updatedAt` without the attribute cannot produce a fresh status;
- `verified = true` cannot produce a field-verification claim;
- malformed or blank attribute values remain unknown;
- timestamp normalization never creates a top-level mirror and removes a supplied
  legacy top-level value without changing `attributes.verifiedAt`;
- the public projection never exposes top-level `verifiedAt`;
- the frontend claim is driven by `source_freshness.verified_at`, not by a legacy
  field.

This workstream performs no data backup or migration because it changes code and
tests only. If later work edits entity rows or regenerates `web/data.json`, that is
a separate data task and must first run `python scripts/backup_data.py`.

## Workstream 2: Scanner Domain Separation and Plan Truth

### Pure Candidate Scanner

Duplicate detection will be split into a pure lexical validator and two candidate
providers. The validator receives explicit relative paths instead of discovering
paths with `root.rglob()`.

It continues to enforce these invariants:

- each canonical artifact name appears only at its approved `config/<name>` path;
- the canonical path is a regular non-symlink file;
- aliases, symlinks, directories, and duplicate lexical locations fail closed;
- diagnostics remain deterministic and sorted.

### Repository Hygiene Domain

The repository check obtains candidates from Git's index using a null-delimited
`git ls-files`. This includes committed files and files staged for a new commit,
while excluding nested worktrees, local caches, WAL files, build output, and other
untracked ambient content.

The repository test must fail if a duplicate canonical artifact is tracked or
staged anywhere outside the approved root config path. It must pass when the same
filename exists only inside an untracked nested worktree.

No path-specific ignore such as `.claude` will be added. The fix is the ownership
boundary, not a list of currently observed noise directories.

### Package Integrity Domain

Release construction validates canonical artifacts against the exact immutable
`_LaunchReleaseSnapshot.members` used to write the archive. An unrelated file in
the source tree cannot fail package validation if it is not a package member, and a
duplicate snapshot member cannot escape validation merely because the ambient tree
looks clean.

Preflight path-safety checks remain before snapshot collection. Canonical member
validation occurs after the snapshot is captured and before any destination archive
is replaced. Existing exact-byte loader tests continue to compare extracted bytes
with snapshot source bytes.

### Scanner Tests

Focused tests cover:

- tracked duplicate detection;
- staged-new duplicate detection where supported by the repository fixture;
- untracked nested-worktree noise being ignored by repository hygiene;
- canonical symlink and non-file rejection;
- duplicate immutable snapshot member rejection;
- ambient non-member duplicates not affecting package integrity;
- exact packaged bytes and failure-before-replacement behavior.

### Documentation Truth

The completed pinned-client implementation plan currently claims implementation
has not started. It will be changed to `STATUS: done` and receive a concise
`## KẾT QUẢ` section containing the actual implementation commits, verification
commands, baseline result, and remaining follow-ups.

Do not retroactively check every historical execution checkbox. The result section
is the authoritative completion record. `docs/HANDOFF.md` and `docs/ROADMAP.md`
will remove resolved scanner and verifiedAt items and retain only genuine residual
risks, including cookie-gate compatibility and any separately deferred egress
observability work.

## Workstream 3: Bound-Complete Pinned Egress

### Policy and Per-Call Budget

The shared client receives an immutable policy instead of independent optional
timeout and redirect arguments:

```python
@dataclass(frozen=True)
class EgressPolicy:
    max_encoded_bytes: int
    max_decoded_bytes: int
    accepted_encodings: tuple[str, ...]
    inactivity_timeout_seconds: float
    total_timeout_seconds: float
    max_redirects: int

@dataclass(frozen=True)
class DeadlineBudget:
    expires_at: float
```

`EgressPolicy` contains durations and limits only and may be safely reused. Each
`get()` call creates a fresh `DeadlineBudget` from `time.monotonic()`. An absolute
expiry must never be stored in a reusable policy.

The public call shape becomes `get(url, *, user_agent, policy)`. Separate `timeout`
and `max_redirects` arguments are removed so a caller cannot accidentally request
an unbounded body. Policy construction rejects non-positive byte limits or
durations, negative redirect limits, duplicate encoding tokens, and encodings
outside the supported `identity`/`gzip` set.

The budget exposes remaining time and a socket timeout equal to
`min(inactivity_timeout, remaining_total)`. Exhaustion raises one stable deadline
exception before new work starts. DNS, redirects, connect attempts, TLS, request
writes, response reads, and decoding all use the same budget.

### Consumer Profiles

The initial profiles are intentionally narrow:

| Consumer | Accepted encoding | Encoded cap | Decoded cap | Total/inactivity duration |
| --- | --- | ---: | ---: | --- |
| Admin image review | `identity` | existing `max_image_size` (currently 12 MiB) | same | 25 seconds |
| Auto-learn text | `identity`, `gzip` | 2 MiB | 2 MiB | 15 seconds |
| Quality-burst text | `identity`, `gzip` | 2 MiB | 2 MiB | existing caller value, default 12 seconds |

For the first implementation, inactivity duration equals total duration. This
preserves current caller tolerance while the shared absolute deadline closes
redirect and operation amplification. A later measured change may shorten idle
timeouts without changing the policy interface.

The 2 MiB text cap is a conservative starting value, not a measured optimum. Text
consumers retain only 6,000 or 5,000 characters, so the limit leaves substantial
headroom. It may be changed only from sanitized rejection evidence, in a separate
reviewed change.

### Explicit Request Encoding

The client sets `Accept-Encoding` explicitly from the policy. Environment-dependent
HTTPX defaults cannot advertise optional Brotli support.

- Image requests advertise `identity` and reject a non-identity response encoding.
- Text requests advertise `gzip, identity` and accept exactly one `Content-Encoding`
  token equal to `gzip` or `identity`.
- A missing or blank `Content-Encoding` is treated as `identity`.
- Brotli, deflate, stacked encodings, unknown tokens, and malformed headers fail
  closed.

Deflate is deferred because deployed servers disagree between zlib-wrapped and raw
framing. Supporting both is unnecessary until compatibility evidence identifies a
real source set that requires it.

### Bounded Raw Read and Gzip Decode

The final-hop response is consumed with `iter_raw()` so encoded bytes are counted
before HTTPX decompression. `Content-Length` may reject an obviously oversized
response early but is never trusted as the authoritative count. Chunked and missing
length responses use the same streaming limit.

At most `max_encoded_bytes + 1` encoded bytes are accepted for overflow detection;
the extra byte is never returned. Identity content uses the encoded buffer directly
after enforcing the decoded cap.

Gzip content is decoded incrementally with `zlib.decompressobj` and an output
`max_length` of remaining decoded capacity plus one. The decoder must drain
`unconsumed_tail` without allowing an unbounded output allocation. It requires a
complete stream, validates the checksum through zlib, rejects trailing concatenated
members or unused data, and never returns more than `max_decoded_bytes`.

Body, encoding, deadline, resolution saturation, and transport failures use stable
`PinnedHTTPError` subclasses. Consumers preserve their current external contracts:

- admin maps an over-limit image to its existing maximum-size validation response;
- admin maps encoding, deadline, and transport failures to the existing fetch
  failure response;
- auto-learn returns `None` after its existing warning behavior;
- quality-burst returns an empty string and remains silent as currently tested.

### Bounded DNS Resolution

System `getaddrinfo()` cannot be interrupted reliably. Resolution therefore uses one
process-wide four-slot gate backed by a bounded semaphore. There is no background
job queue and no executor. Waiting to acquire a slot consumes the caller's remaining
deadline; failure to acquire before expiry fails closed with a stable resolution
exception.

After acquiring a slot, the resolver starts one daemon thread for that resolution
and returns its result through a single-result handoff. The caller waits only for
the remaining request budget. If the request expires first, it discards any later
result; the daemon keeps its slot until `getaddrinfo()` finishes and releases it in
a `finally` path. At most four resolver threads can therefore exist, including when
system DNS is stuck, and no expired request can leave a queued DNS job that starts
later.

The existing rule that every returned address must pass public-address validation
stays unchanged. No unbounded per-request thread creation or
`ThreadPoolExecutor` shutdown wait is permitted. The four-slot limit is a module
constant rather than a new deployment service or paid dependency.

### Deadline Propagation Through Transport

The `DeadlineBudget` is passed through hop resolution, transport construction,
`_PinnedNetworkBackend`, and `_PinnedNetworkStream`.

- Each address attempt recomputes remaining total time.
- `connect`, TLS wrapping, `send`, and `recv` set the socket timeout to the lesser
  of inactivity and remaining total time.
- Partial writes recompute the timeout before every subsequent `send`.
- A zero-byte send becomes a typed write failure.
- A redirect consumes the existing budget; it never creates a new expiry.
- A final decode checks the budget while processing raw chunks and decoder tails.

Peer-address verification, original HTTP Host, TLS SNI, certificate validation,
GET-only behavior, no proxies, no retries, and one fresh HTTP/1.1 pool per hop remain
unchanged.

### Real-httpcore Transport Harness

The test harness uses the actual `_PinnedHTTPTransport` and
`httpcore.ConnectionPool` with a deterministic scripted socket supplied through the
existing socket-factory seam. It does not monkeypatch `ConnectionPool`, use
`httpx.MockTransport`, resolve live DNS, or open an external connection.

Required coverage includes:

- the exact request line and Host header emitted by real httpcore;
- complete fixed-length and chunked responses;
- partial sends followed by successful completion;
- zero send mapped to a typed write failure;
- peer mismatch before HTTP or TLS bytes are sent;
- closed-socket `is_readable` behavior matching httpcore's convention: a missing or
  negative file descriptor is treated as readable/terminal instead of leaking
  `ValueError`;
- response close and connection-pool close;
- deadline exhaustion during redirect, connect, partial write, slow read, and
  decode;
- exact encoded and decoded boundaries, boundary plus one, false Content-Length,
  malformed gzip, truncated gzip, gzip bomb, unsupported encoding, and stacked
  encoding.

The 32 MiB gzip reproducer is converted into a regression test with a 1 MiB decoded
test policy. The compressed fixture is created before allocation tracing begins.
The test requires exact rejection at the decoded cap and peak traced allocation no
greater than eight times `max_decoded_bytes` (8 MiB for this policy). The relative
ceiling tolerates Python allocator differences while still failing any regression
whose memory use scales with the bomb's 32 MiB decoded size.

## Implementation Boundaries, Plan Split, and Commit Order

Two implementation plans will be written from this spec after final owner approval.

- **Plan A - Trust and scanner correctness:** commits 1 and 2 below. It ends with
  focused backend/frontend tests, Nuxt typecheck/build, and hard checks. Its owned
  diff is fully committed; unrelated user or runtime files remain untouched and are
  reported rather than treated as plan output.
- **Plan B - Bound-complete egress:** commits 3 through 7 below. It starts only after
  Plan A is complete and verified, then owns the fresh official backend regression
  and final documentation truth-sync.

Both plans must preserve this overall sequence and leave the repository green after
every commit:

1. `fix: make field verification attribute-authoritative`
   - failing backend and frontend contract tests first;
   - canonical accessor, no-mirror normalization/export contract, API projection,
     frontend byline, type and stale comments;
   - no data files.
2. `fix: scope release artifact scanners to owned inputs`
   - failing tracked-path and snapshot-member tests first;
   - pure candidate scanner and the two domain providers.
3. `test: specify bounded pinned response behavior`
   - policy, body, encoding, allocation, and real-httpcore RED tests.
4. `fix: bound pinned response bodies and decompression`
   - policy contract, raw reader, identity and bounded gzip decoding.
5. `fix: enforce one pinned egress deadline`
   - resolver gate, per-call budget, backend/stream propagation, transport edges.
6. `refactor: migrate pinned egress consumer profiles`
   - admin, auto-learn, and quality-burst adapters with preserved outward behavior.
7. `docs: close pinned hardening follow-ups`
   - plan result truth, ROADMAP, HANDOFF, exact verification receipts and residuals.

If a commit changes production behavior, it must include its paired tests as
required by the repository standards. Either plan may split a listed commit further
if necessary, but neither may combine independent workstreams into a single
production commit or move egress work into Plan A.

## Verification

Plan A uses focused trust, scanner, frontend, and hard-check gates. Plan B reruns its
focused transport/consumer suites and then owns the one fresh full frontend and
official bounded-backend baseline for the final candidate. The split avoids paying
the roughly 90-minute backend baseline after both plans while retaining one
revision-bound final proof.

### Focused Backend

Run the affected suites, including:

- `agent/tests/test_public_api.py`
- `agent/tests/test_upgrade_phase1.py`
- `agent/tests/test_database.py`
- `tests/test_export_data.py`
- `tests/launch_safety/test_artifact_packaging.py`
- `tests/launch_safety/test_release_package.py`
- `tests/test_pinned_http.py`
- `tests/test_pinned_http_consumers.py`
- `tests/test_admin_pinned_http.py`
- focused auto-learn and quality-burst tests selected by node ID or `-k`

### Frontend

Add a focused Vitest contract for the entity byline, then run:

```powershell
cd web-nuxt
npm test
npm run typecheck
npm run build
```

### Repository Gates

Run:

```powershell
python scripts/checks/run_hard.py --all
git diff --check
python scripts/ops/run_backend_regression.py --deadline-seconds 7000
```

Any new failure stops the tranche for diagnosis. Assertions must not be weakened to
make a regression green. Final documentation records exact counts, exit codes,
revision, command lines, and durable receipt hashes.

## Acceptance Criteria

- No public rendering or API contract treats top-level `verifiedAt` as field
  verification.
- Timestamp normalization and future DB exports do not emit top-level `verifiedAt`.
- An adversarial legacy top-level value cannot produce a verified byline or fresh
  verification status.
- No entity/data file is rewritten as part of the trust fix.
- Repository duplicate checks are based on Git-index members.
- Release duplicate checks are based on immutable snapshot members.
- Nested untracked worktrees cannot create false scanner failures.
- Every pinned GET has explicit encoded and decoded caps and a fresh absolute
  monotonic deadline.
- DNS resolution has at most four active daemon threads, no background job queue,
  and fails closed when a slot cannot be acquired inside the request deadline.
- Admin images accept identity only; text accepts identity and bounded gzip only.
- The default production transport composition runs under real httpcore in tests.
- The gzip-bomb allocation test uses a policy-relative ceiling and cannot pass if
  memory scales with the bomb's decoded size.
- Destination validation, exact-sockaddr dialing, peer verification, TLS hostname
  verification, and redirect revalidation remain covered and unchanged.
- Focused backend, frontend tests, typecheck, build, hard checks, and the official
  bounded backend regression all pass on the final candidate revision.
- The prior pinned-client plan truthfully reports completion and remaining
  residuals.
- Plan A completes and verifies trust/scanner work before Plan B begins egress and
  final truth-sync.

## Residual Risks

- A system DNS call may remain blocked after its request times out. Its resolver
  slot remains occupied until the OS call returns; four stuck calls therefore make
  later resolutions fail closed until capacity recovers.
- The initial 2 MiB text cap may reject an unusually large legitimate page.
- Sites that ignore `Accept-Encoding` or require Brotli/deflate will fail closed.
- Consent-cookie redirect gates remain unsupported.
- Production behavior remains unproven until a separately authorized deployment
  and observation pass; this design authorizes neither.
