<template>
  <div>
    <h1>🤖 Knowledge Agent</h1>

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
    <div v-if="health?.model" style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Model</h2>
      <div class="stat-card" style="display: inline-block">
        <code style="font-size: .9rem">{{ health.model }}</code>
      </div>
    </div>

    <!-- Data Quality -->
    <div v-if="health?.data_quality" style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Chất lượng dữ liệu</h2>
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
    <div v-if="health?.cache" style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Cache</h2>
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
    <div style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Subsystems</h2>
      <div class="stat-grid">
        <div v-for="(val, key) in subsystems" :key="key" class="stat-card">
          <div class="stat-value" style="font-size: 1rem" :style="{ color: val ? 'var(--primary)' : '#D94F3D' }">
            {{ val ? '✓' : '✗' }}
          </div>
          <div class="stat-label">{{ key }}</div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Hành động</h2>
      <div style="display: flex; gap: 12px; flex-wrap: wrap">
        <button class="btn btn-primary" :disabled="triggerLoading" @click="triggerLearn">
          {{ triggerLoading ? 'Đang chạy…' : '🧠 Trigger Learn' }}
        </button>
        <button class="btn btn-accent" @click="reload">🔄 Reload KB</button>
        <button class="btn btn-secondary" @click="fetchHealth">📊 Refresh</button>
      </div>
      <p v-if="triggerResult" style="margin-top: 10px; font-size: .88rem; color: var(--muted)">{{ triggerResult }}</p>
    </div>

    <!-- Response Times -->
    <div v-if="health?.response_times" style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Response Times</h2>
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
    <div v-if="health?.errors" style="margin-bottom: 24px">
      <h2 style="font-size: 1.1rem; margin-bottom: 10px">Errors</h2>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value" :style="{ color: (health.errors.total || 0) > 0 ? '#D94F3D' : 'var(--primary)' }">
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
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const health = ref<any>(null)
const triggerLoading = ref(false)
const triggerResult = ref('')

const statusColor = computed(() => {
  if (!health.value) return 'var(--muted)'
  if (health.value.status === 'ok') return 'var(--primary)'
  if (health.value.status === 'degraded') return '#e67e22'
  return '#D94F3D'
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
  try { health.value = await $fetch<any>('/health') } catch { /* ignore */ }
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

async function reload() {
  try {
    await $fetch('/reload', { method: 'POST' })
    triggerResult.value = 'KB reloaded'
    await fetchHealth()
  } catch { triggerResult.value = 'Reload failed' }
}

onMounted(() => fetchHealth())
</script>
