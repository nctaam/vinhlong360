<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Knowledge Agent</h1>
        <p class="ai-subtitle">Giám sát LLM, cache, chi phí và subsystems</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="refreshing" @click="refreshAll"><span :class="{ 'refresh-spin': refreshing }">&#8635;</span> Làm mới</button>
    </div>

    <div v-if="!health && !healthError" class="admin-loading" role="status" aria-label="Đang tải trạng thái agent"><div class="spinner"></div></div>
    <div v-else-if="!health && healthError" class="admin-empty">
      <p>Không kết nối được Knowledge Agent.</p>
      <button type="button" class="btn btn-secondary" @click="refreshAll">Thử lại</button>
    </div>
    <template v-else>

    <!-- Health Status -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-icon" :style="{ background: statusBg, color: statusColor }">&#9889;</div>
        <div>
          <div class="stat-value" :style="{ color: statusColor }">{{ health?.status || '—' }}</div>
          <div class="stat-label">Trạng thái</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon si-blue">&#128640;</div>
        <div>
          <div class="stat-value">{{ health?.version || '—' }}</div>
          <div class="stat-label">Phiên bản</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon si-purple">&#129302;</div>
        <div>
          <div class="stat-value ai-model-val">{{ health?.model || health?.llm_api || '—' }}</div>
          <div class="stat-label">Model / API</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon si-orange">&#128338;</div>
        <div>
          <div class="stat-value">{{ uptime }}</div>
          <div class="stat-label">Uptime</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon si-green">&#127760;</div>
        <div>
          <div class="stat-value">{{ health?.entities || '—' }}</div>
          <div class="stat-label">Entities (KB)</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon si-teal">&#128190;</div>
        <div>
          <div class="stat-value">{{ health?.memory_mb || '—' }} MB</div>
          <div class="stat-label">Bộ nhớ</div>
        </div>
      </div>
    </div>

    <!-- Cache Stats -->
    <div v-if="health?.cache" class="ai-section">
      <h2 class="admin-section-title">Cache</h2>
      <div class="ai-cache-row">
        <div class="ai-ring-wrap">
          <svg class="ai-ring" viewBox="0 0 80 80" aria-hidden="true">
            <circle cx="40" cy="40" r="32" fill="none" stroke="var(--line)" stroke-width="8" opacity=".15" />
            <circle cx="40" cy="40" r="32" fill="none"
              :stroke="hitRate >= 70 ? '#219653' : hitRate >= 40 ? '#e67e22' : '#D94F3D'"
              stroke-width="8" stroke-linecap="round"
              :stroke-dasharray="`${hitRate * 2.01} 201`"
              stroke-dashoffset="50.3"
              class="ai-ring-fill"
            />
          </svg>
          <div class="ai-ring-center">
            <span class="ai-ring-val" :style="{ color: hitRate >= 70 ? 'var(--success)' : hitRate >= 40 ? 'var(--warning)' : 'var(--danger)' }">{{ hitRate }}%</span>
            <span class="ai-ring-lbl">hit rate</span>
          </div>
        </div>
        <div class="ai-metrics ai-metrics-col">
          <div class="ai-metric">
            <span class="ai-metric-val">{{ health.cache.size || 0 }}</span>
            <span class="ai-metric-lbl">Entries</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-val" style="color: var(--success)">{{ health.cache.hits || 0 }}</span>
            <span class="ai-metric-lbl">Hits</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-val" style="color: var(--danger)">{{ health.cache.misses || 0 }}</span>
            <span class="ai-metric-lbl">Misses</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Quality -->
    <div v-if="health?.data_quality" class="ai-section">
      <h2 class="admin-section-title">Chất lượng dữ liệu</h2>
      <div class="ai-dq-row">
        <div class="ai-dq-bar-wrap">
          <div class="ai-dq-bar-label">
            <span>Coverage</span>
            <span class="ai-dq-bar-pct" :style="{ color: dataQualityCoverage >= 80 ? 'var(--success)' : 'var(--warning)' }">{{ dataQualityCoverage }}%</span>
          </div>
          <div class="ai-dq-track">
            <div class="ai-dq-fill" :style="{ width: dataQualityCoverage + '%', background: dataQualityCoverage >= 80 ? 'var(--success)' : 'var(--warning)' }"></div>
          </div>
        </div>
        <div class="ai-metric">
          <span class="ai-metric-val">{{ missingSummary }}</span>
          <span class="ai-metric-lbl">Thiếu summary</span>
        </div>
      </div>
    </div>

    <!-- Response Times -->
    <div v-if="health?.response_times" class="ai-section">
      <h2 class="admin-section-title">Response Times</h2>
      <div class="ai-metrics">
        <div class="ai-metric">
          <span class="ai-metric-val" :style="{ color: rtColor(health.response_times.avg_ms) }">
            <span class="ai-rt-dot" :style="{ background: rtColor(health.response_times.avg_ms) }" aria-hidden="true"></span>{{ health.response_times.avg_ms || 0 }}<small>ms</small>
          </span>
          <span class="ai-metric-lbl">Trung bình</span>
        </div>
        <div class="ai-metric">
          <span class="ai-metric-val" :style="{ color: rtColor(health.response_times.p95_ms) }">
            <span class="ai-rt-dot" :style="{ background: rtColor(health.response_times.p95_ms) }" aria-hidden="true"></span>{{ health.response_times.p95_ms || 0 }}<small>ms</small>
          </span>
          <span class="ai-metric-lbl">P95</span>
        </div>
        <div class="ai-metric">
          <span class="ai-metric-val">{{ health.response_times.total || 0 }}</span>
          <span class="ai-metric-lbl">Tổng requests</span>
        </div>
      </div>
    </div>

    <!-- Errors -->
    <div v-if="health?.errors" class="ai-section">
      <h2 class="admin-section-title">Errors</h2>
      <div class="ai-metrics">
        <div class="ai-metric">
          <span class="ai-metric-val" :style="{ color: (health.errors.total || 0) > 0 ? 'var(--danger)' : 'var(--success)' }">{{ health.errors.total || 0 }}</span>
          <span class="ai-metric-lbl">Tổng lỗi</span>
        </div>
        <div class="ai-metric">
          <span class="ai-metric-val">{{ health.errors.recent || 0 }}</span>
          <span class="ai-metric-lbl">Gần đây (1h)</span>
        </div>
      </div>
    </div>

    <!-- Subsystems -->
    <div class="ai-section">
      <h2 class="admin-section-title">Subsystems</h2>
      <div class="ai-subsys-grid">
        <div v-for="(val, key) in subsystems" :key="key" class="ai-subsys" :class="val ? 'ai-subsys-on' : 'ai-subsys-off'" :title="`${key}: ${val ? 'online' : 'offline'}`" :aria-label="`${key}: ${val ? 'online' : 'offline'}`">
          <span class="ai-subsys-dot"></span>
          <span>{{ key }}</span>
        </div>
      </div>
    </div>

    <!-- Cost & Budget -->
    <div class="ai-section">
      <h2 class="admin-section-title">Chi phí & ngân sách</h2>
      <div class="ai-metrics" v-if="cost" aria-live="polite">
        <div class="ai-metric">
          <span class="ai-metric-val">{{ cost.llm?.available ? '$' + (cost.llm.total_cost_usd || 0).toFixed(4) : '—' }}</span>
          <span class="ai-metric-lbl">LLM tích lũy</span>
        </div>
        <div class="ai-metric" :class="{ 'ai-near-cap': agentNearCap }" :aria-label="agentNearCap ? 'Budget near capacity' : undefined">
          <span class="ai-metric-val">{{ cost.agent_budget?.enabled ? `${cost.agent_budget.used_today}/${cost.agent_budget.cap_per_day}` : 'TẮT' }}</span>
          <span class="ai-metric-lbl">Agent LLM hôm nay</span>
        </div>
      </div>
      <p class="ai-cost-note">
        <span class="ai-cost-note-icon" aria-hidden="true">&#8505;</span>
        <span>Agent tự động: <strong>{{ cost?.agent_budget?.enabled ? 'BẬT' : 'TẮT (mặc định)' }}</strong> —
        đổi qua .env AUTONOMOUS_AGENT_ENABLED + AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY.</span>
      </p>
    </div>

    <!-- Actions -->
    <div class="ai-section">
      <h2 class="admin-section-title">Hành động</h2>
      <div class="ai-action-grid">
        <button type="button" class="ai-action-btn ai-action-primary" :disabled="triggerLoading" @click="triggerLearn">
          <span v-if="triggerLoading" class="ai-action-spinner" aria-hidden="true"></span>
          <span v-else class="ai-action-icon">&#129504;</span>
          <span>{{ triggerLoading ? 'Đang chạy...' : 'Trigger Learn' }}</span>
        </button>
        <button type="button" class="ai-action-btn ai-action-primary" :disabled="triageLoading" @click="triage">
          <span v-if="triageLoading" class="ai-action-spinner" aria-hidden="true"></span>
          <span v-else class="ai-action-icon">&#129302;</span>
          <span>{{ triageLoading ? 'Đang phân tích...' : 'Gợi ý ưu tiên' }}</span>
        </button>
        <button type="button" class="ai-action-btn ai-action-secondary" @click="reload">
          <span class="ai-action-icon">&#128260;</span>
          <span>Reload KB</span>
        </button>
      </div>
      <p v-if="triggerResult" class="ai-trigger-result" :class="{ 'ai-result-error': triggerResultIsError }" role="status" aria-live="polite">{{ triggerResult }}</p>
      <div v-if="triageOut" class="ai-triage-box" :class="{ 'ai-triage-error': triageOutIsError }" role="status" aria-live="polite">
        <span class="ai-triage-icon" aria-hidden="true">{{ triageOutIsError ? '⚠' : '✓' }}</span>
        <span class="ai-triage-text">{{ triageOut }}</span>
      </div>
    </div>

    </template>
  </div>
</template>

<script setup lang="ts">
interface AgentHealth {
  status?: string
  version?: string
  model?: string
  llm_api?: string
  uptime_seconds?: number
  entities?: number
  memory_mb?: number
  cache?: { size?: number; hits?: number; misses?: number }
  data_quality?: { coverage_pct?: number; missing_summary?: number }
  response_times?: { avg_ms?: number; p95_ms?: number; total?: number }
  errors?: { total?: number; recent?: number }
  [key: string]: any
}

interface CostOverview {
  llm?: { available?: boolean; total_cost_usd?: number }
  agent_budget?: {
    enabled?: boolean
    used_today?: number
    cap_per_day?: number
    remaining_today?: number
  }
}

interface TriggerLearnResponse {
  message?: string
}

interface TriageResponse {
  ok?: boolean
  suggestion?: string
  note?: string
  context?: string
}
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'AI Quản lý — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

const refreshing = ref(false)
async function refreshAll() {
  refreshing.value = true
  await Promise.all([fetchHealth(), fetchCost()])
  refreshing.value = false
}

const health = ref<AgentHealth | null>(null)
const healthError = ref(false)
const triggerLoading = ref(false)
const triggerResult = ref('')

const statusColor = computed(() => {
  if (!health.value) return 'var(--muted)'
  if (health.value.status === 'ok') return '#219653'
  if (health.value.status === 'degraded') return '#e67e22'
  return '#D94F3D'
})
const statusBg = computed(() => {
  if (!health.value) return 'rgba(142,142,147,.1)'
  if (health.value.status === 'ok') return 'rgba(var(--primary-rgb),.1)'
  if (health.value.status === 'degraded') return 'rgba(var(--warning-rgb),.1)'
  return 'rgba(var(--danger-rgb),.1)'
})

const uptime = computed(() => {
  const s = Number(health.value?.uptime_seconds) || 0
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`
})

const hitRate = computed(() => {
  const c = health.value?.cache
  if (!c) return 0
  const hits = c.hits || 0
  const misses = c.misses || 0
  const total = hits + misses
  return total ? Math.round((hits / total) * 100) : 0
})

const dataQualityCoverage = computed(() => Number(health.value?.data_quality?.coverage_pct ?? 0))
const missingSummary = computed(() => Number(health.value?.data_quality?.missing_summary ?? 0))

const subsystems = computed(() => {
  if (!health.value) return {}
  const keys = ['vector_search', 'recommender', 'realtime', 'semantic_cache', 'guardrails',
    'circuit_breaker', 'parallel_tools', 'autocorrect', 'orchestrator', 'agent_relay',
    'contextual_retrieval', 'ab_testing', 'tracing', 'cost_tracker']
  const result: Record<string, boolean> = {}
  for (const k of keys) {
    if (health.value[k]) result[k.replace(/_/g, ' ')] = (health.value[k] as Record<string, unknown>).available !== false
  }
  return result
})

async function fetchHealth() {
  try { health.value = await $fetch<AgentHealth>('/health'); healthError.value = false } catch { healthError.value = true; showToast('Không kết nối được agent', 'error') }
}

async function triggerLearn() {
  triggerLoading.value = true
  triggerResult.value = ''
  try {
    const res = await $fetch<TriggerLearnResponse>('/admin-api/trigger-learn', { method: 'POST', headers: authHeaders() })
    triggerResult.value = res.message || 'Learning triggered successfully'
  } catch (e: unknown) {
    triggerResult.value = 'Error: ' + getErrorDetail(e, 'failed')
  } finally {
    triggerLoading.value = false
  }
}

const cost = ref<CostOverview | null>(null)
const agentNearCap = computed(() => {
  const b = cost.value?.agent_budget
  if (!b?.enabled) return false
  const remaining = b.remaining_today ?? b.cap_per_day ?? 0
  const cap = b.cap_per_day ?? 0
  return remaining <= Math.max(1, Math.floor(cap / 5))
})
async function fetchCost() {
  try { cost.value = await $fetch<CostOverview>('/admin-api/cost-overview', { headers: authHeaders() }) } catch { showToast('Không tải được chi phí', 'error') }
}

const triageLoading = ref(false)
const triageOut = ref('')
async function triage() {
  triageLoading.value = true
  triageOut.value = ''
  try {
    const r = await $fetch<TriageResponse>('/admin-api/ai/triage', { method: 'POST', headers: authHeaders() })
    triageOut.value = r.ok
      ? `${r.suggestion}`
      : `${r.note || 'LLM lỗi'}\n\n${r.context || ''}`
  } catch (e: unknown) {
    triageOut.value = 'Lỗi: ' + getErrorDetail(e, 'không gọi được')
  } finally {
    triageLoading.value = false
  }
}

async function reload() {
  if (!await confirmDialog('Reload Knowledge Base? Hệ thống sẽ tải lại toàn bộ dữ liệu.', { danger: true })) return
  try {
    await $fetch('/reload', { method: 'POST', headers: authHeaders() })
    triggerResult.value = 'KB reloaded'
    await fetchHealth()
  } catch { triggerResult.value = 'Reload failed' }
}

// ── Presentational helpers (display-only, no effect on call logic) ──
function rtColor(ms: number | undefined): string {
  const v = Number(ms) || 0
  if (v <= 0) return 'var(--ink)'
  if (v < 500) return 'var(--success)'
  if (v <= 1000) return 'var(--warning)'
  return 'var(--danger)'
}
const triggerResultIsError = computed(() => /error|failed|lỗi/i.test(triggerResult.value))
const triageOutIsError = computed(() => /^lỗi|llm lỗi|error/i.test(triageOut.value.trim()))

// ── Auto-hide stale result feedback after 5s (display-only) ──
let triggerResultTimer: ReturnType<typeof setTimeout> | null = null
let triageOutTimer: ReturnType<typeof setTimeout> | null = null
watch(triggerResult, (v) => {
  if (triggerResultTimer) { clearTimeout(triggerResultTimer); triggerResultTimer = null }
  if (v) triggerResultTimer = setTimeout(() => { triggerResult.value = '' }, 5000)
})
watch(triageOut, (v) => {
  if (triageOutTimer) { clearTimeout(triageOutTimer); triageOutTimer = null }
  if (v) triageOutTimer = setTimeout(() => { triageOut.value = '' }, 5000)
})
onBeforeUnmount(() => {
  if (triggerResultTimer) clearTimeout(triggerResultTimer)
  if (triageOutTimer) clearTimeout(triageOutTimer)
})

onMounted(() => { fetchHealth(); fetchCost() })
</script>

<style scoped>
.ai-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }

/* ── Stat card icon ── */
.ai-model-val { font-size: .9rem; font-family: var(--font-mono, monospace); }

/* ── Sections (card containers with left accent bar) ── */
.ai-section {
  margin-bottom: var(--space-6);
  position: relative;
  background: var(--card, var(--white));
  border: .5px solid var(--line);
  border-left: 4px solid var(--primary);
  border-radius: 14px;
  padding: var(--space-5);
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.ai-section > .admin-section-title { margin-top: 0; }

/* ── Cache ring + row ── */
.ai-cache-row {
  display: flex; align-items: center; gap: var(--space-5);
}
.ai-ring-wrap { position: relative; width: 80px; height: 80px; flex-shrink: 0; }
.ai-ring { width: 80px; height: 80px; transform: rotate(-90deg); }
.ai-ring-fill { animation: ai-ring-in .8s var(--ease-standard) both; }
@keyframes ai-ring-in { from { stroke-dasharray: 0 201; } }
.ai-ring-center {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; pointer-events: none;
}
.ai-ring-val { font-size: .95rem; font-weight: 800; line-height: 1.2; }
.ai-ring-lbl { font-size: .58rem; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
.ai-metrics-col { display: flex; gap: var(--space-3); flex-wrap: wrap; }

/* ── Data quality progress bar ── */
.ai-dq-row {
  display: flex; align-items: center; gap: var(--space-5);
}
.ai-dq-bar-wrap { flex: 1; min-width: 200px; }
.ai-dq-bar-label {
  display: flex; justify-content: space-between; align-items: center;
  font-size: .78rem; font-weight: 500; color: var(--muted);
  margin-bottom: 6px;
}
.ai-dq-bar-pct { font-weight: 800; font-size: .9rem; }
.ai-dq-track {
  height: 10px; border-radius: 5px;
  background: rgba(142,142,147,.08); overflow: hidden;
}
.ai-dq-fill {
  height: 100%; border-radius: 5px;
  animation: ai-dq-grow .6s var(--ease-standard) both;
}
@keyframes ai-dq-grow { from { width: 0 !important; } }

/* ── Inline metrics row ── */
.ai-metrics {
  display: flex; gap: var(--space-4); flex-wrap: wrap;
}
.ai-metric {
  display: flex; flex-direction: column; gap: 2px;
  padding: var(--space-3) var(--space-4);
  background: var(--bg); border: .5px solid var(--line); border-radius: 10px;
  min-width: 100px;
  transition: transform .2s;
}
.ai-metric:hover { transform: translateY(-1px); }
.ai-metric-val { font-size: 1.2rem; font-weight: 800; line-height: 1.2; }
.ai-metric-val small { font-size: .7rem; font-weight: 500; opacity: .6; }
.ai-metric-lbl { font-size: .68rem; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }
.ai-rt-dot {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  margin-right: 6px; vertical-align: middle;
}
.ai-near-cap {
  border-color: var(--warning); background: rgba(var(--warning-rgb),.04);
  border-left-width: 4px; border-left-style: dashed;
  animation: ai-near-cap-pulse 2s var(--ease-in-out) infinite;
}
@keyframes ai-near-cap-pulse {
  0%, 100% { border-left-color: var(--warning); }
  50% { border-left-color: transparent; }
}

/* ── Subsystems grid ── */
.ai-subsys-grid {
  display: flex; flex-wrap: wrap; gap: var(--space-2);
}
.ai-subsys {
  display: inline-flex; align-items: center; gap: 6px;
  padding: var(--space-1) var(--space-3); border-radius: 100px;
  font-size: .75rem; font-weight: 500;
}
.ai-subsys-dot {
  width: 6px; height: 6px; border-radius: 50%;
}
.ai-subsys-on { background: rgba(var(--primary-rgb),.06); color: var(--secondary); }
.ai-subsys-on .ai-subsys-dot { background: var(--secondary); animation: ai-sub-pulse 2.5s var(--ease-in-out) infinite; }
.ai-subsys-off { background: rgba(var(--danger-rgb),.06); color: var(--error); }
.ai-subsys-off .ai-subsys-dot { background: var(--error); opacity: .5; }
@keyframes ai-sub-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }

/* ── Actions grid ── */
.ai-action-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--space-3);
}
.ai-action-btn {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-4) var(--space-3); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  cursor: pointer; font-size: .82rem; font-weight: 500; color: var(--ink);
  transition: transform .3s var(--ease-soft), box-shadow .3s, border-color .3s, background .3s;
}
.ai-action-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.06); border-color: var(--primary); }
.ai-action-btn:active:not(:disabled) { transform: scale(.97); }
.ai-action-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.ai-action-btn:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }
.ai-action-icon { font-size: 1.4rem; }

/* Primary actions — stronger visual weight */
.ai-action-primary {
  background: var(--primary); border-color: var(--primary);
  color: var(--on-primary); font-weight: 600;
}
.ai-action-primary:hover:not(:disabled) {
  transform: translateY(-3px); box-shadow: 0 6px 20px rgba(var(--primary-rgb),.28);
  border-color: var(--primary);
}
/* Secondary action — outline style */
.ai-action-secondary { background: var(--bg); }

/* Inline action spinner */
.ai-action-spinner {
  width: 16px; height: 16px;
  border: 2px solid currentColor; border-top-color: transparent;
  border-radius: 50%;
  animation: admin-spin .6s linear infinite;
  opacity: .7;
}

/* ── Results ── */
.ai-trigger-result {
  margin-top: var(--space-3); padding: var(--space-3) var(--space-4);
  border-radius: 10px; font-size: .85rem;
  background: rgba(var(--primary-rgb),.06); border: .5px solid rgba(var(--primary-rgb),.15);
  color: var(--secondary);
}
.ai-trigger-result.ai-result-error {
  background: rgba(var(--danger-rgb),.08); border-color: var(--error); color: var(--error);
}
.ai-triage-box {
  display: flex; align-items: flex-start; gap: var(--space-2);
  margin-top: var(--space-3); padding: var(--space-4);
  border: .5px solid rgba(var(--primary-rgb),.2); border-left: 3px solid var(--secondary); border-radius: 12px;
  font-size: .85rem; line-height: 1.6;
  background: rgba(var(--primary-rgb),.05);
}
.ai-triage-box .ai-triage-text { white-space: pre-wrap; flex: 1; min-width: 0; }
.ai-triage-icon { font-weight: 800; color: var(--secondary); flex-shrink: 0; line-height: 1.6; }
.ai-triage-box.ai-triage-error {
  background: rgba(var(--danger-rgb),.08); border-color: var(--error); border-left-color: var(--error);
}
.ai-triage-box.ai-triage-error .ai-triage-icon { color: var(--error); }

/* ── Cost note callout ── */
.ai-cost-note {
  display: flex; align-items: flex-start; gap: var(--space-2);
  font-size: .78rem; color: var(--muted); margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4); border-radius: 10px;
  background: rgba(var(--warning-rgb),.04); border: 1px solid rgba(var(--warning-rgb),.2);
}
.ai-cost-note-icon { color: var(--warning); flex-shrink: 0; font-weight: 700; line-height: 1.4; }
.ai-cost-note strong { color: var(--ink); }

/* ── Dark mode ── */
.dark .ai-section { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); border-left-color: var(--primary); box-shadow: 0 1px 3px rgba(0,0,0,.3); }
.dark .ai-dq-track { background: rgba(255,255,255,.06); }
.dark .ai-metric { background: var(--bg, #1c1c1e); border-color: rgba(255,255,255,.08); }
.dark .ai-subsys-on { background: rgba(var(--primary-rgb),.1); }
.dark .ai-subsys-off { background: rgba(var(--danger-rgb),.1); }
.dark .ai-action-secondary { background: var(--bg, #1c1c1e); border-color: rgba(255,255,255,.08); color: var(--ink); }
.dark .ai-action-btn:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(0,0,0,.3); }
.dark .ai-action-primary { color: var(--ink); }
.dark .ai-triage-box { background: rgba(var(--primary-rgb),.1); border-color: rgba(var(--primary-rgb),.3); }
.dark .ai-triage-box.ai-triage-error { background: rgba(var(--danger-rgb),.12); border-color: var(--error); border-left-color: var(--error); }
.dark .ai-trigger-result { background: rgba(var(--primary-rgb),.1); border-color: rgba(var(--primary-rgb),.2); }
.dark .ai-trigger-result.ai-result-error { background: rgba(var(--danger-rgb),.12); border-color: var(--error); }
.dark .ai-cost-note { background: rgba(var(--warning-rgb),.06); border-color: rgba(var(--warning-rgb),.25); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .stat-card:hover .stat-icon { transform: none; }
  .ai-subsys-on .ai-subsys-dot { animation: none; }
  .ai-ring-fill { animation: none; }
  .ai-dq-fill { animation: none; }
  .ai-action-btn:hover:not(:disabled) { transform: none; }
  .ai-action-btn:active:not(:disabled) { transform: none; }
  .ai-action-primary:hover:not(:disabled) { transform: none; }
  .ai-metric:hover { transform: none; }
  .ai-near-cap { animation: none; border-left-color: var(--warning); }
}

@media (max-width: 768px) {
  .ai-metrics { gap: var(--space-2); }
  .ai-metric { min-width: 80px; padding: var(--space-2) var(--space-3); }
  .ai-metric-val { font-size: 1rem; }
  .ai-action-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
