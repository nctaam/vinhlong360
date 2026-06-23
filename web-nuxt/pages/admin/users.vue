<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Quản lý Users</h1>
        <p class="usr-subtitle">{{ subtitle }}</p>
      </div>
      <div class="usr-head-actions">
        <button type="button" class="admin-refresh" :disabled="loading || !displayedUsers.length" @click="exportCSV()">
          <span aria-hidden="true">&#128229;</span> Xuất CSV
        </button>
        <button type="button" class="admin-refresh" :disabled="loading" @click="fetchUsers()">
          <span :class="{ 'refresh-spin': loading }">&#8635;</span> Làm mới
        </button>
      </div>
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

    <div v-if="!loading && users.length" class="usr-rolecounts" aria-label="Số lượng user theo role">
      <button type="button" class="usr-rolecount" :class="{ active: roleFilter === 'user' }" @click="roleFilter = roleFilter === 'user' ? 'all' : 'user'">
        user <span class="usr-rolecount-n">{{ roleCounts.user }}</span>
      </button>
      <button type="button" class="usr-rolecount" :class="{ active: roleFilter === 'moderator' }" @click="roleFilter = roleFilter === 'moderator' ? 'all' : 'moderator'">
        moderator <span class="usr-rolecount-n">{{ roleCounts.moderator }}</span>
      </button>
      <button type="button" class="usr-rolecount" :class="{ active: roleFilter === 'admin' }" @click="roleFilter = roleFilter === 'admin' ? 'all' : 'admin'">
        admin <span class="usr-rolecount-n">{{ roleCounts.admin }}</span>
      </button>
    </div>

    <div v-if="loading" class="admin-table-wrap" aria-busy="true" aria-label="Đang tải danh sách user">
      <table class="admin-table">
        <thead>
          <tr>
            <th>User</th><th>SĐT</th><th>Role</th><th>Trạng thái</th><th>Ngày tạo</th><th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="n in 6" :key="'sk-' + n" class="usr-skeleton-row">
            <td v-for="c in 6" :key="'sk-' + n + '-' + c"><div class="usr-skeleton-line"></div></td>
          </tr>
        </tbody>
      </table>
    </div>
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
          <template v-for="u in displayedUsers" :key="u.id">
          <tr>
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
              <button type="button" v-if="u.is_banned" class="btn-success" :disabled="acting === u.id" @click="requestUnban(u.id)">Mở cấm</button>
              <button type="button" v-else class="btn-danger" :disabled="acting === u.id" @click="requestBan(u.id)">Cấm</button>
            </td>
          </tr>
          <tr v-if="confirmingId === u.id" class="usr-confirm-row">
            <td colspan="6">
              <div class="usr-confirm" role="alertdialog" :aria-label="confirmAction === 'ban' ? 'Xác nhận cấm user' : 'Xác nhận mở cấm user'">
                <span class="usr-confirm-icon" aria-hidden="true">{{ confirmAction === 'ban' ? '⚠' : '✓' }}</span>
                <span class="usr-confirm-text">
                  {{ confirmAction === 'ban' ? 'Cấm' : 'Mở cấm' }} <strong>{{ u.display_name || u.phone }}</strong>?
                </span>
                <div class="usr-confirm-actions">
                  <button type="button" :class="confirmAction === 'ban' ? 'btn-danger' : 'btn-success'" :disabled="acting === u.id" @click="confirmProceed(u.id)">Xác nhận</button>
                  <button type="button" class="usr-confirm-cancel" :disabled="acting === u.id" @click="cancelConfirm()">Huỷ</button>
                </div>
              </div>
            </td>
          </tr>
          </template>
          <tr v-if="!displayedUsers.length">
            <td colspan="6" class="admin-empty-row">
              <div class="admin-empty-state">
                <div class="admin-empty-state-icon">&#128101;</div>
                <div class="admin-empty-state-text">{{ users.length ? 'Không có user khớp bộ lọc trên trang này.' : 'Không có user nào.' }}</div>
                <div class="admin-empty-state-hint">{{ users.length ? 'Thử đổi bộ lọc role hoặc xoá từ khoá tìm kiếm.' : 'Dùng ô tìm kiếm theo SĐT hoặc tên để bắt đầu.' }}</div>
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

// ── Inline confirm-before-destructive (replaces native confirm() for ban/unban) ──
const confirmingId = ref<string | null>(null)
const confirmAction = ref<'ban' | 'unban' | null>(null)
function requestBan(id: string) { confirmingId.value = id; confirmAction.value = 'ban' }
function requestUnban(id: string) { confirmingId.value = id; confirmAction.value = 'unban' }
function cancelConfirm() { confirmingId.value = null; confirmAction.value = null }
function confirmProceed(id: string) {
  const action = confirmAction.value
  confirmingId.value = null
  confirmAction.value = null
  if (action === 'ban') ban(id)
  else if (action === 'unban') unban(id)
}

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

const roleCounts = computed(() => {
  const c: Record<'user' | 'moderator' | 'admin', number> = { user: 0, moderator: 0, admin: 0 }
  users.value.forEach((u: any) => {
    const r = (u.role || 'user') as 'user' | 'moderator' | 'admin'
    if (r in c) c[r]++
    else c.user++
  })
  return c
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
    await $fetch(`/admin-api/users/${id}/role`, { method: 'POST', headers: authHeaders(), query: { role } })
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

function csvCell(v: unknown) {
  const s = String(v ?? '')
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
function exportCSV() {
  const header = ['ID', 'Tên', 'SĐT', 'Role', 'Trạng thái', 'Ngày tạo']
  const rows = displayedUsers.value.map((u: any) => [
    u.id,
    u.display_name || '',
    u.phone || '',
    u.role || 'user',
    u.is_banned ? 'Bị cấm' : 'Hoạt động',
    formatDate(u.created_at),
  ].map(csvCell).join(','))
  const csv = '﻿' + [header.map(csvCell).join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `users-trang-${page.value}.csv`
  a.click()
  URL.revokeObjectURL(url)
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

/* ── Head actions (refresh + export) ── */
.usr-head-actions { display: flex; gap: var(--space-2); align-items: center; flex-shrink: 0; }

/* ── Role count chips (quick filter) ── */
.usr-rolecounts { display: flex; gap: var(--space-2); flex-wrap: wrap; margin: calc(var(--space-3) * -1) 0 var(--space-4); }
.usr-rolecount {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; min-height: 32px;
  font-size: .78rem; font-weight: 500; color: var(--muted);
  background: var(--bg); border: .5px solid var(--line); border-radius: 100px;
  cursor: pointer;
  transition: border-color .2s cubic-bezier(.2,1,.4,1), color .2s, background .2s;
}
.usr-rolecount:hover { border-color: var(--primary, #219653); color: var(--primary, #219653); }
.usr-rolecount:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.usr-rolecount.active { border-color: var(--primary, #219653); color: var(--primary, #219653); background: var(--primary-light, rgba(33,150,83,.08)); }
.usr-rolecount-n {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; padding: 0 5px; height: 18px;
  font-size: .7rem; font-weight: 700; border-radius: 100px;
  background: var(--line); color: var(--ink);
}
.usr-rolecount.active .usr-rolecount-n { background: var(--primary, #219653); color: #fff; }

/* ── Inline confirm row (ban/unban) ── */
.usr-confirm-row td { background: var(--bg-alt); }
.usr-confirm {
  display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-3);
  padding: var(--space-2) var(--space-1);
}
.usr-confirm-icon { font-size: 1.1rem; line-height: 1; flex-shrink: 0; }
.usr-confirm-text { font-size: .88rem; color: var(--ink); }
.usr-confirm-actions { display: flex; gap: var(--space-2); margin-left: auto; }
.usr-confirm-actions button {
  padding: 6px var(--space-3); font-size: .8rem; border-radius: 8px;
  border: .5px solid var(--line); background: var(--bg); cursor: pointer;
  font-weight: 500; min-height: 36px;
  transition: background .25s, color .25s, border-color .25s, transform .35s cubic-bezier(.2,1,.4,1), box-shadow .25s;
}
.usr-confirm-actions button:active { transform: scale(.95); transition-duration: .08s; }
.usr-confirm-actions button:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.usr-confirm-actions button:disabled { opacity: .5; cursor: default; }
.usr-confirm-actions .btn-danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.usr-confirm-actions .btn-danger:hover { background: var(--error, #D94F3D); color: #fff; box-shadow: 0 2px 8px rgba(217,79,61,.2); }
.usr-confirm-actions .btn-success { color: var(--primary, #219653); border-color: var(--primary, #219653); }
.usr-confirm-actions .btn-success:hover { background: var(--primary, #219653); color: #fff; box-shadow: 0 2px 8px rgba(33,150,83,.2); }
.usr-confirm-cancel:hover { background: var(--bg-alt); }

/* ── Loading skeleton rows ── */
.usr-skeleton-line {
  height: 16px; border-radius: 6px;
  background: linear-gradient(90deg, var(--line) 25%, rgba(0,0,0,.03) 50%, var(--line) 75%);
  background-size: 200% 100%;
  animation: usr-skeleton-pulse 1.4s ease-in-out infinite;
}
@keyframes usr-skeleton-pulse { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .usr-cell:hover .usr-avatar { transform: none; }
  .usr-active .usr-status-dot { animation: none; }
  .usr-sort-arrow { transition: none; }
  .usr-skeleton-line { animation: none; }
}

/* ── Dark ── */
.dark .usr-avatar { background: rgba(33,150,83,.2); }
.dark .usr-cell:hover .usr-avatar { box-shadow: 0 2px 8px rgba(33,150,83,.25); }
.dark .usr-role-select { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .usr-active { background: rgba(33,150,83,.12); }
.dark .usr-banned { background: rgba(217,79,61,.12); }
.dark .usr-rolecount { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .usr-rolecount-n { background: rgba(255,255,255,.12); color: var(--ink); }
.dark .usr-rolecount.active { background: rgba(33,150,83,.18); }
.dark .usr-skeleton-line { background: linear-gradient(90deg, rgba(255,255,255,.06) 25%, rgba(255,255,255,.12) 50%, rgba(255,255,255,.06) 75%); background-size: 200% 100%; }
.dark .usr-confirm-actions button { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .usr-confirm-cancel:hover { background: rgba(255,255,255,.06); }
</style>
