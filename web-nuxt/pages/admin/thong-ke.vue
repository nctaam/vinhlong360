<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Thống kê & Phân tích</h1>
        <p class="tk-subtitle">User hỏi gì, bot bí ở đâu, chi phí LLM</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchData">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>

    <!-- Summary cards -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="tk-icon" style="background: rgba(52,120,246,.1); color: #3478F6;">&#128172;</div>
        <div>
          <div class="stat-value">{{ data.summary?.total_queries ?? '—' }}</div>
          <div class="stat-label">Tổng truy vấn</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="tk-icon" style="background: rgba(175,82,222,.1); color: #AF52DE;">&#128161;</div>
        <div>
          <div class="stat-value">{{ data.summary?.unique_queries ?? '—' }}</div>
          <div class="stat-label">Truy vấn khác nhau</div>
        </div>
      </div>
      <div class="stat-card" :class="{ 'status-warn': (data.gaps || []).length > 5 }">
        <div class="tk-icon" style="background: rgba(255,159,10,.1); color: #FF9F0A;">&#128371;</div>
        <div>
          <div class="stat-value">{{ (data.gaps || []).length }}</div>
          <div class="stat-label">Knowledge gaps</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="tk-icon" style="background: rgba(33,150,83,.1); color: #219653;">&#128176;</div>
        <div>
          <div class="stat-value">{{ costTotal }}</div>
          <div class="stat-label">Chi phí (ước)</div>
        </div>
      </div>
    </div>

    <!-- Three-column panels -->
    <div class="tk-panels">
      <section class="tk-panel">
        <div class="tk-panel-head">
          <h2>Câu hỏi phổ biến</h2>
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
          <h2>Bot bí (cần bổ sung KB)</h2>
          <span class="tk-count-badge tk-count-warn" v-if="(data.gaps || []).length">{{ (data.gaps || []).length }}</span>
        </div>
        <ol v-if="(data.gaps || []).length" class="tk-list">
          <li v-for="(it, i) in data.gaps" :key="i">
            <div class="tk-bar-bg tk-bar-warn" :style="{ width: barPct(it, data.gaps) + '%' }"></div>
            <span class="tk-rank">{{ i + 1 }}</span>
            <span class="tk-query">{{ label(it) }}</span>
            <span class="tk-hits">{{ count(it) }}</span>
          </li>
        </ol>
        <div v-else class="tk-empty tk-empty-ok">
          <span class="tk-empty-icon">&#9989;</span>
          <span>Không có gap — tốt!</span>
        </div>
      </section>

      <section class="tk-panel">
        <div class="tk-panel-head">
          <h2>Entity được xem nhiều</h2>
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

    </template>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const data = ref<Record<string, unknown>>({})
const loading = ref(true)

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

async function fetchData() {
  loading.value = true
  try {
    data.value = await $fetch<Record<string, unknown>>('/admin-api/analytics-overview', { headers: authHeaders() })
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Không thể tải thống kê', 'error')
  }
  loading.value = false
}

onMounted(fetchData)
</script>

<style scoped>
.tk-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Stat card icon ── */
.stat-card { display: flex; align-items: center; gap: var(--space-4); }
.tk-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; flex-shrink: 0;
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
.tk-panel:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,.06); border-color: rgba(52,120,246,.15); }

.tk-panel-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-4);
}
.tk-panel-head h2 { font-size: .95rem; font-weight: 600; margin: 0; }

.tk-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 8px;
  border-radius: 100px; font-size: .72rem; font-weight: 700;
  background: rgba(52,120,246,.1); color: #3478F6;
}
.tk-count-warn { background: rgba(255,159,10,.1); color: #c67a00; }

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
  width: 20px; height: 20px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: .68rem; font-weight: 700; flex-shrink: 0;
  background: var(--bg-alt); color: var(--muted);
}
.tk-list li:nth-child(-n+3) .tk-rank { background: rgba(33,150,83,.1); color: #219653; }
.tk-query { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tk-hits { font-weight: 700; color: var(--primary, #219653); font-size: .82rem; flex-shrink: 0; position: relative; }

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
.dark .tk-panel { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .tk-panel:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); border-color: rgba(52,120,246,.25); }
.dark .tk-list li:hover { background: rgba(255,255,255,.03); }
.dark .tk-rank { background: rgba(255,255,255,.06); }
.dark .tk-list li:nth-child(-n+3) .tk-rank { background: rgba(33,150,83,.15); }
.dark .tk-count-badge { background: rgba(52,120,246,.15); }
.dark .tk-count-warn { background: rgba(255,159,10,.15); color: #ffb340; }

@media (max-width: 768px) {
  .tk-panels { grid-template-columns: 1fr; }
}
</style>
