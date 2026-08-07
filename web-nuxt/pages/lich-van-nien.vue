<template>
  <div class="page lvn-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch vạn niên' }]" />

    <header class="lvn-head">
      <p class="lvn-eyebrow"><IconLine name="calendar" /><span>Công cụ tra cứu</span></p>
      <h1>{{ pc('hero_title', 'Lịch vạn niên') }}</h1>
      <p class="lvn-lede">{{ pc('hero_subtitle', 'Đối chiếu dương lịch và âm lịch Việt Nam (múi giờ UTC+7), can chi và tiết khí. Toàn bộ con số trên trang được tính tại chỗ theo thuật toán thiên văn, không tra bảng chép sẵn.') }}</p>
    </header>

    <ClientOnly>
      <div class="lvn-instrument">
        <!-- Hôm nay: dải một dòng, không phải hero ảnh -->
        <section v-if="todayFacts" class="lvn-today" data-lvn-today>
          <span class="lvn-today-label">Hôm nay</span>
          <p class="lvn-today-line">
            <strong>{{ weekdayLabel(todayFacts.jdn) }}, {{ pad(today.day) }}/{{ pad(today.month) }}/{{ today.year }}</strong>
            <span class="lvn-sep" aria-hidden="true">·</span>
            <em class="lvn-lunar-voice">{{ lunarPhrase(todayFacts.lunar) }}</em>
            <span class="lvn-sep" aria-hidden="true">·</span>
            <span>ngày {{ todayFacts.canChiDay }}</span>
            <span class="lvn-sep" aria-hidden="true">·</span>
            <span>tiết {{ todayFacts.tietKhi }}</span>
          </p>
        </section>

        <!-- Lưới tháng -->
        <section class="block lvn-block">
          <div class="lvn-cal">
            <div class="lvn-cal-head">
              <div class="lvn-step">
                <button
                  type="button" class="lvn-nav" data-lvn-prev
                  :disabled="!canStep(-1)" aria-label="Tháng trước"
                  @click="stepMonth(-1)"
                ><IconLine name="arrow-left" /></button>
                <button
                  type="button" class="lvn-nav lvn-nav-next" data-lvn-next
                  :disabled="!canStep(1)" aria-label="Tháng sau"
                  @click="stepMonth(1)"
                ><IconLine name="arrow-left" /></button>
              </div>

              <div class="lvn-picker">
                <label class="lvn-field">
                  <span class="lvn-field-label">Tháng</span>
                  <select v-model.number="viewMonth" data-lvn-month aria-label="Chọn tháng dương lịch">
                    <option v-for="m in 12" :key="m" :value="m">{{ m }}</option>
                  </select>
                </label>
                <label class="lvn-field">
                  <span class="lvn-field-label">Năm</span>
                  <input
                    v-model.number="viewYear" data-lvn-year type="number" inputmode="numeric"
                    :min="LUNAR_YEAR_MIN" :max="LUNAR_YEAR_MAX" step="1" aria-label="Chọn năm dương lịch"
                  >
                </label>
                <button type="button" class="lvn-btn" data-lvn-today-btn @click="goToday">Hôm nay</button>
              </div>
            </div>

            <p v-if="!viewInRange" class="lvn-range-error" role="alert" data-lvn-range-error>
              <IconLine name="alert-triangle" />
              <span>
                Lõi lịch của trang chỉ tính đúng cho năm <strong>{{ LUNAR_YEAR_MIN }}–{{ LUNAR_YEAR_MAX }}</strong>.
                Trước {{ LUNAR_YEAR_MIN }}, lịch Việt Nam không dùng múi giờ UTC+7 (miền Nam theo UTC+8 tới 1975)
                nên kết quả sẽ lệch; sau {{ LUNAR_YEAR_MAX }}, công thức thiên văn bắt đầu trôi.
                Trang không hiển thị con số cho năm {{ viewYear }} thay vì hiển thị một con số sai.
              </span>
            </p>

            <template v-else>
              <!--
                1968–1975: hai miền dùng hai múi giờ khác nhau nên lịch âm lệch nhau.
                Miền Bắc chuyển sang UTC+7 từ 1968, miền Nam giữ UTC+8 tới 1975 — đo trên
                oracle thì 120/2922 ngày quãng đó ra kết quả khác, trong đó có cả mùng 1
                Tết Mậu Thân (29/01 theo UTC+7 vs 30/01 theo UTC+8).
                Lõi trang chạy UTC+7 = lịch nhà nước. Vĩnh Long thuộc miền Nam nên với 8 năm
                này người đọc cần biết mình đang xem bản nào; im lặng ở đây là để họ tin một
                con số mà chính ta biết có hai đáp án (§1.7).
                KHÔNG tự đổi sang UTC+8: ngày giỗ chép lại sau 1975 thường đã quy theo lịch
                nhà nước, đổi ngầm sẽ sai theo chiều ngược lại. Đây là việc của người đọc.
              -->
              <p v-if="viewYear <= 1975" class="lvn-range-error" data-lvn-southern-note>
                <IconLine name="alert-triangle" />
                <span>
                  Năm {{ viewYear }} có hai đáp án. Trang hiển thị theo <strong>lịch nhà nước</strong>
                  (UTC+7, dùng ở miền Bắc từ 1968). Miền Nam — trong đó có Vĩnh Long — khi ấy theo
                  UTC+8 tới 1975, nên một số ngày lệch nhau đúng một ngày, kể cả mùng 1 Tết.
                </span>
              </p>

              <p class="lvn-cal-caption" data-lvn-caption>
                Tháng {{ viewMonth }}/{{ viewYear }} <span class="lvn-sep" aria-hidden="true">·</span>
                <em class="lvn-lunar-voice">{{ lunarSpanLabel }}</em>
              </p>

              <div
                ref="gridEl" class="lvn-grid" role="grid"
                :aria-label="`Lịch tháng ${viewMonth} năm ${viewYear}`"
                @keydown="onGridKeydown"
              >
                <div class="lvn-row lvn-row-head" role="row">
                  <span
                    v-for="w in WEEKDAYS" :key="w.short" class="lvn-dow" role="columnheader"
                    :class="{ 'is-weekend': w.weekend }"
                  ><abbr :title="w.long">{{ w.short }}</abbr></span>
                </div>
                <div v-for="(week, wi) in weeks" :key="wi" class="lvn-row" role="row">
                  <div
                    v-for="(cell, ci) in week" :key="ci"
                    class="lvn-cell" role="gridcell"
                    :class="{
                      'is-blank': !cell,
                      'is-today': cell?.isToday,
                      'is-selected': cell?.isSelected,
                      'is-first': cell?.isFirst,
                      'is-full': cell?.isFull,
                      'is-weekend': WEEKDAYS[ci]?.weekend,
                    }"
                    :data-lvn-cell="cell ? cell.day : undefined"
                    :data-lvn-jdn="cell ? cell.jdn : undefined"
                    :tabindex="cell ? (cell.isSelected ? 0 : -1) : undefined"
                    :aria-selected="cell ? cell.isSelected : undefined"
                    :aria-label="cell ? cell.label : undefined"
                    @click="cell && selectJdn(cell.jdn)"
                  >
                    <template v-if="cell">
                      <span class="lvn-num">{{ cell.day }}</span>
                      <em class="lvn-lunar lvn-lunar-voice">{{ cell.lunarShort }}</em>
                    </template>
                  </div>
                </div>
              </div>

              <p class="lvn-legend">
                <span><span class="lvn-key lvn-key-first" aria-hidden="true">•</span> mùng 1 âm</span>
                <span><span class="lvn-key lvn-key-full" aria-hidden="true">◯</span> ngày rằm (15 âm)</span>
                <span><span class="lvn-key lvn-key-today" aria-hidden="true" /> hôm nay</span>
                <span class="lvn-legend-note">Ô âm lịch ghi ngày; sang tháng âm mới thì ghi <em class="lvn-lunar-voice">ngày/tháng</em>.</span>
              </p>
            </template>
          </div>
        </section>

        <!-- Chi tiết ngày đang chọn -->
        <section v-if="viewInRange && selectedFacts" class="block band lvn-block" data-lvn-detail>
          <h2 class="lvn-h2">Ngày {{ pad(selected.day) }}/{{ pad(selected.month) }}/{{ selected.year }}</h2>
          <dl class="lvn-dl">
            <div class="lvn-dl-row">
              <dt>Dương lịch</dt>
              <dd>{{ weekdayLabel(selectedFacts.jdn) }}, {{ pad(selected.day) }}/{{ pad(selected.month) }}/{{ selected.year }}</dd>
            </div>
            <div class="lvn-dl-row">
              <dt>Âm lịch</dt>
              <dd data-lvn-detail-lunar>
                <em class="lvn-lunar-voice">{{ lunarPhrase(selectedFacts.lunar) }}</em>
                <span v-if="selectedFacts.lunar.leap" class="lvn-tag">tháng nhuận</span>
                <span v-if="selectedFacts.lunar.day === 1" class="lvn-tag lvn-tag-first">mùng 1</span>
                <span v-else-if="selectedFacts.lunar.day === 15" class="lvn-tag lvn-tag-full">ngày rằm</span>
              </dd>
            </div>
            <div class="lvn-dl-row">
              <dt>Can chi ngày</dt>
              <dd data-lvn-detail-canchi-day>{{ selectedFacts.canChiDay }}</dd>
            </div>
            <div class="lvn-dl-row">
              <dt>Can chi tháng</dt>
              <dd>
                {{ selectedFacts.canChiMonth }}
                <small v-if="selectedFacts.lunar.leap" class="lvn-hint">tháng nhuận dùng can chi của tháng chính cùng số</small>
              </dd>
            </div>
            <div class="lvn-dl-row">
              <dt>Can chi năm</dt>
              <dd data-lvn-detail-canchi-year>{{ selectedFacts.canChiYear }}</dd>
            </div>
            <div class="lvn-dl-row">
              <dt>Tiết khí</dt>
              <dd data-lvn-detail-tietkhi>
                {{ selectedFacts.tietKhi }}
                <small class="lvn-hint">bắt đầu {{ selectedFacts.tietKhiStart }}</small>
              </dd>
            </div>
          </dl>

          <h3 class="lvn-h3">Can chi 12 canh giờ</h3>
          <p class="lvn-note-inline">
            Một canh giờ dài hai tiếng đồng hồ; giờ Tý bắt đầu từ 23 giờ hôm trước.
            Đây là tên can chi tính theo lịch, <strong>không phải</strong> đánh giá giờ tốt hay xấu.
          </p>
          <ul class="lvn-hours">
            <li
              v-for="h in selectedFacts.hours" :key="h.index"
              class="lvn-hour" :class="{ 'is-now': h.index === nowChiIndex && selectedIsToday }"
            >
              <span class="lvn-hour-range">{{ h.range }}</span>
              <span class="lvn-hour-name">{{ h.canChi }}</span>
            </li>
          </ul>
        </section>

        <!-- Đối chiếu hai chiều -->
        <section v-if="viewInRange" class="block lvn-block">
          <h2 class="lvn-h2">Đổi ngày</h2>
          <div class="lvn-convert">
            <form class="lvn-form" @submit.prevent>
              <h3 class="lvn-h3">Dương sang âm</h3>
              <div class="lvn-inputs">
                <label class="lvn-field">
                  <span class="lvn-field-label">Ngày</span>
                  <input v-model.number="s2l.day" data-lvn-s2l-day type="number" inputmode="numeric" min="1" max="31" step="1">
                </label>
                <label class="lvn-field">
                  <span class="lvn-field-label">Tháng</span>
                  <input v-model.number="s2l.month" data-lvn-s2l-month type="number" inputmode="numeric" min="1" max="12" step="1">
                </label>
                <label class="lvn-field">
                  <span class="lvn-field-label">Năm</span>
                  <input v-model.number="s2l.year" data-lvn-s2l-year type="number" inputmode="numeric" :min="LUNAR_YEAR_MIN" :max="LUNAR_YEAR_MAX" step="1">
                </label>
              </div>
              <output class="lvn-out" :class="{ 'is-error': !!solarToLunarResult.error }" data-lvn-s2l-out>
                <template v-if="solarToLunarResult.error">{{ solarToLunarResult.error }}</template>
                <template v-else>
                  <em class="lvn-lunar-voice">{{ solarToLunarResult.text }}</em>
                  <small class="lvn-hint">{{ solarToLunarResult.extra }}</small>
                </template>
              </output>
              <button
                v-if="!solarToLunarResult.error" type="button" class="lvn-btn"
                data-lvn-s2l-goto @click="goToConverted('solar')"
              >Xem ngày này trên lịch</button>
            </form>

            <form class="lvn-form" @submit.prevent>
              <h3 class="lvn-h3">Âm sang dương</h3>
              <div class="lvn-inputs">
                <label class="lvn-field">
                  <span class="lvn-field-label">Ngày âm</span>
                  <input v-model.number="l2s.day" data-lvn-l2s-day type="number" inputmode="numeric" min="1" max="30" step="1">
                </label>
                <label class="lvn-field">
                  <span class="lvn-field-label">Tháng âm</span>
                  <input v-model.number="l2s.month" data-lvn-l2s-month type="number" inputmode="numeric" min="1" max="12" step="1">
                </label>
                <label class="lvn-field">
                  <span class="lvn-field-label">Năm âm</span>
                  <input v-model.number="l2s.year" data-lvn-l2s-year type="number" inputmode="numeric" :min="LUNAR_YEAR_MIN" :max="LUNAR_YEAR_MAX" step="1">
                </label>
              </div>
              <label class="lvn-check">
                <input v-model="l2s.leap" data-lvn-l2s-leap type="checkbox">
                <span>Tháng nhuận</span>
              </label>
              <output class="lvn-out" :class="{ 'is-error': !!lunarToSolarResult.error }" data-lvn-l2s-out>
                <template v-if="lunarToSolarResult.error">{{ lunarToSolarResult.error }}</template>
                <template v-else>
                  <strong>{{ lunarToSolarResult.text }}</strong>
                  <small class="lvn-hint">{{ lunarToSolarResult.extra }}</small>
                </template>
              </output>
              <button
                v-if="!lunarToSolarResult.error" type="button" class="lvn-btn"
                data-lvn-l2s-goto @click="goToConverted('lunar')"
              >Xem ngày này trên lịch</button>
            </form>
          </div>
        </section>

        <!-- 24 tiết khí của năm đang xem -->
        <section v-if="viewInRange" class="block band lvn-block">
          <h2 class="lvn-h2">24 tiết khí năm {{ viewYear }}</h2>
          <p class="lvn-note-inline">
            Tiết khí chia một vòng quay của Trái Đất quanh Mặt Trời thành 24 chặng 15 độ.
            Ngày ghi dưới đây là ngày Mặt Trời đi qua mốc, tính theo giờ Việt Nam.
          </p>
          <ol class="lvn-terms" data-lvn-terms>
            <li v-for="t in termsOfYear" :key="t.index" class="lvn-term" :class="{ 'is-current': t.index === selectedFacts?.tietKhiIndex }">
              <span class="lvn-term-date">{{ pad(t.date.day) }}/{{ pad(t.date.month) }}</span>
              <span class="lvn-term-name">{{ t.name }}</span>
            </li>
          </ol>
        </section>
      </div>

      <template #fallback>
        <div class="lvn-boot" role="status" aria-label="Đang dựng lịch">
          <div class="lvn-boot-bar" />
          <div class="lvn-boot-grid"><span v-for="i in 42" :key="i" /></div>
        </div>
      </template>
    </ClientOnly>

    <!-- Ranh giới trung thực: nói rõ trang tính gì và cố ý không nói gì -->
    <section v-once class="block lvn-block lvn-scope">
      <h2 class="lvn-h2">Trang này tính gì</h2>
      <p>
        Âm lịch, can chi ngày — tháng — năm, tiết khí và tháng nhuận đều là phép tính thiên văn
        xác định: vị trí điểm sóc và kinh độ Mặt Trời, quy về múi giờ UTC+7 mà lịch Việt Nam dùng
        từ năm 1968. Cùng một ngày sẽ luôn cho cùng một kết quả, và kết quả đó đối chiếu được với
        bất kỳ bảng lịch nào tính theo cùng quy ước.
      </p>
      <h2 class="lvn-h2">Và cố ý không nói gì</h2>
      <p>
        Lịch vạn niên truyền thống thường kèm ngày tốt — ngày xấu, giờ hoàng đạo, sao tốt — sao xấu.
        Đó là <strong>quan niệm dân gian</strong>, không phải điều kiểm chứng được, và các sách lịch
        khác nhau cho kết quả khác nhau cho cùng một ngày. Trang này không hiển thị những mục đó,
        và cũng không đưa ra lời khuyên nên hay không nên làm việc gì vào ngày nào.
      </p>
      <p class="lvn-source">
        Thuật toán: Hồ Ngọc Đức (Âm lịch Việt Nam), dựa trên <em>Astronomical Algorithms</em> của Jean Meeus.
        Bản chạy trên trang được đối chiếu từng ngày với bản Python cùng thuật toán mà nó được viết lại
        từ đó: các năm mẫu tính từng ngày, và toàn bộ ngày âm 2020–2030 theo chiều ngược. Ngoài các năm
        mẫu đó, bộ kiểm thử chỉ kiểm bất biến cấu trúc. Phép đối chiếu này chứng minh hai bản khớp nhau,
        <strong>không</strong> chứng minh thuật toán gốc đúng — một sai sót nằm trong thuật toán sẽ xuất
        hiện y hệt ở cả hai bên.
      </p>
    </section>

    <section class="block band lvn-block lvn-cross">
      <h2 class="lvn-h2">Xem thêm theo lịch</h2>
      <div class="lvn-cross-links">
        <NuxtLink to="/le-hoi" class="lvn-cross-card">
          <IconLine name="lantern" />
          <span><strong>Lễ hội</strong><small>Kỳ Yên, Ok Om Bok, Nghinh Ông</small></span>
        </NuxtLink>
        <NuxtLink to="/su-kien" class="lvn-cross-card">
          <IconLine name="calendar" />
          <span><strong>Sự kiện</strong><small>Hội chợ, festival sắp diễn ra</small></span>
        </NuxtLink>
        <NuxtLink to="/theo-mua" class="lvn-cross-card">
          <IconLine name="leaf" />
          <span><strong>Theo mùa</strong><small>Tháng này ăn gì, đi đâu</small></span>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  jdFromDate,
  jdToDate,
  solarToLunar,
  tryLunarToSolar,
  canChiDay,
  canChiMonth,
  canChiYear,
  canChiHour,
  hourToChiIndex,
  tietKhiIndex,
  tietKhiStartDatesOfYear,
  isSupportedLunarYear,
  LUNAR_CHI,
  LUNAR_YEAR_MIN,
  LUNAR_YEAR_MAX,
  TIET_KHI,
  type LunarDate,
  type SolarDate,
} from '~/composables/useLunar'

const { f: pc } = usePageContent('lich_van_nien')

const WEEKDAYS = [
  { short: 'T2', long: 'Thứ Hai', weekend: false },
  { short: 'T3', long: 'Thứ Ba', weekend: false },
  { short: 'T4', long: 'Thứ Tư', weekend: false },
  { short: 'T5', long: 'Thứ Năm', weekend: false },
  { short: 'T6', long: 'Thứ Sáu', weekend: false },
  { short: 'T7', long: 'Thứ Bảy', weekend: true },
  { short: 'CN', long: 'Chủ Nhật', weekend: true },
]

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

/** Weekday from the Julian Day Number — no `Date`, so no timezone can shift it. */
function weekdayIndex(jdn: number): number {
  return (jdn + 1) % 7 // 0 = Chủ Nhật
}
function weekdayLabel(jdn: number): string {
  const i = weekdayIndex(jdn)
  return i === 0 ? 'Chủ Nhật' : (WEEKDAYS[i - 1]?.long as string)
}

function daysInSolarMonth(m: number, y: number): number {
  if (m === 2) return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28
  return m === 4 || m === 6 || m === 9 || m === 11 ? 30 : 31
}
function isRealSolarDate(d: number, m: number, y: number): boolean {
  return Number.isInteger(d) && Number.isInteger(m) && Number.isInteger(y)
    && m >= 1 && m <= 12 && d >= 1 && d <= daysInSolarMonth(m, y)
}

/** "15 tháng 7 nhuận năm Ất Tỵ" — tháng Giêng/Chạp gọi tên vì hai tên đó không mơ hồ. */
function lunarPhrase(l: LunarDate): string {
  const name = l.month === 1 ? 'tháng Giêng' : l.month === 12 ? 'tháng Chạp' : `tháng ${l.month}`
  return `${l.day} ${name}${l.leap ? ' nhuận' : ''} năm ${canChiYear(l.year)}`
}

/** Two-hour block of chi `i`: Tý is 23–01, so it starts at (23 + 2i) mod 24. */
function chiHourRange(i: number): string {
  const start = (23 + 2 * i) % 24
  return `${pad(start)}:00–${pad((start + 2) % 24)}:00`
}

// --- Trạng thái ------------------------------------------------------------
const now = new Date()
const today: SolarDate = { day: now.getDate(), month: now.getMonth() + 1, year: now.getFullYear() }
const nowChiIndex = hourToChiIndex(now.getHours())

const viewMonth = ref(today.month)
const viewYear = ref(today.year)
const selected = ref<SolarDate>({ ...today })
const gridEl = ref<HTMLElement | null>(null)

const viewInRange = computed(() => isSupportedLunarYear(viewYear.value))
const selectedIsToday = computed(() =>
  selected.value.day === today.day && selected.value.month === today.month && selected.value.year === today.year)

const todayFacts = computed(() => {
  if (!isSupportedLunarYear(today.year)) return null
  const jdn = jdFromDate(today.day, today.month, today.year)
  return {
    jdn,
    lunar: solarToLunar(today.day, today.month, today.year),
    canChiDay: canChiDay(today.day, today.month, today.year),
    tietKhi: TIET_KHI[tietKhiIndex(today.day, today.month, today.year)] as string,
  }
})

interface Cell {
  day: number
  jdn: number
  lunarShort: string
  isToday: boolean
  isSelected: boolean
  isFirst: boolean
  isFull: boolean
  label: string
}

const weeks = computed<Array<Array<Cell | null>>>(() => {
  if (!viewInRange.value) return []
  const m = viewMonth.value
  const y = viewYear.value
  const firstJdn = jdFromDate(1, m, y)
  const lead = (weekdayIndex(firstJdn) + 6) % 7 // cột 0 = Thứ Hai
  const total = daysInSolarMonth(m, y)
  const flat: Array<Cell | null> = new Array(lead).fill(null)
  for (let d = 1; d <= total; d++) {
    const jdn = firstJdn + d - 1
    const l = solarToLunar(d, m, y)
    // Ngày mở tháng âm mới ghi cả tháng, ngày thường chỉ ghi số — như lịch giấy.
    const short = l.day === 1 ? `${l.day}/${l.month}${l.leap ? 'N' : ''}` : String(l.day)
    flat.push({
      day: d,
      jdn,
      lunarShort: short,
      isToday: d === today.day && m === today.month && y === today.year,
      isSelected: d === selected.value.day && m === selected.value.month && y === selected.value.year,
      isFirst: l.day === 1,
      isFull: l.day === 15,
      label: `${weekdayLabel(jdn)} ${d}/${m}/${y}, âm lịch ${lunarPhrase(l)}`,
    })
  }
  while (flat.length % 7 !== 0) flat.push(null)
  const out: Array<Array<Cell | null>> = []
  for (let i = 0; i < flat.length; i += 7) out.push(flat.slice(i, i + 7))
  return out
})

const lunarSpanLabel = computed(() => {
  if (!viewInRange.value) return ''
  const a = solarToLunar(1, viewMonth.value, viewYear.value)
  const total = daysInSolarMonth(viewMonth.value, viewYear.value)
  const b = solarToLunar(total, viewMonth.value, viewYear.value)
  const nameOf = (l: LunarDate) => `tháng ${l.month}${l.leap ? ' nhuận' : ''}`
  return a.month === b.month && a.leap === b.leap
    ? `âm lịch ${nameOf(a)} năm ${canChiYear(a.year)}`
    : `âm lịch ${nameOf(a)} sang ${nameOf(b)} năm ${canChiYear(b.year)}`
})

const selectedFacts = computed(() => {
  const { day: d, month: m, year: y } = selected.value
  if (!isSupportedLunarYear(y)) return null
  const lunar = solarToLunar(d, m, y)
  const termIndex = tietKhiIndex(d, m, y)
  const starts = tietKhiStartDatesOfYear(y)
  const start = starts.get(termIndex)
  return {
    jdn: jdFromDate(d, m, y),
    lunar,
    canChiDay: canChiDay(d, m, y),
    canChiMonth: canChiMonth(lunar.month, lunar.year),
    canChiYear: canChiYear(lunar.year),
    tietKhiIndex: termIndex,
    tietKhi: TIET_KHI[termIndex] as string,
    tietKhiStart: start ? `${pad(start.day)}/${pad(start.month)}/${y}` : 'từ cuối năm trước',
    hours: LUNAR_CHI.map((_, i) => ({ index: i, range: chiHourRange(i), canChi: canChiHour(d, m, y, i) })),
  }
})

const termsOfYear = computed(() => {
  if (!viewInRange.value) return []
  return [...tietKhiStartDatesOfYear(viewYear.value).entries()]
    .map(([index, date]) => ({ index, date, name: TIET_KHI[index] as string }))
    .sort((a, b) => (a.date.month - b.date.month) || (a.date.day - b.date.day))
})

// --- Điều hướng ------------------------------------------------------------
function monthShift(m: number, y: number, delta: number): { month: number, year: number } {
  const total = (y * 12 + (m - 1)) + delta
  return { month: (total % 12) + 1, year: Math.floor(total / 12) }
}
function canStep(delta: number): boolean {
  if (!viewInRange.value) return false
  return isSupportedLunarYear(monthShift(viewMonth.value, viewYear.value, delta).year)
}
function stepMonth(delta: number) {
  const next = monthShift(viewMonth.value, viewYear.value, delta)
  if (!isSupportedLunarYear(next.year)) return
  viewMonth.value = next.month
  viewYear.value = next.year
}
function goToday() {
  viewMonth.value = today.month
  viewYear.value = today.year
  selected.value = { ...today }
}

function selectJdn(jdn: number) {
  const d = jdToDate(jdn)
  if (!isSupportedLunarYear(d.year)) return
  selected.value = d
  viewMonth.value = d.month
  viewYear.value = d.year
}

async function focusSelected() {
  await nextTick()
  const jdn = jdFromDate(selected.value.day, selected.value.month, selected.value.year)
  gridEl.value?.querySelector<HTMLElement>(`[data-lvn-jdn="${jdn}"]`)?.focus()
}

function onGridKeydown(e: KeyboardEvent) {
  const { day: d, month: m, year: y } = selected.value
  let target: SolarDate | null = null
  const byDays = (n: number) => jdToDate(jdFromDate(d, m, y) + n)
  switch (e.key) {
    case 'ArrowLeft': target = byDays(-1); break
    case 'ArrowRight': target = byDays(1); break
    case 'ArrowUp': target = byDays(-7); break
    case 'ArrowDown': target = byDays(7); break
    case 'Home': target = { day: 1, month: m, year: y }; break
    case 'End': target = { day: daysInSolarMonth(m, y), month: m, year: y }; break
    case 'PageUp':
    case 'PageDown': {
      const next = monthShift(m, y, e.key === 'PageUp' ? -1 : 1)
      target = { day: Math.min(d, daysInSolarMonth(next.month, next.year)), ...next }
      break
    }
    case 'Enter':
    case ' ': target = { day: d, month: m, year: y }; break
    default: return
  }
  e.preventDefault()
  if (!isSupportedLunarYear(target.year)) return
  selected.value = target
  viewMonth.value = target.month
  viewYear.value = target.year
  void focusSelected()
}

// --- Đối chiếu hai chiều ---------------------------------------------------
const s2l = reactive({ day: today.day, month: today.month, year: today.year })
const l2s = reactive<{ day: number, month: number, year: number, leap: boolean }>(
  (() => {
    const l = isSupportedLunarYear(today.year)
      ? solarToLunar(today.day, today.month, today.year)
      : { day: 1, month: 1, year: 2025, leap: false }
    return { day: l.day, month: l.month, year: l.year, leap: l.leap }
  })(),
)

const solarToLunarResult = computed(() => {
  const { day: d, month: m, year: y } = s2l
  if (!isSupportedLunarYear(y)) {
    return { error: `Chỉ tra được năm ${LUNAR_YEAR_MIN}–${LUNAR_YEAR_MAX}. Ngoài khoảng đó kết quả sẽ sai nên trang không hiển thị.`, text: '', extra: '' }
  }
  if (!isRealSolarDate(d, m, y)) {
    return { error: `Không có ngày ${d}/${m}/${y} trên dương lịch.`, text: '', extra: '' }
  }
  const l = solarToLunar(d, m, y)
  return {
    error: '',
    text: lunarPhrase(l),
    extra: `${weekdayLabel(jdFromDate(d, m, y))} · ngày ${canChiDay(d, m, y)} · tiết ${TIET_KHI[tietKhiIndex(d, m, y)]}`,
  }
})

const lunarToSolarResult = computed(() => {
  const { day: d, month: m, year: y, leap } = l2s
  if (!isSupportedLunarYear(y)) {
    return { error: `Chỉ tra được năm ${LUNAR_YEAR_MIN}–${LUNAR_YEAR_MAX}. Ngoài khoảng đó kết quả sẽ sai nên trang không hiển thị.`, text: '', extra: '' }
  }
  if (!Number.isInteger(d) || d < 1 || d > 30 || !Number.isInteger(m) || m < 1 || m > 12) {
    return { error: 'Ngày âm phải từ 1 đến 30, tháng âm từ 1 đến 12.', text: '', extra: '' }
  }
  const solar = tryLunarToSolar(d, m, y, leap)
  if (!solar) {
    return {
      error: leap
        ? `Năm âm ${y} không có tháng ${m} nhuận, hoặc tháng đó không có ngày ${d}.`
        : `Năm âm ${y} không có ngày ${d} tháng ${m} — tháng âm thiếu chỉ có 29 ngày.`,
      text: '', extra: '',
    }
  }
  const jdn = jdFromDate(solar.day, solar.month, solar.year)
  return {
    error: '',
    text: `${weekdayLabel(jdn)}, ${pad(solar.day)}/${pad(solar.month)}/${solar.year}`,
    extra: `ngày ${canChiDay(solar.day, solar.month, solar.year)} · tiết ${TIET_KHI[tietKhiIndex(solar.day, solar.month, solar.year)]}`,
  }
})

function goToConverted(which: 'solar' | 'lunar') {
  if (which === 'solar') {
    if (solarToLunarResult.value.error) return
    selected.value = { day: s2l.day, month: s2l.month, year: s2l.year }
  } else {
    const solar = tryLunarToSolar(l2s.day, l2s.month, l2s.year, l2s.leap)
    if (!solar) return
    selected.value = solar
  }
  viewMonth.value = selected.value.month
  viewYear.value = selected.value.year
  void focusSelected()
}

// --- SEO -------------------------------------------------------------------
useSeoMeta({
  title: () => pc('seo_title', 'Lịch vạn niên — âm lịch, can chi, tiết khí | vinhlong360'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/lich-van-nien') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Lịch vạn niên' },
      ],
    }),
  }],
}))
</script>

<style scoped>
/* Trang này là một dụng cụ tra cứu, không phải catalog: không hero ảnh, không
   lưới card. Nội dung là bảng và danh sách nên trình bày bằng bảng và danh sách. */
.lvn-head { padding: var(--space-8) 0 var(--space-4); }
.lvn-eyebrow {
  display: flex; align-items: center; gap: var(--space-1h);
  margin: 0 0 var(--space-2);
  font-size: var(--text-xs); letter-spacing: var(--tracking-wide, .04em);
  text-transform: uppercase; color: var(--ink-tertiary);
}
.lvn-head h1 { margin: 0; font-size: var(--text-4xl); line-height: var(--leading-tight); }
.lvn-lede {
  max-width: var(--measure-read, 65ch);
  margin: var(--space-3) 0 0;
  color: var(--ink-secondary); line-height: var(--leading-relaxed);
}

/* Giọng chữ riêng cho mọi con số âm lịch — dùng lại đúng một họ chữ trên cả trang. */
.lvn-lunar-voice { font-family: var(--font-editorial); font-style: italic; }

.lvn-today {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-2) var(--space-3);
  padding: var(--space-3) 0;
  border-block: .5px solid var(--line);
}
.lvn-today-label {
  font-size: var(--text-2xs); text-transform: uppercase;
  letter-spacing: var(--tracking-wide, .06em); color: var(--ink-tertiary);
}
.lvn-today-line { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-1h); margin: 0; }
.lvn-sep { color: var(--ink-tertiary); }

.lvn-block { padding-block: var(--space-8); }
.lvn-h2 { margin: 0 0 var(--space-3); font-size: var(--text-xl); }
.lvn-h3 { margin: var(--space-6) 0 var(--space-2); font-size: var(--text-base); }
.lvn-note-inline {
  max-width: var(--measure-read, 65ch);
  margin: 0 0 var(--space-3); color: var(--ink-secondary); font-size: var(--text-sm);
}

/* --- Lịch --- */
.lvn-cal-head {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: var(--space-3); margin-bottom: var(--space-3);
}
.lvn-step { display: flex; gap: var(--space-1h); }
.lvn-nav {
  width: 44px; height: 44px;
  display: inline-flex; align-items: center; justify-content: center;
  border: .5px solid var(--line); border-radius: var(--radius-full);
  background: var(--bg); color: var(--ink); cursor: pointer;
  transition: background var(--duration-fast, .15s) var(--ease-out);
}
.lvn-nav-next { transform: rotate(180deg); }
.lvn-nav:hover:not(:disabled) { background: var(--bg-alt); }
.lvn-nav:disabled { opacity: var(--opacity-disabled, .38); cursor: not-allowed; }
.lvn-nav:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

.lvn-picker { display: flex; flex-wrap: wrap; align-items: flex-end; gap: var(--space-2); }
.lvn-field { display: flex; flex-direction: column; gap: 2px; }
.lvn-field-label { font-size: var(--text-2xs); color: var(--ink-tertiary); }
.lvn-field select,
.lvn-field input {
  min-height: 44px; padding: 0 var(--space-2);
  border: .5px solid var(--border-input, var(--line)); border-radius: var(--radius-control);
  background: var(--bg); color: var(--ink); font: inherit; font-size: var(--text-sm);
}
.lvn-field input[type="number"] { width: 6.5rem; }
.lvn-field select:focus-visible,
.lvn-field input:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }

.lvn-btn {
  min-height: 44px; padding: 0 var(--space-3);
  border: .5px solid var(--line); border-radius: var(--radius-control);
  background: var(--bg-alt); color: var(--ink); font: inherit; font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--duration-fast, .15s) var(--ease-out);
}
.lvn-btn:hover { background: var(--card-hover, var(--line)); }
.lvn-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

.lvn-cal-caption { margin: 0 0 var(--space-2); color: var(--ink-secondary); font-size: var(--text-sm); }

.lvn-range-error {
  display: flex; gap: var(--space-2); align-items: flex-start;
  max-width: var(--measure-read, 65ch);
  padding: var(--space-3); border-inline-start: 2px solid var(--error);
  background: rgba(var(--red-rgb, var(--primary-rgb)), .06);
  color: var(--ink); font-size: var(--text-sm); line-height: var(--leading-relaxed);
}

/* Không đổ cột trên màn hẹp: giữ 7 cột, cho khung tự cuộn ngang. */
.lvn-grid { overflow-x: auto; overscroll-behavior-x: contain; border-block-start: .5px solid var(--line); }
.lvn-row { display: grid; grid-template-columns: repeat(7, minmax(44px, 1fr)); min-width: 336px; }
.lvn-dow {
  padding: var(--space-1h) var(--space-1); text-align: center;
  font-size: var(--text-2xs); font-weight: var(--weight-semibold);
  color: var(--ink-tertiary); text-transform: uppercase;
}
.lvn-dow abbr { text-decoration: none; }
.lvn-dow.is-weekend { color: var(--ink-secondary); }

.lvn-cell {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
  min-height: 56px; padding: var(--space-1);
  border-block-start: .5px solid var(--line);
  border-inline-start: .5px solid var(--line);
  cursor: pointer;
  transition: background var(--duration-fast, .15s) var(--ease-out);
}
.lvn-row > .lvn-cell:last-child { border-inline-end: .5px solid var(--line); }
.lvn-row:last-child > .lvn-cell { border-block-end: .5px solid var(--line); }
.lvn-cell.is-blank { cursor: default; background: var(--bg-alt); }
.lvn-cell:not(.is-blank):hover { background: rgba(var(--primary-rgb), .06); }
.lvn-cell:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.lvn-cell.is-weekend .lvn-num { color: var(--ink-secondary); }
.lvn-cell.is-today { background: rgba(var(--primary-rgb), .1); }
.lvn-cell.is-selected { box-shadow: inset 0 0 0 2px var(--primary-fg); }
.lvn-num { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--ink); }
.lvn-lunar { font-size: var(--text-2xs); color: var(--ink-tertiary); }
.lvn-cell.is-first .lvn-lunar { color: var(--error); font-weight: var(--weight-semibold); }
.lvn-cell.is-full .lvn-lunar { color: var(--accent-dark); font-weight: var(--weight-semibold); }
.lvn-cell.is-first .lvn-lunar::before { content: '•'; margin-inline-end: 1px; }
.lvn-cell.is-full .lvn-lunar::before { content: '◯'; margin-inline-end: 1px; font-size: 8px; }

.lvn-legend {
  display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-4);
  margin: var(--space-2) 0 0; font-size: var(--text-2xs); color: var(--ink-tertiary);
}
.lvn-key-first { color: var(--error); }
.lvn-key-full { color: var(--accent-dark); }
.lvn-key-today {
  display: inline-block; width: 10px; height: 10px; vertical-align: -1px;
  background: rgba(var(--primary-rgb), .35);
}
.lvn-legend-note { flex-basis: 100%; }

/* --- Chi tiết ngày: bảng định nghĩa, không phải card --- */
.lvn-dl { margin: 0; border-block-start: .5px solid var(--line); }
.lvn-dl-row {
  display: grid; grid-template-columns: minmax(9rem, 1fr) 2fr; gap: var(--space-3);
  padding: var(--space-2h) 0; border-block-end: .5px solid var(--line);
}
.lvn-dl-row dt { color: var(--ink-tertiary); font-size: var(--text-sm); }
.lvn-dl-row dd { margin: 0; color: var(--ink); }
.lvn-hint { display: block; margin-top: 2px; color: var(--ink-tertiary); font-size: var(--text-2xs); }
.lvn-tag {
  display: inline-block; margin-inline-start: var(--space-1h); padding: 0 var(--space-1h);
  border: .5px solid var(--line); border-radius: var(--radius-full);
  font-size: var(--text-2xs); color: var(--ink-secondary);
}
.lvn-tag-first { color: var(--error); border-color: currentColor; }
.lvn-tag-full { color: var(--accent-dark); border-color: currentColor; }

.lvn-hours {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 0 var(--space-4); margin: 0; padding: 0; list-style: none;
}
.lvn-hour {
  display: flex; justify-content: space-between; gap: var(--space-2);
  padding: var(--space-1h) 0; border-block-end: .5px solid var(--line);
  font-size: var(--text-sm);
}
.lvn-hour-range { color: var(--ink-tertiary); font-variant-numeric: tabular-nums; }
.lvn-hour.is-now { font-weight: var(--weight-semibold); }
.lvn-hour.is-now .lvn-hour-range { color: var(--primary-fg); }

/* --- Đổi ngày --- */
.lvn-convert { display: grid; grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr)); gap: var(--space-6); }
.lvn-form { display: flex; flex-direction: column; gap: var(--space-2); align-items: flex-start; }
.lvn-form .lvn-h3 { margin-top: 0; }
.lvn-inputs { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.lvn-check { display: flex; align-items: center; gap: var(--space-1h); min-height: 44px; font-size: var(--text-sm); }
.lvn-check input { width: 20px; height: 20px; }
.lvn-out {
  display: block; width: 100%; padding: var(--space-2h) 0;
  border-block-start: .5px solid var(--line);
  font-size: var(--text-lg); color: var(--ink);
}
.lvn-out.is-error { font-size: var(--text-sm); color: var(--error); }

/* --- Tiết khí --- */
.lvn-terms {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 0 var(--space-4); margin: 0; padding: 0; list-style: none;
}
.lvn-term {
  display: flex; gap: var(--space-2); padding: var(--space-1h) 0;
  border-block-end: .5px solid var(--line); font-size: var(--text-sm);
}
.lvn-term-date { color: var(--ink-tertiary); font-variant-numeric: tabular-nums; }
.lvn-term.is-current { font-weight: var(--weight-semibold); }
.lvn-term.is-current .lvn-term-date { color: var(--primary-fg); }

/* --- Ranh giới trung thực --- */
.lvn-scope p { max-width: var(--measure-read, 65ch); color: var(--ink-secondary); line-height: var(--leading-relaxed); }
.lvn-source { font-size: var(--text-sm); color: var(--ink-tertiary); }

/* --- Cross links: hàng, không phải card bo tròn --- */
.lvn-cross-links { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 0 var(--space-6); }
.lvn-cross-card {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) 0; min-height: 44px;
  border-block-end: .5px solid var(--line); color: var(--ink); text-decoration: none;
}
.lvn-cross-card:hover strong { text-decoration: underline; }
.lvn-cross-card small { display: block; color: var(--ink-tertiary); font-size: var(--text-2xs); }

/* --- Khung chờ dựng lịch (chỉ hiện trước khi client tiếp quản) --- */
.lvn-boot { padding-block: var(--space-8); }
.lvn-boot-bar { height: 44px; margin-bottom: var(--space-3); background: var(--sk-base); border-radius: var(--radius-control); }
.lvn-boot-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: .5px; }
.lvn-boot-grid span { display: block; min-height: 56px; background: var(--sk-base); }

@media (max-width: 640px) {
  .lvn-head h1 { font-size: var(--text-3xl); }
  .lvn-cell { min-height: 52px; }
  .lvn-dl-row { grid-template-columns: 1fr; gap: 2px; }
}

@media (prefers-reduced-motion: reduce) {
  .lvn-nav, .lvn-btn, .lvn-cell { transition: none; }
}
</style>
