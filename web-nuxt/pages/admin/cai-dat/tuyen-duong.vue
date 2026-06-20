<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Tuyến đường gợi ý</h1>
        <p class="cs-subtitle">
          Dữ liệu các tuyến đường tự khám phá
          <a href="/tuyen-duong" target="_blank" rel="noopener" class="cs-view">/tuyen-duong ↗</a>
        </p>
      </div>
    </div>

    <div class="cs-help">
      <p>Mỗi tuyến là một đối tượng JSON. Trường <code>area</code> phải là <code>vinh-long</code>, <code>ben-tre</code> hoặc <code>tra-vinh</code>. <code>stops</code> là danh sách điểm dừng (mỗi điểm có <code>name</code> và <code>note</code>).</p>
    </div>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-item"></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <AdminSettingsForm :category="'page'" :fields="fields" :hide-reset="true" @saved="reload" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { DEFAULT_ROUTES } from '~/utils/routesContent'
definePageMeta({ layout: 'admin', middleware: 'admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const loading = ref(true)
const fields = ref<any[]>([])

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/page', { headers: authHeaders() })
    const stored = (r.settings || []).find((s: any) => s.key === 'tuyen_duong.routes')?.value
    const value = Array.isArray(stored) && stored.length ? stored : JSON.parse(JSON.stringify(DEFAULT_ROUTES))
    fields.value = [{
      key: 'tuyen_duong.routes',
      value,
      label: 'Danh sách tuyến đường',
      description: 'Mảng JSON các tuyến. Xoá hết = quay về mặc định.',
      input_type: 'json',
      category: 'page',
    }]
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}

onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-view { color: var(--primary, #219653); text-decoration: none; margin-left: 6px; font-family: 'SF Mono', monospace; font-size: .78rem; }
.cs-view:hover { text-decoration: underline; }
.cs-form-wrap { max-width: 760px; }
.cs-help {
  max-width: 760px; margin-bottom: var(--space-5); padding: var(--space-4);
  background: rgba(33,150,83,.04); border: .5px solid var(--line); border-radius: 12px;
  font-size: .82rem; color: var(--muted); line-height: 1.5;
}
.cs-help p { margin: 0; }
.cs-help code { font-family: 'SF Mono', monospace; font-size: .76rem; color: var(--primary, #219653); }
.cs-skeleton { max-width: 760px; }
.cs-skel-item { height: 280px; border-radius: 12px; background: var(--line); opacity: .4; animation: cs-pulse 1.5s ease-in-out infinite; }
@keyframes cs-pulse { 0%, 100% { opacity: .3; } 50% { opacity: .6; } }
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }
.dark .cs-help { background: rgba(33,150,83,.08); }
@media (prefers-reduced-motion: reduce) {
  .cs-skel-item { animation: none; }
  .cs-fade-enter-active { transition: none; }
}
</style>
