import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HomeLocalBriefing from '../components/home/HomeLocalBriefing.vue'
import { resetWeatherCacheClock } from '../composables/useWeather'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const clientErrorMock = vi.hoisted(() => vi.fn())
vi.mock('../composables/useClientError', () => ({
  captureClientError: clientErrorMock,
  installGlobalErrorCapture: () => {},
  useClientError: () => ({ captureClientError: clientErrorMock, installGlobalErrorCapture: () => {} }),
}))

const wrappers: Array<{ unmount: () => void }> = []

const NuxtLinkStub = defineComponent({
  props: { to: { type: String, required: true } },
  setup(props, { slots }) {
    return () => h('a', { href: props.to }, slots.default?.())
  },
})

const stubs = { NuxtLink: NuxtLinkStub }

const MEASURED_PAYLOAD = {
  area: 'vinh-long',
  area_name: 'Vĩnh Long',
  temp_c: 31.4,
  feels_like_c: 38.2,
  humidity: 74,
  description: 'mây cụm',
  icon: '03d',
  wind_speed_ms: 2.6,
  rain_mm: 0,
  _ts: 1786107942.999447,
}

const FALLBACK_PAYLOAD = {
  area: 'vinh-long',
  area_name: 'Vĩnh Long',
  temp_c: 28,
  humidity: 80,
  description: 'mưa rào',
  icon: '10d',
  wind_speed_ms: 3.0,
  fallback: true,
  _ts: 1786107942.999447,
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

async function mountBriefing() {
  const wrapper = await mountSuspended(HomeLocalBriefing, { global: { stubs } })
  wrappers.push(wrapper)
  await flushUi()
  return wrapper
}

beforeEach(() => {
  apiFetchMock.mockReset()
  clientErrorMock.mockReset()
  resetWeatherCacheClock()
})

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  await clearNuxtData()
})

describe('HomeLocalBriefing — Empirical Stress Testing', () => {
  describe('Adverse Scenario 1: Reading status is unavailable', () => {
    it('collapses gracefully without crashing or throwing when network fails', async () => {
      apiFetchMock.mockRejectedValue(new Error('Network offline'))
      const wrapper = await mountBriefing()

      expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
      expect(wrapper.find('.home-local-briefing').exists()).toBe(false)
      expect(wrapper.text().trim()).toBe('')
    })

    it('collapses gracefully on HTTP 503 service unavailable', async () => {
      const err = Object.assign(new Error('Service Unavailable'), { statusCode: 503 })
      apiFetchMock.mockRejectedValue(err)
      const wrapper = await mountBriefing()

      expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
      expect(wrapper.text().trim()).toBe('')
    })

    it('collapses gracefully on corrupt/empty payload `{}` without throwing', async () => {
      apiFetchMock.mockResolvedValue({})
      const wrapper = await mountBriefing()

      expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
      expect(wrapper.text().trim()).toBe('')
    })

    it('collapses gracefully when payload is null or unexpected primitive', async () => {
      apiFetchMock.mockResolvedValue(null)
      const wrapper = await mountBriefing()

      expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
      expect(wrapper.text().trim()).toBe('')
    })
  })

  describe('Adverse Scenario 2: Tide phase computation & badge integration', () => {
    it('renders MekongWaterBadge and tide cycle information accurately when available', async () => {
      apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
      const wrapper = await mountBriefing()

      const tideSection = wrapper.find('.home-local-briefing__tide')
      expect(tideSection.exists()).toBe(true)
      expect(tideSection.attributes('data-tide-phase')).toMatch(/^(rong|kem|chuyen)$/)
      expect(tideSection.attributes('data-lunar-day')).toBeDefined()

      const tideBadge = wrapper.get('.home-local-briefing__tide-badge')
      expect(tideBadge.text()).toMatch(/^Kỳ Nước (rong|kém|chuyển)$/)

      const mwb = wrapper.find('[data-water-badge]')
      expect(mwb.exists()).toBe(true)
      expect(mwb.attributes('data-tide-state')).toMatch(/^(rong|kem|chuyen)$/)
    })
  })

  describe('Adverse Scenario 3: Template integrity & escaping', () => {
    it('contains zero unescaped HTML and renders clean text interpolations', async () => {
      apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
      const wrapper = await mountBriefing()

      const html = wrapper.html()
      expect(html).not.toContain('&lt;script')
      expect(html).not.toContain('{{')
      expect(html).not.toContain('}}')
      expect(html).not.toContain('NaN')
      expect(html).not.toContain('undefined')
      expect(html).not.toContain('null')
    })
  })

  describe('Adverse Scenario 4: Touch targets and ergonomics', () => {
    it('ensures season link satisfies touch target standard with min-height token', async () => {
      apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
      const wrapper = await mountBriefing()

      const link = wrapper.find('.home-local-briefing__link')
      expect(link.exists()).toBe(true)
      expect(link.attributes('href')).toMatch(/^\/theo-mua\?mua=[1-9][0-2]?$/)
    })
  })
})
