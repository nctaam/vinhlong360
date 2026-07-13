# Launch Safety Gate Design

> STATUS: proposed; awaiting written-spec review; implementation must not start; launch remains blocked

## 1. Goal

Define one fail-closed boundary for search indexing and AI-image disclosure
without enabling indexing in any deployed environment.
The design makes the current closed state deterministic, testable, and
independent of backend availability. It also defines a selective-open state
that is simulated only in tests and cannot be reached through a partial env
change, stale cache, backend omission, or duplicated quality rule.
The required result is:
- production remains globally `noindex,follow`;
- public pages remain crawlable while admin/API/private routes stay blocked;
- closed mode advertises no sitemap in robots or HTML and serves valid empty
  sitemap XML;
- a future selective-open state requires two exact keys plus external gates;
- backend entity responses and sitemap selection share one quality authority;
- all current entity images are treated and disclosed as AI-generated;
- rollback to closed is bounded, restart-based, and does not depend on the backend.
## 2. Owner Decisions

These are fixed inputs, not design questions:
1. Global `noindex` stays enabled.
2. H1 and H2 remain unresolved external launch gates.
3. This work does not claim or imply that either gate is cleared.
4. Every current value under `entity.images` is AI-generated.
5. AI images never count as real, documentary, on-site, or first-hand photos.
6. UI option A is selected: disclosure appears at the point of image use.
7. Selective-open behavior is test simulation only in this workstream.
8. No real environment value is changed.
H1 is the external legal-entity and NĐ147 registration/licensing gate. H2 is
the external ICT/data-counsel review of the site's legal classification and
cross-border data obligations. A later indexing change also requires separate,
explicit project-owner authorization. This spec resolves none of those gates.
UI option A means the hero shows visible disclosure and gallery/lightbox views
retain it. Users do not need to open a policy page or credit drawer to learn
that an image is generated.
## 3. Current Inconsistency and Evidence

The repository can currently express conflicting signals:
- page meta robots and route response headers can disagree;
- `robots.txt` can advertise a sitemap while global meta remains closed;
- the global Nuxt head can emit `<link rel="sitemap">` while the gate is closed;
- prerendered HTML can bypass a request-time launch decision;
- the service worker can replay policy-bearing HTML or root SEO responses and
  currently caches successful responses without honoring `no-store`;
- sitemap and entity detail can apply different quality predicates;
- frontend code can infer quality from fields the backend does not own;
- cached HTML can outlive a policy change;
- missing `indexable` data can be mistaken for permission;
- image presence can be mistaken for evidence of an on-site photograph;
- visible UI, share metadata, and structured data can disclose differently;
- a generic graphic placeholder can inherit actual-image copy.
The launch gate therefore coordinates meta, response headers, robots, sitemap,
cache isolation, backend quality, link eligibility, and disclosure surfaces.
Baseline evidence before implementation:
- backend: 6168 passed, 47 skipped, 78 deselected, 1 xfailed, 1 warning;
- frontend serial: 8 files, 125 passed;
- frontend parallel timed out because of resource contention;
- the serial frontend pass is the accepted baseline;
- the parallel timeout is not classified as a product regression.
New tests may increase counts; the baseline is comparison evidence, not a
requirement that totals remain fixed.
## 4. Architecture

### 4.1 Nuxt Launch Safety Gate

Nuxt owns one server-only `LaunchSafetyGate` that binds every policy-bearing
response to one immutable decision. Dynamic renders compute it once per request;
an ordinary closed SWR hit may replay only a closed response created by the same
closed process:
```text
LaunchSafetyDecision
  operational_state: closed | selective-open | failed-open
  indexing_posture: closed | selective-open
  policy_fingerprint: string | none
  route_manifest_revision: string | none
  backend_policy_revision: string | none
  sitemap_action: closed-empty | guarded-proxy | unavailable
  reason: closed-default | valid-two-key-unlock | invalid-configuration
          | owner-approval-missing | policy-attestation-unavailable
          | policy-mismatch | cache-isolation-unavailable
```
It reads private runtime config. Unlock values never enter public runtime
config or browser JavaScript.
The two-key contract is exact:
1. `LAUNCH_INDEXING_MODE` equals `selective-open`.
2. `LAUNCH_INDEXING_OWNER_APPROVED` equals `true`.
Missing, blank, partial, unknown, case-changed, malformed, or mismatched values
produce `closed`. Mode aliases such as `1`, `true`, `open`, and `enabled` are
invalid. The literal `true` is accepted only for the owner-approval key; it is
not an alias for the mode key. A build-pinned policy fingerprint is validated
separately and is not a substitute for either runtime key.
After both runtime keys pass, Nuxt must obtain a backend policy attestation with
the matching fingerprint and route-manifest revision before the final decision
can become `selective-open`. A dynamic render computes the decision once and
passes it to all SEO surfaces; an allowed ordinary closed SWR response already
contains its closed decision evidence. Components do not reread env values,
bypass the attestation, or make independent launch decisions.
The global Nuxt head must not contain an unconditional sitemap discovery link.
Nuxt may emit `<link rel="sitemap" type="application/xml"
href="/sitemap.xml">` only from the request-bound head after the decision is
fully attested `selective-open`. Closed and failed-open HTML omit it.
### 4.2 Two-Key Unlock and Fail-Closed Rule

The mode key records launch intent. The owner-approval key records explicit
operational authorization by the project owner. Neither key alone carries
permission, and neither key proves that H1 or H2 has been completed.
The closed indexing posture is the startup default and the result of every
configuration error. Before both exact keys establish open intent, its
operational state is `closed`; after open intent, a fail-closed dependency
failure is operationally `failed-open`. Closed meta, header, robots, and empty
sitemap do not call the backend.
Selective-open must validate backend policy attestation before any page,
robots, or sitemap surface opens. Backend absence, an incomplete attestation,
or a mismatched fingerprint/revision yields one request-wide closed indexing
posture. For ordinary closed configuration the decision uses
`operational_state=closed`, `indexing_posture=closed`, and
`sitemap_action=closed-empty`. When both exact runtime keys express open intent
but attestation or policy agreement fails, the decision uses
`operational_state=failed-open`, `indexing_posture=closed`, and
`sitemap_action=unavailable`. Failed-open therefore preserves `noindex`, closed
robots, and no HTML sitemap discovery link while returning HTTP 503 for sitemap
endpoints instead of implying intentional URL removal.

### 4.2.1 Public Policy Response Contract

Nuxt owns the exact public header `X-Launch-Indexing-Policy`. It is present on
every public HTML response and on every response, including errors, from the
four root SEO endpoints `/robots.txt`, `/sitemap.xml`, `/sitemap-media.xml`, and
`/sitemap-index.xml`. Its value is exactly one of:
- `closed`: ordinary closed configuration;
- `selective-open`: both keys and the full backend attestation match;
- `failed-open`: both exact keys requested open, but attestation, revision,
  guarded-proxy validation, or another fail-closed dependency did not complete.

`failed-open` is an operational state, not index permission. Its HTML and robots
posture is closed, its HTML sitemap discovery link is absent, and its sitemap
responses are HTTP 503 `no-store`.
The policy header always reports gate state, not the indexability of the current
URL. In selective-open, a thin or non-allowlisted page can correctly carry
`X-Launch-Indexing-Policy: selective-open` while its meta and `X-Robots-Tag`
remain `noindex,follow`.

Every `selective-open` public HTML or root SEO response also carries these exact
evidence headers with non-empty matching values:
- `X-Launch-Policy-Fingerprint`;
- `X-Launch-Route-Manifest-Revision`;
- `X-Launch-Backend-Policy-Revision`.

A successful selective-open response from any of the three sitemap endpoints
also carries `X-Launch-Sitemap-Batch-Revision`. Closed and failed-open responses
omit all four evidence headers so stale or mismatched values cannot look valid.
The values are reviewed opaque revision identifiers only. Headers must not
contain either unlock value, secret material, backend URLs, environment dumps,
free-form failure detail, or legal/owner evidence. Internal logs may record the
stable `reason` code. Nuxt sets the public contract after validating upstream
evidence; Nginx preserves it and must neither synthesize nor overwrite it.
### 4.3 Policy Fingerprint

The fingerprint identifies reviewed semantics, not merely a deployment. It
covers:
- backend `index_policy` predicate version;
- closed/selective-open matrix version;
- AI-image classification rule;
- disclosure copy version;
- cache-isolation rule version.
The value is stable and build-pinned in reviewed source. Runtime code does not
invent a replacement. Nuxt supplies the expected value on selective-open
policy requests; the backend returns its active value. The fingerprint proves
software-policy agreement only; it is not owner approval or legal clearance.
A missing or mismatched backend fingerprint or route-manifest revision prevents
selective-open globally. Non-entity pages stay `noindex`, `robots.txt` omits its
sitemap line, entity detail remains `noindex` without consulting a local
fallback rule, HTML omits sitemap discovery, the public policy header is
`failed-open`, and sitemap endpoints follow `sitemap_action=unavailable`.
### 4.4 Cache Isolation

Workstream 5 does not add a custom Nitro cache-key system. The current Nuxt
route rules cache policy-bearing HTML and entity responses by URL only, so they
cannot safely represent fingerprint/revision state.
Policy-bearing resources in this section are every public HTML document, all
four root SEO endpoints, and public API responses that contain or feed entity
or ward launch-policy decisions. The required behavior is deliberately simpler:
- ordinary closed processes may retain existing SWR for public HTML because the
  mode is fixed for the lifetime of that process and the response header remains
  closed;
- any process started with both open-intent keys disables SWR for policy-bearing
  HTML, entity-policy/API responses, robots, and all sitemap endpoints before it
  can attempt backend attestation;
- selective-open simulation and failed-open behavior use `no-store` and never
  read or populate a policy-bearing SWR entry;
- closed robots and all closed sitemap responses use `no-store`;
- Nginx must not cache the four guarded root SEO endpoints.

Prerender is not a permitted policy source. The launch-compatible Nuxt build
must exclude every public HTML route, all four root SEO endpoints, and all
entity-policy/API responses from Nitro prerender output; only policy-neutral
build assets may be emitted statically. Startup/readiness for an open-intent
process must fail if its Nitro manifest or output tree contains a policy-bearing
prerender artifact. No selective-open or failed-open response may be served
from generated static HTML, even when the route also has runtime middleware.

The service worker is more conservative because it outlives server processes
and cannot safely infer launch state before a navigation. It may cache only an
explicit allowlist of policy-neutral static assets. It must return without
`respondWith`, `cache.match`, or `cache.put` for:
- every navigation or request accepting `text/html`;
- the four root SEO endpoint paths;
- every `/api/**` request, including entity/ward policy responses;
- any request whose request cache mode is `no-store`.

Every remaining service-worker cache write must inspect `Cache-Control` and
skip the write when the response contains `no-store`. Activation of the new
worker deletes the legacy HTML cache and every prior-version cache that could
contain HTML, root SEO, or API responses, retaining only the new
policy-neutral asset cache. Selective-open and failed-open responses therefore
cannot be read, written, or intercepted by the worker. Rollback verification
must inspect a controlled browser's Cache Storage and prove that no
policy-bearing or open-state artifact remains.
Fingerprint, route-manifest revision, backend-policy revision, entity revision,
and sitemap batch revision remain validation inputs and response evidence, not
cache keys in this workstream. Designing and enabling selective-open caching is
a separately authorized Stage 3 task after H1/H2 and owner approval.
### 4.5 Backend Single Authority

The backend owns one `index_policy` module as the sole entity indexability
authority. Entity response serialization and sitemap selection call that same
module. A batch wrapper remains owned by the module and preserves single-item
semantics.
Nuxt consumes the result. It does not reconstruct entity indexability from
image count, description length, verification flags, or other entity fields.

### 4.6 Public Route Policy

Non-entity canonical pages use the reviewed machine-readable manifest
`config/launch-indexing-policy.json`, consumed by Nuxt and by the backend's
static sitemap builder. The
manifest classifies routes into three explicit groups:
- `indexable-public`: canonical core, listing, and static/legal routes that may
  open only in selective-open;
- `noindex-follow-public`: search results, thin/public details, and public share
  contexts that remain crawlable so bots can read page-level `noindex`;
- `crawl-blocked-sensitive`: admin, admin API, application API/auth, account-
  bound workspaces, private previews, and other authorization-bound routes.
The manifest contributes to the policy fingerprint.
Entity and ward/detail eligibility remain backend decisions. The route manifest
does not duplicate entity quality thresholds.

### 4.7 Open Sitemap Ownership

The backend is the sole owner of selective-open sitemap assembly and XML
serialization. It emits all three documents from one attested generation batch:
- `/sitemap.xml` loads static canonical routes from the shared route manifest,
  evaluates detail URLs through `index_policy`, and merges/deduplicates the
  canonical page URLs into a standard `<urlset>`;
- `/sitemap-media.xml` includes only backend-indexable entities with normalized
  renderable AI images, emits the required AI disclosure in image captions, and
  excludes placeholders and malformed media;
- `/sitemap-index.xml` references exactly `/sitemap.xml` and
  `/sitemap-media.xml` from that same completed batch and returns 503 if either
  child document is unavailable or policy-inconsistent.
Every document emits fingerprint, manifest revision, backend policy revision,
and the same deterministic sitemap batch revision in the exact evidence headers
defined in Section 4.2.1.
An attested open batch is built from one authoritative database snapshot of
entities, relationships, and itineraries. `web/data.json` is not an allowed
fallback for attestation, open sitemap generation, or batch revision. Unit tests
may inject explicit in-memory fixtures; a production DB snapshot failure makes
the open batch unavailable and yields HTTP 503 through the Nuxt gate.
Nuxt owns only the public launch gate, closed endpoint bodies, attestation, and
the guarded proxy. It does not merge URL lists or serialize open sitemap XML.
Nuxt forwards an open sitemap response only after validating all required policy
and batch evidence headers from Section 4.2.1; otherwise it returns HTTP 503
`no-store` with `X-Launch-Indexing-Policy: failed-open` and no evidence headers.

### 4.8 Public Ingress Ownership

Both `nginx.conf` and `nginx-ssl.conf` currently send root robots/sitemap paths
directly to FastAPI, bypassing the Nuxt gate. Workstream 5 must route exactly
`/robots.txt`, `/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml` to
the `vl360_nuxt` upstream before the catch-all route.
The dedicated ingress location must remove Nginx proxy caching for these paths
and preserve host/forwarded headers. FastAPI remains reachable from Nuxt through
the internal API base for guarded open-mode proxying, but is not the public
entry point for the four root SEO endpoints.
Static Nginx configuration tests cover both files, and an Nginx-facing HTTP
integration test proves that all four public paths preserve the exact
`X-Launch-Indexing-Policy` value and required selective-open evidence headers,
and cannot bypass the Nuxt gate.
## 5. Policy Matrix

The matrix is normative:
| Surface | Closed | Selective-open simulation | Failed-open attempt |
| --- | --- | --- | --- |
| `X-Launch-Indexing-Policy` | `closed` | `selective-open`, plus all required matching evidence headers | `failed-open`; no evidence headers |
| HTML meta robots | `noindex,follow` on every public page | `index,follow` only for an allowlisted canonical public route or a backend-indexable detail; otherwise `noindex,follow` | `noindex,follow` on every public page |
| `X-Robots-Tag` | `noindex, follow` on public HTML | Mirrors the page decision; omission is not permission | `noindex, follow` on public HTML |
| HTML sitemap discovery link | Absent | Present only after full request-wide attestation | Absent |
| Robots public crawl | Allow public routes | Allow public routes | Allow public routes under the closed rules |
| Robots sensitive crawl | Block every `crawl-blocked-sensitive` route consistently in every applicable user-agent group | Block the same sensitive route set | Block the same sensitive route set |
| Robots sitemap line | Absent | Present only when both keys and backend policy attestation are valid | Absent |
| `/sitemap.xml` | Valid empty `<urlset>`, HTTP 200, `no-store` | Shared-manifest canonical routes plus backend-indexable canonical detail URLs | HTTP 503 `no-store`; never stale or empty-success fallback |
| `/sitemap-media.xml` | Valid empty media `<urlset>`, HTTP 200, `no-store` | Disclosed AI image entries for backend-indexable entities only; no placeholders | HTTP 503 `no-store`; never stale or empty-success fallback |
| `/sitemap-index.xml` | Valid empty `<sitemapindex>`, HTTP 200, `no-store` | Exactly the main and media child locations from one matching generation batch | HTTP 503 `no-store`; never stale or partial fallback |
| Delivery/cache source | Ordinary closed SWR is allowed; no policy-bearing prerender or service-worker interception | Dynamic per-request response, `no-store`; no prerender, SWR, proxy-cache, or service-worker source | Dynamic fail-closed response, `no-store`; no prerender, SWR, proxy-cache, or service-worker source |
| Public links | Followable for usable public pages | Rich and thin public pages may remain linked | Same as closed |
| Private links | Not promoted through public nav or sitemap | Same restriction | Same restriction |
| Canonical core/listing/static page | `noindex,follow`, absent from sitemap | `index,follow` only when allowed by the shared route manifest; present in sitemap under the same rule | `noindex,follow`, absent from sitemap |
| Thin public entity | `noindex,follow`, absent from sitemap | `noindex,follow`, absent from sitemap | `noindex,follow`, absent from sitemap |
| Rich public entity | `noindex,follow`, absent from sitemap | `index,follow`, present in sitemap | `noindex,follow`, absent from sitemap |
Additional rules:
- closed and failed-open never advertise a sitemap through robots or HTML;
- closed never reads backend sitemap data;
- `follow` supports legitimate navigation but is not index permission;
- search and other `noindex-follow-public` routes remain crawlable but never
  enter the sitemap or selective-open index set;
- account-specific, authorization-bound, API/auth, private preview, admin, and
  other `crawl-blocked-sensitive` routes are disallowed consistently;
- a Googlebot- or AI-bot-specific group may not override the shared sensitive
  disallow set; it must inherit or repeat the same restrictions;
- the launch gate never overrides authorization or publication eligibility;
- non-entity public routes use the shared route manifest, not an ad hoc page
  default or a second hand-maintained sitemap list;
- rich means the shared backend contract returns a valid positive decision;
- thin means public but not backed by a valid positive decision;
- only a fingerprint-matching positive decision enters the open sitemap;
- canonical URL validation remains required for an indexable entity.

### 5.1 Sitemap Endpoint Contract

Closed behavior is required independently for every exposed endpoint:
- `/sitemap.xml`: HTTP 200, `no-store`, valid empty `<urlset>`;
- `/sitemap-media.xml`: HTTP 200, `no-store`, valid empty `<urlset>` with the
  media namespace and no image entries;
- `/sitemap-index.xml`: HTTP 200, `no-store`, valid empty `<sitemapindex>` with
  no child sitemap locations.
Each closed endpoint makes zero backend calls. In selective-open, all three are
proxied only after valid request-wide policy attestation. Open shapes are:
- main sitemap: manifest-approved canonical pages plus backend-indexable detail
  pages;
- media sitemap: image entries only for indexable entities, with AI disclosure
  and no placeholders;
- sitemap index: the two canonical child sitemap locations from one matching
  generation batch.
A proxy, attestation, completeness, child-generation, or revision failure on
any endpoint returns HTTP 503 `no-store` with
`X-Launch-Indexing-Policy: failed-open`; an endpoint never falls back to a stale,
closed-empty, or partially open document. All closed, selective-open, and
failed-open sitemap responses follow the public header contract in Section
4.2.1.
## 6. Backend Indexability Contract

The shared module returns:
```text
IndexPolicyDecision
  kind: entity | ward | itinerary
  indexable: boolean
  reasons: stable reason-code list
  policy_fingerprint: string
  policy_revision: string
```
`indexable` defaults to false; there is no nullable or implicit-true state.
Reason codes support tests and review but do not expose hidden moderation detail.
Public eligibility is evaluated before quality. A missing, provisional,
explicitly unverified, private, or otherwise ineligible entity is not
indexable.
The quality gate is deterministic and shared by single and batch evaluation.
The normative per-kind rules are:
- non-place entity detail: preserve public eligibility and require at least 130
  descriptive words; the former 100-word-plus-real-image branch cannot pass
  because current images are AI and provide zero real-image credit;
- ward/place detail: preserve the existing hub gate, requiring public
  eligibility and either more than one public-eligible child or at least 60
  summary words;
- itinerary detail: remain `noindex,follow` and excluded from every sitemap in
  this workstream because no reviewed itinerary quality predicate exists yet;
- public shared-plan/share routes: remain `noindex,follow` and excluded;
- static area/core/listing/legal pages: use the shared route manifest, not this
  dynamic decision contract.
Adding an itinerary quality predicate or widening supported dynamic kinds is a
separate reviewed change, not an implicit side effect of selective-open.
Its fixed image rules are:
- non-empty current `entity.images` means AI imagery;
- AI imagery contributes zero to `real_image_count`;
- AI imagery cannot satisfy `has_real_image`;
- dimensions, file existence, and visual attractiveness do not alter class;
- malformed image metadata never becomes a real-image signal;
- an entity cannot become rich merely because AI images are present;
- copy must not call current AI imagery real, documentary, or on-site;
- sitemap and entity detail receive identical decisions for identical input.
The public entity/ward response includes at least `indexable`,
`policy_fingerprint`, and `policy_revision`. The sitemap builder calls the same
module directly or through its owned batch wrapper, never a duplicate checklist.
## 7. AI Disclosure Surfaces

### 7.1 Canonical Copy

Actual AI entity image:
> Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.
Generated graphic placeholder for an entity without its own image:
> Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.
These strings and the short `Minh họa AI` label live in the versioned artifact
`config/ai-disclosure.json`, consumed by Python and TypeScript. Its version
contributes to the policy fingerprint. Short variants may not remove the
distinction between actual AI imagery and a generic placeholder.
### 7.2 Hero, Gallery, and Lightbox

- Actual AI hero: visible pill with the short label `Minh họa AI`.
- Placeholder hero: visible pill/caption with exact placeholder copy only.
- The hero image/figure itself references the full canonical sentence through
  `aria-describedby`; the pill is not the sole association target.
- Pill remains readable at mobile/desktop widths and exposed as text to AT.
- Gallery and lightbox consume structured image descriptors containing source,
  alt text, classification, disclosure key, and full caption rather than bare
  URL strings.
- Each AI gallery item carries the exact disclosure in caption data.
- The selected gallery caption and lightbox show the full copy.
- Slide changes preserve accessible caption association.
- Reopening the lightbox does not lose disclosure.
- Placeholder tiles are not counted or described as entity photography.
### 7.3 Share, OG, and Twitter

- First-party native-share payload text includes the AI disclosure when an AI
  image is referenced. The page DOM and controllable OG/Twitter alt fields also
  disclose it; the design does not promise that a third-party platform will
  render every supplied field visibly.
- Copy-link may copy only the canonical URL because the destination hero
  discloses without interaction.
- A placeholder preview uses placeholder copy and does not imply a real view.
- `og:image:alt` and `twitter:image:alt` describe the scene and append the
  exact applicable disclosure.
- Metadata avoids `real photo`, `ảnh thật`, `documentary`, `on-site photo`, and
  equivalent claims for current entity images.
### 7.4 JSON-LD and Image Sitemap

- AI `ImageObject.caption` or `description` includes the exact AI disclosure.
- No author, EXIF, capture location, or photographer credit is fabricated.
- AI image-sitemap entries include disclosure in the supported caption field.
- Placeholder graphics are excluded from image sitemap entries.
- Placeholders are not promoted as entity `ImageObject` evidence.
- Structured data never upgrades AI imagery into first-hand evidence.
## 8. Data Flow

Closed request, including each sitemap endpoint:
```text
request
  -> read private Nuxt launch config
  -> one or both keys absent/invalid
  -> LaunchSafetyDecision(operational_state=closed, indexing_posture=closed)
  -> closed meta + X-Launch-Indexing-Policy: closed + closed robots
  -> omit HTML sitemap discovery link
  -> valid empty sitemap, no-store
  -> no backend launch-policy dependency
  -> no policy-bearing prerender or service-worker source
```
Selective-open preflight for every surface:
```text
request -> both runtime keys exact -> fetch backend policy attestation
  -> fingerprint + route-manifest revision + backend-policy revision match
  -> yes: operational/selective-open + indexing/selective-open
          + guarded-proxy sitemap action
          + X-Launch-Indexing-Policy: selective-open
          + three matching public evidence headers
  -> no/error/incomplete: operational/failed-open + indexing/closed
          + unavailable sitemap action
          + X-Launch-Indexing-Policy: failed-open
          + no evidence headers or HTML sitemap discovery link
```
Selective-open non-entity page simulation:
```text
attested request -> classify path through shared route manifest
  -> indexable-public canonical route: index,follow
  -> noindex-follow-public or crawl-blocked-sensitive: noindex
  -> emit the HTML sitemap discovery link only for this fully attested state
  -> dynamic no-store response; no prerender, SWR, or service-worker source
```
Selective-open entity simulation:
```text
attested request -> fetch public entity policy
  -> verify indexable + fingerprint + revision
  -> valid true: index,follow
  -> false/missing/mismatch: noindex,follow
  -> emit uncached no-store response; revisions remain validation evidence
```
Selective-open sitemap simulation:
```text
sitemap -> both keys exact -> validate backend policy attestation
  -> guarded proxy to backend sitemap owner
  -> main: merge manifest routes + indexable details into page urlset
  -> media: emit disclosed AI images for indexable entities only
  -> index: reference main + media from the same completed batch
  -> Nuxt validates fingerprint + manifest revision + batch revision
  -> forward intact response uncached with selective-open policy/evidence headers
     and no-store, or return 503 no-store with failed-open policy header only
```
Disclosure classification:
```text
renderable entity image -> actual AI -> AI pill/caption disclosure
no renderable image     -> placeholder -> exact placeholder copy only
malformed image data    -> omit from media; never real; never quality credit
```
## 9. Failure Behavior

- config unreadable, missing, partial, or invalid before both exact keys:
  closed posture,
  `X-Launch-Indexing-Policy: closed`, and no HTML sitemap discovery link;
- backend policy attestation missing, unavailable, incomplete, or mismatched:
  request-wide closed indexing and robots behavior,
  `X-Launch-Indexing-Policy: failed-open`, no public evidence headers, and no
  HTML sitemap discovery link; sitemap endpoints return HTTP 503 `no-store`
  through `sitemap_action=unavailable`;
- backend unavailable in closed: closed behavior remains fully usable;
- open sitemap backend error: HTTP 503, `Cache-Control: no-store`, and
  `X-Launch-Indexing-Policy: failed-open`;
- closed `/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml` each
  return their specified empty XML shape with zero backend calls;
- open `robots.txt` backend error: closed robots response, no sitemap line, and
  `X-Launch-Indexing-Policy: failed-open`;
- entity detail missing `indexable`: `noindex,follow`;
- positive `indexable` with fingerprint mismatch: `noindex,follow`;
- entity detail missing required revision: `noindex,follow`;
- partial open sitemap policy response: 503 `no-store`, not partial success;
- invalid/non-canonical URL: omit and report; return 503 if response
  completeness cannot be proven;
- an open-intent Nuxt process that cannot disable policy-bearing SWR/cache:
  fails health readiness and must not serve selective-open traffic;
- an open-intent build with policy-bearing Nitro prerender output, or a worker
  that can intercept/cache a policy-bearing response, fails readiness;
- service-worker activation that does not purge legacy policy-bearing caches is
  a rollout/rollback failure;
- sitemap batch-revision validation failure: HTTP 503 `no-store`;
- present current image with missing disclosure metadata: use exact AI copy;
- no image: use placeholder plus exact placeholder copy;
- attempted real/documentary labeling of current entity images: test and review
  failure.
Sitemap 503 is distinct from an empty success. It avoids presenting an outage
as intentional URL removal while refusing to serve stale or unverified URLs.
## 10. Test Strategy and Baseline Evidence

Every behavior change follows RED -> GREEN.
Nuxt unit tests cover the full two-key truth table: no keys, either key alone,
wrong mode, wrong owner-approval value, case/whitespace variants, and both exact
values. Fingerprint matching, mismatch, and previous-version behavior are a
separate policy-agreement matrix.
Decision-contract tests assert that every selective-open result retains the
fingerprint, route-manifest revision, backend-policy revision, and guarded-proxy
sitemap action required by downstream cache-isolation and endpoint logic.
Closed tests assert meta, header, robots, and empty sitemap without a successful
backend mock. Open simulations cover rich, thin, missing-field, mismatch, and
backend-error behavior.
Public-header contract tests assert the exact `X-Launch-Indexing-Policy` values
`closed`, `selective-open`, and `failed-open` on representative public HTML and
all four root SEO endpoints, including sitemap 503 responses. They assert the
three matching evidence headers on every selective-open response, the sitemap
batch header on successful open sitemap responses, and the absence of evidence
headers in closed/failed-open.
Attestation tests prove that static pages, entity pages, robots, and all sitemap
endpoints share one request-wide decision and cannot open independently.
They distinguish ordinary closed configuration (`closed-empty`) from a failed
open attempt (`unavailable`) without weakening the closed indexing posture.
Selective-open sitemap tests assert endpoint-specific XML: canonical page URLs
for main, disclosed AI image entries with no placeholders for media, and exactly
the two matching child locations for the index. A failed or mismatched child
forces the sitemap index to 503 rather than partial output.
Backend tests compare single and batch decisions for rich candidates, thin,
provisional, explicitly unverified, missing, AI-image, no-image, and malformed
image fixtures. They cover the preserved ward threshold, public-child counting,
and explicit itinerary/shared-plan exclusion. Adding AI images must not change
any real-image criterion.
Sitemap batch tests use injected fixtures and a real test database snapshot;
attested open generation must fail when the authoritative DB snapshot is
unavailable and must never fall back to `web/data.json`.
Integration tests assert:
- meta and `X-Robots-Tag` agreement;
- the unconditional Nuxt app-head sitemap link is absent; closed and failed-open
  HTML contain no sitemap discovery link, while fully attested selective-open
  HTML contains exactly one canonical discovery link;
- open-intent startup disables SWR/cache for policy-bearing HTML, entity policy
  responses, robots, and all sitemap endpoints;
- Nitro prerender manifests and output contain no policy-bearing public HTML
  route, root SEO, or entity-policy artifact, and open-intent readiness rejects
  an injected policy-bearing prerender artifact;
- the service worker does not intercept or access Cache Storage for navigation,
  HTML, the four root SEO endpoints, or `/api/**`; honors request/response
  `no-store` on remaining paths; and activation deletes legacy policy caches;
- both Nginx configs route the four root SEO endpoints to Nuxt with no proxy
  cache, and an Nginx-facing probe observes the exact Nuxt policy and required
  selective-open evidence headers without Nginx synthesis or overwrite;
- closed robots allows both public route groups, blocks every sensitive-route
  category in every applicable bot group, and has no sitemap line;
- all three closed sitemap endpoints return their specified valid empty XML,
  HTTP 200, `no-store`, and make no backend call;
- open main, media, and index sitemaps each satisfy their endpoint-specific XML
  and shared-generation-revision contracts;
- open sitemap error is 503 `no-store`;
- open robots error falls back closed;
- entity detail without valid positive policy remains `noindex`;
- no selective-open or failed-open response reads or populates a policy-bearing
  SWR/proxy cache entry;
- a controlled-browser rollback check finds no policy-bearing Cache Storage
  entries and cannot replay a prior selective-open response offline;
Disclosure tests verify the short AI pill plus its full accessible description,
and exact full copy in gallery, lightbox, native-share payload, OG/Twitter alt,
JSON-LD, and image sitemap. They verify placeholder copy, placeholder
exclusions, keyboard access, accessible captions, and a text scan for forbidden
real/documentary claims.
Regression gate:
- rerun backend suite against the 6168/47/78/1/1 baseline;
- rerun frontend serially against 8 files/125 passed plus new tests;
- record a repeated parallel resource timeout separately;
- do not classify that known timeout as a functional regression when serial
  evidence is green.
## 11. Task Boundaries and Review Workflow

The implementation plan separates:
1. public-route policy JSON plus Python/TypeScript loaders and parity tests;
2. AI-disclosure JSON plus Python/TypeScript loaders and parity tests;
3. backend non-place entity index-policy decision and RED/GREEN unit tests;
4. ward policy plus itinerary/shared-plan exclusion contracts;
5. public entity/ward response integration with policy revision fields;
6. authoritative DB snapshot and deterministic sitemap batch revision;
7. backend policy-attestation endpoint;
8. backend main-sitemap generation from the attested DB batch;
9. backend media-sitemap generation with AI disclosure and exclusions;
10. backend sitemap-index generation and child-batch consistency;
11. Nuxt two-key decision, backend attestation, and exact public policy/evidence
    header contract;
12. Nuxt prerender exclusion, open-intent SWR isolation, service-worker bypass
    and purge behavior, plus readiness failures;
13. closed/failed-open Nuxt meta, conditional HTML sitemap discovery, robots,
    and three empty/unavailable sitemap handlers;
14. Nginx ingress changes in both configs plus config/boundary tests;
15. entity/ward detail robots consumption and failure behavior;
16. hero AI pill, placeholder distinction, and accessible figure description;
17. structured gallery/lightbox image descriptors and captions;
18. native-share payload plus OG/Twitter alt disclosure;
19. JSON-LD disclosure and backend media metadata parity;
20. browser matrix, full regression evidence, and restart-based rollback runbook.
Each task uses a fresh implementer context. Each change records a failing RED
test before the smallest coherent implementation and records GREEN afterward.
Each implemented task receives two fresh reviews in order:
1. spec-compliance review;
2. code-quality review after spec compliance passes.
The implementer fixes findings and requests re-review. Critical and Important
findings block progression. No task is complete with an open Important finding.
Cross-task scope changes require an explicit plan update.
## 12. Non-Goals

This workstream does not:
- deploy, push, merge, or release;
- change real env values or secrets;
- enable indexing on any live target;
- resolve H1/H2, make a legal decision, or grant owner approval;
- migrate, rewrite, backfill, or delete entity data;
- replace AI images with real or user-generated photographs;
- redesign navigation, moderation, or unrelated eligibility rules;
- promise search-engine inclusion or ranking;
- use `robots.txt` as authorization;
- add a second frontend quality predicate;
- enable or design selective-open response caching before Stage 3 approval;
- advertise a sitemap through robots or HTML while closed or failed-open;
- describe current AI imagery as real, documentary, or on-site photography.
## 13. Acceptance Criteria

Implementation is accepted only when:
- default, missing, partial, invalid, and mismatched config is closed;
- only two exact valid runtime keys plus a matching build/backend fingerprint
  produce selective-open in tests;
- every public HTML response and every response from the four root SEO
  endpoints carries exactly one `X-Launch-Indexing-Policy` value from the
  closed/selective-open/failed-open contract;
- every selective-open decision carries fingerprint, route-manifest revision,
  backend-policy revision, and `sitemap_action=guarded-proxy`;
- every selective-open public HTML/root SEO response carries the three required
  matching evidence headers, successful open sitemap responses also carry the
  matching batch revision, and closed/failed-open responses omit them;
- missing or mismatched backend attestation keeps pages and robots closed while
  exposing the failed-open operational header and making all sitemap endpoints
  return 503 `no-store` rather than closed-empty success;
- deployed config remains unchanged and globally closed;
- closed public HTML emits `noindex,follow` in meta and header;
- closed and failed-open HTML omit sitemap discovery links; fully attested
  selective-open HTML emits exactly one `/sitemap.xml` discovery link;
- closed robots allows `indexable-public` and `noindex-follow-public`, blocks
  every `crawl-blocked-sensitive` route consistently, and has no sitemap line;
- `/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml` each return the
  specified empty XML, HTTP 200, `no-store`, and remain backend-independent;
- backend `index_policy` is the only indexability authority;
- entity and ward thresholds match the normative per-kind contract, while
  itinerary and shared-plan details remain `noindex` and absent from sitemaps;
- entity response and sitemap share decision, fingerprint, and revision;
- attested open sitemap generation uses one authoritative DB snapshot and has no
  `web/data.json` fallback;
- non-entity page meta and static sitemap entries share the same route manifest;
- both Nginx configs route the four root SEO endpoints through Nuxt without
  proxy caching, and the public boundary preserves the exact Nuxt policy and
  required selective-open evidence headers;
- all current `entity.images` are classified as AI;
- AI imagery contributes nothing to real-image criteria;
- allowlisted canonical public routes and rich public entities open and enter
  the simulated open sitemap under their respective shared contracts;
- thin/private/invalid/missing/mismatch cases stay excluded or `noindex`;
- open sitemap backend error is 503 `no-store`;
- open robots error returns closed robots with the failed-open policy header;
- open entity detail without valid positive policy is `noindex`;
- ordinary closed SWR cannot be reused by an open-intent process, and every
  selective-open/failed-open policy-bearing response is uncached `no-store`;
- Nitro produces no policy-bearing public HTML route, root SEO, or
  entity-policy prerender artifact, and open-intent readiness rejects any such
  artifact;
- the service worker never intercepts, reads, or writes navigation/HTML, root
  SEO, or `/api/**` responses; honors `no-store` for every remaining cache
  candidate; and activation purges all legacy policy-bearing caches;
- one versioned disclosure JSON artifact drives Python and TypeScript copy, and
  gallery/lightbox use structured descriptors whose image/figure references the
  full disclosure;
- the short AI pill and full accessible description appear on every actual AI
  hero; exact full disclosure appears on gallery/lightbox/share/metadata surfaces;
- exact placeholder copy appears only on placeholder surfaces;
- placeholders are excluded from image sitemap and entity `ImageObject`;
- no current AI image is called real or documentary;
- new behavior shows RED then GREEN evidence;
- backend and serial frontend regression suites pass;
- rollback runbook drains old replicas, force-recreates closed replacements,
  verifies every replica plus Nginx and a controlled browser cache within five
  minutes, proves no open policy/prerender/service-worker artifact remains, and
  forbids mixed fleets;
- spec review precedes quality review for each task;
- no Important finding remains open;
- H1 and H2 remain explicit unresolved launch blockers.
## 14. Rollout, Rollback, and Legal/Owner Gates

Stage 0 is this workstream: implement and test while all real environments stay
closed. Stage 1 gathers truth-table, policy, disclosure, cache-isolation,
ingress, and full regression evidence. Stage 2 requires externally recorded H1
legal-entity/NĐ147
completion, H2 qualified-counsel review, and separate explicit project-owner
authorization. Stage 3 would be a separately authorized operational task and is
outside this spec.
A test simulation, merged commit, passing suite, or generated fingerprint is
not H1 or H2 approval.
Any future selective-open request requires:
- explicit H1 completion;
- explicit H2 counsel sign-off;
- explicit project-owner authorization;
- reviewed build-pinned fingerprint;
- matching backend and Nuxt fingerprints;
- current regression and candidate sitemap evidence;
- verified disclosures on every required surface;
- named rollback owner and observation window.
Both runtime keys are changed as one controlled operation. A partial change is
expected and verified to remain closed.
Nuxt configuration is process-start state. Rollback therefore removes or
invalidates either key and force-recreates every Nuxt replica. A restart is
acceptable only when the runbook first proves the old Nitro cache is purged;
changing an env file alone is not rollback completion.
For the current single-host deployment, the rollback target is five minutes
from command start to externally verified closed behavior. Public traffic is
drained from old open replicas before closed replacements receive traffic; a
mixed open/closed fleet is not an allowed rolling state. If all replacements
are not healthy and verified within the bound, public traffic remains drained
rather than returning to an unverified replica.
Post-restart verification checks every Nuxt replica and the Nginx-facing public
path: representative rich/thin pages, meta/header `noindex,follow`, robots
without sitemap advertisement, retained sensitive-route blocking, valid empty
output from all three sitemap endpoints with HTTP 200 `no-store`, the closed
`X-Launch-Indexing-Policy` header with no evidence headers, no HTML sitemap
discovery link, no policy-bearing Nitro prerender output, and absence of any old
open-intent process. A controlled browser then updates/activates the current
service worker, inspects Cache Storage, and proves that no HTML, root SEO, API,
selective-open, or failed-open artifact can be replayed. Any failed check keeps
public traffic drained.
Engineering owns closed-state correctness, simulation evidence, fingerprint
agreement, and rollback mechanics. The responsible organization/legal process
owns H1; qualified ICT/data counsel owns H2; the project owner owns operational
authorization. No engineer, reviewer, test, env value, or commit may infer any
external approval from technical readiness.
