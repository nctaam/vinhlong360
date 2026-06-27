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
        <span v-if="provisional.length" class="dth-count-badge dth-count-warn" role="status" :aria-label="`${provisional.length} entity chờ duyệt`">{{ provisional.length }}</span>
      </div>

      <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải danh sách tự học"><div class="spinner"></div></div>
      <div v-else-if="loadError" class="admin-empty">
        <p>Không tải được danh sách entity tự học.</p>
        <button type="button" class="btn btn-secondary" @click="loadProvisional">Thử lại</button>
      </div>
      <template v-else>
        <div v-if="!provisional.length" class="dth-empty">
          <span class="dth-empty-icon">&#9989;</span>
          <p>Tất cả entity tự học đã được duyệt.</p>
          <small class="admin-muted">Quay lại kiểm tra sau, hoặc tải nguồn dữ liệu để xem thống kê.</small>
        </div>
        <div v-else class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th scope="col">Entity</th><th scope="col">Loại</th><th scope="col">Tin cậy</th><th scope="col">Nguồn</th><th scope="col">Thao tác</th></tr></thead>
            <tbody>
              <tr v-for="e in provisional" :key="e.id">
                <td>
                  <strong>{{ e.name }}</strong>
                  <small v-if="e.summary" class="dth-summary">{{ e.summary }}</small>
                </td>
                <td><span class="dth-type-badge">{{ e.type }}</span></td>
                <td>
                  <span v-if="typeof e.confidence === 'number'" class="dth-conf-badge" :class="e.confidence >= 0.7 ? 'dth-conf-high' : 'dth-conf-low'">{{ Math.round(e.confidence * 100) }}%</span>
                  <span v-else class="admin-td-muted"><small>—</small></span>
                </td>
                <td class="admin-td-muted"><small>{{ e.source?.[0]?.url || e.source?.[0]?.name || '—' }}</small></td>
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
          <span v-if="exporting" class="dth-tool-spinner" aria-hidden="true"></span>
          <span v-else class="dth-tool-icon">&#128230;</span>
          <span class="dth-tool-label">{{ exporting ? 'Đang xuất...' : 'Export JSON (DB)' }}</span>
          <small>Tải data.json từ DB</small>
        </button>
        <button type="button" class="dth-tool-card" :disabled="loadingSources" @click="loadSources">
          <span v-if="loadingSources" class="dth-tool-spinner" aria-hidden="true"></span>
          <span v-else class="dth-tool-icon">&#128218;</span>
          <span class="dth-tool-label">{{ loadingSources ? 'Đang tải...' : 'Xem nguồn dữ liệu' }}</span>
          <small>Thống kê theo nguồn</small>
        </button>
      </div>

      <div v-if="sources.length" class="dth-sources">
        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr><th scope="col">Nguồn</th><th scope="col">Số entity</th><th scope="col">URL mẫu</th></tr></thead>
            <tbody>
              <tr v-for="s in sources" :key="s.title">
                <td><strong>{{ s.title }}</strong></td>
                <td><span class="dth-source-count" :aria-label="`${s.count} entity`">{{ s.count }}</span></td>
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
useHead({ title: 'Duyệt tự học — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

const provisional = ref<Entity[]>([])
const sources = ref<Record<string, unknown>[]>([])
const exporting = ref(false)
const loading = ref(true)
const loadError = ref(false)
const acting = ref<string | null>(null)
const loadingSources = ref(false)

async function loadProvisional() {
  loading.value = true
  loadError.value = false
  try {
    const r = await $fetch<Record<string, unknown>>('/admin-api/provisional', { headers: authHeaders() })
    provisional.value = (r.provisional || []) as Entity[]
  } catch {
    loadError.value = true
    showToast('Không thể tải danh sách entity tự học', 'error')
  } finally {
    loading.value = false
  }
}
async function approve(e: Entity) {
  if (!await confirmDialog(`Duyệt "${e.name}" vào hệ thống?`)) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/approve`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast(`Đã duyệt ${e.name}`, 'success')
  } catch (err: unknown) { showToast(getErrorDetail(err, 'Duyệt lỗi'), 'error') }
  acting.value = null
}
async function reject(e: Entity) {
  if (!await confirmDialog(`Từ chối + xóa "${e.name}"?`, { danger: true })) return
  acting.value = e.id
  try {
    await $fetch(`/admin-api/provisional/${e.id}/reject`, { method: 'POST', headers: authHeaders() })
    provisional.value = provisional.value.filter(x => x.id !== e.id)
    showToast('Đã từ chối', 'success')
  } catch (err: unknown) { showToast(getErrorDetail(err, 'Từ chối lỗi'), 'error') }
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
.dth-count-warn { background: rgba(var(--warning-rgb),.1); color: #c67a00; }

.dth-summary { display: block; color: var(--muted); margin-top: 2px; font-size: .8rem; }
.dth-type-badge {
  display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-size: .72rem; font-weight: 600;
  background: rgba(142,142,147,.08); color: var(--muted);
}

/* ── Confidence badge ── */
.dth-conf-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 40px; padding: 2px 8px; border-radius: 100px;
  font-size: .72rem; font-weight: 700; font-variant-numeric: tabular-nums;
}
.dth-conf-high { background: rgba(var(--primary-rgb),.1); color: #1a7a43; }
.dth-conf-low { background: rgba(var(--warning-rgb),.12); color: #c67a00; }

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
.dth-tool-spinner {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid rgba(var(--primary-rgb),.2); border-top-color: var(--primary, #219653);
  animation: dth-spin .7s linear infinite;
}
@keyframes dth-spin { to { transform: rotate(360deg); } }
.dth-tool-label { font-size: .88rem; font-weight: 600; color: var(--ink); }
.dth-tool-card small { font-size: .75rem; color: var(--muted); }

.dth-sources { margin-top: var(--space-3); }
.dth-source-count { font-weight: 700; color: var(--primary, #219653); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .dth-tool-card:hover:not(:disabled) { transform: none; }
  .dth-tool-card:active:not(:disabled) { transform: none; }
  .dth-tool-spinner { animation: none; }
}

/* ── Dark ── */
.dark .dth-empty { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dth-tool-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .dth-tool-card:hover:not(:disabled) { box-shadow: 0 4px 16px rgba(0,0,0,.4); }
.dark .dth-conf-high { background: rgba(var(--primary-rgb),.18); color: #4ade80; }
.dark .dth-conf-low { background: rgba(var(--warning-rgb),.14); color: #ffb340; }
.dark .dth-tool-label { color: var(--ink); }
.dark .dth-count-warn { background: rgba(var(--warning-rgb),.12); color: #ffb340; }
.dark .dth-type-badge { background: rgba(255,255,255,.06); }
</style>
