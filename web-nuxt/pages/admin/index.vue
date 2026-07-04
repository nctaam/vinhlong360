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

    <!-- Full error state when stats fetch fails entirely -->
    <div v-if="loadError && !loading" class="dash-error-state" role="alert">
      <span class="dash-error-icon" aria-hidden="true">&#9888;</span>
      <div class="dash-error-body">
        <strong>Không thể tải dữ liệu dashboard</strong>
        <p>Kiểm tra kết nối mạng hoặc trạng thái backend.</p>
        <button type="button" class="btn btn-outline btn-sm" @click="fetchDashboard">Thử lại</button>
      </div>
    </div>

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải dashboard"><div class="spinner"></div></div>
    <template v-else-if="!loadError">
    <div class="dash-loaded" aria-live="polite">

    <!-- Partial-degradation banner -->
    <div v-if="partialDegraded" class="dash-degraded" role="status">
      <span class="dash-degraded-icon" aria-hidden="true">&#9888;</span>
      <span>Chưa tải được: {{ degradedDetail }} — bấm "Làm mới" để thử lại.</span>
    </div>

    <!-- Primary stats -->
    <div class="dash-stats" role="group" aria-label="Thống kê tổng quan">
      <div class="dash-stat-card" role="group" aria-label="Entities">
        <div class="dash-stat-icon si-green" aria-hidden="true">&#127759;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ stats.total_entities || 0 }}<span v-if="stats.entities_week" class="dash-delta">+{{ stats.entities_week }}</span></div>
          <div class="dash-stat-label">Entities</div>
        </div>
      </div>
      <div class="dash-stat-card">
        <div class="dash-stat-icon si-blue" aria-hidden="true">&#127963;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ stats.total_places || 0 }}</div>
          <div class="dash-stat-label">Địa điểm HC</div>
        </div>
      </div>
      <div class="dash-stat-card">
        <div class="dash-stat-icon si-purple" aria-hidden="true">&#128279;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ formatNum(stats.total_relationships) }}</div>
          <div class="dash-stat-label">Quan hệ</div>
        </div>
      </div>
      <div class="dash-stat-card">
        <div class="dash-stat-icon si-orange" aria-hidden="true">&#128506;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ stats.total_itineraries || 0 }}</div>
          <div class="dash-stat-label">Lịch trình</div>
        </div>
      </div>
      <div v-if="stats.total_users" class="dash-stat-card">
        <div class="dash-stat-icon si-indigo" aria-hidden="true">&#128101;</div>
        <div class="dash-stat-body">
          <div class="dash-stat-value">{{ formatNum(stats.total_users) }}<span v-if="stats.users_week" class="dash-delta">+{{ stats.users_week }}</span></div>
          <div class="dash-stat-label">Users</div>
        </div>
      </div>
      <div v-if="stats.total_posts" class="dash-stat-card">
        <div class="dash-stat-icon si-red" aria-hidden="true">&#128172;</div>
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
        <span v-if="stats.backup">Backup: <b>{{ stats.backup.last }}</b> ({{ stats.backup.size_mb }}MB, {{ stats.backup.count }} bản)
          <button type="button" class="dash-backup-btn" :disabled="backupRunning" @click="triggerBackup">{{ backupRunning ? 'Đang chạy…' : 'Tạo backup' }}</button>
        </span>
      </div>
    </div>

    <!-- Ops cockpit -->
    <div v-if="ops" class="dash-ops" role="group" aria-label="Ops cockpit">
      <div class="dash-ops-head">
        <div>
          <strong>Ops cockpit</strong>
          <p>Release, queue, quality budget và rollback readiness</p>
        </div>
        <span :class="['dash-ops-status', ops.status === 'ok' ? 'ok' : 'attention']">{{ ops.status || 'attention' }}</span>
      </div>
      <div class="dash-ops-grid">
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Release gate</span>
          <b>{{ ops.release?.gate_covers_backend_frontend_e2e ? 'OK' : 'Cần kiểm tra' }}</b>
          <small>Migration: {{ ops.release?.latest_migration || 'n/a' }}</small>
        </div>
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Deploy</span>
          <b>{{ ops.release?.deploy_health_blocking ? 'Health-blocking' : 'Chưa khóa đủ' }}</b>
          <small>{{ ops.release?.deploy_host_env_configured ? 'Host env đã đặt' : 'Thiếu VL360_DEPLOY_HOST' }}</small>
        </div>
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Queue backlog</span>
          <b>{{ opsQueueTotal }}</b>
          <small>Moderation {{ ops.queues?.moderation || 0 }} · DQ {{ ops.queues?.data_quality || 0 }}</small>
        </div>
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Rollback</span>
          <b>{{ ops.rollback?.backup_ready ? 'Sẵn sàng' : 'Thiếu backup' }}</b>
          <small>{{ ops.rollback?.latest_backup || 'chưa có bản gần nhất' }}</small>
        </div>
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Schema</span>
          <b>{{ ops.release?.schema_ok ? 'Đồng bộ' : 'Cần migrate' }}</b>
          <small>v{{ ops.release?.schema_version || 0 }}/{{ ops.release?.required_schema_version || '?' }}</small>
        </div>
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Quality trend</span>
          <b>{{ formatQualityTrend(ops.quality_trend) }}</b>
          <small>{{ formatQualityTrendDetail(ops.quality_trend) }}</small>
        </div>
        <div class="dash-ops-cell">
          <span class="dash-ops-label">Write guards</span>
          <b>{{ ops.shared_controls?.tables_ready ? 'DB-backed' : 'Fallback' }}</b>
          <small>Rate {{ ops.shared_controls?.rate_limit_enabled ? 'on' : 'off' }} · Idem {{ ops.shared_controls?.idempotency_enabled ? 'on' : 'off' }}</small>
        </div>
      </div>
    </div>

    <JourneyActionRail
      v-if="adminOpsActions.length"
      :actions="adminOpsActions"
      title="Ưu tiên vận hành"
      subtitle="Xếp hạng theo health, release gate, rollback readiness và hàng đợi cần xử lý."
      aria-label="Hành động ưu tiên cho AdminCP"
      compact
    />

    <!-- Entity completeness -->
    <div v-if="stats.completeness" class="dash-completeness">
      <div class="dash-comp-header">
        <strong>Chất lượng entity</strong>
        <span class="dash-comp-pct">{{ stats.completeness.pct }}%</span>
      </div>
      <div v-for="seg in completenessSegments" :key="seg.key" class="dash-comp-seg">
        <span class="dcs-label">{{ seg.label }}</span>
        <div class="dcs-bar"><div class="dcs-fill" :style="{ width: seg.pct + '%', background: seg.color }"></div></div>
        <span class="dcs-val">{{ seg.count }}/{{ stats.completeness.total }}</span>
      </div>
      <div class="dash-comp-details">
        <NuxtLink v-if="stats.completeness.orphans" to="/admin/entities?orphans=1" class="dash-orphan-link">Mồ côi: <b class="dash-orphan-count">{{ stats.completeness.orphans }}</b></NuxtLink>
      </div>
    </div>

    <!-- Recent activity -->
    <div v-if="recentActivity.length" class="dash-section">
      <h2 class="admin-section-title">Hoạt động gần đây</h2>
      <div class="dash-activity">
        <div v-for="(a, i) in recentActivity" :key="i" class="activity-row">
          <span :class="['activity-method', a.method?.toLowerCase()]">{{ a.method }}</span>
          <span class="activity-main">
            <span class="activity-label">{{ activityLabel(a) }}</span>
            <span class="activity-path">{{ a.method }} {{ a.path }}</span>
          </span>
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
          <svg class="dash-donut" viewBox="0 0 160 160" role="img" :aria-label="`Biểu đồ phân bố ${totalByType} entities theo loại`">
            <title>Phân bố entity theo loại</title>
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
        <div class="dash-chart-card dash-bars-wrap" role="img" aria-label="Biểu đồ cột phân bố entity theo loại">
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
import { useJourneyActions } from '~/composables/useJourneyActions'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Bảng điều khiển — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { adminOpsActions: buildAdminOpsActions } = useJourneyActions()

interface DashboardBackup {
  last?: string
  size_mb?: number
  count?: number
}

interface DashboardCompleteness {
  pct: number
  has_summary: number
  has_images: number
  has_place: number
  total: number
  orphans?: number
}

interface DashboardStats {
  total_entities?: number
  entities_week?: number
  total_places?: number
  total_relationships?: number
  total_itineraries?: number
  total_users?: number
  users_week?: number
  total_posts?: number
  posts_week?: number
  backup?: DashboardBackup
  completeness?: DashboardCompleteness
  by_type?: Record<string, number>
}

interface DashboardHealth {
  status?: string
  version?: string
  uptime_seconds: number
  memory_mb?: number
  llm_api?: string
  data_quality?: {
    coverage_pct?: number
  }
}

interface DashboardOps {
  status?: string
  release?: {
    gate_covers_backend_frontend_e2e?: boolean
    deploy_health_blocking?: boolean
    deploy_host_env_configured?: boolean
    latest_migration?: string
    schema_ok?: boolean
    schema_version?: number
    required_schema_version?: number
  }
  schema?: Record<string, unknown>
  shared_controls?: {
    rate_limit_enabled?: boolean
    idempotency_enabled?: boolean
    tables_ready?: boolean
  }
  queues?: Record<string, number>
  rollback?: {
    backup_ready?: boolean
    latest_backup?: string | null
  }
  quality_trend?: {
    available?: boolean
    latest?: Record<string, { value?: number; unit?: string; created_at?: string }>
    delta_7d?: Record<string, number>
    budget_failures?: Array<{ metric_key?: string; value?: number; expected?: number; op?: string }>
    sample_count?: number
    last_recorded_at?: string | null
  }
}

const stats = ref<DashboardStats>({})
const alerts = ref<Array<{ type: string; count: number; label: string; icon: string; link: string; priority: number }>>([])
const health = ref<DashboardHealth | null>(null)
const ops = ref<DashboardOps | null>(null)
const recentActivity = ref<Array<{ method: string; path: string; ts: string }>>([])
const loading = ref(true)
const loadError = ref(false)
const partialDegraded = ref(false)
const degradedDetail = ref('')
const backupRunning = ref(false)


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

function formatQualityTrend(trend?: DashboardOps['quality_trend']): string {
  if (!trend?.available) return 'Chưa có snapshot'
  const score = trend.latest?.quality_score_avg?.value
  if (typeof score === 'number') return `${score.toFixed(1)}/100`
  const failures = trend.budget_failures?.length || 0
  return failures ? `${failures} budget fail` : 'Đang theo dõi'
}

function formatQualityTrendDetail(trend?: DashboardOps['quality_trend']): string {
  if (!trend?.available) return 'Chạy quality_budget --record-db'
  const delta = trend.delta_7d?.quality_score_avg
  const failures = trend.budget_failures?.length || 0
  const parts: string[] = []
  if (typeof delta === 'number') parts.push(`7 ngày ${delta >= 0 ? '+' : ''}${delta.toFixed(1)}`)
  if (failures) parts.push(`${failures} budget cần xử lý`)
  if (!parts.length && trend.sample_count) parts.push(`${trend.sample_count} snapshot 30 ngày`)
  return parts.join(' · ') || 'Ổn định'
}

function timeAgo(ts: string): string {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (diff < 60) return 'vừa xong'
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  return `${Math.floor(diff / 86400)} ngày trước`
}

function activityLabel(a: { method: string; path: string }): string {
  const p = (a.path || '').replace('/admin-api', '').replace('/admin', '')
  const m = (a.method || '').toUpperCase()
  const seg = (p.split('?')[0] || '').split('/').filter(Boolean) // e.g. ['entities','xyz']
  const res = seg[0] || ''
  const NOUN: Record<string, string> = {
    entities: 'địa điểm', relationships: 'quan hệ', moderation: 'kiểm duyệt',
    users: 'người dùng', itineraries: 'lịch trình', media: 'ảnh', settings: 'cài đặt',
    'site-settings': 'cài đặt', backup: 'backup', 'backup-trigger': 'backup',
  }
  const noun = NOUN[res] || res || 'mục'
  const VERB: Record<string, string> = { POST: 'Tạo', PUT: 'Sửa', PATCH: 'Sửa', DELETE: 'Xoá', GET: 'Xem' }
  const verb = VERB[m] || m
  return `${verb} ${noun}`
}

const TYPE_COLORS: Record<string, string> = {
  attraction: '#219653', dish: '#FF9F0A', product: '#3478F6',
  accommodation: '#AF52DE', nature: '#34C759', experience: '#FF9500',
  craft_village: '#A6822A', event: '#FF3B30', drink: '#30B0C7',
  facility: '#8E8E93',
}

const completenessSegments = computed(() => {
  const c = stats.value?.completeness
  if (!c || !c.total) return []
  const pct = (n: number) => Math.round((n / c.total) * 100)
  return [
    { key: 'summary', label: 'Tóm tắt', count: c.has_summary, pct: pct(c.has_summary), color: 'var(--primary)' },
    { key: 'images', label: 'Ảnh', count: c.has_images, pct: pct(c.has_images), color: 'var(--success)' },
    { key: 'place', label: 'Phường-xã', count: c.has_place, pct: pct(c.has_place), color: 'var(--warning)' },
  ]
})

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

const opsQueueTotal = computed(() => {
  const queues = ops.value?.queues || {}
  return Object.values(queues).reduce((sum, value) => sum + (Number(value) || 0), 0)
})
const adminOpsActions = computed(() => buildAdminOpsActions({
  healthStatus: health.value?.status,
  releaseGateOk: ops.value?.release?.gate_covers_backend_frontend_e2e,
  deployHealthBlocking: ops.value?.release?.deploy_health_blocking,
  deployHostConfigured: ops.value?.release?.deploy_host_env_configured,
  rollbackReady: ops.value?.rollback?.backup_ready,
  queues: ops.value?.queues,
  dataQualityCoverage: health.value?.data_quality?.coverage_pct,
}))

const DEGRADED = Symbol('degraded')

async function fetchDashboard() {
  loading.value = true
  loadError.value = false
  partialDegraded.value = false
  try {
    const [s, a, h, opsRes, auditRes] = await Promise.all([
      $fetch<DashboardStats>('/admin-api/stats', { headers: authHeaders() }),
      $fetch<{ alerts: typeof alerts.value }>('/admin-api/dashboard-alerts', { headers: authHeaders() }).catch(() => DEGRADED),
      $fetch<DashboardHealth>('/health/internal', { headers: authHeaders() }).catch(() => DEGRADED),
      $fetch<DashboardOps>('/admin-api/ops-summary', { headers: authHeaders() }).catch(() => DEGRADED),
      $fetch<{ entries: any[] }>('/admin-api/audit-log?limit=10', { headers: authHeaders() }).catch(() => DEGRADED),
    ])
    stats.value = s
    if (a !== DEGRADED) alerts.value = (a as { alerts: typeof alerts.value }).alerts
    if (h !== DEGRADED) health.value = h as DashboardHealth
    if (opsRes !== DEGRADED) ops.value = opsRes as DashboardOps
    if (auditRes !== DEGRADED) recentActivity.value = (auditRes as { entries: any[] }).entries || []
    const degradedParts: string[] = []
    if (a === DEGRADED) degradedParts.push('cảnh báo')
    if (h === DEGRADED) degradedParts.push('trạng thái agent')
    if (auditRes === DEGRADED) degradedParts.push('nhật ký')
    if (opsRes === DEGRADED) degradedParts.push('ops cockpit')
    partialDegraded.value = degradedParts.length > 0
    degradedDetail.value = degradedParts.join(', ')
  } catch {
    loadError.value = true
    showToast('Không thể tải dữ liệu dashboard', 'error')
  }
  loading.value = false
}

async function triggerBackup() {
  backupRunning.value = true
  try {
    const r = await $fetch<{ success: boolean; backup_name: string; size_mb: number }>('/admin-api/backup-trigger', { method: 'POST', headers: authHeaders() })
    showToast(`Backup thành công: ${r.backup_name} (${r.size_mb}MB)`, 'success')
    await fetchDashboard()
  } catch (e: unknown) { showToast(getErrorDetail(e, 'Backup thất bại'), 'error') }
  backupRunning.value = false
}

onMounted(fetchDashboard)
</script>

<style scoped>
.dash-subtitle { font-size: .88rem; color: var(--muted); margin-top: var(--space-1); }

/* ── Full error state ── */
.dash-error-state {
  display: flex; align-items: flex-start; gap: var(--space-4);
  padding: var(--space-6); border-radius: 14px; margin-bottom: var(--space-6);
  background: rgba(var(--danger-rgb),.06); border: .5px solid rgba(var(--danger-rgb),.2);
  color: var(--ink);
}
.dash-error-icon { font-size: 2rem; flex-shrink: 0; opacity: .6; }
.dash-error-body { display: flex; flex-direction: column; gap: var(--space-2); }
.dash-error-body strong { font-size: 1rem; }
.dash-error-body p { font-size: .88rem; color: var(--muted); margin: 0; }
.dark .dash-error-state { background: rgba(var(--danger-rgb),.08); border-color: rgba(var(--danger-rgb),.15); }

/* Signal freshly-loaded (vs stale) data: fade content in after fetch resolves */
.dash-loaded { animation: dash-fade-in .4s var(--ease-out) both; }
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
  transition: transform .3s var(--ease-soft), box-shadow .3s, border-color .3s;
}
.dash-stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.dash-stat-card:active { transform: scale(.98); }
.dash-stat-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; flex-shrink: 0;
  transition: transform .25s var(--ease-soft);
}
.dash-stat-card:hover .dash-stat-icon { transform: scale(1.08); }
.dash-stat-value { font-size: 1.5rem; font-weight: 800; line-height: 1.2; }
.dash-stat-label { font-size: .75rem; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: .5px; }
.dash-delta { font-size: .7rem; font-weight: 600; color: var(--secondary); margin-left: var(--space-1); }

/* ── Partial-degradation banner ── */
.dash-degraded {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) var(--space-4); border-radius: 10px;
  margin-bottom: var(--space-5); font-size: .85rem; font-weight: 500;
  background: rgba(var(--warning-rgb),.1); color: var(--warning);
  border: .5px solid rgba(var(--warning-rgb),.2);
}
.dash-degraded-icon { font-size: 1rem; flex-shrink: 0; }
.dark .dash-degraded { background: rgba(var(--warning-rgb),.08); color: var(--accent); border-color: rgba(var(--warning-rgb),.15); }

/* ── Alert banners ── */
.dash-alerts { display: flex; flex-direction: column; gap: var(--space-3); margin-bottom: var(--space-8); }
.dash-alert {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4); border-radius: 10px;
  text-decoration: none; font-size: .88rem; font-weight: 500;
  transition: transform .25s var(--ease-soft), opacity .2s;
}
.dash-alert:hover { transform: translateX(4px); }
.dash-alert:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
.dash-alert.warn { background: rgba(var(--warning-rgb),.1); color: var(--warning); border: .5px solid rgba(var(--warning-rgb),.2); }
.dash-alert.error { background: rgba(var(--danger-rgb),.1); color: var(--error); border: .5px solid rgba(var(--danger-rgb),.2); }
.dash-alert.info { background: rgba(var(--blue-rgb),.08); color: rgb(var(--blue-rgb)); border: .5px solid rgba(var(--blue-rgb),.15); }
.dash-alert-icon { font-size: 1.1rem; flex-shrink: 0; }
.dash-alert-num { font-size: 1.3rem; font-weight: 800; min-width: 32px; }
.dash-alert-arrow { margin-left: auto; opacity: .5; }
.dash-all-clear {
  display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4);
  border-radius: 10px; margin-bottom: var(--space-8); font-size: .88rem; font-weight: 500;
  background: rgba(var(--primary-rgb),.08); color: var(--primary); border: .5px solid rgba(var(--primary-rgb),.15);
}

/* ── System health ── */
.dash-health {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-4) var(--space-5); margin-bottom: var(--space-6);
}
.dash-health-header { display: flex; align-items: center; gap: var(--space-2); font-size: .88rem; }
.dash-health-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dash-health-dot.ok { background: var(--secondary); }
.dash-health-dot.degraded { background: rgb(var(--warning-rgb)); }
.dash-health-ver { margin-left: auto; font-size: .75rem; color: var(--muted); }
.dash-health-metrics {
  display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-5);
  margin-top: var(--space-3); font-size: .82rem; color: var(--muted);
}
.dash-health-metrics b { color: var(--ink); font-weight: 600; }
.dash-health-warn { color: rgb(var(--warning-rgb)) !important; }
.dash-backup-btn {
  display: inline-block; margin-left: var(--space-2); padding: 2px 10px; border-radius: 6px;
  border: .5px solid var(--line); background: var(--bg); color: var(--primary-fg);
  font-size: .72rem; font-weight: 600; cursor: pointer; transition: background .2s;
}
.dash-backup-btn:hover:not(:disabled) { background: rgba(var(--primary-rgb),.08); }
.dash-backup-btn:disabled { opacity: var(--opacity-disabled); cursor: wait; }
.dark .dash-health { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }

/* ── Entity completeness ── */
.dash-completeness {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-4) var(--space-5); margin-bottom: var(--space-6);
}
.dash-comp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); font-size: .88rem; }
.dash-comp-pct { font-weight: 800; font-size: 1.1rem; }
.dash-comp-seg { display: grid; grid-template-columns: 72px 1fr 56px; align-items: center; gap: var(--space-2); margin-top: var(--space-1); }
.dcs-label { font-size: var(--text-xs); color: var(--muted); }
.dcs-bar { height: 8px; background: var(--line); border-radius: var(--radius-full); overflow: hidden; }
.dcs-fill { height: 100%; border-radius: var(--radius-full); transition: width .4s var(--ease-out, ease); }
.dcs-val { font-size: var(--text-2xs); color: var(--muted); text-align: right; }
.dash-comp-details { display: flex; gap: var(--space-4); margin-top: var(--space-3); font-size: .78rem; color: var(--muted); }
.dash-orphan-link { color: inherit; text-decoration: none; border-bottom: 1px dashed rgb(var(--warning-rgb)); }
.dash-orphan-link:hover { color: rgb(var(--warning-rgb)); }
.dash-orphan-count { color: rgb(var(--warning-rgb)); }
.dark .dash-completeness { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }

/* ── Quick actions ── */
.dash-section { margin-bottom: var(--space-6); }
.dash-actions { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: var(--space-3); }
.dash-action {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-5) var(--space-3); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  text-decoration: none; color: inherit; font-size: .85rem; font-weight: 500;
  transition: transform .3s var(--ease-soft), box-shadow .3s, border-color .3s;
}
.dash-action:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.06); border-color: var(--primary); background: color-mix(in oklab, var(--primary) 6%, var(--bg)); }
.dash-action:active { transform: scale(.97); }
.dash-action:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
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
  animation: dash-donut-in .6s var(--ease-standard) both;
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
.dash-legend-item { display: flex; align-items: center; gap: var(--space-1); font-size: .72rem; }
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
  animation: dash-bar-grow .5s var(--ease-standard) both;
}
@keyframes dash-bar-grow { from { width: 0 !important; } }
.dash-bar-count { font-size: .82rem; font-weight: 700; text-align: right; }

/* ── Refresh animation ── */
.refresh-spin { display: inline-block; font-size: 1.3rem; line-height: 1; animation: admin-spin .6s linear infinite; }
.admin-refresh:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }

/* ── Dark mode ── */
.dark .dash-stat-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .dash-alert.warn { background: rgba(var(--warning-rgb),.08); color: var(--accent); border-color: rgba(var(--warning-rgb),.15); }
.dark .dash-alert.error { background: rgba(var(--danger-rgb),.08); color: rgb(var(--red-rgb)); border-color: rgba(var(--danger-rgb),.15); }
.dark .dash-action { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dash-action:hover { border-color: var(--primary); box-shadow: 0 4px 12px rgba(0,0,0,.3); background: color-mix(in oklab, var(--primary) 12%, var(--card, #2c2c2e)); }
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
.activity-method.post { background: rgba(var(--secondary-rgb),.15); color: var(--secondary); }
.activity-method.put, .activity-method.patch { background: rgba(var(--warning-rgb),.15); color: rgb(var(--warning-rgb)); }
.activity-method.delete { background: rgba(var(--red-rgb),.15); color: rgb(var(--red-rgb)); }
.activity-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.activity-label { color: var(--ink); font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.activity-path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); font-size: .7rem; }
.activity-time { color: var(--muted); font-size: .72rem; white-space: nowrap; }
.dash-ops {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-4) var(--space-5); margin-bottom: var(--space-6);
}
.dash-ops-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-4); }
.dash-ops-head strong { display: block; font-size: .92rem; }
.dash-ops-head p { margin: 2px 0 0; color: var(--muted); font-size: .78rem; }
.dash-ops-status {
  padding: 3px 9px; border-radius: 999px; font-size: .72rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .02em;
}
.dash-ops-status.ok { background: rgba(var(--secondary-rgb, 33,150,83), .12); color: var(--secondary); }
.dash-ops-status.attention { background: rgba(var(--warning-rgb), .12); color: rgb(var(--warning-rgb)); }
.dash-ops-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-3); }
.dash-ops-cell {
  min-width: 0; display: flex; flex-direction: column; gap: 3px;
  padding: var(--space-3); border: .5px solid var(--line); border-radius: 10px;
  background: rgba(142,142,147,.06);
}
.dash-ops-cell b { font-size: .9rem; color: var(--ink); }
.dash-ops-cell small, .dash-ops-label { color: var(--muted); font-size: .75rem; overflow-wrap: anywhere; }
.dash-ops-label { font-weight: 650; text-transform: uppercase; letter-spacing: .02em; }
.dark .dash-ops { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
@media (max-width: 900px) { .dash-ops-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 520px) { .dash-ops-grid { grid-template-columns: 1fr; } }
</style>
