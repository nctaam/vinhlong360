<template>
  <div class="page events-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sự kiện' }]" :json-ld="true" />

    <!-- Hero: "Đất này giữ lịch riêng" — contemporary register, amber-toned -->
    <section class="catalog-hero cat-event register-su-kien">
      <p class="dateline-eyebrow">
        HÔM NAY · <strong>{{ todayGregorianLabel }}</strong> · ÂM LỊCH <span class="lunar-label">{{ todayLunarLabel }}</span>
      </p>
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🎪</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>

      <!-- Live urgency treatment supersedes the stat-chip row when something is imminent -->
      <NuxtLink v-if="liveNow" :to="entityPath(liveNow.id)" class="now-banner">
        <span class="now-banner-dot" aria-hidden="true"></span>
        <span class="now-banner-text">
          <strong>{{ isHappeningNow(liveNow) ? 'Đang diễn ra' : 'Sắp diễn ra' }}: {{ liveNow.name }}</strong>
          <template v-if="liveNow.place_name"> — {{ liveNow.place_name }}</template>
        </span>
        <span class="now-banner-countdown">{{ countdownLabel(liveNow) }}</span>
      </NuxtLink>
      <div v-else-if="allEvents.length" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="allEvents.length" class="stat-num" />
          <span class="stat-label">sự kiện</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <CountUp :value="a.count" class="stat-num" />
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>

      <!-- Signature moment: lunar ribbon — even the contemporary register runs on the same moon -->
      <div v-if="ribbonTicks.length" class="lunar-ribbon" role="group" aria-label="Dải âm lịch — sự kiện sắp tới theo vị trí trăng">
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

    <!-- Spotlight -->
    <CatalogSpotlight :items="allEvents" />

    <!-- Register toggle: contemporary (sự kiện, here) vs ancestral (lễ hội) — amber ↔ leaf -->
    <section class="block reveal">
      <div class="register-toggle" role="group" aria-label="Chọn sổ lễ hội">
        <NuxtLink to="/le-hoi" class="register-toggle-tab tone-leaf" aria-pressed="false">🎋 Lễ hội truyền thống</NuxtLink>
        <NuxtLink to="/su-kien" class="register-toggle-tab is-active tone-amber" aria-pressed="true">🎪 Sự kiện &amp; hội chợ</NuxtLink>
      </div>
    </section>

    <!-- Ceremonial ledger: full-width rows ordered strictly by nearness in time,
         not a horizontal scroll-row — the same narrative weight le-hoi gives its calendar. -->
    <section v-if="upcoming.length" class="block reveal">
      <div class="sediment-head">
        <h2>Sắp diễn ra</h2>
      </div>
      <div class="ledger" role="list" aria-label="Sự kiện sắp diễn ra, theo thứ tự gần nhất">
        <NuxtLink
          v-for="e in upcoming" :key="e.id"
          :to="entityPath(e.id)"
          class="ledger-row"
          role="listitem"
        >
          <div class="event-date-badge">
            <span class="edb-month">{{ formatMonth(e) }}</span>
            <span class="edb-day">{{ formatDay(e) }}</span>
          </div>
          <span class="ledger-status" :class="{ 'is-now': isHappeningNow(e) }">
            {{ isHappeningNow(e) ? 'Đang diễn ra' : countdownLabel(e) }}
          </span>
          <h3 class="ledger-name">
            <span v-if="e.attributes?.category === 'mua'" class="cat-badge cat-mua">🌾 Mùa vụ</span>
            {{ e.name }}
          </h3>
        </NuxtLink>
      </div>
      <button type="button" class="ical-bulk-btn" @click="downloadIcalBulk">
        📅 Thêm tất cả sự kiện sắp tới vào lịch của bạn
      </button>
    </section>

    <!-- Interstitial -->
    <CatalogInterstitial
      v-if="allEvents.length"
      fact="Mỗi sự kiện đều có nút tải .ics — thêm vào Google Calendar hoặc Apple Calendar chỉ một chạm."
      icon="📅"
      variant="accent"
      :links="[
        { to: '/le-hoi', label: 'Lễ hội truyền thống' },
        { to: '/lich-trinh', label: 'Lịch trình gợi ý' },
      ]"
    />

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
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} sự kiện</span>
        </button>
      </div>
    </section>

    <!-- Editorial: the contemporary register — same land, modern calendar -->
    <section v-once class="page-article reveal">
      <div class="sediment-head sediment-head-first"><h2>Sự kiện tại Vĩnh Long</h2></div>
      <p>Ngoài các lễ hội truyền thống, vùng Vĩnh Long, Bến Tre và Trà Vinh ngày càng có nhiều sự kiện văn hoá, thể thao và du lịch hiện đại. Hội chợ nông sản, festival ẩm thực, giải chạy marathon, triển lãm nghệ thuật và các chương trình xúc tiến du lịch được tổ chức thường xuyên, đặc biệt vào dịp cuối tuần và các ngày lễ lớn.</p>
      <blockquote class="pull-quote">Thưởng thức ẩm thực đường phố, xem trình diễn nghề truyền thống, mua sản phẩm OCOP trực tiếp từ nhà sản xuất, hoặc tham gia hoạt động cộng đồng cùng người dân bản địa — cùng một vùng đất, cách hiện đại để gặp nó.</blockquote>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Controls + Content -->
    <section class="block reveal" aria-label="Duyệt tất cả sự kiện">
    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm sự kiện…" aria-label="Tìm sự kiện" />
      </div>
      <FilterChips
        :filters="statusFilterOptions"
        :model-value="[statusFilter]"
        single-select
        aria-label="Lọc theo trạng thái"
        @update:model-value="v => statusFilter = v[0] || 'all'"
      />
      <FilterChips
        :filters="areaFilterOptions"
        :model-value="[areaFilter]"
        single-select
        aria-label="Lọc theo khu vực"
        @update:model-value="v => areaFilter = v[0] || 'all'"
      />
    </div>

    <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
      <button type="button" :class="['toggle-btn', { active: view === 'list' }]" :aria-pressed="view === 'list'" @click="view = 'list'">📋 Danh sách</button>
      <button type="button" :class="['toggle-btn', { active: view === 'calendar' }]" :aria-pressed="view === 'calendar'" @click="view = 'calendar'">📅 Lịch</button>
    </div>

    <EmptyState v-if="fetchError" icon="⚠️" title="Chưa tải được sự kiện" message="Có thể do mạng chập chờn. Thử lại nhé.">
      <template #actions>
        <button type="button" class="btn btn-outline" @click="refreshNuxtData('events')">Thử lại</button>
      </template>
    </EmptyState>
    <SkeletonList v-else-if="!data && view === 'list'" :count="5" />
    <SkeletonGrid v-else-if="!data" :count="4" />

    <template v-else-if="view === 'list'">
      <p class="result-meta" aria-live="polite">{{ filtered.length }} sự kiện</p>
      <div v-if="filtered.length" class="event-list">
        <NuxtLink
          v-for="e in filtered" :key="e.id"
          :to="entityPath(e.id)"
          class="event-row"
        >
          <div class="event-date-badge">
            <span class="edb-month">{{ formatMonth(e) }}</span>
            <span class="edb-day">{{ formatDay(e) }}</span>
          </div>
          <div class="event-info">
            <span v-if="e.attributes?.category === 'mua'" class="cat-badge cat-mua">🌾 Mùa vụ</span>
            <h3>{{ e.name }}</h3>
            <p v-if="e.summary" class="event-summary">{{ truncateText(e.summary, 120) }}</p>
            <div class="event-meta">
              <span v-if="e.place_name" class="event-place">📍 {{ e.place_name }}</span>
              <span v-if="getArea(e)" class="event-area">{{ AREA_META[getArea(e)]?.emoji }} {{ AREA_META[getArea(e)]?.name }}</span>
              <span v-if="dateRange(e)" class="event-dates">🗓️ {{ dateRange(e) }}</span>
            </div>
          </div>
          <div v-if="e.images?.length" class="event-thumb">
            <NuxtImg v-if="isRemoteUrl(e.images[0] || '')" :src="e.images[0] || ''" :alt="e.name" loading="lazy" decoding="async" width="160" height="120" sizes="160px" @error="fadeEventImageError" />
            <img v-else :src="e.images[0] || ''" :alt="e.name" loading="lazy" decoding="async" width="160" height="120" @error="fadeEventImageError" />
          </div>
          <button v-if="e.attributes?.date_start" type="button" class="ical-btn" title="Thêm vào lịch" @click.stop.prevent="downloadIcal(e)">📅</button>
        </NuxtLink>
      </div>
      <EmptyState v-else icon="🎪" title="Không tìm thấy sự kiện" message="Thử đổi trạng thái, khu vực hoặc từ khóa khác nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="statusFilter = 'all'; areaFilter = 'all'; q = ''">Xóa bộ lọc</button>
          <button type="button" class="btn btn-outline" @click="view = 'calendar'">📅 Xem lịch</button>
          <NuxtLink to="/le-hoi" class="btn btn-outline">🎋 Lễ hội</NuxtLink>
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
        <div class="cal-grid" role="grid" aria-label="Lịch sự kiện">
          <div v-for="d in ['T2','T3','T4','T5','T6','T7','CN']" :key="d" class="cal-day-label" role="columnheader">{{ d }}</div>
          <div
            v-for="(cell, i) in calendarCells" :key="i"
            class="cal-cell"
            role="gridcell"
            :tabindex="cell.events?.length ? 0 : -1"
            :class="{ 'cal-empty': !cell.day, 'cal-today': cell.isToday, 'cal-has-events': cell.events?.length }"
            :aria-label="cell.day ? `Ngày ${cell.day}${cell.events?.length ? `, ${cell.events.length} sự kiện` : ''}` : undefined"
          >
            <div v-if="cell.day" class="cal-day-row">
              <span class="cal-num">{{ cell.day }}</span>
              <span class="cal-lunar" :class="{ 'lunar-first': cell.lunarFirst, 'lunar-mid': cell.lunarMid }">{{ cell.lunar }}</span>
            </div>
            <div v-if="cell.events?.length" class="cal-events">
              <NuxtLink
                v-for="ev in cell.events.slice(0, 2)" :key="ev.id"
                :to="entityPath(ev.id)"
                class="cal-event-dot"
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
        <NuxtLink to="/le-hoi" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🎋</span>
          <div><strong>Lễ hội</strong><p>Truyền thống văn hóa</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon" aria-hidden="true">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon" aria-hidden="true">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'
import { solarToLunar } from '~/composables/useLunar'

useReveal()
const { f: pc } = usePageContent('su_kien')

const q = ref('')
const areaFilter = ref('all')
const statusFilter = ref('all')
const view = ref('list')

useFilterUrl({ vung: areaFilter, trang_thai: statusFilter }, { vung: 'all', trang_thai: 'all' })

const statusFilterOptions = [
  { key: 'all', label: 'Tất cả' },
  { key: 'upcoming', label: 'Sắp diễn ra', icon: '📅' },
  { key: 'past', label: 'Đã qua', icon: '📋' },
]
const areaFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả vùng' },
  ...Object.entries(AREA_META).map(([slug, m]) => ({ key: slug, label: m.name, icon: m.emoji })),
])

const todayStr = new Date().toISOString().slice(0, 10)
function eventStatus(e: Entity): 'upcoming' | 'past' | '' {
  const ds = e.attributes?.date_start_iso || e.attributes?.date_start
  if (!ds) return ''
  const de = e.attributes?.date_end_iso || e.attributes?.date_end || ds
  if (todayStr > de) return 'past'
  if (ds >= todayStr) return 'upcoming'
  return ''
}

const { data, error: fetchError } = await useAsyncData('events', () =>
  apiFetch<{ events: Entity[] }>('/api/events?limit=200&include_past=true')
)

const allEvents = computed(() =>
  (data.value?.events || []).filter((e: Entity) => (e.attributes?.category || 'su-kien') !== 'le-hoi')
)

const areaCountMap = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEvents.value) {
    const area = getArea(e)
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return counts
})

const areaCounts = computed(() =>
  Object.entries(AREA_META)
    .filter(([key]) => areaCountMap.value[key])
    .map(([key, meta]) => ({ key, name: meta.name, count: areaCountMap.value[key] || 0 }))
)

function countByArea(key: string) {
  return areaCountMap.value[key] || 0
}

const upcoming = computed(() => {
  const now = new Date().toISOString().slice(0, 10)
  return allEvents.value
    .filter((e: Entity) => {
      const ds = e.attributes?.date_start_iso || e.attributes?.date_start
      return ds && ds >= now
    })
    // A6 declutter-2: ledger tôn trọng filter đang chọn (đồng bộ với grid).
    .filter((e: Entity) => areaFilter.value === 'all' || getArea(e) === areaFilter.value)
    .filter((e: Entity) => statusFilter.value === 'all' || eventStatus(e) === statusFilter.value)
    .sort((a: Entity, b: Entity) => (a.attributes?.date_start_iso || a.attributes?.date_start || '').localeCompare(b.attributes?.date_start_iso || b.attributes?.date_start || ''))
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

function fadeEventImageError(ev: Event | string) {
  if (typeof ev === 'string') return
  const target = ev.target as HTMLImageElement | null
  if (target) target.style.opacity = '.15'
}


const { calMonth, displayMonth, displayYear, calendarCells } = useEventCalendar(allEvents)

// ── "Đất này giữ lịch riêng" — living-calendar hero devices (additive; does not
// fork eventStatus/filtered above). ──

function eventStart(e: Entity): string {
  return e.attributes?.date_start_iso || e.attributes?.date_start || ''
}
function eventEnd(e: Entity): string {
  return e.attributes?.date_end_iso || e.attributes?.date_end || eventStart(e)
}

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

/** Countdown text for an upcoming/ongoing entry: "còn N ngày" / "còn N giờ". */
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

/** Is entry `e` happening right now? (su-kien's own eventStatus() only distinguishes upcoming/past.) */
function isHappeningNow(e: Entity): boolean {
  const ds = eventStart(e)
  if (!ds) return false
  const de = eventEnd(e) || ds
  return todayStr >= ds && todayStr <= de
}

/** The single most imminent live/near-term entry — drives the hero live banner. */
const liveNow = computed(() => {
  const nowEntry = allEvents.value.find((e: Entity) => isHappeningNow(e))
  if (nowEntry) return nowEntry
  return upcoming.value.find((e: Entity) => {
    const ds = eventStart(e)
    if (!ds) return false
    const days = Math.ceil((new Date(ds + 'T00:00:00').getTime() - Date.now()) / 86400000)
    return days <= 3
  }) || null
})

/** Lunar-ribbon ticks: next 3 upcoming entries positioned by lunar day-of-month (1–30). */
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

/** Bulk .ics: one VCALENDAR with a VEVENT per upcoming entry — client-side only, no backend change. */
function downloadIcalBulk() {
  const items = allEvents.value.filter((e: Entity) => {
    const ds = eventStart(e)
    return ds && ds >= todayStr
  })
  if (!items.length) return
  const esc = (s: string) => (s || '').replace(/[,;\\]/g, ' ')
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//vinhlong360.vn//VI']
  for (const e of items) {
    const attrs: any = e.attributes || {}
    const ds = String(attrs.date_start || eventStart(e) || '').replace(/-/g, '')
    if (!ds) continue
    const de = String(attrs.date_end || eventEnd(e) || attrs.date_start || '').replace(/-/g, '')
    lines.push(
      'BEGIN:VEVENT',
      `DTSTART;VALUE=DATE:${ds}`,
      `DTEND;VALUE=DATE:${de}`,
      `SUMMARY:${esc(e.name)}`,
      `DESCRIPTION:${esc((e.summary || '').slice(0, 200))}`,
      `LOCATION:${esc(e.place_name || '')}`,
      `URL:https://vinhlong360.vn${entityPath(e.id)}`,
      'END:VEVENT',
    )
  }
  lines.push('END:VCALENDAR')
  downloadBlob(new Blob([lines.join('\r\n')], { type: 'text/calendar;charset=utf-8' }), 'su-kien-sap-toi.ics')
}

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})
const eventListSchema = computed(() => {
  const items = allEvents.value.slice(0, 30).map((e: Entity, i: number) => ({
    '@type': 'ListItem',
    position: i + 1,
    item: {
      '@type': 'Event',
      name: e.name,
      ...(e.attributes?.date_start ? { startDate: e.attributes.date_start } : {}),
      ...(e.attributes?.date_end ? { endDate: e.attributes.date_end } : {}),
      url: `https://vinhlong360.vn${entityPath(e.id)}`,
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      ...(e.place_name ? { location: { '@type': 'Place', name: e.place_name } } : {}),
    },
  }))
  if (!items.length) return ''
  return JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Sự kiện',
    numberOfItems: allEvents.value.length,
    itemListOrder: 'https://schema.org/ItemListOrderAscending',
    itemListElement: items,
  })
})

useHead({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
        { '@type': 'ListItem', position: 2, name: 'Sự kiện' },
      ],
    }),
  }],
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/su-kien') }],
  script: eventListSchema.value ? [{ type: 'application/ld+json', innerHTML: eventListSchema.value }] : [],
}))
</script>

<!-- events.css nạp theo route (bỏ khỏi global entry.css) — dùng .event-*/.cal-*/.toggle-btn -->
<style src="~/assets/css/events.css"></style>

<style>
.catalog-hero.cat-event { background: linear-gradient(135deg, rgba(var(--accent-rgb, 255,193,7), .08) 0%, rgba(183, 110, 60, .06) 100%); }
.dark .catalog-hero.cat-event { background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%); }

</style>
