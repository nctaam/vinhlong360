<template>
  <!--
    Dải "bản tin địa phương" trên trang chủ. Ba trạng thái, phân biệt ngay ở cấp DOM
    (`data-weather-status`) chứ không chỉ bằng chữ, để test và audit đọc được:

      measured   — có số đo thật: hiện số + dòng nguồn + mốc giờ đo.
      estimated  — backend chỉ có dữ liệu dự phòng theo mùa: hiện khối, nói rõ bằng lời
                   rằng đây không phải số đo, và KHÔNG hiện con số nào.
      unavailable— không lấy được gì (đang tải, mạng lỗi, 503, payload lạ): ẩn hẳn.
                   Không khung rỗng, không skeleton, không số giả (CLAUDE.md §1.7).
  -->
  <section
    v-if="reading.status !== 'unavailable'"
    class="home-local-briefing"
    :data-material-accent="accent"
    :data-weather-status="reading.status"
    aria-labelledby="home-local-briefing-title"
  >
    <h2 id="home-local-briefing-title" class="home-local-briefing__title">
      <IconLine :name="reading.iconName" aria-hidden="true" />
      <span>Thời tiết hôm nay</span>
    </h2>

    <template v-if="reading.status === 'measured'">
      <p class="home-local-briefing__measure">
        <strong class="home-local-briefing__temp">{{ tempLabel }}</strong>
        <span v-if="reading.description" class="home-local-briefing__desc">{{ reading.description }}</span>
        <span v-if="humidityLabel" class="home-local-briefing__metric">
          <IconLine name="droplet" aria-hidden="true" /> Ẩm {{ humidityLabel }}
        </span>
        <span v-if="windLabel" class="home-local-briefing__metric">
          <IconLine name="wind" aria-hidden="true" /> Gió {{ windLabel }}
        </span>
      </p>
      <p class="home-local-briefing__source">{{ sourceLine }}</p>
    </template>

    <p v-else class="home-local-briefing__estimate">
      Ước theo mùa, chưa nối được dịch vụ đo. Số duy nhất đang có là giá trị mặc định theo
      tháng chứ không phải số đo thực tế, nên tụi mình không hiện nhiệt độ ở đây.
    </p>

    <NuxtLink class="home-local-briefing__link" :to="seasonLink">
      Lịch mùa vụ tháng {{ currentMonth }} →
    </NuxtLink>
  </section>
</template>

<script setup lang="ts">
import { useWeather, weatherAccent, WEATHER_MEASURE_POINT } from '~/composables/useWeather'

const { reading } = useWeather()

const accent = computed(() => weatherAccent(reading.value))

/**
 * Định dạng số kiểu Việt (dấu phẩy thập phân) bằng tay thay vì `toLocaleString`:
 * kết quả giống nhau trên mọi runtime (Node ICU, happy-dom, trình duyệt), nên test
 * khoá được đúng chuỗi mà người dùng thấy.
 */
function vnNumber(value: number, maxFractionDigits = 1): string {
  const rounded = Number(value.toFixed(maxFractionDigits))
  return String(rounded).replace('.', ',')
}

const tempLabel = computed(() => {
  const temp = reading.value.tempC
  return temp === null ? '' : `${vnNumber(temp)}°C`
})

const humidityLabel = computed(() => {
  const humidity = reading.value.humidity
  return humidity === null ? '' : `${vnNumber(humidity, 0)}%`
})

const windLabel = computed(() => {
  const wind = reading.value.windSpeedMs
  return wind === null ? '' : `${vnNumber(wind)} m/s`
})

/** HH:mm theo giờ Việt Nam. Không có Intl/timeZone thì bỏ mốc giờ, không đoán. */
function vnClock(at: Date): string {
  try {
    return new Intl.DateTimeFormat('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Ho_Chi_Minh',
    }).format(at)
  } catch {
    return ''
  }
}

/**
 * Dòng nguồn viết bằng văn xuôi, cố ý KHÔNG dùng `<SourceMark>`: bốn tier của component đó
 * (official / verified / community / unknown — components/SourceMark.vue:24-29) mang nghĩa
 * nghiệp vụ riêng của dự án; gắn "official" cho OpenWeatherMap là mạo nhận thẩm quyền, gắn
 * "verified" thì vi phạm §1.7 vì chưa có `attributes.verifiedAt` nào.
 *
 * Nhãn phạm vi nói "điểm đo", không nói "toàn tỉnh": backend đo đúng MỘT toạ độ
 * (agent/realtime.py:55), không phải trung bình 124 xã/phường.
 */
const sourceLine = computed(() => {
  const parts = ['Nguồn: OpenWeatherMap', WEATHER_MEASURE_POINT.label]
  const at = reading.value.observedAt
  if (at) {
    const clock = vnClock(at)
    // "lấy lúc", KHÔNG phải "đo lúc". Mốc này là `_ts` do backend đóng dấu lúc NHẬN
    // được HTTP response (agent/realtime.py:121), không phải trường `dt` (thời điểm
    // quan trắc) của OpenWeatherMap — `dt` hiện không được chuyển tiếp. Endpoint
    // current-weather free có độ trễ quan trắc vài phút, nên giờ hiển thị luôn MỚI
    // HƠN giờ đo thật; gọi nó là "đo lúc" là làm số liệu trông tươi hơn thực tế.
    // Muốn nói "đo lúc" thì phải mang `dt` về backend trước.
    if (clock) parts.push(`lấy lúc ${clock}`)
  }
  return parts.join(' · ')
})

/**
 * Tháng hiện tại đọc ở client. An toàn với hydration vì cả khối chỉ xuất hiện SAU khi
 * fetch client-side xong (useWeather dùng `server: false`) — SSR không render nhánh này.
 */
const currentMonth = computed(() => new Date().getMonth() + 1)
const seasonLink = computed(() => `/theo-mua?mua=${currentMonth.value}`)
</script>

<style scoped>
/*
  Công thức container copy từ `.home-decision-ledger` (assets/css/home-nocturne.css:162-170)
  để nhịp dọc trang chủ không đổi; chỉ giảm padding để đọc ra "dải" chứ không phải "section".
  Không bo góc, không đổ bóng, không gradient — đúng ngôn ngữ hairline của trang.
  Màu: chỉ token (R30.3 hard-ratchet), không hex/rgb.
*/
.home-local-briefing {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2) var(--space-4);
  width: min(var(--maxw), calc(100% - var(--space-10)));
  min-height: var(--touch-min);
  margin-inline: auto;
  padding-block: var(--space-6);
  border-block-end: 1px solid var(--color-border);
  color: var(--color-text);
}

.home-local-briefing__title {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  color: var(--tri-region-material-accent);
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: .08em;
  text-transform: uppercase;
}

.home-local-briefing__measure {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  font-size: var(--text-sm);
}

.home-local-briefing__temp {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  font-variant-numeric: tabular-nums;
}

.home-local-briefing__desc { color: var(--color-text); }

.home-local-briefing__metric {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

/* Dòng nguồn và dòng "ước theo mùa" cùng cỡ chữ: cái sau KHÔNG được nhỏ hơn phần nội dung
   nó đang chú thích, nếu không nó thành dòng chú thích mờ dễ lướt qua — đúng cách một số
   đo giả lọt vào mắt người đọc. Ở trạng thái `estimated` nó là nội dung chính. */
.home-local-briefing__source,
.home-local-briefing__estimate {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.home-local-briefing__estimate {
  flex: 1 1 20rem;
  max-width: 62ch;
  font-size: var(--text-sm);
}

.home-local-briefing__link {
  display: inline-flex;
  align-items: center;
  min-height: var(--touch-min);
  margin-inline-start: auto;
  color: var(--color-action);
  font-size: var(--text-sm);
  text-decoration: none;
}

.home-local-briefing__link:hover,
.home-local-briefing__link:focus-visible { text-decoration: underline; }

@media (max-width: 40rem) {
  .home-local-briefing {
    /* Mobile: một cột dọc, không carousel ngang. Chỉ số phụ (ẩm/gió) ẩn đi — nhiệt độ,
       mô tả trời và dòng nguồn là phần không được cắt. */
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }

  .home-local-briefing__metric { display: none; }

  .home-local-briefing__link { margin-inline-start: 0; }
}
</style>
