<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Liên hệ</h1>
        <p class="cs-subtitle">Email, Zalo liên hệ</p>
      </div>
    </div>
    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-row" v-for="n in 3" :key="n"><div class="cs-skel-label"></div><div class="cs-skel-input"></div></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <AdminSettingsForm :category="'contact'" :fields="fields" @saved="reload" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const fields = ref<any[]>([])
const loading = ref(true)

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/contact', { headers: authHeaders() })
    fields.value = r.settings || []
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}
onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-form-wrap { max-width: 640px; }
.cs-skeleton { max-width: 640px; display: flex; flex-direction: column; gap: var(--space-5); }
.cs-skel-row { display: flex; flex-direction: column; gap: var(--space-2); }
.cs-skel-label { width: 120px; height: 14px; border-radius: 6px; background: var(--line); animation: cs-pulse 1.5s ease-in-out infinite; }
.cs-skel-input { width: 100%; height: 44px; border-radius: 10px; background: var(--line); opacity: .5; animation: cs-pulse 1.5s ease-in-out .15s infinite; }
@keyframes cs-pulse { 0%, 100% { opacity: .4; } 50% { opacity: .7; } }
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }
@media (prefers-reduced-motion: reduce) {
  .cs-skel-label, .cs-skel-input { animation: none; }
  .cs-fade-enter-active { transition: none; }
}
</style>
