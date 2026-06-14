<template>
  <div>
    <h1>Quản lý Entities</h1>

    <div class="admin-toolbar">
      <input v-model="search" class="input" placeholder="Tìm entity…" @input="debounceFetch" />
      <select v-model="typeFilter" class="input" style="flex: 0 0 160px" @change="fetchEntities(true)">
        <option value="">Tất cả loại</option>
        <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
      </select>
      <button class="btn btn-primary" @click="openCreate">+ Tạo mới</button>
    </div>

    <div v-if="selected.size" class="bulk-bar">
      <span>Đã chọn {{ selected.size }}</span>
      <button class="btn-danger" @click="bulkDelete">Xóa đã chọn</button>
      <button class="btn-success" @click="bulkConfidence">Đặt confidence</button>
      <button class="btn btn-outline btn-sm" @click="selected = new Set()">Bỏ chọn</button>
    </div>

    <div class="admin-table-wrap">
    <table class="admin-table">
      <thead>
        <tr>
          <th style="width:28px"><input type="checkbox" :checked="allSelected" @change="toggleAll" aria-label="Chọn tất cả" /></th>
          <th>ID</th>
          <th>Tên</th>
          <th>Loại</th>
          <th>Địa điểm</th>
          <th>Confidence</th>
          <th>Thao tác</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entities" :key="e.id">
          <td><input type="checkbox" :checked="selected.has(e.id)" @change="toggleSel(e.id)" :aria-label="`Chọn ${e.name}`" /></td>
          <td style="font-size: .78rem; color: var(--muted); max-width: 120px; overflow: hidden; text-overflow: ellipsis">{{ e.id }}</td>
          <td><strong>{{ e.name }}</strong></td>
          <td>{{ e.type }}</td>
          <td>{{ e.place_name || '—' }}</td>
          <td>{{ (e.confidence * 100).toFixed(0) }}%</td>
          <td class="admin-actions">
            <button class="btn-success" @click="openEdit(e)">Sửa</button>
            <button class="btn-danger" @click="deleteEntity(e.id)">Xóa</button>
          </td>
        </tr>
        <tr v-if="!entities.length">
          <td colspan="7" style="text-align: center; padding: 20px; color: var(--muted)">Không có entity nào.</td>
        </tr>
      </tbody>
    </table>
    </div>

    <div class="admin-pagination">
      <button :disabled="page <= 1" @click="page--; fetchEntities()">← Trước</button>
      <span style="padding: 6px 10px; font-size: .85rem">Trang {{ page }}</span>
      <button :disabled="entities.length < limit" @click="page++; fetchEntities()">Sau →</button>
    </div>

    <!-- Edit/Create Modal -->
    <div v-if="showModal" class="modal-overlay" role="dialog" aria-modal="true" :aria-label="editingEntity ? 'Sửa Entity' : 'Tạo Entity'" @click.self="showModal = false" @keyup.escape="showModal = false">
      <div class="modal" style="max-width: 600px">
        <h2>{{ editingEntity ? 'Sửa Entity' : 'Tạo Entity' }}</h2>
        <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 16px">
          <input v-model="form.id" class="input" placeholder="ID (slug)" aria-label="ID (slug)" :disabled="!!editingEntity" />
          <input v-model="form.name" class="input" placeholder="Tên" aria-label="Tên entity" />
          <select v-model="form.type" class="input">
            <option v-for="t in types" :key="t" :value="t">{{ t }}</option>
          </select>
          <input v-model="form.placeId" class="input" placeholder="Place ID (xã/phường)" />
          <textarea v-model="form.summary" class="input" placeholder="Tóm tắt" rows="3" style="resize: vertical"></textarea>
          <input v-model.number="form.confidence" class="input" type="number" min="0" max="1" step="0.1" placeholder="Confidence (0-1)" />

          <!-- Quản lý ảnh (chỉ khi sửa) -->
          <div v-if="editingEntity" class="img-mgr">
            <strong style="font-size:.9rem">Ảnh ({{ (form.images || []).length }}/10)</strong>
            <div v-for="(img, i) in (form.images || [])" :key="i" class="img-row">
              <img :src="img" alt="" class="img-thumb" @error="(e) => ((e.target as HTMLImageElement).style.opacity = '.3')" />
              <span class="img-url">{{ img }}</span>
              <button class="btn-danger btn-sm" @click="removeImage(i)">Xóa</button>
            </div>
            <div style="display:flex; gap:6px; margin-top:6px">
              <input v-model="newImage" class="input" placeholder="https://… (chỉ nguồn cấp phép)" @keyup.enter="addImage" />
              <button class="btn btn-secondary btn-sm" :disabled="!newImage.trim()" @click="addImage">Thêm ảnh</button>
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px">
          <button class="btn btn-outline" @click="showModal = false">Hủy</button>
          <button class="btn btn-primary" @click="saveEntity">{{ editingEntity ? 'Cập nhật' : 'Tạo' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

// Khớp VALID_TYPES backend (trước hardcode sai: 'festival'/'specialty' không tồn tại).
const types = Object.keys(TYPE_META)
const search = ref('')
const typeFilter = ref('')
const page = ref(1)
const limit = 30
const entities = ref<any[]>([])
const showModal = ref(false)
const editingEntity = ref<any>(null)
const form = ref<any>({})
const selected = ref<Set<string>>(new Set())

let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debounceFetch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchEntities(true), 300)
}
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function fetchEntities(reset = false) {
  if (reset) page.value = 1
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String((page.value - 1) * limit) })
    if (search.value) params.set('q', search.value)
    if (typeFilter.value) params.set('type', typeFilter.value)
    const res = await $fetch<any>(`/admin-api/entities?${params}`, { headers: authHeaders() })
    entities.value = res.entities || res || []
  } catch { /* not admin */ }
}

function openCreate() {
  editingEntity.value = null
  form.value = { id: '', name: '', type: 'experience', placeId: '', summary: '', confidence: 0.8, images: [] }
  newImage.value = ''
  showModal.value = true
}

function openEdit(e: any) {
  editingEntity.value = e
  form.value = { id: e.id, name: e.name, type: e.type, placeId: e.placeId || '', summary: e.summary || '',
                 confidence: e.confidence || 0.8, images: Array.isArray(e.images) ? [...e.images] : [] }
  newImage.value = ''
  showModal.value = true
}

async function saveEntity() {
  if (!form.value.name?.trim()) { showToast('Tên không được để trống', 'error'); return }
  if (!editingEntity.value && !form.value.id?.trim()) { showToast('ID không được để trống', 'error'); return }
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
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi lưu entity', 'error')
  }
}

// ── Quản lý ảnh entity (chỉ khi đang sửa) ──
const newImage = ref('')
async function addImage() {
  const url = newImage.value.trim()
  if (!url || !editingEntity.value) return
  try {
    const r = await $fetch<any>(`/admin-api/entities/${form.value.id}/images`, {
      method: 'POST', headers: authHeaders(), body: { url } })
    form.value.images = r.images || form.value.images
    newImage.value = ''
  } catch (e: any) { showToast(e?.data?.detail || 'Thêm ảnh lỗi', 'error') }
}
async function removeImage(idx: number) {
  if (!editingEntity.value) return
  try {
    const r = await $fetch<any>(`/admin-api/entities/${form.value.id}/images/${idx}`, {
      method: 'DELETE', headers: authHeaders() })
    form.value.images = r.images ?? form.value.images.filter((_: any, i: number) => i !== idx)
  } catch { showToast('Xóa ảnh lỗi', 'error') }
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
  try {
    const r = await $fetch<any>('/admin-api/entities/bulk-delete', { method: 'POST', headers: authHeaders(), body: ids })
    showToast(`Đã xóa ${r.count}`, 'success')
    selected.value = new Set()
    await fetchEntities()
  } catch (e: any) { showToast(e?.data?.detail || 'Xóa hàng loạt lỗi', 'error') }
}
async function bulkConfidence() {
  const ids = [...selected.value]
  if (!ids.length) return
  const v = prompt('Đặt confidence (0–1) cho ' + ids.length + ' entity:')
  const c = Number(v)
  if (!v || isNaN(c) || c < 0 || c > 1) return
  try {
    const r = await $fetch<any>(`/admin-api/entities/bulk-update-confidence?confidence=${c}`, {
      method: 'POST', headers: authHeaders(), body: ids })
    showToast(`Đã cập nhật ${r.count}`, 'success')
    selected.value = new Set()
    await fetchEntities()
  } catch (e: any) { showToast(e?.data?.detail || 'Cập nhật hàng loạt lỗi', 'error') }
}

async function deleteEntity(id: string) {
  if (!confirm(`Xóa entity "${id}"?`)) return
  try {
    await $fetch(`/admin-api/entities/${id}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa entity', 'success')
    await fetchEntities()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi xóa entity', 'error')
  }
}

onMounted(() => fetchEntities())
</script>

<style scoped>
.bulk-bar { display: flex; align-items: center; gap: 10px; margin: 10px 0; padding: 8px 12px;
  background: var(--surface, #fff7ed); border: 1px solid #fed7aa; border-radius: 8px; font-size: .9rem; }
.img-mgr { border-top: 1px solid rgba(0,0,0,.1); padding-top: 10px; margin-top: 4px; }
.img-row { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
.img-thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 4px; flex: 0 0 40px; }
.img-url { flex: 1; font-size: .78rem; color: var(--muted, #888); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
