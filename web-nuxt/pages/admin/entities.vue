<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Quản lý Entities</h1>
        <p class="ent-subtitle">{{ entities.length ? `${entities.length} kết quả` : '' }}</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchEntities()">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div class="admin-toolbar">
      <input v-model="search" class="input" placeholder="Tìm entity…" aria-label="Tìm entity" @input="debounceFetch" />
      <select v-model="typeFilter" class="input admin-select-filter" @change="fetchEntities(true)">
        <option value="">Tất cả loại</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <button type="button" class="btn btn-primary" @click="openCreate">+ Tạo mới</button>
    </div>

    <div v-if="selected.size" class="bulk-bar">
      <span>Đã chọn {{ selected.size }}</span>
      <button type="button" class="btn-danger" :disabled="bulkBusy" @click="bulkDelete">Xóa đã chọn</button>
      <button type="button" class="btn btn-outline btn-sm" @click="selected = new Set()">Bỏ chọn</button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th class="admin-th-check"><input type="checkbox" :checked="allSelected" @change="toggleAll" aria-label="Chọn tất cả" /></th>
            <th>ID</th>
            <th>Tên</th>
            <th>Loại</th>
            <th>Địa điểm</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in entities" :key="e.id" :class="{ 'row-selected': selected.has(e.id) }">
            <td><input type="checkbox" :checked="selected.has(e.id)" @change="toggleSel(e.id)" :aria-label="`Chọn ${e.name}`" /></td>
            <td class="admin-td-id">{{ e.id }}</td>
            <td>
              <div class="ent-name-cell">
                <div class="ent-thumb" v-if="e.images?.length">
                  <img :src="e.images[0]" :alt="e.name" width="32" height="32" loading="lazy" @error="(ev) => ((ev.target as HTMLImageElement).style.display = 'none')" />
                </div>
                <div class="ent-thumb ent-thumb-empty" v-else>&#128247;</div>
                <strong>{{ e.name }}</strong>
              </div>
            </td>
            <td><span class="type-badge" :data-type="e.type">{{ e.type }}</span></td>
            <td class="admin-td-muted">{{ e.place_name || '—' }}</td>
            <td class="admin-actions">
              <button type="button" class="btn-success" @click="openEdit(e)">Sửa</button>
              <button type="button" class="btn-danger" :disabled="acting === e.id" @click="deleteEntity(e.id)">Xóa</button>
            </td>
          </tr>
          <tr v-if="!entities.length">
            <td colspan="6" class="admin-empty-row">
              <div class="ent-empty">
                <span class="ent-empty-icon">&#128269;</span>
                <span>Không tìm thấy entity nào.</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <nav class="admin-pagination" role="navigation" aria-label="Phân trang">
        <button type="button" :disabled="page <= 1" @click="page--; fetchEntities()">← Trước</button>
        <span class="admin-page-info">Trang {{ page }}</span>
        <button type="button" :disabled="entities.length < limit" @click="page++; fetchEntities()">Sau →</button>
      </nav>
    </template>

    <!-- Edit/Create Modal -->
    <Transition name="modal-fade">
    <div v-if="showModal" class="modal-overlay show" role="dialog" aria-modal="true" :aria-label="editingEntity ? 'Sửa Entity' : 'Tạo Entity'" @click.self="showModal = false" @keyup.escape="showModal = false">
      <div class="modal admin-modal-md">
        <h2>{{ editingEntity ? 'Sửa Entity' : 'Tạo Entity' }}</h2>
        <div class="admin-form-col">
          <input v-model="form.id" class="input" placeholder="ID (slug)" aria-label="ID (slug)" :disabled="!!editingEntity" />
          <input v-model="form.name" class="input" placeholder="Tên" aria-label="Tên entity" />
          <select v-model="form.type" class="input" aria-label="Loại entity">
            <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
          </select>
          <input v-model="form.placeId" class="input" placeholder="Place ID (xã/phường)" aria-label="Place ID" />
          <textarea v-model="form.summary" class="input admin-textarea" placeholder="Tóm tắt" aria-label="Tóm tắt" rows="3"></textarea>
          <!-- Quản lý ảnh (chỉ khi sửa) -->
          <div v-if="editingEntity" class="img-mgr">
            <strong class="admin-label">Ảnh ({{ (form.images || []).length }}/10)</strong>
            <div v-for="(img, i) in (form.images || [])" :key="i" class="img-row">
              <img :src="img" :alt="`Ảnh ${i + 1}`" class="img-thumb" width="48" height="48" loading="lazy" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.3')" />
              <span class="img-url">{{ img }}</span>
              <button type="button" class="btn-danger btn-sm" @click="removeImage(i)">Xóa</button>
            </div>
            <div class="admin-inline-add">
              <input v-model="newImage" class="input" placeholder="https://… (chỉ nguồn cấp phép)" aria-label="URL ảnh mới" @keyup.enter="addImage" />
              <button type="button" class="btn btn-secondary btn-sm" :disabled="!newImage.trim()" @click="addImage">Thêm ảnh</button>
            </div>
            <div class="admin-inline-add">
              <label class="btn btn-outline btn-sm" style="cursor:pointer; margin:0">
                {{ uploadingImg ? 'Đang tải & tối ưu…' : '📷 Tải ảnh lên (tự nén WebP)' }}
                <input type="file" accept="image/*" class="sr-only" :disabled="uploadingImg" @change="uploadImageFile" />
              </label>
            </div>
          </div>

          <!-- Quản lý quan hệ (chỉ khi sửa) -->
          <div v-if="editingEntity" class="img-mgr">
            <strong class="admin-label">Quan hệ ({{ rels.length }})</strong>
            <div v-for="(r, i) in rels" :key="i" class="img-row">
              <span class="img-url">{{ r.type }} → {{ r.target_name || r.source_name || r.to_id }}</span>
              <button type="button" class="btn-danger btn-sm" @click="removeRel(r)">Xóa</button>
            </div>
            <div class="admin-inline-add">
              <select v-model="newRel.type" class="input" aria-label="Loại quan hệ" style="flex:0 0 130px">
                <option v-for="t in relTypes" :key="t" :value="t">{{ t }}</option>
              </select>
              <input v-model="newRel.to_id" class="input" placeholder="ID entity đích" aria-label="ID entity đích" @keyup.enter="addRel" />
              <button type="button" class="btn btn-secondary btn-sm" :disabled="!newRel.to_id.trim()" @click="addRel">Thêm</button>
            </div>
          </div>
        </div>
        <div class="admin-modal-actions">
          <button type="button" class="btn btn-outline" @click="showModal = false">Hủy</button>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="saveEntity">
            {{ saving ? 'Đang lưu…' : (editingEntity ? 'Cập nhật' : 'Tạo') }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const types = Object.keys(TYPE_META)
const search = ref('')
const typeFilter = ref('')
const page = ref(1)
const limit = 30
const entities = ref<Entity[]>([])
const showModal = ref(false)
const editingEntity = ref<Record<string, unknown> | null>(null)
const form = ref<Record<string, unknown>>({})
const selected = ref<Set<string>>(new Set())
const loading = ref(true)
const acting = ref<string | null>(null)
const saving = ref(false)
const bulkBusy = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debounceFetch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchEntities(true), 300)
}
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function fetchEntities(reset = false) {
  if (reset) page.value = 1
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String((page.value - 1) * limit) })
    if (search.value) params.set('q', search.value)
    if (typeFilter.value) params.set('type', typeFilter.value)
    const res = await $fetch<Record<string, unknown>>(`/admin-api/entities?${params}`, { headers: authHeaders() })
    entities.value = res.entities || res || []
  } catch {
    showToast('Không thể tải danh sách entity', 'error')
  }
  loading.value = false
}

function openCreate() {
  editingEntity.value = null
  form.value = { id: '', name: '', type: 'experience', placeId: '', summary: '', images: [] }
  newImage.value = ''
  showModal.value = true
}

function openEdit(e: Entity) {
  editingEntity.value = e
  form.value = { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '',
                 images: Array.isArray(e.images) ? [...e.images] : [] }
  newImage.value = ''
  newRel.value = { to_id: '', type: 'related_to' }
  fetchRels(e.id)
  showModal.value = true
}

// ── Quản lý quan hệ ──
const relTypes = ['related_to', 'near', 'produced_in', 'located_in', 'associated_with', 'part_of', 'hosts']
const rels = ref<Entity[]>([])
const newRel = ref<{ to_id: string; type: string }>({ to_id: '', type: 'related_to' })
async function fetchRels(id: string) {
  rels.value = []
  try {
    const r = await $fetch<Entity>(`/api/entities/${id}/relationships?limit=100`)
    rels.value = r.relationships || []
  } catch { showToast('Không tải được quan hệ', 'error') }
}
async function addRel() {
  const to = newRel.value.to_id.trim()
  if (!to || !editingEntity.value) return
  try {
    await $fetch('/admin-api/relationships', { method: 'POST', headers: authHeaders(),
      body: { from_id: form.value.id, to_id: to, type: newRel.value.type } })
    newRel.value.to_id = ''
    await fetchRels(form.value.id)
  } catch (e: unknown) { showToast(e?.data?.detail || 'Thêm quan hệ lỗi (id đích tồn tại?)', 'error') }
}
async function removeRel(r: Record<string, unknown>) {
  if (!confirm(`Xóa quan hệ "${r.type}" → ${r.target_name || r.to_id}?`)) return
  const params = new URLSearchParams({ from_id: r.from_id, to_id: r.to_id, type: r.type })
  try {
    await $fetch(`/admin-api/relationships?${params}`, { method: 'DELETE', headers: authHeaders() })
    await fetchRels(form.value.id)
  } catch { showToast('Xóa quan hệ lỗi', 'error') }
}

async function saveEntity() {
  if (!form.value.name?.trim()) { showToast('Tên không được để trống', 'error'); return }
  if (!editingEntity.value && !form.value.id?.trim()) { showToast('ID không được để trống', 'error'); return }
  saving.value = true
  try {
    if (editingEntity.value) {
      await $fetch(`/admin-api/entities/${form.value.id}`, { method: 'PUT', headers: authHeaders(), body: form.value })
      showToast('Đã cập nhật entity', 'success')
    } else {
      await $fetch('/admin-api/entities', { method: 'POST', headers: authHeaders(), body: form.value })
      showToast('Đã tạo entity mới', 'success')
    }
    showModal.value = false
    await fetchEntities()
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Lỗi khi lưu entity', 'error')
  }
  saving.value = false
}

// ── Quản lý ảnh entity (chỉ khi đang sửa) ──
const newImage = ref('')
async function addImage() {
  const url = newImage.value.trim()
  if (!url || !editingEntity.value) return
  try {
    const r = await $fetch<Record<string, unknown>>(`/admin-api/entities/${form.value.id}/images`, {
      method: 'POST', headers: authHeaders(), body: { url } })
    form.value.images = r.images || form.value.images
    newImage.value = ''
  } catch (e: unknown) { showToast(e?.data?.detail || 'Thêm ảnh lỗi', 'error') }
}
async function removeImage(idx: number) {
  if (!editingEntity.value) return
  if (!confirm('Xóa ảnh này?')) return
  try {
    const r = await $fetch<Record<string, unknown>>(`/admin-api/entities/${form.value.id}/images/${idx}`, {
      method: 'DELETE', headers: authHeaders() })
    form.value.images = r.images ?? form.value.images.filter((_: unknown, i: number) => i !== idx)
  } catch { showToast('Xóa ảnh lỗi', 'error') }
}
const uploadingImg = ref(false)
async function uploadImageFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !editingEntity.value) { return }
  uploadingImg.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const r = await $fetch<Record<string, any>>(`/admin-api/entities/${form.value.id}/images/upload`, {
      method: 'POST', headers: authHeaders(), body: fd })
    form.value.images = (r.images as string[]) || form.value.images
    showToast('Đã tải & tối ưu ảnh', 'success')
  } catch (err: any) { showToast(err?.data?.detail || 'Tải ảnh lỗi', 'error') }
  uploadingImg.value = false
  input.value = ''
}

// ── Thao tác hàng loạt ──
function toggleSel(id: string) {
  const s = new Set(selected.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selected.value = s
}
const allSelected = computed(() => entities.value.length > 0 && entities.value.every(e => selected.value.has(e.id)))
function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(entities.value.map(e => e.id))
}
async function bulkDelete() {
  const ids = [...selected.value]
  if (!ids.length || !confirm(`Xóa ${ids.length} entity đã chọn?`)) return
  bulkBusy.value = true
  try {
    const r = await $fetch<Record<string, unknown>>('/admin-api/entities/bulk-delete', { method: 'POST', headers: authHeaders(), body: ids })
    showToast(`Đã xóa ${r.count}`, 'success')
    selected.value = new Set()
    await fetchEntities()
  } catch (e: unknown) { showToast(e?.data?.detail || 'Xóa hàng loạt lỗi', 'error') }
  bulkBusy.value = false
}
async function deleteEntity(id: string) {
  if (!confirm(`Xóa entity "${id}"?`)) return
  acting.value = id
  try {
    await $fetch(`/admin-api/entities/${id}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa entity', 'success')
    await fetchEntities()
  } catch (e: unknown) {
    showToast(e.data?.detail || 'Lỗi khi xóa entity', 'error')
  }
  acting.value = null
}

onMounted(() => fetchEntities())
</script>

<style scoped>
.ent-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Entity name cell with thumbnail ── */
.ent-name-cell { display: flex; align-items: center; gap: var(--space-3); }
.ent-thumb {
  width: 32px; height: 32px; border-radius: 8px; overflow: hidden; flex-shrink: 0;
  background: var(--bg-alt);
  transition: transform .25s cubic-bezier(.2,1,.4,1), box-shadow .25s;
}
.ent-name-cell:hover .ent-thumb { transform: scale(1.08); box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.ent-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ent-thumb-empty {
  display: flex; align-items: center; justify-content: center;
  font-size: .85rem; opacity: .3;
}

/* ── Type badges ── */
.type-badge {
  display: inline-block; padding: 2px 10px; border-radius: 100px;
  font-size: .72rem; font-weight: 600; letter-spacing: .3px;
  text-transform: uppercase;
}
.type-badge[data-type="attraction"] { background: rgba(33,150,83,.1); color: #219653; }
.type-badge[data-type="dish"] { background: rgba(230,126,34,.1); color: #e67e22; }
.type-badge[data-type="product"] { background: rgba(52,120,246,.1); color: #3478F6; }
.type-badge[data-type="accommodation"] { background: rgba(175,82,222,.1); color: #AF52DE; }
.type-badge[data-type="nature"] { background: rgba(52,199,89,.1); color: #34C759; }
.type-badge[data-type="experience"] { background: rgba(255,159,10,.1); color: #c67a00; }
.type-badge[data-type="craft_village"] { background: rgba(162,132,94,.1); color: #A2845E; }
.type-badge[data-type="event"] { background: rgba(217,79,61,.1); color: #D94F3D; }
.type-badge[data-type="drink"] { background: rgba(0,199,190,.1); color: #00C7BE; }
.type-badge[data-type="place"] { background: rgba(142,142,147,.1); color: #8E8E93; }

/* ── Selected row ── */
.row-selected td { background: rgba(52,120,246,.04); transition: background .2s; }

/* ── Empty state ── */
.ent-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.ent-empty-icon { font-size: 2rem; opacity: .3; }

/* ── Bulk bar ── */
.bulk-bar {
  display: flex; align-items: center; gap: var(--space-3); margin: var(--space-3) 0;
  padding: var(--space-3) var(--space-4);
  background: rgba(52,120,246,.06); border: .5px solid rgba(52,120,246,.2);
  border-radius: 10px; font-size: .88rem; font-weight: 500;
  animation: bulk-slide-in .3s cubic-bezier(.2,1,.4,1);
}
@keyframes bulk-slide-in { from { opacity: 0; transform: translateY(-8px); } }

/* ── Image manager ── */
.img-mgr { border-top: .5px solid var(--line); padding-top: var(--space-3); margin-top: var(--space-1); }
.img-row { display: flex; align-items: center; gap: var(--space-2); margin: var(--space-2) 0; }
.img-thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; flex: 0 0 40px; }
.img-url { flex: 1; font-size: .78rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .ent-name-cell:hover .ent-thumb { transform: none; }
  .bulk-bar { animation: none; }
}

/* ── Dark mode ── */
.dark .type-badge[data-type="attraction"] { background: rgba(33,150,83,.15); }
.dark .type-badge[data-type="dish"] { background: rgba(230,126,34,.15); color: #f0943a; }
.dark .type-badge[data-type="product"] { background: rgba(52,120,246,.15); }
.dark .type-badge[data-type="accommodation"] { background: rgba(175,82,222,.15); }
.dark .type-badge[data-type="nature"] { background: rgba(52,199,89,.15); }
.dark .type-badge[data-type="experience"] { background: rgba(255,159,10,.15); color: #ffb340; }
.dark .type-badge[data-type="craft_village"] { background: rgba(162,132,94,.15); }
.dark .type-badge[data-type="event"] { background: rgba(217,79,61,.15); }
.dark .ent-name-cell:hover .ent-thumb { box-shadow: 0 2px 8px rgba(0,0,0,.3); }
.dark .row-selected td { background: rgba(52,120,246,.08); }
.dark .bulk-bar { background: rgba(52,120,246,.08); border-color: rgba(52,120,246,.15); }
</style>
