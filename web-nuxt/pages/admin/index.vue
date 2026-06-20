<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Dashboard</h1>
        <p class="dash-subtitle">Tổng quan hệ thống vinhlong360</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchDashboard">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>

    <!-- Primary stats -->
    <div class="dash-stats">
      <div class="dash-stat-card">
        <div class="dash-stat-icon" style="background: rgba(33,150,83,.1); color: #219653;">&#127759;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ stats.total_entities || 0 }}</div>
          <div class="dash-stat-label">Entities</div>
        </div>
      </div>
      <div class="dash-stat-card">
        <div class="dash-stat-icon" style="background: rgba(52,120,246,.1); color: #3478F6;">&#127963;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ stats.total_places || 0 }}</div>
          <div class="dash-stat-label">Địa điểm HC</div>
        </div>
      </div>
      <div class="dash-stat-card">
        <div class="dash-stat-icon" style="background: rgba(175,82,222,.1); color: #AF52DE;">&#128279;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ formatNum(stats.total_relationships) }}</div>
          <div class="dash-stat-label">Quan hệ</div>
        </div>
      </div>
      <div class="dash-stat-card">
        <div class="dash-stat-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#128506;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ stats.total_itineraries || 0 }}</div>
          <div class="dash-stat-label">Lịch trình</div>
        </div>
      </div>
    </div>

    <!-- Alert cards -->
    <div class="dash-alerts" v-if="modStats.pending || infoReports">
      <NuxtLink v-if="modStats.pending" to="/admin/kiem-duyet" class="dash-alert warn">
        <span class="dash-alert-num">{{ modStats.pending }}</span>
        <span class="dash-alert-text">bài viết chờ duyệt</span>
        <span class="dash-alert-arrow">&#8594;</span>
      </NuxtLink>
      <NuxtLink v-if="infoReports" to="/admin/bao-cao" class="dash-alert error">
        <span class="dash-alert-num">{{ infoReports }}</span>
        <span class="dash-alert-text">báo cáo sai thông tin</span>
        <span class="dash-alert-arrow">&#8594;</span>
      </NuxtLink>
    </div>

    <!-- Quick actions -->
    <div class="dash-section">
      <h2 class="admin-section-title">Thao tác nhanh</h2>
      <div class="dash-actions">
        <NuxtLink to="/admin/entities" class="dash-action">
          <span class="dash-action-icon">&#128203;</span>
          <span>Quản lý entities</span>
        </NuxtLink>
        <NuxtLink to="/admin/data-quality" class="dash-action">
          <span class="dash-action-icon">&#128269;</span>
          <span>Kiểm tra dữ liệu</span>
        </NuxtLink>
        <NuxtLink to="/admin/kiem-duyet" class="dash-action">
          <span class="dash-action-icon">&#128737;</span>
          <span>Kiểm duyệt</span>
        </NuxtLink>
        <NuxtLink to="/admin/ai" class="dash-action">
          <span class="dash-action-icon">&#129302;</span>
          <span>Knowledge Agent</span>
        </NuxtLink>
      </div>
    </div>

    <!-- Charts section -->
    <div class="dash-section">
      <h2 class="admin-section-title">Phân bổ theo loại</h2>
      <div class="dash-chart-row">

        <!-- Donut chart -->
        <div class="dash-chart-card dash-donut-wrap">
          <svg class="dash-donut" viewBox="0 0 160 160">
            <circle cx="80" cy="80" r="60" fill="none" stroke="var(--line)" stroke-width="20" opacity=".2" />
            <circle
              v-for="(seg, i) in donutSegments" :key="i"
              cx="80" cy="80" r="60"
              fill="none"
              :stroke="seg.color"
              stroke-width="20"
              :stroke-dasharray="`${seg.dash} ${377 - seg.dash}`"
              :stroke-dashoffset="seg.offset"
              stroke-linecap="butt"
              class="dash-donut-seg"
              :style="{ animationDelay: `${i * 80}ms` }"
            />
          </svg>
          <div class="dash-donut-center">
            <span class="dash-donut-total">{{ totalByType }}</span>
            <span class="dash-donut-label">entities</span>
          </div>
          <div class="dash-donut-legend">
            <span v-for="(seg, i) in donutSegments" :key="i" class="dash-legend-item">
              <span class="dash-legend-dot" :style="{ background: seg.color }"></span>
              <span class="dash-legend-name">{{ seg.type }}</span>
              <span class="dash-legend-pct">{{ seg.pct }}%</span>
            </span>
          </div>
        </div>

        <!-- Horizontal bar chart -->
        <div class="dash-chart-card dash-bars-wrap">
          <div v-for="(bar, i) in sortedBars" :key="bar.type" class="dash-bar-row">
            <span class="dash-bar-name">{{ bar.type }}</span>
            <div class="dash-bar-track">
              <div
                class="dash-bar-fill"
                :style="{ width: bar.pct + '%', background: bar.color, animationDelay: `${i * 60}ms` }"
              ></div>
            </div>
            <span class="dash-bar-count">{{ bar.count }}</span>
          </div>
        </div>

      </div>
    </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const stats = ref<Record<string, unknown>>({})
const modStats = ref<Record<string, unknown>>({})
const infoReports = ref<number | null>(null)
const loading = ref(true)

function formatNum(n: unknown): string {
  const num = Number(n) || 0
  if (num >= 10000) return (num / 1000).toFixed(1) + 'k'
  if (num >= 1000) return num.toLocaleString()
  return String(num)
}

const TYPE_COLORS: Record<string, string> = {
  attraction: '#219653', dish: '#FF9F0A', product: '#3478F6',
  accommodation: '#AF52DE', nature: '#34C759', experience: '#FF9500',
  craft_village: '#8B6914', event: '#FF3B30', drink: '#30B0C7',
  facility: '#8E8E93',
}

const totalByType = computed(() => {
  const bt = (stats.value.by_type || {}) as Record<string, number>
  return Object.values(bt).reduce((s, v) => s + v, 0)
})

const sortedBars = computed(() => {
  const bt = (stats.value.by_type || {}) as Record<string, number>
  const items = Object.entries(bt).map(([type, count]) => ({ type, count, color: TYPE_COLORS[type] || '#8E8E93' }))
  items.sort((a, b) => b.count - a.count)
  const max = items[0]?.count || 1
  return items.map(it => ({ ...it, pct: Math.round((it.count / max) * 100) }))
})

const donutSegments = computed(() => {
  const bt = (stats.value.by_type || {}) as Record<string, number>
  const items = Object.entries(bt).map(([type, count]) => ({ type, count, color: TYPE_COLORS[type] || '#8E8E93' }))
  items.sort((a, b) => b.count - a.count)
  const total = totalByType.value || 1
  const circumference = 2 * Math.PI * 60 // ~377
  let offset = circumference * 0.25 // start at top
  return items.map(it => {
    const pct = Math.round((it.count / total) * 100)
    const dash = (it.count / total) * circumference
    const seg = { ...it, pct, dash, offset: -offset }
    offset -= dash
    return seg
  })
})

async function fetchDashboard() {
  loading.value = true
  try {
    const [s, m, ir] = await Promise.all([
      $fetch<Record<string, unknown>>('/admin-api/stats', { headers: authHeaders() }),
      $fetch<Record<string, unknown>>('/admin-api/moderation/stats', { headers: authHeaders() }).catch(() => ({})),
      $fetch<Record<string, unknown>>('/admin-api/info-reports?limit=1', { headers: authHeaders() }).catch(() => null),
    ])
    stats.value = s
    modStats.value = m
    if (ir) infoReports.value = ir.total ?? 0
  } catch {
    showToast('Không thể tải dữ liệu dashboard', 'error')
  }
  loading.value = false
}

onMounted(fetchDashboard)
</script>

<style scoped>
.dash-subtitle { font-size: .88rem; color: var(--muted); margin-top: var(--space-1); }

/* ── Primary stat cards ── */
.dash-stats {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-4); margin-bottom: var(--space-6);
}
.dash-stat-card {
  display: flex; align-items: center; gap: var(--space-4);
  background: var(--bg); border-radius: 14px; padding: var(--space-5);
  border: .5px solid var(--line);
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.dash-stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.dash-stat-card:active { transform: scale(.98); }
.dash-stat-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; flex-shrink: 0;
  transition: transform .25s cubic-bezier(.2,1,.4,1);
}
.dash-stat-card:hover .dash-stat-icon { transform: scale(1.08); }
.dash-stat-value { font-size: 1.5rem; font-weight: 800; line-height: 1.2; }
.dash-stat-label { font-size: .75rem; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: .5px; }

/* ── Alert banners ── */
.dash-alerts { display: flex; flex-direction: column; gap: var(--space-3); margin-bottom: var(--space-6); }
.dash-alert {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4); border-radius: 10px;
  text-decoration: none; font-size: .88rem; font-weight: 500;
  transition: transform .25s cubic-bezier(.2,1,.4,1), opacity .2s;
}
.dash-alert:hover { transform: translateX(4px); }
.dash-alert:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
.dash-alert.warn { background: rgba(255,159,10,.1); color: #c67a00; border: .5px solid rgba(255,159,10,.2); }
.dash-alert.error { background: rgba(217,79,61,.1); color: #b33a2a; border: .5px solid rgba(217,79,61,.2); }
.dash-alert-num { font-size: 1.3rem; font-weight: 800; min-width: 32px; }
.dash-alert-arrow { margin-left: auto; opacity: .5; }

/* ── Quick actions ── */
.dash-section { margin-bottom: var(--space-6); }
.dash-actions { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: var(--space-3); }
.dash-action {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-5) var(--space-3); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  text-decoration: none; color: inherit; font-size: .85rem; font-weight: 500;
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.dash-action:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.06); border-color: var(--primary); }
.dash-action:active { transform: scale(.97); }
.dash-action:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.dash-action-icon { font-size: 1.5rem; }

/* ── Charts ── */
.dash-chart-row {
  display: grid; grid-template-columns: 280px 1fr;
  gap: var(--space-4); align-items: start;
}
.dash-chart-card {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-5);
  transition: box-shadow .25s;
}
.dash-chart-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.04); }

/* Donut */
.dash-donut-wrap { display: flex; flex-direction: column; align-items: center; gap: var(--space-4); position: relative; }
.dash-donut { width: 160px; height: 160px; }
.dash-donut-seg {
  animation: dash-donut-in .6s cubic-bezier(.4,0,.2,1) both;
  transform-origin: center;
}
@keyframes dash-donut-in {
  from { stroke-dasharray: 0 377; opacity: 0; }
}
.dash-donut-center {
  position: absolute; top: calc(var(--space-5) + 50px); left: 50%;
  transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center;
  pointer-events: none;
}
.dash-donut-total { font-size: 1.4rem; font-weight: 800; line-height: 1.2; }
.dash-donut-label { font-size: .68rem; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
.dash-donut-legend {
  display: flex; flex-wrap: wrap; gap: 6px 12px; justify-content: center;
}
.dash-legend-item { display: flex; align-items: center; gap: 4px; font-size: .72rem; }
.dash-legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dash-legend-name { color: var(--muted); }
.dash-legend-pct { font-weight: 700; }

/* Bar chart */
.dash-bars-wrap { display: flex; flex-direction: column; gap: 10px; }
.dash-bar-row { display: grid; grid-template-columns: 100px 1fr 44px; gap: 10px; align-items: center; }
.dash-bar-name {
  font-size: .78rem; font-weight: 500; color: var(--muted);
  text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dash-bar-track {
  height: 22px; border-radius: 6px;
  background: rgba(142,142,147,.06);
  overflow: hidden;
}
.dash-bar-fill {
  height: 100%; border-radius: 6px;
  animation: dash-bar-grow .5s cubic-bezier(.4,0,.2,1) both;
}
@keyframes dash-bar-grow { from { width: 0 !important; } }
.dash-bar-count { font-size: .82rem; font-weight: 700; text-align: right; }

/* ── Refresh animation ── */
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Dark mode ── */
.dark .dash-stat-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .dash-alert.warn { background: rgba(255,159,10,.08); color: #ffb340; border-color: rgba(255,159,10,.15); }
.dark .dash-alert.error { background: rgba(217,79,61,.08); color: #ff6b5a; border-color: rgba(217,79,61,.15); }
.dark .dash-action { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-action:hover { border-color: var(--primary); box-shadow: 0 4px 12px rgba(0,0,0,.3); }
.dark .dash-chart-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-chart-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.2); }
.dark .dash-bar-track { background: rgba(255,255,255,.05); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .dash-stat-card:hover { transform: none; }
  .dash-stat-card:active { transform: none; }
  .dash-stat-card:hover .dash-stat-icon { transform: none; }
  .dash-alert:hover { transform: none; }
  .dash-action:hover { transform: none; }
  .dash-action:active { transform: none; }
  .dash-donut-seg { animation: none; }
  .dash-bar-fill { animation: none; }
}

@media (max-width: 768px) {
  .dash-stats { grid-template-columns: repeat(2, 1fr); }
  .dash-stat-card { padding: var(--space-4); }
  .dash-stat-icon { width: 36px; height: 36px; font-size: 1.1rem; }
  .dash-stat-value { font-size: 1.2rem; }
  .dash-actions { grid-template-columns: repeat(2, 1fr); }
  .dash-chart-row { grid-template-columns: 1fr; }
  .dash-bar-row { grid-template-columns: 80px 1fr 36px; }
  .dash-bar-name { font-size: .72rem; }
}
</style>
