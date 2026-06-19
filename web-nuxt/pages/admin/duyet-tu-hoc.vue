<template>
  <div>
    <div class="admin-head-row">
      <h1>Duyệt tự học & Tiện ích</h1>
      <button type="button" class="admin-refresh" :disabled="loading" @click="loadProvisional">🔄 Làm mới</button>
    </div>

    <!-- 1) Provisional review -->
    <h2 class="admin-section-title" style="margin-top: var(--space-4)">🧪 Entity tự học chờ duyệt ({{ provisional.length }})</h2>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <p v-if="!provisional.length" class="admin-muted" style="font-size: var(--text-sm)">
        Không có entity provisional. (Lưu ý: trạng thái provisional nằm trong data.json; DB là nguồn sự thật cho chat
        nên entity tự học hiện đã live — quarantine chỉ còn ý nghĩa khi mô hình hoá cột status ở DB.)
      </p>
      <table v-else class="admin-simple-table">
        <thead><tr><th>Tên</th><th>Loại</th><th>Nguồn</th><th></th></tr></thead>
        <tbody>
          <tr v-for="e in provisional" :key="e.id">
            <td><strong>{{ e.name }}</strong><br><small class="admin-muted">{{ e.summary }}</small></td>
            <td>{{ e.type }}</td>
            <td><small class="admin-muted">{{ e.source?.url || e.source?.title || '—' }}</small></td>
            <td class="admin-actions">
              <button type="button" class="btn-success" :disabled="acting === e.id" @click="approve(e)">
                {{ acting === e.id ? '…' : 'Duyệt' }}
              </button>
              <button type="button" class="btn-danger" :disabled="acting === e.id" @click="reject(e)">Từ chối</button>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- 2) Tiện ích -->
    <h2 class="admin-section-title" style="margin-top: var(--space-6)">🧰 Tiện ích dữ liệu</h2>
    <div class="admin-btn-group" style="margin-bottom: var(--space-3)">
      <button type="button" class="btn btn-primary" :disabled="exporting" @click="exportJson">📤 {{ exporting ? 'Đang xuất…' : 'Export JSON (DB)' }}</button>
      <button type="button" class="btn btn-secondary" :disabled="loadingSources" @click="loadSources">
        📚 {{ loadingSources ? 'Đang tải…' : 'Xem nguồn dữ liệu' }}
      </button>
    </div>
    <table v-if="sources.length" class="admin-simple-table">
      <thead><tr><th>Nguồn</th><th>Số entity</th><th>URL mẫu</th></tr></thead>
      <tbody>
        <tr v-for="s in sources" :key="s.title">
          <td>{{ s.title }}</td><td>{{ s.count }}</td>
          <td><small class="admin-muted">{{ s.sample_url || '—' }}</small></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const provisional = ref<any[]>([])
const sources = ref<any[]>([])
const exporting = ref(false)
const loading = ref(true)
const acting = ref<string | null>(null)
const loadingSources = ref(false)

async function loadProvisional() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/provisional', { headers: authHeaders() })
    provisional.value = r.provisional || []
  } catch {
    showToast('Không thể tải danh sách entity tự học', 'error')
  }
  loading.value = false
}
async function approve(e: any) {
  if (!confirm(`Duyệt "${e.name}" vào hệ thống?`)) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/approve`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast(`Đã duyệt ${e.name}`, 'success')
  } catch (err: any) { showToast(err?.data?.detail || 'Duyệt lỗi', 'error') }
  acting.value = null
}
async function reject(e: any) {
  if (!confirm(`Từ chối + xóa "${e.name}"?`)) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/reject`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast('Đã từ chối', 'success')
  } catch (err: any) { showToast(err?.data?.detail || 'Từ chối lỗi', 'error') }
  acting.value = null
}

async function loadSources() {
  loadingSources.value = true
  try {
    const r = await $fetch<any>('/admin-api/sources', { headers: authHeaders() })
    sources.value = Object.entries(r.sources || {}).map(([title, v]: any) => ({ title, ...v }))
      .sort((a, b) => b.count - a.count)
  } catch { showToast('Tải nguồn lỗi', 'error') }
  loadingSources.value = false
}

async function exportJson() {
  exporting.value = true
  try {
    const data = await $fetch<any>('/admin-api/export', { method: 'POST', headers: authHeaders() })
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `vinhlong360-export-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch { showToast('Export lỗi', 'error') }
  exporting.value = false
}

onMounted(loadProvisional)
</script>
