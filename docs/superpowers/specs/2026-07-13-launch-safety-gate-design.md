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
- closed mode advertises no sitemap and serves valid empty sitemap XML;
- a future selective-open state requires two exact keys plus external gates;
- backend entity responses and sitemap selection share one quality authority;
- all current entity images are treated and disclosed as AI-generated;
- rollback to closed is immediate and does not depend on the backend.
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
- sitemap and entity detail can apply different quality predicates;
- frontend code can infer quality from fields the backend does not own;
- cached HTML can outlive a policy change;
- missing `indexable` data can be mistaken for permission;
- image presence can be mistaken for evidence of an on-site photograph;
- visible UI, share metadata, and structured data can disclose differently;
- a generic graphic placeholder can inherit actual-image copy.
The launch gate therefore coordinates meta, response headers, robots, sitemap,
cache identity, backend quality, link eligibility, and disclosure surfaces.
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

Nuxt owns one server-only `LaunchSafetyGate` that returns an immutable decision
for each request:
```text
LaunchSafetyDecision
  mode: closed | selective-open
  fingerprint: string
  route_manifest_revision: string
  reason: closed-default | valid-two-key-unlock | invalid-configuration
          | owner-approval-missing | policy-attestation-unavailable
          | policy-mismatch
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
can become `selective-open`. The decision is computed once per request and
passed to all SEO surfaces. Components do not reread env values, bypass the
attestation, or make independent launch decisions.
### 4.2 Two-Key Unlock and Fail-Closed Rule

The mode key records launch intent. The owner-approval key records explicit
operational authorization by the project owner. Neither key alone carries
permission, and neither key proves that H1 or H2 has been completed.
Closed is the startup default and the result of every configuration error.
Closed meta, header, robots, and empty sitemap do not call the backend.
Selective-open must validate backend policy attestation before any page,
robots, or sitemap surface opens. Backend absence, an incomplete attestation,
or a mismatched fingerprint/revision yields one request-wide closed decision.
### 4.3 Policy Fingerprint

The fingerprint identifies reviewed semantics, not merely a deployment. It
covers:
- backend `index_policy` predicate version;
- closed/selective-open matrix version;
- AI-image classification rule;
- disclosure copy version;
- cache-fencing schema version.
The value is stable and build-pinned in reviewed source. Runtime code does not
invent a replacement. Nuxt supplies the expected value on selective-open
policy requests; the backend returns its active value. The fingerprint proves
software-policy agreement only; it is not owner approval or legal clearance.
A missing or mismatched backend fingerprint or route-manifest revision prevents
selective-open globally. Non-entity pages stay `noindex`, `robots.txt` omits its
sitemap line, sitemap endpoints use closed output, and entity detail remains
`noindex` without consulting a local fallback rule.
### 4.4 Cache Fencing

Every open cache identity starts with:
```text
route + selective-open + policy fingerprint
      + route-manifest revision + backend-policy revision
```
It then uses one surface-specific suffix:
```text
static canonical page -> static
entity detail         -> entity policy revision
robots.txt            -> robots
open sitemap          -> deterministic sitemap batch revision
```
Closed artifacts use `route + closed + closed-sentinel` and need no backend
revision. A sitemap batch revision deterministically covers the manifest
revision, backend policy revision, entity-data revision, and the evaluated URL
set; it is not a concatenation of per-entity revisions.
Open HTML, payload, route-rule, robots, or sitemap artifacts cannot match a
closed cache namespace. If an open page/robots identity cannot be computed, the
request uses closed output. If an open sitemap identity is incomplete, the
endpoint returns HTTP 503 `no-store` rather than an empty or cached document.
Closed `robots.txt` and sitemap responses use `Cache-Control: no-store`.
Any future open sitemap cache must be short-lived and fingerprint-fenced.
### 4.5 Backend Single Authority

The backend owns one `index_policy` module as the sole entity indexability
authority. Entity response serialization and sitemap selection call that same
module. A batch wrapper remains owned by the module and preserves single-item
semantics.
Nuxt consumes the result. It does not reconstruct entity indexability from
image count, description length, verification flags, or other entity fields.

### 4.6 Public Route Policy

Non-entity canonical pages use one reviewed, machine-readable public-route
manifest consumed by Nuxt and by the backend's static sitemap builder. The
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
serialization. It loads static canonical routes from the shared route manifest,
evaluates detail URLs through `index_policy`, merges/deduplicates the results,
and emits fingerprint, manifest revision, and deterministic batch revision in
response headers.
Nuxt owns only the public launch gate, closed endpoint bodies, attestation, and
the guarded proxy. It does not merge URL lists or serialize open sitemap XML.
Nuxt forwards an open sitemap response only after validating all required policy
headers; otherwise it returns HTTP 503 `no-store`.
## 5. Policy Matrix

The matrix is normative:
| Surface | Closed | Selective-open simulation |
| --- | --- | --- |
| HTML meta robots | `noindex,follow` on every public page | `index,follow` only for an allowlisted canonical public route or a backend-indexable detail; otherwise `noindex,follow` |
| `X-Robots-Tag` | `noindex, follow` on public HTML | Mirrors the page decision; omission is not permission |
| Robots public crawl | Allow public routes | Allow public routes |
| Robots sensitive crawl | Block every `crawl-blocked-sensitive` route consistently in every applicable user-agent group | Block the same sensitive route set |
| Robots sitemap line | Absent | Present only when both keys and backend policy attestation are valid |
| Sitemap XML | Valid empty XML, HTTP 200, `no-store` | Shared-manifest canonical routes plus backend-indexable canonical detail URLs |
| Public links | Followable for usable public pages | Rich and thin public pages may remain linked |
| Private links | Not promoted through public nav or sitemap | Same restriction |
| Canonical core/listing/static page | `noindex,follow`, absent from sitemap | `index,follow` only when allowed by the shared route manifest; present in sitemap under the same rule |
| Thin public entity | `noindex,follow`, absent from sitemap | `noindex,follow`, absent from sitemap |
| Rich public entity | `noindex,follow`, absent from sitemap | `index,follow`, present in sitemap |
Additional rules:
- closed never advertises a sitemap and never reads backend sitemap data;
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
proxied only after valid request-wide policy attestation. A proxy, attestation,
completeness, or revision failure on any endpoint returns HTTP 503 `no-store`;
an endpoint never falls back to a stale or partially open document.
## 6. Backend Indexability Contract

The shared module returns:
```text
IndexPolicyDecision
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
Its fixed image rules are:
- non-empty current `entity.images` means AI imagery;
- AI imagery contributes zero to `real_image_count`;
- AI imagery cannot satisfy `has_real_image`;
- dimensions, file existence, and visual attractiveness do not alter class;
- malformed image metadata never becomes a real-image signal;
- an entity cannot become rich merely because AI images are present;
- copy must not call current AI imagery real, documentary, or on-site;
- sitemap and entity detail receive identical decisions for identical input.
The public entity response includes at least `indexable`,
`policy_fingerprint`, and `policy_revision`. The sitemap builder calls the same
module directly or through its owned batch wrapper, never a duplicate checklist.
## 7. AI Disclosure Surfaces

### 7.1 Canonical Copy

Actual AI entity image:
> Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.
Generated graphic placeholder for an entity without its own image:
> Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.
These strings are centralized product copy. Short variants may not remove the
distinction between actual AI imagery and a generic placeholder.
### 7.2 Hero, Gallery, and Lightbox

- Actual AI hero: visible pill with the short label `Minh họa AI`.
- Placeholder hero: visible pill/caption with exact placeholder copy only.
- The AI pill is associated through accessible description with the full
  canonical AI sentence; disclosure is never hover-only or icon-only.
- Pill remains readable at mobile/desktop widths and exposed as text to AT.
- Each AI gallery item carries the exact disclosure in caption data.
- The selected gallery caption and lightbox show the full copy.
- Slide changes preserve accessible caption association.
- Reopening the lightbox does not lose disclosure.
- Placeholder tiles are not counted or described as entity photography.
### 7.3 Share, OG, and Twitter

- A share card using an AI image includes the AI disclosure in visible text.
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
  -> LaunchSafetyDecision(closed)
  -> closed meta + header + robots
  -> valid empty sitemap, no-store
  -> no backend launch-policy dependency
```
Selective-open preflight for every surface:
```text
request -> both runtime keys exact -> fetch backend policy attestation
  -> fingerprint + route-manifest revision + backend-policy revision match
  -> yes: one request-wide selective-open decision
  -> no/error/incomplete: one request-wide closed decision
```
Selective-open non-entity page simulation:
```text
attested request -> classify path through shared route manifest
  -> indexable-public canonical route: index,follow
  -> noindex-follow-public or crawl-blocked-sensitive: noindex
```
Selective-open entity simulation:
```text
attested request -> fetch public entity policy
  -> verify indexable + fingerprint + revision
  -> valid true: index,follow
  -> false/missing/mismatch: noindex,follow
  -> cache under mode + fingerprint + revision
```
Selective-open sitemap simulation:
```text
sitemap -> both keys exact -> validate backend policy attestation
  -> guarded proxy to backend sitemap owner
  -> backend loads shared manifest + evaluates detail batch
  -> backend merges, deduplicates, serializes, and returns policy headers
  -> Nuxt validates fingerprint + manifest revision + batch revision
  -> forward intact response under fenced cache identity or return 503 no-store
```
Disclosure classification:
```text
renderable entity image -> actual AI -> AI pill/caption disclosure
no renderable image     -> placeholder -> exact placeholder copy only
malformed image data    -> omit from media; never real; never quality credit
```
## 9. Failure Behavior

- config unreadable, missing, partial, stale, or invalid: closed;
- backend policy attestation missing, unavailable, incomplete, or mismatched:
  request-wide closed behavior on every surface;
- backend unavailable in closed: closed behavior remains fully usable;
- open sitemap backend error: HTTP 503 and `Cache-Control: no-store`;
- closed `/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml` each
  return their specified empty XML shape with zero backend calls;
- open `robots.txt` backend error: closed robots response, no sitemap line;
- entity detail missing `indexable`: `noindex,follow`;
- positive `indexable` with fingerprint mismatch: `noindex,follow`;
- entity detail missing required revision: `noindex,follow`;
- partial open sitemap policy response: 503 `no-store`, not partial success;
- invalid/non-canonical URL: omit and report; return 503 if response
  completeness cannot be proven;
- page or robots cache-fence failure: bypass cache and produce closed behavior;
- sitemap cache-fence or batch-revision failure: HTTP 503 `no-store`;
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
Closed tests assert meta, header, robots, and empty sitemap without a successful
backend mock. Open simulations cover rich, thin, missing-field, mismatch, and
backend-error behavior.
Attestation tests prove that static pages, entity pages, robots, and all sitemap
endpoints share one request-wide decision and cannot open independently.
Backend tests compare single and batch decisions for rich candidates, thin,
provisional, explicitly unverified, missing, AI-image, no-image, and malformed
image fixtures. Adding AI images must not change any real-image criterion.
Integration tests assert:
- meta and `X-Robots-Tag` agreement;
- closed robots allows both public route groups, blocks every sensitive-route
  category in every applicable bot group, and has no sitemap line;
- all three closed sitemap endpoints return their specified valid empty XML,
  HTTP 200, `no-store`, and make no backend call;
- open sitemap error is 503 `no-store`;
- open robots error falls back closed;
- entity detail without valid positive policy remains `noindex`;
- cache keys use the base policy identity plus the defined static, entity,
  robots, or sitemap-batch suffix;
Disclosure tests verify the short AI pill plus its full accessible description,
and exact full copy in gallery, lightbox, share-card data, OG/Twitter alt,
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
1. backend `index_policy` model and unit tests;
2. shared entity-response consumption plus backend-owned open sitemap assembly;
3. Nuxt two-key gate, shared public-route manifest, and fingerprint;
4. closed meta/header/robots/sitemap behavior;
5. selective-open simulation and failures;
6. cache fencing;
7. visible AI and placeholder disclosure;
8. share, OG/Twitter, JSON-LD, and image-sitemap disclosure;
9. integration evidence and operational documentation.
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
- advertise a sitemap while closed;
- describe current AI imagery as real, documentary, or on-site photography.
## 13. Acceptance Criteria

Implementation is accepted only when:
- default, missing, partial, invalid, and mismatched config is closed;
- only two exact valid runtime keys plus a matching build/backend fingerprint
  produce selective-open in tests;
- missing or mismatched backend attestation keeps every indexing surface closed;
- deployed config remains unchanged and globally closed;
- closed public HTML emits `noindex,follow` in meta and header;
- closed robots allows `indexable-public` and `noindex-follow-public`, blocks
  every `crawl-blocked-sensitive` route consistently, and has no sitemap line;
- `/sitemap.xml`, `/sitemap-media.xml`, and `/sitemap-index.xml` each return the
  specified empty XML, HTTP 200, `no-store`, and remain backend-independent;
- backend `index_policy` is the only indexability authority;
- entity response and sitemap share decision, fingerprint, and revision;
- non-entity page meta and static sitemap entries share the same route manifest;
- all current `entity.images` are classified as AI;
- AI imagery contributes nothing to real-image criteria;
- allowlisted canonical public routes and rich public entities open and enter
  the simulated open sitemap under their respective shared contracts;
- thin/private/invalid/missing/mismatch cases stay excluded or `noindex`;
- open sitemap backend error is 503 `no-store`;
- open robots error returns closed robots;
- open entity detail without valid positive policy is `noindex`;
- cache uses the closed sentinel or the attested open base identity plus the
  exact static, entity-revision, robots, or deterministic sitemap-batch suffix;
- the short AI pill and full accessible description appear on every actual AI
  hero; exact full disclosure appears on gallery/lightbox/share/metadata surfaces;
- exact placeholder copy appears only on placeholder surfaces;
- placeholders are excluded from image sitemap and entity `ImageObject`;
- no current AI image is called real or documentary;
- new behavior shows RED then GREEN evidence;
- backend and serial frontend regression suites pass;
- spec review precedes quality review for each task;
- no Important finding remains open;
- H1 and H2 remain explicit unresolved launch blockers.
## 14. Rollout, Rollback, and Legal/Owner Gates

Stage 0 is this workstream: implement and test while all real environments stay
closed. Stage 1 gathers truth-table, policy, disclosure, cache-fence, and full
regression evidence. Stage 2 requires externally recorded H1 legal-entity/NĐ147
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
Rollback removes or invalidates either key. New requests immediately use
closed behavior without backend access, and cache fencing prevents open
artifacts from matching the closed namespace.
Post-rollback verification checks representative rich/thin pages, meta/header
`noindex,follow`, robots without sitemap advertisement, retained sensitive-route
blocking, valid empty output from all three sitemap endpoints with HTTP 200
`no-store`, and zero open-policy cache hits in the closed namespace.
Engineering owns closed-state correctness, simulation evidence, fingerprint
agreement, and rollback mechanics. The responsible organization/legal process
owns H1; qualified ICT/data counsel owns H2; the project owner owns operational
authorization. No engineer, reviewer, test, env value, or commit may infer any
external approval from technical readiness.
