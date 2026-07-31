# Homepage Existing Screen Evolution B1 Implementation Plan

> **STATUS: DONE — 2026-07-31.**
>
> Implementation and production-preview verification completed at `d5dd453a`; production deployment remains out of scope.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the existing `/` homepage into the first Adaptive Nocturne public pilot while preserving its Stitch-derived composition, current routes, API contracts, client-only state boundaries, and direct-contact model.

**Architecture:** Keep `pages/index.vue` as the data orchestration boundary and move only deterministic presentation decisions into one synchronous pure adapter. Add three narrow homepage components for the hero dossier, decision ledger, and grouped category index, then apply a homepage-scoped compatibility stylesheet under `data-home-pilot="nocturne-b1"`; existing `EntityFeature`, `StorySpread`, community, journey, image disclosure, and personalization flows remain in place.

**Tech Stack:** Nuxt 4, Vue 3, TypeScript, CSS custom properties, `@nuxt/test-utils`, `@vue/test-utils`, Vitest, Nuxt production build, browser-based responsive visual QA.

## Global Constraints

- Scope is the public homepage `/` only; B2 discovery, B3 entity detail, Plan C context/trust behavior, AdminCP, partner, moderation, auth, RBAC, SEO, shell, booking, ordering, payment, and deployment are out of scope.
- Use **Controlled Composition Upgrade**: retain approximately 70% Existing Stitch Screen composition, normalize approximately 20% through Plan A, and add no more than 10% presentational context.
- Preserve the current `/api/homepage` request, community lazy requests, route destinations, image descriptor policy, hero asset/preload contract, client-only journey rail, and real-signal-only `Dành cho bạn` behavior.
- Nocturne is default; Daylight Parchment uses the same DOM, section order, spacing, actions, and semantic meaning.
- Use Plan A semantic/component tokens only in new CSS; do not add raw color, radius, shadow, font, gradient, glow, glass, WebGL, parallax, or runtime visual dependencies.
- Fraunces is limited to the hero headline, primary editorial feature, and intentional story moments; interface labels, metadata, lists, and actions use Be Vietnam Pro through semantic font tokens.
- Search remains the only dominant first-viewport action; the hero dossier may expose only detail and optional itinerary actions as secondary actions.
- Decision entries are deterministic and data-backed; do not render fake numbering, scores, ranking, urgency, verification, rating, OCOP, travel-time, source, or location claims.
- Keep category destinations exactly once: `/du-lich`, `/kham-pha/am-thuc`, `/ocop`, `/le-hoi`, `/luu-tru`, `/lich-trinh`, and `/ban-do`.
- Community failures remain isolated; social metrics render only when returned; no personalization module renders without existing favorites/recent-history signal.
- All interactive targets are at least `var(--touch-min)` high, keyboard focus is visible with outline plus offset, reduced motion reaches the final state immediately, forced colors retains boundaries and action identity, and 200% text zoom does not clip labels or actions.
- Behavior-level proof must mount affected components and the page; source-string smoke assertions are supporting checks only.
- Do not edit or stage `design-system/vinhlong360/pages/home.md`, `.superpowers/`, `agent/knowledge.db-*`, `design-system/vinhlong360/concepts/`, `docs/page-inventory-design-scope-2026-07-27.md`, or NP-0 plan/spec artifacts.
- `design-system/vinhlong360/pages/home.md` must remain byte-identical with Git object hash `b694ac09ede89442c8af48e193534f0fd25ee3a4` before and after every task.
- Each task uses a fresh implementer, then an independent spec-compliance review and an independent code-quality review. If the review provider returns `404 No active credentials`, record the exact failure and do not describe the fallback self-review as independent.
- Each task records RED and GREEN command output, ends with focused regression checks, stages only its declared files, and creates one independently revertible commit.

## File Structure

- Create `web-nuxt/utils/homeNocturnePresentation.ts`: pure types, stable decision selection, category grouping, and downstream de-duplication; no Vue, browser, storage, network, or clock access.
- Create `web-nuxt/components/home/HomeFeatureDossier.vue`: hero feature media/disclosure plus shared `FramedDossier` body anatomy; no data fetching.
- Create `web-nuxt/components/home/HomeDecisionLedger.vue`: semantic unnumbered route list; no ranking or inference.
- Create `web-nuxt/components/home/HomeCategoryIndex.vue`: primary/utility category grouping; no route ownership outside supplied models.
- Create `web-nuxt/assets/css/home-nocturne.css`: B1-only composition layer scoped under `[data-home-pilot="nocturne-b1"]`.
- Create `web-nuxt/tests/home-nocturne-presentation.test.ts`: pure adapter ordering, omission, route, count, and de-duplication tests.
- Create `web-nuxt/tests/home-nocturne-components.test.ts`: mounted behavior tests for the three new presentation components.
- Create `web-nuxt/tests/home-nocturne-page.test.ts`: mounted homepage success, partial failure, community isolation, personalization, theme-order, and downstream de-duplication tests.
- Modify `web-nuxt/pages/index.vue`: consume the adapter/components, add the pilot root and section markers, retain existing orchestration, and remove obsolete top-zone markup/computeds/selectors.
- Modify `web-nuxt/tests/smoke.test.ts`: remove assertions tied to the numbered decision implementation and keep only non-behavior structural safety checks.
- Modify `web-nuxt/tests/ugc-image-classification.test.ts`: keep the existing homepage UGC behavior fixture compatible with the new child component boundary without weakening image-policy assertions.
- Create `docs/superpowers/qa/2026-07-31-homepage-b1/report.md`: record the completed browser matrix and four canonical screenshot baseline filenames.

---

### Task 1: Build the Pure Homepage Presentation Adapter

**Files:**
- Create: `web-nuxt/utils/homeNocturnePresentation.ts`
- Create: `web-nuxt/tests/home-nocturne-presentation.test.ts`

**Interfaces:**
- Consumes: normalized homepage entity arrays, `currentMonth`, selected hero/spotlight IDs, and real category counts.
- Produces: `createHomeNocturnePresentation(input: HomeNocturnePresentationInput): HomeNocturnePresentation` plus the exact approved public types `HomeDecisionTone`, `HomeDecisionEntry`, `HomeCategoryLink`, and `HomeCategoryGroups`.

- [x] **Step 1: Verify the parallel-session hash guard and capture the focused baseline**

Run from repository root:

```powershell
$homeBriefHash = (git hash-object -- 'design-system/vinhlong360/pages/home.md').Trim()
if ($homeBriefHash -ne 'b694ac09ede89442c8af48e193534f0fd25ee3a4') { throw "home.md changed before Task 1: $homeBriefHash" }
Set-Location web-nuxt
npm test -- tests/journeyActions.test.ts tests/framed-dossier.test.ts tests/theme-mode-control.test.ts
```

Expected: all selected suites PASS and the guard prints no error.

- [x] **Step 2: Write failing adapter behavior tests**

Create `web-nuxt/tests/home-nocturne-presentation.test.ts` with deterministic fixtures. The test must prove order, omission, category route uniqueness, count labels, and cross-region de-duplication:

```ts
import { afterEach, describe, expect, it } from 'vitest'
import { createHomeNocturnePresentation } from '../utils/homeNocturnePresentation'

const event = (id: string, name: string, daysUntil: number) => ({
  id,
  name,
  days_until: daysUntil,
  attributes: { date_start: '2026-08-02' },
})

describe('homepage Nocturne presentation adapter', () => {
  it('builds deterministic data-backed decisions and omits unavailable filler', () => {
    const result = createHomeNocturnePresentation({
      currentMonth: 8,
      heroId: 'hero-1',
      spotlightId: 'spot-1',
      upcomingEvents: [event('event-1', 'Lễ hội sông nước', 2)],
      seasonal: [{ id: 'season-1', name: 'Chôm chôm Bình Hòa Phước' }],
      topDishes: [],
      itineraries: [],
      categoryCounts: { experiences: 4, dishes: 0, products: 3, events: 1, areas: 3 },
    })

    expect(result.decisionEntries.map(entry => entry.tone)).toEqual(['event', 'season'])
    expect(result.decisionEntries.map(entry => entry.title)).toEqual([
      'Có lịch gần nhất',
      'Đang vào mùa',
    ])
    expect(result.decisionEntries.every(entry => entry.id && entry.to && entry.text)).toBe(true)
    expect(result.decisionEntries.some(entry => entry.tone === 'map')).toBe(false)
  })

  it('de-duplicates hero, spotlight, decisions, and immediately following lists', () => {
    const result = createHomeNocturnePresentation({
      currentMonth: 8,
      heroId: 'shared-hero',
      spotlightId: 'shared-spotlight',
      upcomingEvents: [
        event('shared-hero', 'Không lặp hero', 0),
        event('event-1', 'Sự kiện quyết định', 1),
        event('event-2', 'Sự kiện còn lại', 4),
      ],
      seasonal: [
        { id: 'shared-spotlight', name: 'Không lặp spotlight' },
        { id: 'season-1', name: 'Mùa quyết định' },
        { id: 'season-2', name: 'Mùa còn lại' },
      ],
      topDishes: [
        { id: 'dish-1', name: 'Món quyết định', attributes: { rating: 4.8 } },
        { id: 'dish-2', name: 'Món còn lại', attributes: { rating: 4.6 } },
      ],
      itineraries: [{ id: 'plan-1', title: 'Một ngày ven sông' }],
      categoryCounts: {},
    })

    expect(result.decisionEntries.map(entry => entry.tone)).toEqual(['event', 'season', 'food', 'planner'])
    expect(result.upcomingEventEntries.map(item => item.id)).toEqual(['event-2'])
    expect(result.seasonalEntries.map(item => item.id)).toEqual(['season-2'])
    expect(result.dishEntries.map(item => item.id)).toEqual(['dish-2'])
  })

  it('preserves every current category route exactly once in primary and utility groups', () => {
    const result = createHomeNocturnePresentation({
      currentMonth: 8,
      upcomingEvents: [],
      seasonal: [],
      topDishes: [],
      itineraries: [],
      categoryCounts: { experiences: 5, dishes: 2, products: 4, events: 1, areas: 3 },
    })
    const links = [...result.categoryGroups.primary, ...result.categoryGroups.utility]

    expect(links.map(link => link.to)).toEqual([
      '/du-lich',
      '/kham-pha/am-thuc',
      '/ocop',
      '/le-hoi',
      '/luu-tru',
      '/lich-trinh',
      '/ban-do',
    ])
    expect(new Set(links.map(link => link.to)).size).toBe(links.length)
    expect(links.find(link => link.key === 'du-lich')?.countLabel).toBe('5 gợi ý')
    expect(links.find(link => link.key === 'luu-tru')?.countLabel).toBeUndefined()
  })
})
```

- [x] **Step 3: Run the adapter test and verify RED**

```powershell
npm test -- tests/home-nocturne-presentation.test.ts
```

Expected: FAIL because `../utils/homeNocturnePresentation` does not exist.

- [x] **Step 4: Implement the exact pure adapter contract**

Create `web-nuxt/utils/homeNocturnePresentation.ts`. Keep the approved public types exact, use `entityPath()` for entity detail routes, and use the following stable model/selection structure:

```ts
import { entityPath } from '~/utils/routePaths'

export type HomeDecisionTone = 'event' | 'season' | 'planner' | 'food' | 'map'

export type HomeDecisionEntry = {
  id: string
  eyebrow: string
  title: string
  text: string
  to: string
  tone: HomeDecisionTone
}

export type HomeCategoryLink = {
  key: string
  label: string
  hint: string
  to: string
  icon: string
  accent: string
  countLabel?: string
}

export type HomeCategoryGroups = {
  primary: readonly HomeCategoryLink[]
  utility: readonly HomeCategoryLink[]
}

export type HomePresentationEntity = {
  id: string | number
  name?: string | null
  title?: string | null
  days_until?: number | null
  attributes?: {
    rating?: number | string | null
    review_count?: number | null
    date_start?: string | null
    [key: string]: unknown
  }
  [key: string]: unknown
}

type HomeCategoryCountKey = 'experiences' | 'dishes' | 'products' | 'events' | 'areas'

export type HomeNocturnePresentationInput = {
  currentMonth: number
  heroId?: string | number | null
  spotlightId?: string | number | null
  upcomingEvents: readonly HomePresentationEntity[]
  seasonal: readonly HomePresentationEntity[]
  topDishes: readonly HomePresentationEntity[]
  itineraries: readonly HomePresentationEntity[]
  categoryCounts: Partial<Record<HomeCategoryCountKey, number>>
}

export type HomeNocturnePresentation = {
  decisionEntries: readonly HomeDecisionEntry[]
  categoryGroups: HomeCategoryGroups
  upcomingEventEntries: readonly HomePresentationEntity[]
  seasonalEntries: readonly HomePresentationEntity[]
  dishEntries: readonly HomePresentationEntity[]
}

type CategoryDefinition = Omit<HomeCategoryLink, 'countLabel'> & {
  group: 'primary' | 'utility'
  countKey?: HomeCategoryCountKey
}

const CATEGORY_DEFINITIONS: readonly CategoryDefinition[] = [
  { group: 'primary', icon: 'leaf', label: 'Du lịch', hint: 'Vườn, sông, làng nghề', to: '/du-lich', accent: 'leaf', countKey: 'experiences', key: 'du-lich' },
  { group: 'primary', icon: 'bowl', label: 'Ẩm thực', hint: 'Quán ngon, món bản địa', to: '/kham-pha/am-thuc', accent: 'amber', countKey: 'dishes', key: 'am-thuc' },
  { group: 'primary', icon: 'gift', label: 'OCOP', hint: 'Đặc sản làm quà', to: '/ocop', accent: 'clay', countKey: 'products', key: 'ocop' },
  { group: 'primary', icon: 'lantern', label: 'Lễ hội', hint: 'Lịch và văn hóa địa phương', to: '/le-hoi', accent: 'river', countKey: 'events', key: 'le-hoi' },
  { group: 'utility', icon: 'home', label: 'Lưu trú', hint: 'Nghỉ lại theo khu vực', to: '/luu-tru', accent: 'leaf', key: 'luu-tru' },
  { group: 'utility', icon: 'compass', label: 'Lịch trình', hint: 'Gợi ý sẵn 1–3 ngày', to: '/lich-trinh', accent: 'amber', key: 'lich-trinh' },
  { group: 'utility', icon: 'map', label: 'Bản đồ', hint: 'Lọc theo vùng', to: '/ban-do', accent: 'river', countKey: 'areas', key: 'ban-do' },
]

function entityId(entity: HomePresentationEntity | null | undefined): string {
  return String(entity?.id ?? '').trim()
}

function entityLabel(entity: HomePresentationEntity | null | undefined): string {
  return String(entity?.name || entity?.title || '').trim()
}

function firstAvailable(
  entities: readonly HomePresentationEntity[],
  consumed: ReadonlySet<string>,
): HomePresentationEntity | undefined {
  return entities.find(entity => entityId(entity) && entityLabel(entity) && !consumed.has(entityId(entity)))
}

function eventEyebrow(entity: HomePresentationEntity): string {
  if (entity.days_until === 0) return 'Hôm nay'
  if (entity.days_until === 1) return 'Ngày mai'
  if (typeof entity.days_until === 'number') return `Còn ${entity.days_until} ngày`
  return 'Sắp diễn ra'
}

function foodEyebrow(entity: HomePresentationEntity): string {
  const rating = Number(entity.attributes?.rating)
  return Number.isFinite(rating) && rating > 0 ? `${rating.toFixed(1)} điểm` : 'Ẩm thực'
}

function categoryCountLabel(key: HomeCategoryCountKey | undefined, count: number | undefined): string | undefined {
  if (!key || !count || count < 1) return undefined
  if (key === 'dishes') return `${count} nổi bật`
  if (key === 'events') return `${count} sắp tới`
  if (key === 'areas') return `${count} vùng`
  return `${count} gợi ý`
}

export function createHomeNocturnePresentation(
  input: HomeNocturnePresentationInput,
): HomeNocturnePresentation {
  const month = Math.min(12, Math.max(1, Math.trunc(input.currentMonth)))
  const consumed = new Set(
    [input.heroId, input.spotlightId]
      .map(value => String(value ?? '').trim())
      .filter(Boolean),
  )
  const decisionEntries: HomeDecisionEntry[] = []

  const addDecision = (
    entity: HomePresentationEntity | undefined,
    entry: (entity: HomePresentationEntity) => Omit<HomeDecisionEntry, 'id'>,
  ) => {
    if (!entity || decisionEntries.length >= 4) return
    const id = entityId(entity)
    if (!id || consumed.has(id)) return
    consumed.add(id)
    decisionEntries.push({ id, ...entry(entity) })
  }

  addDecision(firstAvailable(input.upcomingEvents, consumed), entity => ({
    eyebrow: eventEyebrow(entity),
    title: 'Có lịch gần nhất',
    text: entityLabel(entity),
    to: entityPath(entity.id),
    tone: 'event',
  }))
  addDecision(firstAvailable(input.seasonal, consumed), entity => ({
    eyebrow: `Tháng ${month}`,
    title: 'Đang vào mùa',
    text: entityLabel(entity),
    to: `/theo-mua?mua=${encodeURIComponent(String(month))}`,
    tone: 'season',
  }))
  addDecision(firstAvailable(input.topDishes, consumed), entity => ({
    eyebrow: foodEyebrow(entity),
    title: 'Ăn gì hôm nay',
    text: entityLabel(entity),
    to: '/kham-pha/am-thuc?sort=rating',
    tone: 'food',
  }))
  addDecision(firstAvailable(input.itineraries, consumed), entity => ({
    eyebrow: 'Lịch trình gợi ý',
    title: 'Đi theo lộ trình có sẵn',
    text: entityLabel(entity),
    to: '/lich-trinh',
    tone: 'planner',
  }))

  const remaining = (entities: readonly HomePresentationEntity[]) =>
    entities.filter(entity => entityId(entity) && !consumed.has(entityId(entity)))

  const groups: { primary: HomeCategoryLink[]; utility: HomeCategoryLink[] } = {
    primary: [],
    utility: [],
  }
  for (const definition of CATEGORY_DEFINITIONS) {
    const { group, countKey, ...link } = definition
    const countLabel = categoryCountLabel(countKey, countKey ? input.categoryCounts[countKey] : undefined)
    groups[group].push(countLabel ? { ...link, countLabel } : link)
  }

  return {
    decisionEntries,
    categoryGroups: groups,
    upcomingEventEntries: remaining(input.upcomingEvents).slice(0, 3),
    seasonalEntries: remaining(input.seasonal),
    dishEntries: remaining(input.topDishes),
  }
}
```

- [x] **Step 5: Run GREEN, typecheck the contract, verify the guard, and commit**

```powershell
npm test -- tests/home-nocturne-presentation.test.ts
npm run typecheck
Set-Location ..
$homeBriefHash = (git hash-object -- 'design-system/vinhlong360/pages/home.md').Trim()
if ($homeBriefHash -ne 'b694ac09ede89442c8af48e193534f0fd25ee3a4') { throw "home.md changed during Task 1: $homeBriefHash" }
git diff --check -- web-nuxt/utils/homeNocturnePresentation.ts web-nuxt/tests/home-nocturne-presentation.test.ts
git add web-nuxt/utils/homeNocturnePresentation.ts web-nuxt/tests/home-nocturne-presentation.test.ts
git commit -m "feat: add homepage nocturne presentation adapter"
```

Expected: focused test and typecheck PASS, no whitespace error, hash unchanged, and only the two declared files enter the commit.

### Task 2: Add the Three Narrow Homepage Presentation Components

**Files:**
- Create: `web-nuxt/components/home/HomeFeatureDossier.vue`
- Create: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Create: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Create: `web-nuxt/tests/home-nocturne-components.test.ts`

**Interfaces:**
- Consumes: `HomeDecisionEntry`, `HomeCategoryGroups`, `ImageDescriptor`, route strings, and existing `FramedDossier`/`ImageDisclosure`/`IconLine` primitives.
- Produces: `[data-home-feature-dossier]`, `[data-home-decision-ledger]`, and `[data-home-category-index]` behavior boundaries consumed by the page and tests.

- [x] **Step 1: Verify the guard and write failing mounted component tests**

Run the hash guard from Task 1, then create `web-nuxt/tests/home-nocturne-components.test.ts`:

```ts
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h } from 'vue'
import { describe, expect, it } from 'vitest'
import HomeCategoryIndex from '../components/home/HomeCategoryIndex.vue'
import HomeDecisionLedger from '../components/home/HomeDecisionLedger.vue'
import HomeFeatureDossier from '../components/home/HomeFeatureDossier.vue'
import type { ImageDescriptor } from '../types/image'

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

const descriptor: ImageDescriptor = {
  url: '/img/hero.webp',
  alt: 'Vườn cây ven sông',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: 'Ảnh minh họa',
  full_disclosure: 'Ảnh minh họa do AI dựng, không phải ảnh chụp tại hiện trường.',
  credit: null,
  width: 960,
  height: 640,
}

describe('homepage Nocturne presentation components', () => {
  it('renders only supplied feature anatomy and keeps disclosure attached to media', async () => {
    const wrapper = await mountSuspended(HomeFeatureDossier, {
      props: {
        eyebrow: 'Trải nghiệm tại Long Hồ',
        title: 'Một buổi trong vườn',
        summary: 'Đi chậm giữa vườn cây và rạch nhỏ.',
        region: 'Long Hồ',
        descriptor,
        disclosureId: 'home-feature-disclosure',
        detailTo: '/dia-diem/hero-1',
        plannerTo: '/tao-lich-trinh?add=hero-1',
      },
      global: { stubs: { NuxtImg: NuxtImgStub, IconLine: true } },
    })
    wrappers.push(wrapper)

    const media = wrapper.get('[data-home-feature-media]')
    expect(media.get('img').attributes('aria-describedby')).toBe('home-feature-disclosure')
    expect(wrapper.get('#home-feature-disclosure').text()).toBe(descriptor.full_disclosure)
    expect(wrapper.get('[data-dossier-title]').text()).toBe('Một buổi trong vườn')
    expect(wrapper.findAll('[data-home-feature-action]')).toHaveLength(2)
    expect(wrapper.text()).not.toMatch(/đã xác minh|phổ biến|điểm đến hàng đầu/i)
  })

  it('preserves feature geometry and disclosure when no image URL is supplied', async () => {
    const wrapper = await mountSuspended(HomeFeatureDossier, {
      props: {
        eyebrow: 'Gợi ý nổi bật',
        title: 'Điểm đến đang cập nhật ảnh',
        descriptor: {
          ...descriptor,
          url: null,
          source_class: 'placeholder',
          source_kind: 'generated-placeholder',
          disclosure_key: 'entity-placeholder',
          short_label: 'Ảnh đại diện đang cập nhật',
          full_disclosure: 'Hình đại diện tạm thời trong khi ảnh thực tế đang được cập nhật.',
        },
        disclosureId: 'home-feature-placeholder',
        detailTo: '/dia-diem/placeholder-1',
      },
      global: { stubs: { NuxtImg: NuxtImgStub, IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-home-feature-media]').classes()).toContain('home-feature-dossier__media--empty')
    expect(wrapper.find('[data-home-feature-media] img').exists()).toBe(false)
    expect(wrapper.get('#home-feature-placeholder').text()).toContain('Hình đại diện tạm thời')
    expect(wrapper.findAll('[data-home-feature-action]')).toHaveLength(1)
  })

  it('renders an unnumbered deterministic decision ledger', async () => {
    const wrapper = await mountSuspended(HomeDecisionLedger, {
      props: {
        entries: [
          { id: 'event-1', eyebrow: 'Ngày mai', title: 'Có lịch gần nhất', text: 'Lễ hội sông nước', to: '/dia-diem/event-1', tone: 'event' },
          { id: 'season-1', eyebrow: 'Tháng 8', title: 'Đang vào mùa', text: 'Chôm chôm', to: '/theo-mua?mua=8', tone: 'season' },
        ],
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.find('ol').exists()).toBe(false)
    const rows = wrapper.findAll('[data-home-decision-entry]')
    expect(rows.map(row => row.get('.home-decision-ledger__eyebrow').text())).toEqual(['Ngày mai', 'Tháng 8'])
    expect(rows.map(row => row.get('.home-decision-ledger__title').text())).toEqual(['Có lịch gần nhất', 'Đang vào mùa'])
    expect(rows.map(row => row.get('.home-decision-ledger__text').text())).toEqual(['Lễ hội sông nước', 'Chôm chôm'])
    expect(wrapper.text()).not.toMatch(/\b0[1-9]\b/)
  })

  it('renders primary and utility routes exactly once', async () => {
    const wrapper = await mountSuspended(HomeCategoryIndex, {
      props: {
        groups: {
          primary: [
            { key: 'du-lich', label: 'Du lịch', hint: 'Vườn và sông', to: '/du-lich', icon: 'leaf', accent: 'leaf', countLabel: '5 gợi ý' },
          ],
          utility: [
            { key: 'ban-do', label: 'Bản đồ', hint: 'Lọc theo vùng', to: '/ban-do', icon: 'map', accent: 'river' },
          ],
        },
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-home-category-primary]').text()).toContain('5 gợi ý')
    expect(wrapper.get('[data-home-category-utility]').text()).not.toContain('gợi ý')
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/du-lich', '/ban-do'])
  })
})
```

- [x] **Step 2: Run the component test and verify RED**

```powershell
Set-Location web-nuxt
npm test -- tests/home-nocturne-components.test.ts
```

Expected: FAIL because the three Vue components do not exist.

- [x] **Step 3: Implement `HomeFeatureDossier.vue` without fetching or inventing claims**

Use one media link with canonical disclosure and one `FramedDossier` body. The component must not accept rating, source, ranking, or personalization props:

```vue
<template>
  <aside class="home-feature-dossier" data-home-feature-dossier>
    <NuxtLink
      v-if="descriptor.url"
      :to="detailTo"
      class="home-feature-dossier__media"
      data-home-feature-media
      :aria-label="`Xem ${title}`"
    >
      <NuxtImg
        :src="descriptor.url"
        :alt="descriptor.alt"
        :aria-describedby="disclosureId"
        width="960"
        height="640"
        sizes="375px sm:540px md:640px"
        loading="eager"
        fetchpriority="high"
      />
      <ImageDisclosure :id="disclosureId" :descriptor="descriptor" presentation="short" />
    </NuxtLink>
    <div v-else class="home-feature-dossier__media home-feature-dossier__media--empty" data-home-feature-media>
      <IconLine name="pin" aria-hidden="true" />
      <ImageDisclosure :id="disclosureId" :descriptor="descriptor" presentation="short" />
    </div>

    <FramedDossier :eyebrow="eyebrow" :title="title" heading-tag="h2">
      <template v-if="summary" #summary><p>{{ summary }}</p></template>
      <template v-if="region" #meta><span>{{ region }}</span></template>
      <template #action>
        <NuxtLink :to="detailTo" class="home-feature-dossier__action" data-home-feature-action>Khám phá</NuxtLink>
        <NuxtLink v-if="plannerTo" :to="plannerTo" no-prefetch class="home-feature-dossier__action home-feature-dossier__action--secondary" data-home-feature-action>Thêm vào lịch trình</NuxtLink>
      </template>
    </FramedDossier>
  </aside>
</template>

<script setup lang="ts">
import type { ImageDescriptor } from '~/types/image'

withDefaults(defineProps<{
  eyebrow: string
  title: string
  summary?: string | null
  region?: string | null
  descriptor: ImageDescriptor
  disclosureId: string
  detailTo: string
  plannerTo?: string
}>(), {
  summary: undefined,
  region: undefined,
  plannerTo: undefined,
})
</script>
```

- [x] **Step 4: Implement the ledger and category index as semantic route lists**

Create `HomeDecisionLedger.vue`:

```vue
<template>
  <section v-if="entries.length" class="home-decision-ledger" data-home-decision-ledger aria-labelledby="home-decision-title">
    <header class="home-decision-ledger__intro">
      <p>Gợi ý nhanh</p>
      <h2 id="home-decision-title">Hôm nay bạn muốn bắt đầu thế nào?</h2>
      <p>Dựa trên mùa, sự kiện và nội dung đang có để đưa bạn tới đúng luồng tiếp theo.</p>
    </header>
    <ul class="home-decision-ledger__list" role="list">
      <li v-for="entry in entries" :key="entry.id" class="home-decision-ledger__row" data-home-decision-entry>
        <NuxtLink :to="entry.to" class="home-decision-ledger__link" :data-tone="entry.tone">
          <span class="home-decision-ledger__eyebrow">{{ entry.eyebrow }}</span>
          <strong class="home-decision-ledger__title">{{ entry.title }}</strong>
          <span class="home-decision-ledger__text">{{ entry.text }}</span>
          <span class="home-decision-ledger__arrow" aria-hidden="true">→</span>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { HomeDecisionEntry } from '~/utils/homeNocturnePresentation'

defineProps<{ entries: readonly HomeDecisionEntry[] }>()
</script>
```

Create `HomeCategoryIndex.vue`:

```vue
<template>
  <section class="home-category-index" data-home-category-index aria-labelledby="home-category-title">
    <header class="home-category-index__header">
      <p>Chỉ mục địa phương</p>
      <h2 id="home-category-title">Khám phá theo nhu cầu</h2>
    </header>
    <nav class="home-category-index__primary" data-home-category-primary aria-label="Khám phá chính">
      <NuxtLink v-for="link in groups.primary" :key="link.key" :to="link.to" class="home-category-index__primary-link" :data-accent="link.accent">
        <IconLine :name="link.icon" aria-hidden="true" />
        <span><strong>{{ link.label }}</strong><small>{{ link.hint }}</small></span>
        <span v-if="link.countLabel" class="home-category-index__count">{{ link.countLabel }}</span>
      </NuxtLink>
    </nav>
    <div class="home-category-index__utility" data-home-category-utility>
      <p>Tiện ích cho hành trình</p>
      <nav aria-label="Tiện ích hành trình">
        <NuxtLink v-for="link in groups.utility" :key="link.key" :to="link.to" class="home-category-index__utility-link" :data-accent="link.accent">
          <IconLine :name="link.icon" aria-hidden="true" />
          <span><strong>{{ link.label }}</strong><small>{{ link.hint }}</small></span>
          <span v-if="link.countLabel" class="home-category-index__count">{{ link.countLabel }}</span>
        </NuxtLink>
      </nav>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { HomeCategoryGroups } from '~/utils/homeNocturnePresentation'

defineProps<{ groups: HomeCategoryGroups }>()
</script>
```

- [x] **Step 5: Run GREEN, regression tests, guard, and commit**

```powershell
npm test -- tests/home-nocturne-components.test.ts tests/framed-dossier.test.ts tests/entity-image-detail.test.ts
npm run typecheck
Set-Location ..
$homeBriefHash = (git hash-object -- 'design-system/vinhlong360/pages/home.md').Trim()
if ($homeBriefHash -ne 'b694ac09ede89442c8af48e193534f0fd25ee3a4') { throw "home.md changed during Task 2: $homeBriefHash" }
git diff --check -- web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/components/home/HomeDecisionLedger.vue web-nuxt/components/home/HomeCategoryIndex.vue web-nuxt/tests/home-nocturne-components.test.ts
git add web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/components/home/HomeDecisionLedger.vue web-nuxt/components/home/HomeCategoryIndex.vue web-nuxt/tests/home-nocturne-components.test.ts
git commit -m "feat: add homepage nocturne presentation components"
```

### Task 3: Integrate the Hero, Decision Ledger, Category Index, and De-duplicated Lists

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Create: `web-nuxt/tests/home-nocturne-page.test.ts`
- Modify: `web-nuxt/tests/smoke.test.ts`
- Modify: `web-nuxt/tests/ugc-image-classification.test.ts`

**Interfaces:**
- Consumes: `createHomeNocturnePresentation`, the three Task 2 components, existing `/api/homepage` state, image descriptors, route helpers, and client-only composables.
- Produces: the stable root `[data-home-pilot="nocturne-b1"]`, top-zone section markers, unchanged request boundaries, and adapter-filtered event/seasonal/dish collections.

- [x] **Step 1: Verify the guard and add a mounted page test that fails against the legacy markup**

Create a real mounted page fixture in `home-nocturne-page.test.ts`. Mock only network boundaries; retain the page's real computed state and new child components. Include `clearNuxtData()` after each case so the fixed `homepage` and `home-community` keys do not leak fixtures:

```ts
import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../pages/index.vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: { type: String, required: true }, alt: { type: String, required: true } },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const EmptyStateStub = defineComponent({
  props: { title: String, message: String },
  template: '<div data-empty-state><strong>{{ title }}</strong><span>{{ message }}</span><slot name="actions" /></div>',
})
const pageStubs = {
  NuxtImg: NuxtImgStub,
  EmptyState: EmptyStateStub,
  EntityCard: { props: ['entity'], template: '<article data-entity-card>{{ entity.name }}</article>' },
  EntityFeature: { template: '<section data-existing-entity-feature />' },
  StorySpread: { template: '<section data-existing-story-spread />' },
  HeroIllustration: true,
  IconLine: true,
  JourneyActionRail: true,
  SearchAutocomplete: { template: '<div data-home-search />' },
  SkeletonGrid: true,
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => apiFetchMock.mockReset())
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
  document.documentElement.classList.remove('dark', 'light')
})

function homeFixture() {
  return {
    month: 8,
    seasonal_tagline: 'Theo dòng sông, gặp mùa trái chín',
    experiences: [
      { id: 'experience-1', name: 'Vườn ven sông', type: 'experience', summary: 'Đi giữa vườn cây.', images: ['/img/hero.webp'] },
      { id: 'experience-2', name: 'Làng nghề gốm', type: 'experience', summary: 'Nghe chuyện người thợ.' },
    ],
    products: [{ id: 'product-1', name: 'Gốm đỏ Mang Thít', type: 'product', summary: 'Một câu chuyện vật liệu.' }],
    upcoming_events: [
      { id: 'event-1', name: 'Lễ hội sông nước', days_until: 1, attributes: { date_start: '2026-08-01' } },
      { id: 'event-2', name: 'Đêm đờn ca', days_until: 4, attributes: { date_start: '2026-08-04' } },
    ],
    seasonal: [
      { id: 'season-1', name: 'Chôm chôm Bình Hòa Phước', type: 'product' },
      { id: 'season-2', name: 'Bưởi Năm Roi', type: 'product' },
    ],
    top_dishes: [
      { id: 'dish-1', name: 'Cá tai tượng chiên xù', attributes: { rating: 4.8, review_count: 12 } },
      { id: 'dish-2', name: 'Bánh xèo hến', attributes: { rating: 4.6, review_count: 8 } },
    ],
    itineraries: [{ id: 'plan-1', title: 'Một ngày ven sông' }],
    area_counts: { 'long-ho': 2, 'mang-thit': 1 },
  }
}

describe('homepage Existing Screen Evolution B1', () => {
  it('renders the controlled top zone and removes decision items from following collections', async () => {
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/homepage') return Promise.resolve(homeFixture())
      if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
      if (path === '/api/community/stats') return Promise.resolve(null)
      if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
      if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
      if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
    wrappers.push(wrapper)
    await flushUi()

    expect(wrapper.get('[data-home-pilot="nocturne-b1"]')).toBeTruthy()
    expect(wrapper.get('[data-home-feature-dossier]').text()).toContain('Vườn ven sông')
    expect(wrapper.find('.hero-kenburns').exists()).toBe(false)
    const decisions = wrapper.findAll('[data-home-decision-entry]')
    expect(decisions.map(row => row.get('.home-decision-ledger__title').text())).toEqual([
      'Có lịch gần nhất',
      'Đang vào mùa',
      'Ăn gì hôm nay',
      'Đi theo lộ trình có sẵn',
    ])
    expect(decisions.map(row => row.get('.home-decision-ledger__text').text())).toEqual([
      'Lễ hội sông nước',
      'Chôm chôm Bình Hòa Phước',
      'Cá tai tượng chiên xù',
      'Một ngày ven sông',
    ])
    const temporal = wrapper.get('[data-home-section="events-seasonal"]')
    expect(temporal.text()).toContain('Đêm đờn ca')
    expect(temporal.text()).not.toContain('Lễ hội sông nước')
    expect(wrapper.findAll('[data-entity-card]').map(card => card.text())).toEqual(['Bưởi Năm Roi'])
    expect(wrapper.text()).toContain('Bánh xèo hến')
  })
})
```

- [x] **Step 2: Run the page test and verify RED**

```powershell
npm test -- tests/home-nocturne-page.test.ts
```

Expected: FAIL because the root pilot, new components, unnumbered entries, and adapter-driven collection results are not integrated.

- [x] **Step 3: Replace only the top-zone presentation markup**

In `pages/index.vue`:

- Change the root to `<div class="home" data-home-pilot="nocturne-b1">`.
- Remove only `<div class="hero-kenburns">` and the legacy `.hero-feature/.hf-*` block; retain `HeroIllustration`, scrim, hero copy, `SearchAutocomplete`, and `/ban-do?near=1` action.
- Render `HomeFeatureDossier` in the right hero zone with `heroFeatureReason`, `heroFeature.name`, `heroFeature.summary`, `hfRegion`, `heroFeatureDescriptor`, `heroFeatureDisclosureId`, `entityPath(heroFeature.id)`, and `plannerAddPath(heroFeature.id)`.
- Replace the numbered `<ol class="decision-index">` section with `<HomeDecisionLedger :entries="homePresentation.decisionEntries" data-home-section="decisions" />`.
- Replace the flat category grid with `<HomeCategoryIndex v-if="!homePending" :groups="homePresentation.categoryGroups" data-home-section="categories" />`.
- Add `data-home-section="hero"`, `data-home-section="recovery"`, and `data-home-section="events-seasonal"` to their stable server-rendered regions.

The new hero binding is exact:

```vue
<HomeFeatureDossier
  v-if="heroFeature"
  class="hero-feature"
  :eyebrow="heroFeatureReason"
  :title="heroFeature.name"
  :summary="heroFeature.summary"
  :region="hfRegion"
  :descriptor="heroFeatureDescriptor"
  :disclosure-id="heroFeatureDisclosureId"
  :detail-to="entityPath(heroFeature.id)"
  :planner-to="plannerAddPath(heroFeature.id)"
/>
```

- [x] **Step 4: Replace page-local decision/category computation with the pure adapter**

Import the three components and adapter. Remove `HomeDecisionCard`, `CATEGORY_LINKS`, `categoryLinks`, `firstUpcomingEvent`, `firstSeasonal`, `firstDish`, `homeDecisionCards`, `eventCountdownLabel`, and `categoryMetric`. Keep `formatEventDay`, `formatEventMonth`, `formatRating`, route helpers, journey/personalization state, and all network calls.

After `heroFeature`, `areaCounts`, and `spotlight` are available, add:

```ts
const homePresentation = computed(() => createHomeNocturnePresentation({
  currentMonth: currentMonth.value,
  heroId: heroFeature.value?.id,
  spotlightId: spotlight.value?.id,
  upcomingEvents: upcomingEvents.value,
  seasonal: seasonal.value,
  topDishes: topDishes.value,
  itineraries: itineraries.value,
  categoryCounts: {
    experiences: experiences.value.length,
    dishes: topDishes.value.length,
    products: productsAll.value.length,
    events: upcomingEvents.value.length,
    areas: Object.keys(areaCounts.value).length,
  },
}))

const upcomingEventList = computed(() => homePresentation.value.upcomingEventEntries)
const seasonalList = computed(() => homePresentation.value.seasonalEntries)
const topDishesList = computed(() => homePresentation.value.dishEntries)
```

Change the event list condition/loop to `upcomingEventList.length` and `v-for="ev in upcomingEventList"`. Keep `experienceThumbs` filtered against hero and spotlight IDs. Remove `hfBg`, `hfIcon`, and the unused `generateCategoryPlaceholder` import; retain `generateCategoryIcon` for the existing `Dành cho bạn` fallback icon.

- [x] **Step 5: Update supporting smoke and UGC fixtures without replacing behavior tests**

In `tests/smoke.test.ts`, keep assertions for intent-led copy, `homepageDecisionActions`, `JourneyActionRail`, `plannerAddPath`, and `Dành cho bạn`. Replace legacy assertions for `homeDecisionCards`, `dx-item`, fake numbering, and page-local category markup with structural assertions for `createHomeNocturnePresentation`, `HomeFeatureDossier`, `HomeDecisionLedger`, `HomeCategoryIndex`, and `data-home-pilot="nocturne-b1"`.

In `tests/ugc-image-classification.test.ts`, add `HomeFeatureDossier`, `HomeDecisionLedger`, and `HomeCategoryIndex` to `pageStubs` only if the existing focused UGC test cannot mount them with its minimal homepage fixture. Do not stub `ImageDisclosure`, remove the `data-image-surface="home-community"` assertion, or relax the no-UGC-thumbnail checks.

- [x] **Step 6: Run GREEN and focused regressions, verify guard, and commit**

```powershell
npm test -- tests/home-nocturne-page.test.ts tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/ugc-image-classification.test.ts tests/smoke.test.ts tests/journeyActions.test.ts
npm run typecheck
Set-Location ..
$homeBriefHash = (git hash-object -- 'design-system/vinhlong360/pages/home.md').Trim()
if ($homeBriefHash -ne 'b694ac09ede89442c8af48e193534f0fd25ee3a4') { throw "home.md changed during Task 3: $homeBriefHash" }
git diff --check -- web-nuxt/pages/index.vue web-nuxt/tests/home-nocturne-page.test.ts web-nuxt/tests/smoke.test.ts web-nuxt/tests/ugc-image-classification.test.ts
git add web-nuxt/pages/index.vue web-nuxt/tests/home-nocturne-page.test.ts web-nuxt/tests/smoke.test.ts web-nuxt/tests/ugc-image-classification.test.ts
git commit -m "feat: integrate homepage nocturne top zone"
```

### Task 4: Complete the Middle/Bottom Composition and Homepage-scoped Visual Layer

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Create: `web-nuxt/assets/css/home-nocturne.css`
- Modify: `web-nuxt/tests/home-nocturne-page.test.ts`

**Interfaces:**
- Consumes: the Task 3 pilot root and section markers, Plan A semantic tokens, adapter-filtered lists, and current `EntityFeature`, `StorySpread`, community, and personalization models.
- Produces: distinct temporal, editorial, split-dossier, community, and personal densities with identical Nocturne/Parchment DOM order.

- [x] **Step 1: Verify the guard and extend the mounted page test for the remaining behavior**

Add these cases to `home-nocturne-page.test.ts`. Also change `beforeEach` to clear `localStorage` so no previous favorite/recent-history signal leaks into the no-personalization assertion:

```ts
beforeEach(() => {
  apiFetchMock.mockReset()
  localStorage.clear()
})

it('keeps navigation and retry available when the homepage request fails', async () => {
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/homepage') return Promise.reject(new Error('homepage unavailable'))
    if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
    if (path === '/api/community/stats') return Promise.resolve(null)
    if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
    if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
    if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
    return Promise.resolve({})
  })

  const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.get('[data-home-search]').exists()).toBe(true)
  expect(wrapper.get('[data-empty-state]').text()).toContain('Đang cập nhật nội dung')
  expect(wrapper.get('[data-empty-state] button').text()).toBe('Tải lại')
  expect(wrapper.get('[data-home-category-index]').findAll('a').map(link => link.attributes('href'))).toEqual([
    '/du-lich',
    '/kham-pha/am-thuc',
    '/ocop',
    '/le-hoi',
    '/luu-tru',
    '/lich-trinh',
    '/ban-do',
  ])
})

it('isolates community failure and omits personalization without a real signal', async () => {
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/homepage') return Promise.resolve(homeFixture())
    if (path.startsWith('/api/community/') || path === '/api/feed?limit=10') {
      return Promise.reject(new Error('community unavailable'))
    }
    if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
    return Promise.resolve({})
  })

  const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.get('[data-existing-entity-feature]').exists()).toBe(true)
  expect(wrapper.get('[data-existing-story-spread]').exists()).toBe(true)
  expect(wrapper.get('[data-home-section="spotlight-food"]').exists()).toBe(true)
  expect(wrapper.get('[data-home-section="community"] a[href="/cong-dong"]').exists()).toBe(true)
  expect(wrapper.find('[data-home-section="for-you"]').exists()).toBe(false)
})

it('preserves the stable section order across Nocturne and Daylight Parchment', async () => {
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path === '/api/homepage') return Promise.resolve(homeFixture())
    if (path === '/api/feed?limit=10') return Promise.resolve({ posts: [] })
    if (path === '/api/community/stats') return Promise.resolve(null)
    if (path === '/api/community/leaderboard?limit=3') return Promise.resolve({ leaders: [] })
    if (path === '/api/community/trending-tags?limit=8') return Promise.resolve({ tags: [] })
    if (path.startsWith('/api/entities/popular?')) return Promise.resolve({ entities: [] })
    return Promise.resolve({})
  })

  document.documentElement.classList.add('dark')
  const wrapper = await mountSuspended(HomePage, { global: { stubs: pageStubs } })
  wrappers.push(wrapper)
  await flushUi()

  const stableSections = new Set([
    'hero',
    'decisions',
    'categories',
    'events-seasonal',
    'editorial-feature',
    'spotlight-food',
    'story-spread',
  ])
  const sectionOrder = () => wrapper
    .findAll('[data-home-section]')
    .map(node => node.attributes('data-home-section'))
    .filter(name => stableSections.has(name))

  const nocturneOrder = sectionOrder()
  document.documentElement.classList.replace('dark', 'light')
  await nextTick()
  expect(sectionOrder()).toEqual(nocturneOrder)
})
```

These are rendered behavior assertions; do not replace them with source-string checks.

- [x] **Step 2: Run the expanded page test and verify RED**

```powershell
Set-Location web-nuxt
npm test -- tests/home-nocturne-page.test.ts
```

Expected: at least the new section-marker/theme-order assertions FAIL because middle/bottom markers and the new scoped CSS import are absent.

- [x] **Step 3: Mark and refine the existing middle/bottom sections without changing their data flow**

In `pages/index.vue`:

- Add stable `data-home-section` values in this order: `events-seasonal`, `editorial-feature`, `spotlight-food`, `story-spread`, `community`, `for-you`.
- Keep events as a vertical temporal list and seasonal content as the only horizontal collection in that middle zone.
- Keep exactly one `EntityFeature` and one later `StorySpread`; do not duplicate either component.
- Rename the spotlight wrapper to `home-spotlight-dossier` and the dish side to `home-food-ledger`; keep current detail and `/kham-pha/am-thuc` routes.
- Render a rating badge only when `Number(d.attributes?.rating) > 0`; render review count only when positive. Remove the `Mới` fallback because it presents absent rating data as a status.
- Keep community inside `ClientOnly`, retain `data-source-class="user-uploaded"`, and translate the visible `Trending:` label to `Đang được nhắc:` without changing tag routes.
- Keep `Dành cho bạn` inside its existing `ClientOnly` and real-signal condition.
- Append `<style src="~/assets/css/home-nocturne.css"></style>` after the existing homepage `<style>` block so the compatibility layer wins only on this page.

- [x] **Step 4: Create the scoped Nocturne/Parchment composition stylesheet**

Create `web-nuxt/assets/css/home-nocturne.css`. Every selector must begin with `[data-home-pilot="nocturne-b1"]`; use semantic tokens and the following complete anatomy:

```css
[data-home-pilot="nocturne-b1"] {
  background: var(--color-canvas);
  color: var(--color-text);
}

[data-home-pilot="nocturne-b1"] .hero {
  min-height: min(52rem, calc(100svh - var(--header-h)));
  background: var(--color-canvas);
  border-block-end: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .hero-inner {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(20rem, .92fr);
  gap: clamp(var(--space-6), 5vw, var(--space-12));
  align-items: end;
  width: min(var(--maxw), calc(100% - var(--space-10)));
  margin-inline: auto;
  padding-block: clamp(var(--space-12), 12vh, var(--space-20));
}

[data-home-pilot="nocturne-b1"] .hero-main h1 {
  max-width: 13ch;
  margin-block: var(--space-3) var(--space-4);
  font-family: var(--font-editorial-display);
  font-size: clamp(var(--text-4xl), 7vw, var(--text-5xl));
  line-height: .98;
  letter-spacing: -.02em;
}

[data-home-pilot="nocturne-b1"] .hero-sub {
  max-width: 42rem;
  color: var(--color-text-muted);
  font-family: var(--font-body);
  font-size: max(var(--text-base), 1rem);
}

[data-home-pilot="nocturne-b1"] .hero-search,
[data-home-pilot="nocturne-b1"] .hero-nearby,
[data-home-pilot="nocturne-b1"] a,
[data-home-pilot="nocturne-b1"] button {
  min-height: var(--touch-min);
}

[data-home-pilot="nocturne-b1"] :is(a, button, input):focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: var(--space-1);
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier {
  display: grid;
  grid-template-rows: minmax(16rem, 1fr) auto;
  align-self: stretch;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__media {
  position: relative;
  display: block;
  min-height: 16rem;
  overflow: hidden;
  border-block-end: 1px solid var(--color-border);
  background: var(--color-surface-raised);
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__media .image-disclosure {
  position: absolute;
  inset-inline-start: var(--space-3);
  inset-block-end: var(--space-3);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier .framed-dossier {
  border: 0;
  border-radius: 0;
  background: transparent;
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__action {
  display: inline-flex;
  align-items: center;
  padding-inline: var(--space-4);
  border: 1px solid var(--color-action);
  color: var(--color-action);
  text-decoration: none;
}

[data-home-pilot="nocturne-b1"] .home-feature-dossier__action--secondary {
  border-color: var(--color-border);
  color: var(--color-text);
}

[data-home-pilot="nocturne-b1"] .home-decision-ledger {
  display: grid;
  grid-template-columns: minmax(15rem, .72fr) minmax(0, 1.28fr);
  gap: var(--space-8);
  width: min(var(--maxw), calc(100% - var(--space-10)));
  margin-inline: auto;
  padding-block: var(--space-10);
  border-block-end: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .home-decision-ledger__intro > p:first-child,
[data-home-pilot="nocturne-b1"] .home-category-index__header > p,
[data-home-pilot="nocturne-b1"] .home-category-index__utility > p {
  color: var(--color-action);
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: .08em;
  text-transform: uppercase;
}

[data-home-pilot="nocturne-b1"] .home-decision-ledger__list {
  margin: 0;
  padding: 0;
  border-block-start: 1px solid var(--color-border);
  list-style: none;
}

[data-home-pilot="nocturne-b1"] .home-decision-ledger__row {
  border-block-end: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .home-decision-ledger__link {
  display: grid;
  grid-template-columns: minmax(7rem, .38fr) minmax(10rem, .72fr) minmax(12rem, 1fr) auto;
  gap: var(--space-4);
  align-items: center;
  min-height: calc(var(--touch-min) + var(--space-5));
  color: var(--color-text);
  text-decoration: none;
}

[data-home-pilot="nocturne-b1"] .home-decision-ledger__eyebrow,
[data-home-pilot="nocturne-b1"] .home-decision-ledger__text {
  color: var(--color-text-muted);
}

[data-home-pilot="nocturne-b1"] .home-category-index {
  width: min(var(--maxw), calc(100% - var(--space-10)));
  margin-inline: auto;
  padding-block: var(--space-10);
}

[data-home-pilot="nocturne-b1"] .home-category-index__primary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-block-start: 1px solid var(--color-border);
  border-inline-start: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .home-category-index__primary-link,
[data-home-pilot="nocturne-b1"] .home-category-index__utility-link {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-5);
  border-inline-end: 1px solid var(--color-border);
  border-block-end: 1px solid var(--color-border);
  color: var(--color-text);
  text-decoration: none;
}

[data-home-pilot="nocturne-b1"] .home-category-index__primary-link small,
[data-home-pilot="nocturne-b1"] .home-category-index__utility-link small {
  display: block;
  margin-block-start: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

[data-home-pilot="nocturne-b1"] .home-category-index__count {
  grid-column: 2;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

[data-home-pilot="nocturne-b1"] .home-category-index__utility {
  display: grid;
  grid-template-columns: minmax(10rem, .32fr) minmax(0, 1fr);
  gap: var(--space-6);
  margin-block-start: var(--space-6);
}

[data-home-pilot="nocturne-b1"] .home-category-index__utility nav {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-block-start: 1px solid var(--color-border);
  border-inline-start: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .happening-rest,
[data-home-pilot="nocturne-b1"] .dishes-list {
  border-block-start: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .event-mini,
[data-home-pilot="nocturne-b1"] .dish-item {
  border-block-end: 1px solid var(--color-border);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  transform: none;
}

[data-home-pilot="nocturne-b1"] .home-spotlight-dossier {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(18rem, .85fr);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

[data-home-pilot="nocturne-b1"] .home-spotlight-dossier .spotlight {
  border-inline-end: 1px solid var(--color-border);
}

[data-home-pilot="nocturne-b1"] .home-food-ledger {
  padding: var(--space-6);
}

[data-home-pilot="nocturne-b1"] .community-join,
[data-home-pilot="nocturne-b1"] .fy-chip {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  box-shadow: none;
}

[data-home-pilot="nocturne-b1"] :is(.event-mini, .dish-item, .fy-chip):hover {
  transform: none;
  border-color: var(--color-action);
}

@media (max-width: 64rem) {
  [data-home-pilot="nocturne-b1"] .hero-inner,
  [data-home-pilot="nocturne-b1"] .home-decision-ledger,
  [data-home-pilot="nocturne-b1"] .home-spotlight-dossier {
    grid-template-columns: 1fr;
  }

  [data-home-pilot="nocturne-b1"] .home-category-index__primary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  [data-home-pilot="nocturne-b1"] .home-spotlight-dossier .spotlight {
    border-inline-end: 0;
    border-block-end: 1px solid var(--color-border);
  }
}

@media (max-width: 48rem) {
  [data-home-pilot="nocturne-b1"] .hero-inner {
    width: min(calc(100% - var(--space-10)), var(--maxw));
    padding-block: var(--space-10);
  }

  [data-home-pilot="nocturne-b1"] .home-decision-ledger__link {
    grid-template-columns: 1fr auto;
    gap: var(--space-2) var(--space-4);
    padding-block: var(--space-4);
  }

  [data-home-pilot="nocturne-b1"] .home-decision-ledger__eyebrow,
  [data-home-pilot="nocturne-b1"] .home-decision-ledger__text {
    grid-column: 1;
  }

  [data-home-pilot="nocturne-b1"] .home-decision-ledger__arrow {
    grid-column: 2;
    grid-row: 1 / span 3;
  }

  [data-home-pilot="nocturne-b1"] .home-category-index__primary,
  [data-home-pilot="nocturne-b1"] .home-category-index__utility nav {
    grid-template-columns: 1fr;
  }

  [data-home-pilot="nocturne-b1"] .home-category-index__utility {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  [data-home-pilot="nocturne-b1"] *,
  [data-home-pilot="nocturne-b1"] *::before,
  [data-home-pilot="nocturne-b1"] *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
  }
}

@media (forced-colors: active) {
  [data-home-pilot="nocturne-b1"] :is(
    .home-feature-dossier,
    .home-decision-ledger__row,
    .home-category-index__primary-link,
    .home-category-index__utility-link,
    .home-spotlight-dossier,
    .community-join,
    .fy-chip
  ) {
    border-color: CanvasText;
  }

  [data-home-pilot="nocturne-b1"] :is(a, button, input):focus-visible {
    outline-color: Highlight;
  }
}
```

The referenced layout, spacing, type, focus, surface, and action tokens already exist in the Plan A/base token layers. Do not add fallback literals or new token aliases for B1.

- [x] **Step 5: Remove only selectors made dead by the new markup**

From the existing `<style>` in `pages/index.vue`, delete the complete legacy selector blocks for `.hero-kenburns` and its keyframes, `.hf-card/.hf-*`, `.decision-shell/.decision-*/.dx-*`, and `.cat-grid/.cat-tile/.cat-*` after confirming no remaining template node uses them:

```powershell
rg -n "hero-kenburns|hf-card|hf-|decision-shell|decision-index|dx-|cat-grid|cat-tile" web-nuxt/pages/index.vue
```

Expected after cleanup: no template or script reference remains; any remaining result must be a migration comment explaining the removed name, not a live selector.

- [x] **Step 6: Run GREEN, accessibility/style regressions, guard, and commit**

```powershell
npm test -- tests/home-nocturne-page.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-presentation.test.ts tests/theme-mode-control.test.ts tests/framed-dossier.test.ts tests/entity-card-disclosure.test.ts tests/image-renderer-inventory.test.ts tests/ugc-image-classification.test.ts tests/smoke.test.ts
npm run typecheck
Set-Location ..
$homeBriefHash = (git hash-object -- 'design-system/vinhlong360/pages/home.md').Trim()
if ($homeBriefHash -ne 'b694ac09ede89442c8af48e193534f0fd25ee3a4') { throw "home.md changed during Task 4: $homeBriefHash" }
git diff --check -- web-nuxt/pages/index.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-nocturne-page.test.ts
git add web-nuxt/pages/index.vue web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-nocturne-page.test.ts
git commit -m "feat: complete homepage nocturne composition"
```

### Task 5: Close Regression, Visual QA, and Rollback Evidence

**Files:**
- Create: `docs/superpowers/qa/2026-07-31-homepage-b1/report.md`
- Modify: `docs/superpowers/plans/2026-07-31-homepage-existing-screen-evolution.md`
- Modify: `docs/superpowers/specs/2026-07-31-homepage-existing-screen-evolution-design.md`

**Interfaces:**
- Consumes: all Task 1–4 commits, mounted behavior suites, Nuxt production build, local production preview, and the approved visual QA matrix.
- Produces: a closed B1 plan/spec status, exact test/build evidence, four canonical screenshot baselines, and a rollback instruction that removes the pilot without touching shared shell or data flow.

- [x] **Step 1: Verify the guard and audit the completed behavior matrix**

Review the spec sections `Required States and Recovery`, `Interaction and Accessibility`, and `Anti-Template Gate` against the mounted tests. The final page suite must explicitly assert:

- failed `/api/homepage` still leaves `[data-home-search]`, all seven category routes, retry action, and public shell mountable;
- rejected community endpoints do not remove editorial feature/story/spotlight regions;
- no real personal signal means no `data-home-section="for-you"`;
- `.dark` and `.light` preserve the same non-client-only `data-home-section` order;
- no numeric rank marker, unsupported trust/source label, or zero-rating `Mới` badge reaches the DOM;
- hero, decision, and downstream event/seasonal/dish fixtures remain de-duplicated.

Every item is implemented in Tasks 1–4. If an item is absent, stop Task 5 and reopen the owning task instead of adding implementation or test scope to the closure commit. Record `No missing behavior assertion after integrated review` in the QA report when the audit is complete.

- [x] **Step 2: Run the full automated verification gate**

From `web-nuxt`:

```powershell
npm test -- tests/home-nocturne-presentation.test.ts tests/home-nocturne-components.test.ts tests/home-nocturne-page.test.ts tests/ugc-image-classification.test.ts tests/journeyActions.test.ts tests/theme-mode-control.test.ts tests/framed-dossier.test.ts tests/entity-card-disclosure.test.ts tests/entity-image-detail.test.ts tests/image-renderer-inventory.test.ts tests/smoke.test.ts
npm run typecheck
npm run build
```

Expected: every selected suite PASS, typecheck exits `0`, production build exits `0`, and no new dependency is added to `package.json` or the lockfile.

- [x] **Step 3: Run the production visual QA matrix**

Start the built preview on an unused port and use the in-app browser control skill to inspect `/` with real keyboard interaction. Test 375, 390, 768, 1024, and 1440 CSS pixels in Nocturne and Daylight Parchment; also test mobile landscape, keyboard tab order, reduced motion, forced colors, image fallback, homepage partial data, community empty/failure, and 200% text zoom.

Capture these four canonical baselines:

```text
docs/superpowers/qa/2026-07-31-homepage-b1/nocturne-mobile-390.webp
docs/superpowers/qa/2026-07-31-homepage-b1/parchment-mobile-390.webp
docs/superpowers/qa/2026-07-31-homepage-b1/nocturne-desktop-1440.webp
docs/superpowers/qa/2026-07-31-homepage-b1/parchment-desktop-1440.webp
```

For every matrix row, record viewport, theme, fixture/state, keyboard result, overflow result, disclosure visibility, and screenshot filename or `not canonical` in `report.md`. A row fails if horizontal page overflow appears, a 44px action becomes smaller, focus is invisible, a disclosure disappears, section order changes, content animates under reduced motion, or labels/actions clip at 200% zoom.

- [x] **Step 4: Perform the anti-template and rollback audit**

Run:

```powershell
rg -n "hero-kenburns|dx-num|glass|backdrop-filter|translateY\(-|linear-gradient|radial-gradient|HOT|đã xác minh|phổ biến nhất|travel time|thời gian di chuyển" web-nuxt/pages/index.vue web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/components/home/HomeDecisionLedger.vue web-nuxt/components/home/HomeCategoryIndex.vue web-nuxt/assets/css/home-nocturne.css
rg -n "data-home-pilot=\"nocturne-b1\"|home-nocturne.css" web-nuxt/pages/index.vue
```

Expected: no prohibited implementation result. Existing legacy gradient strings used only by untouched non-pilot image descriptors must be reviewed manually and documented; do not broaden cleanup beyond B1. Confirm rollback is limited to reverting Tasks 2–4 or removing the three component imports/usages and the page-only CSS import; API, shell, auth, location, trust, and shared Plan A tokens remain untouched.

- [x] **Step 5: Truth-sync documentation and final guard**

After every automated and visual row passes:

- Set the design spec status to `implemented-and-verified`.
- Add `> **STATUS: DONE — 2026-07-31.**` below this plan title.
- Check every completed task/step checkbox.
- Record commit IDs, test command results, build result, preview URL/port, browser matrix, screenshot paths, reviewer outcomes, and any `404 No active credentials` review-provider failure in `report.md`.
- Record the final `home.md` object hash and assert it is still `b694ac09ede89442c8af48e193534f0fd25ee3a4`.

- [x] **Step 6: Commit only closure evidence**

```powershell
Set-Location C:\Code\vinhlong360
$homeBriefHash = (git hash-object -- 'design-system/vinhlong360/pages/home.md').Trim()
if ($homeBriefHash -ne 'b694ac09ede89442c8af48e193534f0fd25ee3a4') { throw "home.md changed before B1 closure: $homeBriefHash" }
git diff --check -- docs/superpowers/qa/2026-07-31-homepage-b1/report.md docs/superpowers/plans/2026-07-31-homepage-existing-screen-evolution.md docs/superpowers/specs/2026-07-31-homepage-existing-screen-evolution-design.md
git add docs/superpowers/qa/2026-07-31-homepage-b1 docs/superpowers/plans/2026-07-31-homepage-existing-screen-evolution.md docs/superpowers/specs/2026-07-31-homepage-existing-screen-evolution-design.md
git commit -m "docs: close homepage nocturne pilot"
```

Expected: closure commit contains only B1 documentation, screenshots, and verification evidence; parallel-session artifacts remain unstaged.

## Execution Handoff

The previously approved execution mode remains **Subagent-Driven**: a fresh implementer handles each task, followed by independent spec-compliance and code-quality reviews before the next task begins. Task 1 starts only after this plan commit is clean and the `home.md` guard still matches.
