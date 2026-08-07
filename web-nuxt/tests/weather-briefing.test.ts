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

/** Payload dự phòng đo thật từ `GET /weather?area=vinh-long` (không có WEATHER_API_KEY). */
const FALLBACK_PAYLOAD = {
  area: 'vinh-long',
  area_name: 'Vĩnh Long',
  temp_c: 28,
  feels_like_c: 32,
  humidity: 80,
  description: 'mưa rào',
  icon: '10d',
  wind_speed_ms: 3.0,
  rain_mm: 5,
  suggestion: '🌧 Mùa mưa — nên mang áo mưa, chọn hoạt động trong nhà buổi chiều',
  fallback: true,
  _ts: 1786107942.999447,
}

/** Nhánh đo thật theo agent/realtime.py:110-122 — KHÔNG có key `fallback`. */
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
  suggestion: '☀️ Trời nắng nóng — nên đội nón, uống nhiều nước',
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

describe('HomeLocalBriefing — (a) có số đo thật', () => {
  it('hiện số, mô tả trời và dòng nguồn có mốc giờ đo', async () => {
    apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
    const wrapper = await mountBriefing()

    const strip = wrapper.get('[data-weather-status]')
    expect(strip.attributes('data-weather-status')).toBe('measured')
    expect(strip.text()).toContain('31,4°C')
    expect(strip.text()).toContain('mây cụm')
    expect(strip.text()).toContain('Ẩm 74%')
    expect(strip.text()).toContain('Gió 2,6 m/s')
    expect(strip.text()).toContain('Nguồn: OpenWeatherMap')
    // "lấy lúc" chứ không phải "đo lúc": mốc giờ là lúc backend NHẬN response
    // (agent/realtime.py:121), không phải lúc quan trắc. Xem comment ở
    // HomeLocalBriefing.vue. Chốt luôn chiều ngược lại để không ai đổi lại.
    expect(strip.text()).toMatch(/lấy lúc \d{2}:\d{2}/)
    expect(strip.text()).not.toContain('đo lúc')
    // KHÔNG được dán nhãn ước lượng lên số đo thật.
    expect(strip.text()).not.toContain('Ước theo mùa')
  })

  it('gọi đúng một điểm đo và KHÔNG bao giờ gọi /weather/all (§1.6)', async () => {
    apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
    await mountBriefing()

    expect(apiFetchMock).toHaveBeenCalledTimes(1)
    expect(apiFetchMock).toHaveBeenCalledWith('/weather?area=vinh-long')
    for (const call of apiFetchMock.mock.calls) {
      expect(String(call[0])).not.toContain('/weather/all')
      expect(String(call[0])).not.toContain('ben-tre')
      expect(String(call[0])).not.toContain('tra-vinh')
    }
  })

  it('không in tên đơn vị hành chính đã bỏ, kể cả khi API trả về (§1.6)', async () => {
    // API dội lại `area_name`; nếu điểm đo bị đổi sang tên tỉnh cũ thì UI vẫn phải câm.
    apiFetchMock.mockResolvedValue({ ...MEASURED_PAYLOAD, area: 'ben-tre', area_name: 'Bến Tre' })
    const wrapper = await mountBriefing()

    const text = wrapper.get('[data-weather-status]').text()
    expect(text).not.toContain('Bến Tre')
    expect(text).not.toContain('Trà Vinh')
    // Nhãn là hằng số FE: nói "điểm đo", không ngụ ý phủ 124 xã/phường.
    expect(text).toContain('điểm đo trung tâm Vĩnh Long')
    expect(text).not.toContain('toàn tỉnh')
  })

  it('tô accent theo trời chỉ khi có số đo', async () => {
    apiFetchMock.mockResolvedValue({ ...MEASURED_PAYLOAD, icon: '10d' })
    const wrapper = await mountBriefing()
    expect(wrapper.get('[data-weather-status]').attributes('data-material-accent')).toBe('river')
  })
})

describe('HomeLocalBriefing — (b) chỉ có dữ liệu dự phòng theo mùa', () => {
  it('hiện khối, nói rõ bằng lời rằng đây không phải số đo', async () => {
    apiFetchMock.mockResolvedValue(FALLBACK_PAYLOAD)
    const wrapper = await mountBriefing()

    const strip = wrapper.get('[data-weather-status]')
    expect(strip.attributes('data-weather-status')).toBe('estimated')
    expect(strip.text()).toContain('Ước theo mùa, chưa nối được dịch vụ đo')
    expect(strip.text()).toContain('không phải số đo thực tế')
  })

  it('KHÔNG rò bất kỳ con số / mô tả trời nào của payload dự phòng', async () => {
    apiFetchMock.mockResolvedValue(FALLBACK_PAYLOAD)
    const wrapper = await mountBriefing()

    const text = wrapper.get('[data-weather-status]').text()
    // Đây là các hằng số cứng theo tháng ở agent/realtime.py:170-184 — render chúng
    // như số đo là vi phạm §1.7.
    expect(text).not.toContain('28')
    expect(text).not.toContain('°C')
    expect(text).not.toContain('80%')
    expect(text).not.toContain('m/s')
    expect(text).not.toContain('mưa rào')
    // Cũng không được mượn chuỗi `suggestion` của backend (chuỗi đó chứa emoji cứng).
    expect(text).not.toContain('áo mưa')
    expect(text).not.toMatch(/[\u{1F300}-\u{1FAFF}☀-➿]/u)
  })

  it('giữ accent trung tính, không mượn màu trời mưa', async () => {
    apiFetchMock.mockResolvedValue(FALLBACK_PAYLOAD)
    const wrapper = await mountBriefing()
    expect(wrapper.get('[data-weather-status]').attributes('data-material-accent')).toBe('neutral')
  })

  it('vẫn dẫn người đọc sang lịch mùa vụ', async () => {
    apiFetchMock.mockResolvedValue(FALLBACK_PAYLOAD)
    const wrapper = await mountBriefing()
    const link = wrapper.get('a')
    expect(link.attributes('href')).toMatch(/^\/theo-mua\?mua=(1[0-2]|[1-9])$/)
  })
})

describe('HomeLocalBriefing — (c) không lấy được gì', () => {
  it('lỗi mạng: ẩn hẳn khối, không khung rỗng, không số giả', async () => {
    apiFetchMock.mockRejectedValue(new Error('fetch failed'))
    const wrapper = await mountBriefing()

    expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
    expect(wrapper.find('.home-local-briefing').exists()).toBe(false)
    expect(wrapper.text().trim()).toBe('')
  })

  it('503 (HAS_REALTIME=false) cũng ẩn hẳn', async () => {
    const err = Object.assign(new Error('Realtime module not available'), { statusCode: 503 })
    apiFetchMock.mockRejectedValue(err)
    const wrapper = await mountBriefing()
    expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
  })

  it('payload rỗng `{}` rơi vào (c), không phải (a)', async () => {
    apiFetchMock.mockResolvedValue({})
    const wrapper = await mountBriefing()
    expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
  })

  it('KHÔNG nuốt lỗi im lặng — lỗi được báo lên đường thu lỗi client', async () => {
    const failure = new Error('fetch failed')
    apiFetchMock.mockRejectedValue(failure)
    await mountBriefing()

    expect(clientErrorMock).toHaveBeenCalled()
    expect(clientErrorMock.mock.calls[0]![0]).toBe('weather.fetch_failed')
    expect(clientErrorMock.mock.calls[0]![1]).toBeTruthy()
  })

  it('thành công thì không báo lỗi', async () => {
    apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
    await mountBriefing()
    expect(clientErrorMock).not.toHaveBeenCalled()
  })
})

describe('HomeLocalBriefing — API chậm & hiệu năng', () => {
  it('API chậm: không chặn render, khối vắng mặt cho tới khi có kết luận', async () => {
    let release: ((value: unknown) => void) | undefined
    apiFetchMock.mockImplementation(() => new Promise((resolve) => { release = resolve }))

    const wrapper = await mountSuspended(HomeLocalBriefing, { global: { stubs } })
    wrappers.push(wrapper)
    await flushUi()

    // Mount đã hoàn tất dù request còn treo → trang không bị giữ lại chờ thời tiết.
    expect(wrapper.find('[data-weather-status]').exists()).toBe(false)
    expect(wrapper.text().trim()).toBe('')

    release?.(MEASURED_PAYLOAD)
    await flushUi()
    expect(wrapper.get('[data-weather-status]').attributes('data-weather-status')).toBe('measured')
  })

  it('không gọi lại liên tục: rời trang rồi quay lại trong TTL không gọi mạng lần nữa', async () => {
    apiFetchMock.mockResolvedValue(MEASURED_PAYLOAD)
    const first = await mountBriefing()
    expect(apiFetchMock).toHaveBeenCalledTimes(1)

    // Gỡ hẳn component (mô phỏng điều hướng khỏi trang chủ) trước khi mount lại, để phép đo
    // không ăn may nhờ hai instance cùng sống chung một khoá useAsyncData.
    first.unmount()
    wrappers.splice(wrappers.indexOf(first), 1)
    await flushUi()

    const second = await mountBriefing()
    expect(apiFetchMock).toHaveBeenCalledTimes(1)
    expect(second.get('[data-weather-status]').attributes('data-weather-status')).toBe('measured')
  })
})
