<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Quản lý Users</h1>
        <p class="usr-subtitle">{{ subtitle }}</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchUsers()">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
      </button>
    </div>

    <div class="admin-toolbar">
      <input v-model="search" class="input" placeholder="Tìm user (SĐT, tên)..." aria-label="Tìm user" @input="debounceFetch" />
      <select v-model="roleFilter" class="usr-filter-select" aria-label="Lọc theo role">
        <option value="all">Tất cả role</option>
        <option value="user">user</option>
        <option value="moderator">moderator</option>
        <option value="admin">admin</option>
      </select>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
      <div class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th>
              <button type="button" class="usr-sort-th" :class="sortIndicatorClass('display_name')" :aria-sort="ariaSort('display_name')" @click="toggleSort('display_name')">
                User <span class="usr-sort-arrow" aria-hidden="true">{{ sortArrow('display_name') }}</span>
              </button>
            </th>
            <th>SĐT</th>
            <th>
              <button type="button" class="usr-sort-th" :class="sortIndicatorClass('role')" :aria-sort="ariaSort('role')" @click="toggleSort('role')">
                Role <span class="usr-sort-arrow" aria-hidden="true">{{ sortArrow('role') }}</span>
              </button>
            </th>
            <th>
              <button type="button" class="usr-sort-th" :class="sortIndicatorClass('is_banned')" :aria-sort="ariaSort('is_banned')" @click="toggleSort('is_banned')">
                Trạng thái <span class="usr-sort-arrow" aria-hidden="true">{{ sortArrow('is_banned') }}</span>
              </button>
            </th>
            <th>
              <button type="button" class="usr-sort-th" :class="sortIndicatorClass('created_at')" :aria-sort="ariaSort('created_at')" @click="toggleSort('created_at')">
                Ngày tạo <span class="usr-sort-arrow" aria-hidden="true">{{ sortArrow('created_at') }}</span>
              </button>
            </th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in displayedUsers" :key="u.id">
            <td>
              <div class="usr-cell">
                <div class="usr-avatar">{{ (u.display_name || '?')[0] }}</div>
                <strong>{{ u.display_name || '—' }}</strong>
              </div>
            </td>
            <td class="admin-td-muted">{{ u.phone }}</td>
            <td>
              <select :value="u.role" class="usr-role-select" :disabled="acting === u.id" :aria-label="`Chọn role cho ${u.display_name || u.phone}`" @change="changeRole(u.id, ($event.target as HTMLSelectElement).value)">
                <option value="user">user</option>
                <option value="moderator">moderator</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td>
              <span class="usr-status" :class="u.is_banned ? 'usr-banned' : 'usr-active'">
                <span class="usr-status-dot"></span>
                {{ u.is_banned ? 'Bị cấm' : 'Hoạt động' }}
              </span>
            </td>
            <td class="admin-td-muted"><time :datetime="u.created_at">{{ formatDate(u.created_at) }}</time></td>
            <td class="admin-actions">
              <button type="button" v-if="u.is_banned" class="btn-success" :disabled="acting === u.id" @click="unban(u.id)">Mở cấm</button>
              <button type="button" v-else class="btn-danger" :disabled="acting === u.id" @click="ban(u.id)">Cấm</button>
            </td>
          </tr>
          <tr v-if="!displayedUsers.length">
            <td colspan="6" class="admin-empty-row">
              <div class="usr-empty">
                <span class="usr-empty-icon">&#128101;</span>
                <span>{{ users.length ? 'Không có user khớp bộ lọc trên trang này.' : 'Không có user nào.' }}</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <nav class="admin-pagination" role="navigation" aria-label="Phân trang">
        <button type="button" :disabled="page <= 1" @click="page--; fetchUsers()">&#8592; Trước</button>
        <span class="admin-page-info">Trang {{ page }}</span>
        <button type="button" :disabled="users.length < limit" @click="page++; fetchUsers()">Sau &#8594;</button>
      </nav>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const search = ref('')
const page = ref(1)
const limit = 30
const users = ref<Entity[]>([])
const loading = ref(true)
const acting = ref<string | null>(null)

// ── Client-side filter + sort (operates on the current page's loaded users) ──
const roleFilter = ref<'all' | 'user' | 'moderator' | 'admin'>('all')
type SortKey = 'display_name' | 'role' | 'is_banned' | 'created_at'
const sortKey = ref<SortKey>('created_at')
const sortDir = ref<'asc' | 'desc'>('desc')

const ROLE_ORDER: Record<string, number> = { user: 0, moderator: 1, admin: 2 }

const displayedUsers = computed(() => {
  let list = users.value.slice()
  if (roleFilter.value !== 'all') {
    list = list.filter(u => ((u as any).role || 'user') === roleFilter.value)
  }
  const dir = sortDir.value === 'asc' ? 1 : -1
  const key = sortKey.value
  list.sort((a: any, b: any) => {
    let cmp = 0
    if (key === 'display_name') {
      cmp = String(a.display_name || '').localeCompare(String(b.display_name || ''), 'vi', { sensitivity: 'base' })
    } else if (key === 'role') {
      cmp = (ROLE_ORDER[a.role] ?? 0) - (ROLE_ORDER[b.role] ?? 0)
    } else if (key === 'is_banned') {
      cmp = (a.is_banned ? 1 : 0) - (b.is_banned ? 1 : 0)
    } else if (key === 'created_at') {
      cmp = (new Date(a.created_at || 0).getTime()) - (new Date(b.created_at || 0).getTime())
    }
    return cmp * dir
  })
  return list
})

const subtitle = computed(() => {
  if (!users.value.length) return ''
  const total = users.value.length
  const shown = displayedUsers.value.length
  return shown === total
    ? `${total} user trên trang này`
    : `${shown}/${total} user trên trang này`
})

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}
function sortArrow(key: SortKey) {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? '↑' : '↓'
}
function sortIndicatorClass(key: SortKey) {
  return { 'usr-sort-active': sortKey.value === key }
}
function ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
  if (sortKey.value !== key) return 'none'
  return sortDir.value === 'asc' ? 'ascending' : 'descending'
}

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
    const res = await $fetch<Record<string, unknown>>(`/admin-api/users?${params}`, { headers: authHeaders() })
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
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Lỗi khi cấm user', 'error')
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
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Lỗi khi mở cấm user', 'error')
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
  } catch (e: unknown) {
    showToast((e as any)?.data?.detail || 'Lỗi khi đổi role', 'error')
  }
  acting.value = null
}

function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : ''
}

onMounted(() => fetchUsers())
</script>

<style scoped>
.usr-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

/* ── Role filter (toolbar) ── */
.usr-filter-select {
  padding: 6px 10px; min-height: 44px; font-size: .85rem;
  border: .5px solid var(--line); border-radius: 10px;
  background: var(--bg); color: var(--ink);
  cursor: pointer; transition: border-color .2s cubic-bezier(.2,1,.4,1), box-shadow .2s;
}
.usr-filter-select:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 0 2px rgba(33,150,83,.1); }
.usr-filter-select:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; box-shadow: none; }

/* ── Sortable column headers ── */
.usr-sort-th {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 6px; margin: -4px -6px;
  font: inherit; font-weight: inherit; color: inherit; text-align: left;
  background: none; border: none; border-radius: 6px;
  cursor: pointer; white-space: nowrap;
  transition: background .2s cubic-bezier(.2,1,.4,1), color .2s;
}
.usr-sort-th:hover { background: var(--primary-light, rgba(33,150,83,.08)); color: var(--primary, #219653); }
.usr-sort-th:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.usr-sort-th.usr-sort-active { color: var(--primary, #219653); }
.usr-sort-arrow {
  display: inline-block; min-width: .7em; font-size: .8em;
  transition: transform .25s cubic-bezier(.2,1,.4,1);
}

.dark .usr-filter-select { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .usr-sort-th:hover { background: rgba(33,150,83,.16); }

/* ── User cell with avatar ── */
.usr-cell { display: flex; align-items: center; gap: var(--space-3); }
.usr-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--primary-light, rgba(33,150,83,.12)); color: var(--primary, #219653);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: .78rem; flex-shrink: 0;
  text-transform: uppercase;
  transition: transform .25s cubic-bezier(.2,1,.4,1), box-shadow .25s;
}
.usr-cell:hover .usr-avatar { transform: scale(1.08); box-shadow: 0 2px 8px rgba(33,150,83,.15); }

/* ── Role select ── */
.usr-role-select {
  padding: 4px 8px; min-height: 32px; font-size: .78rem;
  border: .5px solid var(--line); border-radius: 8px;
  background: var(--bg); color: var(--ink);
  cursor: pointer; transition: border-color .2s cubic-bezier(.2,1,.4,1), box-shadow .2s;
}
.usr-role-select:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 0 2px rgba(33,150,83,.1); }
.usr-role-select:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; box-shadow: none; }

/* ── Status badges with dot ── */
.usr-status {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 2px 10px; border-radius: 100px;
  font-size: .75rem; font-weight: 600;
  transition: background .2s;
}
.usr-status-dot {
  width: 6px; height: 6px; border-radius: 50%;
}
.usr-active { background: rgba(33,150,83,.08); color: #219653; }
.usr-active .usr-status-dot { background: #219653; animation: usr-pulse 2s ease-in-out infinite; }
.usr-banned { background: rgba(217,79,61,.08); color: #D94F3D; }
.usr-banned .usr-status-dot { background: #D94F3D; }
@keyframes usr-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }

/* ── Empty ── */
.usr-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.usr-empty-icon { font-size: 2rem; opacity: .3; }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .usr-cell:hover .usr-avatar { transform: none; }
  .usr-active .usr-status-dot { animation: none; }
  .usr-sort-arrow { transition: none; }
}

/* ── Dark ── */
.dark .usr-avatar { background: rgba(33,150,83,.2); }
.dark .usr-cell:hover .usr-avatar { box-shadow: 0 2px 8px rgba(33,150,83,.25); }
.dark .usr-role-select { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .usr-active { background: rgba(33,150,83,.12); }
.dark .usr-banned { background: rgba(217,79,61,.12); }
</style>
