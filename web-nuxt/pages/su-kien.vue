<template>
  <section class="page events-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Sự kiện' }]" />
    <div class="page-head">
      <h1>Sự kiện</h1>
      <p>Sự kiện văn hóa, hội chợ, festival và hoạt động sắp diễn ra tại Vĩnh Long, Bến Tre, Trà Vinh.</p>
    </div>

    <div class="controls">
      <div class="search-row">
        <input v-model="q" type="search" placeholder="Tìm sự kiện…" />
      </div>
      <div class="chip-row">
        <button :class="['chip', { active: areaFilter === 'all' }]" @click="areaFilter = 'all'">Tất cả vùng</button>
        <button v-for="(meta, slug) in AREA_META" :key="slug" :class="['chip', { active: areaFilter === slug }]" @click="areaFilter = slug">
          {{ meta.emoji }} {{ meta.name }}
        </button>
      </div>
    </div>

    <p class="result-link">Tìm lễ hội truyền thống? <NuxtLink to="/le-hoi">Xem trang Lễ hội →</NuxtLink></p>

    <div class="view-toggle">
      <button :class="['toggle-btn', { active: view === 'list' }]" @click="view = 'list'">📋 Danh sách</button>
      <button :class="['toggle-btn', { active: view === 'calendar' }]" @click="view = 'calendar'">📅 Lịch</button>
    </div>

    <SkeletonGrid v-if="!data" :count="4" />

    <template v-else-if="view === 'list'">
      <p class="result-meta">{{ filtered.length }} sự kiện</p>
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
            <img :src="e.images[0]" :alt="e.name" loading="lazy" />
          </div>
        </NuxtLink>
      </div>
      <EmptyState v-else message="Không có sự kiện nào phù hợp." />
    </template>

    <template v-else>
      <div class="calendar">
        <div class="cal-header">
          <button class="cal-nav" @click="calMonth--" aria-label="Tháng trước">‹</button>
          <h2>Tháng {{ displayMonth }} / {{ displayYear }}</h2>
          <button class="cal-nav" @click="calMonth++" aria-label="Tháng sau">›</button>
        </div>
        <div class="cal-grid">
          <div v-for="d in ['T2','T3','T4','T5','T6','T7','CN']" :key="d" class="cal-day-label">{{ d }}</div>
          <div
            v-for="(cell, i) in calendarCells" :key="i"
            class="cal-cell"
            :class="{ 'cal-empty': !cell.day, 'cal-today': cell.isToday, 'cal-has-events': cell.events?.length }"
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
  </section>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
import { lunarLabel, isLunarFirstDay, isLunarFull } from '~/composables/useLunar'

const q = ref('')
const areaFilter = ref('all')
const view = ref('list')

useFilterUrl({ vung: areaFilter }, { vung: 'all' })

const { data } = await useAsyncData('events', () =>
  $fetch<any>('/api/events?limit=200')
)

const allEvents = computed(() =>
  (data.value?.events || []).filter((e: any) => (e.attributes?.category || 'su-kien') !== 'le-hoi')
)

const filtered = computed(() => {
  let list = allEvents.value
  if (areaFilter.value !== 'all') {
    list = list.filter((e: any) => getArea(e) === areaFilter.value)
  }
  if (q.value.trim()) {
    const kw = q.value.toLowerCase()
    list = list.filter((e: any) => e.name.toLowerCase().includes(kw) || (e.summary || '').toLowerCase().includes(kw))
  }
  return list
})

function getArea(e: any): string {
  return e.place_area || e.area || ''
}

function getDateStart(e: any): Date | null {
  const ds = e.attributes?.date_start
  if (!ds) return null
  const d = new Date(ds + 'T00:00:00')
  return isNaN(d.getTime()) ? null : d
}

function formatMonth(e: any): string {
  const d = getDateStart(e)
  if (!d) {
    const months = e.season?.months
    if (months?.length) return `T${months[0]}`
    return ''
  }
  return `Tg ${d.getMonth() + 1}`
}

function formatDay(e: any): string {
  const d = getDateStart(e)
  if (!d) return '—'
  return String(d.getDate())
}

function dateRange(e: any): string {
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

  const cells: any[] = []
  for (let i = 0; i < startDow; i++) cells.push({ day: 0 })

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const isToday = y === today.getFullYear() && m === today.getMonth() && d === today.getDate()
    const events = allEvents.value.filter((e: any) => {
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
  title: 'Sự kiện — vinhlong360',
  description: 'Sự kiện văn hóa, hội chợ, festival và hoạt động sắp diễn ra tại Vĩnh Long, Bến Tre, Trà Vinh.',
  ogTitle: 'Sự kiện — vinhlong360',
  ogDescription: 'Lịch sự kiện miền Tây: hội chợ, festival, marathon và hơn thế.',
})
</script>

