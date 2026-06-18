<template>
  <div>
    <div class="admin-head-row">
      <h1>🤖 Knowledge Agent</h1>
      <button class="admin-refresh" :disabled="refreshing" @click="refreshAll">🔄 Làm mới</button>
    </div>

    <div v-if="!health" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
    <!-- Health Status -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value" :style="{ color: statusColor }">{{ health?.status || '—' }}</div>
        <div class="stat-label">Trạng thái</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ health?.version || '—' }}</div>
        <div class="stat-label">Phiên bản</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ health?.llm_api || '—' }}</div>
        <div class="stat-label">LLM API</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ health?.memory_mb || '—' }} MB</div>
        <div class="stat-label">Bộ nhớ</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ health?.entities || '—' }}</div>
        <div class="stat-label">Entities (KB)</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ uptime }}</div>
        <div class="stat-label">Uptime</div>
      </div>
    </div>

    <!-- Model Info -->
    <div v-if="health?.model" class="admin-section-block">
      <h2 class="admin-section-title">Model</h2>
      <div class="stat-card" style="display: inline-block">
        <code>{{ health.model }}</code>
      </div>
    </div>

    <!-- Data Quality -->
    <div v-if="health?.data_quality" class="admin-section-block">
      <h2 class="admin-section-title">Chất lượng dữ liệu</h2>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">{{ health.data_quality.coverage_pct }}%</div>
          <div class="stat-label">Coverage</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ health.data_quality.missing_summary }}</div>
          <div class="stat-label">Thiếu summary</div>
        </div>
      </div>
    </div>

    <!-- Cache Stats -->
    <div v-if="health?.cache" class="admin-section-block">
      <h2 class="admin-section-title">Cache</h2>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">{{ health.cache.size || 0 }}</div>
          <div class="stat-label">Entries</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ health.cache.hits || 0 }}</div>
          <div class="stat-label">Hits</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ health.cache.misses || 0 }}</div>
          <div class="stat-label">Misses</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ hitRate }}%</div>
          <div class="stat-label">Hit Rate</div>
        </div>
      </div>
    </div>

    <!-- Subsystems -->
    <div class="admin-section-block">
      <h2 class="admin-section-title">Subsystems</h2>
      <div class="stat-grid">
        <div v-for="(val, key) in subsystems" :key="key" class="stat-card">
          <div class="stat-value admin-sub-value" :class="val ? 'status-active' : 'status-banned'">
            {{ val ? '✓' : '✗' }}
          </div>
          <div class="stat-label">{{ key }}</div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="admin-section-block">
      <h2 class="admin-section-title">Hành động</h2>
      <div class="admin-btn-group">
        <button class="btn btn-primary" :disabled="triggerLoading" @click="triggerLearn">
          {{ triggerLoading ? 'Đang chạy…' : '🧠 Trigger Learn' }}
        </button>
        <button class="btn btn-accent" @click="reload">🔄 Reload KB</button>
        <button class="btn btn-secondary" @click="fetchHealth">📊 Refresh</button>
        <button class="btn btn-outline" :disabled="triageLoading" @click="triage">
          {{ triageLoading ? 'Đang phân tích…' : '🤖 Gợi ý ưu tiên xử lý' }}
        </button>
      </div>
      <p v-if="triggerResult" class="admin-trigger-result">{{ triggerResult }}</p>
      <div v-if="triageOut" class="admin-triage-box">{{ triageOut }}</div>
    </div>

    <!-- Chi phí & ngân sách -->
    <div class="admin-section-block">
      <h2 class="admin-section-title">💰 Chi phí & ngân sách</h2>
      <div class="stat-grid" v-if="cost">
        <div class="stat-card">
          <div class="stat-value">{{ cost.llm?.available ? '$' + (cost.llm.total_cost_usd || 0).toFixed(4) : '—' }}</div>
          <div class="stat-label">LLM tích lũy</div>
        </div>
        <div class="stat-card" :class="{ 'near-cap': agentNearCap }">
          <div class="stat-value">{{ cost.agent_budget?.enabled ? `${cost.agent_budget.used_today}/${cost.agent_budget.cap_per_day}` : 'TẮT' }}</div>
          <div class="stat-label">Agent LLM hôm nay {{ agentNearCap ? '⚠️' : '' }}</div>
        </div>
      </div>
      <p class="admin-muted admin-cost-note">
        Agent tự động: {{ cost?.agent_budget?.enabled ? 'BẬT' : 'TẮT (mặc định)' }} —
        đổi qua .env AUTONOMOUS_AGENT_ENABLED + AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY.
      </p>
    </div>

    <!-- Response Times -->
    <div v-if="health?.response_times" class="admin-section-block">
      <h2 class="admin-section-title">Response Times</h2>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">{{ health.response_times.avg_ms || 0 }}ms</div>
          <div class="stat-label">Trung bình</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ health.response_times.p95_ms || 0 }}ms</div>
          <div class="stat-label">P95</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ health.response_times.total || 0 }}</div>
          <div class="stat-label">Tổng requests</div>
        </div>
      </div>
    </div>

    <!-- Errors -->
    <div v-if="health?.errors" class="admin-section-block">
      <h2 class="admin-section-title">Errors</h2>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value" :class="(health.errors.total || 0) > 0 ? 'status-banned' : 'status-active'">
            {{ health.errors.total || 0 }}
          </div>
          <div class="stat-label">Tổng lỗi</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ health.errors.recent || 0 }}</div>
          <div class="stat-label">Gần đây (1h)</div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
const refreshing = ref(false)
async function refreshAll() {
  refreshing.value = true
  await Promise.all([fetchHealth(), fetchCost()])
  refreshing.value = false
}

const { authHeaders } = useAuth()
const health = ref<any>(null)
const triggerLoading = ref(false)
const triggerResult = ref('')

const statusColor = computed(() => {
  if (!health.value) return 'var(--muted)'
  if (health.value.status === 'ok') return 'var(--primary)'
  if (health.value.status === 'degraded') return 'var(--warning, #e67e22)'
  return 'var(--error, #D94F3D)'
})

const uptime = computed(() => {
  const s = health.value?.uptime_seconds || 0
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`
})

const hitRate = computed(() => {
  const c = health.value?.cache
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
    if (health.value[k]) result[k.replace(/_/g, ' ')] = health.value[k].available !== false
  }
  return result
})

async function fetchHealth() {
  try { health.value = await $fetch<any>('/health') } catch { showToast('Không kết nối được agent', 'error') }
}

async function triggerLearn() {
  triggerLoading.value = true
  triggerResult.value = ''
  try {
    const res = await $fetch<any>('/admin-api/trigger-learn', { method: 'POST', headers: authHeaders() })
    triggerResult.value = res.message || 'Learning triggered successfully'
  } catch (e: any) {
    triggerResult.value = 'Error: ' + (e.data?.detail || e.message || 'failed')
  }
  triggerLoading.value = false
}

const cost = ref<any>(null)
const agentNearCap = computed(() => {
  const b = cost.value?.agent_budget
  return b?.enabled && b.remaining_today <= Math.max(1, Math.floor(b.cap_per_day / 5))
})
async function fetchCost() {
  try { cost.value = await $fetch<any>('/admin-api/cost-overview', { headers: authHeaders() }) } catch { showToast('Không tải được chi phí', 'error') }
}

const triageLoading = ref(false)
const triageOut = ref('')
async function triage() {
  triageLoading.value = true
  triageOut.value = ''
  try {
    const r = await $fetch<any>('/admin-api/ai/triage', { method: 'POST', headers: authHeaders() })
    triageOut.value = r.ok
      ? `🤖 ${r.suggestion}`
      : `${r.note || 'LLM lỗi'}\n\n${r.context || ''}`
  } catch (e: any) {
    triageOut.value = 'Lỗi: ' + (e?.data?.detail || e?.message || 'không gọi được')
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
.near-cap { border-color: var(--warning, #e67e22); }
</style>
