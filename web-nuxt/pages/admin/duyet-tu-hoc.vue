<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Duyệt tự học & Tiện ích</h1>
        <p class="dth-subtitle">Duyệt entity provisional và công cụ dữ liệu</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="loadProvisional"><span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới</button>
    </div>

    <!-- 1) Provisional review -->
    <div class="dth-section">
      <div class="dth-section-head">
        <h2 class="admin-section-title">Entity tự học chờ duyệt</h2>
        <span v-if="provisional.length" class="dth-count-badge dth-count-warn">{{ provisional.length }}</span>
      </div>

      <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
      <template v-else>
        <div v-if="!provisional.length" class="dth-empty">
          <span class="dth-empty-icon">&#9989;</span>
          <p>Không có entity provisional.</p>
          <small class="admin-muted">Lưu ý: trạng thái provisional nằm trong data.json; DB là nguồn sự thật cho chat nên entity tự học hiện đã live — quarantine chỉ còn ý nghĩa khi mô hình hoá cột status ở DB.</small>
        </div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>Entity</th><th>Loại</th><th>Nguồn</th><th>Thao tác</th></tr></thead>
            <tbody>
              <tr v-for="e in provisional" :key="e.id">
                <td>
                  <strong>{{ e.name }}</strong>
                  <small v-if="e.summary" class="dth-summary">{{ e.summary }}</small>
                </td>
                <td><span class="dth-type-badge">{{ e.type }}</span></td>
                <td class="admin-td-muted"><small>{{ e.source?.url || e.source?.title || '—' }}</small></td>
                <td class="admin-actions">
                  <button type="button" class="btn-success" :disabled="acting === e.id" @click="approve(e)">
                    {{ acting === e.id ? '...' : 'Duyệt' }}
                  </button>
                  <button type="button" class="btn-danger" :disabled="acting === e.id" @click="reject(e)">Từ chối</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- 2) Tiện ích -->
    <div class="dth-section">
      <h2 class="admin-section-title">Tiện ích dữ liệu</h2>
      <div class="dth-tools-grid">
        <button type="button" class="dth-tool-card" :disabled="exporting" @click="exportJson">
          <span class="dth-tool-icon">&#128230;</span>
          <span class="dth-tool-label">{{ exporting ? 'Đang xuất...' : 'Export JSON (DB)' }}</span>
          <small>Tải data.json từ DB</small>
        </button>
        <button type="button" class="dth-tool-card" :disabled="loadingSources" @click="loadSources">
          <span class="dth-tool-icon">&#128218;</span>
          <span class="dth-tool-label">{{ loadingSources ? 'Đang tải...' : 'Xem nguồn dữ liệu' }}</span>
          <small>Thống kê theo nguồn</small>
        </button>
      </div>

      <div v-if="sources.length" class="dth-sources">
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th>Nguồn</th><th>Số entity</th><th>URL mẫu</th></tr></thead>
            <tbody>
              <tr v-for="s in sources" :key="s.title">
                <td><strong>{{ s.title }}</strong></td>
                <td><span class="dth-source-count">{{ s.count }}</span></td>
                <td class="admin-td-muted"><small>{{ s.sample_url || '—' }}</small></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const provisional = ref<Entity[]>([])
const sources = ref<Record<string, unknown>[]>([])
const exporting = ref(false)
const loading = ref(true)
const acting = ref<string | null>(null)
const loadingSources = ref(false)

async function loadProvisional() {
  loading.value = true
  try {
    const r = await $fetch<Record<string, unknown>>('/admin-api/provisional', { headers: authHeaders() })
    provisional.value = (r.provisional || []) as Entity[]
  } catch {
    showToast('Không thể tải danh sách entity tự học', 'error')
  }
  loading.value = false
}
async function approve(e: Entity) {
  if (!confirm(`Duyệt "${e.name}" vào hệ thống?`)) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/approve`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast(`Đã duyệt ${e.name}`, 'success')
  } catch (err: unknown) { showToast((err as any)?.data?.detail || 'Duyệt lỗi', 'error') }
  acting.value = null
}
async function reject(e: Entity) {
  if (!confirm(`Từ chối + xóa "${e.name}"?`)) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/reject`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast('Đã từ chối', 'success')
  } catch (err: unknown) { showToast((err as any)?.data?.detail || 'Từ chối lỗi', 'error') }
  acting.value = null
}

async function loadSources() {
  loadingSources.value = true
  try {
    const r = await $fetch<Record<string, unknown>>('/admin-api/sources', { headers: authHeaders() })
    sources.value = Object.entries((r.sources || {}) as Record<string, Record<string, unknown>>).map(([title, v]) => ({ title, ...v }))
      .sort((a: any, b: any) => b.count - a.count)
  } catch { showToast('Tải nguồn lỗi', 'error') }
  loadingSources.value = false
}

async function exportJson() {
  exporting.value = true
  try {
    const data = await $fetch<Record<string, unknown>>('/admin-api/export', { method: 'POST', headers: authHeaders() })
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
.dth-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }

.dth-section { margin-bottom: var(--space-6); }
.dth-section-head {
  display: flex; align-items: center; gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.dth-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 24px; height: 24px; padding: 0 8px;
  border-radius: 100px; font-size: .72rem; font-weight: 700;
}
.dth-count-warn { background: rgba(255,159,10,.1); color: #c67a00; }

.dth-summary { display: block; color: var(--muted); margin-top: 2px; font-size: .8rem; }
.dth-type-badge {
  display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-size: .72rem; font-weight: 600;
  background: rgba(142,142,147,.08); color: var(--muted);
}

/* ── Empty state ── */
.dth-empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-6); text-align: center;
  background: var(--bg); border: .5px solid var(--line); border-radius: 14px;
}
.dth-empty-icon { font-size: 2rem; }
.dth-empty p { margin: 0; font-weight: 500; color: #219653; }
.dth-empty small { max-width: 500px; line-height: 1.5; }

/* ── Tools grid ── */
.dth-tools-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-3); margin-bottom: var(--space-4);
}
.dth-tool-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-5) var(--space-4); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  cursor: pointer; text-align: center;
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.dth-tool-card:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,.06); border-color: var(--primary); }
.dth-tool-card:active:not(:disabled) { transform: scale(.97); }
.dth-tool-card:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.dth-tool-card:disabled { opacity: .4; cursor: not-allowed; }
.dth-tool-icon { font-size: 1.6rem; }
.dth-tool-label { font-size: .88rem; font-weight: 600; color: var(--ink); }
.dth-tool-card small { font-size: .75rem; color: var(--muted); }

.dth-sources { margin-top: var(--space-3); }
.dth-source-count { font-weight: 700; color: var(--primary, #219653); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .dth-tool-card:hover:not(:disabled) { transform: none; }
  .dth-tool-card:active:not(:disabled) { transform: none; }
}

/* ── Dark ── */
.dark .dth-empty { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dth-tool-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dth-tool-card:hover:not(:disabled) { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .dth-tool-label { color: var(--ink); }
.dark .dth-count-warn { background: rgba(255,159,10,.12); color: #ffb340; }
.dark .dth-type-badge { background: rgba(255,255,255,.06); }
</style>
