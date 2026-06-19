<template>
  <div>
    <div class="admin-head-row">
      <h1>Quản lý Lịch trình</h1>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchItineraries">🔄 Làm mới</button>
    </div>

    <div class="admin-toolbar">
      <button type="button" class="btn btn-primary" @click="openCreate">+ Tạo lịch trình</button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Khu vực</th>
              <th>Thời gian</th>
              <th>Điểm dừng</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="it in itineraries" :key="it.id">
              <td class="admin-td-id">{{ it.id }}</td>
              <td><strong>{{ it.name }}</strong></td>
              <td>{{ it.area || '—' }}</td>
              <td>{{ it.duration || '—' }}</td>
              <td>{{ it.stops?.length || 0 }}</td>
              <td class="admin-actions">
                <button type="button" class="btn-success" @click="openEdit(it)">Sửa</button>
                <button type="button" class="btn-danger" :disabled="acting === it.id" @click="deleteItinerary(it.id)">Xóa</button>
              </td>
            </tr>
            <tr v-if="!itineraries.length">
              <td colspan="6" class="admin-empty-row">Chưa có lịch trình.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Transition name="modal-fade">
    <div v-if="showModal" class="modal-overlay show" role="dialog" aria-modal="true" :aria-label="editing ? 'Sửa Lịch trình' : 'Tạo Lịch trình'" @click.self="showModal = false" @keyup.escape="showModal = false">
      <div class="modal admin-modal-md">
        <h2>{{ editing ? 'Sửa Lịch trình' : 'Tạo Lịch trình' }}</h2>
        <div class="admin-form-col">
          <input v-model="form.id" class="input" placeholder="ID (slug)" aria-label="ID (slug)" :disabled="!!editing" />
          <input v-model="form.name" class="input" placeholder="Tên lịch trình" aria-label="Tên lịch trình" />
          <input v-model="form.area" class="input" placeholder="Khu vực (vinh-long / ben-tre / tra-vinh)" aria-label="Khu vực" />
          <input v-model="form.duration" class="input" placeholder="Thời gian (VD: 1 ngày)" aria-label="Thời gian" />
          <textarea v-model="form.description" class="input admin-textarea" placeholder="Mô tả" rows="3"></textarea>
          <label class="admin-label">Stops (JSON)</label>
          <textarea v-model="stopsJson" class="input admin-textarea admin-code" rows="6"></textarea>
        </div>
        <div class="admin-modal-actions">
          <button type="button" class="btn btn-outline" @click="showModal = false">Hủy</button>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? 'Đang lưu…' : (editing ? 'Cập nhật' : 'Tạo') }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const itineraries = ref<any[]>([])
const showModal = ref(false)
const editing = ref<any>(null)
const form = ref<any>({})
const stopsJson = ref('[]')
const loading = ref(true)
const acting = ref<string | null>(null)
const saving = ref(false)

async function fetchItineraries() {
  loading.value = true
  try {
    const res = await $fetch<any>('/admin-api/itineraries', { headers: authHeaders() })
    itineraries.value = res.itineraries || res || []
  } catch {
    showToast('Không thể tải danh sách lịch trình', 'error')
  }
  loading.value = false
}

function openCreate() {
  editing.value = null
  form.value = { id: '', name: '', area: '', duration: '', description: '' }
  stopsJson.value = '[]'
  showModal.value = true
}

function openEdit(it: any) {
  editing.value = it
  form.value = { id: it.id, name: it.name, area: it.area || '', duration: it.duration || '', description: it.description || '' }
  stopsJson.value = JSON.stringify(it.stops || [], null, 2)
  showModal.value = true
}

async function save() {
  if (!form.value.name?.trim()) { showToast('Tên không được để trống', 'error'); return }
  if (!editing.value && !form.value.id?.trim()) { showToast('ID không được để trống', 'error'); return }
  let stops: any[]
  try { stops = JSON.parse(stopsJson.value) } catch { showToast('JSON stops không hợp lệ', 'error'); return }
  const body = { ...form.value, stops }
  saving.value = true
  try {
    if (editing.value) {
      await $fetch(`/admin-api/itineraries/${form.value.id}`, { method: 'PUT', headers: authHeaders(), body })
      showToast('Đã cập nhật lịch trình', 'success')
    } else {
      await $fetch('/admin-api/itineraries', { method: 'POST', headers: authHeaders(), body })
      showToast('Đã tạo lịch trình mới', 'success')
    }
    showModal.value = false
    await fetchItineraries()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi lưu lịch trình', 'error')
  }
  saving.value = false
}

async function deleteItinerary(id: string) {
  if (!confirm(`Xóa lịch trình "${id}"?`)) return
  acting.value = id
  try {
    await $fetch(`/admin-api/itineraries/${id}`, { method: 'DELETE', headers: authHeaders() })
    showToast('Đã xóa lịch trình', 'success')
    await fetchItineraries()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi xóa', 'error')
  }
  acting.value = null
}

onMounted(() => fetchItineraries())
</script>
