<template>
  <div>
    <div class="admin-head-row">
      <h1>Quản lý Users</h1>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchUsers()">🔄 Làm mới</button>
    </div>

    <div class="admin-toolbar">
      <input v-model="search" class="input" placeholder="Tìm user (SĐT, tên)…" aria-label="Tìm user" @input="debounceFetch" />
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Tên</th>
            <th>SĐT</th>
            <th>Role</th>
            <th>Trạng thái</th>
            <th>Ngày tạo</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td><strong>{{ u.display_name || '—' }}</strong></td>
            <td>{{ u.phone }}</td>
            <td>
              <select :value="u.role" class="input admin-select-inline" :disabled="acting === u.id" :aria-label="`Chọn role cho ${u.display_name || u.phone}`" @change="changeRole(u.id, ($event.target as HTMLSelectElement).value)">
                <option value="user">user</option>
                <option value="moderator">moderator</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td>
              <span :class="u.is_banned ? 'status-banned' : 'status-active'">
                {{ u.is_banned ? 'Bị cấm' : 'Hoạt động' }}
              </span>
            </td>
            <td class="admin-td-muted"><time :datetime="u.created_at">{{ formatDate(u.created_at) }}</time></td>
            <td class="admin-actions">
              <button type="button" v-if="u.is_banned" class="btn-success" :disabled="acting === u.id" @click="unban(u.id)">Mở cấm</button>
              <button type="button" v-else class="btn-danger" :disabled="acting === u.id" @click="ban(u.id)">Cấm</button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="6" class="admin-empty-row">Không có user nào.</td>
          </tr>
        </tbody>
      </table>
      </div>

      <nav class="admin-pagination" role="navigation" aria-label="Phân trang">
        <button type="button" :disabled="page <= 1" @click="page--; fetchUsers()">← Trước</button>
        <span class="admin-page-info">Trang {{ page }}</span>
        <button type="button" :disabled="users.length < limit" @click="page++; fetchUsers()">Sau →</button>
      </nav>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const search = ref('')
const page = ref(1)
const limit = 30
const users = ref<any[]>([])
const loading = ref(true)
const acting = ref<string | null>(null)

let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debounceFetch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchUsers(true), 300)
}
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function fetchUsers(reset = false) {
  if (reset) page.value = 1
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String((page.value - 1) * limit) })
    if (search.value) params.set('q', search.value)
    const res = await $fetch<any>(`/admin-api/users?${params}`, { headers: authHeaders() })
    users.value = res.users || res || []
  } catch {
    showToast('Không thể tải danh sách user', 'error')
  }
  loading.value = false
}

async function ban(id: string) {
  if (!confirm('Cấm user này?')) return
  acting.value = id
  try {
    await $fetch(`/admin-api/users/${id}/ban`, { method: 'POST', headers: authHeaders() })
    showToast('Đã cấm user', 'success')
    await fetchUsers()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi cấm user', 'error')
  }
  acting.value = null
}

async function unban(id: string) {
  if (!confirm('Mở cấm user này?')) return
  acting.value = id
  try {
    await $fetch(`/admin-api/users/${id}/unban`, { method: 'POST', headers: authHeaders() })
    showToast('Đã mở cấm user', 'success')
    await fetchUsers()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi mở cấm user', 'error')
  }
  acting.value = null
}

async function changeRole(id: string, role: string) {
  if (!confirm(`Đổi role thành "${role}"?`)) return
  acting.value = id
  try {
    await $fetch(`/admin-api/users/${id}/role`, { method: 'POST', headers: authHeaders(), body: { role } })
    showToast(`Đã đổi role thành ${role}`, 'success')
    await fetchUsers()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi đổi role', 'error')
  }
  acting.value = null
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchUsers())
</script>

<style scoped>
.status-active { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full, 999px); font-size: var(--text-xs); font-weight: var(--weight-semibold); background: rgba(46, 125, 91, .12); color: var(--secondary-fg); }
.status-banned { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full, 999px); font-size: var(--text-xs); font-weight: var(--weight-semibold); background: rgba(220, 38, 38, .1); color: var(--error); }
.admin-select-inline { padding: var(--space-1) var(--space-2); font-size: var(--text-xs); min-height: 36px; border-radius: var(--radius-md); transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo); }
.admin-select-inline:focus-visible { border-color: var(--primary-fg); box-shadow: 0 0 0 2px rgba(var(--primary-rgb), .1); }

</style>
