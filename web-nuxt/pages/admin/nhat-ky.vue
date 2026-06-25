<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Nhật ký admin</h1>
        <p class="audit-subtitle">Lịch sử thao tác quản trị (mutation)</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchLog">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div class="audit-filters">
      <input v-model="search" class="input" placeholder="Tìm theo path hoặc actor..." aria-label="Tìm nhật ký" @input="applyFilter" />
      <select v-model="methodFilter" class="input audit-select" @change="applyFilter">
        <option value="">Tất cả method</option>
        <option value="POST">POST</option>
        <option value="PUT">PUT</option>
        <option value="PATCH">PATCH</option>
        <option value="DELETE">DELETE</option>
      </select>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="audit-summary">{{ filtered.length }} mục{{ total > entries.length ? ` (hiển thị ${entries.length}/${total})` : '' }}</div>

      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Method</th>
              <th>Path</th>
              <th>Actor</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in paginated" :key="i" class="audit-row">
              <td class="audit-ts"><time :datetime="e.ts">{{ formatTs(e.ts) }}</time></td>
              <td><span :class="['audit-method', (e.method || '').toLowerCase()]">{{ e.method }}</span></td>
              <td class="audit-path">{{ e.path }}</td>
              <td class="audit-actor">{{ e.actor || '—' }}</td>
              <td class="audit-ip admin-td-muted">{{ e.ip || '—' }}</td>
            </tr>
            <tr v-if="!paginated.length">
              <td colspan="5" class="admin-empty-row">Không có mục nào.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <nav v-if="totalPages > 1" class="admin-pagination" role="navigation" aria-label="Phân trang">
        <button type="button" :disabled="page <= 1" @click="page--">&larr; Trước</button>
        <span class="admin-page-info">Trang {{ page }}/{{ totalPages }}</span>
        <button type="button" :disabled="page >= totalPages" @click="page++">Sau &rarr;</button>
      </nav>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin' })

const { authHeaders } = useAuth()
const { showToast } = useToast()

const entries = ref<any[]>([])
const total = ref(0)
const loading = ref(true)
const search = ref('')
const methodFilter = ref('')
const page = ref(1)
const PAGE_SIZE = 50

async function fetchLog() {
  loading.value = true
  try {
    const res = await $fetch<{ entries: any[]; total: number }>('/admin-api/audit-log?limit=1000', { headers: authHeaders() })
    entries.value = res.entries || []
    total.value = res.total || 0
  } catch { showToast('Không thể tải nhật ký', 'error') }
  loading.value = false
}

const filtered = computed(() => {
  let list = entries.value
  if (methodFilter.value) list = list.filter(e => e.method === methodFilter.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(e => (e.path || '').toLowerCase().includes(q) || (e.actor || '').toLowerCase().includes(q))
  }
  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE_SIZE)))
const paginated = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return filtered.value.slice(start, start + PAGE_SIZE)
})

function applyFilter() { page.value = 1 }

function formatTs(ts: string): string {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(fetchLog)
</script>

<style scoped>
.audit-subtitle { color: var(--muted); font-size: var(--text-sm); }
.audit-filters { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); flex-wrap: wrap; }
.audit-filters .input { max-width: 300px; }
.audit-select { max-width: 160px; }
.audit-summary { font-size: var(--text-sm); color: var(--muted); margin-bottom: var(--space-2); }
.audit-method { font-weight: 700; font-size: .7rem; padding: 1px 6px; border-radius: var(--radius-sm); text-transform: uppercase; }
.audit-method.post { background: rgba(52,199,89,.15); color: #219653; }
.audit-method.put, .audit-method.patch { background: rgba(255,159,10,.15); color: #FF9F0A; }
.audit-method.delete { background: rgba(255,69,58,.15); color: #FF453A; }
.audit-ts { white-space: nowrap; font-size: .8rem; }
.audit-path { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.audit-actor { font-weight: 500; }
.audit-ip { font-size: .8rem; }

.dark .audit-method.post { background: rgba(52,199,89,.2); color: #34c759; }
.dark .audit-method.put, .dark .audit-method.patch { background: rgba(255,159,10,.2); color: #ffb340; }
.dark .audit-method.delete { background: rgba(255,69,58,.2); color: #ff6961; }

@media (max-width: 600px) {
  .audit-filters { flex-direction: column; }
  .audit-filters .input, .audit-select { max-width: 100%; }
  .audit-path { max-width: 160px; }
}
</style>
