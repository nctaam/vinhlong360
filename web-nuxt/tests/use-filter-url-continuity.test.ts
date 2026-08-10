import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, nextTick, ref } from 'vue'
import { expect, it } from 'vitest'
import { useFilterUrl } from '../composables/useFilterUrl'

const FilterHost = defineComponent({
  setup() {
    const area = ref('all')
    useFilterUrl({ vung: area }, { vung: 'all' })
    return { area }
  },
  template: '<output data-area>{{ area }}</output>',
})

const SearchFilterHost = defineComponent({
  setup() {
    const query = ref('seed')
    useFilterUrl({ q: query }, { q: '' })
    return { query }
  },
  template: '<output data-query>{{ query }}</output>',
})

it('restores bound filters when browser history changes the incoming route', async () => {
  const wrapper = await mountSuspended(FilterHost, { route: '/du-lich?vung=vinh-long' })
  expect(wrapper.get('[data-area]').text()).toBe('vinh-long')

  await wrapper.vm.$router.push('/du-lich?vung=ben-tre')
  await nextTick()

  expect(wrapper.get('[data-area]').text()).toBe('ben-tre')
})

it('preserves an explicit empty-string default instead of inventing an all query', async () => {
  const wrapper = await mountSuspended(SearchFilterHost, { route: '/du-lich' })

  expect(wrapper.get('[data-query]').text()).toBe('')

  wrapper.vm.query = 'gốm'
  await nextTick()
  wrapper.vm.query = ''
  await nextTick()

  expect(wrapper.vm.$route.query.q).toBeUndefined()
})
