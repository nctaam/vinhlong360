<template>
  <div>
    <h1>Báo cáo</h1>

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
            <td style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ r.reason }}</td>
            <td>
              <span :style="{ color: r.status === 'pending' ? '#e67e22' : r.status === 'resolved' ? 'var(--primary)' : 'var(--muted)' }">
                {{ statusLabel(r.status) }}
              </span>
            </td>
            <td style="font-size: .82rem; color: var(--muted)">{{ formatDate(r.created_at) }}</td>
            <td v-if="r.status === 'pending'" class="admin-actions">
              <button class="btn-success" @click="resolve(r.id)">Xử lý</button>
              <button class="btn-danger" @click="dismiss(r.id)">Bỏ qua</button>
            </td>
            <td v-else style="font-size: .82rem; color: var(--muted)">—</td>
          </tr>
          <tr v-if="!reports.length">
            <td colspan="7" style="text-align: center; padding: 20px; color: var(--muted)">Không có báo cáo nào.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const reports = ref<any[]>([])

async function fetchReports() {
  try {
    const res = await $fetch<any>('/admin-api/reports', { headers: authHeaders() })
    reports.value = res.reports || res || []
  } catch {
    showToast('Không thể tải báo cáo', 'error')
  }
}

async function resolve(id: string) {
  try {
    await $fetch(`/admin-api/reports/${id}/resolve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã xử lý báo cáo', 'success')
    await fetchReports()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi xử lý báo cáo', 'error')
  }
}

async function dismiss(id: string) {
  try {
    await $fetch(`/admin-api/reports/${id}/dismiss`, { method: 'POST', headers: authHeaders() })
    showToast('Đã bỏ qua báo cáo', 'success')
    await fetchReports()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi bỏ qua', 'error')
  }
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

onMounted(() => fetchReports())
</script>
