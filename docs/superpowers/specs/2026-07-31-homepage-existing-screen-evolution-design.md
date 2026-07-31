# Homepage Existing Screen Evolution B1 Design

> STATUS: awaiting-written-spec-review
> Approved in conversation on 2026-07-31: Controlled Composition Upgrade.

## 1. Goal

Evolve the existing `/` homepage into the first Adaptive Nocturne public pilot
without replacing its Stitch-derived composition, changing its data contracts,
or importing context/trust behavior reserved for Plan C.

The pilot keeps approximately 70% of the current screen composition, normalizes
approximately 20% through the Nocturne Heritage foundation, and adds no more
than 10% new presentational context. The result must feel like a curated local
field dossier rather than a generic tourism card grid or a command center.

## 2. Authority and Scope

The authority chain for B1 is:

1. `docs/superpowers/specs/2026-07-31-nocturne-heritage-adaptive-public-design.md`;
2. `design-system/vinhlong360/MASTER.md`;
3. the existing production `web-nuxt/pages/index.vue` composition and data flow;
4. Plan A foundation components and semantic tokens.

`design-system/vinhlong360/pages/home.md` is a dirty parallel-session artifact
and must not be edited or staged in B1. Its Hybrid Editorial P1.2 anatomy and
copy may be consulted as reference, but it does not replace Existing Stitch
Screen Evolution as the source of layout authority.

### In scope

- The public homepage `/` only.
- Existing hero, decision layer, categories, events/seasonal, editorial feature,
  spotlight/food, story spread, community, and personalization regions.
- Homepage-specific presentation components and CSS.
- A pure presentation adapter for stable, testable section models.
- Behavior-level regression tests and desktop/mobile visual QA.

### Out of scope

- Discovery and entity-detail pilots, which become B2 and B3.
- New API endpoints, backend ranking, auth, RBAC, SEO policy, or shell changes.
- New GPS/IP access, location inference, source verification, `WhyThis`, or
  official-notice logic reserved for Plan C.
- AdminCP, partner, moderation, booking, ordering, payment, or production deploy.
- Editing or reconciling `design-system/vinhlong360/pages/home.md`.

## 3. Chosen Direction

B1 uses **Controlled Composition Upgrade**.

- Keep the current section order and content sources.
- Replace only the most generic or mechanically repeated presentation anatomy.
- Use the Plan A semantic tokens, Nocturne/Daylight Parchment behavior,
  Controlled Serif rules, `FramedDossier`, and `DossierLineItem`.
- Preserve all current routes and direct-contact action boundaries.
- Avoid a full Hybrid P1.2 reconstruction and avoid a cosmetic token-only pass.

The homepage signature is the **Local Dossier Line**: hero feature, quick
decisions, and spotlight use related hairline, metadata, and action anatomy.
This creates continuity without making every section the same card.

## 4. Composition

The visual skeleton remains stable in this order:

```text
Public shell
  -> Hero thesis + search + feature dossier
  -> Quick decision ledger
  -> Client-only journey continuation when real signal exists
  -> Error/skeleton recovery region
  -> Category index
  -> Events and seasonal collection
  -> One primary editorial feature
  -> Spotlight and food split dossier
  -> Story spread as an editorial pause
  -> Community
  -> Client-only personalization when real signal exists
  -> Footer
```

Personalization may replace item content or ranking inside an existing module;
it must not reorder modules, change navigation, or move the user's scroll
position after hydration.

### 4.1 Hero

Keep the existing two-zone hero:

- Left: kicker, one editorial headline, short supporting copy, primary search,
  and at most one nearby/context action.
- Right: one `HomeFeatureDossier` using an existing entity and image disclosure.
- Search remains the only dominant action in the first viewport.
- The feature action is secondary and may link to detail or add to itinerary.
- The existing hero assets and preload contract remain unchanged unless a test
  proves a concrete CLS or disclosure defect.

Remove the default Ken Burns animation. A single bounded entry transition may
reveal the hero composition; reduced motion renders the final state immediately.

### 4.2 Quick decision ledger

Replace the visually mechanical numbered decision list with
`HomeDecisionLedger`:

- render two to four entries derived from existing event, seasonal, food,
  planner, or map models;
- do not imply an ordered procedure, ranking score, or AI certainty;
- show a concise eyebrow, title, supporting value, and one route action;
- omit unavailable entries instead of padding the module;
- de-duplicate entities already used by the hero or immediately following
  collection.

### 4.3 Category index

Keep every current destination and route, but stop giving all category links the
same visual weight.

- Primary discovery group: destinations, food/local products, culture/heritage.
- Utility group: events, map, itineraries, community, or other existing routes.
- The grouping is presentational only and does not change route semantics.
- Mobile uses a touch-first stacked index; it does not shrink the desktop grid.

### 4.4 Events and seasonal content

- Upcoming events remain a scan-efficient temporal list with real dates.
- Seasonal entities remain the only horizontal collection in this middle zone.
- Expired or unavailable records are omitted according to existing data rules.
- Do not add `HOT`, ratings, countdown urgency, or status labels without current
  data support.

### 4.5 Editorial feature and story spread

`EntityFeature` remains the main media-led signature block. `StorySpread`
remains a separate editorial pause later in the page. They must not compete in
the same viewport with equal visual weight.

- Fraunces is allowed for the feature title or pull quote.
- Interface labels, metadata, and actions use Be Vietnam Pro.
- Existing generated-media disclosure remains visible and authoritative.
- No brand gradient, glass layer, WebGL, parallax, or ambient animation is added.

### 4.6 Spotlight and food

Recompose the current spotlight and food area as a quiet split dossier:

- one spotlight story with media, disclosure, summary, and detail action;
- one dense food/service list using real rating/review data only when present;
- no duplicated hero anatomy and no generic equal-width card grid;
- one primary action per side, with additional navigation visually secondary.

### 4.7 Community and personalization

- Community remains below the editorial regions and always retains its community
  source identity.
- Community API failure or empty data does not hide or blank other homepage
  regions.
- Social metrics render only when returned by the API.
- `Dành cho bạn` renders only when the existing real-signal condition passes.
- Client-only regions remain isolated so SSR and client hydration do not swap
  section nodes.

## 5. Component Boundaries

Create only narrowly scoped homepage components:

### `HomeFeatureDossier.vue`

Consumes an existing entity presentation model and delegates shared anatomy to
`FramedDossier`. It owns homepage hero density, disclosure placement, and the
two permitted secondary actions. It does not fetch data.

### `HomeDecisionLedger.vue`

Consumes `readonly HomeDecisionEntry[]` and renders a semantic list of route
actions. It does not rank, fetch, infer user intent, or display numeric scores.

### `HomeCategoryIndex.vue`

Consumes primary and utility link groups. It owns only responsive grouping and
navigation presentation; route definitions remain in the page presentation
adapter.

Retain `EntityFeature`, `StorySpread`, `EntityCard`, `JourneyActionRail`,
`ImageDisclosure`, `EmptyState`, and `SearchAutocomplete`. Do not create a
homepage mega-component.

## 6. Presentation Adapter

Add a pure homepage presentation adapter with no network or browser side
effects. The implementation plan must choose one focused composable/module and
define these public types exactly:

```ts
type HomeDecisionTone = 'event' | 'season' | 'planner' | 'food' | 'map'

type HomeDecisionEntry = {
  id: string
  eyebrow: string
  title: string
  text: string
  to: string
  tone: HomeDecisionTone
}

type HomeCategoryLink = {
  key: string
  label: string
  hint: string
  to: string
  icon: string
  accent: string
  countLabel?: string
}

type HomeCategoryGroups = {
  primary: readonly HomeCategoryLink[]
  utility: readonly HomeCategoryLink[]
}
```

The adapter consumes existing normalized homepage entities and current month.
It produces stable decision entries and category groups. It must:

- preserve deterministic ordering;
- omit unavailable candidates instead of inventing filler;
- de-duplicate hero, decision, spotlight, and immediately following collection
  entities;
- never add source, verification, rating, OCOP, travel-time, or urgency claims;
- return the same module skeleton for guest and returning-user SSR.

Journey/personalization models stay in their existing client-only composables
and do not enter this adapter.

## 7. Visual System

### Nocturne

- Use `--color-canvas`, `--color-surface`, `--color-surface-raised`,
  `--color-text`, `--color-text-muted`, `--color-border`, `--color-action`, and
  component tokens from Plan A.
- Use near-black Mekong canvas, restrained raised surfaces, and hairline
  boundaries. No glow or glass treatment.

### Daylight Parchment

- Use the same DOM, spacing, hierarchy, and component states.
- Only semantic token values change.
- Parchment is an accessibility/readability variant, not a second homepage.

### Typography

- Fraunces: hero headline, primary feature title, and intentional story moment.
- Be Vietnam Pro: navigation, section labels, body, metadata, list titles, and
  actions.
- Utility headings must not become serif merely to appear editorial.

### CSS isolation

Add a page-only `web-nuxt/assets/css/home-nocturne.css` compatibility layer and
load it from `pages/index.vue` after the existing homepage style block. Scope all
rules under an explicit homepage pilot root attribute/class. Do not register the
file globally and do not run a broad CSS migration.

## 8. Data and State Flow

```text
existing /api/homepage payload
  -> existing normalized computed data
  -> pure homepage presentation adapter
  -> stable SSR homepage skeleton
  -> isolated client-only journey/community/personalization regions
  -> explicit route/contact action
```

- No new endpoint or request is introduced.
- Community remains an independent lazy request.
- No raw GPS/IP, private history, internal score, or hidden reasoning reaches
  the adapter or DOM.
- Manual/user state continues to use existing composables and storage contracts.
- B1 does not render `OfficialNotice`, `SourceMark`, `FreshnessLine`, or
  `WhyThisControl` until Plan C supplies verified contracts.

## 9. Required States and Recovery

### Homepage API failure

- Keep category navigation usable.
- Show the existing compact retry state.
- Do not blank the shell, hero search, or footer.

### Partial data

- Omit only the unavailable entry/module.
- Keep section order stable.
- Never fill a target count with invented content.

### Community failure or empty data

- Render the existing directed empty state or hide only the volatile feed.
- Keep the community route action available.

### No personalization signal

- Do not render `Dành cho bạn`.
- Do not relabel default/editorial ranking as personalized.

### Image failure

- Preserve media aspect ratio and layout geometry.
- Use the existing placeholder classification and disclosure policy.
- Do not substitute an unrelated remote image.

### Hydration

- SSR and client retain identical non-client-only section order.
- Client-only insertions must not reorder adjacent server-rendered sections.
- Theme changes must not alter layout or navigation destinations.

## 10. Interaction and Accessibility

- Search input and all actions have at least 44px hit targets.
- Body and input text remain at least 16px.
- Visible focus uses outline plus offset, not color alone.
- Hover does not lift every tile/card.
- Reduced motion disables the hero entry transition and all non-essential motion.
- Forced colors retains borders, labels, image disclosures, and action identity.
- At 200% text zoom, labels wrap without clipping and no action becomes hidden.
- Mobile uses stacked/touch-first compositions with safe-area support.

## 11. Performance

- Preserve existing hero image preload and explicit responsive source contract.
- Removing Ken Burns must not add a replacement animation or JavaScript loop.
- All below-fold media stays lazy-loaded with stable dimensions/aspect ratio.
- The presentation adapter is synchronous and pure.
- Community or recommendation latency must not delay first meaningful homepage
  content.
- No runtime font, icon, shader, or visual-effect dependency is added.

## 12. Testing and QA

Behavior tests must mount the affected components/page with fixtures and verify
what users see. Source-string assertions alone are insufficient for new B1
behavior.

Minimum automated proof:

- hero dossier renders only supplied entity/media/action anatomy;
- decision ledger omits filler, contains no fake numeric rank, and preserves
  deterministic order;
- hero/decision/next collection de-duplication works;
- category grouping preserves every current route exactly once;
- homepage API partial failure keeps navigation and unaffected modules;
- community failure remains isolated;
- no-signal state omits `Dành cho bạn`;
- Nocturne and Parchment preserve section order;
- generated/user-uploaded image disclosure tests remain green;
- existing journey-action, smoke, theme, Framed Dossier, and image-policy suites
  remain green.

Visual QA matrix:

- 375px, 390px, 768px, 1024px, and 1440px;
- Nocturne and Daylight Parchment;
- keyboard focus and tab order;
- reduced motion and forced colors;
- 200% text zoom and mobile landscape;
- loading, partial, empty, and image-fallback fixtures;
- screenshot baselines for desktop/mobile in both themes.

## 13. Rollout and Rollback

Implementation tasks must be independently revertible:

1. presentation adapter and behavior tests;
2. hero and decision top-zone;
3. category and temporal middle-zone;
4. spotlight/community/personalization composition;
5. final visual QA and documentation closure.

The pilot uses a homepage-scoped root attribute/class so the new CSS layer can
be removed without changing shared components or shell behavior. Do not stage
parallel-session files or unrelated dirty artifacts.

## 14. Anti-Template Gate

B1 fails review if it introduces any of these patterns without a task-specific
reason:

- hero followed by stats, three equal cards, and a generic final CTA;
- bento grids or equal card anatomy across unrelated content families;
- pill clouds, glass content, ambient glow, or brand gradients over every image;
- Fraunces on every heading or every card title;
- hover lift on every interactive surface;
- multiple consecutive horizontal carousels;
- generic copy such as `khám phá điều tuyệt vời` or unsupported `miền Tây` filler;
- fake rating, urgency, verification, OCOP, popularity, or travel-time claims;
- navigation or section reordering after hydration.

## 15. Completion Criteria

B1 is complete only when:

- the production homepage visibly uses the Plan A Nocturne foundation;
- Existing Stitch composition and current data routes remain recognizable;
- the top-zone reads as one hero thesis plus a local decision dossier;
- middle and bottom sections have distinct task-appropriate density;
- all required failure/empty/client-only states remain usable;
- behavior tests, typecheck, production build, and visual QA matrix pass;
- no new API, location, trust, auth, RBAC, SEO, shell, AdminCP, or private-state
  behavior is introduced;
- `design-system/vinhlong360/pages/home.md` remains byte-identical throughout
  implementation.
