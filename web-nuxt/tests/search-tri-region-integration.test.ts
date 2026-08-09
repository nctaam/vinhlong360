import { clearNuxtData } from '#app'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import AISearchAssist from '../components/AISearchAssist.vue'
import EmptyState from '../components/EmptyState.vue'
import SmartRecommendations from '../components/SmartRecommendations.vue'
import SearchPage from '../pages/tim-kiem.vue'
import { useAuth } from '../composables/useAuth'
import { extractNuxtCssPaths } from './helpers/installHomepageStyles'

const searchAllMock = vi.hoisted(() => vi.fn())
const fetchSuggestionsMock = vi.hoisted(() => vi.fn().mockResolvedValue([]))
const navigateToMock = vi.hoisted(() => vi.fn())
const recommendationState = vi.hoisted(() => ({ items: [] as Array<Record<string, unknown>> }))

mockNuxtImport('navigateTo', () => navigateToMock)
vi.mock('../composables/useUnifiedSearch', () => ({
  useUnifiedSearch: () => ({
    searchAll: searchAllMock,
    fetchEntitySuggestions: fetchSuggestionsMock,
    zeroResultRecoveryActions: () => [{ id: 'recent-saved', label: 'Xem mục gần đây và đã lưu', to: '/da-luu' }],
  }),
}))
vi.mock('../composables/useFeature', () => ({
  useFeature: () => ({
    enabled: () => true,
    capabilityMode: () => 'enhanced',
  }),
}))
vi.mock('../composables/useContextualRecommendations', async () => {
  const { ref } = await import('vue')
  return {
    useContextualRecommendations: () => ({
      items: ref([...recommendationState.items]),
      reasons: ref({}),
      profile: ref(null),
      loading: ref(false),
      error: ref(false),
      source: ref('fallback'),
      adaptiveSignals: ref([]),
      priority: ref({ orderedBlocks: [], suggestions: [], reasonCodes: [], reasons: [], primaryCta: 'view', reversible: false, resetAction: null }),
      adaptiveReasonsFor: vi.fn(() => []),
      attentionOwnerScope: ref('scope-guest'),
      attentionVersion: ref(0),
      canShowSuggestion: vi.fn(() => true),
      dismissSuggestion: vi.fn(() => true),
      resetSuggestionSession: vi.fn(),
      refresh: vi.fn(),
    }),
  }
})
vi.mock('../composables/useSiteSettings', () => ({
  useSiteSettings: () => ({
    settings: { value: {} },
    get: (_key: string, fallback: unknown) => fallback,
  }),
}))

const wrappers: Array<{ unmount: () => void }> = []
const stylesheets: HTMLStyleElement[] = []
const semanticTestTokens = {
  '--color-surface-subtle': 'rgb(241, 238, 230)',
  '--color-material-neutral': 'rgb(65, 84, 80)',
  '--color-error': 'rgb(189, 65, 63)',
  '--color-error-rgb': '189, 65, 63',
}
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const pageStubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  SkeletonGrid: { props: ['count'], template: '<div data-skeleton-grid />' },
  SaveButton: true,
  ImageDisclosure: true,
  JourneyActionRail: true,
  MapListSurface: {
    props: ['results', 'selectedId', 'viewport', 'viewportPending', 'mapState'],
    emits: ['viewport-change', 'search-area'],
    template: `<div data-map-list-surface-stub>
      <span v-for="result in results" :key="result.id" :data-search-result-id="result.id">{{ result.name }}</span>
      <button data-search-pan @click="$emit('viewport-change', { center: [105.62, 9.91], zoom: 11 })" />
      <button data-search-commit @click="$emit('search-area', { center: [105.62, 9.91], zoom: 11 })" />
    </div>`,
  },
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}
const componentStubs = {
  NuxtImg: NuxtImgStub,
  SaveButton: true,
  ImageDisclosure: true,
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

type SearchResultSet = {
  entities: Array<Record<string, unknown>>
  posts: Array<Record<string, unknown>>
  users: Array<Record<string, unknown>>
  totals: { entities: number, posts: number, users: number }
}

const emptyResults: SearchResultSet = {
  entities: [],
  posts: [],
  users: [],
  totals: { entities: 0, posts: 0, users: 0 },
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

function extractStyles(source: string): string[] {
  return [...source.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map(match => match[1]!)
}

async function installActualSearchStyles() {
  const workspaceRoot = resolve(import.meta.dirname, '../..')
  const webRoot = resolve(workspaceRoot, 'web-nuxt')
  const config = await readFile(resolve(webRoot, 'nuxt.config.ts'), 'utf8')
  const globalCss = await Promise.all(extractNuxtCssPaths(config).map(file => readFile(resolve(webRoot, 'assets/css', file), 'utf8')))
  const componentCss = await Promise.all([
    'pages/tim-kiem.vue',
    'components/EmptyState.vue',
    'components/AISearchAssist.vue',
    'components/SmartRecommendations.vue',
  ].map(file => readFile(resolve(webRoot, file), 'utf8').then(source => extractStyles(source).join('\n'))))
  const stylesheet = document.createElement('style')
  stylesheet.textContent = [...globalCss, ...componentCss].join('\n')
  document.head.append(stylesheet)
  stylesheets.push(stylesheet)
}

function parsedStylesFor(selectorFragment: string): CSSStyleDeclaration[] {
  return stylesheets.flatMap((stylesheet) => {
    const rules = stylesheet.sheet ? [...stylesheet.sheet.cssRules] : []
    return rules
      .filter((rule): rule is CSSStyleRule => rule.type === CSSRule.STYLE_RULE)
      .filter(rule => rule.selectorText.includes(selectorFragment))
      .map(rule => rule.style)
  })
}

function searchHost(child: ReturnType<typeof h>) {
  return defineComponent({
    setup: () => () => h('main', {
      'data-color-system': 'tri-region-v1',
      'data-page-recipe': 'search',
      'data-material-accent': 'neutral',
    }, [child]),
  })
}

beforeEach(() => {
  searchAllMock.mockReset().mockResolvedValue(emptyResults)
  fetchSuggestionsMock.mockReset().mockResolvedValue([])
  navigateToMock.mockReset()
  recommendationState.items = []
  localStorage.clear()
  sessionStorage.clear()
  document.documentElement.classList.add('light')
  for (const [name, value] of Object.entries(semanticTestTokens)) {
    document.documentElement.style.setProperty(name, value)
  }
})

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  for (const stylesheet of stylesheets.splice(0)) stylesheet.remove()
  document.documentElement.classList.remove('light', 'dark')
  for (const name of Object.keys(semanticTestTokens)) {
    document.documentElement.style.removeProperty(name)
  }
  vi.useRealTimers()
  await clearNuxtData()
})

it('replaces inherited catalog decoration and renders a real Coral error state', async () => {
  await installActualSearchStyles()
  searchAllMock.mockRejectedValue(new Error('search unavailable'))
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    attachTo: document.body,
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const heroStyle = getComputedStyle(wrapper.get<HTMLElement>('.search-hero').element)
  expect(heroStyle.backgroundImage).not.toContain('gradient')
  expect(heroStyle.backgroundColor).toBe('rgb(241, 238, 230)')

  const alert = wrapper.get<HTMLElement>('[data-color-role="status-error"]')
  const alertStyle = getComputedStyle(alert.element)
  expect(alertStyle.borderTopStyle).toBe('solid')
  expect(alertStyle.borderTopColor).toBe('rgb(189, 65, 63)')
  expect(alertStyle.backgroundColor).not.toBe('rgba(0, 0, 0, 0)')
  expect(getComputedStyle(alert.get<HTMLElement>('.empty-title').element).color).toBe('rgb(189, 65, 63)')
  expect(getComputedStyle(alert.get<HTMLElement>('.empty-rule').element).backgroundImage).toBe('none')

  const inputStyle = getComputedStyle(wrapper.get<HTMLInputElement>('input[type="search"]').element)
  expect(inputStyle.borderBottomColor).toBe('rgb(189, 65, 63)')
  expect(inputStyle.boxShadow).toContain('189, 65, 63')
})

it('uses real EmptyState and AISearchAssist with recipe-local neutral decoration', async () => {
  await installActualSearchStyles()
  const emptyWrapper = await mountSuspended(searchHost(h(EmptyState, {
    title: 'Chưa có kết quả',
    message: 'Hãy thử từ khóa khác.',
    colorRecipe: 'tri-region-v1',
  })), { attachTo: document.body })
  wrappers.push(emptyWrapper)

  const empty = emptyWrapper.get<HTMLElement>('.empty-state')
  expect(empty.attributes('data-color-recipe')).toBe('tri-region-v1')
  expect(new Set(empty.findAll('stop').map(stop => stop.attributes('stop-color')))).toEqual(new Set(['var(--color-material-neutral)']))
  const ruleStyle = getComputedStyle(empty.get<HTMLElement>('.empty-rule').element)
  expect(ruleStyle.backgroundImage).toBe('none')
  expect(ruleStyle.backgroundColor).toBe('rgb(65, 84, 80)')

  sessionStorage.setItem('aisearch:gốm', JSON.stringify({ reply: 'Gợi ý địa phương.', suggestions: [] }))
  const aiWrapper = await mountSuspended(searchHost(h(AISearchAssist, {
    query: 'gốm',
    colorRecipe: 'tri-region-v1',
  })), { attachTo: document.body, global: { stubs: componentStubs } })
  wrappers.push(aiWrapper)
  await aiWrapper.get('button').trigger('click')
  await nextTick()

  const assist = aiWrapper.get<HTMLElement>('.ai-search-assist')
  const headingStyle = getComputedStyle(aiWrapper.get<HTMLElement>('.ai-search-h3').element)
  const searchTickStyles = parsedStylesFor('.ai-search-h3::before')
  expect(assist.attributes('data-color-recipe')).toBe('tri-region-v1')
  expect(headingStyle.borderLeftColor).toBe('rgb(65, 84, 80)')
  expect(searchTickStyles.some(style => style.content === 'none' && style.backgroundImage === 'none')).toBe(true)
})

it('propagates the Search recipe through real SmartRecommendations and EntityCard', async () => {
  recommendationState.items = [{
    id: 'craft-rec-1',
    type: 'craft_village',
    name: 'Gốm đỏ Mang Thít',
    quality: { source_tier: 'official' },
  }]
  const wrapper = await mountSuspended(searchHost(h(SmartRecommendations, {
    context: 'search',
    title: 'Gợi ý tiếp theo',
    colorRecipe: 'tri-region-v1',
  })), { global: { stubs: componentStubs } })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.get('.smart-rec').attributes('data-color-recipe')).toBe('tri-region-v1')
  expect(wrapper.get('.card').attributes('data-color-recipe')).toBe('tri-region-v1')
  expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
})

it('submits once while preserving canonical intent, filters, area and viewport', async () => {
  const filters = encodeURIComponent(JSON.stringify({ type: ['craft_village'] }))
  searchAllMock.mockResolvedValue({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít', coordinates: { lat: 10.23, lng: 105.56 } }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })
  const wrapper = await mountSuspended(SearchPage, {
    route: `/tim-kiem?q=g%E1%BB%91m&intent=place&area=vinh-long&filters=${filters}&viewport=11/1624/965`,
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()
  const pushState = vi.spyOn(window.history, 'pushState')

  await wrapper.get('[data-search-pan]').trigger('click')
  await wrapper.get('input[type="search"]').setValue('bưởi Năm Roi')
  await wrapper.get('[data-color-role="action-primary"]').trigger('click')
  expect(navigateToMock).toHaveBeenCalledTimes(1)
  const target = new URL(String(navigateToMock.mock.calls[0]?.[0]), 'https://vinhlong360.local')
  expect(target.pathname).toBe('/tim-kiem')
  expect(target.searchParams.get('q')).toBe('bưởi Năm Roi')
  expect(target.searchParams.get('intent')).toBe('place')
  expect(target.searchParams.get('area')).toBe('vinh-long')
  expect(JSON.parse(target.searchParams.get('filters') || '{}')).toEqual({ type: ['craft_village'] })
  expect(target.searchParams.get('viewport')).toBe('11/1624/965')
  expect(pushState).not.toHaveBeenCalled()
  pushState.mockRestore()
})

it('records the safe serialized search return path in the guest Journey Thread', async () => {
  searchAllMock.mockResolvedValue({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít' }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=gốm&intent=place&area=vinh-long',
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const stored = JSON.parse(sessionStorage.getItem('vl360:journey-thread:v1') || 'null')
  expect(stored).toEqual(expect.objectContaining({
    intent: 'explore',
    returnPath: '/tim-kiem?intent=place&area=vinh-long&q=g%E1%BB%91m',
    currentPath: '/tim-kiem?intent=place&area=vinh-long&q=g%E1%BB%91m',
  }))
  expect(JSON.stringify(stored)).not.toMatch(/10\.25|105\.97|203\.0\.113|auth|user-/i)
})

it('re-snapshots the same canonical search URL when the auth owner changes without remounting', async () => {
  searchAllMock.mockResolvedValue({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít' }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=gốm&intent=place&area=vinh-long',
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const auth = useAuth()
  const guestOwnerScope = JSON.parse(sessionStorage.getItem('vl360:journey-thread:v1') || 'null')?.ownerScope
  auth.user.value = { id: 'round2-account-a' }
  await flushUi()

  const stored = JSON.parse(sessionStorage.getItem('vl360:journey-thread:v1') || 'null')
  expect(stored.ownerScope).not.toBe(guestOwnerScope)
  expect(stored).toEqual(expect.objectContaining({
    intent: 'explore',
    returnPath: '/tim-kiem?intent=place&area=vinh-long&q=g%E1%BB%91m',
    currentPath: '/tim-kiem?intent=place&area=vinh-long&q=g%E1%BB%91m',
  }))
  expect(stored.ownerScope).not.toContain('round2-account-a')
})

it('adds the coordinated map sibling without changing the existing search response shape', async () => {
  searchAllMock.mockResolvedValue({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít', coordinates: { lat: 10.24, lng: 106.01 }, quality: { source_tier: 'official' } }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.find('[data-map-list-surface-stub]').exists()).toBe(true)
  expect(searchAllMock).toHaveBeenCalledWith('gốm', 100)
})

it('changes search result ids only after the explicit spatial commit', async () => {
  searchAllMock.mockResolvedValue({
    entities: [
      { id: 'near', type: 'craft_village', name: 'Gốm đỏ', coordinates: { lat: 10.24, lng: 106.01 } },
      { id: 'far', type: 'product', name: 'Dừa sáp', coordinates: { lat: 9.91, lng: 105.62 } },
    ],
    posts: [],
    users: [],
    totals: { entities: 2, posts: 0, users: 0 },
  })
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=%C4%91%E1%BA%B7c+s%E1%BA%A3n',
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()
  expect(wrapper.findAll('[data-search-result-id]').map(node => node.attributes('data-search-result-id')).sort()).toEqual(['far', 'near'])

  await wrapper.get('[data-search-pan]').trigger('click')
  expect(wrapper.findAll('[data-search-result-id]').map(node => node.attributes('data-search-result-id')).sort()).toEqual(['far', 'near'])

  await wrapper.get('[data-search-commit]').trigger('click')
  await nextTick()
  expect(wrapper.findAll('[data-search-result-id]').map(node => node.attributes('data-search-result-id'))).toEqual(['far'])
})

it('keeps Arrow, Enter and Escape combobox behavior with aria-activedescendant', async () => {
  fetchSuggestionsMock.mockResolvedValue([
    { id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít' },
    { id: 'place-2', type: 'place', name: 'Chợ gốm' },
  ])
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem',
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const input = wrapper.get('input[type="search"]')
  await input.setValue('gốm')
  await vi.waitFor(() => expect(wrapper.find('[role="listbox"]').exists()).toBe(true), { timeout: 1000 })

  await input.trigger('keydown', { key: 'ArrowDown' })
  expect(input.attributes('aria-activedescendant')).toBe('sug-craft-1')
  expect(wrapper.get('#sug-craft-1').attributes('aria-selected')).toBe('true')

  await input.trigger('keydown', { key: 'Escape' })
  expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
  expect(input.attributes('aria-activedescendant')).toBeUndefined()

  await input.setValue('gốm đỏ')
  await vi.waitFor(() => expect(wrapper.find('[role="listbox"]').exists()).toBe(true), { timeout: 1000 })
  await input.trigger('keydown', { key: 'ArrowDown' })
  await input.trigger('keyup', { key: 'Enter' })
  expect(navigateToMock).toHaveBeenCalledWith('/dia-diem/craft-1')
})

it('retries from error through pending to success and clears aria-invalid', async () => {
  let resolveRetry!: (value: typeof emptyResults) => void
  const retryResult = new Promise<typeof emptyResults>(resolve => { resolveRetry = resolve })
  searchAllMock
    .mockRejectedValueOnce(new Error('search unavailable'))
    .mockImplementationOnce(() => retryResult)

  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    global: { stubs: pageStubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const input = wrapper.get('input[type="search"]')
  expect(input.attributes('aria-invalid')).toBe('true')
  await wrapper.get('[role="alert"] button').trigger('click')
  await vi.waitFor(() => expect(searchAllMock).toHaveBeenCalledTimes(2))
  await vi.waitFor(() => expect(wrapper.find('[data-skeleton-grid]').exists()).toBe(true))
  expect(input.attributes('aria-invalid')).toBeUndefined()

  resolveRetry({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít', quality: { source_tier: 'official' } }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })
  await vi.waitFor(() => expect(wrapper.text()).toContain('Gốm đỏ Mang Thít'))
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(input.attributes('aria-invalid')).toBeUndefined()
})
