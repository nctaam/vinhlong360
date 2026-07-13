# Launch Safety Gate Design

> STATUS: proposed; awaiting written-spec review; implementation must not start; launch remains blocked

## 1. Goal

Define one fail-closed boundary for search indexing and AI-image disclosure
without enabling indexing in any deployed environment. The design makes the
current closed state deterministic, backend-independent, uncached, and
testable. It also defines a selective-open state that is exercised only in
tests in this workstream and cannot be reached through a partial environment
change, stale build output, missing policy evidence, or a duplicated quality
rule.

The required result is:

- production remains globally `noindex,follow`;
- public pages remain crawlable while sensitive routes remain crawl-blocked;
- closed mode advertises no sitemap and serves valid empty sitemap XML;
- a future selective-open process requires two exact keys, matching software
  policy evidence, H1/H2 completion, and separate owner authorization;
- backend entity responses and sitemap generation share one quality authority;
- every first-party rendering of current `entity.images`, including public,
  authenticated, and admin surfaces, discloses that the image is AI-generated,
  while review and other UGC photos are never mislabeled;
- a launch-compatible build contains no policy-bearing SWR or prerender output;
- rollback to closed matches the current single-host, single-`vl-nuxt` topology.

## 2. Owner Decisions

These are fixed inputs, not design questions:

1. Global `noindex` stays enabled.
2. H1 and H2 remain unresolved external launch gates.
3. This work does not claim or imply that either gate is cleared.
4. Every current value under `entity.images` is AI-generated.
5. AI images never count as real, documentary, on-site, or first-hand photos.
6. Disclosure option A is selected: disclosure appears at every first-party
   public, authenticated, or admin point where an entity image is used.
7. Selective-open behavior is test simulation only in this workstream.
8. No real environment value is changed.

H1 is the external legal-entity and NĐ147 registration/licensing gate. H2 is
the external ICT/data-counsel review of the site's legal classification and
cross-border data obligations. A later indexing change also requires separate,
explicit project-owner authorization. This spec resolves none of those gates.

Option A applies to more than the detail hero. The inventory includes hero,
thumbnail rail, gallery/lightbox, `EntityCard`, `SavedEntityCard`, listings,
search, nearby and recommendation cards, event thumbnails and related places,
admin entity/media/review tools, and any map/popup or other first-party renderer
that consumes `entity.images` or a representative entity-image value derived
from it. Dense cards and admin grids may use a short pill with an accessible full
description; expanded detail, preview, gallery, and lightbox surfaces show the
full copy.

## 3. Repository Evidence and Current Risk

The current repository can express conflicting launch signals:

- global head metadata says `index, follow` and advertises `/sitemap.xml`;
- request middleware separately emits a global `X-Robots-Tag` noindex header;
- Nuxt `routeRules` bake URL-only SWR into `.output` for public HTML and APIs;
- Nitro prerenders public pages into `.output`;
- the service worker caches HTML and successful responses without honoring
  response `no-store`;
- Nginx sends the root robots/sitemap paths directly to FastAPI;
- backend sitemap generation reads a mutable data source per endpoint, caches
  documents independently, and emits unpinned child URLs;
- the existing backend quality branch treats any image URL as a real image;
- the public gallery API mixes entity images and review photos without a
  machine-readable source classification;
- `EntityCard`, saved cards, event thumbnails, recommendation cards, detail
  media, share metadata, and structured data can render entity images without
  one shared disclosure descriptor;
- `web-nuxt/pages/admin/entities.vue`, `web-nuxt/pages/admin/media.vue`, and
  `web-nuxt/pages/admin/duyet-tu-hoc.vue` directly inspect or render entity image
  values without the shared source descriptor;
- `docker-compose.yml` has one Nuxt service/container, while production uses one
  systemd service named `vl-nuxt`; there is no current replica fleet to drain.
- `docker-compose.yml` also makes `nuxt` depend on `agent: service_healthy` and
  healthchecks the homepage, so the current local topology cannot demonstrate a
  backend-independent safe-closed Nuxt cold start.
- `docker-compose.yml` publishes agent port 8360 and Nuxt port 3000 on every
  host interface, both processes bind `0.0.0.0`, and the merged production
  Compose topology also inherits other non-Nginx host publications. It therefore
  does not enforce Nginx as the exclusive public ingress.
- both Nginx configs use prefix/regex backend locations without a segment-end
  boundary, so names such as `/systematic` can accidentally enter the `/system`
  backend family; the bot-gateway `/webhook` alias is outside the current route
  manifest inventory.
- `GET /api/entities/{entity_id}` currently advertises public caching, emits an
  ETag, and returns 304 for `If-None-Match`; that endpoint will become the
  entity/ward launch-policy decision carrier and cannot retain those HTTP cache
  semantics.

The current packaging boundary also matters:

- the canonical repository root has no `config/` directory yet;
- the Nuxt Docker build context is currently `web-nuxt/`, so it cannot consume a
  canonical root artifact without changing the build context;
- `scripts/deploy.sh` ships `.output` separately and the backend tarball does not
  include `config/`;
- production release root is `/opt/vinhlong360` and live Nuxt output is
  `/opt/vinhlong360/web-nuxt/.output`.

Baseline evidence before implementation remains:

- backend: 6168 passed, 47 skipped, 78 deselected, 1 xfailed, 1 warning;
- frontend serial: 8 files, 125 passed;
- frontend parallel timed out because of resource contention;
- the serial frontend pass is the accepted comparison baseline;
- the parallel timeout is not classified as a product regression.

New tests may increase counts. The baseline is comparison evidence, not a
requirement that totals stay fixed.

## 4. Architecture

### 4.1 Canonical Artifacts and Packaging Boundary

There is exactly one canonical copy of each reviewed JSON artifact:

- `config/launch-indexing-policy.json`;
- `config/ai-disclosure.json`.

No generated or hand-maintained duplicate JSON is allowed under `web-nuxt/`,
`agent/`, a test directory, or release staging. Tests may construct an explicit
temporary fixture and pass its path to a loader; production code has no fallback
artifact and no environment-controlled alternate path.

The packaging contract is normative:

- the Nuxt Docker build context becomes the repository root and selects
  `web-nuxt/Dockerfile`, so the Dockerfile can copy the exact root `config/`
  artifacts into the build;
- local Docker verification uses
  `docker build -f web-nuxt/Dockerfile .` from the repository root;
- the Nuxt build imports the root artifacts and records their exact SHA-256
  digests and reviewed revisions in its generated readiness manifest;
- the backend release tarball includes the root `config/` directory unchanged;
- Python production loaders resolve
  `<release-root>/config/<artifact>.json`, where release root is the parent of
  `agent/`; absence, duplicate selection, schema failure, or revision mismatch
  is fatal for open intent;
- TypeScript production loaders resolve only the artifact copied from that root
  build context; they do not fetch JSON over HTTP at runtime;
- an unpacked-release test extracts the backend tarball into a temporary release
  root and proves both loaders resolve the exact packaged bytes;
- layout tests fail if another file with either canonical artifact filename is
  introduced outside root `config/`.

The launch-compatible release/rehearsal package also records the source-
controlled production Nginx configs, production systemd unit/wrapper
definitions, rendered production Compose network audit, and the identity of the
excluded developer override. Installation may place those operational files in
host-specific locations, but the packaged bytes and rendered listener contract
are the review authority. An unpacked-release test proves the ingress artifacts
are present and that no production command selects the developer override.

Generated `.output` manifests and immutable sitemap bundles are operational
artifacts, not duplicate sources of policy truth.

The reviewed policy fingerprint is a build-pinned SHA-256 value over the backend
`index_policy` semantic revision, both canonical artifact revisions and digests,
the closed/selective-open response matrix revision, the cache-isolation and
service-worker rule revision, and the pinned sitemap-protocol revision. Nuxt and
backend compute or load the same reviewed input set; runtime code may not invent
a substitute fingerprint.

### 4.2 Launch Safety Decision

Nuxt owns one server-only `LaunchSafetyGate`. A policy-bearing request computes
one immutable base decision and passes it to head, response-header, robots, and
sitemap logic. Components do not reread environment values or make an
independent launch decision.

```text
LaunchSafetyDecision
  operational_state: closed | selective-open | failed-open
  indexing_posture: closed | selective-open
  policy_fingerprint: string | none
  route_manifest_revision: string | none
  backend_policy_revision: string | none
  sitemap_batch_revision: string | none
  sitemap_action: closed-empty | guarded-proxy | unavailable
  reason: closed-default | valid-two-key-unlock | invalid-configuration
          | owner-approval-missing | policy-attestation-unavailable
          | policy-mismatch | build-isolation-unsafe
          | entity-policy-unavailable | entity-policy-mismatch
          | sitemap-batch-unavailable | sitemap-evidence-mismatch
```

The exact two-key contract is:

1. `LAUNCH_INDEXING_MODE` equals `selective-open`.
2. `LAUNCH_INDEXING_OWNER_APPROVED` equals `true`.

Missing, blank, partial, unknown, case-changed, whitespace-padded, malformed, or
mismatched values produce a closed request. Aliases such as `1`, `open`,
`enabled`, or `TRUE` are invalid. The literal `true` is accepted only for the
owner-approval key. Unlock values remain private runtime configuration and are
never exposed in browser code, headers, logs, or generated artifacts.

Before both exact keys express open intent, a safe launch-compatible process
uses `operational_state=closed`, `indexing_posture=closed`, and
`sitemap_action=closed-empty`. It does not call the backend for launch readiness,
HTML, robots, or empty sitemaps.

After both keys express open intent, Nuxt must validate a backend attestation
whose policy fingerprint, route-manifest revision, and backend-policy revision
match the build. A matching attestation produces the base
`operational_state=selective-open`, `indexing_posture=selective-open`, and
`sitemap_action=guarded-proxy`. An unavailable, incomplete, malformed, stale, or
mismatched attestation produces failed-open only for the affected request and
readiness attempt. It does not mutate a process-global decision and does not
force unrelated concurrent or later requests into failed-open.

### 4.3 Public Response Contract and Entity-Scoped Failure

Nuxt owns `X-Launch-Indexing-Policy`. It is present exactly once on every public
HTML response and every response, including errors, from `/robots.txt`,
`/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml`. Its value is
exactly one of `closed`, `selective-open`, or `failed-open`.

Every selective-open public HTML or root SEO response carries these three
non-empty, matching evidence headers:

- `X-Launch-Policy-Fingerprint`;
- `X-Launch-Route-Manifest-Revision`;
- `X-Launch-Backend-Policy-Revision`.

Every successful selective-open sitemap response also carries:

- `X-Launch-Sitemap-Batch-Revision`.

A sitemap request containing exactly one `batch` query parameter and no other
query parameter also carries
`X-Launch-Sitemap-Requested-Batch`, whose value must exactly equal the
requested lowercase 64-character SHA-256 hex value and the served batch
revision. The echo header is
omitted when the active root index is requested without a batch parameter.

Closed and failed-open responses omit every evidence and batch-echo header.
Evidence values are reviewed opaque revisions only. They must not contain unlock
values, secret material, backend URLs, environment dumps, free-form failure
detail, or legal/owner evidence. Nginx preserves the Nuxt headers and neither
synthesizes nor overwrites them.

The entity/ward response contract distinguishes a valid negative decision from
a dependency failure:

- an exact, schema-valid response with `indexable=false` and matching
  fingerprint/revision is a valid policy result; the HTML request remains
  `operational_state=selective-open`, retains the three evidence headers, emits
  `noindex,follow`, remains `no-store`, retains the one selective-open sitemap
  discovery link, and does not add or remove any sitemap URL;
- an exact matching `indexable=true` may emit `index,follow` only when the path
  is canonical and the base decision is selective-open;
- a missing or malformed response, transport error, timeout, missing field, or
  fingerprint/revision mismatch is a dependency failure for that HTML request;
  that request becomes `operational_state=failed-open`,
  `indexing_posture=closed`, emits
  `X-Launch-Indexing-Policy: failed-open`, omits all evidence headers and the
  HTML sitemap discovery link, emits `noindex,follow`, and remains `no-store`;
- an entity/ward dependency failure never changes global readiness state, an
  active sitemap pointer, or another request's base decision.

The global sitemap link is
`<link rel="sitemap" type="application/xml" href="/sitemap-index.xml">`.
It appears exactly once only on fully attested selective-open HTML, including a
valid `indexable=false` entity page. Closed and failed-open HTML omit it.

### 4.4 Unconditional Build-Time Cache and Prerender Isolation

Launch compatibility is a build property, not a conditional process-start
route-rule branch. The launch-compatible Nuxt source and generated `.output`
must unconditionally remove SWR, ISR, route cache, and prerender from:

- every public HTML route;
- every `/api/**` response that can contain or feed public content, entity,
  ward, gallery, recommendation, event, or launch-policy decisions;
- the direct policy-bearing data aliases `/events`, `/recommend`, and `/seo/**`;
- `/robots.txt`, `/sitemap.xml`, `/sitemap-media.xml`, and
  `/sitemap-index.xml`;
- `/_internal/launch-readiness`.

No ordinary closed SWR exception exists. Closed, selective-open, and failed-open
policy-bearing Nuxt responses are dynamic and `Cache-Control: no-store`. The
exact FastAPI HTTP authority and its narrower endpoint inventory are defined in
Section 4.7.1; this Nuxt build rule does not silently reclassify every backend
API as policy-bearing. Only policy-neutral content-addressed assets such as
`/_nuxt/**`, reviewed fonts, icons, and static image assets may be cached or
emitted statically. Workstream 5 does not create custom policy cache keys.
Selective-open response caching remains a separately authorized Stage 3 design.

The build emits a generated readiness manifest inside `.output` that records:

- the exact root-artifact SHA-256 digests and revisions;
- the enumerated policy-bearing route classes;
- the compiled route-rule audit result;
- the list of generated public/prerender files;
- the expected service-worker version and rule digest;
- the launch-compatible build revision.

The generated manifest is evidence about output, not a policy source.

The service worker uses a new versioned policy-neutral asset cache. It returns
without `respondWith`, `cache.match`, `cache.put`, or fallback logic for every
navigation, every request accepting `text/html`, all four root SEO paths,
`/_internal/**`, every `/api/**` request, and every request whose cache mode is
`no-store`. It also bypasses the direct policy-bearing aliases `/events`,
`/recommend`, and `/seo/**`. Each remaining cache write checks response
`Cache-Control` and skips `no-store`. Activation deletes the legacy HTML cache
and every prior-version cache that could contain HTML, root SEO, API,
selective-open, or failed-open responses.

### 4.5 Exact Internal Readiness Contract

Nuxt exposes `GET /_internal/launch-readiness` on the container/process-local
listener only. Both Nginx configs must explicitly deny this path before their
catch-all proxy, so it is not a public health endpoint.

The endpoint returns `Cache-Control: no-store` and:

- HTTP 200 for safe closed when the build/output, route-rule, artifact, and
  service-worker checks pass and both exact open-intent keys are not present;
- HTTP 200 for safe selective-open only when the same isolation checks pass,
  both keys are exact, backend attestation matches, and the backend reports a
  valid active sitemap batch;
- HTTP 503 for any missing/corrupt readiness manifest, artifact digest or
  revision mismatch, policy-bearing prerender file, compiled SWR/cache rule,
  unsafe service-worker version/rule digest, failed cache purge declaration,
  failed backend attestation under exact open intent, or unavailable active
  sitemap bundle under exact open intent.

Ordinary closed readiness makes zero backend calls. Partial or malformed unlock
configuration remains closed and can return 200 only when all build-isolation
checks pass. The body contains stable machine-readable check names and reason
codes but no secrets or free-form environment data.

Docker healthcheck executes inside the Nuxt container against
`http://127.0.0.1:3000/_internal/launch-readiness`. The Docker/local deploy
harness uses `docker compose exec -T nuxt` to run that same container-local
probe before routing traffic. `scripts/deploy.sh` uses the endpoint from the
target execution context before its external verification; its current systemd
path uses the equivalent process-local loopback probe before Nginx is reopened.
A homepage 200 is not readiness.

The launch-compatible Compose topology removes the entire
`nuxt.depends_on.agent` relationship, including the current
`condition: service_healthy`, and any equivalent wrapper or deploy-harness wait
that prevents the Nuxt container/process from starting when the agent is absent
or unhealthy. The Nuxt Docker healthcheck uses only the container-local internal
readiness endpoint above. Compose, local deploy, and release harnesses may start
the backend independently, but ordinary closed Nuxt startup is never gated on
backend health or backend startup order.

With both exact open-intent keys absent or invalid, the Nuxt container/process
must cold-start while the agent is absent, return readiness 200 safe closed,
serve closed HTML/robots/empty-sitemap behavior, and make zero backend calls for
those launch-gate surfaces. Backend-dependent non-SEO application features may
remain unavailable; they do not change safe-closed launch readiness. With exact
open intent and the agent absent, the Nuxt process may start but internal
readiness returns 503 because attestation is unavailable; the process receives
no traffic. Any directly probed policy-bearing request follows the existing
failed-open response contract: noindex, `no-store`, no evidence headers, and no
selective-open sitemap discovery.

### 4.6 Route Manifest Schema, Normalization, and Initial Inventory

`config/launch-indexing-policy.json` has this normative logical schema:

```text
schema_version: integer
revision: non-empty reviewed string
canonical_origin: "https://vinhlong360.vn"
unknown_policy: "noindex-follow-public"
normalization:
  percent_decode: "utf8-once"
  encoded_separator_policy: "reject"
  dot_segment_policy: "reject"
  repeated_slash_policy: "redirect-canonical"
  trailing_slash_policy: "redirect-except-root"
  query_policy: "noindex-except-sitemap-batch"
exact_routes[]:
  path: canonical absolute path
  classification: indexable-public | noindex-follow-public
  sitemap: boolean
sensitive_prefixes[]:
  prefix: canonical segment prefix
  classification: crawl-blocked-sensitive
backend_ingress_exceptions[]:
  prefix: canonical segment prefix
  upstream: agent | bot-gateway
  review_reason: non-empty reviewed string
dynamic_templates[]:
  template: canonical path template
  authority: backend-entity | backend-ward | fixed-noindex
  sitemap: backend | false
```

Classification uses the request path, never host-supplied alternate origins.
Rules are applied in this order:

1. reject invalid percent escapes, invalid UTF-8, encoded `/` or `\\`, NUL,
   dot segments, or double-decoding candidates;
2. test both raw and once-decoded segment boundaries against sensitive prefixes;
3. canonicalize repeated slashes, unreserved percent encoding, and a trailing
   slash; safe GET/HEAD variants redirect to the canonical path and never emit
   indexable HTML themselves;
4. match exact routes;
5. match reviewed dynamic templates;
6. apply `unknown_policy=noindex-follow-public` to catch-all/404 routes.

Sensitive prefix classification wins every exact, template, redirect, and
catch-all overlap. Prefix matching is exact-segment matching after path
normalization: a prefix matches only itself or a descendant beginning with
`prefix + "/"`. Thus `/admin` matches `/admin` and `/admin/x` but not
`/administrator`, and `/system` matches `/system` and `/system/logs` but not
`/systematic`. The query string is removed before this comparison and never
changes sensitive classification. Both Nginx configs must use equivalent
end-or-slash boundary semantics for every backend-directed exact, prefix, or
regex location; a bare `location /api` or regex lacking `(?:/|$)` is invalid.
For public HTML, any non-empty query produces `noindex,follow` and is absent from
sitemaps; the sole query exception is the sitemap `batch` protocol defined in
Section 4.8.

The initial reviewed inventory derived from current `web-nuxt/pages` is:

| Classification | Exact routes/templates |
| --- | --- |
| `indexable-public`, sitemap exact | `/`, `/du-lich`, `/dia-diem`, `/san-pham`, `/ocop`, `/luu-tru`, `/le-hoi`, `/su-kien`, `/theo-mua`, `/ban-do`, `/tuyen-duong`, `/danh-ba`, `/gioi-thieu`, `/huong-dan`, `/huong-dan-thanh-vien`, `/lien-he`, `/chinh-sach-bao-mat`, `/dieu-khoan-su-dung` |
| `indexable-public`, sitemap exact | `/kham-pha/am-thuc`, `/kham-pha/thien-nhien`, `/kham-pha/van-hoa`, `/kham-pha/lang-nghe`, `/kham-pha/mua-sam`, `/khu-vuc/vinh-long`, `/khu-vuc/ben-tre`, `/khu-vuc/tra-vinh` |
| backend-delegated dynamic | `/dia-diem/{entity_id}` -> `backend-entity`; `/xa-phuong/{ward_id}` -> `backend-ward` |
| `noindex-follow-public`, excluded | `/tim-kiem`, `/lich-trinh`, `/tao-lich-trinh`, `/cong-dong`, `/bang-xep-hang`, `/bai-viet/{id}`, `/nguoi-dung/{id}`, `/lich-trinh/{id}`, `/lich-trinh-chia-se/{id}` |
| `crawl-blocked-sensitive` exact/prefix | `/_internal`, `/admin`, `/admin-api`, `/analytics`, `/api`, `/auth`, `/chat`, `/events`, `/feedback`, `/freshness`, `/health`, `/reload`, `/recommend`, `/seo`, `/system`, `/weather`, `/webhook`, `/welcome`, `/cai-dat`, `/tai-khoan`, `/da-luu`, `/thong-bao` |

Static sitemap generation includes only exact inventory entries whose
`classification=indexable-public` and `sitemap=true`. It does not crawl Nuxt
links or infer pages from the filesystem. Entity and ward templates are
delegated to backend policy. Itinerary, shared-plan, search, UGC detail, unknown
interest/area values, and catch-all routes remain noindex and excluded.

Python and TypeScript loaders validate the same schema, reject duplicate paths,
reject exact/prefix ambiguity not resolved by the precedence contract, and
compute the same revision. Parity tests run a shared corpus covering exact and
prefix overlap, encoded paths, trailing slashes, repeated slashes, query
strings, invalid escapes, dynamic templates, and catch-all behavior.

The initial `backend_ingress_exceptions` array is empty. A static parity test
extracts every location or alias that proxies to `vl360_agent` or `vl360_bots`
from both `nginx.conf` and `nginx-ssl.conf`, normalizes it to the same segment
boundary model, and requires it to be present in `sensitive_prefixes` or in an
explicit reviewed exception. This covers `/health`, `/analytics`, `/feedback`,
`/welcome`, `/reload`, `/system`, `/seo`, `/weather`, `/recommend`,
`/freshness`, `/chat`, `/events`, `/api`, `/auth`, `/admin-api`, and the
bot-gateway `/webhook` alias. An unknown backend ingress, an exception without a
review reason, or drift between the HTTP and HTTPS configs fails the test.

### 4.7 Backend Indexability Authority

The backend owns one `index_policy` module. Entity/ward serialization, policy
attestation, and sitemap selection call the same single-item decision or its
owned batch wrapper. Nuxt never reconstructs quality from description length,
image count, verification flags, review photos, or another local checklist.

```text
IndexPolicyDecision
  kind: entity | ward | itinerary
  indexable: boolean
  reasons: stable reason-code list
  policy_fingerprint: string
  policy_revision: string
```

`indexable` is mandatory and boolean. There is no nullable or implicit-true
state. Public eligibility is evaluated before quality. Missing, provisional,
explicitly unverified, private, or otherwise ineligible content is not
indexable.

The normative per-kind rules are:

- non-place entity detail: public eligibility plus at least 130 descriptive
  words across summary and non-duplicate description;
- the former 100-word-plus-real-image branch cannot pass because current
  `entity.images` are AI-generated and receive zero real-image credit;
- ward/place detail: public eligibility plus either more than one
  public-eligible child or at least 60 summary words;
- itinerary and shared-plan detail: always `indexable=false`, noindex, and
  excluded in this workstream;
- static routes: use the route manifest, not this dynamic quality contract.

AI images, placeholders, malformed image metadata, review photos, and other UGC
photos do not increment the current real-image predicate. UGC is not called AI,
but it remains outside the current entity-quality predicate until a separate
reviewed provenance and moderation rule explicitly admits it.

#### 4.7.1 Policy-Bearing FastAPI HTTP Cache Authority

The final policy-bearing FastAPI HTTP registry is exact and intentionally
narrow:

| Method and path template | Exposure | Policy role |
| --- | --- | --- |
| `GET /api/entities/{entity_id}` | public through the reviewed `/api` Nginx ingress and consumed by Nuxt | the single entity-or-ward detail decision carrier; the entity kind determines which `index_policy` rule applies |
| `GET /_internal/launch-policy-attestation` | Nuxt-to-agent internal network or loopback only | build/backend fingerprint and revision attestation |
| `GET /_internal/launch-sitemaps/{document}` where `document` is exactly `sitemap-index.xml`, `sitemap.xml`, or `sitemap-media.xml` | Nuxt-to-agent internal network or loopback only | active or pinned immutable sitemap bytes and evidence |

Every response status from these exact endpoints, including validation errors,
not-found responses, dependency failures, and a request carrying
`If-None-Match`, emits `Cache-Control: no-store`. They omit `ETag`,
`Last-Modified`, and every other public cache validator, and they never return
HTTP 304. Nginx disables proxy caching and preserves this contract at the public
boundary; an Nginx-facing request to `GET /api/entities/{entity_id}` must observe
`no-store`, no validator, and a non-304 response even when `If-None-Match` is
present. The two `/_internal` families are never exposed by an Nginx proxy
location; Nuxt calls them through the Compose service network or production
loopback.

The current in-memory entity memoization may remain only as policy-neutral data
memoization. A complete serialized policy response, decision, fingerprint, or
revision is not replayed from that cache. The handler recomputes or validates
the `IndexPolicyDecision`, policy fingerprint, and policy revision on every
request after reading the memoized data. Entity writes, relationship changes,
ward-child eligibility changes, reload, and any policy-artifact/fingerprint
revision change invalidate the affected entity and parent-ward data entries.
This preserves performance without allowing an old policy revision to be
served under new evidence.

Other FastAPI endpoints retain their existing HTTP cache policy unless they are
added to this reviewed registry. The service worker may still conservatively
bypass all `/api/**`. Registry matching uses the resolved FastAPI route identity,
not a broad lexical Nginx regex: existing static routes such as
`/api/entities/map`, `/api/entities/trending`, `/api/entities/compare`,
`/api/entities/popular`, and `/api/entities/search` are not silently swept into
the dynamic detail contract. A source scan compares the registry to every
FastAPI route that serializes `IndexPolicyDecision`, `indexable` plus policy
evidence, launch attestation, or launch sitemap evidence; adding a new policy
decision endpoint without an explicit exposure and
`no-store-no-validator` classification fails.

### 4.8 Immutable Sitemap Bundle and Pinned Publication

The backend is the sole owner of selective-open sitemap assembly and XML
serialization. One generation operation opens one authoritative Postgres
`REPEATABLE READ, READ ONLY` transaction, reads all entity, relationship, ward,
and other required sitemap inputs from that snapshot, computes policy decisions,
and renders all three XML bodies plus their common evidence before publication.
`web/data.json` is not an attestation or open-sitemap fallback.

The bundle contents are:

- `sitemap.xml`: exact manifest-approved static routes plus canonical backend-
  indexable entity and ward URLs;
- `sitemap-media.xml`: normalized renderable `entity.images` only for backend-
  indexable entities, with AI disclosure in the supported caption field; no
  placeholder or UGC image is included;
- `sitemap-index.xml`: exactly two child locations pinned to the bundle batch:
  `/sitemap.xml?batch=<revision>` and
  `/sitemap-media.xml?batch=<revision>`.

The batch revision is the lowercase 64-character SHA-256 content address derived
from the reviewed fingerprint, route-manifest revision, backend-policy revision,
and the completed main/media XML bytes. The index is rendered only after that
revision is known. Before
publication the backend validates all XML, canonical URLs, URL uniqueness,
policy evidence, batch references, and document completeness.

Publication uses backend-owned operational storage at
`<release-root>/agent/data/sitemap-bundles` by default. Tests inject an explicit
temporary store path. A bundle is written to a staging directory, files and
directory metadata are flushed, the staging directory is atomically renamed to
`<batch-revision>/`, and only then is `active.json` atomically replaced. Entity
tables and other domain data are never mutated. A failed write or validation
leaves the previous active pointer intact.

Backend-internal endpoint behavior in selective-open is exact. Nuxt calls
`GET /_internal/launch-sitemaps/{document}` over the service network or
loopback, while the corresponding public root path remains Nuxt-owned:

- internal document `sitemap-index.xml` with no `batch` reads the active pointer
  and serves that immutable bundle's index;
- internal document `sitemap-index.xml?batch=<revision>` serves the exact
  retained bundle;
- internal documents `sitemap.xml?batch=<revision>` and
  `sitemap-media.xml?batch=<revision>` serve the exact retained child;
- a selective-open child request without `batch`, a duplicate or additional
  query parameter, an empty/non-lowercase/non-hex/non-64-character batch, an
  unknown or expired batch, a corrupt bundle, or a requested-batch echo mismatch
  returns HTTP 503 `no-store` with
  `X-Launch-Indexing-Policy: failed-open` and no evidence headers;
- no missing or invalid batch request silently falls back to the active pointer.

Every successful sitemap response exposes and Nuxt validates all four evidence
values: policy fingerprint, route-manifest revision, backend-policy revision,
and sitemap batch revision. For a request with `batch`, Nuxt additionally
validates the requested-batch echo before forwarding the response.

Retention is test-configurable and defaults to 24 hours. Cleanup retains the
active bundle and at least the immediately previous successfully published
bundle even if the previous bundle is older than 24 hours; all other bundles may
be removed only after their 24-hour minimum. On restart the backend reads and
validates `active.json` and the referenced immutable files. Missing or corrupt
state makes selective-open sitemap and open readiness unavailable; it never
causes DB mutation or a mutable regeneration inside a public GET.

Bundle generation is invoked only by the backend CLI
`python -m agent.sitemap_bundle refresh`. The local rehearsal and any future
Stage 3 deploy call it after backend readiness and before Nuxt open readiness.
Backend startup only reloads and validates the active pointer; public sitemap GET
never generates a bundle. Exact open-intent readiness requires a valid active
bundle before traffic.

### 4.9 Exclusive Public Ingress and Ownership

The launch-compatible production Compose topology has one public network
boundary. Only Nginx publishes host ports 80 and 443. `agent` and `nuxt` remove
their inherited host `ports` entries and use internal-network `expose` only for
8360 and 3000. The bot gateway, Postgres, Redis, Prometheus, Grafana, Loki, and
other supporting services also have no production host publication, so the
rendered production Compose model contains no public socket other than Nginx
80/443. A developer-only override may publish a needed service only as an
explicit loopback binding such as `127.0.0.1:3000:3000`; that override is named
and tested as non-production and is never packaged or selected by the production
deploy/rehearsal commands.

Compose Nginx has exactly one startup dependency:

```text
nginx.depends_on.nuxt.condition = service_healthy
nginx.depends_on.agent = absent
```

Nginx can still reach agent and bot gateway over the private Compose network for
reviewed API, auth, chat, event, admin, health/operational, and webhook routes.
Nuxt safe-closed health is independent of agent, so an agent-absent closed cold
start makes Nuxt healthy and permits Nginx to start. With exact open intent and
agent absent, Nuxt readiness is 503; in the cold-start test topology Nginx's
`service_healthy` dependency is unsatisfied and the harness must not mark Nginx
ready or admit public traffic. Runtime/deploy admission also requires the same
Nuxt readiness probe, because Compose startup dependency alone does not withdraw
traffic from an already-running proxy.

The non-Compose production boundary is equivalent. The source-controlled
`vl-agent` and `vl-nuxt` systemd unit definitions or their reviewed launch
wrappers bind 8360 and 3000 to `127.0.0.1` (or loopback IPv6 when explicitly
tested), never public `0.0.0.0`. The bot gateway and any other Nginx-reached
internal HTTP process follow the same loopback-only rule. Unit/static tests
inspect the effective `ExecStart` and environment, and a socket probe confirms
that the services are not listening on a non-loopback address before traffic is
reopened.

Both `nginx.conf` and `nginx-ssl.conf` route exactly `/robots.txt`,
`/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml` to the Nuxt
upstream before their catch-all behavior. Those exact locations have proxy
caching disabled and preserve host/forwarded headers and query strings. The
configs contain an exact
`location = /_internal/launch-readiness { return 404; }`-equivalent rule before
the catch-all, plus a non-proxy deny/not-found boundary for the backend launch
attestation and sitemap families. Therefore public requests cannot reach Nuxt
readiness or FastAPI launch-internal routes through Nginx.

FastAPI remains reachable from Nuxt through the internal API base for entity
decisions, attestation, and guarded sitemap proxying, but is not the public owner
of the four root SEO paths. Direct host access to agent 8360, Nuxt 3000, bot
gateway, `/_internal/launch-readiness`, FastAPI launch attestation/sitemap
routes, or the legacy FastAPI root sitemap handlers must fail from outside the
private network/loopback boundary.

Static configuration tests cover the rendered production Compose model, both
Nginx files, production systemd units/wrappers, and the dev-override exclusion.
A practical local integration combines that static inspection with container
network probes: the host has only Nginx 80/443, `docker compose port` reports no
binding for agent/Nuxt/internal services, Nginx and Nuxt can reach the reviewed
private upstreams, and host-direct 3000/8360/readiness/FastAPI-sitemap bypass
attempts fail. Nginx-facing probes additionally prove root SEO requests cannot
bypass Nuxt, query-pinned batch requests arrive intact, policy/evidence headers
are preserved, and no Nginx cache serves a root SEO or policy-bearing entity
response.

### 4.10 Shared Image Descriptor and Disclosure Inventory

`config/ai-disclosure.json` contains the reviewed version, short label, full AI
copy, placeholder copy, and accessible-description keys. Python and TypeScript
loaders expose a shared descriptor contract:

```text
ImageDescriptor
  url: string | none
  alt: string
  source_class: ai-generated | placeholder | user-uploaded
  source_kind: entity-editorial | generated-placeholder | review-ugc | post-ugc
  disclosure_key: entity-ai | entity-placeholder | ugc-photo
  short_label: string | none
  full_disclosure: string
  credit: string | none
  width: integer | none
  height: integer | none
```

Classification is fixed:

- every current `entity.images` value -> `ai-generated` / `entity-editorial`;
- a generated graphic for an entity with no image -> `placeholder` /
  `generated-placeholder`;
- review or other UGC photo -> `user-uploaded` / `review-ugc` or `post-ugc`.

UGC uses truthful user-photo copy and credit and is never given an AI label.
UGC does not count as a current entity real-image quality signal. A mixed gallery
API returns structured descriptors for both entity AI images and approved review
UGC photos, preserving order and source classification; frontend gallery code no
longer receives an untyped `string[]` for mixed media.

The repository inventory below is the normative minimum, not a closed allowlist.
Every first-party public, authenticated, and admin renderer of `entity.images`
or a representative entity-image value derived from it must consume a shared
`ImageDescriptor` at the rendering boundary and present the matching AI,
placeholder, or user-uploaded classification at the point of use:

- detail hero, thumbnail rail, `PhotoGallery`, and `ImageLightbox`;
- home feature/spotlight backgrounds sourced from `entity.images`, and every
  `EntityCard` use on home, `/dia-diem`, `/du-lich`, `/san-pham`, `/ocop`,
  `/luu-tru`, `/kham-pha/**`, `/khu-vuc/**`, `/theo-mua`, `/tim-kiem`, ward child
  sections, nearby entities, home feature cards, and smart/AI recommendations;
- the `useFavorites` and `useRecentlyViewed` adapters, every `SavedEntityCard`
  use on `/da-luu`, `/lich-trinh`, and user profiles, and the recent-search
  thumbnail on `/tim-kiem`; a derived `image` field may not discard descriptor
  classification;
- entity event thumbnails on `/le-hoi` and `/su-kien`, plus related-place cards;
- `web-nuxt/pages/admin/entities.vue` table thumbnails and image editor,
  `web-nuxt/pages/admin/media.vue` media grid and expanded preview, and
  `web-nuxt/pages/admin/duyet-tu-hoc.vue` inspected image link/list;
- any map/popup entity-image renderer found during implementation inventory;
  the current `/ban-do` popup has no image, and a regression test prevents a new
  unclassified image from being added there;
- review photos, `ReviewCard`, `PostCard`, `EntityFeed`, related post/community
  thumbnails, the admin post-moderation preview, and the mixed gallery API,
  which must stay classified as user-uploaded UGC rather than AI;
- native share payload, OG/Twitter image alt, JSON-LD `ImageObject`, and media
  sitemap metadata.

Dense public cards and admin grids may render the short `Minh họa AI` badge only
when the image, figure, row, or link has an accessible association to the full AI
sentence. Expanded admin previews and inspectors show the full disclosure copy.
Placeholder descriptors show placeholder copy. UGC surfaces show truthful
user-uploaded copy/credit and never inherit an AI label, including on admin
moderation surfaces.

Implementation maintains a machine-readable first-party renderer registry with
the file/surface, access path or adapter, source class, descriptor producer, and
required short/full presentation. An automated repository scan covers Vue
templates, components, pages, composables, and server/client adapters across
public, authenticated, and admin code. It fails when a new direct `entity.images`
access, raw image-array prop, or representative entity-image URL reaches a
renderer without a registered descriptor conversion and point-of-use
classification. Review reconciles the generated scan with this normative
minimum; registration documents a renderer but never exempts it from descriptor
and disclosure requirements.

The exact canonical copy remains:

Actual AI entity image:

> Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.

Generated graphic placeholder:

> Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.

The short label remains `Minh họa AI`. Dense cards may show that short pill only
when the image or enclosing figure references the full accessible sentence.
Expanded detail/gallery/lightbox captions show the full sentence. Placeholder
and UGC descriptors never inherit the AI copy.

## 5. Normative Policy Matrix

| Surface | Closed | Selective-open simulation | Per-request failed-open |
| --- | --- | --- | --- |
| Policy header | `closed`; no evidence | `selective-open`; three matching evidence headers | `failed-open`; no evidence |
| Static canonical HTML | `noindex,follow` | `index,follow` only for exact manifest allowlist and canonical queryless path | `noindex,follow` |
| Valid entity/ward `indexable=true` | `noindex,follow` | `index,follow`; three evidence headers | Not applicable |
| Valid entity/ward `indexable=false` | `noindex,follow` | remains selective-open; `noindex,follow`; three evidence headers; no sitemap mutation | Not applicable |
| Entity/ward response missing/malformed/mismatch | closed behavior | only that HTML request becomes failed-open | `noindex,follow`; omit evidence and discovery link |
| `X-Robots-Tag` on HTML | `noindex, follow` | mirrors final page decision | `noindex, follow` |
| HTML sitemap discovery | absent | exactly one `/sitemap-index.xml` link on fully attested HTML, including valid negative entity policy | absent |
| Robots public crawl | allow public route groups | same | same |
| Robots sensitive crawl | block all sensitive prefixes in every applicable bot group | same | same |
| Robots sitemap line | absent | one `/sitemap-index.xml` line after full attestation | absent |
| Closed sitemap endpoints | HTTP 200 valid empty endpoint-specific XML, `no-store`, zero backend calls | not applicable | not applicable |
| Active sitemap index | absent from robots/HTML | immutable active bundle index, four evidence values | HTTP 503 `no-store` |
| Pinned child/index request | absent from robots/HTML | exact retained batch plus requested-batch echo | HTTP 503 `no-store` |
| Cache/delivery source | dynamic `no-store`; no SWR/prerender/worker | dynamic `no-store`; no SWR/prerender/worker | dynamic `no-store`; no SWR/prerender/worker |
| Sitemap membership | empty | exact manifest routes plus backend-positive entity/ward decisions from one snapshot | no document served |

Additional rules:

- closed and failed-open never advertise a sitemap through robots or HTML;
- closed HTML, robots, readiness, and empty sitemaps make no backend policy call;
- `follow` supports legitimate navigation but is not index permission;
- sensitive prefix blocking wins over route allowlists and bot-specific groups;
- a valid negative entity policy is evidence, not a dependency failure;
- no request mutates the active sitemap bundle or entity database;
- all policy-bearing responses use `no-store` in every state.

### 5.1 Closed XML Shapes

Each closed endpoint is independent and makes zero backend calls:

- `/sitemap.xml`: HTTP 200, `no-store`, valid empty `<urlset>`;
- `/sitemap-media.xml`: HTTP 200, `no-store`, valid empty `<urlset>` with the
  image namespace and no image entry;
- `/sitemap-index.xml`: HTTP 200, `no-store`, valid empty `<sitemapindex>` with no
  child location.

A failed-open sitemap never falls back to one of these empty successes because
that would make a dependency outage look like intentional URL removal.

## 6. Data Flow

Closed request:

```text
request
  -> validate launch-compatible output/readiness invariants
  -> one or both exact keys absent
  -> operational=closed, indexing=closed, sitemap=closed-empty
  -> dynamic no-store response
  -> noindex header/meta + closed robots + no discovery link
  -> endpoint-specific empty sitemap where applicable
  -> zero backend launch-policy calls
```

Selective-open static route:

```text
request -> both keys exact -> validate backend attestation
  -> fingerprint + route-manifest + backend-policy revisions match
  -> normalize/classify path through shared manifest
  -> exact canonical indexable route with no query: index,follow
  -> noindex route, query variant, redirect variant, or catch-all: noindex,follow
  -> selective-open policy + three evidence headers + discovery link
  -> dynamic no-store response
```

Selective-open entity/ward request:

```text
attested request -> GET /api/entities/{entity_id} through the resolved detail route
  -> valid matching indexable=true: selective-open + index,follow
  -> valid matching indexable=false: selective-open + noindex,follow
  -> missing/malformed/transport/mismatch:
       only this request -> failed-open + noindex,follow
       omit evidence + discovery link
  -> no active-bundle mutation in every branch
  -> dynamic no-store response
```

Sitemap publication:

```text
internal refresh -> one DB REPEATABLE READ READ ONLY transaction
  -> evaluate route manifest + entity/ward batch policy
  -> render main XML + media XML
  -> derive content-addressed batch revision
  -> render index with two ?batch=<revision> child URLs
  -> validate all XML + all four evidence values
  -> flush staging bundle -> atomic directory rename
  -> atomic active.json pointer swap
  -> cleanup only beyond retention rules
```

Selective-open sitemap request:

```text
request -> attested Nuxt decision
  -> guarded GET /_internal/launch-sitemaps/{document}
  -> active root index or exact requested batch
  -> backend returns immutable bytes + four evidence values
     + requested-batch echo when applicable
  -> Nuxt validates fingerprint + route-manifest revision
     + backend-policy revision + sitemap batch revision
     + requested-batch echo when applicable
  -> forward no-store selective-open response
  -> any failure: 503 no-store failed-open, no evidence
```

Disclosure classification:

```text
entity.images item -> ai-generated descriptor -> AI disclosure
no entity image    -> placeholder descriptor  -> placeholder disclosure
approved review    -> user-uploaded descriptor -> UGC copy/credit, never AI
malformed media    -> omit; never quality credit
```

## 7. Failure Behavior

- missing, partial, or invalid unlock configuration: safe closed when output
  isolation passes;
- unsafe build/output, route-rule cache, prerender, or worker state: readiness
  503 in every runtime mode;
- exact open intent with missing/mismatched attestation: affected readiness or
  request is failed-open; no process-global latch is written;
- backend unavailable in ordinary closed: closed HTML, robots, readiness, and
  empty sitemaps remain usable with zero backend calls, and Nuxt process startup
  is not blocked by backend health;
- exact open intent with the backend absent: the Nuxt process may start, but
  readiness is 503 failed-open and traffic remains gated;
- valid matching entity/ward `indexable=false`: selective-open request remains
  valid and noindex; it is not relabeled failed-open;
- entity/ward policy missing, malformed, transport-failed, or mismatched: only
  that HTML request becomes failed-open, noindex, `no-store`, with no evidence or
  discovery link;
- open robots attestation failure: closed robots body, no sitemap line,
  `X-Launch-Indexing-Policy: failed-open`;
- child sitemap without batch, unknown/expired batch, corrupt bundle, missing
  active pointer, evidence mismatch, or echo mismatch: HTTP 503 `no-store`, no
  stale/active fallback;
- DB snapshot or bundle publication failure: previous active pointer remains;
  if no valid active bundle exists, open readiness and sitemap requests fail;
- restart with corrupt active bundle: open readiness 503; ordinary closed remains
  backend-independent;
- service-worker activation that fails to delete legacy policy-bearing caches:
  readiness/rehearsal failure;
- current entity image lacking descriptor metadata: classify from source as AI
  and use exact AI copy; do not silently omit disclosure;
- review/UGC photo lacking source classification: omit from mixed first-party
  gallery until classified; never default it to AI or entity-editorial;
- attempted real/documentary labeling of current entity images: test and review
  failure.

## 8. Test Strategy and Evidence

Every behavior change follows RED -> GREEN. Tests are grouped by contract rather
than by the eventual implementation file.

### 8.1 Artifact and Packaging Tests

- validate both JSON schemas, exact canonical filenames, and revisions;
- reject duplicate canonical artifacts anywhere outside root `config/`;
- prove Python and TypeScript loader parity on valid and invalid fixtures;
- prove production loaders have no fallback path while tests can inject an
  explicit fixture path;
- build Nuxt from repository-root context with `web-nuxt/Dockerfile` and verify
  the artifact digests embedded in `.output` match root bytes;
- inspect the backend tarball and an unpacked temporary release root to prove
  `config/` is present and loadable;
- inspect the launch-compatible release/rehearsal package to prove the reviewed
  Nginx and loopback systemd artifacts are present, the rendered production
  Compose audit exposes only 80/443, and no production command selects the
  developer override.

### 8.2 Decision, Header, and Entity Failure Tests

- full two-key truth table, including case, whitespace, aliases, and partial
  values;
- closed readiness and HTML make zero backend launch-policy calls;
- attestation matches/mismatches for fingerprint, route-manifest revision, and
  backend-policy revision;
- exact policy header values and evidence-header presence/absence on public HTML
  and all four root SEO endpoints;
- valid matching entity/ward `indexable=false` remains selective-open, retains
  three evidence headers and discovery link, stays noindex/no-store, and has no
  sitemap side effect;
- missing/malformed/timeout/transport/fingerprint/revision entity failures make
  only the affected request failed-open and do not affect a concurrent valid
  request or later valid request;
- backend unit tests cover every endpoint in the exact policy-bearing FastAPI
  registry on success and failure: `Cache-Control: no-store`, no ETag or other
  validator, and no 304 when `If-None-Match` is sent;
- entity-detail memoization tests change the policy revision and mutate entity,
  relationship, and ward-child inputs to prove data invalidation plus per-request
  decision/evidence recomputation; no cached response can replay an old revision;
- an exact registry/source scan fails when a FastAPI route starts returning
  policy-decision, attestation, or sitemap evidence without an exposure and
  `no-store-no-validator` registry entry; unrelated APIs retain their reviewed
  existing cache assertions, including the static `/api/entities/map`,
  `trending`, `compare`, `popular`, and `search` route identities;
- an Nginx-facing entity-detail test repeats an `If-None-Match` request and sees
  `no-store`, no validator, and a non-304 result at the public boundary;
- meta and `X-Robots-Tag` agree in every branch.

### 8.3 Build, Readiness, and Service-Worker Tests

- compiled `.output` contains no policy-bearing prerendered HTML/API/root SEO
  artifact and no SWR/ISR/cache rule for policy-bearing paths in any mode;
- a deliberately injected prerender file or cache rule makes readiness 503;
- readiness exact path returns 200 for safe closed without backend, 200 for
  fully attested safe open with active bundle, and 503 for each unsafe check;
- a static Compose test rejects every `nuxt.depends_on` reference to `agent`,
  whether health-gated or startup-order-only, any equivalent backend startup
  gate, and any homepage healthcheck; the Nuxt healthcheck must call internal
  readiness;
- rendered production Compose inspection proves only Nginx publishes host
  80/443, agent and Nuxt use internal `expose` without host `ports`, all other
  internal services are unpublished, and any developer binding is explicit
  `127.0.0.1` in an excluded non-production override;
- the rendered Compose model gives Nginx exactly a
  `nuxt: condition: service_healthy` dependency and no agent dependency;
- an agent-absent cold-start integration starts Nuxt with open-intent keys absent
  or invalid and proves readiness 200 safe closed, closed robots, all three valid
  empty sitemap shapes, no sitemap discovery, and zero backend calls;
- the counterpart agent-absent exact-open-intent integration proves the Nuxt
  process starts, readiness returns 503 failed-open, and the harness admits no
  traffic;
- Docker healthcheck and local deploy harness call the internal endpoint from
  inside the container before traffic, without gating closed Nuxt startup on
  agent health;
- the exact-open/agent-absent cold-start leaves the Nginx dependency unsatisfied,
  and both the Compose and deploy harnesses record that no listener is admitted;
- production systemd unit/wrapper tests require agent, Nuxt, and Nginx-reached
  internal HTTP services to bind loopback only and reject `0.0.0.0`;
- service worker bypasses navigation, HTML, root SEO, `/_internal/**`, `/api/**`,
  `/events`, `/recommend`, `/seo/**`, request `no-store`, and response
  `no-store`;
- activation removes legacy HTML/policy caches and retains only the new
  policy-neutral versioned asset cache.

### 8.4 Route Manifest Tests

- initial inventory exactly matches the reviewed table;
- static sitemap extraction includes only exact `sitemap=true` entries;
- entity and ward templates delegate to backend and itinerary/share/search stay
  excluded;
- sensitive prefix wins over exact/template/catch-all overlap;
- `/admin` does not match `/administrator`;
- `/system` and `/system/x` match while `/systematic` does not; equivalent cases
  cover `/api` versus `/apiary`, `/webhook` versus `/webhooks`, and queries do
  not alter the normalized path classification;
- the initial sensitive inventory includes every reviewed agent/bot ingress,
  including `/analytics`, `/welcome`, `/system`, and `/webhook`;
- an automated parity test extracts every backend-directed location/alias from
  both Nginx files and requires a matching manifest sensitive prefix or explicit
  reviewed exception with equivalent end-or-slash semantics; unknown ingress,
  HTTP/HTTPS drift, or a boundaryless location fails;
- encoded separators, invalid UTF-8/escapes, dot segments, and double-decoding
  candidates fail closed;
- trailing slash, repeated slash, unreserved encoding, query, and catch-all
  behavior match the normalization contract;
- Python and TypeScript classifiers return identical results for the shared
  corpus.

### 8.5 Sitemap Bundle and Protocol Tests

- one authoritative transaction/snapshot supplies all three documents;
- mutation committed outside the transaction during generation cannot produce
  mixed main/media/index contents;
- concurrent refreshes use single-writer publication or equivalent locking and
  never expose staging/partial bundles;
- failed publication leaves the old active pointer and immutable bytes intact;
- active index references exactly two child URLs with the same encoded batch;
- fetching the index and then mutating DB still yields the original child bytes
  for that pinned batch;
- active root, pinned root, and pinned children validate fingerprint,
  route-manifest revision, backend-policy revision, sitemap batch revision, and
  requested-batch echo where applicable;
- missing, empty, malformed, expired, and unknown batches return 503 and never
  fall back to active;
- retention keeps active plus at least previous and honors the test clock's
  24-hour minimum;
- backend restart reloads a valid active bundle and rejects corrupt pointer/file
  state;
- snapshot failure never falls back to `web/data.json`.

Unit fixtures remain the deterministic authority for exact XML bytes. In
addition, an opt-in integration test runs against a disposable local PostgreSQL
database (a local container is acceptable) and proves the real isolation and
publication boundary: one `REPEATABLE READ, READ ONLY` snapshot does not observe
a mutation committed by a second connection during generation, all documents
reflect the original snapshot, and concurrent/failed publication exposes only
the previous or complete new atomic bundle and `active.json` pointer. The test
is skipped unless `SITEMAP_BUNDLE_TEST_DATABASE_URL` points to an explicitly
disposable PostgreSQL database and rejects a non-loopback host unless a separate
test-only override is exact. Evidence records the command and pass/skip result,
for example:

```text
SITEMAP_BUNDLE_TEST_DATABASE_URL=postgresql://... \
  python -m pytest agent/tests/test_sitemap_bundle_postgres.py -m integration -q
Expected: snapshot/concurrent-publication tests pass; default suite skips safely.
```

### 8.6 Disclosure and UGC Tests

- shared descriptor classification covers AI entity images, placeholders,
  review UGC, post UGC, and malformed media;
- hero, thumbnail rail, gallery, and lightbox show the required short/full copy
  and preserve accessible association through slide changes and reopen;
- home feature/spotlight tests and `EntityCard` tests cover listings, search,
  ward children, nearby, and smart/AI recommendation consumers;
- descriptor-preserving adapter tests cover `useFavorites`,
  `useRecentlyViewed`, contextual recommendations, `SavedEntityCard` on saved,
  itinerary, and user-profile surfaces, and the recent-search thumbnail;
- event tests cover `/le-hoi`, `/su-kien`, and related-place cards;
- admin tests cover entity-list thumbnails, entity image editing, the media grid,
  expanded media preview, and self-learning image inspection in
  `admin/entities.vue`, `admin/media.vue`, and `admin/duyet-tu-hoc.vue`; dense
  admin rows/grids use the short accessible badge and expanded previews use full
  copy;
- the machine-readable renderer registry and repository-wide source scan cover
  public, authenticated, and admin code and fail for every unregistered or
  unclassified direct/raw entity-image renderer, including a future map/popup;
- mixed gallery API preserves `ai-generated` versus `user-uploaded` source class
  and never labels review/UGC photos as AI, including admin post moderation;
- UGC photos do not change current entity indexability or media sitemap output;
- native share, OG/Twitter alt, JSON-LD, and media sitemap use the correct source
  disclosure; placeholder and UGC copy never inherit AI text;
- text scans reject real/documentary/on-site claims for current entity images.

### 8.7 Ingress, Browser, Rollback, and Regression Tests

- both Nginx configs route all four root SEO paths through Nuxt with query
  preservation and no cache, and deny public internal readiness;
- exact Nginx deny/not-found rules prevent proxying Nuxt readiness and backend
  launch-internal attestation/sitemap paths;
- rendered Compose plus container-network probes prove only 80/443 are host
  reachable; direct host access to 3000, 8360, bot/internal services, readiness,
  and FastAPI sitemap bypass is unavailable while reviewed private upstream
  calls still work;
- Nginx-facing probes preserve exact policy/evidence/batch headers;
- controlled browser activation proves no old worker or Cache Storage entry can
  replay policy-bearing content offline;
- timed local single-host rollback rehearsal follows Section 12 and records each
  phase; it does not claim a live external five-minute result;
- rerun backend against the 6168/47/78/1/1 baseline and frontend serially against
  8 files/125 plus new tests;
- record the known parallel resource timeout separately and do not weaken a new
  functional assertion to accommodate it.

## 9. Dependency-Ordered Task Boundaries

The implementation plan may split any task further. It must not combine these
boundaries without an explicit plan update because each boundary requires a
reviewable RED -> GREEN change.

1. Artifact packaging boundary: root `config/`, Docker root context, release
   tarball layout, duplicate-file guard, and packaging tests.
2. Route-manifest JSON schema and canonical root artifact.
3. TypeScript route-manifest loader and schema-failure tests.
4. Python route-manifest loader and schema-failure tests.
5. Initial route inventory, normalization/classification, parity corpus, and
   static-sitemap extraction tests.
6. AI-disclosure JSON schema and canonical root artifact.
7. TypeScript disclosure loader and exact-copy tests.
8. Python disclosure loader and exact-copy tests.
9. Backend non-place entity `index_policy` decision and unit tests.
10. Ward policy plus itinerary/shared-plan fixed exclusion tests.
11. Public entity/ward response integration with mandatory boolean decision,
    fingerprint, and revision.
12. Exact policy-bearing FastAPI endpoint registry; entity-detail unconditional
    no-store/no-validator/no-304 behavior; memo invalidation and source-scan
    enforcement.
13. Internal-only backend policy-attestation endpoint, revision matching,
    no-store registration, and Nginx non-exposure contract.
14. One authoritative DB snapshot/transaction abstraction for sitemap input.
15. Immutable sitemap bundle store, atomic active pointer, retention, locking,
    restart loading, and failure tests.
16. Opt-in disposable PostgreSQL integration for real `REPEATABLE READ`
    visibility, concurrent mutation, atomic bundle publication, and active
    pointer behavior.
17. Main sitemap rendering from manifest plus entity/ward batch decisions and
    the registered internal-only FastAPI document route.
18. Media sitemap rendering with AI disclosure and placeholder/UGC exclusions.
19. Sitemap-index rendering and exact pinned-batch URL protocol.
20. Nuxt two-key base decision and internal backend attestation client.
21. Nuxt guarded sitemap proxy validating all four evidence values and requested-
    batch echo through the internal backend document route.
22. Nuxt response middleware for exact policy and evidence headers.
23. Per-entity/ward valid-negative and request-scoped failed-open behavior.
24. HTML head/meta/`X-Robots-Tag` integration and conditional sitemap-index link.
25. Closed/failed-open robots and the three endpoint-specific root sitemap
    handlers.
26. Unconditional routeRules/SWR removal, prerender removal, and preliminary
    `.output` policy-bearing artifact audit.
27. Service-worker policy-neutral cache, bypass, no-store, version, rule digest,
    and legacy-cache purge contract.
28. Generated readiness manifest with the final service-worker version/digest,
    plus complete `.output` manifest/digest audit tests.
29. Exact `/_internal/launch-readiness` endpoint and safe-closed/safe-open checks.
30. Exclusive production network topology: remove all non-Nginx host
    publications, use agent/Nuxt internal `expose`, keep dev overrides
    loopback-only, make Nginx depend only on healthy Nuxt, bind production
    systemd internal services to loopback, and add static plus agent-absent and
    container-network tests.
31. `scripts/deploy.sh` and local deploy/release harness readiness wiring without
    a closed-start backend-health gate, plus Docker build verification.
32. Nginx ownership of root SEO paths, query preservation, no-cache behavior,
    exact internal-route denial, segment-boundary backend locations, and
    manifest-to-agent/bot ingress parity in both configs.
33. Shared structured image descriptor and mixed entity/UGC gallery API.
34. Detail hero and thumbnail-rail AI/placeholder disclosure.
35. Gallery and lightbox descriptor/caption/accessibility behavior.
36. Home feature/spotlight plus `EntityCard` listing/search/ward/nearby/
    recommendation consumers.
37. Descriptor-preserving favorite/recent adapters and `SavedEntityCard`
    consumers on saved, itinerary, profile, and recent-search surfaces.
38. Event thumbnails, related places, and map/popup descriptor behavior.
39. Admin entity surfaces in `admin/entities.vue`, `admin/media.vue`, and
    `admin/duyet-tu-hoc.vue`, including dense-badge accessibility and full-copy
    expanded previews.
40. Machine-readable renderer registry plus repository-wide public,
    authenticated, and admin direct/raw entity-image inventory guard.
41. Review/post UGC photo classification, admin moderation behavior, and
    current-quality exclusion.
42. Native share, OG/Twitter alt, JSON-LD, and media metadata parity.
43. Browser/Nginx end-to-end matrix for closed, selective-open, valid negative,
    request-scoped failed-open, pinned sitemap, worker-cache behavior, and the
    exclusive 80/443 network boundary.
44. Executable single-host rollback runbook, source-controlled Nginx
    maintenance/drain include, and timed local rehearsal.
45. Full backend/frontend regression evidence and final source scan.

This graph contains exactly 45 continuous numbered task boundaries. Every
numbered implementation task starts with a fresh implementer context or
agent, without exception; no implementer context is reused for a later task.
Each task records RED before the smallest coherent GREEN change. Its first
spec-compliance review uses a fresh reviewer context independent of the
implementer. Re-review after fixes may reuse that same spec-reviewer role for
continuity. Only after spec compliance explicitly passes does a separate fresh
code-quality reviewer context review the task. Critical and Important findings
block progression. Cross-task scope changes require a plan update.

## 10. Non-Goals

This workstream does not:

- deploy, push, merge, or release;
- change real environment values or secrets;
- enable indexing on any live target;
- resolve H1/H2, make a legal decision, or grant owner approval;
- mutate, migrate, rewrite, backfill, or delete entity data;
- label UGC as AI or admit UGC into the current real-image quality predicate;
- replace AI images with real or user-generated photographs;
- add a second frontend quality predicate;
- add custom policy cache keys or enable selective-open caching;
- use `robots.txt` as authorization;
- promise search-engine inclusion or ranking;
- claim current single-host deployment has a multi-replica drain capability;
- claim the real five-minute rollback target was externally proven in this
  workstream.

## 11. Acceptance Criteria

Implementation is accepted only when:

- deployed configuration remains unchanged and globally closed;
- safe closed works with zero backend launch-policy calls;
- only two exact keys plus matching artifact/attestation evidence can produce
  selective-open in tests;
- every public HTML and root SEO response carries exactly one valid policy
  header and the correct evidence-header presence/absence;
- valid matching entity/ward `indexable=false` stays selective-open, keeps three
  evidence headers and the discovery link, emits noindex/no-store, and has no
  sitemap mutation;
- entity/ward missing/malformed/transport/mismatch failure affects only that
  request, which becomes failed-open with no evidence or discovery link;
- all policy-bearing HTML/API/root SEO responses are dynamic `no-store` with no
  SWR, ISR, route cache, prerender, proxy cache, or service-worker source;
- the exact FastAPI policy-bearing registry contains public
  `GET /api/entities/{entity_id}` and the two reviewed launch-internal route
  families only; every status is `no-store`, emits no validator, never returns
  304, recomputes/validates the current decision evidence, and unrelated backend
  APIs retain their separately reviewed cache policy;
- internal readiness is exact, non-public, backend-independent in closed, and
  checks real `.output`, route rules, artifact hashes, worker rules, runtime
  keys, attestation, and active batch state;
- Docker healthcheck, `scripts/deploy.sh`, and the local deploy harness use the
  internal readiness endpoint from the container/process-local target context
  before traffic;
- the launch-compatible Compose file has no `nuxt.depends_on.agent` relationship
  and local/deploy harnesses contain no equivalent closed-start gate; with the
  agent absent, Nuxt cold-starts to readiness 200 safe closed for absent/invalid
  keys, serves closed robots and empty sitemaps with zero backend calls, while
  exact open intent yields readiness 503 and no admitted traffic;
- rendered production Compose publishes only Nginx 80/443; agent 8360, Nuxt
  3000, bot/backend dependencies, data stores, and monitoring services are
  private, while any development publication is explicit `127.0.0.1` in an
  excluded override;
- Compose Nginx depends on healthy Nuxt only, production systemd agent/Nuxt and
  other Nginx-reached internal services bind loopback rather than `0.0.0.0`, and
  direct host/backend/readiness/FastAPI-sitemap bypass probes fail;
- the two canonical JSON artifacts exist only at root `config/`, Nuxt Docker
  builds from repository root, and backend release packaging includes `config/`;
- the launch-compatible release/rehearsal package contains the reviewed Nginx,
  loopback systemd, and production Compose network-audit artifacts and excludes
  the developer override from every production command;
- Python/TypeScript loaders and route classifiers pass parity tests;
- route manifest schema, normalization, precedence, initial inventory, unknown
  fail-closed behavior, and static-sitemap exactness match Section 4.6;
- sensitive prefixes use exact end-or-slash segment boundaries, include
  `/analytics`, `/welcome`, `/system`, `/webhook` and every other current
  agent/bot ingress, and both Nginx configs pass the automated manifest parity
  scan with no unknown or boundaryless backend alias;
- itinerary/share/search/UGC/catch-all pages remain noindex and excluded;
- backend `index_policy` is the only entity/ward indexability authority and all
  current AI, placeholder, malformed, and UGC media give zero current real-image
  credit;
- one authoritative DB transaction renders a complete immutable sitemap bundle;
- the deterministic XML unit fixtures and opt-in disposable PostgreSQL
  integration both pass, including real `REPEATABLE READ` mutation visibility,
  concurrent publication, and atomic active-pointer evidence;
- publication atomically swaps the active pointer only after validation and
  never mutates entity data;
- active index children are pinned with the exact batch query; missing/expired
  batch never falls back to active;
- Nuxt validates fingerprint, route-manifest revision, backend-policy revision,
  sitemap batch revision, and requested-batch echo where applicable;
- retention and restart behavior preserve an active plus minimum previous bundle
  and fail safely on corrupt state;
- both Nginx configs route root SEO through Nuxt, preserve query/evidence, disable
  caching, return not-found for public readiness and backend launch-internal
  paths, and do not expose FastAPI attestation or sitemap routes directly;
- every first-party public, authenticated, and admin entity-image renderer found
  by the normative minimum plus automated repository inventory consumes the
  shared descriptor and presents the correct AI/placeholder/user-uploaded
  classification at its point of use; no unregistered direct/raw renderer passes
  review or tests;
- dense admin grids may use the accessible `Minh họa AI` badge, expanded admin
  previews use full copy, and placeholder/UGC descriptors use their own truthful
  copy;
- mixed gallery, review, and post photos remain `user-uploaded`, are never called
  AI, and remain outside current entity quality and media sitemap;
- service-worker activation purges legacy policy caches and a controlled browser
  cannot replay prior policy-bearing content;
- each behavior records RED then GREEN evidence and regression suites pass;
- the rollback runbook and timed local rehearsal meet Section 12, while the real
  external five-minute proof remains a Stage 3 requirement;
- H1 and H2 remain explicit unresolved launch blockers and no Important finding
  remains open.

## 12. Rollout, Single-Host Rollback, and External Gates

Stage 0 is this workstream: change source/config/tests and run local rehearsal
while every real environment stays closed. Stage 1 records truth-table, policy,
packaging, disclosure, cache-isolation, ingress, sitemap-bundle, and regression
evidence. Stage 2 requires externally recorded H1 completion, H2 qualified-
counsel review, and separate project-owner authorization. Stage 3 is a separate
operational task that may change real keys and prove live rollback timing.

A test simulation, merged commit, passing suite, readiness 200, generated
fingerprint, or local rehearsal is not H1, H2, or owner approval.

The current topology is one host and one `vl-nuxt` systemd service. The
executable rollback runbook is therefore a maintenance-window replacement, not
a mixed-fleet rollout:

1. Record start time, candidate/rollback release identifiers, operator, and
   known-good closed artifact; verify the closed artifact contains root config,
   a launch-compatible readiness manifest, the reviewed Nginx configs,
   loopback-only systemd unit/wrapper definitions, and the production Compose
   network audit with the developer override excluded.
2. Suspend `vl-watchdog.timer` and stop any active `vl-watchdog.service` so it
   cannot restart processes during rollback.
3. Enable the preinstalled Nginx maintenance/drain include. It returns HTTP 503
   to general public traffic while allowing only the named operator probe source;
   run `nginx -t` and reload Nginx. Failure keeps the existing state and aborts.
4. Stop `vl-nuxt`; do not restart the old open process.
5. Purge the old server-side Nuxt/Nitro/runtime/worker artifacts under
   `/opt/vinhlong360/web-nuxt/.output`, `.nuxt`, `.cache`, and the cache/output
   paths enumerated by the old readiness manifest. Preserve backend sitemap
   bundle storage because it is immutable operational evidence, not Nuxt cache.
6. Install the known-good launch-compatible replacement with one or both unlock
   keys absent, verify root `config/` and packaged ingress artifact digests,
   install runtime dependencies, install/verify the reviewed loopback-only
   service definitions, run `systemctl daemon-reload`, and start `vl-nuxt`.
7. Poll process-local
   `http://127.0.0.1:3000/_internal/launch-readiness`; require safe closed HTTP
   200 and the complete isolation check set before any traffic is admitted.
   Inspect effective listeners and require agent/Nuxt/internal HTTP services on
   loopback only and Nginx as the sole non-loopback 80/443 listener.
8. Through the Nginx-facing production Host/TLS path from the allowlisted
   operator source, verify representative rich/thin HTML, policy/meta noindex,
   robots without sitemap, all three valid empty sitemap shapes, `no-store`, no
   evidence headers, no discovery link, public not-found for internal readiness
   and backend launch-internal paths, and failed direct 3000/8360/FastAPI root-
   sitemap bypass attempts from outside the loopback/private boundary.
9. In a controlled browser using the same allowed path, update and activate the
   current worker, inspect Cache Storage, and prove no HTML, root SEO, API,
   selective-open, or failed-open response can be replayed.
10. Disable maintenance and reload Nginx. Immediately repeat the public
    Nginx-facing closed probes.
11. Re-enable `vl-watchdog.timer` only after the reopened probes pass and record
    elapsed time and evidence.

If the replacement fails before reopening, traffic stays in maintenance. The
operator first rolls forward to a corrected closed replacement; if it is not
available, the operator restores the recorded known-good closed tarball and
repeats steps 6-9. The old open release is never restored. If a post-reopen
probe fails, maintenance is immediately re-enabled before roll-forward or
closed restore. Any uncertainty keeps traffic drained.

Workstream acceptance is an executable runbook plus a timed local rehearsal that
uses the Docker/process-local readiness probe, Nginx harness, and controlled
browser. It records the observed local time but does not claim a live SLA.
Stage 3 must externally prove the real target of five minutes from rollback
command start to reopened, publicly verified closed behavior.

A future multi-replica topology may add replica-by-replica drain and mixed-fleet
prevention as an appendix. That procedure is not a current Workstream 5
requirement and must not replace the single-host runbook above.

Engineering owns closed-state correctness, simulation evidence, packaging,
fingerprint agreement, immutable bundle mechanics, disclosure coverage, and
rollback mechanics. The responsible organization/legal process owns H1;
qualified ICT/data counsel owns H2; the project owner owns operational
authorization. No engineer, reviewer, test, environment value, readiness result,
or commit may infer external approval from technical readiness.
