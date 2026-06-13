<template>
  <div>
    <h1>Quản lý Users</h1>

    <div class="admin-toolbar">
      <input v-model="search" class="input" placeholder="Tìm user (SĐT, tên)…" @input="debounceFetch" />
    </div>

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
            <select :value="u.role" class="input" style="padding: 4px 8px; min-height: auto; font-size: .82rem" @change="changeRole(u.id, ($event.target as HTMLSelectElement).value)">
              <option value="user">user</option>
              <option value="moderator">moderator</option>
              <option value="admin">admin</option>
            </select>
          </td>
          <td>
            <span :style="{ color: u.is_banned ? '#D94F3D' : 'var(--primary)' }">
              {{ u.is_banned ? 'Bị cấm' : 'Hoạt động' }}
            </span>
          </td>
          <td style="font-size: .82rem; color: var(--muted)">{{ formatDate(u.created_at) }}</td>
          <td class="admin-actions">
            <button v-if="u.is_banned" class="btn-success" @click="unban(u.id)">Mở cấm</button>
            <button v-else class="btn-danger" @click="ban(u.id)">Cấm</button>
          </td>
        </tr>
        <tr v-if="!users.length">
          <td colspan="6" style="text-align: center; padding: 20px; color: var(--muted)">Không có user nào.</td>
        </tr>
      </tbody>
    </table>
    </div>

    <div class="admin-pagination">
      <button :disabled="page <= 1" @click="page--; fetchUsers()">← Trước</button>
      <span style="padding: 6px 10px; font-size: .85rem">Trang {{ page }}</span>
      <button :disabled="users.length < limit" @click="page++; fetchUsers()">Sau →</button>
    </div>
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

let debounceTimer: ReturnType<typeof setTimeout> | null = null
function debounceFetch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchUsers(true), 300)
}
onUnmounted(() => { if (debounceTimer) clearTimeout(debounceTimer) })

async function fetchUsers(reset = false) {
  if (reset) page.value = 1
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String((page.value - 1) * limit) })
    if (search.value) params.set('q', search.value)
    const res = await $fetch<any>(`/admin-api/users?${params}`, { headers: authHeaders() })
    users.value = res.users || res || []
  } catch { /* ignore */ }
}

async function ban(id: string) {
  if (!confirm('Cấm user này?')) return
  try {
    await $fetch(`/admin-api/users/${id}/ban`, { method: 'POST', headers: authHeaders() })
    showToast('Đã cấm user', 'success')
    await fetchUsers()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi cấm user', 'error')
  }
}

async function unban(id: string) {
  try {
    await $fetch(`/admin-api/users/${id}/unban`, { method: 'POST', headers: authHeaders() })
    showToast('Đã mở cấm user', 'success')
    await fetchUsers()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi mở cấm user', 'error')
  }
}

async function changeRole(id: string, role: string) {
  if (!confirm(`Đổi role thành "${role}"?`)) return
  try {
    await $fetch(`/admin-api/users/${id}/role`, { method: 'POST', headers: authHeaders(), body: { role } })
    showToast(`Đã đổi role thành ${role}`, 'success')
    await fetchUsers()
  } catch (e: any) {
    showToast(e.data?.detail || 'Lỗi khi đổi role', 'error')
  }
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchUsers())
</script>
