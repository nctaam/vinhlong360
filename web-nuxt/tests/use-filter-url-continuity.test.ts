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

it('restores bound filters when browser history changes the incoming route', async () => {
  const wrapper = await mountSuspended(FilterHost, { route: '/du-lich?vung=vinh-long' })
  expect(wrapper.get('[data-area]').text()).toBe('vinh-long')

  await wrapper.vm.$router.push('/du-lich?vung=ben-tre')
  await nextTick()

  expect(wrapper.get('[data-area]').text()).toBe('ben-tre')
})
