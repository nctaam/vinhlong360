<template>
  <div class="page events-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lễ hội' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-festival">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🎋</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEvents.length" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="allEvents.length" class="stat-num" />
          <span class="stat-label">lễ hội</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <CountUp :value="a.count" class="stat-num" />
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>
    </section>

    <!-- Spotlight nổi bật -->
    <CatalogSpotlight :items="allEvents" />

    <!-- Upcoming / Featured -->
    <section v-if="upcoming.length" class="block reveal">
      <div class="section-head">
        <h2>Sắp diễn ra</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Lễ hội sắp diễn ra" tabindex="0">
        <NuxtLink
          v-for="e in upcoming" :key="e.id"
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
            <div class="event-meta">
              <span v-if="e.place_name" class="event-place">📍 {{ e.place_name }}</span>
              <span v-if="e.attributes?.lunar_date" class="event-lunar">🌙 {{ e.attributes.lunar_date }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Off-season note (no upcoming festivals) -->
    <section v-else-if="data && !fetchError && allEvents.length" class="block reveal">
      <p class="lehoi-offseason">🌙 Lễ hội sẽ trở lại mùa sau — xem lịch bên dưới để biết các mùa lễ hội trong năm.</p>
    </section>

    <!-- Region quick-picks -->
    <section class="block band reveal">
      <div class="section-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string)"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} lễ hội</span>
        </button>
      </div>
    </section>

    <!-- Interstitial -->
    <CatalogInterstitial
      fact="Vùng đất ba tỉnh là nơi giao thoa văn hoá Kinh – Khmer – Hoa, tạo nên hệ thống lễ hội đa dạng hiếm có trong cả nước."
      icon="🎋"
      variant="warm"
      :links="[{ to: '/du-lich', label: 'Trải nghiệm du lịch' }, { to: '/ban-do', label: 'Xem trên bản đồ' }]"
    />

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <h2>Văn hoá lễ hội miền Tây</h2>
      <p>Vùng đất Vĩnh Long, Bến Tre và Trà Vinh là nơi giao thoa của ba nền văn hoá: Kinh, Khmer và Hoa. Mỗi cộng đồng mang đến một hệ thống lễ hội riêng biệt, tạo nên bức tranh văn hoá đa dạng hiếm có trong cả nước. Từ đình miếu Kinh ven sông đến chùa Khmer tháp nhọn, từ hội quán Hoa rực rỡ đèn lồng đến giỗ kỵ danh nhân — lễ hội ở đây không chỉ là dịp vui mà là sợi dây kết nối cộng đồng qua nhiều thế hệ.</p>

      <h2>Lễ hội tiêu biểu</h2>
      <p><strong>Lễ Kỳ Yên</strong> là lễ hội phổ biến nhất, tổ chức tại đình làng khắp vùng vào đầu năm âm lịch, cầu cho mưa thuận gió hoà, mùa màng bội thu. <strong>Ok Om Bok</strong> (lễ Cúng Trăng) là lễ hội đặc trưng của người Khmer Trà Vinh, tổ chức vào rằm tháng 10 âm lịch với đua ghe ngo trên sông Maspéro. <strong>Lễ Nghinh Ông</strong> diễn ra ở các vùng ven biển, tôn vinh Cá Ông (cá voi) — vị thần bảo hộ ngư dân.</p>
      <p>Ngoài ra còn có các lễ giỗ danh nhân như giỗ Thủ khoa Bùi Hữu Nghĩa (Vĩnh Long), giỗ cụ Phan Thanh Giản, và nhiều lễ hội nông nghiệp như Hội trái cây ngon, Lễ hội bánh dân gian Nam Bộ. Mỗi lễ hội thường kéo dài 2–3 ngày với phần lễ trang nghiêm và phần hội sôi nổi.</p>

      <h2>Đi lễ hội — cần biết gì?</h2>
      <p>Hầu hết lễ hội truyền thống mở cửa tự do, không thu phí. Trang phục lịch sự khi vào khu vực chánh điện hoặc chánh đường. Nếu đến chùa Khmer, nên bỏ giày dép trước khi vào và tránh chạm đầu người khác. Thời gian tốt nhất để xem nghi lễ chính thường là buổi sáng; phần hội chợ, văn nghệ diễn ra chiều và tối.</p>
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

    <EmptyState v-if="fetchError" icon="⚠️" title="Không tải được lễ hội" message="Có thể mạng đang chập chờn. Thử lại nhé.">
      <template #actions>
        <button type="button" class="btn btn-outline" @click="refreshNuxtData('festivals')">Thử lại</button>
      </template>
    </EmptyState>
    <SkeletonGrid v-else-if="!data" :count="4" />

    <template v-else-if="view === 'list'">
      <p class="result-meta" aria-live="polite">{{ filtered.length }} lễ hội</p>
      <div v-if="filtered.length" class="event-list">
        <NuxtLink
          v-for="e in filtered" :key="e.id"
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
              <span v-if="e.place_name" class="event-place">📍 {{ e.place_name }}</span>
              <span v-if="getArea(e)" class="event-area">{{ AREA_META[getArea(e)]?.emoji }} {{ AREA_META[getArea(e)]?.name }}</span>
              <span v-if="dateRange(e)" class="event-dates">🗓️ {{ dateRange(e) }}</span>
              <span v-if="e.attributes?.lunar_date" class="event-lunar">🌙 {{ e.attributes.lunar_date }}</span>
            </div>
          </div>
          <div v-if="e.images?.length" class="event-thumb">
            <NuxtImg v-if="isRemoteUrl(e.images[0] || '')" :src="e.images[0] || ''" :alt="e.name" loading="lazy" decoding="async" width="80" height="60" @error="hideImageError" />
            <img v-else :src="e.images[0] || ''" :alt="e.name" loading="lazy" decoding="async" width="80" height="60" @error="hideImageError" />
          </div>
          <button v-if="e.attributes?.date_start" type="button" class="ical-btn" title="Thêm vào lịch" @click.stop.prevent="downloadIcal(e)">📅</button>
        </NuxtLink>
      </div>
      <EmptyState v-else icon="🎋" title="Không tìm thấy lễ hội" message="Thử thay đổi trạng thái, khu vực hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="statusFilter = 'all'; areaFilter = 'all'; q = ''">Xóa bộ lọc</button>
          <button type="button" class="btn btn-outline" @click="view = 'calendar'">📅 Xem lịch</button>
          <NuxtLink to="/su-kien" class="btn btn-outline">🎪 Sự kiện</NuxtLink>
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
          <span class="cross-icon" aria-hidden="true">🎪</span>
          <div><strong>Sự kiện</strong><p>Festival, hội chợ</p></div>
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
import { lunarLabel, isLunarFirstDay, isLunarFull } from '~/composables/useLunar'

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
  { key: 'now', label: 'Đang diễn ra', icon: '🔴' },
  { key: 'soon', label: 'Sắp khai mạc', icon: '🟡' },
]
const areaFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả vùng' },
  ...Object.entries(AREA_META).map(([slug, m]) => ({ key: slug, label: m.name, icon: m.emoji })),
])

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



const { today, calMonth, calYear, displayMonth, displayYear, calendarCells } = useEventCalendar(allEvents)

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
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
  return JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'Lễ hội truyền thống',
    numberOfItems: allEvents.value.length,
    itemListOrder: 'https://schema.org/ItemListOrderAscending',
    itemListElement: items,
  })
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/le-hoi') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Lễ hội truyền thống',
        description: 'Lễ hội đình miếu, lễ Khmer, Nghinh Ông, giỗ danh nhân — truyền thống văn hóa Vĩnh Long, Bến Tre, Trà Vinh.',
        url: 'https://vinhlong360.vn/le-hoi',
        numberOfItems: allEvents.value.length,
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Lễ hội' },
        ],
      }),
    },
    ...(festivalListSchema.value ? [{ type: 'application/ld+json' as const, innerHTML: festivalListSchema.value }] : []),
  ],
})
</script>

<!-- events.css nạp theo route (bỏ khỏi global entry.css) — dùng .event-*/.cal-*/.toggle-btn -->
<style src="~/assets/css/events.css"></style>

<style>
.lehoi-badge {
  background: var(--primary-dark);
}
.lehoi-dot {
  background: var(--primary-dark);
}
.event-lunar {
  font-style: italic;
}

/* Hero depth & cultural warmth: layered scrim over the festival gradient */
.catalog-hero.cat-festival {
  position: relative;
  background:
    radial-gradient(120% 90% at 12% 0%, rgba(var(--accent-rgb), .07) 0%, transparent 55%),
    linear-gradient(135deg, rgba(var(--primary-rgb), .06) 0%, rgba(183, 110, 60, .08) 100%);
}
.dark .catalog-hero.cat-festival {
  background:
    radial-gradient(120% 90% at 12% 0%, rgba(var(--accent-rgb), .05) 0%, transparent 55%),
    linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%);
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
  animation: lehoi-status-pulse 2.8s var(--ease-out-expo) infinite;
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
  border-radius: var(--radius-md);
  border-left: 3px solid rgba(var(--accent-rgb), .35);
}

.dark .lehoi-offseason { background: rgba(var(--accent-rgb), .12); border-left-color: rgba(var(--accent-rgb), .5); }

/* Thumbnail placeholder colour if image fails / while loading */
.event-thumb { background: var(--bg-alt); }

@media (prefers-reduced-motion: reduce) {
  .lehoi-status.status-now { animation: none; }
}

.event-row { position: relative; }
.ical-btn {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  cursor: pointer;
  font-size: var(--text-sm);
  opacity: 0;
  transition: opacity .15s;
  z-index: 1;
}
.event-row:hover .ical-btn,
.event-row:focus-within .ical-btn {
  opacity: 1;
}
.ical-btn:hover {
  background: var(--surface);
  box-shadow: var(--shadow-xs);
}
</style>
