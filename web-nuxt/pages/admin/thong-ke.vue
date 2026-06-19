<template>
  <div>
    <div class="admin-head-row">
      <h1>Thống kê & Phân tích</h1>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchData">🔄 Làm mới</button>
    </div>
    <p class="admin-muted">User hỏi gì · bot bí ở đâu (backlog nội dung) · chi phí LLM.</p>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <!-- Summary -->
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-num">{{ data.summary?.total_queries ?? '—' }}</div><div class="stat-lbl">Tổng truy vấn</div></div>
        <div class="stat-card"><div class="stat-num">{{ data.summary?.unique_queries ?? '—' }}</div><div class="stat-lbl">Truy vấn khác nhau</div></div>
        <div class="stat-card"><div class="stat-num">{{ (data.gaps || []).length }}</div><div class="stat-lbl">Knowledge gaps</div></div>
        <div class="stat-card"><div class="stat-num">{{ costTotal }}</div><div class="stat-lbl">Chi phí (ước)</div></div>
      </div>

      <div class="cols">
        <section class="panel">
          <h2>🔥 Câu hỏi phổ biến</h2>
          <ol v-if="(data.popular || []).length" class="rows">
            <li v-for="(it, i) in data.popular" :key="i"><span>{{ label(it) }}</span><b>{{ count(it) }}</b></li>
          </ol>
          <p v-else class="admin-muted">Chưa có dữ liệu.</p>
        </section>

        <section class="panel">
          <h2>🕳️ Bot bí (cần bổ sung KB)</h2>
          <ol v-if="(data.gaps || []).length" class="rows">
            <li v-for="(it, i) in data.gaps" :key="i"><span>{{ label(it) }}</span><b>{{ count(it) }}</b></li>
          </ol>
          <p v-else class="admin-muted">Không có gap — tốt!</p>
        </section>

        <section class="panel">
          <h2>📍 Entity được xem nhiều</h2>
          <ol v-if="(data.top_entities || []).length" class="rows">
            <li v-for="(it, i) in data.top_entities" :key="i"><span>{{ it.name || it.id || label(it) }}</span><b>{{ count(it) }}</b></li>
          </ol>
          <p v-else class="admin-muted">Chưa có dữ liệu.</p>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const data = ref<any>({})
const loading = ref(true)

function label(it: any) { return it?.query ?? it?.q ?? it?.name ?? String(it) }
function count(it: any) { return it?.count ?? it?.hits ?? it?.n ?? '' }

const costTotal = computed(() => {
  const c = data.value?.costs || {}
  if (c.available === false) return '—'
  const v = c.total_cost ?? c.total ?? c.monthly?.spent ?? c.daily?.spent
  return v != null ? (typeof v === 'number' ? v.toLocaleString('vi-VN') : v) : '—'
})

async function fetchData() {
  loading.value = true
  try {
    data.value = await $fetch<any>('/admin-api/analytics-overview', { headers: authHeaders() })
  } catch (e: any) {
    showToast(e.data?.detail || 'Không thể tải thống kê', 'error')
  }
  loading.value = false
}

onMounted(fetchData)
</script>

<style scoped>
.stat-num { font-size: var(--text-xl); font-weight: var(--weight-bold); }
.stat-lbl { font-size: var(--text-xs); color: var(--muted); margin-top: var(--space-1); }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-4); }
.panel { background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sm); padding: var(--space-4); box-shadow: var(--shadow-xs); }
.panel h2 { font-size: var(--text-base); margin-bottom: var(--space-3); }
.rows { list-style: none; padding: 0; margin: 0; }
.rows li { display: flex; justify-content: space-between; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: .5px solid var(--line); font-size: var(--text-sm); }
.rows li span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rows li b { color: var(--primary); }

.panel { transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); }
.panel:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }

</style>
