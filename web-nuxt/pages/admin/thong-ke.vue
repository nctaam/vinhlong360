<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Thống kê & Phân tích</h1>
        <p class="tk-subtitle">User hỏi gì, bot bí ở đâu, chi phí LLM</p>
      </div>
      <div class="tk-head-actions">
        <button type="button" class="btn btn-outline btn-sm" :disabled="loading || !data.popular" @click="exportCSV">&#128190; Xuất CSV</button>
        <button type="button" class="admin-refresh" :disabled="loading" @click="fetchData">
          <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
        </button>
      </div>
    </div>

    <!-- Date range filter -->
    <div class="tk-range-chips" role="group" aria-label="Khoảng thời gian">
      <button v-for="r in RANGES" :key="r.days" type="button" class="tk-chip" :class="{ active: rangeDays === r.days }" @click="setRange(r.days)">{{ r.label }}</button>
    </div>

    <!-- Skeleton placeholders while loading (replaces flash of empty spinner) -->
    <div v-if="loading" role="status" aria-label="Đang tải thống kê">
      <div class="tk-skeleton" aria-hidden="true">
        <div class="stat-grid">
          <div v-for="n in 4" :key="'sk-card-' + n" class="tk-sk-card" :style="{ animationDelay: (n * 80) + 'ms' }"></div>
        </div>
        <div class="tk-panels">
          <div v-for="n in 3" :key="'sk-panel-' + n" class="tk-sk-panel" :style="{ animationDelay: (n * 100) + 'ms' }"></div>
        </div>
      </div>
    </div>
    <div v-else-if="loadError" class="admin-empty">
      <p>Không tải được thống kê.</p>
      <button type="button" class="btn btn-secondary" @click="fetchData">Thử lại</button>
    </div>
    <template v-else>

    <!-- Summary cards -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="tk-icon" style="background: rgba(var(--blue-rgb),.1); color: #3478F6;">&#128172;</div>
        <div class="tk-stat-body">
          <div class="stat-value">{{ data.summary?.total_queries ?? '—' }}</div>
          <div class="stat-label">Tổng truy vấn</div>
        </div>
        <svg v-if="sparkPoints.length > 1" class="tk-spark" viewBox="0 0 80 24" preserveAspectRatio="none" role="img" aria-label="Xu hướng entity 30 ngày"><title>Trend</title><polyline :points="sparkPoints" fill="none" stroke="#3478F6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </div>
      <div class="stat-card">
        <div class="tk-icon" style="background: rgba(175,82,222,.1); color: #AF52DE;">&#128161;</div>
        <div class="tk-stat-body">
          <div class="stat-value">{{ data.summary?.unique_queries ?? '—' }}</div>
          <div class="stat-label">Truy vấn khác nhau</div>
        </div>
      </div>
      <div class="stat-card" :class="{ 'status-warn': (data.gaps || []).length > 5 }">
        <div class="tk-icon" style="background: rgba(var(--warning-rgb),.1); color: #FF9F0A;">&#128371;</div>
        <div class="tk-stat-body">
          <div class="stat-value">{{ (data.gaps || []).length }}</div>
          <div class="stat-label">Knowledge gaps</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="tk-icon" style="background: rgba(var(--primary-rgb),.1); color: #219653;">&#128176;</div>
        <div class="tk-stat-body">
          <div class="stat-value">
            {{ costTotal }}
            <span v-if="costScope" class="tk-cost-scope">{{ costScope }}</span>
          </div>
          <div class="stat-label">Chi phí (ước)</div>
        </div>
      </div>
    </div>

    <!-- Three-column panels -->
    <section class="tk-section" aria-label="Phân tích chi tiết">
    <h2 class="tk-section-title">Phân tích chi tiết</h2>
    <div class="tk-panels">
      <section class="tk-panel">
        <div class="tk-panel-head">
          <h3>Câu hỏi phổ biến</h3>
          <span class="tk-count-badge" v-if="(data.popular || []).length">{{ (data.popular || []).length }}</span>
        </div>
        <ol v-if="(data.popular || []).length" class="tk-list">
          <li v-for="(it, i) in data.popular" :key="i">
            <div class="tk-bar-bg" :style="{ width: barPct(it, data.popular) + '%' }"></div>
            <span class="tk-rank">{{ i + 1 }}</span>
            <span class="tk-query">{{ label(it) }}</span>
            <span class="tk-hits">{{ count(it) }}</span>
          </li>
        </ol>
        <div v-else class="tk-empty">
          <span class="tk-empty-icon">&#128172;</span>
          <span>Chưa có dữ liệu truy vấn.</span>
        </div>
      </section>

      <section class="tk-panel">
        <div class="tk-panel-head">
          <h3>Bot bí (cần bổ sung KB)</h3>
          <span class="tk-count-badge tk-count-warn" v-if="(data.gaps || []).length">{{ (data.gaps || []).length }}</span>
        </div>
        <ol v-if="(data.gaps || []).length" class="tk-list">
          <li v-for="(it, i) in data.gaps" :key="i">
            <div class="tk-bar-bg tk-bar-warn" :style="{ width: barPct(it, data.gaps) + '%' }"></div>
            <span class="tk-rank">{{ i + 1 }}</span>
            <span class="tk-query">{{ label(it) }}</span>
            <span class="tk-hits">{{ count(it) }}</span>
            <NuxtLink :to="`/admin/entities?q=${encodeURIComponent(String(label(it)))}`" class="tk-gap-action" title="Tìm entity">&#128269;</NuxtLink>
            <NuxtLink to="/admin/entities?create=1" class="tk-gap-action" title="Tạo entity">&#10010;</NuxtLink>
          </li>
        </ol>
        <div v-else class="tk-empty tk-empty-ok">
          <span class="tk-empty-icon">&#9989;</span>
          <span>Không có gap — tốt!</span>
        </div>
      </section>

      <section class="tk-panel">
        <div class="tk-panel-head">
          <h3>Entity được xem nhiều</h3>
          <span class="tk-count-badge" v-if="(data.top_entities || []).length">{{ (data.top_entities || []).length }}</span>
        </div>
        <ol v-if="(data.top_entities || []).length" class="tk-list">
          <li v-for="(it, i) in data.top_entities" :key="i">
            <div class="tk-bar-bg tk-bar-green" :style="{ width: barPct(it, data.top_entities) + '%' }"></div>
            <span class="tk-rank">{{ i + 1 }}</span>
            <span class="tk-query">{{ it.name || it.id || label(it) }}</span>
            <span class="tk-hits">{{ count(it) }}</span>
          </li>
        </ol>
        <div v-else class="tk-empty">
          <span class="tk-empty-icon">&#128205;</span>
          <span>Chưa có dữ liệu xem entity.</span>
        </div>
      </section>
    </div>
    </section>

    </template>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Thống kê — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const data = ref<Record<string, unknown>>({})
const loading = ref(true)
const loadError = ref(false)

const RANGES = [
  { days: 7, label: '7 ngày' },
  { days: 30, label: '30 ngày' },
  { days: 90, label: '90 ngày' },
  { days: 0, label: 'Tất cả' },
] as const
const rangeDays = ref(0)

function setRange(days: number) {
  rangeDays.value = days
  fetchData()
}

const sparkPoints = computed(() => {
  const daily = ((data.value?.daily || []) as Array<{ queries?: number }>).slice().reverse()
  if (daily.length < 2) return ''
  const vals = daily.map(d => d.queries || 0)
  const max = Math.max(...vals, 1)
  const w = 80, h = 24
  return vals.map((v, i) => `${((i / (vals.length - 1)) * w).toFixed(1)},${(h - (v / max) * (h - 2) - 1).toFixed(1)}`).join(' ')
})

function label(it: Record<string, unknown>) { return it?.query ?? it?.q ?? it?.name ?? String(it) }
function count(it: Record<string, unknown>) { return it?.count ?? it?.hits ?? it?.n ?? '' }
function barPct(it: Record<string, unknown>, list: unknown) {
  const arr = (list || []) as Record<string, unknown>[]
  const max = Math.max(...arr.map(x => Number(count(x)) || 0), 1)
  return Math.round(((Number(count(it)) || 0) / max) * 100)
}

const costTotal = computed(() => {
  const c = (data.value?.costs || {}) as Record<string, unknown>
  if (c.available === false) return '—'
  const v = c.total_cost ?? c.total ?? (c.monthly as Record<string, unknown>)?.spent ?? (c.daily as Record<string, unknown>)?.spent
  return v != null ? (typeof v === 'number' ? v.toLocaleString('vi-VN') : v) : '—'
})

// Scope label for the cost card — derived from which field supplied the value (no extra backend data)
const costScope = computed(() => {
  const c = (data.value?.costs || {}) as Record<string, unknown>
  if (c.available === false) return ''
  if (c.total_cost != null || c.total != null) return ''
  if ((c.monthly as Record<string, unknown>)?.spent != null) return 'tháng'
  if ((c.daily as Record<string, unknown>)?.spent != null) return 'ngày'
  return ''
})

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const params = rangeDays.value ? `?days=${rangeDays.value}` : ''
    data.value = await $fetch<Record<string, unknown>>(`/admin-api/analytics-overview${params}`, { headers: authHeaders() })
  } catch (e: unknown) {
    loadError.value = true
    showToast(getErrorDetail(e, 'Không thể tải thống kê'), 'error')
  } finally {
    loading.value = false
  }
}

function exportCSV() {
  const rows: string[][] = [['Danh mục', 'Truy vấn/Entity', 'Lượt']]
  for (const it of (data.value.popular || []) as Record<string, unknown>[])
    rows.push(['Phổ biến', String(label(it)), String(count(it))])
  for (const it of (data.value.gaps || []) as Record<string, unknown>[])
    rows.push(['Knowledge gap', String(label(it)), String(count(it))])
  for (const it of (data.value.top_entities || []) as Record<string, unknown>[])
    rows.push(['Entity', String(label(it)), String(count(it))])
  const csv = rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `analytics-${new Date().toISOString().slice(0, 10)}.csv`
  a.click(); URL.revokeObjectURL(url)
}

onMounted(fetchData)
</script>

<style scoped>
.tk-head-actions { display: flex; gap: var(--space-2); align-items: center; }
.tk-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Stat card icon ── */
.stat-card { display: flex; align-items: center; gap: var(--space-4); position: relative; overflow: hidden; }
.tk-stat-body { flex: 1; min-width: 0; }
.tk-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; flex-shrink: 0;
}

/* ── Metric hierarchy (page-local override of shared .stat-card) ── */
.stat-card .stat-value {
  font-size: 2rem; line-height: 1.1; font-weight: 800;
  display: flex; align-items: baseline; gap: 6px;
}
.stat-card .stat-label {
  font-size: .7rem; text-transform: uppercase; letter-spacing: .6px;
  font-weight: 600; color: var(--muted); margin-top: 3px;
}
/* Cost-scope micro badge ("tháng" / "ngày") */
.tk-cost-scope {
  font-size: .62rem; font-weight: 700; line-height: 1;
  text-transform: uppercase; letter-spacing: .4px;
  padding: 2px 6px; border-radius: 100px;
  background: rgba(var(--primary-rgb),.12); color: #219653;
  align-self: center;
}

/* ── Warn-state card: tint + border/icon only, neutral text ── */
.stat-card.status-warn {
  border-color: var(--warning, #e67e22);
  background: rgba(230,126,34,.04);
}
.stat-card.status-warn .tk-icon {
  background: rgba(var(--warning-rgb),.18) !important;
  color: var(--warning, #e67e22) !important;
}

/* ── Section grouping + divider ── */
.tk-section { margin-top: var(--space-6); }
.tk-section-title {
  font-size: .95rem; font-weight: 600; color: var(--muted);
  margin: 0 0 var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px dashed var(--line);
}

/* ── Panels ── */
.tk-panels {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-4);
}
.tk-panel {
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-5); overflow: hidden;
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.tk-panel:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,.06); border-color: rgba(var(--blue-rgb),.15); }

.tk-panel-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-4);
}
.tk-panel-head h2 { font-size: .95rem; font-weight: 600; margin: 0; }

.tk-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 8px;
  border-radius: 100px; font-size: .72rem; font-weight: 700;
  background: rgba(var(--blue-rgb),.1); color: #3478F6;
  font-family: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
  transition: background .2s, color .2s;
}
.tk-count-warn { background: rgba(var(--warning-rgb),.1); color: #c67a00; }
/* Brighten badge when scanning the panel */
.tk-panel:hover .tk-count-badge { background: rgba(var(--blue-rgb),.22); }
.tk-panel:hover .tk-count-warn { background: rgba(var(--warning-rgb),.22); }

/* ── List items ── */
.tk-list { list-style: none; padding: 0; margin: 0; }
.tk-list li {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: .5px solid var(--line);
  font-size: .85rem;
  transition: background .15s;
  position: relative;
}
.tk-list li:last-child { border-bottom: none; }
.tk-list li:hover { background: rgba(0,0,0,.015); margin: 0 calc(var(--space-2) * -1); padding-left: var(--space-2); padding-right: var(--space-2); border-radius: 6px; }
.tk-rank {
  width: 24px; height: 24px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-size: .72rem; font-weight: 700; flex-shrink: 0;
  background: var(--bg-alt); color: var(--muted);
  font-variant-numeric: tabular-nums;
}
/* Semantic ranking: top-3 solid, 4-10 muted outline, rest plain */
.tk-list li:nth-child(-n+3) .tk-rank { background: var(--primary, #219653); color: #fff; }
.tk-list li:nth-child(n+4):nth-child(-n+10) .tk-rank {
  background: transparent; border: 1px solid rgba(var(--primary-rgb),.3); color: #219653;
}
.tk-query { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tk-hits {
  flex: 0 0 auto; text-align: right;
  font-weight: 700; color: var(--primary, #219653); font-size: .82rem;
  position: relative;
  font-family: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
}

/* ── Bar background in list items ── */
.tk-bar-bg {
  position: absolute; left: 0; top: 0; bottom: 0;
  border-radius: 6px; opacity: .07;
  background: #3478F6;
  animation: tk-bar-grow .5s cubic-bezier(.4,0,.2,1) both;
  pointer-events: none;
}
.tk-bar-warn { background: #FF9F0A; }
.tk-bar-green { background: #219653; }
@keyframes tk-bar-grow { from { width: 0 !important; } }

.tk-rank { position: relative; }
.tk-query { position: relative; }

/* ── Empty states ── */
.tk-empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-6) 0; color: var(--muted); font-size: .85rem;
}
.tk-empty-icon { font-size: 1.8rem; opacity: .3; }
.tk-empty-ok { color: var(--primary, #219653); }
.tk-empty-ok .tk-empty-icon { opacity: .5; }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .tk-panel:hover { transform: none; }
}

/* ── Dark mode ── */
.dark .tk-panel {
  background: rgb(46,46,50);
  border-color: rgba(255,255,255,.1);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
}
.dark .tk-panel:hover { box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 4px 16px rgba(0,0,0,.3); border-color: rgba(var(--blue-rgb),.3); }
.dark .tk-list li:hover { background: rgba(255,255,255,.03); }
.dark .tk-rank { background: rgba(255,255,255,.06); }
.dark .tk-list li:nth-child(n+4):nth-child(-n+10) .tk-rank { border-color: rgba(var(--primary-rgb),.5); color: #4fb87a; }
.dark .tk-count-badge { background: rgba(var(--blue-rgb),.15); }
.dark .tk-count-warn { background: rgba(var(--warning-rgb),.15); color: #ffb340; }
.dark .tk-panel:hover .tk-count-badge { background: rgba(var(--blue-rgb),.3); }
.dark .tk-panel:hover .tk-count-warn { background: rgba(var(--warning-rgb),.28); }
/* stat-value (primary green) — keep high contrast in dark */
.dark .stat-card .stat-value { color: #4fb87a; }
.dark .tk-cost-scope { background: rgba(var(--primary-rgb),.22); color: #6fce96; }
.dark .stat-card.status-warn { background: rgba(240,160,80,.08); border-color: var(--warning, #f0a050); }
.dark .tk-sk-card, .dark .tk-sk-panel { background: rgba(255,255,255,.06); }

/* ── Loading skeleton ── */
.tk-skeleton .stat-grid { margin-bottom: var(--space-8); }
.tk-sk-card {
  height: 80px; border-radius: 14px; background: var(--line);
  opacity: .4; animation: tk-skeleton-pulse 1.4s ease-in-out infinite;
}
.tk-skeleton .tk-panels {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--space-4);
}
.tk-sk-panel {
  height: 256px; border-radius: 14px; background: var(--line);
  opacity: .3; animation: tk-skeleton-pulse 1.4s ease-in-out infinite;
}
@keyframes tk-skeleton-pulse {
  0%, 100% { opacity: .4; }
  50% { opacity: .65; }
}

/* ── Responsive stat-grid (page-local) ── */
@media (min-width: 768px) and (max-width: 1024px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 767px) {
  .stat-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .tk-panels { grid-template-columns: 1fr; }
}

/* ── Reduced motion: skeleton ── */
@media (prefers-reduced-motion: reduce) {
  .tk-sk-card, .tk-sk-panel { animation: none; }
}
/* ── Sparkline ── */
.tk-spark {
  width: 80px; height: 24px; flex-shrink: 0; opacity: .5;
  transition: opacity .2s;
}
.stat-card:hover .tk-spark { opacity: .9; }

/* ── Date range chips ── */
.tk-range-chips { display: flex; gap: var(--space-2); margin-bottom: var(--space-5); flex-wrap: wrap; }
.tk-chip {
  padding: 6px 14px; border-radius: 100px; border: .5px solid var(--line);
  background: var(--bg); color: var(--muted); font-size: .82rem; font-weight: 500;
  cursor: pointer; transition: all .2s;
}
.tk-chip:hover { border-color: var(--primary, #219653); color: var(--ink); }
.tk-chip.active { background: var(--primary, #219653); color: #fff; border-color: var(--primary, #219653); }
.tk-chip:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dark .tk-chip.active { background: var(--primary, #219653); }

.tk-gap-action { text-decoration: none; font-size: .8rem; opacity: .4; transition: opacity .15s; margin-left: 2px; }
.tk-gap-action:hover { opacity: 1; }
</style>
