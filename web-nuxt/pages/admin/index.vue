<template>
  <div>
    <div class="admin-head-row">
      <h1>Dashboard</h1>
      <button class="admin-refresh" :disabled="loading" @click="fetchDashboard">🔄 Làm mới</button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_entities || 0 }}</div>
        <div class="stat-label">Entities</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_places || 0 }}</div>
        <div class="stat-label">Địa điểm</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_relationships || 0 }}</div>
        <div class="stat-label">Quan hệ</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_itineraries || 0 }}</div>
        <div class="stat-label">Lịch trình</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.low_confidence || 0 }}</div>
        <div class="stat-label">Cần xem lại</div>
      </div>
      <div v-if="modStats.pending !== undefined" class="stat-card">
        <div class="stat-value">{{ modStats.pending }}</div>
        <div class="stat-label">Chờ duyệt</div>
      </div>
      <NuxtLink v-if="infoReports !== null" to="/admin/bao-cao" class="stat-card admin-link-plain">
        <div class="stat-value">{{ infoReports }}</div>
        <div class="stat-label">Báo sai ⚠️</div>
      </NuxtLink>
    </div>

    <h2 class="admin-section-title">Theo loại</h2>
    <div class="stat-grid">
      <div v-for="(count, type) in stats.by_type" :key="type" class="stat-card admin-type-stat">
        <div class="stat-value">{{ count }}</div>
        <div class="stat-label">{{ type }}</div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const stats = ref<any>({})
const modStats = ref<any>({})
const infoReports = ref<number | null>(null)
const loading = ref(true)

async function fetchDashboard() {
  loading.value = true
  try {
    const [s, m, ir] = await Promise.all([
      $fetch<any>('/admin-api/stats', { headers: authHeaders() }),
      $fetch<any>('/admin-api/moderation/stats', { headers: authHeaders() }).catch(() => ({})),
      $fetch<any>('/admin-api/info-reports?limit=1', { headers: authHeaders() }).catch(() => null),
    ])
    stats.value = s
    modStats.value = m
    if (ir) infoReports.value = ir.total ?? 0
  } catch {
    showToast('Không thể tải dữ liệu dashboard', 'error')
  }
  loading.value = false
}

onMounted(fetchDashboard)
</script>
