<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Knowledge Agent</h1>
        <p class="ai-subtitle">Giám sát LLM, cache, chi phí và subsystems</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="refreshing" @click="refreshAll"><span :class="{ 'refresh-spin': refreshing }">&#8635;</span> Làm mới</button>
    </div>

    <div v-if="!health" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>

    <!-- Health Status -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="ai-icon" :style="{ background: statusBg, color: statusColor }">&#9889;</div>
        <div>
          <div class="stat-value" :style="{ color: statusColor }">{{ health?.status || '—' }}</div>
          <div class="stat-label">Trạng thái</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="ai-icon" style="background: rgba(52,120,246,.1); color: #3478F6;">&#128640;</div>
        <div>
          <div class="stat-value">{{ health?.version || '—' }}</div>
          <div class="stat-label">Phiên bản</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="ai-icon" style="background: rgba(175,82,222,.1); color: #AF52DE;">&#129302;</div>
        <div>
          <div class="stat-value ai-model-val">{{ health?.model || health?.llm_api || '—' }}</div>
          <div class="stat-label">Model / API</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="ai-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#128338;</div>
        <div>
          <div class="stat-value">{{ uptime }}</div>
          <div class="stat-label">Uptime</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="ai-icon" style="background: rgba(33,150,83,.1); color: #219653;">&#127760;</div>
        <div>
          <div class="stat-value">{{ health?.entities || '—' }}</div>
          <div class="stat-label">Entities (KB)</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="ai-icon" style="background: rgba(0,199,190,.1); color: #00C7BE;">&#128190;</div>
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
          <svg class="ai-ring" viewBox="0 0 80 80">
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
            <span class="ai-ring-val" :style="{ color: hitRate >= 70 ? '#219653' : hitRate >= 40 ? '#e67e22' : '#D94F3D' }">{{ hitRate }}%</span>
            <span class="ai-ring-lbl">hit rate</span>
          </div>
        </div>
        <div class="ai-metrics ai-metrics-col">
          <div class="ai-metric">
            <span class="ai-metric-val">{{ health.cache.size || 0 }}</span>
            <span class="ai-metric-lbl">Entries</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-val" style="color: #219653">{{ health.cache.hits || 0 }}</span>
            <span class="ai-metric-lbl">Hits</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-val" style="color: #D94F3D">{{ health.cache.misses || 0 }}</span>
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
            <span class="ai-dq-bar-pct" :style="{ color: health.data_quality.coverage_pct >= 80 ? '#219653' : '#e67e22' }">{{ health.data_quality.coverage_pct }}%</span>
          </div>
          <div class="ai-dq-track">
            <div class="ai-dq-fill" :style="{ width: health.data_quality.coverage_pct + '%', background: health.data_quality.coverage_pct >= 80 ? '#219653' : '#e67e22' }"></div>
          </div>
        </div>
        <div class="ai-metric">
          <span class="ai-metric-val">{{ health.data_quality.missing_summary }}</span>
          <span class="ai-metric-lbl">Thiếu summary</span>
        </div>
      </div>
    </div>

    <!-- Response Times -->
    <div v-if="health?.response_times" class="ai-section">
      <h2 class="admin-section-title">Response Times</h2>
      <div class="ai-metrics">
        <div class="ai-metric">
          <span class="ai-metric-val">{{ health.response_times.avg_ms || 0 }}<small>ms</small></span>
          <span class="ai-metric-lbl">Trung bình</span>
        </div>
        <div class="ai-metric">
          <span class="ai-metric-val">{{ health.response_times.p95_ms || 0 }}<small>ms</small></span>
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
          <span class="ai-metric-val" :style="{ color: (health.errors.total || 0) > 0 ? '#D94F3D' : '#219653' }">{{ health.errors.total || 0 }}</span>
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
        <div v-for="(val, key) in subsystems" :key="key" class="ai-subsys" :class="val ? 'ai-subsys-on' : 'ai-subsys-off'">
          <span class="ai-subsys-dot"></span>
          <span>{{ key }}</span>
        </div>
      </div>
    </div>

    <!-- Cost & Budget -->
    <div class="ai-section">
      <h2 class="admin-section-title">Chi phí & ngân sách</h2>
      <div class="ai-metrics" v-if="cost">
        <div class="ai-metric">
          <span class="ai-metric-val">{{ cost.llm?.available ? '$' + (cost.llm.total_cost_usd || 0).toFixed(4) : '—' }}</span>
          <span class="ai-metric-lbl">LLM tích lũy</span>
        </div>
        <div class="ai-metric" :class="{ 'ai-near-cap': agentNearCap }">
          <span class="ai-metric-val">{{ cost.agent_budget?.enabled ? `${cost.agent_budget.used_today}/${cost.agent_budget.cap_per_day}` : 'TẮT' }}</span>
          <span class="ai-metric-lbl">Agent LLM hôm nay</span>
        </div>
      </div>
      <p class="ai-cost-note">
        Agent tự động: <strong>{{ cost?.agent_budget?.enabled ? 'BẬT' : 'TẮT (mặc định)' }}</strong> —
        đổi qua .env AUTONOMOUS_AGENT_ENABLED + AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY.
      </p>
    </div>

    <!-- Actions -->
    <div class="ai-section">
      <h2 class="admin-section-title">Hành động</h2>
      <div class="ai-action-grid">
        <button type="button" class="ai-action-btn" :disabled="triggerLoading" @click="triggerLearn">
          <span class="ai-action-icon">&#129504;</span>
          <span>{{ triggerLoading ? 'Đang chạy...' : 'Trigger Learn' }}</span>
        </button>
        <button type="button" class="ai-action-btn" @click="reload">
          <span class="ai-action-icon">&#128260;</span>
          <span>Reload KB</span>
        </button>
        <button type="button" class="ai-action-btn" :disabled="triageLoading" @click="triage">
          <span class="ai-action-icon">&#129302;</span>
          <span>{{ triageLoading ? 'Đang phân tích...' : 'Gợi ý ưu tiên' }}</span>
        </button>
      </div>
      <p v-if="triggerResult" class="ai-trigger-result">{{ triggerResult }}</p>
      <div v-if="triageOut" class="ai-triage-box">{{ triageOut }}</div>
    </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const refreshing = ref(false)
async function refreshAll() {
  refreshing.value = true
  await Promise.all([fetchHealth(), fetchCost()])
  refreshing.value = false
}

const health = ref<Record<string, unknown> | null>(null)
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
  if (health.value.status === 'ok') return 'rgba(33,150,83,.1)'
  if (health.value.status === 'degraded') return 'rgba(255,159,10,.1)'
  return 'rgba(217,79,61,.1)'
})

const uptime = computed(() => {
  const s = Number(health.value?.uptime_seconds) || 0
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`
})

const hitRate = computed(() => {
  const c = health.value?.cache as Record<string, number> | undefined
  if (!c) return 0
  const total = (c.hits || 0) + (c.misses || 0)
  return total ? Math.round((c.hits / total) * 100) : 0
})

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
  try { health.value = await $fetch<Record<string, unknown>>('/health') } catch { showToast('Không kết nối được agent', 'error') }
}

async function triggerLearn() {
  triggerLoading.value = true
  triggerResult.value = ''
  try {
    const res = await $fetch<Record<string, unknown>>('/admin-api/trigger-learn', { method: 'POST', headers: authHeaders() })
    triggerResult.value = (res.message as string) || 'Learning triggered successfully'
  } catch (e: unknown) {
    triggerResult.value = 'Error: ' + ((e as any)?.data?.detail || (e as any)?.message || 'failed')
  }
  triggerLoading.value = false
}

const cost = ref<Record<string, unknown> | null>(null)
const agentNearCap = computed(() => {
  const b = cost.value?.agent_budget as Record<string, number> | undefined
  return b?.enabled && b.remaining_today <= Math.max(1, Math.floor(b.cap_per_day / 5))
})
async function fetchCost() {
  try { cost.value = await $fetch<Record<string, unknown>>('/admin-api/cost-overview', { headers: authHeaders() }) } catch { showToast('Không tải được chi phí', 'error') }
}

const triageLoading = ref(false)
const triageOut = ref('')
async function triage() {
  triageLoading.value = true
  triageOut.value = ''
  try {
    const r = await $fetch<Record<string, unknown>>('/admin-api/ai/triage', { method: 'POST', headers: authHeaders() })
    triageOut.value = r.ok
      ? `${r.suggestion}`
      : `${r.note || 'LLM lỗi'}\n\n${r.context || ''}`
  } catch (e: unknown) {
    triageOut.value = 'Lỗi: ' + ((e as any)?.data?.detail || (e as any)?.message || 'không gọi được')
  }
  triageLoading.value = false
}

async function reload() {
  try {
    await $fetch('/reload', { method: 'POST', headers: authHeaders() })
    triggerResult.value = 'KB reloaded'
    await fetchHealth()
  } catch { triggerResult.value = 'Reload failed' }
}

onMounted(() => { fetchHealth(); fetchCost() })
</script>

<style scoped>
.ai-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }

/* ── Stat card icon ── */
.stat-card { display: flex; align-items: center; gap: var(--space-4); }
.ai-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.15rem; flex-shrink: 0;
  transition: transform .25s cubic-bezier(.2,1,.4,1);
}
.stat-card:hover .ai-icon { transform: scale(1.08); }
.ai-model-val { font-size: .9rem; font-family: var(--font-mono, monospace); }

/* ── Sections ── */
.ai-section { margin-bottom: var(--space-6); }

/* ── Cache ring + row ── */
.ai-cache-row {
  display: flex; align-items: center; gap: var(--space-5);
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-5);
}
.ai-ring-wrap { position: relative; width: 80px; height: 80px; flex-shrink: 0; }
.ai-ring { width: 80px; height: 80px; transform: rotate(-90deg); }
.ai-ring-fill { animation: ai-ring-in .8s cubic-bezier(.4,0,.2,1) both; }
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
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
  padding: var(--space-5);
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
  animation: ai-dq-grow .6s cubic-bezier(.4,0,.2,1) both;
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
.ai-near-cap { border-color: var(--warning, #e67e22); background: rgba(255,159,10,.04); }

/* ── Subsystems grid ── */
.ai-subsys-grid {
  display: flex; flex-wrap: wrap; gap: var(--space-2);
}
.ai-subsys {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 100px;
  font-size: .75rem; font-weight: 500;
}
.ai-subsys-dot {
  width: 6px; height: 6px; border-radius: 50%;
}
.ai-subsys-on { background: rgba(33,150,83,.06); color: #219653; }
.ai-subsys-on .ai-subsys-dot { background: #219653; animation: ai-sub-pulse 2.5s ease-in-out infinite; }
.ai-subsys-off { background: rgba(217,79,61,.06); color: #D94F3D; }
.ai-subsys-off .ai-subsys-dot { background: #D94F3D; opacity: .5; }
@keyframes ai-sub-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }

/* ── Actions grid ── */
.ai-action-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--space-3);
}
.ai-action-btn {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-4) var(--space-3); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  cursor: pointer; font-size: .82rem; font-weight: 500; color: var(--ink);
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.ai-action-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.06); border-color: var(--primary); }
.ai-action-btn:active:not(:disabled) { transform: scale(.97); }
.ai-action-btn:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.ai-action-btn:disabled { opacity: .4; cursor: not-allowed; }
.ai-action-icon { font-size: 1.4rem; }

/* ── Results ── */
.ai-trigger-result {
  margin-top: var(--space-3); padding: var(--space-3) var(--space-4);
  border-radius: 10px; font-size: .85rem;
  background: rgba(33,150,83,.06); border: .5px solid rgba(33,150,83,.15);
  color: #219653;
}
.ai-triage-box {
  margin-top: var(--space-3); padding: var(--space-4);
  border: .5px solid var(--line); border-radius: 12px;
  white-space: pre-wrap; font-size: .85rem; line-height: 1.6;
  background: var(--bg);
}

/* ── Cost note ── */
.ai-cost-note { font-size: .78rem; color: var(--muted); margin-top: var(--space-2); }

/* ── Dark mode ── */
.dark .ai-cache-row { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .ai-dq-row { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .ai-dq-track { background: rgba(255,255,255,.06); }
.dark .ai-metric { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .ai-subsys-on { background: rgba(33,150,83,.1); }
.dark .ai-subsys-off { background: rgba(217,79,61,.1); }
.dark .ai-action-btn { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); color: var(--ink); }
.dark .ai-action-btn:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(0,0,0,.3); }
.dark .ai-triage-box { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .ai-trigger-result { background: rgba(33,150,83,.1); border-color: rgba(33,150,83,.2); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .stat-card:hover .ai-icon { transform: none; }
  .ai-subsys-on .ai-subsys-dot { animation: none; }
  .ai-ring-fill { animation: none; }
  .ai-dq-fill { animation: none; }
  .ai-action-btn:hover:not(:disabled) { transform: none; }
  .ai-action-btn:active:not(:disabled) { transform: none; }
  .ai-metric:hover { transform: none; }
}

@media (max-width: 768px) {
  .ai-metrics { gap: var(--space-2); }
  .ai-metric { min-width: 80px; padding: var(--space-2) var(--space-3); }
  .ai-metric-val { font-size: 1rem; }
  .ai-action-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
