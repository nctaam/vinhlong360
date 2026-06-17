<template>
  <div>
    <div class="admin-head-row">
      <h1>Báo cáo</h1>
      <button class="admin-refresh" :disabled="loading" @click="fetchAll">🔄 Làm mới</button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Người báo</th>
              <th>Loại</th>
              <th>Đối tượng</th>
              <th>Lý do</th>
              <th>Trạng thái</th>
              <th>Ngày</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reports" :key="r.id">
              <td>{{ r.reporter_name || r.reporter_phone || '—' }}</td>
              <td>{{ r.target_type || r.ref_type || '—' }}</td>
              <td>
                <NuxtLink v-if="targetLink(r)" :to="targetLink(r)" target="_blank">{{ r.target_id || r.ref_id }}</NuxtLink>
                <span v-else>{{ r.target_id || r.ref_id || '—' }}</span>
              </td>
              <td class="admin-td-truncate">{{ r.reason }}</td>
              <td>
                <span :class="r.status === 'pending' ? 'status-pending' : r.status === 'resolved' ? 'status-resolved' : 'status-dismissed'">
                  {{ statusLabel(r.status) }}
                </span>
              </td>
              <td class="admin-td-muted">{{ formatDate(r.created_at) }}</td>
              <td v-if="r.status === 'pending'" class="admin-actions">
                <button class="btn-success" :disabled="acting === r.id" @click="resolve(r.id)">
                  {{ acting === r.id ? '…' : 'Xử lý' }}
                </button>
                <button class="btn-danger" :disabled="acting === r.id" @click="dismiss(r.id)">Bỏ qua</button>
              </td>
              <td v-else class="admin-td-muted">—</td>
            </tr>
            <tr v-if="!reports.length">
              <td colspan="7" class="admin-empty-row">Không có báo cáo nào.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 class="admin-section-title" style="margin-top:24px">⚠️ Báo sai thông tin (ẩn danh) <small class="admin-muted">— {{ infoOpen }} chưa xử lý</small></h2>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>Loại</th><th>Đối tượng</th><th>Lý do</th><th>Trạng thái</th><th>Ngày</th><th>Thao tác</th></tr></thead>
          <tbody>
            <tr v-for="r in infoReports" :key="r.ts" :style="{ opacity: (r.status || 'open') === 'open' ? 1 : .5 }">
              <td>{{ r.target_type }}</td>
              <td><NuxtLink v-if="infoLink(r)" :to="infoLink(r)" target="_blank">{{ r.target_id }}</NuxtLink><span v-else>{{ r.target_id }}</span></td>
              <td class="admin-td-truncate">{{ r.reason }}<br><small class="admin-muted">{{ r.detail }}</small></td>
              <td>{{ infoStatus(r.status) }}</td>
              <td class="admin-td-muted">{{ formatDate(r.ts) }}</td>
              <td class="admin-actions">
                <template v-if="(r.status || 'open') === 'open'">
                  <button class="btn-success" :disabled="infoActing === r.ts" @click="infoAction(r, 'resolved')">Xử lý</button>
                  <button class="btn-danger" :disabled="infoActing === r.ts" @click="infoAction(r, 'dismissed')">Bỏ qua</button>
                </template>
                <span v-else>—</span>
              </td>
            </tr>
            <tr v-if="!infoReports.length"><td colspan="6" class="admin-empty-row">Không có báo sai nào.</td></tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const reports = ref<any[]>([])
const infoReports = ref<any[]>([])
const infoOpen = ref(0)
const loading = ref(true)
const acting = ref<string | null>(null)
const infoActing = ref<string | null>(null)

async function fetchAll() {
  loading.value = true
  await Promise.all([fetchReports(), fetchInfoReports()])
  loading.value = false
}

async function fetchInfoReports() {
  try {
    const res = await $fetch<any>('/admin-api/info-reports?limit=200', { headers: authHeaders() })
    infoReports.value = res.reports || []
    infoOpen.value = res.open ?? 0
  } catch { /* ignore */ }
}

async function infoAction(r: any, status: string) {
  if (status === 'dismissed' && !confirm('Bỏ qua báo sai này?')) return
  infoActing.value = r.ts
  try {
    await $fetch('/admin-api/info-reports/action', { method: 'POST', headers: authHeaders(), body: { ts: r.ts, status } })
    r.status = status
    infoOpen.value = infoReports.value.filter(x => (x.status || 'open') === 'open').length
  } catch (e: any) { showToast(e?.data?.detail || 'Lỗi cập nhật', 'error') }
  infoActing.value = null
}

function infoStatus(s: string) {
  return s === 'resolved' ? 'Đã xử lý' : s === 'dismissed' ? 'Bỏ qua' : 'Chưa xử lý'
}
function infoLink(r: any) {
  const id = r.target_id
  if (!id) return ''
  if (r.target_type === 'post') return `/bai-viet/${id}`
  if (r.target_type === 'facility' || r.target_type === 'entity') return `/dia-diem/${id}`
  return ''
}

async function fetchReports() {
  try {
    const res = await $fetch<any>('/admin-api/reports', { headers: authHeaders() })
    reports.value = res.reports || res || []
  } catch {
    showToast('Không thể tải báo cáo', 'error')
  }
}

async function resolve(id: string) {
  if (!confirm('Xác nhận xử lý báo cáo này?')) return
  acting.value = id
  try {
    await $fetch(`/admin-api/reports/${id}/resolve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã xử lý báo cáo', 'success')
    await fetchReports()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi xử lý báo cáo', 'error')
  }
  acting.value = null
}

async function dismiss(id: string) {
  if (!confirm('Bỏ qua báo cáo này?')) return
  acting.value = id
  try {
    await $fetch(`/admin-api/reports/${id}/dismiss`, { method: 'POST', headers: authHeaders() })
    showToast('Đã bỏ qua báo cáo', 'success')
    await fetchReports()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi bỏ qua', 'error')
  }
  acting.value = null
}

function statusLabel(status: string) {
  if (status === 'pending') return 'Chờ xử lý'
  if (status === 'resolved') return 'Đã xử lý'
  return 'Bỏ qua'
}

function targetLink(report: any) {
  const type = report.target_type || report.ref_type
  const id = report.target_id || report.ref_id
  if (!id) return ''
  if (type === 'entity') return `/dia-diem/${id}`
  if (type === 'post') return `/bai-viet/${id}`
  if (type === 'user') return `/nguoi-dung/${id}`
  return ''
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchAll())
</script>

<style scoped>
.status-pending { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full, 999px); font-size: var(--text-xs); font-weight: var(--weight-semibold); background: rgba(234, 140, 30, .12); color: #b45309; }
.status-resolved { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full, 999px); font-size: var(--text-xs); font-weight: var(--weight-semibold); background: rgba(46, 125, 91, .12); color: var(--secondary-fg); }
.status-dismissed { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full, 999px); font-size: var(--text-xs); font-weight: var(--weight-semibold); background: rgba(0,0,0,.06); color: var(--muted); }

</style>
