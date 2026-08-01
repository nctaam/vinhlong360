import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SearchPage from '../pages/tim-kiem.vue'

const searchAllMock = vi.hoisted(() => vi.fn())
const fetchSuggestionsMock = vi.hoisted(() => vi.fn().mockResolvedValue([]))
vi.mock('../composables/useUnifiedSearch', () => ({
  useUnifiedSearch: () => ({
    searchAll: searchAllMock,
    fetchEntitySuggestions: fetchSuggestionsMock,
  }),
}))

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})
const stubs = {
  NuxtImg: NuxtImgStub,
  Breadcrumb: true,
  EmptyState: { props: ['title', 'message'], template: '<div data-empty-state><strong>{{ title }}</strong><span>{{ message }}</span><slot name="actions" /></div>' },
  SkeletonGrid: true,
  SaveButton: true,
  ImageDisclosure: true,
  SmartRecommendations: true,
  JourneyActionRail: true,
  IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

beforeEach(() => {
  searchAllMock.mockReset()
  fetchSuggestionsMock.mockClear()
  localStorage.clear()
})
afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})

it('shows semantic search state and source labels for real results', async () => {
  searchAllMock.mockResolvedValue({
    entities: [{ id: 'craft-1', type: 'craft_village', name: 'Gốm đỏ Mang Thít', quality: { source_tier: 'official' } }],
    posts: [],
    users: [],
    totals: { entities: 1, posts: 0, users: 0 },
  })

  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    global: { stubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  const root = wrapper.get('[data-page-recipe="search"]')
  expect(root.attributes('data-material-accent')).toBe('neutral')
  expect((wrapper.get('input[type="search"]').element as HTMLInputElement).value).toBe('gốm')
  expect(wrapper.get('[data-color-role="action-primary"]')).toBeTruthy()
  expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
  expect(wrapper.get('[data-material-accent="clay"]').text()).toContain('Gốm đỏ Mang Thít')
})

it('keeps an error visible in text and aria, not only Coral', async () => {
  searchAllMock.mockRejectedValue(new Error('search unavailable'))
  const wrapper = await mountSuspended(SearchPage, {
    route: '/tim-kiem?q=g%E1%BB%91m',
    global: { stubs },
  })
  wrappers.push(wrapper)
  await flushUi()

  expect(wrapper.get('[role="alert"]').text()).toContain('Không thể tìm kiếm')
  expect(wrapper.get('input[type="search"]').attributes('aria-invalid')).toBe('true')
})
