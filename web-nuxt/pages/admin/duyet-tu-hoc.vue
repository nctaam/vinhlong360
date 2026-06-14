<template>
  <div>
    <h1>Duyệt tự học & Tiện ích</h1>

    <!-- 1) Provisional review -->
    <h2 style="font-size:1.1rem; margin:16px 0 8px">🧪 Entity tự học chờ duyệt ({{ provisional.length }})</h2>
    <p v-if="!provisional.length" class="muted" style="font-size:.88rem">
      Không có entity provisional. (Lưu ý: trạng thái provisional nằm trong data.json; DB là nguồn sự thật cho chat
      nên entity tự học hiện đã live — quarantine chỉ còn ý nghĩa khi mô hình hoá cột status ở DB.)
    </p>
    <table v-else class="tbl">
      <thead><tr><th>Tên</th><th>Loại</th><th>Conf</th><th>Nguồn</th><th></th></tr></thead>
      <tbody>
        <tr v-for="e in provisional" :key="e.id">
          <td><strong>{{ e.name }}</strong><br><small class="muted">{{ e.summary }}</small></td>
          <td>{{ e.type }}</td>
          <td>{{ ((e.confidence || 0) * 100).toFixed(0) }}%</td>
          <td><small class="muted">{{ e.source?.url || e.source?.title || '—' }}</small></td>
          <td class="admin-actions">
            <button class="btn-success" @click="approve(e)">Duyệt</button>
            <button class="btn-danger" @click="reject(e)">Từ chối</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 2) Tiện ích -->
    <h2 style="font-size:1.1rem; margin:24px 0 8px">🧰 Tiện ích dữ liệu</h2>
    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px">
      <button class="btn btn-primary" :disabled="exporting" @click="exportJson">📤 {{ exporting ? 'Đang xuất…' : 'Export JSON (DB)' }}</button>
      <button class="btn btn-secondary" @click="loadSources">📚 Xem nguồn dữ liệu</button>
    </div>
    <table v-if="sources.length" class="tbl">
      <thead><tr><th>Nguồn</th><th>Số entity</th><th>URL mẫu</th></tr></thead>
      <tbody>
        <tr v-for="s in sources" :key="s.title">
          <td>{{ s.title }}</td><td>{{ s.count }}</td>
          <td><small class="muted">{{ s.sample_url || '—' }}</small></td>
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

async function loadProvisional() {
  try {
    const r = await $fetch<any>('/admin-api/provisional', { headers: authHeaders() })
    provisional.value = r.provisional || []
  } catch { /* ignore */ }
}
async function approve(e: any) {
  try {
    await $fetch(`/admin-api/provisional/${e.id}/approve`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast(`Đã duyệt ${e.name}`, 'success')
  } catch (err: any) { showToast(err?.data?.detail || 'Duyệt lỗi', 'error') }
}
async function reject(e: any) {
  if (!confirm(`Từ chối + xóa "${e.name}"?`)) return
  try {
    await $fetch(`/admin-api/provisional/${e.id}/reject`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast('Đã từ chối', 'success')
  } catch (err: any) { showToast(err?.data?.detail || 'Từ chối lỗi', 'error') }
}

async function loadSources() {
  try {
    const r = await $fetch<any>('/admin-api/sources', { headers: authHeaders() })
    sources.value = Object.entries(r.sources || {}).map(([title, v]: any) => ({ title, ...v }))
      .sort((a, b) => b.count - a.count)
  } catch { showToast('Tải nguồn lỗi', 'error') }
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

<style scoped>
.muted { color: var(--muted, #888); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th, .tbl td { text-align: left; padding: 8px; border-bottom: 1px solid rgba(0,0,0,.08); vertical-align: top; }
</style>
