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
    <div class="dash-loaded">

    <!-- Partial-degradation banner -->
    <div v-if="partialDegraded" class="dash-degraded" role="status">
      <span class="dash-degraded-icon" aria-hidden="true">&#9888;</span>
      <span>Một phần dữ liệu dashboard chưa tải được — bấm "Làm mới" để thử lại.</span>
    </div>

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
      <div v-if="stats.total_users" class="dash-stat-card">
        <div class="dash-stat-icon" style="background: rgba(88,86,214,.1); color: #5856D6;">&#128101;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ formatNum(stats.total_users) }}<span v-if="stats.users_week" class="dash-delta">+{{ stats.users_week }}</span></div>
          <div class="dash-stat-label">Users</div>
        </div>
      </div>
      <div v-if="stats.total_posts" class="dash-stat-card">
        <div class="dash-stat-icon" style="background: rgba(255,69,58,.1); color: #FF453A;">&#128172;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ formatNum(stats.total_posts) }}<span v-if="stats.posts_week" class="dash-delta">+{{ stats.posts_week }}</span></div>
          <div class="dash-stat-label">Bài viết</div>
        </div>
      </div>
    </div>

    <!-- Dynamic priority alerts -->
    <div class="dash-alerts" v-if="alerts.length">
      <NuxtLink v-for="a in alerts" :key="a.type" :to="a.link" :class="['dash-alert', a.priority <= 2 ? 'warn' : a.priority <= 3 ? 'error' : 'info']">
        <span class="dash-alert-icon">{{ a.icon }}</span>
        <span class="dash-alert-num">{{ a.count }}</span>
        <span class="dash-alert-text">{{ a.label.replace(String(a.count) + ' ', '') }}</span>
        <span class="dash-alert-arrow">&#8594;</span>
      </NuxtLink>
    </div>
    <div v-else-if="!loading" class="dash-all-clear">
      <span>&#10003;</span> Không có mục nào cần xử lý
    </div>

    <!-- System health -->
    <div v-if="health" class="dash-health">
      <div class="dash-health-header">
        <span :class="['dash-health-dot', health.status]"></span>
        <strong>Hệ thống {{ health.status === 'ok' ? 'hoạt động tốt' : 'degraded' }}</strong>
        <span class="dash-health-ver">v{{ health.version }}</span>
      </div>
      <div class="dash-health-metrics">
        <span>Uptime: <b>{{ formatUptime(health.uptime_seconds) }}</b></span>
        <span v-if="health.memory_mb">RAM: <b>{{ health.memory_mb }}MB</b></span>
        <span>LLM: <b :class="health.llm_api === 'ok' ? '' : 'dash-health-warn'">{{ health.llm_api || 'chưa kiểm' }}</b></span>
        <span v-if="health.data_quality">Dữ liệu: <b>{{ health.data_quality.coverage_pct }}%</b></span>
      </div>
    </div>

    <!-- Entity completeness -->
    <div v-if="stats.completeness" class="dash-completeness">
      <div class="dash-comp-header">
        <strong>Chất lượng entity</strong>
        <span class="dash-comp-pct">{{ stats.completeness.pct }}%</span>
      </div>
      <div class="dash-comp-bar"><div class="dash-comp-fill" :style="{ width: stats.completeness.pct + '%' }"></div></div>
      <div class="dash-comp-details">
        <span>Tóm tắt: {{ stats.completeness.has_summary }}/{{ stats.completeness.total }}</span>
        <span>Ảnh: {{ stats.completeness.has_images }}/{{ stats.completeness.total }}</span>
        <span>Phường/xã: {{ stats.completeness.has_place }}/{{ stats.completeness.total }}</span>
        <span v-if="stats.completeness.orphans">Mồ côi: <b style="color:#FF9F0A">{{ stats.completeness.orphans }}</b></span>
      </div>
    </div>

    <!-- Recent activity -->
    <div v-if="recentActivity.length" class="dash-section">
      <h2 class="admin-section-title">Hoạt động gần đây</h2>
      <div class="dash-activity">
        <div v-for="(a, i) in recentActivity" :key="i" class="activity-row">
          <span :class="['activity-method', a.method?.toLowerCase()]">{{ a.method }}</span>
          <span class="activity-path">{{ a.path }}</span>
          <span class="activity-time">{{ timeAgo(a.ts) }}</span>
        </div>
      </div>
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
const alerts = ref<Array<{ type: string; count: number; label: string; icon: string; link: string; priority: number }>>([])
const health = ref<Record<string, any> | null>(null)
const recentActivity = ref<Array<{ method: string; path: string; ts: string }>>([])
const loading = ref(true)
const partialDegraded = ref(false)

function formatNum(n: unknown): string {
  const num = Number(n) || 0
  if (num >= 10000) return (num / 1000).toFixed(1) + 'k'
  if (num >= 1000) return num.toLocaleString()
  return String(num)
}

function formatUptime(s: number): string {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function timeAgo(ts: string): string {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (diff < 60) return 'vừa xong'
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  return `${Math.floor(diff / 86400)} ngày trước`
}

const TYPE_COLORS: Record<string, string> = {
  attraction: '#219653', dish: '#FF9F0A', product: '#3478F6',
  accommodation: '#AF52DE', nature: '#34C759', experience: '#FF9500',
  craft_village: '#A6822A', event: '#FF3B30', drink: '#30B0C7',
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

const DEGRADED = Symbol('degraded')

async function fetchDashboard() {
  loading.value = true
  partialDegraded.value = false
  try {
    const [s, a, h, auditRes] = await Promise.all([
      $fetch<Record<string, unknown>>('/admin-api/stats', { headers: authHeaders() }),
      $fetch<{ alerts: typeof alerts.value }>('/admin-api/dashboard-alerts', { headers: authHeaders() }).catch(() => DEGRADED),
      $fetch<Record<string, any>>('/api/health').catch(() => DEGRADED),
      $fetch<{ entries: any[] }>('/admin-api/audit-log?limit=10', { headers: authHeaders() }).catch(() => DEGRADED),
    ])
    stats.value = s
    if (a !== DEGRADED) alerts.value = (a as { alerts: typeof alerts.value }).alerts
    if (h !== DEGRADED) health.value = h as Record<string, any>
    if (auditRes !== DEGRADED) recentActivity.value = (auditRes as { entries: any[] }).entries || []
    partialDegraded.value = a === DEGRADED || h === DEGRADED
  } catch {
    showToast('Không thể tải dữ liệu dashboard', 'error')
  }
  loading.value = false
}

onMounted(fetchDashboard)
</script>

<style scoped>
.dash-subtitle { font-size: .88rem; color: var(--muted); margin-top: var(--space-1); }

/* Signal freshly-loaded (vs stale) data: fade content in after fetch resolves */
.dash-loaded { animation: dash-fade-in .4s ease-out both; }
@keyframes dash-fade-in { from { opacity: .5; } to { opacity: 1; } }

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
.dash-delta { font-size: .7rem; font-weight: 600; color: #34C759; margin-left: 4px; }

/* ── Partial-degradation banner ── */
.dash-degraded {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) var(--space-4); border-radius: 10px;
  margin-bottom: var(--space-5); font-size: .85rem; font-weight: 500;
  background: rgba(255,159,10,.1); color: #c67a00;
  border: .5px solid rgba(255,159,10,.2);
}
.dash-degraded-icon { font-size: 1rem; flex-shrink: 0; }
.dark .dash-degraded { background: rgba(255,159,10,.08); color: #ffb340; border-color: rgba(255,159,10,.15); }

/* ── Alert banners ── */
.dash-alerts { display: flex; flex-direction: column; gap: var(--space-3); margin-bottom: var(--space-8); }
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
.dash-alert.info { background: rgba(52,120,246,.08); color: #2563EB; border: .5px solid rgba(52,120,246,.15); }
.dash-alert-icon { font-size: 1.1rem; flex-shrink: 0; }
.dash-alert-num { font-size: 1.3rem; font-weight: 800; min-width: 32px; }
.dash-alert-arrow { margin-left: auto; opacity: .5; }
.dash-all-clear {
  display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4);
  border-radius: 10px; margin-bottom: var(--space-8); font-size: .88rem; font-weight: 500;
  background: rgba(33,150,83,.08); color: var(--primary, #219653); border: .5px solid rgba(33,150,83,.15);
}

/* ── System health ── */
.dash-health {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-4) var(--space-5); margin-bottom: var(--space-6);
}
.dash-health-header { display: flex; align-items: center; gap: var(--space-2); font-size: .88rem; }
.dash-health-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dash-health-dot.ok { background: #34C759; }
.dash-health-dot.degraded { background: #FF9F0A; }
.dash-health-ver { margin-left: auto; font-size: .75rem; color: var(--muted); }
.dash-health-metrics {
  display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-5);
  margin-top: var(--space-3); font-size: .82rem; color: var(--muted);
}
.dash-health-metrics b { color: var(--ink); font-weight: 600; }
.dash-health-warn { color: #FF9F0A !important; }
.dark .dash-health { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }

/* ── Entity completeness ── */
.dash-completeness {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-4) var(--space-5); margin-bottom: var(--space-6);
}
.dash-comp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); font-size: .88rem; }
.dash-comp-pct { font-weight: 800; font-size: 1.1rem; }
.dash-comp-bar { height: 8px; background: rgba(142,142,147,.1); border-radius: 4px; overflow: hidden; }
.dash-comp-fill { height: 100%; background: var(--primary, #219653); border-radius: 4px; transition: width .5s ease-out; }
.dash-comp-details { display: flex; gap: var(--space-4); margin-top: var(--space-3); font-size: .78rem; color: var(--muted); }
.dark .dash-completeness { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }

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
.dash-action:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.06); border-color: var(--primary); background: color-mix(in oklab, var(--primary, #219653) 6%, var(--bg)); }
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
.refresh-spin { display: inline-block; font-size: 1.3rem; line-height: 1; animation: admin-spin .6s linear infinite; }
.admin-refresh:disabled { opacity: .55; cursor: not-allowed; }

/* ── Dark mode ── */
.dark .dash-stat-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .dash-alert.warn { background: rgba(255,159,10,.08); color: #ffb340; border-color: rgba(255,159,10,.15); }
.dark .dash-alert.error { background: rgba(217,79,61,.08); color: #ff6b5a; border-color: rgba(217,79,61,.15); }
.dark .dash-action { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-action:hover { border-color: var(--primary); box-shadow: 0 4px 12px rgba(0,0,0,.3); background: color-mix(in oklab, var(--primary, #219653) 12%, var(--card, #2c2c2e)); }
.dark .admin-refresh:disabled { border-color: rgba(255,255,255,.12); }
.dark .dash-chart-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-chart-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.2); }
.dark .dash-bar-track { background: rgba(255,255,255,.05); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .dash-loaded { animation: none; }
  .dash-stat-card:hover { transform: none; }
  .dash-stat-card:active { transform: none; }
  .dash-stat-card:hover .dash-stat-icon { transform: none; }
  .dash-alert:hover { transform: none; }
  .dash-action:hover { transform: none; }
  .dash-action:active { transform: none; }
  .dash-donut-seg { animation: none; }
  .dash-bar-fill { animation: none; }
}

/* Stack donut + bars earlier (accounts for sidebar on tablet landscape) */
@media (max-width: 900px) {
  .dash-chart-row { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .dash-stats { grid-template-columns: repeat(2, 1fr); }
  .dash-stat-card { padding: var(--space-4); }
  .dash-stat-icon { width: 36px; height: 36px; font-size: 1.1rem; }
  .dash-stat-value { font-size: 1.2rem; }
  .dash-actions { grid-template-columns: repeat(2, 1fr); }
  .dash-chart-row { grid-template-columns: 1fr; }
  .dash-bar-row { grid-template-columns: 70px 1fr 36px; }
  .dash-bar-name { font-size: .72rem; }
}

@media (max-width: 480px) {
  .dash-donut-legend { gap: 3px 6px; }
  .dash-legend-item { font-size: .65rem; }
}
.dash-activity { display: flex; flex-direction: column; gap: 2px; }
.activity-row { display: flex; align-items: center; gap: .5rem; padding: .4rem .6rem; border-radius: var(--radius-sm); font-size: .8rem; }
.activity-row:nth-child(odd) { background: var(--bg-alt); }
.activity-method { font-weight: 700; font-size: .7rem; padding: 1px 6px; border-radius: var(--radius-sm); text-transform: uppercase; }
.activity-method.post { background: rgba(52,199,89,.15); color: #219653; }
.activity-method.put, .activity-method.patch { background: rgba(255,159,10,.15); color: #FF9F0A; }
.activity-method.delete { background: rgba(255,69,58,.15); color: #FF453A; }
.activity-path { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ink); }
.activity-time { color: var(--muted); font-size: .72rem; white-space: nowrap; }
</style>
