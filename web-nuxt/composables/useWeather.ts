/**
 * useWeather — đọc `GET /weather` cho MỘT điểm đo và phân loại độ tin cậy của con số
 * TRƯỚC khi giao cho giao diện.
 *
 * Lý do composable này tồn tại (đọc kỹ trước khi sửa):
 *
 * Backend `get_weather()` (agent/realtime.py:69-184) có ba nhánh nhưng CHỈ MỘT mã trả về.
 * Khi thiếu `WEATHER_API_KEY` (:86-87), khi upstream trả != 200 (:106-107), hoặc khi có bất
 * kỳ exception nào (:129-137), nó trả `_fallback_weather()` (:163-184) — một payload ĐỦ MỌI
 * FIELD mà widget thời tiết sẽ render: `temp_c: 28`, `humidity: 80`, `description: "mưa rào"`,
 * `icon: "10d"`. Những giá trị đó là HẰNG SỐ CỨNG theo THÁNG, không phải số đo, và giống hệt
 * nhau cho mọi điểm đo. HTTP luôn 200 (agent/server.py:4782-4786), không có mã lỗi nào.
 *
 * Dấu hiệu phân biệt DUY NHẤT là key `fallback: true` (realtime.py:182). Nhánh đo thật
 * (realtime.py:110-122) KHÔNG có key này — **vắng mặt**, chứ không phải `fallback: false`.
 * ⇒ Chỉ được kiểm tra theo hướng truthy. Viết `if (payload.fallback === false)` là sai và sẽ
 * làm dữ liệu dự phòng đi thẳng vào nhánh "đo thật".
 *
 * Bind thẳng `temp_c` vào template mà quên `fallback` = hiển thị hằng số bịa như thể là
 * nhiệt độ đo được → vi phạm CLAUDE.md §1.7 (không khai khống). Đó là lý do file này KHÔNG
 * export payload thô: nó chỉ export `WeatherReading` đã gắn `status`, và ở trạng thái không
 * phải `measured` thì mọi trường số đều là `null` — giao diện không có gì để lỡ tay render.
 */

import { apiFetch } from '~/utils/apiFetch'

/**
 * Điểm đo duy nhất được dùng.
 *
 * CLAUDE.md §1.6: từ 07/2025 chỉ còn MỘT tỉnh Vĩnh Long (2 cấp: tỉnh → 124 xã/phường).
 * Backend vẫn khai `AREA_COORDS` theo ba tên tỉnh CŨ — `vinh-long` / `ben-tre` / `tra-vinh`
 * (agent/realtime.py:54-58) — và `GET /weather/all` (agent/server.py:4788-4792) trả cả ba kèm
 * `area_name` là "Bến Tre" / "Trà Vinh". Đó là các đơn vị hành chính KHÔNG CÒN TỒN TẠI.
 *
 * Hai quyết định kéo theo:
 *  1. KHÔNG BAO GIỜ gọi `/weather/all`, và không gọi `area=ben-tre` / `area=tra-vinh`.
 *  2. KHÔNG hiển thị `area_name` do API trả về. Nhãn địa bàn là hằng số của frontend
 *     (`LABEL` dưới đây). "Vĩnh Long" ở đây là tên tỉnh HIỆN TẠI nên hợp lệ; nhưng toạ độ
 *     10.2537/105.9722 là MỘT điểm (trung tâm tỉnh lỵ), không phải trung bình 124 xã/phường
 *     — nên nhãn nói "điểm đo", không nói "toàn tỉnh".
 */
export const WEATHER_MEASURE_POINT = Object.freeze({
  /** Khoá `area` gửi lên API. Là slug nội bộ của backend, không phải nhãn hiển thị. */
  area: 'vinh-long',
  /** Nhãn hiển thị — hằng số FE, KHÔNG lấy từ `area_name` của API. */
  label: 'điểm đo trung tâm Vĩnh Long',
} as const)

/**
 * Ba trạng thái, tách bạch để giao diện không thể nhập nhèm:
 *
 *  - `measured`  — số đo thật từ upstream. Được phép hiện số.
 *  - `estimated` — backend chỉ có đường dự phòng theo mùa (`fallback: true`). Giao diện PHẢI
 *                  nói rõ đây không phải số đo. Mọi trường số ở trạng thái này là `null` —
 *                  xem ghi chú "vì sao không hiện số" ở `EMPTY_READING`.
 *  - `unavailable` — không lấy được gì (lỗi mạng, timeout, 503, payload lạ). Giao diện ẨN HẲN.
 */
export type WeatherStatus = 'measured' | 'estimated' | 'unavailable'

export interface WeatherReading {
  status: WeatherStatus
  /** °C. Chỉ khác `null` khi `status === 'measured'`. */
  tempC: number | null
  /** °C cảm giác. Chỉ khác `null` khi `status === 'measured'`. */
  feelsLikeC: number | null
  /** %. Chỉ khác `null` khi `status === 'measured'`. */
  humidity: number | null
  /** m/s. Chỉ khác `null` khi `status === 'measured'`. */
  windSpeedMs: number | null
  /** Mô tả trời bằng tiếng Việt của upstream. Chỉ khác `null` khi `status === 'measured'`. */
  description: string | null
  /** Tên icon cho `<IconLine>`. Ở trạng thái không đo được là icon trung tính. */
  iconName: string
  /** Thời điểm backend ghi số đo (từ `_ts`). Cho phép người đọc tự đánh giá độ cũ. */
  observedAt: Date | null
}

/** Reading rỗng — dùng chung cho `estimated` và `unavailable`. */
function emptyReading(status: WeatherStatus): WeatherReading {
  return {
    status,
    // Vì sao `estimated` cũng để null hết: payload dự phòng CÓ đủ số (28°C / 80% / "mưa rào"),
    // nhưng chúng là hằng số theo tháng chứ không phải quan trắc. Kể cả có dán nhãn, một con
    // số "28°C" đứng trên trang chủ vẫn được đọc như số đo — ảnh chụp màn hình, người lướt
    // nhanh, trình đọc màn hình đều mất phần chú thích. §1.7 nói không khai khống, nên cách
    // an toàn tuyệt đối là không chở số ra khỏi composable này. Giao diện chỉ nhận được
    // `status: 'estimated'` và tự nói bằng lời rằng chưa có nguồn đo.
    tempC: null,
    feelsLikeC: null,
    humidity: null,
    windSpeedMs: null,
    description: null,
    // KHÔNG dùng glyph thời tiết ở đây. Một hình đám mây đặt ngay dưới tiêu đề
    // "Thời tiết hôm nay" bị đọc như một mô tả trời ("nhiều mây") — và đó là kênh
    // phi-chữ mà câu đính chính bằng chữ bên dưới không phủ được: ảnh chụp màn hình,
    // người lướt nhanh, thumbnail chia sẻ đều giữ lại hình mà mất phần chữ.
    // `circle-help` nói đúng thứ đang có: chưa biết. (IconLine.vue cũng dùng chính
    // tên này làm fallback cho icon lạ, nên chắc chắn tồn tại.)
    iconName: 'circle-help',
    observedAt: null,
  }
}

export const UNAVAILABLE_READING: WeatherReading = Object.freeze(emptyReading('unavailable'))

/**
 * Mã icon OpenWeatherMap → tên icon trong `components/IconLine.vue`.
 * `13` (tuyết) không xảy ra ở Vĩnh Long nhưng vẫn map để không rơi vào dấu "?" của
 * IconLine (IconLine.vue:84 fallback tên lạ về `circle-help`).
 */
const OWM_ICON_TO_LINE_ICON: Record<string, string> = {
  '01d': 'sun', '01n': 'moon',
  '02d': 'cloud-sun', '02n': 'cloud-moon',
  '03d': 'cloud', '03n': 'cloud',
  '04d': 'cloud', '04n': 'cloud',
  '09d': 'cloud-rain', '09n': 'cloud-rain',
  '10d': 'cloud-rain', '10n': 'cloud-rain',
  '11d': 'cloud-lightning', '11n': 'cloud-lightning',
  '13d': 'cloud', '13n': 'cloud',
  '50d': 'haze', '50n': 'haze',
}

export function weatherIconName(owmIcon: unknown): string {
  if (typeof owmIcon !== 'string') return 'cloud'
  return OWM_ICON_TO_LINE_ICON[owmIcon] || 'cloud'
}

/** Gợi ý accent theo trời — `river` khi có mưa, `amber` khi nắng, còn lại trung tính. */
export function weatherAccent(reading: WeatherReading): 'river' | 'amber' | 'neutral' {
  if (reading.status !== 'measured') return 'neutral'
  if (reading.iconName === 'cloud-rain' || reading.iconName === 'cloud-lightning') return 'river'
  if (reading.iconName === 'sun') return 'amber'
  return 'neutral'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Số hữu hạn thật sự. Chuỗi `"28"` KHÔNG được coi là số — thà ẩn còn hơn hiện bừa. */
function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function trimmedText(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const text = value.trim()
  return text ? text : null
}

/** `_ts` là epoch giây (float) do backend ghi ở realtime.py:121. */
function observedAtFrom(value: unknown): Date | null {
  const seconds = finiteNumber(value)
  if (seconds === null || seconds <= 0) return null
  const date = new Date(seconds * 1000)
  return Number.isNaN(date.getTime()) ? null : date
}

/**
 * Hàm thuần — toàn bộ luật §1.7 nằm ở đây, không dính mạng, test trực tiếp được.
 */
export function classifyWeather(payload: unknown): WeatherReading {
  if (!isRecord(payload)) return emptyReading('unavailable')

  // (b) Đường dự phòng theo mùa. Kiểm tra TRƯỚC mọi thứ khác, và kiểm tra theo hướng
  //     truthy — nhánh đo thật không có key này nên `=== false` sẽ không bao giờ đúng.
  if (payload.fallback) return emptyReading('estimated')

  // (a) Đường đo thật. `temp_c` là điều kiện cần: payload rỗng `{}`, lỗi đã parse thành JSON,
  //     hay bất kỳ hình dạng lạ nào đều không có nó → rơi xuống (c) chứ không render khung rỗng.
  const tempC = finiteNumber(payload.temp_c)
  if (tempC === null) return emptyReading('unavailable')

  return {
    status: 'measured',
    tempC,
    feelsLikeC: finiteNumber(payload.feels_like_c),
    humidity: finiteNumber(payload.humidity),
    windSpeedMs: finiteNumber(payload.wind_speed_ms),
    description: trimmedText(payload.description),
    iconName: weatherIconName(payload.icon),
    observedAt: observedAtFrom(payload._ts),
  }
}

/**
 * Backend cache 30 phút (`WEATHER_CACHE_TTL = 1800`, agent/realtime.py:37). Gọi lại sớm hơn
 * mốc này chỉ tốn round-trip mà nhận đúng bản cũ, nên client giữ lại kết quả trong 10 phút
 * qua các lần điều hướng SPA. `refresh()` thủ công vẫn đi thẳng, không qua cache.
 */
const CLIENT_CACHE_TTL_MS = 10 * 60 * 1000
const ASYNC_DATA_KEY = 'weather-vinh-long'

let lastResolvedAt = 0

/** Chỉ dùng trong test — xoá mốc cache giữa các case. */
export function resetWeatherCacheClock() {
  lastResolvedAt = 0
}

export function useWeather() {
  const { captureClientError } = useClientError()

  const { data, pending, error, refresh } = useAsyncData<WeatherReading>(
    ASYNC_DATA_KEY,
    async () => {
      const payload = await apiFetch<unknown>(`/weather?area=${WEATHER_MEASURE_POINT.area}`)
      lastResolvedAt = Date.now()
      return classifyWeather(payload)
    },
    {
      // Hiệu năng — SSR KHÔNG chờ API thời tiết.
      // `server: false` là cách duy nhất chắc chắn: `lazy: true` vẫn để Nuxt gom promise vào
      // payload SSR. Đổi lại, dải chỉ xuất hiện sau hydrate. Chi phí CLS gần như bằng 0 vì
      // hero cao `min(52rem, 100svh - header)` (assets/css/home-nocturne.css:20) nên dải nằm
      // ngay DƯỚI fold ở lần vẽ đầu — dịch chuyển ngoài viewport không tính vào CLS.
      // Đồng thời tránh luôn hydration mismatch: SSR và lần render client đầu tiên đều là
      // `unavailable` → cùng một cây DOM.
      server: false,
      lazy: true,
      default: () => UNAVAILABLE_READING,
      getCachedData(key, nuxtApp, ctx) {
        // Chỉ tái dùng khi vào lại trang; `refresh()` / watch luôn gọi thật.
        if (ctx?.cause && ctx.cause !== 'initial') return undefined
        if (!lastResolvedAt || Date.now() - lastResolvedAt > CLIENT_CACHE_TTL_MS) return undefined
        const cached = nuxtApp?.payload?.data?.[key] ?? nuxtApp?.static?.data?.[key]
        return (cached as WeatherReading | undefined) ?? undefined
      },
    },
  )

  // KHÔNG nuốt lỗi im lặng. `useAsyncData` giữ lỗi trong `error` và đặt `data` về default
  // (`unavailable`) nên giao diện tự ẩn; nhưng im lặng hoàn toàn thì endpoint chết cũng
  // không ai biết. `captureClientError` đã dedupe theo (message::error) và cap 20 lỗi/phiên
  // (composables/useClientError.ts:17,60) nên một backend chết không sinh vòng lặp gửi lỗi.
  watch(error, (err) => {
    if (!err) return
    captureClientError('weather.fetch_failed', err, { area: WEATHER_MEASURE_POINT.area })
  }, { immediate: true })

  const reading = computed<WeatherReading>(() => data.value ?? UNAVAILABLE_READING)
  const status = computed<WeatherStatus>(() => reading.value.status)
  /** Chỉ đúng khi đã có kết luận — dùng để giao diện không nhấp nháy lúc đang tải. */
  const settled = computed(() => !pending.value)

  return { reading, status, pending, settled, error, refresh }
}
