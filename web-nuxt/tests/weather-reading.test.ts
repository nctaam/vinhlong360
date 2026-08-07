import { describe, expect, it } from 'vitest'
import {
  WEATHER_MEASURE_POINT,
  classifyWeather,
  weatherAccent,
  weatherIconName,
} from '../composables/useWeather'

/**
 * Fixture đo THẬT từ `GET /weather?area=vinh-long` trên worktree này (không có
 * `WEATHER_API_KEY` trong môi trường ⇒ đây đúng là đường dự phòng). Giữ nguyên văn,
 * kể cả emoji trong `suggestion` và field private `_ts` đang rò ra JSON công khai.
 */
const REAL_FALLBACK_PAYLOAD = {
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

/**
 * Hình dạng nhánh ĐO THẬT, dựng đúng theo `agent/realtime.py:110-122`: cùng bộ field,
 * `_ts` có, và **KHÔNG có key `fallback`** — vắng mặt chứ không phải `false`. Đây là điểm
 * dễ sai nhất của việc này nên nó phải là fixture, không phải mô tả trong comment.
 */
const REAL_MEASURED_PAYLOAD = {
  area: 'vinh-long',
  area_name: 'Vĩnh Long',
  temp_c: 31.4,
  feels_like_c: 38.2,
  humidity: 74,
  description: 'mây cụm',
  icon: '03d',
  wind_speed_ms: 2.6,
  rain_mm: 0,
  suggestion: '☀️ Trời nắng nóng — nên đội nón, uống nhiều nước, tham quan vườn trái cây có bóng mát',
  _ts: 1786107942.999447,
}

describe('classifyWeather — ba trạng thái §1.7', () => {
  it('(a) số đo thật: giữ nguyên số và mốc thời gian đo', () => {
    const reading = classifyWeather(REAL_MEASURED_PAYLOAD)

    expect(reading.status).toBe('measured')
    expect(reading.tempC).toBe(31.4)
    expect(reading.feelsLikeC).toBe(38.2)
    expect(reading.humidity).toBe(74)
    expect(reading.windSpeedMs).toBe(2.6)
    expect(reading.description).toBe('mây cụm')
    expect(reading.iconName).toBe('cloud')
    expect(reading.observedAt?.getTime()).toBe(Math.trunc(1786107942.999447 * 1000))
  })

  it('(b) dự phòng theo mùa: KHÔNG chở bất kỳ con số nào ra khỏi composable', () => {
    const reading = classifyWeather(REAL_FALLBACK_PAYLOAD)

    expect(reading.status).toBe('estimated')
    // Payload có đủ 28°C / 80% / 3.0 m/s / "mưa rào" nhưng tất cả phải bị chặn lại ở đây.
    expect(reading.tempC).toBeNull()
    expect(reading.feelsLikeC).toBeNull()
    expect(reading.humidity).toBeNull()
    expect(reading.windSpeedMs).toBeNull()
    expect(reading.description).toBeNull()
    expect(reading.observedAt).toBeNull()
    // Icon cũng là một khẳng định về trời, chỉ khác là bằng hình. Chặn số mà vẫn vẽ
    // đám mây thì ảnh chụp màn hình vẫn nói "nhiều mây" trong khi không có dữ liệu nào.
    expect(reading.iconName).toBe('circle-help')
    expect(['cloud', 'sun', 'cloud-rain', 'cloud-sun', 'cloud-lightning', 'snowflake'])
      .not.toContain(reading.iconName)
  })

  it('(b) nhận diện fallback theo hướng truthy, không dựa vào `fallback === false`', () => {
    // Nhánh đo thật KHÔNG có key `fallback`; nếu code test `=== false` thì payload dự phòng
    // sẽ lọt sang "measured". Case này khoá đúng hướng so sánh.
    expect(classifyWeather({ ...REAL_FALLBACK_PAYLOAD, fallback: true }).status).toBe('estimated')
    expect('fallback' in REAL_MEASURED_PAYLOAD).toBe(false)
    expect(classifyWeather(REAL_MEASURED_PAYLOAD).status).toBe('measured')
    // Backend tương lai có đánh dấu tường minh `fallback: false` thì vẫn là số đo.
    expect(classifyWeather({ ...REAL_MEASURED_PAYLOAD, fallback: false }).status).toBe('measured')
    // Giá trị truthy lạ (chuỗi lý do chẳng hạn) → nghiêng về phía an toàn: không phải số đo.
    expect(classifyWeather({ ...REAL_FALLBACK_PAYLOAD, fallback: 'no_api_key' }).status).toBe('estimated')
  })

  it('(c) payload rỗng / lạ / không phải object: unavailable, không số nào', () => {
    for (const payload of [{}, null, undefined, [], 'ok', 42, { area: 'vinh-long' }]) {
      const reading = classifyWeather(payload)
      expect(reading.status).toBe('unavailable')
      expect(reading.tempC).toBeNull()
      expect(reading.description).toBeNull()
    }
  })

  it('(c) temp_c dạng chuỗi không được coi là số đo', () => {
    // Thà ẩn còn hơn render một giá trị chưa xác thực kiểu.
    const reading = classifyWeather({ ...REAL_MEASURED_PAYLOAD, temp_c: '31.4' })
    expect(reading.status).toBe('unavailable')
    expect(reading.tempC).toBeNull()
  })

  it('(c) temp_c NaN/Infinity bị loại', () => {
    expect(classifyWeather({ ...REAL_MEASURED_PAYLOAD, temp_c: Number.NaN }).status).toBe('unavailable')
    expect(classifyWeather({ ...REAL_MEASURED_PAYLOAD, temp_c: Number.POSITIVE_INFINITY }).status).toBe('unavailable')
  })

  it('số đo thiếu field phụ vẫn là số đo, field thiếu về null', () => {
    const reading = classifyWeather({ temp_c: 29, icon: '01d', _ts: 1786107942 })
    expect(reading.status).toBe('measured')
    expect(reading.tempC).toBe(29)
    expect(reading.humidity).toBeNull()
    expect(reading.description).toBeNull()
    expect(reading.iconName).toBe('sun')
  })

  it('_ts hỏng thì không bịa mốc đo', () => {
    expect(classifyWeather({ ...REAL_MEASURED_PAYLOAD, _ts: 0 }).observedAt).toBeNull()
    expect(classifyWeather({ ...REAL_MEASURED_PAYLOAD, _ts: 'hôm nay' }).observedAt).toBeNull()
    expect(classifyWeather({ ...REAL_MEASURED_PAYLOAD, _ts: -5 }).observedAt).toBeNull()
  })
})

describe('weatherIconName — phủ hết mã OpenWeatherMap', () => {
  it('map đủ 18 mã, không mã nào rơi về dấu hỏi của IconLine', () => {
    const codes = [
      '01d', '01n', '02d', '02n', '03d', '03n', '04d', '04n', '09d',
      '09n', '10d', '10n', '11d', '11n', '13d', '13n', '50d', '50n',
    ]
    for (const code of codes) {
      expect(weatherIconName(code), code).not.toBe('circle-help')
      expect(weatherIconName(code), code).toBeTruthy()
    }
    expect(weatherIconName('01d')).toBe('sun')
    expect(weatherIconName('01n')).toBe('moon')
    expect(weatherIconName('02d')).toBe('cloud-sun')
    expect(weatherIconName('02n')).toBe('cloud-moon')
    expect(weatherIconName('10n')).toBe('cloud-rain')
    expect(weatherIconName('11d')).toBe('cloud-lightning')
    expect(weatherIconName('50d')).toBe('haze')
  })

  it('mã lạ hoặc thiếu về icon trung tính', () => {
    expect(weatherIconName('99z')).toBe('cloud')
    expect(weatherIconName(undefined)).toBe('cloud')
    expect(weatherIconName(null)).toBe('cloud')
    expect(weatherIconName(7)).toBe('cloud')
  })
})

describe('weatherAccent', () => {
  it('chỉ tô màu khi có số đo thật', () => {
    expect(weatherAccent(classifyWeather({ temp_c: 28, icon: '10d' }))).toBe('river')
    expect(weatherAccent(classifyWeather({ temp_c: 28, icon: '11d' }))).toBe('river')
    expect(weatherAccent(classifyWeather({ temp_c: 33, icon: '01d' }))).toBe('amber')
    expect(weatherAccent(classifyWeather({ temp_c: 30, icon: '03d' }))).toBe('neutral')
    // Dự phòng luôn trung tính — không được mượn màu "trời mưa" để trông như số đo.
    expect(weatherAccent(classifyWeather(REAL_FALLBACK_PAYLOAD))).toBe('neutral')
    expect(weatherAccent(classifyWeather({}))).toBe('neutral')
  })
})

describe('WEATHER_MEASURE_POINT — §1.6', () => {
  it('chỉ dùng một điểm đo, nhãn không nhắc đơn vị hành chính đã bỏ', () => {
    expect(WEATHER_MEASURE_POINT.area).toBe('vinh-long')
    expect(WEATHER_MEASURE_POINT.label).not.toMatch(/Bến Tre|Trà Vinh/)
    // Nhãn phải nói "điểm đo", không được ngụ ý phủ toàn tỉnh (124 xã/phường).
    expect(WEATHER_MEASURE_POINT.label).toContain('điểm đo')
  })
})
