<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Báo cáo</h1>
        <p class="rpt-subtitle">Quản lý báo cáo vi phạm & sai thông tin</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchAll">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <!-- ── Filter chips ── -->
      <div class="rpt-filters">
        <div class="rpt-filter-group" role="group" aria-label="Lọc theo trạng thái">
          <span class="rpt-filter-label">Trạng thái</span>
          <button
            v-for="s in statusChips" :key="s.value" type="button"
            class="rpt-chip" :class="{ active: statusFilter === s.value }"
            :aria-pressed="statusFilter === s.value"
            @click="statusFilter = s.value">
            {{ s.label }}
            <span class="rpt-chip-count">{{ countByStatus(s.value) }}</span>
          </button>
        </div>
        <div class="rpt-filter-group" role="group" aria-label="Lọc theo loại đối tượng">
          <span class="rpt-filter-label">Đối tượng</span>
          <button
            v-for="t in typeChips" :key="t.value" type="button"
            class="rpt-chip" :class="{ active: typeFilter === t.value }"
            :aria-pressed="typeFilter === t.value"
            @click="typeFilter = t.value">
            {{ t.label }}
            <span class="rpt-chip-count">{{ countByType(t.value) }}</span>
          </button>
        </div>
      </div>

      <!-- ── Bulk action bar ── -->
      <div v-if="selectedIds.size" class="rpt-bulkbar">
        <span class="rpt-bulk-count">{{ selectedIds.size }} đã chọn</span>
        <div class="rpt-bulk-actions">
          <button type="button" class="btn-success" :disabled="bulkActing" @click="bulkAction('resolve')">
            {{ bulkActing ? '…' : 'Xử lý đã chọn' }}
          </button>
          <button type="button" class="btn-danger" :disabled="bulkActing" @click="bulkAction('dismiss')">Bỏ qua đã chọn</button>
          <button type="button" class="rpt-bulk-clear" :disabled="bulkActing" @click="clearSelection">Bỏ chọn</button>
        </div>
      </div>

      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th class="rpt-th-check">
                <input
                  type="checkbox" class="rpt-checkbox" aria-label="Chọn tất cả (chờ xử lý) trên trang"
                  :checked="allPageSelected" :indeterminate.prop="somePageSelected && !allPageSelected"
                  :disabled="!pageSelectableIds.length" @change="toggleSelectAllPage($event)">
              </th>
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
            <tr v-for="r in pagedReports" :key="r.id" :class="{ 'rpt-row-selected': selectedIds.has(r.id) }">
              <td class="rpt-td-check">
                <input
                  v-if="r.status === 'pending'" type="checkbox" class="rpt-checkbox"
                  :aria-label="`Chọn báo cáo ${r.id}`"
                  :checked="selectedIds.has(r.id)" @change="toggleSelect(r.id)">
              </td>
              <td>{{ r.reporter_name || r.reporter_phone || '—' }}</td>
              <td>{{ r.target_type || r.ref_type || '—' }}</td>
              <td>
                <NuxtLink v-if="targetLink(r)" :to="targetLink(r)" target="_blank" rel="noopener">{{ r.target_id || r.ref_id }}</NuxtLink>
                <span v-else>{{ r.target_id || r.ref_id || '—' }}</span>
              </td>
              <td class="rpt-reason-cell">
                <div :class="expanded.has(r.id) ? 'rpt-reason-full' : 'admin-td-truncate'">{{ r.reason }}</div>
                <button
                  v-if="isLongReason(r.reason)" type="button" class="rpt-reason-toggle"
                  :aria-expanded="expanded.has(r.id)" @click="toggleExpand(r.id)">
                  {{ expanded.has(r.id) ? 'Thu gọn' : 'Xem thêm' }}
                </button>
              </td>
              <td>
                <span :class="r.status === 'pending' ? 'status-pending' : r.status === 'resolved' ? 'status-resolved' : 'status-dismissed'">
                  {{ statusLabel(r.status) }}
                </span>
              </td>
              <td class="admin-td-muted"><time :datetime="r.created_at">{{ formatDate(r.created_at) }}</time></td>
              <td v-if="r.status === 'pending'" class="admin-actions">
                <button type="button" class="btn-success" :disabled="acting === r.id" @click="resolve(r.id)">
                  {{ acting === r.id ? '…' : 'Xử lý' }}
                </button>
                <button type="button" class="btn-danger" :disabled="acting === r.id" @click="dismiss(r.id)">Bỏ qua</button>
              </td>
              <td v-else class="admin-td-muted">—</td>
            </tr>
            <tr v-if="!filteredReports.length">
              <td colspan="8" class="admin-empty-row">
                <div class="rpt-empty"><span class="rpt-empty-icon">&#128203;</span><span>{{ reports.length ? 'Không có báo cáo khớp bộ lọc.' : 'Không có báo cáo nào.' }}</span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── Load more / count ── -->
      <div v-if="filteredReports.length" class="rpt-pager">
        <span class="rpt-pager-info">Hiển thị {{ pagedReports.length }} / {{ filteredReports.length }}</span>
        <button v-if="hasMore" type="button" class="rpt-loadmore" @click="visibleCount += PAGE_SIZE">
          Tải thêm ({{ Math.min(PAGE_SIZE, filteredReports.length - visibleCount) }})
        </button>
      </div>

      <div class="rpt-section-head">
        <h2 class="admin-section-title">Báo sai thông tin (ẩn danh)</h2>
        <span v-if="infoOpen" class="rpt-open-badge">{{ infoOpen }} chưa xử lý</span>
      </div>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>Loại</th><th>Đối tượng</th><th>Lý do</th><th>Trạng thái</th><th>Ngày</th><th>Thao tác</th></tr></thead>
          <tbody>
            <tr v-for="r in infoReports" :key="r.ts" :style="{ opacity: (r.status || 'open') === 'open' ? 1 : .5 }">
              <td>{{ r.target_type }}</td>
              <td><NuxtLink v-if="infoLink(r)" :to="infoLink(r)" target="_blank" rel="noopener">{{ r.target_id }}</NuxtLink><span v-else>{{ r.target_id }}</span></td>
              <td class="admin-td-truncate">{{ r.reason }}<br><small class="admin-muted">{{ r.detail }}</small></td>
              <td>{{ infoStatus(r.status) }}</td>
              <td class="admin-td-muted"><time :datetime="r.ts">{{ formatDate(r.ts) }}</time></td>
              <td class="admin-actions">
                <template v-if="(r.status || 'open') === 'open'">
                  <button type="button" class="btn-success" :disabled="infoActing === r.ts" @click="infoAction(r, 'resolved')">Xử lý</button>
                  <button type="button" class="btn-danger" :disabled="infoActing === r.ts" @click="infoAction(r, 'dismissed')">Bỏ qua</button>
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
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const reports = ref<Entity[]>([])
const infoReports = ref<Entity[]>([])
const infoOpen = ref(0)
const loading = ref(true)
const acting = ref<string | null>(null)
const infoActing = ref<string | null>(null)

// ── Filters / pagination / selection (client-side over loaded data) ──
const PAGE_SIZE = 20
const REASON_LIMIT = 120
const statusFilter = ref<'all' | 'open' | 'resolved' | 'dismissed'>('all')
const typeFilter = ref<'all' | 'entity' | 'post' | 'user'>('all')
const visibleCount = ref(PAGE_SIZE)
const selectedIds = ref<Set<string>>(new Set())
const expanded = ref<Set<string>>(new Set())
const bulkActing = ref(false)

const statusChips = [
  { value: 'all', label: 'Tất cả' },
  { value: 'open', label: 'Chờ xử lý' },
  { value: 'resolved', label: 'Đã xử lý' },
  { value: 'dismissed', label: 'Bỏ qua' },
] as const
const typeChips = [
  { value: 'all', label: 'Tất cả' },
  { value: 'entity', label: 'Địa điểm' },
  { value: 'post', label: 'Bài viết' },
  { value: 'user', label: 'Người dùng' },
] as const

function reportType(r: Record<string, unknown>) {
  return r.target_type || r.ref_type || ''
}
// "open" chip maps to the backend "pending" status for main reports
function matchStatus(r: Record<string, unknown>, f: string) {
  if (f === 'all') return true
  if (f === 'open') return r.status === 'pending'
  return r.status === f
}
function countByStatus(f: string) {
  return reports.value.filter(r => matchStatus(r, f)).length
}
function countByType(f: string) {
  if (f === 'all') return reports.value.length
  return reports.value.filter(r => reportType(r) === f).length
}

const filteredReports = computed(() =>
  reports.value.filter(r => matchStatus(r, statusFilter.value)
    && (typeFilter.value === 'all' || reportType(r) === typeFilter.value)),
)
const pagedReports = computed(() => filteredReports.value.slice(0, visibleCount.value))
const hasMore = computed(() => visibleCount.value < filteredReports.value.length)

// reset pagination when filters change
watch([statusFilter, typeFilter], () => { visibleCount.value = PAGE_SIZE })

// ── Reason expand ──
function isLongReason(reason: string) {
  return !!reason && reason.length > REASON_LIMIT
}
function toggleExpand(id: string) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

// ── Selection (only pending reports are selectable) ──
const pageSelectableIds = computed(() =>
  pagedReports.value.filter(r => r.status === 'pending').map(r => r.id as string))
const allPageSelected = computed(() =>
  pageSelectableIds.value.length > 0 && pageSelectableIds.value.every(id => selectedIds.value.has(id)))
const somePageSelected = computed(() =>
  pageSelectableIds.value.some(id => selectedIds.value.has(id)))

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}
function toggleSelectAllPage(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  const next = new Set(selectedIds.value)
  for (const id of pageSelectableIds.value) checked ? next.add(id) : next.delete(id)
  selectedIds.value = next
}
function clearSelection() {
  selectedIds.value = new Set()
}

async function bulkAction(kind: 'resolve' | 'dismiss') {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  const verb = kind === 'resolve' ? 'xử lý' : 'bỏ qua'
  if (!confirm(`Xác nhận ${verb} ${ids.length} báo cáo đã chọn?`)) return
  bulkActing.value = true
  let ok = 0, fail = 0
  // Loop the existing per-item endpoints (no bulk endpoint available)
  for (const id of ids) {
    try {
      await $fetch(`/admin-api/reports/${id}/${kind}`, { method: 'POST', headers: authHeaders() })
      ok++
    } catch { fail++ }
  }
  bulkActing.value = false
  clearSelection()
  if (ok) showToast(`Đã ${verb} ${ok} báo cáo${fail ? `, ${fail} lỗi` : ''}`, fail ? 'error' : 'success')
  else showToast('Không thể cập nhật báo cáo', 'error')
  await fetchReports()
}

async function fetchAll() {
  loading.value = true
  await Promise.all([fetchReports(), fetchInfoReports()])
  loading.value = false
}

async function fetchInfoReports() {
  try {
    const res = await $fetch<Record<string, unknown>>('/admin-api/info-reports?limit=200', { headers: authHeaders() })
    infoReports.value = res.reports || []
    infoOpen.value = res.open ?? 0
  } catch { showToast('Không thể tải danh sách báo sai', 'error') }
}

async function infoAction(r: Record<string, unknown>, status: string) {
  if (status === 'dismissed' && !confirm('Bỏ qua báo sai này?')) return
  if (status === 'resolved' && !confirm('Đánh dấu đã xử lý?')) return
  infoActing.value = r.ts
  try {
    await $fetch('/admin-api/info-reports/action', { method: 'POST', headers: authHeaders(), body: { ts: r.ts, status } })
    r.status = status
    infoOpen.value = infoReports.value.filter(x => (x.status || 'open') === 'open').length
  } catch (e: unknown) { showToast(e?.data?.detail || 'Lỗi cập nhật', 'error') }
  infoActing.value = null
}

function infoStatus(s: string) {
  return s === 'resolved' ? 'Đã xử lý' : s === 'dismissed' ? 'Bỏ qua' : 'Chưa xử lý'
}
function infoLink(r: Record<string, unknown>) {
  const id = r.target_id
  if (!id) return ''
  if (r.target_type === 'post') return `/bai-viet/${id}`
  if (r.target_type === 'facility' || r.target_type === 'entity') return `/dia-diem/${id}`
  return ''
}

async function fetchReports() {
  try {
    const res = await $fetch<Record<string, unknown>>('/admin-api/reports', { headers: authHeaders() })
    reports.value = res.reports || res || []
    // drop selections for reports no longer pending (e.g. just resolved/dismissed)
    const pending = new Set(reports.value.filter(r => r.status === 'pending').map(r => r.id as string))
    selectedIds.value = new Set([...selectedIds.value].filter(id => pending.has(id)))
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
  } catch (e: unknown) {
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
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Lỗi khi bỏ qua', 'error')
  }
  acting.value = null
}

function statusLabel(status: string) {
  if (status === 'pending') return 'Chờ xử lý'
  if (status === 'resolved') return 'Đã xử lý'
  return 'Bỏ qua'
}

function targetLink(report: Record<string, unknown>) {
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
.rpt-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

.rpt-section-head {
  display: flex; align-items: center; gap: var(--space-3);
  margin-top: var(--space-8); margin-bottom: var(--space-4);
}
.rpt-open-badge {
  display: inline-flex; align-items: center; padding: 2px 10px;
  border-radius: 100px; font-size: .72rem; font-weight: 600;
  background: rgba(255,159,10,.1); color: #c67a00;
}

/* ── Status badges ── */
.status-pending, .status-resolved, .status-dismissed {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 10px; border-radius: 100px;
  font-size: .72rem; font-weight: 600;
  transition: background .2s;
}
.status-pending::before, .status-resolved::before, .status-dismissed::before {
  content: ''; width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.status-pending { background: rgba(255,159,10,.08); color: #c67a00; }
.status-pending::before { background: #FF9F0A; animation: rpt-pulse 2s ease-in-out infinite; }
.status-resolved { background: rgba(33,150,83,.08); color: #219653; }
.status-resolved::before { background: #219653; }
.status-dismissed { background: rgba(142,142,147,.08); color: var(--muted); }
.status-dismissed::before { background: var(--muted); opacity: .4; }
@keyframes rpt-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }

.rpt-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.rpt-empty-icon { font-size: 2rem; opacity: .3; }

/* ── Filter chips ── */
.rpt-filters {
  display: flex; flex-wrap: wrap; gap: var(--space-5) var(--space-6);
  margin-bottom: var(--space-4);
}
.rpt-filter-group { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); }
.rpt-filter-label { font-size: .72rem; font-weight: 600; color: var(--muted); margin-right: 2px; }
.rpt-chip {
  display: inline-flex; align-items: center; gap: 6px;
  min-height: 32px; padding: 4px 12px;
  border: 1px solid var(--border); border-radius: 100px;
  background: var(--surface, #fff); color: var(--text, #1d1d1f);
  font-size: .78rem; font-weight: 500; cursor: pointer;
  transition: background .2s, border-color .2s, color .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.rpt-chip:hover { border-color: var(--primary, #0071e3); }
.rpt-chip:active { transform: scale(.96); }
.rpt-chip.active {
  background: var(--primary, #0071e3); border-color: var(--primary, #0071e3); color: #fff;
}
.rpt-chip:focus-visible { outline: 2px solid var(--primary, #0071e3); outline-offset: 2px; }
.rpt-chip-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; padding: 0 5px;
  border-radius: 100px; font-size: .68rem; font-weight: 600;
  background: rgba(0,0,0,.06); color: var(--muted);
}
.rpt-chip.active .rpt-chip-count { background: rgba(255,255,255,.25); color: #fff; }

/* ── Bulk action bar ── */
.rpt-bulkbar {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4); margin-bottom: var(--space-3);
  border: 1px solid var(--primary, #0071e3); border-radius: var(--radius, 12px);
  background: rgba(0,113,227,.06);
  animation: rpt-slide-in .25s cubic-bezier(.2,1,.4,1);
}
@keyframes rpt-slide-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
.rpt-bulk-count { font-size: .82rem; font-weight: 600; color: var(--primary, #0071e3); }
.rpt-bulk-actions { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.rpt-bulk-clear {
  min-height: 32px; padding: 4px 12px; border: none; border-radius: 8px;
  background: transparent; color: var(--muted); font-size: .78rem; cursor: pointer;
  transition: color .2s;
}
.rpt-bulk-clear:hover { color: var(--text, #1d1d1f); }
.rpt-bulk-clear:focus-visible { outline: 2px solid var(--primary, #0071e3); outline-offset: 2px; }

/* ── Checkboxes / selected row ── */
.rpt-th-check, .rpt-td-check { width: 36px; text-align: center; }
.rpt-checkbox { width: 17px; height: 17px; cursor: pointer; accent-color: var(--primary, #0071e3); }
.rpt-checkbox:focus-visible { outline: 2px solid var(--primary, #0071e3); outline-offset: 2px; }
.rpt-row-selected { background: rgba(0,113,227,.05); }

/* ── Expandable reason ── */
.rpt-reason-cell { max-width: 360px; }
.rpt-reason-full { white-space: normal; word-break: break-word; line-height: 1.45; }
.rpt-reason-toggle {
  margin-top: 4px; padding: 0; border: none; background: none;
  color: var(--primary, #0071e3); font-size: .72rem; font-weight: 600; cursor: pointer;
}
.rpt-reason-toggle:hover { text-decoration: underline; }
.rpt-reason-toggle:focus-visible { outline: 2px solid var(--primary, #0071e3); outline-offset: 2px; border-radius: 4px; }

/* ── Pager ── */
.rpt-pager {
  display: flex; align-items: center; justify-content: center; gap: var(--space-4);
  margin-top: var(--space-4);
}
.rpt-pager-info { font-size: .76rem; color: var(--muted); }
.rpt-loadmore {
  min-height: 36px; padding: 6px 18px;
  border: 1px solid var(--border); border-radius: 100px;
  background: var(--surface, #fff); color: var(--text, #1d1d1f);
  font-size: .82rem; font-weight: 600; cursor: pointer;
  transition: background .2s, border-color .2s, transform .2s cubic-bezier(.2,1,.4,1);
}
.rpt-loadmore:hover { border-color: var(--primary, #0071e3); }
.rpt-loadmore:active { transform: scale(.97); }
.rpt-loadmore:focus-visible { outline: 2px solid var(--primary, #0071e3); outline-offset: 2px; }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .status-pending::before { animation: none; }
  .rpt-chip, .rpt-loadmore { transition: none; }
  .rpt-chip:active, .rpt-loadmore:active { transform: none; }
  .rpt-bulkbar { animation: none; }
}

/* ── Dark ── */
.dark .status-pending { background: rgba(255,159,10,.12); color: #ffb340; }
.dark .status-resolved { background: rgba(33,150,83,.12); }
.dark .status-dismissed { background: rgba(255,255,255,.06); }
.dark .rpt-open-badge { background: rgba(255,159,10,.12); color: #ffb340; }
.dark .rpt-chip { background: rgba(255,255,255,.04); }
.dark .rpt-chip-count { background: rgba(255,255,255,.1); }
.dark .rpt-chip.active .rpt-chip-count { background: rgba(255,255,255,.25); }
.dark .rpt-bulkbar { background: rgba(0,113,227,.12); }
.dark .rpt-row-selected { background: rgba(0,113,227,.1); }
.dark .rpt-loadmore { background: rgba(255,255,255,.04); }
</style>
