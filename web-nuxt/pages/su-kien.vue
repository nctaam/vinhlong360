<template>
  <div class="page events-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sự kiện' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-event">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🎪</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEvents.length" class="catalog-stats">
        <div class="stat-item">
          <span class="stat-num">{{ allEvents.length }}</span>
          <span class="stat-label">sự kiện</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <span class="stat-num">{{ a.count }}</span>
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>
    </section>

    <p class="result-link">Tìm lễ hội truyền thống? <NuxtLink to="/le-hoi">Xem trang Lễ hội →</NuxtLink></p>

    <!-- Upcoming -->
    <section v-if="upcoming.length" class="block">
      <div class="section-head">
        <h2>Sắp diễn ra</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Sự kiện sắp diễn ra">
        <NuxtLink
          v-for="e in upcoming" :key="e.id"
          :to="`/dia-diem/${e.id}`"
          class="event-row"
        >
          <div class="event-date-badge">
            <span class="edb-month">{{ formatMonth(e) }}</span>
            <span class="edb-day">{{ formatDay(e) }}</span>
          </div>
          <div class="event-info">
            <span v-if="e.attributes?.category === 'mua'" class="cat-badge cat-mua">🌾 Mùa vụ</span>
            <h3>{{ e.name }}</h3>
            <div class="event-meta">
              <span v-if="e.place_name" class="event-place">📍 {{ e.place_name }}</span>
              <span v-if="dateRange(e)" class="event-dates">🗓️ {{ dateRange(e) }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Region quick-picks -->
    <section class="block reveal">
      <div class="section-head">
        <h2>Chọn theo khu vực</h2>
      </div>
      <div class="quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', { active: areaFilter === key }]"
          @click="areaFilter = areaFilter === key ? 'all' : (key as string)"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-count">{{ countByArea(key as string) }} sự kiện</span>
        </button>
      </div>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Controls -->
    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm sự kiện…" aria-label="Tìm sự kiện" />
      </div>
      <div class="chip-row" role="group" aria-label="Lọc theo khu vực">
        <button type="button" :class="['chip', { active: areaFilter === 'all' }]" :aria-pressed="areaFilter === 'all'" @click="areaFilter = 'all'">Tất cả vùng</button>
        <button type="button" v-for="(meta, slug) in AREA_META" :key="slug" :class="['chip', { active: areaFilter === slug }]" :aria-pressed="areaFilter === slug" @click="areaFilter = slug">
          {{ meta.emoji }} {{ meta.name }}
        </button>
      </div>
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
          :to="`/dia-diem/${e.id}`"
          class="event-row"
        >
          <div class="event-date-badge">
            <span class="edb-month">{{ formatMonth(e) }}</span>
            <span class="edb-day">{{ formatDay(e) }}</span>
          </div>
          <div class="event-info">
            <span v-if="e.attributes?.category === 'mua'" class="cat-badge cat-mua">🌾 Mùa vụ</span>
            <h3>{{ e.name }}</h3>
            <p v-if="e.summary" class="event-summary">{{ truncate(e.summary, 120) }}</p>
            <div class="event-meta">
              <span v-if="e.place_name" class="event-place">📍 {{ e.place_name }}</span>
              <span v-if="getArea(e)" class="event-area">{{ AREA_META[getArea(e)]?.emoji }} {{ AREA_META[getArea(e)]?.name }}</span>
              <span v-if="dateRange(e)" class="event-dates">🗓️ {{ dateRange(e) }}</span>
            </div>
          </div>
          <div v-if="e.images?.length" class="event-thumb">
            <img :src="e.images[0]" :alt="e.name" loading="lazy" decoding="async" width="160" height="120" />
          </div>
        </NuxtLink>
      </div>
      <EmptyState v-else icon="🎪" title="Không tìm thấy sự kiện" message="Thử đổi khu vực hoặc từ khóa khác nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="areaFilter = 'all'; q = ''">Xóa bộ lọc</button>
          <button type="button" class="btn btn-outline" @click="view = 'calendar'">Xem lịch</button>
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
            :tabindex="-1"
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
                :to="`/dia-diem/${ev.id}`"
                class="cal-event-dot"
                :title="ev.name"
              >{{ truncate(ev.name, 18) }}</NuxtLink>
              <span v-if="cell.events.length > 2" class="cal-more">+{{ cell.events.length - 2 }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Cross-links -->
    <section class="block reveal catalog-cross">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/le-hoi" class="cross-card">
          <span class="cross-icon">🎋</span>
          <div><strong>Lễ hội</strong><p>Truyền thống văn hóa</p></div>
        </NuxtLink>
        <NuxtLink to="/du-lich" class="cross-card">
          <span class="cross-icon">🌿</span>
          <div><strong>Du lịch</strong><p>Trải nghiệm miệt vườn</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
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
const { f: pc } = usePageContent('su_kien')

const q = ref('')
const areaFilter = ref('all')
const view = ref('list')

useFilterUrl({ vung: areaFilter }, { vung: 'all' })

const { data, error: fetchError } = await useAsyncData('events', () =>
  $fetch<{ events: Entity[] }>('/api/events?limit=200')
)

const allEvents = computed(() =>
  (data.value?.events || []).filter((e: Entity) => (e.attributes?.category || 'su-kien') !== 'le-hoi')
)

const areaCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEvents.value) {
    const area = getArea(e)
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return Object.entries(AREA_META)
    .filter(([key]) => counts[key])
    .map(([key, meta]) => ({ key, name: meta.name, count: counts[key] }))
})

function countByArea(key: string) {
  return allEvents.value.filter((e: Entity) => getArea(e) === key).length
}

const upcoming = computed(() => {
  const now = new Date().toISOString().slice(0, 10)
  return allEvents.value
    .filter((e: Entity) => {
      const ds = e.attributes?.date_start
      return ds && ds >= now
    })
    .sort((a: Entity, b: Entity) => (a.attributes?.date_start || '').localeCompare(b.attributes?.date_start || ''))
    .slice(0, 6)
})

const filtered = computed(() => {
  let list = allEvents.value
  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => getArea(e) === areaFilter.value)
  }
  if (q.value.trim()) {
    const kw = q.value.toLowerCase()
    list = list.filter((e: Entity) => e.name.toLowerCase().includes(kw) || (e.summary || '').toLowerCase().includes(kw))
  }
  return list
})

function getArea(e: Entity): string {
  return e.place_area || e.area || ''
}

function getDateStart(e: Entity): Date | null {
  const ds = e.attributes?.date_start
  if (!ds) return null
  const d = new Date(ds + 'T00:00:00')
  return isNaN(d.getTime()) ? null : d
}

function formatMonth(e: Entity): string {
  const d = getDateStart(e)
  if (!d) {
    const months = e.season?.months
    if (months?.length) return `T${months[0]}`
    return ''
  }
  return `Tg ${d.getMonth() + 1}`
}

function formatDay(e: Entity): string {
  const d = getDateStart(e)
  if (!d) return '—'
  return String(d.getDate())
}

function dateRange(e: Entity): string {
  const attrs = e.attributes || {}
  const ds = attrs.date_start
  const de = attrs.date_end
  if (!ds) return ''
  const fmt = (s: string) => {
    const d = new Date(s + 'T00:00:00')
    return `${d.getDate()}/${d.getMonth() + 1}`
  }
  if (ds === de) return fmt(ds)
  return `${fmt(ds)} – ${fmt(de)}`
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

// Calendar
const today = new Date()
const calMonth = ref(today.getMonth())
const calYear = ref(today.getFullYear())

const displayMonth = computed(() => {
  let m = calMonth.value % 12
  if (m < 0) m += 12
  return m + 1
})
const displayYear = computed(() => {
  return calYear.value + Math.floor(calMonth.value / 12)
})

watch(calMonth, (v) => {
  if (v < 0) { calYear.value--; calMonth.value = v + 12 }
  else if (v > 11) { calYear.value++; calMonth.value = v - 12 }
})

const calendarCells = computed(() => {
  const y = displayYear.value
  const m = displayMonth.value - 1
  const firstDay = new Date(y, m, 1)
  const lastDay = new Date(y, m + 1, 0)
  const daysInMonth = lastDay.getDate()

  let startDow = firstDay.getDay()
  if (startDow === 0) startDow = 7
  startDow--

  const cells: { day: number; isToday?: boolean; events?: Entity[]; lunar?: string; lunarFirst?: boolean; lunarMid?: boolean }[] = []
  for (let i = 0; i < startDow; i++) cells.push({ day: 0 })

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const isToday = y === today.getFullYear() && m === today.getMonth() && d === today.getDate()
    const events = allEvents.value.filter((e: Entity) => {
      const attrs = e.attributes || {}
      const ds = attrs.date_start
      const de = attrs.date_end || ds
      if (!ds) return false
      if (dateStr < ds || dateStr > de) return false
      const span = (new Date(de).getTime() - new Date(ds).getTime()) / 86400000
      return span <= 30
    })
    const lunar = lunarLabel(d, m + 1, y)
    const lunarFirst = isLunarFirstDay(d, m + 1, y)
    const lunarMid = isLunarFull(d, m + 1, y)
    cells.push({ day: d, isToday, events, lunar, lunarFirst, lunarMid })
  }
  return cells
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl('/su-kien') }] })
</script>

<!-- events.css nạp theo route (bỏ khỏi global entry.css) — dùng .event-*/.cal-*/.toggle-btn -->
<style src="~/assets/css/events.css"></style>

<style>
.catalog-hero.cat-event { background: linear-gradient(135deg, rgba(var(--accent-rgb, 255,193,7), .08) 0%, rgba(183, 110, 60, .06) 100%); }
.dark .catalog-hero.cat-event { background: linear-gradient(135deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.01) 100%); }
</style>
