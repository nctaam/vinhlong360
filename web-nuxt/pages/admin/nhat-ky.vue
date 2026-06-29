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
      <select v-model="methodFilter" class="input audit-select" @change="applyFilterImmediate">
        <option value="">Tất cả method</option>
        <option value="POST">POST</option>
        <option value="PUT">PUT</option>
        <option value="PATCH">PATCH</option>
        <option value="DELETE">DELETE</option>
      </select>
      <input v-model="dateFrom" type="date" class="input audit-date" aria-label="Từ ngày" @change="applyFilterImmediate" />
      <input v-model="dateTo" type="date" class="input audit-date" aria-label="Đến ngày" @change="applyFilterImmediate" />
      <button type="button" class="btn btn-outline btn-sm" :disabled="!filtered.length" @click="exportCSV">CSV</button>
    </div>

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải nhật ký"><div class="spinner"></div></div>
    <template v-else>
      <div class="audit-summary">{{ filtered.length }} mục{{ total > entries.length ? ` (hiển thị ${entries.length}/${total})` : '' }}</div>

      <div class="admin-table-wrap">
        <table class="admin-table" aria-label="Nhật ký hoạt động">
          <thead>
            <tr>
              <th scope="col">Thời gian</th>
              <th scope="col">Method</th>
              <th scope="col">Path</th>
              <th scope="col">Actor</th>
              <th scope="col">IP</th>
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
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Nhật ký — Admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const entries = ref<any[]>([])
const total = ref(0)
const loading = ref(true)
const search = ref('')
const methodFilter = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const page = ref(1)
const PAGE_SIZE = 50

let searchTimer: ReturnType<typeof setTimeout> | null = null

async function fetchLog() {
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: '5000' })
    if (methodFilter.value) params.set('method', methodFilter.value)
    if (search.value.trim()) params.set('q', search.value.trim())
    if (dateFrom.value) params.set('date_from', dateFrom.value)
    if (dateTo.value) params.set('date_to', dateTo.value)
    const res = await $fetch<{ entries: any[]; total: number }>(`/admin-api/audit-log?${params}`, { headers: authHeaders() })
    entries.value = res.entries || []
    total.value = res.total || 0
  } catch { showToast('Không thể tải nhật ký', 'error') }
  loading.value = false
}

const filtered = computed(() => entries.value)

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE_SIZE)))
const paginated = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE
  return filtered.value.slice(start, start + PAGE_SIZE)
})

function applyFilter() {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchLog(), 300)
}
function applyFilterImmediate() {
  page.value = 1
  fetchLog()
}

function exportCSV() {
  const rows = filtered.value
  if (!rows.length) return
  const csvCell = (v: string) => /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v
  const header = 'Thời gian,Method,Path,Actor,IP'
  const lines = rows.map(e => [e.ts, e.method, e.path, e.actor, e.ip].map(v => csvCell(String(v || ''))).join(','))
  const blob = new Blob(['﻿' + header + '\n' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

function formatTs(ts: string): string {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(fetchLog)
onUnmounted(() => { if (searchTimer) clearTimeout(searchTimer) })
</script>

<style scoped>
.audit-subtitle { color: var(--muted); font-size: var(--text-sm); }
.audit-filters { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); flex-wrap: wrap; }
.audit-filters .input { max-width: 300px; }
.audit-select { max-width: 160px; }
.audit-date { max-width: 160px; }
.audit-summary { font-size: var(--text-sm); color: var(--muted); margin-bottom: var(--space-2); }
.audit-method { font-weight: 700; font-size: .7rem; padding: 1px 6px; border-radius: var(--radius-sm); text-transform: uppercase; }
.audit-method.post { background: rgba(52,199,89,.15); color: var(--success); }
.audit-method.put, .audit-method.patch { background: rgba(var(--warning-rgb),.15); color: var(--warning); }
.audit-method.delete { background: rgba(255,69,58,.15); color: var(--error); }
.audit-ts { white-space: nowrap; font-size: .8rem; }
.audit-path { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.audit-actor { font-weight: 500; }
.audit-ip { font-size: .8rem; }

.dark .audit-method.post { background: rgba(52,199,89,.2); }
.dark .audit-method.put, .dark .audit-method.patch { background: rgba(var(--warning-rgb),.2); }
.dark .audit-method.delete { background: rgba(255,69,58,.2); }

@media (max-width: 600px) {
  .audit-filters { flex-direction: column; }
  .audit-filters .input, .audit-select { max-width: 100%; }
  .audit-path { max-width: 160px; }
}
</style>
