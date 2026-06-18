<template>
  <div>
    <div class="admin-head-row">
      <h1>Chưa phân loại xã/phường</h1>
      <button class="admin-refresh" :disabled="loading" @click="load">🔄 Làm mới</button>
    </div>
    <p class="admin-muted">Entity nội dung chưa gán xã. Gán đúng để xuất hiện ở trang xã/phường + danh mục khu vực.</p>

    <div class="bar">
      <input v-model="q" class="input" placeholder="Tìm theo tên…" @keyup.enter="load" />
      <button class="btn btn-secondary" @click="load">Tìm</button>
      <span class="admin-muted">{{ total }} chưa phân loại</span>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <table v-else-if="items.length" class="admin-simple-table">
      <thead><tr><th>Tên</th><th>Loại</th><th>Gán xã/phường</th><th></th></tr></thead>
      <tbody>
        <tr v-for="e in items" :key="e.id">
          <td><strong>{{ e.name }}</strong><br><small class="admin-muted">{{ e.summary }}</small></td>
          <td>{{ e.type }}</td>
          <td>
            <select v-model="pick[e.id]" class="input">
              <option value="">— Chọn —</option>
              <optgroup v-for="g in wardGroups" :key="g.area" :label="g.label">
                <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
              </optgroup>
            </select>
          </td>
          <td><button class="btn btn-primary btn-sm" :disabled="!pick[e.id] || busy[e.id]" @click="assign(e)">Gán</button></td>
        </tr>
      </tbody>
    </table>
    <EmptyState v-else message="Không có entity nào chưa phân loại 🎉" />
  </div>
</template>

<script setup lang="ts">
import { AREA_META } from '~/composables/useConstants'
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']

const q = ref('')
const items = ref<any[]>([])
const total = ref(0)
const loading = ref(true)
const pick = ref<Record<string, string>>({})
const busy = ref<Record<string, boolean>>({})

const { data: places } = await useAsyncData('cpl-places', () => $fetch<any>('/api/places').catch(() => []))
const wardGroups = computed(() => {
  const wards = (places.value || []).filter((p: any) => ADMIN_LEVELS.includes(p.level))
  return Object.keys(AREA_META).map(area => ({
    area, label: AREA_META[area].name,
    wards: wards.filter((w: any) => w.area === area).sort((a: any, b: any) => a.name.localeCompare(b.name, 'vi')),
  })).filter(g => g.wards.length)
})

async function load() {
  loading.value = true
  try {
    const r = await $fetch<any>(`/admin-api/unclassified?limit=200&q=${encodeURIComponent(q.value)}`, { headers: authHeaders() })
    items.value = r.entities || []
    total.value = r.total || 0
  } catch { showToast('Không tải được danh sách', 'error') }
  loading.value = false
}

async function assign(e: any) {
  const pid = pick.value[e.id]
  if (!pid) return
  busy.value = { ...busy.value, [e.id]: true }
  try {
    await $fetch(`/admin-api/entities/${e.id}/place`, { method: 'POST', headers: authHeaders(), body: { place_id: pid } })
    items.value = items.value.filter(x => x.id !== e.id)  // bỏ khỏi danh sách chưa phân loại
    total.value = Math.max(0, total.value - 1)
    showToast(`Đã gán ${e.name}`, 'success')
  } catch (err: any) {
    showToast(err?.data?.detail || 'Gán thất bại', 'error')
  }
  busy.value = { ...busy.value, [e.id]: false }
}

onMounted(load)
</script>

<style scoped>
.bar { display: flex; gap: var(--space-2); align-items: center; margin: var(--space-3) 0 var(--space-4); }
.bar .input { max-width: 280px; }
.admin-simple-table select.input { max-width: 220px; }
</style>
