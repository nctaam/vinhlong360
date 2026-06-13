<template>
  <div>
    <h1>Kiểm duyệt</h1>

    <div class="stat-grid" style="margin-bottom: 20px">
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
          <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ p.content }}</td>
          <td>{{ p.post_type }}</td>
          <td style="font-size: .82rem; color: var(--muted)">{{ formatDate(p.created_at) }}</td>
          <td class="admin-actions">
            <button class="btn-success" @click="approve(p.id)">Duyệt</button>
            <button class="btn-danger" @click="reject(p.id)">Từ chối</button>
          </td>
        </tr>
        <tr v-if="!queue.length">
          <td colspan="5" style="text-align: center; padding: 20px; color: var(--muted)">Không có bài nào chờ duyệt.</td>
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
const queue = ref<any[]>([])
const modStats = ref<any>({})

async function fetchQueue() {
  try {
    const [q, s] = await Promise.all([
      $fetch<any>('/admin-api/moderation/queue', { headers: authHeaders() }),
      $fetch<any>('/admin-api/moderation/stats', { headers: authHeaders() }),
    ])
    queue.value = q.posts || q || []
    modStats.value = s
  } catch { /* ignore */ }
}

async function approve(id: string) {
  try {
    await $fetch(`/admin-api/moderation/${id}/approve`, { method: 'POST', headers: authHeaders() })
    showToast('Đã duyệt bài viết', 'success')
    await fetchQueue()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi duyệt', 'error')
  }
}

async function reject(id: string) {
  if (!confirm('Từ chối bài viết này?')) return
  try {
    await $fetch(`/admin-api/moderation/${id}/reject`, { method: 'POST', headers: authHeaders() })
    showToast('Đã từ chối bài viết', 'success')
    await fetchQueue()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi từ chối', 'error')
  }
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchQueue())
</script>
