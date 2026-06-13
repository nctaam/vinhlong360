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

    <div class="admin-table-wrap">
    <table class="admin-table">
      <thead>
        <tr>
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
          <td colspan="6" style="text-align: center; padding: 20px; color: var(--muted)">Không có entity nào.</td>
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
          <input v-model="form.place_id" class="input" placeholder="Place ID" />
          <textarea v-model="form.summary" class="input" placeholder="Tóm tắt" rows="3" style="resize: vertical"></textarea>
          <input v-model.number="form.confidence" class="input" type="number" min="0" max="1" step="0.1" placeholder="Confidence (0-1)" />
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
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const types = ['experience', 'attraction', 'dish', 'product', 'accommodation', 'craft_village', 'festival', 'specialty']
const search = ref('')
const typeFilter = ref('')
const page = ref(1)
const limit = 30
const entities = ref<any[]>([])
const showModal = ref(false)
const editingEntity = ref<any>(null)
const form = ref<any>({})

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
  form.value = { id: '', name: '', type: 'experience', place_id: '', summary: '', confidence: 0.8 }
  showModal.value = true
}

function openEdit(e: any) {
  editingEntity.value = e
  form.value = { id: e.id, name: e.name, type: e.type, place_id: e.place_id || '', summary: e.summary || '', confidence: e.confidence || 0.8 }
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
