<template>
  <div class="page events-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lễ hội' }]" :json-ld="true" />

    <!-- Hero: "Đất này giữ lịch riêng" — lunar-first, time-aware -->
    <section class="catalog-hero cat-festival register-le-hoi">
      <p class="dateline-eyebrow">
        HÔM NAY · <strong>{{ todayGregorianLabel }}</strong> · ÂM LỊCH <span class="lunar-label">{{ todayLunarLabel }}</span>
      </p>
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true"><IconLine name="lantern" /></span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>

      <!-- Live urgency treatment supersedes the stat-chip row when something is imminent -->
      <NuxtLink v-if="liveNow" :to="entityPath(liveNow.id)" class="now-banner">
        <span class="now-banner-dot" aria-hidden="true"></span>
        <span class="now-banner-text">
          <strong>{{ eventStatus(liveNow) === 'now' ? 'Đang diễn ra' : 'Sắp diễn ra' }}: {{ liveNow.name }}</strong>
          <template v-if="liveNow.place_name"> — {{ liveNow.place_name }}</template>
        </span>
        <span class="now-banner-countdown">{{ countdownLabel(liveNow) }}</span>
      </NuxtLink>
      <div v-else-if="allEvents.length" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="allEvents.length" class="stat-num" />
          <span class="stat-label">lễ hội</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <CountUp :value="a.count" class="stat-num" />
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>

      <!-- Signature moment: lunar ribbon proves the calendar runs on the moon, not the marketing quarter -->
      <div v-if="ribbonTicks.length" class="lunar-ribbon" role="group" aria-label="Dải âm lịch — lễ hội sắp tới theo vị trí trăng">
        <svg class="lunar-ribbon-moon" viewBox="0 0 32 32" aria-hidden="true">
          <circle class="moon-base" cx="16" cy="16" r="13" />
          <path class="moon-lit" :d="todayMoonPath" />
        </svg>
        <span class="lunar-ribbon-label">Trăng <strong>{{ todayLunar.day }}/30</strong></span>
        <div class="lunar-ribbon-track">
          <button
            v-for="tick in ribbonTicks" :key="tick.id"
            type="button"
            class="lunar-ribbon-tick"
            :style="{ left: tick.pct + '%' }"
            @click="navigateTo(entityPath(tick.id))"
          >
            <span class="lunar-ribbon-tip"><strong>{{ tick.name }}</strong>{{ tick.hook }}</span>
            <span class="sr-only">{{ tick.name }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Spotlight nổi bật -->
    <CatalogSpotlight :items="allEvents" />

    <CatalogAeoPlaque
      title="Cẩm nang nghi thức lễ hội ba dân tộc Kinh — Khmer — Hoa"
      kicker="Văn hóa tâm linh · Nghi thức bản địa"
      accent="river"
      icon="calendar"
      :entries="festivalAeoEntries"
      cta-to="/lich-van-nien"
      cta-label="Tra cứu lịch vạn niên & âm lịch"
    />

    <!-- Ceremonial ledger: full-width rows ordered strictly by nearness in time,
         not a horizontal scroll-row — a calendar of upcoming ritual time deserves
         the same narrative weight as an itinerary. -->
    <section v-if="upcoming.length" class="block reveal">
      <div class="sediment-head">
        <h2>Sắp diễn ra</h2>
      </div>
      <ul class="ledger" aria-label="Lễ hội sắp diễn ra, theo thứ tự gần nhất">
        <!-- ul/li: role="listitem" đặt thẳng lên NuxtLink làm thẻ <a> MẤT vai trò
             link (ARIA ghi đè vai trò ngầm) và mất luôn tên khả truy cập, vì
             listitem là name-from-author. Trình đọc màn hình đọc các hàng này là
             "mục danh sách" trống thay vì đọc tên và cho biết bấm được. -->
        <li v-for="e in upcoming" :key="e.id" class="ledger-item">
        <NuxtLink
          :to="entityPath(e.id)"
          class="ledger-row"
        >
          <div class="event-date-badge lehoi-badge">
            <span class="edb-month">{{ formatMonth(e) }}</span>
            <span class="edb-day">{{ formatDay(e) }}</span>
          </div>
          <span class="ledger-status" :class="{ 'is-now': eventStatus(e) === 'now', 'is-soon': eventStatus(e) === 'soon' }">
            {{ eventStatus(e) ? STATUS_LABEL[eventStatus(e)] : countdownLabel(e) }}
          </span>
          <h3 class="ledger-name">{{ e.name }}</h3>
          <span v-if="e.place_name" class="ledger-place"><IconLine name="pin" /> {{ e.place_name }}</span>
          <span v-if="e.attributes?.lunar_date" class="lunar-label"><IconLine name="moon" /> {{ e.attributes.lunar_date }}</span>
        </NuxtLink>
        </li>
      </ul>
      <button type="button" class="ical-bulk-btn" @click="downloadIcalBulk">
        <IconLine name="calendar" /> Thêm cả mùa lễ hội vào lịch của bạn
      </button>
    </section>

    <!-- Off-season mini-preview (no upcoming festivals): whets appetite instead of dead-ending -->
    <section v-else-if="data && !fetchError && allEvents.length" class="block reveal">
      <p class="lehoi-offseason"><IconLine name="moon" /> Mùa lễ hội sẽ quay lại — xem lịch bên dưới để biết các mùa lễ hội trong năm.</p>
      <div v-if="offseasonNext.length" class="offseason-preview">
        <p v-for="e in offseasonNext" :key="e.id" class="offseason-preview-item">
          <span class="lunar-label" v-if="e.attributes?.lunar_date"><IconLine name="moon" /> {{ e.attributes.lunar_date }}</span>
          <NuxtLink :to="entityPath(e.id)"><strong>{{ e.name }}</strong></NuxtLink>
        </p>
      </div>
    </section>

    <!-- Register toggle: ancestral (lễ hội, here) vs contemporary (sự kiện) — leaf ↔ amber -->
    <section class="block reveal">
      <div class="register-toggle" role="group" aria-label="Chọn sổ lễ hội">
        <!-- aria-current, KHÔNG phải aria-pressed: đây là link điều hướng
             (<a>), mà aria-pressed chỉ hợp lệ với role="button" — axe bắt
             critical `aria-allowed-attr` (2026-08-05). -->
        <NuxtLink to="/le-hoi" class="register-toggle-tab is-active tone-leaf" aria-current="page"><IconLine name="lantern" /> Lễ hội truyền thống</NuxtLink>
        <NuxtLink to="/su-kien" class="register-toggle-tab tone-amber"><IconLine name="megaphone" /> Sự kiện &amp; hội chợ</NuxtLink>
      </div>
    </section>

    <!-- Region quick-picks — blob shapes gesture at real geography without map tiles -->
    <section class="block band reveal">
      <div class="sediment-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks blob-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string)"
        >
          <IconLine :name="meta.icon" class="quick-pick-icon" />
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} lễ hội</span>
        </button>
      </div>
    </section>

    <!-- Interstitial -->
    <!-- declutter-2 A2: interstitial le-hoi SUPPRESS — fact trùng gần nguyên văn đoạn
         mở editorial ngay dưới (duplication-test). -->

    <!-- Editorial: le-hoi's strongest asset, elevated with pull-quote treatment
         so the strongest lines aren't buried in dense paragraph body text. -->
    <section v-once class="page-article reveal">
      <div class="sediment-head sediment-head-first"><h2>Văn hoá lễ hội Vĩnh Long</h2></div>
      <p>Vùng đất tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025) là nơi giao thoa của ba nền văn hoá: Kinh, Khmer và Hoa. Mỗi cộng đồng mang đến một hệ thống lễ hội riêng biệt, tạo nên bức tranh văn hoá đa dạng hiếm có trong cả nước.</p>
      <blockquote class="pull-quote">Từ đình miếu Kinh ven sông đến chùa Khmer tháp nhọn, từ hội quán Hoa rực rỡ đèn lồng đến giỗ kỵ danh nhân — lễ hội ở đây không chỉ là dịp vui mà là sợi dây kết nối cộng đồng qua nhiều thế hệ.</blockquote>

      <!-- Ba dòng lễ hội: makes the tri-ethnic framing visible at a glance -->
      <div class="etiquette-box">
        <p><strong>Ba dòng lễ hội, một vùng đất</strong> — đình Kinh giữ lịch theo năm âm lịch, chùa Khmer giữ lịch theo trăng tròn, hội quán Hoa giữ lịch theo phường hội. Ba cách đếm ngày, cùng chảy trên một dòng Cửu Long.</p>
      </div>

      <div class="sediment-head"><h2>Lễ hội tiêu biểu</h2></div>
      <p><strong>Lễ Kỳ Yên</strong> là lễ hội phổ biến nhất, tổ chức tại đình làng khắp vùng vào đầu năm âm lịch, cầu cho mưa thuận gió hoà, mùa màng bội thu.</p>
      <blockquote class="pull-quote">Ok Om Bok — lễ Cúng Trăng của người Khmer vùng Trà Vinh (trước 7-2025), tổ chức vào rằm tháng 10 âm lịch với đua ghe ngo trên sông Maspéro.</blockquote>
      <p><strong>Lễ Nghinh Ông</strong> diễn ra ở các vùng ven biển, tôn vinh Cá Ông (cá voi) — vị thần bảo hộ ngư dân. Ngoài ra còn có các lễ giỗ danh nhân như giỗ Thủ khoa Bùi Hữu Nghĩa (Vĩnh Long), giỗ cụ Phan Thanh Giản, và nhiều lễ hội nông nghiệp như Hội trái cây ngon, Lễ hội bánh dân gian Nam Bộ. Mỗi lễ hội thường kéo dài 2–3 ngày với phần lễ trang nghiêm và phần hội sôi nổi.</p>

      <div class="sediment-head"><h2>Đi lễ hội — cần biết gì?</h2></div>
      <div class="etiquette-box">
        <p>Hầu hết lễ hội truyền thống mở cửa tự do, không thu phí. Trang phục lịch sự khi vào khu vực chánh điện hoặc chánh đường. Nếu đến chùa Khmer, nên bỏ giày dép trước khi vào và tránh chạm đầu người khác. Thời gian tốt nhất để xem nghi lễ chính thường là buổi sáng; phần hội chợ, văn nghệ diễn ra chiều và tối.</p>
      </div>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Controls + Content -->
    <section ref="controlsSection" class="block reveal" aria-label="Duyệt tất cả lễ hội">
    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm lễ hội…" aria-label="Tìm lễ hội" />
      </div>
      <FilterChips
        :filters="statusFilterOptions"
        :model-value="[statusFilter]"
        single-select
        aria-label="Lọc theo trạng thái"
        @update:model-value="v => statusFilter = v[0] || 'all'"
      />
      <div v-if="activeFilterCount > 0" class="active-filter-ledger" role="region" aria-label="Bộ lọc đang áp dụng">
        <span class="afl-heading">Đang lọc:</span>
        <div class="afl-chips">
          <span v-if="q.trim()" class="afl-chip">
            <span class="afl-text">Tìm: "{{ q.trim() }}"</span>
            <button type="button" class="afl-remove" aria-label="Xóa từ khóa tìm kiếm" @click="q = ''"><IconLine name="x" aria-hidden="true" /></button>
          </span>
          <span v-if="statusFilter !== 'all'" class="afl-chip">
            <span class="afl-text">{{ STATUS_LABEL[statusFilter] || statusFilter }}</span>
            <button type="button" class="afl-remove" aria-label="Bỏ lọc trạng thái" @click="statusFilter = 'all'"><IconLine name="x" aria-hidden="true" /></button>
          </span>
          <span v-if="areaFilter !== 'all'" class="afl-chip">
            <span class="afl-text">{{ AREA_META[areaFilter]?.name || areaFilter }}</span>
            <button type="button" class="afl-remove" aria-label="Bỏ lọc khu vực" @click="areaFilter = 'all'"><IconLine name="x" aria-hidden="true" /></button>
          </span>
          <button type="button" class="afl-clear-all" @click="clearFilters">Xóa tất cả</button>
        </div>
      </div>
    </div>

    <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
      <button type="button" :class="['toggle-btn', { active: view === 'list' }]" :aria-pressed="view === 'list'" @click="view = 'list'"><IconLine name="list" /> Danh sách</button>
      <button type="button" :class="['toggle-btn', { active: view === 'calendar' }]" :aria-pressed="view === 'calendar'" @click="view = 'calendar'"><IconLine name="calendar" /> Lịch</button>
    </div>

    <EmptyState v-if="fetchError" icon-name="alert-triangle" title="Không tải được lễ hội" message="Có thể mạng đang chập chờn. Thử lại nhé.">
      <template #actions>
        <button type="button" class="btn btn-outline" @click="refreshNuxtData('festivals')">Thử lại</button>
      </template>
    </EmptyState>
    <SkeletonGrid v-else-if="!data" :count="4" />

    <template v-else-if="view === 'list'">
      <p class="result-meta" aria-live="polite">{{ filtered.length }} lễ hội</p>
      <div v-if="filtered.length" class="event-list">
        <NuxtLink
          v-for="(e, index) in filtered" :key="e.id"
          :to="entityPath(e.id)"
          class="event-row"
        >
          <div class="event-date-badge lehoi-badge">
            <span class="edb-month">{{ formatMonth(e) }}</span>
            <span class="edb-day">{{ formatDay(e) }}</span>
          </div>
          <div class="event-info">
            <span v-if="eventStatus(e)" class="lehoi-status" :class="`status-${eventStatus(e)}`">{{ STATUS_LABEL[eventStatus(e)] }}</span>
            <h3>{{ e.name }}</h3>
            <p v-if="e.summary" class="event-summary">{{ truncateText(e.summary, 120) }}</p>
            <div class="event-meta">
              <span v-if="e.place_name" class="event-place"><IconLine name="pin" /> {{ e.place_name }}</span>
              <span v-if="getArea(e)" class="event-area"><IconLine :name="AREA_META[getArea(e)]?.icon || 'pin'" /> {{ AREA_META[getArea(e)]?.name }}</span>
              <span v-if="dateRange(e)" class="event-dates"><IconLine name="calendar" /> {{ dateRange(e) }}</span>
              <span v-if="e.attributes?.lunar_date" class="lunar-label"><IconLine name="moon" /> {{ e.attributes.lunar_date }}</span>
            </div>
          </div>
          <div v-if="eventImageUrl(e)" class="event-media">
            <div class="event-thumb">
              <NuxtImg v-if="isRemoteUrl(eventImageUrl(e)!)" data-event-image :src="eventImageUrl(e)!" :alt="eventImage(e)!.alt" :aria-describedby="eventDisclosureId(e, index)" loading="lazy" decoding="async" width="80" height="60" @error="hideImageError" />
              <img v-else data-event-image :src="eventImageUrl(e)!" :alt="eventImage(e)!.alt" :aria-describedby="eventDisclosureId(e, index)" loading="lazy" decoding="async" width="80" height="60" @error="hideImageError" />
            </div>
            <span class="event-disclosure"><ImageDisclosure :id="eventDisclosureId(e, index)" :descriptor="eventImage(e)!" presentation="short" /></span>
          </div>
          <button v-if="e.attributes?.date_start" type="button" class="ical-btn" title="Thêm vào lịch" aria-label="Thêm lễ hội này vào lịch" @click.stop.prevent="downloadIcal(e)"><IconLine name="calendar" /></button>
        </NuxtLink>
      </div>
      <EmptyState v-else icon-name="lantern" title="Không tìm thấy lễ hội" message="Thử thay đổi trạng thái, khu vực hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters()"><IconLine name="x" aria-hidden="true" /> Xóa bộ lọc</button>
          <button type="button" class="btn btn-outline" @click="view = 'calendar'"><IconLine name="calendar" /> Xem lịch</button>
          <NuxtLink to="/su-kien" class="btn btn-outline"><IconLine name="megaphone" /> Sự kiện</NuxtLink>
        </template>
      </EmptyState>
    </template>

    <template v-else>
      <div class="calendar">
        <div class="cal-header">
          <button type="button" class="cal-nav" @click="calMonth--" aria-label="Tháng trước">‹</button>
          <h2>Tháng {{ displayMonth }} / {{ displayYear }}</h2>
          <button type="button" class="cal-nav" @click="calMonth++" aria-label="Tháng sau">›</button>
        </div>
        <div class="cal-grid" role="grid" aria-label="Lịch lễ hội">
          <div v-for="d in ['T2','T3','T4','T5','T6','T7','CN']" :key="d" class="cal-day-label" role="columnheader">{{ d }}</div>
          <div
            v-for="(cell, i) in calendarCells" :key="i"
            class="cal-cell"
            role="gridcell"
            :tabindex="cell.events?.length ? 0 : -1"
            :class="{ 'cal-empty': !cell.day, 'cal-today': cell.isToday, 'cal-has-events': cell.events?.length }"
            :aria-label="cell.day ? `Ngày ${cell.day}${cell.events?.length ? `, ${cell.events.length} lễ hội` : ''}` : undefined"
          >
            <div v-if="cell.day" class="cal-day-row">
              <span class="cal-num">{{ cell.day }}</span>
              <span class="cal-lunar" :class="{ 'lunar-first': cell.lunarFirst, 'lunar-mid': cell.lunarMid }">{{ cell.lunar }}</span>
            </div>
            <div v-if="cell.events?.length" class="cal-events">
              <NuxtLink
                v-for="ev in cell.events.slice(0, 2)" :key="ev.id"
                :to="entityPath(ev.id)"
                class="cal-event-dot lehoi-dot"
                :title="ev.name"
              >{{ truncateText(ev.name, 18) }}</NuxtLink>
              <span v-if="cell.events.length > 2" class="cal-more">+{{ cell.events.length - 2 }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
    </section>

    <!-- Cross-links -->
    <section class="block band reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/su-kien" class="cross-card">
          <span class="cross-icon" aria-hidden="true"><IconLine name="lantern" /></span>
          <div><strong>Sự kiện</strong><p>Festival, hội chợ</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true"><IconLine name="leaf" /></span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon" aria-hidden="true"><IconLine name="calendar" /></span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true"><IconLine name="map" /></span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import type { ImageDescriptor } from '~/types/image'
import ImageDisclosure from '~/components/ImageDisclosure.vue'
import { AREA_META } from '~/composables/useConstants'
import { solarToLunar } from '~/composables/useLunar'
import { describeEntityImages, describeEntityPlaceholder } from '~/utils/imageDescriptors'
import { useId } from 'vue'

useReveal()
const { f: pc } = usePageContent('le_hoi')

const q = ref('')
const areaFilter = ref('all')
const statusFilter = ref('all')
const view = ref('list')
const controlsSection = ref<HTMLElement | null>(null)

function scrollToControls() {
  nextTick(() => controlsSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

watch([areaFilter, statusFilter], scrollToControls)

useFilterUrl({ vung: areaFilter, trang_thai: statusFilter }, { vung: 'all', trang_thai: 'all' })

const statusFilterOptions = [
  { key: 'all', label: 'Tất cả' },
  { key: 'now', label: 'Đang diễn ra', iconName: 'flame' },
  { key: 'soon', label: 'Sắp khai mạc', iconName: 'clock' },
]

const activeFilterCount = computed(() => {
  let n = 0
  if (areaFilter.value !== 'all') n++
  if (statusFilter.value !== 'all') n++
  if (q.value.trim()) n++
  return n
})

function clearFilters() {
  areaFilter.value = 'all'
  statusFilter.value = 'all'
  q.value = ''
}

const festivalAeoEntries = [
  {
    heading: 'Lễ Hội Kỳ Yên & Miếu Đình Người Kinh',
    text: 'Cầu quốc thái dân an, phong điều vũ thuận. Diễn ra trang nghiêm tại các đình làng cổ kính với nghi thức rước sắc thần, lễ tế tiền hiền và nghệ thuật hát bội truyền thống.',
  },
  {
    heading: 'Lễ Tết Chôl Chnăm Thmây & Ok Om Bok Người Khmer',
    text: 'Tết năm mới ấm áp và lễ hội cúng trăng tạ ơn đất trời. Điểm nhấn là nghi thức tắm Phật, đút cốm dẹp truyền thống và không khí rộn rã tại các ngôi chùa Khmer Nam Bộ.',
  },
  {
    heading: 'Lễ Vía Bà & Miếu Thất Phủ Người Hoa',
    text: 'Không gian văn hóa tín ngưỡng đặc sắc tại Thất Phủ Miếu (Chùa Ông), múa lân sư rồng sôi động cùng tục xin xăm, thỉnh lộc linh thiêng đầu xuân.',
  },
]

const { data, error: fetchError } = await useAsyncData('festivals', () =>
  apiFetch<{ events: Entity[] }>('/api/events?limit=200&include_past=true')
)

function categoryTokens(e: Entity) {
  const raw = (e.attributes as any)?.category_array || (e.attributes as any)?.category
  const list = Array.isArray(raw) ? raw : String(raw || '').split(/[;,|]/)
  return list.map(v => String(v).trim().toLowerCase()).filter(Boolean)
}

function eventStart(e: Entity) {
  const attrs = e.attributes as any
  return attrs?.date_start_iso || attrs?.date_start || ''
}

function eventEnd(e: Entity) {
  const attrs = e.attributes as any
  return attrs?.date_end_iso || attrs?.date_end || eventStart(e)
}

const allEvents = computed(() =>
  (data.value?.events || []).filter((e: Entity) => categoryTokens(e).includes('le-hoi'))
)

const eventImageDescriptors = computed(() => new Map(
  allEvents.value.map((event: Entity) => [event.id, describeEntityImages(event)[0] || null] as const),
))
const disclosureInstance = useId().replace(/[^A-Za-z0-9_-]+/g, '-')

function eventImage(e: Entity): ImageDescriptor | null {
  return eventImageDescriptors.value.get(e.id) || describeEntityPlaceholder(e)
}

function eventImageUrl(e: Entity): string | null {
  return eventImage(e)?.url || null
}

function eventDisclosureId(e: Entity, index: number): string {
  const token = String(e.id || 'event').trim().replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'event'
  return `event-image-disclosure-${token}-${disclosureInstance}-${index}`
}

const areaCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEvents.value) {
    const area = getArea(e)
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return Object.entries(AREA_META)
    .filter(([key]) => counts[key])
    .map(([key, meta]) => ({ key, name: meta.name, count: counts[key] || 0 }))
})

function countByArea(key: string) {
  return allEvents.value.filter((e: Entity) => getArea(e) === key).length
}

const upcoming = computed(() => {
  const now = new Date().toISOString().slice(0, 10)
  return allEvents.value
    .filter((e: Entity) => {
      const ds = eventStart(e)
      return ds && ds >= now
    })
    // A6 declutter-2: ledger tôn trọng filter đang chọn (trước đây tĩnh trong khi
    // grid động — friction). Khi cả hai = 'all' hành vi y hệt cũ.
    .filter((e: Entity) => areaFilter.value === 'all' || getArea(e) === areaFilter.value)
    .filter((e: Entity) => statusFilter.value === 'all' || eventStatus(e) === statusFilter.value)
    .sort((a: Entity, b: Entity) => eventStart(a).localeCompare(eventStart(b)))
    .slice(0, 6)
})

const filtered = computed(() => {
  let list = allEvents.value
  if (statusFilter.value !== 'all') {
    list = list.filter((e: Entity) => eventStatus(e) === statusFilter.value)
  }
  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => getArea(e) === areaFilter.value)
  }
  if (q.value.trim()) {
    const kw = q.value.toLowerCase()
    list = list.filter((e: Entity) => (e.name || '').toLowerCase().includes(kw) || (e.summary || '').toLowerCase().includes(kw))
  }
  return list
})

const getArea = getEntityArea

const formatMonth = formatEventMonth
const formatDay = formatEventDay
const dateRange = eventDateRange

function hideImageError(ev: Event | string) {
  if (typeof ev === 'string') return
  const target = ev.target as HTMLImageElement | null
  if (target) target.style.display = 'none'
}

const todayStr = new Date().toISOString().slice(0, 10)

function eventStatus(e: Entity): '' | 'now' | 'soon' {
  const attrs = e.attributes || {}
  const ds = eventStart(e)
  if (!ds) return ''
  const de = eventEnd(e) || ds
  if (todayStr >= ds && todayStr <= de) return 'now'
  if (ds > todayStr) {
    const days = Math.round((new Date(ds + 'T00:00:00').getTime() - new Date(todayStr + 'T00:00:00').getTime()) / 86400000)
    if (days <= 14) return 'soon'
  }
  return ''
}

const STATUS_LABEL: Record<string, string> = { now: 'Đang diễn ra', soon: 'Sắp khai mạc' }



const { calMonth, displayMonth, displayYear, calendarCells } = useEventCalendar(allEvents)

// ── "Đất này giữ lịch riêng" — living-calendar hero devices (additive; does not
// fork eventStatus/filtered/categoryTokens above). ──

const now = new Date()
const todayLunar = solarToLunar(now.getDate(), now.getMonth() + 1, now.getFullYear())
const todayLunarLabel = `${todayLunar.day}/${todayLunar.month}${todayLunar.leap ? ' (nhuận)' : ''}`
const todayGregorianLabel = now.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

/**
 * Moon-phase silhouette as a pure SVG path (r=13, centred at 16,16). Terminator is a
 * half-ellipse whose horizontal radius is r·cos(phaseAngle): day 0 → new moon (dark),
 * day ~14.77 → full moon (fully lit), day ~29.53 → new moon again. Right limb lit while
 * waxing (phase ≤ π), left limb lit while waning (phase > π) — standard convention.
 * Verified against the analytic illuminated-fraction formula (1−cos(phase))/2 via an
 * SVG-spec-accurate arc-flattening + shoelace-area check (max error 0.0002 across a full cycle).
 */
function moonPhasePath(lunarDay: number): string {
  const r = 13
  const cx = 16
  const cy = 16
  const phase = (lunarDay / 29.53) * Math.PI * 2 // 0..2π across the lunar month
  const rx = Math.abs(r * Math.cos(phase))
  const rightLit = phase <= Math.PI
  const gibbous = phase > Math.PI / 2 && phase < Math.PI * 1.5
  const outerSweep = rightLit ? 1 : 0
  // Crescent: terminator curves opposite the outer sweep (concave, subtracts from a half-disc).
  // Gibbous: terminator curves the same way as the outer sweep (convex, adds to a half-disc).
  const terminatorSweep = gibbous ? outerSweep : (1 - outerSweep)
  return `M ${cx} ${cy - r} A ${r} ${r} 0 0 ${outerSweep} ${cx} ${cy + r} A ${rx} ${r} 0 0 ${terminatorSweep} ${cx} ${cy - r} Z`
}
const todayMoonPath = computed(() => moonPhasePath(todayLunar.day))

/** Countdown text for an upcoming/ongoing entry: "còn N ngày" / "còn N giờ" / "ngày cuối". */
function countdownLabel(e: Entity): string {
  const ds = eventStart(e)
  const de = eventEnd(e) || ds
  if (!ds) return ''
  const nowMs = Date.now()
  const startMs = new Date(ds + 'T00:00:00').getTime()
  const endMs = new Date(de + 'T23:59:59').getTime()
  if (nowMs >= startMs && nowMs <= endMs) {
    const hoursLeft = Math.round((endMs - nowMs) / 3600000)
    return hoursLeft <= 24 ? `còn ${Math.max(1, hoursLeft)} giờ` : 'đang diễn ra'
  }
  const daysLeft = Math.ceil((startMs - nowMs) / 86400000)
  return daysLeft <= 0 ? 'hôm nay' : `còn ${daysLeft} ngày`
}

/** The single most imminent "now" (preferred) or "soon" entry — drives the hero live banner. */
const liveNow = computed(() => {
  const nowEntry = allEvents.value.find((e: Entity) => eventStatus(e) === 'now')
  if (nowEntry) return nowEntry
  return upcoming.value.find((e: Entity) => {
    const ds = eventStart(e)
    if (!ds) return false
    const days = Math.ceil((new Date(ds + 'T00:00:00').getTime() - Date.now()) / 86400000)
    return days <= 3
  }) || null
})

/** Lunar-ribbon ticks: next 3 upcoming festivals positioned by lunar day-of-month (1–30). */
const ribbonTicks = computed(() => {
  return upcoming.value.slice(0, 3).map((e: Entity) => {
    const ds = eventStart(e)
    let lunarPos = todayLunar.day
    if (ds) {
      const d = new Date(ds + 'T00:00:00')
      const l = solarToLunar(d.getDate(), d.getMonth() + 1, d.getFullYear())
      lunarPos = l.day
    }
    return {
      id: e.id,
      name: e.name,
      hook: e.summary ? truncateText(e.summary, 70) : (e.place_name || ''),
      pct: Math.min(97, Math.max(3, (lunarPos / 30) * 100)),
    }
  })
})

/** Off-season mini-preview: next 3 festivals by name when nothing is upcoming — replaces a dead-end apology. */
const offseasonNext = computed(() => {
  return allEvents.value
    .filter((e: Entity) => eventStart(e))
    .sort((a: Entity, b: Entity) => eventStart(a).localeCompare(eventStart(b)))
    .slice(0, 3)
})

/**
 * Bulk .ics: one VCALENDAR with a VEVENT per upcoming festival — client-side only, no backend change.
 * Line assembly lives in utils/safe.ts so the all-day DTEND rule (exclusive end = last day + 1,
 * RFC 5545 §3.6.1) has a single implementation shared with su-kien and the per-row button.
 */
function downloadIcalBulk() {
  const items = allEvents.value
    .filter((e: Entity) => {
      const ds = eventStart(e)
      return ds && ds >= todayStr
    })
    .map((e: Entity) => ({
      id: e.id,
      name: e.name,
      summary: e.summary,
      place_name: e.place_name,
      dateStart: eventStart(e),
      dateEnd: eventEnd(e),
    }))
  downloadIcsBundle(items, 'le-hoi-sap-toi.ics')
}

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
  ogUrl: canonicalUrl('/le-hoi'),
  twitterCard: 'summary_large_image',
})

const festivalListSchema = computed(() => {
  const items = allEvents.value.slice(0, 30).map((e: Entity, i: number) => ({
    '@type': 'ListItem',
    position: i + 1,
    item: {
      '@type': 'Event',
      name: e.name,
      ...(eventStart(e) ? { startDate: eventStart(e) } : {}),
      ...(eventEnd(e) ? { endDate: eventEnd(e) } : {}),
      url: `https://vinhlong360.vn${entityPath(e.id)}`,
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      ...(e.place_name ? { location: { '@type': 'Place', name: e.place_name } } : {}),
    },
  }))
  if (!items.length) return ''
  return safeJsonLd({
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Lễ hội truyền thống',
    numberOfItems: allEvents.value.length,
    itemListOrder: 'https://schema.org/ItemListOrderAscending',
    itemListElement: items,
  })
})

useHead(() => {
  const pageUrl = canonicalUrl('/le-hoi')
  const graphNodes: any[] = [
    buildWebSiteSchema(),
    buildOrganizationSchema(),
    {
      '@type': 'CollectionPage',
      '@id': `${pageUrl}#collection`,
      name: 'Lễ hội truyền thống Vĩnh Long',
      description: 'Lễ hội đình miếu, lễ Khmer, Nghinh Ông, giỗ danh nhân — truyền thống văn hóa tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
      url: pageUrl,
      numberOfItems: allEvents.value.length,
      isPartOf: { '@id': `${SITE_URL}/#website` },
      about: {
        '@type': 'Thing',
        name: 'Lễ hội truyền thống Vĩnh Long',
        description: 'Văn hóa ba dòng sông giao thoa giữa cộng đồng Kinh, Khmer và Hoa.',
      },
      speakable: buildSpeakableSpecification(['.page-article', 'h1', '.pull-quote', '.etiquette-box', '.catalog-aeo-plaque__title', '.catalog-aeo-plaque__dek']),
    },
  ]

  const faqItems: FaqItem[] = [
    {
      q: 'Văn hóa lễ hội Vĩnh Long có những nét đặc trưng gì?',
      a: 'Vĩnh Long là nơi giao thoa văn hóa độc đáo của ba dân tộc Kinh, Khmer và Hoa với các lễ hội đình miếu Kỳ Yên, lễ hội Ok Om Bok cúng trăng, Chôl Chnăm Thmây và lễ hội Nghinh Ông miền duyên hải.',
    },
    {
      q: 'Du khách tham gia lễ hội ở Vĩnh Long cần lưu ý những quy tắc gì?',
      a: 'Hầu hết các lễ hội truyền thống mở cửa tự do không thu phí. Du khách nên mặc trang phục lịch sự khi vào chánh điện; tháo giày dép khi vào chùa Khmer và nên tham dự các nghi thức chính vào buổi sáng.',
    },
    {
      q: 'Làm thế nào để theo dõi lịch diễn ra các lễ hội theo cả âm lịch và dương lịch?',
      a: 'Trang Lễ hội trên VinhLong360 tích hợp bảng chuyển đổi âm - dương lịch, chu kỳ trăng và tải lịch nhắc sự kiện dạng tập tin .ics về điện thoại tiện lợi.',
    },
  ]
  const faqNode = buildFaqPageSchema(faqItems, `${pageUrl}#faq`)
  if (faqNode) graphNodes.push(faqNode)

  return {
    link: [{ rel: 'canonical', href: pageUrl }],
    script: [
      {
        type: 'application/ld+json',
        innerHTML: safeJsonLd({
          '@context': 'https://schema.org',
          '@graph': graphNodes,
        }),
      },
      ...(festivalListSchema.value ? [{ type: 'application/ld+json' as const, innerHTML: festivalListSchema.value }] : []),
    ],
  }
})
</script>

<!-- events.css nạp theo route (bỏ khỏi global entry.css) — dùng .event-*/.cal-*/.toggle-btn -->
<style src="~/assets/css/events.css"></style>

<style>
.lehoi-badge {
  background: var(--color-brand);
}
/* Không cần bản .dark riêng: --color-brand đã đậm ở cả hai chế độ nên chữ
   trắng đạt 10.12:1, và ranh giới do vòng viền ở .dark .event-date-badge lo. */
.lehoi-dot {
  background: var(--color-brand);
}

/* Hero depth & cultural warmth: layered scrim over the festival gradient */
.catalog-hero.cat-festival {
  position: relative;
  background:
    radial-gradient(120% 90% at 12% 0%, rgba(var(--accent-rgb), .07) 0%, transparent 55%),
    linear-gradient(135deg, rgba(var(--color-brand-rgb), .06) 0%, rgba(var(--accent-rgb), .08) 100%);
}
.dark .catalog-hero.cat-festival {
  background:
    radial-gradient(120% 90% at 12% 0%, rgba(var(--accent-rgb), .05) 0%, transparent 55%),
    linear-gradient(135deg, rgba(var(--white-rgb),.03) 0%, rgba(var(--white-rgb),.01) 100%);
}

/* Time-aware status label above an event name */
.lehoi-status {
  display: inline-block;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: .02em;
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  margin-bottom: var(--space-1);
}
.lehoi-status.status-soon {
  background: rgba(var(--accent-rgb), .14);
  color: var(--accent-dark);
}
.lehoi-status.status-now {
  background: rgba(var(--secondary-rgb), .14);
  color: var(--secondary-dark);
  /* Settle-then-still: a multi-day festival can stay "Đang diễn ra" for days —
     pulsing the whole time would blow the motion budget. Play the attention-cue
     3× (~8.4s) on first paint, then rest still like every other settled badge. */
  animation: lehoi-status-pulse 2.8s var(--ease-out-expo) 3;
}
.dark .lehoi-status.status-soon { background: rgba(var(--accent-rgb), .22); color: var(--accent); }
.dark .lehoi-status.status-now { background: rgba(var(--secondary-rgb), .22); color: var(--secondary); }
@keyframes lehoi-status-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(var(--secondary-rgb), .0); }
  50% { box-shadow: 0 0 0 4px rgba(var(--secondary-rgb), .12); }
}

/* Off-season note when there are no upcoming festivals */
.lehoi-offseason {
  margin: 0;
  padding: var(--space-4) var(--space-5);
  font-size: var(--text-sm);
  color: var(--ink-tertiary, var(--muted));
  background: rgba(var(--accent-rgb), .08);
  border-radius: var(--radius-surface);
  border: 1px solid rgba(var(--accent-rgb), .2);
}

.dark .lehoi-offseason { background: rgba(var(--accent-rgb), .12); border-color: rgba(var(--accent-rgb), .3); }

/* Thumbnail placeholder colour if image fails / while loading */
.event-thumb { background: var(--bg-alt); }

@media (prefers-reduced-motion: reduce) {
  .lehoi-status.status-now { animation: none; }
}

</style>
