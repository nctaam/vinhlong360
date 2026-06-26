<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Chưa phân loại xã/phường</h1>
        <p class="cpl-subtitle">Entity nội dung chưa gán xã. Gán đúng để xuất hiện ở trang xã/phường + danh mục khu vực.</p>
      </div>
      <div class="admin-head-actions">
        <span v-if="total" class="cpl-progress-pill" role="status" aria-label="Tiến độ phân loại">
          {{ filtered.length }} / {{ total }} cần gán
        </span>
        <button type="button" class="admin-refresh" :disabled="loading" @click="load"><span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới</button>
      </div>
    </div>

    <div class="cpl-toolbar">
      <input v-model="q" class="input" placeholder="Tìm theo tên..." aria-label="Tìm theo tên" @keyup.enter="load" />
      <button type="button" class="btn btn-secondary btn-sm" @click="load">Tìm</button>
      <select v-model="typeFilter" class="cpl-type-filter input" aria-label="Lọc theo loại">
        <option value="">Tất cả loại ({{ items.length }})</option>
        <option v-for="t in typeOptions" :key="t.type" :value="t.type">{{ t.type }} ({{ t.count }})</option>
      </select>
      <span v-if="total" class="cpl-total-badge">{{ total }} chưa phân loại</span>
      <span v-if="typeFilter || q" class="cpl-total-badge cpl-filter-badge">{{ filtered.length }} khớp bộ lọc</span>
    </div>

    <div v-if="loading" class="admin-loading" role="status" aria-label="Đang tải entity chưa phân loại"><div class="spinner"></div></div>
    <template v-else>
      <!-- Bulk action bar -->
      <div v-if="selectedIds.length" class="cpl-bulk-bar" role="region" aria-label="Gán hàng loạt">
        <span class="cpl-bulk-count">{{ selectedIds.length }} / {{ filtered.length }} đã chọn</span>
        <select v-model="bulkPick" class="cpl-place-select" aria-label="Chọn xã/phường để gán hàng loạt" :disabled="bulkBusy">
          <option value="">— Chọn xã/phường —</option>
          <optgroup v-for="g in wardGroups" :key="g.area" :label="g.label">
            <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
          </optgroup>
        </select>
        <button type="button" class="btn btn-primary btn-sm cpl-bulk-apply" :disabled="!bulkPick || bulkBusy" @click="assignBulk">
          {{ bulkBusy ? `Đang gán ${bulkProgress.done}/${bulkProgress.total}...` : `Gán ${selectedIds.length} entity` }}
          <span v-if="bulkBusy && bulkProgress.total" class="cpl-bulk-progress" :style="{ width: (bulkProgress.done / bulkProgress.total * 100) + '%' }" aria-hidden="true"></span>
        </button>
        <button type="button" class="btn btn-secondary btn-sm cpl-bulk-clear" :disabled="bulkBusy" @click="clearSelection">Bỏ chọn</button>
      </div>

      <div v-if="items.length && filtered.length" class="admin-table-wrap cpl-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th class="cpl-check-col">
                <input
                  type="checkbox"
                  class="cpl-checkbox"
                  :checked="allPageSelected"
                  :indeterminate.prop="somePageSelected && !allPageSelected"
                  :aria-label="allPageSelected ? 'Bỏ chọn tất cả trên trang' : 'Chọn tất cả trên trang'"
                  @change="togglePage"
                />
              </th>
              <th scope="col">Entity</th>
              <th scope="col">Loại</th>
              <th scope="col">Gán xã/phường</th>
              <th scope="col"><span class="sr-only">Thao tác</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in pageItems" :key="e.id" :class="{ 'cpl-row-selected': selected[e.id] }">
              <td class="cpl-check-col">
                <input
                  type="checkbox"
                  class="cpl-checkbox"
                  :checked="!!selected[e.id]"
                  :disabled="bulkBusy"
                  :aria-label="`Chọn ${e.name}`"
                  @change="toggleOne(e.id)"
                />
              </td>
              <td>
                <strong>{{ e.name }}</strong>
                <small v-if="e.summary" class="cpl-summary">{{ e.summary }}</small>
              </td>
              <td><span class="cpl-type-badge" :style="typeBadgeStyle(e.type)">{{ e.type }}</span></td>
              <td>
                <select v-model="pick[e.id]" class="cpl-place-select" :aria-label="`Chọn xã/phường cho ${e.name}`">
                  <option value="">— Chọn —</option>
                  <optgroup v-for="g in wardGroups" :key="g.area" :label="g.label">
                    <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
                  </optgroup>
                </select>
              </td>
              <td>
                <button type="button" class="btn btn-primary btn-sm" :disabled="!pick[e.id] || busy[e.id] || bulkBusy" @click="assign(e)">
                  {{ busy[e.id] ? '...' : 'Gán' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filtered.length > pageItems.length" class="cpl-loadmore">
          <div class="cpl-loadmore-track" role="progressbar" :aria-valuenow="loadPct" aria-valuemin="0" aria-valuemax="100" :aria-label="`Đã hiển thị ${pageItems.length} trên ${filtered.length}`">
            <div class="cpl-loadmore-fill" :style="{ width: loadPct + '%' }"></div>
          </div>
          <span class="cpl-loadmore-info">Hiển thị {{ pageItems.length }} / {{ filtered.length }} ({{ loadPct }}%)</span>
          <button type="button" class="btn btn-secondary btn-sm" @click="showMore">Tải thêm</button>
        </div>
      </div>

      <div v-else-if="items.length && !filtered.length" class="admin-empty-state cpl-empty-miss">
        <div class="admin-empty-state-icon">&#128269;</div>
        <div class="admin-empty-state-text">Không tìm thấy</div>
        <div class="admin-empty-state-hint">Không có entity nào khớp bộ lọc. Thử bỏ bộ lọc hoặc tìm kiếm lại.</div>
      </div>

      <div v-else class="admin-empty-state cpl-empty-done">
        <div class="admin-empty-state-icon">&#10004;</div>
        <div class="admin-empty-state-text">Hoàn tất</div>
        <div class="admin-empty-state-hint">Không có entity nào chưa phân loại. Quay lại danh sách entities để xem toàn bộ.</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { Place, Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']
const PAGE_SIZE = 50

const q = ref('')
const items = ref<Entity[]>([])
const total = ref(0)
const loading = ref(true)
const pick = ref<Record<string, string>>({})
const busy = ref<Record<string, boolean>>({})

// Filter / pagination state
const typeFilter = ref('')
const visibleCount = ref(PAGE_SIZE)

// Bulk-assign state
const selected = ref<Record<string, boolean>>({})
const bulkPick = ref('')
const bulkBusy = ref(false)
const bulkProgress = ref({ done: 0, total: 0 })

const { data: places } = await useAsyncData('cpl-places', () => apiFetch<Place[]>('/api/places').catch(() => []))
const wardGroups = computed(() => {
  const wards = (places.value || []).filter((p: Entity) => ADMIN_LEVELS.includes(p.level))
  return Object.keys(AREA_META).map(area => ({
    area, label: AREA_META[area].name,
    wards: wards.filter((w: Entity) => w.area === area).sort((a: Entity, b: Entity) => a.name.localeCompare(b.name, 'vi')),
  })).filter(g => g.wards.length)
})

// Distinct entity types over the loaded list, with counts
const typeOptions = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of items.value) {
    const t = e.type || '—'
    counts[t] = (counts[t] || 0) + 1
  }
  return Object.keys(counts).sort((a, b) => a.localeCompare(b, 'vi')).map(type => ({ type, count: counts[type] }))
})

// Client-side filter (over the already-loaded list)
const filtered = computed(() => {
  if (!typeFilter.value) return items.value
  return items.value.filter(e => (e.type || '—') === typeFilter.value)
})

// Client-side pagination ("load more")
const pageItems = computed(() => filtered.value.slice(0, visibleCount.value))
const loadPct = computed(() => filtered.value.length ? Math.round((pageItems.value.length / filtered.value.length) * 100) : 0)

// Semantic type→color mapping for badges (fallback to neutral gray).
const TYPE_COLORS: Record<string, string> = {
  'Điểm đến': '#3478F6', 'Du lịch': '#3478F6',
  'Dịch vụ': '#AF52DE',
  'Ẩm thực': '#FF9F0A', 'Món ăn': '#FF9F0A', 'Đặc sản': '#FF9F0A',
  'Sản phẩm': '#34C759', 'OCOP': '#34C759',
  'Lưu trú': '#5AC8FA',
  'Sự kiện': '#FF375F', 'Lễ hội': '#FF375F',
  'Làng nghề': '#A2845E',
}
function typeBadgeStyle(type?: string) {
  const c = (type && TYPE_COLORS[type])
  if (!c) return {}
  return { background: c + '1f', color: c }
}

// Selection helpers (selection is tracked by id, survives pagination)
const selectedIds = computed(() => Object.keys(selected.value).filter(id => selected.value[id]))
const allPageSelected = computed(() => pageItems.value.length > 0 && pageItems.value.every(e => selected.value[e.id]))
const somePageSelected = computed(() => pageItems.value.some(e => selected.value[e.id]))

watch([typeFilter, q], () => { visibleCount.value = PAGE_SIZE })

function showMore() {
  visibleCount.value += PAGE_SIZE
}

function toggleOne(id: string) {
  selected.value = { ...selected.value, [id]: !selected.value[id] }
}
function togglePage() {
  const next = { ...selected.value }
  const target = !allPageSelected.value
  for (const e of pageItems.value) next[e.id] = target
  selected.value = next
}
function clearSelection() {
  selected.value = {}
}

async function load() {
  loading.value = true
  try {
    const r = await $fetch<Record<string, unknown>>(`/admin-api/unclassified?limit=200&q=${encodeURIComponent(q.value)}`, { headers: authHeaders() })
    items.value = (r.entities || []) as Entity[]
    total.value = (r.total || 0) as number
    // Reset transient view state on reload
    selected.value = {}
    bulkPick.value = ''
    visibleCount.value = PAGE_SIZE
    // Drop type filter if it no longer matches anything
    if (typeFilter.value && !items.value.some(e => (e.type || '—') === typeFilter.value)) typeFilter.value = ''
  } catch { showToast('Không tải được danh sách', 'error') } finally {
    loading.value = false
  }
}

async function assign(e: Entity) {
  const pid = pick.value[e.id]
  if (!pid) return
  busy.value = { ...busy.value, [e.id]: true }
  try {
    await $fetch(`/admin-api/entities/${e.id}/place`, { method: 'POST', headers: authHeaders(), body: { place_id: pid } })
    removeItem(e.id)
    showToast(`Đã gán ${e.name}`, 'success')
  } catch (err: unknown) {
    showToast(getErrorDetail(err, 'Gán thất bại'), 'error')
  } finally {
    busy.value = { ...busy.value, [e.id]: false }
  }
}

// Bulk assign: loop the existing single-item endpoint (no bulk endpoint exists yet).
async function assignBulk() {
  if (bulkBusy.value) return
  const pid = bulkPick.value
  const ids = selectedIds.value
  if (!pid || !ids.length) return
  bulkBusy.value = true
  bulkProgress.value = { done: 0, total: ids.length }
  let ok = 0
  let fail = 0
  for (const id of ids) {
    const e = items.value.find(x => x.id === id)
    if (!e) { bulkProgress.value = { ...bulkProgress.value, done: bulkProgress.value.done + 1 }; continue }
    try {
      await $fetch(`/admin-api/entities/${id}/place`, { method: 'POST', headers: authHeaders(), body: { place_id: pid } })
      removeItem(id)
      ok++
    } catch {
      fail++
    }
    bulkProgress.value = { ...bulkProgress.value, done: bulkProgress.value.done + 1 }
  }
  bulkBusy.value = false
  bulkPick.value = ''
  bulkProgress.value = { done: 0, total: 0 }
  if (fail === 0) showToast(`Đã gán ${ok} entity`, 'success')
  else if (ok === 0) showToast(`Gán thất bại (${fail})`, 'error')
  else showToast(`Đã gán ${ok}, thất bại ${fail}`, 'warning')
}

// Remove an assigned item from the list + all transient state.
function removeItem(id: string) {
  items.value = items.value.filter(x => x.id !== id)
  total.value = Math.max(0, total.value - 1)
  if (selected.value[id]) {
    const next = { ...selected.value }
    delete next[id]
    selected.value = next
  }
}

onMounted(load)
</script>

<style scoped>
.cpl-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; max-width: 500px; }

/* ── Head row progress pill ── */
.admin-head-actions { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.cpl-progress-pill {
  display: inline-flex; align-items: center; padding: 3px 11px;
  border-radius: 100px; font-size: .75rem; font-weight: 600;
  background: rgba(120,120,128,.1); color: var(--muted);
  white-space: nowrap;
}

.cpl-toolbar {
  display: flex; gap: var(--space-3); align-items: center;
  margin-bottom: var(--space-4); flex-wrap: wrap;
}
.cpl-toolbar .input { max-width: 280px; }
.cpl-type-filter { max-width: 220px; min-height: 44px; cursor: pointer; }

.cpl-total-badge {
  display: inline-flex; align-items: center; padding: 2px 10px;
  border-radius: 100px; font-size: .75rem; font-weight: 600;
  background: rgba(255,159,10,.08); color: #c67a00;
}
.cpl-filter-badge { background: rgba(33,150,83,.08); color: #1a7a44; }

.cpl-summary { display: block; color: var(--muted); margin-top: 2px; font-size: .78rem; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.cpl-type-badge {
  display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-size: .72rem; font-weight: 600;
  background: rgba(142,142,147,.08); color: var(--muted);
}

.cpl-place-select {
  max-width: 220px; padding: 4px 8px; min-height: 44px;
  font-size: .82rem; border: .5px solid var(--line); border-radius: 8px;
  background: var(--bg); color: var(--ink); cursor: pointer;
  transition: border-color .2s cubic-bezier(.2,1,.4,1), box-shadow .2s;
}
.cpl-place-select:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 0 2px rgba(33,150,83,.1); }
.cpl-place-select:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; box-shadow: none; }

/* ── Bulk bar ── */
.cpl-bulk-bar {
  display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap;
  margin-bottom: var(--space-3); padding: var(--space-2) var(--space-3);
  background: rgba(33,150,83,.06);
  border: .5px solid rgba(33,150,83,.2); border-top: 1px solid rgba(33,150,83,.3);
  border-radius: 12px;
}
.cpl-bulk-count { font-size: .82rem; font-weight: 600; color: var(--primary, #219653); }
.cpl-bulk-clear { margin-left: auto; }

/* Progress bar along bottom edge of the bulk-apply button */
.cpl-bulk-apply { position: relative; overflow: hidden; }
.cpl-bulk-progress {
  position: absolute; left: 0; bottom: 0; height: 2px;
  background: rgba(255,255,255,.85); border-radius: 0 1px 1px 0;
  transition: width .2s cubic-bezier(.2,1,.4,1);
}

/* ── Checkboxes ── */
.cpl-check-col { width: 44px; text-align: center; }
.cpl-checkbox {
  width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary, #219653);
  /* expand hit area to WCAG 2.5.5 (44px) without growing the visual box */
  padding: 13px; margin: -13px; box-sizing: content-box;
}
.cpl-checkbox:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; border-radius: 3px; }
.cpl-row-selected { background: rgba(33,150,83,.05); }

/* ── Row density + scan-friendly hover (page-scoped; does not touch shared .admin-table rules) ── */
.cpl-table-wrap :deep(.admin-table) td { padding-top: var(--space-2); padding-bottom: var(--space-2); }
.cpl-table-wrap :deep(.admin-table) td strong { line-height: 1.3; }
.cpl-table-wrap :deep(.admin-table) tbody tr td:first-child { position: relative; }
.cpl-table-wrap :deep(.admin-table) tbody tr:hover td:first-child::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  background: var(--primary, #219653);
}

/* ── Load more ── */
.cpl-loadmore {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-3); margin-top: var(--space-2);
}
.cpl-loadmore-track {
  width: 100%; max-width: 360px; height: 4px; border-radius: 100px;
  background: rgba(120,120,128,.16); overflow: hidden;
}
.cpl-loadmore-fill {
  height: 100%; border-radius: 100px; background: var(--primary, #219653);
  transition: width .25s cubic-bezier(.2,1,.4,1);
}
.cpl-loadmore-info { font-size: .8rem; color: var(--muted); }

/* ── Empty states (use shared .admin-empty-state; tint icon by intent) ── */
.cpl-empty-done .admin-empty-state-icon { color: var(--primary, #219653); opacity: .85; }
.cpl-empty-miss .admin-empty-state-icon { color: var(--muted); }

/* ── Responsive: reflow toolbar on narrow viewports ── */
@media (max-width: 600px) {
  .cpl-toolbar { display: grid; grid-template-columns: 1fr auto; align-items: stretch; }
  .cpl-toolbar .input { max-width: none; grid-column: 1 / 2; }
  .cpl-toolbar .btn { grid-column: 2 / 3; }
  .cpl-type-filter { grid-column: 1 / -1; max-width: none; }
  .cpl-total-badge, .cpl-filter-badge { grid-column: 1 / -1; }
  .cpl-bulk-clear { margin-left: 0; }
}

/* ── Dark ── */
.dark .cpl-progress-pill { background: rgba(255,255,255,.08); }
.dark .cpl-total-badge { background: rgba(255,159,10,.12); color: #ffb340; }
.dark .cpl-filter-badge { background: rgba(33,150,83,.14); color: #4ade80; }
.dark .cpl-type-badge { background: rgba(255,255,255,.06); }
.dark .cpl-place-select { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .cpl-bulk-bar { background: rgba(33,150,83,.1); border-color: rgba(33,150,83,.25); border-top-color: rgba(33,150,83,.35); }
.dark .cpl-bulk-count { color: #4ade80; }
.dark .cpl-bulk-progress { background: rgba(255,255,255,.7); }
.dark .cpl-loadmore-track { background: rgba(255,255,255,.1); }
.dark .cpl-row-selected { background: rgba(33,150,83,.08); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .cpl-place-select, .cpl-bulk-progress, .cpl-loadmore-fill { transition: none; }
}
</style>
