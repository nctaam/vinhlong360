<template>
  <div>
    <div class="admin-head-row">
      <h1>Kiểm duyệt</h1>
      <button class="admin-refresh" :disabled="loading" @click="fetchQueue">🔄 Làm mới</button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">{{ modStats.pending || 0 }}</div>
          <div class="stat-label">Chờ duyệt</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ modStats.approved_today || 0 }}</div>
          <div class="stat-label">Duyệt hôm nay</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ modStats.rejected_today || 0 }}</div>
          <div class="stat-label">Từ chối hôm nay</div>
        </div>
      </div>

      <div class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Tác giả</th>
            <th>Nội dung</th>
            <th>Loại</th>
            <th>Ngày</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in queue" :key="p.id">
            <td>{{ p.display_name || p.phone || '—' }}</td>
            <td class="admin-td-truncate">{{ p.content }}</td>
            <td>{{ p.post_type }}</td>
            <td class="admin-td-muted">{{ formatDate(p.created_at) }}</td>
            <td class="admin-actions">
              <button class="btn-success" :disabled="acting === p.id" @click="approve(p.id)">
                {{ acting === p.id ? '…' : 'Duyệt' }}
              </button>
              <button class="btn-danger" :disabled="acting === p.id" @click="reject(p.id)">Từ chối</button>
            </td>
          </tr>
          <tr v-if="!queue.length">
            <td colspan="5" class="admin-empty-row">Không có bài nào chờ duyệt.</td>
          </tr>
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
const queue = ref<any[]>([])
const modStats = ref<any>({})
const loading = ref(true)
const acting = ref<string | null>(null)

async function fetchQueue() {
  loading.value = true
  try {
    const [q, s] = await Promise.all([
      $fetch<any>('/admin-api/moderation/queue', { headers: authHeaders() }),
      $fetch<any>('/admin-api/moderation/stats', { headers: authHeaders() }),
    ])
    queue.value = q.posts || q || []
    modStats.value = s
  } catch {
    showToast('Không thể tải hàng đợi kiểm duyệt', 'error')
  }
  loading.value = false
}

async function approve(id: string) {
  if (!confirm('Duyệt bài viết này?')) return
  acting.value = id
  try {
    await $fetch(`/admin-api/moderation/${id}/approve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã duyệt bài viết', 'success')
    await fetchQueue()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi duyệt', 'error')
  }
  acting.value = null
}

async function reject(id: string) {
  if (!confirm('Từ chối bài viết này?')) return
  acting.value = id
  try {
    await $fetch(`/admin-api/moderation/${id}/reject`, { method: 'POST', headers: authHeaders() })
    showToast('Đã từ chối bài viết', 'success')
    await fetchQueue()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi từ chối', 'error')
  }
  acting.value = null
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchQueue())
</script>
